"""provenance 结构化溯源测试:origin 枚举/构造/携带 + 统一写入路径门禁。

覆盖:
- config.make_provenance / carry_provenance / origin_from_source
- Service.propose(gate_level="executable") 契约门禁(ContractViolation)
- propose_semantic 工具薄壳:miss_ref/origin_sql → provenance 落库参数
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gyra_serve.ecp.config import (
    ORIGIN_AGENT,
    ORIGIN_DISCOVERY,
    ORIGIN_EDIT,
    ORIGIN_LEGACY,
    ORIGIN_MISS_LEARN,
    carry_provenance,
    make_provenance,
    origin_from_source,
)
from gyra_serve.ecp.service.contracts import ContractViolation
from gyra_serve.ecp.service.service import Service


class TestProvenanceHelpers:
    def test_make_provenance_omits_empty(self):
        prov = make_provenance(ORIGIN_AGENT, actor="agent:x")
        assert prov == {"origin": "agent", "actor": "agent:x"}

    def test_make_provenance_full(self):
        prov = make_provenance(
            ORIGIN_MISS_LEARN,
            actor="agent:x",
            origin_sql=["SELECT 1", None, ""],
            miss_ref={"kind": "db", "pattern": "p", "datasource_id": 3},
            note="聚类出现 7 次",
        )
        assert prov["origin_sql"] == ["SELECT 1"]  # 空值过滤
        assert prov["miss_ref"]["datasource_id"] == 3

    def test_carry_keeps_original_origin(self):
        prev = {"origin": "miss_learn", "origin_sql": ["SELECT 1"]}
        carried = carry_provenance(prev, "edit_of:mtr.x@v1")
        assert carried["origin"] == "miss_learn"  # 来源不被编辑覆盖
        assert carried["derived_from"] == "edit_of:mtr.x@v1"
        assert carried["origin_sql"] == ["SELECT 1"]

    def test_carry_empty_becomes_edit(self):
        carried = carry_provenance(None, "edit_of:mtr.x@v1")
        assert carried["origin"] == ORIGIN_EDIT

    def test_origin_from_source_mapping(self):
        assert origin_from_source("discovery:ds1") == ORIGIN_DISCOVERY
        assert origin_from_source("sql_manual:default") == "manual_sql"
        assert origin_from_source("gate:rule5") == "rule5_gate"
        assert origin_from_source("edit_of:ent.x@v1") == ORIGIN_EDIT
        assert origin_from_source("agent:propose_semantic") == ORIGIN_AGENT
        assert origin_from_source("whatever") == ORIGIN_LEGACY
        assert origin_from_source(None) == ORIGIN_LEGACY


class TestProposeGate:
    def _svc(self):
        svc = Service.__new__(Service)
        svc._object_dao = MagicMock()
        svc._oplog_dao = MagicMock()
        svc._edge_dao = MagicMock()
        return svc

    def test_executable_gate_rejects_incomplete(self):
        svc = self._svc()
        with pytest.raises(ContractViolation) as exc:
            svc.propose(
                object_id="mtr.x",
                obj_type="metric",
                payload={"name": "x"},  # 缺 entity/expression
                gate_level="executable",
            )
        assert any("expression" in p or "entity" in p for p in exc.value.problems)
        svc._object_dao.create_proposal.assert_not_called()

    def test_executable_gate_passes_and_stores_provenance(self):
        svc = self._svc()
        svc._object_dao.create_proposal.return_value = SimpleNamespace(
            id="mtr.x", version=1, status="proposed",
        )
        prov = make_provenance(ORIGIN_MISS_LEARN, origin_sql=["SELECT 1"])
        svc.propose(
            object_id="mtr.x",
            obj_type="metric",
            payload={"name": "x", "entity": "ent.a", "expression": "SUM(F1)"},
            provenance=prov,
            gate_level="executable",
        )
        kw = svc._object_dao.create_proposal.call_args.kwargs
        assert kw["provenance"]["origin"] == "miss_learn"
        assert kw["provenance"]["origin_sql"] == ["SELECT 1"]

    def test_no_gate_keeps_lenient_batch_path(self):
        """批量管线(gate_level=None)不做 executable 校验,允许不完整候选。"""
        svc = self._svc()
        svc._object_dao.create_proposal.return_value = SimpleNamespace(
            id="rel.a__b", version=1, status="proposed",
        )
        svc.propose(
            object_id="rel.a__b",
            obj_type="relation",
            payload={"from": "ent.a", "to": "ent.b", "path": None},
        )
        svc._object_dao.create_proposal.assert_called_once()


class TestProposeSemanticTool:
    @pytest.mark.asyncio
    async def test_miss_ref_becomes_miss_learn_provenance(self):
        from gyra_serve.ecp.tools import ecp_tools

        captured = {}

        class _FakeService:
            def propose(self, **kw):
                captured.update(kw)
                return SimpleNamespace(id="mtr.x", version=1, status="proposed")

        original = ecp_tools._service
        ecp_tools._service = lambda: _FakeService()
        try:
            out = json.loads(
                await ecp_tools.propose_semantic(
                    object_id="mtr.x",
                    obj_type="metric",
                    payload={"name": "x", "entity": "ent.a", "expression": "SUM(F1)"},
                    miss_ref={"kind": "db", "pattern": "p", "datasource_id": 3},
                    origin_sql=["SELECT dt FROM t"],
                )
            )
        finally:
            ecp_tools._service = original

        assert out["status"] == "proposed"
        prov = captured["provenance"]
        assert prov["origin"] == "miss_learn"
        assert prov["miss_ref"]["pattern"] == "p"
        assert prov["origin_sql"] == ["SELECT dt FROM t"]
        assert captured["gate_level"] == "executable"

    @pytest.mark.asyncio
    async def test_no_miss_ref_is_agent_origin(self):
        from gyra_serve.ecp.tools import ecp_tools

        captured = {}

        class _FakeService:
            def propose(self, **kw):
                captured.update(kw)
                return SimpleNamespace(id="mtr.x", version=1, status="proposed")

        original = ecp_tools._service
        ecp_tools._service = lambda: _FakeService()
        try:
            await ecp_tools.propose_semantic(
                object_id="mtr.x",
                obj_type="metric",
                payload={"name": "x", "entity": "ent.a", "expression": "SUM(F1)"},
            )
        finally:
            ecp_tools._service = original
        assert captured["provenance"]["origin"] == "agent"

    @pytest.mark.asyncio
    async def test_contract_violation_returns_gaps(self):
        from gyra_serve.ecp.tools import ecp_tools

        class _FakeService:
            def propose(self, **kw):
                raise ContractViolation(["指标缺少 entity 绑定"])

        original = ecp_tools._service
        ecp_tools._service = lambda: _FakeService()
        try:
            out = json.loads(
                await ecp_tools.propose_semantic(
                    object_id="mtr.x",
                    obj_type="metric",
                    payload={"name": "x"},
                )
            )
        finally:
            ecp_tools._service = original
        assert out["contract_gaps"] == ["指标缺少 entity 绑定"]
