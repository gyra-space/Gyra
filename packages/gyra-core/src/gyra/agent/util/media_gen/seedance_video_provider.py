"""Volcano Engine Seedance (豆包视频生成) Video Generation Provider.

Implements video generation via the Volcano Engine Ark API, supporting:
- doubao-seedance-2-0-250428 (Seedance 2.0, newest)
- doubao-seedance-1-5-pro-251215 (Seedance 1.5 Pro)
- doubao-seedance-1-0-pro-250428 (Seedance 1.0 Pro)
- doubao-seedance-1-0-pro-fast-250428 (Seedance 1.0 Pro Fast)

API docs: https://www.volcengine.com/docs/82379/1520757
"""

import asyncio
import logging
from typing import Any, List, Optional, Set

from gyra.agent.util.media_gen.base import (
    MediaGenProvider,
    MediaGenResult,
    MediaSubmission,
    download_media_with_retry,
    resolve_media_image_url,
)
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)

# Model names are free-form (protocol-based routing); passed through to the
# Ark API. New Seedance model versions work without code changes.

# Default API endpoints
_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_CREATE_TASK_ENDPOINT = "/contents/generations/tasks"
_QUERY_TASK_ENDPOINT = "/contents/generations/tasks/{task_id}"

# Supported resolutions
_SUPPORTED_RESOLUTIONS = {"480p", "720p", "1080p", "4k"}

# Supported aspect ratios
_SUPPORTED_RATIOS = {"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}

# 各 Seedance 模型族支持的视频时长范围（秒）。模型名按路由透传，Ark 对 duration 的
# 合法区间随模型版本不同：Seedance 1.0 Pro / Pro Fast 为 [2,12]，1.5 Pro 为 [4,12]，
# 2.0 系列（含 mini/fast）为 [4,15]。请求时长超出区间会触发 InvalidParameter，因此
# 在提交前先归一到区间内（就近取值），避免请求直接失败。未命中版本时按 2.0 系列兜底。
_SEEDANCE_1_0_DURATION_RANGE = (2, 12)
_SEEDANCE_1_5_DURATION_RANGE = (4, 12)
_SEEDANCE_2_0_DURATION_RANGE = (4, 15)


def _duration_range_for(model: str) -> tuple[int, int]:
    """按模型名推断该 Seedance 模型族支持的时长范围 (min, max)。"""
    m = (model or "").lower()
    if "1-0" in m or "1.0" in m:
        return _SEEDANCE_1_0_DURATION_RANGE
    if "1-5" in m or "1.5" in m:
        return _SEEDANCE_1_5_DURATION_RANGE
    return _SEEDANCE_2_0_DURATION_RANGE


def _normalize_duration(model: str, duration: Any) -> int:
    """规整 duration 到模型合法区间；越界时就近取值并记 warning。"""
    if duration is None or isinstance(duration, bool):
        duration = 5
    elif not isinstance(duration, int):
        duration = int(duration)
    lo, hi = _duration_range_for(model)
    if duration < lo:
        logger.warning(
            f"[SeedanceVideoProvider] duration={duration}s is below model {model} "
            f"minimum {lo}s; clamped to {lo}s"
        )
        return lo
    if duration > hi:
        logger.warning(
            f"[SeedanceVideoProvider] duration={duration}s is above model {model} "
            f"maximum {hi}s; clamped to {hi}s"
        )
        return hi
    return duration


def _extract_video_url(content: Any) -> str:
    r"""从任务查询响应中提取视频 URL，兼容两种 ``content`` 结构。

    - dict: Volcano Ark 实际返回 ``content`` 为对象，``video_url`` 是字符串
      （个别版本可能是 ``{"url": ...}``）。
    - list: 兼容旧格式，元素形如
      ``{"type": "video_url", "video_url": {"url": "..."}}``。

    Args:
        content: 响应里的 ``content`` 字段。

    Returns:
        视频 URL 字符串；找不到时返回空字符串。
    """
    if isinstance(content, dict):
        url = content.get("video_url")
        if isinstance(url, str) and url:
            return url
        if isinstance(url, dict):
            nested = url.get("url")
            if isinstance(nested, str) and nested:
                return nested
        return ""
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "video_url":
                video_url_obj = item.get("video_url")
                if isinstance(video_url_obj, dict):
                    url = video_url_obj.get("url")
                    if url:
                        return url
                elif isinstance(video_url_obj, str) and video_url_obj:
                    return video_url_obj
    return ""


@MediaGenProviderRegistry.register(protocol="volcengine_video", env_key="ARK_API_KEY")
class SeedanceVideoProvider(MediaGenProvider):
    """Volcano Engine Seedance (豆包) video generation provider.

    Uses the Ark API with async task pattern: submit -> poll -> download.
    Supports text-to-video and image-to-video generation. Model name is
    free-form (passed through to the Ark API).
    """

    def supported_image_models(self) -> List[str]:
        return []

    def supported_video_models(self) -> List[str]:
        return []

    def supported_inputs(self, model: str, kind: str = "") -> Set[str]:
        """Seedance 支持首帧(图生视频 i2v)与首尾帧生视频；fast 变体不支持首尾帧。
        参考图(r2v)不支持 —— 传入 reference_images 会被显式拒绝，而非静默忽略。"""
        supported = {"image_url"}
        if "fast" not in (model or "").lower():
            supported.add("image_url_last")
        return supported

    async def generate_image(
        self,
        prompt: str,
        model: str = "",
        **kwargs: Any,
    ) -> MediaGenResult:
        raise NotImplementedError(
            "Seedance video provider does not support image generation"
        )

    async def generate_video(
        self,
        prompt: str,
        model: str = "doubao-seedance-1-0-pro-250428",
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate a video using Volcano Engine Seedance API.
        Args:
            prompt: Text description of the video (supports Chinese & English).
            model: Model to use (doubao-seedance-2-0-250428, doubao-seedance-1-5-pro-251215, etc.).
            **kwargs: Additional params:
                - duration: Video duration in seconds (default 5; range depends on the
                  model family: Seedance 2.0 系列 [4,15]，1.5 Pro [4,12]，
                  1.0 Pro/Pro Fast [2,12]；超出区间将自动就近规整).
                - resolution: "480p", "720p", "1080p", "4k" (default "720p").
                - aspect_ratio: "16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"
                  (default "16:9").
                - seed: Random seed for reproducibility.
                - watermark: Whether to add watermark (default False).
                - camera_fixed: Whether to fix camera (default False).
                - generate_audio: Whether to generate audio (default True for 2.0/1.5 Pro).
                - image_url: First frame image URL for image-to-video generation.
                - image_url_last: Last frame image URL for first-last-frame video generation.
                - timeout: Max wait time in seconds (default 600).
        """
        self.validate_inputs(model, "video", kwargs)
        submission = await self.submit_video(prompt, model, **kwargs)
        try:
            return await submission.complete()
        except TimeoutError as e:
            # 提交已成功仅轮询超时：携带 submission 上抛，由调用方转后台续等
            # 同一 task（provider 侧仍在运行，重复提交会重复扣费）
            from .base import MediaPollTimeoutError

            raise MediaPollTimeoutError(str(e), submission=submission) from e

    async def submit_video(
        self,
        prompt: str,
        model: str = "doubao-seedance-1-0-pro-250428",
        **kwargs: Any,
    ) -> MediaSubmission:
        """Submit a Seedance video task; return a resumable MediaSubmission.

        The HTTP submit runs synchronously so immediate errors (auth, bad
        params) surface now. Polling + download is deferred to
        ``submission.complete()`` for background execution via AsyncTaskManager.
        """
        self.validate_inputs(model, "video", kwargs)
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx package is required for Seedance video generation. "
                "Install with: pip install httpx"
            )

        timeout = kwargs.get("timeout", 600)
        base_url = self.base_url or _DEFAULT_BASE_URL

        duration = _normalize_duration(model, kwargs.get("duration", 5))
        resolution = kwargs.get("resolution", "720p")
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        seed = kwargs.get("seed")
        watermark = kwargs.get("watermark", False)
        camera_fixed = kwargs.get("camera_fixed", False)
        generate_audio = kwargs.get("generate_audio")
        # 首帧/尾帧可能是内部 AFS URI(gyra-fs://)或文件服务相对路径，必须转成
        # Ark 可抓取的公网 URL 或 base64 data URI，否则会触发 InvalidParameter。
        image_url = resolve_media_image_url(kwargs.get("image_url"))
        image_url_last = resolve_media_image_url(kwargs.get("image_url_last"))

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build content array
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        # Add first frame image if provided (image-to-video)
        if image_url:
            image_obj: dict[str, Any] = {
                "type": "image_url",
                "image_url": {"url": image_url},
            }
            if image_url_last:
                # First + last frame mode
                image_obj["role"] = "first_frame"
                content.append(image_obj)
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url_last},
                        "role": "last_frame",
                    }
                )
            else:
                # First frame only mode
                image_obj["role"] = "first_frame"
                content.append(image_obj)

        # Build request body
        body: dict[str, Any] = {
            "model": model,
            "content": content,
            "resolution": resolution,
            "ratio": aspect_ratio,
            "duration": duration,
            "watermark": watermark,
            "camera_fixed": camera_fixed,
        }

        # Optional parameters
        if seed is not None:
            body["seed"] = seed
        if generate_audio is not None:
            body["generate_audio"] = generate_audio

        logger.info(
            f"[SeedanceVideoProvider] Submitting video job: model={model}, "
            f"duration={duration}s, resolution={resolution}, ratio={aspect_ratio}, "
            f"image_to_video={'yes' if image_url else 'no'}"
        )

        # Submit (short-lived client; poll/download use their own).
        async with httpx.AsyncClient(timeout=timeout) as client:
            create_url = f"{base_url}{_CREATE_TASK_ENDPOINT}"
            logger.info(
                f"[SeedanceVideoProvider] Request POST {create_url} body={body}"
            )
            submit_resp = await client.post(create_url, headers=headers, json=body)
            if submit_resp.is_error:
                # Surface Ark's error body (code/message) instead of the bare
                # status line httpx would produce.
                try:
                    err = submit_resp.json()
                except ValueError:
                    err = None
                if not isinstance(err, dict):
                    err = {}
                code = err.get("code", "")
                msg = (
                    err.get("message", "")
                    or err.get("msg", "")
                    or submit_resp.text[:200]
                )
                raise RuntimeError(
                    f"Seedance request failed (HTTP {submit_resp.status_code}"
                    f"{f' {code}' if code else ''}): {msg}"
                )
            job = submit_resp.json()
            if not isinstance(job, dict):
                raise RuntimeError(
                    f"Seedance API returned an unexpected non-dict response "
                    f"(type={type(job).__name__}): {submit_resp.text[:200]}"
                )

        task_id = job.get("id")
        if not task_id:
            raise ValueError(f"Seedance API returned no task ID: {job}")

        logger.info(f"[SeedanceVideoProvider] Task created: {task_id}")

        async def _complete() -> MediaGenResult:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Poll until complete
                video_url = await self._poll_task(
                    client, base_url, task_id, timeout
                )
                # Download (validated: storage may transiently return an
                # XML error body right after task completion)
                logger.info(
                    f"[SeedanceVideoProvider] Downloading video from {video_url}"
                )
                video_data = await download_media_with_retry(
                    client, video_url, kind="video", provider="seedance"
                )

            metadata: dict[str, Any] = {
                "model": model,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "task_id": task_id,
                "provider": "seedance",
                "video_url": video_url,
            }
            if seed is not None:
                metadata["seed"] = seed
            if image_url:
                metadata["image_to_video"] = True

            return MediaGenResult(
                data=video_data,
                format="mp4",
                mime_type="video/mp4",
                duration_seconds=float(duration),
                metadata=metadata,
            )

        return MediaSubmission(
            task_id=task_id,
            provider="seedance",
            model=model,
            complete=_complete,
            metadata={"task_id": task_id, "model": model},
        )

    async def resume_task(
        self,
        task_id: str,
        model: str = "doubao-seedance-1-0-pro-250428",
        **kwargs: Any,
    ) -> MediaSubmission:
        """按已有 task_id 召回：只轮询 + 下载，不重新提交（不重复扣费）。"""
        import httpx

        timeout = kwargs.get("timeout", 600)
        base_url = self.base_url or _DEFAULT_BASE_URL

        async def _complete() -> MediaGenResult:
            async with httpx.AsyncClient(timeout=timeout) as client:
                video_url = await self._poll_task(
                    client, base_url, task_id, timeout
                )
                logger.info(
                    f"[SeedanceVideoProvider] Recalling video from {video_url}"
                )
                video_data = await download_media_with_retry(
                    client, video_url, kind="video", provider="seedance"
                )

            return MediaGenResult(
                data=video_data,
                format="mp4",
                mime_type="video/mp4",
                metadata={
                    "model": model,
                    "task_id": task_id,
                    "provider": "seedance",
                    "video_url": video_url,
                    "recalled": True,
                },
            )

        return MediaSubmission(
            task_id=task_id,
            provider="seedance",
            model=model,
            complete=_complete,
            metadata={"task_id": task_id, "model": model},
        )

    async def _poll_task(
        self,
        client: Any,
        base_url: str,
        task_id: str,
        timeout: int,
    ) -> str:
        """Poll Seedance task until completion, return video URL.

        Args:
            client: httpx.AsyncClient instance.
            base_url: Ark API base URL.
            task_id: Task ID to poll.
            timeout: Maximum wait time in seconds.

        Returns:
            Video URL string.
        """
        query_url = f"{base_url}{_QUERY_TASK_ENDPOINT.format(task_id=task_id)}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        poll_interval = 10  # seconds (video generation takes longer)
        elapsed = 0

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            resp = await client.get(query_url, headers=headers)
            resp.raise_for_status()
            try:
                raw = resp.json()
            except ValueError:
                raise RuntimeError(
                    f"Seedance task query returned non-JSON body "
                    f"(task_id={task_id}): {resp.text[:200]}"
                )
            if not isinstance(raw, dict):
                raise RuntimeError(
                    f"Seedance task query returned non-dict JSON "
                    f"(type={type(raw).__name__}, task_id={task_id}): "
                    f"{resp.text[:200]}"
                )
            status_data = raw

            status = status_data.get("status", "")

            if status == "succeeded":
                # Extract video URL from content (dict or list).
                # Volcano Ark returns content as a dict: {'video_url': '...'}.
                url = _extract_video_url(status_data.get("content"))
                if url:
                    return url

                # Fallback: try output field
                output = status_data.get("output")
                if isinstance(output, dict):
                    url = output.get("url")
                    if url:
                        return url

                raise ValueError(
                    f"Task succeeded but no video URL found: {status_data}"
                )

            elif status in ("failed", "cancelled", "expired"):
                error = status_data.get("error", {})
                error_msg = ""
                if isinstance(error, dict):
                    error_msg = error.get("message", "")
                if not error_msg:
                    error_msg = status_data.get("message", "Unknown error")
                raise RuntimeError(
                    f"Seedance video generation failed (status={status}): {error_msg}"
                )

            logger.debug(
                f"[SeedanceVideoProvider] Task {task_id} status: {status} "
                f"({elapsed}s elapsed)"
            )

        raise TimeoutError(
            f"Seedance video generation timed out after {timeout}s "
            f"(task_id={task_id})"
        )
