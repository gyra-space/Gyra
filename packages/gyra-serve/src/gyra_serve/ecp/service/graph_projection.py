"""ECP 边投影 —— 从语义对象 payload 抽取图边（写时物化的投影源）。

背景(models.py 的 SemanticEdgeDao docstring):边表是"materialized
projection, never hand-edited"——本模块是投影的单一计算点,写入路径
(propose / confirm 产生新版本)与全量重建(rebuild_edges)都调这里,
物理上不可能漂移。

全景图的三类节点(node_kind):

- ``object``  语义对象本身(节点 id = 对象 id,如 ``ent.order``)
- ``asset``   已登记的原始资产引用(节点 id = ``asset:<asset_ref.pk>``,
   kind = db / document / space / api,来自 AssetRefDao)
- ``kn``      知识层节点(wiki 文档 / 跨文档实体,来自 knowledge L2 图,
   由 service.graph() 查询时聚合,不经边表)

对象→对象边(纯函数,无需查库):

- metric    ─belongs_to─▶ payload.entity
- relation  ─joins─▶ payload.from / payload.to
- dimension ─belongs_to─▶ payload.entity(若有)

对象→资产边(经 ``resolve_asset`` 反查 asset_ref 注册表,未登记则不出边):

- entity                  ─binding─▶ asset:db(datasource_id)
- claim/terminology/policy ─ref─▶ asset:document(``{space}:{doc_id}``)
"""

from typing import Any, Callable, Dict, List, Optional

# (kind, ref_id) -> 资产节点 id("asset:<pk>")或 None(未登记)
AssetResolver = Callable[[str, str], Optional[str]]

DOC_TYPES = ("claim", "terminology", "policy")


def _doc_ref_id(binding: Dict[str, Any]) -> Optional[str]:
    """文档类 binding → document 资产的 ref_id(``{space}:{doc_id}``)。"""
    doc_id = binding.get("doc_id")
    if not doc_id:
        return None
    if isinstance(doc_id, str) and doc_id.startswith(("doc:", "verbat:")):
        doc_id = doc_id.split(":", 1)[1]
    space = binding.get("space") or ""
    return f"{space}:{doc_id}" if space else str(doc_id)


def project_edges(
    obj_type: str,
    payload: Dict[str, Any],
    resolve_asset: Optional[AssetResolver] = None,
) -> List[Dict[str, Any]]:
    """从对象 payload 抽取全部出边。

    返回 ``[{edge_type, dst, status?}]``;对象→对象边无条件产出(dst 是
    对象 id),对象→资产边仅在资产已登记(resolve_asset 命中)时产出。
    纯函数:同一 (obj_type, payload, 注册表状态) 永远同一结果(幂等投影)。
    """
    if not isinstance(payload, dict):
        return []
    edges: List[Dict[str, Any]] = []

    def _add(edge_type: str, dst: Any) -> None:
        if isinstance(dst, str) and dst:
            edges.append({"edge_type": edge_type, "dst": dst})

    if obj_type == "entity":
        binding = payload.get("binding") or {}
        ds = binding.get("datasource_id")
        if ds is not None and resolve_asset:
            node = resolve_asset("db", str(ds))
            if node:
                _add("binding", node)
    elif obj_type == "metric":
        _add("belongs_to", payload.get("entity"))
    elif obj_type == "relation":
        _add("joins", payload.get("from"))
        _add("joins", payload.get("to"))
    elif obj_type == "dimension":
        _add("belongs_to", payload.get("entity"))
    elif obj_type in DOC_TYPES:
        binding = payload.get("binding") or {}
        ref_id = _doc_ref_id(binding)
        if ref_id and resolve_asset:
            node = resolve_asset("document", ref_id)
            if node:
                _add("ref", node)

    return edges
