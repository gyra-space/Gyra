"""Alibaba Cloud HappyHorse (通义万相视频) Video Generation Provider.

Implements video generation via the DashScope API, supporting three scenarios
routed by model name suffix:
- happyhorse-1.1-t2v / happyhorse-1.0-t2v  (text-to-video)
- happyhorse-1.1-i2v / happyhorse-1.0-i2v  (image-to-video, first frame)
- happyhorse-1.1-r2v / happyhorse-1.0-r2v  (reference-to-video, 1~9 reference images)

All scenarios share the same endpoint; the difference is `input.media`.
Uses the DashScope async task pattern: submit -> poll -> download.

API docs:
- t2v: https://help.aliyun.com/zh/model-studio/happyhorse-text-to-video-api-reference
- i2v: https://help.aliyun.com/zh/model-studio/happyhorse-image-to-video-api-reference
- r2v: https://help.aliyun.com/zh/model-studio/happyhorse-reference-to-video-api-reference
"""

import logging
from typing import Any, List, Optional

from gyra.agent.util.media_gen._dashscope_common import (
    build_headers,
    normalize_base_url,
    poll_dashscope_task,
    raise_for_response,
)
from gyra.agent.util.media_gen.base import (
    MediaGenProvider,
    MediaGenResult,
    MediaSubmission,
    download_media_with_retry,
)
from gyra.agent.util.media_gen.provider_registry import MediaGenProviderRegistry

logger = logging.getLogger(__name__)

# Model names are free-form (protocol-based routing). Scenario is derived from
# the model-name suffix (-t2v / -i2v / -r2v), so future versions work without
# code changes.

# Default API endpoints (DashScope generic domain; workspace-specific maas
# domain can be supplied via base_url for better performance/stability)
_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"
_CREATE_TASK_ENDPOINT = "/services/aigc/video-generation/video-synthesis"

# Supported resolutions (HappyHorse uses uppercase, no 4k)
_SUPPORTED_RESOLUTIONS = {"480P", "720P", "1080P"}

# Supported aspect ratios for t2v / r2v (i2v follows the first frame)
_SUPPORTED_RATIOS = {
    "16:9", "9:16", "1:1", "4:3", "3:4", "4:5", "5:4", "9:21", "21:9",
}

# ── 视频格式声明（声明驱动）─────────────────────────────────────────────
# 请求参数格式由模型配置里的 `video_format` 声明决定，provider 统一读取并自动适配，
# 新模型无需改代码只需在模型配置中声明。未声明时回退到内置默认格式（按模型名推断）。
#
# video_format 声明结构（可放模型配置 media model 的扩展字段）：
#   {
#     "style": "size" | "resolution",   # size=用 size("宽*高"); resolution=用 resolution+ratio
#     "resolutions": ["360P","540P",...], # 支持的档位（大写）；缺省时用该项默认
#     "ratios": ["16:9","4:3",...],       # 支持的宽高比；缺省时用该项默认
#     "default_resolution": "720P",       # 兜底档位（分辨率不在支持集时降级）
#     "size_map": { "720P": {"16:9": "1280*720", ...} },  # size 风格下 分辨率×宽高比→size
#     "fallback_size": "1280*720",        # size 风格下组合不在 size_map 时的兜底
#   }
#
# 内置默认：happyhorse（resolution 风格）、pixverse（size 风格，数据来自百炼官方文档）
_DEFAULT_VIDEO_FORMATS: dict[str, dict[str, Any]] = {
    "happyhorse": {
        "style": "resolution",
        "resolutions": ["480P", "720P", "1080P"],
        "ratios": ["16:9", "9:16", "1:1", "4:3", "3:4", "4:5", "5:4", "9:21", "21:9"],
        "default_resolution": "1080P",
    },
    "pixverse": {
        "style": "size",
        "resolutions": ["360P", "540P", "720P", "1080P"],
        "ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "3:2", "2:3", "21:9"],
        "default_resolution": "720P",
        "fallback_size": "1280*720",
        "size_map": {
            "360P": {
                "16:9": "640*360", "4:3": "640*480", "1:1": "640*640",
                "3:4": "480*640", "9:16": "360*640", "3:2": "640*432",
                "2:3": "432*640", "21:9": "640*288",
            },
            "540P": {
                "16:9": "1024*576", "4:3": "1024*768", "1:1": "1024*1024",
                "3:4": "768*1024", "9:16": "576*1024", "3:2": "1024*688",
                "2:3": "688*1024", "21:9": "1024*448",
            },
            "720P": {
                "16:9": "1280*720", "4:3": "1108*832", "1:1": "960*960",
                "3:4": "832*1108", "9:16": "720*1280", "3:2": "1200*800",
                "2:3": "800*1200", "21:9": "1280*560",
            },
            "1080P": {
                "16:9": "1920*1080", "4:3": "1664*1248", "1:1": "1440*1440",
                "3:4": "1248*1664", "9:16": "1080*1920", "3:2": "1776*1184",
                "2:3": "1184*1776", "21:9": "1920*832",
            },
        },
    },
}

# 模型名前缀 → 内置默认格式 key；未命中回退 happyhorse（resolution 风格）
_PREFIX_DEFAULT_FORMAT = {
    "pixverse/": "pixverse",
}


def _scenario_of(model: str) -> str:
    """Return the scenario tag (t2v / i2v / r2v) from a model name."""
    name = model.lower()
    if name.endswith("-t2v"):
        return "t2v"
    if name.endswith("-i2v"):
        return "i2v"
    if name.endswith("-r2v"):
        return "r2v"
    return ""


def _extract_video_url(data: dict) -> str:
    """Extract video_url from a SUCCEEDED DashScope task response."""
    url = data.get("output", {}).get("video_url")
    if not url:
        raise ValueError(f"Task succeeded but no video_url found: {data}")
    return url


@MediaGenProviderRegistry.register(protocol="dashscope_video", env_key="DASHSCOPE_API_KEY")
class HappyHorseVideoProvider(MediaGenProvider):
    """Alibaba Cloud HappyHorse video generation provider.

    Uses the DashScope API with async task pattern: submit -> poll -> download.
    Supports text-to-video, image-to-video (first frame) and
    reference-to-video (multiple reference images). Model name is free-form;
    scenario is routed by the model-name suffix (-t2v / -i2v / -r2v).
    """

    def supported_image_models(self) -> List[str]:
        return []

    def supported_video_models(self) -> List[str]:
        return []

    def _video_format_for(self, model: str) -> dict[str, Any]:
        """解析模型的视频格式声明（声明驱动）。

        优先级：模型配置里的 ``video_format`` 扩展字段 ＞ 内置默认（按模型名前缀）。
        模型配置即 ModelConfigCache 中该媒体模型的完整配置（含用户自定义扩展字段）。
        任何解析异常回退 happyhorse（resolution 风格），保证不阻断生成。
        """
        fmt: Optional[dict[str, Any]] = None
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache

            cfg = ModelConfigCache.get_config(model) or {}
            if isinstance(cfg.get("video_format"), dict):
                fmt = cfg["video_format"]
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[HappyHorseVideoProvider] read video_format for '{model}' failed: {e}"
            )

        if not fmt:
            m = model.lower()
            prefix = next(
                (p for p in _PREFIX_DEFAULT_FORMAT if m.startswith(p)),
                None,
            )
            fmt_key = _PREFIX_DEFAULT_FORMAT.get(prefix, "happyhorse")
            fmt = _DEFAULT_VIDEO_FORMATS.get(
                fmt_key, _DEFAULT_VIDEO_FORMATS["happyhorse"]
            )
        return fmt

    def _provider_label(self, model: str) -> str:
        """返回该模型在配置里填写的提供商名（provider name）。

        直接读取用户模型配置中的 ``provider`` 字段（如 ``alibaba``），
        不硬编码，确保错误信息展示的就是用户配置时填的名字。
        读取失败时回退到内部实现名，保证不阻断。
        """
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache

            cfg = ModelConfigCache.get_config(model) or {}
            p = cfg.get("provider")
            if p:
                return str(p)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[HappyHorseVideoProvider] read provider for '{model}' failed: {e}"
            )
        return "happyhorse"

    async def generate_image(
        self,
        prompt: str,
        model: str = "",
        **kwargs: Any,
    ) -> MediaGenResult:
        raise NotImplementedError(
            "HappyHorse video provider does not support image generation"
        )

    async def generate_video(
        self,
        prompt: str,
        model: str = "happyhorse-1.1-t2v",
        **kwargs: Any,
    ) -> MediaGenResult:
        """Generate a video using Alibaba Cloud HappyHorse API.

        Args:
            prompt: Text description of the video (supports Chinese & English).
            model: Model to use (happyhorse-1.1-t2v / -i2v / -r2v, or 1.0 variants).
            **kwargs: Additional params:
                - duration: Video duration in seconds (default 5, range 3-15).
                - resolution: "480p", "720p", "1080p" (default "1080p").
                  Case-insensitive; normalized to HappyHorse's uppercase form.
                - aspect_ratio: "16:9", "9:16", "1:1", "4:3", "3:4", "4:5",
                  "5:4", "9:21", "21:9" (default "16:9"). Only for t2v/r2v;
                  i2v follows the first frame and ignores this param.
                - seed: Random seed for reproducibility.
                - watermark: Whether to add "Happy Horse" watermark (default False).
                  Note: HappyHorse's own default is True; we pass False explicitly
                  to keep the tool's "no watermark by default" semantics.
                - image_url: First frame image URL for i2v (required for i2v).
                  Supports public URL and Base64 (data:image/xxx;base64,...).
                - reference_images: List of 1~9 reference image URLs for r2v
                  (required for r2v). Use [Image 1]/[Image 2] in the prompt to
                  refer to them.
                - timeout: Max wait time in seconds (default 600).
        """
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
        model: str = "happyhorse-1.1-t2v",
        **kwargs: Any,
    ) -> MediaSubmission:
        """Submit a HappyHorse video task; return a resumable MediaSubmission.

        The HTTP submit runs synchronously so immediate errors (auth, bad
        params) surface now. Polling + download is deferred to
        ``submission.complete()`` for background execution via AsyncTaskManager.
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx package is required for HappyHorse video generation. "
                "Install with: pip install httpx"
            )

        timeout = kwargs.get("timeout", 1800)
        base_url = normalize_base_url(self.base_url or _DEFAULT_BASE_URL)

        duration = kwargs.get("duration", 5)
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        seed = kwargs.get("seed")
        watermark = kwargs.get("watermark", False)
        image_url = kwargs.get("image_url")
        reference_images = kwargs.get("reference_images")

        # 场景由模型名后缀（-t2v/-i2v/-r2v）决定；模型名无后缀时按输入推断：
        # 有参考图 → r2v，有首帧图 → i2v，否则 → t2v（文生视频）。
        scenario = _scenario_of(model)
        if not scenario:
            if reference_images:
                scenario = "r2v"
            elif image_url:
                scenario = "i2v"
            else:
                scenario = "t2v"

        # Validate duration (HappyHorse range is 3-15; PixVerse 也在此区间)
        if not isinstance(duration, int) or duration < 3 or duration > 15:
            raise ValueError(
                f"HappyHorse duration must be an integer in [3, 15], got {duration}"
            )

        # Build input.media based on scenario
        media = self._build_media(scenario, image_url, reference_images)

        # 视频格式声明驱动：按模型配置的 video_format（或内置默认）决定请求参数。
        # size 风格用 size("宽*高")，resolution 风格用 resolution + ratio。协议层
        # 完成档位换算与兜底，Agent 侧声明分辨率/宽高比即可，新模型无需改代码。
        fmt = self._video_format_for(model)
        style = (fmt.get("style") or "resolution").lower()
        resolutions = set(fmt.get("resolutions") or _SUPPORTED_RESOLUTIONS)
        ratios = set(fmt.get("ratios") or _SUPPORTED_RATIOS)
        default_res = (fmt.get("default_resolution") or "720P").upper()
        size_map = fmt.get("size_map") or {}
        fallback_size = fmt.get("fallback_size") or "1280*720"

        if style == "size":
            raw_res = (kwargs.get("resolution") or default_res).strip().upper()
            # 分辨率不在支持集时降级到默认档位（协议层兜底，不阻断）
            if raw_res not in resolutions:
                logger.info(
                    f"[HappyHorseVideoProvider] unsupported resolution '{raw_res}' "
                    f"for '{model}', fell back to {default_res}"
                )
                raw_res = default_res
            size = (size_map.get(raw_res) or {}).get(
                aspect_ratio, fallback_size
            )
            parameters: dict[str, Any] = {
                "size": size,
                "duration": duration,
                "watermark": watermark,
            }
            if seed is not None:
                parameters["seed"] = seed
            if scenario in ("t2v", "r2v") and aspect_ratio not in ratios:
                # 不可用宽高比已兜底到默认档位，仅提示不阻断
                logger.info(
                    f"[HappyHorseVideoProvider] unsupported ratio "
                    f"'{aspect_ratio}' for '{model}', fell back to size={size}"
                )
        else:
            resolution = self._normalize_resolution(
                kwargs.get("resolution", default_res), resolved_set=resolutions
            )
            # Build parameters: ratio only applies to t2v / r2v (i2v follows first frame)
            parameters = {
                "resolution": resolution,
                "duration": duration,
                "watermark": watermark,
            }
            if scenario in ("t2v", "r2v"):
                if aspect_ratio not in ratios:
                    raise ValueError(
                        f"Unsupported aspect_ratio '{aspect_ratio}' for HappyHorse "
                        f"{scenario}. Supported: {sorted(ratios)}"
                    )
                parameters["ratio"] = aspect_ratio
            if seed is not None:
                parameters["seed"] = seed

        body: dict[str, Any] = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": parameters,
        }
        if media:
            body["input"]["media"] = media

        headers = build_headers(self.api_key, async_mode=True)

        logger.info(
            f"[HappyHorseVideoProvider] Submitting {scenario} job: model={model}, "
            f"duration={duration}s, "
            f"{'size=' + parameters['size'] if style == 'size' else 'resolution=' + resolution}, "
            f"ratio={parameters.get('ratio', 'n/a')}, "
            f"media_count={len(media) if media else 0}"
        )
        # 记录完整请求参数（含 prompt / media / parameters），便于排障。
        # 不输出 headers（含 Authorization），避免泄露 api_key。
        create_url = f"{base_url}{_CREATE_TASK_ENDPOINT}"
        logger.info(
            f"[HappyHorseVideoProvider] Request POST {create_url} body={body}"
        )

        # Submit (short-lived client; poll/download use their own).
        async with httpx.AsyncClient(timeout=timeout) as client:
            submit_resp = await client.post(create_url, headers=headers, json=body)
            result = raise_for_response(submit_resp, provider="happyhorse")

        task_id = result.get("output", {}).get("task_id")
        if not task_id:
            raise ValueError(f"HappyHorse API returned no task_id: {result}")

        logger.info(f"[HappyHorseVideoProvider] Task created: {task_id}")

        async def _complete() -> MediaGenResult:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Poll until complete
                video_url = await poll_dashscope_task(
                    client, base_url, task_id, self.api_key, timeout,
                    extract_url=_extract_video_url,
                    poll_interval=15,
                    provider=self._provider_label(model),
                    model=model,
                )
                # Download (validated: OSS may transiently return an XML
                # error body right after task completion)
                logger.info(
                    f"[HappyHorseVideoProvider] Downloading video from {video_url}"
                )
                video_data = await download_media_with_retry(
                    client, video_url, kind="video", provider="happyhorse"
                )

            metadata: dict[str, Any] = {
                "model": model,
                "scenario": scenario,
                "duration": duration,
                "task_id": task_id,
                "provider": "happyhorse",
                "video_url": video_url,
            }
            if style == "size":
                # size 风格（宽*高）记录档位与换算结果
                metadata["resolution"] = default_res
                metadata["size"] = parameters.get("size", fallback_size)
            else:
                metadata["resolution"] = resolution
            if scenario in ("t2v", "r2v"):
                metadata["aspect_ratio"] = aspect_ratio
            if seed is not None:
                metadata["seed"] = seed
            if scenario == "i2v":
                metadata["image_to_video"] = True
            elif scenario == "r2v":
                metadata["reference_image_count"] = len(media)

            return MediaGenResult(
                data=video_data,
                format="mp4",
                mime_type="video/mp4",
                duration_seconds=float(duration),
                metadata=metadata,
            )

        return MediaSubmission(
            task_id=task_id,
            provider="happyhorse",
            model=model,
            complete=_complete,
            metadata={"task_id": task_id, "scenario": scenario, "model": model},
        )

    async def resume_task(
        self,
        task_id: str,
        model: str = "happyhorse-1.1-t2v",
        **kwargs: Any,
    ) -> MediaSubmission:
        """按已有 task_id 召回：只轮询 + 下载，不重新提交（不重复扣费）。

        供服务重启 / 流程中断后找回已生成结果。
        """
        import httpx

        timeout = kwargs.get("timeout", 1800)
        base_url = normalize_base_url(self.base_url or _DEFAULT_BASE_URL)
        scenario = _scenario_of(model) or "t2v"

        async def _complete() -> MediaGenResult:
            async with httpx.AsyncClient(timeout=timeout) as client:
                video_url = await poll_dashscope_task(
                    client, base_url, task_id, self.api_key, timeout,
                    extract_url=_extract_video_url,
                    poll_interval=15,
                    provider=self._provider_label(model),
                    model=model,
                )
                logger.info(
                    f"[HappyHorseVideoProvider] Recalling video from {video_url}"
                )
                video_data = await download_media_with_retry(
                    client, video_url, kind="video", provider="happyhorse"
                )

            return MediaGenResult(
                data=video_data,
                format="mp4",
                mime_type="video/mp4",
                metadata={
                    "model": model,
                    "scenario": scenario,
                    "task_id": task_id,
                    "provider": "happyhorse",
                    "video_url": video_url,
                    "recalled": True,
                },
            )

        return MediaSubmission(
            task_id=task_id,
            provider="happyhorse",
            model=model,
            complete=_complete,
            metadata={"task_id": task_id, "scenario": scenario, "model": model},
        )

    def _build_media(
        self,
        scenario: str,
        image_url: Optional[str],
        reference_images: Optional[List[str]],
    ) -> List[dict[str, Any]]:
        """Build input.media array based on the scenario."""
        if scenario == "t2v":
            return []

        if scenario == "i2v":
            if not image_url:
                raise ValueError(
                    "image_url is required for HappyHorse image-to-video (i2v)"
                )
            return [{"type": "first_frame", "url": image_url}]

        # r2v: reference images
        if not reference_images:
            raise ValueError(
                "reference_images is required for HappyHorse "
                "reference-to-video (r2v)"
            )
        if not isinstance(reference_images, (list, tuple)):
            raise ValueError("reference_images must be a list of URL strings")
        if len(reference_images) < 1 or len(reference_images) > 9:
            raise ValueError(
                f"HappyHorse r2v requires 1~9 reference images, "
                f"got {len(reference_images)}"
            )
        return [
            {"type": "reference_image", "url": url}
            for url in reference_images
            if url
        ]

    def _normalize_resolution(
        self, resolution: str, *, resolved_set: Optional[set] = None
    ) -> str:
        """Normalize resolution to uppercase form (e.g. 720p -> 720P).

        Args:
            resolution: 分辨率输入（大小写不敏感，如 "720p" / "1080P"）。
            resolved_set: 允许的档位集合（来自视频格式声明）；缺省用 HappyHorse
                默认集（480P/720P/1080P）。不在集合内时报错。
        """
        allowed = resolved_set or _SUPPORTED_RESOLUTIONS
        normalized = resolution.strip().upper()
        if normalized not in allowed:
            raise ValueError(
                f"Unsupported resolution '{resolution}'. "
                f"Supported: {sorted(allowed)}"
            )
        return normalized
