"""RBAC 资源管理权限测试:空间管理员可维护资源,成员不可。"""
from unittest.mock import patch

from gyra_serve.workspace.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    Role,
    check_permission,
)


def test_manage_resource_granted_to_admin_roles():
    """owner/approver 拥有 MANAGE_RESOURCE;contributor/viewer 不拥有。"""
    assert Permission.MANAGE_RESOURCE in ROLE_PERMISSIONS[Role.OWNER]
    assert Permission.MANAGE_RESOURCE in ROLE_PERMISSIONS[Role.APPROVER]
    assert Permission.MANAGE_RESOURCE not in ROLE_PERMISSIONS[Role.CONTRIBUTOR]
    assert Permission.MANAGE_RESOURCE not in ROLE_PERMISSIONS[Role.VIEWER]


def test_check_permission_manage_resource_by_role():
    """check_permission 按角色判定 MANAGE_RESOURCE。"""
    cases = {
        Role.OWNER.value: True,
        Role.APPROVER.value: True,
        Role.CONTRIBUTOR.value: False,
        Role.VIEWER.value: False,
    }
    for role_str, expected in cases.items():
        with patch(
            "gyra_serve.workspace.rbac.WorkspaceMemberDao"
        ) as MockMemberDao:
            MockMemberDao.return_value.get_role.return_value = role_str
            assert (
                check_permission(workspace_id=1, user_id=2, permission=Permission.MANAGE_RESOURCE)
                is expected
            ), f"role={role_str} expected={expected}"