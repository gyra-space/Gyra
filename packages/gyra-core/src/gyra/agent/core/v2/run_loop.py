"""V2 多轮循环。

包 run_step，循环直到 LLM 不再 emit tool_calls / terminate / max_steps / 失败 / awaiting。
turn 结束触发 HookManager.turn_complete，conversation 结束触发 conversation_complete。
"""
import dataclasses
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Dict, List, Optional

from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.runtime import run_step, _resolve_harness_deps
from gyra.agent.core.v2.state_store import StateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState

if TYPE_CHECKING:
    from gyra.agent.core.v2.harness.context import HarnessContext


_AWAITING_STATES = {
    StepState.AWAITING_USER,
    StepState.AWAITING_TOOL_PERMISSION,
    StepState.AWAITING_SUB_AGENT,
}


# 真正挂起 turn 的交互状态（run_loop 收到即中断）。
# - AWAITING_SUB_AGENT：子 agent 派发中间态，runtime 在 spawn 后随即 emit
#   tool_result 继续本 step，中断会导致 spawn 永不执行 → 不中断。
# - AWAITING_TOOL_PERMISSION：PermissionGate 在 yield 该事件后继续 await
#   InteractionAdapter（同步阻塞等用户审批），中断会杀死 adapter 等待 →
#   不中断（无 adapter 时 gate 已 fail-closed 拒绝，不会走到该状态）。
# - AWAITING_USER：AskUserAdapter 已持久化 interaction_checkpoint，turn 中断
#   由 serve 层挂起 conversation，用户响应后经 checkpoint resume → 中断。
_TURN_SUSPENDING_STATES = {
    StepState.AWAITING_USER,
}


@dataclasses.dataclass
class _TurnContext:
    round: int = 0
    interrupted: bool = False
    user_prompt: str = ""
    final_answer: Optional[str] = None
    user_id: Optional[str] = None
    conv_id: str = ""
    agent_id: str = ""
    step_count: int = 0


async def run_loop(
    agent_id: str,
    conv_id: str,
    input_: dict,
    state_store: Optional[StateStore] = None,
    thinking_fn: Optional[Callable] = None,
    acting_fn: Optional[Callable] = None,
    *,
    parent_step_id: Optional[str] = None,
    permission_gate: Optional[Any] = None,
    subagent_runtime: Optional[Any] = None,
    hook_manager: Optional[Any] = None,
    tool_context_factory: Optional[Any] = None,
    max_steps: int = 20,
    user_id: Optional[str] = None,
    request_meta: Optional[dict] = None,
    event_stream: Optional[EventStream] = None,
    harness: Optional["HarnessContext"] = None,
) -> AsyncGenerator[StepEvent, None]:
    """多轮循环。

    event_stream：共享 EventStream（P0 插件订阅挂载点），透传给每个 run_step；
    缺省时各 step 自建（无订阅者，行为与旧版一致）。

    harness：统一服务总线。提供时从 harness 解包未显式传入的依赖
    （storage / events / approval / subagents / hooks / thinking / acting），
    显式参数优先——向后兼容旧调用方式。
    """
    # HarnessContext 解包：显式参数优先于 harness（事件流绑定一致性见 helper）
    deps = _resolve_harness_deps(
        harness,
        state_store=state_store,
        event_stream=event_stream,
        permission_gate=permission_gate,
        subagent_runtime=subagent_runtime,
        thinking_fn=thinking_fn,
        acting_fn=acting_fn,
        hook_manager=hook_manager,
        tool_context_factory=tool_context_factory,
    )
    state_store = deps["state_store"]
    event_stream = deps["event_stream"]
    permission_gate = deps["permission_gate"]
    subagent_runtime = deps["subagent_runtime"]
    thinking_fn = deps["thinking_fn"]
    acting_fn = deps["acting_fn"]
    hook_manager = deps["hook_manager"]
    tool_context_factory = deps["tool_context_factory"]
    if state_store is None:
        raise ValueError("state_store (or harness.storage) is required")
    if thinking_fn is None:
        raise ValueError("thinking_fn (or harness.thinking_fn) is required")

    turn_ctx = _TurnContext(
        round=0,
        user_prompt=input_.get("prompt", ""),
        user_id=user_id,
        conv_id=conv_id,
        agent_id=agent_id,
    )

    step_count = 0
    last_had_tool_calls = True
    turn_complete_fired = False
    conversation_history: List[Dict[str, str]] = []

    while step_count < max_steps and last_had_tool_calls:
        last_had_tool_calls = False
        final_answer_parts = []

        async for step_event in run_step(
            agent_id=agent_id,
            conv_id=conv_id,
            input_=input_,
            state_store=state_store,
            thinking_fn=thinking_fn,
            acting_fn=acting_fn,
            parent_step_id=parent_step_id,
            permission_gate=permission_gate,
            subagent_runtime=subagent_runtime,
            request_meta=request_meta,
            event_stream=event_stream,
            tool_context_factory=tool_context_factory,
        ):
            yield step_event

            # 收集 final_answer（来自 llm_token；只取 content 通道，
            # thinking 推理文本不属于最终答案）
            if step_event.event_type == "llm_token":
                token = step_event.output.get("token", "") if step_event.output else ""
                channel = step_event.output.get("channel", "content") if step_event.output else "content"
                if token and channel != "thinking":
                    final_answer_parts.append(token)

            # 检查 tool_calls
            if step_event.event_type == "tool_call":
                last_had_tool_calls = True

            # 检查 awaiting 状态
            if step_event.state in _TURN_SUSPENDING_STATES:
                turn_ctx.interrupted = True
                # turn_complete NOT fired here — an interrupted turn is not "complete".
                # Memory tier1 (write_turn_lightweight) registered on turn_complete
                # skips interrupted turns by design. If future design requires recording
                # interrupted turns, fire turn_complete with interrupted=True here.
                return

            if step_event.state == StepState.FAILED:
                return

            if step_event.state == StepState.DONE and step_event.event_type == "step_done":
                step_count += 1

        # 一个 step 结束
        if not last_had_tool_calls:
            # turn 结束
            turn_ctx.round += 1
            turn_ctx.final_answer = "".join(final_answer_parts) or None
            turn_ctx.step_count = step_count

            if hook_manager is not None:
                from gyra.agent.core.v2.hook_integration import (
                    build_turn_complete_context,
                )
                await hook_manager.trigger(
                    "turn_complete",
                    build_turn_complete_context(
                        round=turn_ctx.round,
                        interrupted=turn_ctx.interrupted,
                        user_prompt=turn_ctx.user_prompt,
                        final_answer=turn_ctx.final_answer,
                        user_id=turn_ctx.user_id,
                        conv_id=turn_ctx.conv_id,
                        agent_id=turn_ctx.agent_id,
                        step_count=turn_ctx.step_count,
                    ),
                )
            conversation_history.append(
                {"role": "user", "content": turn_ctx.user_prompt or ""}
            )
            conversation_history.append(
                {
                    "role": "assistant",
                    "content": turn_ctx.final_answer or "",
                }
            )
            turn_complete_fired = True
            break  # turn 结束，退出 loop

    if step_count >= max_steps and not turn_complete_fired:
        # 达到上限，触发 turn_complete（interrupted=True）
        if hook_manager is not None:
            from gyra.agent.core.v2.hook_integration import (
                build_turn_complete_context,
            )
            turn_ctx.interrupted = True
            turn_ctx.round += 1
            await hook_manager.trigger(
                "turn_complete",
                build_turn_complete_context(
                    round=turn_ctx.round,
                    interrupted=True,
                    user_prompt=turn_ctx.user_prompt,
                    final_answer=None,
                    user_id=turn_ctx.user_id,
                    conv_id=turn_ctx.conv_id,
                    agent_id=turn_ctx.agent_id,
                    step_count=step_count,
                ),
            )

    # Conversation lifecycle end: trigger tier 3 memory curation.
    # Note: awaiting/failed states return early above, so we only reach here
    # on a completed (or max-steps-completed) turn.
    await trigger_conversation_complete(
        hook_manager,
        conv_id=conv_id,
        agent_id=agent_id,
        user_id=user_id,
        total_rounds=turn_ctx.round,
        conversation_history=conversation_history,
    )


async def trigger_conversation_complete(
    hook_manager: Any,
    *,
    conv_id: str,
    agent_id: str,
    user_id: Optional[str],
    total_rounds: int,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> None:
    """run_loop 调用方在 conversation 结束时调。"""
    if hook_manager is None:
        return
    from gyra.agent.core.v2.hook_integration import (
        build_conversation_complete_context,
    )
    await hook_manager.trigger(
        "conversation_complete",
        build_conversation_complete_context(
            conv_id=conv_id,
            agent_id=agent_id,
            user_id=user_id,
            total_rounds=total_rounds,
            conversation_history=conversation_history,
        ),
    )
