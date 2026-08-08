"""Media Generation Provider Registry (vendor-level protocol).

Each **vendor protocol** maps to one merged provider class that routes by the
model's ``model_type`` (image/video/audio) to the right backend interface, e.g.
``volcengine_multimedia`` (Seedream image + Seedance video). Legacy fine-grained
protocols (``volcengine_video`` etc.) remain registered as aliases for backward
compatibility. Model names are **free-form**: the user configures a model name +
protocol in the model-config UI; the tool resolves the protocol by model name and
instantiates the matching provider class. No hardcoded model lists.

Availability is driven by ModelConfigCache (UI-configured media models), not by
code-declared model sets -- so new model versions work without code changes.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Type

from gyra.agent.util.media_gen.base import MediaGenProvider

logger = logging.getLogger(__name__)

MediaGenProviderFactory = ...  # placeholder for type clarity

# Env-var fallbacks per protocol (used when a UI-configured model has no api_key).
# 兼容保留细分协议的 env fallback（存量配置）；厂商级协议也已加入。
PROVIDER_ENV_FALLBACKS: Dict[str, List[str]] = {
    "dashscope_multimedia": ["DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY_2", "ALIBABA_API_KEY"],
    "dashscope_video": ["DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY_2", "ALIBABA_API_KEY"],
    "dashscope_image": ["DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY_2", "ALIBABA_API_KEY"],
    "dashscope_audio": ["DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY_2", "ALIBABA_API_KEY"],
    "volcengine_multimedia": ["ARK_API_KEY", "VOLC_API_KEY", "VOLCENGINE_API_KEY"],
    "volcengine_video": ["ARK_API_KEY", "VOLC_API_KEY", "VOLCENGINE_API_KEY"],
    "volcengine_image": ["ARK_API_KEY", "VOLC_API_KEY", "VOLCENGINE_API_KEY"],
    "volcengine_audio": ["VOLC_OPENSPEECH_API_KEY", "ARK_API_KEY", "VOLC_API_KEY"],
    "openai_multimedia": ["OPENAI_API_KEY"],
    "openai_image": ["OPENAI_API_KEY"],
    "openai_video": ["OPENAI_API_KEY"],
    "openai_audio": ["OPENAI_API_KEY"],
    "google_multimedia": ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"],
    "google_image": ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"],
}

# Human-readable labels for each protocol (UI/display).
PROTOCOL_LABELS: Dict[str, str] = {
    "dashscope_multimedia": "百炼多媒体",
    "dashscope_video": "百炼视频",
    "dashscope_image": "百炼图像",
    "volcengine_multimedia": "火山多媒体",
    "volcengine_video": "火山视频",
    "volcengine_image": "火山图像",
    "openai_multimedia": "OpenAI 多媒体",
    "openai_image": "OpenAI 图像",
    "openai_video": "OpenAI 视频",
    "google_multimedia": "Google 多媒体",
    "google_image": "Google 图像",
}


class MediaGenProviderRegistry:
    """Singleton registry mapping media-gen protocols to provider classes."""

    _instance: Optional["MediaGenProviderRegistry"] = None
    _protocol_providers: Dict[str, Type[MediaGenProvider]] = {}
    _protocol_env_keys: Dict[str, str] = {}

    # 默认模型（由系统配置 media_gen 注入；为 None 时工具回退到第一个可用模型）
    _default_video_model: Optional[str] = None
    _default_image_model: Optional[str] = None
    _default_audio_model: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── 默认模型配置 ───────────────────────────────────────────────

    @classmethod
    def set_default_models(
        cls,
        video_model: Optional[str] = None,
        image_model: Optional[str] = None,
        audio_model: Optional[str] = None,
    ) -> None:
        """设置媒体生成默认模型（由配置同步层调用）。"""
        if video_model is not None:
            cls._default_video_model = video_model or None
        if image_model is not None:
            cls._default_image_model = image_model or None
        if audio_model is not None:
            cls._default_audio_model = audio_model or None

    @classmethod
    def get_default_video_model(cls) -> Optional[str]:
        return cls._default_video_model

    @classmethod
    def get_default_image_model(cls) -> Optional[str]:
        return cls._default_image_model

    @classmethod
    def get_default_audio_model(cls) -> Optional[str]:
        return cls._default_audio_model

    @classmethod
    def get_first_usable_model(cls, capability: str) -> Optional[str]:
        """返回指定能力下第一个可用（已配置且有凭证）的模型名。

        Args:
            capability: "video" | "image" | "audio"
        """
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache
        except Exception as e:
            logger.debug(f"[MediaGenProviderRegistry] ModelConfigCache unavailable: {e}")
            return None

        for m in ModelConfigCache.get_media_models():
            if (
                ModelConfigCache.get_model_capability(m) == capability
                and cls._is_model_usable(m)
            ):
                return m["model"]
        return None

    @classmethod
    def get_usable_model_names(cls, capability: str) -> List[str]:
        """返回指定能力下所有可用（已配置且有凭证）的模型名列表。

        供多媒体 Agent「可用模型候选池」校验候选是否可用。
        """
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache
        except Exception as e:
            logger.debug(f"[MediaGenProviderRegistry] ModelConfigCache unavailable: {e}")
            return []

        return [
            m["model"]
            for m in ModelConfigCache.get_media_models()
            if ModelConfigCache.get_model_capability(m) == capability
            and cls._is_model_usable(m)
        ]

    @classmethod
    def register(
        cls,
        protocol: str,
        env_key: Optional[str] = None,
    ):
        """Register a media-gen provider class for a protocol.

        Used as a decorator. ``protocol`` is the API-shape identifier
        (e.g. ``dashscope_video``); ``env_key`` is the primary env var that
        holds the API key (used as fallback when UI config has no api_key).
        """

        def decorator(provider_cls: Type[MediaGenProvider]) -> Type[MediaGenProvider]:
            cls._protocol_providers[protocol] = provider_cls
            if env_key:
                cls._protocol_env_keys[protocol] = env_key
            logger.info(f"Registered media gen provider for protocol: {protocol}")
            return provider_cls

        return decorator

    @classmethod
    def get_supported_protocols(cls) -> List[str]:
        return list(cls._protocol_providers.keys())

    @classmethod
    def has_protocol(cls, protocol: str) -> bool:
        return protocol in cls._protocol_providers

    @classmethod
    def create_provider_by_protocol(
        cls,
        protocol: str,
        api_key: str = "",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[MediaGenProvider]:
        """Create a provider instance for a protocol."""
        provider_class = cls._protocol_providers.get(protocol)
        if not provider_class:
            return None
        return provider_class(api_key=api_key or "", base_url=base_url, **kwargs)

    @classmethod
    def get_env_api_key(cls, protocol: str) -> Optional[str]:
        """Return an API key from env vars for a protocol, or None.

        Checks the registered env_key first, then PROVIDER_ENV_FALLBACKS.
        """
        key = cls._protocol_env_keys.get(protocol)
        if key:
            val = os.environ.get(key)
            if val:
                return val
        for k in PROVIDER_ENV_FALLBACKS.get(protocol, []):
            val = os.environ.get(k)
            if val:
                return val
        return None

    @classmethod
    def _is_model_usable(cls, media_entry: Dict[str, Any]) -> bool:
        """A configured media model is usable if it has an api_key (UI) or an
        env-var key for its protocol."""
        if media_entry.get("api_key"):
            return True
        return cls.get_env_api_key(media_entry.get("protocol", "")) is not None

    @classmethod
    def format_available_summary(cls, capability: str = "all") -> str:
        """Human-readable summary of configured (and usable) media-gen models.

        Args:
            capability: "image" | "video" | "all". Image tools pass "image",
                video tools pass "video" so each tool only lists relevant models.
        """
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache
        except Exception as e:
            logger.debug(f"[MediaGenProviderRegistry] ModelConfigCache unavailable: {e}")
            return ""

        media = ModelConfigCache.get_media_models()
        if capability in ("image", "video"):
            media = [
                m for m in media
                if ModelConfigCache.get_model_capability(m) == capability
            ]

        usable = [m for m in media if cls._is_model_usable(m)]
        if not usable:
            return ""

        lines = ["**当前可用的媒体生成模型：**\n"]
        for m in sorted(usable, key=lambda x: x["model"]):
            label = PROTOCOL_LABELS.get(m["protocol"], m["protocol"])
            cap_tag = {
                "image": "图片",
                "video": "视频",
                "audio": "音频",
            }.get(ModelConfigCache.get_model_capability(m), "媒体")
            lines.append(f"- `{m['model']}` ({cap_tag}/{label})")
        return "\n".join(lines)
