"""ShellExecTool command validation security tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from gyra.agent.tools.builtin.sandbox.shell_exec import ShellExecTool
from gyra.sandbox.sandbox_utils import (
    get_skill_command_extra_roots,
    is_high_risk_command,
    is_skill_script_command,
    validate_shell_command,
)


def _make_mock_sandbox_client(
    work_dir="/home/ubuntu", skill_dir="/data/skill"
):
    client = MagicMock()
    client.work_dir = work_dir
    client.skill_dir = skill_dir
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
async def test_allows_skill_dir_command():
    """Regression: shell_exec must not falsely reject paths inside skill_dir
    (e.g. ``find <skill_dir>/data-analysis -name '*.html'``). The path fence
    must whitelist skill_dir just like LocalShellClient does."""
    client = _make_mock_sandbox_client("/home/ubuntu", skill_dir="/data/skill")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute(
        {
            "command": "find /data/skill/data-analysis -type f -name '*.html' | head -20"
        },
        context=ctx,
    )
    assert result.success
    client.shell.exec_command.assert_awaited_once()


@pytest.mark.asyncio
async def test_still_blocks_escape_outside_allowed_roots():
    """Escape that is neither under work_dir nor skill_dir stays blocked."""
    client = _make_mock_sandbox_client("/home/ubuntu", skill_dir="/data/skill")
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute({"command": "cat /etc/passwd"}, context=ctx)
    assert not result.success
    client.shell.exec_command.assert_not_awaited()


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
    assert is_high_risk_command("cat img.iso >/dev/nvme0n1")
    assert is_high_risk_command("dd if=iso of=/dev/mapper/vg-root")


def test_dev_null_redirection_not_high_risk():
    """Regression: ``2>/dev/null`` was matched by the old block-device regex
    (r\"of=/dev/|>\\s*/dev/\"), so a plain ``grep ... 2>/dev/null | sort -u |
    head -60`` was flagged high-risk and blocked behind user authorization.
    Pseudo-device redirections are harmless and must never be flagged."""
    command = (
        'grep -oE "XTHIM\\.[A-Z_]+|XTHIS\\.[A-Z_]+|CDXTHIP\\.[A-Z_]+'
        '|CDXT[A-Z_]*\\.[A-Z_]+" data/tool_output_execute_raw_sql.txt '
        "2>/dev/null | sort -u | head -60"
    )
    assert not is_high_risk_command(command)
    assert not is_high_risk_command("ls -la > /dev/null")
    assert not is_high_risk_command("make 2>/dev/null 1>&2")
    assert not is_high_risk_command("echo hi >/dev/stdout")
    assert not is_high_risk_command("cmd > /dev/tty")
    assert not is_high_risk_command("dd if=/dev/zero of=/dev/null count=1")


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


# --- heredoc bodies are not path-validated ---


def test_heredoc_with_slash_literal_allowed():
    """Regression: a Python heredoc with ``if '/' in repo:`` was rejected
    because ``'/'`` tokenises to the bare path ``/`` (root). Heredoc bodies are
    program stdin, not path arguments, so they must not be path-validated.
    """
    command = (
        "python3 << 'EOF'\n"
        "import re\n"
        "if '/' in repo and not repo.startswith('orgs/'):\n"
        "    pass\n"
        "EOF"
    )
    validate_shell_command(command, "/home/ubuntu")  # no raise


def test_heredoc_body_not_path_validated():
    """A path-like token inside a heredoc body is stdin/code, not an escape.

    Consistent with ``python3 -c`` (code execution is permitted in the local
    sandbox; OS-level isolation is the real boundary, per LocalShellClient).
    """
    command = "python3 << 'EOF'\nopen('/etc/passwd')\nEOF"
    validate_shell_command(command, "/home/ubuntu")  # no raise


def test_heredoc_does_not_mask_following_escape():
    """Commands after a closed heredoc are still path-validated."""
    command = "python3 << 'EOF'\nprint(1)\nEOF\ncat /etc/passwd"
    with pytest.raises(PermissionError):
        validate_shell_command(command, "/home/ubuntu")


def test_heredoc_unquoted_and_dash_delimiters():
    """<<- (tab-stripped) and unquoted delimiters are recognised."""
    validate_shell_command("cat << EOF\nbody\nEOF", "/home/ubuntu")
    validate_shell_command("cat <<- EOF\n\tbody\nEOF", "/home/ubuntu")


def test_here_string_not_treated_as_heredoc():
    """``<<<`` here-string must not be misread as a heredoc start."""
    validate_shell_command("cat <<< x", "/home/ubuntu")


def test_bitshift_in_quoted_c_not_misread_as_heredoc():
    """``<<`` inside a quoted ``python3 -c`` arg is not a heredoc start; a
    following escape on the next line must still be caught (quote-awareness)."""
    command = 'python3 -c "x = a << b"\ncat /etc/passwd'
    with pytest.raises(PermissionError):
        validate_shell_command(command, "/home/ubuntu")


# --- command-line regex patterns are not misread as paths ---


def test_command_line_regex_with_leading_slash_allowed():
    """Regression: ``grep '/[^/"]*/[^/"]*"'`` and ``awk '/^[0-9]+/'`` were
    blocked because the pattern starts with '/' and was misread as an absolute
    path. Tokens with regex metacharacters are now treated as patterns and
    skipped by the path fence.
    """
    validate_shell_command(r"""grep '/[^/"]*/[^/"]*"' f.txt""", "/home/ubuntu")
    validate_shell_command(r"""awk '/^[0-9]+/' f.txt""", "/home/ubuntu")


def test_bare_slash_token_still_blocked():
    """A bare '/' is still blocked -- it is the same signal that catches
    ``rm -rf /`` and ``cat f; rm -rf /`` injections (which is_high_risk_command
    misses because the binary is ``cat``), so it cannot be skipped without
    opening an injection hole. Pass a real argument instead of '/'.
    """
    with pytest.raises(PermissionError):
        validate_shell_command("echo '/'", "/home/ubuntu")


def test_glob_token_skipped_but_specific_path_blocked():
    """Trade-off: a metachar token like ``/etc/*`` is skipped (treated as a
    pattern), so glob-style escapes are no longer caught by the path fence.
    Specific existing paths and ``rm -rf /`` are still blocked. The fence is
    defense-in-depth (``python3 -c`` bypasses it); OS-level isolation is the
    real boundary.
    """
    validate_shell_command("cat /etc/*", "/home/ubuntu")  # no raise (pattern)
    with pytest.raises(PermissionError):
        validate_shell_command("cat /etc/passwd", "/home/ubuntu")
    with pytest.raises(PermissionError):
        validate_shell_command("cat file; rm -rf /", "/home/ubuntu")


# --- skill-script trust: skill 目录脚本默认受信，不拦不授权 ---


def _make_skill_tree(tmp_path):
    """在 tmp_path 下造一个最小 skill 目录: run.sh + scripts/run.py。"""
    skill_dir = tmp_path / "skill"
    (skill_dir / "scripts").mkdir(parents=True)
    run_py = skill_dir / "scripts" / "run.py"
    run_py.write_text("print('ok')\n")
    run_sh = skill_dir / "run.sh"
    run_sh.write_text("echo ok\n")
    return str(skill_dir), str(run_py), str(run_sh)


class TestIsSkillScriptCommand:
    def test_interpreter_with_skill_script_true(self, tmp_path):
        skill_dir, run_py, _ = _make_skill_tree(tmp_path)
        assert is_skill_script_command(f"python3 {run_py} --flag x", skill_dir)

    def test_arg_containing_high_risk_words_true(self, tmp_path):
        """参数字符串里出现 dd of=/dev/sda 之类字样纯属误伤场景, 必须放行。"""
        skill_dir, run_py, _ = _make_skill_tree(tmp_path)
        command = f'python3 {run_py} --note "dd of=/dev/sda"'
        assert is_high_risk_command(command)
        assert is_skill_script_command(command, skill_dir)

    def test_direct_execution_of_skill_binary_true(self, tmp_path):
        skill_dir, _, run_sh = _make_skill_tree(tmp_path)
        assert is_skill_script_command(f"{run_sh} --help", skill_dir)

    def test_pipeline_entries_true(self, tmp_path):
        skill_dir, run_py, run_sh = _make_skill_tree(tmp_path)
        assert is_skill_script_command(f"cat data.txt | python3 {run_py}", skill_dir)
        assert is_skill_script_command(f"bash {run_sh} | head -5", skill_dir)

    def test_relative_script_with_work_dir_true(self, tmp_path):
        skill_dir, _, _ = _make_skill_tree(tmp_path)
        assert is_skill_script_command(
            "python3 scripts/run.py", skill_dir, work_dir=skill_dir
        )

    def test_gated_binary_in_chain_false(self, tmp_path):
        """组合命令里出现 rm/dd 等入口, 绝不借 skill 脚本名义放行。"""
        skill_dir, run_py, _ = _make_skill_tree(tmp_path)
        assert not is_skill_script_command(
            f"rm -rf /tmp/x && python3 {run_py}", skill_dir
        )
        assert not is_skill_script_command(
            f"dd of=/dev/sda && python3 {run_py}", skill_dir
        )

    def test_inline_code_not_trusted(self, tmp_path):
        """-c/-m 的内联代码/模块不是脚本文件, 即便引用 skill 路径也不受信。"""
        skill_dir, run_py, _ = _make_skill_tree(tmp_path)
        assert not is_skill_script_command(f'python3 -c "open({run_py!r})"', skill_dir)
        assert not is_skill_script_command("python3 -m http.server", skill_dir)

    def test_missing_or_outside_script_false(self, tmp_path):
        skill_dir, _, _ = _make_skill_tree(tmp_path)
        outside = tmp_path / "outside.py"
        outside.write_text("x = 1\n")
        assert not is_skill_script_command(
            f"python3 {skill_dir}/missing.py", skill_dir
        )
        assert not is_skill_script_command(f"python3 {outside}", skill_dir)

    def test_no_skill_dirs_false(self, tmp_path):
        skill_dir, run_py, _ = _make_skill_tree(tmp_path)
        assert not is_skill_script_command(f"python3 {run_py}", None)
        assert not is_skill_script_command(f"python3 {run_py}", "")

    def test_unparseable_command_false(self):
        assert not is_skill_script_command("python3 'unclosed", "/data/skill")

    def test_extra_roots_constant(self):
        assert get_skill_command_extra_roots() == ("/tmp",)


def test_skill_command_tmp_output_needs_extra_roots(tmp_path):
    """/tmp 不在默认白名单; skill 脚本命令需追加 extra roots 后栅栏才放行。"""
    skill_dir, run_py, _ = _make_skill_tree(tmp_path)
    command = f"python3 {run_py} --out /tmp/gyra_probe.json"
    with pytest.raises(PermissionError):
        validate_shell_command(command, str(tmp_path / "ws"), allowed_roots=[skill_dir])
    validate_shell_command(
        command,
        str(tmp_path / "ws"),
        allowed_roots=[skill_dir, *get_skill_command_extra_roots()],
    )


@pytest.mark.asyncio
async def test_skill_script_command_skips_authorization(monkeypatch, tmp_path):
    """skill 脚本命令: 参数中的高危字样不再触发用户授权, 直接执行。"""
    monkeypatch.setattr(
        "gyra.agent.tools.builtin.sandbox.shell_exec._resolve_sandbox_type",
        lambda: "local",
    )
    called = {"approval": False}

    async def _should_not_call(gateway, command, reason, **kwargs):
        called["approval"] = True
        return True

    monkeypatch.setattr(
        "gyra.agent.tools.authorization_middleware.request_command_approval",
        _should_not_call,
    )
    skill_dir, run_py, _ = _make_skill_tree(tmp_path)
    client = _make_mock_sandbox_client(str(tmp_path / "ws"), skill_dir=skill_dir)
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    command = f'python3 {run_py} --note "dd of=/dev/sda"'
    assert is_high_risk_command(command)  # 前提: 旧判定会把这条命令当高危
    result = await tool.execute({"command": command}, context=ctx)
    assert result.success
    client.shell.exec_command.assert_awaited_once()
    assert called["approval"] is False


@pytest.mark.asyncio
async def test_skill_script_tmp_output_allowed(monkeypatch, tmp_path):
    """skill 脚本命令写 /tmp: 栅栏放行, 不再误报越界。"""
    monkeypatch.setattr(
        "gyra.agent.tools.builtin.sandbox.shell_exec._resolve_sandbox_type",
        lambda: "local",
    )
    skill_dir, run_py, _ = _make_skill_tree(tmp_path)
    client = _make_mock_sandbox_client(str(tmp_path / "ws"), skill_dir=skill_dir)
    tool = ShellExecTool()
    ctx = {"sandbox_client": client}

    result = await tool.execute(
        {"command": f"python3 {run_py} --out /tmp/gyra_probe.json"}, context=ctx
    )
    assert result.success
    client.shell.exec_command.assert_awaited_once()
