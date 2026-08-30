"""FastAPI dependency factories for permission checking.

``require_permission`` 是 ``gyra_serve.permissions.has`` 的依赖包装:
统一走协议判定(注册表 fail-closed + deny 否决 + 实例级 grant),
旁路语义(插件关闭放行 / legacy admin / superadmin)由 has() 保证。
"""

from typing import Optional

from fastapi import Depends, HTTPException

from gyra_serve.utils.auth import UserRequest, get_user_from_headers

# 协议权限入口（按 permission key 校验 + 实例级 grant），见 gyra_serve.permissions
from gyra_serve.permissions import has as has_permission  # noqa: F401
from gyra_serve.permissions import require as require_key  # noqa: F401


def require_permission(
    resource_type: str,
    action: str,
    resource_id: Optional[str] = "*",
):
    """FastAPI 依赖工厂 - 检查用户是否拥有指定权限。

    使用方式:
        # 检查对所有 agent 的 write 权限（通配符）
        @router.post("/agents")
        async def create_agent(
            user: UserRequest = Depends(require_permission("agent", "write")),
        ):
            ...

        # 检查对特定资源的权限时,resource_id 在依赖构造期传入
        # (路径参数需在端点函数体内用 has_permission 判定,
        #  依赖工厂拿不到路径参数)

    判定语义(与 gyra_serve.permissions.has 一致):
    1. 未注册的权限 key → 拒绝(fail-closed)
    2. 插件关闭(permissions 为 None)→ 放行(开发模式)
    3. legacy role=="admin" / superadmin 角色 → 放行
    4. deny 命中(scoped 或通配)→ 拒绝
    5. 角色权限:精确 resource_id → 通配 → "admin" 动作覆盖
    6. 资源实例级 grant(resource_grant 表)
    7. 全部未命中 → 403
    """
    permission_key = f"{resource_type}.{action}"

    def dependency(user: UserRequest = Depends(get_user_from_headers)) -> UserRequest:
        if has_permission(user, permission_key, resource_id=resource_id):
            return user
        if resource_id and resource_id != "*":
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {action} on {resource_type}:{resource_id}",
            )
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {action} on {resource_type}",
        )

    return dependency


def require_admin():
    """快捷方式：要求 system admin 权限"""
    return require_permission("system", "admin")


def require_read(resource_type: str):
    """快捷方式：要求读权限"""
    return require_permission(resource_type, "read")


def require_write(resource_type: str):
    """快捷方式：要求写权限"""
    return require_permission(resource_type, "write")


def require_execute(resource_type: str):
    """快捷方式：要求执行权限"""
    return require_permission(resource_type, "execute")
