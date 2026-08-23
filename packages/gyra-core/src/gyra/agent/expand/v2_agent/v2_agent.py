"""V2Agent — 使用 V2 run_loop 引擎的标准主 Agent 模板。

设计目标："换引擎不换车"——复用现有 serve 链路（agent_chat → build_agent →
initiate_chat）、资源协议、工具注入与 BAIZE vis 渲染协议，仅把主 Agent 内部的
think/act 循环替换为 V2 run_loop（run_step 状态机 + V2AgentRuntime 门面）。

与 ReActMasterAgent（V1 引擎）的关系：
  - 继承 ReActMasterAgent 以获得全部装配（bind 链 / ContextEngine / WorkLog /
    工具注入 / AFS / 交付物），role 独立为 "PIXIU"（貔貅）。
  - 覆盖 thinking()：内部用 V2 run_loop 驱动一轮 turn（thinking_fn + acting_fn +
    PermissionGate），消费 StepEvent 并把 token/工具事件桥回 BAIZE vis。
  - 配套覆盖 act() / verify()：run_loop 已执行工具与验证，V1 外层循环直接收尾。

接入方式（无 serve 层改动）：
  1. 本类被 AgentManager.after_start 自动扫描注册（gyra.agent.expand 递归扫描
     ConversableAgent 子类），role="PIXIU" 即注册键；
  2. app.agent = "PIXIU" 时，_build_agent_by_gpts 的
     resolve_agent_name → get_by_name("PIXIU") → cls().bind(...).build() 命中本类；
     历史 app.agent = "V2"/"V2Agent"/"v2"/"BIXIU" 经别名解析到 "PIXIU" 同样命中；
  3. 渲染复用现有 BAIZE vis（listen_thinking_stream / gpts_memory.push_message），
     前端无需任何改动。
"""
from __future__ import annotations

import inspect
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from gyra._private.pydantic import Field, PrivateAttr
from gyra.util.executor_utils import execute_no_wait

from gyra.agent.core.agent import Agent
from gyra.agent.core.types import AgentMessage
from gyra.agent.core.role import ProfileConfig
from gyra.agent.core.schema import Status
from gyra.agent.core.action.base import ActionOutput, AskUserType
from gyra.agent.core.memory.gpts.base import GptsMessage
from gyra.agent.core.memory.gpts.file_base import WorkEntry, WorkLogStatus
from gyra.agent.core.memory.gpts.gpts_memory import AgentTaskContent, AgentTaskType
from gyra.agent.core.file_system.file_tree import TreeNodeData
from gyra.agent.util.llm.llm_client import AgentLLMOut, AIWrapper
from gyra.agent.core.v2 import (
    V2AgentRuntime,
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
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.expand.react_master_agent import ReActMasterAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 进程级静态组件缓存（跨轮/跨会话复用；agent 实例每轮重建，这些静态件不应重建）
# ---------------------------------------------------------------------------
# StateStore 按 (state_dir, app_code) 分片——无会话态，可安全共享；
# DbStateStore 连接已线程局部化（state_store.py），SqlAlchemyStateStore
# session-per-op 线程安全。淘汰时尽力 close()。
_V2_STATE_STORES: "dict[tuple, object]" = {}
_V2_STATE_STORES_CAP = 32

# SkillRegistry 按 skill 根目录共享（纯只读磁盘扫描结果；digest 机制保证
# 目录内容变化时 catalog consumer 重新注入）。
_V2_SKILL_REGISTRIES: "dict[str, object]" = {}


def _state_store_cache_put(key: tuple, store) -> None:
    if len(_V2_STATE_STORES) >= _V2_STATE_STORES_CAP:
        oldest_key = next(iter(_V2_STATE_STORES))
        oldest = _V2_STATE_STORES.pop(oldest_key, None)
        close = getattr(oldest, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # noqa: BLE001
                pass
    _V2_STATE_STORES[key] = store


class V2Agent(ReActMasterAgent):
    """标准主 Agent 模板（V2 引擎）。

    复用现有 serve bind 链与 BAIZE vis 渲染，内部 think/act 由 V2 run_loop 驱动。
    """

    profile: ProfileConfig = Field(
        default_factory=lambda: ProfileConfig(
            name="貔貅",
            role="PIXIU",
            goal="我是貔貅（PIXIU），使用事件驱动运行时（run_loop 状态机）高效解决复杂任务。",
            desc="貔貅（PIXIU）：标准主 Agent 模板（V2 引擎），复用现有资源/工具/渲染协议，内部由 V2 run_loop 驱动。",
            # "V2"/"V2Agent"/"v2"/"BIXIU" 作为别名保留，兼容历史存量应用
            aliases=["V2Agent", "V2", "v2", "BIXIU"],
            # 与 ReActMasterAgent 对齐：显式置 None，避免命中 ProfileConfig
            # DynConfig 默认值（ConfigInfo 对象），导致 prompt 组装时 .strip() 崩溃。
            system_prompt_template=None,
            user_prompt_template=None,
        )
    )

    # V2 状态存储根目录（可选）。缺省 None → DATA_DIR/v2_state（真实持久化）；
    # 测试/沙箱场景可注入隔离目录，避免多实例共享事件日志。
    v2_state_dir: Optional[str] = Field(
        default=None,
        description="V2 事件溯源 StateStore 根目录（缺省 DATA_DIR/v2_state）",
    )

    # ---- V2 引擎装配 ----
    _v2_engine_initialized: bool = PrivateAttr(default=False)
    _v2_state_store: Any = PrivateAttr(default=None)
    _v2_event_stream: Any = PrivateAttr(default=None)
    _v2_runtime: Optional[V2AgentRuntime] = PrivateAttr(default=None)
    # 统一服务总线（V2 引擎消费的唯一入口）
    _v2_harness: Any = PrivateAttr(default=None)
    # 收集 run_loop 产出的最终答案文本（content 通道）
    _v2_final_answer: str = PrivateAttr(default="")
    # 收集 run_loop 产出的推理文本（thinking 通道，用于最终消息思考字段）
    _v2_thinking_answer: str = PrivateAttr(default="")
    # run_loop 内工具执行记录（tool_call_id/name/args/message_id 待回填结果）
    _v2_pending_tool_calls: List[dict] = PrivateAttr(default_factory=list)
    # tool_call 事件清空最终答案累积前的旁白快照（供 WorkEntry.assistant_content）
    _v2_pending_narration: str = PrivateAttr(default="")
    # 本轮是否因 ask_user 交互工具挂起（run_loop 收到 AWAITING_USER interaction_request
    # 时置 True，act() 据此返回 ask_user=True 的 ActionOutput，让 V1 外层把会话置 WAITING）
    _v2_awaiting_user: bool = PrivateAttr(default=False)

    # ---- 渲染桥接（harness 事件总线：VisBridge 订阅 llm_token/step_done → BAIZE vis）----
    _v2_reply_message_id: str = PrivateAttr(default="")
    _v2_start_time: Optional[datetime] = PrivateAttr(default=None)
    # vis 渲染桥（harness 事件流订阅者，引擎只产事件）
    _v2_vis_bridge: Any = PrivateAttr(default=None)
    # skill 资源总线（对齐 DSH ctx.skills；每个 V2Agent 持有一份 registry）
    _v2_skill_registry: Any = PrivateAttr(default=None)
    # skill catalog consumer（按 digest 变化以 user-role reminder 注入 LLM）
    _v2_catalog_consumer: Any = PrivateAttr(default=None)
    # DB catalog consumer（按 DB 列表 digest 变化以 user-role reminder 注入 LLM）
    _v2_db_catalog_consumer: Any = PrivateAttr(default=None)
    # 当前 turn 生效的模型别名（usage 展示桥接用）
    _v2_model_alias: str = PrivateAttr(default="")
    # engine 装配完成回调（serve 层绑定 job_registry 等；懒装配后触发）
    _v2_engine_ready_hook: Any = PrivateAttr(default=None)
    # 会话对话消息事件 seq（user/message、assistant/message 单调递增）
    _v2_dialog_seq: Any = PrivateAttr(default_factory=lambda: {"n": 0})

    def _ensure_v2_state_store(self):
        """懒创建 V2 事件溯源持久化 StateStore（真实库，非 tempdir）。

        默认落 ``{DATA_DIR}/v2_state`` 按 Agent 隔离的单库文件，内部按 conv_id
        分表记录——跨 conv / 跨进程 / 重启均可恢复。替换早期
        ``tempfile.gettempdir()/gyra-v2-{id(self)}.db`` 的进程内临时库。
        """
        if self._v2_state_store is None:
            from gyra.agent.core.v2.state_store import create_state_store
            key = (self.v2_state_dir or "", self.not_null_agent_context.agent_app_code)
            store = _V2_STATE_STORES.get(key)
            if store is None:
                store = create_state_store(
                    agent_id=self.not_null_agent_context.agent_app_code,
                    data_dir=self.v2_state_dir,
                )
                _state_store_cache_put(key, store)
            self._v2_state_store = store
        return self._v2_state_store

    def _ensure_v2_event_stream(self) -> EventStream:
        """懒创建共享 EventStream（PermissionGate 与 V2AgentRuntime 共用）。

        单实例挂载点：插件经 subscribe_step_event() 注册的回调能看到
        run_loop 与 PermissionGate 产出的全部 StepEvent。
        """
        if self._v2_event_stream is None:
            self._v2_event_stream = EventStream(self._ensure_v2_state_store())
        return self._v2_event_stream

    def _ensure_v2_skill_registry(self):
        """懒创建 skill 资源总线（对齐 DSH ``ctx.skills``）。

        注册默认 provider（``FilesystemSkillProvider``）——skill 根目录
        优先级：``$GYRA_SKILLS_DIR`` > ``~/skills`` > ``~/.gyra/skills``。
        若全部不存在则保持空 registry（catalog 为空，consumer 不注入）。

        返回 :class:`SkillRegistry` 实例，复用同一对象作为 ``harness.skills``。
        """
        if self._v2_skill_registry is not None:
            return self._v2_skill_registry
        from gyra.agent.core.v2.skills import SkillRegistry, LAYER_SCOPE

        try:
            from gyra.agent.core.v2.skills import FilesystemSkillProvider
            from gyra.agent.core.v2.skills.filesystem_provider import (
                _default_skill_root,
            )
            base_dir = _default_skill_root()
        except Exception:  # noqa: BLE001
            base_dir = None

        # 进程级共享：FS 扫描结果按根目录复用（目录内容变化由 digest 机制
        # 驱动 catalog consumer 重新注入；registry 本身不携带会话态）。
        cache_key = str(base_dir) if base_dir else "<none>"
        registry = _V2_SKILL_REGISTRIES.get(cache_key)
        if registry is None:
            registry = SkillRegistry()
            if base_dir:
                try:
                    fs_provider = FilesystemSkillProvider(base_skill_dir=base_dir)
                    registry.register_provider(LAYER_SCOPE, fs_provider)
                    logger.debug(f"[V2Agent] skill registry wired with {base_dir}")
                except Exception:  # noqa: BLE001
                    logger.debug(
                        "[V2Agent] filesystem skill provider not wired, "
                        "registry stays empty",
                        exc_info=True,
                    )
            _V2_SKILL_REGISTRIES[cache_key] = registry
        self._v2_skill_registry = registry
        return registry

    def _ensure_v2_catalog_consumer(self):
        """懒创建 skill catalog consumer（首次 / digest 变化才注入 reminder）。

        与 :meth:`_ensure_v2_skill_registry` 配对：consumer 持有 digest 状态，
        在每轮 ``thinking()`` 时被 ``default_thinking`` 拉取。

        返回 :class:`SkillCatalogConsumer` 实例。
        """
        if self._v2_catalog_consumer is not None:
            return self._v2_catalog_consumer
        from gyra.agent.core.v2.skills import SkillCatalogConsumer, LAYER_SCOPE
        registry = self._ensure_v2_skill_registry()
        self._v2_catalog_consumer = SkillCatalogConsumer(
            registry=registry,
            layer_chain=[LAYER_SCOPE, "host"],
            cwd=None,
        )
        return self._v2_catalog_consumer

    def _ensure_v2_db_catalog_consumer(self):
        """懒创建 DB 列表 consumer（首次 / DB 列表 digest 变化才注入 reminder）。

        provider = agent.capability_pack 的 ``db`` 视图；首次或 DB 列表 digest
        变化时以 user-role ``<available_databases>`` 摘要注入（db_name + type +
        dialect + datasource_id；**不**含 schema 详情——按需 ``db({action})`` 取）。
        """
        if self._v2_db_catalog_consumer is not None:
            return self._v2_db_catalog_consumer
        from gyra.agent.core.v2.db_consumer import DbCatalogConsumer

        agent_self = self

        def _provider():
            cap_pack = getattr(agent_self, "capability_pack", None)
            if cap_pack is None:
                return []
            out: List[Dict[str, Any]] = []
            for c in cap_pack.get_all("db"):
                out.append(
                    {
                        "db_name": getattr(c, "db_name", "") or "",
                        "db_type": getattr(c, "_db_type", "") or "",
                        "dialect": (
                            getattr(c, "_dialect", "")
                            or getattr(c, "_db_type", "")
                            or ""
                        ),
                        "datasource_id": getattr(c, "_datasource_id", None),
                        "description": "",  # DBCapability 当前无 description
                    }
                )
            return out

        self._v2_db_catalog_consumer = DbCatalogConsumer(provider=_provider)
        return self._v2_db_catalog_consumer

    def subscribe_step_event(
        self,
        callback,
        event_types: Optional[List[str]] = None,
        mode: str = "emit",
    ):
        """订阅 V2 引擎的 StepEvent（P0 插件化扩展点），返回 unsubscribe()。

        - ``event_types``：None 订阅全部事件；否则只通知匹配的事件类型
          （如 ["llm_token"]、["tool_executed"]、["step_done"]）。
        - ``mode``：DSH 三分法分发模式——
          - ``"emit"``：广播，回调 ``callback(event)``，异常不影响主流程；
          - ``"waterfall"``：中间件链，回调 ``callback(event, next)``，
            须 ``await next()`` 传递 / ``await next(new_event)`` 改写 / 不调 next 中止；
          - ``"serial"``：终态检查点，回调 ``callback(event) -> Optional[decision]``，
            首个非 None/False 决策胜出。
        - 事件在持久化后通知（waterfall 在链结束后持久化最终事件）；
          回调可为同步或异步；异常不影响主流程。
        - 可在引擎装配前调用（共享 EventStream 独立于 runtime 懒创建）。
        """
        return self._ensure_v2_event_stream().subscribe(
            callback, event_types=event_types, mode=mode
        )

    @property
    def v2_job_registry(self) -> Any:
        """V2 引擎的 JobRegistry（harness.jobs 的对外视图）。

        产品层 AsyncTaskCoordinator 可把任务状态同步进本 registry（纯增量），
        引擎/子 agent 经 ``harness.jobs`` 查询；未装配返回 None。
        """
        if self._v2_harness is None:
            return None
        return self._v2_harness.jobs

    @property
    def _v2_conv_id(self) -> str:
        """V2 事件日志的会话级 conv_id（跨轮稳定）。

        serve 层每轮对话会生成新的 conv_id（``base_N``），但事件日志必须按
        会话聚合（跨轮连续），否则多轮追问历史断裂。用 conv_session_id
        （= base，稳定）作为事件 conv_id；gpts_messages 仍用 serve 的每轮
        conv_id（产品回放语义不变）。
        """
        return (
            self.not_null_agent_context.conv_session_id
            or self.not_null_agent_context.conv_id
        )

    def set_v2_engine_ready_hook(self, hook: Any) -> None:
        """注册 engine 装配完成回调（serve 层绑定 job_registry 等）。

        ``_ensure_v2_engine`` 为懒装配（首轮 thinking 时执行）；serve 层在
        build 时无法拿到 ``v2_job_registry``（harness 未建），通过本钩子在
        装配完成后得到回调（携带本 agent 实例）。
        """
        self._v2_engine_ready_hook = hook

    # ------------------------------------------------------------------
    # V2 引擎装配
    # ------------------------------------------------------------------

    async def _ensure_v2_engine(self) -> Optional[V2AgentRuntime]:
        """装配 V2 run_loop 所需的 thinking_fn / acting_fn / permission_gate。"""
        if self._v2_engine_initialized and self._v2_runtime is not None:
            return self._v2_runtime
        _t0 = time.monotonic()
        try:
            llm_client: Optional[AIWrapper] = getattr(self, "llm_client", None)
            if llm_client is None:
                raise ValueError("V2Agent requires llm_client (AIWrapper) initialized")

            model_alias, _ = await self.select_llm_model()

            # 0. DB capability 切到 DSH 模式：inject_schema=False → 不拼
            #    schema 进 system prompt，按需 ``db({action: ...})`` 取
            #    （对齐 DSH tool-db "不拼 schema 进 prompt"）。
            try:
                cap_pack = getattr(self, "capability_pack", None)
                if cap_pack is not None:
                    for c in cap_pack.get_all("db"):
                        if hasattr(c, "_inject_schema"):
                            c._inject_schema = False
                    # Skill capability 切到 DSH 模式：跳过 <available_skills> SYSTEM
                    # 注入，避免与 SkillCatalogConsumer 目录重复；skill 事实源
                    # 统一归 V2 SkillRegistry（对齐 DSH tool-skill）。
                    for c in cap_pack.get_all("skill"):
                        if hasattr(c, "_inject_system_catalog"):
                            c._inject_system_catalog = False
            except Exception:  # noqa: BLE001
                logger.debug(
                    "[V2Agent] flip db/skill capability DSH-mode failed",
                    exc_info=True,
                )

            # 1. thinking_fn：LLM 上下文由事件日志投影单源提供（default_thinking
            #    的 context_provider），不再读 gpts_messages。ContextEngine 仅保留
            #    render_tool_calls=False 守卫：即便任何遗留路径碰它，工具事实也不会
            #    二次渲染进 LLM 上下文（工具事实只经事件投影进入）。
            context_engine = await self._ensure_context_engine()
            try:
                if context_engine is not None and hasattr(
                    context_engine, "config"
                ):
                    context_engine.config.render_tool_calls = False
            except Exception:  # noqa: BLE001
                logger.debug("[V2Agent] disable render_tool_calls failed", exc_info=True)

            from gyra.agent.core.v2.llm_stream_adapter import make_gyra_llm_stream_fn

            async def _get_function_calling_context():
                """懒构建 function_calling_context（复用 V1 工具声明构建链）。

                首轮先构建并缓存到 self.function_calling_context；后续轮次直接复用，
                避免多步 run_loop 内重复全量构建。
                在 V1 工具声明基础上追加 V2 引擎专用工具（spawn_subagent），
                使 LLM 感知子 Agent seam 能力。
                """
                try:
                    fcc = getattr(self, "function_calling_context", None)
                    if fcc is None or not fcc.get("tools"):
                        fcc = await self.function_calling_params()
                        self.function_calling_context = fcc
                    # 追加 V2 引擎专用工具声明（子 Agent seam 装配后才可用）：
                    # 用工具实例的 to_openai_tool() 生成（单一事实源，非硬编码）
                    if spawn_subagent_tool is not None:
                        try:
                            tool_decls = list(fcc.get("tools") or [])
                            has_spawn = any(
                                (t.get("function") or {}).get("name")
                                == "spawn_subagent"
                                for t in tool_decls
                            )
                            if not has_spawn:
                                fcc = dict(fcc)
                                fcc["tools"] = tool_decls + [
                                    spawn_subagent_tool.to_openai_tool()
                                ]
                        except Exception:  # noqa: BLE001
                            pass
                    return fcc
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"[V2Agent] function_calling_params failed: {e}"
                    )
                    return None

            # 0. Skill catalog consumer（对齐 DSH tool-skill）：
            #    把可用 skill 列表按 digest 变化以 user-role reminder 注入，
            #    避免污染 system prompt（KV-cache 友好）。
            catalog_consumer = self._ensure_v2_catalog_consumer()
            # 0.1 DB 列表 consumer（对齐 DSH tool-db）：可用 DB 列表按 digest
            #     变化以 user-role reminder 注入（**不**含 schema 详情，按需
            #     ``db({action: "describe_tables"})`` 取）。
            db_catalog_consumer = self._ensure_v2_db_catalog_consumer()

            # 0.2 ContextManager：token meter + spill + compaction 统一编排
            #     （thinking_fn 用它做 pre_step spill；V2AgentRuntime 做 post_step）。
            context_manager = None
            try:
                from gyra.agent.core.v2.context_manager import (
                    ContextManager,
                    ContextManagerConfig,
                )
                context_manager = ContextManager(
                    store=self._ensure_v2_state_store(),
                    event_stream=self._ensure_v2_event_stream(),
                    model=model_alias,
                    conv_id=self._v2_conv_id,
                    config=ContextManagerConfig(),
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[V2Agent] context manager init failed: {e}")

            # 子 Agent seam（懒装配）：闭包变量供 _get_function_calling_context
            # 与 thinking/acting 复用；装配失败时保持 None（无 spawn_subagent）。
            subagent_runtime = None
            spawn_subagent_tool = None
            # JobRegistry（对齐 DSH ctx.jobs）：异步任务统一注册/查询。
            # 子 agent 终态经 seam 同步进 registry；产品层 AsyncTaskCoordinator
            # 也可把任务状态同步进来（纯增量，不影响 serve 台账）。
            from gyra.agent.core.v2 import JobRegistry

            job_registry = JobRegistry()
            # 已通知过的子任务（避免异步子 agent 终态重复注入）
            _sub_notified: set = set()

            async def _operational_reminders() -> Optional[str]:
                """运行时操作上下文（异步任务完成通知 + 子 agent 完成 + 用户补充输入）。

                对齐 V1 ``_operational_parts`` 语义，追加到 system prompt 尾部；
                TODO 列表**不**在此注入（对齐 DSH tool-todo，由 todowrite 工具
                参数 + 结果回显自见，避免污染 KV-cache 前缀）。
                """
                parts: List[str] = []
                # 1) V1 异步任务（media 生成 + spawn_agent_task 后台子 Agent）完成通知
                try:
                    bg = await self._collect_background_notifications()
                    if bg:
                        self._bg_notif_delivered = True
                        parts.append("[异步任务完成通知]\n" + bg)
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[V2Agent] collect bg notifications failed: {e}")
                # 2) V2 引擎内异步子 agent 完成通知（经 harness.jobs 终态查询，
                #    SubAgentRuntime seam 在 spawn/终态时同步状态）
                try:
                    if job_registry is not None:
                        _done_jobs = [
                            _j
                            for _j in job_registry.list_for_conv(
                                self._v2_conv_id
                            )
                            if _j.get("kind") == "subagent"
                            and _j.get("status")
                            in ("completed", "failed", "cancelled")
                            and _j.get("task_id") not in _sub_notified
                        ]
                        _sub_parts = []
                        for _j in _done_jobs:
                            _sub_notified.add(_j["task_id"])
                            _sub_parts.append(
                                f"- 子任务 {_j['task_id']} "
                                f"({_j.get('agent_name', '')}) 已结束: "
                                f"{_j['status']}"
                            )
                        if _sub_parts:
                            parts.append("[子任务完成通知]\n" + "\n".join(_sub_parts))
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[V2Agent] subagent done collect failed: {e}")
                # 3) 用户补充输入（InteractionGateway 队列，清空式消费）
                try:
                    session_id = (
                        self.not_null_agent_context.conv_session_id
                        or self.not_null_agent_context.conv_id
                    )
                    supp = await self._collect_supplemental_user_input(session_id)
                    if supp:
                        parts.append(supp)
                except Exception as e:  # noqa: BLE001
                    logger.debug(
                        f"[V2Agent] collect supplemental input failed: {e}"
                    )
                return "\n\n".join(parts) if parts else None

            thinking_fn = make_default_thinking_fn(
                llm_stream_fn=make_gyra_llm_stream_fn(
                    llm_client,
                    model_alias,
                    get_function_calling_context=_get_function_calling_context,
                ),
                model_alias=model_alias,
                memory_bundle=getattr(self, "_memory_bundle", None),
                system_prompt=None,  # 由 input_["system_prompt"] 注入
                # V2 单源：LLM 上下文完全来自事件日志投影
                # （user/assistant/tool 消息 + compaction 摘要），不再读 gpts_messages
                context_provider=self._v2_build_full_context,
                catalog_consumer=catalog_consumer,
                db_catalog_consumer=db_catalog_consumer,
                # 上下文生命周期：pre_step spill 超大工具结果
                context_manager=context_manager,
                # think-time 注入：异步任务完成通知 + 用户补充输入（对齐 V1）
                operational_reminders_provider=_operational_reminders,
            )

            # 2. acting_fn：复用现有工具注入（available_system_tools + resource）
            system_tools = dict(getattr(self, "available_system_tools", None) or {})
            tool_resolver = ToolResolver(
                system_tools=system_tools,
                resource_pack=getattr(self, "resource", None),
            )
            # 注入 V2 引擎专用工具：SkillTool（对齐 DSH tool-skill：唯一的
            # ``skill`` 入口，V1/V2 公用；V1 的无 registry 退化为磁盘/沙箱读取）
            try:
                from gyra.agent.core.v2.skills import (
                    SkillTool,
                    SKILL_TOOL_NAME,
                    LAYER_SCOPE,
                )
                skill_registry = self._ensure_v2_skill_registry()
                skill_tool = SkillTool(
                    skill_registry,
                    layer_chain=[LAYER_SCOPE, "host"],
                    cwd=None,
                )
                tool_resolver.register_tool(SKILL_TOOL_NAME, skill_tool)
            except Exception:  # noqa: BLE001
                logger.debug(
                    "[V2Agent] skill tool not wired",
                    exc_info=True,
                )
            # 注入 V2 引擎专用工具：DbTool（对齐 DSH tool-db：单入口
            # ``db({action, ...})`` 取代 V1 get_table_spec/execute_sql/list_tables/
            # search_tables 四件套；V1 工具继续保留供 V1 链路使用）
            try:
                from gyra.agent.core.v2 import DbTool, DB_TOOL_NAME
                tool_resolver.register_tool(DB_TOOL_NAME, DbTool())
            except Exception:  # noqa: BLE001
                logger.debug(
                    "[V2Agent] db tool not wired",
                    exc_info=True,
                )
            # 持住工厂引用：供 run_step/resume_step 构造 ToolContext 时注入 agent
            # （对齐 V1 tool_action 的 ``arguments["agent"] = agent``；否则 todowrite/
            # todoread 等统一框架工具拿不到 agent，报 "Todo 存储不可用"）。
            self._v2_tool_context_factory = ToolContextFactory(
                agent_id=self.not_null_agent_context.agent_app_code,
                conv_id=self._v2_conv_id,
                agent=self,
            )
            acting_fn = make_default_acting_fn(
                tool_resolver=tool_resolver,
                doom_loop_detector=DoomLoopAdapter(
                    getattr(self, "_doom_loop_detector", None)
                ),
                failure_tracker=ToolFailureTracker(max_failures=3),
                truncator=TruncatorAdapter(getattr(self, "_truncator", None)),
                tool_context_factory=self._v2_tool_context_factory,
            )

            # 2.5 SubAgent seam（对齐 DSH ctx.subagents）：子 agent 复用主
            #     thinking/acting fn（子 agent 由 input_ 字段驱动会话绑定），
            #     装配 spawn_subagent 工具并注册进 tool_resolver + function_calling_context。
            try:
                from gyra.agent.core.v2 import SubAgentRuntime, SpawnSubagentTool

                subagent_runtime = SubAgentRuntime(
                    state_store=self._ensure_v2_state_store(),
                    default_thinking_fn=thinking_fn,
                    default_acting_fn=acting_fn,
                    default_user_id=getattr(
                        self.not_null_agent_context, "staff_no", None
                    ),
                    # 子 agent 终态同步进 harness.jobs（seam 统一查询）
                    job_registry=job_registry,
                )
                spawn_subagent_tool = SpawnSubagentTool(subagent_runtime)
                tool_resolver.register_tool(
                    "spawn_subagent", spawn_subagent_tool
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[V2Agent] subagent runtime not wired: {e}")
                subagent_runtime = None

            # 3. PermissionGate：复用现有规则集（fail-closed 单调守卫可经 register_guard 扩展）。
            #    interaction_adapter 从 ReActMaster interaction extension 获取
            #    （V1 ask_user/授权共用同一 adapter，ASK 路径才可真正询问用户）。
            _interaction_adapter = None
            try:
                _ext = self._get_interaction_extension()
                if _ext is not None:
                    _interaction_adapter = _ext.adapter
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[V2Agent] interaction adapter resolve failed: {e}")
                _interaction_adapter = None
            gate = PermissionGate(
                state_store=self._ensure_v2_state_store(),
                event_stream=self._ensure_v2_event_stream(),
                interaction_adapter=_interaction_adapter,
                session_cache=SessionPermissionCache(),
                ruleset=getattr(self, "permission_ruleset", None),
                mode=PermissionMode.DEFAULT,
                step_id=None,  # bound by run_step
                conv_id=self._v2_conv_id,
                agent_id=self.not_null_agent_context.agent_app_code,
                tool=None,
            )

            # 3.5 HookManager + memory tier0-3（turn_complete / conversation_complete）：
            #     memory_bundle 已由 ReActMasterAgent 装配时初始化。
            hook_manager = None
            try:
                from gyra.agent.core.hook.manager import HookManager
                from gyra.agent.core.hook.schema import TeamHookConfig

                hook_manager = HookManager(config=TeamHookConfig(enabled=True))
                memory_bundle = getattr(self, "_memory_bundle", None)
                if memory_bundle is not None:
                    from gyra.agent.core.v2 import register_memory_hooks

                    register_memory_hooks(
                        hook_manager=hook_manager,
                        memory_bundle=memory_bundle,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[V2Agent] hook manager not wired: {e}")
                hook_manager = None

            # 3.6 JobRegistry 已在上方（子 Agent seam 装配处）创建，见闭包变量
            #     ``job_registry``；此处直接注入 harness，不再重复实例化。

            # 4. 统一装配：组装 HarnessContext（V2 引擎服务总线）。
            #    run_loop/run_step/V2AgentRuntime 只消费 harness，不再散传依赖。
            #    storage=真实持久化 StateStore；events=共享事件流（插件订阅挂载点）；
            #    tools=统一工具入口；approval=审批门（含 serial 决策检查点）；
            #    subagents=子 Agent seam（SubAgentRuntime）；jobs=异步任务注册表；
            #    hooks=HookManager（turn_complete/conversation_complete + memory tier0-3）；
            #    skills=SkillSeam（对齐 DSH ctx.skills：catalog digest + 工具）。
            from gyra.agent.core.v2.harness import HarnessContext, VisBridge
            from gyra.agent.core.v2.skills import (
                SkillRegistry,
                LAYER_SCOPE,
            )

            # skill 资源总线：每个 agent 持有一个 registry；provider 列表由
            # FilesystemSkillProvider 装配（可覆盖到 sandbox）。
            self._v2_skill_registry = self._ensure_v2_skill_registry()

            self._v2_harness = HarnessContext(
                storage=self._ensure_v2_state_store(),
                events=self._ensure_v2_event_stream(),
                tools=tool_resolver,
                approval=gate,
                subagents=subagent_runtime,  # 引擎内子 Agent seam
                jobs=job_registry,           # 异步任务注册表（产品层可同步）
                hooks=hook_manager,          # HookManager（turn_complete 等钩子）
                skills=self._v2_skill_registry,  # SkillSeam（对齐 DSH ctx.skills）
                thinking_fn=thinking_fn,
                acting_fn=acting_fn,
                tool_context_factory=self._v2_tool_context_factory,
            )

            # 5. vis 渲染桥：以 emit 订阅者身份消费 harness 事件流
            #    （llm_token 增量渲染 / step_done 终态重置 → BAIZE vis）。
            #    对齐 DSH：引擎只产事件，渲染作为订阅者消费事件，不再手动调用。
            self._v2_vis_bridge = VisBridge(
                agent=self,
                event_stream=self._ensure_v2_event_stream(),
            )
            self._v2_vis_bridge.attach()

            # 5.5 usage_metric 事件订阅：桥接 V1 前端用量展示。
            #     V2 架构：引擎只产事件（每 LLM 调用一次 usage_metric），
            #     展示作为事件流订阅者消费——无需逐帧去重/手工状态。
            self.subscribe_step_event(
                self._bridge_v1_usage_metric,
                event_types=["usage_metric"],
                mode="emit",
            )

            self._v2_model_alias = model_alias
            self._v2_runtime = V2AgentRuntime(
                agent_id=self.not_null_agent_context.agent_app_code,
                conv_id=self._v2_conv_id,
                harness=self._v2_harness,
                max_steps=getattr(self, "get_effective_max_steps", lambda: 20)()
                if callable(getattr(self, "get_effective_max_steps", None))
                else 20,
                model_alias=model_alias,
                # 复用已装配的 ContextManager（pre_step spill 同实例）
                context_manager=context_manager,
            )
            self._v2_engine_initialized = True
            logger.info(
                "[V2_ENGINE][PERF] engine assembled in %.1fms (conv=%s)",
                (time.monotonic() - _t0) * 1000,
                self._v2_conv_id,
            )
            # engine 装配完成 → 通知 serve 层钩子（绑定 job_registry 等）
            hook = getattr(self, "_v2_engine_ready_hook", None)
            if hook is not None:
                try:
                    res = hook(self)
                    if inspect.isawaitable(res):
                        await res
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[V2Agent] engine ready hook failed: {e}")
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
        self._v2_thinking_answer = ""
        self._v2_awaiting_user = False
        self._v2_reply_message_id = reply_message_id
        self._v2_start_time = datetime.now()
        self._v2_pending_tool_calls = []
        # 左面板规划空间根节点：base_agent.generate_reply 以用户消息 id 建了
        # AGENT 节点，工具 TASK 节点挂它下面（与 V1 任务树结构一致）
        self._v2_root_node_id = (
            getattr(received_message, "message_id", None) if received_message else None
        )
        # vis 渲染桥：每轮 turn 设置渲染上下文（llm_token/step_done 订阅者消费）
        bridge = self._v2_vis_bridge
        if bridge is not None:
            logger.info(
                f"[V2Agent][D][begin_turn] reply_message_id={reply_message_id!r}, "
                f"has_reply_message={reply_message is not None}, "
                f"goal_id={getattr(reply_message, 'goal_id', None)!r}"
            )
            bridge.begin_turn(
                reply_message_id=reply_message_id,
                start_time=self._v2_start_time,
                received_message=received_message,
                reply_message=reply_message,
            )

        user_prompt = self._extract_text_from_content(
            getattr(received_message, "content", None) or ""
        )
        # 多模态：提取媒体段（图片/音频/视频/文件）随 input_ 透传给 thinking_fn
        media_items = self._extract_media_items(
            getattr(received_message, "content", None) or []
        )
        conv_id = self._v2_conv_id
        session_id = self.not_null_agent_context.conv_session_id or conv_id
        system_prompt = prompt or (
            getattr(reply_message, "system_prompt", None) if reply_message else None
        )

        runtime = await self._ensure_v2_engine()
        if runtime is None:
            raise ValueError("[V2Agent] V2 engine not available")

        # V2 单源：用户消息写入事件日志（user/message 事件），
        # 下轮 LLM 上下文经 ProjectorRegistry 全量投影恢复，不依赖 gpts_messages。
        await self._emit_dialog_message("user", user_prompt)

        # 运行 run_loop，消费 StepEvent
        try:
            async for step_event in runtime.stream(
                user_prompt,
                extra={
                    "session_id": session_id,
                    "conv_id": conv_id,
                    "agent_id": self.not_null_agent_context.agent_app_code,
                    # 透传 system prompt：default_thinking 从 input_["system_prompt"]
                    # 读取并作为首条 system 消息注入 LLM（缺省则模型完全无系统指令，
                    # 表现为无目标地反复探索工具）。注意：缺省时 input_ 无该键，这里
                    # 即使为 None 也显式携带，让 thinking_fn 的 fallback 语义保持清晰。
                    "system_prompt": system_prompt,
                    # 多模态媒体段（OpenAI content items 数组）
                    "media_items": media_items,
                },
            ):
                await self._handle_v2_step_event(step_event, received_message)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[V2Agent] run_loop failed: {e}", exc_info=True)
            raise
        finally:
            # 收尾兜底:个别工具结果帧可能因丢帧/WorkEntry 绑定失败未把步骤翻成
            # 终态。turn 结束(run_loop 正常返回或异常)时对仍 pending 的工具调用
            # 补推一次终态 TASK 节点,避免前端步骤永远停在 running。
            await self._flush_pending_tool_states()

        # V2 单源：最终答案写入事件日志（assistant/message 事件）
        await self._emit_dialog_message("assistant", self._v2_final_answer)

        # token 占用环形图桥接：turn 收尾用 V2 TokenMeter 快照驱动 V1 展示
        await self._emit_v1_context_usage(runtime)

        model_name = getattr(runtime, "model_alias", None)
        logger.info(
            f"[V2Agent][D][final] _v2_final_answer_len={len(self._v2_final_answer)}, "
            f"thinking_len={len(self._v2_thinking_answer)}, "
            f"final_head={self._v2_final_answer[:60]!r}, "
            f"final_tail={self._v2_final_answer[-60:]!r}"
        )
        # 组装 V1 协议输出：content=最终正文（content 通道），
        # thinking_content=推理文本（thinking 通道），与 V1 渲染语义对齐，
        # 避免最终消息把推理与正文混在一起反复展示。
        return AgentLLMOut(
            llm_name=model_name,
            thinking_content=self._v2_thinking_answer,
            content=self._v2_final_answer,
            tool_calls=[],
        )

    async def _handle_v2_step_event(
        self,
        step_event: StepEvent,
        received_message: Optional[AgentMessage] = None,
    ) -> None:
        """消费 StepEvent：业务累积 + 会话持久化。

        vis 渲染（llm_token 增量 / step_done 终态重置）已迁移到 VisBridge——
        以 harness 事件流订阅者身份触发，V2Agent 不再手动调用渲染方法。
        """
        if step_event.event_type == "llm_token":
            token = (step_event.output or {}).get("token", "")
            if token:
                # thinking 通道 → 推理文本；content 通道 → 最终答案正文。
                # 分开累积，最终消息的 thinking/content 字段各自干净。
                channel = (step_event.output or {}).get("channel", "content")
                if channel == "thinking":
                    self._v2_thinking_answer += token
                else:
                    self._v2_final_answer += token
                if len(self._v2_final_answer + self._v2_thinking_answer) < 200 or True:
                    logger.info(
                        f"[V2Agent][D][accumulate] llm_token channel={channel!r} "
                        f"token_len={len(token)}, final_len={len(self._v2_final_answer)}, "
                        f"thinking_len={len(self._v2_thinking_answer)}, "
                        f"final_head={self._v2_final_answer[:40]!r}"
                    )
                # 渲染由 VisBridge 订阅者处理（引擎只产事件）
        elif step_event.event_type == "tool_call":
            # 出现工具调用说明当前 step 之后还会续跑：其正文/思考只是中间旁白，
            # 清空累积——最终答案/思考只保留最后一个 step（无工具调用）的内容，
            # 否则所有 step 的旁白会拼接进最终消息，导致结论文本乱码式重复。
            # 旁白快照随 pending 工具调用保存，供 WorkEntry.assistant_content 记录。
            logger.info(
                f"[V2Agent][D][accumulate] tool_call CLEARS final_answer: "
                f"prev_final_len={len(self._v2_final_answer)}, tool={step_event.input.get('tool') if step_event.input else None}"
            )
            self._v2_pending_narration = self._v2_final_answer
            self._v2_final_answer = ""
            self._v2_thinking_answer = ""
            # 记录工具调用：写一条带 tool_calls 的 assistant 消息进会话，
            # 供 run_loop 下一轮 thinking 的 ContextEngine 渲染 CALL 单元。
            await self._persist_v2_tool_call(step_event)
        elif step_event.event_type == "tool_result":
            # 回填工具执行结果：写 WorkEntry（按 tool_call_id 关联），
            # 并收集 ActionOutput 供 act() 返回（V1 外层 action_report）。
            await self._persist_v2_tool_result(step_event)
        elif (
            step_event.event_type == "interaction_request"
            and step_event.state == StepState.AWAITING_USER
        ):
            # ask_user 交互工具已把 run_loop 挂起为 AWAITING_USER：记录标记，
            # act() 据此返回 ask_user=True 的 ActionOutput，V1 外层将会话置 WAITING，
            # 前端提交回答时经 interaction_checkpoint 恢复同一会话（而非新建 _2）。
            self._v2_awaiting_user = True
        # step_done 的 vis 终态重置由 VisBridge 订阅处理

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
            # 携带 running 态 ActionOutput：vis 转换器据此刻画左面板规划空间的
            # 工具步骤（_act_out_2_plan）；结果返回后 action_report 由 WorkEntry
            # 动态重建（complete/failed），状态经 TASK 节点重推刷新
            action_report=[
                ActionOutput(
                    action_id=tool_call_id,
                    name=tool_name,
                    action=tool_name,
                    action_input=args,
                    content="",
                    state=Status.RUNNING.value,
                    start_time=datetime.now(),
                    have_retry=False,
                )
            ],
        )
        try:
            await gpts_memory.append_message(conv_id, gmsg, save_db=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] persist tool_call message failed: {e}")
            return
        # 挂 TASK 节点到规划空间任务树：upsert_task -> push(new_task_nodes)
        # -> 转换器渲染该消息的 plan item（V1 每轮 upsert_task 的对齐路径）
        await self._upsert_v2_tool_task_node(
            message_id=message_id,
            tool_name=tool_name,
            state=Status.RUNNING.value,
        )
        self._v2_pending_tool_calls.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "args": args,
                "message_id": message_id,
                # 调用前的旁白快照（此时 _v2_final_answer 已被 tool_call 事件清空）
                "narration": getattr(self, "_v2_pending_narration", "") or "",
            }
        )

    async def _upsert_v2_tool_task_node(
        self, message_id: str, tool_name: str, state: str
    ) -> None:
        """把工具步骤挂成任务树的 TASK 节点并推送前端（左面板规划空间）。

        vis_messages 会为 v2 消息绑定 WorkEntry 重建 action_report，转换器
        _gen_plan_items -> _act_out_2_plan 即可产出 d-agent-plan 工具步骤条目。
        """
        gpts_memory = self.memory.gpts_memory if self.memory else None
        if gpts_memory is None or not self._v2_root_node_id:
            return
        try:
            await gpts_memory.upsert_task(
                conv_id=self.not_null_agent_context.conv_id,
                task=TreeNodeData(
                    node_id=message_id,
                    parent_id=self._v2_root_node_id,
                    content=AgentTaskContent(
                        agent_name=self.name or self.role,
                        task_type=AgentTaskType.TASK.value,
                        message_id=message_id,
                    ),
                    state=state,
                    name=tool_name,
                ),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] upsert tool task node failed: {e}")

    async def _persist_v2_tool_result(self, step_event: StepEvent) -> None:
        """回填工具执行结果（WorkEntry）。

        工具结果经 WorkEntry 写回会话（vis_messages/vis_final 会绑定 work entries
        渲染执行步骤），不再收集 ActionOutput——act() 只返回终止型收尾，避免最终
        消息 action_report 重复携带工具结果导致"结果出现多次"。
        """
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
                # 工具 view 通道：skill_meta 包装成 d-skill-meta VIS 标签，
                # 经 WorkEntry.view → action_report 送前端渲染（不进 LLM 上下文）
                skill_meta = output.get("skill_meta")
                view_text = None
                if skill_meta:
                    from gyra.agent.core.v2.skills.skill_tool import (
                        _skill_meta_view,
                    )
                    view_text = _skill_meta_view(str(skill_meta))
                entry = WorkEntry(
                    timestamp=step_event.timestamp or time.time(),
                    tool=pending["tool_name"],
                    args=pending["args"],
                    result=result_text or None,
                    view=view_text,
                    success=success,
                    status=WorkLogStatus.ACTIVE.value,
                    tool_call_id=pending["tool_call_id"],
                    message_id=pending["message_id"],
                    conv_id=self.not_null_agent_context.conv_id,
                    assistant_content=pending.get("narration") or "",
                    round_index=0,
                )
                await gpts_memory.append_work_entry(
                    self.not_null_agent_context.conv_id, entry, save_db=True
                )
                # 关键:把 WorkEntry 关联回 tool_call 消息并失效 action_report 缓存。
                # tool_call 消息创建时缓存了 state=RUNNING 的 action_report(GptsMessage
                # __post_init__ 路由到 _action_report_cache),不主动失效则流式 vis 重建
                # 永远拿到 RUNNING 缓存——所有工具步骤卡「运行中」。set_work_entries 会
                # 清空缓存,后续 action_report 属性从 WorkEntry 动态重建为终态。
                cache = await gpts_memory.cache(self.not_null_agent_context.conv_id)
                tool_msg = (
                    cache.messages.get(pending["message_id"]) if cache else None
                )
                if tool_msg is not None:
                    entries = (
                        cache.work_entries_by_message.get(pending["message_id"])
                        if cache
                        else None
                    )
                    tool_msg.set_work_entries(entries or [entry])
                    # 回写 DB：WorkEntry 绑定后 action_report 已按执行结果重建
                    # （含结果文本/失败原因），需同步持久化；否则 DB 里残留消息创建时
                    # 的 RUNNING 空快照，刷新后工具步骤只显示状态、没有结果内容。
                    try:
                        execute_no_wait(
                            gpts_memory.message_memory.update, tool_msg
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            f"[V2Agent] persist rebuilt tool action_report failed: {e}"
                        )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[V2Agent] persist tool_result work_entry failed: {e}")
        # 结果就绪后重推 TASK 节点：消息此时已绑定 WorkEntry（action_report
        # 重建为 complete/failed），左面板工具步骤状态随之刷新
        await self._upsert_v2_tool_task_node(
            message_id=pending["message_id"],
            tool_name=pending["tool_name"],
            state=Status.COMPLETE.value if success else Status.FAILED.value,
        )

    async def _flush_pending_tool_states(self) -> None:
        """turn 收尾兜底:把仍 pending 的工具调用补推一次终态。

        tool_result 的状态翻转依赖单次推送帧(upsert_task → push_message),
        帧丢失或 WorkEntry 绑定失败都会让前端步骤停在 running。run_loop 结束时
        对仍未出队的 pending 调用强制置 failed(工具未正常回结果),清空队列。
        """
        if not self._v2_pending_tool_calls:
            return
        leftovers, self._v2_pending_tool_calls = self._v2_pending_tool_calls, []
        for pending in leftovers:
            try:
                await self._upsert_v2_tool_task_node(
                    message_id=pending["message_id"],
                    tool_name=pending["tool_name"],
                    state=Status.FAILED.value,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[V2Agent] flush pending tool state failed: {e}")

    async def _emit_dialog_message(self, role: str, content: str) -> None:
        """emit user/message 或 assistant/message 到事件日志（V2 单源事实）。

        每轮 turn 结束时成对写入（用户消息 + 最终答案），下轮 LLM 上下文经
        ProjectorRegistry 全量投影即可恢复完整对话——不再依赖 gpts_messages。
        """
        if not content:
            return
        from gyra.agent.core.v2.step_event import StepEvent
        from gyra.agent.core.v2.step_state import StepState

        try:
            stream = self._ensure_v2_event_stream()
            if self._v2_dialog_seq["n"] == 0:
                existing = await self._ensure_v2_state_store().get_events(
                    self._v2_conv_id
                )
                self._v2_dialog_seq["n"] = (
                    max((e.seq for e in existing), default=-1) + 1
                )
            ev = StepEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                step_id=f"dialog-{uuid.uuid4().hex[:6]}",
                conv_id=self._v2_conv_id,
                agent_id=self.not_null_agent_context.agent_app_code,
                parent_step_id=None,
                state=StepState.DONE,
                event_type=f"{role}/message",
                input={},
                output={"text": content},
                seq=self._v2_dialog_seq["n"],
                timestamp=time.time(),
            )
            self._v2_dialog_seq["n"] += 1
            await stream.emit(ev)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] emit {role}/message failed: {e}")

    async def _v2_build_full_context(
        self,
        conv_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[dict]:
        """V2 单源：从事件日志投影完整 LLM 上下文（user/assistant/tool + 摘要）。

        替代旧版从 gpts_messages 构建的 ContextEngine 输入——用户/助手消息、
        工具事实、压缩摘要全部来自 V2 事件日志。按 agent_id 过滤（排除
        shared_conv 子 agent），预算截断保留摘要 + 近期消息（多轮追问不丢近期）。

        子 agent 复用本方法时传入子 conv_id / 子 agent_id（default_thinking
        从 input_ 透传），各自投影自己的事件日志。
        """
        try:
            from gyra.agent.core.v2.projector_registry import get_projector_registry

            conv_id = conv_id or self._v2_conv_id
            if agent_id is None:
                agent_id = self.not_null_agent_context.agent_app_code
            events = await self._ensure_v2_state_store().get_events(conv_id)
            events = [
                e for e in events if getattr(e, "agent_id", None) == agent_id
            ]
            msgs = get_projector_registry().project_events(events)
            return await self._trim_full_context(msgs)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] build full context failed: {e}")
            return []

    async def _trim_full_context(self, msgs: List[dict]) -> List[dict]:
        """预算截断完整上下文：保留 compaction 摘要（开头）+ 最近消息（成对）。

        预算 = context_window × 60%（对话为主）；早期超出预算的事件由 Compactor
        摘要兜底（若压缩未触发，早期历史被截断——近期多轮追问不受影响）。
        """
        if not msgs:
            return msgs
        try:
            window = await self.get_agent_llm_context_length()
        except Exception:  # noqa: BLE001
            window = 128000
        budget = max(int(window * 0.6), 4000)

        def _msg_tokens(m: dict) -> int:
            n = len(str(m.get("content", "")))
            for tc in m.get("tool_calls") or []:
                n += len(str((tc.get("function") or {}).get("arguments", "")))
            return max(1, n // 4)

        # compaction 摘要（system 消息）始终保留在开头
        summary_msgs = [m for m in msgs if m.get("role") == "system"]
        rest = [m for m in msgs if m.get("role") != "system"]
        total = sum(_msg_tokens(m) for m in summary_msgs)
        kept_recent: List[dict] = []
        pending: List[dict] = []
        for m in reversed(rest):
            if total >= budget and (pending or kept_recent):
                break
            pending.append(m)
            total += _msg_tokens(m)
            if m.get("role") == "tool":
                kept_recent = list(reversed(pending)) + kept_recent
                pending = []
        if pending:
            kept_recent = list(reversed(pending)) + kept_recent
        return summary_msgs + kept_recent

    async def _v2_build_extra_tool_messages(self) -> List[dict]:
        """从 V2 事件日志投影工具执行历史（事实源统一 + replace_shadow 折叠）。

        每轮 thinking 注入，确保模型在后续步骤能看到工具执行事实，收敛多步循环。
        - 用 :class:`ProjectorRegistry.project_events`：消费 ``compaction/summary``
          事件（replace_shadow 折叠被压缩历史为摘要）与 tool_call/tool_result 配对；
        - 按 agent_id 过滤：shared_conv 子 agent 事件不混入主会话投影
          （子 agent 的 agent_id 为 ``subagent-task-*``）；
        - **量级控制**：按 token 预算截断、只保留最近工具调用——事件日志工具历史
          随轮次线性增长，若不设上限会撑爆上下文，导致多轮追问时**近期**工具事实
          被早期海量调用挤掉而丢失。截断保留最近的（追问相关），早期由
          Compactor 摘要兜底（事件日志仍可查）。
        """
        try:
            from gyra.agent.core.v2.projector_registry import get_projector_registry

            events = await self._ensure_v2_state_store().get_events(
                self._v2_conv_id
            )
            agent_id = self.not_null_agent_context.agent_app_code
            events = [
                e for e in events if getattr(e, "agent_id", None) == agent_id
            ]
            msgs = get_projector_registry().project_events(events)
            return await self._trim_tool_history(msgs)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] project tool history failed: {e}")
            return []

    async def _trim_tool_history(self, msgs: List[dict]) -> List[dict]:
        """按 token 预算截断工具历史投影，保留最近调用（多轮追问不丢近期）。

        预算 = context_window × 15%（防御性上限，防止工具历史无界增长撑爆上下文）；
        从末尾（最近）向前累积，超出预算即截断。assistant tool_calls 与其对应
        tool 结果必须成对保留（按配对的 tool 消息为界切分）。
        """
        if not msgs:
            return msgs
        try:
            window = await self.get_agent_llm_context_length()
        except Exception:  # noqa: BLE001
            window = 128000
        budget = max(int(window * 0.15), 2000)

        def _msg_tokens(m: dict) -> int:
            n = len(str(m.get("content", "")))
            for tc in m.get("tool_calls") or []:
                n += len(str((tc.get("function") or {}).get("arguments", "")))
            return max(1, n // 4)

        total = 0
        kept: List[dict] = []
        # 从末尾向前累积；遇到 tool 消息与前面 assistant 的配对必须一起保留，
        # 因此以"tool 消息"为对齐点成块切分。
        pending_pairs: List[dict] = []
        for m in reversed(msgs):
            if total >= budget and (pending_pairs or kept):
                break
            pending_pairs.append(m)
            total += _msg_tokens(m)
            if m.get("role") == "tool":
                kept = list(reversed(pending_pairs)) + kept
                pending_pairs = []
        # 尾部未配对的 assistant tool_calls 也保留（成对语义）
        if pending_pairs:
            kept = list(reversed(pending_pairs)) + kept
        return kept

    async def _bridge_v1_usage_metric(self, step_event: StepEvent) -> None:
        """usage_metric StepEvent 订阅者：桥接 V1 前端用量展示。

        V2 引擎产 ``usage_metric`` 事件（每 LLM 调用一次，含 this_call），
        本回调把它映射到 V1 的 emit_usage_metric（serve 层经
        register_usage_callback 转 SSE）。V2 架构：引擎只产事件，展示作为
        事件流订阅者消费——事件本身每 LLM 调用一次，天然去重。
        """
        this_call = (step_event.output or {}).get("this_call") or {}
        prompt = int(this_call.get("prompt") or 0)
        completion = int(this_call.get("completion") or 0)
        if not prompt and not completion:
            return
        try:
            from gyra.agent.core.usage_metric import (
                emit_usage_metric as v1_emit_usage,
            )

            v1_emit_usage(
                conv_id=self.not_null_agent_context.conv_id,
                model_name=(
                    (step_event.output or {}).get("model")
                    or self._v2_model_alias
                    or ""
                ),
                prompt_tokens=prompt,
                completion_tokens=completion,
                role="main",
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[V2Agent] v1 usage emit skipped: {e}")

    async def _emit_v1_context_usage(self, runtime: Any) -> None:
        """桥接 V1 前端上下文占用环形图：用 V2 TokenMeter 当前占用快照驱动展示。

        注意这里用 :meth:`TokenMeter.snapshot_current`（最近一次 LLM 调用的
        ``this_call.prompt``）而非累计 ``snapshot()``：累计值随每次 LLM 调用
        单调增长，压缩把历史折叠成摘要后累计值并不会回落，导致环形图
        「只增不减、看不到压缩效果」。当前占用取最近一次调用的输入（prompt），
        压缩后下一轮 prompt 明显变小，能正确反映压缩后的上下文空间。
        """
        if runtime is None:
            return
        try:
            cm = getattr(runtime, "_context_manager", None)
            if cm is None:
                return
            snap = await cm.token_meter.snapshot_current(
                model=self._v2_model_alias or None
            )
            if not snap or snap.total <= 0:
                return
            from gyra.agent.core.usage_metric import (
                emit_context_usage as v1_ctx_usage,
            )

            v1_ctx_usage(
                conv_id=self.not_null_agent_context.conv_id,
                total_tokens=snap.total,
                context_window=snap.context_window,
                prompt_tokens=snap.prompt,
                # 当前占用口径不含本call输出；保证 prompt+completion=total
                completion_tokens=0,
                model_name=self._v2_model_alias or "",
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[V2Agent] context usage emit skipped: {e}")

    async def act(
        self,
        message: AgentMessage,
        sender: Agent,
        reviewer: Optional[Agent] = None,
        **kwargs,
    ) -> List[ActionOutput]:
        """run_loop 已在 thinking() 内执行工具；此处仅返回终止型收尾。

        工具步骤**不**再塞进最终消息的 action_report——它们已随各 tool_call 消息
        + WorkEntry 在流式阶段实时渲染（vis_messages/vis_final 绑定 work entries），
        若在此重复返回，manus 转换器会为最终消息再建一批 step_id 不同的步骤，
        造成"工具结果出现多次"。工具结果也已写回会话 WorkEntry（右面板可查）。

        与 V1 对齐：终止型 ActionOutput 附加交付文件（_attach_delivery_files），
        保证右面板交付物列表与 V1 表现一致。
        """
        terminate_out = ActionOutput(
            content=self._v2_final_answer or "V2 引擎已执行完毕",
            name=self.name,
            is_exe_success=True,
            terminate=True,
            # ask_user 交互工具挂起：act() 返回 ask_user=True 的 ActionOutput，
            # V1 外层（UserProxyAgent.receive）据此把会话状态置 WAITING，
            # 前端提交回答时经 interaction_checkpoint 恢复原会话。
            ask_user=self._v2_awaiting_user,
            ask_type=AskUserType.CONCLUSION_INCOMPLETE.value if self._v2_awaiting_user else None,
            # 稳定 action_id + 显式终态 + 收尾时间戳：
            # 避免随机 uuid 被 vis 转换器当成新工具步骤重复渲染；
            # state/start_time 缺失时部分转换器会误判为 running 或参与时序排序。
            action_id=f"v2-terminate-{self._v2_reply_message_id or 'final'}",
            state=Status.COMPLETE.value,
            start_time=datetime.now(),
        )
        # 对齐 V1 act()：terminate 时附加交付文件（AFS 收集结论文件/交付物）
        try:
            if hasattr(self, "_attach_delivery_files"):
                terminate_out = await self._attach_delivery_files(terminate_out)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[V2Agent] attach delivery files failed: {e}")
        return [terminate_out]

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

    @staticmethod
    def _extract_media_items(content: Any) -> List[Dict[str, Any]]:
        """从多模态消息 content 提取媒体段（OpenAI 多模态 content items）。

        输入为 serve 层媒体消息产物（list，每项 ``{type, object: {data, name}}``）；
        图片/音频/视频/文件转成 OpenAI content 数组格式（``image_url`` /
        ``audio_url`` / ``video_url`` / ``file_url``），文本项跳过
        （由 :meth:`_extract_text_from_content` 处理）。支持多模态模型消费。
        """
        items: List[Dict[str, Any]] = []
        if not isinstance(content, list):
            return items
        for item in content:
            if not isinstance(item, dict):
                continue
            ctype = str(item.get("type") or "").lower()
            obj = item.get("object") or {}
            if isinstance(obj, dict):
                data = obj.get("data")
                name = str(obj.get("name") or "")
            else:
                data = getattr(obj, "data", None)
                name = str(getattr(obj, "name", "") or "")
            if not data:
                continue
            if ctype == "text":
                continue
            # 泛化 file 按扩展名细分媒体类型
            mtype = ctype
            if ctype == "file" and name:
                low = name.lower()
                if any(ext in low for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
                    mtype = "image"
                elif any(ext in low for ext in (".mp3", ".wav", ".m4a", ".aac", ".flac")):
                    mtype = "audio"
                elif any(ext in low for ext in (".mp4", ".mov", ".webm", ".avi", ".mkv")):
                    mtype = "video"
            payload_map = {
                "image": ("image_url", {"image_url": {"url": data}}),
                "audio": ("audio_url", {"audio_url": {"url": data}}),
                "video": ("video_url", {"video_url": {"url": data}}),
            }
            kind, payload = payload_map.get(
                mtype, ("file_url", {"file_url": {"url": data}})
            )
            items.append({"type": kind, **payload})
        return items
