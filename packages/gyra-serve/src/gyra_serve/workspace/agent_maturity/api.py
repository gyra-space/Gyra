"""Agent 成长模型 API 端点。"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra._private.pydantic import BaseModel, Field
from gyra.component import SystemApp
from gyra_serve.core import Result

from ..config import ServeConfig
from .service import (
    AGENT_MATURITY_SERVICE_COMPONENT_NAME,
    AgentMaturityService,
    AgentStage,
)

router = APIRouter()
global_system_app: Optional[SystemApp] = None
logger = logging.getLogger(__name__)

get_bearer_token = HTTPBearer(auto_error=False)


def get_service() -> AgentMaturityService:
    if global_system_app is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "System app not initialized",
                    "type": "internal_error",
                }
            },
        )
    return global_system_app.get_component(
        AGENT_MATURITY_SERVICE_COMPONENT_NAME, AgentMaturityService
    )


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: AgentMaturityService = Depends(get_service),
) -> Optional[str]:
    if service.config.api_keys:
        api_keys = [k.strip() for k in service.config.api_keys.split(",")]
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "",
                        "type": "invalid_request_error",
                        "param": None,
                        "code": "invalid_api_key",
                    }
                },
            )
        return token
    return None


# --------------------------------------------------------------------------- #
# 请求 schemas
# --------------------------------------------------------------------------- #
class AgentAttestRequest(BaseModel):
    """agent 级背书请求"""
    user_id: str = Field(..., description="背书人 user_id")
    workspace_id: int = Field(..., description="workspace ID")


class AgentPromoteRequest(BaseModel):
    """手动晋升请求(管理员)"""
    to_stage: str = Field(
        ..., description="目标阶段: novice/proficient/expert/master"
    )
    actor: str = Field(..., description="操作人 user_id")
    workspace_id: int = Field(..., description="workspace ID")
    force: bool = Field(
        False, description="是否跳过规则校验(管理员强制晋升)"
    )


class AgentRecalculateRequest(BaseModel):
    """重新计算评分请求"""
    workspace_id: int = Field(..., description="workspace ID")


# --------------------------------------------------------------------------- #
# 端点
# 注意: /list 必须在 /{agent_id} 之前声明, 否则会被当作 agent_id="list" 匹配
# --------------------------------------------------------------------------- #
@router.get(
    "/agent_maturity/list",
    response_model=Result,
    dependencies=[Depends(check_api_key)],
)
async def list_agent_maturity(
    workspace_id: int = Query(..., description="workspace ID"),
    stage: Optional[str] = Query(
        None, description="按阶段过滤: novice/proficient/expert/master"
    ),
    service: AgentMaturityService = Depends(get_service),
) -> Result:
    """列出 workspace 的 agent 成长状态。"""
    try:
        result = service.list_by_workspace(workspace_id, stage=stage)
        return Result.succ(result)
    except Exception as e:
        logger.exception("agent maturity list exception!")
        return Result.failed(str(e))


@router.get(
    "/agent_maturity/{agent_id}",
    response_model=Result,
    dependencies=[Depends(check_api_key)],
)
async def get_agent_maturity(
    agent_id: str,
    workspace_id: int = Query(..., description="workspace ID"),
    service: AgentMaturityService = Depends(get_service),
) -> Result:
    """查看 agent 成长状态(阶段/评分/权限/背书)。"""
    try:
        result = service.get_maturity(agent_id, workspace_id)
        if result is None:
            return Result.failed(
                f"agent maturity record not found: {agent_id}"
            )
        return Result.succ(result)
    except Exception as e:
        logger.exception("agent maturity get exception!")
        return Result.failed(str(e))


@router.post(
    "/agent_maturity/{agent_id}/attest",
    response_model=Result,
    dependencies=[Depends(check_api_key)],
)
async def attest_agent(
    agent_id: str,
    request: AgentAttestRequest,
    service: AgentMaturityService = Depends(get_service),
) -> Result:
    """agent 级背书(expert→master 需 N 人背书)。"""
    try:
        result = await service.attest_agent(
            agent_id=agent_id,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("agent maturity attest exception!")
        return Result.failed(str(e))


@router.post(
    "/agent_maturity/{agent_id}/promote",
    response_model=Result,
    dependencies=[Depends(check_api_key)],
)
async def promote_agent(
    agent_id: str,
    request: AgentPromoteRequest,
    service: AgentMaturityService = Depends(get_service),
) -> Result:
    """手动晋升 agent(管理员)。"""
    try:
        try:
            to_stage = AgentStage(request.to_stage)
        except ValueError:
            return Result.failed(
                f"invalid stage: {request.to_stage}, "
                f"expected: {[s.value for s in AgentStage]}"
            )
        result = await service.promote(
            agent_id=agent_id,
            to_stage=to_stage,
            actor=request.actor,
            workspace_id=request.workspace_id,
            force=request.force,
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("agent maturity promote exception!")
        return Result.failed(str(e))


@router.post(
    "/agent_maturity/{agent_id}/recalculate",
    response_model=Result,
    dependencies=[Depends(check_api_key)],
)
async def recalculate_agent(
    agent_id: str,
    request: AgentRecalculateRequest,
    service: AgentMaturityService = Depends(get_service),
) -> Result:
    """重新采集信号并计算评分。"""
    try:
        result = service.recalculate(agent_id, request.workspace_id)
        return Result.succ(result)
    except Exception as e:
        logger.exception("agent maturity recalculate exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    """注册 AgentMaturityService 并绑定 global_system_app。"""
    global global_system_app
    system_app.register(AgentMaturityService, config=config)
    global_system_app = system_app
