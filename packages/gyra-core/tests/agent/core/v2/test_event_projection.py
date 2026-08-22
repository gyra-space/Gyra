"""事件日志投影测试——事实源统一（model-visible = logged）。"""
import os
import tempfile

import pytest

from gyra.agent.core.v2.event_projection import (
    ToolHistoryProjector,
    project_tool_history,
)
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DbStateStore(path)
    os.unlink(path)


def _mk_event(seq, state, event_type, input_=None, output=None, step_id="s1"):
    return StepEvent(
        event_id=f"evt-{seq}",
        step_id=step_id,
        conv_id="c1",
        agent_id="a1",
        parent_step_id=None,
        state=state,
        event_type=event_type,
        input=input_ or {},
        output=output or {},
        seq=seq,
        timestamp=seq,
    )


async def test_project_empty_log(store):
    """空日志 → 空投影。"""
    assert await project_tool_history(store, "c1") == []


async def test_project_single_tool_pair(store):
    """单工具调用 → assistant(tool_calls) + tool(结果) 消息对。"""
    await store.append_event(_mk_event(1, StepState.INIT, "step_init"))
    await store.append_event(
        _mk_event(2, StepState.ACTING, "tool_call",
                  input_={"tool": "bash", "input": {"cmd": "ls"}})
    )
    await store.append_event(
        _mk_event(3, StepState.OBSERVING, "tool_result",
                  output={"is_exe_success": True, "content": "file.txt", "tool_name": "bash"})
    )
    msgs = await project_tool_history(store, "c1")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "assistant"
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "bash"
    # tool_call_id 确定性派生：assistant 与 tool 消息一致
    call_id = msgs[0]["tool_calls"][0]["id"]
    assert msgs[1]["role"] == "tool"
    assert msgs[1]["tool_call_id"] == call_id
    assert msgs[1]["content"] == "file.txt"


async def test_project_multiple_tools_fifo(store):
    """多工具按 FIFO 配对（与 runtime 顺序执行一致）。"""
    await store.append_event(
        _mk_event(1, StepState.ACTING, "tool_call",
                  input_={"tool": "bash", "input": {"cmd": "a"}})
    )
    await store.append_event(
        _mk_event(2, StepState.ACTING, "tool_call",
                  input_={"tool": "read", "input": {"path": "b"}})
    )
    await store.append_event(
        _mk_event(3, StepState.OBSERVING, "tool_result",
                  output={"is_exe_success": True, "content": "out-a", "tool_name": "bash"})
    )
    await store.append_event(
        _mk_event(4, StepState.OBSERVING, "tool_result",
                  output={"is_exe_success": True, "content": "out-b", "tool_name": "read"})
    )
    msgs = await project_tool_history(store, "c1")
    assert len(msgs) == 4
    # 第一对：bash → out-a；第二对：read → out-b
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "bash"
    assert msgs[1]["content"] == "out-a"
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "read"
    assert msgs[3]["content"] == "out-b"


async def test_project_skips_unfinished(store):
    """未配对 tool_call（当前 step 正在 thinking）默认跳过。"""
    await store.append_event(
        _mk_event(1, StepState.ACTING, "tool_call",
                  input_={"tool": "bash", "input": {"cmd": "ls"}})
    )
    # 无 tool_result → 默认投影为空
    assert await project_tool_history(store, "c1") == []
    # include_unfinished=True → 保留 assistant 声明
    msgs = await project_tool_history(store, "c1", include_unfinished=True)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "assistant"


async def test_project_error_result_content(store):
    """执行失败的结果：content 取 error 文案。"""
    await store.append_event(
        _mk_event(1, StepState.ACTING, "tool_call",
                  input_={"tool": "bash", "input": {"cmd": "x"}})
    )
    await store.append_event(
        _mk_event(2, StepState.OBSERVING, "tool_result",
                  output={"is_exe_success": False, "error": "boom", "tool_name": "bash"})
    )
    msgs = await project_tool_history(store, "c1")
    assert msgs[1]["content"] == "boom"


async def test_projector_cache_and_append(store):
    """ToolHistoryProjector 增量缓存：追加事件后再次 get 返回最新投影。"""
    projector = ToolHistoryProjector(store)
    await store.append_event(
        _mk_event(1, StepState.ACTING, "tool_call",
                  input_={"tool": "bash", "input": {"cmd": "a"}})
    )
    assert await projector.get("c1") == []

    # 追加结果 → 投影出现
    await store.append_event(
        _mk_event(2, StepState.OBSERVING, "tool_result",
                  output={"is_exe_success": True, "content": "ok", "tool_name": "bash"})
    )
    msgs = await projector.get("c1")
    assert len(msgs) == 2
    assert msgs[1]["content"] == "ok"
