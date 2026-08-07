"""Media Generation Provider base classes.

Provides abstract interfaces for image/video generation providers
(DALL-E, Stable Diffusion, Sora, etc.).
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MediaGenResult:
    """Result of a media generation call."""

    data: bytes
    format: str  # "png", "jpg", "mp4", "webm"
    mime_type: str  # "image/png", "video/mp4"
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None  # for video
    metadata: Dict[str, Any] = field(default_factory=dict)


class MediaPollTimeoutError(TimeoutError):
    """媒体生成任务已提交成功、但本地轮询超时。

    与生成失败不同：provider 侧任务通常仍在运行，**不应重新提交**（重复扣费）。
    携带 ``submission`` 时调用方可把同一 task 转后台继续轮询+下载。
    """

    def __init__(self, message: str, submission: Optional["MediaSubmission"] = None):
        super().__init__(message)
        self.submission = submission


@dataclass
class MediaSubmission:
    """A submitted async media-generation task, resumable for completion.

    Returned by a provider's ``submit_*`` method once the HTTP submit succeeds
    and a task_id is known. ``complete`` is a no-arg coroutine that polls the
    task and downloads the result into a :class:`MediaGenResult`. This split
    lets the tool submit synchronously (catching immediate errors like 403)
    while polling/downloading in the background via AsyncTaskManager.

    Attributes:
        task_id: Provider task id returned by the submit endpoint.
        provider: Provider name (e.g. "happyhorse", "seedance").
        model: Model name.
        complete: ``Callable[[], Awaitable[MediaGenResult]]`` -- poll + download.
        metadata: Extra info (task_id, scenario, ...) for the eventual result.
    """

    task_id: str
    provider: str
    model: str
    complete: Any  # Callable[[], Awaitable[MediaGenResult]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MediaGenProvider(ABC):
    """Abstract base class for media generation providers."""

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.extra_kwargs = kwargs

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: str,
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate an image from a text prompt."""

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        model: str,
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate a video from a text prompt."""

    @abstractmethod
    def supported_image_models(self) -> List[str]:
        """List supported image generation models."""

    @abstractmethod
    def supported_video_models(self) -> List[str]:
        """List supported video generation models."""


# ---------------------------------------------------------------------------
# Validated media download
# ---------------------------------------------------------------------------
#
# Providers receive a signed result URL (usually Alibaba OSS accelerate) and
# download the payload. Right after a task completes, the storage endpoint
# can transiently return an XML error body (e.g. ``SignatureDoesNotMatch``)
# with an HTTP 200 status while the object is still propagating. A bare
# ``raise_for_status()`` cannot catch that -- the error XML would be saved
# as the .png/.mp4 payload and the delivered file would be corrupt.
# ``download_media_with_retry`` validates the payload (error-body sniffing,
# Content-Type, magic bytes) and retries with backoff before giving up.


def _looks_like_error_payload(data: bytes) -> bool:
    """Detect XML error bodies (OSS/S3 style ``<Error><Code>...``)."""
    head = data[:1024].lstrip()
    return head.startswith(b"<?xml") and b"<Error>" in head and b"<Code>" in head


def _sniff_image(data: bytes) -> bool:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
        return True
    if data.startswith(b"\xff\xd8\xff"):  # JPEG
        return True
    if data.startswith((b"GIF87a", b"GIF89a")):  # GIF
        return True
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    head = data[:512].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return True
    if data.startswith(b"BM"):  # BMP
        return True
    return False


def _sniff_video(data: bytes) -> bool:
    if len(data) > 12 and data[4:8] == b"ftyp":  # MP4 / MOV / M4V
        return True
    if data.startswith(b"\x1a\x45\xdf\xa3"):  # WebM / MKV (EBML)
        return True
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"AVI ":
        return True
    if data.startswith(b"FLV\x01"):  # FLV
        return True
    if data.startswith(b"\x30\x26\xb2\x75\x8e\x66\xcf\x11"):  # ASF / WMV
        return True
    return False


def _validate_media_payload(
    data: bytes, content_type: str, kind: Literal["image", "video"]
) -> Tuple[bool, str]:
    """Return (is_valid, reason)."""
    if not data:
        return False, "empty response body"
    if _looks_like_error_payload(data):
        snippet = data[:200].decode("utf-8", errors="replace").replace("\n", " ")
        return False, f"storage returned an XML error body: {snippet}"
    ct = (content_type or "").split(";")[0].strip().lower()
    if kind == "image":
        if _sniff_image(data) or ct.startswith("image/"):
            return True, ""
        return False, f"payload is not a recognizable image (content-type={ct!r}, {len(data)} bytes)"
    # video: OSS may serve clips as application/octet-stream with
    # x-oss-force-download, so accept octet-stream when magic bytes match or
    # the payload is large enough to plausibly be media.
    if _sniff_video(data) or ct.startswith("video/"):
        return True, ""
    if ct in ("application/octet-stream", "binary/octet-stream", "") and len(data) > 100 * 1024:
        return True, ""
    return False, f"payload is not a recognizable video (content-type={ct!r}, {len(data)} bytes)"


async def download_media_with_retry(
    client: Any,
    url: str,
    *,
    kind: Literal["image", "video"],
    provider: str = "media",
    attempts: int = 4,
    retry_delay: float = 2.0,
) -> bytes:
    """Download a generated media payload with validation and retry.

    Args:
        client: httpx.AsyncClient instance.
        url: Signed result URL to download.
        kind: ``"image"`` or ``"video"`` -- selects validation rules.
        provider: Provider name for log/error messages.
        attempts: Total download attempts (first + retries).
        retry_delay: Base backoff seconds (scaled by attempt number).

    Returns:
        The validated media bytes.

    Raises:
        RuntimeError: no attempt produced a valid payload.
    """
    last_error = "unknown error"
    for attempt in range(1, attempts + 1):
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001 - retried below, surfaced after exhaustion
            last_error = f"HTTP error: {e}"
        else:
            ok, reason = _validate_media_payload(
                resp.content, resp.headers.get("content-type", ""), kind
            )
            if ok:
                return resp.content
            last_error = reason
        if attempt < attempts:
            delay = retry_delay * attempt
            logger.warning(
                f"[{provider}] {kind} download invalid ({last_error}); "
                f"retry {attempt}/{attempts - 1} in {delay:.0f}s"
            )
            await asyncio.sleep(delay)
    raise RuntimeError(
        f"{provider} failed to download a valid {kind} after {attempts} "
        f"attempts: {last_error}"
    )
