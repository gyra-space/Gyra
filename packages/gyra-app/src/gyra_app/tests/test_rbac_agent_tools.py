"""RBAC 管理 Agent 工具(agent_tools)单元测试。

覆盖:
- fail-closed 守卫:无用户上下文 / 非管理员 → 一律拒绝;
- 管理员身份 → 放行并执行业务逻辑(DB 层 mock);
- 批量注册 dry_run 预览不写库,冲突行/未知角色行标记正确;
- 写工具注册元数据(ask_user / risk_level)。
"""

from unittest.mock import MagicMock, patch

import pytest

from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.base import ToolRiskLevel
from gyra_serve.utils.auth import UserRequest

from gyra_app.feature_plugins.permissions import agent_tools


def _ctx(user: UserRequest = None) -> ToolContext:
    ctx = ToolContext()
    if user is not None:
        ctx.set_resource("user_request", user)
    return ctx


def _admin() -> UserRequest:
    return UserRequest(user_id="1", user_name="admin", role="admin")


def _normal_user() -> UserRequest:
    # permissions={} 表示权限插件开启但无任何授权(非 dev 模式)
    return UserRequest(
        user_id="2", user_name="bob", role="normal",
        permissions={}, roles=[], grants=[],
    )


# --------------------------------------------------------------------------- #
# 守卫:fail-closed
# --------------------------------------------------------------------------- #
def test_no_identity_denied():
    result = agent_tools.rbac_list_roles(context=_ctx())
    assert result["success"] is False
    assert result["code"] == "PERMISSION_DENIED"


def test_no_context_denied():
    result = agent_tools.rbac_list_roles(context=None)
    assert result["success"] is False


def test_non_admin_denied():
    result = agent_tools.rbac_list_roles(context=_ctx(_normal_user()))
    assert result["success"] is False
    assert "system.admin" in result["error"]


def test_write_tool_non_admin_denied():
    result = agent_tools.rbac_delete_role(role_id=1, context=_ctx(_normal_user()))
    assert result["success"] is False
    assert result["code"] == "PERMISSION_DENIED"


# --------------------------------------------------------------------------- #
# 管理员路径(DB mock)
# --------------------------------------------------------------------------- #
def test_admin_list_roles():
    with patch.object(agent_tools, "_dao") as mock_dao:
        mock_dao.list_roles.return_value = [
            {"id": 1, "name": "viewer", "description": "", "is_system": 1,
             "scope_type": "global", "gmt_create": None, "gmt_modify": None}
        ]
        mock_dao.list_role_permissions.return_value = [
            {"id": 1, "role_id": 1, "resource_type": "agent", "resource_id": "*",
             "action": "read", "effect": "allow", "gmt_create": None}
        ]
        result = agent_tools.rbac_list_roles(context=_ctx(_admin()))
    assert result["success"] is True
    assert result["total"] == 1
    assert result["items"][0]["permissions"][0]["action"] == "read"


def test_create_user_unknown_role_rejected():
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch.object(agent_tools, "_get_user_service") as mock_svc:
        mock_dao.get_role_by_name.return_value = None
        result = agent_tools.rbac_create_user(
            username="alice", password="secret123",
            role_names=["ghost"], context=_ctx(_admin()),
        )
    assert result["success"] is False
    assert "角色不存在" in result["error"]
    mock_svc.return_value.create_local_user.assert_not_called()


def test_create_user_success_assigns_roles():
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch.object(agent_tools, "_get_user_service") as mock_svc, \
         patch.object(agent_tools, "_svc") as mock_perm_svc:
        mock_dao.get_role_by_name.return_value = {"id": 7, "name": "viewer"}
        mock_svc.return_value.create_local_user.return_value = {"id": 42}
        result = agent_tools.rbac_create_user(
            username="alice", password="secret123",
            role_names=["viewer"], context=_ctx(_admin()),
        )
    assert result["success"] is True
    assert result["user_id"] == 42
    mock_dao.assign_role_to_user.assert_called_once_with(42, 7)
    mock_perm_svc.invalidate_cache.assert_called_once_with(42)


# --------------------------------------------------------------------------- #
# rbac_set_role_permissions: 兼容字符串/权限 key 传参
# --------------------------------------------------------------------------- #
def test_set_role_permissions_accepts_string_keys():
    """LLM 把 permission key 当字符串传(如 'agent.admin')不应抛异常。"""
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch.object(agent_tools, "_svc"):
        mock_dao.get_role.return_value = {
            "id": 14, "name": "cs_space_admin", "is_system": 0
        }
        result = agent_tools.rbac_set_role_permissions(
            role_id=14,
            permissions=["agent.admin", "tool.admin", "database.admin"],
            context=_ctx(_admin()),
        )
    assert result["success"] is True
    assert len(result["applied"]) == 3
    assert len(result["skipped"]) == 0
    calls = mock_dao.add_role_permission.call_args_list
    assert calls[0].kwargs == {
        "role_id": 14, "resource_type": "agent", "action": "admin",
        "resource_id": "*", "effect": "allow",
    }
    assert calls[1].kwargs["resource_type"] == "tool"
    assert calls[2].kwargs["resource_type"] == "database"


def test_set_role_permissions_accepts_key_dict():
    """dict 形态但用 key 字段(来自 rbac_list_permission_definitions)。"""
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch.object(agent_tools, "_svc"):
        mock_dao.get_role.return_value = {
            "id": 14, "name": "cs_space_admin", "is_system": 0
        }
        result = agent_tools.rbac_set_role_permissions(
            role_id=14,
            permissions=[{"key": "channel.manage"}, {"key": "cron.manage"}],
            context=_ctx(_admin()),
        )
    assert result["success"] is True
    calls = mock_dao.add_role_permission.call_args_list
    assert [c.kwargs["resource_type"] for c in calls] == ["channel", "cron"]
    assert [c.kwargs["action"] for c in calls] == ["manage", "manage"]


def test_set_role_permissions_skips_invalid_items():
    """非法/无法解析的项跳过并记录原因,不抛异常。"""
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch.object(agent_tools, "_svc"):
        mock_dao.get_role.return_value = {
            "id": 14, "name": "cs_space_admin", "is_system": 0
        }
        result = agent_tools.rbac_set_role_permissions(
            role_id=14,
            permissions=[
                "agent.admin",
                "not-a-key",
                {"resource_type": "tool", "action": "admin"},
            ],
            context=_ctx(_admin()),
        )
    assert result["success"] is True
    assert len(result["applied"]) == 2
    assert len(result["skipped"]) == 1
    mock_dao.add_role_permission.assert_called()


# --------------------------------------------------------------------------- #
# 批量注册:dry_run 预览
# --------------------------------------------------------------------------- #
def _batch_users():
    return [
        {"username": "new_user", "password": "pass123", "role_names": ["viewer"]},
        {"username": "dup_user", "password": "pass123"},
        {"username": "x", "password": "pass123"},
        {"username": "bad_role", "password": "pass123", "role_names": ["ghost"]},
    ]


def _patch_batch_deps(mock_dao, mock_user_dao_cls):
    mock_dao.get_role_by_name.side_effect = (
        lambda name: {"id": 7, "name": "viewer"} if name == "viewer" else None
    )
    mock_user_dao_cls.return_value.get_by_username.side_effect = (
        lambda name: {"id": 9} if name == "dup_user" else None
    )


def test_batch_dry_run_previews_without_writing():
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch("gyra_app.auth.user_service.UserDao") as mock_user_dao_cls, \
         patch.object(agent_tools, "_get_user_service") as mock_svc:
        _patch_batch_deps(mock_dao, mock_user_dao_cls)
        result = agent_tools.rbac_batch_create_users(
            users=_batch_users(), context=_ctx(_admin()),
        )
    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["summary"] == {"total": 4, "ok": 1, "failed": 3}
    problems = {p["username"]: p["problems"] for p in result["preview"]}
    assert problems["new_user"] == []
    assert "用户名已存在" in problems["dup_user"][0]
    assert "用户名缺失或太短" in problems["x"][0]
    assert any("角色不存在" in p for p in problems["bad_role"])
    # dry_run 不写库
    mock_svc.return_value.create_local_user.assert_not_called()


def test_batch_execute_creates_only_valid_rows():
    with patch.object(agent_tools, "_dao") as mock_dao, \
         patch("gyra_app.auth.user_service.UserDao") as mock_user_dao_cls, \
         patch.object(agent_tools, "_get_user_service") as mock_svc, \
         patch.object(agent_tools, "_svc"):
        _patch_batch_deps(mock_dao, mock_user_dao_cls)
        mock_svc.return_value.create_local_user.return_value = {"id": 100}
        result = agent_tools.rbac_batch_create_users(
            users=_batch_users(), dry_run=False, context=_ctx(_admin()),
        )
    assert result["success"] is True
    assert result["summary"]["created"] == 1
    created = [r["username"] for r in result["results"] if r["created"]]
    assert created == ["new_user"]
    mock_svc.return_value.create_local_user.assert_called_once()


def test_batch_rejects_oversize():
    result = agent_tools.rbac_batch_create_users(
        users=[{"username": f"u{i}", "password": "pass123"} for i in range(501)],
        context=_ctx(_admin()),
    )
    assert result["success"] is False
    assert "500" in result["error"]


# --------------------------------------------------------------------------- #
# 参数校验
# --------------------------------------------------------------------------- #
def test_assign_role_requires_exactly_one_target():
    result = agent_tools.rbac_assign_role(role_name="viewer", context=_ctx(_admin()))
    assert result["success"] is False
    assert "二选一" in result["error"] or "只能给一个" in result["error"]


def test_assign_role_unknown_role():
    with patch.object(agent_tools, "_dao") as mock_dao:
        mock_dao.get_role_by_name.return_value = None
        result = agent_tools.rbac_assign_role(
            role_name="ghost", user_id=1, context=_ctx(_admin())
        )
    assert result["success"] is False
    assert "不存在" in result["error"]


def test_delete_system_role_blocked():
    with patch.object(agent_tools, "_dao") as mock_dao:
        mock_dao.get_role.return_value = {"id": 1, "name": "admin", "is_system": 1}
        result = agent_tools.rbac_delete_role(role_id=1, context=_ctx(_admin()))
    assert result["success"] is False
    assert "系统内置角色" in result["error"]
    mock_dao.delete_role.assert_not_called()


def test_grant_resource_rejects_non_grantable_key():
    with patch.object(agent_tools, "_dao"), \
         patch.object(agent_tools, "_get_user_service") as mock_svc:
        mock_svc.return_value.get_user.return_value = {"id": 1}
        # system.admin 已注册但 grantable=False
        result = agent_tools.rbac_grant_resource(
            user_id=1, permission_key="system.admin", resource_id="*",
            context=_ctx(_admin()),
        )
    assert result["success"] is False
    assert "不支持实例级授权" in result["error"]


# --------------------------------------------------------------------------- #
# 注册元数据
# --------------------------------------------------------------------------- #
def test_tools_registered_with_metadata():
    read_tool = agent_tools.rbac_list_roles._tool
    write_tool = agent_tools.rbac_delete_role._tool
    batch_tool = agent_tools.rbac_batch_create_users._tool

    assert read_tool.metadata.risk_level == ToolRiskLevel.SAFE
    assert read_tool.metadata.requires_permission is False

    assert write_tool.metadata.risk_level == ToolRiskLevel.HIGH
    assert write_tool.metadata.requires_permission is True  # ask_user

    assert batch_tool.metadata.risk_level == ToolRiskLevel.HIGH
    assert batch_tool.metadata.requires_permission is True

    from gyra.agent.tools.registry import tool_registry

    for name in (
        "rbac_list_users", "rbac_get_user_detail", "rbac_list_roles",
        "rbac_list_groups", "rbac_get_group", "rbac_list_permission_definitions",
        "rbac_list_grants", "rbac_create_user", "rbac_batch_create_users",
        "rbac_create_role", "rbac_update_role", "rbac_delete_role",
        "rbac_set_role_permissions", "rbac_assign_role", "rbac_remove_role",
        "rbac_create_group", "rbac_add_group_members",
        "rbac_grant_resource", "rbac_revoke_resource",
    ):
        assert tool_registry.get(name) is not None, f"工具未注册: {name}"
