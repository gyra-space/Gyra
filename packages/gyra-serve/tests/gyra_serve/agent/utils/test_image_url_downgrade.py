"""Tests: capability-aware file shunting in sandbox_file_ref.process_user_input_file.

Unified decision (decide_process_mode) semantics:
- 非多媒体文件（文档/代码/压缩/数据/未知）→ 一律 SANDBOX_TOOL
- 多媒体文件 + 模型能力含所需模态(vision/audio/video) → MODEL_DIRECT
- 多媒体文件 + 多媒体 agent(prefer_direct_media) → MODEL_DIRECT
- 否则 → SANDBOX_TOOL（先入沙箱，由 agent 经工具/子 agent 委派）
"""
import sys
from unittest.mock import MagicMock

import pytest

if "gyra_app.config" not in sys.modules:
    sys.modules["gyra_app"] = MagicMock()
    sys.modules["gyra_app.config"] = MagicMock()

from gyra_serve.agent.file_io.sandbox_file_ref import (
    looks_like_image,
    process_user_input_file,
)


def _image_url_input(file_name: str, url: str = "gyra-fs://_/bk/id1") -> dict:
    return {"type": "image_url", "image_url": {"url": url, "file_name": file_name}}


@pytest.mark.asyncio
async def test_confirmed_image_with_vision_stays_multimodal():
    """正常 .png image_url + 模型具备 vision → 直接消费,同时产出稳定引用
    (model_direct) 供主 agent 转发给多媒体子 agent 作首帧/参考图。"""
    multimodal, ref, err = await process_user_input_file(
        _image_url_input("cat.png"), capabilities=["vision"]
    )
    assert multimodal is not None
    assert multimodal["type"] == "image_url"
    assert ref is not None
    assert ref.process_mode == "model_direct"
    assert ref.sandbox_path.endswith("uploads/cat.png")
    assert ref.url == "gyra-fs://_/bk/id1"
    assert err is None


@pytest.mark.asyncio
async def test_multimedia_agent_prefers_direct_media_without_caps():
    """.png + 多媒体 agent(无能力标签) → 仍直接消费,并产出 model_direct 引用。"""
    multimodal, ref, err = await process_user_input_file(
        _image_url_input("cat.png"), prefer_direct_media=True
    )
    assert multimodal is not None
    assert ref is not None
    assert ref.process_mode == "model_direct"


@pytest.mark.asyncio
async def test_image_without_vision_goes_sandbox():
    """.png + 模型无 vision(普通文本模型) → 无法直接消费,进沙箱工具消费。"""
    multimodal, ref, err = await process_user_input_file(_image_url_input("cat.png"))
    assert multimodal is None
    assert ref is not None
    assert ref.process_mode == "sandbox_tool"


@pytest.mark.asyncio
async def test_audio_without_audio_capability_goes_sandbox():
    """.mp3 + 模型无 audio 能力 → 进沙箱。"""
    inp = {
        "type": "file_url",
        "file_url": {"url": "gyra-fs://_/bk/id5", "file_name": "voice.mp3"},
    }
    multimodal, ref, err = await process_user_input_file(inp)
    assert multimodal is None
    assert ref is not None
    assert ref.process_mode == "sandbox_tool"


@pytest.mark.asyncio
async def test_audio_with_audio_capability_but_file_url_forced_sandbox():
    """.mp3 + 模型有 audio 能力：file_url 目前仅图片走 MODEL_DIRECT,
    其余强制沙箱（守卫逻辑），避免非图媒体直接硬塞模型。"""
    inp = {
        "type": "file_url",
        "file_url": {"url": "gyra-fs://_/bk/id6", "file_name": "voice.mp3"},
    }
    multimodal, ref, err = await process_user_input_file(
        inp, capabilities=["audio"]
    )
    assert multimodal is None
    assert ref is not None
    assert ref.process_mode == "sandbox_tool"


@pytest.mark.asyncio
async def test_non_image_claimed_as_image_url_downgrades_to_sandbox():
    """image_url + pdf(即使模型有 vision)→ pdf 非媒体模态,守卫降级沙箱。"""
    multimodal, ref, err = await process_user_input_file(
        _image_url_input("report.pdf"), capabilities=["vision"]
    )
    assert multimodal is None
    assert ref is not None
    assert ref.process_mode == "sandbox_tool"
    assert err is None


@pytest.mark.asyncio
async def test_extensionless_image_url_with_no_mime_downgrades_to_sandbox():
    """无扩展名 + 无 mime → 无法确认模态,降级沙箱。"""
    multimodal, ref, err = await process_user_input_file(
        _image_url_input("image_abc12345"), capabilities=["vision"]
    )
    assert multimodal is None
    assert ref is not None
    assert ref.process_mode == "sandbox_tool"


@pytest.mark.asyncio
async def test_jpeg_extension_with_vision_stays_multimodal():
    """.jpeg + vision → 仍多模态(扩展名路径生效)。"""
    inp = {
        "type": "image_url",
        "image_url": {"url": "gyra-fs://_/bk/id2", "file_name": "photo.jpeg"},
    }
    multimodal, ref, err = await process_user_input_file(inp, capabilities=["vision"])
    assert multimodal is not None
    assert ref is not None
    assert ref.process_mode == "model_direct"


@pytest.mark.asyncio
async def test_file_url_image_with_vision_forced_sandbox():
    """file_url + .png + vision：当前守卫仅放行 image_url 直接消费，
    file_url 一律强制沙箱（由工具消费），避免非标准媒体协议硬塞模型。"""
    inp = {
        "type": "file_url",
        "file_url": {"url": "gyra-fs://_/bk/id7", "file_name": "scene.png"},
    }
    multimodal, ref, err = await process_user_input_file(inp, capabilities=["vision"])
    assert multimodal is None
    assert ref is not None
    assert ref.process_mode == "sandbox_tool"


@pytest.mark.asyncio
async def test_pdf_defaults_to_sandbox_without_caps():
    """默认配置下 .pdf → SANDBOX_TOOL。"""
    multimodal, ref, err = await process_user_input_file(_image_url_input("r.pdf"))
    assert multimodal is None
    assert ref is not None


def test_looks_like_image_helper():
    assert looks_like_image("a.png", None) is True
    assert looks_like_image("a.JPEG", None) is True
    assert looks_like_image("abc", "image/jpeg") is True
    assert looks_like_image("r.pdf", "application/pdf") is False
    assert looks_like_image("abc123", None) is False
    assert looks_like_image("abc", "application/octet-stream") is False
    assert looks_like_image("", None) is False