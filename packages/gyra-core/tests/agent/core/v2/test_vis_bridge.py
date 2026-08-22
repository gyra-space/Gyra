"""VisBridge 测试——vis 渲染桥（harness 事件总线订阅者）。

验证：引擎只产事件（StepEvent），VisBridge 作为 emit 订阅者消费
llm_token（增量渲染）/ step_done（终态重置），把渲染动作桥到 BAIZE vis。
"""
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.harness import VisBridge
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DbStateStore(path)
    os.unlink(path)


@pytest.fixture
def events(store):
    return EventStream(store)


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


def _make_bridge(agent, events):
    bridge = VisBridge(agent=agent, event_stream=events)
    bridge.attach()
    bridge.begin_turn(reply_message_id="reply-1", received_message=MagicMock())
    return bridge


async def test_llm_token_renders_incrementally(store, events):
    """llm_token 事件 → 增量渲染（listen_thinking_stream），is_first_chunk 只首帧。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    bridge = _make_bridge(agent, events)

    await events.emit(
        _mk_event(1, "llm_token", StepState.THINKING, {"token": "你"})
    )
    await events.emit(
        _mk_event(2, "llm_token", StepState.THINKING, {"token": "好"})
    )

    assert agent.listen_thinking_stream.await_count == 2
    first_kwargs = agent.listen_thinking_stream.await_args_list[0].kwargs
    second_kwargs = agent.listen_thinking_stream.await_args_list[1].kwargs
    # 无 channel 的 token 按 content 通道渲染：首帧 is_first_content=True
    assert first_kwargs["is_first_chunk"] is False
    assert first_kwargs["is_first_content"] is True
    assert second_kwargs["is_first_chunk"] is False
    assert second_kwargs["is_first_content"] is False
    assert first_kwargs["cu_content_incr"] == "你"
    assert second_kwargs["cu_content_incr"] == "好"
    assert first_kwargs["cu_thinking_incr"] is None
    assert bridge._final_text == "你好"
    assert bridge._thinking_text == ""


async def test_llm_token_thinking_content_separated(store, events):
    """thinking/content 分通道渲染：思考走 cu_thinking_incr，正文走 cu_content_incr。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    bridge = _make_bridge(agent, events)

    # 推理阶段（thinking 通道）
    await events.emit(
        _mk_event(1, "llm_token", StepState.THINKING,
                  {"token": "我先想", "channel": "thinking"})
    )
    # 正文阶段（content 通道）
    await events.emit(
        _mk_event(2, "llm_token", StepState.THINKING,
                  {"token": "最终答案", "channel": "content"})
    )

    assert agent.listen_thinking_stream.await_count == 2
    think_kwargs = agent.listen_thinking_stream.await_args_list[0].kwargs
    content_kwargs = agent.listen_thinking_stream.await_args_list[1].kwargs
    # 思考首帧：is_first_chunk=True，走 cu_thinking_incr
    assert think_kwargs["is_first_chunk"] is True
    assert think_kwargs["cu_thinking_incr"] == "我先想"
    assert think_kwargs["cu_content_incr"] is None
    # 正文首帧：is_first_content=True，走 cu_content_incr；思考通道不再 first
    assert content_kwargs["is_first_chunk"] is False
    assert content_kwargs["is_first_content"] is True
    assert content_kwargs["cu_content_incr"] == "最终答案"
    assert content_kwargs["cu_thinking_incr"] is None
    # 累积分离
    assert bridge._thinking_text == "我先想"
    assert bridge._final_text == "最终答案"


async def test_step_done_resets_vis(store, events):
    """step_done 事件 → 终态重置（reset_stream_vis，带累积 thinking）。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    bridge = _make_bridge(agent, events)

    await events.emit(
        _mk_event(1, "llm_token", StepState.THINKING,
                  {"token": "最终", "channel": "thinking"})
    )
    await events.emit(_mk_event(2, "step_done", StepState.DONE))

    agent.reset_stream_vis.assert_awaited_once_with("reply-1", thinking="最终")


async def test_reset_uses_thinking_only(store, events):
    """reset 只回填累积 thinking，正文（content）不回填进思考块避免重复。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    bridge = _make_bridge(agent, events)

    await events.emit(
        _mk_event(1, "llm_token", StepState.THINKING,
                  {"token": "推理", "channel": "thinking"})
    )
    await events.emit(
        _mk_event(2, "llm_token", StepState.THINKING,
                  {"token": "正文", "channel": "content"})
    )
    await events.emit(_mk_event(3, "step_done", StepState.DONE))

    # 思考块只含 thinking 文本，不含正文
    agent.reset_stream_vis.assert_awaited_once_with("reply-1", thinking="推理")


async def test_non_vis_events_ignored(store, events):
    """非订阅事件（tool_call/tool_result/step_status）不触发渲染。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    _make_bridge(agent, events)

    await events.emit(
        _mk_event(1, "tool_call", StepState.ACTING,
                  {"tool": "bash", "input": {"cmd": "ls"}})
    )
    await events.emit(
        _mk_event(2, "tool_result", StepState.OBSERVING,
                  {"tool_name": "bash", "content": "ok", "is_exe_success": True})
    )

    agent.listen_thinking_stream.assert_not_called()
    agent.reset_stream_vis.assert_not_called()


async def test_tool_call_splits_narration_segments(store, events):
    """tool_call 边界把旁白切成独立 message_id 段，支持与工具步骤时序交错。

    修复：V2 整轮旁白原先全累积在一个 message_id 下，scene workspace 转换器
    把它们聚合为一个 trailing answer 块，与工具步骤渲染割裂。现在每次工具调用
    前 finalize 当前段并推进到新 message_id，使旁白能按各自时间戳就近交错。
    """
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    bridge = _make_bridge(agent, events)

    # 段0：讲述旁白 → 随后工具调用
    await events.emit(
        _mk_event(1, "llm_token", StepState.THINKING,
                  {"token": "让我先查看目录", "channel": "content"})
    )
    await events.emit(
        _mk_event(2, "tool_call", StepState.ACTING,
                  {"tool": "Bash", "input": {"cmd": "ls"}})
    )
    # 段0 终结：reset 当前段 + 切到新 message_id
    agent.reset_stream_vis.assert_awaited_with(
        "reply-1", thinking=None
    )
    assert bridge._reply_message_id == "reply-1-seg1"
    assert bridge._final_text == ""
    assert bridge._thinking_text == ""
    assert bridge._seg_index == 1
    # 段1：新 message_id 继续流式
    await events.emit(
        _mk_event(3, "llm_token", StepState.THINKING,
                  {"token": "继续分析", "channel": "content"})
    )
    assert agent.listen_thinking_stream.await_count == 2
    last_kwargs = agent.listen_thinking_stream.await_args_list[1].kwargs
    assert last_kwargs["reply_message_id"] == "reply-1-seg1"
    assert last_kwargs["is_first_content"] is True
    assert bridge._final_text == "继续分析"


async def test_tool_call_without_narration_does_not_reset(store, events):
    """无前置旁白直接调工具：不清空段落，仅推进编号（不触发 reset=无副作用）。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    bridge = _make_bridge(agent, events)

    await events.emit(
        _mk_event(1, "tool_call", StepState.ACTING,
                  {"tool": "Bash", "input": {"cmd": "ls"}})
    )
    agent.reset_stream_vis.assert_not_called()
    assert bridge._reply_message_id == "reply-1-seg1"
    assert bridge._seg_index == 1
    assert bridge._final_text == ""


async def test_detach_stops_rendering(store, events):
    """detach 后事件不再触发渲染。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    bridge = _make_bridge(agent, events)

    bridge.detach()
    await events.emit(
        _mk_event(1, "llm_token", StepState.THINKING, {"token": "x"})
    )
    await events.emit(_mk_event(2, "step_done", StepState.DONE))

    agent.listen_thinking_stream.assert_not_called()
    agent.reset_stream_vis.assert_not_called()


async def test_begin_turn_resets_state(store, events):
    """begin_turn 重置渲染增量状态（多轮 turn 隔离）。"""
    agent = MagicMock()
    agent.listen_thinking_stream = AsyncMock()
    agent.reset_stream_vis = AsyncMock()
    bridge = _make_bridge(agent, events)

    await events.emit(_mk_event(1, "llm_token", StepState.THINKING, {"token": "a"}))
    # 新一轮 turn
    bridge.begin_turn(reply_message_id="reply-2")
    await events.emit(_mk_event(2, "llm_token", StepState.THINKING, {"token": "b"}))

    assert agent.listen_thinking_stream.await_count == 2
    last_kwargs = agent.listen_thinking_stream.await_args_list[1].kwargs
    # 新一轮 content 首帧 is_first_content=True
    assert last_kwargs["is_first_content"] is True
    assert bridge._final_text == "b"
    assert bridge._thinking_text == ""
