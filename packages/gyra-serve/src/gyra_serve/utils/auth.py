import logging
from typing import Dict, List, Optional

from fastapi import Header, HTTPException, Request

from gyra._private.pydantic import BaseModel

logger = logging.getLogger(__name__)


class UserRequest(BaseModel):
    user_id: Optional[str] = None
    user_no: Optional[str] = None
    real_name: Optional[str] = None
    # same with user_id
    user_name: Optional[str] = None
    user_channel: Optional[str] = None
    role: Optional[str] = "normal"
    nick_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    nick_name_like: Optional[str] = None
    # 新增字段（插件关闭时为 None，表示不做权限检查）
    permissions: Optional[Dict[str, List[str]]] = None  # resource_type(或 rt:rid) -> [actions]
    deny_permissions: Optional[Dict[str, List[str]]] = None  # deny 分桶,同上分键格式
    roles: Optional[List[str]] = None  # 用户拥有的角色名列表
    grants: Optional[List[Dict]] = None  # 资源实例级授权 [{permission_key, resource_type, resource_id, ...}]


def _is_permissions_enabled() -> bool:
    """检查 permissions 插件是否启用（运行时读取配置）"""
    try:
        from gyra_core.config import ConfigManager

        cfg = ConfigManager.get()
        entry = (cfg.feature_plugins or {}).get("permissions")
        if entry is None:
            return False
        if hasattr(entry, "enabled"):
            return bool(entry.enabled)
        if isinstance(entry, dict):
            return bool(entry.get("enabled"))
        return False
    except Exception:
        return False


def is_admin_user(user_id: Optional[int]) -> bool:
    """判断用户是否为 admin/superadmin(超管可见所有数据)。

    判定依据(任一命中即返回 True,全部失败兜底 False):
    1. RBAC 角色名含 ``admin`` / ``superadmin``(user_role 关联表,最可靠);
    2. 兼容存量:user 表 legacy ``role`` 列 == "admin"。

    全程防御式实现:权限表不存在 / 数据库异常时不抛错,视为非 admin。
    """
    if user_id is None:
        return False
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    try:
        from gyra_app.feature_plugins.permissions.service import PermissionService

        perms = PermissionService().get_user_permissions(uid)
        if "admin" in perms.role_names or "superadmin" in perms.role_names:
            return True
    except Exception as e:  # noqa: BLE001
        logger.debug(f"is_admin_user: RBAC role check failed for user {uid}: {e}")
    try:
        from gyra_app.auth.user_service import UserEntity
        from gyra.storage.metadata.db_manager import db

        with db.session(commit=False) as s:
            user_obj = s.query(UserEntity).filter(UserEntity.id == uid).first()
            if user_obj and user_obj.role == "admin":
                return True
    except Exception as e:  # noqa: BLE001
        logger.debug(f"is_admin_user: legacy role check failed for user {uid}: {e}")
    return False


def get_user_from_headers(
    request: Request = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None),
) -> UserRequest:
    """统一用户解析入口。

    permissions OFF: 返回 mock admin（开发模式，完全不变）
    permissions ON:  必须携带 gyra_session cookie 或 Bearer token，
                     验签失败 401（fail-closed，不接受 X-User-ID 自报身份）
    """
    try:
        if not _is_permissions_enabled():
            # ===== 插件关闭：保持现有行为 =====
            if x_user_id:
                return UserRequest(
                    user_id=x_user_id,
                    role="admin",
                    nick_name=x_user_id,
                    real_name=x_user_id,
                )
            return UserRequest(
                user_id="001",
                role="admin",
                nick_name="gyra",
                real_name="gyra",
            )

        # ===== 插件开启：验证 session（fail-closed） =====
        token = None
        if request:
            token = request.cookies.get("gyra_session")
        if not token and authorization:
            token = authorization.replace("Bearer ", "")
        if not token:
            logger.warning("[auth] No session token found - rejecting with 401")
            raise HTTPException(status_code=401, detail="Authentication required")

        from gyra_app.auth.session import verify_session_token

        user_data = verify_session_token(token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        # 加载用户权限（带 60s 缓存）
        from gyra_app.feature_plugins.permissions.service import PermissionService

        user_id = user_data.get("id", 0)
        perms = PermissionService().get_user_permissions(user_id)

        # 获取用户的 role 字段与启用状态（从数据库）
        # is_active != 1(被禁用/软删)直接 401——无状态 HMAC token 本身
        # 不携带启用状态,必须每请求核对,否则禁用用户的旧 token 仍可用。
        user_role = "normal"
        try:
            from gyra_app.auth.user_service import UserEntity
            from gyra.storage.metadata.db_manager import db

            with db.session(commit=False) as s:
                user_obj = s.query(UserEntity).filter(UserEntity.id == user_id).first()
        except Exception:
            user_obj = None
        if user_obj is None or getattr(user_obj, "is_active", 1) != 1:
            raise HTTPException(status_code=401, detail="Account disabled or deleted")
        if user_obj.role:
            user_role = user_obj.role

        return UserRequest(
            user_id=str(user_data.get("name", "")),
            user_no=str(user_data.get("id", "")),
            real_name=user_data.get("name", ""),
            nick_name=user_data.get("fullname", "") or user_data.get("name", ""),
            email=user_data.get("email", ""),
            avatar_url=user_data.get("avatar", ""),
            role=user_role,
            permissions=perms.permissions_map,
            deny_permissions=perms.deny_map,
            roles=perms.role_names,
            grants=perms.grants,
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Authentication failed!")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")