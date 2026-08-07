"""Segmenter 测试。"""

from gyra.agent.expand.react_master_agent.context_engine.assembler import (
    TimelineAssembler,
)
from gyra.agent.expand.react_master_agent.context_engine.segmenter import Segmenter

from .conftest import FakeMsg


def test_segment_by_conv_id():
    msgs = [
        FakeMsg("c1", "human", "m1", content="q1", rounds=1, created_at=1.0),
        FakeMsg("c1", "ai", "m2", content="a1", rounds=1, created_at=2.0),
        FakeMsg("c2", "human", "m3", content="q2", rounds=2, created_at=3.0),
    ]
    tl = TimelineAssembler().assemble(msgs, {"c1": [], "c2": []}, "c2", "s")
    segs = Segmenter().segment(tl)
    assert [s.conv_id for s in segs] == ["c1", "c2"]
    assert len(segs[0].units) == 2
    assert len(segs[1].units) == 1


def test_segments_sorted_chronologically_no_current_forcing():
    # current 是较老的 c1，但时序最新的 c2 应排末尾（不再强制 current 到末尾）
    msgs = [
        FakeMsg("c1", "human", "m1", content="q1", rounds=1, created_at=1.0),
        FakeMsg("c2", "human", "m2", content="q2", rounds=2, created_at=2.0),
    ]
    tl = TimelineAssembler().assemble(msgs, {"c1": [], "c2": []}, "c1", "s")
    segs = Segmenter().segment(tl)
    assert [s.conv_id for s in segs] == ["c1", "c2"]
    assert segs[-1].conv_id == "c2"  # 时序最新者末尾，而非 current(c1)


def test_flatten_roundtrip():
    msgs = [
        FakeMsg("c1", "human", "m1", content="q1", rounds=1, created_at=1.0),
        FakeMsg("c2", "human", "m2", content="q2", rounds=2, created_at=2.0),
    ]
    tl = TimelineAssembler().assemble(msgs, {"c1": [], "c2": []}, "c2", "s")
    segs = Segmenter().segment(tl)
    flat = Segmenter.flatten(segs)
    assert len(flat) == 2
