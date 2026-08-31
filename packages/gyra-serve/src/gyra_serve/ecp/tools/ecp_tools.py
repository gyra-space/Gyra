"""ECP agent tools (tool surface, ECP v1.2).

The protocol is enforced by the TOOL SURFACE, not by prompts:
- `execute_metric_query` is the ONLY path to ✅ verified numbers (the gate
  lives in service/executor.py, agent-invisible and unbypassable)
- `execute_raw_sql` is the sanctioned fallback — always ⚠️ inferred, always
  op-logged as a miss (lint clustering feedstock)
- trust markers are hardcoded in tool return values, never agent-declared
- user disambiguation reuses gyra-core's builtin AskUserTool

Tools are stateless: workspace_id is an argument (default 'default').
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from gyra.agent.tools.decorators import tool
from gyra.agent.tools.base import ToolCategory, ToolRiskLevel
from gyra.agent.resource.tool.base import FunctionTool
from gyra.vis import Vis

from ..config import DEFAULT_WORKSPACE_ID, STATUS_CONFIRMED
from ..models.models import (
    MissLearnDao,
    OpLogDao,
    SemanticAlignmentDao,
    SemanticObjectDao,
)
from ..service.query_understanding import expand_query_terms

logger = logging.getLogger(__name__)


def _ws(workspace_id: Optional[str]) -> str:
    return workspace_id or DEFAULT_WORKSPACE_ID


def _service():
    """ECP Service 组件(tools 无状态,经 SYSTEM_APP 按需获取)。"""
    from gyra._private.config import Config

    from ..config import SERVE_SERVICE_COMPONENT_NAME
    from ..service.service import Service

    return Config().SYSTEM_APP.get_component(SERVE_SERVICE_COMPONENT_NAME, Service)


# d-sql-query VIS 围栏的 JSON 上限:保证围栏完整、不被外层截断,避免前端渲染成残缺组件。
_MAX_SQL_VIS_BYTES = 3 * 1024
# execute_raw_sql 单次最多物化的行数(避免超大结果整体进内存),超出部分用 has_more 提示。
_MAX_SQL_VIS_ROWS = 1000


def _cap_sql_display_rows(
    sql: str,
    db_name: str,
    db_type: str,
    dialect: str,
    columns: List[Any],
    rows: List[List[Any]],
) -> List[List[Any]]:
    """逐步缩减显示行数,使 d-sql-query JSON 不超过 _MAX_SQL_VIS_BYTES。

    原始查询可能返回超大量行(execute_raw_sql 为探索路径不强制 LIMIT),若整段围栏
    超过 _MAX_TOOL_OUTPUT_CHARS(8K)会被 ToolAction 截断,把 JSON 拦腰截断导致前端
    渲染成残缺组件;这里先缩减展示行数,保证围栏完整且数据量可控。

    返回缩减后的展示 rows(仅含本页)。
    """
    if not rows:
        return rows

    def _size(r: List[List[Any]]) -> int:
        data = {
            "sql": sql,
            "db_name": db_name,
            "db_type": db_type,
            "dialect": dialect,
            "columns": columns,
            "rows": r,
        }
        return len(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    if _size(rows) <= _MAX_SQL_VIS_BYTES:
        return rows

    for limit in (200, 100, 50, 20, 10, 5):
        if limit >= len(rows):
            continue
        candidate = rows[:limit]
        if _size(candidate) <= _MAX_SQL_VIS_BYTES:
            return candidate

    return rows[:5]


@tool(
    "search_semantics",
    description=(
        "Search CONFIRMED enterprise semantic objects (metrics/entities/"
        "dimensions/relations). Accepts natural language: the query is "
        "expanded via LLM (synonyms/aliases/CN-EN variants, returned as "
        "expanded_terms) and matched against object names/aliases/descriptions "
        "plus confirmed alignment synonyms. Always search here first when "
        "answering business-number questions; only use execute_raw_sql if "
        "nothing matches."
    ),
    args={
        "query": {
            "type": "string",
            "description": "关键词或自然语言短语（名称/别名/id，中英文均可）",
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def search_semantics(query: str, workspace_id: Optional[str] = None, **kwargs) -> str:
    ws = _ws(workspace_id)
    entries = await asyncio.to_thread(SemanticObjectDao().list_catalog, ws)
    # 查询理解:本地分词 + LLM 语义扩展(同义词/别名/中英对照),失败降级本地分词
    terms = await expand_query_terms(query)
    term_set = [t.casefold() for t in terms if t and t.strip()]
    ql = (query or "").strip().casefold()
    # 已确认语义对齐:object_id → [实体名],LLM 推理产物(人工确认)补齐跨命名映射
    aligned_map: Dict[str, List[str]] = {}
    try:
        for avo in await asyncio.to_thread(
            SemanticAlignmentDao().list, ws, status=STATUS_CONFIRMED
        ):
            aligned_map.setdefault(avo.object_id, []).append(avo.entity_name.casefold())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp] search_semantics alignment load failed: {e}")

    scored = []
    for e in entries:
        id_l = (e.id or "").casefold()
        names_l = [n.casefold() for n in [e.name or "", *(e.aliases or [])] if n]
        haystack = " ".join(
            [id_l, e.name or "", *(e.aliases or []), e.one_line or ""]
        ).casefold()
        hit_terms = [t for t in term_set if t in haystack]
        exact = bool(ql) and (any(ql in n for n in names_l) or ql in id_l)
        ens = aligned_map.get(e.id) or []
        aligned_hit = any(
            t in en or en in t for t in term_set for en in ens
        ) or bool(ql) and any(ql in en or en in ql for en in ens)
        if not exact and not hit_terms and not aligned_hit:
            continue
        score = len(hit_terms) / len(term_set) if term_set else 0.0
        match_type = "expanded"
        if aligned_hit:
            score += 1.5
            match_type = "aligned"
        if exact:
            score += 2.0
            match_type = "exact"
        scored.append(
            (
                round(score, 4),
                e.id or "",
                {
                    "id": e.id,
                    "type": e.obj_type,
                    "name": e.name,
                    "aliases": e.aliases,
                    "one_line": e.one_line,
                    "score": round(score, 4),
                    "match_type": match_type,
                },
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]))
    results = [item[2] for item in scored[:50]]
    # vis 输出:右面板独立渲染(类型徽章+结果卡片);失败回退裸 JSON
    try:
        vis = Vis.of("d-ecp-search")
        if vis:
            return vis.sync_display(
                query=query,
                workspace_id=ws,
                total=len(results),
                results=results,
                expanded_terms=terms,
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp] search_semantics vis display failed: {e}")
    return json.dumps(
        {"expanded_terms": terms, "total": len(results), "results": results},
        ensure_ascii=False,
    )


@tool(
    "get_semantic_object",
    description=(
        "Get the full confirmed payload of a semantic object: caliber "
        "definition, binding, dimension values, grain, version."
    ),
    args={
        "object_id": {"type": "string", "description": "对象 id，如 mtr.net_sales"},
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def get_semantic_object(object_id: str, workspace_id: Optional[str] = None, **kwargs) -> str:
    vo = await asyncio.to_thread(
        SemanticObjectDao().get_confirmed, object_id, _ws(workspace_id)
    )
    if not vo:
        return json.dumps(
            {"error": f"对象 {object_id} 不存在或未确认"}, ensure_ascii=False
        )
    # vis 输出:右面板独立渲染(类型徽章+关键字段+payload折叠);失败回退裸 JSON
    try:
        vis = Vis.of("d-ecp-object")
        if vis:
            return vis.sync_display(
                id=vo.id,
                version=vo.version,
                type=vo.obj_type,
                status=vo.status,
                payload=vo.payload or {},
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp] get_semantic_object vis display failed: {e}")
    return json.dumps(
        {
            "id": vo.id,
            "version": vo.version,
            "type": vo.obj_type,
            "status": vo.status,
            "payload": vo.payload,
        },
        ensure_ascii=False,
    )


@tool(
    "execute_metric_query",
    description=(
        "THE gated ✅ path for business numbers. Execute a CONFIRMED metric "
        "with dimension filters/group-by/time range. All IDs must come from "
        "the confirmed catalog (search_semantics/get_semantic_object). "
        "Returns trust=verified with full lineage."
    ),
    args={
        "metric_id": {"type": "string", "description": "已确认指标 id"},
        "group_by": {
            "type": "array",
            "items": {"type": "string"},
            "description": "分组维度 id 列表",
            "required": False,
        },
        "filters": {
            "type": "array",
            "items": {"type": "object"},
            "description": "筛选：[{dim_id, values: [label], mode: include|exclude}]",
            "required": False,
        },
        "time": {
            "type": "object",
            "description": "时间：{range: 'YYYY-MM-DD~YYYY-MM-DD', column?}",
            "required": False,
        },
        "question": {
            "type": "string",
            "description": "原始用户问题（用于解析缓存回填）",
            "required": False,
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.DATABASE,
    risk_level=ToolRiskLevel.LOW,
)
async def execute_metric_query_tool(
    metric_id: str,
    group_by: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    time: Optional[Dict[str, Any]] = None,
    question: Optional[str] = None,
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    from ..service.executor import GateError, execute_metric_query
    from ..service.resolver import backfill

    ws = _ws(workspace_id)

    # 飞轮回忆路径(读):question 命中 resolution cache 且 metric 一致 →
    # 直接重放冻结参数(零漂移,标注 cache_hit);缓存过期(GateError)落回正常路径。
    if question:
        from ..service.resolver import lookup, replay

        cached = lookup(question, ws)
        if (
            cached
            and cached.get("tool") == "execute_metric_query"
            and (cached.get("params") or {}).get("metric_id") == metric_id
        ):
            try:
                result = await asyncio.to_thread(replay, cached)
                try:
                    vis = Vis.of("d-ecp-metric")
                    if vis:
                        return vis.sync_display(
                            trust=result.get("trust", "verified"),
                            metric_id=metric_id,
                            columns=result.get("columns"),
                            rows=result.get("rows"),
                            row_count=result.get("row_count"),
                            sql=result.get("sql"),
                            lineage=result.get("lineage"),
                            cache_hit=True,
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[ecp] recall vis display failed: {e}")
                return json.dumps(result, ensure_ascii=False, default=str)
            except GateError as e:
                logger.info(
                    f"[ecp] recall replay rejected ({e.code}: {e}), "
                    f"fall through to live execution"
                )

    try:
        result = await asyncio.to_thread(
            execute_metric_query,
            metric_id=metric_id,
            workspace_id=ws,
            group_by=group_by,
            filters=filters,
            time_range=time,
        )
    except GateError as e:
        # 门禁拒绝也走 vis(trust=none 错误态渲染),失败回退裸 JSON
        try:
            vis = Vis.of("d-ecp-metric")
            if vis:
                return vis.sync_display(
                    trust="none", metric_id=metric_id, error=str(e), code=e.code
                )
        except Exception:  # noqa: BLE001
            pass
        return json.dumps(
            {"error": str(e), "code": e.code, "trust": "none"}, ensure_ascii=False
        )
    # Recall flywheel: successful, uncorrected calls backfill the cache.
    if question:
        await asyncio.to_thread(
            backfill,
            question,
            ws,
            {
                "tool": "execute_metric_query",
                "params": {
                    "metric_id": metric_id,
                    "workspace_id": ws,
                    "group_by": group_by,
                    "filters": filters,
                    "time": time,
                },
            },
        )
    # vis 输出:trust 徽章 + 结果表 + 血缘页脚;失败回退裸 JSON
    try:
        vis = Vis.of("d-ecp-metric")
        if vis:
            return vis.sync_display(
                trust=result.get("trust", "verified"),
                metric_id=metric_id,
                columns=result.get("columns"),
                rows=result.get("rows"),
                row_count=result.get("row_count"),
                sql=result.get("sql"),
                lineage=result.get("lineage"),
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp] execute_metric_query vis display failed: {e}")
    return json.dumps(result, ensure_ascii=False, default=str)


@tool(
    "execute_raw_sql",
    description=(
        "Exploration path (⚠️ UNVERIFIED but encouraged). Use freely for "
        "open-ended analysis, concepts not yet in the semantic catalog, "
        "distributions/correlations/custom calibers. This is how the "
        "semantic layer learns: your reasoning feeds miss clustering. "
        "You MUST tell the user results are unverified caliber, and "
        "propose_semantic valuable reusable calibers you discovered. "
        "SQL 编写规范: 性能优先——禁止 SELECT *;单次查询返回不超过 2000 行"
        "(系统自动封顶 LIMIT 并截断超限结果,超过 30s 的查询会被终止);"
        "大表必须带时间过滤,单次查询时间跨度不超过 1 年,跨年分批查询再汇总;"
        "WHERE 优先使用索引列,聚合在库内完成(GROUP BY + LIMIT)。"
    ),
    args={
        "datasource_id": {"type": "integer", "description": "数据源 id"},
        "sql": {"type": "string", "description": "SELECT 语句（只读）"},
        "reasoning": {
            "type": "string",
            "description": (
                "探索目的 + 发现了什么目录没有的概念（飞轮原料，会被聚类学习）。"
                "示例: '分析各门店温度与销售额相关性；目录缺少温度-销售关联维度'"
            ),
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.DATABASE,
    risk_level=ToolRiskLevel.LOW,
)
async def execute_raw_sql(
    datasource_id: int,
    sql: str,
    reasoning: str,
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    ws = _ws(workspace_id)
    # 只读校验:先剥离注释(-- 行注释 / /* */ 块注释)再取首个关键字,
    # 否则带注释头的合法 SELECT 会被误判为写操作
    import re as _re

    cleaned = _re.sub(r"--.*$", "", sql, flags=_re.MULTILINE)
    cleaned = _re.sub(r"/\*.*?\*/", "", cleaned, flags=_re.DOTALL)
    stripped = cleaned.strip().lstrip("(").strip()
    first = stripped.split(None, 1)[0].upper() if stripped else ""
    if first not in ("SELECT", "WITH", "SHOW", "DESC", "DESCRIBE", "EXPLAIN"):
        return json.dumps(
            {"error": "只允许只读查询（SELECT/WITH/SHOW/DESC/EXPLAIN）", "trust": "none"},
            ensure_ascii=False,
        )
    # The miss is op-logged — lint clustering turns high-frequency misses
    # into new object/alias/dimension proposals (recall flywheel).
    await asyncio.to_thread(
        OpLogDao().append,
        "fallback", ws,
        {"datasource_id": datasource_id, "sql": sql[:2000], "reasoning": reasoning},
    )
    # 飞轮全自动:确保该工作空间的每日自动学习任务已注册(幂等,失败静默)
    try:
        from ..service.auto_learn import ensure_auto_learn_cron

        await ensure_auto_learn_cron(ws)
    except Exception:  # noqa: BLE001
        pass
    truncated = False
    row_limit = 0
    try:
        from gyra_serve.datasource.manages.connect_config_db import (
            ConnectConfigDao,
        )
        from gyra._private.config import Config

        config = await asyncio.to_thread(ConnectConfigDao().get_one, {"id": datasource_id})
        db_name = getattr(config, "db_name", None)
        if not db_name:
            return json.dumps(
                {"error": f"数据源 {datasource_id} 不存在", "trust": "none"},
                ensure_ascii=False,
            )
        cfg = Config()
        connector = cfg.local_db_manager.get_connector(db_name)
        # 执行安全层:LIMIT 注入/封顶 + 语句超时 + 流式截断(与 execute_sql 一致)
        from gyra_serve.sql_guard.safe_exec import (
            apply_select_limit,
            run_select_with_limits,
            timeout_error_message,
        )

        row_limit = cfg.SQL_MAX_ROWS
        dialect = getattr(connector, "dialect", getattr(connector, "db_type", ""))
        sql = apply_select_limit(sql, dialect, row_limit)
        try:
            raw, truncated = await asyncio.to_thread(
                run_select_with_limits,
                connector, sql,
                timeout=cfg.SQL_QUERY_TIMEOUT, max_rows=row_limit,
            )
        except TimeoutError:
            return json.dumps(
                {
                    "error": timeout_error_message(cfg.SQL_QUERY_TIMEOUT, row_limit),
                    "trust": "none",
                },
                ensure_ascii=False,
            )
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": str(e), "trust": "none"}, ensure_ascii=False)
    columns, rows = [], []
    total_rows = 0
    if raw:
        columns = list(raw[0])
        # 转换为 list(与 execute_sql 一致);仅物化展示上限内的行,避免超大结果
        # (如百万行)整体进内存,总数仍以 raw 为准,超出部分用 has_more 提示。
        total_rows = len(raw) - 1
        rows = [list(r) for r in raw[1 : 1 + _MAX_SQL_VIS_ROWS]]

    # 隐私脱敏:与 execute_sql 一致,结果统一走脱敏入口后再进入展示/导出,
    # 保证 ECP 兜底的 execute_raw_sql 也遵守数据库脱敏原则。
    # 系统目录表(all_tables 等)只含元数据、无业务数据,且其列名易与
    # 业务脱敏规则撞名(触发 masker 按列名的兜底匹配),故跳过脱敏;
    # 混合查询(系统表 + 业务表)仍保守脱敏。
    if rows:
        try:
            from gyra_serve.sql_guard.masking import (
                is_internal_catalog_sql,
                mask_run_result,
            )

            if not is_internal_catalog_sql(sql):
                columns, rows, _masked = await asyncio.to_thread(
                    mask_run_result, datasource_id, columns, rows
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[execute_raw_sql] masking skipped: {e}")

    # 缩减展示行数:保证 d-sql-query 围栏完整(不被外层截断成残缺组件)且数据量可控。
    db_type = getattr(connector, 'db_type', 'unknown')
    dialect = getattr(connector, 'dialect', getattr(connector, 'db_type', 'unknown'))
    display_rows = _cap_sql_display_rows(sql, db_name, db_type, dialect, columns, rows)
    page_size = len(display_rows)
    has_more = page_size < total_rows

    # Use d-sql-query VIS component for rendering (same as execute_sql)
    result_data = {
        "sql": sql,
        "db_name": db_name,
        "db_type": db_type,
        "dialect": dialect,
        "columns": columns,
        "rows": display_rows,
        "total_rows": total_rows,
        "page": 1,
        # 响应仅含本页数据,前端 Pagination 并不向后端拉取下一页,总页数固定为 1,
        # 用 has_more / display_truncated 提示还有更多行,避免出现可点但无数据的空页。
        "total_pages": 1,
        "page_size": page_size,
        "has_more": has_more,
        "display_truncated": has_more,
        "display_row_count": page_size,
        # ECP-specific fields
        "trust": "inferred",
        "warning": "⚠️ 未验证口径：此结果未经语义层确认",
    }

    if truncated:
        result_data["result_truncation_note"] = (
            f"结果已按安全上限截断为 {row_limit} 行(实际还有更多数据)。"
            "请加大时间过滤(单次时间跨度不超过 1 年)、库内聚合或分批查询。"
        )

    try:
        vis = Vis.of("d-sql-query")
        return vis.sync_display(**result_data)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[execute_raw_sql] Failed to render d-sql-query: {e}")
        # Fallback to JSON format
        return json.dumps(result_data, ensure_ascii=False, default=str)


@tool(
    "get_miss_report",
    description=(
        "Get clustered UNCOVERED questions (execute_raw_sql fallback log), "
        "grouped by normalized SQL pattern and ranked by frequency. Use this "
        "to learn what users repeatedly need but the catalog cannot answer — "
        "then propose_semantic for the high-frequency, genuinely-missing "
        "concepts (skip anything the catalog or inbox already covers)."
    ),
    args={
        "min_count": {
            "type": "integer",
            "description": "只返回出现次数 >= 此值的聚类，默认 2",
            "required": False,
        },
        "limit": {
            "type": "integer",
            "description": "最多返回聚类数，默认 20",
            "required": False,
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def get_miss_report(
    min_count: int = 2,
    limit: int = 20,
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    from ..service.service import cluster_fallbacks

    ws = _ws(workspace_id)
    entries = await asyncio.to_thread(
        OpLogDao().list, ws, op="fallback", page=1, page_size=500
    )
    learned = await asyncio.to_thread(MissLearnDao().learned_keys, ws)
    clusters = [
        c
        for c in cluster_fallbacks(entries)
        if c["count"] >= max(1, min_count)
        and (c.get("kind"), c.get("datasource_id"), c.get("pattern")) not in learned
    ][:limit]
    return json.dumps(
        {
            "workspace_id": ws,
            "total_fallbacks": len(entries),
            "learned_count": len(learned),
            "clusters": clusters,
            "hint": "对照已确认目录与收件箱,只为真正未覆盖且高频的概念用 "
            "propose_semantic 提案;已有概念不要重复提案。成功提案后请用 "
            "mark_miss_learned 标记这些聚类已学习,避免每天重复。",
        },
        ensure_ascii=False,
        default=str,
    )


@tool(
    "mark_miss_learned",
    description=(
        "Mark miss clusters as LEARNED (a proposal was generated for them). "
        "Call after propose_semantic succeeds for a cluster, passing back the "
        "same cluster objects from get_miss_report (kind/datasource_id/pattern). "
        "Once marked, the daily miss-learning cron excludes them so it never "
        "re-proposes already-covered concepts."
    ),
    args={
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "datasource_id": {"type": "integer"},
                    "pattern": {"type": "string"},
                    "example_sql": {"type": "string"},
                },
            },
            "description": "要标记为已学习的 miss 聚类对象(取自 get_miss_report 输出)",
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def mark_miss_learned(
    clusters: List[Dict[str, Any]],
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    ws = _ws(workspace_id)
    dao = MissLearnDao()
    marked, skipped = [], []
    for c in clusters or []:
        kind = c.get("kind")
        pattern = c.get("pattern")
        if not kind or not pattern:
            skipped.append(c)
            continue
        vo = await asyncio.to_thread(
            dao.mark_learned,
            ws,
            kind,
            pattern,
            datasource_id=c.get("datasource_id"),
            example=c.get("example_sql") or c.get("example"),
            trigger="agent",
        )
        marked.append(
            {"kind": vo.kind, "pattern": vo.pattern,
             "datasource_id": vo.datasource_id, "learned_at": vo.learned_at}
        )
    return json.dumps(
        {"workspace_id": ws, "marked": marked, "skipped": skipped},
        ensure_ascii=False,
        default=str,
    )


@tool(
    "query_canon",
    description=(
        "THE gated ✅ path for factual questions about managed documents "
        "(policies/definitions/rules). Execute CONFIRMED canon entries "
        "(claim/terminology/policy from search_semantics) and get answers "
        "with citations + full lineage. Each answer carries anchor_status "
        "(verified/drift/unquoted/unchecked) and top-level trust is honest: "
        "verified = all anchors replayed OK, partial = some drifted (doc may "
        "have changed), inferred = could not verify. Surface drift warnings "
        "and propose updating the anchor."
    ),
    args={
        "question": {"type": "string", "description": "原始事实型问题"},
        "object_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "已确认条目 id 列表(须来自 search_semantics/get_semantic_object)",
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def query_canon(
    question: str,
    object_ids: List[str],
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    from ..service.executor import GateError, execute_claim_query

    ws = _ws(workspace_id)
    try:
        result = await execute_claim_query(object_ids, ws)
    except GateError as e:
        return json.dumps(
            {"error": str(e), "code": e.code, "trust": "none"}, ensure_ascii=False
        )
    result["question"] = question
    return json.dumps(result, ensure_ascii=False, default=str)


@tool(
    "explore_docs",
    description=(
        "Document exploration path (⚠️ UNVERIFIED but encouraged). Free "
        "search over ECP-managed knowledge spaces for questions the canon "
        "cannot answer yet. Results are always trust=inferred; the miss is "
        "logged for canon learning. Tell the user the caliber is unverified, "
        "and propose_semantic valuable claims/terms you discover (with "
        "source_quote and anchor)."
    ),
    args={
        "question": {"type": "string", "description": "探索问题"},
        "space": {
            "type": "string",
            "description": "限定知识空间 slug;不填则检索本工作空间全部托管空间",
            "required": False,
        },
        "limit": {
            "type": "integer",
            "description": "返回条数,默认 5",
            "required": False,
        },
        "reasoning": {
            "type": "string",
            "description": "探索目的 + 发现了什么目录没有的概念(飞轮原料)",
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.LOW,
)
async def explore_docs(
    question: str,
    reasoning: str,
    space: Optional[str] = None,
    limit: int = 5,
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    from ..models.models import AssetRefDao

    ws = _ws(workspace_id)

    # 目标空间:指定 space,或本 ECP workspace 全部登记空间资产(active)
    if space:
        spaces = [space]
    else:
        try:
            space_assets = await asyncio.to_thread(AssetRefDao().list, ws, kind="space")
            spaces = [
                a.ref_id
                for a in space_assets or []
                if getattr(a, "status", "active") == "active"
            ]
        except Exception:  # noqa: BLE001
            spaces = []
    if not spaces:
        return json.dumps(
            {"error": f"工作空间 {ws} 无托管知识空间", "trust": "none"},
            ensure_ascii=False,
        )

    # op_log 记 miss(doc 形态,飞轮原料) + 确保自动学习任务存在
    await asyncio.to_thread(
        OpLogDao().append,
        "fallback",
        ws,
        {
            "kind": "doc",
            "question": question,
            "spaces": spaces,
            "reasoning": reasoning,
        },
    )
    try:
        from ..service.auto_learn import ensure_auto_learn_cron

        await ensure_auto_learn_cron(ws)
    except Exception:  # noqa: BLE001
        pass

    # 查询理解:扩展查询变体多路召回(主问句 hybrid + 扩展词 keyword),RRF 合并
    try:
        terms = await expand_query_terms(question, max_terms=8)
    except Exception:  # noqa: BLE001
        terms = []
    variants = [question]
    for t in terms:
        if t and t not in variants:
            variants.append(t)
        if len(variants) >= 3:
            break

    # 检索各空间 verbat(L0 原文块)
    hits: List[Dict[str, Any]] = []
    try:
        from gyra._private.config import Config

        system_app = Config().SYSTEM_APP
        from gyra_serve.knowledge.config import (
            SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
        )
        from gyra_serve.knowledge.service.service import (
            Service as KnowledgeService,
        )

        ks = system_app.get_component(KNOWLEDGE_SERVICE, KnowledgeService)

        def _rrf(rank: int) -> float:
            return 1.0 / (60 + rank)

        for sp in spaces:
            try:
                vault = await ks.get_vault(sp)
                merged: Dict[str, Dict[str, Any]] = {}
                for vi, variant in enumerate(variants):
                    mode = "hybrid" if vi == 0 else "keyword"
                    try:
                        found = await vault.verbat_search(
                            variant, limit=limit * 2, mode=mode
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.info(
                            f"[explore_docs] variant {variant!r} on space {sp} failed: {e}"
                        )
                        continue
                    for rank, h in enumerate(found):
                        entry = merged.setdefault(
                            h.verbat_id,
                            {
                                "space": sp,
                                "verbat_id": h.verbat_id,
                                "score": 0.0,
                                "snippet": getattr(h, "snippet", ""),
                                "source_file": getattr(h, "source_file", ""),
                            },
                        )
                        entry["score"] += _rrf(rank)
                hits.extend(merged.values())
            except Exception as e:  # noqa: BLE001
                logger.info(f"[explore_docs] search space {sp} failed: {e}")
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {"error": f"知识服务不可用: {e}", "trust": "none"}, ensure_ascii=False
        )

    for h in hits:
        h["score"] = round(h["score"], 4)
    hits = sorted(hits, key=lambda x: -x["score"])[:limit]
    return json.dumps(
        {
            "hits": hits,
            "spaces_searched": spaces,
            "query_variants": variants,
            "trust": "inferred",
            "warning": "⚠️ 未验证口径:结果来自临时检索,未经语义层确认",
        },
        ensure_ascii=False,
        default=str,
    )


def _sheet_headers(content: str) -> List[str]:
    """提取内容中的 Excel sheet 块标题(## Sheet: <name> (N rows))。"""
    names: List[str] = []
    for m in re.finditer(r"(?m)^## Sheet:\s*(.+?)\s*$", content):
        name = re.sub(r"\s*\(\d+\s*rows\)\s*$", "", m.group(1)).strip()
        if name:
            names.append(name)
    return names


def _extract_sheet_block(content: str, sheet: str) -> Optional[str]:
    """按 sheet 名取 Excel 分块:从 ## Sheet: <name> 表头到下一个 ## 标题或文末。"""
    marker = f"## Sheet: {sheet}"
    idx = content.find(marker)
    if idx == -1:
        return None
    nxt = content.find("\n## ", idx + len(marker))
    return content[idx:] if nxt == -1 else content[idx:nxt]


@tool(
    "get_verbat",
    description=(
        "Read the FULL content of a located knowledge document (verbat) by id. "
        "explore_docs only returns short snippets — use this after it to get "
        "the complete rows/data. For spreadsheet-derived docs read one sheet "
        "block at a time (names in the response's sheets); large docs page via "
        "offset/limit. Always trust=inferred."
    ),
    args={
        "verbat_id": {"type": "string", "description": "verbat id(来自 explore_docs 命中的 verbat_id)"},
        "space": {
            "type": "string",
            "description": "限定知识空间 slug;不填则在本工作空间全部托管空间内查找",
            "required": False,
        },
        "sheet": {
            "type": "string",
            "description": "只读取该 sheet 的分块内容(Excel/表格类文档,名字见响应里的 sheets)",
            "required": False,
        },
        "offset": {
            "type": "integer",
            "description": "内容字符偏移(配合 limit 分页读大文档),默认 0",
            "required": False,
        },
        "limit": {
            "type": "integer",
            "description": "单次最多返回字符数,默认 6000;超出置 truncated 并提示分页/sheet 精读",
            "required": False,
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def get_verbat(
    verbat_id: str,
    space: Optional[str] = None,
    sheet: Optional[str] = None,
    offset: int = 0,
    limit: int = 6000,
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    from ..models.models import AssetRefDao

    ws = _ws(workspace_id)
    # 目标空间解析:与 explore_docs 一致
    if space:
        spaces = [space]
    else:
        try:
            space_assets = await asyncio.to_thread(AssetRefDao().list, ws, kind="space")
            spaces = [
                a.ref_id
                for a in space_assets or []
                if getattr(a, "status", "active") == "active"
            ]
        except Exception:  # noqa: BLE001
            spaces = []
    if not spaces:
        return json.dumps(
            {"error": f"工作空间 {ws} 无托管知识空间", "trust": "none"},
            ensure_ascii=False,
        )

    try:
        from gyra._private.config import Config
        from gyra_serve.knowledge.config import (
            SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
        )
        from gyra_serve.knowledge.service.service import (
            Service as KnowledgeService,
        )

        ks = Config().SYSTEM_APP.get_component(KNOWLEDGE_SERVICE, KnowledgeService)
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {"error": f"知识服务不可用: {e}", "trust": "none"}, ensure_ascii=False
        )

    # 按 id 在目标空间内定位 verbat
    hit_space: Optional[str] = None
    v = None
    for sp in spaces:
        try:
            vault = await ks.get_vault(sp)
        except Exception as e:  # noqa: BLE001
            logger.info(f"[get_verbat] space {sp} failed: {e}")
            continue
        try:
            v = await vault.verbat_get(verbat_id)
        except Exception as e:  # noqa: BLE001
            logger.info(f"[get_verbat] verbat_get {verbat_id} on {sp} failed: {e}")
            continue
        if v is not None:
            hit_space = sp
            break
    if v is None:
        return json.dumps(
            {"error": f"未找到 verbat {verbat_id}", "trust": "none"},
            ensure_ascii=False,
        )

    full = v.content or ""
    total_len = len(full)
    sheets = _sheet_headers(full)

    # 内容源:sheet 分块(若指定)或全文;offset/limit 统一分页截断
    if sheet:
        block = _extract_sheet_block(full, sheet)
        if block is None:
            return json.dumps(
                {
                    "error": f"未找到 sheet {sheet!r}",
                    "available_sheets": sheets,
                    "trust": "none",
                },
                ensure_ascii=False,
            )
        source = block
        source_label = f"sheet {sheet!r} 分块"
    else:
        source = full
        source_label = "全文"
    source_len = len(source)
    start = max(0, int(offset or 0))
    max_chars = max(0, int(limit or 0))
    seg = source[start : start + max_chars] if max_chars else source[start:]
    truncated = start + len(seg) < source_len

    note = f"内容源: {source_label}({source_len} 字符);本次返回 {len(seg)} 字符"
    if truncated:
        note += ";已截断,可调 offset/limit 继续读,或按 sheets 精读分块"
    if sheet:
        note += f";可用 sheets: {sheets}"

    return json.dumps(
        {
            "space": hit_space,
            "verbat_id": v.id,
            "source_file": v.source_file,
            "extract_mode": getattr(v.extract_mode, "value", str(v.extract_mode)),
            "deprecated": v.deprecated,
            "filed_at": v.filed_at.isoformat() if v.filed_at else None,
            "sheets": sheets,
            "total_len": total_len,
            "returned_len": len(seg),
            "truncated": truncated,
            "content": seg,
            "note": note,
            "trust": "inferred",
            "warning": "⚠️ 未验证口径:此为知识库原始文档内容(L0),未经语义层确认",
        },
        ensure_ascii=False,
        default=str,
    )


@tool(
    "get_ecp_catalog",
    description=(
        "Get the FULL confirmed semantic catalog (compact text) plus the "
        "behavior rules for answering business-number questions. Call this "
        "first when entering an ECP-enabled conversation."
    ),
    args={
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.SAFE,
)
async def get_ecp_catalog(workspace_id: Optional[str] = None, **kwargs) -> str:
    from ..service.catalog import BEHAVIOR_GUIDE, build_catalog_text

    catalog = build_catalog_text(_ws(workspace_id))
    if not catalog:
        return "（语义目录为空，暂无已确认对象）\n\n" + BEHAVIOR_GUIDE
    return catalog + "\n\n" + BEHAVIOR_GUIDE


@tool(
    "propose_semantic",
    description=(
        "Propose a NEW semantic object (metric/entity/dimension/relation) "
        "when the catalog lacks a concept. Proposals always land in the "
        "confirmation inbox (status=proposed) and do NOT affect queries "
        "until a human confirms them."
    ),
    args={
        "object_id": {"type": "string", "description": "对象 id（ent./mtr./dim./rel. 前缀）"},
        "obj_type": {"type": "string", "description": "entity | metric | relation | dimension"},
        "payload": {
            "type": "object",
            "description": (
                "类型对应的 payload 定义，确认需满足契约："
                "entity 需 binding{table, datasource_id}；"
                "metric 需 entity(实体id) + expression(如 SUM(列))；"
                "dimension 需 column，values 每项需 codes 列表；"
                "relation 需 from + to"
            ),
        },
        "confidence": {"type": "number", "description": "置信度 0-1", "required": False},
        "miss_ref": {
            "type": "object",
            "description": (
                "MISS 学习溯源(从 get_miss_report 聚类学习时必传):"
                "{kind, pattern, datasource_id} 聚类键,提案详情可回链原始 miss 轨迹"
            ),
            "required": False,
        },
        "origin_sql": {
            "type": "array",
            "items": {"type": "string"},
            "description": "产生该提案的原始 SQL 快照(MISS 学习/手工 SQL 时传入,确认人可见)",
            "required": False,
        },
        "workspace_id": {
            "type": "string",
            "description": "工作空间 id，默认 default",
            "required": False,
        },
    },
    category=ToolCategory.SEARCH,
    risk_level=ToolRiskLevel.LOW,
)
async def propose_semantic(
    object_id: str,
    obj_type: str,
    payload: Dict[str, Any],
    confidence: Optional[float] = None,
    miss_ref: Optional[Dict[str, Any]] = None,
    origin_sql: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
    **kwargs,
) -> str:
    """提案工具薄壳:统一经 Service.propose 唯一写入口(契约门禁/兜底/边投影)。

    miss_ref 给定时 origin=miss_learn(并回链 miss 聚类),否则 origin=agent。
    """
    from ..config import (
        ORIGIN_AGENT,
        ORIGIN_MISS_LEARN,
        STATUS_PROPOSED,
        make_provenance,
    )
    from ..service.contracts import ContractViolation

    ws = _ws(workspace_id)
    origin = ORIGIN_MISS_LEARN if miss_ref else ORIGIN_AGENT
    try:
        vo = _service().propose(
            object_id=object_id,
            obj_type=obj_type,
            payload=payload,
            workspace_id=ws,
            confidence=confidence,
            created_by="llm",
            source="agent:propose_semantic",
            provenance=make_provenance(
                origin,
                actor="agent:propose_semantic",
                origin_sql=origin_sql,
                miss_ref=miss_ref,
            ),
            gate_level="executable",
        )
    except ContractViolation as e:
        return json.dumps(
            {
                "error": "提案不满足可执行契约,未入库;请补全后重提",
                "contract_gaps": e.problems,
            },
            ensure_ascii=False,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    if vo.status == STATUS_PROPOSED:
        note = "提案已进入确认收件箱，确认前不影响任何查询"
    else:
        # 去重命中:返回已有 confirmed VO,未产生新提案
        note = "已存在相同的已确认版本,未重复提案"
    return json.dumps(
        {
            "proposal_id": f"{vo.id}@v{vo.version}",
            "status": vo.status,
            "note": note,
        },
        ensure_ascii=False,
    )


def build_ecp_agent_tools(workspace_id: Optional[str] = None) -> List[FunctionTool]:
    """Build the ECP agent tools with ``workspace_id`` bound by closure.

    Mirrors ``build_scene_management_tools``: workspace_id is captured so the agent
    never passes it (cannot get it wrong -- catalog injected by ECPCapability and
    tool calls always target the same workspace). Tool metadata mirrors the
    ``@tool`` specs above minus workspace_id. Returns ``FunctionTool`` list for
    TOOLS-slot Contributions (consumed by react_master via ``_tool_to_function``).
    """
    ws = workspace_id or DEFAULT_WORKSPACE_ID

    async def _search(query: str) -> str:
        return await search_semantics(query=query, workspace_id=ws)

    async def _get_object(object_id: str) -> str:
        return await get_semantic_object(object_id=object_id, workspace_id=ws)

    async def _exec_metric(
        metric_id: str,
        group_by: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        time: Optional[Dict[str, Any]] = None,
        question: Optional[str] = None,
    ) -> str:
        return await execute_metric_query_tool(
            metric_id=metric_id,
            group_by=group_by,
            filters=filters,
            time=time,
            question=question,
            workspace_id=ws,
        )

    async def _exec_raw(datasource_id: int, sql: str, reasoning: str) -> str:
        return await execute_raw_sql(
            datasource_id=datasource_id,
            sql=sql,
            reasoning=reasoning,
            workspace_id=ws,
        )

    async def _catalog() -> str:
        return await get_ecp_catalog(workspace_id=ws)

    async def _miss_report(min_count: int = 2, limit: int = 20) -> str:
        return await get_miss_report(
            min_count=min_count, limit=limit, workspace_id=ws
        )

    async def _query_canon(question: str, object_ids: List[str]) -> str:
        return await query_canon(
            question=question, object_ids=object_ids, workspace_id=ws
        )

    async def _explore_docs(
        question: str, reasoning: str, space: Optional[str] = None, limit: int = 5
    ) -> str:
        return await explore_docs(
            question=question,
            reasoning=reasoning,
            space=space,
            limit=limit,
            workspace_id=ws,
        )

    async def _get_verbat(
        verbat_id: str,
        space: Optional[str] = None,
        sheet: Optional[str] = None,
        offset: int = 0,
        limit: int = 6000,
    ) -> str:
        return await get_verbat(
            verbat_id=verbat_id,
            space=space,
            sheet=sheet,
            offset=offset,
            limit=limit,
            workspace_id=ws,
        )

    async def _propose(
        object_id: str,
        obj_type: str,
        payload: Dict[str, Any],
        confidence: Optional[float] = None,
        miss_ref: Optional[Dict[str, Any]] = None,
        origin_sql: Optional[List[str]] = None,
    ) -> str:
        return await propose_semantic(
            object_id=object_id,
            obj_type=obj_type,
            payload=payload,
            confidence=confidence,
            miss_ref=miss_ref,
            origin_sql=origin_sql,
            workspace_id=ws,
        )

    return [
        FunctionTool(
            "search_semantics",
            _search,
            description="搜索已确认的语义对象(指标/实体/维度/关系)。回答业务数字问题前先在此查找。",
            args={"query": {"type": "string", "description": "关键词(名称/别名/id)"}},
        ),
        FunctionTool(
            "get_semantic_object",
            _get_object,
            description="获取语义对象完整定义:口径、绑定、维度值、粒度、版本。",
            args={"object_id": {"type": "string", "description": "对象 id,如 mtr.net_sales"}},
        ),
        FunctionTool(
            "execute_metric_query",
            _exec_metric,
            description=(
                "执行已确认指标的查询(唯一产出 ✅ 可信数字的路径)。"
                "所有 id 须来自已确认目录(search_semantics/get_semantic_object)。"
            ),
            args={
                "metric_id": {"type": "string", "description": "已确认指标 id"},
                "group_by": {
                    "type": "array",
                    "description": "分组维度 id 列表",
                    "required": False,
                },
                "filters": {
                    "type": "array",
                    "description": "筛选:[{dim_id, values:[label], mode:include|exclude}]",
                    "required": False,
                },
                "time": {
                    "type": "object",
                    "description": "时间:{range:'YYYY-MM-DD~YYYY-MM-DD', column?}",
                    "required": False,
                },
                "question": {
                    "type": "string",
                    "description": "原始用户问题(用于解析缓存回填)",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "execute_raw_sql",
            _exec_raw,
            description=(
                "探索路径(⚠️ 未验证但被鼓励)。开放性分析、目录未覆盖的概念、"
                "分布/相关性/自定义口径时主动使用——这是语义层的学习通道。"
                "须告知用户结果为未验证口径,有价值的可复用口径用 propose_semantic 沉淀。"
            ),
            args={
                "datasource_id": {"type": "integer", "description": "数据源 id"},
                "sql": {"type": "string", "description": "SELECT 语句(只读)"},
                "reasoning": {
                    "type": "string",
                    "description": (
                        "探索目的+发现了什么目录没有的概念(飞轮原料,会被聚类学习)。"
                        "示例:'分析门店温度与销售相关性;目录缺少温度-销售关联维度'"
                    ),
                },
            },
        ),
        FunctionTool(
            "get_ecp_catalog",
            _catalog,
            description="获取完整已确认语义目录(紧凑文本)+ 行为约定。进入 ECP 对话时先调用。",
            args={},
        ),
        FunctionTool(
            "get_miss_report",
            _miss_report,
            description=(
                "获取按频次聚类的未覆盖问题(execute_raw_sql 兜底记录)。"
                "用于学习用户反复需要但目录无法回答的概念,"
                "对高频且确实缺失的用 propose_semantic 提案。"
            ),
            args={
                "min_count": {
                    "type": "integer",
                    "description": "只返回出现次数>=此值的聚类,默认 2",
                    "required": False,
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回聚类数,默认 20",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "query_canon",
            _query_canon,
            description=(
                "文档事实查询的可信路径(✅)。用已确认条目(claim/terminology/policy)"
                "回答制度/定义/规则类问题,返回带引用的答案。"
                "条目 id 须来自 search_semantics/get_semantic_object。"
            ),
            args={
                "question": {"type": "string", "description": "原始事实型问题"},
                "object_ids": {
                    "type": "array",
                    "description": "已确认条目 id 列表",
                },
            },
        ),
        FunctionTool(
            "explore_docs",
            _explore_docs,
            description=(
                "文档探索路径(⚠️ 未验证但被鼓励)。目录未覆盖时在托管知识空间"
                "自由检索,结果须声明未验证口径;发现的可信口径用 "
                "propose_semantic 提案(带 source_quote 和 anchor)。"
            ),
            args={
                "question": {"type": "string", "description": "探索问题"},
                "reasoning": {
                    "type": "string",
                    "description": "探索目的+发现了什么目录没有的概念(飞轮原料)",
                },
                "space": {
                    "type": "string",
                    "description": "限定知识空间 slug,不填检索全部托管空间",
                    "required": False,
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数,默认 5",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "get_verbat",
            _get_verbat,
            description=(
                "按 verbat_id 读取已定位知识文档的完整内容(explore_docs 只给片段)。"
                "explore_docs 命中后用它拿完整行/数据;Excel 类文档支持 sheet 精读分块,"
                "大文档支持 offset/limit 分页。结果须声明未验证口径。"
            ),
            args={
                "verbat_id": {
                    "type": "string",
                    "description": "来自 explore_docs 命中的 verbat_id",
                },
                "space": {
                    "type": "string",
                    "description": "限定知识空间 slug,不填则在全部托管空间查找",
                    "required": False,
                },
                "sheet": {
                    "type": "string",
                    "description": "只读取该 sheet 分块(Excel/表格类文档)",
                    "required": False,
                },
                "offset": {
                    "type": "integer",
                    "description": "内容字符偏移,默认 0",
                    "required": False,
                },
                "limit": {
                    "type": "integer",
                    "description": "单次最多返回字符数,默认 6000",
                    "required": False,
                },
            },
        ),
        FunctionTool(
            "propose_semantic",
            _propose,
            description="提案新语义对象(指标/实体/维度/关系)。只进确认收件箱,确认前不影响查询。",
            args={
                "object_id": {
                    "type": "string",
                    "description": "对象 id(ent./mtr./dim./rel. 前缀)",
                },
                "obj_type": {
                    "type": "string",
                    "description": "entity | metric | relation | dimension",
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "类型对应的 payload 定义,确认需满足契约:"
                        "entity 需 binding{table, datasource_id};"
                        "metric 需 entity(实体id) + expression(如 SUM(列));"
                        "dimension 需 column,values 每项需 codes 列表;"
                        "relation 需 from + to"
                    ),
                },
                "confidence": {
                    "type": "number",
                    "description": "置信度 0-1",
                    "required": False,
                },
                "miss_ref": {
                    "type": "object",
                    "description": (
                        "MISS 学习溯源(从 get_miss_report 聚类学习时必传):"
                        "{kind, pattern, datasource_id} 聚类键"
                    ),
                    "required": False,
                },
                "origin_sql": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "产生该提案的原始 SQL 快照(MISS 学习/手工 SQL 时传入)",
                    "required": False,
                },
            },
        ),
    ]
