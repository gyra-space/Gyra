"""Alibaba Cloud DashScope (百炼) TTS Audio Provider.

Non-realtime speech synthesis via the DashScope ``SpeeechSynthesizer`` HTTP
endpoint (``/api/v1/services/audio/tts/SpeechSynthesizer``). Supports
Qwen-Audio-TTS and CosyVoice models. Returns audio bytes directly in the
response body.

API docs: https://help.aliyun.com/zh/model-studio/non-realtime-cosyvoice-api/
"""

import logging
from typing import Any, List, Optional

import httpx

from gyra.agent.util.media_gen._dashscope_common import (
    normalize_base_url,
)
from gyra.agent.util.media_gen.base import MediaGenProvider, MediaGenResult
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"
_TTS_ENDPOINT = "/services/audio/tts/SpeechSynthesizer"

# format -> mime type
_FORMAT_MIME = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "opus": "audio/ogg",
    "pcm": "audio/wav",
}


@MediaGenProviderRegistry.register(protocol="dashscope_audio", env_key="DASHSCOPE_API_KEY")
class DashScopeAudioProvider(MediaGenProvider):
    """DashScope TTS provider (Qwen-Audio-TTS / CosyVoice)."""

    def supported_image_models(self) -> List[str]:
        return []

    def supported_video_models(self) -> List[str]:
        return []

    async def generate_audio(
        self,
        prompt: str,
        model: str = "qwen-audio-3.0-tts-flash",
        **kwargs: Any,
    ) -> MediaGenResult:
        """Synthesize speech from text using DashScope.

        Args:
            prompt: Text to speak.
            model: TTS model (qwen-audio-3.0-tts-flash / cosyvoice-v3.5-flash ...).
            **kwargs:
                - voice: 音色 (e.g. "longanhuan_v3.6")
                - format: "mp3" | "wav" | "opus" | "pcm" (default mp3)
                - sample_rate: 8000~48000 (default 24000)
                - volume: 0~100 (default 50)
                - rate: 0.5~2.0 (default 1.0)
                - bit_rate: 6~510 kbps (opus only)
                - pitch: 0.5~2.0 (default 1.0)
        """
        voice = kwargs.get("voice") or "longanhuan_v3.6"
        fmt = kwargs.get("format") or "mp3"

        payload: dict[str, Any] = {
            "model": model,
            "input": {
                "text": prompt,
                "voice": voice,
                "format": fmt,
            },
            "parameters": {},
        }
        if kwargs.get("sample_rate"):
            payload["input"]["sample_rate"] = int(kwargs["sample_rate"])
        for k in ("volume", "rate", "bit_rate", "pitch"):
            if kwargs.get(k) is not None:
                payload["parameters"][k] = kwargs[k]

        base_url = normalize_base_url(self.base_url or _DEFAULT_BASE_URL)
        url = f"{base_url}{_TTS_ENDPOINT}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        logger.info(f"[DashScopeAudioProvider] Synthesizing audio: model={model}, voice={voice}")

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            # DashScope signals errors with a JSON body even on 4xx.
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("audio/") and "application/json" in content_type:
                try:
                    err = resp.json()
                    code = err.get("code")
                    if code:
                        raise RuntimeError(
                            f"DashScope TTS failed ({code}): {err.get('message', '')}"
                        )
                except ValueError:
                    pass
            resp.raise_for_status()
            data = resp.content

        if not data:
            raise ValueError("DashScope TTS returned empty audio data")

        mime = _FORMAT_MIME.get(fmt, "audio/mpeg")
        return MediaGenResult(
            data=data,
            format=fmt,
            mime_type=mime,
            metadata={"model": model, "voice": voice, "format": fmt},
        )