"""工具执行授权 API。

配合「终止 + 持久化待授权工具 + 同 id 恢复执行」的工具授权模型：
- requires_permission 工具执行前进入 WAITING，待授权信息登记到 ToolApprovalRegistry。
- 前端在输入框上方渲染授权卡片，调用 /v2/tool/approve 确认或拒绝。
- 确认后前端用旧 conv_id 发起一次恢复（对话处于 WAITING -> is_retry_chat），
  recovering 机制重新执行待授权工具（registry 命中已授权则放行），继续 AgentLoop。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field

from gyra_app.feature_plugins.permissions.checker import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class ToolApproveRequest(BaseModel):
    """工具授权确认/拒绝请求。"""

    conv_id: str = Field(..., description="会话ID(前端 convUid)")
    action_uid: str = Field(..., description="待授权工具调用ID(tool_call.id / action_uid)")
    approved: bool = Field(True, description="True=授权, False=拒绝")
    reason: Optional[str] = Field(None, description="拒绝原因")


class PendingItem(BaseModel):
    action_uid: str
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)


def _registry():
    from gyra.agent.core.tool_approval_registry import get_tool_approval_registry

    return get_tool_approval_registry()


@router.post(
    "/v2/tool/approve",
    dependencies=[Depends(require_permission("agent", "chat"))],
)
async def approve_tool_execution(request: ToolApproveRequest = Body(...)):
    """确认/拒绝待授权工具调用。

    仅登记结果；不在此触发恢复。前端确认后用旧 conv_id 发起恢复请求
    (/v1/chat/completions)，对话处于 WAITING 会走 is_retry_chat，重新执行
    待授权工具（已授权则放行）。
    """
    registry = _registry()
    if request.approved:
        had = registry.approve(request.conv_id, request.action_uid)
        logger.info(
            f"[ToolApprovalAPI] approve conv={request.conv_id} "
            f"action={request.action_uid} had_pending={had}"
        )
    else:
        registry.reject(request.conv_id, request.action_uid)
        logger.info(
            f"[ToolApprovalAPI] reject conv={request.conv_id} "
            f"action={request.action_uid} reason={request.reason}"
        )
    return {
        "success": True,
        "approved": request.approved,
        "conv_id": request.conv_id,
        "action_uid": request.action_uid,
    }


@router.get(
    "/v2/tool/pending",
    dependencies=[Depends(require_permission("agent", "chat"))],
)
async def get_pending_approvals(conv_id: str = Query(..., description="会话ID")):
    """获取会话的待授权工具调用列表（供前端授权卡片展示）。"""
    registry = _registry()
    pending = registry.get_pending(conv_id)
    items: List[PendingItem] = [
        PendingItem(
            action_uid=aid,
            tool_name=info.get("tool_name", ""),
            args=info.get("args", {}) or {},
        )
        for aid, info in pending.items()
    ]
    return {
        "conv_id": conv_id,
        "has_pending": len(items) > 0,
        "pending": [item.dict() for item in items],
    }
