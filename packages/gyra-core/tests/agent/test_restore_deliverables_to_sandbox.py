"""Tests for AFS deliverable restore-to-sandbox on conversation recovery.

覆盖用户反馈的诉求:异步/后台生成时沙箱不可用、交付物只留存于 AFS(文件服务/OSS),
会话恢复时通过 ``sync_workspace -> restore_deliverables_to_sandbox`` 把交付物
补回沙箱工作目录,保证主 agent 能直接访问。
"""

import pytest

from gyra.agent.core.file_system.agent_file_system import AgentFileSystem
from gyra.agent.core.memory.gpts.file_base import (
    AgentFileMetadata,
    FileStatus,
    FileType,
    SimpleFileMetadataStorage,
)


class _FakeSandboxFile:
    """桩沙箱文件客户端:记录 write 调用。"""

    def __init__(self):
        self.writes: list = []

    async def write(self, path, data, **kwargs):
        self.writes.append((path, bytes(data)))


class _FakeSandbox:
    def __init__(self, work_dir="/sandbox/home"):
        self.work_dir = work_dir
        self.file = _FakeSandboxFile()


class _FakeMetaStorage(SimpleFileMetadataStorage):
    """可预置元数据的存储桩。"""

    def __init__(self, files):
        super().__init__()
        for f in files:
            self._storage.setdefault(f.conv_id, {})[f.file_key] = f


def _deliverable_meta(
    conv_id="conv-1",
    file_key="video_key",
    file_name="generated_video_abc.mp4",
    category=FileType.DELIVERABLE,
):
    return AgentFileMetadata(
        file_id="f-1",
        conv_id=conv_id,
        conv_session_id=conv_id,
        file_key=file_key,
        file_name=file_name,
        file_type=category.value,
        local_path="/host/agent_storage/conv-1/default/video_key.mp4",
        oss_url="gyra-fs://deliver/generated_video_abc.mp4",
        preview_url="https://file-service/preview.mp4",
        download_url="https://file-service/download.mp4",
        status=FileStatus.COMPLETED.value,
    )


@pytest.mark.asyncio
async def test_restore_writes_deliverables_to_sandbox(monkeypatch):
    """交付物从 AFS 读回字节并写入沙箱工作目录。"""
    meta = _deliverable_meta()
    afs = AgentFileSystem(
        conv_id="conv-1",
        sandbox=_FakeSandbox(),
        metadata_storage=_FakeMetaStorage([meta]),
    )

    async def _fake_read(storage_uri):
        assert storage_uri == meta.oss_url
        return b"\x00\x01real-video-bytes"

    monkeypatch.setattr(afs, "_read_from_storage", _fake_read)

    restored = await afs.restore_deliverables_to_sandbox()

    assert restored == 1
    path, data = afs.sandbox.file.writes[0]
    # 与 _save_to_storage 的落盘路径一致: {work_dir}/{goal_id}/{file_name}
    assert path == "/sandbox/home/default/generated_video_abc.mp4"
    assert data == b"\x00\x01real-video-bytes"


@pytest.mark.asyncio
async def test_restore_noop_without_sandbox(monkeypatch):
    """无沙箱时(如纯后台、无 sandbox 上下文)直接返回 0,不报错。"""
    meta = _deliverable_meta()
    afs = AgentFileSystem(
        conv_id="conv-1",
        sandbox=None,
        metadata_storage=_FakeMetaStorage([meta]),
    )

    monkeypatch.setattr(afs, "_read_from_storage", lambda uri: b"x")

    assert await afs.restore_deliverables_to_sandbox() == 0


@pytest.mark.asyncio
async def test_restore_skips_files_that_fail_to_read(monkeypatch):
    """读取失败的文件跳过,不影响其余文件还原。"""
    ok_meta = _deliverable_meta(file_key="ok_key", file_name="ok.mp4")
    bad_meta = _deliverable_meta(file_key="bad_key", file_name="bad.mp4")
    bad_meta.oss_url = "gyra-fs://deliver/bad.mp4"
    afs = AgentFileSystem(
        conv_id="conv-1",
        sandbox=_FakeSandbox(),
        metadata_storage=_FakeMetaStorage([ok_meta, bad_meta]),
    )

    async def _fake_read(storage_uri):
        if "bad" in storage_uri:
            return None  # 读失败
        return b"ok-bytes"

    monkeypatch.setattr(afs, "_read_from_storage", _fake_read)

    restored = await afs.restore_deliverables_to_sandbox()

    assert restored == 1
    assert len(afs.sandbox.file.writes) == 1
    assert afs.sandbox.file.writes[0][0] == "/sandbox/home/default/ok.mp4"


@pytest.mark.asyncio
async def test_sync_workspace_triggers_restore(monkeypatch):
    """sync_workspace(恢复时调用)会自动把交付物补回沙箱。"""
    meta = _deliverable_meta()
    afs = AgentFileSystem(
        conv_id="conv-1",
        sandbox=_FakeSandbox(),
        metadata_storage=_FakeMetaStorage([meta]),
    )

    async def _fake_read(storage_uri):
        return b"restored-bytes"

    monkeypatch.setattr(afs, "_read_from_storage", _fake_read)

    await afs.sync_workspace()

    assert len(afs.sandbox.file.writes) == 1
    assert afs.sandbox.file.writes[0][0] == "/sandbox/home/default/generated_video_abc.mp4"