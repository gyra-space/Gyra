"""Google Multimedia Provider.

Merges image generation (Nano Banana / Gemini 2.5 Flash Image) under a single
vendor protocol ``google_multimedia``. Video generation is not supported by
Google's current media API shape, so ``generate_video`` raises NotImplementedError.
"""

import logging
from typing import Any, List, Optional, Set

from gyra.agent.util.media_gen.base import (
    MediaGenProvider,
    MediaGenResult,
)
from gyra.agent.util.media_gen.google_banana_provider import GoogleBananaProvider
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)


@MediaGenProviderRegistry.register(
    protocol="google_multimedia", env_key="GOOGLE_API_KEY"
)
class GoogleMultimediaProvider(MediaGenProvider):
    """Google 多媒体 provider：图片走 Nano Banana。"""

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._image = GoogleBananaProvider(
            api_key=api_key, base_url=base_url, **kwargs
        )

    def supported_image_models(self) -> List[str]:
        return self._image.supported_image_models()

    def supported_video_models(self) -> List[str]:
        return []

    def supported_inputs(self, model: str, kind: str = "") -> Set[str]:
        """Google 合并协议：仅图片(Nano Banana 支持图片编辑 image_url)。"""
        return self._image.supported_inputs(model, kind)

    async def generate_image(
        self, prompt: str, model: str, **kwargs: Any
    ) -> MediaGenResult:
        return await self._image.generate_image(prompt, model, **kwargs)

    async def generate_video(
        self, prompt: str, model: str, **kwargs: Any
    ) -> MediaGenResult:
        raise NotImplementedError(
            "Google 多媒体 provider 当前不支持视频生成"
        )