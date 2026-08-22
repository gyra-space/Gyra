"""高频渲染事件不落库测试（EventStream volatile 模式）。

验证：
  - StateStore.append_events 批量落库正确（Db / SqlAlchemy 两个后端）；
  - EventStream 默认（batch=None）对 llm_token 只广播不落库；
  - batch=False 显式关闭后所有事件立即落库；
  - 强持久化事件（step_done 等）不受影响，始终落库。
"""
import os
import tempfile

import pytest

from gyra.agent.core.v2 import EventBatchConfig, EventStream
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DbStateStore(path)
    os.unlink(path)


def _mk_event(seq, event_type, state, output=None):
    return StepEvent(
        event_id=f"evt-{seq}",
        step_id="s1",
        conv_id="c1",
        agent_id="a1",
        parent_step_id=None,
        state=state,
        event_type=event_type,
        input={},
        output=output or {},
        seq=seq,
        timestamp=seq,
    )


# ---------------------------------------------------------------------------
# StateStore.append_events（两个后端）
# ---------------------------------------------------------------------------


async def test_db_state_store_append_events(store):
    """DbStateStore 批量落库，读回与逐条一致。"""
    events = [
        _mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}),
        _mk_event(2, "llm_token", StepState.THINKING, {"token": "b"}),
        _mk_event(3, "llm_token", StepState.THINKING, {"token": "c"}),
    ]
    await store.append_events(events)
    got = await store.get_events("c1")
    assert [e.seq for e in got] == [1, 2, 3]
    assert got[0].output["token"] == "a"


async def test_db_state_store_append_events_empty(store):
    """空列表批量落库为无操作。"""
    await store.append_events([])
    assert await store.get_events("c1") == []


async def test_unified_state_store_append_events(tmp_path):
    """SqlAlchemyStateStore 批量落库与逐条一致。"""
    from gyra.agent.core.v2 import SqlAlchemyStateStore
    from gyra.storage.metadata.db_manager import DatabaseManager

    mgr = DatabaseManager()
    mgr.init_db(f"sqlite:///{tmp_path / 'sys.db'}")
    store = SqlAlchemyStateStore(mgr)
    await store.append_events(
        [_mk_event(1, "llm_token", StepState.THINKING, {"token": "x"})]
    )
    assert len(await store.get_events("c1")) == 1


# ---------------------------------------------------------------------------
# EventStream 高频渲染事件不落库
# ---------------------------------------------------------------------------


async def test_llm_token_broadcast_only(store):
    """默认开启：llm_token 只广播订阅者，不落库。"""
    stream = EventStream(store, batch=EventBatchConfig())
    notified = []

    async def spy(event):
        notified.append(event.event_type)

    stream.subscribe(spy, mode="emit")

    await stream.emit(_mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}))
    assert [e.event_type for e in await store.get_events("c1")] == []
    assert notified == ["llm_token"]


async def test_strong_events_still_persist(store):
    """强持久化事件（step_done）不受不落库配置影响。"""
    stream = EventStream(store, batch=EventBatchConfig())
    await stream.emit(_mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}))
    await stream.emit(_mk_event(2, "step_done", StepState.DONE))
    seqs = [e.seq for e in await store.get_events("c1")]
    assert seqs == [2]  # 只有 step_done 落库；seq 空洞不影响相对顺序


async def test_batch_off_by_default(store):
    """显式 batch=False 关闭不落库：llm_token 也立即落库。"""
    stream = EventStream(store, batch=False)
    await stream.emit(_mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}))
    assert len(await store.get_events("c1")) == 1


async def test_batch_on_by_default(store):
    """默认（batch=None）开启不落库：llm_token 只广播不落库。"""
    stream = EventStream(store)  # default: 开启
    notified = []

    async def spy(event):
        notified.append(event.event_type)

    stream.subscribe(spy, mode="emit")
    await stream.emit(_mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}))
    assert [e.event_type for e in await store.get_events("c1")] == []
    assert notified == ["llm_token"]


async def test_batch_custom_event_types(store):
    """自定义不落库的事件类型。"""
    stream = EventStream(
        store,
        batch=EventBatchConfig(batch_event_types=frozenset({"tool_result"})),
    )
    await stream.emit(_mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}))
    # llm_token 不在自定义集合中 → 立即落库
    assert len(await store.get_events("c1")) == 1
    await stream.emit(_mk_event(2, "tool_result", StepState.OBSERVING, {"ok": 1}))
    assert len(await store.get_events("c1")) == 1  # tool_result 不落库
