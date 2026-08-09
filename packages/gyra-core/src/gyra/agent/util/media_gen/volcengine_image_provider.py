"""Volcano Engine Seedream (豆包图像) Image Generation Provider.

Implements image generation via the Volcano Engine Ark Images API
(sync ``/images/generations`` endpoint), supporting:
- doubao-seedream-5-0-260128 (Seedream 5.0)
- doubao-seedream-4-0-250828 (Seedream 4.0)
- doubao-seedream-3-0-t2i-250415 (Seedream 3.0)

API reference: https://www.volcengine.com/docs/82379/1541523
Endpoint is synchronous -- the response returns image URL(s) directly
(no task submit / poll round-trip).
"""

import logging
from typing import Any, List, Optional

from gyra.agent.util.media_gen.base import (
    MediaGenProvider,
    MediaGenResult,
    download_media_with_retry,
)
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)

# Default API endpoints
_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_IMAGE_ENDPOINT = "/images/generations"

# Seedream size keywords -> pixel dimensions (for metadata). The API accepts
# "1K" / "2K" / "4K" (and 16:9 / 4:3 / 1:1 variants). Pass through untouched.
_SEEDREAM_SIZES = {"1K", "2K", "4K"}


@MediaGenProviderRegistry.register(protocol="volcengine_image", env_key="ARK_API_KEY")
class VolcengineImageProvider(MediaGenProvider):
    """Volcano Engine Seedream (豆包图像) image generation provider.

    Model name is free-form (passed through to the Ark API). Uses the
    synchronous ``/images/generations`` endpoint with ``response_format: url``.
    """

    def supported_image_models(self) -> List[str]:
        return []

    def supported_video_models(self) -> List[str]:
        return []

    async def generate_image(
        self,
        prompt: str,
        model: str = "doubao-seedream-5-0-260128",
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate an image using Volcano Engine Seedream API.

        Args:
            prompt: Text description of the image (supports Chinese & English).
            model: Model to use (doubao-seedream-5-0-260128, etc.).
            **kwargs: Additional params:
                - size: "1K", "2K", "4K" (or pixel dims like "1024x1024",
                  mapped to the nearest Seedream keyword).
                - watermark: Whether to add a watermark (default False).
                - seed: Random seed for reproducibility.
                - timeout: Max wait time in seconds (default 180).
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx package is required for Seedream image generation. "
                "Install with: pip install httpx"
            )

        timeout = kwargs.get("timeout", 180)
        base_url = self.base_url or _DEFAULT_BASE_URL

        size = self._normalize_size(kwargs.get("size", "2K"))
        watermark = kwargs.get("watermark", False)
        seed = kwargs.get("seed")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "sequential_image_generation": "disabled",
            "response_format": "url",
            "size": size,
            "stream": False,
            "watermark": watermark,
        }
        if seed is not None:
            body["seed"] = seed

        logger.info(
            f"[VolcengineImageProvider] Generating image: model={model}, "
            f"size={size}, watermark={watermark}"
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            create_url = f"{base_url}{_IMAGE_ENDPOINT}"
            logger.info(
                f"[VolcengineImageProvider] Request POST {create_url} body={body}"
            )
            resp = await client.post(create_url, headers=headers, json=body)
            if resp.is_error:
                try:
                    err = resp.json()
                except ValueError:
                    err = {}
                code = err.get("code", "")
                msg = (
                    err.get("message", "")
                    or err.get("msg", "")
                    or resp.text[:200]
                )
                raise RuntimeError(
                    f"Seedream request failed (HTTP {resp.status_code}"
                    f"{f' {code}' if code else ''}): {msg}"
                )
            result = resp.json()

            image_url = self._extract_image_url(result)
            logger.info(
                f"[VolcengineImageProvider] Downloading image from {image_url}"
            )
            image_data = await download_media_with_retry(
                client, image_url, kind="image", provider="seedream"
            )

        width, height = self._parse_dimensions(size)

        return MediaGenResult(
            data=image_data,
            format="png",
            mime_type="image/png",
            width=width,
            height=height,
            metadata={
                "model": model,
                "size": size,
                "provider": "seedream",
                "image_url": image_url,
            },
        )

    async def generate_video(
        self,
        prompt: str,
        model: str = "",
        **kwargs: Any,
    ) -> MediaGenResult:
        raise NotImplementedError(
            "Seedream image provider does not support video generation"
        )

    @staticmethod
    def _extract_image_url(data: dict) -> str:
        """Extract the image URL from a Seedream (images/generations) response.

        The response shape is ``{"data": [{"url": "..."}, ...]}``.
        """
        data_list = data.get("data") or []
        if isinstance(data_list, list):
            for item in data_list:
                if isinstance(item, dict):
                    url = item.get("url") or item.get("image_url")
                    if url:
                        return url
        # Fallbacks
        images = data.get("images")
        if isinstance(images, list) and images:
            return str(images[0])
        raise ValueError(f"Seedream response has no image URL: {data}")

    @staticmethod
    def _normalize_size(size: str) -> str:
        """Map pixel dimensions to Seedream size keywords.

        Seedream accepts "1K" / "2K" / "4K". If the caller passes pixel
        dimensions (e.g. "1024x1024"), map to the nearest keyword; otherwise
        pass through.
        """
        s = (size or "").strip().lower()
        if s in {"1k", "2k", "4k"}:
            return s.upper()
        if "x" in s:
            try:
                w = int(s.split("x")[0])
            except ValueError:
                return size
            if w >= 2048:
                return "4K"
            if w >= 1024:
                return "2K"
            return "1K"
        return size

    @staticmethod
    def _parse_dimensions(size: str) -> tuple[Optional[int], Optional[int]]:
        """Return (width, height) for a Seedream size keyword, or None."""
        mapping = {
            "1K": (1024, 1024),
            "2K": (2048, 2048),
            "4K": (4096, 4096),
        }
        return mapping.get(size, (None, None))