"""RBAC 强校验 —— 角色 / 权限 / FastAPI 依赖。

空间域权限已统一到权限协议(gyra_serve.permissions):本模块的 Permission
枚举映射到协议 key(PERMISSION_TO_KEY),判定走 has_scope()
(全局管理员短路 -> user_role 空间绑定角色 -> 成员表兜底映射)。

默认启用校验。环境变量 ``GYRA_RBAC_ENABLED`` (或 ``RBAC_ENABLED``) = false 可
关闭(迁移/调试用);关闭时所有 ``require_permission`` 依赖直接放行,行为与无
RBAC 完全一致。

角色层次(与 workspace_member.role 字符串对齐,兜底映射用):
    OWNER -> space.admin       管理 -- 全权限
    CONTRIBUTOR -> space.member 使用(对话/任务/看产出)
    VIEWER -> space.viewer     查看 -- 只读
"""
import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request

from .models.models import WorkspaceDao, WorkspaceEntity, WorkspaceMemberDao

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """空间成员角色(值与 workspace_member.role 列存储字符串一致)。"""

    OWNER = "owner"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


# 角色 -> 中文显示名(供 API / 前端展示)。
ROLE_LABELS: Dict[Role, str] = {
    Role.OWNER: "管理",
    Role.CONTRIBUTOR: "使用",
    Role.VIEWER: "查看",
}


class Permission(str, Enum):
    """受 RBAC 管控的写权限。"""

    START_TASK = "start_task"
    RESOLVE_INTERVENTION = "resolve_intervention"
    PUBLISH_ASSET = "publish_asset"
    UPDATE_WORKSPACE = "update_workspace"
    CREATE_PLAYBOOK = "create_playbook"
    DELETE_ASSET = "delete_asset"
    DELETE_TASK = "delete_task"
    ATTEST = "attest"
    COACH = "coach"
    ESCALATE = "escalate"
    MANAGE_RESOURCE = "manage_resource"  # 维护空间资源(含 llm_model 空间专属模型/token)
    DELETE_WORKSPACE = "delete_workspace"  # 释放(软删除)空间 —— 危险操作,仅空间拥有者


ROLE_PERMISSIONS: Dict[Role, set] = {
    Role.OWNER: set(Permission),  # 所有权限(管理)
    Role.CONTRIBUTOR: {
        Permission.START_TASK,
        Permission.PUBLISH_ASSET,
        Permission.CREATE_PLAYBOOK,
    },
    Role.VIEWER: set(),  # 无写权限(查看)
}


# 旧 Permission 枚举 -> 统一权限协议 key（判定走 has_scope）
PERMISSION_TO_KEY: Dict[Permission, str] = {
    Permission.START_TASK: "space.task.start",
    Permission.RESOLVE_INTERVENTION: "space.task.manage",
    Permission.PUBLISH_ASSET: "space.asset.manage",
    Permission.UPDATE_WORKSPACE: "space.workspace.manage",
    Permission.CREATE_PLAYBOOK: "space.playbook.manage",
    Permission.DELETE_ASSET: "space.asset.manage",
    Permission.DELETE_TASK: "space.task.manage",
    Permission.ATTEST: "space.asset.manage",
    Permission.COACH: "space.asset.manage",
    Permission.ESCALATE: "space.task.manage",
    Permission.MANAGE_RESOURCE: "space.capability.manage",
    Permission.DELETE_WORKSPACE: "space.workspace.manage",
}


def _rbac_enabled() -> bool:
    """RBAC 是否启用。默认启用;环境变量 GYRA_RBAC_ENABLED / RBAC_ENABLED = false 时关闭。"""
    val = os.environ.get("GYRA_RBAC_ENABLED") or os.environ.get("RBAC_ENABLED")
    if val is None:
        return True
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def get_user_role(workspace_id: int, user_id: int) -> Role:
    """查询 user 在 workspace 中的角色。

    - 已登记为成员: 返回成员记录的 role(未知值降级 VIEWER)。
    - 未登记但为空间所有者(owner_user_id): 返回 OWNER。
    - 其余: 返回 VIEWER(无写权限)。
    """
    role_str = WorkspaceMemberDao().get_role(workspace_id, user_id)
    if role_str:
        try:
            return Role(role_str)
        except ValueError:
            logger.warning(
                f"unknown role '{role_str}' for user={user_id} ws={workspace_id}, "
                f"fallback VIEWER"
            )
            return Role.VIEWER

    # 未登记为成员: 检查是否为空间所有者
    session = WorkspaceDao().get_raw_session()
    try:
        ws = (
            session.query(WorkspaceEntity)
            .filter(WorkspaceEntity.id == workspace_id)
            .first()
        )
        if ws and ws.owner_user_id == user_id:
            return Role.OWNER
    finally:
        session.close()
    return Role.VIEWER


def check_permission(
    workspace_id: int, user_id: int, permission: Permission
) -> bool:
    """检查 user 是否在 workspace 中拥有指定权限（统一协议判定）。"""
    from gyra_serve.permissions import has_scope
    from gyra_serve.utils.auth import UserRequest, _is_permissions_enabled

    key = PERMISSION_TO_KEY[permission]

    user = UserRequest(user_id=str(user_id), user_no=str(user_id))
    if _is_permissions_enabled():
        # 插件开启:填充真实权限快照——否则 permissions=None 会被 has_scope
        # 当作开发模式,永远走成员表兜底、跳过 user_role 空间绑定与 deny
        try:
            from gyra_app.feature_plugins.permissions.service import (
                PermissionService,
            )

            perms = PermissionService().get_user_permissions(user_id)
            user = UserRequest(
                user_id=str(user_id),
                user_no=str(user_id),
                permissions=perms.permissions_map,
                deny_permissions=perms.deny_map,
                roles=perms.role_names,
                grants=perms.grants,
            )
        except Exception as e:
            logger.warning(f"load user permissions failed, fail-closed: {e}")
            return False
    return has_scope(user, key, workspace_id)


# --------------------------------------------------------------------------- #
# 请求上下文解析:从 FastAPI Request 中解析 workspace_id 与 user_id
# --------------------------------------------------------------------------- #
def _lookup_workspace_id_by_task(task_id: int) -> Optional[int]:
    """通过 task_id 反查 workspace_id(直接查实体,避免依赖 system_app)。"""
    from gyra_serve.task.models.models import TaskDao, TaskEntity

    session = TaskDao().get_raw_session()
    try:
        row = (
            session.query(TaskEntity)
            .filter(TaskEntity.id == task_id)
            .first()
        )
        return row.workspace_id if row else None
    finally:
        session.close()


def _lookup_workspace_id_by_intervention(intervention_id: int) -> Optional[int]:
    """通过 intervention_id 反查 workspace_id。"""
    from gyra_serve.intervention.models.models import (
        InterventionDao,
        InterventionEntity,
    )

    session = InterventionDao().get_raw_session()
    try:
        row = (
            session.query(InterventionEntity)
            .filter(InterventionEntity.id == intervention_id)
            .first()
        )
        return row.workspace_id if row else None
    finally:
        session.close()


def _lookup_workspace_id_by_asset(asset_id: int) -> Optional[int]:
    """通过 asset_id 反查 workspace_id。"""
    from gyra_serve.workspace_asset.models.models import (
        AssetDao,
        AssetEntity,
    )

    session = AssetDao().get_raw_session()
    try:
        row = (
            session.query(AssetEntity)
            .filter(AssetEntity.id == asset_id)
            .first()
        )
        return row.workspace_id if row else None
    finally:
        session.close()


def _lookup_workspace_id_by_resource(resource_id: int) -> Optional[int]:
    """通过 resource_id 反查 workspace_id。"""
    from gyra_serve.workspace.models.models import (
        WorkspaceResourceDao,
        WorkspaceResourceEntity,
    )

    session = WorkspaceResourceDao().get_raw_session()
    try:
        row = (
            session.query(WorkspaceResourceEntity)
            .filter(WorkspaceResourceEntity.id == resource_id)
            .first()
        )
        return row.workspace_id if row else None
    finally:
        session.close()


def _lookup_workspace_id_by_code(workspace_code: str) -> Optional[int]:
    """通过 workspace_code 反查 workspace_id。"""
    session = WorkspaceDao().get_raw_session()
    try:
        row = (
            session.query(WorkspaceEntity)
            .filter(WorkspaceEntity.workspace_code == workspace_code)
            .first()
        )
        return row.id if row else None
    finally:
        session.close()


def _lookup_workspace_id_by_playbook(playbook_id: int) -> Optional[int]:
    """通过 playbook_id 反查 workspace_id。"""
    from gyra_serve.playbook.models.models import PlaybookDao, PlaybookEntity

    session = PlaybookDao().get_raw_session()
    try:
        row = (
            session.query(PlaybookEntity)
            .filter(PlaybookEntity.id == playbook_id)
            .first()
        )
        return row.workspace_id if row else None
    finally:
        session.close()


async def _resolve_workspace_id(request: Request) -> Optional[int]:
    """从请求路径参数 / 查询参数 / JSON body 中解析 workspace_id。

    解析优先级:
      1. path_params.workspace_id (直接)
      2. body.workspace_id (直接)
      3. query.workspace_id (直接)
      4. path/query/body 中的 task_id -> Task 反查
      5. path_params.parent_task_id -> Task 反查
      6. path_params.intervention_id -> Intervention 反查
      7. body/path/query 中的 asset_id -> Asset 反查
      8. body/query 中的 workspace_code -> Workspace 反查
      9. path/query 中的 playbook_id -> Playbook 反查
      10. body.resource_id -> Resource 反查

    body 读取失败(非 JSON / 空 body / multipart)时静默降级为无可解析 body。
    """
    path_params = dict(request.path_params or {})
    query_params = dict(request.query_params or {})

    # 1. path 中的 workspace_id
    ws_id = path_params.get("workspace_id")
    if ws_id is not None:
        try:
            return int(ws_id)
        except (TypeError, ValueError):
            pass

    # 读取 body(Starlette 缓存 _body,后续端点解析 body 不受影响)
    body: Dict[str, Any] = {}
    try:
        parsed = await request.json()
        if isinstance(parsed, dict):
            body = parsed
    except Exception:
        body = {}

    # 2. body 中的 workspace_id
    if body.get("workspace_id") is not None:
        try:
            return int(body["workspace_id"])
        except (TypeError, ValueError):
            pass

    # 3. query 中的 workspace_id
    if query_params.get("workspace_id") is not None:
        try:
            return int(query_params["workspace_id"])
        except (TypeError, ValueError):
            pass

    def _task_lookup(raw) -> Optional[int]:
        try:
            return _lookup_workspace_id_by_task(int(raw))
        except (TypeError, ValueError):
            return None

    # 4. task_id: path / query / body
    task_id = path_params.get("task_id") or query_params.get("task_id")
    if task_id is not None:
        ws_id = _task_lookup(task_id)
        if ws_id is not None:
            return ws_id
    if body.get("task_id") is not None:
        ws_id = _task_lookup(body["task_id"])
        if ws_id is not None:
            return ws_id

    # 5. path 中的 parent_task_id (spawn 端点)
    parent_id = path_params.get("parent_task_id")
    if parent_id is not None:
        ws_id = _task_lookup(parent_id)
        if ws_id is not None:
            return ws_id

    # 6. path 中的 intervention_id
    intervention_id = path_params.get("intervention_id")
    if intervention_id is not None:
        try:
            ws_id = _lookup_workspace_id_by_intervention(int(intervention_id))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by intervention failed: {e}")

    # 7. asset_id: body / path / query
    def _asset_lookup(raw) -> Optional[int]:
        try:
            return _lookup_workspace_id_by_asset(int(raw))
        except (TypeError, ValueError):
            return None

    for asset_raw in (body.get("asset_id"), path_params.get("asset_id"), query_params.get("asset_id")):
        if asset_raw is not None:
            ws_id = _asset_lookup(asset_raw)
            if ws_id is not None:
                return ws_id

    # 8. workspace_code: body / query
    ws_code = body.get("workspace_code") or query_params.get("workspace_code")
    if ws_code:
        try:
            ws_id = _lookup_workspace_id_by_code(str(ws_code))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by code failed: {e}")

    # 9. playbook_id: path / query
    playbook_id = path_params.get("playbook_id") or query_params.get("playbook_id")
    if playbook_id is not None:
        try:
            ws_id = _lookup_workspace_id_by_playbook(int(playbook_id))
            if ws_id is not None:
                return ws_id
        except (TypeError, ValueError):
            pass

    # 10. body 中的 resource_id (资源管理端点 remove/update 用)
    resource_id = body.get("resource_id")
    if resource_id is not None:
        try:
            ws_id = _lookup_workspace_id_by_resource(int(resource_id))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by resource failed: {e}")

    return None


def require_permission(permission: Permission):
    """返回 FastAPI 路由依赖,校验当前请求用户是否拥有指定空间权限。

    用法: ``dependencies=[Depends(require_permission(Permission.START_TASK))]``

    行为:
    - RBAC 未启用(GYRA_RBAC_ENABLED=false): 直接放行(调试/迁移用)。
    - 身份:permissions 插件开启时必须持有效 session(fail-closed,401);
      插件关闭(开发模式)沿用 X-User-ID 自报身份 + 成员角色矩阵。
    - 权限不足 / 解析不出 workspace_id: 403(fail-closed)。
    """

    from gyra_serve.utils.auth import get_user_from_headers

    key = PERMISSION_TO_KEY[permission]

    async def _dependency(
        request: Request,
        user=Depends(get_user_from_headers),
    ):
        if not _rbac_enabled():
            return  # 未启用 RBAC,放行

        workspace_id = await _resolve_workspace_id(request)

        from gyra_serve.permissions import has_scope

        if not has_scope(user, key, workspace_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "message": (
                            f"permission denied: requires {permission.value}"
                        ),
                        "type": "permission_denied",
                        "permission": permission.value,
                    }
                },
            )

    return _dependency
