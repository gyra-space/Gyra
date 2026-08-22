"""Todowrite 工具的 LLM 回显格式 + 事件溯源 todo/write 写入测试。

对齐 DSH tool-todo 设计：
  - 工具结果回显是简洁文本（不是 verbose JSON 字符串），LLM 验证写入即可；
  - 完整 todos 通过 ``ToolResult.metadata`` 携带，**不**进 LLM 上下文；
  - V2 上下文存在时 emit ``todo/write`` 事件到 StateStore（last-write-wins）。
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.core.memory.gpts.file_base import TodoItem, TodoStatus
from gyra.agent.tools.builtin.todo.todowrite import TodowriteTool


class _FakeGptsMemory:
    def __init__(self, existing=None):
        self._existing = list(existing or [])
        self._writes = []

    async def read_todos(self, conv_id):
        return list(self._existing)

    async def write_todos(self, conv_id, todos):
        self._writes.append(list(todos))
        self._existing = list(todos)

    async def push_dock_widget(self, conv_id, widget):
        return None


class _FakeAgentCtx:
    def __init__(self, conv_id):
        self.conv_id = conv_id
        self.conv_session_id = conv_id


class _FakeAgent:
    def __init__(self, conv_id, state_store=None):
        self.name = "fake-agent"
        self.not_null_agent_context = _FakeAgentCtx(conv_id)
        self.memory = MagicMock()
        self.memory.gpts_memory = _FakeGptsMemory()
        self._v2_current_step_id = "s1"
        if state_store is not None:
            self._ensure_v2_state_store = MagicMock(return_value=state_store)


def _make_tool():
    return TodowriteTool()


async def test_todowrite_result_is_human_readable_text():
    """工具结果应是简洁文本（不应该是 verbose JSON 字符串）。"""
    tool = _make_tool()
    agent = _FakeAgent("c1")
    result = await tool.execute(
        {"todos": [
            {"content": "设计接口", "status": "pending"},
            {"content": "实现", "status": "in_progress"},
        ]},
        context=MagicMock(agent=agent),
    )
    assert result.success
    out = result.output
    assert isinstance(out, str), f"expected str, got {type(out)}"
    # 简洁回显：含 counts + 各 status
    assert "已更新任务列表" in out
    assert "1 pending" in out
    assert "1 in_progress" in out
    # 含紧凑列表
    assert "[pending] 设计接口" in out
    assert "[in_progress] 实现" in out
    # 不应是 verbose JSON 字符串
    assert not out.strip().startswith("{"), (
        "工具输出不应是 JSON 字符串，应是 LLM 友好的简洁文本"
    )


async def test_todowrite_result_metadata_carries_full_todos():
    """完整 todos 通过 metadata.todos 携带，LLM 上下文不接收（不进 V2 LLM 投影）。"""
    tool = _make_tool()
    agent = _FakeAgent("c1")
    result = await tool.execute(
        {"todos": [
            {"content": "A", "status": "pending"},
            {"content": "B", "status": "completed"},
        ]},
        context=MagicMock(agent=agent),
    )
    assert result.success
    assert "todos" in result.metadata
    assert isinstance(result.metadata["todos"], list)
    assert len(result.metadata["todos"]) == 2
    # counts 同步
    assert result.metadata["counts"] == {
        "pending": 1,
        "in_progress": 0,
        "completed": 1,
    }


async def test_todowrite_emits_todo_write_event_when_v2_state_store_present():
    """V2 上下文存在时 emit ``todo/write`` 事件到 StateStore（last-write-wins）。"""
    tool = _make_tool()
    state_store = MagicMock()
    state_store.append_event = AsyncMock()
    agent = _FakeAgent("c1", state_store=state_store)

    result = await tool.execute(
        {"todos": [
            {"content": "A", "status": "pending"},
            {"content": "B", "status": "in_progress"},
        ]},
        context=MagicMock(agent=agent),
    )
    assert result.success
    state_store.append_event.assert_called_once()
    ev = state_store.append_event.call_args[0][0]
    assert ev.event_type == "todo/write"
    assert ev.conv_id == "c1"
    assert ev.input == {"tool": "todowrite"}
    assert isinstance(ev.output, dict)
    assert "todos" in ev.output
    assert len(ev.output["todos"]) == 2


async def test_todowrite_skips_event_when_no_v2_state_store():
    """V1 / 无 V2 上下文时**不**emit 事件，行为兼容。"""
    tool = _make_tool()
    agent = _FakeAgent("c1", state_store=None)
    # 确保 _ensure_v2_state_store 不存在
    if hasattr(agent, "_ensure_v2_state_store"):
        delattr(agent, "_ensure_v2_state_store")
    result = await tool.execute(
        {"todos": [{"content": "A", "status": "pending"}]},
        context=MagicMock(agent=agent),
    )
    assert result.success
    # 不会 raise，事件通道是辅助的


async def test_todowrite_failure_does_not_emit_event():
    """todo 写入失败时**不**emit 事件。"""
    tool = _make_tool()
    state_store = MagicMock()
    state_store.append_event = AsyncMock()
    agent = _FakeAgent("c1", state_store=state_store)

    # 让 gpts_memory.write_todos 抛错
    agent.memory.gpts_memory.write_todos = AsyncMock(
        side_effect=RuntimeError("storage down")
    )

    result = await tool.execute(
        {"todos": [{"content": "A", "status": "pending"}]},
        context=MagicMock(agent=agent),
    )
    assert not result.success
    state_store.append_event.assert_not_called()
