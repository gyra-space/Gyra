"""ContextManager — V2 上下文生命周期管理（token meter + spill + compaction）。

把 :class:`TokenMeter` / :class:`SpillManager` / :class:`Compactor` 三个能力
编排为一个统一入口，让 :class:`V2AgentRuntime` / :class:`run_loop` 在 turn 收尾
自动检测压力、裁剪超大消息、按需压缩历史。

**典型用法**（V2AgentRuntime 装配时）::

    ctx_manager = ContextManager(
        store=state_store,
        event_stream=event_stream,
        model="gpt-4",
        spill_manager=spill_manager,
        compactor=compactor,
    )
    # run_step 前：spill 工具结果（如已配置）
    # run_step 后：may_compact（自动判定 + 执行）
"""
from __future__ import annotations

import dataclasses
from typing import Any, Awaitable, Callable, Dict, List, Optional

from gyra.agent.core.v2.compaction import (
    Compactor,
    CompactionPolicy,
    CompactionResult,
    HeuristicSummarizer,
    LLMSummarizer,
)
from gyra.agent.core.v2.spill import SpillManager
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.token_meter import (
    PressureLevel,
    TokenMeter,
    TokenMeterConfig,
    TokenSnapshot,
)


@dataclasses.dataclass
class ContextManagerConfig:
    """ContextManager 配置。"""
    # Token meter
    token_meter: TokenMeterConfig = dataclasses.field(default_factory=TokenMeterConfig)
    # Spill
    enable_spill: bool = True
    spill_max_inline_chars: int = 20000
    # Compaction
    enable_compaction: bool = True
    compaction_policy: CompactionPolicy = dataclasses.field(default_factory=CompactionPolicy)
    # 是否在每 step 后自动检查（V2AgentRuntime 装配时由 run_loop 调用）
    auto_check_after_step: bool = True


class ContextManager:
    """V2 上下文生命周期管理。"""

    def __init__(
        self,
        *,
        store: Any,
        event_stream: Any,
        model: Optional[str] = None,
        conv_id: Optional[str] = None,
        spill_manager: Optional[SpillManager] = None,
        compactor: Optional[Compactor] = None,
        llm_summarizer: Optional[LLMSummarizer] = None,
        config: Optional[ContextManagerConfig] = None,
        emit_fn: Optional[Callable[..., Awaitable[Any]]] = None,
        step_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        self._store = store
        self._event_stream = event_stream
        self._model = model
        self._conv_id = conv_id
        self._config = config or ContextManagerConfig()
        self._token_meter = TokenMeter(
            store, conv_id or "default", model=model, config=self._config.token_meter,
        )
        # spill_manager 缺省按需创建（外部可注入复用）
        if spill_manager is not None:
            self._spill = spill_manager
        else:
            try:
                from gyra.agent.core.v2.spill import create_default_spill_manager
                self._spill = create_default_spill_manager()
            except Exception:  # noqa: BLE001
                self._spill = None

        # compactor 缺省构建（延后到 conv_id / step_id 已知时再构造）
        self._compactor = compactor
        self._llm_summarizer = llm_summarizer
        self._emit_fn = emit_fn
        self._step_id = step_id or "step-unknown"
        self._agent_id = agent_id or "agent-unknown"

    # ------------------------------------------------------------------
    # 访问器
    # ------------------------------------------------------------------

    @property
    def token_meter(self) -> TokenMeter:
        return self._token_meter

    @property
    def spill(self) -> Optional[SpillManager]:
        return self._spill

    @property
    def compactor(self) -> Optional[Compactor]:
        return self._compactor

    @property
    def config(self) -> ContextManagerConfig:
        return self._config

    # ------------------------------------------------------------------
    # 步骤前：spill 工具结果
    # ------------------------------------------------------------------

    async def pre_step(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """run_step 前处理：spill 超大工具结果，避免压爆 LLM 上下文。"""
        if not self._config.enable_spill or self._spill is None:
            return messages
        if not messages:
            return messages
        return self._spill.compact_tool_results(messages)

    # ------------------------------------------------------------------
    # 步骤后：自动判定 + compaction
    # ------------------------------------------------------------------

    async def post_step(
        self,
        *,
        step_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        turn_count: int = 0,
    ) -> Dict[str, Any]:
        """run_step 后调用：自动判定 token 压力 + 触发 compaction。

        返回 ``{snapshot, compaction}`` 供 V2AgentRuntime 观测/记录。
        """
        used_step_id = step_id or self._step_id
        used_agent_id = agent_id or self._agent_id
        result: Dict[str, Any] = {
            "snapshot": None,
            "compaction": None,
            "pressure_warning": False,
        }
        snap = await self._token_meter.snapshot(model=self._model)
        result["snapshot"] = snap.to_dict()
        if snap.pressure_level in (PressureLevel.WARN, PressureLevel.HIGH, PressureLevel.CRITICAL):
            result["pressure_warning"] = True

        if not self._config.enable_compaction:
            return result

        compactor = self._ensure_compactor(
            step_id=used_step_id, agent_id=used_agent_id,
        )
        # 可能被 force 触发：转交 compactor 内部判定
        # （force_compact_every_n_turns 由 policy.should_trigger_by_force(turn_count) 决定）
        if self._config.compaction_policy.should_trigger_by_force(turn_count):
            comp_result = await compactor.run(force=False)
        else:
            comp_result = await compactor.maybe_run()
        result["compaction"] = comp_result.to_dict()
        return result

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _ensure_compactor(
        self,
        *,
        step_id: str,
        agent_id: str,
    ) -> Compactor:
        if self._compactor is not None and self._compactor._step_id == step_id:
            return self._compactor
        # 重建（不同 step 时切换 step_id）
        emit = self._emit_fn
        self._compactor = Compactor(
            store=self._store,
            emit=emit,
            conv_id=self._conv_id or "default",
            agent_id=agent_id,
            step_id=step_id,
            llm_summarizer=self._llm_summarizer,
            policy=self._config.compaction_policy,
            model=self._model,
            token_meter=self._token_meter,
        )
        return self._compactor

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def get_context_summary(self) -> Dict[str, Any]:
        """快速返回当前配置（不读 events，仅元信息）。"""
        return {
            "model": self._model,
            "enable_spill": self._config.enable_spill,
            "enable_compaction": self._config.enable_compaction,
            "warn_ratio": self._config.token_meter.warn_ratio,
            "compact_ratio": self._config.token_meter.compact_ratio,
            "evict_ratio": self._config.token_meter.evict_ratio,
            "min_keep_recent_turns": self._config.compaction_policy.min_keep_recent_turns,
        }
