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
async def test_command_substitution_allowed(tmp_path):
    """Command substitution is permitted in the local sandbox."""
    client = _make_client(tmp_path)
    os.makedirs(client._work_dir_physical, exist_ok=True)
    result = await client.exec_command(
        command="echo $(echo hi)", work_dir=client._work_dir_physical
    )
    assert result.status == "completed"
    assert "hi" in result.output


@pytest.mark.asyncio
async def test_python_c_allowed(tmp_path):
    """python3 -c is permitted in the local sandbox (code execution is allowed)."""
    client = _make_client(tmp_path)
    result = await client.exec_command(command="python3 -c 'print(1)'")
    assert result.status == "completed"
    assert "1" in result.output


@pytest.mark.asyncio
async def test_python_c_multiline_allowed(tmp_path):
    """Multi-line python3 -c with parens/newlines runs (report-generation case)."""
    client = _make_client(tmp_path)
    os.makedirs(client._work_dir_physical, exist_ok=True)
    script = "x = (1, 2)\nprint(sum(x))"
    result = await client.exec_command(
        command=f'python3 -c "{script}"', work_dir=client._work_dir_physical
    )
    assert result.status == "completed"
    assert "3" in result.output


@pytest.mark.asyncio
async def test_bash_c_allowed(tmp_path):
    """bash -c is permitted (no command allowlist)."""
    client = _make_client(tmp_path)
    result = await client.exec_command(command="bash -c 'echo hi'")
    assert result.status == "completed"
    assert "hi" in result.output


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


@pytest.mark.asyncio
async def test_skill_dir_command_allowed(tmp_path):
    """Commands referencing the sanctioned skill_dir pass the path fence.

    Regression: SandboxManager.initialize() runs `mkdir -p <skill_dir>` to prep
    the knowledge repo. The fence must honor the client's allowed_roots (which
    include skill_dir), not just the physical work_dir -- otherwise the sandbox
    blocks its own initialization.
    """
    skill_dir = tmp_path / "skill"
    client = _make_client(
        tmp_path, work_dir="/data/workspace", skill_dir=str(skill_dir)
    )
    result = await client.exec_command(command=f"mkdir -p {skill_dir}")
    assert result.status == "completed"
    assert skill_dir.exists()


@pytest.mark.asyncio
async def test_logical_workdir_allowed_when_basedir_behind_symlink(tmp_path):
    """Regression: macOS /var -> /private/var.

    When the sandbox base_dir lives behind a symlink, the stored allowed roots
    keep the symlinked prefix (abspath) while the candidate cwd is resolved
    (realpath). Passing the LOGICAL work_dir -- as shell_exec.py does via
    client.work_dir -- must still resolve into the sandbox instead of being
    falsely rejected as 'escapes sandbox allowed roots'.
    """
    real_root = tmp_path / "real"
    real_root.mkdir()
    link_root = tmp_path / "link"
    link_root.symlink_to(real_root, target_is_directory=True)

    sessions = link_root / "sessions"
    sessions.mkdir()
    (sessions / "s1").mkdir()
    runtime = MockRuntime(str(sessions))

    client = LocalShellClient(
        sandbox_id="s1",
        work_dir="/data/workspace",
        runtime=runtime,
    )
    os.makedirs(client._work_dir_physical, exist_ok=True)
    # Sanity: the symlink makes abspath != realpath for the session root,
    # which is the condition that triggered the original false rejection.
    assert os.path.realpath(client._session_root) != client._session_root

    result = await client.exec_command(command="echo ok", work_dir="/data/workspace")
    assert result.status == "completed"
    assert "ok" in result.output


@pytest.mark.asyncio
async def test_skill_script_command_can_write_tmp(tmp_path):
    """skill 目录脚本默认受信: 栅栏额外放行 /tmp(脚本中间产物常见落点)。"""
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    script = skill_dir / "run.py"
    script.write_text(
        "import pathlib\n"
        "pathlib.Path('/tmp/gyra_skill_probe_out.json').write_text('ok')\n"
    )
    client = _make_client(tmp_path, work_dir="/data/workspace", skill_dir=str(skill_dir))

    probe = "/tmp/gyra_skill_probe_out.json"
    try:
        result = await client.exec_command(command=f"python3 {script} --out {probe}")
        assert result.status == "completed"
        with open(probe) as f:
            assert f.read() == "ok"
    finally:
        if os.path.exists(probe):
            os.remove(probe)


@pytest.mark.asyncio
async def test_non_skill_command_cannot_write_tmp(tmp_path):
    """非 skill 脚本命令写 /tmp 仍被路径栅栏拦截。"""
    client = _make_client(
        tmp_path, work_dir="/data/workspace", skill_dir=str(tmp_path / "skill")
    )
    result = await client.exec_command(command="touch /tmp/gyra_fence_probe_blocked")
    assert result.status == "failed"
