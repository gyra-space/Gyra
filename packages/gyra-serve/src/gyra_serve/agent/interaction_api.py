"""
Interaction API - 用户交互端点

提供 ask_user 响应提交、待处理请求查询、请求取消等接口
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interaction", tags=["Interaction"])


class InteractionRespondRequest(BaseModel):
    """用户交互响应请求"""

    request_id: str = Field(..., description="交互请求ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    choice: Optional[str] = Field(None, description="用户选择的选项值")
    choices: List[str] = Field(default_factory=list, description="多选结果")
    input_value: Optional[str] = Field(None, description="用户输入内容")
    user_message: Optional[str] = Field(None, description="用户消息 (system_reminder 格式)")
    grant_scope: Optional[str] = Field(None, description="授权范围")
    grant_duration: Optional[int] = Field(None, description="授权时长(秒)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class InteractionCancelRequest(BaseModel):
    """取消交互请求"""

    request_id: str = Field(..., description="交互请求ID")
    reason: str = Field("user_cancel", description="取消原因")


class InteractionRespondResponse(BaseModel):
    """响应结果"""

    success: bool
    message: str
    request_id: str


class PendingRequestItem(BaseModel):
    """待处理请求项"""

    request_id: str
    interaction_type: str
    title: str
    message: str
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _get_interaction_gateway():
    """获取全局交互网关实例"""
    try:
        from gyra.agent.interaction.interaction_gateway import get_interaction_gateway

        gateway = get_interaction_gateway()
        return gateway
    except ImportError:
        logger.warning("[InteractionAPI] Cannot import interaction gateway")
        return None
    except Exception as e:
        logger.warning(f"[InteractionAPI] Failed to get interaction gateway: {e}")
        return None


_confirm_store: Optional[Any] = None


def _get_confirm_store():
    """获取确认记录存取（持久化：跟随系统数据库，重启不丢）。"""
    global _confirm_store
    if _confirm_store is None:
        from gyra.agent.core.v2.state_store import create_state_store

        _confirm_store = create_state_store()
    return _confirm_store


@router.post("/respond", response_model=InteractionRespondResponse)
async def respond_to_interaction(request: InteractionRespondRequest):
    """
    提交用户交互响应

    前端 VisConfirmCard 提交用户选择后调用此接口，
    解除 Agent 的 send_and_wait() 阻塞，继续执行。
    """
    gateway = _get_interaction_gateway()
    if not gateway:
        raise HTTPException(
            status_code=503,
            detail="Interaction gateway not available",
        )

    try:
        from gyra.agent.interaction.interaction_protocol import (
            InteractionResponse,
            InteractionStatus,
        )

        response = InteractionResponse(
            request_id=request.request_id,
            session_id=request.session_id,
            choice=request.choice,
            choices=request.choices,
            input_value=request.input_value,
            user_message=request.user_message,
            status=InteractionStatus.RESPONSED,
            grant_scope=request.grant_scope,
            grant_duration=request.grant_duration,
            metadata=request.metadata,
        )

        # 先解除 Agent 阻塞（deliver_response 幂等：已响应则 no-op），再持久化确认记录。
        await gateway.deliver_response(response)

        # 持久化"谁在何时确认了什么"，并拒绝重复确认。
        confirm_store = _get_confirm_store()
        responder = request.metadata.get("responder") or request.metadata.get("user") or {}
        if not isinstance(responder, dict):
            responder = {}
        record = {
            "request_id": request.request_id,
            "responded_at": datetime.now(timezone.utc).isoformat(),
            "responder": {
                "user_no": responder.get("user_no"),
                "nick_name": responder.get("nick_name"),
                "avatar_url": responder.get("avatar_url"),
            },
            "confirm_type": request.metadata.get("confirm_type") or "select",
            "question": request.metadata.get("question"),
            "header": request.metadata.get("header"),
            "choice": request.choice,
            "input_content": request.input_value,
            "is_custom_input": bool(request.metadata.get("is_custom_input", False)),
        }
        first_save = await confirm_store.save_confirm_record(request.request_id, record)
        if not first_save:
            existing = await confirm_store.get_confirm_record(request.request_id)
            logger.info(
                f"[InteractionAPI] Duplicate response rejected for request_id={request.request_id}"
            )
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "already_responded",
                    "record": existing,
                },
            )

        logger.info(
            f"[InteractionAPI] Confirm record persisted for request_id={request.request_id} "
            f"responder={record['responder']} confirm_type={record['confirm_type']}"
        )

        logger.info(
            f"[InteractionAPI] Response delivered for request_id={request.request_id}"
        )

        return InteractionRespondResponse(
            success=True,
            message="Response delivered successfully",
            request_id=request.request_id,
        )

    except Exception as e:
        logger.exception(f"[InteractionAPI] Failed to deliver response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deliver response: {str(e)}",
        )


@router.get("/pending")
async def get_pending_requests(session_id: str) -> List[PendingRequestItem]:
    """
    获取指定会话的待处理交互请求
    """
    gateway = _get_interaction_gateway()
    if not gateway:
        return []

    try:
        requests = await gateway.get_pending_requests(session_id)
        return [
            PendingRequestItem(
                request_id=req.request_id,
                interaction_type=req.interaction_type,
                title=req.title,
                message=req.message,
                created_at=req.created_at.isoformat()
                if hasattr(req.created_at, "isoformat")
                else str(req.created_at),
                metadata=req.metadata,
            )
            for req in requests
        ]
    except Exception as e:
        logger.warning(f"[InteractionAPI] Failed to get pending requests: {e}")
        return []


@router.get("/status")
async def get_confirm_status(request_id: str) -> Dict[str, Any]:
    """
    查询确认卡片的已确认状态。

    前端 VisConfirmCard 每次渲染据此决定交互态 / 只读态：
    - 未确认(response.responded=False)：可交互；
    - 已确认(response.responded=True)：只读并展示谁在何时确认了什么。
    """
    confirm_store = _get_confirm_store()
    record = await confirm_store.get_confirm_record(request_id)
    return {"responded": record is not None, "record": record}


@router.post("/cancel", response_model=InteractionRespondResponse)
async def cancel_interaction(request: InteractionCancelRequest):
    """
    取消交互请求
    """
    gateway = _get_interaction_gateway()
    if not gateway:
        raise HTTPException(
            status_code=503,
            detail="Interaction gateway not available",
        )

    try:
        await gateway.cancel_request(request.request_id, request.reason)

        logger.info(
            f"[InteractionAPI] Request cancelled: request_id={request.request_id}, reason={request.reason}"
        )

        return InteractionRespondResponse(
            success=True,
            message="Request cancelled",
            request_id=request.request_id,
        )

    except Exception as e:
        logger.exception(f"[InteractionAPI] Failed to cancel request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel request: {str(e)}",
        )
