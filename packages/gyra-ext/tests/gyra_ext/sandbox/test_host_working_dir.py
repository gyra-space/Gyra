"""场景空间独立沙箱目录(host_working_dir)测试。

设计:场景空间对话(大厅/任务)的沙箱工作目录指向空间家目录
(pilot/data/workspaces/<id>,与数据集目录同源),跨会话持久;
host_working_dir 未设置时保持原有的 session 目录嵌套行为。
"""
import os

import pytest

from gyra.sandbox.providers.base import SessionConfig
from gyra_ext.sandbox.local.improved_provider import LocalSandboxConfig
from gyra_ext.sandbox.local.improved_runtime import ImprovedLocalSandboxSession


def _make_session(tmp_path, config: SessionConfig) -> ImprovedLocalSandboxSession:
    return ImprovedLocalSandboxSession(
        session_id="s1", config=config, runtime_dir=str(tmp_path / "rt")
    )


def test_host_working_dir_used_directly(tmp_path):
    """host_working_dir 设置时:物理工作目录=该真实路径,不嵌套 session 目录。"""
    host_dir = tmp_path / "workspaces" / "42"
    config = SessionConfig(working_dir="/ignored", host_working_dir=str(host_dir))
    session = _make_session(tmp_path, config)
    assert session._work_dir == str(host_dir)
    assert os.path.isdir(host_dir)  # 自动创建
    # 不嵌套:不在 session_dir 下
    assert not session._work_dir.startswith(session.session_dir)


def test_default_nested_behavior_unchanged(tmp_path):
    """未设置 host_working_dir:保持原有的 session 目录嵌套行为。"""
    config = SessionConfig(working_dir="/data/workspace")
    session = _make_session(tmp_path, config)
    expected = os.path.abspath(
        os.path.join(session.session_dir, "data/workspace")
    )
    assert session._work_dir == expected


def test_config_from_dict_carries_host_work_dir():
    cfg = LocalSandboxConfig.from_dict({"host_work_dir": "/tmp/ws/1"})
    assert cfg.host_work_dir == "/tmp/ws/1"
    sc = cfg.to_session_config()
    assert sc.host_working_dir == "/tmp/ws/1"


def test_config_default_work_dir_promoted_to_host():
    """默认 work_dir(项目 DATA_DIR 下的真实路径)自动作为 host 工作目录,
    文件落到真实路径(pilot/data/workspace)而非 /tmp 嵌套目录。"""
    from gyra_ext.sandbox.local.improved_provider import (
        DEFAULT_LOCAL_SANDBOX_WORK_DIR,
    )

    cfg = LocalSandboxConfig.from_dict({})
    assert cfg.host_work_dir == os.path.abspath(DEFAULT_LOCAL_SANDBOX_WORK_DIR)
    assert cfg.to_session_config().host_working_dir == cfg.host_work_dir


def test_config_logical_work_dir_stays_nested():
    """DATA_DIR 之外的逻辑路径(如 /data/workspace)不提升为 host 工作目录,
    保持原有 /tmp 嵌套行为。"""
    cfg = LocalSandboxConfig.from_dict({"work_dir": "/data/workspace"})
    assert cfg.host_work_dir is None
    assert cfg.to_session_config().host_working_dir is None


@pytest.mark.asyncio
async def test_default_config_writes_to_real_workspace(tmp_path, monkeypatch):
    """端到端:默认配置(DATA_DIR 下真实 work_dir)提升为 host 工作目录后,
    文件直接写到真实工作空间路径,而非 /tmp 嵌套 session 目录。

    用 tmp_path 模拟 DATA_DIR,避免污染真实的 pilot/data/workspace。
    """
    import gyra_ext.sandbox.local.improved_provider as mod
    from gyra_ext.sandbox.local.file_client import LocalFileClient

    fake_data = tmp_path / "data"
    fake_data.mkdir()
    monkeypatch.setattr(mod, "DATA_DIR", str(fake_data))
    real_ws = str(fake_data / "workspace")

    cfg = LocalSandboxConfig.from_dict({"work_dir": real_ws})
    assert cfg.host_work_dir == os.path.abspath(real_ws)

    class _RT:
        base_dir = str(tmp_path / "sessions")

    client = LocalFileClient(
        sandbox_id="s1",
        work_dir=cfg.work_dir,
        runtime=_RT(),
        host_work_dir=cfg.host_work_dir,
    )
    await client.write(f"{real_ws}/file.txt", "hello", overwrite=True)

    # 文件落到真实工作空间路径
    assert os.path.isfile(os.path.join(real_ws, "file.txt"))
    assert (fake_data / "workspace" / "file.txt").read_text() == "hello"


def test_workspace_sandbox_root(tmp_path, monkeypatch):
    """空间沙箱根目录:绝对路径 + files/db/runtime 子目录 + env 覆盖。"""
    from gyra_serve.workspace.dataset_service import workspace_sandbox_root

    monkeypatch.setenv("GYRA_WORKSPACE_SANDBOX_ROOT", str(tmp_path / "ws"))
    root = workspace_sandbox_root(7)
    assert root == os.path.abspath(str(tmp_path / "ws" / "7"))
    for sub in ("files", "db", "runtime"):
        assert os.path.isdir(os.path.join(root, sub))
