# packages/gyra-core/tests/agent/core/v2/test_event_stream_modes.py
"""DSH 三分法（emit / waterfall / serial）分发测试。

覆盖：
1. EventStream 单元：waterfall 链式中间件（顺序/改写/中止/过滤/异常 fail-open/持久化）；
2. EventStream 单元：serial 终态检查点（首个非空胜出/None 跳过/全 None/过滤）；
3. run_step 接缝：thinking_started 改写/中止、tool_pre_execute 否决/改写/透传；
4. PermissionGate serial 决策：裁决短路 adapter。
"""
import pytest
import tempfile
import os

from gyra.agent.core.v2.event_stream import EventStream, DispatchResult
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.runtime import run_step
from gyra.agent.core.v2.permission_gate import PermissionGate, PermissionDecision
from gyra.agent.core.v2.permission_mode import PermissionMode
from gyra.agent.core.v2.session_cache import SessionPermissionCache
from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.tools.context import ToolContext
from gyra_core.permission.ruleset import PermissionRuleset, PermissionRule, PermissionAction


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = DbStateStore(path)
    yield s
    os.unlink(path)


@pytest.fixture
def stream(store):
    return EventStream(store)


def _make_event(event_type: str, seq: int = 0, state: StepState = StepState.THINKING,
                input_data=None, output_data=None):
    return StepEvent(
        event_id=f"evt-{event_type}-{seq}",
        step_id="step-1",
        conv_id="conv-1",
        agent_id="agent-1",
        parent_step_id=None,
        state=state,
        event_type=event_type,
        input=input_data or {},
        output=output_data or {},
        seq=seq,
        timestamp=0.0,
    )


# =============================================================================
# 1. EventStream —— waterfall
# =============================================================================

async def test_waterfall_chain_runs_in_order(store):
    stream = EventStream(store)
    order = []
    for i in (1, 2, 3):
        async def mw(event, next_, i=i):
            order.append(i)
            await next_()
        stream.subscribe(mw, mode="waterfall")

    dr = await stream.emit_waterfall(_make_event("thinking_started", 0, StepState.THINKING))
    assert order == [1, 2, 3]
    assert dr.aborted is False
    assert dr.event.event_type == "thinking_started"
    # 事件已持久化
    persisted = await store.get_events("conv-1")
    assert len(persisted) == 1


async def test_waterfall_rewrites_via_next_new_event(store):
    stream = EventStream(store)
    downstream_seen = []

    async def rewrite(event, next_):
        rewritten = event.model_copy(update={"input": {"prompt": "rewritten"}})
        return await next_(rewritten)

    async def observe(event, next_):
        downstream_seen.append(event.input.get("prompt"))
        await next_()

    stream.subscribe(rewrite, mode="waterfall")
    stream.subscribe(observe, mode="waterfall")

    dr = await stream.emit_waterfall(
        _make_event("thinking_started", 0, StepState.THINKING, input_data={"prompt": "orig"})
    )
    assert downstream_seen == ["rewritten"]
    assert dr.event.input["prompt"] == "rewritten"
    # 持久化的是改写后的最终事件
    persisted = await store.get_events("conv-1")
    assert persisted[0].input["prompt"] == "rewritten"


async def test_waterfall_abort_without_next(store):
    stream = EventStream(store)
    downstream_called = []

    async def abort_mw(event, next_):
        return  # 不调 next() → 中止整条链

    async def downstream(event, next_):
        downstream_called.append(event.event_type)
        await next_()

    stream.subscribe(abort_mw, mode="waterfall")
    stream.subscribe(downstream, mode="waterfall")

    dr = await stream.emit_waterfall(_make_event("thinking_started", 0, StepState.THINKING))
    assert dr.aborted is True
    assert downstream_called == []


async def test_waterfall_event_type_filter(store):
    stream = EventStream(store)
    seen = []

    async def mw(event, next_):
        seen.append(event.event_type)
        await next_()

    stream.subscribe(mw, event_types=["tool_pre_execute"], mode="waterfall")
    await stream.emit_waterfall(_make_event("thinking_started", 0, StepState.THINKING))
    await stream.emit_waterfall(_make_event("tool_pre_execute", 1, StepState.ACTING))
    assert seen == ["tool_pre_execute"]


async def test_waterfall_subscriber_error_fails_open(store):
    stream = EventStream(store)
    reached = []

    async def broken(event, next_):
        raise RuntimeError("mw boom")

    async def ok(event, next_):
        reached.append(event.event_type)
        await next_()

    stream.subscribe(broken, mode="waterfall")
    stream.subscribe(ok, mode="waterfall")

    dr = await stream.emit_waterfall(_make_event("thinking_started", 0, StepState.THINKING))
    assert reached == ["thinking_started"]  # 异常中间件 fail-open，下游仍执行
    assert dr.aborted is False


async def test_waterfall_mode_fanout_emit_observers_see_all(store):
    """emit 观察者看到全部事件；waterfall 干预者只参与 waterfall dispatch。"""
    stream = EventStream(store)
    emit_seen = []
    wf_seen = []

    stream.subscribe(lambda e: emit_seen.append(e.event_type), mode="emit")
    async def wf(e, next_):
        wf_seen.append(e.event_type)
        await next_()
    stream.subscribe(wf, mode="waterfall")

    await stream.emit(_make_event("step_init", 0, StepState.INIT))
    await stream.emit_waterfall(_make_event("thinking_started", 1, StepState.THINKING))

    assert emit_seen == ["step_init", "thinking_started"]
    assert wf_seen == ["thinking_started"]


# =============================================================================
# 2. EventStream —— serial
# =============================================================================

async def test_serial_first_non_none_wins(store):
    stream = EventStream(store)
    calls = []

    def mw1(e):
        calls.append("mw1")
        return {"action": "allow"}

    def mw2(e):
        calls.append("mw2")
        return {"action": "deny"}

    stream.subscribe(mw1, mode="serial")
    stream.subscribe(mw2, mode="serial")

    dr = await stream.emit_serial(_make_event("interaction_request", 0, StepState.AWAITING_TOOL_PERMISSION))
    assert dr.decision == {"action": "allow"}
    assert calls == ["mw1"]  # 首个非 None/False 决策胜出，后续停止


async def test_serial_skips_none_and_false(store):
    stream = EventStream(store)
    calls = []

    def mw1(e):
        calls.append("mw1")
        return None

    def mw2(e):
        calls.append("mw2")
        return False

    def mw3(e):
        calls.append("mw3")
        return "allow"

    for mw in (mw1, mw2, mw3):
        stream.subscribe(mw, mode="serial")

    dr = await stream.emit_serial(_make_event("interaction_request", 0, StepState.AWAITING_TOOL_PERMISSION))
    assert dr.decision == "allow"
    assert calls == ["mw1", "mw2", "mw3"]


async def test_serial_all_none_returns_none_decision(store):
    stream = EventStream(store)
    stream.subscribe(lambda e: None, mode="serial")
    stream.subscribe(lambda e: False, mode="serial")
    dr = await stream.emit_serial(_make_event("interaction_request", 0, StepState.AWAITING_TOOL_PERMISSION))
    assert dr.decision is None


async def test_serial_async_callback_and_filter(store):
    stream = EventStream(store)
    seen = []

    async def mw(e):
        seen.append(e.event_type)
        return "deny"

    stream.subscribe(mw, event_types=["interaction_request"], mode="serial")
    dr = await stream.emit_serial(_make_event("interaction_request", 0, StepState.AWAITING_TOOL_PERMISSION))
    assert dr.decision == "deny"
    assert seen == ["interaction_request"]
    # 不匹配的事件类型不触发
    await stream.emit_serial(_make_event("tool_call", 1, StepState.ACTING))
    assert seen == ["interaction_request"]


async def test_serial_persists_before_notify(store):
    """durability-before-visibility：serial 回调触发时事件已落库。"""
    stream = EventStream(store)
    persisted_at_call = []

    async def mw(e):
        persisted = await store.get_events("conv-1")
        persisted_at_call.append(e.event_id in [p.event_id for p in persisted])
        return None

    stream.subscribe(mw, mode="serial")
    await stream.emit_serial(_make_event("interaction_request", 0, StepState.AWAITING_TOOL_PERMISSION))
    assert persisted_at_call == [True]


# =============================================================================
# 3. run_step 接缝集成
# =============================================================================

async def _thinking_fn(input_):
    yield {"token": "hi"}


async def _thinking_fn_with_tool(input_):
    yield {"token": "call"}
    yield {"token": "", "tool_calls": [{"tool": "read_file", "input": {"path": "/a"}}]}


async def _acting_fn(tool_call: V2ToolCall, ctx: ToolContext) -> V2ToolResult:
    return V2ToolResult.ok(output=f"executed:{tool_call.name}:{tool_call.args}", tool_name=tool_call.name)


async def test_run_step_thinking_waterfall_rewrites_request(store):
    stream = EventStream(store)
    seen_inputs = []

    async def thinking_fn(input_):
        seen_inputs.append(dict(input_))
        yield {"token": "ok"}

    async def rewrite(event, next_):
        event.input["prompt"] = "rewritten"
        await next_()

    stream.subscribe(rewrite, event_types=["thinking_started"], mode="waterfall")

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "orig"}, store, thinking_fn,
                            event_stream=stream):
        events.append(e)

    assert seen_inputs == [{"prompt": "rewritten"}]
    # 事件流正常走到 DONE
    assert events[-1].state is StepState.DONE


async def test_run_step_thinking_waterfall_aborts(store):
    stream = EventStream(store)
    thinking_called = []

    async def thinking_fn(input_):
        thinking_called.append(input_)
        yield {"token": "should-not-happen"}

    async def abort_mw(event, next_):
        return  # 中止

    stream.subscribe(abort_mw, event_types=["thinking_started"], mode="waterfall")

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, thinking_fn,
                            event_stream=stream):
        events.append(e)

    assert thinking_called == []  # LLM 未被调用
    types = [e.event_type for e in events]
    assert "step_aborted" in types
    assert "llm_token" not in types
    assert events[-1].state is StepState.DONE


async def test_run_step_tool_pre_execute_denies(store):
    stream = EventStream(store)
    acted = []

    async def acting_fn(tool_call, ctx):
        acted.append(tool_call)
        return V2ToolResult.ok(output="x", tool_name=tool_call.name)

    async def deny_mw(event, next_):
        event.output = {"denied": True, "reason": "blocked by policy"}
        await next_()

    stream.subscribe(deny_mw, event_types=["tool_pre_execute"], mode="waterfall")

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, _thinking_fn_with_tool,
                            acting_fn, event_stream=stream):
        events.append(e)

    assert acted == []  # 工具未执行
    tool_call_events = [e for e in events if e.event_type == "tool_call"]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].output["denied"] is True
    assert tool_call_events[0].output["reason"] == "blocked by policy"
    # 无 tool_result
    assert not [e for e in events if e.event_type == "tool_result"]


async def test_run_step_tool_pre_execute_aborts(store):
    stream = EventStream(store)
    acted = []

    async def acting_fn(tool_call, ctx):
        acted.append(tool_call)
        return V2ToolResult.ok(output="x", tool_name=tool_call.name)

    async def abort_mw(event, next_):
        return  # 不调 next → 中止

    stream.subscribe(abort_mw, event_types=["tool_pre_execute"], mode="waterfall")

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, _thinking_fn_with_tool,
                            acting_fn, event_stream=stream):
        events.append(e)

    assert acted == []
    tool_call_events = [e for e in events if e.event_type == "tool_call"]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].output["denied"] is True


async def test_run_step_tool_pre_execute_rewrites_args(store):
    stream = EventStream(store)
    acted_args = []

    async def acting_fn(tool_call, ctx):
        acted_args.append(tool_call.args)
        return V2ToolResult.ok(output="x", tool_name=tool_call.name)

    async def rewrite_mw(event, next_):
        event.input["input"] = {"path": "/rewritten"}
        await next_()

    stream.subscribe(rewrite_mw, event_types=["tool_pre_execute"], mode="waterfall")

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, _thinking_fn_with_tool,
                            acting_fn, event_stream=stream):
        events.append(e)

    assert acted_args == [{"path": "/rewritten"}]
    assert any(e.event_type == "tool_result" for e in events)


async def test_run_step_tool_pre_execute_passthrough_no_subscriber(store):
    """无订阅者时行为与旧版一致（回归保护）。"""
    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, _thinking_fn_with_tool,
                            _acting_fn):
        events.append(e)
    assert any(e.event_type == "tool_call" for e in events)
    assert any(e.event_type == "tool_result" for e in events)


# =============================================================================
# 4. PermissionGate serial 决策短路
# =============================================================================

def _gate(store, stream, ruleset, adapter=None):
    return PermissionGate(
        state_store=store, event_stream=stream,
        interaction_adapter=adapter,
        session_cache=SessionPermissionCache(),
        ruleset=ruleset, mode=PermissionMode.DEFAULT,
        step_id="step-1", conv_id="conv-1", agent_id="agent-1",
    )


def _ask_ruleset():
    return PermissionRuleset(rules={
        "rm": PermissionRule(tool_pattern="rm", action=PermissionAction.ASK)
    }, default_action=PermissionAction.ALLOW)


async def test_gate_serial_decision_allows_skips_adapter(store, stream):
    adapter_called = []

    class FakeAdapter:
        async def request_tool_permission(self, tool_name, tool_args, **kwargs):
            adapter_called.append(tool_name)
            class R:
                choice = "deny"
            return R()

    stream.subscribe(lambda e: "allow", event_types=["interaction_request"], mode="serial")
    gate = _gate(store, stream, _ask_ruleset(), adapter=FakeAdapter())

    events = [e async for e in gate.check({"tool": "rm", "input": {"path": "/x"}})]
    assert adapter_called == []  # serial 裁决短路，未阻塞用户
    assert gate.last_result.decision is PermissionDecision.ALLOW
    assert "serial subscriber" in gate.last_result.reason
    assert len(events) == 1
    assert events[0].event_type == "interaction_request"


async def test_gate_serial_decision_denies_skips_adapter(store, stream):
    adapter_called = []

    class FakeAdapter:
        async def request_tool_permission(self, tool_name, tool_args, **kwargs):
            adapter_called.append(tool_name)
            class R:
                choice = "allow_once"
            return R()

    stream.subscribe(lambda e: {"action": "deny"}, event_types=["interaction_request"], mode="serial")
    gate = _gate(store, stream, _ask_ruleset(), adapter=FakeAdapter())

    async for _ in gate.check({"tool": "rm", "input": {"path": "/x"}}):
        pass
    assert adapter_called == []
    assert gate.last_result.decision is PermissionDecision.DENY


async def test_gate_serial_no_decision_falls_back_to_adapter(store, stream):
    adapter_called = []

    class FakeAdapter:
        async def request_tool_permission(self, tool_name, tool_args, **kwargs):
            adapter_called.append(tool_name)
            class R:
                choice = "allow_once"
            return R()

    # 无 serial 订阅者（或全部返回 None/False）→ 回退 adapter
    stream.subscribe(lambda e: None, event_types=["interaction_request"], mode="serial")
    gate = _gate(store, stream, _ask_ruleset(), adapter=FakeAdapter())

    events = [e async for e in gate.check({"tool": "rm", "input": {"path": "/x"}})]
    assert adapter_called == ["rm"]
    assert gate.last_result.decision is PermissionDecision.ALLOW
    assert len(events) == 1


async def test_gate_serial_allows_without_adapter(store, stream):
    """serial 裁决时无需配置 InteractionAdapter（DSH 审批检查点可完全替代人工审批）。"""
    stream.subscribe(lambda e: "allow_once", event_types=["interaction_request"], mode="serial")
    gate = _gate(store, stream, _ask_ruleset(), adapter=None)

    events = [e async for e in gate.check({"tool": "rm", "input": {"path": "/x"}})]
    assert gate.last_result.decision is PermissionDecision.ALLOW
    assert len(events) == 1
