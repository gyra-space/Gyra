"""SQL Guard RBAC provider 测试:表级回退 + 列级 deny。"""
from unittest.mock import patch

from gyra_serve.sql_guard.rbac_provider import RbacPermissionProvider
from gyra_serve.utils.auth import UserRequest


def _user(**kw):
    base = dict(
        user_id="2", user_no="2", user_name="bob", role="normal",
        permissions={}, deny_permissions={}, roles=[], grants=[],
    )
    base.update(kw)
    return UserRequest(**base)


class TestColumnAccess:
    def test_no_deny_allows_all(self):
        p = RbacPermissionProvider(user=_user())
        assert p.check_column_access("2", 3, "orders", ["id", "salary"]) == []

    def test_denied_column_returned(self):
        u = _user(deny_permissions={"database:3.orders.salary": ["read"]})
        p = RbacPermissionProvider(user=u)
        assert p.check_column_access("2", 3, "orders", ["id", "salary"]) == ["salary"]

    def test_deny_manage_or_admin_also_blocks(self):
        u = _user(deny_permissions={"database:3.orders.salary": ["manage"]})
        p = RbacPermissionProvider(user=u)
        assert p.check_column_access("2", 3, "orders", ["salary"]) == ["salary"]

    def test_deny_on_other_table_not_applied(self):
        u = _user(deny_permissions={"database:3.users.salary": ["read"]})
        p = RbacPermissionProvider(user=u)
        assert p.check_column_access("2", 3, "orders", ["salary"]) == []

    def test_no_user_allows_all(self):
        p = RbacPermissionProvider(user=None)
        assert p.check_column_access("2", 3, "orders", ["salary"]) == []


class TestTableAccessFallback:
    def test_table_level_then_ds_then_wildcard(self):
        """表级 miss → 数据源级 allow 命中。"""
        u = _user(permissions={"database:3": ["read"]})
        with patch("gyra_serve.permissions.check.has", wraps=None) as _:
            p = RbacPermissionProvider(user=u)
            # 走真实 has():scoped map 键 database:3
            assert p.check_table_access("2", 3, "orders", "select") is True

    def test_wildcard_allow(self):
        u = _user(permissions={"database": ["read"]})
        p = RbacPermissionProvider(user=u)
        assert p.check_table_access("2", 3, "orders", "select") is True

    def test_denied_when_nothing_matches(self):
        u = _user(permissions={"agent": ["read"]})
        p = RbacPermissionProvider(user=u)
        assert p.check_table_access("2", 3, "orders", "select") is False

    def test_deny_blocks_table(self):
        u = _user(
            permissions={"database": ["read"]},
            deny_permissions={"database:3.orders": ["read"]},
        )
        p = RbacPermissionProvider(user=u)
        assert p.check_table_access("2", 3, "orders", "select") is False

    def test_database_admin_covers(self):
        """database.admin 已注册,admin 动作覆盖所有表。"""
        u = _user(permissions={"database": ["admin"]})
        p = RbacPermissionProvider(user=u)
        assert p.check_table_access("2", 99, "anything", "delete") is True
