"""Alibaba Cloud DashScope (百炼) Multimedia Provider.

Merges image generation (Wanxiang / 千问图像) and video generation
(HappyHorse) under a single vendor protocol ``dashscope_multimedia``.
The caller routes by the model's ``model_type`` (image/video) to the right
method (generate_image / generate_video); this provider delegates to the
corresponding specialized provider.
"""

import logging
from typing import Any, List, Optional

from gyra.agent.util.media_gen.base import (
    MediaGenProvider,
    MediaGenResult,
    MediaSubmission,
)
from gyra.agent.util.media_gen.dashscope_audio_provider import DashScopeAudioProvider
from gyra.agent.util.media_gen.happyhorse_video_provider import HappyHorseVideoProvider
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry
from gyra.agent.util.media_gen.wanxiang_image_provider import WanxiangImageProvider

logger = logging.getLogger(__name__)


@MediaGenProviderRegistry.register(
    protocol="dashscope_multimedia", env_key="DASHSCOPE_API_KEY"
)
class DashScopeMultimediaProvider(MediaGenProvider):
    """百炼多媒体 provider：图片走 Wanxiang/千问图像，视频走 HappyHorse。"""

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._image = WanxiangImageProvider(
            api_key=api_key, base_url=base_url, **kwargs
        )
        self._video = HappyHorseVideoProvider(
            api_key=api_key, base_url=base_url, **kwargs
        )
        self._audio = DashScopeAudioProvider(
            api_key=api_key, base_url=base_url, **kwargs
        )

    def supported_image_models(self) -> List[str]:
        return self._image.supported_image_models()

    def supported_video_models(self) -> List[str]:
        return self._video.supported_video_models()

    async def generate_image(
        self, prompt: str, model: str, **kwargs: Any
    ) -> MediaGenResult:
        return await self._image.generate_image(prompt, model, **kwargs)

    async def generate_video(
        self, prompt: str, model: str, **kwargs: Any
    ) -> MediaGenResult:
        return await self._video.generate_video(prompt, model, **kwargs)

    async def generate_audio(
        self, prompt: str, model: str, **kwargs: Any
    ) -> MediaGenResult:
        return await self._audio.generate_audio(prompt, model, **kwargs)

    async def submit_video(
        self, prompt: str, model: str, **kwargs: Any
    ) -> MediaSubmission:
        return await self._video.submit_video(prompt, model, **kwargs)

    async def resume_task(
        self, task_id: str, model: str, kind: str = "", **kwargs: Any
    ) -> MediaSubmission:
        # image+video 合并协议：按任务类型路由到正确的子 provider，避免图片召回
        # 误打到视频 provider（用 provider_task_id 轮询会查错厂商任务而失败）。
        # 单子类 provider 的 resume_task 均接受 **kwargs，kind 透传无害。
        if kind == "image":
            return await self._image.resume_task(task_id, model, **kwargs)
        return await self._video.resume_task(task_id, model, **kwargs)