import contextvars
import logging
from typing import Dict, Any, Optional, List, Tuple
from copy import deepcopy

from gyra_core.config.schema import (
    DEFAULT_MAX_NEW_TOKENS,
    LEGACY_MAX_TOKENS_AS_CONTEXT_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _migrate_legacy_token_fields(cfg: Dict[str, Any]) -> None:
    """遗留迁移：旧配置只有 max_new_tokens/max_tokens、没有 context_window，
    且常把上下文空间（如 256K）误填进 max_new_tokens。超过阈值时迁回 context_window，
    输出上限重置为默认，避免作为 max_tokens 发出触发 provider 上限报错。

    原地修改 cfg；已显式设置 context_window 时跳过（幂等）。与
    ``LLMProviderModelConfig.model_post_init`` 保持同一口径，供 raw dict 路径
    （parse_provider_configs / 空间级模型 / 直接 register_configs）复用。
    """
    if cfg.get("context_window"):
        return
    legacy = cfg.get("max_new_tokens")
    if legacy is None:
        legacy = cfg.get("max_tokens")
    if isinstance(legacy, int) and legacy > LEGACY_MAX_TOKENS_AS_CONTEXT_THRESHOLD:
        logger.info(
            "migrate legacy max_new_tokens=%s -> context_window for model %s "
            "(reset max_new_tokens=%d)",
            legacy,
            cfg.get("model") or cfg.get("name"),
            DEFAULT_MAX_NEW_TOKENS,
        )
        cfg["context_window"] = legacy
        cfg["max_new_tokens"] = DEFAULT_MAX_NEW_TOKENS
        if "max_tokens" in cfg:
            cfg["max_tokens"] = DEFAULT_MAX_NEW_TOKENS

# 当前请求/任务作用域内的空间级模型配置覆盖(ContextVar)。
# 空间绑定 llm_model 资源时,空间级模型/token 优先于全局缓存,实现"空间专属 token"的管控。
_space_model_config: "contextvars.ContextVar[Optional[Dict[str, Any]]]" = (
    contextvars.ContextVar("space_model_config", default=None)
)


def _normalize_space_model(config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """归一化空间级模型配置,补全 protocol/model 等派生字段。无效配置返回 None。

    空间配置只存 api_key_ref(引用加密 secrets),不落明文 token;运行时经
    ConfigReferenceResolver 解析。若显式给了 api_key 也透传(仍以 secrets 优先)。
    """
    if not config:
        return None
    model = (config.get("model") or "").strip()
    if not model:
        return None
    provider = (config.get("provider") or "openai").strip()
    protocol = (config.get("protocol") or "").strip() or infer_protocol(provider)
    base_url = config.get("base_url") or config.get("api_base")
    api_key_ref = (config.get("api_key_ref") or "").strip()
    api_key = config.get("api_key")
    # 空间配置只存 api_key_ref(引用加密 secrets)。运行时解析成 api_key,
    # 使 get_config 返回的合并配置能被 llm_client 直接用作 provider 凭据。
    if api_key_ref and not api_key:
        try:
            from gyra_core.config.encryption import ConfigReferenceResolver

            resolved = ConfigReferenceResolver.resolve(api_key_ref)
            if resolved and isinstance(resolved, str):
                api_key = resolved
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"resolve space model api_key_ref failed: {e}"
            )
    normalized = {
        "provider": provider,
        "model": model,
        "protocol": protocol,
        "base_url": base_url,
        "api_key_ref": api_key_ref,
        "api_key": api_key,
        # 透传模型推理参数:空间级配置可覆盖温度/思考深度等,未配置的字段回退全局。
        "temperature": config.get("temperature"),
        "max_new_tokens": config.get("max_new_tokens") or config.get("max_tokens"),
        "context_window": config.get("context_window"),
        "top_p": config.get("top_p"),
        "reasoning_effort": config.get("reasoning_effort"),
        # 透传模型元数据:空间绑定模型未在全局注册时,仍能保留多模态/能力/类型,
        # 使 is_multimodal / get_multimodal_models / select_llm_model 正确识别。
        "model_type": config.get("model_type") or "llm",
        "capabilities": config.get("capabilities") or ["text"],
        "is_multimodal": bool(config.get("is_multimodal", config.get("supports_vision", False))),
    }
    # 遗留迁移:空间级模型同样可能把上下文空间误填进 max_new_tokens
    _migrate_legacy_token_fields(normalized)
    return normalized


def _space_model_key(config: Optional[Dict[str, Any]]) -> Optional[str]:
    """空间模型完整 key(provider/model);无配置返回 None。"""
    if not config:
        return None
    return f"{config.get('provider')}/{config.get('model')}"

# 媒体生成协议（= API 形状 = 一个 provider 类）。图/视频编码在后缀。
# model_config_cache 用它过滤媒体模型（防聊天污染）；media_gen 用它路由+列可用模型。
MEDIA_PROTOCOLS = {
    "dashscope_video",   # 百炼视频 (HappyHorse t2v/i2v/r2v)
    "dashscope_image",   # 百炼图像 (qwen-image / wan2.x / wanx)
    "volcengine_video",  # 火山视频 (Seedance)
    "openai_image",      # OpenAI 图像 (DALL-E)
    "openai_video",      # OpenAI 视频 (Sora)
    "google_image",      # Google 图像 (Nano Banana)
}
IMAGE_PROTOCOLS = {"dashscope_image", "openai_image", "google_image"}
VIDEO_PROTOCOLS = {"dashscope_video", "volcengine_video", "openai_video"}

# 接入协议推断映射：provider 名称 -> 协议
def infer_protocol(provider_name: str) -> str:
    """根据 provider 来源名称推断接入协议"""
    name = (provider_name or "").strip().lower()
    openai_compatible = {
        "openai", "alibaba", "aliyun", "dashscope", "aws", "azure",
        "deepseek", "zhipu", "moonshot", "openrouter", "siliconflow",
        "custom", "tencent", "baidu", "volcengine", "minimax",
    }
    if name in openai_compatible:
        return "openai"
    if name in {"anthropic", "claude"}:
        return "anthropic"
    if name == "theta":
        return "theta"
    return name or "openai"


class ModelConfigCache:
    """全局模型配置缓存

    支持两种格式存储：
    - provider/model: 完整格式，如 "openai/DeepSeek-V3"
    - model: 简单格式，用于查找默认 provider
    """

    _instance = None
    _model_configs: Dict[str, Dict[str, Any]] = {}  # key: "provider/model"
    _model_providers: Dict[
        str, List[str]
    ] = {}  # key: model_name, value: list of provider keys

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_configs(cls, configs: Dict[str, Dict[str, Any]]):
        """注册模型配置

        Args:
            configs: key 为 "provider/model" 格式，value 为配置
        """
        for key, config in configs.items():
            cls._model_configs[key] = config

            # 提取模型名，建立模型到 provider 的映射
            model_name = config.get("model") or key.split("/")[-1]
            if model_name not in cls._model_providers:
                cls._model_providers[model_name] = []
            if key not in cls._model_providers[model_name]:
                cls._model_providers[model_name].append(key)

        logger.info(f"ModelConfigCache: registered {len(configs)} models")
        for model, providers in cls._model_providers.items():
            logger.info(f"  {model}: {providers}")

    @classmethod
    def set_space_model_config(cls, config: Optional[Dict[str, Any]]) -> None:
        """设置当前作用域的空间级模型配置覆盖(ContextVar)。

        空间绑定 llm_model 资源时调用;None 表示清除覆盖(回退全局)。配置只含
        api_key_ref(引用 secrets),token 运行时解析,不落明文。
        """
        _space_model_config.set(_normalize_space_model(config))

    @classmethod
    def get_space_model_config(cls) -> Optional[Dict[str, Any]]:
        """读取当前作用域的空间级模型配置覆盖;无则返回 None。"""
        return _space_model_config.get()

    @classmethod
    def get_config(cls, model_key: str) -> Optional[Dict[str, Any]]:
        """获取模型配置

        Args:
            model_key: 可以是 "provider/model" 格式，或纯模型名

        Returns:
            模型配置，如果没找到返回 None

        空间级优先级:当前作用域绑定了 llm_model 资源且请求的模型匹配空间模型时,
        返回空间配置(以全局默认配置为底、空间配置覆盖),实现空间专属 token。
        """
        space_cfg = cls.get_space_model_config()
        if space_cfg:
            space_model = space_cfg.get("model")
            space_key = _space_model_key(space_cfg)
            if model_key and (model_key == space_model or model_key == space_key):
                merged = {}
                global_cfg = cls._model_configs.get(model_key) or (
                    cls._model_configs.get(space_key)
                )
                if global_cfg:
                    merged.update(global_cfg)
                # 空间配置覆盖全局;但空间未设置的推理参数(值为 None)不得覆盖全局默认,
                # 从而满足"默认使用系统配置"的要求。
                for _k, _v in space_cfg.items():
                    if _v is not None:
                        merged[_k] = _v
                return merged

        # 先尝试完整 key
        if model_key in cls._model_configs:
            return cls._model_configs[model_key]

        # 如果是纯模型名，返回第一个 provider 的配置
        if model_key in cls._model_providers:
            providers = cls._model_providers[model_key]
            if providers:
                return cls._model_configs[providers[0]]

        return None

    @classmethod
    def has_model(cls, model_key: str) -> bool:
        """检查模型是否存在"""
        space_cfg = cls.get_space_model_config()
        if space_cfg:
            space_model = space_cfg.get("model")
            space_key = _space_model_key(space_cfg)
            if model_key and (model_key == space_model or model_key == space_key):
                return True
        if model_key in cls._model_configs:
            return True
        if model_key in cls._model_providers:
            return True
        return False

    @classmethod
    def get_all_models(cls, include_media_gen: bool = False) -> List[str]:
        """获取所有模型名（去重）。

        Args:
            include_media_gen: 是否包含媒体生成模型 (protocol == "media_gen")。
                默认 False，排除生成模型，避免聊天/embedding/rerank 的
                ``all_models[0]`` 兜底误选到图像/视频生成模型。展示/同步类
                调用方应传 True 以查看全量。

        空间级优先级:当前作用域绑定了 llm_model 资源时,空间模型置顶(优先被
        select_llm_model 选中)。空间模型为媒体生成模型时,按 include_media_gen 过滤。
        """
        space_cfg = cls.get_space_model_config()
        space_model = (space_cfg or {}).get("model")
        base = (
            list(cls._model_providers.keys())
            if include_media_gen
            else [
                m for m in cls._model_providers.keys()
                if not cls._is_media_model(m)
            ]
        )
        if space_model:
            if include_media_gen or not cls._is_media_model(space_model):
                base = [space_model] + [m for m in base if m != space_model]
            else:
                base = [m for m in base if m != space_model]
        return base

    @classmethod
    def _is_media_model(cls, model_key: str) -> bool:
        """该模型是否为媒体生成模型 (protocol 属于 MEDIA_PROTOCOLS)。"""
        config = cls.get_config(model_key)
        return bool(config and config.get("protocol") in MEDIA_PROTOCOLS)

    @classmethod
    def get_media_models(cls) -> List[Dict[str, Any]]:
        """返回所有媒体生成模型的配置（protocol 属于 MEDIA_PROTOCOLS）。

        供 media_gen 工具的可用性展示与凭据解析使用。
        每项: {"model", "protocol", "api_key", "base_url", "provider"}
        """
        result: List[Dict[str, Any]] = []
        for model_name in cls._model_providers.keys():
            if not cls._is_media_model(model_name):
                continue
            config = cls.get_config(model_name) or {}
            result.append({
                "model": model_name,
                "protocol": config.get("protocol"),
                "api_key": config.get("api_key", ""),
                "base_url": config.get("base_url") or config.get("api_base", ""),
                "provider": config.get("provider", ""),
            })
        return result

    @classmethod
    def get_all_model_keys(cls) -> List[str]:
        """获取所有模型 key（provider/model 格式）"""
        return list(cls._model_configs.keys())

    @classmethod
    def clear(cls):
        """清空缓存"""
        cls._model_configs = {}
        cls._model_providers = {}

    @classmethod
    def is_multimodal(cls, model_key: str) -> bool:
        """检查模型是否支持多模态（图片输入）

        Args:
            model_key: 可以是 "provider/model" 格式，或纯模型名

        Returns:
            是否支持多模态，如果没找到配置返回 False
        """
        config = cls.get_config(model_key)
        if config:
            if "capabilities" in config:
                return "vision" in config["capabilities"]
            return config.get("is_multimodal", False)
        return False

    @classmethod
    def get_multimodal_models(cls) -> List[str]:
        """获取所有支持多模态的模型名

        Returns:
            支持图片输入的模型列表
        """
        multimodal_models = []
        for model_name in cls._model_providers.keys():
            if cls.is_multimodal(model_name):
                multimodal_models.append(model_name)
        return multimodal_models

    @classmethod
    def get_model_type(cls, model_key: str) -> Optional[str]:
        """获取模型类型

        Args:
            model_key: 可以是 "provider/model" 格式，或纯模型名

        Returns:
            模型类型，如果没找到配置返回 None
        """
        config = cls.get_config(model_key)
        if config:
            return config.get("model_type")
        return None

    @classmethod
    def get_capabilities(cls, model_key: str) -> List[str]:
        """获取模型能力标签

        Args:
            model_key: 可以是 "provider/model" 格式，或纯模型名

        Returns:
            能力标签列表，如果没找到配置返回空列表
        """
        config = cls.get_config(model_key)
        if config:
            capabilities = config.get("capabilities")
            if capabilities:
                return list(capabilities)
            # 兼容旧配置
            if config.get("is_multimodal"):
                return ["text", "vision"]
            return ["text"]
        return []


def parse_provider_configs(
    global_agent_conf: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """解析 [[agent.llm.provider]] 配置

    Args:
        global_agent_conf: agent.llm 配置

    Returns:
        key 为 "provider/model" 格式的配置映射，包含 is_multimodal 字段标识是否支持图片输入
    """
    model_configs = {}

    # 输入验证日志
    if not global_agent_conf:
        logger.warning("[parse_provider_configs] Input is None or empty")
        return model_configs

    logger.info(
        f"[parse_provider_configs] Input keys: {list(global_agent_conf.keys())}"
    )

    providers_list = global_agent_conf.get("provider")

    if not providers_list:
        logger.warning(
            f"[parse_provider_configs] No 'provider' key found, available keys: {list(global_agent_conf.keys())}"
        )
        return model_configs

    if not isinstance(providers_list, list):
        logger.warning(
            f"[parse_provider_configs] 'provider' is not a list, type: {type(providers_list)}"
        )
        return model_configs

    logger.info(
        f"[parse_provider_configs] Processing {len(providers_list)} providers"
    )

    for idx, provider_conf in enumerate(providers_list):
        if not isinstance(provider_conf, dict):
            logger.warning(
                f"[parse_provider_configs] Provider[{idx}] is not a dict, skipping"
            )
            continue

        provider_name = provider_conf.get("provider", "default")
        logger.info(f"[parse_provider_configs] Processing provider '{provider_name}'")

        p_defaults = {
            k: v for k, v in provider_conf.items() if k not in ["model", "provider"]
        }
        p_defaults["provider"] = provider_name

        # 接入协议：优先使用显式配置，否则根据 provider 推断
        protocol = provider_conf.get("protocol")
        if not protocol:
            protocol = infer_protocol(provider_name)
        p_defaults["protocol"] = protocol

        if "api_base" in p_defaults and "base_url" not in p_defaults:
            p_defaults["base_url"] = p_defaults["api_base"]

        p_models = provider_conf.get("model", [])
        if not p_models:
            logger.warning(
                f"[parse_provider_configs] Provider '{provider_name}' has no 'model' key"
            )
            continue

        if not isinstance(p_models, list):
            logger.warning(
                f"[parse_provider_configs] Provider '{provider_name}' models is not a list, type: {type(p_models)}"
            )
            continue

        logger.info(
            f"[parse_provider_configs] Provider '{provider_name}' has {len(p_models)} models"
        )

        for m_idx, m_conf in enumerate(p_models):
            if not isinstance(m_conf, dict):
                logger.warning(
                    f"[parse_provider_configs] Provider '{provider_name}' model[{m_idx}] is not a dict, skipping"
                )
                continue

            model_name = m_conf.get("name") or m_conf.get("model")
            if not model_name:
                logger.warning(
                    f"[parse_provider_configs] Provider '{provider_name}' model[{m_idx}] has no 'name' or 'model' field, skipping"
                )
                continue

            logger.info(
                f"[parse_provider_configs] Registering model '{provider_name}/{model_name}'"
            )

            final_conf_dict = deepcopy(p_defaults)
            final_conf_dict.update(m_conf)
            if "api_base" in final_conf_dict and "base_url" not in final_conf_dict:
                final_conf_dict["base_url"] = final_conf_dict["api_base"]
            if "name" in final_conf_dict and "model" not in final_conf_dict:
                final_conf_dict["model"] = model_name

            # 模型类型与能力标签
            model_type = final_conf_dict.get("model_type")
            if not model_type:
                model_type = "llm"
            final_conf_dict["model_type"] = model_type

            capabilities = final_conf_dict.get("capabilities")
            if not capabilities:
                capabilities = []
                # 兼容旧配置：is_multimodal -> vision
                if final_conf_dict.get("is_multimodal") or final_conf_dict.get("supports_vision"):
                    capabilities.append("vision")
            # 去重并保持为列表
            capabilities = list(dict.fromkeys(capabilities))
            if "text" not in capabilities:
                capabilities.insert(0, "text")
            final_conf_dict["capabilities"] = capabilities

            is_multimodal = m_conf.get(
                "is_multimodal", m_conf.get("supports_vision", False)
            )
            final_conf_dict["is_multimodal"] = bool(is_multimodal)

            api_key_ref = final_conf_dict.get("api_key_ref", "")
            if api_key_ref and not final_conf_dict.get("api_key"):
                try:
                    from gyra_core.config.encryption import (
                        ConfigReferenceResolver,
                    )

                    resolved_value = ConfigReferenceResolver.resolve(api_key_ref)
                    if resolved_value and isinstance(resolved_value, str):
                        final_conf_dict["api_key"] = resolved_value
                        logger.debug(
                            f"[parse_provider_configs] Resolved api_key_ref for {provider_name}/{model_name}: "
                            f"{resolved_value[:8]}...{resolved_value[-4:] if len(resolved_value) > 12 else ''}"
                        )
                except Exception as e:
                    logger.warning(
                        f"[parse_provider_configs] Failed to resolve api_key_ref for {provider_name}/{model_name}: {e}"
                    )

            config_key = f"{provider_name}/{model_name}"
            # 遗留迁移：把误填进 max_new_tokens 的上下文空间迁回 context_window
            _migrate_legacy_token_fields(final_conf_dict)
            model_configs[config_key] = final_conf_dict

    logger.info(
        f"[parse_provider_configs] Total registered: {len(model_configs)} models"
    )
    if model_configs:
        logger.info(
            f"[parse_provider_configs] Registered models: {list(model_configs.keys())}"
        )
    else:
        logger.warning("[parse_provider_configs] No models were registered!")

    return model_configs
