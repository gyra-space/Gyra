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

import json
import logging
import tempfile
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from gyra._private.pydantic import Field, PrivateAttr

from gyra.agent.core.agent import Agent
from gyra.agent.core.types import AgentMessage
from gyra.agent.core.role import ProfileConfig
from gyra.agent.core.schema import Status
from gyra.agent.core.action.base import ActionOutput
from gyra.agent.core.memory.gpts.base import GptsMessage
from gyra.agent.core.memory.gpts.file_base import WorkEntry, WorkLogStatus
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
            # 与 ReActMasterAgent 对齐：显式置 None，避免命中 ProfileConfig
            # DynConfig 默认值（ConfigInfo 对象），导致 prompt 组装时 .strip() 崩溃。
            system_prompt_template=None,
            user_prompt_template=None,
        )
    )

    # ---- V2 引擎装配 ----
    _v2_engine_initialized: bool = PrivateAttr(default=False)
    _v2_state_store: Any = PrivateAttr(default=None)
    _v2_event_stream: Any = PrivateAttr(default=None)
    _v2_runtime: Optional[V2AgentRuntime] = PrivateAttr(default=None)
    # 收集 run_loop 产出的最终答案文本
    _v2_final_answer: str = PrivateAttr(default="")
    # run_loop 内工具执行记录（tool_call_id/name/args/message_id 待回填结果）
    _v2_pending_tool_calls: List[dict] = PrivateAttr(default_factory=list)
    # 工具执行结果 ActionOutput（act() 返回，供 V1 外层 action_report / vis 使用）
    _v2_tool_action_outputs: List[ActionOutput] = PrivateAttr(default_factory=list)
    # run_loop 工具历史（按 step 分组）：[{calls:[{tool_call_id,tool_name,args}], results:{id:{content,success}}}]
    # 每轮 thinking 经 get_extra_messages 确定性注入模型上下文，避免 DB 读回竞态
    _v2_tool_rounds: List[dict] = PrivateAttr(default_factory=list)

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

            async def _get_function_calling_context():
                """懒构建 function_calling_context（复用 V1 工具声明构建链）。

                首轮先构建并缓存到 self.function_calling_context；后续轮次直接复用，
                避免多步 run_loop 内重复全量构建。
                """
                try:
                    fcc = getattr(self, "function_calling_context", None)
                    if fcc is None or not fcc.get("tools"):
                        fcc = await self.function_calling_params()
                        self.function_calling_context = fcc
                    return fcc
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"[V2Agent] function_calling_params failed: {e}"
                    )
                    return None

            thinking_fn = make_default_thinking_fn(
                llm_stream_fn=make_gyra_llm_stream_fn(
                    llm_client,
                    model_alias,
                    get_function_calling_context=_get_function_calling_context,
                ),
                model_alias=model_alias,
                context_engine=context_engine,
                memory_bundle=getattr(self, "_memory_bundle", None),
                get_session_messages=_get_session_messages,
                get_work_log=_get_work_log,
                get_context_window=_get_context_window,
                system_prompt=None,  # 由 input_["system_prompt"] 注入
                get_extra_messages=self._v2_build_extra_tool_messages,
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
        self._v2_pending_tool_calls = []
        self._v2_tool_action_outputs = []
        self._v2_tool_rounds = []

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
        elif step_event.event_type == "tool_call":
            # 记录工具调用：写一条带 tool_calls 的 assistant 消息进会话，
            # 供 run_loop 下一轮 thinking 的 ContextEngine 渲染 CALL 单元。
            await self._persist_v2_tool_call(step_event)
        elif step_event.event_type == "tool_result":
            # 回填工具执行结果：写 WorkEntry（按 tool_call_id 关联），
            # 并收集 ActionOutput 供 act() 返回（V1 外层 action_report）。
            await self._persist_v2_tool_result(step_event)
        elif step_event.event_type == "step_done" and step_event.state is StepState.DONE:
            # 终态：重置 vis（清掉攒批）
            try:
                await self.reset_stream_vis(
                    self._v2_reply_message_id,
                    thinking=self._v2_final_answer or None,
                )
            except Exception as _e:  # noqa: BLE001
                logger.debug(f"[V2Agent] reset_stream_vis skipped: {_e}")

    async def _persist_v2_tool_call(self, step_event: StepEvent) -> None:
        """把 run_loop 的工具调用事件持久化到会话（assistant 消息 + tool_calls）。

        时序说明：run_loop 下一轮 thinking 的 messages 从 gpts_memory 重新构建，
        工具调用必须写回会话，ContextEngine 才能渲染 tool_calls + 结果，
        LLM 后续轮次才能感知工具执行事实。
        """
        input_data = step_event.input or {}
        tool_name = input_data.get("tool") or ""
        args = input_data.get("input") or {}
        if not tool_name:
            return
        gpts_memory = self.memory.gpts_memory if self.memory else None
        if gpts_memory is None:
            return
        tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        try:
            args_str = json.dumps(args, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001
            args_str = "{}"
        conv_id = self.not_null_agent_context.conv_id
        gmsg = GptsMessage(
            conv_id=conv_id,
            conv_session_id=self.not_null_agent_context.conv_session_id or conv_id,
            sender=self.name or self.role or "assistant",
            sender_name=self.name or self.role or "assistant",
            message_id=message_id,
            role="assistant",
            # content 必须置空：工具调用消息是动作声明，历史 thinking 若回流
            # 会让模型在下一轮复述旧思考再新增，导致 thinking 文本逐轮累积重复
            content="",
            tool_calls=[
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": args_str},
                }
            ],
            rounds=0,
            app_code=self.not_null_agent_context.gpts_app_code,
            data_version="v2",
        )
        try:
            await gpts_memory.append_message(conv_id, gmsg, save_db=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] persist tool_call message failed: {e}")
            return
        self._v2_pending_tool_calls.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "args": args,
                "message_id": message_id,
            }
        )
        # 记录到工具历史（按 step 分组；上一轮已出结果则开新组）
        if not self._v2_tool_rounds or self._v2_tool_rounds[-1]["results"]:
            self._v2_tool_rounds.append({"calls": [], "results": {}})
        self._v2_tool_rounds[-1]["calls"].append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "args": args,
            }
        )

    async def _persist_v2_tool_result(self, step_event: StepEvent) -> None:
        """回填工具执行结果（WorkEntry）并收集 ActionOutput 供 act() 返回。"""
        if not self._v2_pending_tool_calls:
            return
        pending = self._v2_pending_tool_calls.pop(0)
        gpts_memory = self.memory.gpts_memory if self.memory else None
        output = step_event.output or {}
        result_text = str(output.get("content") or "")
        if not result_text and output.get("error"):
            result_text = str(output["error"])
        success = bool(output.get("is_exe_success", True))

        if gpts_memory is not None:
            try:
                entry = WorkEntry(
                    timestamp=step_event.timestamp or time.time(),
                    tool=pending["tool_name"],
                    args=pending["args"],
                    result=result_text or None,
                    success=success,
                    status=WorkLogStatus.ACTIVE.value,
                    tool_call_id=pending["tool_call_id"],
                    message_id=pending["message_id"],
                    conv_id=self.not_null_agent_context.conv_id,
                    assistant_content=self._v2_final_answer or "",
                    round_index=0,
                )
                await gpts_memory.append_work_entry(
                    self.not_null_agent_context.conv_id, entry, save_db=True
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[V2Agent] persist tool_result work_entry failed: {e}")

        self._v2_tool_action_outputs.append(
            ActionOutput(
                content=result_text,
                name=pending["tool_name"],
                action_name=pending["tool_name"],
                is_exe_success=success,
                terminate=False,
            )
        )
        # 回填工具历史：定位含该 tool_call 的 step 组
        for rd in reversed(self._v2_tool_rounds):
            if any(
                c["tool_call_id"] == pending["tool_call_id"] for c in rd["calls"]
            ):
                rd["results"][pending["tool_call_id"]] = {
                    "content": result_text,
                    "success": success,
                }
                break

    def _v2_build_extra_tool_messages(self) -> List[dict]:
        """构造 run_loop 已执行工具的历史 LLM 消息（assistant tool_calls + tool 结果）。

        每轮 thinking 注入，确保模型在后续步骤能看到工具执行事实，收敛多步循环。
        """
        msgs: List[dict] = []
        for rd in self._v2_tool_rounds:
            if not rd.get("results"):
                continue  # 本轮尚未出结果（当前 step 正在 thinking）
            tcs = []
            for c in rd["calls"]:
                try:
                    args_str = json.dumps(c["args"], ensure_ascii=False, default=str)
                except Exception:  # noqa: BLE001
                    args_str = "{}"
                tcs.append(
                    {
                        "id": c["tool_call_id"],
                        "type": "function",
                        "function": {"name": c["tool_name"], "arguments": args_str},
                    }
                )
            if not tcs:
                continue
            msgs.append({"role": "assistant", "content": "", "tool_calls": tcs})
            for c in rd["calls"]:
                res = rd["results"].get(c["tool_call_id"])
                content = res["content"] if res else "[工具执行失败/无结果]"
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": c["tool_call_id"],
                        "content": content or "[空结果]",
                    }
                )
        return msgs

    async def act(
        self,
        message: AgentMessage,
        sender: Agent,
        reviewer: Optional[Agent] = None,
        **kwargs,
    ) -> List[ActionOutput]:
        """run_loop 已在 thinking() 内执行工具；此处返回工具执行记录 + 终止型收尾，
        供 V1 外层 action_report / vis 使用（工具结果也已写回会话 WorkEntry）。"""
        outputs = list(self._v2_tool_action_outputs or [])
        outputs.append(
            ActionOutput(
                content=self._v2_final_answer or "V2 引擎已执行完毕",
                name=self.name,
                is_exe_success=True,
                terminate=True,
            )
        )
        return outputs

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
