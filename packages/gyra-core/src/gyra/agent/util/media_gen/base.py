"""Media Generation Provider base classes.

Provides abstract interfaces for image/video generation providers
(DALL-E, Stable Diffusion, Sora, etc.).
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def resolve_media_image_url(url: Any) -> str:
    """把媒体生成的图片输入（image_url / image_url_last / reference_images）里的
    内部文件地址转成外部模型可消费的**无鉴权公共预览地址**（签名公网 URL），
    兜底为 base64 data URI。

    媒体生成 provider（Seedance、HappyHorse、万相、Google/Nano-Banana 等）收到的
    图片输入可能是内部 Agent File System URI（``gyra-fs://...``，本地 fs 协议）或
    文件服务相对路径（``/api/v2/serve/file/files/...``）。外部图片/视频 API 无法抓取
    这两种地址，因此复用 LLM 链路已验证的存储改写逻辑：**优先**调用
    ``storage_client.get_public_url(metadata.uri)`` 产出无鉴权的签名公共预览地址
    （``/api/v2/serve/file/public/files/<bucket>/<file_id>?...token&expires``），
    仅当拿不到可访问的公网 URL（如 host 为本地/回环、未配置 public_url_secret）时
    **兜底**为图片字节 base64 data URI。任何失败都原样返回，调用方退化为原行为，
    而不是直接中断。

    Args:
        url: 原始图片地址（str）。None / 非字符串原样返回。

    Returns:
        改写后可被厂商 API 消费的 URL 字符串。
    """
    if not url or not isinstance(url, str):
        return url  # type: ignore[return-value]
    try:
        from gyra.agent.util.llm.provider._image_url_rewriter import (
            build_image_url_rewriter,
            resolve_storage_client,
        )

        rewriter = build_image_url_rewriter(resolve_storage_client())
        return rewriter(url)
    except Exception:  # noqa: BLE001 - 改写失败不阻断生成，维持原地址
        logger.debug(
            "[media_gen] media image URL rewrite failed; returning original url",
            exc_info=True,
        )
        return url


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

    async def generate_image(
        self,
        prompt: str,
        model: str,
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate an image from a text prompt.

        默认不支持。支持图片生成的 provider 需覆盖此方法。
        """
        raise NotImplementedError(
            f"{type(self).__name__} 不支持图片生成（generate_image 未实现）"
        )

    async def generate_video(
        self,
        prompt: str,
        model: str,
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate a video from a text prompt.

        默认不支持。支持视频生成的 provider 需覆盖此方法。
        """
        raise NotImplementedError(
            f"{type(self).__name__} 不支持视频生成（generate_video 未实现）"
        )

    @abstractmethod
    def supported_image_models(self) -> List[str]:
        """List supported image generation models."""

    @abstractmethod
    def supported_video_models(self) -> List[str]:
        """List supported video generation models."""

    def supported_inputs(self, model: str, kind: str = "") -> Set[str]:
        """该 provider + 指定模型实际可消耗的图片输入字段集合。

        取值是 executor 统一传入的**通用图片输入字段名**（不是厂商参数名）：
        - ``image_url``：单张首帧图 / 图片编辑参考图
        - ``image_url_last``：尾帧（首尾帧生视频，需与 image_url 同用）
        - ``reference_images``：参考图列表（参考生视频 r2v / 图生图 i2i）

        ``kind`` 为 "image"/"video"（厂商级合并协议需据此路由到内层 provider）。

        默认返回**全量**（对应"未声明/不确定"的 provider 不做拦截，始终透传）；
        明确知道自己输入边界的 provider（Seedance / HappyHorse / 万相图像等）
        必须按 model 覆盖返回**收窄**的集合。模型不支持某输入字段时，executor
        会据此给出明确报错（而非静默丢弃，避免用户标注的角色无效）。
        """
        return {"image_url", "image_url_last", "reference_images"}

    def validate_inputs(self, model: str, kind: str, kwargs: Dict[str, Any]) -> None:
        """在 provider 内部校验图片输入字段是否被本 provider+模型支持。

        与 executor 层的校验互补：executor 覆盖 agent/子 Agent 路径，这里覆盖
        直接调用 provider 的工具路径，保证「不支持的输入明确报错，而非静默丢弃」。
        仅当 provider 已覆盖 ``supported_inputs`` 返回收窄集合时才会真正拦截；
        未声明的 provider 默认全量支持，维持原透传行为。

        Raises:
            ValueError: 携带了本模型不支持的图片输入字段。
        """
        supported = set(self.supported_inputs(model, kind))
        labels = {
            "image_url": "图片输入(image_url/首帧/参考图)",
            "image_url_last": "尾帧(image_url_last)",
            "reference_images": "参考图(reference_images)",
        }
        problems = []
        if kwargs.get("image_url") and "image_url" not in supported:
            problems.append(labels["image_url"])
        if kwargs.get("reference_images") and "reference_images" not in supported:
            problems.append(labels["reference_images"])
        if kwargs.get("image_url_last"):
            if "image_url_last" not in supported:
                problems.append(labels["image_url_last"])
            elif not kwargs.get("image_url"):
                problems.append("尾帧(image_url_last)必须与首帧(image_url)同时提供")
        if problems:
            raise ValueError(
                f"模型 '{model}' 无法满足你的图片输入要求：{'；'.join(problems)}。"
                f"请改用支持相应能力的媒体生成模型。"
            )

    async def generate_audio(
        self,
        prompt: str,
        model: str,
        **kwargs: Any,
    ) -> MediaGenResult:
        """Text-to-speech: synthesize audio from text.

        默认不支持。支持音频生成的 provider 需覆盖此方法。厂商级多媒体协议
        （dashscope_multimedia / volcengine_multimedia / openai_multimedia）
        内部按模型 model_type=audio 路由到这里。
        """
        raise NotImplementedError(
            f"{type(self).__name__} 不支持音频生成（generate_audio 未实现）"
        )

    async def resume_task(
        self,
        task_id: str,
        model: str,
        **kwargs: Any,
    ) -> "MediaSubmission":
        """按已有 provider task_id 重建可轮询的 submission（不重新提交、不重复扣费）。

        供服务重启 / 流程中断后的手动召回：只对已存在的 provider 任务做
        轮询 + 下载。默认不支持，子类按需实现。
        """
        raise NotImplementedError(
            f"{type(self).__name__} 不支持按 task_id 召回（resume_task 未实现）"
        )


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


def _sniff_audio(data: bytes) -> bool:
    if data.startswith(b"ID3"):  # MP3 (ID3 tag)
        return True
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":  # WAV
        return True
    if data.startswith(b"OggS"):  # OGG / Opus
        return True
    if data.startswith(b"fLaC"):  # FLAC
        return True
    return False


def _validate_media_payload(
    data: bytes, content_type: str, kind: Literal["image", "video", "audio"]
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
    if kind == "audio":
        if _sniff_audio(data) or ct.startswith("audio/"):
            return True, ""
        return False, f"payload is not recognizable audio (content-type={ct!r}, {len(data)} bytes)"
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
    kind: Literal["image", "video", "audio"],
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
