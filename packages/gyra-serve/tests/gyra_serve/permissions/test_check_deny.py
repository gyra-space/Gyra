"""deny 否决判定测试:has() 全局域 + has_scope 空间域(deny 优先于 allow)。"""
from unittest.mock import patch

from gyra_serve.permissions.check import has, has_scope
from gyra_serve.utils.auth import UserRequest


def _user(**kw):
    base = dict(
        user_id="2", user_no="2", user_name="bob", role="normal",
        permissions={}, deny_permissions={}, roles=[], grants=[],
    )
    base.update(kw)
    return UserRequest(**base)


class TestHasDeny:
    def test_deny_beats_allow_same_key(self):
        u = _user(permissions={"agent": ["read"]}, deny_permissions={"agent": ["read"]})
        assert has(u, "agent.read") is False

    def test_allow_works_without_deny(self):
        u = _user(permissions={"agent": ["read"]})
        assert has(u, "agent.read") is True

    def test_scoped_deny_only_blocks_that_instance(self):
        u = _user(
            permissions={"agent": ["chat"]},
            deny_permissions={"agent:app-1": ["chat"]},
        )
        assert has(u, "agent.chat", resource_id="app-1") is False
        assert has(u, "agent.chat", resource_id="app-2") is True
        assert has(u, "agent.chat") is True  # 通配判定不受 scoped deny 影响

    def test_deny_admin_action_covers_all_actions(self):
        u = _user(permissions={"agent": ["read", "chat"]},
                  deny_permissions={"agent": ["admin"]})
        assert has(u, "agent.read") is False
        assert has(u, "agent.chat") is False

    def test_deny_wildcard_star(self):
        u = _user(permissions={"agent": ["chat"]}, deny_permissions={"*": ["chat"]})
        assert has(u, "agent.chat") is False

    def test_deny_does_not_block_superadmin(self):
        u = _user(roles=["superadmin"], deny_permissions={"agent": ["admin"]})
        assert has(u, "agent.read") is True

    def test_deny_does_not_block_legacy_admin(self):
        u = _user(role="admin", deny_permissions={"agent": ["admin"]})
        assert has(u, "agent.read") is True

    def test_deny_blocks_grant_fallback(self):
        """deny 优先于实例级 grant。"""
        u = _user(
            permissions={},
            deny_permissions={"agent": ["chat"]},
            grants=[{"permission_key": "agent.chat", "resource_type": "agent",
                     "resource_id": "app-1"}],
        )
        assert has(u, "agent.chat", resource_id="app-1") is False

    def test_unregistered_key_still_closed(self):
        u = _user(permissions={"*": ["admin"]})
        assert has(u, "nope.nothing") is False


class TestHasScopeDeny:
    def test_space_deny_beats_allow(self):
        u = _user(permissions={"space.chat": []})  # 非 None = 插件开启
        with patch("gyra_serve.permissions.check._load_scoped_keys") as m:
            m.side_effect = lambda user_no, ws, effect="allow": (
                {"space.chat.use"} if effect == "deny" else {"space.chat.use"}
            )
            assert has_scope(u, "space.chat.use", workspace_id=1) is False

    def test_space_allow_when_no_deny(self):
        u = _user(permissions={"space.chat": []})
        with patch("gyra_serve.permissions.check._load_scoped_keys") as m:
            m.side_effect = lambda user_no, ws, effect="allow": (
                set() if effect == "deny" else {"space.chat.use"}
            )
            assert has_scope(u, "space.chat.use", workspace_id=1) is True
