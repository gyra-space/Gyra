"""Spill seam 测试：落盘 / 取回 / locator / 超大消息折叠。"""
import os
import tempfile
import pytest

from gyra.agent.core.v2.spill import (
    FileSpillStore,
    SpillManager,
    SpillPolicy,
)


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_file_spill_store_put_get(tmp_data_dir):
    """落盘 + 取回。"""
    store = FileSpillStore(tmp_data_dir)
    sid = store.put("hello world", hint="test")
    assert sid.startswith("spill://")
    assert store.exists(sid)
    content = store.get(sid)
    assert content == b"hello world"


def test_file_spill_store_delete(tmp_data_dir):
    sid = FileSpillStore(tmp_data_dir).put("test", hint="t")
    assert FileSpillStore(tmp_data_dir).exists(sid)
    FileSpillStore(tmp_data_dir).delete(sid)
    assert not FileSpillStore(tmp_data_dir).exists(sid)


def test_file_spill_size_bytes(tmp_data_dir):
    store = FileSpillStore(tmp_data_dir)
    sid = store.put("a" * 1000)
    assert store.size_bytes(sid) == 1000


def test_file_spill_idempotent(tmp_data_dir):
    """相同内容不重复落盘。"""
    store = FileSpillStore(tmp_data_dir)
    sid1 = store.put("same")
    sid2 = store.put("same")
    # sha256 相同但时间戳不同 → 不同 id
    assert sid1 != sid2
    assert store.exists(sid1) and store.exists(sid2)


def test_spill_manager_maybe_spill_string(tmp_data_dir):
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=100),
    )
    # 短内容：inline
    assert sm.maybe_spill_string("hi") == "hi"
    # 长内容：spill
    long_text = "x" * 200
    locator = sm.maybe_spill_string(long_text)
    assert locator.startswith("spill://")
    assert sm.resolve_locator(locator) == long_text.encode("utf-8")


def test_compact_tool_results_inline_short(tmp_data_dir):
    """短 tool 消息：inline 通过。"""
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=100, max_summary_chars=50),
    )
    msgs = [{"role": "tool", "tool_call_id": "c1", "content": "short"}]
    out = sm.compact_tool_results(msgs)
    assert out[0]["content"] == "short"
    assert "_spill_locator" not in out[0]


def test_compact_tool_results_spill_large(tmp_data_dir):
    """超大 tool 消息：spill + 注入 locator + 摘要。"""
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=100, max_summary_chars=50),
    )
    big = "x" * 500
    msgs = [{"role": "tool", "tool_call_id": "c1", "content": big}]
    out = sm.compact_tool_results(msgs)
    assert "_spill_locator" in out[0]
    assert "spill://" in out[0]["content"]
    assert "500" in out[0]["content"]  # size_bytes
    # 取回
    full = sm.resolve_locator(out[0]["_spill_locator"])
    assert full == big.encode("utf-8")


def test_compact_tool_results_skip_system(tmp_data_dir):
    """system 消息跳过 spill。"""
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=100),
    )
    msgs = [{"role": "system", "content": "x" * 500}]
    out = sm.compact_tool_results(msgs)
    assert "_spill_locator" not in out[0]
    assert out[0]["content"] == "x" * 500


def test_compact_event_output_spill(tmp_data_dir):
    """StepEvent.output 的 tool content spill。"""
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=100),
    )
    big = "y" * 500
    event_output = {"content": big, "is_exe_success": True}
    new_out = sm.compact_event_output(event_output)
    assert "_spill_locator" in new_out
    assert "spill://" in new_out["content"]


def test_compact_event_output_no_spill(tmp_data_dir):
    """短 content 不 spill。"""
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=100),
    )
    new_out = sm.compact_event_output({"content": "short", "is_exe_success": True})
    assert new_out == {"content": "short", "is_exe_success": True}


def test_compact_tool_results_hard_truncate(tmp_data_dir):
    """中等长度（不 spill 但超 max_summary_chars）→ 截断 + 标记。"""
    sm = SpillManager(
        FileSpillStore(tmp_data_dir),
        SpillPolicy(max_inline_chars=200, max_summary_chars=50),
    )
    medium = "z" * 100
    msgs = [{"role": "tool", "tool_call_id": "c1", "content": medium}]
    out = sm.compact_tool_results(msgs)
    # 100 < 200 max_inline → 不 spill，但 < 50 max_summary → 截断到 50 + "..." 后缀
    assert len(out[0]["content"]) == 50 + len("...[truncated]")
    assert out[0]["content"].endswith("...[truncated]")
