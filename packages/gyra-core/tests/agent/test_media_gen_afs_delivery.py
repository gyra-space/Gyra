"""Tests locking in AFS-managed delivery for media generation tools.

覆盖用户反馈的核心问题:生成结果必须落 AFS(文件服务)并产出交付物(pdf/预览/下载
地址),而不是只抛给模型原始 OSS 地址。这里验证 ``_save_and_deliver`` 在同步与
异步链路上都会通过 AFS 持久化字节并构造带 artifact 的 ToolResult。
"""

from types import SimpleNamespace

import pytest

from gyra.agent.tools.builtin.media_gen.media_gen_tools import (
    GenerateVideoTool,
)
from gyra.agent.tools.result import ResultStatus
from gyra.agent.util.media_gen.base import MediaGenResult


class _FakeAFS:
    """最小化 AFS 桩:记录 save_binary_file 调用并返回可交付元数据。"""

    def __init__(self):
        self.saved = []

    async def save_binary_file(self, **kwargs):
        self.saved.append(kwargs)
        return SimpleNamespace(
            preview_url="https://file-service/preview.mp4",
            download_url="https://file-service/download.mp4",
            metadata={"object_path": "gyra-fs://deliver/generated_video_abc.mp4"},
        )


@pytest.fixture
def tool():
    return GenerateVideoTool()


@pytest.mark.asyncio
async def test_sync_deliver_saves_to_afs_and_builds_artifact(tool):
    afs = _FakeAFS()
    result = MediaGenResult(
        data=b"\x00\x01video-bytes",
        format="mp4",
        mime_type="video/mp4",
        duration_seconds=5.0,
        metadata={"model": "happyhorse-1.1-t2v", "provider": "happyhorse"},
    )

    tr = await tool._save_and_deliver(
        result,
        file_name="generated_video_abc.mp4",
        description="测试视频",
        context=None,
        prompt="繁华街市追逐",
        afs=afs,
    )

    # 1) 字节务必经 AFS 落盘(不丢失、不转为字符串)
    assert len(afs.saved) == 1
    saved = afs.saved[0]
    assert saved["data"] == result.data
    assert saved["is_deliverable"] is True
    assert saved["file_name"] == "generated_video_abc.mp4"

    # 2) ToolResult 携带 AFS 管理的 artifact(预览/下载地址),而非裸 OSS URL
    assert tr.status == ResultStatus.SUCCESS
    assert tr.artifacts and tr.artifacts[0].url == "https://file-service/preview.mp4"
    assert tr.artifacts[0].name == "generated_video_abc.mp4"
    assert "交付文件" in tr.output
    assert "https://file-service/preview.mp4" in tr.output


@pytest.mark.asyncio
async def test_sync_deliver_without_afs_still_returns_result(tool):
    """无 AFS 时(极端降级)不崩溃,输出仍含原始链接,但无 artifact。"""
    result = MediaGenResult(
        data=b"v",
        format="mp4",
        mime_type="video/mp4",
        metadata={"model": "m", "video_url": "https://oss.example.com/raw.mp4"},
    )
    tr = await tool._save_and_deliver(
        result,
        file_name="generated_video_abc.mp4",
        description="d",
        context=None,
        prompt="p",
        afs=None,
    )
    assert tr.status == ResultStatus.SUCCESS
    assert "https://oss.example.com/raw.mp4" in tr.output
    # 无 AFS 时 artifact 无 AFS 管理的 url(裸 OSS 地址只在文本里,不进 artifact)
    assert tr.artifacts
    assert tr.artifacts[0].url is None