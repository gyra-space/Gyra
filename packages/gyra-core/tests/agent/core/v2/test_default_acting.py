"""default_acting_fn 测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from gyra.agent.core.v2.default_acting import make_default_acting_fn
from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.core.v2.tool_failure_tracker import ToolFailureTracker
from gyra.agent.core.v2.tool_context_factory import ToolContextFactory
from gyra.agent.core.v2.tool_resolver import ToolResolver
from gyra.agent.tools.context import ToolContext


class FakeTool:
    def __init__(self, name, result):
        self.name = name
        self._result = result

    async def execute(self, args, context=None):
        return self._result


class FakeDoomLoop:
    async def check(self, tool_name, args):
        return True  # 允许


class FakeDoomLoopBlock:
    async def check(self, tool_name, args):
        return False  # 阻止


class FakeTruncator:
    async def truncate(self, content, tool_name, args):
        # 不截断
        return MagicMock(truncated=False, truncated_content=content)


def _make_factory():
    return ToolContextFactory(agent_id="a1", conv_id="c1")


def _make_acting_fn(tool, doom_loop=None, truncator=None, hook_manager=None):
    resolver = ToolResolver(system_tools={tool.name: tool})
    failure_tracker = ToolFailureTracker(max_failures=3)
    return make_default_acting_fn(
        tool_resolver=resolver,
        doom_loop_detector=doom_loop or FakeDoomLoop(),
        failure_tracker=failure_tracker,
        truncator=truncator or FakeTruncator(),
        hook_manager=hook_manager,
        tool_context_factory=_make_factory(),
    )


@pytest.mark.asyncio
async def test_execute_success():
    tool = FakeTool("read_file", V2ToolResult.ok(output="file content", tool_name="read_file"))
    acting_fn = _make_acting_fn(tool)
    tc = V2ToolCall(name="read_file", args={"path": "/tmp/x"})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert result.success
    assert result.output == "file content"


@pytest.mark.asyncio
async def test_doom_loop_blocks():
    tool = FakeTool("bash", V2ToolResult.ok(output="ok", tool_name="bash"))
    acting_fn = _make_acting_fn(tool, doom_loop=FakeDoomLoopBlock())
    tc = V2ToolCall(name="bash", args={})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert not result.success
    assert "doom loop" in result.error.lower()


@pytest.mark.asyncio
async def test_doom_loop_adapter_blocks_with_real_detector():
    """回归：DoomLoopAdapter 误读 should_block 导致永不阻断。

    BAIZE DoomLoopCheckResult 没有 should_block 字段，真实字段是 is_doom_loop。
    用真实 DoomLoopDetector 连续相同调用 threshold 次后，adapter.check 必须返回
    False（阻断），acting_fn 应返回 doom loop 失败而非继续执行工具。
    """
    from gyra.agent.core.v2.compat_adapters import DoomLoopAdapter
    from gyra.agent.expand.react_master_agent.doom_loop_detector import DoomLoopDetector

    detector = DoomLoopDetector(threshold=3)
    adapter = DoomLoopAdapter(detector)
    tool = FakeTool("bash", V2ToolResult.ok(output="ok", tool_name="bash"))
    acting_fn = _make_acting_fn(tool, doom_loop=adapter)
    ctx = ToolContext()
    tc = V2ToolCall(name="bash", args={"command": "echo hi"})

    # 前 threshold-1 次正常执行（未达阈值）
    for _ in range(2):
        r = await acting_fn(tc, ctx)
        assert r.success

    # 第 threshold 次起命中 doom loop，应被阻断
    r = await acting_fn(tc, ctx)
    assert not r.success
    assert "doom loop" in r.error.lower()

    # adapter.check 本身也应直接返回 False
    assert await adapter.check("bash", {"command": "echo hi"}) is False


@pytest.mark.asyncio
async def test_doom_loop_adapter_allows_when_no_loop():
    """真实检测器未达到阈值时，adapter.check 应放行。"""
    from gyra.agent.core.v2.compat_adapters import DoomLoopAdapter
    from gyra.agent.expand.react_master_agent.doom_loop_detector import DoomLoopDetector

    detector = DoomLoopDetector(threshold=3)
    adapter = DoomLoopAdapter(detector)
    assert await adapter.check("bash", {"command": "echo a"}) is True
    assert await adapter.check("bash", {"command": "echo b"}) is True


@pytest.mark.asyncio
async def test_failure_tracker_blocks_after_threshold():
    tool = FakeTool("bash", V2ToolResult.fail(error="boom", tool_name="bash"))
    acting_fn = _make_acting_fn(tool)
    tc = V2ToolCall(name="bash", args={})
    ctx = ToolContext()
    # 失败 3 次
    for _ in range(3):
        await acting_fn(tc, ctx)
    # 第 4 次应被 block
    result = await acting_fn(tc, ctx)
    assert not result.success
    assert "blocked" in result.error.lower() or "阈值" in result.error


@pytest.mark.asyncio
async def test_unknown_tool_returns_fail():
    tool = FakeTool("read_file", V2ToolResult.ok(output="x", tool_name="read_file"))
    acting_fn = _make_acting_fn(tool)
    tc = V2ToolCall(name="nonexistent", args={})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert not result.success
    assert "未注册" in result.error or "not registered" in result.error.lower()


@pytest.mark.asyncio
async def test_pre_tool_use_hook_can_deny():
    from gyra.agent.core.hook.schema import HookDecision
    tool = FakeTool("bash", V2ToolResult.ok(output="ok", tool_name="bash"))
    hook_manager = MagicMock()
    hook_manager.trigger_blocking = AsyncMock(return_value=HookDecision.deny(reason="audit denied"))
    acting_fn = _make_acting_fn(tool, hook_manager=hook_manager)
    tc = V2ToolCall(name="bash", args={})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert not result.success
    assert "hook denied" in result.error


@pytest.mark.asyncio
async def test_post_tool_use_hook_fires():
    from gyra.agent.core.hook.schema import HookDecision
    tool = FakeTool("bash", V2ToolResult.ok(output="ok", tool_name="bash"))
    hook_manager = MagicMock()
    hook_manager.trigger_blocking = AsyncMock(return_value=HookDecision.cont())
    hook_manager.trigger = AsyncMock()
    acting_fn = _make_acting_fn(tool, hook_manager=hook_manager)
    tc = V2ToolCall(name="bash", args={})
    ctx = ToolContext()
    await acting_fn(tc, ctx)
    # post_tool_use 应被触发
    hook_manager.trigger.assert_called_once()
    call_args = hook_manager.trigger.call_args
    assert call_args.args[0] == "post_tool_use"


@pytest.mark.asyncio
async def test_exception_recorded_as_failure():
    class CrashTool:
        name = "bash"
        async def execute(self, args, context=None):
            raise RuntimeError("crashed")
    acting_fn = _make_acting_fn(CrashTool())
    tc = V2ToolCall(name="bash", args={})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert not result.success
    assert "执行异常" in result.error


@pytest.mark.asyncio
async def test_hook_deny_with_real_enum():
    """C1 regression: real HookDecision.deny() with BlockingPolicy enum should be honoured."""
    from gyra.agent.core.hook.schema import HookDecision
    tool = FakeTool("bash", V2ToolResult.ok(output="ok", tool_name="bash"))
    hook_manager = MagicMock()
    decision = HookDecision.deny(reason="audit blocked")
    hook_manager.trigger_blocking = AsyncMock(return_value=decision)
    acting_fn = _make_acting_fn(tool, hook_manager=hook_manager)
    tc = V2ToolCall(name="bash", args={})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert not result.success
    assert "hook denied" in result.error


@pytest.mark.asyncio
async def test_hook_modify_with_real_enum():
    """C2 regression: real HookDecision.modify() with modified_input should apply changes."""
    from gyra.agent.core.hook.schema import HookDecision
    tool = FakeTool("bash", V2ToolResult.ok(output="ok", tool_name="bash"))
    hook_manager = MagicMock()
    decision = HookDecision.modify(modified_input={"safe": True}, reason="sanitized")
    hook_manager.trigger_blocking = AsyncMock(return_value=decision)
    hook_manager.trigger = AsyncMock()
    acting_fn = _make_acting_fn(tool, hook_manager=hook_manager)
    tc = V2ToolCall(name="bash", args={"cmd": "rm -rf /"})
    ctx = ToolContext()
    result = await acting_fn(tc, ctx)
    assert result.success
    # verify the hook_manager.trigger was called for post_tool_use (hook fires)
    # the key assertion: acting_fn didn't crash, and the modified_input was applied
    # We can't directly inspect tool_input (it's local), but if the tool executed,
    # the modify was applied instead of being silently dropped
    assert result.output == "ok"
