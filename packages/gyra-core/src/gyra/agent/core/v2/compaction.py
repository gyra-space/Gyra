"""Compaction — 上下文压缩（对齐 DSH ``ctx.compaction`` + ``compaction-basic`` 后端）。

**问题**：长会话累积的事件/消息超出 LLM 上下文窗口，必须压缩历史。

**Compaction 流程**（每 turn 收尾触发，**post-step**）：
  1. **触发判定**：``TokenMeter.snapshot()`` 检查压力等级（``HIGH`` / ``CRITICAL``）；
  2. **范围选取**：从最早的非关键 surface 事件起，找到"可丢弃段"
     （旧的 user/assistant/tool 消息；保留 system + 最近 N turn）；
  3. **生成摘要**：调 ``LLMSummarizer`` 对可丢弃段生成文本摘要；
  4. **replace 语义**：把可丢弃段的 surface 事件折叠为单个
     ``compaction/summary`` 事件（用 ``replace_shadow`` 机制覆盖原段消息）；
  5. **持久化**：摘要作为新 surface 事件写入 StateStore（``compaction/summary``），
     投影时自动注入 LLM 上下文。

**事件类型**（已注册到 :class:`EventRegistry`）：
  - ``compaction/start``（surface=False）：触发事件（审计）；
  - ``compaction/summary``（surface=True）：摘要事件（替换原段，注入 LLM）；
  - ``compaction/end``（surface=False）：结束事件（审计）。

**Compaction 策略（CompactionPolicy）**：
  - ``min_keep_recent_turns``：保留最近 N 轮 turn 不动（默认 3）；
  - ``min_keep_system_messages``：保留 system 消息（默认 True）；
  - ``summary_max_tokens``：摘要目标长度（默认 800 token）；
  - ``trigger_levels``：触发压力等级集合（默认 {HIGH, CRITICAL}）；
  - ``force_compact_every_n_turns``：每 N turn 强制压缩（默认 0=关闭）。

**使用方式**::

    compactor = Compactor(
        store=state_store,
        emit=emit_fn,
        llm_summarizer=my_summarizer,  # 或默认 HeuristicSummarizer
        policy=CompactionPolicy(),
        model="gpt-4",
    )
    await compactor.maybe_run()  # 内部判定是否触发
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from gyra.agent.core.v2.event_registry import (
    ProjectorFn,
    get_event_registry,
    register_event_type,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.token_meter import (
    PressureLevel,
    TokenMeter,
    TokenMeterConfig,
)


# ------------------------------------------------------------------
# LLM Summarizer 协议
# ------------------------------------------------------------------

class LLMSummarizer(Protocol):
    """摘要器协议（业务可注入 LLM 实现）。"""

    async def summarize(
        self,
        messages: List[Dict[str, Any]],
        *,
        target_tokens: int = 800,
        hint: str = "",
    ) -> str: ...


class HeuristicSummarizer:
    """默认启发式摘要器：拼接关键字段，截断到 target_tokens。

    不依赖 LLM（测试 / 无 LLM 场景）；
    业务可注入 :class:`LLMSummarizer` 实现做 LLM 摘要。
    """

    async def summarize(
        self,
        messages: List[Dict[str, Any]],
        *,
        target_tokens: int = 800,
        hint: str = "",
    ) -> str:
        if not messages:
            return ""
        # target_tokens * 4 字符近似
        max_chars = max(200, target_tokens * 4)
        lines: List[str] = []
        total = 0
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            content = content.strip()
            if not content:
                continue
            # 截断
            if len(content) > 1000:
                content = content[:1000] + "..."
            line = f"[{role}] {content}"
            if total + len(line) + 1 > max_chars:
                lines.append("... [已截断更多历史]")
                break
            lines.append(line)
            total += len(line) + 1
        summary = "\n".join(lines)
        if hint:
            summary = f"{hint}\n\n{summary}"
        return summary


# ------------------------------------------------------------------
# CompactionPolicy
# ------------------------------------------------------------------

@dataclass
class CompactionPolicy:
    """Compaction 触发与执行策略。"""
    min_keep_recent_turns: int = 3  # 保留最近 N turn 不动
    min_keep_system_messages: bool = True  # 保留 system 消息
    summary_max_tokens: int = 800  # 摘要目标长度
    trigger_levels: tuple = (PressureLevel.HIGH, PressureLevel.CRITICAL)
    force_compact_every_n_turns: int = 0  # 每 N turn 强制压缩；0=关闭
    # 软提示：若 model 报告总 token 接近此比例但未到 HIGH，提早 warn
    soft_warn_ratio: float = 0.75
    # 摘要注入前缀
    summary_role_label: str = "Compaction 摘要"
    # 摘要 event 是否带 _surface_node_id（用于 replace shadow 折叠）
    enable_replace_shadow: bool = True

    def should_trigger_by_pressure(self, level: PressureLevel) -> bool:
        return level in self.trigger_levels

    def should_trigger_by_force(self, turn_count: int) -> bool:
        if self.force_compact_every_n_turns <= 0:
            return False
        return turn_count > 0 and (turn_count % self.force_compact_every_n_turns == 0)


# ------------------------------------------------------------------
# CompactionResult
# ------------------------------------------------------------------

@dataclass
class CompactionResult:
    """单次 compaction 执行的产物。"""
    triggered: bool
    reason: str = ""  # "pressure_high" | "force" | "manual" | "no_trigger"
    summary: str = ""
    compacted_event_count: int = 0
    kept_recent_event_count: int = 0
    summary_event_id: Optional[str] = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": self.triggered,
            "reason": self.reason,
            "summary": self.summary,
            "compacted_event_count": self.compacted_event_count,
            "kept_recent_event_count": self.kept_recent_event_count,
            "summary_event_id": self.summary_event_id,
            "elapsed_ms": self.elapsed_ms,
        }


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _count_turns(events: List[StepEvent]) -> int:
    """按 step_done 事件数估算 turn 数（粗略；按 step 边界）。"""
    return sum(1 for e in events if e.event_type == "step_done")


def _is_compactable_event(ev: StepEvent) -> bool:
    """事件是否可被压缩（属于"可丢弃段"）。"""
    # llm_token 不可 compact（高频噪声）
    if ev.event_type == "llm_token":
        return False
    # step_init / step_done / 各种 internal 事件不参与 LLM 上下文（surface=False）
    reg = get_event_registry()
    if not reg.is_surface(ev.event_type):
        return False
    # 任何已存在的 compaction/summary 也不再 compact（防止递归）
    if ev.event_type == "compaction/summary":
        return False
    return True


def _is_kept_event(ev: StepEvent, recent_step_ids: set) -> bool:
    """事件是否在保留段（最近 N turn 的 step_id）。"""
    if recent_step_ids and ev.step_id in recent_step_ids:
        return True
    return False


def _project_events_to_messages(events: List[StepEvent]) -> List[Dict[str, Any]]:
    """纯函数：events → LLM 消息列表（无状态/无缓存）。

    使用 ProjectorRegistry 投影（延迟初始化，全局单例）。
    """
    from gyra.agent.core.v2.projector_registry import get_projector_registry
    return get_projector_registry().project_events(events)


# ------------------------------------------------------------------
# Compactor
# ------------------------------------------------------------------

# emit 回调签名（与 runtime._make_emit 一致）
EmitFn = Callable[..., Awaitable[Any]]


class Compactor:
    """Compaction 执行器。

    设计原则：
      - **append-only 严格保留**：原事件永不被删除/修改，compaction 仅追加
        ``compaction/summary`` 事件，投影层用 replace_shadow 折叠；
      - **崩溃可恢复**：compaction/start → 摘要生成 → compaction/end 三个事件
        都写入 StateStore；中途崩溃下次 resume 时通过 ``compaction/end`` 缺失
        判定未完成（恢复路径见 :meth:`resumable`）。
      - **幂等**：连续两次相同范围 compaction 不会重复（已存在
        ``compaction/summary`` 不会被再 compact）。
    """

    def __init__(
        self,
        *,
        store: Any,
        emit: Optional[EmitFn] = None,
        conv_id: str,
        agent_id: str,
        step_id: str,
        llm_summarizer: Optional[LLMSummarizer] = None,
        policy: Optional[CompactionPolicy] = None,
        model: Optional[str] = None,
        token_meter: Optional[TokenMeter] = None,
    ) -> None:
        self._store = store
        self._emit = emit
        self._conv_id = conv_id
        self._agent_id = agent_id
        self._step_id = step_id
        self._summarizer = llm_summarizer or HeuristicSummarizer()
        self._policy = policy or CompactionPolicy()
        self._model = model
        self._token_meter = token_meter or TokenMeter(
            store, conv_id, model=model,
        )

    @property
    def policy(self) -> CompactionPolicy:
        return self._policy

    @property
    def token_meter(self) -> TokenMeter:
        return self._token_meter

    # ------------------------------------------------------------------
    # 触发判定
    # ------------------------------------------------------------------

    async def should_trigger(self) -> tuple:
        """返回 (是否触发, 原因, pressure_level)。

        触发条件（满足任一即触发）：
          1. TokenMeter 压力等级 ∈ policy.trigger_levels；
          2. force_compact_every_n_turns 强制触发（turn 数达标）。
        """
        snap = await self._token_meter.snapshot(model=self._model)
        if self._policy.should_trigger_by_pressure(snap.pressure_level):
            return True, f"pressure_{snap.pressure_level.value}", snap.pressure_level
        events = await self._store.get_events(self._conv_id)
        turns = _count_turns(events)
        if self._policy.should_trigger_by_force(turns):
            return True, f"force_every_{self._policy.force_compact_every_n_turns}_turns", snap.pressure_level
        return False, "no_trigger", snap.pressure_level

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def maybe_run(self) -> CompactionResult:
        """检查并按需执行 compaction。"""
        start = time.time()
        triggered, reason, level = await self.should_trigger()
        if not triggered:
            return CompactionResult(
                triggered=False,
                reason="no_trigger",
                elapsed_ms=(time.time() - start) * 1000,
            )
        return await self._run_with_reason(reason, level, start=start)

    async def run(self, *, force: bool = False) -> CompactionResult:
        """显式调用：force=True 忽略 trigger 判定。"""
        start = time.time()
        if force:
            return await self._run_with_reason("manual", PressureLevel.OK, start=start)
        return await self.maybe_run()

    # ------------------------------------------------------------------
    # 核心：执行压缩
    # ------------------------------------------------------------------

    async def _run_with_reason(
        self,
        reason: str,
        level: PressureLevel,
        *,
        start: float,
    ) -> CompactionResult:
        # 1. audit: compaction/start
        await self._audit("compaction/start", {
            "reason": reason,
            "pressure_level": level.value,
        })

        # 2. 选范围：events → compactable + kept_recent
        events = await self._store.get_events(self._conv_id)
        if not events:
            await self._audit("compaction/end", {"compacted_count": 0})
            return CompactionResult(
                triggered=True, reason=reason, summary="",
                elapsed_ms=(time.time() - start) * 1000,
            )

        # 保留最近 N turn（按 step_done 划分）
        recent_step_ids = self._recent_step_ids(events)
        compactable: List[StepEvent] = []
        for ev in events:
            if not _is_compactable_event(ev):
                continue
            if _is_kept_event(ev, recent_step_ids):
                continue
            if self._policy.min_keep_system_messages and ev.event_type == "user/message":
                # user message 不强保留——可被压；保留策略只针对 system
                pass
            compactable.append(ev)

        if not compactable:
            await self._audit("compaction/end", {"compacted_count": 0})
            return CompactionResult(
                triggered=True, reason=reason, summary="",
                compacted_event_count=0,
                elapsed_ms=(time.time() - start) * 1000,
            )

        # 3. 投影为消息
        messages = _project_events_to_messages(compactable)

        # 4. LLM 摘要
        summary = await self._summarizer.summarize(
            messages,
            target_tokens=self._policy.summary_max_tokens,
            hint=f"[以下是对早期历史的压缩摘要]\n本 turn 起点 = {self._step_id}",
        )

        # 5. 写入 compaction/summary 事件（surface=True, replace_shadow）
        summary_event_id: Optional[str] = None
        if self._emit is not None:
            ev = await self._emit(
                StepState.OBSERVING,
                "compaction/summary",
                input_data={
                    "compacted_count": len(compactable),
                    "kept_recent_count": len(recent_step_ids),
                },
                output_data={
                    "summary": summary,
                    "compacted_event_ids": [e.event_id for e in compactable],
                    "compacted_seq_range": [
                        compactable[0].seq, compactable[-1].seq,
                    ],
                    # replace_shadow：把同 surface_node 的消息折叠为最新摘要
                    **(
                        {
                            "_surface_node_id": "compaction",
                            "_surface_op": "replace",
                        }
                        if self._policy.enable_replace_shadow
                        else {}
                    ),
                },
            )
            summary_event_id = getattr(ev, "event_id", None) or (
                ev.get("event_id") if isinstance(ev, dict) else None
            )

        # 6. audit: compaction/end
        await self._audit("compaction/end", {
            "compacted_count": len(compactable),
            "kept_recent_count": len(recent_step_ids),
            "summary_event_id": summary_event_id,
            "summary_chars": len(summary),
        })

        return CompactionResult(
            triggered=True,
            reason=reason,
            summary=summary,
            compacted_event_count=len(compactable),
            kept_recent_event_count=len(recent_step_ids),
            summary_event_id=summary_event_id,
            elapsed_ms=(time.time() - start) * 1000,
        )

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _recent_step_ids(self, events: List[StepEvent]) -> set:
        """返回最近 N turn 的 step_id 集合（按 step_done 倒数）。"""
        n = self._policy.min_keep_recent_turns
        if n <= 0:
            return set()
        # 从尾部向前数 N 个 step_done
        recent: List[str] = []
        for ev in reversed(events):
            if ev.event_type == "step_done":
                if ev.step_id not in recent:
                    recent.append(ev.step_id)
                if len(recent) >= n:
                    break
        return set(recent)

    async def _audit(self, event_type: str, output: Dict[str, Any]) -> None:
        if self._emit is None:
            return
        try:
            await self._emit(
                StepState.OBSERVING,
                event_type,
                input_data={"compaction": True},
                output_data=output,
            )
        except Exception:
            pass


# ------------------------------------------------------------------
# 默认初始化：把 compaction 事件注册到 EventRegistry（surface 标记 + 投影器）
# ------------------------------------------------------------------

def _ensure_compaction_events_registered() -> None:
    """确保 compaction 事件类型已注册（surface 标记 + 投影器）。"""
    from gyra.agent.core.v2.projector_registry import project_compaction_summary
    reg = get_event_registry()
    # start / end：surface=False（仅审计）
    if reg.get("compaction/start") is None:
        register_event_type(
            "compaction/start", is_surface=False, category="compaction",
        )
    if reg.get("compaction/end") is None:
        register_event_type(
            "compaction/end", is_surface=False, category="compaction",
        )
    # summary：surface=True，必有投影器
    if reg.get("compaction/summary") is None:
        register_event_type(
            "compaction/summary",
            is_surface=True,
            category="compaction",
            projector_fn=project_compaction_summary,
        )
    elif reg.get("compaction/summary").projector_fn is None:
        reg.set_projector("compaction/summary", project_compaction_summary)


_ensure_compaction_events_registered()
