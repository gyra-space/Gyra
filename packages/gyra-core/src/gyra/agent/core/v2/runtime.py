# packages/gyra-core/src/gyra/agent/core/v2/runtime.py
"""run_step()——V2 Runtime 入口.

P0: INIT → THINKING → ACTING（可选）→ OBSERVING → DONE
P1: + PermissionGate 在 ACTING 前拦截，AWAITING_TOOL_PERMISSION 状态
崩溃恢复：每个 yield 前持久化，resume_step 从 StateStore 重放 + 重做未完成 step。
"""
from __future__ import annotations
import uuid
import time
from typing import AsyncGenerator, Callable, Awaitable, Optional, Dict, TYPE_CHECKING
from gyra.agent.core.v2.step_state import (
    StepState, validate_transition, IllegalTransitionError,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.state_store import StateStore
from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.thinking_chunk import ThinkingChunk, TokenChunk, ToolCallChunk, UsageChunk, AwaitUserChunk
from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.tools.context import ToolContext

if TYPE_CHECKING:
    from gyra.agent.core.v2.subagent_runtime import SubAgentRuntime


ThinkingFn = Callable[[dict], AsyncGenerator[ThinkingChunk, None]]
ActingFn = Callable[[V2ToolCall, ToolContext], Awaitable[V2ToolResult]]

_AWAITING_STATES = {
    StepState.AWAITING_USER,
    StepState.AWAITING_TOOL_PERMISSION,
    StepState.AWAITING_SUB_AGENT,
}

# Per-process tracker of the last state per step_id. Used by validate_transition.
# In a multi-process setup each process has its own tracker and loads initial
# state from StateStore on resume.
_step_state_tracker: Dict[str, StepState] = {}


def _validate_and_track_transition(step_id: str, prev: Optional[StepState], new: StepState) -> None:
    """Validate prev -> new transition; raise on invalid; track new state.

    If prev is None, we trust the caller (initial state or resume from store).
    Consecutive events in the same state are allowed (e.g. multiple THINKING tokens).
    """
    if prev is not None and prev is not new:
        if not validate_transition(prev, new):
            raise IllegalTransitionError(
                f"Invalid transition for step {step_id}: {prev.value} -> {new.value}"
            )
    _step_state_tracker[step_id] = new


def _make_emit(stream, step_id, conv_id, agent_id, parent_step_id, seq_start):
    """创建 emit 函数：构造 StepEvent、校验状态转换、持久化、返回。"""
    seq = {"n": seq_start}

    async def emit(state, event_type, input_data=None, output_data=None):
        prev = _step_state_tracker.get(step_id)
        _validate_and_track_transition(step_id, prev, state)
        event = StepEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            step_id=step_id,
            conv_id=conv_id,
            agent_id=agent_id,
            parent_step_id=parent_step_id,
            state=state,
            event_type=event_type,
            input=input_data or {},
            output=output_data or {},
            seq=seq["n"],
            timestamp=time.time(),
        )
        seq["n"] += 1
        return await stream.emit(event)

    return emit


async def _run_thinking_phase(emit, thinking_fn, input_, result_box, request_meta=None):
    """INIT + THINKING 阶段。yield 事件，把 tool_calls/await_user 写入 result_box。

    C3 fix: 兼容 dict yield（transitional tests）和 ThinkingChunk dataclass yield（default_thinking_fn）。
    """
    if request_meta:
        # request/header 快照：记录本次模型请求的可审计元信息
        # （model/system_prompt 摘要/会话标识），作为日志事实供重放与审计。
        yield await emit(
            StepState.INIT, "request_header",
            input_data=request_meta,
        )
    yield await emit(StepState.INIT, "step_init", input_data=input_)
    # P0 阶段发射点：THINKING 阶段开始（插件可在此注入/观测 LLM 调用前置逻辑）
    yield await emit(StepState.THINKING, "thinking_started")
    result_box["tool_calls"] = []
    result_box["await_user"] = False
    async for chunk in thinking_fn(input_):
        # 兼容 dict（transitional）和 typed ThinkingChunk
        if isinstance(chunk, dict):
            await_user = chunk.get("await_user")
            tool_calls = chunk.get("tool_calls")
            token = chunk.get("token", "")
            usage = chunk.get("usage")
        elif isinstance(chunk, TokenChunk):
            await_user = False
            tool_calls = None
            token = chunk.token
            usage = chunk.usage
        elif isinstance(chunk, ToolCallChunk):
            await_user = False
            tool_calls = chunk.tool_calls
            token = ""
            usage = None
        elif isinstance(chunk, UsageChunk):
            await_user = False
            tool_calls = None
            token = ""
            usage = chunk.usage
        elif isinstance(chunk, AwaitUserChunk):
            result_box["await_user"] = True
            yield await emit(
                StepState.AWAITING_USER, "interaction_request",
                input_data={"reason": chunk.reason or "thinking_fn requested user input"},
            )
            return
        else:
            continue

        if await_user:
            result_box["await_user"] = True
            yield await emit(
                StepState.AWAITING_USER, "interaction_request",
                input_data={"reason": "thinking_fn requested user input"},
            )
            return
        if tool_calls:
            # Normalize: V2ToolCall → {"tool": name, "input": args} dict
            if isinstance(tool_calls, list) and tool_calls and isinstance(tool_calls[0], V2ToolCall):
                result_box["tool_calls"].extend(
                    {"tool": tc.name, "input": tc.args} for tc in tool_calls
                )
            else:
                result_box["tool_calls"].extend(tool_calls)
        output_data = {"token": token}
        if usage:
            output_data["usage"] = usage
        yield await emit(
            StepState.THINKING, "llm_token",
            output_data=output_data,
        )


async def _run_acting_phase(
    emit, gate, tool_calls, acting_fn, state_store=None,
    subagent_runtime=None, parent_step_id=None, parent_conv_id=None,
    parent_agent_id=None, step_id=None, conv_id=None,
):
    """ACTING + OBSERVING 阶段。每个 tool_call 前 PermissionGate.check()。"""
    if step_id is None:
        raise ValueError("step_id is required for _run_acting_phase")
    if conv_id is None:
        raise ValueError("conv_id is required for _run_acting_phase")

    suspended = False  # ask_user 挂起时不发 observing_done
    executed_count = 0  # 实际执行（非 denied / 非 subagent 拦截）的工具数

    for tc in tool_calls:
        # Sub-agent interception (spec §8)
        if tc.get("tool") == "spawn_subagent" and subagent_runtime is not None:
            from gyra.agent.core.v2.subagent_runtime import SubAgentSpawnSpec
            spec_input = tc.get("input", {})
            # Strip test-only injected callables from persisted event input
            display_input = {k: v for k, v in spec_input.items() if not k.startswith("_")}
            yield await emit(
                StepState.AWAITING_SUB_AGENT, "subagent_spawn",
                input_data={**tc, "input": display_input},
            )
            spec = SubAgentSpawnSpec(
                agent_name=spec_input.get("agent_name", "unknown"),
                task=spec_input.get("task", ""),
                run_in_background=spec_input.get("run_in_background", False),
                context=spec_input.get("context", {}),
                parent_step_id=parent_step_id or "step-unknown",
                parent_conv_id=parent_conv_id or "conv-unknown",
                parent_agent_id=parent_agent_id or "agent-unknown",
                depth=0,  # P2 simplification: depth tracking via context in P3
                thinking_fn=spec_input.get("_sub_thinking_fn"),
                acting_fn=spec_input.get("_sub_acting_fn"),
                interaction_gateway=None,
            )
            handle = await subagent_runtime.spawn(spec)
            yield await emit(
                StepState.OBSERVING, "tool_result",
                output_data=handle.to_payload(),
            )
            continue

        # PermissionGate path (existing)
        if gate is not None:
            async for perm_event in gate.check(tc, emit=emit):
                yield perm_event
            result = gate.last_result
            if result.decision == PermissionDecision.DENY:
                yield await emit(
                    StepState.ACTING, "tool_call",
                    input_data=tc, output_data={"denied": True, "reason": result.reason},
                )
                continue
            # ALLOW path: delete the interaction checkpoint (if a request_id was set)
            if result.request_id and state_store is not None:
                await state_store.delete_interaction_checkpoint(result.request_id)
        yield await emit(StepState.ACTING, "tool_call", input_data=tc)
        if acting_fn is not None:
            # Convert dict to V2ToolCall
            v2_call = V2ToolCall(
                name=tc["tool"],
                args=tc.get("input", {}),
            )
            # Construct ToolContext
            ctx = ToolContext(
                agent_id=parent_agent_id or "unknown",
                agent_name="v2_agent",
                conversation_id=conv_id or "unknown",
            )
            result = await acting_fn(v2_call, ctx)
            executed_count += 1
            # Convert V2ToolResult back to dict for event system
            result_dict = {
                "is_exe_success": result.success,
                "content": str(result.output) if result.output is not None else "",
                "tool_name": result.tool_name,
            }
            if result.error:
                result_dict["error"] = result.error
            if result.error_code:
                result_dict["error_code"] = result.error_code
            # P0 阶段发射点：工具函数执行完毕（与 OBSERVING 态的 tool_result 区分，
            # 供插件观测原始执行事实——成功/失败/错误码，不含截断后的 content）
            yield await emit(
                StepState.ACTING, "tool_executed",
                input_data={"tool": tc["tool"]},
                output_data={
                    "success": result.success,
                    **({"error": result.error} if result.error else {}),
                    **({"error_code": result.error_code} if result.error_code else {}),
                },
            )
            # P2 follow-up: legacy ActionOutput.ask_user compat (§9.4)
            if isinstance(result_dict, dict) and "ask_user" in result_dict:
                from gyra.agent.core.v2.ask_user_adapter import AskUserAdapter
                adapter = AskUserAdapter(state_store=state_store) if state_store else None
                if adapter is not None:
                    ask_event = await adapter.convert(
                        result_dict["ask_user"],
                        step_id=step_id,
                        conv_id=conv_id,
                    )
                    # Re-emit via runtime's emit so seq is correct
                    yield await emit(
                        StepState.AWAITING_USER, "interaction_request",
                        input_data=ask_event.input,
                    )
                    suspended = True
                    return  # step suspended
            yield await emit(StepState.OBSERVING, "tool_result", output_data=result_dict)

    # P0 阶段发射点：OBSERVING 阶段收尾（全部工具结果已记录；挂起时不发）
    if not suspended:
        yield await emit(
            StepState.OBSERVING, "observing_done",
            output_data={
                "tool_count": len(tool_calls),
                "executed_count": executed_count,
            },
        )


# Import here to avoid circular import at module load
from gyra.agent.core.v2.permission_gate import PermissionGate, PermissionDecision  # noqa: E402


async def run_step(
    agent_id: str,
    conv_id: str,
    input_: dict,
    state_store: StateStore,
    thinking_fn: ThinkingFn,
    acting_fn: Optional[ActingFn] = None,
    parent_step_id: Optional[str] = None,
    permission_gate: Optional[PermissionGate] = None,
    subagent_runtime: Optional["SubAgentRuntime"] = None,
    request_meta: Optional[dict] = None,
    event_stream: Optional[EventStream] = None,
) -> AsyncGenerator[StepEvent, None]:
    """跑一个 step，yield 所有 StepEvent。每个事件持久化后再 yield。

    event_stream：外部注入的共享 EventStream（P0 插件订阅挂载点）；
    缺省时按 state_store 新建（无订阅者，行为与旧版一致）。
    """
    stream = event_stream if event_stream is not None else EventStream(state_store)
    step_id = f"step-{uuid.uuid4().hex[:8]}"
    if permission_gate is not None:
        permission_gate._step_id = step_id  # bind gate to this step
    emit = _make_emit(stream, step_id, conv_id, agent_id, parent_step_id, seq_start=0)

    result_box = {}
    async for e in _run_thinking_phase(emit, thinking_fn, input_, result_box, request_meta=request_meta):
        yield e

    if result_box["await_user"]:
        return

    if result_box["tool_calls"]:
        async for e in _run_acting_phase(
            emit, permission_gate, result_box["tool_calls"], acting_fn,
            state_store=state_store,
            subagent_runtime=subagent_runtime,
            parent_step_id=step_id, parent_conv_id=conv_id, parent_agent_id=agent_id,
            step_id=step_id, conv_id=conv_id,
        ):
            yield e
        # P2 follow-up: if acting phase suspended for user input, don't emit DONE
        if _step_state_tracker.get(step_id) in _AWAITING_STATES:
            return

    yield await emit(StepState.DONE, "step_done")


async def resume_step(
    agent_id: str,
    conv_id: str,
    input_: dict,
    state_store: StateStore,
    thinking_fn: ThinkingFn,
    acting_fn: Optional[ActingFn] = None,
    step_id: Optional[str] = None,
    permission_gate: Optional[PermissionGate] = None,
    subagent_runtime: Optional["SubAgentRuntime"] = None,
    request_meta: Optional[dict] = None,
    event_stream: Optional[EventStream] = None,
) -> AsyncGenerator[StepEvent, None]:
    """从崩溃点续接。

    - 无 step_id：等价 run_step
    - 有 step_id 且最后状态是 AWAITING_*：恢复到等待状态（不重跑 thinking）
    - 有 step_id 且最后状态是 THINKING/ACTING/OBSERVING/INIT：重做该 step
    """
    if not step_id:
        async for e in run_step(
            agent_id, conv_id, input_, state_store,
            thinking_fn, acting_fn, permission_gate=permission_gate,
            subagent_runtime=subagent_runtime,
            request_meta=request_meta,
            event_stream=event_stream,
        ):
            yield e
        return

    # Inspect last state for this step
    state_result = await state_store.get_step_state(step_id)
    last_state = state_result[0] if state_result else None

    stream = event_stream if event_stream is not None else EventStream(state_store)
    if permission_gate is not None:
        permission_gate._step_id = step_id
    existing = await state_store.get_events(conv_id)
    seq_start = existing[-1].seq + 1 if existing else 0
    emit = _make_emit(stream, step_id, conv_id, agent_id, None, seq_start)

    # P0 Important #3: resume_awaiting path
    if last_state in _AWAITING_STATES:
        # Restore the awaiting state without re-running thinking
        # _validate_and_track_transition needs prev=None to skip the check
        # (the step's persisted state is already this; we're re-emitting for SSE)
        _step_state_tracker.pop(step_id, None)
        yield await emit(last_state, "interaction_request",
                         input_data={"reason": f"resumed from {last_state.value}"})
        return

    # redo_step path: re-run thinking + acting (P0 Important #1: acting_fn now included)
    _step_state_tracker.pop(step_id, None)  # reset tracker so INIT is valid
    result_box = {}
    async for e in _run_thinking_phase(emit, thinking_fn, input_, result_box, request_meta=request_meta):
        yield e

    if result_box["await_user"]:
        return

    if result_box["tool_calls"]:
        async for e in _run_acting_phase(
            emit, permission_gate, result_box["tool_calls"], acting_fn,
            state_store=state_store,
            subagent_runtime=subagent_runtime,
            parent_step_id=step_id, parent_conv_id=conv_id, parent_agent_id=agent_id,
            step_id=step_id, conv_id=conv_id,
        ):
            yield e
        # P2 follow-up: if acting phase suspended for user input, don't emit DONE
        if _step_state_tracker.get(step_id) in _AWAITING_STATES:
            return

    yield await emit(StepState.DONE, "step_done")
