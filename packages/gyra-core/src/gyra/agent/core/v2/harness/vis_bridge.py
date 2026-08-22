"""VisBridge —— V2 vis 渲染桥（harness 事件总线规范）。

对齐 DeepSeek Harness 的"引擎只产事件，UI/渲染作为订阅者消费事件"：
  - V2 引擎（run_loop / run_step）只产出 StepEvent（llm_token / tool_call /
    tool_result / step_done / ...），经 harness.events（EventStream）广播；
  - :class:`VisBridge` 以 **emit 模式订阅者** 身份消费这些事件，把渲染事实
    桥到 BAIZE vis（gpts_memory.push_message，经 base_agent 的
    ``listen_thinking_stream`` / ``reset_stream_vis`` 成熟渲染实现，
    含 stream_out 开关与 memory-context scrubber）。

渲染对齐 V1（ReActMasterAgent）：
  - llm_token 分通道渲染：``channel="thinking"`` 走 ``cu_thinking_incr``
    （思考块），``channel="content"`` 走 ``cu_content_incr``（正文文本），
    并各自维护 first-chunk 标记（与 V1 的 thinking_chunk_count/
    content_chunk_count 语义一致）；
  - step_done 终态重置只回填**累积思考文本**（非混合全文），避免正文重复。
  工具步骤（tool_call / tool_result）由 V2Agent.act() 收尾时以 action_report
  渲染（与 V1 逐轮 send 语义对齐），本桥不重复推送。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.util.llm.llm_client import AgentLLMOut

logger = logging.getLogger(__name__)

# 本桥订阅的事件类型：llm_token（增量渲染）与 step_done（终态重置）
_VIS_EVENT_TYPES = ["llm_token", "step_done"]


class VisBridge:
    """订阅 harness.events 的 vis 渲染桥。

    用法（由 V2Agent 装配）：:

        bridge = VisBridge(agent=self, event_stream=self._ensure_v2_event_stream())
        bridge.attach()                       # 装配引擎时
        bridge.begin_turn(reply_message_id, start_time, received_message)  # 每轮 turn 前
        # run_loop 运行期间，llm_token / step_done 事件自动触发渲染
        bridge.detach()                       # 引擎销毁时（可选）
    """

    def __init__(self, agent: Any, event_stream: Any):
        self._agent = agent
        self._events = event_stream
        self._unsubscribers: List[Any] = []
        # ---- 渲染上下文（begin_turn 设置）----
        self._reply_message_id: str = ""
        self._start_time: Optional[datetime] = None
        self._received_message: Optional[Any] = None
        # reply_message：listen_thinking_stream 的 temp_message 需要它的
        # goal_id 作为流式内容的挂载节点（window3/manus 的 _process_stream_msg
        # 按 goal_id 挂载到任务树根节点，缺失则整帧被丢弃）
        self._reply_message: Optional[Any] = None
        # first-chunk 标记：与 V1 的 thinking_chunk_count / content_chunk_count
        # 语义对齐——is_first_chunk 只在 thinking 通道首帧为 True，
        # is_first_content 只在 content 通道首帧为 True。
        self._is_first_chunk: bool = True
        self._is_first_content: bool = True
        # 本桥累积的思考文本（供终态 reset 的 thinking 参数；不含正文）
        self._thinking_text: str = ""
        # 本桥累积的正文文本（最终答案）
        self._final_text: str = ""

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def attach(self) -> None:
        """注册为 harness.events 的 emit 订阅者（幂等）。"""
        if self._unsubscribers:
            return
        self._unsubscribers.append(
            self._events.subscribe(
                self._on_event,
                event_types=list(_VIS_EVENT_TYPES),
                mode="emit",
            )
        )

    def detach(self) -> None:
        """注销订阅。"""
        for unsubscribe in self._unsubscribers:
            try:
                unsubscribe()
            except Exception:  # noqa: BLE001
                pass
        self._unsubscribers = []

    def begin_turn(
        self,
        reply_message_id: str,
        start_time: Optional[datetime] = None,
        received_message: Optional[Any] = None,
        reply_message: Optional[Any] = None,
    ) -> None:
        """每轮 turn 前设置渲染上下文并重置增量状态。"""
        self._reply_message_id = reply_message_id
        self._start_time = start_time or datetime.now()
        self._received_message = received_message
        self._reply_message = reply_message
        self._is_first_chunk = True
        self._is_first_content = True
        self._thinking_text = ""
        self._final_text = ""

    # ------------------------------------------------------------------
    # 事件订阅处理
    # ------------------------------------------------------------------

    async def _on_event(self, event: StepEvent) -> None:
        if event.event_type == "llm_token":
            await self._render_token(event)
        elif event.event_type == "step_done" and event.state is StepState.DONE:
            await self._render_reset(event)

    async def _render_token(self, event: StepEvent) -> None:
        """llm_token → BAIZE vis 增量渲染（复用 listen_thinking_stream）。

        分通道：thinking 推理文本走思考块，content 正文走文本，
        各自维护 first-chunk 标记（对齐 V1 渲染语义）。
        """
        output = event.output or {}
        token = output.get("token", "")
        channel = output.get("channel", "content")
        if not token:
            return
        if channel == "thinking":
            self._thinking_text += token
            cu_thinking_incr, cu_content_incr = token, None
            is_first_chunk = self._is_first_chunk
            is_first_content = False
        else:
            self._final_text += token
            cu_thinking_incr, cu_content_incr = None, token
            is_first_chunk = False
            is_first_content = self._is_first_content
        try:
            await self._agent.listen_thinking_stream(
                llm_out=AgentLLMOut(
                    llm_name=event.agent_id,
                    # 分通道填充：content 恒非空会触发 listen_thinking_stream 的
                    # content_stream_out 门控，把 thinking 帧误判为内容帧丢弃
                    content=token if channel != "thinking" else "",
                    thinking_content=token if channel == "thinking" else "",
                ),
                reply_message_id=self._reply_message_id,
                start_time=self._start_time or datetime.now(),
                cu_thinking_incr=cu_thinking_incr,
                cu_content_incr=cu_content_incr,
                is_first_chunk=is_first_chunk,
                is_first_content=is_first_content,
                received_message=self._received_message,
                reply_message=self._reply_message,
                sender=self._agent,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[VisBridge] listen_thinking_stream skipped: {e}")
        if channel == "thinking":
            self._is_first_chunk = False
        else:
            self._is_first_content = False

    async def _render_reset(self, event: StepEvent) -> None:
        """step_done → 终态重置 vis（清掉攒批）。

        只回填累积**思考文本**（thinking 通道），正文保持流式累积的
        content 不变，避免正文在思考块里重复出现。
        """
        try:
            await self._agent.reset_stream_vis(
                self._reply_message_id,
                thinking=self._thinking_text or None,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[VisBridge] reset_stream_vis skipped: {e}")
