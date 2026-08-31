"""ECP 语义身份：对象 id 稳定派生 + 语义指纹去重键（协议层 ①②）。

背景（对话 52ea9cf2 协议根因）：
- ``object_id``（ent./mtr./dim./rel. 前缀）以前由 LLM 每次现编，同一物理概念
  今天叫 mtr.gmv、明天被学成 mtr.sales_total —— id 一旦不同，`create_proposal`
  里"同 id + payload 逐字节相等"的硬去重就失效，已确认概念会被重复提进待办。
- 根因是：身份归 LLM 命名（不稳定），且去重判"字面相等"而非"语义同源"，
  写入路径也没有确定性语义门禁。

本模块提供两条协议修正：
1. ``derive_object_id``   —— 从绑定结构推导确定性 id（给未显式命名的新对象），
   LLM 不再拥有身份，只提供人类可读字段（name/aliases/expression/values 等）。
2. ``semantic_fingerprint`` —— 与 id 无关的"同一概念"判据（归一化语义指纹）。
   提案入库前用它比对已确认目录：命中 → 路由为"修订"（③，沿用已确认对象 id，
   不生成并行的新候选）；未命中 → 才作为新候选。这让"已确认概念"从构造上
   不会再被当作新提案进入待办（④），且不依赖 LLM 听话。

设计取舍：id 仍允许调用方（Agent）显式命名——因为 Agent 会在提案内互相引用
（如 metric.entity=ent.xxx），静默改写 id 会破坏这些跨引用。因此稳定性靠"修订
沿用已确认 id"来实现：每个概念自首次确认起收敛到唯一 id；后续同概念先经指纹
命中，或去重、或成为该 id 下的修订，id 不再漂移。
"""

import json
import re
from typing import Any, Dict, Optional

from .contracts import normalize_payload

_WS_RE = re.compile(r"\s+")


def _norm_ident(value: Any) -> str:
    """归一化标识（表名/列名/实体名）：去首尾空白、小写、压缩连续空白。

    保留 ``.``（owner.table）与 ``_``，因为它们是表/列名的真实组成部分；
    只抹平大小写与首尾/中间多余空白。
    """
    if value is None:
        return ""
    return _WS_RE.sub(" ", str(value).strip().lower()).strip()


def _norm_expr(value: Any) -> str:
    """归一化聚合表达式：小写 + 压缩空白（SUM( A ) → sum( a )）。"""
    if value is None:
        return ""
    return _WS_RE.sub(" ", str(value).strip().lower()).strip()


def _norm_json(value: Any) -> str:
    """归一化结构化筛选（extra_filters 等）：排序键 + 小写序列化。"""
    if value is None:
        return ""
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        return ""


def _slug(value: Any) -> str:
    """把表达式/名称压成 id 可安全嵌入的短串（小写、非字母数字转 _）。"""
    s = (value or "").strip().lower()
    s = re.sub(r"\W+", "_", s)
    return s.strip("_")[:64]


def semantic_fingerprint(obj_type: str, payload: Any) -> Optional[str]:
    """归一化语义指纹：判断"同一概念"的确定性键（无 id 依赖）。

    - entity      按 (datasource_id, table)——同一物理表即同一实体。
    - metric      按 (entity, expression, extra_filters)——聚合口径标识一个指标；
                   name 是标签不算身份（改名不改口径），filters 是口径的一部分须纳入。
    - dimension   按 (entity, column)。
    - relation    按 {from, to}（无向）。
    - claim/policy 按 source_quote 逐字摘录（原文子串校验同源）。
    - terminology 按 (name, definition)。

    无法派生物理身份（缺关键绑定字段）时返回 None，调用方跳过去重。
    """
    payload = normalize_payload(obj_type, payload or {})
    t = obj_type
    if t == "entity":
        binding = payload.get("binding") or {}
        ds = binding.get("datasource_id")
        table = _norm_ident(binding.get("table"))
        if not table:
            return None
        return f"entity|{ds}|{table}"
    if t == "metric":
        entity = _norm_ident(payload.get("entity"))
        expr = _norm_expr(payload.get("expression"))
        if not entity or not expr:
            return None
        filters = _norm_json(payload.get("extra_filters"))
        return f"metric|{entity}|{expr}|{filters}"
    if t == "dimension":
        entity = _norm_ident(payload.get("entity"))
        col = _norm_ident(payload.get("column"))
        if not entity or not col:
            return None
        return f"dimension|{entity}|{col}"
    if t == "relation":
        f = _norm_ident(payload.get("from"))
        to = _norm_ident(payload.get("to"))
        if not f or not to:
            return None
        return f"relation|{min(f, to)}|{max(f, to)}"
    if t in ("claim", "policy"):
        quote = _norm_ident(payload.get("source_quote"))
        if not quote:
            return None
        return f"{t}|{quote}"
    if t == "terminology":
        name = _norm_ident(payload.get("name"))
        definition = _norm_ident(payload.get("definition"))
        if not (name or definition):
            return None
        return f"terminology|{name}|{definition}"
    return None


def derive_object_id(obj_type: str, payload: Any) -> Optional[str]:
    """为未显式命名的对象推导确定性 id（① 身份派生）。

    仅供 ``Service.propose`` 在调用方未提供 ``object_id`` 时使用；Agent 显式命名
    的 id 一律保留（以维持其跨引用）。一旦某概念被确认，后续同名概念经语义指纹
    命中去重/修订，会收敛到该确认 id，因此这里只影响"首个新概念"的命名。
    """
    payload = normalize_payload(obj_type, payload or {})
    if obj_type == "entity":
        binding = payload.get("binding") or {}
        table = (binding.get("table") or "").strip()
        if not table:
            return None
        ds = binding.get("datasource_id")
        return f"ent.{ds}.{table}" if ds is not None else f"ent.{table}"
    if obj_type == "metric":
        entity = (_norm_ident(payload.get("entity")) or "").strip()
        expr = (payload.get("expression") or "").strip()
        if not entity or not expr:
            return None
        return f"mtr.{entity}.{_slug(expr)}"
    if obj_type == "dimension":
        entity = (_norm_ident(payload.get("entity")) or "").strip()
        col = (_norm_ident(payload.get("column")) or "").strip()
        if not entity or not col:
            return None
        return f"dim.{entity}.{col}"
    if obj_type == "relation":
        f = (_norm_ident(payload.get("from")) or "").strip()
        to = (_norm_ident(payload.get("to")) or "").strip()
        if not f or not to:
            return None
        return f"rel.{f}__{to}"
    return None
