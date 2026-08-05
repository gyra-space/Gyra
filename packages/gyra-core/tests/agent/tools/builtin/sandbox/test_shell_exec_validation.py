"""ShellExecTool command validation security tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.tools.builtin.sandbox.shell_exec import ShellExecTool
from gyra.sandbox.sandbox_utils import validate_shell_command, is_high_risk_command


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
async def test_allows_command_substitution():
    """Command substitution is permitted in the local sandbox."""
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat `id`"}, context=ctx)
    assert result.success

    result = await tool.execute({"command": "cat $(id)"}, context=ctx)
    assert result.success


@pytest.mark.asyncio
async def test_allows_python_c():
    """python3 -c is permitted in the local sandbox (code execution is allowed)."""
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "python3 -c 'print(1)'"}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_allows_python_c_multiline_with_metachars():
    """Multi-line python3 -c containing $, parens, newlines is allowed.

    Regression for the scene-agent report case that was blocked by the old
    raw-metachar scan and the python -c ban.
    """
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    command = 'python3 -c "data = (1, 2)\nprint(data)\nprint($x)"'
    result = await tool.execute({"command": command}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_allows_bash_c():
    """bash -c is permitted (no command allowlist)."""
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "bash -c 'echo hi'"}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()


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
async def test_allows_any_binary():
    """No command allowlist: curl and other binaries are permitted."""
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "curl http://example.com"}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()


# --- validate_shell_command: local path fence vs remote open ---


def test_validate_local_path_fence_blocks_escape():
    """Local sandbox: paths outside work_dir are still blocked."""
    with pytest.raises(PermissionError):
        validate_shell_command("cat /etc/passwd", "/home/ubuntu")


def test_validate_remote_is_open():
    """Remote sandbox: no validation, even path-escape commands pass."""
    # Should not raise.
    validate_shell_command("cat /etc/passwd", "/home/ubuntu", sandbox_type="e2b")
    validate_shell_command("rm -rf /", "/home/ubuntu", sandbox_type="docker")


# --- is_high_risk_command ---


def test_high_risk_rm_recursive():
    assert is_high_risk_command("rm -rf dir")
    assert is_high_risk_command("rm -r dir")
    assert is_high_risk_command("rm --recursive dir")
    assert not is_high_risk_command("rm file")  # non-recursive rm is not high-risk


def test_high_risk_disk_and_block_device():
    assert is_high_risk_command("dd if=/dev/zero of=/dev/sda")
    assert is_high_risk_command("mkfs.ext4 /dev/sda1")
    assert is_high_risk_command("cat img.iso > /dev/sda")


def test_high_risk_normal_commands_false():
    assert not is_high_risk_command("ls -la")
    assert not is_high_risk_command("mkdir dir")
    assert not is_high_risk_command("cp a b")
    assert not is_high_risk_command("python3 -c 'print(1)'")
    assert not is_high_risk_command("node app.js")


# --- ShellExecTool: high-risk authorization flow (local) ---


@pytest.mark.asyncio
async def test_high_risk_local_prompts_and_allows(monkeypatch):
    """Local + high-risk: approval granted -> command executes."""
    monkeypatch.setattr(
        "gyra.agent.tools.builtin.sandbox.shell_exec._resolve_sandbox_type",
        lambda: "local",
    )

    async def _approve(gateway, command, reason, **kwargs):
        return True

    monkeypatch.setattr(
        "gyra.agent.tools.authorization_middleware.request_command_approval",
        _approve,
    )
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "rm -rf /home/ubuntu/dir"}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_high_risk_local_denied_blocks(monkeypatch):
    """Local + high-risk: approval denied -> command does not execute."""
    monkeypatch.setattr(
        "gyra.agent.tools.builtin.sandbox.shell_exec._resolve_sandbox_type",
        lambda: "local",
    )

    async def _deny(gateway, command, reason, **kwargs):
        return False

    monkeypatch.setattr(
        "gyra.agent.tools.authorization_middleware.request_command_approval",
        _deny,
    )
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "rm -rf /home/ubuntu/dir"}, context=ctx)
    assert not result.success
    client.shell.exec_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_high_risk_remote_no_prompt(monkeypatch):
    """Remote sandbox: high-risk command executes without authorization prompt."""
    monkeypatch.setattr(
        "gyra.agent.tools.builtin.sandbox.shell_exec._resolve_sandbox_type",
        lambda: "e2b",
    )
    called = {"approval": False}

    async def _should_not_call(gateway, command, reason, **kwargs):
        called["approval"] = True
        return True

    monkeypatch.setattr(
        "gyra.agent.tools.authorization_middleware.request_command_approval",
        _should_not_call,
    )
    client = _make_mock_sandbox_client("/home/ubuntu")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "rm -rf /home/ubuntu/dir"}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()
    assert called["approval"] is False
