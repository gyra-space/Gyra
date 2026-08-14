import pytest
import tempfile
import os
import asyncio
from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = DbStateStore(path)
    yield s
    os.unlink(path)


async def test_emit_persists_and_returns_event(store):
    stream = EventStream(store)
    event = StepEvent(
        event_id="evt-1",
        step_id="step-1",
        conv_id="conv-1",
        agent_id="agent-1",
        parent_step_id=None,
        state=StepState.INIT,
        event_type="step_init",
        input={},
        output={},
        seq=0,
        timestamp=0.0,
    )
    returned = await stream.emit(event)
    assert returned is event
    persisted = await store.get_events("conv-1")
    assert len(persisted) == 1
    assert persisted[0].event_id == "evt-1"


async def test_replay_yields_historical_events_in_order(store):
    stream = EventStream(store)
    for i in range(3):
        await stream.emit(StepEvent(
            event_id=f"evt-{i}",
            step_id="step-1",
            conv_id="conv-1",
            agent_id="agent-1",
            parent_step_id=None,
            state=StepState.THINKING,
            event_type="llm_token",
            input={},
            output={"i": i},
            seq=i,
            timestamp=float(i),
        ))

    # 模拟进程重启后重放
    new_stream = EventStream(store)
    events = []
    async for e in new_stream.replay("conv-1"):
        events.append(e)
    assert [e.seq for e in events] == [0, 1, 2]
    assert [e.output["i"] for e in events] == [0, 1, 2]


async def test_replay_since_seq(store):
    stream = EventStream(store)
    for i in range(5):
        await stream.emit(StepEvent(
            event_id=f"evt-{i}",
            step_id="step-1",
            conv_id="conv-1",
            agent_id="agent-1",
            parent_step_id=None,
            state=StepState.THINKING,
            event_type="llm_token",
            input={},
            output={},
            seq=i,
            timestamp=float(i),
        ))
    new_stream = EventStream(store)
    events = []
    async for e in new_stream.replay("conv-1", since_seq=3):
        events.append(e)
    assert [e.seq for e in events] == [3, 4]


# =============================================================================
# P0 插件化扩展：subscribe
# =============================================================================


def _make_event(event_type: str, seq: int = 0, state: StepState = StepState.THINKING):
    return StepEvent(
        event_id=f"evt-{event_type}-{seq}",
        step_id="step-1",
        conv_id="conv-1",
        agent_id="agent-1",
        parent_step_id=None,
        state=state,
        event_type=event_type,
        input={},
        output={},
        seq=seq,
        timestamp=0.0,
    )


async def test_subscribe_receives_all_events(store):
    stream = EventStream(store)
    seen = []
    stream.subscribe(seen.append)

    await stream.emit(_make_event("step_init", 0, StepState.INIT))
    await stream.emit(_make_event("llm_token", 1))

    assert [e.event_type for e in seen] == ["step_init", "llm_token"]


async def test_subscribe_filters_by_event_types(store):
    stream = EventStream(store)
    seen = []
    stream.subscribe(seen.append, event_types=["tool_call", "tool_result"])

    await stream.emit(_make_event("step_init", 0, StepState.INIT))
    await stream.emit(_make_event("tool_call", 1, StepState.ACTING))
    await stream.emit(_make_event("llm_token", 2))

    assert [e.event_type for e in seen] == ["tool_call"]


async def test_subscribe_supports_async_callback(store):
    stream = EventStream(store)
    seen = []

    async def on_event(e):
        await asyncio.sleep(0)
        seen.append(e.event_type)

    stream.subscribe(on_event)
    await stream.emit(_make_event("step_init", 0, StepState.INIT))
    assert seen == ["step_init"]


async def test_subscriber_notified_after_persistence(store):
    """durability-before-visibility：回调触发时事件已落库。"""
    stream = EventStream(store)
    persisted_at_notify = []

    async def on_event(e):
        persisted = await store.get_events("conv-1")
        persisted_at_notify.append(e.event_id in [p.event_id for p in persisted])

    stream.subscribe(on_event)
    await stream.emit(_make_event("step_init", 0, StepState.INIT))
    assert persisted_at_notify == [True]


async def test_unsubscribe_stops_notification(store):
    stream = EventStream(store)
    seen = []
    unsubscribe = stream.subscribe(seen.append)

    await stream.emit(_make_event("step_init", 0, StepState.INIT))
    unsubscribe()
    await stream.emit(_make_event("llm_token", 1))

    assert [e.event_type for e in seen] == ["step_init"]


async def test_subscriber_error_does_not_break_stream(store):
    """订阅者异常只记日志，主事件流与其他订阅者不受影响。"""
    stream = EventStream(store)
    seen = []

    def bad_callback(e):
        raise RuntimeError("plugin boom")

    stream.subscribe(bad_callback)
    stream.subscribe(seen.append)

    returned = await stream.emit(_make_event("step_init", 0, StepState.INIT))
    assert returned.event_type == "step_init"
    assert seen == [returned]
    # 事件仍已持久化
    persisted = await store.get_events("conv-1")
    assert len(persisted) == 1
