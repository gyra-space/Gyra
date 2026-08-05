"""ToolAction sandbox authorization gate tests."""

import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gyra.agent.expand.actions.tool_action import ToolAction


class MockAgentContext:
    def __init__(self):
        self.agent_app_code = "test_app"
        self.conv_id = "conv_1"
        self.conv_session_id = "session_1"
        self.env_context = {}


class MockAgent:
    def __init__(self, sandbox_manager=None):
        self.name = "test_agent"
        self.agent_context = MockAgentContext()
        self.sandbox_manager = sandbox_manager
        self.llm_config = MagicMock()
        self.llm_config.llm_client = None


def _make_tool_info(name="Bash", is_async=True):
    tool_info = MagicMock()
    tool_info.name = name
    tool_info.is_async = is_async
    tool_info.async_execute = AsyncMock(return_value=MagicMock(success=True, output="ok"))
    tool_info.execute = MagicMock(return_value=MagicMock(success=True, output="ok"))
    tool_info.metadata = MagicMock()
    tool_info.metadata.requires_permission = True
    tool_info.metadata.authorization_config = {}
    tool_info.args = {"command": {"type": "string"}, "cwd": {"type": "string"}}
    tool_info._tool_base = None
    return tool_info


@pytest.mark.asyncio
async def test_bash_cwd_inside_sandbox_allowed(tmp_path):
    work_dir = str(tmp_path / "workspace")
    os.makedirs(work_dir, exist_ok=True)

    sandbox_client = MagicMock()
    sandbox_client.work_dir = work_dir

    sandbox_manager = MagicMock()
    sandbox_manager.client = sandbox_client

    agent = MockAgent(sandbox_manager=sandbox_manager)
    tool_info = _make_tool_info("Bash")

    action = ToolAction()
    result = await action._execute_tool(
        tool_info,
        {"command": "ls", "cwd": work_dir},
        agent=agent,
    )

    assert result["success"] is True
    tool_info.async_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_bash_cwd_outside_sandbox_denied(tmp_path):
    work_dir = str(tmp_path / "workspace")
    os.makedirs(work_dir, exist_ok=True)

    sandbox_client = MagicMock()
    sandbox_client.work_dir = work_dir

    sandbox_manager = MagicMock()
    sandbox_manager.client = sandbox_client

    agent = MockAgent(sandbox_manager=sandbox_manager)
    tool_info = _make_tool_info("Bash")

    action = ToolAction()
    result = await action._execute_tool(
        tool_info,
        {"command": "ls", "cwd": "/etc"},
        agent=agent,
    )

    assert result["success"] is False
    assert "outside" in result["error"].lower() or "sandbox" in result["error"].lower()
    tool_info.async_execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_shell_exec_no_cwd_allowed(tmp_path):
    work_dir = str(tmp_path / "workspace")
    os.makedirs(work_dir, exist_ok=True)

    sandbox_client = MagicMock()
    sandbox_client.work_dir = work_dir

    sandbox_manager = MagicMock()
    sandbox_manager.client = sandbox_client

    agent = MockAgent(sandbox_manager=sandbox_manager)
    tool_info = _make_tool_info("shell_exec")
    tool_info.args = {"command": {"type": "string"}, "timeout": {"type": "integer"}}

    action = ToolAction()
    result = await action._execute_tool(
        tool_info,
        {"command": "ls"},
        agent=agent,
    )

    assert result["success"] is True
    tool_info.async_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_shell_tool_not_blocked(tmp_path):
    work_dir = str(tmp_path / "workspace")
    os.makedirs(work_dir, exist_ok=True)

    sandbox_client = MagicMock()
    sandbox_client.work_dir = work_dir

    sandbox_manager = MagicMock()
    sandbox_manager.client = sandbox_client

    agent = MockAgent(sandbox_manager=sandbox_manager)
    tool_info = _make_tool_info("Read")

    action = ToolAction()
    result = await action._execute_tool(
        tool_info,
        {"path": "/etc/passwd"},
        agent=agent,
    )

    assert result["success"] is True
    tool_info.async_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_authorization_can_be_disabled(tmp_path):
    work_dir = str(tmp_path / "workspace")
    os.makedirs(work_dir, exist_ok=True)

    sandbox_client = MagicMock()
    sandbox_client.work_dir = work_dir

    sandbox_manager = MagicMock()
    sandbox_manager.client = sandbox_client

    agent = MockAgent(sandbox_manager=sandbox_manager)
    tool_info = _make_tool_info("Bash")

    mock_app_config = MagicMock()
    mock_app_config.sandbox.authorization_enabled = False

    mock_system_app = MagicMock()
    mock_system_app.config.configs.get.return_value = mock_app_config

    with patch(
        "gyra._private.config.Config"
    ) as mock_cfg_cls:
        mock_cfg = MagicMock()
        mock_cfg.SYSTEM_APP = mock_system_app
        mock_cfg_cls.return_value = mock_cfg

        action = ToolAction()
        result = await action._execute_tool(
            tool_info,
            {"command": "ls", "cwd": "/etc"},
            agent=agent,
        )

    assert result["success"] is True
    tool_info.async_execute.assert_awaited_once()
