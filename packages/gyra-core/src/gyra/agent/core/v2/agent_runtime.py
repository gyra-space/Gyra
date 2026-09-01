"""V2AgentRuntime — V2 标准主 agent 的薄接口门面。

对应 dsh 的 Agent 接口思想：把"驱动循环 + LLM 交互 + 工具 + 权限 + 会话存储"
封装为一个薄门面，面向标准主 agent 提供统一的运行/渲染入口，同时保留
run_loop / run_step / resume_step 作为可组合的底层原语。

职责边界（只做编排，不做业务）：
  - 组装 thinking_fn / acting_fn / permission_gate / hook_manager
  - 运行 run_loop，产出 StepEvent 事件流
  - 将 StepEvent 转换为 StreamEvent / SSE 文本（前端渲染）
  - 记录 request/header 快照（可审计、可重放）

标准主 agent 通过该门面驱动，不再关心 run_step 内部状态机细节。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator, Awaitable, Callable, Dict, Iterable, List, Optional, Union

from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.run_loop import run_loop
from gyra.agent.core.v2.runtime import _resolve_harness_deps
from gyra.agent.core.v2.state_store import StateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.stream_event import StreamEvent
from gyra.agent.core.v2.stream_converter import step_event_to_stream_event
from gyra.agent.core.v2.sse_adapter import stream_to_sse

if TYPE_CHECKING:
    from gyra.agent.core.v2.harness.context import HarnessContext


class V2AgentRuntime:
    """V2 标准主 agent 运行时门面。

    典型用法::

        runtime = V2AgentRuntime(
            agent_id="app-x", conv_id="conv-1",
            state_store=store,
            thinking_fn=thinking_fn,
            acting_fn=acting_fn,
            permission_gate=gate,
            hook_manager=hook_manager,
        )
        # 事件流
        async for step_event in runtime.stream({"prompt": "hi"}):
            ...
        # SSE 渲染（前端）
        async for sse_line in runtime.stream_sse({"prompt": "hi"}):
            ...
    """

    def __init__(
        self,
        *,
        agent_id: str,
        conv_id: str,
        state_store: Optional[StateStore] = None,
        thinking_fn: Optional[Callable] = None,
        acting_fn: Optional[Callable] = None,
        permission_gate: Optional[Any] = None,
        subagent_runtime: Optional[Any] = None,
        hook_manager: Optional[Any] = None,
        max_steps: int = 20,
        user_id: Optional[str] = None,
        model_alias: Optional[str] = None,
        event_stream: Optional[EventStream] = None,
        harness: Optional["HarnessContext"] = None,
        context_manager: Optional[Any] = None,
        context_manager_config: Optional[Any] = None,
    ):
        """构造运行时门面。

        harness：统一服务总线。提供时从 harness 解包未显式传入的依赖
        （storage / events / approval / subagents / hooks / thinking / acting），
        显式参数优先——向后兼容旧调用方式。

        context_manager：可选的 :class:`ContextManager`（token meter + spill + compaction）；
        缺省时按 context_manager_config 自动创建。
        """
        deps = _resolve_harness_deps(
            harness,
            state_store=state_store,
            event_stream=event_stream,
            permission_gate=permission_gate,
            subagent_runtime=subagent_runtime,
            thinking_fn=thinking_fn,
            acting_fn=acting_fn,
            hook_manager=hook_manager,
        )
        state_store = deps["state_store"]
        event_stream = deps["event_stream"]
        permission_gate = deps["permission_gate"]
        subagent_runtime = deps["subagent_runtime"]
        thinking_fn = deps["thinking_fn"]
        acting_fn = deps["acting_fn"]
        hook_manager = deps["hook_manager"]
        tool_context_factory = deps["tool_context_factory"]
        if state_store is None:
            raise ValueError("state_store (or harness.storage) is required")

        self.agent_id = agent_id
        self.conv_id = conv_id
        self.state_store = state_store
        self.thinking_fn = thinking_fn
        self.acting_fn = acting_fn
        self.permission_gate = permission_gate
        self.subagent_runtime = subagent_runtime
        self.hook_manager = hook_manager
        self.tool_context_factory = tool_context_factory
        self.max_steps = max_steps
        self.user_id = user_id
        self.model_alias = model_alias
        # 共享 EventStream：run_loop 内所有 step 的事件都经它持久化+广播，
        # 是 P0 插件化扩展的订阅挂载点
        self.event_stream = event_stream if event_stream is not None else EventStream(state_store)

        # ContextManager（懒加载）：token meter + spill + compaction 自动编排。
        # emit_fn 注入后，compaction/summary 事件才能真正持久化进事件日志
        # （TokenMeter 重算 + ProjectorRegistry replace_shadow 折叠的事实源）。
        self._cm_seq = {"n": 0}
        self._context_manager = context_manager
        self._context_manager_config = context_manager_config
        if self._context_manager is None:
            try:
                from gyra.agent.core.v2.context_manager import (
                    ContextManager,
                    ContextManagerConfig,
                )
                self._context_manager = ContextManager(
                    store=state_store,
                    event_stream=self.event_stream,
                    model=model_alias,
                    conv_id=conv_id,
                    config=context_manager_config or ContextManagerConfig(),
                    emit_fn=self._cm_emit,
                )
            except Exception:  # noqa: BLE001
                self._context_manager = None

    async def _cm_emit(self, state, event_type, input_data=None, output_data=None):
        """ContextManager 的 emit 实现：compaction 等审计事件持久化进事件日志。

        Compactor 以 ``(state, event_type, input_data, output_data)`` 调用本函数；
        事件以 turn 级 step_id（``agent-conv-turn``）写入，seq 与会话单调对齐，
        保证 ProjectorRegistry / TokenMeter 重放顺序正确。
        """
        import time as _t
        import uuid as _u

        if self._cm_seq["n"] == 0:
            existing = await self.state_store.get_events(self.conv_id)
            self._cm_seq["n"] = max((e.seq for e in existing), default=-1) + 1
        ev = StepEvent(
            event_id=f"evt-{_u.uuid4().hex[:8]}",
            step_id=self._step_id_for_cm(),
            conv_id=self.conv_id,
            agent_id=self.agent_id,
            parent_step_id=None,
            state=state,
            event_type=event_type,
            input=input_data or {},
            output=output_data or {},
            seq=self._cm_seq["n"],
            timestamp=_t.time(),
        )
        self._cm_seq["n"] += 1
        return await self.event_stream.emit(ev)

    # ------------------------------------------------------------------
    # 插件订阅（P0 插件化扩展点）
    # ------------------------------------------------------------------

    def subscribe(
        self,
        callback: Callable[[StepEvent], Union[None, Awaitable[None]]],
        event_types: Optional[Iterable[str]] = None,
        mode: str = "emit",
    ) -> Callable[[], None]:
        """订阅本运行时的 StepEvent，返回 unsubscribe()。

        - event_types=None 订阅全部事件；否则只通知匹配的事件类型
          （如 ["llm_token"] 或 ["tool_call", "tool_result"]）。
        - mode：DSH 三分法分发模式（emit 观察 / waterfall 中间件 / serial 决策点）。
        - 事件在持久化到 StateStore 之后通知订阅者（durability-before-visibility）。
        - 订阅者异常只记录日志，不影响主事件流。
        """
        return self.event_stream.subscribe(
            callback, event_types=event_types, mode=mode
        )

    # ------------------------------------------------------------------
    # 事件流
    # ------------------------------------------------------------------

    def build_request_meta(self, input_: dict) -> dict:
        """构造 request/header 快照：本次模型请求的可审计元信息。

        记录 model_alias、prompt 摘要、会话标识与输入元数据，供重放与审计。
        """
        prompt = input_.get("prompt", "")
        return {
            "model": self.model_alias,
            "agent_id": self.agent_id,
            "conv_id": self.conv_id,
            "user_id": self.user_id,
            "prompt": prompt if len(prompt) <= 200 else prompt[:200] + "...(truncated)",
            "max_steps": self.max_steps,
            "session_id": input_.get("session_id"),
        }

    def build_input(self, prompt: str, extra: Optional[dict] = None) -> dict:
        """构造 run_loop 输入：统一注入会话标识与元数据。"""
        input_ = {
            "prompt": prompt,
            "agent_id": self.agent_id,
            "conv_id": self.conv_id,
            "user_id": self.user_id,
        }
        if extra:
            input_.update(extra)
        return input_

    async def stream(
        self,
        prompt: str,
        extra: Optional[dict] = None,
    ) -> AsyncGenerator[StepEvent, None]:
        """运行标准主 agent，yield 全部 StepEvent。

        turn 收尾（含 awaiting/failed 提前退出）。

        post-turn 触发 :class:`ContextManager.post_step`（自动判定 token
        压力 + spill/compaction）—— 这是 V2 上下文生命周期的核心入口。
        """
        input_ = self.build_input(prompt, extra)
        request_meta = self.build_request_meta(input_)
        turn_count = 0
        try:
            async for event in run_loop(
                agent_id=self.agent_id,
                conv_id=self.conv_id,
                input_=input_,
                state_store=self.state_store,
                thinking_fn=self.thinking_fn,
                acting_fn=self.acting_fn,
                permission_gate=self.permission_gate,
                subagent_runtime=self.subagent_runtime,
                hook_manager=self.hook_manager,
                tool_context_factory=self.tool_context_factory,
                max_steps=self.max_steps,
                user_id=self.user_id,
                request_meta=request_meta,
                event_stream=self.event_stream,
            ):
                if event.event_type == "step_done" and event.state == StepState.DONE:
                    turn_count += 1
                yield event
        finally:
            # post-turn context lifecycle：自动 spill/compaction
            if self._context_manager is not None:
                try:
                    await self._context_manager.post_step(
                        step_id=self._step_id_for_cm(),
                        agent_id=self.agent_id,
                        turn_count=turn_count,
                    )
                except Exception:  # noqa: BLE001
                    # 上下文管理失败不阻断主流程（已落库事件可下次 resume 处理）
                    pass

    def _step_id_for_cm(self) -> str:
        """为 ContextManager 构造一个本 turn 唯一标识（用于 compaction 审计）。"""
        return f"{self.agent_id}-{self.conv_id}-turn"

    async def collect(
        self,
        prompt: str,
        extra: Optional[dict] = None,
    ) -> List[StepEvent]:
        """运行并收集全部 StepEvent（同步便利接口）。"""
        return [e async for e in self.stream(prompt, extra)]

    # ------------------------------------------------------------------
    # 渲染（StreamEvent / SSE）
    # ------------------------------------------------------------------

    async def stream_events(
        self,
        prompt: str,
        extra: Optional[dict] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """把 StepEvent 转换为外部 StreamEvent（前端协议层）。"""
        async for step_event in self.stream(prompt, extra):
            yield step_event_to_stream_event(step_event)

    async def stream_sse(
        self,
        prompt: str,
        extra: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """生成 BAIZE 兼容的 SSE data 行，前端直接消费渲染。

        事件流结束后追加 ``[DONE]`` 结束信号（run_loop 内部不产生 done 事件，
        前端依赖 ``[DONE]`` 判定 turn 完成）。
        """
        async for line in stream_to_sse(self.stream_events(prompt, extra)):
            yield line
        yield 'data:{"vis":"[DONE]"} \n\n'

    async def collect_sse(
        self,
        prompt: str,
        extra: Optional[dict] = None,
    ) -> List[str]:
        """收集全部 SSE 行（测试/调试便利接口）。"""
        return [line async for line in self.stream_sse(prompt, extra)]
