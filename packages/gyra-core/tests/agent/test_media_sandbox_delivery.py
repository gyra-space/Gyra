"""媒体文件落盘兜底 单元测试。

覆盖：
- AFS _save_with_file_storage_client 无 sandbox 时落本地拷贝到 base_path
- _LocalDirSandboxAdapter 的 file.write 接口
- MultimediaAgent._local_workspace_sandbox_fallback 的配置门控
"""
from __future__ import annotations

import pytest

from gyra.agent.core.file_system.agent_file_system import AgentFileSystem


class TestAFSLocalCopyFallback:
    @pytest.mark.asyncio
    async def test_no_sandbox_writes_local_copy(self, tmp_path):
        """无 sandbox 时，文件除进 FileStorage 外还应落 base_path 本地拷贝。"""

        class _FakeStorageClient:
            def save_file(self, bucket, file_name, file_data, custom_metadata=None):
                return f"distributed://node/{bucket}/fake-id"

        afs = AgentFileSystem(
            conv_id="conv_1",
            base_working_dir=str(tmp_path),
            sandbox=None,
            file_storage_client=_FakeStorageClient(),
        )
        uri, size = await afs._save_to_storage(
            "generated_media_x", b"\x89PNG fake bytes", extension="png"
        )
        assert uri.startswith("distributed://")
        local_copy = tmp_path / "conv_1" / "default" / "generated_media_x.png"
        assert local_copy.exists()
        assert local_copy.read_bytes() == b"\x89PNG fake bytes"
        assert size == len(b"\x89PNG fake bytes")


class TestLocalDirSandboxAdapter:
    @pytest.mark.asyncio
    async def test_file_write(self, tmp_path):
        from gyra.agent.multimedia.agent import _LocalDirSandboxAdapter

        adapter = _LocalDirSandboxAdapter(str(tmp_path))
        assert adapter.work_dir == str(tmp_path)
        target = f"{adapter.work_dir}/default/generated_media_y.png"
        await adapter.file.write(target, b"\x89PNG bytes")
        assert (tmp_path / "default" / "generated_media_y.png").read_bytes() == (
            b"\x89PNG bytes"
        )

    def test_fallback_gated_on_local_type(self, monkeypatch, tmp_path):
        """type 非 local / 无 work_dir / 目录不存在时不给兜底。"""
        from gyra.agent.multimedia.agent import MultimediaAgent

        agent = MultimediaAgent()

        class _SandboxCfg:
            def __init__(self, type_, work_dir):
                self.type = type_
                self.work_dir = work_dir

        class _AppConfig:
            def __init__(self, sandbox):
                self.sandbox = sandbox

        class _Cfg:
            def __init__(self, sandbox):
                self.config = type(
                    "C", (), {"configs": {"app_config": _AppConfig(sandbox)}}
                )()

        import gyra._private.config as cfg_mod

        def _patch_system_app(sandbox):
            stub = type("S", (), {"SYSTEM_APP": _Cfg(sandbox)})()
            monkeypatch.setattr(cfg_mod, "Config", lambda: stub)

        # type=local + 存在的目录 → 给兜底
        _patch_system_app(_SandboxCfg("local", str(tmp_path)))
        fb = agent._local_workspace_sandbox_fallback()
        assert fb is not None
        assert fb.work_dir == str(tmp_path)

        # type=e2b → 不给
        _patch_system_app(_SandboxCfg("e2b", str(tmp_path)))
        assert agent._local_workspace_sandbox_fallback() is None

        # 目录不存在 → 不给
        _patch_system_app(_SandboxCfg("local", str(tmp_path / "nope")))
        assert agent._local_workspace_sandbox_fallback() is None
