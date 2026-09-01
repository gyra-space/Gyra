"""Tests for the reusable multimedia executor + agent (agent 协作范式载体).

覆盖：
- 预设风格/场景 prompt 组装（style_prompt 前置 + scene_prompt 后置）
- provider 参数组装（固定覆盖 + 输出默认 + 请求覆盖的优先级）
- 同步图片生成：provider 调用 → AFS 交付 → 带 artifact 的 SUCCESS ToolResult
- 异步视频提交：submit → AsyncTaskManager → 返回 PENDING job_id
- 模型选择优先级：显式 › config 默认 › 系统默认 › 首个可用
- MultimediaAgent 标准接口（run / generate_image / generate_video）
- MultimediaAgent 作为一等公民注册进 AgentManager（role=MULTIMEDIA）
- MultimediaAgent.to_async_delegate 生成 spawn_agent_task 兼容的委派协程
"""

from types import SimpleNamespace

import pytest

from gyra.agent.multimedia import (
    KIND_IMAGE,
    KIND_VIDEO,
    MultimediaAgent,
    MultimediaAgentConfig,
    MultimediaExecutor,
    MultimediaRequest,
)
from gyra.agent.tools.result import ResultStatus
from gyra.agent.util.media_gen.base import MediaGenResult, MediaSubmission

# ---------------------------------------------------------------------------
# 假 provider / AFS
# ---------------------------------------------------------------------------


class _FakeImageProvider:
    """测试用图片 provider：记录调用，返回固定 MediaGenResult。"""

    def __init__(self, api_key="", base_url=None, **kwargs):
        self.calls = []

    async def generate_image(self, prompt, model, **kwargs):
        self.calls.append((prompt, model, kwargs))
        return MediaGenResult(
            data=b"\x89PNG\r\n\x1a\nimage-bytes",
            format="png",
            mime_type="image/png",
            metadata={"model": model, "provider": "fake_image"},
        )


class _FakeVideoProvider:
    """测试用视频 provider：支持同步与异步（submit_video）。"""

    def __init__(self, api_key="", base_url=None, **kwargs):
        self.submits = []

    async def generate_video(self, prompt, model, **kwargs):
        return MediaGenResult(
            data=b"\x00\x00\x00\x18ftypvideo-bytes",
            format="mp4",
            mime_type="video/mp4",
            duration_seconds=5.0,
            metadata={"model": model, "provider": "fake_video", "resolution": "720p"},
        )

    async def submit_video(self, prompt, model, **kwargs):
        self.submits.append((prompt, model, kwargs))
        task_id = "submission-1"

        async def _complete():
            return await self.generate_video(prompt, model, **kwargs)

        return MediaSubmission(
            task_id=task_id,
            provider="fake_video",
            model=model,
            complete=_complete,
        )


class _FakeAFS:
    """最小化 AFS 桩：记录 save_binary_file 并返回可交付元数据。"""

    def __init__(self):
        self.saved = []

    async def save_binary_file(self, **kwargs):
        self.saved.append(kwargs)
        return SimpleNamespace(
            preview_url="https://file-service/preview.bin",
            download_url="https://file-service/download.bin",
            metadata={"object_path": "gyra-fs://deliver/generated.bin"},
        )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider_registry():
    """注册测试 provider 协议，测试后清理。"""
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    MediaGenProviderRegistry.register("test_image")(_FakeImageProvider)
    MediaGenProviderRegistry.register("test_video")(_FakeVideoProvider)
    yield MediaGenProviderRegistry
    # 清理测试协议，避免污染其他用例
    MediaGenProviderRegistry._protocol_providers.pop("test_image", None)
    MediaGenProviderRegistry._protocol_providers.pop("test_video", None)


@pytest.fixture
def config():
    return MultimediaAgentConfig(
        name="designer",
        default_image_model="img-model",
        default_video_model="vid-model",
        style_prompt="赛博朋克风格，高对比度",
        scene_prompt="居中构图，电影级光影",
        negative_prompt="低分辨率，模糊",
        default_image_size="1024x1024",
        default_video_resolution="1080p",
        default_video_aspect_ratio="16:9",
        default_video_duration=5,
        file_prefix="designed",
        fixed_params={"n": 1, "quality": "hd"},
    )


@pytest.mark.asyncio
async def test_build_prompt(config):
    """style_prompt 前置 + scene_prompt 后置。"""
    executor = MultimediaExecutor(config)
    final = executor._build_prompt("一只猫")
    assert final == "赛博朋克风格，高对比度\n一只猫\n居中构图，电影级光影"


@pytest.mark.asyncio
async def test_build_gen_kwargs_defaults_and_override(config):
    """固定覆盖 + 输出默认 + 请求覆盖优先级。"""
    executor = MultimediaExecutor(config)
    req = MultimediaRequest(prompt="p", kind=KIND_IMAGE, params={"size": "512x512"})
    kwargs = executor._build_gen_kwargs(KIND_IMAGE, req)
    assert kwargs["size"] == "512x512"  # 请求覆盖默认
    assert kwargs["n"] == 1  # fixed_params
    assert kwargs["quality"] == "hd"  # fixed_params
    assert kwargs["negative_prompt"] == "低分辨率，模糊"

    req_v = MultimediaRequest(prompt="p", kind=KIND_VIDEO, params={"duration": 8})
    kwargs_v = executor._build_gen_kwargs(KIND_VIDEO, req_v)
    assert kwargs_v["resolution"] == "1080p"  # config 输出默认
    assert kwargs_v["aspect_ratio"] == "16:9"
    assert kwargs_v["duration"] == 8  # 请求覆盖


@pytest.mark.asyncio
async def test_sync_image_generation_delivers_to_afs(
    config, provider_registry, monkeypatch
):
    """同步图片生成：调用 provider → AFS 交付 → SUCCESS ToolResult + artifact。"""
    fake = _FakeImageProvider()
    provider_registry._protocol_providers["test_image"] = type(fake)

    def _fake_resolve(model):
        return ("test_image", "fake-key", None)

    monkeypatch.setattr(
        MultimediaExecutor, "_resolve_media_model", staticmethod(_fake_resolve)
    )

    afs = _FakeAFS()
    executor = MultimediaExecutor(config, afs=afs)
    tr = await executor.run(
        MultimediaRequest(prompt="一只太空猫", kind=KIND_IMAGE, model="img-model")
    )

    assert tr.status == ResultStatus.SUCCESS
    assert tr.artifacts and tr.artifacts[0].url == "https://file-service/preview.bin"
    assert len(afs.saved) == 1
    assert afs.saved[0]["data"] == b"\x89PNG\r\n\x1a\nimage-bytes"
    assert afs.saved[0]["is_deliverable"] is True
    # 固定风格/场景 prompt 已注入
    assert "赛博朋克风格" in tr.output or tr.output


@pytest.mark.asyncio
async def test_async_video_submission_returns_pending(
    config, provider_registry, monkeypatch
):
    """异步视频提交：submit → AsyncTaskManager → PENDING job_id。"""
    fake_video = _FakeVideoProvider()
    fake_image = _FakeImageProvider()
    provider_registry._protocol_providers["test_video"] = type(fake_video)
    provider_registry._protocol_providers["test_image"] = type(fake_image)

    def _fake_resolve(model):
        return ("test_video", "fake-key", None)

    monkeypatch.setattr(
        MultimediaExecutor, "_resolve_media_model", staticmethod(_fake_resolve)
    )

    executor = MultimediaExecutor(config, conv_id="conv-1")
    tr = await executor.run(
        MultimediaRequest(
            prompt="日落海浪慢镜头",
            kind=KIND_VIDEO,
            model="vid-model",
            wait=False,
            conv_id="conv-1",
        )
    )

    assert tr.status == ResultStatus.PENDING
    assert tr.metadata.get("job_id")
    assert tr.metadata["async_task"]["kind"] == "video"
    assert tr.metadata["async_task"]["conv_id"] == "conv-1"
    # 已提交到后台，完成后可查询
    job_id = tr.metadata["job_id"]
    from gyra.agent.util.async_task_manager import AsyncTaskManager

    mgr = AsyncTaskManager.media_instance()
    state = mgr.get_status(job_id)
    assert state is not None


@pytest.mark.asyncio
async def test_model_resolution_priority(config, monkeypatch):
    """模型选择优先级：可用显式 › 屏蔽非法显式(文本模型)回退默认 › config 默认。"""
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    monkeypatch.setattr(
        MediaGenProviderRegistry,
        "get_usable_model_names",
        lambda cap: {
            "image": ["img-model", "img-explicit"],
            "video": ["vid-model"],
        }[cap],
    )

    executor = MultimediaExecutor(config)
    # 可用显式模型最高
    assert executor._resolve_model(KIND_IMAGE, "img-explicit") == "img-explicit"
    # 非法显式（文本模型）被屏蔽，回退 config 默认模型
    assert executor._resolve_model(KIND_IMAGE, "qwen3.6-plus") == "img-model"
    # config 默认
    assert executor._resolve_model(KIND_IMAGE, "") == "img-model"
    assert executor._resolve_model(KIND_VIDEO, "") == "vid-model"


@pytest.mark.asyncio
async def test_model_resolution_candidate_pool(monkeypatch):
    """可用模型候选池：只在池内选（默认›第一个可用›池内第一个）。"""
    from gyra.agent.multimedia.executor import MultimediaExecutor
    from gyra.agent.multimedia.config import MultimediaAgentConfig
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    monkeypatch.setattr(
        MediaGenProviderRegistry,
        "get_usable_model_names",
        lambda cap: {
            "image": ["img-a", "img-b"],
            "video": ["vid-a"],
        }[cap],
    )

    # 默认模型在池内且可用 → 用默认
    cfg1 = MultimediaAgentConfig(
        image_models=["img-a", "img-b"],
        default_image_model="img-b",
    )
    assert MultimediaExecutor(cfg1)._resolve_model(KIND_IMAGE, "") == "img-b"

    # 默认模型不在池内 → 用池内第一个可用
    cfg2 = MultimediaAgentConfig(
        image_models=["img-a", "img-b"],
        default_image_model="img-other",
    )
    assert MultimediaExecutor(cfg2)._resolve_model(KIND_IMAGE, "") == "img-a"

    # 池内都不可用 → 用池内第一个
    monkeypatch.setattr(
        MediaGenProviderRegistry, "get_usable_model_names", lambda cap: []
    )
    cfg3 = MultimediaAgentConfig(image_models=["img-x", "img-y"])
    assert MultimediaExecutor(cfg3)._resolve_model(KIND_IMAGE, "") == "img-x"

    # 候选池为空 → 回退 config 默认
    cfg4 = MultimediaAgentConfig()
    assert MultimediaExecutor(cfg4)._resolve_model(KIND_IMAGE, "") == ""


@pytest.mark.asyncio
async def test_deliver_always_afs_and_artifact(monkeypatch):
    """交付强制：无 deliver_to_afs / create_artifact，结果始终落 AFS 并建 artifact。"""
    assert not hasattr(MultimediaAgentConfig, "deliver_to_afs")
    assert not hasattr(MultimediaAgentConfig, "create_artifact")


@pytest.mark.asyncio
async def test_agent_standard_interface(config, provider_registry, monkeypatch):
    """MultimediaAgent 标准接口：run / generate_image / generate_video。"""
    provider_registry._protocol_providers["test_image"] = _FakeImageProvider
    provider_registry._protocol_providers["test_video"] = _FakeVideoProvider

    def _fake_resolve(model):
        proto = "test_video" if "vid" in (model or "") else "test_image"
        return (proto, "fake-key", None)

    monkeypatch.setattr(
        MultimediaExecutor, "_resolve_media_model", staticmethod(_fake_resolve)
    )

    agent = MultimediaAgent(config, afs=_FakeAFS())
    assert agent.name == "designer"
    assert agent.info()["capability_image"] is True

    tr_img = await agent.generate_image("一只猫")
    assert tr_img.status == ResultStatus.SUCCESS

    tr_vid = await agent.generate_video("日落海浪", wait=False)
    assert tr_vid.status == ResultStatus.PENDING


@pytest.mark.asyncio
async def test_agent_manager_registration(config):
    """MultimediaAgent 作为一等公民注册进 AgentManager（role=MULTIMEDIA）。

    与 ReActMaster 等主 Agent 模板共用同一注册/寻址机制，无独立注册表。
    """
    from gyra.agent.core.agent_manage import get_agent_manager
    from gyra.agent.core.base_agent import ConversableAgent

    mgr = get_agent_manager()
    # 注册后可按 role 或别名寻址（已注册则跳过）
    try:
        mgr.get_by_name("MULTIMEDIA")
    except ValueError:
        mgr.register_agent(MultimediaAgent)
    assert isinstance(MultimediaAgent, type) and issubclass(
        MultimediaAgent, ConversableAgent
    )
    assert mgr.get_by_name("MULTIMEDIA") is MultimediaAgent
    inst = mgr.get_agent("MULTIMEDIA")
    assert isinstance(inst, MultimediaAgent)
    assert inst.role == "MULTIMEDIA"


@pytest.mark.asyncio
async def test_bind_app_config_multi_instance():
    """bind_app_config：同一 MULTIMEDIA 模板下不同 app 各自携带独立配置（互不覆盖）。

    对应多实例寻址：同一 role 的多个多媒体 app，通过 app_code 各自绑定自己的
    名称/默认模型/风格 prompt，委派时互不污染。
    """
    a = MultimediaAgent()
    b = MultimediaAgent()

    a.bind_app_config(
        {
            "multimedia_agent": {
                "name": "卡通风格",
                "default_image_model": "img-cartoon",
                "default_video_model": "vid-cartoon",
                "style_prompt": "3D 卡通",
            }
        }
    )
    b.bind_app_config(
        {
            "multimedia_agent": {
                "name": "真人风格",
                "default_image_model": "img-real",
                "default_video_model": "vid-real",
                "style_prompt": "写实摄影",
            }
        }
    )

    assert a.name == "卡通风格"
    assert b.name == "真人风格"
    assert a.config.default_image_model == "img-cartoon"
    assert b.config.default_image_model == "img-real"
    assert a.config.default_video_model == "vid-cartoon"
    assert b.config.default_video_model == "vid-real"
    assert a.config.style_prompt == "3D 卡通"
    assert b.config.style_prompt == "写实摄影"
    # 互不污染：修改 a 不影响 b
    assert a.config.name != b.config.name


@pytest.mark.asyncio
async def test_bind_app_config_invalid_keeps_default():
    """bind_app_config 传入非 dict / 无多媒体配置时保持默认配置。"""
    agent = MultimediaAgent()
    agent.bind_app_config(None)
    assert agent.config.name == "multimedia_agent"
    agent.bind_app_config({})
    assert agent.config.name == "multimedia_agent"


@pytest.mark.asyncio
async def test_to_async_delegate_resolves(config):
    """to_async_delegate 生成与 spawn_agent_task 兼容的委派协程。"""
    agent = MultimediaAgent(config)

    # 委派协程签名与 spawn_agent_task 兼容
    result = await agent.to_async_delegate()(
        subagent_name="designer", task="一只猫", context={}
    )
    assert result is not None


@pytest.mark.asyncio
async def test_delegate_passes_reference_images(config, provider_registry, monkeypatch):
    """委派协程把 context 里的参考图/首帧/尾帧透传给 provider（图片输入链路）。"""
    fake = _FakeImageProvider()
    provider_registry._protocol_providers["test_image"] = type(fake)

    def _fake_resolve(model):
        return ("test_image", "fake-key", None)

    monkeypatch.setattr(
        MultimediaExecutor, "_resolve_media_model", staticmethod(_fake_resolve)
    )
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    monkeypatch.setattr(
        MediaGenProviderRegistry,
        "create_provider_by_protocol",
        staticmethod(lambda protocol, api_key, base_url: fake),
    )

    agent = MultimediaAgent(config, afs=_FakeAFS())
    delegate = agent.to_async_delegate()
    assert delegate is not None

    result = await delegate(
        subagent_name="designer",
        task="参考这张图生成一张赛博猫",
        context={
            "kind": "image",
            "reference_images": ["https://ref/1.png", "https://ref/2.png"],
            "image_url": "https://ref/first.png",
            "image_url_last": "https://ref/last.png",
        },
    )
    assert result is not None

    # 断言 provider 收到的 kwargs 包含参考图 / 首帧 / 尾帧
    assert fake.calls, "provider 应被以同步 path 调用（无 submit_image 时）"
    prompt, model, kwargs = fake.calls[0]
    assert kwargs["reference_images"] == [
        "https://ref/1.png",
        "https://ref/2.png",
    ]
    assert kwargs["image_url"] == "https://ref/first.png"
    assert kwargs["image_url_last"] == "https://ref/last.png"


@pytest.mark.asyncio
async def test_delegate_kind_from_context_and_task(  # noqa: E501
    config, provider_registry, monkeypatch
):
    """委派协程支持从 context.kind 或 task 里的 kind= 标记解析类型。"""
    fake_video = _FakeVideoProvider()
    provider_registry._protocol_providers["test_video"] = type(fake_video)

    def _fake_resolve(model):
        return ("test_video", "fake-key", None)

    monkeypatch.setattr(
        MultimediaExecutor, "_resolve_media_model", staticmethod(_fake_resolve)
    )
    from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

    monkeypatch.setattr(
        MediaGenProviderRegistry,
        "create_provider_by_protocol",
        staticmethod(lambda protocol, api_key, base_url: fake_video),
    )

    agent = MultimediaAgent(config, afs=_FakeAFS())
    delegate = agent.to_async_delegate()
    # context.kind=video → 走视频 provider
    await delegate(
        subagent_name="designer",
        task="日落海浪",
        context={"kind": "video", "params": {"duration": 8}},
    )
    assert fake_video.submits, "video 应走异步 submit_video"
    assert fake_video.submits[0][2]["duration"] == 8

    # task 里 kind= 标记 → 仍解析为 video
    await delegate(
        subagent_name="designer",
        task="kind=video 生成一段海浪",
        context={},
    )
    assert len(fake_video.submits) >= 2
