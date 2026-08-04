"""Agent 职能角色 API 端点 —— 分配 / 查询 / 团队装配 / 成熟度校验。

路由前缀由 workspace serve 挂载:
    GET  /agent_roles/list              列出 workspace 下所有角色分配
    POST /agent_roles/assign            分配/更新角色(幂等)
    GET  /agent_roles/{agent_id}        查询 agent 角色
    GET  /agent_roles/{agent_id}/check  校验 agent 成熟度是否满足角色要求
    POST /agent_roles/assemble_team     按 Playbook declaration 装配团队蓝图
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra._private.pydantic import BaseModel, Field
from gyra.component import SystemApp
from gyra_serve.core import Result

from .config import ServeConfig
from .agent_roles import (
    AGENT_ROLE_SERVICE_COMPONENT_NAME,
    AgentRole,
    AgentRoleService,
)

router = APIRouter()
global_system_app: Optional[SystemApp] = None
logger = logging.getLogger(__name__)

get_bearer_token = HTTPBearer(auto_error=False)


def get_service() -> AgentRoleService:
    if global_system_app is None:
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "System app not initialized"}},
        )
    return global_system_app.get_component(
        AGENT_ROLE_SERVICE_COMPONENT_NAME, AgentRoleService
    )


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: AgentRoleService = Depends(get_service),
) -> Optional[str]:
    if service.config.api_keys:
        api_keys = [k.strip() for k in service.config.api_keys.split(",")]
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(status_code=401, detail="invalid api key")
        return token
    return None


# --------------------------------------------------------------------------- #
# 请求 schemas
# --------------------------------------------------------------------------- #
class AgentRoleAssignRequest(BaseModel):
    agent_id: str = Field(..., description="被分配的 agent id")
    role: str = Field(..., description="角色: fetcher/analyzer/reporter/coordinator/reviewer")
    workspace_id: int = Field(..., description="workspace ID")


class AssembleTeamRequest(BaseModel):
    workspace_id: int = Field(..., description="workspace ID")
    declaration: Optional[Dict[str, Any]] = Field(
        None, description="Playbook declaration(含 roles 块)"
    )


# --------------------------------------------------------------------------- #
# 端点
# 注意: /list 必须在 /{agent_id} 之前声明
# --------------------------------------------------------------------------- #
@router.get(
    "/agent_roles/list",
    dependencies=[Depends(check_api_key)],
)
async def list_roles(
    workspace_id: int,
    service: AgentRoleService = Depends(get_service),
) -> Result:
    """列出 workspace 下所有 agent 角色分配。"""
    try:
        entities = service.dao.list_by_workspace(workspace_id)
        return Result.succ([service.dao.to_response(e) for e in entities])
    except Exception as e:
        logger.exception("agent_roles list exception!")
        return Result.failed(str(e))


@router.post(
    "/agent_roles/assign",
    dependencies=[Depends(check_api_key)],
)
async def assign_role(
    request: AgentRoleAssignRequest,
    service: AgentRoleService = Depends(get_service),
) -> Result:
    """分配/更新 agent 角色(幂等 upsert)。"""
    try:
        role = AgentRole(request.role)
    except ValueError:
        return Result.failed(f"invalid role: {request.role}")
    try:
        assignment = service.assign_role(
            agent_id=request.agent_id, role=role, workspace_id=request.workspace_id
        )
        return Result.succ({
            "agent_id": assignment.agent_id,
            "role": assignment.role.value,
            "workspace_id": assignment.workspace_id,
        })
    except Exception as e:
        logger.exception("agent_roles assign exception!")
        return Result.failed(str(e))


@router.get(
    "/agent_roles/{agent_id}",
    dependencies=[Depends(check_api_key)],
)
async def get_role(
    agent_id: str,
    workspace_id: int,
    service: AgentRoleService = Depends(get_service),
) -> Result:
    """查询 agent 在 workspace 中的角色。"""
    try:
        role = service.get_role(agent_id=agent_id, workspace_id=workspace_id)
        return Result.succ({"agent_id": agent_id, "role": role.value if role else None})
    except Exception as e:
        logger.exception("agent_roles get exception!")
        return Result.failed(str(e))


@router.get(
    "/agent_roles/{agent_id}/check",
    dependencies=[Depends(check_api_key)],
)
async def check_maturity(
    agent_id: str,
    workspace_id: int,
    role: str,
    service: AgentRoleService = Depends(get_service),
) -> Result:
    """校验 agent 成熟度是否满足指定角色要求。"""
    try:
        target_role = AgentRole(role)
    except ValueError:
        return Result.failed(f"invalid role: {role}")
    try:
        result = service.validate_maturity(
            agent_id=agent_id, role=target_role, workspace_id=workspace_id
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("agent_roles check_maturity exception!")
        return Result.failed(str(e))


@router.post(
    "/agent_roles/assemble_team",
    dependencies=[Depends(check_api_key)],
)
async def assemble_team(
    request: AssembleTeamRequest,
    service: AgentRoleService = Depends(get_service),
) -> Result:
    """按 Playbook declaration 的 roles 块装配团队蓝图。"""
    try:
        team = service.assemble_team(
            playbook_declaration=request.declaration,
            workspace_id=request.workspace_id,
        )
        return Result.succ(team)
    except Exception as e:
        logger.exception("agent_roles assemble_team exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    """注册 AgentRoleService 并绑定 global_system_app。"""
    global global_system_app
    system_app.register(AgentRoleService, config=config)
    global_system_app = system_app
