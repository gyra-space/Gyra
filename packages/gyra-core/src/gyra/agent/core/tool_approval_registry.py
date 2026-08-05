"""工具执行授权注册表（内存版，单机部署）。

工具授权采用「终止 + 持久化待授权工具 + 同 id 恢复执行」模型：
- 工具需要授权时，ToolAction 返回 WAITING（ask_type=BEFORE_ACTION），Agent loop
  结束，对话进入 WAITING。
- 用户在前端授权卡片确认后，调用授权端点把 (conv_id, action_uid) 登记为已授权。
- 恢复（is_retry_chat）时，待授权工具被重新执行；ToolAction 在审批闸口前查询本
  注册表，命中已授权则放行执行，不再二次 WAITING。

key 为 (conv_id, action_uid)，action_uid 即 LLM tool_call.id，恢复时由 recovering
机制原样复用，保持稳定。
"""

from typing import Dict, Set, Optional
import logging

logger = logging.getLogger(__name__)


class ToolApprovalRegistry:
    """内存级工具授权登记。"""

    def __init__(self):
        # conv_id -> {action_uid}
        self._approved: Dict[str, Set[str]] = {}
        # conv_id -> {action_uid -> (tool_name, args)} 待授权（已提出、未确认）
        self._pending: Dict[str, Dict[str, dict]] = {}

    def register_pending(
        self,
        conv_id: str,
        action_uid: str,
        tool_name: str,
        args: Optional[dict] = None,
    ) -> None:
        """登记一个待授权工具调用。"""
        if not conv_id or not action_uid:
            return
        self._pending.setdefault(conv_id, {})[action_uid] = {
            "tool_name": tool_name,
            "args": args or {},
        }

    def approve(self, conv_id: str, action_uid: str) -> bool:
        """用户确认授权某个待授权工具调用。返回是否确有待授权项。"""
        had_pending = action_uid in self._pending.get(conv_id, {})
        self._approved.setdefault(conv_id, set()).add(action_uid)
        # 清理 pending
        self._pending.get(conv_id, {}).pop(action_uid, None)
        logger.info(
            f"[ToolApproval] approved conv={conv_id} action={action_uid} "
            f"(had_pending={had_pending})"
        )
        return had_pending

    def is_approved(self, conv_id: str, action_uid: str) -> bool:
        """恢复时查询该工具调用是否已被授权。"""
        return action_uid in self._approved.get(conv_id, set())

    def reject(self, conv_id: str, action_uid: str) -> None:
        """用户拒绝授权：清理 pending/approved。"""
        self._approved.get(conv_id, set()).discard(action_uid)
        self._pending.get(conv_id, {}).pop(action_uid, None)

    def get_pending(self, conv_id: str) -> Dict[str, dict]:
        """获取会话的待授权工具调用（供前端卡片查询）。"""
        return dict(self._pending.get(conv_id, {}))

    def clear(self, conv_id: str) -> None:
        """会话结束后清理。"""
        self._approved.pop(conv_id, None)
        self._pending.pop(conv_id, None)


_registry = ToolApprovalRegistry()


def get_tool_approval_registry() -> ToolApprovalRegistry:
    return _registry
