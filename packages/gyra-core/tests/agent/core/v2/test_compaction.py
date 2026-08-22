"""Compaction 端到端测试：触发 / 摘要 / replace shadow / 事件持久化。"""
import os
import tempfile
import asyncio
import pytest

from gyra.agent.core.v2.compaction import (
    Compactor,
    CompactionPolicy,
    HeuristicSummarizer,
)
from gyra.agent.core.v2.event_stream import EventBatchConfig, EventStream
from gyra.agent.core.v2.event_registry import get_event_registry
from gyra.agent.core.v2.projector_registry import get_projector_registry
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.token_meter import TokenMeter, TokenMeterConfig


@pytest.fixture
def tmp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    s = DbStateStore(path)
    yield s
    if os.path.exists(path):
        os.unlink(path)


def _usage(seq: int, prompt: int, completion: int, conv_id="c1") -> StepEvent:
    return StepEvent(
        event_id=f"u-{seq}",
        step_id=f"s-{seq}",
        conv_id=conv_id,
        agent_id="a1",
        state=StepState.THINKING,
        event_type="usage_metric",
        output={"this_call": {"prompt": prompt, "completion": completion, "total": prompt + completion}},
        seq=seq,
        timestamp=float(seq),
    )


def _user_message(seq: int, text: str, conv_id="c1") -> StepEvent:
    return StepEvent(
        event_id=f"u{seq}",
        step_id=f"s-{seq}",
        conv_id=conv_id,
        agent_id="a1",
        state=StepState.THINKING,
        event_type="user/message",
        output={"text": text},
        seq=seq,
        timestamp=float(seq),
    )


def _step_done(seq: int, step_id: str, conv_id="c1") -> StepEvent:
    return StepEvent(
        event_id=f"d{seq}",
        step_id=step_id,
        conv_id=conv_id,
        agent_id="a1",
        state=StepState.DONE,
        event_type="step_done",
        seq=seq,
        timestamp=float(seq),
    )


def _make_emit_fn(store):
    seq = [0]
    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        seq[0] += 1
        ev = StepEvent(
            event_id=f"e-{seq[0]}",
            step_id="s-current", conv_id="c1", agent_id="a1",
            state=state, event_type=et, input=input_data or {}, output=output_data or {},
            seq=seq[0] + 1000, timestamp=float(seq[0]),
        )
        await store.append_event(ev)
        return ev
    return emit


@pytest.mark.asyncio
async def test_should_trigger_by_pressure(tmp_store):
    """压力达到 compact_ratio → 触发。"""
    for i in range(5):
        await tmp_store.append_event(_usage(i, 100, 0))
    token_meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=500, compact_ratio=0.85, warn_ratio=0.7),
    )
    compactor = Compactor(
        store=tmp_store, emit=None, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(force_compact_every_n_turns=0),
        token_meter=token_meter,
    )
    triggered, reason, _ = await compactor.should_trigger()
    assert triggered is True
    assert "pressure" in reason


@pytest.mark.asyncio
async def test_should_trigger_by_force(tmp_store):
    """force_compact_every_n_turns 强制触发。"""
    await tmp_store.append_event(_step_done(1, "s-1"))
    await tmp_store.append_event(_step_done(2, "s-2"))
    await tmp_store.append_event(_step_done(3, "s-3"))
    token_meter = TokenMeter(tmp_store, "c1", model=None)
    compactor = Compactor(
        store=tmp_store, emit=None, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(force_compact_every_n_turns=3),
        token_meter=token_meter,
    )
    triggered, reason, _ = await compactor.should_trigger()
    assert triggered is True
    assert "force" in reason


@pytest.mark.asyncio
async def test_no_trigger_when_no_pressure(tmp_store):
    token_meter = TokenMeter(tmp_store, "c1", model=None)
    compactor = Compactor(
        store=tmp_store, emit=None, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(force_compact_every_n_turns=0),
        token_meter=token_meter,
    )
    triggered, reason, _ = await compactor.should_trigger()
    assert triggered is False
    assert reason == "no_trigger"


@pytest.mark.asyncio
async def test_compaction_writes_summary_event(tmp_store):
    """compaction 触发后写入 compaction/start, summary, end 事件。"""
    emit = _make_emit_fn(tmp_store)

    await tmp_store.append_event(_user_message(1, "第一段用户问题"))
    await tmp_store.append_event(_user_message(2, "第二段用户问题"))
    await tmp_store.append_event(_step_done(3, "s-old"))
    for i in range(5, 10):
        await tmp_store.append_event(_usage(i, 100, 0))

    token_meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=500, compact_ratio=0.85),
    )
    compactor = Compactor(
        store=tmp_store, emit=emit, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(min_keep_recent_turns=1, summary_max_tokens=200),
        token_meter=token_meter,
    )
    result = await compactor.maybe_run()
    assert result.triggered is True
    assert result.compacted_event_count > 0
    assert result.summary

    events = await tmp_store.get_events("c1")
    types = [e.event_type for e in events]
    assert "compaction/start" in types
    assert "compaction/summary" in types
    assert "compaction/end" in types


@pytest.mark.asyncio
async def test_compaction_summary_projects_to_system_message(tmp_store):
    """compaction/summary 事件投影为 system 消息。"""
    emit = _make_emit_fn(tmp_store)

    await tmp_store.append_event(_user_message(1, "old question"))
    await tmp_store.append_event(_step_done(2, "s-old"))
    for i in range(3, 8):
        await tmp_store.append_event(_usage(i, 100, 0))

    token_meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=500, compact_ratio=0.85),
    )
    compactor = Compactor(
        store=tmp_store, emit=emit, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(min_keep_recent_turns=0),
        token_meter=token_meter,
    )
    await compactor.maybe_run()

    events = await tmp_store.get_events("c1")
    proj = get_projector_registry()
    msgs = proj.project_events(events)
    summary_msgs = [m for m in msgs if m.get("role") == "system" and "Compaction" in m.get("content", "")]
    assert len(summary_msgs) >= 1


@pytest.mark.asyncio
async def test_compaction_idempotent_no_double_compress(tmp_store):
    """已有 compaction/summary 的事件不会被再压缩（不会被计入 compactable 范围）。"""
    emit = _make_emit_fn(tmp_store)

    await tmp_store.append_event(_user_message(1, "old"))
    summary_ev = StepEvent(
        event_id="s0",
        step_id="s-0",
        conv_id="c1",
        agent_id="a1",
        state=StepState.OBSERVING,
        event_type="compaction/summary",
        output={"summary": "先前的摘要"},
        seq=2,
        timestamp=2.0,
    )
    await tmp_store.append_event(summary_ev)
    for i in range(3, 8):
        await tmp_store.append_event(_usage(i, 100, 0))

    token_meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=500, compact_ratio=0.85),
    )
    compactor = Compactor(
        store=tmp_store, emit=emit, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(min_keep_recent_turns=0),
        token_meter=token_meter,
    )
    await compactor.maybe_run()
    events = await tmp_store.get_events("c1")
    summary_count = sum(1 for e in events if e.event_type == "compaction/summary")
    # 旧 1 + 新 1（user 触发压缩但 summary 不再被压缩）
    assert summary_count == 2
