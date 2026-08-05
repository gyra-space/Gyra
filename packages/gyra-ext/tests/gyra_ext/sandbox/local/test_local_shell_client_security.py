"""LocalShellClient command and cwd containment security tests."""

import os
import pytest

from gyra_ext.sandbox.local.shell_client import LocalShellClient


class MockRuntime:
    def __init__(self, base_dir):
        self.base_dir = base_dir


def _make_client(tmp_path, work_dir="/data/workspace", skill_dir=None, host_work_dir=None):
    session_dir = tmp_path / "sessions" / "s1"
    session_dir.mkdir(parents=True)
    runtime = MockRuntime(str(tmp_path / "sessions"))
    return LocalShellClient(
        sandbox_id="s1",
        work_dir=work_dir,
        runtime=runtime,
        skill_dir=skill_dir,
        host_work_dir=host_work_dir,
    )


@pytest.mark.asyncio
async def test_allowed_workspace_command(tmp_path):
    client = _make_client(tmp_path, work_dir="/data/workspace")
    os.makedirs(client._work_dir_physical, exist_ok=True)
    (tmp_path / "sessions" / "s1" / "data" / "workspace" / "file.txt").write_text("hello")

    result = await client.exec_command(command="cat file.txt", work_dir=client._work_dir_physical)
    assert result.status == "completed"
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_pipe_allowed(tmp_path):
    client = _make_client(tmp_path, work_dir="/data/workspace")
    os.makedirs(client._work_dir_physical, exist_ok=True)
    (tmp_path / "sessions" / "s1" / "data" / "workspace" / "file.txt").write_text("a\nb\nc\n")

    result = await client.exec_command(
        command="cat file.txt | wc -l", work_dir=client._work_dir_physical
    )
    assert result.status == "completed"
    assert "3" in result.output


@pytest.mark.asyncio
async def test_absolute_path_escape_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="cat /etc/passwd")
    assert result.status == "failed"
    assert "escapes" in result.output or "超出" in result.output or "禁止" in result.output


@pytest.mark.asyncio
async def test_relative_path_escape_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="cat ../../../etc/passwd")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_semicolon_injection_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="cat file.txt; rm -rf /")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_command_substitution_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="cat `id`")
    assert result.status == "failed"

    result = await client.exec_command(command="cat $(id)")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_python_c_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="python3 -c 'print(1)'")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bash_c_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="bash -c 'echo hi'")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_disallowed_binary_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="curl http://example.com")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_cwd_outside_sandbox_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="ls", work_dir="/etc")
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_cwd_relative_traversal_blocked(tmp_path):
    client = _make_client(tmp_path)
    result = await client.exec_command(command="ls", work_dir="../../../etc")
    assert result.status == "failed"
