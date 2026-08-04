"""RBAC 强校验 —— 角色 / 权限 / FastAPI 依赖。

P2 任务9: 收紧 25 个写端点的角色校验,viewer 理论上不能再 start_task 等。

向后兼容:默认不启用。仅当环境变量 ``GYRA_RBAC_ENABLED`` (或 ``RBAC_ENABLED``)
为真时校验;未启用时所有 ``require_permission`` 依赖直接放行,行为与无 RBAC 完全
一致,存量调用零迁移。

角色层次(与 workspace_member.role 字符串对齐):
    OWNER > APPROVER > CONTRIBUTOR > VIEWER
- OWNER:       全权限(空间所有者)
- APPROVER:    启动任务 / 解决介入 / 发布资产 / 建剧本 / 背书 / coach / 升级
- CONTRIBUTOR: 启动任务 / 发布资产 / 建剧本
- VIEWER:      只读(无写权限)
"""
import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, Request

from .models.models import WorkspaceDao, WorkspaceEntity, WorkspaceMemberDao

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """空间成员角色(值与 workspace_member.role 列存储字符串一致)。"""

    OWNER = "owner"
    APPROVER = "approver"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class Permission(str, Enum):
    """受 RBAC 管控的写权限。"""

    START_TASK = "start_task"
    RESOLVE_INTERVENTION = "resolve_intervention"
    PUBLISH_ASSET = "publish_asset"
    UPDATE_WORKSPACE = "update_workspace"
    CREATE_PLAYBOOK = "create_playbook"
    DELETE_ASSET = "delete_asset"
    ATTEST = "attest"
    COACH = "coach"
    ESCALATE = "escalate"


ROLE_PERMISSIONS: Dict[Role, set] = {
    Role.OWNER: set(Permission),  # 所有权限
    Role.APPROVER: {
        Permission.START_TASK,
        Permission.RESOLVE_INTERVENTION,
        Permission.PUBLISH_ASSET,
        Permission.CREATE_PLAYBOOK,
        Permission.ATTEST,
        Permission.COACH,
        Permission.ESCALATE,
    },
    Role.CONTRIBUTOR: {
        Permission.START_TASK,
        Permission.PUBLISH_ASSET,
        Permission.CREATE_PLAYBOOK,
    },
    Role.VIEWER: set(),  # 无写权限
}


def _rbac_enabled() -> bool:
    """RBAC 是否启用。环境变量 GYRA_RBAC_ENABLED / RBAC_ENABLED = true 时启用。"""
    val = os.environ.get("GYRA_RBAC_ENABLED") or os.environ.get("RBAC_ENABLED")
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
    """检查 user 是否在 workspace 中拥有指定权限。"""
    role = get_user_role(workspace_id, user_id)
    return permission in ROLE_PERMISSIONS.get(role, set())


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


async def _resolve_workspace_id(request: Request) -> Optional[int]:
    """从请求路径参数 / JSON body 中解析 workspace_id。

    解析优先级:
      1. path_params.workspace_id (直接)
      2. body.workspace_id (直接)
      3. path_params.task_id -> Task 反查
      4. path_params.intervention_id -> Intervention 反查
      5. body.asset_id -> Asset 反查
      6. body.workspace_code -> Workspace 反查

    body 读取失败(非 JSON / 空 body / multipart)时静默降级为无可解析 body。
    """
    path_params = dict(request.path_params or {})

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

    # 3. path 中的 task_id
    task_id = path_params.get("task_id")
    if task_id is not None:
        try:
            ws_id = _lookup_workspace_id_by_task(int(task_id))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by task failed: {e}")

    # 4. path 中的 intervention_id
    intervention_id = path_params.get("intervention_id")
    if intervention_id is not None:
        try:
            ws_id = _lookup_workspace_id_by_intervention(int(intervention_id))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by intervention failed: {e}")

    # 5. body 中的 asset_id
    if body.get("asset_id") is not None:
        try:
            ws_id = _lookup_workspace_id_by_asset(int(body["asset_id"]))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by asset failed: {e}")

    # 6. body 中的 workspace_code
    ws_code = body.get("workspace_code")
    if ws_code:
        try:
            ws_id = _lookup_workspace_id_by_code(str(ws_code))
            if ws_id is not None:
                return ws_id
        except Exception as e:
            logger.warning(f"rbac resolve workspace by code failed: {e}")

    return None


def _resolve_user_id(header_user_id: Optional[int], body: Dict[str, Any]) -> Optional[int]:
    """解析调用者 user_id:优先 X-User-ID 头,其次 body 中的常见字段。"""
    if header_user_id is not None:
        try:
            return int(header_user_id)
        except (TypeError, ValueError):
            pass
    for key in ("user_id", "resolved_by_user_id", "actor"):
        val = body.get(key)
        if val is None:
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return None


def require_permission(permission: Permission):
    """返回 FastAPI 路由依赖,校验当前请求用户是否拥有指定权限。

    用法: ``dependencies=[Depends(require_permission(Permission.START_TASK))]``

    行为:
    - RBAC 未启用: 直接放行(向后兼容)。
    - RBAC 启用但无法解析 workspace_id / user_id: 放行(不阻断无 header 的存量调用)。
    - RBAC 启用且权限不足: 抛 403。
    """

    async def _dependency(
        request: Request,
        user_id: Optional[int] = Header(None, alias="X-User-ID"),
    ):
        if not _rbac_enabled():
            return  # 未启用 RBAC,放行

        workspace_id = await _resolve_workspace_id(request)
        if workspace_id is None:
            # 无法解析上下文:向后兼容,不阻断
            return

        # body 已被 _resolve_workspace_id 读取并缓存(Starlette 缓存 _body),
        # 这里复用缓存以提取 user_id 兜底字段
        body: Dict[str, Any] = {}
        try:
            parsed = await request.json()
            if isinstance(parsed, dict):
                body = parsed
        except Exception:
            body = {}

        caller_uid = _resolve_user_id(user_id, body)
        if caller_uid is None:
            # 无法识别调用者:向后兼容,不阻断
            return

        if not check_permission(workspace_id, caller_uid, permission):
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
