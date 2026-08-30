"""ECP ↔ knowledge 软层的只读桥梁(图谱/对齐共用的知识空间访问层)。

收敛三处重复(service.py 时代):knowledge Service 获取样板(5+ 份)、
slug 聚合规则(3 份 "ecp-{ws} + 资产 + ecp_ 派生 docs-")、kn 实体名收集。
全部 best-effort:空间不可达/服务缺失一律降级为空,不阻塞硬层主流程。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def get_knowledge_service(system_app: Any) -> Optional[Any]:
    """获取 knowledge Service 组件;未装配/异常返回 None(调用方降级)。"""
    try:
        from gyra_serve.knowledge.config import (
            SERVE_SERVICE_COMPONENT_NAME as KNOWLEDGE_SERVICE,
        )
        from gyra_serve.knowledge.service.service import Service as KnowledgeService

        return system_app.get_component(KNOWLEDGE_SERVICE, KnowledgeService)
    except Exception:  # noqa: BLE001
        return None


def knowledge_slugs(
    ws: str,
    registered: Dict[tuple, Any],
    referenced: Dict[tuple, Any],
) -> set:
    """聚合需要读取的知识空间 slug 集合(不依赖资产登记完整性)。

    来源:ECP 软层(ecp-<ws>) + 已登记 space/document 资产 + 被 claim
    引用的空间 + 场景空间派生(workspace_id 形如 ecp_<code> → docs-<code>)。
    """
    slugs = {f"ecp-{ws}"}
    for kind, ref_id in list(registered) + list(referenced):
        if kind == "space":
            slugs.add(ref_id)
        elif kind == "document" and ":" in ref_id:
            slugs.add(ref_id.split(":", 1)[0])
    # 场景空间派生:ECP workspace_id = ecp_<workspace_code>,
    # 文档空间 slug 约定 docs-<workspace_code>(workspace 模块上传入口)
    if ws.startswith("ecp_"):
        slugs.add(f"docs-{ws[len('ecp_') :]}")
    return slugs


def collect_registered_referenced(svc: Any, ws: str) -> Tuple[Dict[tuple, Any], Dict[tuple, None]]:
    """扫描对象 payload,收集 (已登记资产, 被引用资产) 两个索引。"""
    from .graph_projection import project_edges

    objects = svc._object_dao.list_latest(workspace_id=ws, page=1, page_size=1000).items
    registered = {(a.kind, a.ref_id): a for a in svc._asset_dao.list(ws)}
    referenced: Dict[tuple, None] = {}
    for o in objects:
        _, refs = project_edges(o.obj_type, o.payload or {})
        for key in refs:
            referenced[key] = None
    return registered, referenced


async def kn_entity_names(svc: Any, ws: str) -> Dict[str, List[str]]:
    """收集各知识空间的实体名(裸标识端点)——LLM 对齐的输入。

    与图谱同一套 slug 聚合与端点规则:非 ``doc:``/``verbat:`` 前缀的
    端点即实体名。
    """
    registered, referenced = collect_registered_referenced(svc, ws)
    slugs = knowledge_slugs(ws, registered, referenced)

    ks = get_knowledge_service(svc._system_app)
    if ks is None:
        return {}

    result: Dict[str, List[str]] = {}
    for slug in sorted(slugs):
        try:
            vault = await ks.get_vault(slug)
            sub = await vault.graph_query()
        except Exception:  # noqa: BLE001
            continue
        names = set()
        for ep in list(sub.nodes or []):
            if ep and not ep.startswith(("doc:", "verbat:")):
                names.add(ep)
        for e in sub.edges:
            for ep in (e.subject, e.object):
                if ep and not ep.startswith(("doc:", "verbat:")):
                    names.add(ep)
        if names:
            result[slug] = sorted(names)
    return result


async def entity_graph_context(
    svc: Any, slug_entities: Dict[str, List[str]]
) -> Dict[str, Dict[str, str]]:
    """实体 → 图上下文证据(一跳关联 + 来源文档片段),对齐/检索共用。

    对每个实体 vault.graph_query 一跳:收集邻居实体名(消歧)与边的
    source_verbat_id,反查原文片段(业务含义证据主体)。**纯图查询
    + 文档读取,零 LLM**;全部 best-effort——空间不可达/实体无图/
    读文失败都降级为无上下文,不阻塞对齐与检索主流程。
    """
    from .alignment import fold_context

    ks = get_knowledge_service(svc._system_app)
    if ks is None:
        return {}

    out: Dict[str, Dict[str, str]] = {}
    for slug, names in slug_entities.items():
        try:
            vault = await ks.get_vault(slug)
        except Exception:  # noqa: BLE001
            continue
        for name in names:
            try:
                sub = await vault.graph_query(name, hop=1)
            except Exception:  # noqa: BLE001
                continue
            neighbors: List[str] = []
            verbat_ids: List[str] = []
            for e in sub.edges:
                for ep in (e.subject, e.object):
                    if (
                        ep
                        and ep != name
                        and not ep.startswith(("doc:", "verbat:"))
                        and ep not in neighbors
                    ):
                        neighbors.append(ep)
                vid = getattr(e, "source_verbat_id", None)
                if vid and vid not in verbat_ids:
                    verbat_ids.append(vid)
            snippets: List[str] = []
            for vid in verbat_ids[:2]:
                try:
                    v = await vault.verbat_get(vid)
                except Exception:  # noqa: BLE001
                    continue
                text = str(
                    getattr(v, "content", None) or getattr(v, "text", None) or ""
                ).strip()
                if text:
                    snippets.append(text)
            ctx = fold_context(neighbors, snippets)
            if ctx:
                out.setdefault(slug, {})[name] = ctx
    return out
