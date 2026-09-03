"""提案业务视图测试:summary/origin/lineage/sql_preview 的派生正确性。

设计(docs/ECP-functional-design.md 提案内容升级):
- provenance 优先,老数据 source 字符串降级映射
- metric 血缘:expression/extra_filters 列解析 + entity.fields 标注 declared
- 静态 SQL 预览:与 executor 同一组装路径,不执行;不完整提案降级 warnings
"""

from types import SimpleNamespace

from gyra_serve.ecp.service.proposal_view import build_proposal_view


def _vo(**kw):
    defaults = dict(
        id="mtr.net_sales", version=1, workspace_id="default",
        obj_type="metric", status="proposed", name="净销售额",
        payload={}, confidence=0.8, evidence=None, created_by="llm",
        created_at=None, confirmed_by=None, confirmed_at=None,
        source=None, provenance=None, supersedes=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _objects(*objs):
    by_id = {}
    for o in objs:
        by_id.setdefault(o.id, []).append(o)
    return SimpleNamespace(
        version_history=lambda ref_id, ws: by_id.get(ref_id, [])
    )


def _ds_resolver(ds_id):
    return {3: "ERP生产库"}.get(ds_id)


_ENTITY = _vo(
    id="ent.order", obj_type="entity", status="confirmed", name="销售订单",
    payload={
        "name": "销售订单",
        "binding": {"kind": "db", "table": "tb_so_01", "pk": "F001", "datasource_id": 3},
        "default_filters": ["F007 != '9'"],
        "fields": {
            "F001": {"meaning": "订单号", "role": "identifier"},
            "F003": {"meaning": "含税销售金额", "role": "measure", "unit": "CNY"},
            "F012": {"meaning": "税额", "role": "measure"},
            "F007": {"meaning": "状态", "role": "dimension"},
            "dt": {"meaning": "下单日期", "role": "time"},
        },
    },
)

_METRIC_PAYLOAD = {
    "name": "净销售额",
    "entity": "ent.order",
    "expression": "SUM(F003) - SUM(F012)",
    "extra_filters": ["F007 != 'CANCELLED'"],
    "grain": ["F007"],
    "unit": "CNY",
}


class TestOrigin:
    def test_provenance_miss_learn_with_origin_sql(self):
        vo = _vo(
            payload=_METRIC_PAYLOAD,
            provenance={
                "origin": "miss_learn",
                "actor": "agent:propose_semantic",
                "origin_sql": ["SELECT dt, SUM(F003) FROM tb_so_01 GROUP BY dt"],
                "miss_ref": {"kind": "db", "pattern": "select ... ?", "datasource_id": 3},
            },
        )
        view = build_proposal_view(vo, _objects(_ENTITY), _ds_resolver)
        assert view.origin.kind == "miss_learn"
        assert view.origin.label == "MISS 学习"
        assert view.origin.origin_sql == [
            "SELECT dt, SUM(F003) FROM tb_so_01 GROUP BY dt"
        ]
        assert view.origin.miss_ref["pattern"] == "select ... ?"

    def test_legacy_source_fallback(self):
        vo = _vo(payload=_METRIC_PAYLOAD, source="discovery:ds3")
        view = build_proposal_view(vo, _objects(_ENTITY), _ds_resolver)
        assert view.origin.kind == "discovery"
        assert view.origin.label == "初始扫描"
        assert view.origin.legacy_source == "discovery:ds3"

    def test_unknown_source_is_legacy(self):
        vo = _vo(payload=_METRIC_PAYLOAD, source="something_custom")
        view = build_proposal_view(vo, _objects(_ENTITY))
        assert view.origin.kind == "legacy"
        assert view.origin.legacy_source == "something_custom"


class TestLineage:
    def test_metric_lineage_columns_and_objects(self):
        vo = _vo(payload=_METRIC_PAYLOAD)
        view = build_proposal_view(vo, _objects(_ENTITY), _ds_resolver)
        lin = view.lineage
        assert lin.datasource_id == 3
        assert lin.datasource_name == "ERP生产库"
        assert lin.tables == ["tb_so_01"]
        cols = {c.column: c for c in lin.columns}
        # expression 列:度量表达式 + entity.fields 标注 meaning
        assert cols["F003"].usage == "度量表达式"
        assert cols["F003"].meaning == "含税销售金额"
        assert cols["F003"].declared is True
        # extra_filters 列
        assert "筛选条件" in cols["F007"].usage
        # grain 列
        assert "分组粒度" in cols["F007"].usage
        # 时间列补充
        assert cols["dt"].usage == "时间列"
        # 引用对象带状态
        assert lin.objects[0].id == "ent.order"
        assert lin.objects[0].status == "confirmed"

    def test_undeclared_column_flagged(self):
        payload = dict(_METRIC_PAYLOAD, expression="SUM(F003) - SUM(F999)")
        vo = _vo(payload=payload)
        view = build_proposal_view(vo, _objects(_ENTITY), _ds_resolver)
        cols = {c.column: c for c in view.lineage.columns}
        assert cols["F999"].declared is False  # 口径疑点

    def test_entity_lineage(self):
        view = build_proposal_view(_ENTITY, _objects(), _ds_resolver)
        lin = view.lineage
        assert lin.tables == ["tb_so_01"]
        cols = {c.column: c for c in lin.columns}
        assert cols["F001"].usage == "主键"
        assert cols["dt"].usage == "时间列"
        assert "筛选条件" in cols["F007"].usage

    def test_doc_lineage(self):
        vo = _vo(
            id="clm.return_rate", obj_type="claim",
            payload={
                "text": "退货率上限 5%",
                "binding": {"kind": "doc", "space": "docs-ws", "doc_id": "v_1",
                            "anchor": "sec:2"},
                "source_quote": "退货率上限 5%",
            },
        )
        view = build_proposal_view(vo)
        assert view.lineage.document == {
            "space": "docs-ws", "doc_id": "v_1", "anchor": "sec:2"
        }
        assert view.sql_preview is None


class TestSqlPreview:
    def test_metric_static_preview(self):
        vo = _vo(payload=_METRIC_PAYLOAD)
        view = build_proposal_view(vo, _objects(_ENTITY), _ds_resolver)
        sp = view.sql_preview
        assert sp.sql is not None
        assert "SUM(F003) - SUM(F012)" in sp.sql.replace('"', "")
        assert "tb_so_01" in sp.sql
        assert "F007" in sp.sql  # default_filters + extra_filters 都在
        assert "近 7 天" in sp.scenario
        assert sp.participants[0].id == "ent.order"

    def test_metric_without_entity_degrades_to_warning(self):
        vo = _vo(payload=_METRIC_PAYLOAD)
        view = build_proposal_view(vo, _objects(), _ds_resolver)
        assert view.sql_preview.sql is None
        assert view.sql_preview.warnings

    def test_brief_level_skips_sql_preview(self):
        vo = _vo(payload=_METRIC_PAYLOAD)
        view = build_proposal_view(vo, _objects(_ENTITY), _ds_resolver, level="brief")
        assert view.sql_preview is None
        assert view.summary

    def test_entity_preview(self):
        view = build_proposal_view(_ENTITY, _objects(), _ds_resolver)
        assert "SELECT * FROM tb_so_01" in view.sql_preview.sql
        assert "F007" in view.sql_preview.sql


class TestSummaryAndEvidence:
    def test_metric_summary(self):
        vo = _vo(payload=_METRIC_PAYLOAD)
        view = build_proposal_view(vo, _objects(_ENTITY))
        assert "SUM(F003)" in view.summary
        assert "F007" in view.summary

    def test_evidence_contracted(self):
        vo = _vo(
            payload=_METRIC_PAYLOAD,
            evidence=[{"source": "财务核算办法.docx", "quote": "净销售额剔税",
                       "extra_field": "dropped"}],
        )
        view = build_proposal_view(vo, _objects(_ENTITY))
        assert view.evidence[0].source == "财务核算办法.docx"
        assert view.evidence[0].quote == "净销售额剔税"
        assert not hasattr(view.evidence[0], "extra_field")


# ---------------------------------------------------------------- 畸形数据降级
# 历史/导入数据可能出现 payload 不是 object(JSON 数组),打开详情曾报
# "'list' object has no attribute 'get'"。视图必须降级渲染而不是抛异常。
class TestMalformedPayload:
    def test_list_payload_degrades(self):
        vo = _vo(payload=["SUM(F003)", "extra"])  # 非 object 的脏 payload
        view = build_proposal_view(vo)
        assert view.summary
        assert view.lineage is not None
        assert view.sql_preview is not None  # full 级降级为警告

    def test_entity_list_binding_and_fields_degrades(self):
        vo = _vo(
            obj_type="entity",
            payload={"binding": ["bad"], "fields": ["bad"], "name": "脏实体"},
        )
        view = build_proposal_view(vo)
        assert view.summary == "绑定表 ?"
        assert view.lineage is not None
        assert view.sql_preview is not None
        assert view.sql_preview.sql is None
        assert view.sql_preview.warnings
