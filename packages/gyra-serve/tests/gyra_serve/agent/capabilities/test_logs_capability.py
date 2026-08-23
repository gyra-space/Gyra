"""logs capability 测试:注册归属 + 本地查询 + 安全校验 + host 解析 + 超时。

本地查询用例基于真实日志目录(自动探测或显式 LOG_DIR 环境变量)。
无日志环境时,相关用例自动跳过。
"""

import asyncio
import os
import shlex
from pathlib import Path

import pytest

from gyra_serve.agent.capabilities.logs.tools import (
    LOG_TOOL_NAMES,
    register_logs_tools_capability,
)

LOG_DIR = os.environ.get("LOGS_TEST_DIR") or str(Path.cwd() / "logs")


def _have_logs() -> bool:
    return Path(LOG_DIR).is_dir() and any(Path(LOG_DIR).glob("*.log*"))


def _import_impl():
    import gyra_serve.agent.capabilities.logs.tools._logs_tools_impl  # noqa: F401
    return pytest.importorskip("gyra_serve.agent.capabilities.logs.tools._logs_tools_impl")


# =========================================================================== #
# 注册与归属
# =========================================================================== #
def test_logs_tools_registered():
    impl = _import_impl()
    from gyra.agent.tools.registry import tool_registry

    register_logs_tools_capability(tool_registry)
    for name in LOG_TOOL_NAMES:
        tool = tool_registry.get(name)
        assert tool is not None, f"{name} 未注册"
        assert tool.metadata.capability_id == "logs"
        assert getattr(tool.metadata, "risk_level", None) is not None


# =========================================================================== #
# 本地查询功能(需要真实日志目录)
# =========================================================================== #
@pytest.mark.skipif(not _have_logs(), reason="无日志目录可测")
@pytest.mark.asyncio
async def test_list_log_files():
    impl = _import_impl()
    r = await impl.list_log_files(log_dir=LOG_DIR)
    assert "日志目录" in r and ".log" in r


@pytest.mark.skipif(not _have_logs(), reason="无日志目录可测")
@pytest.mark.asyncio
async def test_search_logs_level_only():
    """仅级别过滤(首级 grep 须带文件参数,否则挂起)——回归 137 挂起 bug。"""
    impl = _import_impl()
    r = await asyncio.wait_for(
        impl.search_logs(pattern="", level="ERROR", log_dir=LOG_DIR, limit=5),
        timeout=10,
    )
    assert "检索结果" in r or "无匹配" in r


@pytest.mark.skipif(not _have_logs(), reason="无日志目录可测")
@pytest.mark.asyncio
async def test_search_logs_time_range():
    impl = _import_impl()
    r = await impl.search_logs(
        pattern=".", from_time="2000-01-01", to_time="2999-12-31",
        log_dir=LOG_DIR, limit=10,
    )
    assert "检索结果" in r


@pytest.mark.skipif(not _have_logs(), reason="无日志目录可测")
@pytest.mark.asyncio
async def test_tail_logs_auto_pick_latest():
    impl = _import_impl()
    r = await asyncio.wait_for(impl.tail_logs(log_dir=LOG_DIR, lines=5), timeout=10)
    assert "最近 5 行" in r


@pytest.mark.skipif(not _have_logs(), reason="无日志目录可测")
@pytest.mark.asyncio
async def test_analyze_logs():
    impl = _import_impl()
    r = await impl.analyze_logs(log_dir=LOG_DIR, top=3)
    assert "Top3" in r or "无 ERROR/WARN" in r


# =========================================================================== #
# 安全校验
# =========================================================================== #
def test_whitelist_rejects_rm():
    impl = _import_impl()
    with pytest.raises(ValueError):
        impl._validate_command("grep x logs/*.log | rm -rf /")


def test_injection_pattern_quoted_not_executed(tmp_path):
    """恶意 pattern 必须被 shlex.quote 完整引用,不得产生副作用。"""
    impl = _import_impl()
    marker = tmp_path / "pwned"
    evil = f"'; echo PWNED > {marker}; '"
    cmd = impl._grep_segment(evil, None, impl._glob_arg(str(tmp_path), None))
    assert shlex.quote(evil) in cmd  # 被完整引用为单个参数
    asyncio.run(impl.search_logs(pattern=evil, log_dir=str(tmp_path), limit=3))
    assert not marker.exists()


def test_invalid_pattern_rejected():
    impl = _import_impl()
    with pytest.raises(ValueError):
        asyncio.run(impl.search_logs(pattern="a\nb", log_dir=LOG_DIR))


def test_invalid_time_rejected():
    impl = _import_impl()
    with pytest.raises(ValueError):
        asyncio.run(impl.search_logs(pattern="ERROR", from_time="2026/08/23", log_dir=LOG_DIR))


def test_invalid_level_rejected():
    impl = _import_impl()
    with pytest.raises(ValueError):
        asyncio.run(impl.search_logs(pattern="", level="TRACE", log_dir=LOG_DIR))


# =========================================================================== #
# host 解析(动态,无固定配置)
# =========================================================================== #
def test_resolve_host_shorthand():
    impl = _import_impl()
    h = impl._resolve_host("root@10.0.0.5:2222")
    assert h == {"host": "10.0.0.5", "user": "root", "port": 2222}
    assert impl._resolve_host(None) is None
    assert impl._resolve_host("10.0.0.5") == {"host": "10.0.0.5"}


def test_resolve_host_json():
    impl = _import_impl()
    h = impl._resolve_host('{"host":"a.b","user":"u","log_dir":"/opt/x/logs"}')
    assert h["host"] == "a.b" and h["log_dir"] == "/opt/x/logs"


def test_resolve_host_json_with_raw_newline_key_content():
    """手工拼的 host JSON 里 key_content(私钥)带真实换行也能解析。"""
    impl = _import_impl()
    import json

    pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nxx\n-----END OPENSSH PRIVATE KEY-----\n"
    raw = '{"host":"a.b","key_content":"%s"}' % pem  # 真实换行,未转义
    assert impl._resolve_host(raw)["key_content"].startswith("-----BEGIN")
    std = json.dumps({"host": "a.b", "key_content": pem})  # 标准转义
    assert impl._resolve_host(std)["key_content"].startswith("-----BEGIN")
    with pytest.raises(ValueError):
        impl._resolve_host('{"host": broken')


def test_resolve_host_invalid():
    impl = _import_impl()
    for bad in ["bad host!", "a b@1.2.3.4", "host:99999"]:
        with pytest.raises(ValueError):
            impl._resolve_host(bad)


def test_host_registry():
    impl = _import_impl()
    impl.register_log_host("prod-1", {"host": "10.1.1.1", "log_dir": "/srv/app/logs"})
    try:
        assert impl._resolve_host("prod-1")["host"] == "10.1.1.1"
        assert "prod-1" in impl.list_log_hosts()
    finally:
        impl.unregister_log_host("prod-1")


def test_remote_requires_log_dir():
    impl = _import_impl()
    with pytest.raises(ValueError):
        impl._resolve_log_dir({"host": "10.0.0.5"}, None)  # 远程必须显式 log_dir


# =========================================================================== #
# 按需绑定注入语义(默认不注入;agent 配置绑定后才注入)
# =========================================================================== #
def test_logs_tools_not_injected_by_default():
    """未绑定的 agent 默认不注入 logs 工具(注册≠注入)。"""
    impl = _import_impl()
    from gyra.agent.tools.registry import tool_registry
    from gyra.agent.tools.tool_manager import AgentToolConfiguration

    register_logs_tools_capability(tool_registry)
    assert all(tool_registry.get(n) is not None for n in LOG_TOOL_NAMES)  # 已注册
    cfg = AgentToolConfiguration(app_id="a", agent_name="x")
    assert all(not cfg.is_tool_enabled(n) for n in LOG_TOOL_NAMES)  # 但默认禁用


def test_logs_tools_enabled_after_binding():
    """agent 配置显式绑定后 → 注入;解绑(tombstone)后 → 不注入。"""
    impl = _import_impl()
    from gyra.agent.tools.tool_manager import (
        AgentToolConfiguration,
        ToolBindingConfig,
        ToolBindingType,
    )

    cfg = AgentToolConfiguration(app_id="a", agent_name="x")
    cfg.bindings["search_logs"] = ToolBindingConfig(
        tool_id="search_logs", binding_type=ToolBindingType.CUSTOM
    )
    assert cfg.is_tool_enabled("search_logs")
    cfg.bindings["search_logs"] = ToolBindingConfig(
        tool_id="search_logs", binding_type=ToolBindingType.CUSTOM, is_bound=False
    )
    assert not cfg.is_tool_enabled("search_logs")


# =========================================================================== #
# SSH 认证密钥(key_file 服务端路径 / key_content 临时传入)
# =========================================================================== #
def test_ssh_key_materialize_key_content(tmp_path):
    impl = _import_impl()
    pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nabc123\n-----END OPENSSH PRIVATE KEY-----\n"
    path, tmp = impl._materialize_ssh_key({"host": "x", "key_content": pem})
    assert tmp is not None and path == tmp
    try:
        with open(path, encoding="utf-8") as f:
            assert f.read() == pem
        assert os.stat(path).st_mode & 0o777 == 0o600  # 0600 权限
    finally:
        os.unlink(path)


def test_ssh_key_materialize_key_file(tmp_path):
    impl = _import_impl()
    keyfile = tmp_path / "web.pem"
    keyfile.write_text("-----BEGIN RSA PRIVATE KEY-----\nk\n")
    path, tmp = impl._materialize_ssh_key({"host": "x", "key_file": str(keyfile)})
    assert path == str(keyfile) and tmp is None  # 文件路径直接复用,不建临时文件


def test_ssh_key_materialize_none():
    impl = _import_impl()
    assert impl._materialize_ssh_key({"host": "x"}) == (None, None)


def test_ssh_key_invalid_content_rejected():
    impl = _import_impl()
    with pytest.raises(ValueError):
        impl._materialize_ssh_key({"host": "x", "key_content": "not a key"})
    with pytest.raises(ValueError):
        impl._materialize_ssh_key({"host": "x", "key_content": "x" * 70000})


def test_ssh_key_missing_file_rejected():
    impl = _import_impl()
    with pytest.raises(ValueError):
        impl._materialize_ssh_key({"host": "x", "key_file": "/no/such/key.pem"})


@pytest.mark.asyncio
async def test_ssh_key_content_tmp_cleaned_after_failure():
    """key_content 连接失败后临时私钥文件必须被清理(不落盘残留)。"""
    impl = _import_impl()
    pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nDUMMY\n-----END OPENSSH PRIVATE KEY-----\n"
    import glob

    before = set(glob.glob("/tmp/gyra_ssh_key_*"))
    with pytest.raises(RuntimeError):
        await impl._run_remote_async(
            {"host": "10.255.255.1", "user": "nobody", "port": 22, "key_content": pem},
            "ls /tmp", timeout=15,
        )
    after = set(glob.glob("/tmp/gyra_ssh_key_*"))
    assert after == before  # 无残留


# =========================================================================== #
# 超时与输出上限
# =========================================================================== #
@pytest.mark.asyncio
async def test_command_timeout():
    impl = _import_impl()
    with pytest.raises(TimeoutError):
        await impl._run_async("tail -f /dev/null", timeout=2)


def test_output_truncated():
    impl = _import_impl()
    out = impl._truncate_or_pass("x" * 100, limit=10)
    assert out == "x" * 10 + "\n... [输出超 10 字节,已截断]"


def test_bad_command_shell_syntax():
    impl = _import_impl()
    with pytest.raises(ValueError):
        impl._validate_command("grep 'unterminated")


def test_time_normalize():
    impl = _import_impl()
    assert impl._normalize_time("2026-08-23") == "2026-08-23 00:00:00"
    assert impl._normalize_time("2026-08-23 04:05") == "2026-08-23 04:05:00"
    assert impl._normalize_time(None) == ""
