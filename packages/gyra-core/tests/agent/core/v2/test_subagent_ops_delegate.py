"""SubAgentOpsDelegate 桥接测试：SubAgentRuntime 的委托交互行为。

覆盖目标（设计文档 §3.3 / 验收清单）：
- 无 delegate：spawn ASYNC 行为与改造前一致（回归）
- delegate 注入：ASYNC spawn 调 try_register(created=True)，建执行体，
  终态 DONE 回调 on_terminal（result_text 带 answer）
- 去重命中（created=False）：spawn 短路——sub_conv_id 改写为已有任务、
  transcript_id=None、不建 asyncio task、不触发 on_terminal
- try_register 抛异常：spawn 照常执行（委托故障不阻断引擎）
- on_terminal 抛异常：不影响子任务终态
- FAILED（thinking_fn 缺失早退）：on_terminal 仍被回调（error 文案透传）
- 进度上报：多步 run_loop 产生 step 级事件时 update_progress 被调
- 幂等：on_terminal 对同一 task 只回调一次
"""
import os
import tempfile

import pytest

from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.subagent_handle import SubAgentStatus
from gyra.agent.core.v2.subagent_ops_delegate import SubAgentRegistration
from gyra.agent.core.v2.subagent_runtime import (
    SubAgentRuntime,
    SubAgentSpawnSpec,
)
from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.tools.context import ToolContext


class FakeDelegate:
    def __init__(
        self,
        registration: SubAgentRegistration | None = None,
        fail_try_register: bool = False,
        fail_terminal: bool = False,
    ):
        self.try_register_calls = []
        self.progress_calls = []
        self.terminal_calls = []
        self._registration = registration
        self._fail_try_register = fail_try_register
        self._fail_terminal = fail_terminal

    async def try_register(self, handle, spec):
        self.try_register_calls.append((handle, spec))
        if self._fail_try_register:
            raise RuntimeError("boom-register")
        if self._registration is not None:
            return self._registration
        return SubAgentRegistration(
            created=True,
            task_id=handle.task_id,
            sub_conv_id=handle.sub_conv_id,
        )

    async def update_progress(self, handle, progress, note=""):
        self.progress_calls.append((handle.task_id, progress, note))

    async def on_terminal(self, handle, result_text="", error=""):
        self.terminal_calls.append(
            (handle.task_id, handle.status, result_text, error)
        )
        if self._fail_terminal:
            raise RuntimeError("boom-terminal")


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = DbStateStore(path)
    yield s
    os.unlink(path)


async def _sub_thinking(input_):
    yield {"token": "hello ", "tool_calls": []}


async def _multi_step_thinking(input_):
    yield {"token": "", "tool_calls": [{"tool": "echo", "input": {}}]}
    yield {"token": "final answer", "tool_calls": []}


async def _echo_acting(tc: V2ToolCall, ctx: ToolContext) -> V2ToolResult:
    return V2ToolResult.ok(output="ok", tool_name=tc.name)


_UNSET = object()


def _make_spec(
    task="do something",
    run_in_background=False,
    thinking_fn=_UNSET,
    acting_fn=_UNSET,
):
    # 哨兵默认：显式传 None 表示真的不给 fn（触发引擎早退 FAILED 分支）
    return SubAgentSpawnSpec(
        agent_name="BAIZE",
        task=task,
        run_in_background=run_in_background,
        context={},
        parent_step_id="step-p",
        parent_conv_id="conv-p",
        parent_agent_id="agent-p",
        depth=0,
        thinking_fn=_sub_thinking if thinking_fn is _UNSET else thinking_fn,
        acting_fn=_echo_acting if acting_fn is _UNSET else acting_fn,
    )


async def test_no_delegate_spawn_async_unchanged(store):
    """无 delegate：行为与未桥接前一致（transcript 正常、终态 DONE）。"""
    runtime = SubAgentRuntime(state_store=store, max_depth=5)
    handle = await runtime.spawn(_make_spec(run_in_background=True))
    await runtime.wait(handle, timeout=2.0)
    assert handle.status is SubAgentStatus.DONE
    assert handle.transcript_id is not None


async def test_delegate_try_register_created_then_terminal_done(store):
    delegate = FakeDelegate()
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    handle = await runtime.spawn(_make_spec(run_in_background=True))
    await runtime.wait(handle, timeout=2.0)

    assert len(delegate.try_register_calls) == 1
    reg_handle, reg_spec = delegate.try_register_calls[0]
    assert reg_handle.task_id == handle.task_id
    assert reg_spec.task == "do something"
    assert len(delegate.terminal_calls) == 1
    task_id, status, result_text, error = delegate.terminal_calls[0]
    assert task_id == handle.task_id
    assert status is SubAgentStatus.DONE
    assert "hello" in result_text
    assert error == ""


async def test_delegate_dedup_short_circuits_spawn(store):
    """去重命中：短路复用在途任务，不建执行体、不触发终态回调。"""
    delegate = FakeDelegate(
        registration=SubAgentRegistration(
            created=False,
            task_id="task-ignored",
            sub_conv_id="conv-existing",
            status="running",
        )
    )
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    handle = await runtime.spawn(_make_spec(run_in_background=True))

    assert handle.sub_conv_id == "conv-existing"
    assert handle.transcript_id is None
    assert handle.status is SubAgentStatus.RUNNING
    assert handle.task_id not in runtime._async_tasks
    assert handle.task_id not in runtime._handles
    assert delegate.terminal_calls == []


async def test_delegate_try_register_failure_does_not_block(store):
    """try_register 抛异常：引擎照常建执行体并完成。"""
    delegate = FakeDelegate(fail_try_register=True)
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    handle = await runtime.spawn(_make_spec(run_in_background=True))
    await runtime.wait(handle, timeout=2.0)
    assert handle.status is SubAgentStatus.DONE
    assert len(delegate.terminal_calls) == 1


async def test_delegate_terminal_failure_does_not_affect_status(store):
    """on_terminal 抛异常：不影响子任务终态与结果。"""
    delegate = FakeDelegate(fail_terminal=True)
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    handle = await runtime.spawn(_make_spec(run_in_background=True))
    await runtime.wait(handle, timeout=2.0)
    assert handle.status is SubAgentStatus.DONE


async def test_delegate_on_terminal_called_for_early_failed(store):
    """thinking_fn 缺失早退 FAILED：on_terminal 仍被回调（error 透传）。"""
    delegate = FakeDelegate()
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    spec = _make_spec(run_in_background=True, thinking_fn=None)
    handle = await runtime.spawn(spec)
    await runtime.wait(handle, timeout=2.0)

    assert handle.status is SubAgentStatus.FAILED
    assert len(delegate.terminal_calls) == 1
    _, status, _, error = delegate.terminal_calls[0]
    assert status is SubAgentStatus.FAILED
    assert "thinking_fn unavailable" in error


async def test_delegate_progress_reported_per_step(store):
    """多步 run_loop：step 级事件触发 update_progress（1-95 区间）。"""
    delegate = FakeDelegate()
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    spec = _make_spec(
        run_in_background=True,
        thinking_fn=_multi_step_thinking,
        acting_fn=_echo_acting,
    )
    handle = await runtime.spawn(spec)
    await runtime.wait(handle, timeout=3.0)

    assert len(delegate.progress_calls) >= 1
    for _, progress, note in delegate.progress_calls:
        assert 1 <= progress <= 95
        assert isinstance(note, str)


async def test_delegate_on_terminal_idempotent(store):
    """终态回调幂等：同一 task 只回调一次。"""
    delegate = FakeDelegate()
    runtime = SubAgentRuntime(
        state_store=store, max_depth=5, ops_delegate=delegate
    )
    spec = _make_spec(run_in_background=True, thinking_fn=None)
    handle = await runtime.spawn(spec)
    await runtime.wait(handle, timeout=2.0)
    await runtime._notify_terminal(handle)
    await runtime._notify_terminal(handle)
    assert len(delegate.terminal_calls) == 1
