"""同步媒体生成路径的持久化任务记录（镜像）单元测试。

覆盖（媒体生成很贵，一个请求结果都不能丢）：
- 同步图片生成：生成前登记 atask 记录，成功后回写终态 + provider 元数据
- 同步视频（显式 submit）：provider_task_id 立即落记录
- 同步轮询超时转后台：镜像记"已转后台"并指向真正的 atask
- 在途镜像可被防重复守卫命中（同步路径重复提交被拦截）
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from gyra.agent.multimedia import (
    KIND_IMAGE,
    KIND_VIDEO,
    MultimediaAgentConfig,
    MultimediaExecutor,
    MultimediaRequest,
)
from gyra.agent.tools.result import ResultStatus
from gyra.agent.util.async_task_manager import (
    AsyncTaskManager,
    AsyncTaskStatus,
)
from gyra.agent.util.media_gen.base import MediaGenResult, MediaSubmission


class _FakeImageProvider:
    def __init__(self, api_key="", base_url=None, **kwargs):
        pass

    async def generate_image(self, prompt, model, **kwargs):
        return MediaGenResult(
            data=b"\x89PNG\r\n\x1a\nimage-bytes",
            format="png",
            mime_type="image/png",
            metadata={
                "model": model,
                "provider": "fake_image",
                "task_id": "img-task-1",
                "image_url": "https://oss/img.png",
            },
        )


class _FakeVideoProvider:
    def __init__(self, api_key="", base_url=None, timeout=False, **kwargs):
        self._timeout = timeout

    async def submit_video(self, prompt, model, **kwargs):
        async def _complete():
            if self._timeout:
                raise TimeoutError("poll timed out")
            return MediaGenResult(
                data=b"\x00\x00\x00\x18ftypvideo-bytes",
                format="mp4",
                mime_type="video/mp4",
                metadata={
                    "model": model,
                    "task_id": "vid-task-1",
                    "video_url": "https://oss/vid.mp4",
                },
            )

        return MediaSubmission(
            task_id="vid-task-1",
            provider="fake_video",
            model=model,
            complete=_complete,
            metadata={"duration": 5, "resolution": "1080p"},
        )


class _FakeAFS:
    def __init__(self):
        self.saved = []

    async def save_binary_file(self, **kwargs):
        self.saved.append(kwargs)
        return SimpleNamespace(
            preview_url="https://file-service/preview.bin",
            download_url="https://file-service/download.bin",
            metadata={"object_path": "gyra-fs://deliver/generated.bin"},
        )


@pytest.fixture
def config():
    return MultimediaAgentConfig(
        name="designer",
        default_image_model="img-model",
        default_video_model="vid-model",
        file_prefix="designed",
    )


@pytest.fixture
def video_config():
    return MultimediaAgentConfig(
        name="videographer",
        capability="video",
        default_video_model="vid-model",
        file_prefix="designed",
    )


@pytest.fixture
def manager(monkeypatch):
    """隔离的 AsyncTaskManager（不碰单例/台账文件）。"""
    mgr = AsyncTaskManager(ledger_path=None)
    monkeypatch.setattr(
        AsyncTaskManager,
        "media_instance",
        classmethod(lambda cls, ledger_path=None: mgr),
    )
    return mgr


def _patch_resolve(monkeypatch, protocol):
    def _fake_resolve(model):
        return (protocol, "fake-key", None)

    monkeypatch.setattr(
        MultimediaExecutor, "_resolve_media_model", staticmethod(_fake_resolve)
    )


@pytest.fixture
def providers():
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    MediaGenProviderRegistry.register("test_image")(_FakeImageProvider)
    MediaGenProviderRegistry.register("test_video")(_FakeVideoProvider)
    MediaGenProviderRegistry.register("test_video_timeout")(
        type("T", (_FakeVideoProvider,), {"__init__": lambda s, **kw: _FakeVideoProvider.__init__(s, timeout=True, **kw)})
    )
    yield MediaGenProviderRegistry
    for p in ("test_image", "test_video", "test_video_timeout"):
        MediaGenProviderRegistry._protocol_providers.pop(p, None)


@pytest.mark.asyncio
async def test_sync_image_registers_and_completes_mirror(
    config, providers, manager, monkeypatch
):
    """同步图片：生成前登记 atask，成功后回写 COMPLETED + provider 元数据。"""
    _patch_resolve(monkeypatch, "test_image")
    executor = MultimediaExecutor(config, afs=_FakeAFS())

    tr = await executor.run(
        MultimediaRequest(prompt="一只太空猫", kind=KIND_IMAGE, model="img-model")
    )
    assert tr.status == ResultStatus.SUCCESS

    assert len(manager._tasks) == 1
    state = next(iter(manager._tasks.values()))
    assert state.spec.kind == KIND_IMAGE
    assert state.spec.context["source"] == "multimedia_sync"
    assert "一只太空猫" in state.spec.context["prompt"]
    assert state.status == AsyncTaskStatus.COMPLETED
    # provider 元数据已合并（task_id / 原始链接 / 文件名）
    assert state.spec.context["provider_task_id"] == "img-task-1"
    assert state.spec.context["raw_url"] == "https://oss/img.png"
    assert state.spec.context["file_name"].endswith(".png")
    # 结果已同步交付 → consumed，不再注入完成通知
    assert state.consumed is True


@pytest.mark.asyncio
async def test_sync_video_mirror_has_provider_task_id_upfront(
    video_config, providers, manager, monkeypatch
):
    """同步视频（显式 submit）：提交后 provider_task_id 立即落记录。"""
    _patch_resolve(monkeypatch, "test_video")
    executor = MultimediaExecutor(video_config, afs=_FakeAFS())

    tr = await executor.run(
        MultimediaRequest(prompt="海浪慢镜头", kind=KIND_VIDEO, model="vid-model")
    )
    assert tr.status == ResultStatus.SUCCESS

    state = next(iter(manager._tasks.values()))
    assert state.spec.kind == KIND_VIDEO
    assert state.spec.context["provider_task_id"] == "vid-task-1"
    assert state.spec.context["provider"] == "fake_video"
    assert state.spec.context["gen_kwargs"]["duration"] == 5
    assert state.status == AsyncTaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_poll_timeout_migrates_to_background(
    video_config, providers, manager, monkeypatch
):
    """同步轮询超时：镜像记"已转后台"，真正的 atask 带 provider_task_id。"""
    _patch_resolve(monkeypatch, "test_video_timeout")
    executor = MultimediaExecutor(video_config, afs=_FakeAFS())

    tr = await executor.run(
        MultimediaRequest(prompt="海浪慢镜头", kind=KIND_VIDEO, model="vid-model")
    )
    # 转后台 → PENDING，含新 job_id
    assert tr.status == ResultStatus.PENDING
    bg_job = tr.metadata["job_id"]

    assert len(manager._tasks) == 2
    mirror = next(
        s for s in manager._tasks.values()
        if s.spec.context.get("source") == "multimedia_sync"
    )
    bg = manager.get_status(bg_job)

    # 镜像：已转后台，指向真正的 atask（completed + consumed）
    assert mirror.status == AsyncTaskStatus.COMPLETED
    assert bg_job in (mirror.result or "")
    assert "vid-task-1" in (mirror.result or "")
    assert mirror.consumed is True

    # 真正的后台任务：provider_task_id 落 detail（complete 会再超时 → FAILED，
    # 但 provider 记录不丢）
    assert bg is not None
    assert bg.spec.context["provider_task_id"] == "vid-task-1"


@pytest.mark.asyncio
async def test_sync_in_flight_mirror_triggers_dedup(
    config, providers, manager, monkeypatch
):
    """同步路径的在途镜像可被防重复守卫命中：相同请求不再重复提交。"""
    _patch_resolve(monkeypatch, "test_image")
    executor = MultimediaExecutor(config, afs=_FakeAFS())

    # 手动模拟一个正在进行的相同任务（上一次同步生成尚未完成）
    from gyra.agent.util.async_task_manager import AsyncTaskSpec

    await manager.register_external(
        AsyncTaskSpec(
            task_id="atask_running",
            kind=KIND_IMAGE,
            model="img-model",
            task_description="AI 生成内容: 一只太空猫",
            conv_id="",
            context={
                "source": "multimedia_sync",
                "prompt": "一只太空猫",
            },
        )
    )

    tr = await executor.run(
        MultimediaRequest(prompt="一只太空猫", kind=KIND_IMAGE, model="img-model")
    )
    # 命中在途 → 复用，不产生新任务、不调用 provider
    assert tr.status == ResultStatus.PENDING
    assert tr.metadata["reused"] is True
    assert tr.metadata["job_id"] == "atask_running"
    assert len(manager._tasks) == 1


# ---------------------------------------------------------------------------
# 手动召回（recall_media_job_record）
# ---------------------------------------------------------------------------


class _RecallableVideoProvider:
    """支持 resume_task 的视频 provider：轮询已有 task 直接返回结果。"""

    def __init__(self, api_key="", base_url=None, **kwargs):
        self.resumed = []

    async def resume_task(self, task_id, model, **kwargs):
        self.resumed.append((task_id, model, kwargs))

        async def _complete():
            return MediaGenResult(
                data=b"\x00\x00\x00\x18ftypvideo-bytes",
                format="mp4",
                mime_type="video/mp4",
                metadata={
                    "model": model,
                    "task_id": task_id,
                    "provider": "fake_video",
                    "video_url": "https://oss/recalled.mp4",
                    "recalled": True,
                },
            )

        return MediaSubmission(
            task_id=task_id,
            provider="fake_video",
            model=model,
            complete=_complete,
        )


class _NoResumeProvider:
    """未实现 resume_task 的 provider（基类默认抛 NotImplementedError）。"""

    def __init__(self, api_key="", base_url=None, **kwargs):
        pass


@pytest.fixture
def recall_providers():
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    MediaGenProviderRegistry.register("test_recall")(_RecallableVideoProvider)
    MediaGenProviderRegistry.register("test_noresume")(_NoResumeProvider)
    yield MediaGenProviderRegistry
    for p in ("test_recall", "test_noresume"):
        MediaGenProviderRegistry._protocol_providers.pop(p, None)


def _job(**overrides):
    job = {
        "task_id": "atask_dead",
        "conv_id": "conv_1",
        "kind": "video",
        "model": "vid-model",
        "description": "海浪慢镜头",
        "status": "failed",
        "detail": {
            "provider": "fake_video",
            "provider_task_id": "vid-task-1",
            "prompt": "海浪慢镜头",
            "gen_kwargs": {"duration": 5},
        },
    }
    job.update(overrides)
    return job


@pytest.mark.asyncio
async def test_recall_success_delivers_and_updates_record(
    recall_providers, manager, monkeypatch
):
    """召回成功：resume_task 轮询已有任务 → 交付 → record_updates 完整。"""
    from gyra.agent.multimedia import recall as recall_mod

    _patch_resolve(monkeypatch, "test_recall")
    fake_afs = _FakeAFS()
    monkeypatch.setattr(recall_mod, "_build_recall_afs", lambda conv_id: fake_afs)

    outcome = await recall_mod.recall_media_job_record(_job())

    assert outcome["success"] is True
    assert len(fake_afs.saved) == 1
    updates = outcome["record_updates"]
    assert updates["status"] == "completed"
    assert updates["artifact"]["url"] == "https://file-service/preview.bin"
    assert updates["detail"]["recalled"] is True
    assert updates["detail"]["provider_task_id"] == "vid-task-1"
    assert updates["detail"]["raw_url"] == "https://oss/recalled.mp4"


@pytest.mark.asyncio
async def test_recall_rejects_missing_provider_task_id(recall_providers, manager):
    """记录缺 provider_task_id → 明确失败，不发起任何请求。"""
    from gyra.agent.multimedia import recall as recall_mod

    job = _job(detail={"prompt": "x"})
    outcome = await recall_mod.recall_media_job_record(job)
    assert outcome["success"] is False
    assert "provider_task_id" in outcome["message"]


@pytest.mark.asyncio
async def test_recall_rejects_non_media_kind(recall_providers, manager):
    """非媒体任务（subagent）→ 拒绝召回。"""
    from gyra.agent.multimedia import recall as recall_mod

    outcome = await recall_mod.recall_media_job_record(_job(kind="subagent"))
    assert outcome["success"] is False
    assert "不是媒体生成任务" in outcome["message"]


@pytest.mark.asyncio
async def test_recall_provider_without_resume(recall_providers, manager, monkeypatch):
    """provider 未实现 resume_task → 返回不支持错误。"""
    from gyra.agent.multimedia import recall as recall_mod

    _patch_resolve(monkeypatch, "test_noresume")
    outcome = await recall_mod.recall_media_job_record(_job())
    assert outcome["success"] is False
    assert "不支持" in outcome["message"]
