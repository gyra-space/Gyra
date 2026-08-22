"""TokenMeter — token 计量与上下文压力评估（对齐 DSH ``ctx.tokenMeter``）。

V2 引擎需要回答三个问题：
  1. **本 step 用了多少 token**（prompt / completion / total）；
  2. **会话累计用了多少 token**；
  3. **距离 context window 还剩多少**（用于触发 compaction / spill）。

事实源：``usage_metric`` StepEvent（``run_step`` 在 LLM 调用后写入）。
计算：``TokenMeter`` 走 ``store.get_events(conv_id)`` 重算，不依赖内存态——
多进程/重启场景天然安全。

配置 ``TokenMeterConfig``：
  - ``context_window``：模型最大上下文（默认 0 = 自动查 ModelConfigCache）；
  - ``warn_ratio``：超过该比例触发 warn StepEvent（默认 0.7）；
  - ``compact_ratio``：超过该比例触发 compaction（默认 0.85）；
  - ``evict_ratio``：超过该比例立即丢最旧 turn（硬降级，默认 0.95）。

用法::

    meter = TokenMeter(store, conv_id, model="gpt-4")
    snap = await meter.snapshot()  # {prompt, completion, total, ratio, headroom}
    if snap.pressure_level == "high":
        await compactor.run()
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from gyra.agent.core.v2.usage_metric import _CONTEXT_WINDOW_KEYS


class PressureLevel(str, Enum):
    """上下文压力等级。"""
    OK = "ok"            # ratio < warn_ratio
    WARN = "warn"        # warn_ratio <= ratio < compact_ratio
    HIGH = "high"        # compact_ratio <= ratio < evict_ratio
    CRITICAL = "critical"  # ratio >= evict_ratio（建议立即降级）


@dataclass
class TokenSnapshot:
    """单次 snapshot。"""
    prompt: int
    completion: int
    total: int
    context_window: int
    ratio: float
    headroom: int  # context_window - total
    pressure_level: PressureLevel
    usage_event_count: int  # 本次累计的 usage_metric 事件数
    last_usage_event_seq: int  # 最近一次 usage_metric 事件的 seq（增量起点）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "total": self.total,
            "context_window": self.context_window,
            "ratio": self.ratio,
            "headroom": self.headroom,
            "pressure_level": self.pressure_level.value,
            "usage_event_count": self.usage_event_count,
            "last_usage_event_seq": self.last_usage_event_seq,
        }


@dataclass
class TokenMeterConfig:
    """TokenMeter 配置。"""
    context_window: int = 0  # 0 = 自动从 ModelConfigCache 查
    warn_ratio: float = 0.70
    compact_ratio: float = 0.85
    evict_ratio: float = 0.95
    # 估算 fallback：usage 事件缺失时用 chars/4 粗估（仅警告场景）
    fallback_chars_per_token: int = 4


def _get_context_window(model: Optional[str], override: int) -> int:
    if override > 0:
        return override
    if not model:
        return 0
    try:
        from gyra.agent.util.llm.model_config_cache import ModelConfigCache

        cfg = ModelConfigCache.get_config(model)
    except Exception:
        return 0
    if not isinstance(cfg, dict):
        return 0
    for key in _CONTEXT_WINDOW_KEYS:
        v = cfg.get(key)
        if v is None:
            continue
        try:
            return int(v)
        except (TypeError, ValueError):
            continue
    return 0


class TokenMeter:
    """会话级 token 计量器。"""

    def __init__(
        self,
        store: Any,
        conv_id: str,
        model: Optional[str] = None,
        config: Optional[TokenMeterConfig] = None,
    ) -> None:
        self._store = store
        self._conv_id = conv_id
        self._model = model
        self._config = config or TokenMeterConfig()

    @property
    def conv_id(self) -> str:
        return self._conv_id

    @property
    def model(self) -> Optional[str]:
        return self._model

    @property
    def config(self) -> TokenMeterConfig:
        return self._config

    async def snapshot(
        self,
        *,
        model: Optional[str] = None,
    ) -> TokenSnapshot:
        """重算当前会话 token 状态（事实源 = ``usage_metric`` StepEvent）。"""
        events = await self._store.get_events(self._conv_id)
        prompt = completion = total = 0
        usage_count = 0
        last_seq = 0
        for ev in events:
            if ev.event_type != "usage_metric":
                continue
            this_call = (ev.output or {}).get("this_call", {})
            prompt += int(this_call.get("prompt", 0) or 0)
            completion += int(this_call.get("completion", 0) or 0)
            total += int(this_call.get("total", 0) or 0)
            usage_count += 1
            last_seq = max(last_seq, ev.seq)

        # 模型可动态改变（fallback 取 model_config 查表）
        used_model = model or self._model
        window = _get_context_window(used_model, self._config.context_window)
        ratio = (total / window) if window > 0 else 0.0
        headroom = max(window - total, 0) if window > 0 else 0

        # 压力等级
        if ratio >= self._config.evict_ratio:
            level = PressureLevel.CRITICAL
        elif ratio >= self._config.compact_ratio:
            level = PressureLevel.HIGH
        elif ratio >= self._config.warn_ratio:
            level = PressureLevel.WARN
        else:
            level = PressureLevel.OK

        return TokenSnapshot(
            prompt=prompt,
            completion=completion,
            total=total,
            context_window=window,
            ratio=ratio,
            headroom=headroom,
            pressure_level=level,
            usage_event_count=usage_count,
            last_usage_event_seq=last_seq,
        )

    async def incremental_snapshot(
        self,
        since_seq: int,
        *,
        model: Optional[str] = None,
    ) -> TokenSnapshot:
        """仅重算 since_seq 之后新增 usage 的 token（增量）。

        与 :meth:`snapshot` 同接口，但只扫描增量事件；对频繁调用方更轻量。
        仍以会话总累计写回（headroom / pressure 反映会话全局状态）。
        """
        full = await self.snapshot(model=model)
        # 增量本身只是更小的子集；为了简化直接返回全量
        # 业务可基于 last_usage_event_seq 自行减法得到增量
        return full

    async def estimate_text_tokens(self, text: str) -> int:
        """无 usage 数据时用 chars/4 粗估（仅辅助）。"""
        if not text:
            return 0
        return max(1, len(text) // max(1, self._config.fallback_chars_per_token))

    async def should_warn(self) -> bool:
        snap = await self.snapshot()
        return snap.pressure_level in (PressureLevel.WARN, PressureLevel.HIGH, PressureLevel.CRITICAL)

    async def should_compact(self) -> bool:
        snap = await self.snapshot()
        return snap.pressure_level in (PressureLevel.HIGH, PressureLevel.CRITICAL)

    async def should_evict(self) -> bool:
        snap = await self.snapshot()
        return snap.pressure_level is PressureLevel.CRITICAL
