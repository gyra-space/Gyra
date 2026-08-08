"""CompressionService 单测（两段式压缩核心，无真实 LLM）。"""

import pytest

from gyra.agent.expand.react_master_agent.context_engine.compression import (
    CompressionConfig,
    CompressionSegment,
    CompressionService,
)
from gyra.agent.expand.react_master_agent.context_engine.engine import (
    InMemoryCompressionPersistence,
)
from gyra.agent.expand.react_master_agent.context_engine.timeline import (
    ResultStatus,
    TimelineUnit,
    ToolCallBinding,
    UnitKind,
)


def _user(seq, tokens=100, rounds=1, mid=None):
    return TimelineUnit(
        kind=UnitKind.USER, conv_id="c1", message_id=mid or f"u{seq}",
        rounds=rounds, created_at=float(seq), seq=seq,
        user_content=f"user{seq}", tokens=tokens,
    )


def _call(seq, tool="fa", result="r", tokens=100, rounds=1, mid=None, status=ResultStatus.OK):
    b = ToolCallBinding(
        tool_call_id=f"tc{seq}", tool_name=tool, args={},
        result_status=status, result_text=result, tokens=tokens,
    )
    return TimelineUnit(
        kind=UnitKind.CALL, conv_id="c1", message_id=mid or f"m{seq}",
        rounds=rounds, created_at=float(seq), seq=seq, ai_text="", calls=[b], tokens=tokens,
    )


def _svc(summarize=None, cfg=None, persistence=None):
    return CompressionService(
        summarize_fn=summarize,
        persistence=persistence or InMemoryCompressionPersistence(),
        config=cfg or CompressionConfig(),
    )


# ---------------------------------------------------------------------- #
# should_compress
# ---------------------------------------------------------------------- #
def test_should_compress_threshold():
    cfg = CompressionConfig(threshold_ratio=0.9, min_interval_turns=0)
    svc = _svc(cfg=cfg)
    assert not svc.should_compress(800, 1000, 0)  # 0.8 < 0.9
    assert svc.should_compress(920, 1000, 0)  # 0.92 >= 0.9


def test_should_compress_anti_thrash():
    cfg = CompressionConfig(threshold_ratio=0.5, min_interval_turns=3)
    svc = _svc(cfg=cfg)
    # 首次：未压缩过 -> 允许
    assert svc.should_compress(800, 1000, 3)
    # 模拟刚压缩完（turns_since=1 < 3）-> 拒绝
    assert not svc.should_compress(800, 1000, 1)


# ---------------------------------------------------------------------- #
# determine_boundary
# ---------------------------------------------------------------------- #
def test_determine_boundary_splits():
    svc = _svc()
    units = [_user(i) for i in range(10)]  # 10 × 100 tokens
    compress, retain = svc.determine_boundary(units, retain_tokens=400)
    # 保留区从最新往回 4 个（400 tokens），压缩区 6 个
    assert len(retain) == 4
    assert len(compress) == 6
    # 保留区是最新 4 个
    assert [u.seq for u in retain] == [6, 7, 8, 9]
    # 压缩区是较旧 6 个
    assert [u.seq for u in compress] == [0, 1, 2, 3, 4, 5]


def test_determine_boundary_keeps_at_least_one():
    svc = _svc()
    units = [_user(i) for i in range(3)]
    # 极小保留预算 -> 至少保留最新 1 个
    compress, retain = svc.determine_boundary(units, retain_tokens=10)
    assert len(retain) >= 1
    assert retain[-1].seq == 2


def test_determine_boundary_empty_compress_when_all_retained():
    svc = _svc()
    units = [_user(i) for i in range(3)]
    # 保留预算足够大 -> 全保留，压缩区空
    compress, retain = svc.determine_boundary(units, retain_tokens=100000)
    assert compress == []
    assert len(retain) == 3


# ---------------------------------------------------------------------- #
# compress
# ---------------------------------------------------------------------- #
class _Summ:
    def __init__(self, text="SUMMARY"):
        self.text = text
        self.calls = 0
        self.prompts = []

    async def __call__(self, prompt, max_tokens):
        self.calls += 1
        self.prompts.append(prompt)
        return self.text


@pytest.mark.asyncio
async def test_compress_first_time_no_prev():
    svc = _svc(summarize=_Summ("FIRST"))
    units = [_user(0), _call(1), _user(2)]
    seg = await svc.compress("s", "c1", units, prev_segment=None, seq=1)
    assert seg is not None
    assert seg.seq == 1
    assert seg.degraded is False
    assert "FIRST" in seg.summary
    assert seg.boundary_message_id == "u2"  # 最后一个单元
    assert seg.prev_segment_id is None
    assert len(seg.source_message_ids) == 3


@pytest.mark.asyncio
async def test_compress_incremental_includes_prev_summary():
    summ = _Summ("SECOND")
    svc = _svc(summarize=summ)
    prev = CompressionSegment(
        seq=1, summary="[历史上下文摘要 ...]\nFIRST", boundary_message_id="u2",
        segment_id=10,
    )
    units = [_user(3), _call(4)]
    seg = await svc.compress("s", "c1", units, prev_segment=prev, seq=2)
    assert seg.seq == 2
    assert seg.prev_segment_id == 10
    # 摘要输入含前次摘要
    assert "FIRST" in summ.prompts[0]
    assert "SECOND" in seg.summary


@pytest.mark.asyncio
async def test_compress_degrade_when_no_llm():
    svc = _svc(summarize=None)  # 无 LLM
    units = [_user(0), _call(1)]
    seg = await svc.compress("s", "c1", units, prev_segment=None, seq=1)
    assert seg.degraded is True
    assert seg.summary  # 截断兜底有内容


# ---------------------------------------------------------------------- #
# persist + load
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_persist_and_load_latest():
    pers = InMemoryCompressionPersistence()
    svc = _svc(summarize=_Summ("S"), persistence=pers)
    units = [_user(0), _call(1), _user(2)]
    seg = await svc.compress("s", "c1", units, prev_segment=None, seq=1)
    seg_id = await svc.persist("s", "c1", seg)
    assert seg_id is not None
    assert seg.segment_id == seg_id

    loaded = await svc.load_latest("s")
    assert loaded is not None
    assert loaded.seq == 1
    assert "S" in loaded.summary
    assert loaded.boundary_message_id == "u2"


@pytest.mark.asyncio
async def test_persist_skips_degraded():
    pers = InMemoryCompressionPersistence()
    svc = _svc(summarize=None, persistence=pers)
    seg = await svc.compress("s", "c1", [_user(0)], prev_segment=None, seq=1)
    assert seg.degraded is True
    seg_id = await svc.persist("s", "c1", seg)
    assert seg_id is None  # degraded 不持久化
    assert await svc.load_latest("s") is None


@pytest.mark.asyncio
async def test_load_all_returns_sorted():
    pers = InMemoryCompressionPersistence()
    svc = _svc(summarize=_Summ("S"), persistence=pers)
    for seq, units in [(1, [_user(0)]), (2, [_user(1)]), (3, [_user(2)])]:
        prev = await svc.load_latest("s")
        seg = await svc.compress("s", "c1", units, prev_segment=prev, seq=seq)
        await svc.persist("s", "c1", seg)
    all_segs = await svc.load_all("s")
    assert [s.seq for s in all_segs] == [1, 2, 3]
