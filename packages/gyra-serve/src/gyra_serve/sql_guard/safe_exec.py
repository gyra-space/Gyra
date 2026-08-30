"""SQL 执行安全层 — Agent 工具链路的硬约束。

背景:Agent/场景空间经 DB 资源(execute_sql)/ ECP 资源(execute_raw_sql)
执行 SQL 时,历史上直接裸跑 ``connector.run(sql)`` —— 无超时、无 LIMIT 注入、
无行数截断,一条烂 SQL 即可拖垮整库。本模块把已有的两个能力接到工具层:

- ``RDBMSConnector.query_ex()``:按方言注入语句超时 + ``max_rows`` 流式截断
- guard ``parse_sql`` 的 LIMIT 识别(参考 SelectLimitRule,但加方言门控:
  Oracle/MSSQL 等不支持 LIMIT 的方言不注入,避免产出语法错误)

提示词软约束文案也集中在此(SQL_USAGE_RULES),供 DBCapability 的
<usage_rules> 与 ECP BEHAVIOR_GUIDE 统一引用。
"""

import logging
import re
from typing import Any, List, Optional, Tuple

from gyra_serve.sql_guard.models import SQLType

logger = logging.getLogger(__name__)

# 支持 LIMIT 语法的方言白名单;不在名单内的方言(oracle/mssql 等)不注入
# LIMIT,由 query_ex 的 max_rows 流式截断 + 语句超时兜底。
_LIMIT_DIALECTS = {
    "mysql",
    "postgresql",
    "postgres",
    "sqlite",
    "duckdb",
    "oceanbase",
    "starrocks",
    "clickhouse",
}

_LIMIT_VALUE_PATTERN = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)

# 注入 system prompt / 行为约定的 SQL 编写规范(软约束,与工具层硬约束互补)
SQL_USAGE_RULES = """【SQL 编写规范 — 必须遵守】
1. 性能优先:只查询需要的列,禁止 SELECT *
2. 单次查询返回不超过 2000 行;更多数据用 LIMIT 分页/分批,明细大结果用 output_to_file 文件模式
3. 大表必须带时间过滤,单次查询时间跨度不超过 1 年;跨年分析分批查询再汇总
4. WHERE 优先使用索引列/分区列,避免函数包裹索引列导致全表扫描
5. 聚合/排序在数据库内完成(GROUP BY / ORDER BY + LIMIT),不拉全量明细到内存再处理
6. 不确定开销时先小成本探查(LIMIT 采样 / COUNT / EXPLAIN),禁止盲目执行可能整库扫描的重查询"""


def apply_select_limit(sql: str, dialect: str, limit: int) -> str:
    """对 SELECT/WITH 查询注入或封顶 LIMIT(仅 LIMIT 系方言)。

    - 无 LIMIT:追加 ``LIMIT {limit}``
    - 已有 LIMIT 超过上限:封顶为 {limit}(与 SelectLimitRule 一致,替换该值的
      所有出现)
    - 非 SELECT/WITH、非 LIMIT 系方言、limit<=0:原样返回

    Args:
        sql: 原始 SQL
        dialect: 数据库方言(connector.dialect)
        limit: 行数上限,<=0 表示不干预
    """
    if not limit or limit <= 0:
        return sql
    if (dialect or "").lower() not in _LIMIT_DIALECTS:
        return sql

    from gyra_serve.sql_guard.guard import get_sql_guard

    parsed = get_sql_guard().parse_sql(sql)
    if parsed.sql_type not in (SQLType.SELECT.value, SQLType.WITH.value):
        return sql

    if not parsed.has_limit:
        cleaned = sql.rstrip().rstrip(";")
        return f"{cleaned} LIMIT {limit}"

    if parsed.limit_value and parsed.limit_value > limit:
        pattern = re.compile(
            r"\bLIMIT\s+" + str(parsed.limit_value), re.IGNORECASE
        )
        return pattern.sub(f"LIMIT {limit}", sql)

    return sql


def run_select_with_limits(
    connector: Any,
    sql: str,
    timeout: Optional[float],
    max_rows: int,
) -> Tuple[List, bool]:
    """带超时与行数截断执行查询,返回与 ``connector.run()`` 相同形状的结果。

    优先走 ``connector.query_ex(timeout=..., max_rows=max_rows+1)``:多取一行
    作为截断哨兵;无 query_ex 的 connector 回退 ``connector.run``(不截断)。

    Args:
        connector: RDBMSConnector(或兼容对象)
        sql: 已经过 apply_select_limit 处理的 SQL
        timeout: 语句超时秒数,None 或 <=0 表示不设超时
        max_rows: 行数上限,<=0 表示不截断

    Returns:
        (result, truncated): result 形状为 ``[field_names, *rows]``(与 run()
        一致,下游分页/导出/脱敏逻辑不变);truncated 表示结果触及 max_rows 被截断

    Raises:
        TimeoutError: 查询超时(由 query_ex 按方言抛出),调用方负责格式化
    """
    effective_timeout = timeout if timeout and timeout > 0 else None
    sentinel = max_rows + 1 if max_rows and max_rows > 0 else None

    if hasattr(connector, "query_ex"):
        field_names, rows = connector.query_ex(
            sql, fetch="all", timeout=effective_timeout, max_rows=sentinel
        )
        rows = list(rows) if rows else []
        truncated = bool(
            sentinel is not None and len(rows) > max_rows
        )
        if truncated:
            rows = rows[:max_rows]
        if not field_names:
            return [], False
        return [tuple(field_names)] + rows, truncated

    # 无 query_ex 的 connector:保持原行为(无法超时/截断,仅记日志)
    logger.warning(
        "[safe_exec] connector %s has no query_ex, running without "
        "timeout/row-cap protection",
        type(connector).__name__,
    )
    return connector.run(sql), False


def timeout_error_message(timeout: float, max_rows: int) -> str:
    """超时错误的统一文案(引导模型优化 SQL 后重试)。"""
    return (
        f"查询超过 {timeout:g}s 被终止,已保护数据库不被长时间阻塞。\n"
        f"请优化 SQL 后重试:\n"
        f"1. 加大时间过滤力度(单次查询时间跨度不超过 1 年,大表必须带时间条件)\n"
        f"2. 用 GROUP BY 在库内聚合,避免拉全量明细\n"
        f"3. WHERE 使用索引列/分区列,避免函数包裹索引列\n"
        f"4. 只查询需要的列,不要 SELECT *\n"
        f"5. 单次返回不超过 {max_rows} 行,可先用 LIMIT 小范围探查或 EXPLAIN 评估开销"
    )
