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


# 会话"进行中"状态(与 use-chat-polling 的 isInProgress 语义一致):
# 只有这些状态才可能有活跃 Agent 消费补充输入队列。
_IN_PROGRESS_STATES = {"running", "waiting", "retrying"}


async def _has_active_execution(session_id: str) -> bool:
    """判断会话最近一轮是否处于进行中状态(有活跃 Agent 消费补充输入)。

    兜底校验:打开历史任务/快速切换会话时,前端 running 判定可能误判为
    RUNNING,把已结束(终态)会话的追问也投递到队列——而该队列没有活跃
    Agent 消费,消息会被静默搁置(无报错、无 AI 回复)。此处仅当会话最近
    一轮为 running/waiting/retrying 时才放行入队;终态或无会话则拒绝。
    任何异常按"放行"降级,不阻断原本合法的入队。
    """
    try:
        from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsDao

        dao = GptsConversationsDao()
        convs = await dao.get_by_session_id_asc(session_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[input_api] check active execution failed, degrade to allow: {e}"
        )
        return True
    if not convs:
        return False
    state = getattr(convs[-1], "state", None)
    return state in _IN_PROGRESS_STATES


@router.post(
    "/v2/input/submit",
    dependencies=[Depends(require_permission("agent", "chat"))],
)
async def submit_user_input(request: UserInputSubmitRequest = Body(...)):
    """提交用户补充输入到运行中会话的输入队列。

    前端仅在 agent 运行中调用(按钮态保证);但为防历史任务/会话切换使 running
    误判,后端兜底校验会话是否确有活跃执行,否则返回明确失败,避免静默吞消息。
    """
    gateway = _gateway()
    if not await _has_active_execution(request.session_id):
        return {
            "success": False,
            "message": "当前会话没有正在执行的任务, 请直接发送新消息",
            "queue_length": 0,
            "execution_node": None,
        }
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
