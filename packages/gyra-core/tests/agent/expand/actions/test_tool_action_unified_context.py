"""ToolAction 统一工具框架 context 传递测试。

回归:非沙箱裸 ToolBase（如 todowrite/todoread，经 available_system_tools 直接注入、
未经 UnifiedToolAdapter 包装）在有 sandbox_manager 的 agent 下，应收到 agent 作为
context，而非被误判为旧框架工具走 sandbox dict 分支（导致 todo 报 "Todo 存储不可用"）。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.expand.actions.tool_action import ToolAction
from gyra.agent.tools.base import ToolBase, ToolCategory, ToolRiskLevel
from gyra.agent.tools.metadata import ToolMetadata
from gyra.agent.tools.result import ToolResult


class MockAgentContext:
    def __init__(self):
        self.agent_app_code = "test_app"
        self.conv_id = "conv_1"
        self.conv_session_id = "session_1"
        self.env_context = {}


class MockAgent:
    def __init__(self, sandbox_manager=None, memory=None, not_null_agent_context=None):
        self.name = "test_agent"
        self.agent_context = MockAgentContext()
        self.sandbox_manager = sandbox_manager
        self.llm_config = MagicMock()
        self.llm_config.llm_client = None
        self.memory = memory
        self.not_null_agent_context = not_null_agent_context


class _ContextRecorderTool(ToolBase):
    """非沙箱裸 ToolBase，记录 execute 收到的 context。"""

    def __init__(self):
        self.received_context = None
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="recorder",
            display_name="Recorder",
            description="records context",
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.SAFE,
        )

    def _define_parameters(self):
        return {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        }

    async def execute(self, args, context=None):
        self.received_context = context
        return ToolResult.ok(output="ok", tool_name="recorder")


@pytest.mark.asyncio
async def test_bare_unified_toolbase_gets_agent_context_with_sandbox():
    """非沙箱裸 ToolBase + 有 sandbox_manager 的 agent -> context 应为 agent 本身。

    修复前：tool_base is None 使其走 sandbox dict 分支，context 丢失。
    """
    sandbox_manager = MagicMock()
    sandbox_manager.client = MagicMock(work_dir="/ws")

    agent = MockAgent(sandbox_manager=sandbox_manager)
    tool = _ContextRecorderTool()

    action = ToolAction()
    result = await action._execute_tool(tool, {"x": "1"}, agent=agent)

    assert result["success"] is True
    # 关键：收到 agent 本身，而非 {"sandbox_manager": ...} 或 None
    assert tool.received_context is agent


@pytest.mark.asyncio
async def test_todowrite_succeeds_with_sandbox_agent():
    """todowrite 在沙箱 agent 下不应报 'Todo 存储不可用'。"""
    gpts_memory = AsyncMock()
    gpts_memory.read_todos = AsyncMock(return_value=[])
    gpts_memory.write_todos = AsyncMock()
    gpts_memory.push_message = AsyncMock()

    memory = MagicMock()
    memory.gpts_memory = gpts_memory

    agent_ctx = MagicMock()
    agent_ctx.conv_id = "conv_1"
    agent_ctx.conv_session_id = "session_1"

    sandbox_manager = MagicMock()
    sandbox_manager.client = MagicMock(work_dir="/ws")

    agent = MockAgent(
        sandbox_manager=sandbox_manager,
        memory=memory,
        not_null_agent_context=agent_ctx,
    )

    from gyra.agent.tools.builtin.todo.todowrite import TodowriteTool

    tool = TodowriteTool()
    action = ToolAction()
    result = await action._execute_tool(
        tool,
        {"todos": [{"content": "任务1", "status": "pending"}]},
        agent=agent,
    )

    assert result["success"] is True
    assert "存储不可用" not in (result.get("content") or "")
    gpts_memory.write_todos.assert_awaited_once()
