"""高频渲染事件不落库默认开启（llm_token）测试。"""
import os
import tempfile
import pytest

from gyra.agent.core.v2.event_stream import EventBatchConfig, EventStream
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.state_store import DbStateStore


@pytest.fixture
def tmp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    s = DbStateStore(path)
    yield s
    if os.path.exists(path):
        os.unlink(path)


def _make_event(seq: int, event_type: str = "llm_token") -> StepEvent:
    return StepEvent(
        event_id=f"e-{seq}",
        step_id="s-1",
        conv_id="c-1",
        agent_id="a-1",
        state=StepState.THINKING,
        event_type=event_type,
        input={},
        output={"token": f"t{seq}"},
        seq=seq,
        timestamp=0.0,
    )


@pytest.mark.asyncio
async def test_event_batch_default_enabled(tmp_store):
    """None / 缺省 → 默认开启不落库（llm_token 只广播）。"""
    stream = EventStream(tmp_store)  # 缺省 None → 默认开启
    assert stream._batch is not None
    assert "llm_token" in stream._batch.effective_types()


@pytest.mark.asyncio
async def test_event_batch_explicit_false_disabled(tmp_store):
    """显式传 False → 关闭不落库。"""
    stream = EventStream(tmp_store, batch=False)
    assert stream._batch is None


@pytest.mark.asyncio
async def test_llm_tokens_not_persisted_step_done_is(tmp_store):
    """llm_token 不落库；step_done 强事件照常落库。"""
    stream = EventStream(tmp_store, batch=EventBatchConfig())
    for i in range(1, 11):
        await stream.emit(_make_event(i, "llm_token"))
    await stream.emit(_make_event(11, "step_done"))
    events = await tmp_store.get_events("c-1")
    assert len(events) == 1
    assert events[0].event_type == "step_done"


@pytest.mark.asyncio
async def test_non_batched_events_persist_immediately(tmp_store):
    """tool_call / step_done 等强事件不落库配置外，立刻落库。"""
    stream = EventStream(tmp_store, batch=EventBatchConfig())
    await stream.emit(_make_event(1, "tool_call"))
    events = await tmp_store.get_events("c-1")
    assert len(events) == 1
