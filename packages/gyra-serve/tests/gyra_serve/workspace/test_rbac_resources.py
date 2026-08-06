"""RBAC 三角色权限矩阵测试:管理(owner)/使用(contributor)/查看(viewer)。"""
from unittest.mock import patch

import pytest

from gyra_serve.workspace.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    Role,
    check_permission,
)


def test_role_set_is_three_tiers():
    """角色收敛为管理/使用/查看三档,approver 已移除。"""
    assert {r for r in Role} == {Role.OWNER, Role.CONTRIBUTOR, Role.VIEWER}


def test_manage_resource_granted_to_manager_only():
    """管理(owner)拥有 MANAGE_RESOURCE;使用/查看不拥有。"""
    assert Permission.MANAGE_RESOURCE in ROLE_PERMISSIONS[Role.OWNER]
    assert Permission.MANAGE_RESOURCE not in ROLE_PERMISSIONS[Role.CONTRIBUTOR]
    assert Permission.MANAGE_RESOURCE not in ROLE_PERMISSIONS[Role.VIEWER]


def test_delete_task_granted_to_manager_only():
    """删除任务为管理(owner)专属;使用/查看不可。"""
    assert Permission.DELETE_TASK in ROLE_PERMISSIONS[Role.OWNER]
    assert Permission.DELETE_TASK not in ROLE_PERMISSIONS[Role.CONTRIBUTOR]
    assert Permission.DELETE_TASK not in ROLE_PERMISSIONS[Role.VIEWER]


def test_viewer_has_no_write_permissions():
    """查看(viewer)无任何写权限。"""
    assert ROLE_PERMISSIONS[Role.VIEWER] == set()


def test_owner_has_all_permissions():
    """管理(owner)拥有全部权限。"""
    assert ROLE_PERMISSIONS[Role.OWNER] == set(Permission)


# 三角色 x 关键权限 的判定矩阵(期望值)
MATRIX = {
    Permission.START_TASK: {Role.OWNER: True, Role.CONTRIBUTOR: True, Role.VIEWER: False},
    Permission.PUBLISH_ASSET: {Role.OWNER: True, Role.CONTRIBUTOR: True, Role.VIEWER: False},
    Permission.CREATE_PLAYBOOK: {Role.OWNER: True, Role.CONTRIBUTOR: True, Role.VIEWER: False},
    Permission.DELETE_TASK: {Role.OWNER: True, Role.CONTRIBUTOR: False, Role.VIEWER: False},
    Permission.UPDATE_WORKSPACE: {Role.OWNER: True, Role.CONTRIBUTOR: False, Role.VIEWER: False},
    Permission.MANAGE_RESOURCE: {Role.OWNER: True, Role.CONTRIBUTOR: False, Role.VIEWER: False},
    Permission.RESOLVE_INTERVENTION: {Role.OWNER: True, Role.CONTRIBUTOR: False, Role.VIEWER: False},
}


@pytest.mark.parametrize("permission", list(MATRIX))
def test_check_permission_matrix(permission):
    """check_permission 按三角色矩阵判定关键权限。"""
    for role, expected in MATRIX[permission].items():
        with patch("gyra_serve.workspace.rbac.WorkspaceMemberDao") as MockMemberDao:
            MockMemberDao.return_value.get_role.return_value = role.value
            assert (
                check_permission(workspace_id=1, user_id=2, permission=permission)
                is expected
            ), f"role={role.value} permission={permission.value} expected={expected}"


def test_unknown_role_falls_back_to_viewer():
    """未知角色字符串降级为查看(viewer),无写权限。"""
    with patch("gyra_serve.workspace.rbac.WorkspaceMemberDao") as MockMemberDao:
        MockMemberDao.return_value.get_role.return_value = "approver"  # 已废弃值
        assert check_permission(
            workspace_id=1, user_id=2, permission=Permission.START_TASK
        ) is False
