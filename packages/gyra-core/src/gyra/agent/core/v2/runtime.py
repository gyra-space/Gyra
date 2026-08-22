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
    from gyra.agent.core.v2.harness.context import HarnessContext


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


def _resolve_harness_deps(
    harness,
    *,
    state_store=None,
    event_stream=None,
    permission_gate=None,
    subagent_runtime=None,
    thinking_fn=None,
    acting_fn=None,
    hook_manager=None,
) -> dict:
    """从 HarnessContext 解包依赖；显式参数优先。

    事件流一致性（关键）：显式传入 ``state_store`` 而未显式传 ``event_stream``
    时，事件流必须绑定**显式 state_store**（而非 ``harness.events`` 绑定的
    ``harness.storage``）——否则事件会持久化到错误的存储。
    """
    if harness is None:
        return {
            "state_store": state_store,
            "event_stream": event_stream,
            "permission_gate": permission_gate,
            "subagent_runtime": subagent_runtime,
            "thinking_fn": thinking_fn,
            "acting_fn": acting_fn,
            "hook_manager": hook_manager,
        }
    provided_store = state_store is not None
    state_store = state_store if state_store is not None else harness.storage
    if event_stream is None:
        # 显式 store 与 harness.events 不共享存储：必须新建绑定显式 store 的事件流
        event_stream = EventStream(state_store) if provided_store else harness.events
    permission_gate = (
        permission_gate if permission_gate is not None else harness.approval
    )
    subagent_runtime = (
        subagent_runtime if subagent_runtime is not None else harness.subagents
    )
    thinking_fn = thinking_fn if thinking_fn is not None else harness.thinking_fn
    acting_fn = acting_fn if acting_fn is not None else harness.acting_fn
    hook_manager = hook_manager if hook_manager is not None else harness.hooks
    return {
        "state_store": state_store,
        "event_stream": event_stream,
        "permission_gate": permission_gate,
        "subagent_runtime": subagent_runtime,
        "thinking_fn": thinking_fn,
        "acting_fn": acting_fn,
        "hook_manager": hook_manager,
    }


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
    """创建 emit 函数：构造 StepEvent、校验状态转换、持久化、返回。

    mode 支持 DSH 三分法：
      - "emit"（默认）：广播，返回 StepEvent；
      - "waterfall"：中间件链（可改写/中止），返回 DispatchResult；
      - "serial"：终态检查点（首个非空决策胜出），返回 DispatchResult。
    """
    seq = {"n": seq_start}

    async def emit(state, event_type, input_data=None, output_data=None, *, mode="emit"):
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
        if mode == "waterfall":
            return await stream.emit_waterfall(event)
        if mode == "serial":
            return await stream.emit_serial(event)
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
    # thinking_started —— waterfall 接缝（对齐 DSH agent/pre-step）：
    # 中间件可改写请求（await next(new_event)）或中止（不调 next 直接返回）。
    # 链结束后才持久化最终事件，保证事件溯源记录最终事实。
    pre = await emit(
        StepState.THINKING, "thinking_started",
        input_data=input_, mode="waterfall",
    )
    yield pre.event
    if pre.aborted:
        result_box["aborted"] = True
        return
    effective_input = pre.event.input or input_
    result_box["tool_calls"] = []
    result_box["await_user"] = False
    async for chunk in thinking_fn(effective_input):
        # 兼容 dict（transitional）和 typed ThinkingChunk
        if isinstance(chunk, dict):
            await_user = chunk.get("await_user")
            tool_calls = chunk.get("tool_calls")
            token = chunk.get("token", "")
            usage = chunk.get("usage")
            channel = chunk.get("channel", "content")
        elif isinstance(chunk, TokenChunk):
            await_user = False
            tool_calls = None
            token = chunk.token
            usage = chunk.usage
            channel = getattr(chunk, "channel", "content")
        elif isinstance(chunk, ToolCallChunk):
            await_user = False
            tool_calls = chunk.tool_calls
            token = ""
            usage = None
            channel = "content"
        elif isinstance(chunk, UsageChunk):
            await_user = False
            tool_calls = None
            token = ""
            usage = chunk.usage
            channel = "content"
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
        # 记录本 step 最近一次 usage（流式多帧可能重复携带同一最终 metrics；
        # 只在 thinking 阶段收尾 emit 一次 usage_metric，避免重复累计）。
        if usage:
            result_box["last_usage"] = usage
        output_data = {"token": token, "channel": channel}
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
    system_prompt=None, user_id=None,
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
            # 先 emit ACTING tool_call：让 tool_result 在事件投影中有配对，
            # 子 agent 结果（handle.result.answer）才能进入主 agent LLM 上下文。
            yield await emit(
                StepState.ACTING, "tool_call",
                input_data={"tool": "spawn_subagent", "input": display_input},
            )
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
                # 生产接线：子 agent 继承父会话的 system_prompt / 用户标识
                # （子 agent 复用主 thinking_fn 闭包，由 input_ 字段驱动会话绑定）
                system_prompt=spec_input.get("system_prompt") or system_prompt,
                session_id=spec_input.get("session_id"),
                user_id=spec_input.get("user_id") or user_id,
                shared_conv=spec_input.get("shared_conv", False),
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

        # tool_pre_execute —— waterfall 接缝（对齐 DSH tools/pre-execute）：
        # 中间件可改写工具参数（await next(new_event)）或否决（output.denied）或中止。
        pre = await emit(
            StepState.ACTING, "tool_pre_execute", input_data=tc, mode="waterfall",
        )
        yield pre.event
        if pre.aborted:
            yield await emit(
                StepState.ACTING, "tool_call",
                input_data=pre.event.input or tc,
                output_data={"denied": True, "reason": "waterfall middleware aborted"},
            )
            continue
        effective_tc = pre.event.input or tc
        if pre.event.output.get("denied"):
            yield await emit(
                StepState.ACTING, "tool_call",
                input_data=effective_tc,
                output_data={
                    "denied": True,
                    "reason": pre.event.output.get("reason"),
                },
            )
            continue
        yield await emit(StepState.ACTING, "tool_call", input_data=effective_tc)
        if acting_fn is not None:
            # Convert dict to V2ToolCall
            v2_call = V2ToolCall(
                name=effective_tc["tool"],
                args=effective_tc.get("input", {}),
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
            # 工具 view 通道：skill 等工具的 frontmatter 元数据（用户视角可视化，
            # 不进 LLM 上下文）——写入 WorkEntry.view → action_report → 前端
            _meta = getattr(result, "metadata", None) or {}
            if _meta.get("skill_meta"):
                result_dict["skill_meta"] = _meta["skill_meta"]
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
            # P2 follow-up: ask_user 挂起检测（AskUserTool metadata / legacy ActionOutput 双路径）。
            # AskUserTool 把"要挂起"标记放在 ToolResult.metadata["ask_user"]；旧 Actions 经
            # ActionOutput.ask_user 返回。任一路径命中 → AskUserAdapter 转成 AWAITING_USER
            # interaction_request + 持久化 interaction_checkpoint，run_loop 据此挂起 turn。
            ask_user_payload = None
            if isinstance(result_dict, dict) and "ask_user" in result_dict:
                ask_user_payload = result_dict["ask_user"]
            elif getattr(result, "metadata", None) and result.metadata.get("ask_user"):
                # 两种形态：AskUserTool metadata["ask_user"]=True（payload 用整个
                # metadata，含 questions/header）；legacy ActionOutput
                # metadata["ask_user"]={message, options}（payload 用内层 dict）。
                _ask = result.metadata.get("ask_user")
                ask_user_payload = _ask if isinstance(_ask, dict) else result.metadata
            # 先发 tool_result：drsk-confirm 内容写进 WorkEntry / 执行步骤 output，
            # 前端确认卡片依赖该内容渲染；再发 AWAITING_USER 让 run_loop 挂起 turn。
            # 注意：ask_user 挂起时 tool_result 以 ACTING 态发射——状态机合法转换表
            # 中 OBSERVING → AWAITING_USER 非法（OBSERVING 只允许 THINKING/ACTING/
            # AWAITING_SUB_AGENT/DONE/FAILED），ACTING → AWAITING_USER 才合法。
            tool_result_state = StepState.ACTING if ask_user_payload else StepState.OBSERVING
            yield await emit(tool_result_state, "tool_result", output_data=result_dict)
            if ask_user_payload:
                from gyra.agent.core.v2.ask_user_adapter import AskUserAdapter
                adapter = AskUserAdapter(state_store=state_store) if state_store else None
                if adapter is not None:
                    ask_event = await adapter.convert(
                        ask_user_payload,
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


async def _maybe_emit_usage_metric(
    emit, state_store, step_id, conv_id, agent_id, result_box, request_meta=None,
):
    """thinking 阶段收尾：把最后一次 usage 写为 usage_metric StepEvent。

    TokenMeter / usage 展示的事实源是 ``usage_metric`` 事件；流式多帧可能重复
    携带同一 metrics，这里只取本 step 最后一次，每 LLM 调用恰好 emit 一次。

    Returns:
        持久化后的 ``usage_metric`` StepEvent（None 表示无 usage 不 emit）。
        run_step 把它 yield 给订阅者/SSE——V2 契约：所有 StepEvent 均可消费。
    """
    usage = result_box.get("last_usage")
    if not usage:
        return None
    try:
        from gyra.agent.core.v2.usage_metric import emit_usage_metric

        model = (request_meta or {}).get("model") or ""
        return await emit_usage_metric(
            store=state_store,
            emit=emit,
            step_id=step_id,
            conv_id=conv_id,
            agent_id=agent_id,
            llm_call_id=f"llm-{uuid.uuid4().hex[:8]}",
            model=model,
            this_call={
                "prompt": int(usage.get("prompt_tokens") or 0),
                "completion": int(usage.get("completion_tokens") or 0),
                "total": int(usage.get("total_tokens") or 0),
                "cached": int(usage.get("cached_tokens") or 0),
            },
            current_state=StepState.THINKING,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[runtime] emit usage_metric failed: {e}")
        return None


async def run_step(
    agent_id: str,
    conv_id: str,
    input_: dict,
    state_store: Optional[StateStore] = None,
    thinking_fn: Optional[ThinkingFn] = None,
    acting_fn: Optional[ActingFn] = None,
    parent_step_id: Optional[str] = None,
    permission_gate: Optional[PermissionGate] = None,
    subagent_runtime: Optional["SubAgentRuntime"] = None,
    request_meta: Optional[dict] = None,
    event_stream: Optional[EventStream] = None,
    harness: Optional["HarnessContext"] = None,
) -> AsyncGenerator[StepEvent, None]:
    """跑一个 step，yield 所有 StepEvent。每个事件持久化后再 yield。

    event_stream：外部注入的共享 EventStream（P0 插件订阅挂载点）；
    缺省时按 state_store 新建（无订阅者，行为与旧版一致）。

    harness：统一服务总线。提供时从 harness 解包未显式传入的依赖
    （storage / events / approval / subagents / thinking / acting），
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
    )
    state_store = deps["state_store"]
    event_stream = deps["event_stream"]
    permission_gate = deps["permission_gate"]
    subagent_runtime = deps["subagent_runtime"]
    thinking_fn = deps["thinking_fn"]
    acting_fn = deps["acting_fn"]
    if state_store is None:
        raise ValueError("state_store (or harness.storage) is required")
    if thinking_fn is None:
        raise ValueError("thinking_fn (or harness.thinking_fn) is required")

    stream = event_stream if event_stream is not None else EventStream(state_store)
    step_id = f"step-{uuid.uuid4().hex[:8]}"
    if permission_gate is not None:
        permission_gate._step_id = step_id  # bind gate to this step
    # 会话级全局单调 seq：每个 step 从 store 当前最大 seq 续号（对齐 resume_step），
    # 避免多步 run_loop 下各步 seq 从 0 重复，导致 get_events 的 ORDER BY seq
    # 跨步骤交错、事件投影（project_tool_history）错配 tool_call/tool_result。
    existing = await state_store.get_events(conv_id)
    seq_start = max((e.seq for e in existing), default=-1) + 1
    emit = _make_emit(stream, step_id, conv_id, agent_id, parent_step_id, seq_start=seq_start)

    result_box = {}
    async for e in _run_thinking_phase(emit, thinking_fn, input_, result_box, request_meta=request_meta):
        yield e

    if result_box.get("aborted"):
        yield await emit(StepState.DONE, "step_aborted",
                         input_data={"reason": "pre-thinking waterfall aborted"})
        return

    if result_box["await_user"]:
        return

    # thinking 收尾：emit usage_metric（TokenMeter 事实源，每 LLM 调用一次）
    _usage_event = await _maybe_emit_usage_metric(
        emit, state_store, step_id, conv_id, agent_id, result_box, request_meta,
    )
    if _usage_event is not None:
        yield _usage_event

    if result_box["tool_calls"]:
        async for e in _run_acting_phase(
            emit, permission_gate, result_box["tool_calls"], acting_fn,
            state_store=state_store,
            subagent_runtime=subagent_runtime,
            parent_step_id=step_id, parent_conv_id=conv_id, parent_agent_id=agent_id,
            step_id=step_id, conv_id=conv_id,
            system_prompt=input_.get("system_prompt"),
            user_id=input_.get("user_id"),
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
    state_store: Optional[StateStore] = None,
    thinking_fn: Optional[ThinkingFn] = None,
    acting_fn: Optional[ActingFn] = None,
    step_id: Optional[str] = None,
    permission_gate: Optional[PermissionGate] = None,
    subagent_runtime: Optional["SubAgentRuntime"] = None,
    request_meta: Optional[dict] = None,
    event_stream: Optional[EventStream] = None,
    harness: Optional["HarnessContext"] = None,
) -> AsyncGenerator[StepEvent, None]:
    """从崩溃点续接。

    - 无 step_id：等价 run_step
    - 有 step_id 且最后状态是 AWAITING_*：恢复到等待状态（不重跑 thinking）
    - 有 step_id 且最后状态是 THINKING/ACTING/OBSERVING/INIT：重做该 step

    harness：与 :func:`run_step` 相同的解包语义。
    """
    deps = _resolve_harness_deps(
        harness,
        state_store=state_store,
        event_stream=event_stream,
        permission_gate=permission_gate,
        subagent_runtime=subagent_runtime,
        thinking_fn=thinking_fn,
        acting_fn=acting_fn,
    )
    state_store = deps["state_store"]
    event_stream = deps["event_stream"]
    permission_gate = deps["permission_gate"]
    subagent_runtime = deps["subagent_runtime"]
    thinking_fn = deps["thinking_fn"]
    acting_fn = deps["acting_fn"]
    if state_store is None:
        raise ValueError("state_store (or harness.storage) is required")
    if thinking_fn is None:
        raise ValueError("thinking_fn (or harness.thinking_fn) is required")

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

    if result_box.get("aborted"):
        yield await emit(StepState.DONE, "step_aborted",
                         input_data={"reason": "pre-thinking waterfall aborted"})
        return

    if result_box["await_user"]:
        return

    # thinking 收尾：emit usage_metric（TokenMeter 事实源，每 LLM 调用一次）
    _usage_event = await _maybe_emit_usage_metric(
        emit, state_store, step_id, conv_id, agent_id, result_box, request_meta,
    )
    if _usage_event is not None:
        yield _usage_event

    if result_box["tool_calls"]:
        async for e in _run_acting_phase(
            emit, permission_gate, result_box["tool_calls"], acting_fn,
            state_store=state_store,
            subagent_runtime=subagent_runtime,
            parent_step_id=step_id, parent_conv_id=conv_id, parent_agent_id=agent_id,
            step_id=step_id, conv_id=conv_id,
            system_prompt=input_.get("system_prompt"),
            user_id=input_.get("user_id"),
        ):
            yield e
        # P2 follow-up: if acting phase suspended for user input, don't emit DONE
        if _step_state_tracker.get(step_id) in _AWAITING_STATES:
            return

    yield await emit(StepState.DONE, "step_done")
