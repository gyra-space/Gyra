"""OpenAI Multimedia Provider.

Merges image generation (DALL-E) and video generation (Sora) under a single
vendor protocol ``openai_multimedia``. The caller routes by the model's
``model_type`` (image/video) to the right method; this provider delegates to
the corresponding specialized provider.
"""

import logging
from typing import Any, List, Optional

from gyra.agent.util.media_gen.base import (
    MediaGenProvider,
    MediaGenResult,
    MediaSubmission,
)
from gyra.agent.util.media_gen.openai_audio_provider import OpenAIAudioProvider
from gyra.agent.util.media_gen.openai_image_provider import OpenAIImageProvider
from gyra.agent.util.media_gen.openai_video_provider import OpenAIVideoProvider
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)


@MediaGenProviderRegistry.register(
    protocol="openai_multimedia", env_key="OPENAI_API_KEY"
)
class OpenAIMultimediaProvider(MediaGenProvider):
    """OpenAI 多媒体 provider：图片走 DALL-E，视频走 Sora。"""

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._image = OpenAIImageProvider(
            api_key=api_key, base_url=base_url, **kwargs
        )
        self._video = OpenAIVideoProvider(
            api_key=api_key, base_url=base_url, **kwargs
        )
        self._audio = OpenAIAudioProvider(
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