"""AgentLLM（模型/LLM）配置的数据库持久化。

模型/LLM 配置以数据库为准（分布式部署多节点共享同一份配置），同时保留本地
gyra.json 作为备份。读取时优先使用数据库中的配置，数据库无记录时回退到文件。

存储格式为前端使用的 agent_llm 结构（providers/models），与
``gyra_core.config.schema.AgentLLMConfig`` 保持一致。
"""

import logging
from typing import Any, Dict, Optional

from gyra_core.config.schema import AgentLLMConfig

logger = logging.getLogger(__name__)

_AGENT_LLM_CONFIG_KEY = "agent_llm"
_AGENT_LLM_CONFIG_TYPE = "agent_llm"


def _dao():
    from gyra_app.feature_plugins.system_config_dao import SystemConfigDao

    return SystemConfigDao()


def load_agent_llm_dict() -> Optional[Dict[str, Any]]:
    """从数据库读取 agent_llm 配置（前端格式 providers/models），无记录返回 None。"""
    try:
        data = _dao().get_config(_AGENT_LLM_CONFIG_KEY, _AGENT_LLM_CONFIG_TYPE)
        if data and isinstance(data, dict):
            return data
    except Exception as e:  # pragma: no cover - best-effort DB read
        logger.warning(f"Failed to load agent_llm from database: {e}")
    return None


def load_agent_llm_model_names(exclude_media: bool = True) -> list:
    """从数据库读取 agent_llm 配置并提取所有模型名（数据库优先，分布式共享）。

    同时兼容前端格式（providers/models）与后端格式（provider/model）。
    ``exclude_media=True`` 时排除媒体生成模型（图片/视频/音频），避免聊天模型
    下拉混入多媒体生成模型；模型配置与协议在 provider 级，判定时需合并两者。
    无记录或异常时返回空列表，调用方应回退到内存配置。
    """
    data = load_agent_llm_dict()
    if not data or not isinstance(data, dict):
        return []
    names = set()
    providers = data.get("providers")
    if not isinstance(providers, list):
        providers = data.get("provider")
    for p in providers or []:
        if not isinstance(p, dict):
            continue
        models = p.get("models")
        if not isinstance(models, list):
            models = p.get("model")
        p_defaults = {k: v for k, v in p.items() if k not in ("models", "model")}
        for m in models or []:
            if not isinstance(m, dict):
                continue
            name = m.get("name") or m.get("model")
            if not name:
                continue
            if exclude_media:
                try:
                    from gyra.agent.util.llm.model_config_cache import (
                        is_media_model_config,
                    )

                    merged = dict(p_defaults)
                    merged.update(m)
                    if is_media_model_config(merged):
                        continue
                except Exception:
                    pass
            names.add(name)
    return list(names)


def save_agent_llm_dict(
    agent_llm: Dict[str, Any], description: Optional[str] = None
) -> bool:
    """将 agent_llm 配置写入数据库（upsert，数据库为准）。"""
    try:
        _dao().set_config(
            _AGENT_LLM_CONFIG_KEY,
            agent_llm,
            _AGENT_LLM_CONFIG_TYPE,
            description=description or "Agent LLM 模型/Provider 配置（数据库为准）",
        )
        return True
    except Exception as e:
        logger.exception(f"Failed to save agent_llm to database: {e}")
        return False


def apply_agent_llm_dict(config) -> bool:
    """若数据库存在 agent_llm 配置，则覆盖 ``config.agent_llm``（数据库为准）。

    Args:
        config: AppConfig 实例（会被原地修改）

    Returns:
        是否成功从数据库覆盖。数据库无记录或解析失败时返回 False。
    """
    data = load_agent_llm_dict()
    if not data:
        return False
    try:
        config.agent_llm = AgentLLMConfig(**data)
        logger.info(
            "agent_llm overlaid from database: %d providers",
            len(config.agent_llm.providers),
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to apply agent_llm from database: {e}")
        return False