"""Intervention API endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra.component import SystemApp
from gyra_serve.core import Result

from .schemas import (
    AttestInterventionRequest, CoachInterventionRequest,
    EscalateInterventionRequest, InterventionListFilter,
    InterventionRequest, InterventionResolveRequest, InterventionResponse,
    ReconcileInterventionRequest,
)
from ..config import ServeConfig
from ..service.extended_modes import (
    EXTENDED_INTERVENTION_SERVICE_COMPONENT_NAME, ExtendedInterventionService,
)
from ..service.service import INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService
from gyra_serve.workspace.rbac import Permission, require_permission

router = APIRouter()
global_system_app: Optional[SystemApp] = None
logger = logging.getLogger(__name__)


def get_service() -> InterventionService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService)


def get_extended_service() -> ExtendedInterventionService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(
        EXTENDED_INTERVENTION_SERVICE_COMPONENT_NAME, ExtendedInterventionService
    )


get_bearer_token = HTTPBearer(auto_error=False)


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: InterventionService = Depends(get_service),
) -> Optional[str]:
    if service.config.api_keys:
        api_keys = [k.strip() for k in service.config.api_keys.split(",")]
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(status_code=401, detail="invalid api key")
        return token
    return None


@router.post("/interventions/create", response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def create_intervention(
    request: InterventionRequest, service: InterventionService = Depends(get_service),
) -> Result[InterventionResponse]:
    try:
        return Result.succ(service.create(request))
    except Exception as e:
        logger.exception("intervention create exception!")
        return Result.failed(str(e))


@router.post("/interventions/list", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def list_interventions(
    f: InterventionListFilter, service: InterventionService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.list_interventions(f))
    except Exception as e:
        logger.exception("intervention list exception!")
        return Result.failed(str(e))


@router.get("/interventions/info", response_model=Result[InterventionResponse],
            dependencies=[Depends(check_api_key)])
async def get_intervention(
    intervention_id: int = Query(...),
    service: InterventionService = Depends(get_service),
) -> Result[InterventionResponse]:
    try:
        result = service.get_by_id(intervention_id)
        if not result:
            return Result.failed(f"intervention {intervention_id} not found")
        return Result.succ(result)
    except Exception as e:
        logger.exception("intervention info exception!")
        return Result.failed(str(e))


@router.post("/interventions/{intervention_id}/resolve",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key),
                           Depends(require_permission(Permission.RESOLVE_INTERVENTION))])
async def resolve_intervention(
    intervention_id: int, request: InterventionResolveRequest,
    service: InterventionService = Depends(get_service),
) -> Result[InterventionResponse]:
    try:
        return Result.succ(service.resolve(intervention_id, request))
    except Exception as e:
        logger.exception("intervention resolve exception!")
        return Result.failed(str(e))


@router.post("/interventions/{intervention_id}/abort",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def abort_intervention(
    intervention_id: int, service: InterventionService = Depends(get_service),
) -> Result[InterventionResponse]:
    try:
        return Result.succ(service.abort(intervention_id))
    except Exception as e:
        logger.exception("intervention abort exception!")
        return Result.failed(str(e))


@router.post("/interventions/{intervention_id}/resolve-and-execute",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def resolve_and_execute(
    intervention_id: int, request: InterventionResolveRequest,
    service: InterventionService = Depends(get_service),
) -> Result[InterventionResponse]:
    try:
        entity = await service.execute_resolved(
            intervention_id=intervention_id,
            decision=request.decision,
            distillation=request.distillation,
            resolved_by_user_id=request.resolved_by_user_id,
        )
        return Result.succ(service.dao.to_response(entity))
    except Exception as e:
        logger.exception("intervention resolve-and-execute exception!")
        return Result.failed(str(e))


# --------------------------------------------------------------------------- #
# 扩展介入模式(P1任务7): coach / escalate / reconcile / attest
# --------------------------------------------------------------------------- #
@router.post("/interventions/coach",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def create_coach_intervention(
    request: CoachInterventionRequest,
    extended_service: ExtendedInterventionService = Depends(get_extended_service),
) -> Result[InterventionResponse]:
    """创建coach纠偏介入(非阻塞,联动成熟度降级)。"""
    try:
        return Result.succ(await extended_service.create_coach(request))
    except Exception as e:
        logger.exception("intervention coach exception!")
        return Result.failed(str(e))


@router.post("/interventions/escalate",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def create_escalate_intervention(
    request: EscalateInterventionRequest,
    extended_service: ExtendedInterventionService = Depends(get_extended_service),
) -> Result[InterventionResponse]:
    """创建escalate升级介入(可能阻塞,等待转交确认)。"""
    try:
        return Result.succ(await extended_service.create_escalate(request))
    except Exception as e:
        logger.exception("intervention escalate exception!")
        return Result.failed(str(e))


@router.post("/interventions/reconcile",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def create_reconcile_intervention(
    request: ReconcileInterventionRequest,
    extended_service: ExtendedInterventionService = Depends(get_extended_service),
) -> Result[InterventionResponse]:
    """创建reconcile对账介入(可能阻塞,触发索引对账)。"""
    try:
        return Result.succ(await extended_service.create_reconcile(request))
    except Exception as e:
        logger.exception("intervention reconcile exception!")
        return Result.failed(str(e))


@router.post("/interventions/attest",
             response_model=Result[InterventionResponse],
             dependencies=[Depends(check_api_key)])
async def create_attest_intervention(
    request: AttestInterventionRequest,
    extended_service: ExtendedInterventionService = Depends(get_extended_service),
) -> Result[InterventionResponse]:
    """创建attest背书介入(非阻塞,联动成熟度晋升)。"""
    try:
        return Result.succ(await extended_service.create_attest(request))
    except Exception as e:
        logger.exception("intervention attest exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    global global_system_app
    system_app.register(InterventionService, config=config)
    system_app.register(ExtendedInterventionService, config=config)
    global_system_app = system_app
