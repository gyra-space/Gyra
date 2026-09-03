"""ECP 提案业务视图 —— 从 payload 派生"业务人看得懂"的提案内容。

设计(docs/ECP-functional-design.md 提案内容升级):
- **读时派生,不落库**——血缘与 SQL 是 payload 的函数,落库必腐化;
  只有来源快照(provenance)在写入时落库。
- 三个业务问题一个视图回答:
  ① 从哪来 → lineage(库名/表/字段用途/引用对象状态)
  ② 用起来生成什么 SQL → sql_preview(与 executor 同一确定性组装,
     不执行;试跑真数据走 /debug)
  ③ 怎么被提出来的 → origin(provenance 优先,老数据降级 source 映射)

字段级血缘:metric.expression / extra_filters 经 sqlglot 解析出列名,
对照 entity.fields 标注 meaning/role;未声明的列(declared=False)
是口径疑点,前端高亮。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import sqlglot
from sqlglot import exp

from ..api.schemas import (
    ColumnRefVO,
    EvidenceItemVO,
    LineageVO,
    ObjectRefVO,
    OriginVO,
    ProposalViewVO,
    SemanticObjectVO,
    SqlPreviewVO,
)
from ..config import ORIGIN_LABELS, origin_from_source

logger = logging.getLogger(__name__)

_DB_TYPES = ("entity", "metric", "dimension", "relation")
_DOC_TYPES = ("claim", "terminology", "policy")


def _as_dict(value: Any) -> Dict[str, Any]:
    """把任意值安全当作 dict 用(非 dict 一律按空处理)。

    历史/导入数据可能出现 payload / binding / fields 不是 object(如 JSON 数组),
    读时派生的详情视图必须能降级而不是抛 ``'list' object has no attribute 'get'``。
    """
    return value if isinstance(value, dict) else {}


# ------------------------------------------------------------------ summary
def _summary(vo: SemanticObjectVO) -> str:
    """一句话业务口径(按类型契约生成;取代前端 summarizePayload 的散落逻辑)。"""
    p = _as_dict(vo.payload)
    if vo.obj_type == "entity":
        binding = _as_dict(p.get("binding"))
        table = binding.get("table") or "?"
        pk = binding.get("pk")
        base = f"绑定表 {table}" + (f"(PK: {pk})" if pk else "")
        n_fields = len(_as_dict(p.get("fields")))
        return f"{base} · {n_fields} 个字段" if n_fields else base
    if vo.obj_type == "metric":
        expr = p.get("expression") or "?"
        grain = p.get("grain") or []
        base = f"口径 {expr}"
        return f"{base} · 粒度 {', '.join(grain)}" if grain else base
    if vo.obj_type == "dimension":
        col = p.get("column") or "?"
        n = len(p.get("values") or [])
        return f"维度列 {col} · {n} 个值"
    if vo.obj_type == "relation":
        path = p.get("path")
        base = f"{p.get('from') or '?'} → {p.get('to') or '?'}"
        return f"{base} · {path}" if path else base
    # 文档类
    text = p.get("text") or p.get("definition") or p.get("rule") or ""
    return text[:80] + ("…" if len(text) > 80 else "") if text else ""


# -------------------------------------------------------------------- origin
def _origin(vo: SemanticObjectVO) -> OriginVO:
    prov = _as_dict(getattr(vo, "provenance", None))
    if prov:
        kind = prov.get("origin") or "legacy"
        return OriginVO(
            kind=kind,
            label=ORIGIN_LABELS.get(kind, kind),
            actor=prov.get("actor"),
            origin_sql=prov.get("origin_sql") or [],
            miss_ref=prov.get("miss_ref"),
            note=prov.get("note"),
            derived_from=prov.get("derived_from"),
        )
    # 老数据降级:source 自由文本映射
    kind = origin_from_source(vo.source)
    return OriginVO(
        kind=kind,
        label=ORIGIN_LABELS.get(kind, kind),
        legacy_source=vo.source,
    )


# ------------------------------------------------------------------ 列解析
def _sql_columns(fragment: Any) -> List[str]:
    """从 SQL 片段(expression/filter)解析引用的列名(sqlglot,失败返回 [])。"""
    if not fragment or not isinstance(fragment, str):
        return []
    try:
        tree = sqlglot.parse_one(fragment)
        return [c.name for c in tree.find_all(exp.Column)]
    except Exception:  # noqa: BLE001
        return []


def _column_ref(
    col: str, usage: str, fields: Dict[str, Any], seen: Dict[str, ColumnRefVO]
) -> None:
    """登记一个列引用(按列名去重,usage 合并);fields 为 entity.fields 声明。"""
    meta = _as_dict(fields.get(col))
    existing = seen.get(col)
    if existing:
        if usage and usage not in existing.usage:
            existing.usage = f"{existing.usage}·{usage}" if existing.usage else usage
        return
    seen[col] = ColumnRefVO(
        column=col,
        meaning=meta.get("meaning"),
        role=meta.get("role"),
        usage=usage,
        declared=col in fields,
    )


def _ref_vo(obj: Any) -> ObjectRefVO:
    return ObjectRefVO(
        id=getattr(obj, "id", None) or "?",
        obj_type=getattr(obj, "obj_type", None),
        name=getattr(obj, "name", None),
        status=getattr(obj, "status", None),
        version=getattr(obj, "version", None),
    )


def _resolve_ref(objects: Any, ref_id: Optional[str], workspace_id: str) -> Optional[Any]:
    """取引用对象的最新版本(不论状态;与 executor preview 同语义)。"""
    if not objects or not ref_id:
        return None
    try:
        hist = objects.version_history(ref_id, workspace_id)
        return hist[0] if hist else None
    except Exception:  # noqa: BLE001
        return None


def _datasource_name(ds_id: Any, resolver: Optional[Callable[[Any], Optional[str]]]) -> Optional[str]:
    if ds_id is None or resolver is None:
        return None
    try:
        return resolver(ds_id)
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------- lineage
def _build_lineage(
    vo: SemanticObjectVO,
    objects: Any,
    ds_name_resolver: Optional[Callable[[Any], Optional[str]]],
) -> Optional[LineageVO]:
    p = _as_dict(vo.payload)
    ws = vo.workspace_id

    if vo.obj_type in _DOC_TYPES:
        binding = _as_dict(p.get("binding"))
        return LineageVO(
            document={
                "space": binding.get("space"),
                "doc_id": binding.get("doc_id"),
                "anchor": binding.get("anchor"),
            }
        )

    if vo.obj_type == "entity":
        binding = _as_dict(p.get("binding"))
        ds_id = binding.get("datasource_id")
        table = binding.get("table")
        fields = _as_dict(p.get("fields"))
        cols: Dict[str, ColumnRefVO] = {}
        for name, meta in fields.items():
            meta = _as_dict(meta)
            role = meta.get("role")
            usage = {
                "identifier": "主键" if binding.get("pk") == name else "标识",
                "measure": "度量",
                "dimension": "维度",
                "time": "时间列",
            }.get(role, role or "")
            cols[name] = ColumnRefVO(
                column=name,
                meaning=meta.get("meaning"),
                role=role,
                usage=usage,
                declared=True,
            )
        for frag in p.get("default_filters") or []:
            for col in _sql_columns(frag):
                _column_ref(col, "筛选条件", fields, cols)
        return LineageVO(
            datasource_id=ds_id,
            datasource_name=_datasource_name(ds_id, ds_name_resolver),
            tables=[table] if table else [],
            columns=list(cols.values()),
        )

    if vo.obj_type == "metric":
        entity = _resolve_ref(objects, p.get("entity"), ws)
        ep = _as_dict(entity.payload) if entity else {}
        binding = _as_dict(ep.get("binding"))
        fields = _as_dict(ep.get("fields"))
        ds_id = binding.get("datasource_id")
        cols: Dict[str, ColumnRefVO] = {}
        for col in _sql_columns(p.get("expression")):
            _column_ref(col, "度量表达式", fields, cols)
        for frag in p.get("extra_filters") or []:
            for col in _sql_columns(frag):
                _column_ref(col, "筛选条件", fields, cols)
        for g in p.get("grain") or []:
            if isinstance(g, str) and g in fields:
                _column_ref(g, "分组粒度", fields, cols)
        pk = binding.get("pk")
        if pk:
            _column_ref(pk, "主键", fields, cols)
        for name, meta in fields.items():
            if _as_dict(meta).get("role") == "time":
                _column_ref(name, "时间列", fields, cols)
        objects_refs = [_ref_vo(entity)] if entity else []
        return LineageVO(
            datasource_id=ds_id,
            datasource_name=_datasource_name(ds_id, ds_name_resolver),
            tables=[binding["table"]] if binding.get("table") else [],
            columns=list(cols.values()),
            objects=objects_refs,
        )

    if vo.obj_type == "dimension":
        entity = _resolve_ref(objects, p.get("entity"), ws)
        ep = _as_dict(entity.payload) if entity else {}
        binding = _as_dict(ep.get("binding"))
        fields = _as_dict(ep.get("fields"))
        ds_id = binding.get("datasource_id")
        cols: Dict[str, ColumnRefVO] = {}
        col = p.get("column")
        if col:
            _column_ref(col, "维度列", fields, cols)
        objects_refs = [_ref_vo(entity)] if entity else []
        return LineageVO(
            datasource_id=ds_id,
            datasource_name=_datasource_name(ds_id, ds_name_resolver),
            tables=[binding["table"]] if binding.get("table") else [],
            columns=list(cols.values()),
            objects=objects_refs,
        )

    if vo.obj_type == "relation":
        src = _resolve_ref(objects, p.get("from"), ws)
        dst = _resolve_ref(objects, p.get("to"), ws)
        tables: List[str] = []
        ds_id = None
        for e in (src, dst):
            b = _as_dict(_as_dict(e.payload).get("binding")) if e else {}
            if b.get("table") and b["table"] not in tables:
                tables.append(b["table"])
            ds_id = ds_id if ds_id is not None else b.get("datasource_id")
        cols: Dict[str, ColumnRefVO] = {}
        for col in _sql_columns(str(p.get("path") or "")):
            _column_ref(col, "join 条件", {}, cols)
        objects_refs = [_ref_vo(e) for e in (src, dst) if e]
        return LineageVO(
            datasource_id=ds_id,
            datasource_name=_datasource_name(ds_id, ds_name_resolver),
            tables=tables,
            columns=list(cols.values()),
            objects=objects_refs,
        )

    return None


# --------------------------------------------------------------- sql preview
def _sample_time_range(ep: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """实体声明了 role=time 字段时,生成"近 7 天"示例时间窗(静态预览用)。"""
    for name, meta in _as_dict(ep.get("fields")).items():
        if _as_dict(meta).get("role") == "time":
            today = datetime.now().date()
            start = today - timedelta(days=7)
            return {"column": name, "range": f"{start.isoformat()}~{today.isoformat()}"}
    return None


def _build_sql_preview(
    vo: SemanticObjectVO, objects: Any
) -> Optional[SqlPreviewVO]:
    """静态 SQL 组装效果(不执行;与 executor 同一确定性组装路径)。

    任何解析失败不报错——提案本就允许不完整,失败原因进 warnings,
    sql=None 由前端降级展示。
    """
    p = _as_dict(vo.payload)
    ws = vo.workspace_id
    warnings: List[str] = []
    participants: List[ObjectRefVO] = []

    try:
        if vo.obj_type == "metric":
            entity = _resolve_ref(objects, p.get("entity"), ws)
            if not entity:
                return SqlPreviewVO(
                    sql=None, warnings=[f"指标引用的实体 {p.get('entity')} 未解析"],
                )
            participants.append(_ref_vo(entity))
            ep = _as_dict(entity.payload)
            binding = _as_dict(ep.get("binding"))
            if not binding.get("table"):
                return SqlPreviewVO(
                    sql=None,
                    participants=participants,
                    warnings=[f"实体 {entity.id} 缺少 binding.table,无法组装"],
                )
            if not p.get("expression"):
                return SqlPreviewVO(
                    sql=None,
                    participants=participants,
                    warnings=["指标缺少 expression"],
                )
            from .executor import DbBindingExecutor

            time_range = _sample_time_range(ep)
            sql = DbBindingExecutor()._assemble_sql(
                p, ep, binding, [], [], time_range
            )
            scenario = "静态预览:无分组、无额外筛选"
            if time_range:
                scenario += f"、近 7 天示例时间窗({time_range['range']})"
            scenario += ";试跑可自定义分组/筛选/时间"
            return SqlPreviewVO(
                sql=sql, scenario=scenario,
                participants=participants, warnings=warnings,
            )

        if vo.obj_type == "entity":
            binding = _as_dict(p.get("binding"))
            table = binding.get("table")
            if not table:
                return SqlPreviewVO(sql=None, warnings=["实体缺少 binding.table"])
            sql = f"SELECT * FROM {table}"
            conds = p.get("default_filters") or []
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            return SqlPreviewVO(
                sql=sql, scenario="静态预览:实体默认口径全量采样",
                warnings=warnings,
            )

        if vo.obj_type == "dimension":
            col = p.get("column")
            if not col:
                return SqlPreviewVO(sql=None, warnings=["维度缺少 column"])
            entity = _resolve_ref(objects, p.get("entity"), ws)
            if not entity:
                return SqlPreviewVO(
                    sql=None, warnings=[f"维度引用的实体 {p.get('entity')} 未解析"]
                )
            participants.append(_ref_vo(entity))
            ep = _as_dict(entity.payload)
            binding = _as_dict(ep.get("binding"))
            table = binding.get("table")
            if not table:
                return SqlPreviewVO(
                    sql=None, participants=participants,
                    warnings=[f"实体 {entity.id} 缺少 binding.table"],
                )
            sql = f"SELECT DISTINCT {col} AS {col} FROM {table}"
            conds = ep.get("default_filters") or []
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            return SqlPreviewVO(
                sql=sql, scenario="静态预览:维度真实值去重采样",
                participants=participants, warnings=warnings,
            )

        if vo.obj_type == "relation":
            src = _resolve_ref(objects, p.get("from"), ws)
            dst = _resolve_ref(objects, p.get("to"), ws)
            if not src or not dst:
                return SqlPreviewVO(sql=None, warnings=["relation 端点实体未解析"])
            participants.extend([_ref_vo(src), _ref_vo(dst)])
            sb = _as_dict(_as_dict(src.payload).get("binding"))
            db = _as_dict(_as_dict(dst.payload).get("binding"))
            if sb.get("datasource_id") != db.get("datasource_id"):
                return SqlPreviewVO(
                    sql=None, participants=participants,
                    warnings=["跨数据源 join 暂不支持预览"],
                )
            path = p.get("path")
            if not path:
                return SqlPreviewVO(
                    sql=None, participants=participants,
                    warnings=["relation 缺少 path(join 条件),待确认人补全"],
                )
            import re as _re

            m = _re.fullmatch(r"\s*([\w.]+)\s*=\s*([\w.]+)\s*", str(path))
            if not m:
                return SqlPreviewVO(
                    sql=None, participants=participants,
                    warnings=[f"无法解析 join path: {path}"],
                )
            left, right = m.group(1), m.group(2)
            lt, _, lc = left.rpartition(".")
            rt, _, rc = right.rpartition(".")
            sql = (
                f"SELECT a.{lc} AS fk_from, b.{rc} AS fk_to "
                f"FROM {lt} a JOIN {rt} b ON a.{lc} = b.{rc}"
            )
            return SqlPreviewVO(
                sql=sql, scenario="静态预览:join 连通性验证",
                participants=participants, warnings=warnings,
            )
    except Exception as e:  # noqa: BLE001 预览失败不阻塞视图(降级为无 SQL)
        logger.info("[ecp] sql preview for %s@v%s failed: %s", vo.id, vo.version, e)
        return SqlPreviewVO(sql=None, warnings=[f"SQL 预览组装失败: {e}"])

    return None  # 文档类无 SQL 预览


# --------------------------------------------------------------------- 入口
def build_proposal_view(
    vo: SemanticObjectVO,
    objects: Any = None,
    ds_name_resolver: Optional[Callable[[Any], Optional[str]]] = None,
    level: str = "full",
) -> ProposalViewVO:
    """为一个语义对象版本构建业务视图。

    - ``objects``: SemanticObjectDao(解析引用对象;None 时 lineage/sql_preview
      只做自身 payload 可知的部分)
    - ``ds_name_resolver``: datasource_id → 数据源名(列表页可传入带缓存的
      解析器避免 N 次查询)
    - ``level``: "brief"(列表卡片:summary+origin+lineage,不算 SQL 预览)
      或 "full"(详情:含 sql_preview)
    """
    evidence = [
        EvidenceItemVO(source=e.get("source"), quote=e.get("quote"))
        for e in (vo.evidence or [])
        if isinstance(e, dict)
    ]
    return ProposalViewVO(
        summary=_summary(vo),
        origin=_origin(vo),
        lineage=_build_lineage(vo, objects, ds_name_resolver),
        sql_preview=(
            _build_sql_preview(vo, objects) if level == "full" else None
        ),
        evidence=evidence,
    )
