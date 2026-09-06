"""Phase 1.2 外挂物化链路单元测试：materialize_expert_equipment。

覆盖：
- 正常物化（技能 + 数据源，池命中）
- 外挂级 config 覆盖池配置同名键（如知识库 top_k）
- 池未命中：skill/MCP 回退全局注册表直引（空间绑定非必需）
- 悬空外挂（知识库/数据源等空间域资源不在空间池）→ 跳过 + warning，不阻断
- 无成员行 / 无外挂行 → 返回 []
"""
from unittest import mock

import pytest

from gyra_serve.workspace import materializer as M


class _FakePoolRec:
    """模拟 WorkspaceResource 绑定记录（response 形态：config dict）。"""

    def __init__(self, type_, name, physical_ref=None, config=None, is_active=True):
        self.type = type_
        self.name = name
        self.physical_ref = physical_ref or name
        self.config = config or {}
        self.is_active = is_active


class _FakeEquipmentRow:
    def __init__(self, resource_type, resource_ref, config_json=None):
        self.resource_type = resource_type
        self.resource_ref = resource_ref
        self.config_json = config_json


@pytest.fixture()
def member_and_equipment():
    """patch WorkspaceExpertService：成员存在 + 两条外挂。"""
    with mock.patch(
        "gyra_serve.workspace.expert.WorkspaceExpertService"
    ) as svc_cls:
        svc = svc_cls.return_value
        svc.get_member_by_app_code.return_value = mock.Mock(id=7)
        svc.list_equipment.return_value = [
            _FakeEquipmentRow("skill", "db_query_skill"),
            _FakeEquipmentRow("datasource", "prod_core_db"),
        ]
        yield svc


@pytest.fixture()
def pool():
    """patch _load_pool_by_ref：空间池含两个资源。"""
    records = {
        "db_query_skill": _FakePoolRec("skill", "db_query_skill"),
        "prod_core_db": _FakePoolRec("data_source", "prod_core_db",
                                     config={"readonly": True}),
    }
    with mock.patch.object(M, "_load_pool_by_ref", return_value=records):
        yield records


class TestMaterializeExpertEquipment:
    def test_materialize_pool_hit(self, member_and_equipment, pool):
        resources = M.materialize_expert_equipment(
            system_app=mock.Mock(), workspace_id=1, app_code="expert_a")
        assert len(resources) == 2
        types = {r.type for r in resources}
        assert "skill(gyra)" in types
        assert "datasource" in types

    def test_dangling_equipment_skipped(self, member_and_equipment, pool):
        # 第二条外挂引用不在池中 → 跳过，第一条正常物化
        member_and_equipment.list_equipment.return_value = [
            _FakeEquipmentRow("skill", "db_query_skill"),
            _FakeEquipmentRow("datasource", "removed_db"),
        ]
        resources = M.materialize_expert_equipment(
            system_app=mock.Mock(), workspace_id=1, app_code="expert_a")
        assert len(resources) == 1

    def test_pool_miss_skill_falls_back_global(self, member_and_equipment, pool):
        """池未命中的 skill 外挂：回退全局技能库直引，仍正常物化。"""
        member_and_equipment.list_equipment.return_value = [
            _FakeEquipmentRow("skill", "global_only_skill"),
        ]
        resources = M.materialize_expert_equipment(
            system_app=mock.Mock(), workspace_id=1, app_code="expert_a")
        assert len(resources) == 1
        assert resources[0].type == "skill(gyra)"

    def test_pool_miss_mcp_falls_back_global(self, member_and_equipment, pool):
        """池未命中的 mcp 外挂：回退全局 MCP 注册表（get_mcp_info）物化。"""
        member_and_equipment.list_equipment.return_value = [
            _FakeEquipmentRow("mcp", "global_mcp"),
        ]
        with mock.patch(
            "gyra_serve.agent.resource.tool.mcp_collect.get_mcp_info"
        ) as get_info:
            get_info.return_value = {
                "name": "Global MCP",
                "sse_url": "http://mcp.example/sse",
                "sse_headers": {},
                "type": "sse",
            }
            resources = M.materialize_expert_equipment(
                system_app=mock.Mock(), workspace_id=1, app_code="expert_a")
        assert len(resources) == 1
        assert resources[0].type == "mcp(gyra)"

    def test_pool_miss_datasource_still_dangling(self, member_and_equipment, pool):
        """空间域资源（数据源）池未命中 → 无全局兜底，仍按悬空跳过。"""
        member_and_equipment.list_equipment.return_value = [
            _FakeEquipmentRow("datasource", "removed_db"),
        ]
        assert M.materialize_expert_equipment(
            system_app=mock.Mock(), workspace_id=1, app_code="expert_a") == []

    def test_equipment_config_overrides_pool(self, member_and_equipment, pool):
        member_and_equipment.list_equipment.return_value = [
            _FakeEquipmentRow("datasource", "prod_core_db",
                              config_json='{"readonly": false, "limit": 100}'),
        ]
        resources = M.materialize_expert_equipment(
            system_app=mock.Mock(), workspace_id=1, app_code="expert_a")
        assert len(resources) == 1
        import json
        value = json.loads(resources[0].value) if isinstance(
            resources[0].value, str) else resources[0].value
        # 外挂级参数覆盖池配置同名键
        assert value.get("readonly") is False
        assert value.get("limit") == 100

    def test_no_member_returns_empty(self, pool):
        with mock.patch(
            "gyra_serve.workspace.expert.WorkspaceExpertService"
        ) as svc_cls:
            svc_cls.return_value.get_member_by_app_code.return_value = None
            assert M.materialize_expert_equipment(
                mock.Mock(), 1, "expert_missing") == []

    def test_no_equipment_returns_empty(self, pool):
        with mock.patch(
            "gyra_serve.workspace.expert.WorkspaceExpertService"
        ) as svc_cls:
            svc = svc_cls.return_value
            svc.get_member_by_app_code.return_value = mock.Mock(id=7)
            svc.list_equipment.return_value = []
            assert M.materialize_expert_equipment(
                mock.Mock(), 1, "expert_a") == []

    def test_service_exception_returns_empty(self):
        with mock.patch(
            "gyra_serve.workspace.expert.WorkspaceExpertService"
        ) as svc_cls:
            svc_cls.return_value.get_member_by_app_code.side_effect = RuntimeError("db down")
            assert M.materialize_expert_equipment(
                mock.Mock(), 1, "expert_a") == []

    def test_materialize_registers_datasource_as_ecp_asset(self, pool):
        """P1 资产收口:datasource 外挂物化时同步登记进派生 ECP workspace 的
        asset_ref(kind=db),使专家外挂资产被 ECP 托管(asset_gate 拦截直连)。"""
        with mock.patch(
            "gyra_serve.workspace.expert.WorkspaceExpertService"
        ) as svc_cls:
            svc = svc_cls.return_value
            svc.get_member_by_app_code.return_value = mock.Mock(id=7)
            svc.list_equipment.return_value = [
                _FakeEquipmentRow("datasource", "prod_core_db"),
            ]
            pool_records = {
                "prod_core_db": _FakePoolRec("data_source", "prod_core_db"),
            }
            with mock.patch.object(M, "_load_pool_by_ref", return_value=pool_records):
                # mock workspace service -> workspace_code, 使派生 ecp_ws 可解析
                ws_svc = mock.Mock()
                ws = mock.Mock()
                ws.workspace_code = "ws_abc123"
                ws_svc.get_by_id.return_value = ws
                with mock.patch(
                    "gyra_serve.workspace.service.service.WorkspaceService",
                    return_value=ws_svc,
                ):
                    with mock.patch(
                        "gyra_serve.ecp.models.models.AssetRefDao"
                    ) as dao_cls:
                        dao = dao_cls.return_value
                        resources = M.materialize_expert_equipment(
                            mock.Mock(), 1, "expert_a")
        assert len(resources) == 1
        # datasource 被登记为 ECP 托管 db 资产
        dao.register.assert_called_once_with("db", "prod_core_db", "ecp_ws_abc123")

    def test_materialize_registers_knowledge_space_as_ecp_asset(self, pool):
        """P1 资产收口:knowledge_space 外挂登记为 kind=space。"""
        with mock.patch(
            "gyra_serve.workspace.expert.WorkspaceExpertService"
        ) as svc_cls:
            svc = svc_cls.return_value
            svc.get_member_by_app_code.return_value = mock.Mock(id=7)
            svc.list_equipment.return_value = [
                _FakeEquipmentRow("knowledge_space", "docs-ws_abc123"),
            ]
            pool_records = {
                "docs-ws_abc123": _FakePoolRec("knowledge_space", "docs-ws_abc123"),
            }
            with mock.patch.object(M, "_load_pool_by_ref", return_value=pool_records):
                ws_svc = mock.Mock()
                ws = mock.Mock()
                ws.workspace_code = "ws_abc123"
                ws_svc.get_by_id.return_value = ws
                with mock.patch(
                    "gyra_serve.workspace.service.service.WorkspaceService",
                    return_value=ws_svc,
                ):
                    with mock.patch(
                        "gyra_serve.ecp.models.models.AssetRefDao"
                    ) as dao_cls:
                        dao = dao_cls.return_value
                        resources = M.materialize_expert_equipment(
                            mock.Mock(), 1, "expert_a")
        assert len(resources) == 1
        dao.register.assert_called_once_with("space", "docs-ws_abc123", "ecp_ws_abc123")
