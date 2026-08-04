"""V2 用户补充输入 API.

运行中的 Agent 对话,用户可通过该接口提交"补充输入"到 InteractionGateway
的用户输入队列,由正在执行的 agent 在下一轮 think 前消费并注入上下文。
不开启新的 SSE 流,不中止当前生成。

session_id 即前端 convUid(== 后端 conv_session_id)。
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field

from gyra_app.feature_plugins.permissions.checker import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class UserInputSubmitRequest(BaseModel):
    """用户补充输入提交请求。"""

    session_id: str = Field(..., description="会话ID(前端 convUid)")
    content: str = Field(..., description="补充输入内容")
    input_type: str = Field("text", description="输入类型")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


def _gateway():
    """延迟导入全局交互网关单例(避免模块加载期依赖)。"""
    from gyra.agent.interaction.interaction_gateway import get_interaction_gateway

    return get_interaction_gateway()


@router.post(
    "/v2/input/submit",
    dependencies=[Depends(require_permission("agent", "chat"))],
)
async def submit_user_input(request: UserInputSubmitRequest = Body(...)):
    """提交用户补充输入到运行中会话的输入队列。

    前端仅在 agent 运行中调用(按钮态保证);后端不重复校验活跃性,直接入队。
    """
    gateway = _gateway()
    await gateway.submit_user_input(
        session_id=request.session_id,
        content=request.content,
        input_type=request.input_type,
        metadata=request.metadata or {},
    )
    # 读取队列长度(不清空):clear=False 仅返回当前列表,不清空队列
    pending = await gateway.get_pending_user_inputs(request.session_id, clear=False)
    return {
        "success": True,
        "queue_length": len(pending),
        "execution_node": None,
    }


@router.get(
    "/v2/input/queue/{session_id}",
    dependencies=[Depends(require_permission("agent", "chat"))],
)
async def get_input_queue_status(session_id: str):
    """查询会话的补充输入队列状态。"""
    gateway = _gateway()
    pending = await gateway.get_pending_user_inputs(session_id, clear=False)
    return {
        "has_pending_input": len(pending) > 0,
        "pending_count": len(pending),
        "execution_node": None,
        "is_local": True,
    }


@router.delete(
    "/v2/input/queue/{session_id}",
    dependencies=[Depends(require_permission("agent", "chat"))],
)
async def clear_input_queue(session_id: str):
    """清空会话的补充输入队列。"""
    gateway = _gateway()
    gateway.clear_user_input_queue(session_id)
    return {"success": True}
