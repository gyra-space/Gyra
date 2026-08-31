"""Binding executors: polymorphic execution over asset bindings (ECP v1.2).

`entity.binding.kind` selects a BindingExecutor implementation. The gated
`execute_metric_query` tool is the ONLY path that produces ✅ verified
numbers; it delegates physical execution to the executor registered for the
binding kind. New binding sources (API in P3, Excel later) plug in here
without touching the protocol.

The DB executor assembles SQL deterministically with sqlglot from the frozen
metric expression — the LLM picks catalog IDs, code assembles the SQL.
"""

import asyncio
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import sqlglot
from sqlglot import exp

from .contracts import validate_payload

logger = logging.getLogger(__name__)

# 时间类型列的确定性兜底(DB 列类型 → role=time),覆盖 LLM 漏标
_TIME_TYPE_RE = re.compile(r"\b(date|datetime|timestamp|time|year)\b", re.IGNORECASE)


def _is_time_type(col_type: Any) -> bool:
    """判断 DB 列类型是否为时间类(date/datetime/timestamp/time/year)。"""
    if not isinstance(col_type, str):
        return False
    return bool(_TIME_TYPE_RE.search(col_type))


def _normalize_anchor(text: Optional[str]) -> str:
    """锚点归一化: NFKC + 去全部空白 + casefold。

    冻结摘录与当前原文常因排版差异(全半角/不可见空白/大小写)造成
    "假漂移";归一化后再做子串比较,只把真实的内容改动判为 drift。
    """
    if not text:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text))).casefold()


def _mask_dict_rows(
    datasource_id: Optional[int],
    columns,
    rows: List[Dict[str, Any]],
    *,
    table_name: Optional[str] = None,
    sql: Optional[str] = None,
):
    """对 dict 行结果统一走脱敏入口(-- 隐私脱敏,与 execute_sql 一致)。

    rows 为 ``[dict]`` 结构;脱敏按列索引作用,需先按 ``columns`` 顺序重排成
    list,脱敏完成后再按不变的 ``columns`` 重建 dict,保证键与顺序不丢失。

    sql/table_name 命中系统目录白名单时跳过脱敏,避免列名兜底误伤。

    Returns:
        (masked_rows, masked_column_names): 脱敏后的 dict 行 + 实际被脱敏列名。
        任何失败返回原始 rows 与空列表(脱敏永不破坏查询路径)。
    """
    if not rows or not columns:
        return rows, []
    try:
        from gyra_serve.sql_guard.masking import (
            is_internal_catalog_sql,
            is_internal_catalog_table,
            mask_run_result,
        )

        # 系统目录表(ALL_TABLES/PG_CATALOG 等)无业务数据,跳过脱敏。
        if sql:
            if is_internal_catalog_sql(sql):
                return rows, []
        elif table_name and is_internal_catalog_table(table_name):
            return rows, []

        list_rows = [[r.get(c) for c in columns] for r in rows]
        _, list_rows, masked = mask_run_result(
            datasource_id, columns, list_rows, table_name=table_name
        )
        return [dict(zip(columns, mr)) for mr in list_rows], masked
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[mask_dict_rows] masking skipped: {e}")
        return rows, []


class GateError(Exception):
    """Deterministic gate rejection (agent-visible, never bypassable)."""

    def __init__(self, message: str, code: str = "GATE_REJECTED"):
        super().__init__(message)
        self.code = code


class BindingExecutor:
    """Interface for executing a confirmed metric against its binding."""

    binding_kind: str = ""

    def validate_binding(self, binding: Dict[str, Any]) -> List[str]:
        """Return a list of binding problems; empty means valid."""
        raise NotImplementedError

    def execute_metric_query(
        self,
        daos,
        metric_id: str,
        workspace_id: str,
        group_by: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        time_range: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class DbBindingExecutor(BindingExecutor):
    """Executes against RDBMS bindings (read-only, sqlglot assembly).

    Gate steps (all deterministic, agent-invisible):
      ① all IDs exist and are confirmed
      ② filter labels ∈ dimension.values → mapped to codes
      ③ group_by dims belong to the metric's entity (grain check)
      ④ cross-entity requires a confirmed relation (write rule 5) — otherwise
        reject AND auto-create a relation proposal
      ⑤ SQL assembled from frozen expression + default/extra filters
      ⑥ assembled SQL must contain every frozen filter string
      ⑦ read-only execution via connector
      ⑧ lineage recorded by the caller
    """

    binding_kind = "db"

    def __init__(self, connector_factory: Optional[Callable[[int], Any]] = None):
        # Injectable for tests; default resolves via CFG.local_db_manager.
        self._connector_factory = connector_factory or self._default_connector

    # ------------------------------------------------------------------ setup
    @staticmethod
    def _default_connector(datasource_id: int):
        from gyra._private.config import Config
        from gyra_serve.datasource.manages.connect_config_db import (
            ConnectConfigDao,
        )

        config = ConnectConfigDao().get_one({"id": datasource_id})
        db_name = getattr(config, "db_name", None)
        if not db_name:
            raise GateError(f"数据源 {datasource_id} 不存在", code="BINDING_INVALID")
        return Config().local_db_manager.get_connector(db_name)

    # ------------------------------------------------------------------- gate
    def execute_metric_query(
        self,
        daos,
        metric_id: str,
        workspace_id: str,
        group_by: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        time_range: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        group_by = group_by or []
        filters = filters or []

        # ① metric + entity must exist and be confirmed
        metric = daos.objects.get_confirmed(metric_id, workspace_id)
        if not metric or metric.obj_type != "metric":
            raise GateError(f"指标 {metric_id} 不存在或未确认", code="NOT_CONFIRMED")
        mp = metric.payload or {}
        # payload 形状校验走 contracts 单一事实来源(与 confirm 晋升门禁同规则)
        problems = validate_payload("metric", mp, level="executable")
        if problems:
            raise GateError(
                f"指标 {metric_id}: {'; '.join(problems)}", code="PAYLOAD_INVALID"
            )
        entity_id = mp.get("entity")
        entity = daos.objects.get_confirmed(entity_id, workspace_id)
        if not entity:
            raise GateError(f"实体 {entity_id} 不存在或未确认", code="NOT_CONFIRMED")
        ep = entity.payload or {}
        binding = ep.get("binding") or {}
        problems = validate_payload("entity", ep, level="executable")
        if problems:
            raise GateError(
                f"实体 {entity_id}: {'; '.join(problems)}",
                code="BINDING_INVALID",
            )

        # ②③ dimensions: resolve filters + group_by
        dim_conditions: List[str] = []
        group_cols: List[str] = []
        involved_entities = {entity_id}
        for dim_id in group_by:
            dim = self._confirmed_dim(daos, dim_id, workspace_id)
            self._check_grain(dim, mp)
            involved_entities.add(dim.payload.get("entity") or entity_id)
            group_cols.append(dim.payload["column"])
        for f in filters:
            dim = self._confirmed_dim(daos, f.get("dim_id") or f.get("dim"), workspace_id)
            involved_entities.add(dim.payload.get("entity") or entity_id)
            dim_conditions.append(self._dim_condition(dim, f))

        # ④ cross-entity requires a confirmed relation (rule 5)
        involved_entities.discard(entity_id)
        for other in involved_entities:
            self._require_relation(daos, entity_id, other, workspace_id)

        # ⑤ assemble SQL deterministically
        sql = self._assemble_sql(mp, ep, binding, group_cols, dim_conditions, time_range)

        # ⑥ frozen filters must be present in the SQL (defense in depth:
        # assembly is deterministic so this should never fail). Compared in
        # sqlglot-normalized form (e.g. '!=' normalizes to '<>').
        sql_norm = sqlglot.parse_one(sql).sql()
        for frag in (ep.get("default_filters") or []) + (mp.get("extra_filters") or []):
            if frag and sqlglot.parse_one(frag).sql() not in sql_norm:
                raise GateError(
                    f"SQL 组装缺少冻结过滤条件: {frag}", code="ASSEMBLY_INVALID"
                )

        # ⑦ read-only execution (DB 语句级超时 + 行数熔断 + TTL 结果缓存)
        from gyra_serve.app_card.sql_runtime import (
            get_query_settings,
            get_result_cache,
            is_timeout_error,
        )

        settings = get_query_settings()
        exec_timeout = (
            float(timeout)
            if timeout is not None
            else (
                float(settings.query_timeout_seconds)
                if settings.query_timeout_seconds > 0
                else None
            )
        )
        cap = max_rows if max_rows is not None else settings.max_result_rows
        datasource_id = binding.get("datasource_id")
        lineage = {
            "metric_id": metric_id,
            "metric_version": metric.version,
            "entity_id": entity_id,
            "entity_version": entity.version,
            "table": binding.get("table"),
            "datasource_id": datasource_id,
            "executed_at": datetime.now().isoformat(),
        }
        cache = get_result_cache()
        cache_key = ("ecp_metric", datasource_id, sql, cap)
        cached = cache.get(cache_key) if cache is not None else None
        if cached is not None:
            columns, rows, truncated = cached
            result = {
                "rows": rows,
                "columns": columns,
                "row_count": len(rows),
                "trust": "verified",
                "sql": sql,
                "cached": True,
                "lineage": lineage,
            }
            if truncated:
                result["truncated"] = True
            return result
        connector = self._connector_factory(datasource_id)
        truncated = False
        try:
            try:
                fields, data_rows = connector.query_ex(
                    sql,
                    fetch="all",
                    timeout=exec_timeout,
                    max_rows=cap + 1,
                )
                raw = [list(fields), *(data_rows or [])]
            except TypeError:
                # 旧连接器 query_ex 签名不含 fetch/max_rows, 回退原执行路径。
                # 回退路径同样要做行数熔断:流式 fetchmany(cap+1), 不 fetchall 全量拉内存。
                from sqlalchemy import text as _sql_text

                with connector.session_scope(commit=False) as _session:
                    _result = _session.execute(_sql_text(sql))
                    _columns_fb = list(_result.keys())
                    _rows_fb: list = []
                    while len(_rows_fb) <= cap:
                        _chunk = _result.fetchmany(min(1024, cap + 1 - len(_rows_fb)))
                        if not _chunk:
                            break
                        _rows_fb.extend(_chunk)
                raw = [_columns_fb, *_rows_fb]
        except Exception as e:  # noqa: BLE001
            if is_timeout_error(e):
                shown = f"{exec_timeout:g}" if exec_timeout is not None else "默认"
                raise GateError(
                    f"指标查询超时(超过 {shown} 秒), 已被数据库中止, "
                    "请缩小时间范围或先做聚合再试",
                    code="QUERY_TIMEOUT",
                )
            raise
        columns, rows = [], []
        if raw:
            columns = list(raw[0])
            rows = [dict(zip(columns, r)) for r in raw[1:]]
            # 隐私脱敏:DB 结果统一走脱敏入口,与 execute_sql 保持一致。
            if rows:
                rows, _ = _mask_dict_rows(
                    datasource_id, columns, rows,
                    table_name=binding.get("table"), sql=sql,
                )
        if len(rows) > cap:
            rows = rows[:cap]
            truncated = True

        result = {
            "rows": rows,
            "columns": columns,
            "row_count": len(rows),
            "trust": "verified",
            "sql": sql,
            "lineage": lineage,
        }
        if truncated:
            result["truncated"] = True
        if cache is not None:
            cache.put(cache_key, (columns, rows, truncated))
        return result

    # ------------------------------------------------------------------ steps
    @staticmethod
    def _confirmed_dim(daos, dim_id: Optional[str], workspace_id: str):
        if not dim_id:
            raise GateError("维度 id 缺失", code="DIM_INVALID")
        dim = daos.objects.get_confirmed(dim_id, workspace_id)
        if not dim or dim.obj_type != "dimension":
            raise GateError(f"维度 {dim_id} 不存在或未确认", code="NOT_CONFIRMED")
        problems = validate_payload("dimension", dim.payload or {}, level="executable")
        if problems:
            raise GateError(
                f"维度 {dim_id}: {'; '.join(problems)}", code="PAYLOAD_INVALID"
            )
        return dim

    @staticmethod
    def _check_grain(dim, metric_payload: Dict[str, Any]) -> None:
        grain = metric_payload.get("grain") or []
        if not grain:
            return
        col = dim.payload["column"]
        name = (dim.name or "").lower()
        if col not in grain and name not in [g.lower() for g in grain]:
            raise GateError(
                f"维度 {dim.id}（列 {col}）不在指标粒度 {grain} 内",
                code="GRAIN_INVALID",
            )

    @staticmethod
    def _dim_condition(dim, f: Dict[str, Any]) -> str:
        """Map filter labels → codes via the dimension value dictionary."""
        labels = f.get("values") or f.get("values_label") or []
        mode = (f.get("mode") or "include").lower()
        column = dim.payload["column"]
        codes: List[str] = []
        available = []
        for v in dim.payload.get("values") or []:
            available.append(v.get("label"))
            for lbl in labels:
                if lbl == v.get("label") or lbl in (v.get("aliases") or []):
                    codes.extend(str(c) for c in (v.get("codes") or []))
        missing = [
            lbl
            for lbl in labels
            if not any(
                lbl == v.get("label") or lbl in (v.get("aliases") or [])
                for v in dim.payload.get("values") or []
            )
        ]
        if missing:
            raise GateError(
                f"维度值 {missing} 不在 {dim.id} 的值字典 {available} 中",
                code="DIM_VALUE_UNKNOWN",
            )
        if not codes:
            raise GateError(f"维度 {dim.id} 筛选值为空", code="DIM_INVALID")
        quoted = ", ".join(f"'{c}'" for c in sorted(set(codes)))
        op = "NOT IN" if mode == "exclude" else "IN"
        return f"{column} {op} ({quoted})"

    @staticmethod
    def _require_relation(daos, from_id: str, to_id: str, workspace_id: str) -> None:
        """Write rule 5: no confirmed relation → reject + auto-propose one."""
        for rel_id in (f"rel.{from_id.split('.', 1)[-1]}__{to_id.split('.', 1)[-1]}",):
            rel = daos.objects.get_confirmed(rel_id, workspace_id)
            if rel and rel.obj_type == "relation":
                return
        # Fallback: scan confirmed relations by payload endpoints.
        for entry in daos.objects.list_catalog(workspace_id):
            if entry.obj_type != "relation":
                continue
            rel = daos.objects.get_confirmed(entry.id, workspace_id)
            if not rel:
                continue
            rp = rel.payload or {}
            pair = {rp.get("from"), rp.get("to")}
            if pair == {from_id, to_id}:
                return
        # Auto-propose the missing relation, then reject.
        proposal_id = f"rel.{from_id.split('.', 1)[-1]}__{to_id.split('.', 1)[-1]}"
        try:
            from ..config import ORIGIN_RULE5_GATE, make_provenance

            daos.objects.create_proposal(
                proposal_id,
                "relation",
                {"from": from_id, "to": to_id, "path": None, "cardinality": None},
                workspace_id=workspace_id,
                created_by="llm",
                source="gate:rule5",
                provenance=make_provenance(
                    ORIGIN_RULE5_GATE,
                    actor="executor:rule5",
                    note=f"跨实体查询缺已确认关系({from_id} → {to_id}),执行门禁自动提案",
                ),
            )
        except Exception:  # noqa: BLE001
            pass
        raise GateError(
            f"跨实体查询需要已确认的 relation（{from_id} → {to_id}）。"
            f"已自动生成 relation 提案 {proposal_id}，请确认后重试。",
            code="RELATION_MISSING",
        )

    # --------------------------------------------------------------- assembly
    def _assemble_sql(
        self,
        mp: Dict[str, Any],
        ep: Dict[str, Any],
        binding: Dict[str, Any],
        group_cols: List[str],
        dim_conditions: List[str],
        time_range: Optional[Dict[str, Any]],
    ) -> str:
        expression = mp.get("expression")
        if not expression:
            raise GateError("指标缺少冻结 expression", code="PAYLOAD_INVALID")
        table = binding["table"]

        select_exprs = [sqlglot.parse_one(c) for c in group_cols]
        select_exprs.append(sqlglot.parse_one(f"{expression} AS value"))

        query = sqlglot.select(*select_exprs).from_(table)

        conditions: List[str] = []
        conditions.extend(ep.get("default_filters") or [])
        conditions.extend(mp.get("extra_filters") or [])
        conditions.extend(dim_conditions)
        time_cond = self._time_condition(ep, time_range)
        if time_cond:
            conditions.append(time_cond)
        for cond in conditions:
            query = query.where(cond)

        if group_cols:
            query = query.group_by(*group_cols)

        return query.sql()

    @staticmethod
    def _time_condition(
        ep: Dict[str, Any], time_range: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        if not time_range:
            return None
        rng = time_range.get("range")
        if not rng or "~" not in str(rng):
            return None
        column = time_range.get("column")
        if not column:
            for name, meta in (ep.get("fields") or {}).items():
                if (meta or {}).get("role") == "time":
                    column = name
                    break
        if not column:
            # 兜底:LLM 提案漏标 role=time 时,按 DB 列类型确定性找时间列
            column = _resolve_time_column_by_type(ep)
        if not column:
            raise GateError(
                "需要时间筛选但实体未定义 role=time 的字段", code="TIME_COLUMN_MISSING"
            )
        start, end = [s.strip() for s in str(rng).split("~", 1)]
        return f"{column} BETWEEN '{start}' AND '{end}'"


def _resolve_time_column_by_type(ep: Dict[str, Any]) -> Optional[str]:
    """按 DB 列类型(date/datetime/timestamp/time/year)从 table spec 找时间列。

    兜底 LLM 提案漏标 role=time 的实体:时间筛选时若无显式 column 也无
    role=time 字段,用表结构的确定性类型判断,避免 TIME_COLUMN_MISSING。
    best-effort:任何失败返回 None(由调用方决定是否降级/报错)。
    """
    try:
        from gyra_serve.datasource.manages.table_spec_db import TableSpecDao

        binding = ep.get("binding") or {}
        table = binding.get("table")
        ds_id = binding.get("datasource_id")
        if not table or not ds_id:
            return None
        specs = TableSpecDao().get_all_by_datasource(ds_id) or []
        for s in specs:
            t = getattr(s, "table_name", None)
            if isinstance(s, dict):
                t = s.get("table_name")
            if t != table:
                continue
            cols = None
            if isinstance(s, dict):
                cols = s.get("columns")
            else:
                raw = getattr(s, "columns_json", None)
                if isinstance(raw, str):
                    try:
                        import json

                        cols = json.loads(raw)
                    except (ValueError, TypeError):  # noqa: S110
                        cols = None
                else:
                    cols = raw
            for c in cols or []:
                if not isinstance(c, dict):
                    continue
                cname, ctype = c.get("name"), c.get("type")
                if cname and _is_time_type(ctype):
                    return cname
            return None
    except Exception:  # noqa: BLE001 基础设施不可用 → 交给调用方报错/降级
        return None
    return None


class _ExecutorDaos:
    """Thin DAO bundle passed to executors (keeps executor decoupled from
    the Service component so tools and tests can construct it directly)."""

    def __init__(self):
        from ..models.models import SemanticObjectDao

        self.objects = SemanticObjectDao()


class DocBindingExecutor(BindingExecutor):
    """Executes against document bindings — evidence playback (P0 文档扩展)。

    与 DB 侧"SQL 确定性组装"对称,文档侧是**证据确定性回放**:
      ① claim/terminology/policy 必须 confirmed(同 metric 门禁)
      ② binding 契约校验(contracts 单一事实来源)
      ③ anchor 回放:经 doc_fetcher 取原文,归一化后校验冻结 source_quote
         为子串;每条独立标注 anchor_status(verified/drift/unquoted/
         unchecked),单条漂移不阻断整批,仅记入 warnings(文档改版信号);
         基础设施不可用 → best-effort 标 unchecked
      ④ 返回带引用的答案,trust 按核查结果取 verified(全部核实)/
         partial(有漂移)/inferred(未核实) + 血缘
    """

    binding_kind = "doc"
    _DOC_TYPES = ("claim", "terminology", "policy")

    def __init__(self, doc_fetcher: Optional[Callable] = None, **_kwargs):
        # doc_fetcher(space, doc_id) -> Optional[str](原文文本);可注入供测试
        self._doc_fetcher = doc_fetcher or self._default_doc_fetcher

    @staticmethod
    async def _default_doc_fetcher(space: str, doc_id: str) -> Optional[str]:
        """经 KnowledgeService 取 verbat 原文。找不到/服务不可用返回 None。"""
        try:
            from gyra._private.config import Config

            system_app = Config().SYSTEM_APP
            if system_app is None:
                return None
            from gyra_serve.knowledge.config import (
                SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
            )
            from gyra_serve.knowledge.service.service import (
                Service as KnowledgeService,
            )

            ks = system_app.get_component(KNOWLEDGE_SERVICE, KnowledgeService)
            vault = await ks.get_vault(space)
            v = await vault.verbat_get(doc_id)
            if v is None:
                return None
            return getattr(v, "content", None) or getattr(v, "text", None)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[doc-executor] fetch {space}:{doc_id} failed: {e}")
            return None

    async def execute_claim_query(
        self, daos, object_ids: List[str], workspace_id: str
    ) -> Dict[str, Any]:
        answers: List[Dict[str, Any]] = []
        warnings: List[str] = []
        for oid in object_ids:
            obj = await asyncio.to_thread(
                daos.objects.get_confirmed, oid, workspace_id
            )
            if not obj or obj.obj_type not in self._DOC_TYPES:
                raise GateError(f"条目 {oid} 不存在或未确认", code="NOT_CONFIRMED")
            p = obj.payload or {}
            problems = validate_payload(obj.obj_type, p, level="executable")
            if problems:
                raise GateError(
                    f"条目 {oid}: {'; '.join(problems)}", code="PAYLOAD_INVALID"
                )
            binding = p.get("binding") or {}
            quote = p.get("source_quote")
            n_quote = _normalize_anchor(quote)
            original = await self._doc_fetcher(
                binding.get("space", ""), binding.get("doc_id", "")
            )
            if not n_quote:
                anchor_status = "unquoted"
            elif original is None:
                # 基础设施不可用 → best-effort,不阻断,标 unchecked
                anchor_status = "unchecked"
            elif n_quote in _normalize_anchor(original):
                anchor_status = "verified"
            else:
                # 单条漂移不炸批:条目保留在 answers 中,warnings 记改版信号
                anchor_status = "drift"
                warnings.append(
                    f"条目 {oid} 锚点漂移:原文中未找到冻结摘录"
                    f"(文档可能已改版),请重新确认或更新 anchor"
                )
            answers.append(
                {
                    "id": oid,
                    "type": obj.obj_type,
                    "version": obj.version,
                    "text": p.get("text") or p.get("definition") or p.get("rule"),
                    "condition": p.get("condition"),
                    "quote": quote,
                    "anchor_status": anchor_status,
                    "citation": {
                        "space": binding.get("space"),
                        "doc_id": binding.get("doc_id"),
                        "anchor": binding.get("anchor"),
                        "anchor_status": anchor_status,
                        "anchor_verified": anchor_status == "verified",
                    },
                }
            )
        # 诚实 trust:全部核实才算 verified;有漂移降为 partial;
        # 全部未核实(基础设施不可用/未冻结摘录)降为 inferred。
        statuses = {a["anchor_status"] for a in answers}
        if not statuses or statuses == {"verified"}:
            trust = "verified"
        elif "drift" in statuses:
            trust = "partial"
        else:
            trust = "inferred"
        return {
            "answers": answers,
            "trust": trust,
            "warnings": warnings,
            "lineage": {
                "workspace_id": workspace_id,
                "executed_at": datetime.now().isoformat(),
            },
        }


# Executor registry keyed by binding kind.
EXECUTORS: Dict[str, type] = {
    DbBindingExecutor.binding_kind: DbBindingExecutor,
    DocBindingExecutor.binding_kind: DocBindingExecutor,
}


def get_executor(binding_kind: str, **kwargs) -> Optional[BindingExecutor]:
    cls = EXECUTORS.get(binding_kind)
    return cls(**kwargs) if cls else None


async def execute_claim_query(
    object_ids: List[str],
    workspace_id: str,
    doc_fetcher: Optional[Callable] = None,
) -> Dict[str, Any]:
    """The gated ✅ path for document canon (P0 文档扩展)。

    与 execute_metric_query 对称:confirmed 条目 → 契约校验 → anchor 回放
    → 带引用答案(trust 按核查结果 verified/partial/inferred + 血缘)。
    """
    daos = _ExecutorDaos()
    executor = DocBindingExecutor(doc_fetcher=doc_fetcher)
    return await executor.execute_claim_query(daos, object_ids, workspace_id)


def execute_metric_query(
    metric_id: str,
    workspace_id: str,
    group_by: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    time_range: Optional[Dict[str, Any]] = None,
    connector_factory: Optional[Callable[[int], Any]] = None,
) -> Dict[str, Any]:
    """The gated ✅ path. Resolves the metric's binding kind and delegates."""
    daos = _ExecutorDaos()
    metric = daos.objects.get_confirmed(metric_id, workspace_id)
    if not metric:
        raise GateError(f"指标 {metric_id} 不存在或未确认", code="NOT_CONFIRMED")
    entity = daos.objects.get_confirmed(
        (metric.payload or {}).get("entity") or "", workspace_id
    )
    kind = ((entity.payload or {}).get("binding") or {}).get("kind", "db") if entity else "db"
    executor = get_executor(kind, connector_factory=connector_factory)
    if not executor:
        raise GateError(f"不支持的绑定类型 {kind}", code="BINDING_INVALID")
    from gyra_serve.app_card.sql_runtime import get_query_settings

    settings = get_query_settings()
    exec_timeout = (
        float(settings.query_timeout_seconds)
        if settings.query_timeout_seconds > 0
        else None
    )
    return executor.execute_metric_query(
        daos, metric_id, workspace_id,
        group_by=group_by, filters=filters, time_range=time_range,
        timeout=exec_timeout, max_rows=settings.max_result_rows,
    )


# =============================================================================
# Preview (调试验证) mode — 只读 dry-run of PROPOSED computation rules.
#
# 与 gated 路径(execute_metric_query)共用同一确定性组装/执行,但**不**走
# confirmed-only 门禁:按提案自身 payload 解析其引用(entity/dimension/relation
# 的最新版本,不论状态),只读执行,返回 trust=preview(永不 verified)。
# 纯读、不落库、不改状态 —— 确认人可在确认前先核对真实数据。
# =============================================================================


def _preview_fail(message: str, sql: Optional[str] = None,
                  warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "trust": "none", "ok": False, "error": message,
        "warnings": warnings or [], "columns": [], "rows": [],
        "row_count": 0, "sql": sql,
    }


def _preview_connector(datasource_id: int):
    from gyra._private.config import Config
    from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao

    config = ConnectConfigDao().get_one({"id": datasource_id})
    db_name = getattr(config, "db_name", None)
    if not db_name:
        raise GateError(f"数据源 {datasource_id} 不存在", code="BINDING_INVALID")
    return Config().local_db_manager.get_connector(db_name)


def _preview_run(sql: str, datasource_id: int, obj: Any,
                 warnings: Optional[List[str]] = None,
                 limit: Optional[int] = None) -> Dict[str, Any]:
    """只读执行并统一返回 preview 结果(trust=preview)。

    limit 通过 connector.limit_sql 按目标数据库方言生成(Oracle 12c+ 用
    FETCH FIRST、11g 用 ROWNUM 子查询),避免硬编码 LIMIT 语法不兼容。
    """
    result: Dict[str, Any] = {
        "trust": "preview", "ok": True, "warnings": warnings or [],
        "error": None, "sql": sql,
        "lineage": {
            "obj_id": getattr(obj, "id", None),
            "version": getattr(obj, "version", None),
            "obj_type": getattr(obj, "obj_type", None),
            "mode": "preview",
            "executed_at": datetime.now().isoformat(),
        },
    }
    try:
        connector = _preview_connector(datasource_id)
    except Exception as e:  # noqa: BLE001
        result.update(trust="none", ok=False, error=f"数据源不可用: {e}")
        return result
    if limit and limit > 0:
        try:
            sql = connector.limit_sql(sql, limit)
        except Exception as e:  # noqa: BLE001
            result.update(trust="none", ok=False, error=f"LIMIT 生成失败: {e}")
            return result
    from gyra_serve.app_card.sql_runtime import (
        get_query_settings,
        is_timeout_error,
    )

    settings = get_query_settings()
    exec_timeout = (
        float(settings.query_timeout_seconds)
        if settings.query_timeout_seconds > 0
        else None
    )
    try:
        try:
            fields, data_rows = connector.query_ex(
                sql, fetch="all", timeout=exec_timeout,
            )
            raw = [list(fields), *(data_rows or [])]
        except TypeError:
            # 旧连接器 query_ex 签名不含 fetch 参数, 回退原执行路径
            raw = connector.run(sql)
    except Exception as e:  # noqa: BLE001
        if is_timeout_error(e):
            shown = f"{exec_timeout:g}" if exec_timeout is not None else "默认"
            result.update(
                trust="none", ok=False,
                error=f"查询超时(超过 {shown} 秒), 已被数据库中止, "
                      "请缩小时间范围或先做聚合再试",
            )
            return result
        result.update(trust="none", ok=False, error=f"执行失败: {e}")
        return result
    columns, rows = [], []
    if raw:
        columns = list(raw[0])
        rows = [dict(zip(columns, r)) for r in raw[1:]]
    # 隐私脱敏:preview(confirm 试跑)同样遵守脱敏原则,与其他 DB 出口一致。
    if rows:
        rows, _ = _mask_dict_rows(datasource_id, columns, rows, sql=sql)
    result.update(columns=columns, rows=rows, row_count=len(rows))
    return result


def _resolve_ref(daos, ref_id: Optional[str], workspace_id: str) -> Optional[Any]:
    """取一个对象的最新版本(不论状态),用于 preview 解析提案引用。"""
    if not ref_id:
        return None
    hist = daos.objects.version_history(ref_id, workspace_id)
    return hist[0] if hist else None


def _preview_dim_condition(dim: Any, f: Dict[str, Any]) -> tuple:
    """筛选 label→code 映射;值字典缺失时把 label 当原始 code(fallback)。"""
    payload = dim.payload or {}
    col = payload.get("column")
    if not col:
        return None, f"筛选维度 {dim.id} 缺少 column"
    labels = f.get("values") or f.get("values_label") or []
    mode = (f.get("mode") or "include").lower()
    codes: List[str] = []
    for v in payload.get("values") or []:
        for lbl in labels:
            if lbl == v.get("label") or lbl in (v.get("aliases") or []):
                codes.extend(str(c) for c in (v.get("codes") or []))
    if not codes:
        codes = [str(l) for l in labels]  # 值字典为空 → 原始 code
    if not codes:
        return None, f"筛选维度 {dim.id} 无有效值"
    quoted = ", ".join(f"'{c}'" for c in sorted(set(codes)))
    op = "NOT IN" if mode == "exclude" else "IN"
    return f"{col} {op} ({quoted})", None


def _assemble_preview_sql(mp: Dict[str, Any], ep: Dict[str, Any],
                          binding: Dict[str, Any], group_cols: List[str],
                          dim_conditions: List[str],
                          time_range: Optional[Dict[str, Any]]) -> str:
    """复用 DbBindingExecutor 的确定性组装;行数限制由 _preview_run 按方言生成。"""
    executor = DbBindingExecutor()
    return executor._assemble_sql(mp, ep, binding, group_cols, dim_conditions, time_range)


def _preview_metric(daos, obj, mp: Dict[str, Any], ws: str,
                    filters, group_by, time_range, limit) -> Dict[str, Any]:
    warnings: List[str] = []
    entity = _resolve_ref(daos, mp.get("entity"), ws)
    if not entity:
        return _preview_fail(f"指标引用的实体 {mp.get('entity')} 不存在")
    ep = entity.payload or {}
    binding = ep.get("binding") or {}
    table = binding.get("table")
    ds_id = binding.get("datasource_id")
    if not table or not ds_id:
        return _preview_fail(f"实体 {entity.id} 缺少 binding.table/datasource_id,无法组装")
    expression = mp.get("expression")
    if not expression:
        return _preview_fail("指标缺少 expression")

    group_cols: List[str] = []
    grain = mp.get("grain") or []
    for dim_id in group_by or []:
        dim = _resolve_ref(daos, dim_id, ws)
        if not dim:
            warnings.append(f"分组维度 {dim_id} 未找到,已忽略")
            continue
        col = (dim.payload or {}).get("column")
        if not col:
            warnings.append(f"分组维度 {dim_id} 缺少 column,已忽略")
            continue
        # 大小写不敏感比较:Oracle 等库列名大小写由存储决定,LLM 常混写大小写
        if grain and col.upper() not in [g.upper() for g in grain] and (
            dim.name or ""
        ).lower() not in [g.lower() for g in grain]:
            warnings.append(f"分组维度 {dim_id} 不在指标粒度 {grain} 内(试跑仍执行)")
        group_cols.append(col)

    dim_conditions: List[str] = []
    for f in filters or []:
        dim_id = f.get("dim_id") or f.get("dim")
        dim = _resolve_ref(daos, dim_id, ws)
        if not dim:
            warnings.append(f"筛选维度 {dim_id} 未找到,已忽略")
            continue
        cond, warn = _preview_dim_condition(dim, f)
        if cond:
            dim_conditions.append(cond)
        elif warn:
            warnings.append(warn)

    sql = _assemble_preview_sql(mp, ep, binding, group_cols, dim_conditions, time_range)
    return _preview_run(sql, ds_id, obj, warnings, limit)


def _preview_entity(daos, obj, payload: Dict[str, Any], ws: str, limit: int) -> Dict[str, Any]:
    binding = payload.get("binding") or {}
    table = binding.get("table")
    ds_id = binding.get("datasource_id")
    if not table or not ds_id:
        return _preview_fail("实体缺少 binding.table/datasource_id")
    sql = f"SELECT * FROM {table}"
    conds = payload.get("default_filters") or []
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    return _preview_run(sql, ds_id, obj, limit=limit)


def _preview_dimension(daos, obj, payload: Dict[str, Any], ws: str, limit: int) -> Dict[str, Any]:
    col = payload.get("column")
    if not col:
        return _preview_fail("维度缺少 column")
    entity = _resolve_ref(daos, payload.get("entity"), ws)
    if not entity:
        return _preview_fail("维度引用的实体不存在(无法定位表)")
    binding = (entity.payload or {}).get("binding") or {}
    table = binding.get("table")
    ds_id = binding.get("datasource_id")
    if not table or not ds_id:
        return _preview_fail(f"实体 {entity.id} 缺少 binding.table/datasource_id")
    sql = f"SELECT DISTINCT {col} AS {col} FROM {table}"
    conds = (entity.payload or {}).get("default_filters") or []
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    result = _preview_run(sql, ds_id, obj, limit=limit)
    if not result.get("ok"):
        return result
    actual = {str(r[col]) for r in result["rows"] if r.get(col) is not None}
    proposed = set()
    for v in payload.get("values") or []:
        proposed.update(str(c) for c in (v.get("codes") or []))
    missing = sorted(proposed - actual)
    extra = sorted(actual - proposed)
    if missing:
        result["warnings"].append(f"值字典 {len(missing)} 个 code 未在表中出现: {missing[:10]}")
    else:
        result["warnings"].append("值字典全部落在真实值中")
    if extra:
        result["warnings"].append(f"表中有 {len(extra)} 个未收录值: {extra[:10]}")
    return result


def _preview_relation(daos, obj, payload: Dict[str, Any], ws: str, limit: int) -> Dict[str, Any]:
    src = _resolve_ref(daos, payload.get("from"), ws)
    dst = _resolve_ref(daos, payload.get("to"), ws)
    if not src or not dst:
        return _preview_fail("relation 端点实体不存在")
    sb = (src.payload or {}).get("binding") or {}
    db = (dst.payload or {}).get("binding") or {}
    if sb.get("datasource_id") != db.get("datasource_id"):
        return _preview_fail("跨数据源 join 暂不支持试跑")
    path = payload.get("path")
    if not path:
        return _preview_fail("relation 缺少 path(join 条件)")
    import re

    m = re.fullmatch(r"\s*([\w.]+)\s*=\s*([\w.]+)\s*", str(path))
    if not m:
        return _preview_fail(f"无法解析 join path: {path}")
    left, right = m.group(1), m.group(2)
    def _parts(ident: str):
        # 兼容 表.列 与 库.表.列(Oracle owner.table.column)两种写法:
        # 按最后一个点拆分为 表(可含库前缀) + 列
        tbl, _, col = ident.rpartition(".")
        return tbl, col
    lt, lc = _parts(left)
    rt, rc = _parts(right)
    if not lc or not rc:
        return _preview_fail(f"join 条件需形如 表.列 = 表.列(可含库前缀): {path}")
    sql = (
        f"SELECT a.{lc} AS fk_from, b.{rc} AS fk_to "
        f"FROM {lt} a JOIN {rt} b ON a.{lc} = b.{rc}"
    )
    return _preview_run(sql, sb.get("datasource_id"), obj, limit=limit)


def preview_payload(daos, obj: Any, workspace_id: str,
                    filters: Optional[List[Dict[str, Any]]] = None,
                    group_by: Optional[List[str]] = None,
                    time_range: Optional[Dict[str, Any]] = None,
                    limit: int = 20) -> Dict[str, Any]:
    """基于提案 payload 试跑(调试验证)。obj 可为任意状态(proposed 优先)。"""
    obj_type = obj.obj_type
    payload = obj.payload or {}
    if obj_type == "metric":
        return _preview_metric(daos, obj, payload, workspace_id, filters, group_by, time_range, limit)
    if obj_type == "entity":
        return _preview_entity(daos, obj, payload, workspace_id, limit)
    if obj_type == "dimension":
        return _preview_dimension(daos, obj, payload, workspace_id, limit)
    if obj_type == "relation":
        return _preview_relation(daos, obj, payload, workspace_id, limit)
    return _preview_fail(f"对象类型 {obj_type} 不支持试跑")


def preview_query(
    object_id: str,
    version: int,
    workspace_id: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    group_by: Optional[List[str]] = None,
    time_range: Optional[Dict[str, Any]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """确认页调试验证入口(DB 类):按提案版本试跑,返回 real data + SQL + warnings。"""
    daos = _ExecutorDaos()
    obj = daos.objects.get_version(object_id, version, workspace_id)
    if not obj:
        return _preview_fail(f"对象 {object_id}@v{version} 不存在")
    return preview_payload(daos, obj, workspace_id, filters, group_by, time_range, limit)


async def preview_canon(
    object_id: str,
    version: int,
    workspace_id: str,
) -> Dict[str, Any]:
    """确认页调试验证入口(文档类):anchor 回放,校验 source_quote ∈ 原文。"""
    daos = _ExecutorDaos()
    obj = daos.objects.get_version(object_id, version, workspace_id)
    if not obj:
        return _preview_fail(f"对象 {object_id}@v{version} 不存在")
    if obj.obj_type not in DocBindingExecutor._DOC_TYPES:
        return _preview_fail(f"类型 {obj.obj_type} 非文档类,不支持出处校验")
    p = obj.payload or {}
    binding = p.get("binding") or {}
    quote = p.get("source_quote")
    warnings: List[str] = []
    original = await DocBindingExecutor._default_doc_fetcher(
        binding.get("space", ""), binding.get("doc_id", "")
    )
    anchor_verified = None
    n_quote = _normalize_anchor(quote)
    if original is None:
        warnings.append("基础设施不可用或文档缺失,无法校验出处")
    else:
        anchor_verified = bool(n_quote and n_quote in _normalize_anchor(original))
        if not anchor_verified:
            warnings.append("锚点漂移:原文中未找到冻结摘录(文档可能已改版)")
    return {
        "trust": "preview", "ok": True, "error": None,
        "warnings": warnings, "columns": [], "rows": [], "row_count": 0,
        "sql": None, "anchor_verified": anchor_verified, "quote": quote,
        "lineage": {
            "obj_id": object_id, "version": version, "obj_type": obj.obj_type,
            "mode": "preview", "executed_at": datetime.now().isoformat(),
        },
    }
