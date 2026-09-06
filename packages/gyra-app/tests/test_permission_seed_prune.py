"""seed 内置角色 read 收权的幂等性测试。

_prune_builtin_role_reads 只允许执行一次（system_config 标记 key），
执行后管理员手工重新授予的 read 不能被后续启动回滚。
"""

from gyra_app.feature_plugins.permissions import seed
from gyra_app.feature_plugins.permissions.seed import (
    SEED_ROLES,
    _prune_builtin_role_reads,
)


class FakeDao:
    """最小 PermissionDao 桩：只实现 prune 用到的四个方法。"""

    def __init__(self, roles):
        # roles: {role_name: {"id": int, "perms": [{"id", "resource_type", "action", "resource_id"}]}}
        self.roles = roles
        self.removed = []

    def get_role_by_name(self, name):
        role = self.roles.get(name)
        return {"id": role["id"]} if role else None

    def list_role_permissions(self, role_id):
        for role in self.roles.values():
            if role["id"] == role_id:
                return list(role["perms"])
        return []

    def remove_role_permission(self, permission_id):
        for role in self.roles.values():
            for p in role["perms"]:
                if p["id"] == permission_id:
                    role["perms"].remove(p)
                    self.removed.append(permission_id)
                    return True
        return False


class FakeSystemConfigDao:
    """模拟 system_config 标记 key 的存取。"""

    store = {}

    def __init__(self):
        pass

    def get_config(self, config_key, config_type="feature_plugin"):
        return self.store.get((config_type, config_key))

    def set_config(self, config_key, config_value, config_type="feature_plugin", description=None):
        self.store[(config_type, config_key)] = config_value
        return config_value


def _make_dao():
    return FakeDao(
        {
            "superadmin": {"id": 1, "perms": []},
            "guest": {
                "id": 2,
                "perms": [
                    {"id": 11, "resource_type": "model", "action": "read", "resource_id": "*"},
                    {"id": 12, "resource_type": "model", "action": "chat", "resource_id": "*"},
                    # scoped 行不动（实例级授权不属收权范围）
                    {"id": 13, "resource_type": "agent", "action": "read", "resource_id": "3"},
                ],
            },
            "normal_user": {
                "id": 3,
                "perms": [
                    {"id": 21, "resource_type": "agent", "action": "read", "resource_id": "*"},
                    {"id": 22, "resource_type": "agent", "action": "chat", "resource_id": "*"},
                ],
            },
            "admin": {
                "id": 4,
                "perms": [
                    {"id": 31, "resource_type": "model", "action": "read", "resource_id": "*"},
                    {"id": 32, "resource_type": "system", "action": "admin", "resource_id": "*"},
                ],
            },
        }
    )


def setup_function(fn):
    FakeSystemConfigDao.store.clear()


def _patch(monkeypatch):
    monkeypatch.setattr(
        "gyra_app.feature_plugins.system_config_dao.SystemConfigDao",
        FakeSystemConfigDao,
    )


def test_seed_non_admin_roles_have_no_resource_read():
    """seed 矩阵：非 admin 内置角色不再包含资源 read。"""
    for role_def in SEED_ROLES:
        if role_def["name"] in ("superadmin", "admin"):
            continue
        for resource_type, action in role_def["permissions"]:
            assert action != "read", (
                f"built-in role {role_def['name']} should not seed "
                f"{resource_type}.read"
            )


def test_seed_admin_keeps_reads():
    admin = next(r for r in SEED_ROLES if r["name"] == "admin")
    perms = set(admin["permissions"])
    assert ("model", "read") in perms
    assert ("system", "admin") in perms


def test_prune_removes_reads_and_marks_done(monkeypatch):
    _patch(monkeypatch)
    dao = _make_dao()

    _prune_builtin_role_reads(dao)

    # 只删了非 admin 角色的通配 read
    assert sorted(dao.removed) == [11, 21]
    guest = dao.roles["guest"]["perms"]
    assert [p["id"] for p in guest] == [12, 13]  # chat 与 scoped read 保留
    admin = dao.roles["admin"]["perms"]
    assert [p["id"] for p in admin] == [31, 32]  # admin 不动
    # 标记 key 已写入
    assert FakeSystemConfigDao.store[("internal", seed._READ_PRUNE_MARKER_KEY)]["done"] is True


def test_prune_is_one_time_only(monkeypatch):
    """执行过一次后，管理员手工重新授予的 read 不被回滚。"""
    _patch(monkeypatch)
    dao = _make_dao()
    _prune_builtin_role_reads(dao)

    # 管理员重新授予 normal_user agent.read
    dao.roles["normal_user"]["perms"].append(
        {"id": 99, "resource_type": "agent", "action": "read", "resource_id": "*"}
    )
    _prune_builtin_role_reads(dao)

    assert dao.removed == [11, 21]  # 第二次调用没有新增删除
    assert any(p["id"] == 99 for p in dao.roles["normal_user"]["perms"])
