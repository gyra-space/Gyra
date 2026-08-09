"""Shared DashScope HTTP plumbing for media-gen providers.

DashScope (Alibaba Cloud Model Studio) providers share:
- Bearer auth + an optional `X-DashScope-Async: enable` header
- The async task polling protocol: GET /api/v1/tasks/{task_id}, parsing
  ``output.task_status`` (PENDING/RUNNING -> SUCCEEDED/FAILED/CANCELED/UNKNOWN)

This module centralizes that plumbing so providers (wanxiang image,
happyhorse video, ...) stay thin. Sync endpoints (e.g. qwen-image-3.0-pro
via multimodal-generation/generation) only use ``build_headers`` and
``raise_for_error`` -- they do not poll.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"
TASK_QUERY_PATH = "/tasks/{task_id}"

# Terminal failure statuses returned by /api/v1/tasks/{task_id}
_FAILED_STATUSES = ("FAILED", "CANCELED", "UNKNOWN")


def normalize_base_url(base_url: str) -> str:
    """Normalize a DashScope base URL to end with exactly one ``/api/v1``.

    The per-endpoint constants are version-relative (``/services/aigc/...``,
    ``/tasks/{task_id}``), so the base URL must carry the ``/api/v1`` version
    prefix -- i.e. it is configured down to the ``v1`` layer, matching how the
    Alibaba Cloud console exposes a workspace endpoint
    (``https://llm-xxx.cn-beijing.maas.aliyuncs.com/api/v1``).

    Accept the base URL with or without the suffix and normalize to a single
    trailing ``/api/v1``: keep it if present, append it if missing, and never
    duplicate it. This avoids the ``/api/v1/api/v1/...`` 404 that happens when
    a versioned base URL meets a versioned endpoint constant.

    It also truncates any path past ``/api/v1`` — e.g. a base_url mistakenly
    configured as a full endpoint (``.../api/v1/services/aigc/...``) is
    reduced back to ``.../api/v1`` so the per-endpoint constant appended by
    the provider isn't duplicated into a malformed URL.
    """
    if not base_url:
        return base_url
    url = base_url.rstrip("/")
    idx = url.rfind("/api/v1")
    if idx != -1:
        return url[: idx + len("/api/v1")]
    return f"{url}/api/v1"


def build_headers(api_key: str, *, async_mode: bool = False) -> dict[str, str]:
    """Build DashScope request headers.

    Args:
        api_key: DashScope API key.
        async_mode: If True, add ``X-DashScope-Async: enable``. Required by
            the async task-based endpoints (text2image/image-synthesis,
            image-generation/generation, video-generation/video-synthesis)
            to return a task_id instead of blocking. The
            multimodal-generation/generation endpoint is synchronous and
            does not need this header.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if async_mode:
        headers["X-DashScope-Async"] = "enable"
    return headers


def raise_for_error(result: dict, provider: str = "dashscope") -> None:
    """Raise RuntimeError if a DashScope response carries a top-level error.

    DashScope signals errors with a top-level ``code``/``message`` pair
    (success responses omit ``code``). This is shared by both the create
    endpoints and the sync multimodal endpoint.
    """
    code = result.get("code")
    if code:
        raise RuntimeError(
            f"{provider} request failed ({code}): {result.get('message', '')}"
        )


def raise_for_response(resp: Any, provider: str = "dashscope") -> dict:
    """Parse a DashScope HTTP response and raise on error.

    DashScope signals errors with a top-level ``code``/``message`` pair even
    for HTTP 4xx (e.g. ``{"code":"AccessDenied","message":"..."}``), which
    httpx's ``raise_for_status`` would mask behind a generic status line.
    Parse the body first and surface DashScope's message; fall back to
    ``raise_for_status`` for non-JSON / gateway-level errors.

    Returns the parsed JSON body (``{}`` if unparseable) on success.
    """
    try:
        result = resp.json()
    except ValueError:
        result = None
    if isinstance(result, dict):
        raise_for_error(result, provider=provider)
    resp.raise_for_status()
    return result or {}


async def poll_dashscope_task(
    client: Any,
    base_url: str,
    task_id: str,
    api_key: str,
    timeout: int,
    extract_url: Callable[[dict], str],
    poll_interval: int = 10,
    provider: str = "dashscope",
    model: Optional[str] = None,
) -> str:
    """Poll a DashScope async task until completion, return the result URL.

    Args:
        client: httpx.AsyncClient instance.
        base_url: DashScope base URL.
        task_id: Task ID returned by the create endpoint.
        api_key: DashScope API key.
        timeout: Maximum wait time in seconds.
        extract_url: Callable(full_response_dict) -> URL string. Should raise
            ValueError if the URL cannot be located in a SUCCEEDED response.
        poll_interval: Seconds between polls.
        provider: Provider name for log/error messages.
        model: Model name (e.g. ``pixverse/pixverse-v6-t2v``) appended to error
            messages so failures clearly identify which model was used.

    Returns:
        Result URL string (image or video).

    Raises:
        RuntimeError: task reached a FAILED/CANCELED/UNKNOWN status.
        TimeoutError: task did not finish within ``timeout``.
    """
    query_url = f"{base_url}{TASK_QUERY_PATH.format(task_id=task_id)}"
    headers = {"Authorization": f"Bearer {api_key}"}

    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        resp = await client.get(query_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        output = data.get("output", {})
        status = output.get("task_status", "")

        if status == "SUCCEEDED":
            return extract_url(data)

        if status in _FAILED_STATUSES:
            error_msg = (
                output.get("message", "")
                or output.get("code", "")
                or data.get("message", "")
                or f"task status {status}"
            )
            # 明确标注是哪个提供商 / 哪个模型，便于快速定位。
            # provider 参数由调用方传入用户配置的提供商名（如 alibaba）。
            label = f"{provider} [{model}]" if model else provider
            raise RuntimeError(
                f"{label} task failed (status={status}): {error_msg}"
            )

        logger.debug(
            f"[{provider}] Task {task_id} status: {status} ({elapsed}s elapsed)"
        )

    raise TimeoutError(
        f"{provider} task timed out after {timeout}s (task_id={task_id})"
    )
