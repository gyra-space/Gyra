"""统一权限校验入口：按协议 key 校验，支持资源实例级 grant。

用法::

    from gyra_serve.permissions import require

    @router.post("/tasks", dependencies=[Depends(require("space.task.start"))])
    async def start_task(...): ...

判定顺序（fail-closed，插件开启时）：
1. permissions 插件关闭 -> 开发模式放行（user.permissions 为 None）
2. legacy user.role == "admin" / superadmin 角色 -> 放行
3. 角色权限：精确 resource_id -> 通配 -> "admin" 动作覆盖
4. 资源实例级 grant（resource_grant 表，含时效判定）
5. 全部未命中 -> 403
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request

from gyra_serve.utils.auth import UserRequest, get_user_from_headers

from .protocol import PermissionRegistry, parse_key


def _grant_allows(grant: dict, permission_key: str, resource_id: Optional[str]) -> bool:
    if grant.get("permission_key") != permission_key:
        return False
    granted_rid = grant.get("resource_id")
    return granted_rid == "*" or (
        resource_id is not None and granted_rid == str(resource_id)
    )


def has(
    user: UserRequest,
    permission_key: str,
    resource_id: Optional[str] = None,
) -> bool:
    """同步判定（非 FastAPI 依赖），供 service 层/工具派发层复用。"""
    if PermissionRegistry.get(permission_key) is None:
        # 未注册的 key 一律拒绝（fail-closed，防拼写绕过）
        return False
    resource_type, action = parse_key(permission_key)

    if user.permissions is None:  # 插件关闭（开发模式）
        return True
    if user.role == "admin":  # legacy 兼容
        return True
    if "superadmin" in (user.roles or []):
        return True

    # 角色权限
    if resource_id and resource_id != "*":
        scoped = user.permissions.get(f"{resource_type}:{resource_id}", [])
        if action in scoped or "admin" in scoped:
            return True
    allowed = user.permissions.get(resource_type, [])
    wildcard = user.permissions.get("*", [])
    if action in allowed or "admin" in allowed or action in wildcard or "admin" in wildcard:
        return True

    # 资源实例级 grant
    for grant in user.grants or []:
        if _grant_allows(grant, permission_key, resource_id):
            return True
    return False


def require(permission_key: str, resource_id: Optional[str] = None):
    """FastAPI 依赖工厂：校验协议权限 key。"""
    if PermissionRegistry.get(permission_key) is None:
        raise ValueError(
            f"Unknown permission key {permission_key!r}: "
            "not registered by any PermissionModule"
        )

    def dependency(
        user: UserRequest = Depends(get_user_from_headers),
    ) -> UserRequest:
        if has(user, permission_key, resource_id=resource_id):
            return user
        target = f"{permission_key} (resource={resource_id})" if resource_id else permission_key
        raise HTTPException(status_code=403, detail=f"Permission denied: {target}")

    return dependency


# --------------------------------------------------------------------------- #
# 空间域判定（scope_type=space 的权限按 workspace 判定）
# --------------------------------------------------------------------------- #
# 内置空间角色名 -> workspace_member.role 字符串（迁移前/插件关闭时的兜底映射）
_SPACE_ROLE_FALLBACK = {
    "owner": "space.admin",
    "contributor": "space.member",
    "viewer": "space.viewer",
}


def _fallback_space_keys(role_str: Optional[str]) -> set:
    """按 workspace_member.role 字符串取内置空间角色权限集（无 DB 依赖）。"""
    from .modules.space import SPACE_ALL, SPACE_MEMBER_KEYS, SPACE_VIEWER_KEYS

    key = _SPACE_ROLE_FALLBACK.get(role_str or "")
    if key == "space.admin":
        return set(SPACE_ALL)
    if key == "space.member":
        return set(SPACE_MEMBER_KEYS)
    if key == "space.viewer":
        return set(SPACE_VIEWER_KEYS)
    return set()


def _load_scoped_keys(user_no: int, workspace_id: int) -> set:
    """加载用户在该空间绑定的（含自定义）角色的全部权限 key。"""
    from gyra_app.feature_plugins.permissions.dao import PermissionDao

    dao = PermissionDao()
    keys: set = set()
    try:
        roles = dao.get_scoped_user_roles(user_no, scope_id=workspace_id)
    except Exception:
        roles = []
    for perm in dao.get_permissions_for_roles([r["id"] for r in roles] or [0]):
        if perm.get("effect") != "allow":
            continue
        keys.add(f"{perm['resource_type']}.{perm['action']}")
    return keys


def has_scope(
    user: UserRequest,
    permission_key: str,
    workspace_id: Optional[int],
) -> bool:
    """空间域判定：用户在该 workspace 上是否拥有 space.* 权限。

    优先级：
    1. 开发模式（permissions 插件关闭）：退回 workspace_member.role 内置矩阵
    2. 全局 admin/superadmin（或 legacy admin）：放行（全局管理员）
    3. 该空间上绑定的角色权限（user_role.scope_id=workspace_id，支持自定义角色）
    4. 兜底：workspace_member.role 映射内置空间角色（迁移未跑时的安全网）
    5. 未命中 -> 拒绝（fail-closed；解析不出 workspace_id 也拒绝）
    """
    if PermissionRegistry.get(permission_key) is None:
        return False

    # 解析用户数字 ID（DB user.id）
    user_no = None
    for raw in (user.user_no, user.user_id):
        if raw is None or raw == "":
            continue
        try:
            user_no = int(str(raw).strip())
            break
        except (TypeError, ValueError):
            continue

    if user.permissions is None:
        # 开发模式（插件关闭）：沿用空间成员角色矩阵，保持本地行为可预期
        if workspace_id is None or user_no is None:
            return True
        try:
            from gyra_serve.workspace.models.models import WorkspaceMemberDao

            role_str = WorkspaceMemberDao().get_role(workspace_id, user_no)
        except Exception:
            role_str = None
        return permission_key in _fallback_space_keys(role_str)

    if workspace_id is None:
        return False  # fail-closed：解析不出空间上下文即拒绝

    # 全局管理员短路
    if user.role == "admin" or "superadmin" in (user.roles or []):
        return True
    if "admin" in (user.roles or []):
        return True

    if user_no is None:
        return False

    # 空间绑定的角色权限（含自定义角色）
    if permission_key in _load_scoped_keys(user_no, workspace_id):
        return True

    # 兜底：成员表 role 字符串映射（迁移未跑时不至于全员锁死）
    try:
        from gyra_serve.workspace.models.models import WorkspaceMemberDao

        role_str = WorkspaceMemberDao().get_role(workspace_id, user_no)
    except Exception:
        role_str = None
    return permission_key in _fallback_space_keys(role_str)


def require_space(permission_key: str):
    """FastAPI 依赖工厂：校验空间域权限（自动从请求解析 workspace_id）。

    workspace_id 解析复用 workspace/rbac.py 的成熟逻辑
    （path/body 直传 + task/intervention/asset/resource/code 反查）。
    """
    if PermissionRegistry.get(permission_key) is None:
        raise ValueError(
            f"Unknown permission key {permission_key!r}: "
            "not registered by any PermissionModule"
        )

    async def dependency(
        request: Request,
        user: UserRequest = Depends(get_user_from_headers),
    ) -> UserRequest:
        from gyra_serve.workspace.rbac import _resolve_workspace_id

        workspace_id = await _resolve_workspace_id(request)
        if has_scope(user, permission_key, workspace_id):
            return user
        target = (
            f"{permission_key} (workspace={workspace_id})"
            if workspace_id is not None
            else permission_key
        )
        raise HTTPException(status_code=403, detail=f"Permission denied: {target}")

    return dependency


# --------------------------------------------------------------------------- #
# 会话归属判定（个人会话按创建者，空间会话按空间可见性）
# --------------------------------------------------------------------------- #
def _conv_workspace_id(conv_uid: str) -> Optional[int]:
    """会话若挂在某个空间上，返回 workspace_id；否则 None。"""
    try:
        from gyra.storage.metadata.db_manager import db
        from gyra_serve.workspace.models.models import WorkspaceConversationLinkEntity

        with db.session(commit=False) as s:
            row = (
                s.query(WorkspaceConversationLinkEntity)
                .filter(WorkspaceConversationLinkEntity.conv_uid == conv_uid)
                .first()
            )
            return row.workspace_id if row else None
    except Exception:
        return None


def _conv_owner_user_id(conv_uid: str) -> Optional[str]:
    """个人会话创建者：chat_history.user_name / gpts_conversations.user_code。"""
    try:
        from gyra.storage.metadata.db_manager import db

        with db.session(commit=False) as s:
            from gyra.storage.chat_history.chat_history_db import ChatHistoryEntity

            row = (
                s.query(ChatHistoryEntity)
                .filter(ChatHistoryEntity.conv_uid == conv_uid)
                .first()
            )
            if row and row.user_name:
                return str(row.user_name)
            from gyra_serve.agent.db.gpts_conversations_db import (
                GptsConversationsEntity,
            )

            row2 = (
                s.query(GptsConversationsEntity)
                .filter(GptsConversationsEntity.conv_id == conv_uid)
                .first()
            )
            if row2 and row2.user_code:
                return str(row2.user_code)
    except Exception:
        pass
    return None


def can_read_conversation(
    user: UserRequest,
    conv_uid: str,
    owner_user_id: Optional[str] = None,
    allow_unknown_owner: bool = False,
) -> bool:
    """会话读取归属判定。

    开发模式（插件关闭）放行；否则：
    1. 全局管理员放行；
    2. 空间会话：对所属空间有任意可见性（space.workspace.view）即放行；
    3. 个人会话：仅创建者本人（比对 user_id 名字串与 user_no 数字串）；
    4. 归属完全未知的会话（如 agent 子会话不在会话主表）：
       allow_unknown_owner=True 时对已登录用户放行（chat_query 轮询链路），
       否则拒绝（fail-closed）。
    """
    if user.permissions is None:
        return True
    if _is_privileged(user):
        return True

    workspace_id = _conv_workspace_id(conv_uid)
    if workspace_id is not None:
        return has_scope(user, "space.workspace.view", workspace_id)

    owner = owner_user_id if owner_user_id is not None else _conv_owner_user_id(conv_uid)
    if owner is None:
        return allow_unknown_owner
    owner = str(owner)
    return owner in (str(user.user_id or ""), str(user.user_no or ""))


# --------------------------------------------------------------------------- #
# 文件归属判定（uploader / metadata 中的 workspace、conv、task 归属链）
# --------------------------------------------------------------------------- #
def _load_file_row(bucket: str, file_id: str):
    try:
        from gyra.storage.metadata.db_manager import db
        from gyra_serve.file.models.models import ServeEntity

        with db.session(commit=False) as s:
            return (
                s.query(ServeEntity)
                .filter(
                    ServeEntity.bucket == bucket,
                    ServeEntity.file_id == file_id,
                )
                .first()
            )
    except Exception:
        return None


def _file_workspace_id(row) -> Optional[int]:
    """从文件元数据解析归属空间：workspace_id 直取，或 conv/task 反查。"""
    import json as _json

    meta = {}
    try:
        meta = _json.loads(row.custom_metadata) if row.custom_metadata else {}
    except Exception:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    for key in ("workspace_id", "ws_id"):
        raw = meta.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    for key in ("conv_uid", "conv_id"):
        raw = meta.get(key)
        if raw:
            ws = _conv_workspace_id(str(raw))
            if ws is not None:
                return ws
    raw = meta.get("task_id")
    if raw is not None:
        try:
            from gyra_serve.workspace.rbac import _lookup_workspace_id_by_task

            return _lookup_workspace_id_by_task(int(raw))
        except (TypeError, ValueError):
            pass
    return None


def _is_privileged(user: UserRequest) -> bool:
    return (
        user.role == "admin"
        or "admin" in (user.roles or [])
        or "superadmin" in (user.roles or [])
    )


def _file_conv_owner(row) -> Optional[str]:
    import json as _json

    meta = {}
    try:
        meta = _json.loads(row.custom_metadata) if row.custom_metadata else {}
    except Exception:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    for key in ("conv_uid", "conv_id", "session_id"):
        raw = meta.get(key)
        if raw:
            owner = _conv_owner_user_id(str(raw))
            if owner:
                return owner
    return None


def can_read_file(user: UserRequest, bucket: str, file_id: str) -> bool:
    """文件读取归属判定：开发模式/管理员放行；否则按
    空间归属(space.file.read) -> 上传者本人 -> 个人会话创建者 -> 拒绝。"""
    if user.permissions is None or _is_privileged(user):
        return True
    row = _load_file_row(bucket, file_id)
    if row is None:
        return False
    ws_id = _file_workspace_id(row)
    if ws_id is not None and has_scope(user, "space.file.read", ws_id):
        return True
    uploader = str(row.user_name or "")
    if uploader and uploader in (
        str(user.user_id or ""),
        str(user.user_no or ""),
    ):
        return True
    if ws_id is None:
        owner = _file_conv_owner(row)
        if owner and owner in (str(user.user_id or ""), str(user.user_no or "")):
            return True
    return False


def can_delete_file(user: UserRequest, bucket: str, file_id: str) -> bool:
    """文件删除判定：开发模式/管理员放行；否则按
    空间归属(space.workspace.manage) -> 上传者本人 -> 个人会话创建者 -> 拒绝。"""
    if user.permissions is None or _is_privileged(user):
        return True
    row = _load_file_row(bucket, file_id)
    if row is None:
        return False
    ws_id = _file_workspace_id(row)
    if ws_id is not None and has_scope(user, "space.workspace.manage", ws_id):
        return True
    uploader = str(row.user_name or "")
    if uploader and uploader in (
        str(user.user_id or ""),
        str(user.user_no or ""),
    ):
        return True
    if ws_id is None:
        owner = _file_conv_owner(row)
        if owner and owner in (str(user.user_id or ""), str(user.user_no or "")):
            return True
    return False
