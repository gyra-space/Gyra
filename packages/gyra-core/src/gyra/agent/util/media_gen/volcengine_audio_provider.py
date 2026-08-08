"""Volcano Engine (火山) TTS Audio Provider.

Non-streaming audio generation via the Volcano Engine OpenSpeech HTTP API
(``POST https://openspeech.bytedance.com/api/v3/tts/create``), authenticated
with the ``X-Api-Key`` header. Supports the seed-audio model (seed-audio-1.0)
with a ``speaker`` voice id.

API docs: https://www.volcengine.com/docs/6561/2550782

Note: the OpenSpeech TTS host / auth differ from the Ark content-generation
host (``ark.cn-beijing.volces.com`` + ``ARK_API_KEY``). The api_key passed in
here is the OpenSpeech ``X-Api-Key`` (falls back to volcengine env vars).
"""

import base64
import json
import logging
from typing import Any, List, Optional

import httpx

from gyra.agent.util.media_gen.base import MediaGenProvider, MediaGenResult
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://openspeech.bytedance.com"
_TTS_ENDPOINT = "/api/v3/tts/create"


@MediaGenProviderRegistry.register(
    protocol="volcengine_audio", env_key="VOLC_OPENSPEECH_API_KEY"
)
class VolcengineAudioProvider(MediaGenProvider):
    """Volcano Engine TTS provider (seed-audio)."""

    def supported_image_models(self) -> List[str]:
        return []

    def supported_video_models(self) -> List[str]:
        return []

    async def generate_audio(
        self,
        prompt: str,
        model: str = "seed-audio-1.0",
        **kwargs: Any,
    ) -> MediaGenResult:
        """Synthesize speech from text using Volcano OpenSpeech.

        Args:
            prompt: Text to speak.
            model: TTS model (seed-audio-1.0).
            **kwargs:
                - speaker / voice: 音色ID (豆包语音合成模型2.0 音色)
                - format: "mp3" | "wav" | "pcm" | "ogg_opus" (default mp3)
                - sample_rate: 8000~48000 (default 24000)
                - speech_rate: -50~100 (default 0)
                - loudness_rate: -50~100 (default 0)
                - pitch_rate: -12~12 (default 0)
        """
        speaker = kwargs.get("speaker") or kwargs.get("voice") or ""
        fmt = kwargs.get("format") or "mp3"

        payload: dict[str, Any] = {
            "model": model,
            "text_prompt": prompt,
            "audio_config": {
                "format": fmt,
                "sample_rate": int(kwargs.get("sample_rate") or 24000),
            },
        }
        if speaker:
            payload["speaker"] = speaker
        for k in ("speech_rate", "loudness_rate", "pitch_rate"):
            if kwargs.get(k) is not None:
                payload["audio_config"][k] = int(kwargs[k])

        base_url = (self.base_url or _DEFAULT_BASE_URL).rstrip("/")
        if base_url.endswith("/api/v3"):
            base_url = _DEFAULT_BASE_URL
        url = f"{base_url}{_TTS_ENDPOINT}"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

        logger.info(f"[VolcengineAudioProvider] Synthesizing audio: model={model}, speaker={speaker}")

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # OpenSpeech returns base64 audio in the response body.
        raw = data.get("data") or data.get("audio_data") or ""
        if not raw:
            detail = data.get("message") or data.get("code") or data
            raise RuntimeError(f"Volcengine TTS returned no audio data: {detail}")
        audio_bytes = base64.b64decode(raw)

        mime = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "pcm": "audio/wav",
            "ogg_opus": "audio/ogg",
        }.get(fmt, "audio/mpeg")

        return MediaGenResult(
            data=audio_bytes,
            format=fmt,
            mime_type=mime,
            metadata={"model": model, "speaker": speaker, "format": fmt},
        )