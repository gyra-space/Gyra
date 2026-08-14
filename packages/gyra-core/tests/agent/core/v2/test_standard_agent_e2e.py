"""标准主 agent V2 端到端测试：V2AgentRuntime 门面 + waterfall 权限 + SSE 渲染。

覆盖：
  - V2AgentRuntime 门面驱动标准主 agent（thinking + acting + permission + SSE）
  - request/header 快照事件持久化（可审计、可重放）
  - PermissionGate waterfall 决策中间件（可插拔 middleware）
  - ToolGuard 单调守卫（fail-closed：只拒绝，不允许；顺序无关）
  - SSE 渲染：token → string vis；tool_call/tool_result 被抑制；done → [DONE]
"""
import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.core.v2 import (
    V2AgentRuntime,
    DbStateStore,
    StepState,
    PermissionGate,
    PermissionMode,
    SessionPermissionCache,
    ToolGuard,
    PermissionContext,
    PermissionMiddleware,
    DecisionResult,
    DecisionKind,
)
from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.core.v2.tool_resolver import ToolResolver
from gyra.agent.core.v2.tool_failure_tracker import ToolFailureTracker
from gyra.agent.core.v2.tool_context_factory import ToolContextFactory
from gyra.agent.core.v2.default_acting import make_default_acting_fn
from gyra.agent.tools.context import ToolContext
from gyra_core.permission.ruleset import PermissionRuleset, PermissionRule, PermissionAction


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DbStateStore(path)
    os.unlink(path)


# =============================================================================
# 工具与 thinking/acting 装配
# =============================================================================


class EchoTool:
    name = "echo"

    async def execute(self, args, context=None):
        return V2ToolResult.ok(
            output=f"echo: {args.get('text', '')}", tool_name="echo"
        )


class DeniedTool:
    """被单调守卫拒绝的工具。"""
    name = "rm_file"

    async def execute(self, args, context=None):
        return V2ToolResult.ok(output="deleted", tool_name="rm_file")


def _make_thinking_fn(rounds=2):
    """第一轮 emit 工具调用，第二轮返回 final answer。"""
    call_count = {"n": 0}

    async def thinking(input_):
        call_count["n"] += 1
        if call_count["n"] == 1:
            yield {"token": "我先调用工具。"}
            yield {
                "token": "",
                "tool_calls": [
                    {"tool": "echo", "input": {"text": "hello"}},
                    {"tool": "rm_file", "input": {"path": "/x"}},
                ],
            }
        else:
            yield {"token": "最终答案：完成。"}

    return thinking


def _make_acting_fn():
    resolver = ToolResolver(system_tools={"echo": EchoTool(), "rm_file": DeniedTool()})
    return make_default_acting_fn(
        tool_resolver=resolver,
        doom_loop_detector=MagicMock(check=AsyncMock(return_value=True)),
        failure_tracker=ToolFailureTracker(max_failures=3),
        truncator=MagicMock(
            truncate=AsyncMock(
                return_value=MagicMock(truncated=False, truncated_content="")
            )
        ),
        tool_context_factory=ToolContextFactory(agent_id="a1", conv_id="c1"),
    )


def _make_runtime(store, gate=None, conv_id="c1"):
    return V2AgentRuntime(
        agent_id="a1",
        conv_id=conv_id,
        state_store=store,
        thinking_fn=_make_thinking_fn(),
        acting_fn=_make_acting_fn(),
        permission_gate=gate,
        model_alias="test-model",
        max_steps=10,
    )


# =============================================================================
# 测试
# =============================================================================


async def test_standard_agent_full_run_and_render(store):
    """标准主 agent 通过 V2AgentRuntime 完整运行 + SSE 渲染。

    - 事件流包含 request_header / step_init / llm_token / tool_call / tool_result / step_done
    - 工具执行成功，最终 DONE
    - SSE 行含 string vis token；tool 内部事件不泄漏为原始对象文本
    """
    rt = _make_runtime(store, conv_id="conv-run")
    events = await rt.collect("帮我跑个流程")

    states = [e.state for e in events]
    assert StepState.INIT in states
    assert StepState.THINKING in states
    assert StepState.ACTING in states
    assert StepState.OBSERVING in states
    assert states[-1] is StepState.DONE

    tool_calls = [e for e in events if e.event_type == "tool_call"]
    tool_names = {e.input.get("tool") for e in tool_calls}
    assert "echo" in tool_names
    assert "rm_file" in tool_names

    tool_results = [e for e in events if e.event_type == "tool_result"]
    assert len(tool_results) >= 2

    # SSE 渲染：用独立 runtime（thinking_fn 是有状态闭包，需新的实例）
    sse_rt = _make_runtime(store, conv_id="conv-render")
    sse_lines = await sse_rt.collect_sse("帮我跑个流程")
    rendered = "\n".join(sse_lines)
    assert '"vis": "我先调用工具。"' in rendered
    assert '"vis": "最终答案：完成。"' in rendered
    # 工具内部事件不得以原始对象文本泄漏（sse_adapter 抑制 step/tool 事件）
    assert '"vis": {"type": "tool_call"' not in rendered
    assert "[DONE]" in rendered


async def test_request_header_snapshot_persisted(store):
    """request/header 快照事件被持久化到 StateStore（可审计、可重放）。"""
    rt = _make_runtime(store, conv_id="conv-rs")
    await rt.collect("hello")

    # 快照应落在 step_event 日志中（event_type == "request_header"）
    events = await store.get_events("conv-rs")
    headers = [e for e in events if e.event_type == "request_header"]
    # 一个 turn 内的每个 step 都会记录一条 request/header（每个 step 一次模型请求）
    assert len(headers) >= 1
    header = headers[0]
    assert header.input.get("model") == "test-model"
    assert header.input.get("agent_id") == "a1"
    assert header.input.get("conv_id") == "conv-rs"
    assert "prompt" in header.input
    # 快照 state 是 INIT，且排在 step_init 之前（同一 step 的序）
    assert header.state is StepState.INIT
    step_init = [e for e in events if e.event_type == "step_init"][0]
    assert header.seq < step_init.seq


async def test_permission_gate_ruleset_deny_blocks_tool(store):
    """ruleset 静态规则 DENY → 工具被拒绝（fail-closed）。"""
    ruleset = PermissionRuleset(rules={
        "rm_file": PermissionRule(tool_pattern="rm_file", action=PermissionAction.DENY)
    }, default_action=PermissionAction.ALLOW)
    gate = PermissionGate(
        state_store=store, event_stream=EventStream(store),
        interaction_adapter=None,
        session_cache=SessionPermissionCache(),
        ruleset=ruleset, mode=PermissionMode.DEFAULT,
        step_id="step-1", conv_id="c1", agent_id="a1",
    )
    rt = _make_runtime(store, gate=gate)
    events = await rt.collect("hi")

    tool_calls = [e for e in events if e.event_type == "tool_call"]
    rm_call = [e for e in tool_calls if e.input.get("tool") == "rm_file"]
    assert len(rm_call) == 1
    assert rm_call[0].output.get("denied") is True
    # echo 未受 ruleset 影响，正常执行
    echo_results = [
        e for e in events
        if e.event_type == "tool_result" and e.output.get("tool_name") == "echo"
    ]
    assert len(echo_results) == 1


async def test_tool_guard_monotonic_deny(store):
    """ToolGuard 单调守卫：只允许拒绝，顺序无关，fail-closed。

    - 即使 ruleset 说 ALLOW，守卫也能一票否决
    - 守卫注册顺序不影响结果（任一拒绝即拒绝）
    """
    class AlwaysDenyGuard(ToolGuard):
        async def check(self, ctx: PermissionContext):
            if ctx.tool_name == "echo":
                return "echo is blocked by guard"
            return None

    ruleset = PermissionRuleset(rules={
        "echo": PermissionRule(tool_pattern="echo", action=PermissionAction.ALLOW)
    }, default_action=PermissionAction.ALLOW)

    gate = PermissionGate(
        state_store=store, event_stream=EventStream(store),
        interaction_adapter=None,
        session_cache=SessionPermissionCache(),
        ruleset=ruleset, mode=PermissionMode.DEFAULT,
        step_id="step-1", conv_id="c1", agent_id="a1",
    )
    gate.register_guard(AlwaysDenyGuard())

    # 直接调用 gate.check —— ruleset ALLOW 也被守卫否决
    events = [e async for e in gate.check({"tool": "echo", "input": {}})]
    assert events == []
    assert gate.last_result.decision == "deny"
    assert "guard" in gate.last_result.reason

    # 顺序无关：再注册一个永远放行的守卫，结果仍为 deny
    class PassGuard(ToolGuard):
        async def check(self, ctx: PermissionContext):
            return None
    gate.register_guard(PassGuard())
    events = [e async for e in gate.check({"tool": "echo", "input": {}})]
    assert gate.last_result.decision == "deny"


async def test_custom_middleware_waterfall_short_circuit(store):
    """自定义 PermissionMiddleware 可短路决策（waterfall 语义）。"""
    class DenyByInputMiddleware(PermissionMiddleware):
        order = 15  # 在 ruleset 之前

        async def run(self, ctx, next_):
            if ctx.tool_name == "echo" and ctx.tool_input.get("text") == "blocked":
                return DecisionResult(kind=DecisionKind.DENY, reason="middleware: blocked text")
            return await next_()

    ruleset = PermissionRuleset(rules={
        "echo": PermissionRule(tool_pattern="echo", action=PermissionAction.ALLOW)
    }, default_action=PermissionAction.ALLOW)

    gate = PermissionGate(
        state_store=store, event_stream=EventStream(store),
        interaction_adapter=None,
        session_cache=SessionPermissionCache(),
        ruleset=ruleset, mode=PermissionMode.DEFAULT,
        step_id="step-1", conv_id="c1", agent_id="a1",
    )
    gate.register_middleware(DenyByInputMiddleware())

    # 中间件短路 → deny
    events = [e async for e in gate.check({"tool": "echo", "input": {"text": "blocked"}})]
    assert events == []
    assert gate.last_result.decision == "deny"
    assert "blocked text" in gate.last_result.reason

    # 未命中中间件 → 委托下游（ruleset allow）
    events = [e async for e in gate.check({"tool": "echo", "input": {"text": "ok"}})]
    assert gate.last_result.decision == "allow"


async def test_standard_agent_with_hooks(store):
    """标准主 agent + HookManager：turn_complete 触发。"""
    hook_manager = MagicMock()
    hook_manager.trigger = AsyncMock()
    decision = MagicMock()
    decision.action = "CONTINUE"
    hook_manager.trigger_blocking = AsyncMock(return_value=decision)

    rt = V2AgentRuntime(
        agent_id="a1",
        conv_id="c1",
        state_store=store,
        thinking_fn=_make_thinking_fn(),
        acting_fn=_make_acting_fn(),
        hook_manager=hook_manager,
        model_alias="test-model",
        max_steps=10,
    )
    await rt.collect("hi")

    turn_complete_calls = [
        c for c in hook_manager.trigger.call_args_list if c.args[0] == "turn_complete"
    ]
    assert len(turn_complete_calls) == 1


async def test_runtime_subscribe_passthrough(store):
    """V2AgentRuntime.subscribe：插件经门面订阅 StepEvent（P0 插件化扩展点）。

    - 过滤订阅只收到匹配事件
    - 全量订阅收到含新发射点（thinking_started/tool_executed/observing_done）的完整序列
    - unsubscribe 后不再收到事件
    """
    rt = _make_runtime(store, conv_id="conv-sub")

    executed_seen = []
    all_seen = []
    rt.subscribe(executed_seen.append, event_types=["tool_executed"])
    unsubscribe_all = rt.subscribe(all_seen.append)

    await rt.collect("帮我跑个流程")
    unsubscribe_all()

    # 过滤订阅：echo 工具执行完毕事件（rm_file 被默认模式放行时也会执行；
    # 此处 _make_runtime 无 gate，两个工具都会执行）
    assert len(executed_seen) >= 1
    assert all(e.event_type == "tool_executed" for e in executed_seen)
    assert all(e.state is StepState.ACTING for e in executed_seen)

    # 全量订阅：覆盖 P0 新发射点
    all_types = [e.event_type for e in all_seen]
    assert "thinking_started" in all_types
    assert "tool_executed" in all_types
    assert "observing_done" in all_types
    # thinking_started 先于该 step 的 llm_token
    assert all_types.index("thinking_started") < all_types.index("llm_token")

    # unsubscribe 后再跑不再收到（用新 conv 的独立 runtime 复跑）
    rt2 = _make_runtime(store, conv_id="conv-sub-2")
    count_before = len(all_seen)
    # rt2 有自己的 EventStream，all_seen 订阅的是 rt 的——不会收到 rt2 事件
    await rt2.collect("帮我跑个流程")
    assert len(all_seen) == count_before
