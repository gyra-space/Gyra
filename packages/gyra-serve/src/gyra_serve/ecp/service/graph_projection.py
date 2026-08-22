"""ECP 边投影 —— 从语义对象 payload 抽取图边(单一计算点)。

背景(models.py 的 SemanticEdgeDao docstring):边表是"materialized
projection, never hand-edited"——本模块是投影的单一计算点。两个消费方:

- ``Service.graph()``:查询时**实时投影**全部边(图永远反映当前对象
  状态,不依赖物化表是否跟上——存量数据冷启动也有连线);
- ``Service._refresh_edges`` / ``rebuild_edges``:写时物化**对象→对象**
  边进边表(dst 是对象 id,长度安全,供 Agent 图遍历/lint 用)。

全景图的三类节点(node_kind):

- ``object``  语义对象本身(节点 id = 对象 id,如 ``ent.order``)
- ``asset``   资产节点(节点 id = ``asset:<kind>:<ref_id>``,**稳定 id**:
  已登记(AssetRefVO)则 enrich 名称/状态,未登记则为虚拟节点
  status="unregistered"——跨资源连线不依赖登记完整性)
- ``kn``      知识层节点(wiki 文档 / verbatim,来自 knowledge L2 图,
  由 service.graph() 查询时聚合,不经边表)

边一览:

- metric    ─belongs_to─▶ payload.entity                       (对象→对象)
- relation  ─joins─▶ payload.from / payload.to                 (对象→对象)
- dimension ─belongs_to─▶ payload.entity                       (对象→对象)
- entity    ─binding─▶ asset:db:<datasource_id>                (对象→资产)
- claim/terminology/policy ─ref─▶ asset:document:<space>:<doc_id>
                                                                (对象→资产)

设计决策:资产边**不进物化边表**——资产 ref_id(``{space}:{doc_id}``)可达
256 字符,超出边表 src/dst 的 String(128);且资产边只服务可视化(实时投影
成本可忽略),写路径物化只保留对象→对象边。
"""

from typing import Any, Dict, List, Tuple

DOC_TYPES = ("claim", "terminology", "policy")


def _doc_ref_id(binding: Dict[str, Any]) -> str:
    """文档类 binding → document 资产的 ref_id(``{space}:{doc_id}``)。"""
    doc_id = binding.get("doc_id")
    if not doc_id:
        return ""
    if isinstance(doc_id, str) and doc_id.startswith(("doc:", "verbat:")):
        doc_id = doc_id.split(":", 1)[1]
    space = binding.get("space") or ""
    return f"{space}:{doc_id}" if space else str(doc_id)


def asset_node_id(kind: str, ref_id: str) -> str:
    """资产节点的稳定 id(登记与否一致,登记仅 enrich)。"""
    return f"asset:{kind}:{ref_id}"


def project_edges(
    obj_type: str, payload: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """从对象 payload 抽取全部出边与被引用资产。

    返回 ``(edges, asset_refs)``:

    - edges: ``[{edge_type, dst}]``。对象→对象边 dst = 对象 id;
      对象→资产边 dst = ``asset:<kind>:<ref_id>``(稳定 id)。
    - asset_refs: 被引用的 ``[(kind, ref_id)]``(去重),调用方据此生成
      资产节点(已登记 enrich / 未登记虚拟节点)。

    纯函数:同一 (obj_type, payload) 永远同一结果(幂等投影),不查库、
    不依赖资产注册表状态。
    """
    if not isinstance(payload, dict):
        return [], []
    edges: List[Dict[str, Any]] = []
    refs: List[Tuple[str, str]] = []

    def _add(edge_type: str, dst: Any) -> None:
        if isinstance(dst, str) and dst:
            edges.append({"edge_type": edge_type, "dst": dst})

    if obj_type == "entity":
        binding = payload.get("binding") or {}
        ds = binding.get("datasource_id")
        if ds is not None:
            ref_id = str(ds)
            _add("binding", asset_node_id("db", ref_id))
            refs.append(("db", ref_id))
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
        if ref_id:
            _add("ref", asset_node_id("document", ref_id))
            refs.append(("document", ref_id))

    return edges, refs
