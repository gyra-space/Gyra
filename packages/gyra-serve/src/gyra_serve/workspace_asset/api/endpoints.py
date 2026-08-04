"""WorkspaceAsset API endpoints."""
import logging
from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra._private.pydantic import BaseModel, Field
from gyra.component import SystemApp
from gyra.distributed import MaturityLevel
from gyra_serve.core import Result

from .schemas import (
    AssetAttestRequest, AssetCoachRequest, AssetListFilter, AssetMaturityLogResponse,
    AssetMaturityPromoteRequest, AssetRequest, AssetResponse, AssetSearchRequest,
    AssetVersionResponse, TaskAssetLinkRequest, TaskAssetLinkResponse,
)
from ..config import ServeConfig
from ..service.index_service import INDEX_SERVICE_COMPONENT_NAME, AssetIndexService
from ..service.maturity import MATURITY_SERVICE_COMPONENT_NAME, AssetMaturityService
from ..service.sediment_service import SEDIMENT_SERVICE_COMPONENT_NAME, SedimentPipeline
from ..service.service import ASSET_SERVICE_COMPONENT_NAME, AssetService
from gyra_serve.workspace.rbac import Permission, require_permission

router = APIRouter()
global_system_app: Optional[SystemApp] = None
logger = logging.getLogger(__name__)


def get_service() -> AssetService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(ASSET_SERVICE_COMPONENT_NAME, AssetService)


get_bearer_token = HTTPBearer(auto_error=False)


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: AssetService = Depends(get_service),
) -> Optional[str]:
    if service.config.api_keys:
        api_keys = [k.strip() for k in service.config.api_keys.split(",")]
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(status_code=401, detail="invalid api key")
        return token
    return None


@router.post("/assets/create", response_model=Result[AssetResponse],
             dependencies=[Depends(check_api_key)])
async def create_asset(
    request: AssetRequest, service: AssetService = Depends(get_service),
) -> Result[AssetResponse]:
    try:
        return Result.succ(service.create(request))
    except Exception as e:
        logger.exception("asset create exception!")
        return Result.failed(str(e))


@router.post("/assets/list", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def list_assets(
    f: AssetListFilter, service: AssetService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.list_assets(f))
    except Exception as e:
        logger.exception("asset list exception!")
        return Result.failed(str(e))


@router.get("/assets/info", response_model=Result[AssetResponse],
            dependencies=[Depends(check_api_key)])
async def get_asset(
    asset_id: int = Query(...),
    service: AssetService = Depends(get_service),
) -> Result[AssetResponse]:
    try:
        result = service.get_by_id(asset_id)
        if not result:
            return Result.failed(f"asset {asset_id} not found")
        return Result.succ(result)
    except Exception as e:
        logger.exception("asset info exception!")
        return Result.failed(str(e))


@router.post("/assets/update", response_model=Result[AssetResponse],
             dependencies=[Depends(check_api_key)])
async def update_asset(
    request: AssetRequest, service: AssetService = Depends(get_service),
) -> Result[AssetResponse]:
    try:
        return Result.succ(service.update(request))
    except Exception as e:
        logger.exception("asset update exception!")
        return Result.failed(str(e))


@router.post("/assets/search", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def search_assets(
    req: AssetSearchRequest, service: AssetService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.search(req))
    except Exception as e:
        logger.exception("asset search exception!")
        return Result.failed(str(e))


@router.get("/assets/{asset_id}/versions", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def list_versions(
    asset_id: int, service: AssetService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.list_versions(asset_id))
    except Exception as e:
        logger.exception("asset versions exception!")
        return Result.failed(str(e))


@router.post("/assets/link_task", response_model=Result[TaskAssetLinkResponse],
             dependencies=[Depends(check_api_key)])
async def link_to_task(
    request: TaskAssetLinkRequest, service: AssetService = Depends(get_service),
) -> Result[TaskAssetLinkResponse]:
    try:
        return Result.succ(service.link_to_task(request))
    except Exception as e:
        logger.exception("asset link_task exception!")
        return Result.failed(str(e))


@router.get("/assets/task_links", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def list_task_links(
    task_id: int = Query(...),
    service: AssetService = Depends(get_service),
) -> Result:
    try:
        return Result.succ(service.list_links_by_task(task_id))
    except Exception as e:
        logger.exception("asset task_links exception!")
        return Result.failed(str(e))


# --------------------------------------------------------------------------- #
# 飞轮体系: 成熟度 / 索引 / 沉淀 API
# --------------------------------------------------------------------------- #
def get_maturity_service() -> AssetMaturityService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(
        MATURITY_SERVICE_COMPONENT_NAME, AssetMaturityService
    )


def get_index_service() -> AssetIndexService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(
        INDEX_SERVICE_COMPONENT_NAME, AssetIndexService
    )


def get_sediment_service() -> SedimentPipeline:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(
        SEDIMENT_SERVICE_COMPONENT_NAME, SedimentPipeline
    )


class AssetMaturityListRequest(BaseModel):
    """按成熟度列出资产请求"""
    workspace_id: int
    min_maturity: str = Field(
        "confirmed", description="draft/proposed/confirmed/published/canonical"
    )
    limit: int = 100


class AssetIndexSearchRequest(BaseModel):
    """索引检索请求"""
    workspace_id: int
    query: Optional[str] = None
    asset_type: Optional[str] = None
    min_maturity: Optional[str] = None
    limit: int = 10
    exclude_asset_ids: Optional[List[int]] = None


class AssetIndexReconcileRequest(BaseModel):
    """索引对账请求"""
    workspace_id: int


class SedimentCheckRequest(BaseModel):
    """沉淀检查请求"""
    agent_id: str
    workspace_id: int


# ----- 成熟度 API -----
@router.post("/assets/maturity/promote", response_model=Result[AssetMaturityLogResponse],
             dependencies=[Depends(check_api_key),
                           Depends(require_permission(Permission.PUBLISH_ASSET))])
async def promote_asset_maturity(
    request: AssetMaturityPromoteRequest,
    service: AssetMaturityService = Depends(get_maturity_service),
) -> Result[AssetMaturityLogResponse]:
    try:
        to_level = MaturityLevel(request.to_level)
        result = await service.promote(
            asset_id=request.asset_id,
            to_level=to_level,
            actor=request.actor,
            note=request.note or "",
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("asset maturity promote exception!")
        return Result.failed(str(e))


@router.post("/assets/maturity/attest", response_model=Result[AssetResponse],
             dependencies=[Depends(check_api_key)])
async def attest_asset(
    request: AssetAttestRequest,
    service: AssetMaturityService = Depends(get_maturity_service),
) -> Result[AssetResponse]:
    try:
        result = await service.attest(
            asset_id=request.asset_id,
            user_id=request.user_id,
            note=request.note,
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("asset maturity attest exception!")
        return Result.failed(str(e))


@router.post("/assets/maturity/coach", response_model=Result[AssetMaturityLogResponse],
             dependencies=[Depends(check_api_key)])
async def coach_asset(
    request: AssetCoachRequest,
    service: AssetMaturityService = Depends(get_maturity_service),
) -> Result[AssetMaturityLogResponse]:
    try:
        result = await service.coach(
            asset_id=request.asset_id,
            user_id=request.user_id,
            coach_note=request.coach_note,
            severity=request.severity,
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("asset maturity coach exception!")
        return Result.failed(str(e))


@router.get("/assets/{asset_id}/maturity/logs", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def list_maturity_logs(
    asset_id: int,
    service: AssetMaturityService = Depends(get_maturity_service),
) -> Result:
    try:
        return Result.succ(service.list_maturity_logs(asset_id))
    except Exception as e:
        logger.exception("asset maturity logs exception!")
        return Result.failed(str(e))


@router.post("/assets/maturity/list_by_maturity", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def list_by_maturity(
    request: AssetMaturityListRequest,
    service: AssetMaturityService = Depends(get_maturity_service),
) -> Result:
    try:
        return Result.succ(service.list_by_maturity(
            workspace_id=request.workspace_id,
            min_maturity=request.min_maturity,
            limit=request.limit,
        ))
    except Exception as e:
        logger.exception("asset list_by_maturity exception!")
        return Result.failed(str(e))


# ----- 索引 API -----
@router.post("/assets/search_indexed", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def search_indexed_assets(
    request: AssetIndexSearchRequest,
    service: AssetIndexService = Depends(get_index_service),
) -> Result:
    try:
        result = await service.search(
            workspace_id=request.workspace_id,
            query=request.query,
            asset_type=request.asset_type,
            min_maturity=request.min_maturity,
            limit=request.limit,
            exclude_asset_ids=request.exclude_asset_ids,
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("asset search_indexed exception!")
        return Result.failed(str(e))


@router.post("/assets/index/reconcile", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def reconcile_index(
    request: AssetIndexReconcileRequest,
    service: AssetIndexService = Depends(get_index_service),
) -> Result:
    try:
        report = await service.reconcile(workspace_id=request.workspace_id)
        return Result.succ(asdict(report))
    except Exception as e:
        logger.exception("asset index reconcile exception!")
        return Result.failed(str(e))


# ----- 沉淀 API -----
@router.post("/assets/sediment/check", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def sediment_check(
    request: SedimentCheckRequest,
    service: SedimentPipeline = Depends(get_sediment_service),
) -> Result:
    try:
        result = await service.run_sediment_check(
            agent_id=request.agent_id,
            workspace_id=request.workspace_id,
        )
        return Result.succ(result)
    except Exception as e:
        logger.exception("asset sediment check exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    global global_system_app
    system_app.register(AssetService, config=config)
    # 飞轮体系: 成熟度 / 索引 / 沉淀 服务注册
    system_app.register(AssetMaturityService, config=config)
    system_app.register(AssetIndexService, config=config)
    system_app.register(SedimentPipeline, config=config)
    global_system_app = system_app
