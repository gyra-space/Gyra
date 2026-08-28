"""资产全景图测试:边投影纯函数 + 写时物化 + graph() 实时投影与三类节点。

设计要点:
- project_edges:幂等纯函数,返回 (edges, asset_refs)——对象→对象边
  无条件、对象→资产边一律产出(稳定 id asset:<kind>:<ref_id>,不依赖登记)
- _refresh_edges:只物化对象→对象边进边表(资产 ref_id 可达 256 字符,
  超边表 String(128))
- graph():查询时实时投影全部边——存量数据冷启动即有连线;未登记的
  被引用资产生成虚拟节点(status=unregistered)
- _knowledge_subgraph:verbat 端点映射到稳定资产节点 id(与 claim 的
  ref 边同节点,三层连通);空间来源不依赖登记(派生 docs-<code>)
- 语义对齐:aligns_to 边从 semantic_alignment 表(LLM 推理产出 +
  人工确认)投影;EntityAligner._validate 是 LLM 幻觉防护闸门
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from gyra_serve.ecp.service.alignment import EntityAligner
from gyra_serve.ecp.service.graph_projection import (
    ALIGNMENT_EDGE,
    align_key,
    project_edges,
)
from gyra_serve.ecp.service.service import Service


# --------------------------------------------------------------- 纯函数投影
class TestProjectEdges:
    def test_metric_belongs_to_entity(self):
        edges, refs = project_edges(
            "metric", {"entity": "ent.order", "expression": "SUM(F1)"}
        )
        assert edges == [{"edge_type": "belongs_to", "dst": "ent.order"}]
        assert refs == []

    def test_relation_joins_both_endpoints(self):
        edges, _ = project_edges(
            "relation", {"from": "ent.order", "to": "ent.store"}
        )
        assert {e["dst"] for e in edges} == {"ent.order", "ent.store"}
        assert all(e["edge_type"] == "joins" for e in edges)

    def test_entity_binding_edge_regardless_of_registration(self):
        """资产边不依赖登记:datasource_id 引用一律出稳定 id 的边。"""
        edges, refs = project_edges(
            "entity",
            {"binding": {"kind": "db", "table": "t1", "datasource_id": 3}},
        )
        assert edges == [{"edge_type": "binding", "dst": "asset:db:3"}]
        assert refs == [("db", "3")]

    def test_claim_ref_edge_to_document_asset(self):
        edges, refs = project_edges(
            "claim",
            {
                "text": "退货率上限 5%",
                "binding": {"kind": "doc", "space": "docs-ws1", "doc_id": "v_abc"},
                "source_quote": "退货率上限 5%",
            },
        )
        assert edges == [{"edge_type": "ref", "dst": "asset:document:docs-ws1:v_abc"}]
        assert refs == [("document", "docs-ws1:v_abc")]

    def test_doc_id_with_verbat_prefix_normalized(self):
        edges, refs = project_edges(
            "claim", {"binding": {"space": "s", "doc_id": "verbat:v_1"}}
        )
        assert edges == [{"edge_type": "ref", "dst": "asset:document:s:v_1"}]
        assert refs == [("document", "s:v_1")]

    def test_dimension_entity_optional(self):
        assert project_edges("dimension", {"column": "c"}) == ([], [])
        assert project_edges("dimension", {"column": "c", "entity": "ent.a"}) == (
            [{"edge_type": "belongs_to", "dst": "ent.a"}],
            [],
        )


class TestAlignKey:
    def test_normalizes_case_punct_keeps_cjk(self):
        """归一键:小写、去标点空白,中文保留——仅作索引键,非对齐决策。"""
        assert align_key("风控模型A") == "风控模型a"
        assert align_key("  Sales-Order! ") == "salesorder"
        assert align_key(None) == ""


# --------------------------------------------------------------- 写时物化
def _svc(assets, objects):
    svc = Service.__new__(Service)
    svc._asset_dao = MagicMock()
    svc._asset_dao.list.return_value = assets
    svc._object_dao = MagicMock()
    svc._object_dao.list_latest.return_value = SimpleNamespace(items=objects)
    svc._edge_dao = MagicMock()
    svc._oplog_dao = MagicMock()
    return svc


def _asset(pk, kind, ref_id, name=None):
    return SimpleNamespace(
        id=pk, kind=kind, ref_id=ref_id, status="active",
        ref_meta={"name": name} if name else {},
    )


class TestRefreshEdges:
    def test_materializes_object_edges_only(self):
        """物化只保留对象→对象边;资产边不进边表(ref_id 超长风险)。"""
        svc = _svc(assets=[], objects=[])
        vo = SimpleNamespace(
            id="ent.order", obj_type="entity", version=1, status="proposed",
            payload={"binding": {"kind": "db", "table": "t1", "datasource_id": 3}},
        )
        svc._refresh_edges(vo, "default")
        # entity 只有资产边 → 边表写空列表
        svc._edge_dao.replace_out_edges.assert_called_once_with(
            "ent.order", "default", 1, []
        )

    def test_metric_object_edge_materialized(self):
        svc = _svc(assets=[], objects=[])
        vo = SimpleNamespace(
            id="mtr.sales", obj_type="metric", version=1, status="proposed",
            payload={"entity": "ent.order", "expression": "SUM(F1)"},
        )
        svc._refresh_edges(vo, "default")
        svc._edge_dao.replace_out_edges.assert_called_once_with(
            "mtr.sales", "default", 1,
            [{"edge_type": "belongs_to", "dst": "ent.order"}],
        )

    def test_rebuild_counts_object_edges_only(self):
        objects = [
            SimpleNamespace(
                id="mtr.sales", obj_type="metric", version=2,
                payload={"entity": "ent.order", "expression": "SUM(F1)"},
            ),
            SimpleNamespace(
                id="ent.order", obj_type="entity", version=1,
                payload={"binding": {"datasource_id": 3}},
            ),
        ]
        svc = _svc(assets=[], objects=objects)
        result = svc.rebuild_edges("default")
        assert result["objects"] == 2
        assert result["edges"] == 1  # 只有 belongs_to;binding 是资产边不物化


# --------------------------------------------------------------- graph 视图
class TestGraphView:
    def test_graph_projects_edges_live_with_virtual_assets(self):
        """存量对象零物化冷启动:graph() 实时投影,未登记资产出虚拟节点。"""
        import asyncio

        objects = [
            SimpleNamespace(
                id="ent.order", obj_type="entity", name="订单",
                status="confirmed", version=1,
                payload={"binding": {"datasource_id": 3}},
            ),
            SimpleNamespace(
                id="mtr.sales", obj_type="metric", name="销售额",
                status="confirmed", version=1,
                payload={"entity": "ent.order", "expression": "SUM(F1)"},
            ),
        ]
        # db 资产未登记 → 虚拟资产节点
        svc = _svc(assets=[], objects=objects)

        vo = asyncio.run(svc.graph("default"))
        ids = {n.id for n in vo.nodes}
        assert ids == {"ent.order", "mtr.sales", "asset:db:3"}
        virtual = next(n for n in vo.nodes if n.id == "asset:db:3")
        assert virtual.node_kind == "asset"
        assert virtual.status == "unregistered"
        assert virtual.obj_type == "db"
        assert sorted((l.source, l.edge_type, l.target) for l in vo.links) == [
            ("ent.order", "binding", "asset:db:3"),
            ("mtr.sales", "belongs_to", "ent.order"),
        ]

    def test_graph_enriches_registered_assets(self):
        import asyncio

        objects = [
            SimpleNamespace(
                id="ent.order", obj_type="entity", name="订单",
                status="confirmed", version=1,
                payload={"binding": {"datasource_id": 3}},
            )
        ]
        svc = _svc(
            assets=[_asset(7, "db", "3", "销售库")], objects=objects
        )
        vo = asyncio.run(svc.graph("default"))
        asset_node = next(n for n in vo.nodes if n.id == "asset:db:3")
        assert asset_node.status == "active"
        assert asset_node.name == "销售库"
        assert ("ent.order", "binding", "asset:db:3") in [
            (l.source, l.edge_type, l.target) for l in vo.links
        ]

    def test_knowledge_endpoint_mapping_prefers_document_asset(self):
        """verbat 端点映射到稳定资产节点 id——与 claim 的 ref 边同节点。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        # document 既已登记又被 claim 引用,两种来源都应映射到同一节点
        registered = {("document", "docs-ws1:v_abc"): _asset(9, "document", "docs-ws1:v_abc")}
        referenced = {("document", "docs-ws1:v_abc"): None}

        edge = SimpleNamespace(subject="doc:wiki_1", predicate="derived-from",
                               object="verbat:v_abc")
        sub = SimpleNamespace(nodes=[], edges=[edge], root=None)
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        async def get_vault(slug):
            if slug == "docs-ws1":
                return vault
            raise KeyError(slug)  # 其他空间不存在 → 跳过

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        kn_nodes, links = asyncio.run(
            svc._knowledge_subgraph("ecp_ws1", registered, referenced)
        )
        assert len(kn_nodes) == 1  # doc:wiki_1(另一端映射到资产节点)
        assert [(l.source, l.target, l.edge_type) for l in links] == [
            ("kn:docs-ws1:doc:wiki_1", "asset:document:docs-ws1:v_abc",
             "derived-from")
        ]

    def test_knowledge_slug_derived_from_workspace_id(self):
        """workspace_id=ecp_<code> → 聚合 docs-<code>,不依赖资产登记。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        edge = SimpleNamespace(subject="doc:w1", predicate="about",
                               object="doc:w2")
        sub = SimpleNamespace(nodes=[], edges=[edge], root=None)
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        seen_slugs = []

        async def get_vault(slug):
            seen_slugs.append(slug)
            if slug == "docs-demo":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        kn_nodes, links = asyncio.run(
            svc._knowledge_subgraph("ecp_demo", {}, {})
        )
        assert "docs-demo" in seen_slugs
        assert len(kn_nodes) == 2
        assert len(links) == 1

    def test_unknown_verbat_endpoint_degrades_to_kn(self):
        """未被引用/登记的 verbatim → kn 节点(知识层),不冒充资产。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        edge = SimpleNamespace(subject="doc:wiki_1", predicate="derived-from",
                               object="verbat:v_x")
        sub = SimpleNamespace(nodes=[], edges=[edge], root=None)
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        async def get_vault(slug):
            if slug == "docs-ws1":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        kn_nodes, links = asyncio.run(
            svc._knowledge_subgraph("ecp_ws1", {}, {})
        )
        targets = {n.id for n in kn_nodes}
        assert targets == {"kn:docs-ws1:doc:wiki_1", "kn:docs-ws1:verbat:v_x"}

    def test_bare_entity_endpoint_maps_to_kn_entity_node(self):
        """实体名等裸标识端点 → kn 实体节点(软知识语义层进全景图)。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        edge = SimpleNamespace(subject="doc:wiki_1", predicate="about",
                               object="风控模型A")
        sub = SimpleNamespace(nodes=[], edges=[edge], root=None)
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        async def get_vault(slug):
            if slug == "docs-ws1":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        kn_nodes, links = asyncio.run(
            svc._knowledge_subgraph("ecp_ws1", {}, {})
        )
        by_id = {n.id: n for n in kn_nodes}
        assert "kn:docs-ws1:entity:风控模型A" in by_id
        ent = by_id["kn:docs-ws1:entity:风控模型A"]
        assert ent.obj_type == "entity"
        assert ent.node_kind == "kn"
        assert [(l.source, l.target, l.edge_type) for l in links] == [
            ("kn:docs-ws1:doc:wiki_1", "kn:docs-ws1:entity:风控模型A", "about")
        ]

    def test_alignment_edges_projected_from_index(self):
        """裸实体端点按 (slug, align_key) 查对齐索引 → aligns_to 边携带状态。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        edge = SimpleNamespace(subject="doc:wiki_1", predicate="about",
                               object="风控模型A")
        sub = SimpleNamespace(nodes=[], edges=[edge], root=None)
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        async def get_vault(slug):
            if slug == "docs-ws1":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        # LLM 推理 + 人工确认后固化在对齐表的数据(此处模拟投影输入)
        index = {
            ("docs-ws1", align_key("风控模型A")): [
                ("ent.risk", "confirmed"),
                ("ent.deal", "proposed"),
            ]
        }
        kn_nodes, links = asyncio.run(
            svc._knowledge_subgraph("ecp_ws1", {}, {}, index)
        )
        align = [l for l in links if l.edge_type == ALIGNMENT_EDGE]
        assert sorted((l.source, l.target, l.status) for l in align) == [
            ("kn:docs-ws1:entity:风控模型A", "ent.deal", "proposed"),
            ("kn:docs-ws1:entity:风控模型A", "ent.risk", "confirmed"),
        ]

    def test_graph_projects_alignment_from_dao(self):
        """graph() 端到端:从对齐 DAO 构建索引,kn 实体连出 aligns_to 边。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = _svc(assets=[], objects=[])
        svc._alignment_dao = MagicMock()
        svc._alignment_dao.decisions.return_value = [
            SimpleNamespace(slug="ecp-default", entity_name="风控模型A",
                            object_id="ent.risk", status="confirmed"),
        ]
        edge = SimpleNamespace(subject="doc:wiki_1", predicate="about",
                               object="风控模型A")
        sub = SimpleNamespace(nodes=[], edges=[edge], root=None)
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        async def get_vault(slug):
            if slug == "ecp-default":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        vo = asyncio.run(svc.graph("default"))
        svc._alignment_dao.decisions.assert_called_once_with("default")
        align = [l for l in vo.links if l.edge_type == ALIGNMENT_EDGE]
        assert [(l.source, l.target, l.status) for l in align] == [
            ("kn:ecp-default:entity:风控模型A", "ent.risk", "confirmed"),
        ]

    def test_entity_graph_context_collects_neighbors_and_snippets(self):
        """图上下文收集:一跳邻居 + source_verbat_id 反查原文片段。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        edge = SimpleNamespace(
            subject="销售单据", predicate="mentions", object="doc:wiki_1",
            source_verbat_id="verbat:v1",
        )
        vault = MagicMock()
        vault.graph_query = MagicMock(
            return_value=_async_ret(
                SimpleNamespace(
                    nodes=["销售单据", "doc:wiki_1"], edges=[edge], root="销售单据"
                )
            )
        )
        vault.verbat_get = MagicMock(
            return_value=_async_ret(
                SimpleNamespace(content="销售单据指客户下单后生成的结算凭证。")
            )
        )

        async def get_vault(slug):
            if slug == "docs-ws1":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        ctx = asyncio.run(svc._entity_graph_context({"docs-ws1": ["销售单据"]}))
        vault.graph_query.assert_called_once_with("销售单据", hop=1)
        assert ctx == {
            "docs-ws1": {
                "销售单据": "关联文档片段:销售单据指客户下单后生成的结算凭证。"
            }
        }

    def test_entity_graph_context_degrades_silently(self):
        """空间不可达 → 空上下文,不阻塞对齐/检索主流程。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)

        async def get_vault(slug):
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks
        assert asyncio.run(svc._entity_graph_context({"nope": ["x"]})) == {}

    def test_graph_entity_search_attaches_context(self):
        """entity 检索命中 kn 实体 → vo.entity_context 附图上下文证据。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = _svc(assets=[], objects=[])
        svc._alignment_dao = MagicMock()
        svc._alignment_dao.decisions.return_value = []

        full_sub = SimpleNamespace(
            nodes=["doc:wiki_1", "风控模型A"],
            edges=[
                SimpleNamespace(
                    subject="doc:wiki_1", predicate="about", object="风控模型A",
                    source_verbat_id=None,
                )
            ],
            root=None,
        )
        one_hop = SimpleNamespace(
            nodes=["doc:wiki_1", "风控模型A"],
            edges=[
                SimpleNamespace(
                    subject="doc:wiki_1", predicate="about", object="风控模型A",
                    source_verbat_id="verbat:v9",
                )
            ],
            root="风控模型A",
        )

        def gq(entity=None, predicate=None, hop=1, include_invalid=False):
            # _knowledge_subgraph 全图无参调用;上下文收集按实体一跳
            return _async_ret(one_hop if entity == "风控模型A" else full_sub)

        vault = MagicMock()
        vault.graph_query = MagicMock(side_effect=gq)
        vault.verbat_get = MagicMock(
            return_value=_async_ret(
                SimpleNamespace(content="风控模型A 用于信贷审批额度测算。")
            )
        )

        async def get_vault(slug):
            if slug == "ecp-default":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        vo = asyncio.run(svc.graph("default", entity="风控模型A"))
        assert vo.entity_context and "风控模型A" in vo.entity_context
        assert "风控模型A 用于信贷审批额度测算。" in vo.entity_context["风控模型A"]

    def test_isolated_nodes_included_in_panorama(self):
        """孤立节点(不在任何边上的 doc/实体)也成为 kn 节点。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        # graph_query 返回孤立节点(无任何边)
        sub = SimpleNamespace(
            nodes=["doc:orphan_1", "verbat:v_lone", "孤立实体"],
            edges=[], root=None,
        )
        vault = MagicMock()
        vault.graph_query = MagicMock(return_value=_async_ret(sub))

        async def get_vault(slug):
            if slug == "docs-ws1":
                return vault
            raise KeyError(slug)

        ks = MagicMock()
        ks.get_vault = get_vault
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks

        kn_nodes, links = asyncio.run(
            svc._knowledge_subgraph("ecp_ws1", {}, {})
        )
        ids = {n.id for n in kn_nodes}
        assert ids == {
            "kn:docs-ws1:doc:orphan_1",
            "kn:docs-ws1:verbat:v_lone",
            "kn:docs-ws1:entity:孤立实体",
        }
        assert links == []


class _async_ret:
    """极简 awaitable,让 MagicMock 返回可 await 的值。"""

    def __init__(self, value):
        self._value = value

    def __await__(self):
        async def _coro():
            return self._value

        return _coro().__await__()

# ------------------------------------------------------- LLM 幻觉防护闸门
class TestEntityAlignerValidate:
    """EntityAligner._validate:LLM 输出的确定性校验闸门。

    与提案侧 quote 子串校验同哲学——LLM 可能幻觉,固化前必须过代码
    校验:object_id 白名单、entity 归属、confidence 截断。
    """

    ENTITIES = ["风控模型A", "销售单据"]
    OBJECT_IDS = {"ent.risk", "ent.order"}

    def test_valid_candidates_pass(self):
        raw = (
            '[{"entity_name": "风控模型A", "object_id": "ent.risk",'
            ' "confidence": 0.9, "rationale": "同指风控业务对象"}]'
        )
        out = EntityAligner()._validate(raw, self.ENTITIES, self.OBJECT_IDS)
        assert out == [
            {
                "entity_name": "风控模型A",
                "object_id": "ent.risk",
                "confidence": 0.9,
                "rationale": "同指风控业务对象",
            }
        ]

    def test_markdown_fenced_output_parsed(self):
        raw = (
            "```json\n"
            '[{"entity_name": "销售单据", "object_id": "ent.order",'
            ' "confidence": 1, "rationale": "业务俗称"}]\n'
            "```"
        )
        out = EntityAligner()._validate(raw, self.ENTITIES, self.OBJECT_IDS)
        assert len(out) == 1
        assert out[0]["confidence"] == 1.0

    def test_hallucinated_object_id_filtered(self):
        raw = (
            '[{"entity_name": "风控模型A", "object_id": "ent.nope",'
            ' "confidence": 0.9, "rationale": "幻觉 id"}]'
        )
        assert EntityAligner()._validate(raw, self.ENTITIES, self.OBJECT_IDS) == []

    def test_unknown_entity_filtered(self):
        raw = (
            '[{"entity_name": "不在批次的实体", "object_id": "ent.risk",'
            ' "confidence": 0.9, "rationale": ""}]'
        )
        assert EntityAligner()._validate(raw, self.ENTITIES, self.OBJECT_IDS) == []

    def test_confidence_clamped(self):
        raw = (
            '[{"entity_name": "风控模型A", "object_id": "ent.risk",'
            ' "confidence": 7, "rationale": ""},'
            '{"entity_name": "风控模型A", "object_id": "ent.risk",'
            ' "confidence": 0, "rationale": ""},'
            '{"entity_name": "风控模型A", "object_id": "ent.risk",'
            ' "confidence": "bad", "rationale": ""}]'
        )
        out = EntityAligner()._validate(raw, self.ENTITIES, self.OBJECT_IDS)
        assert [c["confidence"] for c in out] == [1.0, 0.01, 0.5]

    def test_non_array_output_rejected_with_error(self):
        al = EntityAligner()
        assert al._validate('{"oops": 1}', self.ENTITIES, self.OBJECT_IDS) == []
        assert al.last_error == "LLM 输出不是 JSON 数组"

    def test_none_raw_keeps_existing_error(self):
        """raw=None 是 LLM 调用失败场景:保留调用期 last_error 不覆盖。"""
        al = EntityAligner()
        al.last_error = "LLM 调用失败: timeout"
        assert al._validate(None, self.ENTITIES, self.OBJECT_IDS) == []
        assert al.last_error == "LLM 调用失败: timeout"

# ------------------------------------------------- 图上下文证据(prompt 输入增强)
class TestFoldContext:
    def test_folds_snippets_and_neighbors(self):
        """证据主体是文档片段,邻居实体名辅助消歧。"""
        from gyra_serve.ecp.service.alignment import fold_context

        ctx = fold_context(
            ["订单", "客户"], ["销售单据指客户下单后生成的结算凭证。"]
        )
        assert ctx.startswith("关联文档片段:销售单据指客户下单后生成的结算凭证。")
        assert ctx.endswith("关联实体:订单、客户")

    def test_truncates_snippets_and_limits_neighbors(self):
        """片段截 400 字,邻居最多 5 个——单批 20 实体的 prompt 体量可控。"""
        from gyra_serve.ecp.service.alignment import fold_context

        ctx = fold_context(
            list("abcdef"), ["x" * 500, "y" * 500]
        )
        assert "x" * 400 in ctx and "y" * 400 in ctx
        neighbor_part = ctx.split("关联实体:")[1]
        assert neighbor_part == "a、b、c、d、e"

    def test_empty_inputs(self):
        from gyra_serve.ecp.service.alignment import fold_context

        assert fold_context([], []) == ""


class TestAlignBatchContext:
    def test_prompt_includes_entity_context(self):
        """带图上下文时 prompt 逐实体附带证据;无上下文实体保持裸名。"""
        import asyncio

        al = EntityAligner()
        captured = {}

        async def fake_call(prompt, max_tokens=4000):
            captured["prompt"] = prompt
            return "[]"

        al._call_llm = fake_call
        obj = SimpleNamespace(
            id="ent.order", obj_type="entity", name="订单",
            payload={"aliases": ["销售单据"], "description": "客户订单"},
        )
        asyncio.run(
            al.align_batch(
                ["销售单据", "风控模型A"],
                [obj],
                context={"销售单据": "关联文档片段:销售单据指订单凭证。"},
            )
        )
        prompt = captured["prompt"]
        assert "- 销售单据(上下文:关联文档片段:销售单据指订单凭证。)" in prompt
        assert "- 风控模型A\n" in prompt

    def test_context_optional(self):
        """不传 context 时 prompt 与旧版一致(裸实体名列表)。"""
        import asyncio

        al = EntityAligner()
        captured = {}

        async def fake_call(prompt, max_tokens=4000):
            captured["prompt"] = prompt
            return "[]"

        al._call_llm = fake_call
        obj = SimpleNamespace(id="ent.a", obj_type="entity", name="A", payload={})
        asyncio.run(al.align_batch(["实体甲"], [obj]))
        assert "## 知识实体\n- 实体甲\n\n## 语义层对象" in captured["prompt"]
