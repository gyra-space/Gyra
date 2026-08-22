"""Plan mode seam（对齐 DSH ``ctx.planMode``）。

V2 plan 模式：
  - 模型进入 "plan only" 状态（不再发 tool_call，只输出 plan/step 文本）；
  - run_loop 收到 ``plan/start`` 事件后切换 PlanModeFilter 中间件；
  - plan/step 折叠为单一 plan state，结束后 ``plan/finish`` 折叠入最后一条消息。

事件类型（已注册到 :class:`EventRegistry`）：
  - ``plan/start``（surface=True）：进入 plan 模式；
  - ``plan/step``（surface=True）：plan 步骤文本（折叠入 plan 状态）；
  - ``plan/finish``（surface=True）：plan 完成（折叠为最后一步）。

折叠规则：所有 plan 阶段事件用同一个 ``_surface_node_id="plan"`` 标记，
``_surface_op="replace"`` 由 projector 折叠为最新的 ``plan/finish`` 消息。
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

from gyra.agent.core.v2.event_registry import (
    EventRegistry,
    ProjectorFn,
    get_event_registry,
    register_event_type,
    register_post_init_hook,
)
from gyra.agent.core.v2.projector_registry import get_projector_registry
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


# ------------------------------------------------------------------
# PlanState：当前会话 plan 状态
# ------------------------------------------------------------------

@dataclass
class PlanStep:
    seq: int
    text: str
    timestamp: float


@dataclass
class PlanState:
    """当前会话的 plan 状态（in-memory，agent 级别）。"""
    active: bool = False
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    steps: List[PlanStep] = field(default_factory=list)
    final_text: Optional[str] = None  # 折叠为最终 plan 消息

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active": self.active,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "step_count": len(self.steps),
            "final_text": self.final_text,
        }


# ------------------------------------------------------------------
# PlanManager：plan 模式状态管理 + 事件发射
# ------------------------------------------------------------------

EmitFn = Callable[..., Awaitable[Any]]


class PlanManager:
    """Plan 模式状态机 + 事件发射。

    用法::

        plan = PlanManager(emit=emit_fn, step_id=step_id)
        await plan.start("设计新功能")
        await plan.add_step("1. 收集需求")
        await plan.add_step("2. 实现")
        await plan.finish("准备进入执行阶段")
    """

    SURFACE_NODE_ID = "plan"

    def __init__(
        self,
        *,
        emit: EmitFn,
        step_id: str = "step-unknown",
        state: Optional[PlanState] = None,
    ) -> None:
        self._emit = emit
        self._step_id = step_id
        self._state = state or PlanState()

    @property
    def state(self) -> PlanState:
        return self._state

    @property
    def active(self) -> bool:
        return self._state.active

    async def start(self, plan_summary: str) -> StepEvent:
        """进入 plan 模式。"""
        self._state.active = True
        self._state.started_at = time.time()
        return await self._emit(
            StepState.THINKING,
            "plan/start",
            input_data={"summary": plan_summary},
            output_data={
                "text": plan_summary,
                # replace_shadow：所有 plan 阶段折叠为最新 plan/finish
                "_surface_node_id": self.SURFACE_NODE_ID,
                "_surface_op": "append",  # start 之后还有 step/finish
            },
        )

    async def add_step(self, text: str) -> StepEvent:
        """追加 plan 步骤。"""
        if not self._state.active:
            raise RuntimeError("PlanManager.add_step called before start()")
        seq = len(self._state.steps) + 1
        self._state.steps.append(PlanStep(seq=seq, text=text, timestamp=time.time()))
        return await self._emit(
            StepState.THINKING,
            "plan/step",
            input_data={"text": text},
            output_data={
                "text": text,
                "seq": seq,
                "_surface_node_id": self.SURFACE_NODE_ID,
                "_surface_op": "append",
            },
        )

    async def finish(self, final_text: Optional[str] = None) -> StepEvent:
        """完成 plan 模式。"""
        if not self._state.active:
            raise RuntimeError("PlanManager.finish called before start()")
        self._state.finished_at = time.time()
        if not final_text:
            # 默认拼接 step 列表
            final_text = self.format_plan()
        self._state.final_text = final_text
        self._state.active = False
        return await self._emit(
            StepState.THINKING,
            "plan/finish",
            input_data={"text": final_text},
            output_data={
                "text": final_text,
                "step_count": len(self._state.steps),
                # 折叠所有 plan/* 消息为最新这条
                "_surface_node_id": self.SURFACE_NODE_ID,
                "_surface_op": "replace",
            },
        )

    def format_plan(self) -> str:
        """格式化 plan 为纯文本（注入 LLM 用）。"""
        lines = []
        if self._state.steps:
            lines.append("Plan 步骤：")
            for s in self._state.steps:
                lines.append(f"  {s.seq}. {s.text}")
        if self._state.final_text and self._state.final_text not in lines:
            lines.append("")
            lines.append(f"完成：{self._state.final_text}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# 默认 plan 投影器（已在 projector_registry 注册）
# ------------------------------------------------------------------

def project_plan_start(event: StepEvent) -> Optional[dict]:
    return _project_plan_event(event, role_label="Plan 启动")


def project_plan_step(event: StepEvent) -> Optional[dict]:
    return _project_plan_event(event, role_label="Plan 步骤")


def project_plan_finish(event: StepEvent) -> Optional[dict]:
    return _project_plan_event(event, role_label="Plan 完成")


def _project_plan_event(event: StepEvent, *, role_label: str) -> Optional[dict]:
    text = (event.output or {}).get("text") or (event.input or {}).get("text")
    if not text:
        return None
    return {
        "role": "system",
        "content": f"[{role_label}] {text}",
    }


# ------------------------------------------------------------------
# 默认初始化：把 plan 事件注册到 EventRegistry
# ------------------------------------------------------------------

def _ensure_plan_events_registered(reg: Optional[EventRegistry] = None) -> None:
    """挂载 plan/* 投影器到 EventRegistry（幂等 + reset-safe）。

    兼容两种调用方式：
      1. 模块导入期直接调用（不带参数）：执行一次性挂载；
      2. 注册为 post_init_hook（registry reset 后被自动调用）：保证
         测试调用 ``reset_event_registry`` 后仍能恢复。
    """
    if reg is None:
        reg = get_event_registry()
    for name, fn in (
        ("plan/start", project_plan_start),
        ("plan/step", project_plan_step),
        ("plan/finish", project_plan_finish),
    ):
        existing = reg.get(name)
        if existing is None:
            register_event_type(
                name, is_surface=True, category="plan", projector_fn=fn,
            )
        elif existing.projector_fn is None:
            reg.set_projector(name, fn)


_ensure_plan_events_registered()
register_post_init_hook(_ensure_plan_events_registered)
