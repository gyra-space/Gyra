"""AppCard 开发期数据预览工具 —— 让生成 skill 的 agent 在写卡片时能验证数据并看性能。

定位:这是**数据库资源**自带的取数工具之一(与 execute_sql / get_table_spec /
list_tables 一起,随 ``DBResource`` 一起注入 agent 的 TOOLS 槽),无需单独绑定
``app_card`` 资源。

背景:
  生成期 agent 用 ``execute_sql`` / ``execute_metric_query`` 探索数据时,返回的是
  VIS 组件(``d-sql-query`` / ``d-ecp-metric``),其 ``rows`` 是**二维数组**;而运行期
  ``GyraAppCard.op`` 返回的是**对象数组**(dict rows)。两者不一致导致"预览数据对,
  运行期渲染错"。

本工具绕过 VIS 归一化,直接复用 app_card 运行期的同一派发路径
(``run_readonly_sql`` / ``execute_metric_query``),并额外带上性能基线:

  - ``op="query.sql"`` / ``"sql.preview"`` → 运行期同款 dict-rows + ``row_count`` + ``elapsed_ms``
  - ``op="query.metric"`` / ``"metric.preview"`` → 运行期同款 dict-rows + ``row_count`` + ``elapsed_ms``
  - ``op="sql.explain"`` → 尽力而为查询计划(用于调优/看索引),失败降级为提示

工具输出为**干净 JSON**(非 VIS 包裹),agent 可直接用返回的 ``columns`` / ``rows``
作为写渲染逻辑与核对字段名的依据,并用 ``elapsed_ms`` / ``row_count`` 评估性能。

取数走应用卡片**专用有界线程池**(run_bounded): 并发+排队满时抛 AppCardBusyError
快速失败,避免大量慢 SQL 把全局线程池和事件循环拖死。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from gyra.agent.tools.base import ToolCategory, ToolRiskLevel
from gyra.agent.tools.decorators import tool

from gyra_serve.app_card.service.service import _find_query, run_readonly_sql
from gyra_serve.app_card.sql_runtime import AppCardBusyError, run_bounded

_SQL_OPS = {"query.sql", "sql.preview"}
_METRIC_OPS = {"query.metric", "metric.preview"}
_EXPLAIN_OPS = {"sql.explain"}


def _finish(result: Dict[str, Any], started: float) -> Dict[str, Any]:
    """统一补性能基线字段(elapsed_ms),并保证关键字段形状稳定。"""
    result.setdefault("columns", [])
    result.setdefault("rows", [])
    result.setdefault("row_count", len(result.get("rows") or []))
    result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    return result


def _busy_result(e: BaseException) -> Dict[str, Any]:
    """排队已满的快速失败结果: 不占线程等待, 提示稍后重试。"""
    return {"trust": "none", "error": str(e), "code": "APP_CARD_BUSY",
            "columns": [], "rows": [], "row_count": 0}


def _resolve_sql_args(
    params: Dict[str, Any], query_key: Optional[str], queries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """复刻运行期 _invoke_sql 的 query_key 解析 + bind 合并,保证与运行期一致。"""
    q = _find_query(queries or [], query_key)
    sql = params.get("sql")
    datasource_id = params.get("datasource_id")
    bind_params = params.get("bind_params") or {}
    if q and q.get("kind") == "sql":
        sql = sql or q.get("sql")
        datasource_id = datasource_id or q.get("datasource_id")
        bind_params = {**q.get("bind_params", {}), **bind_params}
    limit = params.get("limit") if not q else q.get("limit")
    return {"sql": sql, "datasource_id": datasource_id,
            "bind_params": bind_params, "limit": limit}


def _run_sql_explain(
    datasource_id: int, sql: str, bind_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """尽力而为查询计划:EXPLAIN <sql> 只读执行,失败降级为提示,永不抛异常。"""
    try:
        from gyra._private.config import Config
        from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao

        config = ConnectConfigDao().get_one({"id": datasource_id})
        db_name = None
        if config is not None:
            db_name = config.get("db_name") if isinstance(config, dict) else getattr(config, "db_name", None)
        if not db_name:
            return {"trust": "none", "error": f"数据源 {datasource_id} 不存在",
                    "columns": [], "rows": [], "row_count": 0, "sql": sql}
        connector = Config().local_db_manager.get_connector(db_name)
        raw = connector.run(f"EXPLAIN {sql}")
        columns, rows = [], []
        if raw:
            columns = list(raw[0])
            rows = [dict(zip(columns, r)) for r in raw[1:]]
        return {"trust": "inferred", "columns": columns, "rows": rows,
                "row_count": len(rows), "sql": f"EXPLAIN {sql}",
                "note": "查询计划(EXPLAIN),用于性能调优;不同数据库解释字段不同"}
    except Exception as e:  # noqa: BLE001
        return {"trust": "none", "error": f"EXPLAIN 不可用: {e}",
                "columns": [], "rows": [], "row_count": 0, "sql": sql}


@tool(
    "app_card_preview",
    description=(
        "AppCard 应用卡片开发期取数预览：按运行期同一派发路径执行 query.sql / "
        "query.metric，返回对象数组 rows + trust + row_count + elapsed_ms(性能基线)。"
        "开发应用卡片时用它验证 SQL/指标列名与取数、并评估/调优查询性能，"
        "避免用 execute_sql(二维数组 rows)写代码导致运行期渲染错乱。"
    ),
    args={
        "op": {
            "type": "string",
            "description": "取值：query.sql / sql.preview / query.metric / metric.preview / sql.explain",
        },
        "params": {
            "type": "object",
            "description": (
                "query.sql 传 {sql, datasource_id, bind_params?, limit?}；"
                "query.metric 传 {metric_id, group_by?, filters?, time_range?}。"
            ),
            "required": False,
        },
        "query_key": {
            "type": "string",
            "description": "引用 queries 里已声明的命名查询(可选，与 params 二选一)",
            "required": False,
        },
        "queries": {
            "type": "array",
            "description": "命名查询契约(未落库也可)，配合 query_key 引用",
            "required": False,
        },
        "workspace_id": {
            "type": "integer",
            "description": "工作空间 id(指标执行必需)",
            "required": False,
        },
    },
    category=ToolCategory.DATABASE,
    risk_level=ToolRiskLevel.LOW,
    tags=["app-card", "preview", "sql", "metric", "dev"],
)
async def app_card_preview(
    op: str,
    params: Optional[Dict[str, Any]] = None,
    query_key: Optional[str] = None,
    queries: Optional[List[Dict[str, Any]]] = None,
    workspace_id: Optional[int] = None,
    **kwargs,
) -> str:
    params = params or {}
    queries = list(queries or [])
    started = time.perf_counter()

    if op in _SQL_OPS:
        args = _resolve_sql_args(params, query_key, queries)
        if not args["sql"] or not args["datasource_id"]:
            result = {"trust": "none", "error": "缺少 sql 或 datasource_id",
                      "columns": [], "rows": [], "row_count": 0}
            return json.dumps(_finish(result, started), ensure_ascii=False)
        try:
            result = await run_bounded(
                run_readonly_sql,
                int(args["datasource_id"]),
                args["sql"],
                args["bind_params"],
                args["limit"],
            )
        except AppCardBusyError as e:
            result = _busy_result(e)
        return json.dumps(_finish(result, started), ensure_ascii=False, default=str)

    if op in _EXPLAIN_OPS:
        args = _resolve_sql_args(params, query_key, queries)
        if not args["sql"] or not args["datasource_id"]:
            result = {"trust": "none", "error": "缺少 sql 或 datasource_id",
                      "columns": [], "rows": [], "row_count": 0}
            return json.dumps(_finish(result, started), ensure_ascii=False)
        try:
            result = await run_bounded(
                _run_sql_explain,
                int(args["datasource_id"]),
                args["sql"],
                args["bind_params"],
            )
        except AppCardBusyError as e:
            result = _busy_result(e)
        return json.dumps(_finish(result, started), ensure_ascii=False, default=str)

    if op in _METRIC_OPS:
        from gyra_serve.ecp.service.executor import GateError, execute_metric_query

        if not workspace_id:
            result = {"trust": "none", "error": "指标执行需要 workspace_id",
                      "columns": [], "rows": [], "row_count": 0}
            return json.dumps(_finish(result, started), ensure_ascii=False)
        metric_id = params.get("metric_id")
        q = _find_query(queries, query_key)
        if q and q.get("kind") == "metric":
            metric_id = metric_id or q.get("metric_id")
        if not metric_id:
            result = {"trust": "none", "error": "缺少 metric_id",
                      "columns": [], "rows": [], "row_count": 0}
            return json.dumps(_finish(result, started), ensure_ascii=False)
        try:
            result = await run_bounded(
                execute_metric_query,
                metric_id=metric_id,
                workspace_id=str(workspace_id),
                group_by=params.get("group_by"),
                filters=params.get("filters"),
                time_range=params.get("time_range"),
            )
        except GateError as e:
            result = {"trust": "none", "error": str(e),
                      "code": getattr(e, "code", "GATE_REJECTED"),
                      "columns": [], "rows": [], "row_count": 0}
        except AppCardBusyError as e:
            result = _busy_result(e)
        return json.dumps(_finish(result, started), ensure_ascii=False, default=str)

    result = {"trust": "none", "error": f"不支持的能力 {op}",
              "columns": [], "rows": [], "row_count": 0}
    return json.dumps(_finish(result, started), ensure_ascii=False)
