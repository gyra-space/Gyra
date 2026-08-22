"""HarnessContext 服务总线测试——统一装配 + run_loop/run_step 消费 harness。"""
import os
import tempfile

import pytest

from gyra.agent.core.v2.harness import HarnessContext, JobRegistry, SubagentSeam
from gyra.agent.core.v2.harness.seams import SubagentSeam as _SeamABC
from gyra.agent.core.v2.run_loop import run_loop
from gyra.agent.core.v2.runtime import run_step, resume_step
from gyra.agent.core.v2.state_store import create_state_store
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.subagent_runtime import SubAgentRuntime


@pytest.fixture
def data_dir():
    d = tempfile.mkdtemp(suffix="-harness")
    yield d
    for f in os.listdir(d):
        os.unlink(os.path.join(d, f))
    os.rmdir(d)


async def _thinking_no_tools(input_):
    yield {"token": "final answer"}


async def _acting_return_ok(tool_call, ctx):
    from gyra.agent.core.v2.tool_call_types import V2ToolResult
    return V2ToolResult.ok(output="tool result", tool_name="test_tool")


def test_build_creates_persistent_store(data_dir):
    """build() 创建真实持久化 StateStore（落 data_dir，非 tempdir）。"""
    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=data_dir,
        thinking_fn=_thinking_no_tools, acting_fn=_acting_return_ok,
    )
    # storage 是 DbStateStore，且对应文件在 data_dir 下
    assert harness.storage is not None
    assert harness.events is not None
    assert harness.jobs is not None
    files = os.listdir(data_dir)
    assert any(f.endswith(".db") for f in files)


async def test_run_loop_consumes_harness_only(data_dir):
    """run_loop 只传 harness 即可运行（thinking/acting/state/events 从 harness 解包）。"""
    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=data_dir,
        thinking_fn=_thinking_no_tools, acting_fn=_acting_return_ok,
    )
    events = []
    async for e in run_loop(agent_id="a1", conv_id="c1",
                            input_={"prompt": "hi", "session_id": "s1"},
                            harness=harness, max_steps=5):
        events.append(e)
    assert events[0].state is StepState.INIT
    assert events[-1].state is StepState.DONE
    # 事件已持久化到 harness.storage（llm_token 只广播不落库，不在其中）
    stored = await harness.storage.get_events("c1")
    assert len(stored) == len([e for e in events if e.event_type != "llm_token"])


async def test_run_loop_explicit_args_win_over_harness(data_dir):
    """显式参数优先于 harness 解包。"""
    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=data_dir,
        thinking_fn=_thinking_no_tools, acting_fn=_acting_return_ok,
    )
    # 显式 store 用独立 db 文件，避免与 harness.storage 命名冲突
    explicit_store = create_state_store(agent_id="a1", conv_id="c1", db_path=os.path.join(data_dir, "explicit.db"))
    events = []
    async for e in run_loop(agent_id="a1", conv_id="c1",
                            input_={"prompt": "hi", "session_id": "s1"},
                            state_store=explicit_store, thinking_fn=_thinking_no_tools,
                            acting_fn=_acting_return_ok, harness=harness, max_steps=5):
        events.append(e)
    # 显式 store 收到事件，harness.storage 不收（解包未覆盖显式参数）
    assert await explicit_store.get_events("c1")
    assert await harness.storage.get_events("c1") == []


async def test_run_step_with_harness(data_dir):
    """run_step / resume_step 支持 harness。"""
    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=data_dir,
        thinking_fn=_thinking_no_tools, acting_fn=_acting_return_ok,
    )
    events = []
    async for e in run_step(agent_id="a1", conv_id="c1",
                            input_={"prompt": "hi"}, harness=harness):
        events.append(e)
    assert events[-1].state is StepState.DONE
    # resume_step 无 step_id 等价 run_step
    events2 = []
    async for e in resume_step(agent_id="a1", conv_id="c1",
                               input_={"prompt": "hi"}, harness=harness):
        events2.append(e)
    assert events2[-1].state is StepState.DONE


async def test_missing_harness_deps_raise():
    """无 harness 且缺 state_store/thinking_fn → 明确报错。"""
    with pytest.raises(ValueError):
        async for _ in run_loop(agent_id="a1", conv_id="c1", input_={"prompt": "hi"}):
            pass


def test_job_registry():
    """JobRegistry 注册/状态/查询/终态聚合。"""
    jobs = JobRegistry()
    jobs.register("t1", conv_id="c1", kind="media")
    jobs.register("t2", conv_id="c1", kind="subagent")
    assert jobs.get_status("t1")["status"] == "pending"
    jobs.update_status("t1", "completed")
    assert len(jobs.wait_all("c1")) == 1
    assert len(jobs.list_for_conv("c1")) == 2


def test_subagent_runtime_implements_seam():
    """SubAgentRuntime 实现 SubagentSeam（可替换 provider 契约）。"""
    assert issubclass(SubAgentRuntime, _SeamABC)
    # seam 接口方法齐全
    for m in ("spawn", "wait", "get_status", "cancel", "resume"):
        assert hasattr(SubAgentRuntime, m)


def test_seam_exported_via_package():
    """seam 接口可从 v2 包导出。"""
    from gyra.agent.core.v2 import SubagentSeam as Exported
    assert Exported is _SeamABC


def test_harness_alias_properties(data_dir):
    """harness 旧命名兼容属性。"""
    harness = HarnessContext.build(agent_id="a1", conv_id="c1", data_dir=data_dir)
    assert harness.state_store is harness.storage
    assert harness.event_stream is harness.events
