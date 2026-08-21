"""资产全景图测试:边投影纯函数 + 写时物化 + graph() 三类节点聚合。

设计见 docs/ECP.md v1.2(图是投影)与"空间资产全景图"方案:
- project_edges:幂等纯函数,对象→对象边无条件、对象→资产边需注册表命中
- _refresh_edges:挂在 propose/confirm 写路径,replace_out_edges 删旧插新
- graph():节点实时(对象+资产+kn)、边物化 + knowledge 查询时聚合
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from gyra_serve.ecp.service.graph_projection import project_edges
from gyra_serve.ecp.service.service import Service


# --------------------------------------------------------------- 纯函数投影
class TestProjectEdges:
    def test_metric_belongs_to_entity(self):
        edges = project_edges(
            "metric", {"entity": "ent.order", "expression": "SUM(F1)"}
        )
        assert edges == [{"edge_type": "belongs_to", "dst": "ent.order"}]

    def test_relation_jins_both_endpoints(self):
        edges = project_edges(
            "relation", {"from": "ent.order", "to": "ent.store"}
        )
        assert {e["dst"] for e in edges} == {"ent.order", "ent.store"}
        assert all(e["edge_type"] == "joins" for e in edges)

    def test_entity_binding_edge_requires_registered_asset(self):
        payload = {"binding": {"kind": "db", "table": "t1", "datasource_id": 3}}
        # 未登记 → 无资产边
        assert project_edges("entity", payload, lambda k, r: None) == []
        # 已登记 → binding 边指向资产节点
        edges = project_edges("entity", payload, lambda k, r: "asset:7" if k == "db" else None)
        assert edges == [{"edge_type": "binding", "dst": "asset:7"}]

    def test_claim_ref_edge_to_document_asset(self):
        payload = {
            "text": "退货率上限 5%",
            "binding": {"kind": "doc", "space": "docs-ws1", "doc_id": "v_abc"},
            "source_quote": "退货率上限 5%",
        }
        resolve = lambda k, r: "asset:9" if (k, r) == ("document", "docs-ws1:v_abc") else None  # noqa: E731
        assert project_edges("claim", payload, resolve) == [
            {"edge_type": "ref", "dst": "asset:9"}
        ]

    def test_doc_id_with_verbat_prefix_normalized(self):
        payload = {"binding": {"space": "s", "doc_id": "verbat:v_1"}}
        resolve = lambda k, r: "asset:1" if r == "s:v_1" else None  # noqa: E731
        assert project_edges("claim", payload, resolve) == [
            {"edge_type": "ref", "dst": "asset:1"}
        ]

    def test_no_resolver_still_yields_object_edges(self):
        """resolve 缺省时对象→对象边照常(资产边静默跳过)。"""
        assert project_edges("metric", {"entity": "ent.a"}) == [
            {"edge_type": "belongs_to", "dst": "ent.a"}
        ]

    def test_dimension_entity_optional(self):
        assert project_edges("dimension", {"column": "c"}) == []
        assert project_edges("dimension", {"column": "c", "entity": "ent.a"}) == [
            {"edge_type": "belongs_to", "dst": "ent.a"}
        ]


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
    def test_propose_hook_recomputes_out_edges(self):
        svc = _svc(
            assets=[_asset(7, "db", "3", "销售库")],
            objects=[],
        )
        vo = SimpleNamespace(
            id="ent.order", obj_type="entity", version=1, status="proposed",
            payload={"binding": {"kind": "db", "table": "t1", "datasource_id": 3}},
        )
        svc._refresh_edges(vo, "default")
        svc._edge_dao.replace_out_edges.assert_called_once_with(
            "ent.order", "default", 1,
            [{"edge_type": "binding", "dst": "asset:7"}],
        )

    def test_rebuild_is_idempotent_full_projection(self):
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
        svc = _svc(assets=[_asset(7, "db", "3")], objects=objects)
        result = svc.rebuild_edges("default")
        assert result["objects"] == 2
        assert result["edges"] == 2  # belongs_to + binding
        assert svc._edge_dao.replace_out_edges.call_count == 2


# --------------------------------------------------------------- graph 视图
class TestGraphView:
    def test_graph_merges_objects_assets_and_edges(self):
        import asyncio

        objects = [
            SimpleNamespace(
                id="ent.order", obj_type="entity", name="订单",
                status="confirmed", version=1,
                payload={"binding": {"datasource_id": 3}},
            )
        ]
        assets = [_asset(7, "db", "3", "销售库")]
        svc = _svc(assets=assets, objects=objects)

        # edge 表返回一条物化边
        fake_row = SimpleNamespace(
            src="ent.order", edge_type="binding", dst="asset:7", status=None
        )
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [fake_row]
        svc._edge_dao.session.return_value.__enter__.return_value = session

        # knowledge 聚合不可用(无 _system_app) → 静默跳过
        vo = asyncio.run(svc.graph("default"))
        ids = {n.id for n in vo.nodes}
        assert ids == {"ent.order", "asset:7"}
        asset_node = next(n for n in vo.nodes if n.id == "asset:7")
        assert asset_node.node_kind == "asset"
        assert asset_node.obj_type == "db"
        assert asset_node.name == "销售库"
        assert [(l.source, l.edge_type, l.target) for l in vo.links] == [
            ("ent.order", "binding", "asset:7")
        ]

    def test_knowledge_endpoint_mapping_prefers_document_asset(self):
        """verbat 端点优先映射到已登记 document 资产节点(三层连通点)。"""
        import asyncio

        from gyra_serve.ecp.service.service import Service as S

        svc = S.__new__(S)
        assets = [_asset(9, "document", "docs-ws1:v_abc")]

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
            svc._knowledge_subgraph("ws1", assets)
        )
        assert len(kn_nodes) == 1  # doc:wiki_1(另一端映射到资产节点)
        assert [(l.source, l.target, l.edge_type) for l in links] == [
            ("kn:docs-ws1:doc:wiki_1", "asset:9", "derived-from")
        ]


class _async_ret:
    """极简 awaitable,让 MagicMock 返回可 await 的值。"""

    def __init__(self, value):
        self._value = value

    def __await__(self):
        async def _coro():
            return self._value

        return _coro().__await__()
