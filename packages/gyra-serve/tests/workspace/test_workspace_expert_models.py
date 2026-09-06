"""Phase 1.1 数据层单元测试：workspace_expert / workspace_expert_equipment。

用 SQLite 内存库验证：建表、唯一约束、upsert 幂等、级联查询。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gyra.storage.metadata import Model
from gyra_serve.workspace.expert.expert_models import (
    WorkspaceExpertDao,
    WorkspaceExpertEntity,
    WorkspaceExpertEquipmentDao,
    WorkspaceExpertEquipmentEntity,
)


@pytest.fixture()
def session_factory(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Model.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    # BaseDao.get_raw_session 依赖全局 session 工厂；patch 到内存库
    for dao_cls in (WorkspaceExpertDao, WorkspaceExpertEquipmentDao):
        monkeypatch.setattr(dao_cls, "get_raw_session", lambda self: factory())
    return factory


class TestWorkspaceExpertDao:
    def test_upsert_create_then_update(self, session_factory):
        dao = WorkspaceExpertDao()
        row = dao.upsert(workspace_id=1, app_code="expert_dataops", role_hint="数据运营")
        assert row.id is not None
        assert row.is_active is True

        row2 = dao.upsert(workspace_id=1, app_code="expert_dataops", role_hint="数据运营2")
        assert row2.id == row.id
        assert row2.role_hint == "数据运营2"

    def test_upsert_idempotent_unique(self, session_factory):
        dao = WorkspaceExpertDao()
        dao.upsert(workspace_id=1, app_code="expert_a")
        dao.upsert(workspace_id=1, app_code="expert_a")
        assert len(dao.list_by_workspace(1)) == 1

    def test_get_by_app_code(self, session_factory):
        dao = WorkspaceExpertDao()
        dao.upsert(workspace_id=1, app_code="expert_a", role_hint="a")
        got = dao.get_by_app_code(1, "expert_a")
        assert got is not None and got.role_hint == "a"
        assert dao.get_by_app_code(1, "nonexist") is None

    def test_list_by_workspace_active_only(self, session_factory):
        dao = WorkspaceExpertDao()
        dao.upsert(workspace_id=1, app_code="a")
        dao.upsert(workspace_id=1, app_code="b", is_active=False)
        dao.upsert(workspace_id=2, app_code="c")
        assert len(dao.list_by_workspace(1)) == 1
        assert len(dao.list_by_workspace(1, active_only=False)) == 2

    def test_upsert_icon_override_semantics(self, session_factory):
        dao = WorkspaceExpertDao()
        row = dao.upsert(workspace_id=1, app_code="expert_icon")
        assert row.icon is None
        # 非空 = 设置空间覆盖
        row = dao.upsert(workspace_id=1, app_code="expert_icon", icon="gyra-fs://a.png")
        assert row.icon == "gyra-fs://a.png"
        # 缺省（None）= 保持不变
        row = dao.upsert(workspace_id=1, app_code="expert_icon", role_hint="运营")
        assert row.icon == "gyra-fs://a.png"
        assert row.role_hint == "运营"
        # '' = 清除覆盖，回落全局身份
        row = dao.upsert(workspace_id=1, app_code="expert_icon", icon="")
        assert row.icon is None

    def test_service_upsert_member_icon(self, session_factory):
        from gyra_serve.workspace.expert.expert_service import WorkspaceExpertService

        service = WorkspaceExpertService()
        m = service.upsert_member(1, "expert_x", icon="gyra-fs://i.png")
        assert m.icon == "gyra-fs://i.png"
        # None 不动已有覆盖
        service.upsert_member(1, "expert_x")
        assert service.get_member_by_app_code(1, "expert_x").icon == "gyra-fs://i.png"
        # '' 清除覆盖
        service.upsert_member(1, "expert_x", icon="")
        assert service.get_member_by_app_code(1, "expert_x").icon is None


class TestWorkspaceExpertEquipmentDao:
    def test_upsert_and_list(self, session_factory):
        dao = WorkspaceExpertEquipmentDao()
        dao.upsert(expert_id=1, resource_type="skill", resource_ref="db_query")
        dao.upsert(expert_id=1, resource_type="knowledge_space", resource_ref="合同模板库")
        dao.upsert(expert_id=1, resource_type="skill", resource_ref="db_query")  # idempotent
        rows = dao.list_by_expert(1)
        assert len(rows) == 2

    def test_upsert_updates_config(self, session_factory):
        dao = WorkspaceExpertEquipmentDao()
        dao.upsert(expert_id=1, resource_type="knowledge_space", resource_ref="kb",
                   config_json='{"top_k": 3}')
        row = dao.upsert(expert_id=1, resource_type="knowledge_space", resource_ref="kb",
                         config_json='{"top_k": 5}')
        import json
        assert json.loads(row.config_json)["top_k"] == 5

    def test_delete_by_expert(self, session_factory):
        dao = WorkspaceExpertEquipmentDao()
        dao.upsert(expert_id=1, resource_type="skill", resource_ref="a")
        dao.upsert(expert_id=1, resource_type="skill", resource_ref="b")
        dao.upsert(expert_id=2, resource_type="skill", resource_ref="c")
        assert dao.delete_by_expert(1) == 2
        assert len(dao.list_by_expert(1)) == 0
        assert len(dao.list_by_expert(2)) == 1

    def test_unique_constraint(self, session_factory):
        dao = WorkspaceExpertEquipmentDao()
        dao.upsert(expert_id=1, resource_type="skill", resource_ref="a")
        # 直接 insert 违反唯一约束应报错（upsert 路径不会触发）
        import sqlalchemy.exc
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session = dao.get_raw_session()
            session.add(WorkspaceExpertEquipmentEntity(
                expert_id=1, resource_type="skill", resource_ref="a"))
            session.commit()
