"""ShellExecTool command validation security tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.tools.builtin.sandbox.shell_exec import ShellExecTool


def _make_mock_sandbox_client(work_dir="/home/ubuntu"):
    client = MagicMock()
    client.work_dir = work_dir
    client.agent_file_system = None
    client.shell = MagicMock()
    client.shell.exec_command = AsyncMock(
        return_value=MagicMock(status="completed", exit_code=0, output="ok", console=[])
    )
    client.file = MagicMock()
    return client


@pytest.mark.asyncio
async def test_allows_workspace_command():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat /home/ubuntu/file.txt"}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_blocks_absolute_escape():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat /etc/passwd"}, context=ctx)
    assert not result.success
    client.shell.exec_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocks_parent_escape():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat ../secret"}, context=ctx)
    assert not result.success
    client.shell.exec_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocks_shell_injection():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat file; rm -rf /"}, context=ctx)
    assert not result.success
    client.shell.exec_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocks_command_substitution():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat `id`"}, context=ctx)
    assert not result.success

    result = await tool.execute({"command": "cat $(id)"}, context=ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_blocks_python_c():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "python3 -c 'print(1)'"}, context=ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_blocks_bash_c():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "bash -c 'echo hi'"}, context=ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_allows_and_and_pipe():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute(
        {"command": "cat /home/ubuntu/a.txt && cat /home/ubuntu/b.txt | wc -l"},
        context=ctx,
    )
    assert result.success
    client.shell.exec_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_blocks_disallowed_binary():
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "curl http://example.com"}, context=ctx)
    assert not result.success
