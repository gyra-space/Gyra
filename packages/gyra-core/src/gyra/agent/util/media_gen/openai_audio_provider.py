"""OpenAI Audio (TTS) Provider.

Text-to-speech via the OpenAI Audio Speech API (``/v1/audio/speech``).
Model name is free-form (tts-1 / tts-1-hd / gpt-4o-mini-tts).
"""

import logging
from typing import Any, List, Optional

from gyra.agent.util.media_gen.base import MediaGenProvider, MediaGenResult
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)


@MediaGenProviderRegistry.register(protocol="openai_audio", env_key="OPENAI_API_KEY")
class OpenAIAudioProvider(MediaGenProvider):
    """OpenAI TTS provider. Model name is free-form."""

    def supported_image_models(self) -> List[str]:
        return []

    def supported_video_models(self) -> List[str]:
        return []

    async def generate_audio(
        self,
        prompt: str,
        model: str = "tts-1",
        **kwargs: Any,
    ) -> MediaGenResult:
        """Synthesize speech from text using OpenAI Audio Speech API.

        Args:
            prompt: Text to speak aloud.
            model: Model to use (tts-1 / tts-1-hd / gpt-4o-mini-tts).
            **kwargs:
                - voice: "alloy" | "echo" | "fable" | "onyx" | "nova" | "shimmer"
                - response_format: "mp3" | "opus" | "aac" | "flac" | "wav" | "pcm"
                - speed: 0.25 ~ 4.0
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for TTS generation. "
                "Install with: pip install openai"
            )

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = AsyncOpenAI(**client_kwargs)

        voice = kwargs.get("voice", "alloy")
        fmt = kwargs.get("response_format", "mp3")
        speed = kwargs.get("speed", 1.0)

        logger.info(f"[OpenAIAudioProvider] Synthesizing audio: model={model}, voice={voice}")

        response = await client.audio.speech.create(
            model=model,
            input=prompt,
            voice=voice,
            response_format=fmt,
            speed=speed,
        )

        data = response.read()
        if not data:
            raise ValueError("OpenAI returned empty audio data")

        mime = {
            "mp3": "audio/mpeg",
            "opus": "audio/ogg",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/wav",
        }.get(fmt, "audio/mpeg")

        metadata: dict[str, Any] = {
            "model": model,
            "voice": voice,
            "format": fmt,
        }

        return MediaGenResult(
            data=data,
            format=fmt,
            mime_type=mime,
            metadata=metadata,
        )