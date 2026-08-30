"""ECP 资产全景图:写时物化 + 查询时实时投影 + 知识层子图聚合。

- 写时物化(_refresh_edges/rebuild_edges):对象→对象边进边表,服务
  Agent 图遍历/lint 影响分析;边表不是 source of truth,可全量重建
- 查询时实时投影(graph):硬层对象 + 资产节点 + 知识层 kn 节点三类,
  边永远反映当前状态,不依赖物化边表是否跟上
- 知识层聚合(_knowledge_subgraph):vault L2 图查询时聚合,零同步任务

GraphOps 是无状态协作者,经 svc 门面访问 DAO 与 system_app。
"""

import logging
from typing import Any, Dict, List, Optional

from ..api.schemas import GraphLinkVO, GraphNodeVO, GraphVO, SemanticObjectVO
from .graph_projection import (
    ALIGNMENT_EDGE,
    align_key,
    asset_node_id,
    project_edges,
)
from .knowledge_bridge import (
    entity_graph_context,
    get_knowledge_service,
    knowledge_slugs,
)

logger = logging.getLogger(__name__)


class GraphOps:
    """图谱协作者(无状态;经 svc 门面访问 DAO 与 system_app)。"""

    def __init__(self, svc: Any):
        self._svc = svc

    # -------------------------------------------------------- 写时物化
    def refresh_edges(self, vo: SemanticObjectVO, ws: str) -> None:
        """写时物化:重算该对象的**对象→对象**出边进边表。

        挂在所有产生新版本的写路径上(propose / confirm / normalize_confirmed),
        replace_out_edges 删旧插新,天然增量;reject/deprecate 只改 status,
        边不动(状态由节点渲染)。资产边不进物化表(ref_id 可达 256 字符,
        超出边表 String(128);资产边只服务可视化,由 graph() 实时投影)。
        Best-effort:投影失败不阻塞业务写入(边表不是 source of truth,
        rebuild_edges 可全量重建)。
        """
        try:
            edges, _refs = project_edges(vo.obj_type, vo.payload or {})
            obj_edges = [
                e for e in edges if not e["dst"].startswith("asset:")
            ]
            self._svc._edge_dao.replace_out_edges(vo.id, ws, vo.version, obj_edges)
        except Exception:  # noqa: BLE001
            logger.exception("edge projection failed for %s@v%s", vo.id, vo.version)

    def rebuild_edges(self, workspace_id: Optional[str] = None) -> dict:
        """幂等全量重建 workspace 的物化边投影(对象→对象边)。

        物化投影不是 source of truth:边永远可以从对象 payload 重算,
        丢了大不了重建。投影规则升级后一次调用即可对存量生效。
        (graph() 已改为查询时实时投影,本方法服务边表消费方——
        Agent 图遍历 / lint 影响分析。)
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        total_edges = 0
        objects = 0
        page = 1
        while True:
            result = svc._object_dao.list_latest(
                workspace_id=ws, page=page, page_size=500
            )
            if not result.items:
                break
            for o in result.items:
                edges, _refs = project_edges(o.obj_type, o.payload or {})
                obj_edges = [
                    e for e in edges if not e["dst"].startswith("asset:")
                ]
                svc._edge_dao.replace_out_edges(o.id, ws, o.version, obj_edges)
                total_edges += len(obj_edges)
                objects += 1
            if len(result.items) < 500:
                break
            page += 1
        svc._oplog_dao.append(
            "graph_rebuild", ws, {"objects": objects, "edges": total_edges}
        )
        return {"workspace_id": ws, "objects": objects, "edges": total_edges}

    # ---------------------------------------------------- 知识层子图聚合
    async def knowledge_subgraph(
        self,
        ws: str,
        registered: Dict[tuple, Any],
        referenced: Dict[tuple, None],
        alignment_index: Optional[Dict[tuple, List[tuple]]] = None,
    ) -> tuple[List[GraphNodeVO], List[GraphLinkVO]]:
        """聚合知识空间 L2 图(wiki/doc/跨文档实体)为 kn 节点与边。

        查询时聚合路线:不落边表、零同步任务——vault 的边自带 valid_to
        时间有效性,文档重 ingest 旧边自动失效,聚合永远拿到当前有效图。

        端点映射(三层连通的关键):

        - ``verbat:<id>`` → 若 ``{slug}:{id}`` 是已知资产(已登记或被
          claim 引用),映射到**稳定资产节点 id**(与 claim 的 ref 边
          指向同一节点——资源层与知识层在此连通);否则降级为 kn 节点。
        - ``doc:<id>`` → kn 节点(wiki 页)。
        - 其他端点(实体名等裸标识) → kn 实体节点(``kn:<slug>:entity:<name>``)。

        知识实体 → 硬层对象的对齐:从 ``alignment_index``(语义对齐表
        投影,键 ``(slug, align_key(entity_name))``,由 graph() 从
        semantic_alignment 表构建)读 ``aligns_to`` 边——对齐关系是
        LLM 推理产出后固化入库的数据,查询时零 LLM 依赖;
        GraphLinkVO.status 携带 proposed/confirmed 供前端区分展示。

        节点来自 ``graph_query().nodes ∪ edges 端点``:孤立文档/实体
        (没有任何 L2 边)也会成为 kn 节点——刚 ingest 完还没建边的
        空间在全景图里立即可见。

        聚合空间来源(不依赖资产登记完整性):ECP 软层(ecp-<ws>) +
        已登记 space/document 资产 + 被 claim 引用的空间 + 场景空间
        派生的文档空间(workspace_id 形如 ecp_<code> → docs-<code>)。
        """
        alignment_index = alignment_index or {}
        slugs = knowledge_slugs(ws, registered, referenced)

        known_docs = set(registered) | set(referenced)
        nodes: Dict[str, GraphNodeVO] = {}
        links: List[GraphLinkVO] = []
        seen: set = set()

        ks = get_knowledge_service(self._svc._system_app)
        if ks is None:
            return [], []

        for slug in sorted(slugs):
            try:
                vault = await ks.get_vault(slug)
                sub = await vault.graph_query()
            except Exception:  # noqa: BLE001
                continue  # 空间不存在或暂不可达:跳过,不阻塞全景图

            def _map(endpoint: str) -> Optional[str]:
                if not endpoint:
                    return None
                if endpoint.startswith("verbat:"):
                    vid = endpoint.split(":", 1)[1]
                    if ("document", f"{slug}:{vid}") in known_docs:
                        return asset_node_id("document", f"{slug}:{vid}")
                if endpoint.startswith(("doc:", "verbat:")):
                    ep_type, ep_id = endpoint.split(":", 1)
                    kn_id = f"kn:{slug}:{endpoint}"
                    if kn_id not in nodes:
                        nodes[kn_id] = GraphNodeVO(
                            id=kn_id,
                            obj_type="wiki" if ep_type == "doc" else "verbat",
                            name=ep_id,
                            status="confirmed",
                            node_kind="kn",
                        )
                    return kn_id
                # 实体名等裸标识端点(如 curation 的实体名) → kn 实体节点
                kn_id = f"kn:{slug}:entity:{endpoint}"
                if kn_id not in nodes:
                    nodes[kn_id] = GraphNodeVO(
                        id=kn_id,
                        obj_type="entity",
                        name=endpoint,
                        status="confirmed",
                        node_kind="kn",
                    )
                    # 语义对齐边:LLM 推理产出并固化在 semantic_alignment
                    # 表的数据,此处按 (slug, 归一实体名) 查表投影
                    for obj_id, a_status in alignment_index.get(
                        (slug, align_key(endpoint)), ()
                    ):
                        links.append(
                            GraphLinkVO(
                                source=kn_id,
                                target=obj_id,
                                edge_type=ALIGNMENT_EDGE,
                                status=a_status,
                            )
                        )
                return kn_id

            # 孤立节点(不在任何边上的 doc/verbat/实体)也纳入全景图
            for n in sub.nodes or []:
                _map(n)

            for e in sub.edges:
                src = _map(e.subject)
                dst = _map(e.object)
                if not src or not dst or src == dst:
                    continue
                key = (src, e.predicate, dst)
                if key in seen:
                    continue
                seen.add(key)
                links.append(
                    GraphLinkVO(source=src, target=dst, edge_type=e.predicate)
                )
        return list(nodes.values()), links

    # ------------------------------------------------------------ 全景图
    async def graph(
        self, workspace_id: Optional[str] = None, entity: Optional[str] = None
    ) -> GraphVO:
        """Asset-panorama graph view for one workspace.

        边**查询时实时投影**(纯函数,单空间 ≤ 千对象成本可忽略)——图
        永远反映当前对象/资产状态,不依赖物化边表是否跟上(存量数据
        冷启动也有连线)。物化边表只服务 Agent 图遍历/lint。

        节点三类(实时查询,零同步):硬层对象 + 资产节点(已登记 enrich
        名称/状态,被引用未登记 → 虚拟节点 status=unregistered) +
        知识层 kn 节点(L2 图聚合涌现)。kn 实体节点与硬层对象之间按
        semantic_alignment 表(LLM 推理固化 + 人工确认)投影
        ``aligns_to`` 对齐边,status 区分 proposed/confirmed。

        ``entity`` 给定时返回检索视图:命中节点(id/name/别名归一匹配)
        及其一跳邻域——一次调用同时取回「硬层对象 ↔ 对齐的 kn 实体 ↔
        提及它的 wiki 文档」。
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        objects = svc._object_dao.list_latest(
            workspace_id=ws, page=1, page_size=1000
        ).items

        # ---- 语义对齐索引:LLM 推理产出 + 人工确认后固化的对齐数据,
        #      键 (slug, align_key(entity_name)) → [(对象 id, 状态)]。
        #      rejected 不投影;这里只读表,不做任何语义判断。
        alignment_index: Dict[tuple, List[tuple]] = {}
        try:
            for d in svc._alignment_dao.decisions(ws):
                key = align_key(d.entity_name)
                if key:
                    alignment_index.setdefault((d.slug, key), []).append(
                        (d.object_id, d.status)
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ecp] build alignment index failed: {e}")

        # ---- 检索索引:归一(name/aliases)→ 对象 id 列表,仅供
        #      entity 检索视图命中,不参与连边。
        semantic_index: Dict[str, List[str]] = {}
        for o in objects:
            payload = o.payload or {}
            for nm in [o.name, *(payload.get("aliases") or [])]:
                key = align_key(nm)
                if key:
                    bucket = semantic_index.setdefault(key, [])
                    if o.id not in bucket:
                        bucket.append(o.id)

        # ---- 实时投影:对象→对象边 + 对象→资产边(稳定资产节点 id)
        links: List[GraphLinkVO] = []
        seen: set = set()
        referenced: Dict[tuple, None] = {}
        for o in objects:
            edges, refs = project_edges(o.obj_type, o.payload or {})
            for key in refs:
                referenced[key] = None
            for e in edges:
                key = (o.id, e["edge_type"], e["dst"])
                if key in seen:
                    continue
                seen.add(key)
                links.append(
                    GraphLinkVO(
                        source=o.id, target=e["dst"], edge_type=e["edge_type"]
                    )
                )

        # ---- 资产节点:已登记(enrich) ∪ 被引用(未登记 → 虚拟节点)
        registered = {
            (a.kind, a.ref_id): a for a in svc._asset_dao.list(ws)
        }
        nodes = [
            GraphNodeVO(
                id=o.id, obj_type=o.obj_type, name=o.name,
                status=o.status, version=o.version,
            )
            for o in objects
        ]
        for key in {**registered, **referenced}:
            kind, ref_id = key
            a = registered.get(key)
            nodes.append(
                GraphNodeVO(
                    id=asset_node_id(kind, ref_id),
                    obj_type=kind,
                    name=(
                        (a.ref_meta or {}).get("name") or ref_id if a else ref_id
                    ),
                    status=(a.status or "active") if a else "unregistered",
                    version=0,
                    node_kind="asset",
                )
            )

        # ---- knowledge 层聚合(kn 节点 + L2 边 + aligns_to 对齐边),
        #      best-effort 不阻塞
        try:
            kn_nodes, kn_links = await self.knowledge_subgraph(
                ws, registered, referenced, alignment_index
            )
            nodes.extend(kn_nodes)
            for lk in kn_links:
                key = (lk.source, lk.edge_type, lk.target)
                if key not in seen:
                    seen.add(key)
                    links.append(lk)
        except Exception:  # noqa: BLE001
            pass

        vo = GraphVO(nodes=nodes, links=links)
        if entity:
            vo = self.focus(vo, entity, semantic_index)
            # 检索增强:命中的 kn 实体附图上下文证据(一跳关联 + 来源
            # 文档片段),与对齐推理共用同一套收集——纯图查询+文档读取,
            # 零 LLM,前端详情面板与下游 LLM 复用同一份证据。
            hits = [
                (n.id, n.name)
                for n in vo.nodes
                if n.obj_type == "entity"
                and n.node_kind == "kn"
                and (
                    n.id == entity
                    or (n.name and align_key(n.name) == align_key(entity))
                )
            ]
            slug_names: Dict[str, List[str]] = {}
            for nid, name in hits:
                # kn:<slug>:entity:<name>(maxsplit 保实体名完整)
                parts = nid.split(":", 3)
                if len(parts) == 4 and name:
                    slug_names.setdefault(parts[1], []).append(name)
            if slug_names:
                try:
                    grouped = await entity_graph_context(svc, slug_names)
                except Exception:  # noqa: BLE001
                    grouped = {}
                flat = {k: v for m in grouped.values() for k, v in m.items()}
                if flat:
                    vo.entity_context = flat
            return vo
        return vo

    @staticmethod
    def focus(
        vo: GraphVO, entity: str, semantic_index: Dict[str, List[str]]
    ) -> GraphVO:
        """按实体检索:命中节点(id/name/别名归一匹配) + 一跳邻域。

        命中来源三路:语义索引(对象 name/aliases)、节点 id 精确匹配、
        节点 name 归一匹配(覆盖 kn/asset 节点)。邻域经 aligns_to 边
        可同时拉进对齐的另一侧(如 kn 实体 → ent.order),实现一次
        检索取回「对象 ↔ 知识实体 ↔ wiki 文档」完整关系链。
        """
        key = align_key(entity)
        matched = set(semantic_index.get(key, ()))
        for n in vo.nodes:
            if n.id == entity or (n.name and align_key(n.name) == key):
                matched.add(n.id)
        keep = set(matched)
        for lk in vo.links:
            if lk.source in matched or lk.target in matched:
                keep.add(lk.source)
                keep.add(lk.target)
        return GraphVO(
            nodes=[n for n in vo.nodes if n.id in keep],
            links=[
                lk
                for lk in vo.links
                if lk.source in keep and lk.target in keep
            ],
        )
