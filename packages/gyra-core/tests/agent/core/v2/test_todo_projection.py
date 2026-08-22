"""V2 TODO 状态设计测试（对齐 DSH tool-todo）。

覆盖 3 个不变量：
  1. ``todo/write`` 事件 surface=False——不参与 ProjectorRegistry LLM 投影；
  2. ``project_current_todo`` 从事件流 last-write-wins 读出最新 todo 列表；
  3. default_thinking_fn **不**把 todo 注入 LLM 上下文（无 <system-reminder>）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.core.v2.event_registry import (
    EventRegistry,
    get_event_registry,
    reset_event_registry,
)
from gyra.agent.core.v2.projector_registry import (
    ProjectorRegistry,
    get_projector_registry,
    reset_projector_registry,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.todo_projection import project_current_todo


# ---------- EventRegistry / ProjectorRegistry 不变量 ----------

def test_todo_write_event_is_not_surface():
    """``todo/write`` 必须 surface=False——事件不进入 LLM 上下文。"""
    reset_event_registry()
    reg = get_event_registry()
    info = reg.get("todo/write")
    assert info is not None, "todo/write 未在默认事件词表注册"
    assert info.is_surface is False, (
        "todo/write surface=True 会污染 LLM 上下文，破坏 KV-cache"
    )
    assert info.category == "todo"


def test_todo_write_event_not_projected_to_llm():
    """``todo/write`` 事件经过 ProjectorRegistry 后**不**产出 LLM 消息。"""
    reset_event_registry()
    reset_projector_registry()
    proj = get_projector_registry()

    seq = [0]

    async def emit(state, et, **kwargs):
        seq[0] += 1
        return StepEvent(
            event_id=f"e-{seq[0]}",
            step_id="s1", conv_id="c1", agent_id="a1",
            state=state, event_type=et,
            input=kwargs.get("input_data") or {},
            output=kwargs.get("output_data") or {},
            seq=seq[0], timestamp=float(seq[0]),
        )

    # 模拟 V2Agent 写入：1 个 user/assistant 对话 + 1 个 todo/write 事件
    user_ev = StepEvent(
        event_id="e-user", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.THINKING, event_type="user/message",
        input={}, output={"text": "帮我设计 TODO 流程"},
        seq=1, timestamp=1.0,
    )
    todo_ev = StepEvent(
        event_id="e-todo-1", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.OBSERVING, event_type="todo/write",
        input={"tool": "todowrite"},
        output={"todos": [
            {"id": "1", "content": "设计", "status": "pending"},
            {"id": "2", "content": "实现", "status": "pending"},
        ]},
        seq=2, timestamp=2.0,
    )
    asst_ev = StepEvent(
        event_id="e-asst", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.THINKING, event_type="assistant/message",
        input={}, output={"text": "好的，我来实现"},
        seq=3, timestamp=3.0,
    )
    msgs = proj.project_events([user_ev, todo_ev, asst_ev])
    roles = [m.get("role") for m in msgs]
    contents = [m.get("content") for m in msgs]
    # 投影产物只能有 user + assistant，**不**含 todo/write
    assert "tool" not in roles
    assert "system" not in roles
    assert roles.count("user") == 1
    assert roles.count("assistant") == 1
    # todo 字段不能在 LLM 消息里出现
    joined = " ".join(str(c) for c in contents)
    assert "设计" not in joined or "帮我设计 TODO 流程" in joined, (
        f"todo 内容不应作为独立 LLM 消息出现：{joined}"
    )
    assert "in_progress" not in joined
    assert "pending" not in joined or "帮我设计 TODO 流程" in joined


# ---------- project_current_todo 投影 ----------

class _FakeStore:
    def __init__(self, events):
        self._events = events

    async def get_events(self, conv_id):
        return list(self._events)


async def test_project_current_todo_last_write_wins():
    """多次 todo/write 写入时返回最后一次的 todos（last-write-wins）。"""
    events = [
        StepEvent(
            event_id="e1", step_id="s", conv_id="c", agent_id="a",
            state=StepState.OBSERVING, event_type="todo/write",
            input={}, output={"todos": [{"id": "1", "content": "A", "status": "pending"}]},
            seq=1, timestamp=1.0,
        ),
        StepEvent(
            event_id="e2", step_id="s", conv_id="c", agent_id="a",
            state=StepState.OBSERVING, event_type="todo/write",
            input={}, output={"todos": [
                {"id": "1", "content": "A", "status": "completed"},
                {"id": "2", "content": "B", "status": "in_progress"},
            ]},
            seq=2, timestamp=2.0,
        ),
        # 混入其他事件，验证过滤
        StepEvent(
            event_id="e3", step_id="s", conv_id="c", agent_id="a",
            state=StepState.THINKING, event_type="user/message",
            input={}, output={"text": "x"},
            seq=3, timestamp=3.0,
        ),
    ]
    latest = await project_current_todo(_FakeStore(events), "c")
    assert latest is not None
    assert len(latest) == 2
    assert latest[0]["status"] == "completed"
    assert latest[1]["status"] == "in_progress"


async def test_project_current_todo_no_write_returns_none():
    """没有 todo/write 事件时返回 None（区别于"空列表"）。"""
    events = [
        StepEvent(
            event_id="e1", step_id="s", conv_id="c", agent_id="a",
            state=StepState.THINKING, event_type="user/message",
            input={}, output={"text": "x"},
            seq=1, timestamp=1.0,
        ),
    ]
    assert await project_current_todo(_FakeStore(events), "c") is None


async def test_project_current_todo_empty_list_is_legal_state():
    """最新 todo/write payload 的 todos 是空列表时返回 []，不是 None。"""
    events = [
        StepEvent(
            event_id="e1", step_id="s", conv_id="c", agent_id="a",
            state=StepState.OBSERVING, event_type="todo/write",
            input={}, output={"todos": []},
            seq=1, timestamp=1.0,
        ),
    ]
    latest = await project_current_todo(_FakeStore(events), "c")
    assert latest == []


# ---------- default_thinking_fn 不注入 TODO ----------

async def _fake_llm_stream(messages, model):
    yield {"token": "x"}


async def test_default_thinking_does_not_inject_todo_reminder():
    """V2 default_thinking_fn **不**把 todo 状态注入 LLM 上下文。

    验证手段：注入一个会污染的 fake gpts_memory + 在 gpts_memory 写入
    大量 todo，思考函数跑完后，发送给 LLM 的 messages 列表里**不能**含
    ``<system-reminder>`` 文本（DSH 模式下 system prompt 是静态前缀）。
    """
    from gyra.agent.core.v2.default_thinking import make_default_thinking_fn

    # 准备假数据：memory_bundle.gpts_memory.read_todos 会返回 100 项
    class _Todo:
        def __init__(self, id, content, status):
            self.id = id
            self.content = content
            self.status = status

    fake_todos = [
        _Todo(str(i), f"任务{i}", "pending") for i in range(50)
    ] + [
        _Todo(str(i), f"完成{i}", "completed") for i in range(50, 100)
    ]

    fake_memory = MagicMock()
    fake_memory.gpts_memory = MagicMock()
    fake_memory.gpts_memory.read_todos = AsyncMock(return_value=fake_todos)

    bundle = MagicMock()
    bundle.pipeline = MagicMock()
    bundle.pipeline.scrub_stream_delta = MagicMock(side_effect=lambda t: t)
    bundle.pipeline.consume_prefetch = AsyncMock(return_value=None)
    bundle.manager = MagicMock()
    bundle.manager.retrieve_relevant_memories = AsyncMock(return_value="")
    bundle.gpts_memory = fake_memory.gpts_memory

    # capture 实际发给 LLM 的 messages
    captured = {}

    async def _capture_stream(messages, model):
        captured["messages"] = list(messages)
        yield {"token": "ok"}

    thinking_fn = make_default_thinking_fn(
        llm_stream_fn=_capture_stream,
        model_alias="test",
        memory_bundle=bundle,
        context_provider=lambda *a, **k: [{"role": "user", "content": "hi"}],
    )
    async for _ in thinking_fn({"prompt": "hi", "conv_id": "c1", "session_id": "s1"}):
        pass

    # 收集所有 content
    msgs = captured.get("messages", [])
    joined = "\n".join(
        m.get("content", "") if isinstance(m.get("content"), str) else str(m.get("content"))
        for m in msgs
    )
    # DSH 设计：system prompt 静态、消息流无 <system-reminder> todo 注入
    assert "<system-reminder>" not in joined, (
        f"V2 default_thinking 仍然注入了 <system-reminder>，违背 DSH 设计：\n{joined}"
    )
    assert "当前任务进度" not in joined, (
        f"V2 default_thinking 仍然注入了 todo 进度，违背 DSH 设计：\n{joined}"
    )
    # 也不能把 todo 内容掺到任何消息里
    assert "任务0" not in joined and "完成50" not in joined, (
        f"V2 default_thinking 意外注入了 todo 内容：\n{joined}"
    )
