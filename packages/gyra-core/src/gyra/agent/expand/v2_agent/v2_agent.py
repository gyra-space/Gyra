"""V2Agent — 使用 V2 run_loop 引擎的标准主 Agent 模板。

设计目标："换引擎不换车"——复用现有 serve 链路（agent_chat → build_agent →
initiate_chat）、资源协议、工具注入与 BAIZE vis 渲染协议，仅把主 Agent 内部的
think/act 循环替换为 V2 run_loop（run_step 状态机 + V2AgentRuntime 门面）。

与 ReActMasterAgent（V1 引擎）的关系：
  - 继承 ReActMasterAgent 以获得全部装配（bind 链 / ContextEngine / WorkLog /
    工具注入 / AFS / 交付物），role 独立为 "V2"。
  - 覆盖 thinking()：内部用 V2 run_loop 驱动一轮 turn（thinking_fn + acting_fn +
    PermissionGate），消费 StepEvent 并把 token/工具事件桥回 BAIZE vis。
  - 配套覆盖 act() / verify()：run_loop 已执行工具与验证，V1 外层循环直接收尾。

接入方式（无 serve 层改动）：
  1. 本类被 AgentManager.after_start 自动扫描注册（gyra.agent.expand 递归扫描
     ConversableAgent 子类），role="V2" 即注册键；
  2. app.agent = "V2" 时，_build_agent_by_gpts 的
     resolve_agent_name → get_by_name("V2") → cls().bind(...).build() 命中本类；
  3. 渲染复用现有 BAIZE vis（listen_thinking_stream / gpts_memory.push_message），
     前端无需任何改动。
"""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from gyra._private.pydantic import Field, PrivateAttr

from gyra.agent.core.agent import Agent
from gyra.agent.core.types import AgentMessage
from gyra.agent.core.role import ProfileConfig
from gyra.agent.core.schema import Status
from gyra.agent.core.action.base import ActionOutput
from gyra.agent.util.llm.llm_client import AgentLLMOut, AIWrapper
from gyra.agent.core.v2 import (
    V2AgentRuntime,
    DbStateStore,
    PermissionGate,
    PermissionMode,
    SessionPermissionCache,
    make_default_thinking_fn,
    make_default_acting_fn,
    ToolResolver,
    ToolFailureTracker,
    ToolContextFactory,
    DoomLoopAdapter,
    TruncatorAdapter,
)
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.expand.react_master_agent import ReActMasterAgent

logger = logging.getLogger(__name__)


class V2Agent(ReActMasterAgent):
    """标准主 Agent 模板（V2 引擎）。

    复用现有 serve bind 链与 BAIZE vis 渲染，内部 think/act 由 V2 run_loop 驱动。
    """

    profile: ProfileConfig = Field(
        default_factory=lambda: ProfileConfig(
            name="V2",
            role="V2",
            goal="使用 V2 事件驱动运行时（run_loop 状态机）高效解决复杂任务。",
            desc="标准主 Agent 模板（V2 引擎）：复用现有资源/工具/渲染协议，内部由 V2 run_loop 驱动。",
            aliases=["V2Agent", "v2"],
        )
    )

    # ---- V2 引擎装配 ----
    _v2_engine_initialized: bool = PrivateAttr(default=False)
    _v2_state_store: Any = PrivateAttr(default=None)
    _v2_event_stream: Any = PrivateAttr(default=None)
    _v2_runtime: Optional[V2AgentRuntime] = PrivateAttr(default=None)
    # 收集 run_loop 产出的最终答案文本
    _v2_final_answer: str = PrivateAttr(default="")

    # ---- 渲染桥接（BAIZE vis 复用）----
    _v2_reply_message_id: str = PrivateAttr(default="")
    _v2_start_time: Optional[datetime] = PrivateAttr(default=None)
    _v2_is_first_chunk: bool = PrivateAttr(default=True)

    def _ensure_v2_state_store(self):
        """懒创建 V2 StateStore（临时 SQLite；生产可替换为统一 StateStore 配置）。"""
        if self._v2_state_store is None:
            self._v2_state_store = DbStateStore(
                f"{tempfile.gettempdir()}/gyra-v2-{id(self)}.db"
            )
        return self._v2_state_store

    def _ensure_v2_event_stream(self) -> EventStream:
        """懒创建共享 EventStream（PermissionGate 与 V2AgentRuntime 共用）。

        单实例挂载点：插件经 subscribe_step_event() 注册的回调能看到
        run_loop 与 PermissionGate 产出的全部 StepEvent。
        """
        if self._v2_event_stream is None:
            self._v2_event_stream = EventStream(self._ensure_v2_state_store())
        return self._v2_event_stream

    def subscribe_step_event(
        self,
        callback,
        event_types: Optional[List[str]] = None,
    ):
        """订阅 V2 引擎的 StepEvent（P0 插件化扩展点），返回 unsubscribe()。

        - event_types=None 订阅全部事件；否则只通知匹配的事件类型
          （如 ["llm_token"]、["tool_executed"]、["step_done"]）。
        - 事件在持久化后通知；回调可为同步或异步；异常不影响主流程。
        - 可在引擎装配前调用（共享 EventStream 独立于 runtime 懒创建）。
        """
        return self._ensure_v2_event_stream().subscribe(callback, event_types=event_types)

    # ------------------------------------------------------------------
    # V2 引擎装配
    # ------------------------------------------------------------------

    async def _ensure_v2_engine(self) -> Optional[V2AgentRuntime]:
        """装配 V2 run_loop 所需的 thinking_fn / acting_fn / permission_gate。"""
        if self._v2_engine_initialized and self._v2_runtime is not None:
            return self._v2_runtime
        try:
            llm_client: Optional[AIWrapper] = getattr(self, "llm_client", None)
            if llm_client is None:
                raise ValueError("V2Agent requires llm_client (AIWrapper) initialized")

            model_alias, _ = await self.select_llm_model()

            # 1. thinking_fn：复用现有 ContextEngine + gpts_memory + llm_client
            context_engine = await self._ensure_context_engine()
            gpts_memory = self.memory.gpts_memory if self.memory else None

            async def _get_session_messages(session_id: str):
                if gpts_memory is not None and hasattr(
                    gpts_memory, "get_session_messages"
                ):
                    return await gpts_memory.get_session_messages(session_id)
                return []

            async def _get_work_log(conv_id: str):
                if gpts_memory is not None and hasattr(gpts_memory, "get_work_log"):
                    try:
                        return await gpts_memory.get_work_log(conv_id)
                    except Exception:  # noqa: BLE001
                        return []
                return []

            async def _get_context_window(model: str) -> int:
                try:
                    return await self.get_agent_llm_context_length()
                except Exception:  # noqa: BLE001
                    return 128000

            from gyra.agent.core.v2.llm_stream_adapter import make_gyra_llm_stream_fn

            thinking_fn = make_default_thinking_fn(
                llm_stream_fn=make_gyra_llm_stream_fn(llm_client, model_alias),
                model_alias=model_alias,
                context_engine=context_engine,
                memory_bundle=getattr(self, "_memory_bundle", None),
                get_session_messages=_get_session_messages,
                get_work_log=_get_work_log,
                get_context_window=_get_context_window,
                system_prompt=None,  # 由 input_["system_prompt"] 注入
            )

            # 2. acting_fn：复用现有工具注入（available_system_tools + resource）
            system_tools = dict(getattr(self, "available_system_tools", None) or {})
            tool_resolver = ToolResolver(
                system_tools=system_tools,
                resource_pack=getattr(self, "resource", None),
            )
            acting_fn = make_default_acting_fn(
                tool_resolver=tool_resolver,
                doom_loop_detector=DoomLoopAdapter(
                    getattr(self, "_doom_loop_detector", None)
                ),
                failure_tracker=ToolFailureTracker(max_failures=3),
                truncator=TruncatorAdapter(getattr(self, "_truncator", None)),
                tool_context_factory=ToolContextFactory(
                    agent_id=self.not_null_agent_context.agent_app_code,
                    conv_id=self.not_null_agent_context.conv_id,
                ),
            )

            # 3. PermissionGate：复用现有规则集（fail-closed 单调守卫可经 register_guard 扩展）
            gate = PermissionGate(
                state_store=self._ensure_v2_state_store(),
                event_stream=self._ensure_v2_event_stream(),
                interaction_adapter=getattr(self, "interaction_adapter", None),
                session_cache=SessionPermissionCache(),
                ruleset=getattr(self, "permission_ruleset", None),
                mode=PermissionMode.DEFAULT,
                step_id=None,  # bound by run_step
                conv_id=self.not_null_agent_context.conv_id,
                agent_id=self.not_null_agent_context.agent_app_code,
                tool=None,
            )

            self._v2_runtime = V2AgentRuntime(
                agent_id=self.not_null_agent_context.agent_app_code,
                conv_id=self.not_null_agent_context.conv_id,
                state_store=self._ensure_v2_state_store(),
                thinking_fn=thinking_fn,
                acting_fn=acting_fn,
                permission_gate=gate,
                max_steps=getattr(self, "get_effective_max_steps", lambda: 20)()
                if callable(getattr(self, "get_effective_max_steps", None))
                else 20,
                model_alias=model_alias,
                event_stream=self._ensure_v2_event_stream(),
            )
            self._v2_engine_initialized = True
            return self._v2_runtime
        except Exception as e:  # noqa: BLE001
            logger.error(f"[V2Agent] engine assemble failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 引擎覆盖：thinking / act / verify
    # ------------------------------------------------------------------

    async def thinking(
        self,
        messages: List[AgentMessage],
        reply_message_id: str,
        sender: Optional[Agent] = None,
        prompt: Optional[str] = None,
        received_message: Optional[AgentMessage] = None,
        reply_message: Optional[AgentMessage] = None,
        **kwargs,
    ) -> Optional[AgentLLMOut]:
        """用 V2 run_loop 驱动一轮 turn，产出 AgentLLMOut（V1 协议兼容）。"""
        self._v2_final_answer = ""
        self._v2_reply_message_id = reply_message_id
        self._v2_start_time = datetime.now()
        self._v2_is_first_chunk = True

        user_prompt = self._extract_text_from_content(
            getattr(received_message, "content", None) or ""
        )
        conv_id = self.not_null_agent_context.conv_id
        session_id = self.not_null_agent_context.conv_session_id or conv_id
        system_prompt = prompt or (
            getattr(reply_message, "system_prompt", None) if reply_message else None
        )

        runtime = await self._ensure_v2_engine()
        if runtime is None:
            raise ValueError("[V2Agent] V2 engine not available")

        # 运行 run_loop，消费 StepEvent
        try:
            async for step_event in runtime.stream(
                user_prompt,
                extra={"session_id": session_id, "conv_id": conv_id},
            ):
                await self._handle_v2_step_event(step_event, received_message)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[V2Agent] run_loop failed: {e}", exc_info=True)
            raise

        model_name = getattr(runtime, "model_alias", None)
        # 组装 V1 协议输出（content=最终答案；工具已由 run_loop 内部执行并推送 vis）
        return AgentLLMOut(
            llm_name=model_name,
            thinking_content=self._v2_final_answer,
            content=self._v2_final_answer,
            tool_calls=[],
        )

    async def _handle_v2_step_event(
        self,
        step_event: StepEvent,
        received_message: Optional[AgentMessage] = None,
    ) -> None:
        """把 StepEvent 桥回 BAIZE vis（复用 listen_thinking_stream）。"""
        if step_event.event_type == "llm_token":
            token = (step_event.output or {}).get("token", "")
            if token:
                self._v2_final_answer += token
                # BAIZE vis 增量推送
                await self.listen_thinking_stream(
                    llm_out=AgentLLMOut(
                        llm_name=step_event.agent_id,
                        content=token,
                        thinking_content=token,
                    ),
                    reply_message_id=self._v2_reply_message_id,
                    start_time=self._v2_start_time or datetime.now(),
                    cu_thinking_incr=None,
                    cu_content_incr=token,
                    is_first_chunk=self._v2_is_first_chunk,
                    is_first_content=False,
                    received_message=received_message,
                )
                self._v2_is_first_chunk = False
        elif step_event.event_type == "step_done" and step_event.state is StepState.DONE:
            # 终态：重置 vis（清掉攒批）
            try:
                await self.reset_stream_vis(
                    self._v2_reply_message_id,
                    thinking=self._v2_final_answer or None,
                )
            except Exception as _e:  # noqa: BLE001
                logger.debug(f"[V2Agent] reset_stream_vis skipped: {_e}")

    async def act(
        self,
        message: AgentMessage,
        sender: Agent,
        reviewer: Optional[Agent] = None,
        **kwargs,
    ) -> List[ActionOutput]:
        """run_loop 已在 thinking() 内执行工具；此处返回终止型，V1 外层直接收尾。"""
        return [
            ActionOutput(
                content=self._v2_final_answer or "V2 引擎已执行完毕",
                name=self.name,
                is_exe_success=True,
                terminate=True,
            )
        ]

    async def verify(
        self,
        message: AgentMessage,
        sender: Agent,
        reviewer: Optional[Agent] = None,
        **kwargs,
    ) -> Tuple[bool, Optional[str]]:
        """run_loop 已完成状态机验证；V1 外层直接通过。"""
        return True, None

    # ------------------------------------------------------------------
    # 兼容辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text_from_content(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("object", {}).get("data", "")))
                elif hasattr(item, "get_text"):
                    try:
                        parts.append(str(item.get_text()))
                    except Exception:  # noqa: BLE001
                        pass
            return "".join(parts)
        return str(content)
