"""权限协议（Permission-as-Protocol）。

- protocol: PermDef / PermissionModule / PermissionRegistry
- check:    require()（FastAPI 依赖工厂）与 has()（同步判定）
- modules:  内置权限模块（import 即注册）
"""

from .protocol import (
    PermDef,
    PermissionModule,
    PermissionRegistry,
    SCOPE_GLOBAL,
    SCOPE_SPACE,
    parse_key,
)
from .check import (
    can_delete_file,
    can_read_conversation,
    can_read_file,
    has,
    has_scope,
    require,
    require_space,
)

__all__ = [
    "PermDef",
    "PermissionModule",
    "PermissionRegistry",
    "parse_key",
    "has",
    "has_scope",
    "require",
    "require_space",
    "can_read_conversation",
    "can_read_file",
    "can_delete_file",
    "SCOPE_GLOBAL",
    "SCOPE_SPACE",
]
