"""TokenMeter 测试：snapshot、pressure 等级判定、增量。"""
import os
import tempfile
import pytest

from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.token_meter import (
    PressureLevel,
    TokenMeter,
    TokenMeterConfig,
)


@pytest.fixture
def tmp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    s = DbStateStore(path)
    yield s
    if os.path.exists(path):
        os.unlink(path)


def _usage_event(seq: int, prompt: int, completion: int) -> StepEvent:
    total = prompt + completion
    return StepEvent(
        event_id=f"u-{seq}",
        step_id=f"s-{seq}",
        conv_id="c1",
        agent_id="a1",
        state=StepState.THINKING,
        event_type="usage_metric",
        output={
            "this_call": {
                "prompt": prompt,
                "completion": completion,
                "total": total,
            }
        },
        seq=seq,
        timestamp=0.0,
    )


@pytest.mark.asyncio
async def test_snapshot_empty(tmp_store):
    """无 usage 事件 → 全部 0，level=OK。"""
    meter = TokenMeter(tmp_store, "c1", model="gpt-4")
    snap = await meter.snapshot()
    assert snap.prompt == 0
    assert snap.completion == 0
    assert snap.total == 0
    assert snap.pressure_level is PressureLevel.OK


@pytest.mark.asyncio
async def test_snapshot_aggregates(tmp_store):
    """聚合多个 usage 事件。"""
    await tmp_store.append_event(_usage_event(1, 100, 50))
    await tmp_store.append_event(_usage_event(2, 200, 80))
    meter = TokenMeter(tmp_store, "c1", model="gpt-4")
    snap = await meter.snapshot()
    assert snap.prompt == 300
    assert snap.completion == 130
    assert snap.total == 430


@pytest.mark.asyncio
async def test_pressure_levels(tmp_store):
    """不同累计 ratio 触发不同 pressure_level（usage 事件累加，ratio 跨越 OK/WARN/HIGH/CRITICAL 阈值）。"""
    meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=1000, warn_ratio=0.7, compact_ratio=0.85, evict_ratio=0.95),
    )
    # 累计 total = 200，ratio 0.2 → OK
    await tmp_store.append_event(_usage_event(1, 100, 100))
    snap = await meter.snapshot()
    assert snap.pressure_level is PressureLevel.OK
    # 累计 total = 800，ratio 0.8 → WARN（>= 0.7）
    await tmp_store.append_event(_usage_event(2, 400, 200))
    snap = await meter.snapshot()
    assert snap.pressure_level is PressureLevel.WARN
    # 累计 total = 900，ratio 0.9 → HIGH（>= 0.85）
    await tmp_store.append_event(_usage_event(3, 80, 20))
    snap = await meter.snapshot()
    assert snap.pressure_level is PressureLevel.HIGH
    # 累计 total = 1000，ratio 1.0 → CRITICAL（>= 0.95）
    await tmp_store.append_event(_usage_event(4, 50, 50))
    snap = await meter.snapshot()
    assert snap.pressure_level is PressureLevel.CRITICAL
    # 继续追加仍维持 CRITICAL
    await tmp_store.append_event(_usage_event(5, 200, 0))
    snap = await meter.snapshot()
    assert snap.pressure_level is PressureLevel.CRITICAL


@pytest.mark.asyncio
async def test_should_compact(tmp_store):
    """should_compact 在 HIGH/CRITICAL 触发。"""
    meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=100, compact_ratio=0.5, evict_ratio=0.9),
    )
    assert not await meter.should_compact()
    await tmp_store.append_event(_usage_event(1, 60, 0))
    assert await meter.should_compact()
    await tmp_store.append_event(_usage_event(2, 50, 0))
    assert await meter.should_compact()


@pytest.mark.asyncio
async def test_estimate_text_tokens(tmp_store):
    """粗估（chars/4）≥ 1。"""
    meter = TokenMeter(tmp_store, "c1", model=None)
    assert await meter.estimate_text_tokens("") == 0
    assert await meter.estimate_text_tokens("hi") == 1
    assert await meter.estimate_text_tokens("a" * 100) == 25


@pytest.mark.asyncio
async def test_snapshot_current_empty(tmp_store):
    """无 usage 事件 → 当前占用快照返回 None。"""
    meter = TokenMeter(tmp_store, "c1", model="gpt-4")
    assert await meter.snapshot_current() is None


@pytest.mark.asyncio
async def test_snapshot_current_uses_latest_call(tmp_store):
    """当前占用取最近一次 LLM 调用的 prompt（非累计，压缩后可回落）。"""
    await tmp_store.append_event(_usage_event(1, 3000, 200))
    await tmp_store.append_event(_usage_event(2, 2500, 100))
    meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=10000),
    )
    snap = await meter.snapshot_current()
    assert snap is not None
    # 累计 snapshot 仍是 5500+300，但当前占用只看最近一次调用（口径不含输出）
    assert snap.prompt == 2500
    assert snap.total == 2500
    assert snap.completion == 100
    assert snap.ratio == 0.25


@pytest.mark.asyncio
async def test_snapshot_current_reflects_compaction(tmp_store):
    """压缩后下一轮 prompt 变小，当前占用应随之回落（累计值则不会）。"""
    # 压缩前：历史很长，prompt 很大
    await tmp_store.append_event(_usage_event(1, 4000, 200))
    # 压缩后：历史被折叠成摘要，下一轮 prompt 明显变小
    await tmp_store.append_event(_usage_event(2, 800, 80))
    meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(context_window=10000),
    )
    snap = await meter.snapshot_current()
    assert snap is not None
    # 当前占用反映压缩后（变小），而非累计 4800
    assert snap.total == 800
    assert snap.ratio == 0.08
    # 对照：累计 snapshot 仍持续增长，无法体现压缩
    cum = await meter.snapshot()
    assert cum.total == 4000 + 800 + 200 + 80
