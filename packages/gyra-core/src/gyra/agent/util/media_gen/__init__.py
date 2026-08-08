"""Media Generation Provider module.

Provides pluggable providers for image/video generation:
- OpenAI DALL-E (image) and Sora (video)
- Alibaba Cloud Wanxiang / 通义万相 (image)
- Alibaba Cloud HappyHorse (video: text-to-video / image-to-video / reference-to-video)
- Volcano Engine Seedance / 豆包 (video)
- Google Nano Banana / Gemini 2.5 Flash Image (image)
"""

from gyra.agent.util.media_gen.base import MediaGenProvider, MediaGenResult
from gyra.agent.util.media_gen.config import MediaGenConfig
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

# Auto-register built-in providers on import
from gyra.agent.util.media_gen import openai_image_provider  # noqa: F401
from gyra.agent.util.media_gen import openai_video_provider  # noqa: F401
from gyra.agent.util.media_gen import wanxiang_image_provider  # noqa: F401
from gyra.agent.util.media_gen import happyhorse_video_provider  # noqa: F401
from gyra.agent.util.media_gen import seedance_video_provider  # noqa: F401
from gyra.agent.util.media_gen import volcengine_image_provider  # noqa: F401
from gyra.agent.util.media_gen import google_banana_provider  # noqa: F401
# 音频(TTS) provider
from gyra.agent.util.media_gen import openai_audio_provider  # noqa: F401
from gyra.agent.util.media_gen import dashscope_audio_provider  # noqa: F401
from gyra.agent.util.media_gen import volcengine_audio_provider  # noqa: F401
# 厂商级合并 provider（按 model_type 路由图片/视频/音频）
from gyra.agent.util.media_gen import dashscope_multimedia_provider  # noqa: F401
from gyra.agent.util.media_gen import volcengine_multimedia_provider  # noqa: F401
from gyra.agent.util.media_gen import openai_multimedia_provider  # noqa: F401
from gyra.agent.util.media_gen import google_multimedia_provider  # noqa: F401

__all__ = [
    "MediaGenProvider",
    "MediaGenResult",
    "MediaGenConfig",
    "MediaGenProviderRegistry",
]
