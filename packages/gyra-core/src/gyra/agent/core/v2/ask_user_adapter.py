"""AskUserAdapter — legacy ActionOutput.ask_user → InteractionRequest converter.

Spec §9.4 compat layer. Old Actions return ActionOutput.ask_user; this adapter
converts that payload to an AWAITING_USER StepEvent (persisted via the same
interaction_checkpoint table used by PermissionGate). The runtime yields the
event upstream and delegates to InteractionGateway.

This keeps legacy Actions working without modification until P4 cleanup.
"""
from __future__ import annotations
import uuid
import time
from typing import TYPE_CHECKING
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState

if TYPE_CHECKING:
    from gyra.agent.core.v2.state_store import StateStore


class AskUserAdapter:
    def __init__(self, state_store: "StateStore"):
        self._store = state_store

    async def convert(
        self,
        ask_user_payload: dict,
        step_id: str,
        conv_id: str,
    ) -> StepEvent:
        """Convert legacy ask_user dict to AWAITING_USER StepEvent + persist checkpoint."""
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        # 兼容两种 payload 形态：
        #   - legacy ActionOutput：{message, options}
        #   - AskUserTool metadata：{header, questions: [{question, options, ...}], ...}
        #   （questions 转成 message/options 便于 checkpoint 承载可读内容）
        message = (
            ask_user_payload.get("message")
            or ask_user_payload.get("header")
            or ""
        )
        options = ask_user_payload.get("options", [])
        questions = ask_user_payload.get("questions")
        if not message and questions:
            primary = questions[0] if isinstance(questions, list) and questions else {}
            if isinstance(primary, dict):
                message = primary.get("question") or primary.get("header") or ""
                options = primary.get("options") or []
        request_payload = {
            "request_id": request_id,
            "type": "ASK_USER_LEGACY",
            "message": message,
            "options": options,
            "step_id": step_id,
            "conv_id": conv_id,
        }
        # 透传 AskUserTool 原始元数据（questions/header/request_id 等），
        # 供 serve 层按 conv 定位 AWAITING_USER checkpoint 时判断来源。
        if questions is not None:
            request_payload["questions"] = questions
        if ask_user_payload.get("header"):
            request_payload["header"] = ask_user_payload["header"]
        await self._store.save_interaction_checkpoint(
            request_id, step_id, conv_id, request_payload
        )
        return StepEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            step_id=step_id,
            conv_id=conv_id,
            agent_id="",  # set by runtime when yielding
            parent_step_id=None,
            state=StepState.AWAITING_USER,
            event_type="interaction_request",
            input=request_payload,
            output={},
            seq=0,  # runtime's emit will overwrite seq when re-emitting
            timestamp=time.time(),
        )
