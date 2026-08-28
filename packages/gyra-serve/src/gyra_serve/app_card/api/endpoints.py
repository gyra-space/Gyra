"""AppCard API endpoints — unified invoke protocol."""
import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra.component import SystemApp
from gyra_serve.core import Result
from gyra_serve.permissions import require_space
from gyra_serve.utils.auth import UserRequest, get_user_from_headers

from .schemas import (
    AppCardCreateRequest, AppCardDeleteRequest, AppCardInvokeRequest, AppCardListFilter,
    AppCardPreviewInvokeRequest, AppCardResponse, AppCardUpdateRequest, AppCardValidateResponse,
)
from ..config import ServeConfig
from ..service.service import APP_CARD_SERVICE_COMPONENT_NAME, AppCardService
from ..sql_runtime import AppCardBusyError, run_bounded

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
    user: UserRequest = Depends(get_user_from_headers),
) -> Result[AppCardResponse]:
    try:
        identity = user.user_no or user.user_id or request.created_by
        if not request.created_by and identity:
            request.created_by = str(identity)
        return Result.succ(await asyncio.to_thread(service.create, request))
    except Exception as e:
        logger.exception("app_card create exception!")
        return Result.failed(str(e))


@router.post("/app_cards/list", response_model=Result,
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def list_app_cards(
    f: AppCardListFilter, service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result:
    try:
        return Result.succ(await asyncio.to_thread(service.list_by_workspace, f, user))
    except Exception as e:
        logger.exception("app_card list exception!")
        return Result.failed(str(e))


@router.get("/app_cards/info", response_model=Result[AppCardResponse],
            dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def get_app_card(
    card_id: int = Query(...),
    workspace_id: int = Query(...),
    service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result[AppCardResponse]:
    try:
        result = await asyncio.to_thread(service.get_by_id, card_id, user)
        if not result:
            return Result.failed(f"app_card {card_id} not found")
        return Result.succ(result)
    except Exception as e:
        logger.exception("app_card info exception!")
        return Result.failed(str(e))


@router.post("/app_cards/update", response_model=Result[AppCardResponse],
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def update_app_card(
    request: AppCardUpdateRequest, service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result[AppCardResponse]:
    try:
        result = await asyncio.to_thread(service.update, request, user)
        if not result:
            return Result.failed(f"app_card {request.id} not found")
        return Result.succ(result)
    except PermissionError as e:
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card update exception!")
        return Result.failed(str(e))


@router.post("/app_cards/preview/invoke", response_model=Result,
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def preview_invoke_app_card(
    request: AppCardPreviewInvokeRequest, service: AppCardService = Depends(get_service),
) -> Result:
    """开发期预览取数: 用编辑器里(未落库)的查询契约走运行期 dispatch,
    便于「JSON 写完后先看真实取数效果, 再导入落库」。"""
    try:
        req = AppCardInvokeRequest(op=request.op, params=request.params, query_key=request.query_key)
        # 取数走专用有界线程池: 并发+排队满时快速失败, 不挤占全局线程池
        return Result.succ(
            await run_bounded(
                service.preview_invoke, request.workspace_id, request.queries or [], req
            )
        )
    except AppCardBusyError as e:
        logger.warning("app_card preview invoke busy: %s", e)
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card preview invoke exception!")
        return Result.failed(str(e))


@router.post("/app_cards/validate", response_model=Result[AppCardValidateResponse],
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def validate_app_card(
    request: AppCardCreateRequest, service: AppCardService = Depends(get_service),
) -> Result[AppCardValidateResponse]:
    try:
        # 取数走专用有界线程池, 与运行期 invoke 一致不阻塞事件循环
        result = await run_bounded(
            service.validate_queries, request.workspace_id, request.queries or []
        )
        return Result.succ(result)
    except AppCardBusyError as e:
        logger.warning("app_card validate busy: %s", e)
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card validate exception!")
        return Result.failed(str(e))


@router.post("/app_cards/delete", response_model=Result,
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def delete_app_card(
    request: AppCardDeleteRequest, service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result:
    try:
        ok = await asyncio.to_thread(service.delete, request.id, request.workspace_id, user)
        return Result.succ({"deleted": ok})
    except PermissionError as e:
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card delete exception!")
        return Result.failed(str(e))


@router.get("/app_cards/share/render", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def get_app_card_share_render(
    card_id: int = Query(...),
    token: str = Query(...),
    service: AppCardService = Depends(get_service),
) -> Result:
    """匿名分享: 凭分享令牌加载子应用渲染信息(无需登录)。"""
    try:
        payload = await asyncio.to_thread(service.get_render_anonymous, card_id, token)
        if payload is None:
            return Result.failed("无效的分享链接或未开启匿名分享")
        return Result.succ(payload)
    except Exception as e:
        logger.exception("app_card share render exception!")
        return Result.failed(str(e))


@router.post("/app_cards/share/invoke", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def invoke_app_card_share(
    card_id: int,
    request: AppCardInvokeRequest,
    token: str = Query(...),
    service: AppCardService = Depends(get_service),
) -> Result:
    """匿名分享: 凭分享令牌走统一 invoke 协议取数(无需登录)。"""
    try:
        result = await run_bounded(service.invoke_anonymous, card_id, token, request)
        return Result.succ(result)
    except AppCardBusyError as e:
        logger.warning("app_card share invoke busy: %s", e)
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card share invoke exception!")
        return Result.failed(str(e))


@router.get("/app_cards/share/login/render", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def get_app_card_login_render(
    card_id: int = Query(...),
    service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result:
    """登录分享: 已登录用户凭卡片 id 加载渲染信息(受卡片查看权限约束)。"""
    try:
        result = await asyncio.to_thread(service.get_render_share_login, card_id, user)
        if not result:
            return Result.failed("无权查看该子应用，或子应用不存在")
        return Result.succ(result)
    except Exception as e:
        logger.exception("app_card login share render exception!")
        return Result.failed(str(e))


@router.post("/app_cards/share/login/invoke", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def invoke_app_card_login_share(
    card_id: int,
    request: AppCardInvokeRequest,
    service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result:
    """登录分享: 已登录用户凭卡片 id 走统一 invoke 协议取数(受卡片查看权限约束)。"""
    try:
        return Result.succ(
            await run_bounded(service.invoke_login, card_id, request, user)
        )
    except AppCardBusyError as e:
        logger.warning("app_card login share invoke busy: %s", e)
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card login share invoke exception!")
        return Result.failed(str(e))


# 动态路径路由必须注册在所有静态路径之后, 否则 `{card_id}` 会抢先吞掉
# /app_cards/preview/invoke、/app_cards/share/invoke 等静态路径(把 "preview"/"share"
# 当作 card_id 解析而报 not integer)。FastAPI 按注册顺序匹配。
@router.post("/app_cards/{card_id}/invoke", response_model=Result,
             dependencies=[Depends(check_api_key), Depends(require_space("space.task.view"))])
async def invoke_app_card(
    card_id: int,
    request: AppCardInvokeRequest,
    workspace_id: int = Query(...),
    service: AppCardService = Depends(get_service),
    user: UserRequest = Depends(get_user_from_headers),
) -> Result:
    try:
        # 取数是同步阻塞代码(SQLAlchemy), 放专用有界线程池执行: 既不阻塞事件循环,
        # 又用并发+排队上限防慢 SQL 把服务拖死(超限快速失败)
        result = await run_bounded(
            service.invoke, card_id, workspace_id, request, user
        )
        return Result.succ(result)
    except AppCardBusyError as e:
        logger.warning("app_card invoke busy: %s", e)
        return Result.failed(str(e))
    except Exception as e:
        logger.exception("app_card invoke exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    global global_system_app
    system_app.register(AppCardService, config=config)
    global_system_app = system_app
