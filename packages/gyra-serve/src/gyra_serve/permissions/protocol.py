"""权限协议核心：权限定义、模块基类与注册中心。

设计要点：
- 权限定义的单一事实来源在代码里（各模块继承 PermissionModule 声明），
  启动时由 Registry 同步到 permission_definition 表供管理界面使用；
- 权限 key 形如 ``<module>.<resource>.<action>``（全局域至少两段，如
  ``agent.chat``；空间域三段，如 ``space.task.start``）；
- key 与存量 ``(resource_type, action)`` 存储无损互转：按最后一个 ``.``
  切分，前段为 resource_type、末段为 action。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SCOPE_GLOBAL = "global"
SCOPE_SPACE = "space"


@dataclass(frozen=True)
class PermDef:
    """一条权限定义。

    key:          协议权限 key，如 ``space.task.start``
    name:         展示名（管理界面用）
    description:  权限说明
    scope_type:   ``global``（不绑空间）| ``space``（按空间判定）
    grantable:    是否允许开资源实例级授权（resource_grant）
    risk_level:   ``read`` | ``write`` | ``dangerous``（UI 分组/审批参考）
    """

    key: str
    name: str
    description: str = ""
    scope_type: str = SCOPE_GLOBAL
    grantable: bool = False
    risk_level: str = "write"

    def __post_init__(self):
        if self.scope_type not in (SCOPE_GLOBAL, SCOPE_SPACE):
            raise ValueError(f"Invalid scope_type {self.scope_type!r} for {self.key}")
        if self.risk_level not in ("read", "write", "dangerous"):
            raise ValueError(f"Invalid risk_level {self.risk_level!r} for {self.key}")
        parse_key(self.key)  # key 必须可解析


def parse_key(permission_key: str) -> Tuple[str, str]:
    """把协议 key 解析为存量存储格式 ``(resource_type, action)``。

    ``space.task.start`` -> ``("space.task", "start")``；
    ``agent.chat``       -> ``("agent", "chat")``。
    """
    resource_type, _, action = permission_key.rpartition(".")
    if not resource_type or not action:
        raise ValueError(
            f"Invalid permission key {permission_key!r}: "
            "expected '<resource_type>.<action>'"
        )
    return resource_type, action


class PermissionRegistry:
    """权限注册中心：模块子类化 PermissionModule 时自动登记。"""

    _modules: Dict[str, "type[PermissionModule]"] = {}
    _key_owner: Dict[str, str] = {}

    @classmethod
    def register(cls, module_cls: "type[PermissionModule]") -> None:
        name = getattr(module_cls, "name", None)
        perms = getattr(module_cls, "permissions", None)
        if not name or not isinstance(name, str):
            raise ValueError(f"{module_cls.__name__}: missing module 'name'")
        if not perms:
            raise ValueError(f"{module_cls.__name__}: empty 'permissions'")

        if name in cls._modules:
            # 进程内重复 import 时幂等；定义冲突则报错
            if cls._modules[name] is not module_cls:
                raise ValueError(f"Permission module name conflict: {name}")
            return

        for p in perms:
            if not p.key.startswith(f"{name}."):
                raise ValueError(
                    f"{module_cls.__name__}: permission key {p.key!r} "
                    f"must start with '{name}.'"
                )
            owner = cls._key_owner.get(p.key)
            if owner is not None:
                raise ValueError(
                    f"Permission key {p.key!r} already registered by module {owner}"
                )
            cls._key_owner[p.key] = name

        cls._modules[name] = module_cls
        logger.debug("Permission module registered: %s (%d keys)", name, len(perms))

    @classmethod
    def all(cls) -> List[PermDef]:
        """返回全部已注册的权限定义（按模块名、声明顺序）。"""
        result: List[PermDef] = []
        for name in sorted(cls._modules):
            result.extend(cls._modules[name].permissions)
        return result

    @classmethod
    def keys(cls) -> List[str]:
        return [p.key for p in cls.all()]

    @classmethod
    def get(cls, permission_key: str) -> Optional[PermDef]:
        owner = cls._key_owner.get(permission_key)
        if owner is None:
            return None
        for p in cls._modules[owner].permissions:
            if p.key == permission_key:
                return p
        return None

    @classmethod
    def reset(cls) -> None:
        """仅测试用：清空注册表。"""
        cls._modules.clear()
        cls._key_owner.clear()


class PermissionModule:
    """权限协议模块基类：子类化即自动注册，无需手动登记。

    用法::

        class SpacePermModule(PermissionModule):
            name = "space"
            permissions = [
                PermDef("space.chat.use", "空间对话", scope_type=SCOPE_SPACE),
                ...
            ]

        # 模块内直接取校验依赖
        space_mod = SpacePermModule()
        @router.post("/tasks", dependencies=[Depends(space_mod.require("space.task.start"))])
    """

    name: str = ""
    permissions: List[PermDef] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 允许定义中间抽象基类（abstract=True 跳过注册）
        if getattr(cls, "_abstract", False):
            return
        PermissionRegistry.register(cls)

    def require(self, permission_key: str, resource_id: Optional[str] = None):
        """返回校验该权限的 FastAPI 依赖。"""
        from gyra_serve.permissions.check import require

        return require(permission_key, resource_id=resource_id)


# 触发内置模块注册（import 即注册）
from . import modules  # noqa: E402,F401
