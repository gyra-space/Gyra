"""run_loop 多轮循环测试。"""
import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock
from gyra.agent.core.v2.run_loop import run_loop
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_state import StepState


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DbStateStore(path)
    os.unlink(path)


async def _thinking_no_tools(input_):
    """thinking_fn 不 emit tool_calls → 单 step turn。"""
    yield {"token": "final answer"}


async def _acting_return_ok(tool_call, ctx):
    from gyra.agent.core.v2.tool_call_types import V2ToolResult
    return V2ToolResult.ok(output="tool result", tool_name="test_tool")


async def test_single_step_turn(store):
    """thinking 不 emit tool_calls → run_loop 跑一个 step 就结束。"""
    events = []
    async for e in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=_thinking_no_tools,
        acting_fn=_acting_return_ok,
        max_steps=5,
    ):
        events.append(e)
    # 应有 INIT / THINKING / DONE
    states = [e.state for e in events]
    assert states[0] == StepState.INIT
    assert states[-1] == StepState.DONE


async def test_max_steps_caps_loop(store):
    """max_steps=1 时只跑 1 个 step。"""
    call_count = {"n": 0}
    async def thinking(input_):
        call_count["n"] += 1
        yield {"token": "x"}

    events = []
    async for e in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=thinking,
        acting_fn=_acting_return_ok,
        max_steps=1,
    ):
        events.append(e)
    assert call_count["n"] == 1


async def test_turn_complete_hook_fires(store):
    """turn 结束时触发 HookManager.turn_complete。"""
    hook_manager = MagicMock()
    hook_manager.trigger = AsyncMock()
    async for _ in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=_thinking_no_tools,
        acting_fn=_acting_return_ok,
        hook_manager=hook_manager,
        max_steps=5,
    ):
        pass
    hook_manager.trigger.assert_called()
    # 至少一次 turn_complete
    calls = [c.args[0] for c in hook_manager.trigger.call_args_list]
    assert "turn_complete" in calls


async def test_awaiting_user_returns(store):
    """thinking_fn emit await_user=True → AWAITING_USER → run_loop 应 return。"""
    async def thinking(input_):
        yield {"await_user": True}

    events = []
    async for e in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=thinking,
        acting_fn=_acting_return_ok,
        max_steps=5,
    ):
        events.append(e)

    # 应有 AWAITING_USER 事件
    states = [e.state for e in events]
    assert StepState.AWAITING_USER in states
    # 不应有 DONE 事件（step 被暂停）
    assert StepState.DONE not in states


async def test_multi_step_turn(store):
    """thinking emit tool_call → acting → thinking 再无 tool_call → turn 结束。"""
    state = {"call": 0}

    async def thinking(input_):
        state["call"] += 1
        if state["call"] == 1:
            yield {"token": "calling", "tool_calls": [{"tool": "read_file", "input": {}}]}
        else:
            yield {"token": "final"}

    from gyra.agent.core.v2.tool_call_types import V2ToolResult

    async def acting(tool_call, ctx):
        return V2ToolResult.ok(output="ok", tool_name="read_file")

    events = []
    async for e in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=thinking,
        acting_fn=acting,
        max_steps=5,
    ):
        events.append(e)

    # 应有 2 个 step（thinking 调了 2 次）
    assert state["call"] == 2
    # 应有 1 个 tool_call + 1 个 tool_result
    tool_calls = [e for e in events if e.event_type == "tool_call"]
    tool_results = [e for e in events if e.event_type == "tool_result"]
    assert len(tool_calls) == 1
    assert len(tool_results) == 1


async def test_multi_step_tool_history_global_seq(store):
    """多步工具循环：事件 seq 全局单调续号，工具历史投影保持时序与配对正确。

    回归 Bug A：旧实现每步 seq 从 0 开始，且各步 token 数不同导致 tool_call 落点
    不同（step2 的 tool_call 可能排到 step1 之前），get_events 按 seq 排序会把
    多步事件交错打乱，project_tool_history 输出乱序/错配，模型看不到正确工具历史
    而陷入工具死循环。
    """
    from gyra.agent.core.v2.event_projection import project_tool_history
    from gyra.agent.core.v2.tool_call_types import V2ToolResult

    state = {"call": 0}

    async def thinking(input_):
        state["call"] += 1
        if state["call"] == 1:
            # 第 1 步：多发几轮 token → tool_call 落在更高 seq
            for i in range(5):
                yield {"token": f"t1-{i}"}
            yield {"tool_calls": [{"tool": "tool_1", "input": {"k": 1}}]}
        elif state["call"] == 2:
            # 第 2 步：少发 token → tool_call 落在更低 seq（旧实现下会先于 step1）
            yield {"token": "t2"}
            yield {"tool_calls": [{"tool": "tool_2", "input": {"k": 2}}]}
        else:
            yield {"token": "final"}

    async def acting(tool_call, ctx):
        return V2ToolResult.ok(output=f"res-{tool_call.name}", tool_name=tool_call.name)

    async for _ in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=thinking,
        acting_fn=acting,
        max_steps=5,
    ):
        pass

    events = await store.get_events("c1")
    # 全局单调：step2 的 tool_call seq 必须大于 step1 的 tool_call seq
    tc_seqs = {
        ev.input.get("tool"): ev.seq
        for ev in events
        if ev.event_type == "tool_call"
    }
    assert tc_seqs.get("tool_1") is not None and tc_seqs.get("tool_2") is not None
    assert tc_seqs["tool_1"] < tc_seqs["tool_2"], (
        f"seq 非全局单调（tool_call 错位）: {tc_seqs}"
    )

    # 投影必须严格按执行顺序配对：tool_1 → res-tool_1, tool_2 → res-tool_2
    msgs = await project_tool_history(store, "c1")
    assert len(msgs) == 4, f"投影消息数错误: {msgs}"
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "tool_1"
    assert msgs[1]["content"] == "res-tool_1"
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "tool_2"
    assert msgs[3]["content"] == "res-tool_2"


async def test_max_steps_no_double_turn_complete(store):
    """max_steps reached on no-tool step should fire turn_complete only once."""
    call_count = {"n": 0}
    async def thinking(input_):
        call_count["n"] += 1
        yield {"token": "x"}  # no tool_calls

    hook_manager = MagicMock()
    hook_manager.trigger = AsyncMock()
    async for _ in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=thinking,
        acting_fn=_acting_return_ok,
        hook_manager=hook_manager,
        max_steps=1,
    ):
        pass
    turn_complete_calls = [c for c in hook_manager.trigger.call_args_list if c.args[0] == "turn_complete"]
    assert len(turn_complete_calls) == 1, f"Expected 1 turn_complete, got {len(turn_complete_calls)}"


async def test_run_loop_forwards_tool_context_factory(store):
    """回归：run_loop 必须把 tool_context_factory 透传给 run_step。

    之前 tool_context_factory 只在 HarnessContext 里存在，run_loop → run_step
    均未转发，导致工具执行的 ToolContext 是不带任何资源的裸上下文，
    RBAC 等 fail-closed 工具拿不到 user_request 而误报"缺少用户上下文"。
    """
    from gyra.agent.core.v2.tool_call_types import V2ToolResult
    from gyra.agent.core.v2.tool_context_factory import ToolContextFactory

    marker = {"user_id": "admin", "roles": ["admin"]}
    factory = ToolContextFactory(
        agent_id="a1", conv_id="c1", user_request=marker,
    )

    captured = {}

    async def thinking(input_):
        yield {"tool_calls": [{"tool": "probe", "input": {}}]}

    async def acting(tool_call, ctx):
        captured["resource"] = ctx.get_resource("user_request")
        captured["config"] = ctx.config.get("user_request")
        return V2ToolResult.ok(output="ok", tool_name=tool_call.name)

    async for _ in run_loop(
        agent_id="a1", conv_id="c1",
        input_={"prompt": "hi", "session_id": "s1"},
        state_store=store,
        thinking_fn=thinking,
        acting_fn=acting,
        tool_context_factory=factory,
        max_steps=3,
    ):
        pass

    assert captured["resource"] is marker, "工具上下文缺少 user_request 资源"
    assert captured["config"] is marker, "工具上下文 config 缺少 user_request"
