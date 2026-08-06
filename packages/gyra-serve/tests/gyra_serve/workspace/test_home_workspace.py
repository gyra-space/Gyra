"""WorkspaceService.get_or_create_home 测试:首页默认空间幂等解析(用户级)。

解析顺序(基于 member.is_home,按用户隔离):
1. 有 member.is_home=True 的成员空间 -> 返回
2. 兼容存量:有 settings.is_home 标记(空间级)的 -> 一次性提升为用户级主空间
3. 无标记 -> 最早创建(id 最小)补用户级标记(存量用户零迁移)
4. 无空间 -> 新建"我的工作台"(create 派生钩子生效)
归档空间不参与选择。
"""
import pytest

from gyra.storage.metadata import db
from gyra_serve.workspace.api.schemas import WorkspaceRequest
from gyra_serve.workspace.config import ServeConfig
from gyra_serve.workspace.models.models import (
    WorkspaceConversationLinkDao,
    WorkspaceDao,
    WorkspaceMemberDao,
    WorkspaceResourceDao,
)
from gyra_serve.workspace.service.service import WorkspaceService


@pytest.fixture
def service(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(f"sqlite:///{db_path}")
    db.create_all()
    svc = WorkspaceService(
        None,
        ServeConfig(),
        dao=WorkspaceDao(),
        member_dao=WorkspaceMemberDao(),
        resource_dao=WorkspaceResourceDao(),
        conv_link_dao=WorkspaceConversationLinkDao(),
    )
    # init_app 不走(无 SystemApp);create 的 ECP 供给钩子对 None system_app
    # 已做 fail-open 保护。
    return svc


def _create(svc, name, owner=1, **kw):
    return svc.create(WorkspaceRequest(name=name, owner_user_id=owner, **kw))


def _member_is_home(svc, workspace_id, user_id=1):
    """查询用户在该空间的主空间标记。"""
    return svc.member_dao.get_home_workspace_id(user_id) == workspace_id


def test_create_when_no_workspace(service):
    home = service.get_or_create_home(user_id=1)
    assert home.name == "我的工作台"
    assert home.settings.get("is_home") is True
    # 幂等:再次调用返回同一空间,不新建
    again = service.get_or_create_home(user_id=1)
    assert again.id == home.id
    assert len(service.list_workspaces(1)) == 1


def test_member_home_wins(service):
    a = _create(service, "空间A")
    b = _create(service, "空间B")
    # 用户显式把 B 设为主空间
    service.set_home(user_id=1, workspace_id=b.id)
    home = service.get_or_create_home(user_id=1)
    assert home.id == b.id
    assert not _member_is_home(service, a.id)
    assert _member_is_home(service, b.id)


def test_set_home_is_per_user(service):
    """主空间按用户隔离:用户1设 B 为主,不影响用户2。"""
    a = _create(service, "空间A", owner=1)
    b = _create(service, "空间B", owner=1)
    # 用户2 加入空间A
    from gyra_serve.workspace.api.schemas import WorkspaceMemberRequest
    service.add_member(WorkspaceMemberRequest(workspace_id=a.id, user_id=2, role="contributor"))
    service.set_home(user_id=1, workspace_id=b.id)
    # 用户2 未设置主空间:取最早创建的 A
    home2 = service.get_or_create_home(user_id=2)
    assert home2.id == a.id
    assert service.member_dao.get_home_workspace_id(2) == a.id
    # 用户1 仍为 B
    assert service.member_dao.get_home_workspace_id(1) == b.id


def test_legacy_unmarked_falls_back_to_earliest_and_marks(service):
    """存量用户:无标记时取最早创建的,并补上用户级标记。"""
    a = _create(service, "空间A")
    _create(service, "空间B")
    home = service.get_or_create_home(user_id=1)
    assert home.id == a.id
    # 用户级标记已补
    assert _member_is_home(service, a.id)
    # 再次调用直接命中标记
    assert service.get_or_create_home(user_id=1).id == a.id


def test_legacy_settings_home_promoted(service):
    """存量空间级 settings.is_home 一次性提升为用户级主空间。"""
    a = _create(service, "空间A")
    b = _create(service, "空间B", settings={"is_home": True})
    home = service.get_or_create_home(user_id=1)
    assert home.id == b.id
    # 已提升为用户级
    assert _member_is_home(service, b.id)


def test_archived_home_is_skipped(service):
    a = _create(service, "空间A", settings={"is_home": True})
    b = _create(service, "空间B")
    service.archive(a.workspace_code)
    home = service.get_or_create_home(user_id=1)
    assert home.id == b.id
    # B 被补用户级标记
    assert _member_is_home(service, b.id)


def test_set_home_requires_membership(service):
    """非该空间成员设置主空间应失败。"""
    a = _create(service, "空间A")
    # 用户2 不是空间A成员
    assert service.set_home(user_id=2, workspace_id=a.id) is None
    assert service.member_dao.get_home_workspace_id(2) is None


def test_other_users_workspaces_invisible(service):
    _create(service, "别人的空间", owner=2)
    home = service.get_or_create_home(user_id=1)
    assert home.name == "我的工作台"
    assert home.owner_user_id == 1