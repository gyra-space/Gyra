"""PR 8: 会话级 usage 聚合。

V1 已有 ModelInferenceMetrics（每次 LLM 调用记录 prompt/completion/total_tokens），
持久化在 gpts_messages.metrics JSON。本模块补会话级聚合：
- aggregate_usage(conv_id): 扫 gpts_messages.metrics，按 model/role 聚合
- emit_usage_metric: 单次 LLM 调用 usage 记录（可选，写入内存聚合 buffer）
- estimate_cost: 用 model_pricing 表估算成本

设计为只读聚合（不写 DB），避免侵入 V1 现有 metrics 持久化路径。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from gyra.agent.core.model_pricing import get_pricing

logger = logging.getLogger(__name__)

# 本地缓存 tiktoken 词表：优先读取代码目录下捆绑的 cl100k_base 词表，避免运行时联网下载。
# 若外部已显式设置 TIKTOKEN_CACHE_DIR，则尊重外部配置（setdefault 不覆盖）。
_TIKTOKEN_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "tiktoken_cache"
)
try:
    os.makedirs(_TIKTOKEN_CACHE_DIR, exist_ok=True)
except OSError:  # noqa: BLE001
    pass
os.environ.setdefault("TIKTOKEN_CACHE_DIR", _TIKTOKEN_CACHE_DIR)

# 缓存 tiktoken encoding，避免每次调用重复初始化/下载
_tiktoken_encoding = None


def count_tokens(text: str) -> int:
    """实时计算一段文本的 token 数。

    计算规则（优先级从上到下）：
    1. 若 tiktoken 可用，用 cl100k_base 精确切分（真实 token 数）；
    2. tokenizer 不可用/失败时，兜底按「字符数/4」推算。
    """
    if not text:
        return 0
    global _tiktoken_encoding
    try:
        if _tiktoken_encoding is None:
            import tiktoken

            _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
        return max(1, len(_tiktoken_encoding.encode(text)))
    except Exception:  # noqa: BLE001
        return max(1, len(text) // 4)


def warmup_tokenizer() -> bool:
    """预热 tiktoken tokenizer（best-effort）。

    首次 get_encoding 需要加载/下载 BPE 文件（可能联网），预热可把这一
    一次性成本挪到启动阶段，避免首个请求在热路径上同步等待。失败时静默
    返回 False，运行期 count_tokens 仍会退化到「字符/4」兜底。
    """
    global _tiktoken_encoding
    try:
        if _tiktoken_encoding is None:
            import tiktoken

            _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
        return True
    except Exception:  # noqa: BLE001
        logger.debug("[usage] tokenizer warmup skipped")
        return False


@dataclass
class ConversationUsage:
    """会话级 usage 聚合。"""
    conv_id: str
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    total_cost_usd: float = 0.0
    by_model: Dict[str, int] = field(default_factory=dict)  # model_name -> total_tokens
    by_role: Dict[str, int] = field(default_factory=dict)  # main/subagent -> total_tokens
    last_model_name: str = ""  # 最近一次 LLM 调用的模型名，用于估算 context_window

    def add_call(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        role: str = "main",
    ) -> None:
        """累加一次 LLM 调用。"""
        prompt_tokens = prompt_tokens or 0
        completion_tokens = completion_tokens or 0
        call_total = prompt_tokens + completion_tokens

        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += call_total
        self.total_llm_calls += 1
        if model_name:
            self.last_model_name = model_name

        if model_name:
            self.by_model[model_name] = self.by_model.get(model_name, 0) + call_total
        self.by_role[role] = self.by_role.get(role, 0) + call_total
        self.total_cost_usd += estimate_cost(
            model_name, prompt_tokens, completion_tokens
        )


# PR 8: in-memory usage buffer，供 emit_usage_metric 实时累加
# conv_id -> ConversationUsage
_usage_buffers: Dict[str, ConversationUsage] = {}

# 按会话注册的 usage 回调，用于实时推送 SSE（例如 Agent 空间上下文用量环形图）
# conv_id -> Callable[[ConversationUsage], None]
UsageCallback = Callable[[ConversationUsage], None]
_usage_callbacks: Dict[str, UsageCallback] = {}


def register_usage_callback(conv_id: str, callback: UsageCallback) -> None:
    """注册一个会话的 usage 更新回调。"""
    if conv_id:
        _usage_callbacks[conv_id] = callback


def unregister_usage_callback(conv_id: str) -> None:
    """注销会话的 usage 回调。"""
    _usage_callbacks.pop(conv_id, None)


def get_context_window(model_name: str) -> int:
    """根据模型名估算 context window。

    优先读取 ModelConfigCache 中的上下文长度字段；未命中时回退常见默认值 128000。
    """
    if not model_name:
        return 128000
    try:
        from gyra.agent.util.llm.model_config_cache import ModelConfigCache

        cfg = ModelConfigCache.get_config(model_name)
        if cfg:
            # 仅认上下文空间语义的字段；max_tokens/max_new_tokens 是输出上限，不能当上下文窗口
            for key in (
                "context_window",
                "context_length",
                "max_context_length",
                "max_context_len",
                "max_context_window",
            ):
                val = cfg.get(key)
                if isinstance(val, int) and val > 0:
                    return val
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[usage] get_context_window failed for {model_name}: {e}")
    return 128000


def emit_usage_metric(
    conv_id: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    role: str = "main",
) -> None:
    """记录一次 LLM 调用的 usage 到 in-memory buffer。

    供 llm_client / base_agent 在 LLM 调用结束后调用。
    fire-and-forget：异常只 log warning，不影响 LLM 调用路径。
    若注册了回调，更新 buffer 后会触发回调（异常同样吞掉）。
    """
    if not conv_id:
        return
    try:
        usage = _usage_buffers.get(conv_id)
        if usage is None:
            usage = ConversationUsage(conv_id=conv_id)
            _usage_buffers[conv_id] = usage
        usage.add_call(
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            role=role,
        )
        callback = _usage_callbacks.get(conv_id)
        if callback is not None:
            try:
                callback(usage)
            except Exception as cb_err:  # noqa: BLE001
                logger.warning(f"[usage] callback failed conv={conv_id}: {cb_err}")
    except Exception as e:
        logger.warning(
            f"[usage] emit failed conv={conv_id} model={model_name}: {e}"
        )


def emit_context_usage(
    conv_id: str,
    total_tokens: int,
    context_window: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model_name: str = "",
    system_prompt_tokens: int = 0,
    history_tokens: int = 0,
    user_message_tokens: int = 0,
    layer_tokens: Optional[Dict[str, int]] = None,
) -> None:
    """推送**当前上下文空间占用**快照到已注册回调（供环形图展示当前占用）。

    注意与 emit_usage_metric 的区别：
    - emit_usage_metric: 累计 LLM 调用 token 消耗（prompt+completion 累加），用于
      会话级用量/成本统计。
    - emit_context_usage: 反映**当前这一轮真正加载进上下文的 message+tool 占用**，
      是「当前上下文窗口已用/占比」而非累计消耗。非累计，每次为独立快照。

    除整体占用外，还携带明细分类（供前端环形图 tooltip 与详情抽屉展示）：
    - prompt_tokens: 全部消息 token（system + history + 当前用户消息）
    - completion_tokens: 工具列表 token
    - system_prompt_tokens / history_tokens / user_message_tokens: 消息内部分类
    - layer_tokens: 分层 compressed/retained 的 token 占用

    明细统一写入 by_model["__context_detail__"]，由回调读取后透传给 SSE payload。
    若传入 context_window>0 一并写入，否则回调按 last_model_name 自行估算。
    """
    if not conv_id:
        return
    try:
        usage = ConversationUsage(conv_id=conv_id)
        usage.total_tokens = int(total_tokens or 0)
        usage.total_prompt_tokens = int(prompt_tokens or 0)
        usage.total_completion_tokens = int(completion_tokens or 0)
        usage.total_llm_calls = 1
        usage.last_model_name = model_name or ""
        if context_window and context_window > 0:
            usage.by_model["__context_window__"] = int(context_window)
        usage.by_model["__context_detail__"] = {
            "prompt": int(prompt_tokens or 0),
            "completion": int(completion_tokens or 0),
            "system": int(system_prompt_tokens or 0),
            "history": int(history_tokens or 0),
            "user_msg": int(user_message_tokens or 0),
            "tools": int(completion_tokens or 0),
            "layers": {
                "compressed": int((layer_tokens or {}).get("compressed") or 0),
                "retained": int((layer_tokens or {}).get("retained") or 0),
            },
        }
        callback = _usage_callbacks.get(conv_id)
        if callback is not None:
            try:
                callback(usage)
            except Exception as cb_err:  # noqa: BLE001
                logger.warning(
                    f"[usage] context callback failed conv={conv_id}: {cb_err}"
                )
    except Exception as e:
        logger.warning(f"[usage] emit_context failed conv={conv_id}: {e}")


def get_in_memory_usage(conv_id: str) -> Optional[ConversationUsage]:
    """读 in-memory buffer。无则 None。"""
    return _usage_buffers.get(conv_id)


def clear_in_memory_usage(conv_id: str) -> None:
    """清空 conv_id 的 in-memory buffer（会话结束时调用）。"""
    _usage_buffers.pop(conv_id, None)


def estimate_cost(
    model_name: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """用 model_pricing 估算成本（USD）。

    Args:
        model_name: 模型名（用于查定价表）
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数

    Returns:
        USD 成本，未知模型返回 0.0
    """
    if not model_name:
        return 0.0
    prompt_per_1m, completion_per_1m = get_pricing(model_name)
    return (
        (prompt_tokens or 0) * prompt_per_1m / 1_000_000
        + (completion_tokens or 0) * completion_per_1m / 1_000_000
    )


def _extract_llm_tokens(metrics_dict: Dict[str, Any]) -> tuple[int, int, int]:
    """从 MessageMetrics dict 提取 (prompt, completion, total) tokens。

    MessageMetrics 结构：{llm_metrics: {prompt_tokens, completion_tokens, total_tokens}, ...}
    """
    llm = metrics_dict.get("llm_metrics") or {}
    prompt = llm.get("prompt_tokens") or 0
    completion = llm.get("completion_tokens") or 0
    total = llm.get("total_tokens") or (prompt + completion)
    return (prompt, completion, total)


def aggregate_usage_from_messages(
    conv_id: str,
    messages: List[Any],
    role_resolver=None,
) -> ConversationUsage:
    """从 GptsMessage 列表聚合 usage。

    Args:
        conv_id: 会话 ID
        messages: GptsMessage 列表（或具有 model_name + metrics 字段的 duck-typed 对象）
        role_resolver: optional callable(msg) -> "main" | "subagent"，None 时全按 "main"

    Returns:
        ConversationUsage
    """
    usage = ConversationUsage(conv_id=conv_id)
    for msg in messages:
        model_name = getattr(msg, "model_name", None)
        metrics = getattr(msg, "metrics", None)
        if metrics is None:
            continue

        # metrics 可能是 dict / str / MessageMetrics 对象
        metrics_dict: Dict[str, Any]
        if isinstance(metrics, str):
            try:
                metrics_dict = json.loads(metrics)
            except Exception:
                continue
        elif isinstance(metrics, dict):
            metrics_dict = metrics
        elif hasattr(metrics, "to_dict"):
            metrics_dict = metrics.to_dict()
        else:
            continue

        prompt, completion, total = _extract_llm_tokens(metrics_dict)
        if total == 0:
            continue

        role = "main"
        if role_resolver is not None:
            try:
                role = role_resolver(msg) or "main"
            except Exception:
                role = "main"

        usage.add_call(
            model_name=model_name or "unknown",
            prompt_tokens=prompt,
            completion_tokens=completion,
            role=role,
        )
    return usage


async def aggregate_usage(conv_id: str) -> ConversationUsage:
    """异步聚合：从 DB 读 gpts_messages 聚合 usage。

    Lazy import 避免循环依赖（gyra-core → gyra-serve）。
    """
    from gyra_serve.agent.db.gpts_messages_db import GptsMessagesDao

    dao = GptsMessagesDao()
    messages = await dao.get_by_conv_id(conv_id)
    return aggregate_usage_from_messages(conv_id, messages)


def format_usage_log(usage: ConversationUsage) -> str:
    """格式化 usage 为一行日志。"""
    return (
        f"[usage] conv={usage.conv_id} "
        f"calls={usage.total_llm_calls} "
        f"prompt={usage.total_prompt_tokens} "
        f"completion={usage.total_completion_tokens} "
        f"total={usage.total_tokens} "
        f"cost=${usage.total_cost_usd:.4f} "
        f"by_model={usage.by_model} "
        f"by_role={usage.by_role}"
    )
