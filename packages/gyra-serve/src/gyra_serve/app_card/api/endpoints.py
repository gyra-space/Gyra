"""AppCard API endpoints — unified invoke protocol."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra.component import SystemApp
from gyra_serve.core import Result
from gyra_serve.permissions import require_space

from .schemas import (
    AppCardCreateRequest, AppCardInvokeRequest, AppCardListFilter,
    AppCardResponse, AppCardUpdateRequest, AppCardValidateResponse,
)
from ..config import ServeConfig
from ..service.service import APP_CARD_SERVICE_COMPONENT_NAME, AppCardService

router = APIRouter()
global_system_app: Optional[SystemApp] = None
logger = logging.getLogger(__name__)


def get_service() -> AppCardService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(APP_CARD_SERVICE_COMPONENT_NAME, AppCardService)


get_bearer_token = HTTPBearer(auto_error=False)


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: AppCardService = Depends(get_service),
) -> Optional[str]:
    if service.config.api_keys:
        api_keys = [k.strip() for k in service.config.api_keys.split(",")]
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(status_code=401, detail="invalid api key")
        return token
    return None


@router.post("/app_cards/create", response_model=Result[AppCardResponse],
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.manage"))])
async def create_app_card(
    request: AppCardCreateRequest, service: AppCardService = Depends(get_service),
) -> Result[AppCardResponse]:
    try:
        return Result.succ(service.create(request))
    except Exception as e:
        logger.exception("app_card create exception!")
        return Result.failed(str(e))


@router.post("/app_cards/list", response_model=Result,
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def list_app_cards(
    f: AppCardListFilter, service: AppCardService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.list_by_workspace(f))
    except Exception as e:
        logger.exception("app_card list exception!")
        return Result.failed(str(e))


@router.get("/app_cards/info", response_model=Result[AppCardResponse],
            dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def get_app_card(
    card_id: int = Query(...),
    workspace_id: int = Query(...),
    service: AppCardService = Depends(get_service),
) -> Result[AppCardResponse]:
    try:
        result = service.get_by_id(card_id)
        if not result:
            return Result.failed(f"app_card {card_id} not found")
        return Result.succ(result)
    except Exception as e:
        logger.exception("app_card info exception!")
        return Result.failed(str(e))


@router.post("/app_cards/update", response_model=Result[AppCardResponse],
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.manage"))])
async def update_app_card(
    request: AppCardUpdateRequest, service: AppCardService = Depends(get_service),
) -> Result[AppCardResponse]:
    try:
        result = service.update(request)
        if not result:
            return Result.failed(f"app_card {request.id} not found")
        return Result.succ(result)
    except Exception as e:
        logger.exception("app_card update exception!")
        return Result.failed(str(e))


@router.post("/app_cards/{card_id}/invoke", response_model=Result,
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def invoke_app_card(
    card_id: int,
    request: AppCardInvokeRequest,
    workspace_id: int = Query(...),
    service: AppCardService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.invoke(card_id, workspace_id, request))
    except Exception as e:
        logger.exception("app_card invoke exception!")
        return Result.failed(str(e))


@router.post("/app_cards/validate", response_model=Result[AppCardValidateResponse],
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.manage"))])
async def validate_app_card(
    request: AppCardCreateRequest, service: AppCardService = Depends(get_service),
) -> Result[AppCardValidateResponse]:
    try:
        return Result.succ(service.validate_queries(request.workspace_id, request.queries or []))
    except Exception as e:
        logger.exception("app_card validate exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    global global_system_app
    system_app.register(AppCardService, config=config)
    global_system_app = system_app
