import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends

from gyra.component import SystemApp
from gyra_app.openapi.api_view_model import Result

logger = logging.getLogger(__name__)

router = APIRouter()

# Optional RBAC dependency. Permissions are enforced when the feature plugin is
# available; otherwise the endpoints remain open for backwards compatibility.
try:
    from gyra_app.feature_plugins.permissions.checker import require_permission
    from gyra_serve.utils.auth import UserRequest

    PERMISSIONS_AVAILABLE = True
except Exception:
    PERMISSIONS_AVAILABLE = False
    require_permission = None  # type: ignore[assignment]
    UserRequest = None  # type: ignore[misc,assignment]


def _require_model_read():
    if PERMISSIONS_AVAILABLE and require_permission:
        return require_permission("model", "read")

    async def _noop():
        return None

    return _noop


def _require_model_manage():
    if PERMISSIONS_AVAILABLE and require_permission:
        return require_permission("model", "manage")

    async def _noop():
        return None

    return _noop


def _load_agent_llm_config() -> Optional[Dict[str, Any]]:
    """Load agent_llm configuration from the canonical sources."""
    # 数据库为准：模型/LLM 配置存储在数据库中（分布式多节点共享）。
    try:
        from gyra_app.config_storage.agent_llm_db_storage import load_agent_llm_dict

        db_data = load_agent_llm_dict()
        if db_data:
            return _normalize_agent_llm(db_data)
    except Exception as e:
        import traceback
        logger.warning(
            f"Failed to load agent_llm from database: {e}\n"
            f"{traceback.format_exc()}"
        )

    # Prefer the JSON config manager (matches what the UI edits).
    try:
        from gyra_core.config import ConfigManager

        cfg = ConfigManager.get()
        if cfg is not None:
            agent_llm = getattr(cfg, "agent_llm", None)
            if agent_llm is not None:
                return _normalize_agent_llm(agent_llm)
    except Exception as e:
        import traceback
        logger.warning(
            f"Failed to load agent_llm from ConfigManager: {e}\n"
            f"{traceback.format_exc()}"
        )

    # Fallback to the in-process SystemApp config.
    try:
        system_app = SystemApp.get_instance()
        if system_app is not None:
            agent_llm = system_app.config.get("agent.llm")
            if agent_llm is not None:
                return _normalize_agent_llm(agent_llm)
    except Exception as e:
        import traceback
        logger.warning(
            f"Failed to load agent.llm from SystemApp: {e}\n"
            f"{traceback.format_exc()}"
        )

    return None


def _normalize_agent_llm(agent_llm: Any) -> Dict[str, Any]:
    """Normalize agent_llm to a plain dict with backend-shaped provider list."""
    if isinstance(agent_llm, dict):
        data = agent_llm
    elif hasattr(agent_llm, "model_dump"):
        data = agent_llm.model_dump(mode="json")
    else:
        data = dict(agent_llm)

    # Frontend format uses "providers" / "models"; backend uses "provider" / "model".
    if "providers" in data:
        providers = data.pop("providers")
        normalized_providers = []
        for p in providers or []:
            if not isinstance(p, dict):
                continue
            np = dict(p)
            if "models" in np:
                np["model"] = np.pop("models")
            normalized_providers.append(np)
        data["provider"] = normalized_providers

    return data


def _iter_configured_models(agent_llm: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Iterate configured models as {provider, model_name, model_conf} dicts."""
    result = []
    providers = agent_llm.get("provider") or []
    if not isinstance(providers, list):
        return result

    for p_conf in providers:
        if not isinstance(p_conf, dict):
            continue
        provider_name = p_conf.get("provider", "unknown")
        p_defaults = {k: v for k, v in p_conf.items() if k not in ("model", "provider")}
        p_defaults["provider"] = provider_name

        models = p_conf.get("model") or []
        if not isinstance(models, list):
            continue

        for m_conf in models:
            if not isinstance(m_conf, dict):
                continue
            model_name = m_conf.get("name") or m_conf.get("model")
            if not model_name:
                continue
            merged = dict(p_defaults)
            merged.update(m_conf)
            if "api_base" in merged and "base_url" not in merged:
                merged["base_url"] = merged["api_base"]
            result.append(
                {
                    "provider": provider_name,
                    "model_name": model_name,
                    "model_conf": merged,
                }
            )

    return result


def _worker_type(model_conf: Dict[str, Any]) -> str:
    """Infer the worker type for a configured model."""
    # Config-based models are consumed through the proxy LLM worker.
    return "llm"


def _is_media_model(model_conf: Dict[str, Any]) -> bool:
    """聊天模型下拉排除媒体生成模型（图片/视频/音频）。

    与 ModelConfigCache.is_media_model_config 同口径：命中厂商级多媒体协议
    （dashscope/volcengine/openai/google_multimedia）或 model_type 为
    image/video/audio 即视为媒体生成模型。普通聊天只应选择文本/视觉 LLM，
    媒体生成模型由多媒体 Agent 配置池（image_models/video_models）另行管理。
    """
    try:
        from gyra.agent.util.llm.model_config_cache import is_media_model_config

        return is_media_model_config(model_conf)
    except Exception:
        # 判定函数不可用时不误杀：按 model_type 兜底
        return (model_conf.get("model_type") or "").lower() in (
            "image",
            "video",
            "audio",
        )


def _resolve_global_default(agent_llm: Dict[str, Any]) -> Optional[str]:
    """解析全局默认模型名称。

    与 api_v1 helpers.model_helper.find_default_model 口径一致：取配置中
    is_default=true 的首个模型（按 provider 配置顺序），未配置则返回 None。
    该模型在整个模型列表中是唯一带 is_default 标记的「全局默认模型」。
    """
    for item in _iter_configured_models(agent_llm):
        if item["model_conf"].get("is_default"):
            return item["model_name"]
    return None


@router.get("/models")
async def list_models(
    user: Optional[UserRequest] = Depends(_require_model_read()),
) -> Result[List[Dict[str, Any]]]:
    """List configured models in the format expected by the model management UI."""
    try:
        agent_llm = _load_agent_llm_config()
        if not agent_llm:
            return Result.succ([])

        default_model_name = _resolve_global_default(agent_llm)
        responses = []
        for item in _iter_configured_models(agent_llm):
            provider_name = item["provider"]
            model_name = item["model_name"]
            model_conf = item["model_conf"]
            # 聊天模型下拉只展示文本/视觉 LLM；媒体生成模型由多媒体 Agent 配置池管理
            if _is_media_model(model_conf):
                continue
            worker_type = _worker_type(model_conf)

            responses.append(
                {
                    "chat_scene": "chat",
                    "model_name": model_name,
                    "name": model_name,
                    "worker_type": worker_type,
                    "model_type": model_conf.get("model_type", "llm"),
                    "is_default": model_name == default_model_name,
                    "host": f"proxy@{provider_name}",
                    "port": 0,
                    "manager_host": "system-config",
                    "manager_port": 0,
                    "healthy": True,
                    "check_healthy": True,
                    "prompt_template": None,
                    "last_heartbeat": "permanent",
                    "stream_api": None,
                    "nostream_api": None,
                }
            )

        return Result.succ(responses)
    except Exception as e:
        logger.exception(f"list models error: {e}")
        return Result.failed(code="E000X", msg=f"list models error: {e}")


@router.get("/model-types")
async def list_model_types(
    user: Optional[UserRequest] = Depends(_require_model_read()),
) -> Result[List[Dict[str, Any]]]:
    """List supported model types from the configured AgentLLM providers."""
    try:
        agent_llm = _load_agent_llm_config()
        if not agent_llm:
            return Result.succ([])

        params = []
        for item in _iter_configured_models(agent_llm):
            provider_name = item["provider"]
            model_name = item["model_name"]
            model_conf = item["model_conf"]
            params.append(
                {
                    "model": model_name,
                    "path": model_name,
                    "worker_type": _worker_type(model_conf),
                    "path_exist": True,
                    "proxy": True,
                    "enabled": True,
                    "host": f"proxy@{provider_name}",
                    "port": 0,
                    # ConfigurableForm expects an array of parameter definitions.
                    # We don't have runtime parameter metadata for proxy models,
                    # so expose an empty list to keep the form from crashing.
                    "params": [],
                    "provider": provider_name,
                    "protocol": model_conf.get("protocol", provider_name),
                    "model_type": model_conf.get("model_type", "llm"),
                    "capabilities": model_conf.get("capabilities", []),
                    "is_multimodal": model_conf.get("is_multimodal", False),
                    "description": model_conf.get("description", ""),
                }
            )

        return Result.succ(params)
    except Exception as e:
        logger.exception(f"list model types error: {e}")
        return Result.failed(code="E000X", msg=f"list model types error: {e}")


@router.post("/models")
async def create_model(
    body: Dict[str, Any] = Body(...),
    user: Optional[UserRequest] = Depends(_require_model_manage()),
) -> Result[bool]:
    """Create/start a model.

    The legacy cluster-based worker deployment has been removed; models are now
    configured through AgentLLM providers. This endpoint returns success so the
    UI remains compatible.
    """
    logger.info(f"create_model called with: {body}")
    return Result.succ(True)


@router.post("/models/start")
async def start_model(
    body: Dict[str, Any] = Body(...),
    user: Optional[UserRequest] = Depends(_require_model_manage()),
) -> Result[bool]:
    """Start a model (no-op for config-based models)."""
    logger.info(f"start_model called with: {body}")
    return Result.succ(True)


@router.post("/models/stop")
async def stop_model(
    body: Dict[str, Any] = Body(...),
    user: Optional[UserRequest] = Depends(_require_model_manage()),
) -> Result[bool]:
    """Stop a model (no-op for config-based models)."""
    logger.info(f"stop_model called with: {body}")
    return Result.succ(True)
