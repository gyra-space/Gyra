"""PermissionService 聚合测试:deny 分桶 + scoped key 不压扁(泄漏修复)。"""
from unittest.mock import MagicMock, patch

import pytest

from gyra_app.feature_plugins.permissions.service import (
    PermissionService,
    UserPermissions,
)


def _svc_with_dao(perms_rows, roles=None, grants=None):
    svc = PermissionService()
    dao = MagicMock()
    dao.get_user_roles.return_value = roles or [{"id": 1, "name": "r1"}]
    dao.get_user_group_roles.return_value = []
    dao.get_permissions_for_roles.return_value = perms_rows
    dao.get_user_grants.return_value = grants or []
    svc._dao = dao
    return svc


def _row(rt, act, rid="*", effect="allow"):
    return {"resource_type": rt, "action": act, "resource_id": rid, "effect": effect}


@pytest.fixture(autouse=True)
def _clear_cache():
    PermissionService._cache.clear()
    yield
    PermissionService._cache.clear()


class TestAggregation:
    def test_deny_rows_go_to_deny_map(self):
        svc = _svc_with_dao([_row("agent", "read"), _row("agent", "chat", effect="deny")])
        perms = svc.get_user_permissions(1)
        assert perms.permissions_map == {"agent": ["read"]}
        assert perms.deny_map == {"agent": ["chat"]}

    def test_scoped_rows_not_flattened_to_wildcard(self):
        """resource_id != '*' 的行必须用 scoped key,不能泄漏成全量权限。"""
        svc = _svc_with_dao([_row("agent", "read", rid="financial-advisor")])
        perms = svc.get_user_permissions(1)
        assert perms.permissions_map == {"agent:financial-advisor": ["read"]}
        assert "agent" not in perms.permissions_map


class TestCheckScopedPermission:
    def _svc_with_perms(self, allow, deny, grants=None):
        svc = PermissionService()
        svc.get_user_permissions = lambda uid: UserPermissions(
            user_id=uid, role_names=[], permissions_map=allow,
            deny_map=deny, grants=grants or [],
        )
        return svc

    def test_scoped_allow_only_that_instance(self):
        svc = self._svc_with_perms({"agent:app-1": ["read"]}, {})
        assert svc.check_scoped_permission(1, "agent", "app-1", "read") is True
        assert svc.check_scoped_permission(1, "agent", "app-2", "read") is False

    def test_deny_beats_allow(self):
        svc = self._svc_with_perms({"agent": ["read"]}, {"agent": ["read"]})
        assert svc.check_permission(1, "agent", "read") is False

    def test_scoped_deny_beats_wildcard_allow(self):
        svc = self._svc_with_perms({"agent": ["chat"]}, {"agent:app-1": ["chat"]})
        assert svc.check_scoped_permission(1, "agent", "app-1", "chat") is False
        assert svc.check_scoped_permission(1, "agent", "app-2", "chat") is True

    def test_superadmin_bypasses_deny(self):
        svc = PermissionService()
        svc.get_user_permissions = lambda uid: UserPermissions(
            user_id=uid, role_names=["superadmin"],
            permissions_map={}, deny_map={"agent": ["admin"]}, grants=[],
        )
        assert svc.check_permission(1, "agent", "read") is True

    def test_deny_beats_grant(self):
        svc = self._svc_with_perms(
            {"agent": ["chat"]}, {"agent": ["chat"]},
            grants=[{"permission_key": "agent.chat", "resource_id": "*"}],
        )
        assert svc.check_permission(1, "agent", "chat") is False
