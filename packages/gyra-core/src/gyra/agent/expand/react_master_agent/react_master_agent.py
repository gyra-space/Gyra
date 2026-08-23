"""
ReActMaster Agent - 最佳实践的 ReAct 范式 Agent 实现

核心特性：
1. "末日循环" (Doom Loop) 检测机制
2. 上下文压缩 (SessionCompaction)
3. 工具输出截断 (Truncate.output)
4. 历史记录修剪 (prune)
5. Kanban 任务规划（可选，通过 enable_kanban=True 启用）
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable

from gyra._private.pydantic import Field, PrivateAttr
from gyra.configs.model_config import DATA_DIR
from gyra_core.config.schema import DEFAULT_MAX_NEW_TOKENS
import os
from gyra.agent import (
    ActionOutput,
    Agent,
    AgentMessage,
    ProfileConfig,
)
from gyra.agent.core.base_agent import ConversableAgent, ContextHelper
from gyra.agent.core.base_team import Team
from gyra.agent.core.base_parser import SchemaType
from gyra.agent.core.role import AgentRunMode
from gyra.agent.core.schema import Status
from gyra.core.interface.message import ModelMessageRoleType
from gyra.agent.util.llm.llm_client import AgentLLMOut
from gyra.sandbox.base import SandboxBase
from gyra.util.template_utils import render

from gyra.agent.expand.tool_agent.function_call_parser import (
    FunctionCallOutputParser,
    ReActOut,
)

# 导入核心组件
from .doom_loop_detector import (
    DoomLoopDetector,
    IntelligentDoomLoopDetector,
    DoomLoopCheckResult,
)

# 历史压缩已统一收敛到 context_engine.ContextEngine（取代 SessionCompaction /
# HistoryPruner / HistoryMessageBuilder / LayerManager 等历史 7 套机制）。
from .truncation import Truncator, TruncationConfig

from .prompt_fc import (
    REACT_MASTER_FC_SYSTEM_TEMPLATE_CN,
    REACT_MASTER_FC_USER_TEMPLATE_CN,
    REACT_MASTER_FC_WRITE_MEMORY_TEMPLATE_CN,
    REACT_MASTER_FC_SYSTEM_TEMPLATE,
    REACT_MASTER_FC_USER_TEMPLATE,
    REACT_MASTER_FC_WRITE_MEMORY_TEMPLATE,
)
from ...core.file_system.agent_file_system import AgentFileSystem

# 新增模块导入
from .work_log import WorkLogManager, create_work_log_manager
from gyra.agent.project_ecosystem import (
    ECOSYSTEM_AUTO,
    ProjectEcosystem,
    ProjectEcosystemLoader,
)
from gyra.agent.core.memory.gpts.file_base import WorkLogStatus
from gyra.agent.core.hook_context_builders import (
    build_conversation_complete_context,
)
from .phase_manager import PhaseManager, TaskPhase, create_phase_manager
from .report_generator import ReportGenerator, ReportType, ReportFormat
from .kanban_manager import (
    KanbanManager,
    create_kanban_manager,
    validate_deliverable_schema,
)
from gyra.agent.core.memory.gpts.system_event import (
    SystemEventManager,
    SystemEventType,
)
from ...resource import FunctionTool, ToolParameter
from ..actions.agent_action import AgentStart
from ..actions.knowledge_action import KnowledgeSearch
from ..actions.sql_action import SqlAction
from ..actions.tool_action import ToolAction
from ...core.action.blank_action import BlankAction

# 导入 read_file 工具使其注册到 system_tool_dict
from ...core.tools.read_file_tool import read_file  # noqa: F401

# 导入 PromptAssembler（通用 Prompt 组装模块）
from ...shared.prompt_assembly import (
    PromptAssembler,
    PromptAssemblyConfig,
    create_prompt_assembler,
)

logger = logging.getLogger(__name__)


def separator_join_system_blocks(blocks: Any, separator: str = "\n\n") -> str:
    """将 SystemBlock 列表按确定序合并为 str(S10 降级用)。

    与现 PromptAssembler 的 section_separator 拼接语义对齐,保向前兼容。
    真实 cache_control 由 provider 层 S12 直接消费 FrozenBundle(SystemBlock 列表)。
    """
    return separator.join(b.text for b in blocks if getattr(b, "text", ""))


def _tool_from_entry(entry: Any) -> Any:
    """从 TOOLS 槽条目取工具句柄(S15):ToolEntry 取 .tool;Contribution 取 .content。

    统一 builtin(ToolEntry,executor_id=agent:builtin)与资源工具(Contribution)
    的形态差异,供 function_calling_params 转 schema。

    防御:若取出的句柄本身又是一个 ToolEntry(嵌套包装,如某些装配路径把
    ToolEntry 直接当作工具句柄),递归解包到实际工具句柄,避免 _tool_to_function
    遇到既无 to_openai_tool 也无 args 的 ToolEntry 时抛 AttributeError。
    """
    tool = getattr(entry, "tool", None)
    if tool is None:
        tool = getattr(entry, "content", None)
    while (
        tool is not None
        and hasattr(tool, "tool_name")
        and hasattr(tool, "tool")
        and not hasattr(tool, "to_openai_tool")
    ):
        tool = tool.tool
    return tool


def _get_sandbox_system_info(sandbox_client: SandboxBase) -> str:
    """Get system info description based on sandbox provider type."""
    provider = getattr(sandbox_client, "provider", lambda: "unknown")()

    if provider == "local":
        import platform
        import os

        system = platform.system()
        if system == "Darwin":
            return f"macOS ({platform.processor()}), 本地沙箱环境，路径映射到项目目录"
        elif system == "Linux":
            return f"Linux ({platform.processor()}), 本地沙箱环境，路径映射到项目目录"
        elif system == "Windows":
            return f"Windows, 本地沙箱环境，路径映射到项目目录"
        else:
            return f"{system}, 本地沙箱环境，路径映射到项目目录"
    else:
        return "Ubuntu 24.04 linux/amd64（已联网），用户：ubuntu（拥有免密 sudo 权限）"


async def _build_project_context(instance: Any) -> str:
    """构建工程目录生态上下文（项目记忆 + 项目技能），供 system 身份层注入。

    数据源：``instance.ext_config.project_ecosystem``（agent 编辑里配置的
    project_dir + 兼容类型）。探测缓存于 ``ProjectEcosystemLoader``。
    """
    try:
        ext_config = getattr(instance, "ext_config", None) or {}
        # app.ext_config.project_ecosystem = {project_dir, type}
        eco_cfg = ext_config.get("project_ecosystem") or {}
        project_dir = (eco_cfg.get("project_dir") or "").strip()
        if not project_dir or not os.path.isdir(project_dir):
            return ""
        eco_type = (eco_cfg.get("type") or ECOSYSTEM_AUTO).strip() or ECOSYSTEM_AUTO
        loaded = await asyncio.to_thread(
            ProjectEcosystemLoader.load, project_dir, eco_type
        )
        if not loaded or not loaded.has_content:
            return ""
        return await asyncio.to_thread(_render_project_context, loaded)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[project-ecosystem] build project_context failed: {e}")
        return ""


def _render_project_context(eco: ProjectEcosystem) -> str:
    """把探测结果渲染为 system 注入块。"""
    lines: List[str] = [
        "## 项目生态上下文（Claude Code / Cursor 兼容）",
        f"项目目录：`{eco.project_dir}`（生态类型：{eco.ecosystem_type}）",
        "",
        "以下内容来自项目目录中的 CLAUDE.md / AGENTS.md 与 .claude / .cursor 配置，"
        "是对项目的工作约定与技能指引，执行任务时必须遵循：",
    ]
    memory_text = eco.render_memory()
    if memory_text:
        lines.append("")
        lines.append("### 项目记忆（CLAUDE.md / AGENTS.md）")
        lines.append(memory_text)

    if eco.skills:
        lines.append("")
        lines.append("### 项目技能（来自 .claude / .cursor 的 SKILL.md）")
        lines.append(
            "开始任务前优先查看：使用 `Skill` 工具读取对应 `<path>` 的 SKILL.md 内容，"
            "按其指导执行；技能文件与项目代码同目录，可自由读取。"
        )
        for sk in eco.skills:
            lines.append(
                f"- <skill><name>{sk.name}</name>"
                f"<description>{sk.description or '--'}</description>"
                f"<path>{sk.path}</path><origin>{sk.origin}</origin></skill>"
            )

    if eco.rules:
        lines.append("")
        lines.append("### 项目规则（.claude/rules / .cursor/rules）")
        for rule in eco.rules[:10]:
            globs = ",".join(rule.globs) if rule.globs else "*"
            head = rule.content.strip().splitlines()[0][:80] if rule.content.strip() else ""
            lines.append(
                f"- <rule><path>{rule.path}</path><globs>{globs}</globs>"
                f"<summary>{head}</summary></rule>"
            )

    if eco.commands:
        lines.append("")
        lines.append("### 项目命令（.claude/commands 斜杠命令）")
        lines.append(
            "这些是项目预定义的 `/命令`，任务相关时用 `view` 读取 `<path>` 的提示词内容并按其执行："
        )
        for cmd in eco.commands:
            lines.append(
                f"- <command><name>/{cmd.name}</name>"
                f"<description>{cmd.description or '--'}</description>"
                f"<path>{cmd.path}</path></command>"
            )

    if eco.subagents:
        lines.append("")
        lines.append("### 项目子 Agent（.claude/agents 定义）")
        lines.append(
            "这些是项目声明的子 Agent 角色；任务相关时读取 `<path>` 定义，"
            "把其系统提示作为委托子 Agent 的执行指令（或用 SubAgent 工具按其角色分工）："
        )
        for sa in eco.subagents:
            lines.append(
                f"- <subagent><name>{sa.name}</name>"
                f"<description>{sa.description or '--'}</description>"
                f"<path>{sa.path}</path>"
                f"<tools>{sa.tools or '--'}</tools></subagent>"
            )

    if eco.mcp_servers:
        lines.append("")
        lines.append("### 项目 MCP 服务器（.mcp.json / settings.json mcpServers）")
        for mcp in eco.mcp_servers:
            endpoint = (
                mcp.url
                if mcp.transport == "http"
                else f"{mcp.command} {' '.join(mcp.args)}"
            )
            lines.append(
                f"- <mcp><name>{mcp.name}</name><transport>{mcp.transport}</transport>"
                f"<endpoint>{endpoint}</endpoint><source>{mcp.source}</source></mcp>"
            )

    if eco.env:
        lines.append("")
        lines.append("### 项目环境变量（.claude/settings.json env）")
        lines.append(
            "项目声明了以下环境变量（真实值不注入，按需向用户确认或读取 `.env` 等）："
        )
        for item in eco.env:
            value = f"={item.value}" if item.value else ""
            lines.append(f"- <env><key>{item.key}</key>{value}</env>")

    return "\n".join(lines)


class ReActMasterAgent(ConversableAgent, Team):
    """
    ReActMaster Agent - 最佳实践的 ReAct 范式 Agent

    这是基于 ReAct (Reasoning + Acting) 范式的智能 Agent 实现，具备以下特性：

    1. **末日循环检测 (Doom Loop Detection)**
       - 监控工具调用模式
       - 检测连续重复调用
       - 请求用户确认防止无限循环

    2. **上下文压缩 (Session Compaction)**
       - 自动检测上下文溢出
       - 使用 LLM 生成对话摘要
       - 保留关键信息，减少 Token 消耗

    3. **工具输出截断 (Tool Output Truncation)**
       - 限制大型输出（默认 2000 行 / 50KB）
       - 保存完整输出到临时文件
       - 提供智能提示指导后续处理

    4. **历史记录修剪 (History Pruning)**
       - 定期清理旧的工具输出
       - 保留关键消息
       - 管理上下文窗口使用
    """

    # 基础配置
    max_retry_count: int = 300
    run_mode: AgentRunMode = AgentRunMode.LOOP
    # 标准 Team Agent：支持 hire 子 Agent（.agents），子 Agent 以团队成员形式派发
    is_team: bool = True

    profile: ProfileConfig = Field(
        default_factory=lambda: ProfileConfig(
            name="BAIZE",
            role="BAIZE",
            goal="白泽，一个遵循最佳ReAct推理范式实践的Agent，通过系统化推理和工具使用高效解决复杂任务。",
            system_prompt_template=None,
            user_prompt_template=None,
            write_memory_template=REACT_MASTER_FC_WRITE_MEMORY_TEMPLATE_CN,
            # 别名配置：用于历史数据兼容
            aliases=["ReActMasterV2", "ReActMaster"],
        )
    )

    agent_parser: FunctionCallOutputParser = Field(
        default_factory=lambda: FunctionCallOutputParser(extract_scratch_pad=False)
    )
    function_calling: bool = True

    # 组件配置
    enable_doom_loop_detection: bool = True
    doom_loop_threshold: int = 3
    enable_session_compaction: bool = True
    context_window: int = 128000
    compaction_threshold_ratio: float = 0.8
    enable_output_truncation: bool = True
    enable_history_pruning: bool = True
    prune_protect_tokens: int = 4000

    # Message List 历史模式（原生格式 vs 文本注入）
    use_message_list_history: bool = True
    message_list_history_max_tokens: int = 30000

    # 新功能配置 -> WorkLog、Phase、ReportGenerator 集成配置
    enable_work_log: bool = True
    enable_phase_management: bool = True
    enable_auto_report: bool = True

    # WorkLog 配置
    work_log_context_window: int = 128000
    work_log_compression_ratio: float = 0.7
    work_log_large_result_threshold: int = 10 * 1024  # 10KB

    # Phase 配置
    phase_auto_detection: bool = True
    phase_enable_prompts: bool = True

    # Report 配置
    report_auto_generate: bool = False  # 默认不自动生成，可在任务结束时手动调用
    report_default_type: str = "detailed"
    report_default_format: str = "markdown"

    # Kanban 配置 (从 PDCAAgent 合并)
    enable_kanban: bool = False  # 启用 Kanban 任务规划模式
    kanban_exploration_limit: int = 2  # 探索阶段最大轮次
    kanban_auto_stage_transition: bool = True  # 自动阶段转换

    # 内部状态
    _ctx: ContextHelper[dict] = PrivateAttr(default_factory=lambda: ContextHelper(dict))
    _doom_loop_detector: Optional[DoomLoopDetector] = PrivateAttr(default=None)
    # _session_compaction removed - replaced by UnifiedCompactionPipeline
    # _history_pruner removed - replaced by UnifiedCompactionPipeline
    _truncator: Optional[Truncator] = PrivateAttr(default=None)  # Kept as fallback
    _agent_file_system: Optional[AgentFileSystem] = PrivateAttr(default=None)
    _tool_call_count: int = PrivateAttr(default=0)
    _compaction_count: int = PrivateAttr(default=0)
    _prune_count: int = PrivateAttr(default=0)

    # 工具失败追踪：记录每个工具的连续失败次数
    _tool_failure_counts: Dict[str, int] = PrivateAttr(default_factory=lambda: {})
    _max_tool_failure_count: int = PrivateAttr(default=5)  # 同一工具最大失败次数（前3次提醒，5次终止）
    # PR 7: ToolFailureTracker 接入 — 在 V1 内联计数基础上加 cooldown + record_success
    # _tool_failure_counts 保留作为 snapshot 向后兼容字段，由 tracker 反映
    _failure_tracker: Optional[Any] = PrivateAttr(default=None)

    # Kanban 内部状态
    _kanban_manager: Optional[KanbanManager] = PrivateAttr(default=None)
    _kanban_initialized: bool = PrivateAttr(default=False)

    # PromptAssembler 状态（通用 Prompt 组装器）
    _prompt_assembler: Optional[PromptAssembler] = PrivateAttr(default=None)
    # ResourceFacade 状态（RFC-005 协议层快照门面,S10 接入）
    _resource_facade: Optional[Any] = PrivateAttr(default=None)
    # 最近一次 assemble 产出的快照(供 function_calling_params 取 tools 等,S10)
    _last_snapshot: Optional[Any] = PrivateAttr(default=None)
    # RFC-006 Stage 3:工具派发器(按 ToolEntry.executor_id 路由 Route B → Capability.execute)
    _tool_dispatcher: Optional[Any] = PrivateAttr(default=None)

    # AsyncTaskManager 异步任务管理器（在 preload_resource 中按需初始化）
    _async_task_manager: Optional[Any] = PrivateAttr(default=None)

    # SystemEventManager 系统事件管理器（用于 VIS 渲染）
    _system_event_manager: Optional[SystemEventManager] = PrivateAttr(default=None)

    # ContextEngine 统一上下文管理引擎（取代历史 7 套机制）
    _context_engine: Optional[Any] = PrivateAttr(default=None)
    _context_engine_initialized: bool = PrivateAttr(default=False)
    # 历史 HistoryMessageBuilder 已退役；保留占位以兼容旧的 fallback 分支判断
    _history_message_builder: Optional[Any] = PrivateAttr(default=None)
    _history_builder_initialized: bool = PrivateAttr(default=False)
    _last_budget_event_data: Optional[Dict] = PrivateAttr(default=None)
    _budget_event_min_change_ratio: float = PrivateAttr(default=0.05)

    available_system_tools: Dict[str, FunctionTool] = Field(
        default_factory=dict, description="available system tools"
    )
    enable_function_call: bool = True

    def __init__(self, **kwargs):
        """Initialize ReActMaster Agent."""
        Team.__init__(self, **kwargs)
        super().__init__(**kwargs)
        self._init_actions([AgentStart, KnowledgeSearch, SqlAction, ToolAction])
        self._initialize_components()

        # 初始化交互能力
        self._interaction_extension = None

        # 背景异步任务完成通知是否在本轮 think 中下发（供 act() 判断是否强制续跑）
        self._bg_notif_delivered = False
        # 异步 resume 轮次强制续跑计数器及上限（避免 LLM 反复返回占位文本导致死循环）
        self._async_resume_force_count = 0
        self._async_resume_force_limit = 2
        # 输出超长截断(finish_reason=length)强制续跑计数器及上限（避免死循环）
        self._length_force_count = 0
        self._length_force_limit = 2
        # 异步 resume 是否在"当前用户轮次"内持续生效（跨 LLM 迭代保持，换新用户消息时重置）
        self._async_resume_active = False
        self._async_resume_received_id = None
        # 输出截断续跑计数按用户消息维度的重置标记
        self._length_received_id = None


    async def preload_resource(self) -> None:
        """Preload resources and inject system tools.

        工具注入现在通过统一工具框架进行：
        1. base_agent.system_tool_injection() 从 tool_manager 获取绑定工具
        2. 工具绑定配置来自编辑页面保存的 resource_tool
        3. 无配置时使用默认工具
        """
        await super().preload_resource()
        await self.system_tool_injection()
        await self.sandbox_tool_injection()

        # 初始化 SystemEventManager
        await self._ensure_system_event_manager()

        # NOTE: read_file, todowrite, todoread 等工具现在通过统一工具框架注入
        # 不再在此处直接注入，见 base_agent.system_tool_injection()

        # NOTE: 历史回顾工具（read_history_chapter, search_history 等）不在此处注入。
        # 它们只在首次 compaction 完成后才动态注入，见 _inject_history_tools_if_needed()。

        # 注入异步任务工具（当检测到多 Agent 场景时）
        await self._inject_async_task_tools()

        # 注入 todo 工具（目标任务管理核心机制，始终注入，不依赖 resource_tool 配置）
        await self._inject_todo_tools()

    async def _inject_todo_tools(self) -> None:
        """注入 todo 工具到 available_system_tools。

        todowrite/todoread 是 BAIZE 目标任务 TODO 闭环的核心机制工具
        （LLM 自维护进度 + 每轮 reminder 注入），不依赖 agent 的 resource_tool
        绑定配置，始终注入（类似 ask_user 的核心地位）。
        """
        try:
            from ...tools.registry import tool_registry

            for tool_name in ("todowrite", "todoread"):
                if tool_name not in self.available_system_tools:
                    tool = tool_registry.get(tool_name)
                    if tool:
                        self.available_system_tools[tool_name] = tool
        except Exception as e:
            logger.warning(f"[TodoTools] inject failed: {e}")

    async def _inject_async_task_tools(self) -> None:
        """
        注入异步任务工具到 available_system_tools。

        条件：存在 AppResource（表示有可委派的子 Agent）或已 hire 子 Agent。
        创建 AsyncTaskManager 并注册 4 个 FunctionTool 包装。

        注意：不能在 self.agents 为空时直接放弃注入——agent_chat 在 build()
        （触发本方法）之后才 hire 子 Agent，此时提前返回会让未绑定 delegate 的
        内置 SpawnAgentTaskTool 被分发，报 'NoneType' object has no attribute
        'delegate'。委派适配器在调用时才解析 self.agents，注入不依赖 hire 时机。
        """
        try:
            # 检查 capability_pack 是否有 AppCapability
            has_app_resource = False
            if getattr(self, "_has_capability", None) and self._has_capability("app"):
                has_app_resource = True

            if not has_app_resource and not getattr(self, "agents", None):
                return

            from ...util.async_task_manager import AsyncTaskManager, AsyncTaskSpec

            # 创建一个轻量级 SubagentManager 适配器，包装 core v1 的 agent delegation
            class CoreV1SubagentAdapter:
                """适配 Core V1 的 agent delegation 为 SubagentManager.delegate 接口"""

                def __init__(self, master_agent):
                    self._master = master_agent

                async def delegate(
                    self,
                    subagent_name: str,
                    task: str,
                    parent_session_id: str = "",
                    context: Optional[Dict] = None,
                    sync: bool = True,
                    **kwargs,
                ):
                    """通过 Core V1 的 send/receive 机制委派任务"""
                    from gyra.agent import AgentMessage

                    # 找到目标子 Agent
                    recipient = next(
                        (
                            agent
                            for agent in self._master.agents
                            if agent.name == subagent_name
                            or getattr(agent, "agent_context", None)
                            and getattr(agent.agent_context, "agent_app_code", None)
                            == subagent_name
                        ),
                        None,
                    )

                    if not recipient:
                        # 团队成员未命中 → 回退按 app_code/app_name 解析 AppResource
                        # （与 SubAgent 工具的 _resolve_app_code 同一语义），
                        # 命中则以独立子会话跑目标 app（覆盖多媒体生成助手等 app）
                        return await self._delegate_via_app(subagent_name, task)

                    # 构建消息
                    message = AgentMessage.init_new(
                        content=task,
                        context=context or {},
                        show_message=False,
                        observation=task,
                        current_goal=task,
                    )

                    try:
                        answer = await self._master.send(
                            message=message,
                            recipient=recipient,
                            request_reply=True,
                            request_sender_reply=False,
                        )

                        return self._result_from_answer(answer)
                    except Exception as e:
                        result = type(
                            "SubagentResult",
                            (),
                            {
                                "success": False,
                                "output": None,
                                "error": str(e),
                                "artifacts": {},
                            },
                        )()
                        return result

                @staticmethod
                def _fail_result(error: str):
                    return type(
                        "SubagentResult",
                        (),
                        {
                            "success": False,
                            "output": None,
                            "error": error,
                            "artifacts": {},
                        },
                    )()

                @staticmethod
                def _result_from_answer(answer: Any):
                    """从子 Agent 回复构造结果,并识别目标失败。

                    优先读结构化标记 ``answer.success``(MultimediaAgent 经
                    correctness_check 在生成失败时置 False,见 multimedia/agent.py);
                    该字段缺失(非 AgentMessage 等旧路径)才回退"多媒体生成失败"
                    content 前缀匹配。识别为失败时 success=False,使
                    AsyncTaskManager._run_task 把任务标 FAILED 而非 completed--
                    目标失败(如视频 403)不应算完成,否则前端误显示"完成"且
                    result_preview 带失败文本。
                    """
                    content = getattr(answer, "content", None) or ""
                    structured = getattr(answer, "success", None)
                    if structured is not None:
                        is_failure = not structured
                    else:
                        is_failure = isinstance(
                            content, str
                        ) and content.startswith("多媒体生成失败")
                    return type(
                        "SubagentResult",
                        (),
                        {
                            "success": not is_failure,
                            "output": None if is_failure else content,
                            "error": content if is_failure else None,
                            "artifacts": {},
                        },
                    )()

                def _resolve_app_code(self, subagent_name: str) -> str:
                    """在 master 的 app 资源中按 app_code/app_name 解析目标子 Agent。

                    与 agent_action._resolve_app_code 同一语义：从 capability_pack
                    的 AppCapability 解析（v1 resource_map 兜底已删）。
                    """
                    master = self._master
                    pack = getattr(master, "capability_pack", None)
                    caps = pack.get_all("app") if pack is not None else []
                    for cap in caps:
                        code = getattr(cap, "app_code", "") or ""
                        name = getattr(cap, "app_name", "") or ""
                        if subagent_name in (code, name):
                            return code
                    return ""

                async def _delegate_via_app(self, subagent_name: str, task: str):
                    """经 AppCapability 以独立子会话委派到目标 app（后台执行）。

                    与 SubAgent async 分支同一执行形态，但注册/恢复由
                    spawn_agent_task 的 atask 体系负责，不重复登记 SubagentCoordinator。
                    """
                    app_code = self._resolve_app_code(subagent_name)
                    if not app_code:
                        available = []
                        pack = getattr(self._master, "capability_pack", None)
                        caps = pack.get_all("app") if pack is not None else []
                        for cap in caps:
                            n = (
                                getattr(cap, "app_name", None)
                                or getattr(cap, "app_code", None)
                            )
                            if n:
                                available.append(n)
                        hint = f"可用: {', '.join(available)}" if available else "无可用 app 资源"
                        return self._fail_result(
                            f"子 Agent '{subagent_name}' 不存在（{hint}）"
                        )
                    try:
                        from gyra_serve.agent.capabilities.app import AppCapability
                    except ImportError:
                        return self._fail_result(
                            f"子 Agent '{subagent_name}' 是 app 资源，但 gyra_serve 不可用"
                        )
                    try:
                        import uuid

                        master_ctx = getattr(self._master, "agent_context", None)
                        parent_depth = (
                            (master_ctx.extra or {}).get("subagent_depth", 0)
                            if master_ctx
                            else 0
                        )
                        app_cap = AppCapability(app_name=app_code, app_code=app_code)
                        answer = await app_cap.start_app(
                            user_input=task,
                            sender=self._master,
                            conv_uid=str(uuid.uuid4()),
                            parent_depth=parent_depth or 0,
                        )
                        return self._result_from_answer(answer)
                    except Exception as e:
                        return self._fail_result(str(e))

            # 创建适配器，并把 subagent 任务提交到进程级统一单例（与 media 任务共用）。
            # spec.delegate 打包已绑定 adapter 的委派协程，使单例无需 subagent_manager
            # 也能跑 subagent 任务，实现两类任务统一查看 / 统一持久化 / 统一恢复。
            adapter = CoreV1SubagentAdapter(self)
            session_id = (
                getattr(self.agent_context, "conv_id", "") if self.agent_context else ""
            )

            self._async_task_manager = AsyncTaskManager.media_instance()

            # 把统一单例纳入 AsyncTaskCoordinator 轮询，使 spawn_agent_task 提交的
            # 后台子 Agent 任务也能被 #2(WAITING) / #3(resume) / #4(恢复) 覆盖。
            try:
                from gyra_serve.agent.async_task_coordinator import (
                    get_async_task_coordinator,
                )
                coord = get_async_task_coordinator()
                if coord is not None:
                    coord.add_manager(self._async_task_manager)
            except Exception as coord_err:  # noqa: BLE001 - serve 不可用时静默跳过
                logger.warning(
                    f"[ReActMasterAgent] register subagent manager to coordinator failed: {coord_err}"
                )

            # 获取可用子 Agent 名称列表
            agent_names = []
            for agent in self.agents or []:
                name = agent.name or getattr(
                    getattr(agent, "agent_context", None), "agent_app_code", None
                )
                if name:
                    agent_names.append(name)
            if not agent_names:
                # build 时子 Agent 尚未 hire（agent_chat 在 build 后 hire），
                # 从 capability_pack 的 AppCapability 兜底取可委派子 Agent 名称，供工具描述展示
                pack = getattr(self, "capability_pack", None)
                caps = pack.get_all("app") if pack is not None else []
                for cap in caps:
                    name = (
                        getattr(cap, "app_name", None)
                        or getattr(cap, "app_code", None)
                    )
                    if name:
                        agent_names.append(name)

            # 创建 FunctionTool 包装
            atm = self._async_task_manager

            async def _spawn_agent_task(
                agent_name: str,
                task: str,
                timeout: int = 300,
                depend_on: str = "",
                wait_for_result: bool = True,
            ) -> "ToolResult":
                from gyra.agent.tools import ToolResult

                # 防重复提交：同会话已有同 agent 同内容的在途任务时直接复用，
                # 不新建（图片/视频生成按次计费，重复提交 = 重复扣费）
                in_flight = atm.find_in_flight(
                    conv_id=session_id,
                    agent_name=agent_name,
                    task_description=task,
                )
                if in_flight is not None:
                    existing_id = in_flight.spec.task_id
                    return ToolResult.ok(
                        output=(
                            f"相同任务已在后台执行中，已复用、未重复提交。\n"
                            f"- Task ID: {existing_id}\n"
                            f"- Agent: {agent_name}\n"
                            f"- 状态: {in_flight.status.value}\n\n"
                            f"请勿再次提交相同任务。"
                            + (
                                "本轮将结束等待，任务完成后会自动恢复继续。"
                                if wait_for_result
                                else "结果完成后会经异步通知注入上下文。"
                            )
                        ),
                        tool_name="spawn_agent_task",
                        metadata={
                            "task_id": existing_id,
                            "agent_name": agent_name,
                            "reused": True,
                            "wait_async": bool(wait_for_result),
                            "async_task": {
                                "task_id": existing_id,
                                "kind": "subagent",
                                "model": agent_name,
                                "conv_id": session_id,
                            },
                        },
                    )

                spec = AsyncTaskSpec(
                    agent_name=agent_name,
                    task_description=task,
                    timeout=timeout,
                    conv_id=session_id,
                    depend_on=[d.strip() for d in depend_on.split(",") if d.strip()]
                    if depend_on
                    else [],
                    # 统一单例下 subagent 任务经 delegate 委派（已绑定 adapter）
                    delegate=lambda: adapter.delegate(
                        subagent_name=agent_name,
                        task=task,
                        parent_session_id=session_id,
                        context={},
                        sync=True,
                    ),
                )
                task_id = await atm.spawn(spec)
                deps_info = f"\n依赖: {spec.depend_on}" if spec.depend_on else ""
                wait_note = (
                    "\n本轮将在此结束并等待任务完成，完成后会自动恢复继续（无需轮询）。"
                    if wait_for_result
                    else "\n你可以继续其他工作，结果完成后会经异步通知注入上下文。"
                )
                return ToolResult.ok(
                    output=(
                        f"任务已提交到后台执行。\n"
                        f"- Task ID: {task_id}\n"
                        f"- Agent: {agent_name}\n"
                        f"- 描述: {task[:100]}\n"
                        f"- 超时: {timeout}s{deps_info}\n\n"
                        f"你可以继续其他工作，稍后用 check_tasks 查看状态或 wait_tasks 获取结果。"
                        f"{wait_note}"
                    ),
                    tool_name="spawn_agent_task",
                    metadata={
                        "task_id": task_id,
                        "agent_name": agent_name,
                        "wait_async": bool(wait_for_result),
                        "async_task": {
                            "task_id": task_id,
                            "kind": "subagent",
                            "model": agent_name,
                            "conv_id": session_id,
                        },
                    },
                )

            async def _check_tasks(task_ids: str = "") -> str:
                ids = (
                    [t.strip() for t in task_ids.split(",") if t.strip()]
                    if task_ids
                    else None
                )
                output = atm.format_status_table(ids)
                if "未找到" in output:
                    output += (
                        "\n\n提示：标记「未找到」的 ID 请核对拼写；SubAgent 异步返回的 "
                        "sub_conv_id 与 spawn_agent_task 返回的 atask_* 均可直接查询。"
                        "任务查询不到不代表丢失，请勿因此重复提交生成任务。"
                    )
                return output

            async def _wait_tasks(task_ids: str = "", timeout: int = 60) -> str:
                ids = (
                    [t.strip() for t in task_ids.split(",") if t.strip()]
                    if task_ids
                    else []
                )
                if ids:
                    # 对未知 task_id 显式报错，避免误导性的"等待超时"导致重复提交
                    known = set(atm.known_task_ids(ids))
                    unknown = [t for t in ids if t not in known]
                    if unknown and not known:
                        return (
                            f"错误：任务 ID 不存在: {unknown}。请核对 ID（SubAgent 异步返回的 "
                            f"sub_conv_id、spawn_agent_task 返回的 atask_* 均可直接查询）；"
                            f"不要因查询不到就重复提交生成任务。"
                        )
                    if unknown:
                        ids = [t for t in ids if t in known]
                    results = await atm.wait_all(ids, timeout=timeout)
                else:
                    results = await atm.wait_any(timeout=timeout)
                if not results:
                    return "等待超时，暂无任务完成。你可以继续其他工作后再检查。"
                return atm.format_results(results)

            async def _cancel_task(task_id: str) -> str:
                success = await atm.cancel(task_id)
                return (
                    f"任务 {task_id} 已取消。"
                    if success
                    else f"无法取消任务 {task_id}（任务可能已完成或不存在）。"
                )

            # 注册为 FunctionTool
            spawn_tool = FunctionTool(
                name="spawn_agent_task",
                func=_spawn_agent_task,
                description=(
                    "启动一个后台 Agent 异步任务。默认 wait_for_result=true（阻塞等待）："
                    "提交后本轮立即结束，任务完成后自动恢复继续，无需轮询；仅当结果与后续"
                    "工作完全无关时传 wait_for_result=false。相同内容的任务会被去重复用，"
                    "不会重复执行（图片/视频生成按次计费，切勿重复提交）。"
                    f"可用 Agent: {', '.join(agent_names)}"
                ),
                args={
                    "agent_name": ToolParameter(
                        name="agent_name",
                        type="string",
                        required=True,
                        description=f"目标子 Agent 名称。可选: {', '.join(agent_names)}",
                    ),
                    "task": ToolParameter(
                        name="task",
                        type="string",
                        required=True,
                        description="任务描述，请提供清晰具体的说明。",
                    ),
                    "timeout": ToolParameter(
                        name="timeout",
                        type="integer",
                        required=False,
                        description="超时秒数（默认300）",
                        default=300,
                    ),
                    "depend_on": ToolParameter(
                        name="depend_on",
                        type="string",
                        required=False,
                        description="依赖的 task_id 列表，逗号分隔（可选）。这些任务完成后才开始。",
                        default="",
                    ),
                    "wait_for_result": ToolParameter(
                        name="wait_for_result",
                        type="boolean",
                        required=False,
                        description=(
                            "是否需要等待任务结果（默认 true）。true=阻塞等待：提交后本轮结束，"
                            "完成后自动恢复；false=后台执行：继续其他工作，结果经异步通知注入。"
                        ),
                        default=True,
                    ),
                },
            )

            check_tool = FunctionTool(
                name="check_tasks",
                func=_check_tasks,
                description="查看后台任务的当前状态，不阻塞。",
                args={
                    "task_ids": ToolParameter(
                        name="task_ids",
                        type="string",
                        required=False,
                        description="要查询的 task_id 列表，逗号分隔。为空则查询全部。",
                        default="",
                    ),
                },
            )

            wait_tool = FunctionTool(
                name="wait_tasks",
                func=_wait_tasks,
                description="等待后台任务完成并获取结果。指定 task_ids 等待全部完成，为空则等待任意一个完成。",
                args={
                    "task_ids": ToolParameter(
                        name="task_ids",
                        type="string",
                        required=False,
                        description="等待的 task_id 列表，逗号分隔。为空则等待任意一个完成。",
                        default="",
                    ),
                    "timeout": ToolParameter(
                        name="timeout",
                        type="integer",
                        required=False,
                        description="最大等待秒数（默认60）",
                        default=60,
                    ),
                },
            )

            cancel_tool = FunctionTool(
                name="cancel_task",
                func=_cancel_task,
                description="取消一个正在执行或等待中的后台任务。",
                args={
                    "task_id": ToolParameter(
                        name="task_id",
                        type="string",
                        required=True,
                        description="要取消的任务 ID",
                    ),
                },
            )

            self.available_system_tools["spawn_agent_task"] = spawn_tool
            self.available_system_tools["check_tasks"] = check_tool
            self.available_system_tools["wait_tasks"] = wait_tool
            self.available_system_tools["cancel_task"] = cancel_tool

            logger.info(
                f"[ReActMasterAgent] 异步任务工具已注入，可用子 Agent: {agent_names}"
            )

        except ImportError as e:
            logger.debug(f"[ReActMasterAgent] 异步任务模块未找到: {e}")
        except Exception as e:
            logger.warning(f"[ReActMasterAgent] 注入异步任务工具失败: {e}")

    async def _collect_async_task_notifications(self) -> Optional[str]:
        """
        收集已完成的异步任务通知。

        在 thinking() 中调用，将后台完成的任务结果注入到 LLM 上下文。

        Returns:
            格式化的通知文本，没有通知则返回 None
        """
        if not self._async_task_manager:
            return None

        try:
            completed = self._async_task_manager.get_completed_results(consume=True)
            if not completed:
                return None

            notification = self._async_task_manager.format_notifications(completed)
            return notification if notification else None

        except Exception as e:
            logger.warning(f"[ReActMasterAgent] 收集异步任务通知失败: {e}")
            return None

    async def _collect_media_job_notifications(self) -> Optional[str]:
        """收集已完成的异步媒体生成任务通知 (generate_video 异步模式)。

        在 thinking() 中调用,将后台完成的媒体生成结果注入到 LLM 上下文。
        """
        try:
            from gyra.agent.util.async_task_manager import AsyncTaskManager

            mgr = AsyncTaskManager.media_instance()
            conv_id = (
                getattr(self.agent_context, "conv_id", "")
                if self.agent_context
                else ""
            )
            completed = mgr.get_completed_results(conv_id=conv_id, consume=True)
            if not completed:
                return None
            notification = mgr.format_notifications(completed)
            return notification if notification else None
        except Exception as e:
            logger.warning(f"[ReActMasterAgent] 收集媒体任务通知失败: {e}")
            return None

    async def _collect_background_notifications(self) -> Optional[str]:
        """合并收集异步子 Agent 任务 + 异步媒体生成任务的通知。"""
        parts = []
        for getter in (
            self._collect_async_task_notifications,
            self._collect_media_job_notifications,
        ):
            try:
                n = await getter()
            except Exception as e:
                logger.warning(
                    f"[ReActMasterAgent] collect background notifications failed: {e}"
                )
                n = None
            if n:
                parts.append(n)
        return "\n\n".join(parts) if parts else None

    async def _collect_supplemental_user_input(self, session_id: str) -> Optional[str]:
        """收集运行中用户提交的补充输入(来自 InteractionGateway 队列)。

        每轮 think 前调用,清空式消费队列,把所有待处理输入拼成文本返回。
        无补充输入返回 None。session_id 为 conv_session_id(前端 convUid)。
        """
        try:
            from gyra.agent.interaction.interaction_gateway import (
                get_interaction_gateway,
            )
            gateway = get_interaction_gateway()
            inputs = await gateway.get_pending_user_inputs(session_id, clear=True)
        except Exception as e:
            logger.warning(
                f"[ReActMasterAgent] collect supplemental user input failed: {e}"
            )
            return None
        if not inputs:
            return None
        lines = [f"- {item.content}" for item in inputs if getattr(item, "content", None)]
        if not lines:
            return None
        return "[用户补充输入]\n" + "\n".join(lines)

    async def function_calling_params(self):
        def _tool_to_function(tool) -> Dict:
            # 新框架 ToolBase: 使用 to_openai_tool() 方法
            if hasattr(tool, "to_openai_tool"):
                return tool.to_openai_tool()

            # 旧框架 BaseTool: 使用 args 属性
            properties = {}
            required_list = []
            for key, value in tool.args.items():
                properties[key] = {
                    "type": value.type,
                    "description": value.description,
                }
                if value.required:
                    required_list.append(key)
            parameters_dict = {
                "type": "object",
                "properties": properties,
                "required": required_list,
            }

            function = {}
            function["name"] = tool.name
            function["description"] = tool.description
            function["parameters"] = parameters_dict
            return {"type": "function", "function": function}

        functions = []

        snapshot = getattr(self, "_last_snapshot", None)
        if snapshot is not None and snapshot.all_tools():
            # S15: builtin + 资源工具统一从快照一处取(all_tools 兼容 ToolEntry/Contribution)
            for entry in snapshot.all_tools():
                tool_item = _tool_from_entry(entry)
                if tool_item is not None:
                    functions.append(_tool_to_function(tool_item))
            logger.info(
                f"function_calling_params: tools from snapshot.all_tools, "
                f"total={len(functions)} "
                f"(builtin={len(snapshot.builtin_tools)}, "
                f"sandbox={len(snapshot.sandbox_tools())}, "
                f"resource={len(snapshot.tools)})"
            )
            if snapshot.sandbox_tools():
                sb_names = [e.tool_name for e in snapshot.sandbox_tools()]
                logger.info(
                    f"function_calling_params: sandbox-delegated tools "
                    f"(capability_id=sandbox): {sb_names}"
                )
        else:
            # 回退路径(无快照):builtin 工具
            logger.info(
                f"function_calling_params(fallback): available_system_tools count="
                f"{len(self.available_system_tools)}"
            )
            for k, v in self.available_system_tools.items():
                functions.append(_tool_to_function(v))

        system_tool_count = len(self.available_system_tools)
        resource_tool_count = len(functions) - system_tool_count
        logger.info(
            f"function_calling_params: total={len(functions)} "
            f"(system={system_tool_count}, resource={resource_tool_count})"
        )

        if system_tool_count == 0 and resource_tool_count > 0:
            logger.warning(
                "function_calling_params: system tools are EMPTY! "
                "Only resource tools available. Check preload_resource() was called."
            )
        elif system_tool_count > 0 and resource_tool_count == 0:
            logger.warning(
                "function_calling_params: resource tools are EMPTY! "
                "Only system tools available. Check resource binding."
            )

        if functions:
            return {
                "tool_choice": "auto",
                "tools": functions,
                "parallel_tool_calls": True,
            }
        else:
            logger.warning("function_calling_params: No functions available!")
            return None

    def _initialize_components(self):
        """初始化核心组件"""
        # 1. 初始化 Doom Loop 检测器
        if self.enable_doom_loop_detection:
            self._doom_loop_detector = IntelligentDoomLoopDetector(
                threshold=self.doom_loop_threshold,
                permission_callback=self._ask_user_permission,
            )
            logger.info(
                f"DoomLoopDetector initialized with threshold={self.doom_loop_threshold}"
            )

        # SessionCompaction and HistoryPruner have been replaced by UnifiedCompactionPipeline.
        # Initialization removed in Phase 2 cleanup.

        # 4. 初始化 AgentFileSystem 和输出截断器
        if self.enable_output_truncation:
            # 创建截断器（AgentFileSystem 将在需要时异步初始化）
            self._truncator = Truncator(
                max_lines=self._truncator_max_lines
                if hasattr(self, "_truncator_max_lines")
                else TruncationConfig.DEFAULT_MAX_LINES,
                max_bytes=self._truncator_max_bytes
                if hasattr(self, "_truncator_max_bytes")
                else TruncationConfig.DEFAULT_MAX_BYTES,
            )
            self._agent_file_system = None
            logger.info(
                "Truncator initialized (AgentFileSystem will be initialized on demand)"
            )

        # 5. 初始化 WorkLog 管理器（延迟初始化）
        if self.enable_work_log:
            self._work_log_manager = None
            self._work_log_initialized = False
            logger.info("WorkLog enabled (will initialize on demand)")
        else:
            self._work_log_manager = None
            self._work_log_initialized = False

        # 6. 初始化阶段管理器
        if self.enable_phase_management:
            self._phase_manager = PhaseManager(
                auto_phase_detection=self.phase_auto_detection,
                enable_phase_prompts=self.phase_enable_prompts,
            )
            logger.info(
                f"PhaseManager initialized (auto_detection={self.phase_auto_detection})"
            )
        else:
            self._phase_manager = None

        # 7. 准备报告生成器（延迟初始化）
        if self.enable_auto_report:
            self._report_generator = None
            logger.info("ReportGenerator enabled (will initialize on demand)")
        else:
            self._report_generator = None

        # 8. 初始化 Kanban 管理器（延迟初始化）
        if self.enable_kanban:
            self._kanban_manager = None
            self._kanban_initialized = False
            logger.info(
                f"Kanban enabled (exploration_limit={self.kanban_exploration_limit})"
            )
        else:
            self._kanban_manager = None
            self._kanban_initialized = False

        # 9. 初始化交互能力
        self._interaction_extension = None
        logger.info("Interaction extension enabled (will initialize on demand)")

        # 10. 初始化统一压缩管道（延迟初始化，需要 conv_id）
        self._compaction_pipeline = None
        self._pipeline_initialized = False

    def _get_interaction_extension(self):
        """获取交互扩展（懒加载）"""
        if self._interaction_extension is None:
            from .interaction_extension import create_interaction_extension

            self._interaction_extension = create_interaction_extension(self)
        return self._interaction_extension

    def _get_prompt_assembler(self) -> PromptAssembler:
        """获取 Prompt 组装器（懒加载）- 使用 Agent 级别的模板目录"""
        if self._prompt_assembler is None:
            from pathlib import Path

            # 获取 Agent 级别的 prompts 目录
            agent_prompts_dir = Path(__file__).parent / "prompts"

            config = PromptAssemblyConfig(
                architecture="v1",
                language=getattr(self.profile, "language", "zh")
                if hasattr(self, "profile")
                else "zh",
            )
            self._prompt_assembler = PromptAssembler(config)

            # 设置 Agent 级别的模板目录
            self._prompt_assembler.registry.set_agent_prompts_dir(agent_prompts_dir)
            self._prompt_assembler.registry.initialize(agent_prompts_dir)

            logger.info(
                f"PromptAssembler initialized with agent prompts: {agent_prompts_dir}"
            )

        return self._prompt_assembler

    def _get_resource_facade(self) -> Any:
        """获取 ResourceFacade（懒加载,RFC-005 S10 接入)。

        产完整 system 快照(身份/记忆/资源/控制四层 Contribution)+ tools。
        RFC-006 Stage 2:注入共享 SandboxExecutor 到 executor_provider,打通
        capability requires=["sandbox"] 的执行投影接线。
        """
        if self._resource_facade is None:
            from gyra.agent.capabilities import ResourceFacade

            facade = ResourceFacade()
            # Stage 2:注入共享沙箱 executor(非 Capability;平台底座,多 capability 经
            # requires=["sandbox"] 引用)。无 sandbox_manager 时跳过(纯协议/测试场景)。
            if getattr(self, "sandbox_manager", None) is not None:
                from gyra.agent.capabilities.sandbox.executor import SandboxExecutor

                facade.executor_provider["sandbox"] = SandboxExecutor(self.sandbox_manager)
            self._resource_facade = facade
            # Stage 3:构造工具派发器(Route B → Capability.execute)。Route A(builtin)
            # 不经 dispatcher,仍在 ToolAction._execute_tool 主路径直调;故不设
            # builtin_executor 回调。仅非 BUILTIN executor_id 的工具走 dispatcher。
            from gyra.core.interface.resource.dispatcher import ToolDispatcher

            self._tool_dispatcher = ToolDispatcher(registry=facade.registry)
        return self._resource_facade

    def resolve_tool_entry(self, tool_name: str) -> Any:
        """S19: 按 tool_name 从 _last_snapshot 统一查工具句柄(执行面与声明面同源)。

        返回 ToolEntry/Contribution 的工具句柄(BaseTool);未找到返回 None。
        ToolAction.run 优先用此方法找句柄,消除"声明面(snapshot) vs 执行面
        (sandbox_tool_dict/system_tool_dict/unified/resource 多 dict)"两源不一致。
        init_params 副作用(沙箱 client 等)仍按工具类型在 ToolAction 内设置。
        """
        snap = getattr(self, "_last_snapshot", None)
        if snap is None:
            return None
        from gyra.core.interface.resource.dispatcher import ToolDispatcher

        idx = ToolDispatcher.build_index(snap.all_tools())
        entry = idx.get(tool_name)
        if entry is None:
            return None
        # ToolEntry 取 .tool;Contribution 取 .content
        return getattr(entry, "tool", None) or getattr(entry, "content", None)

    async def _build_sandbox_capability(self):
        """S14+S20:沙箱 Capability 输入投影。

        有沙箱时返回 (env_contribs, sandbox_tool_entries, non_sandbox_builtin):
        - env_contribs: 沙箱 env 信息 SYSTEM Contribution。
        - sandbox_tool_entries: 委托沙箱的文件/脚本类工具(Bash/Read/Write/Edit/
          deliver_file/download_file)归 capability_id=sandbox 的 ToolEntry。
        - non_sandbox_builtin: 其余 builtin 工具(spawn_agent/ask_user/Skill 等不借沙箱的),
          仍走 builtin。

        无沙箱时返回 ([], [], available_system_tools 全量)——文件/脚本是本地默认工具。

        capability_id 标归属(沙箱沙箱、非沙箱 builtin);executor_id 仍 builtin
        (工具执行体自处理沙箱/本地切换,选B 务实方案)。
        """
        no_sandbox = (not self.sandbox_manager) or (
            not getattr(self.sandbox_manager, "client", None)
        )
        all_tools = dict(self.available_system_tools)
        if no_sandbox:
            return [], [], all_tools
        try:
            from gyra.agent.capabilities.sandbox import SandboxResource

            work_dir = getattr(self.sandbox_manager, "work_dir", "/workspace") or "/workspace"
            res = SandboxResource(self.sandbox_manager.client, work_dir=work_dir)
            env_contribs = res.declare_env()
            sandbox_tool_entries = res.declare_tools(all_tools)
            # 沙箱委托类工具从 builtin 移出(由 sandbox_tool_entries 提供),避免重复声明
            sandbox_names = {e.tool_name for e in sandbox_tool_entries}
            non_sandbox_builtin = {
                k: v for k, v in all_tools.items() if k not in sandbox_names
            }
            return env_contribs, sandbox_tool_entries, non_sandbox_builtin
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[S14/S20] sandbox capability failed: {e}")
            return [], [], all_tools

    @property
    def interaction(self):
        """交互能力访问入口"""
        return self._get_interaction_extension()

    async def _ask_user_permission(self, message: str, context: Dict = None) -> bool:
        """
        请求用户权限回调

        Args:
            message: 确认消息
            context: 上下文信息

        Returns:
            bool: 是否允许继续
        """
        try:
            extension = self._get_interaction_extension()

            tool_name = context.get("tool_name", "unknown") if context else "unknown"
            tool_args = context.get("tool_args", {}) if context else {}

            authorized = await extension.request_tool_authorization(
                tool_name=tool_name,
                tool_args=tool_args,
                reason=message,
            )

            if authorized:
                logger.info(f"User authorized: {tool_name}")
            else:
                logger.warning(f"User denied: {tool_name}")

            return authorized

        except Exception as e:
            logger.warning(f"Interaction failed, falling back to default: {e}")

            if self.memory and self.memory.gpts_memory and self.not_null_agent_context:
                await self.memory.gpts_memory.push_message(
                    conv_id=self.not_null_agent_context.conv_id,
                    stream_msg={
                        "type": "permission_request",
                        "message": message,
                        "context": context or {},
                    },
                )

            return False

    async def ask_user(
        self,
        question: str,
        title: str = "需要您的输入",
        default: str = None,
        options: List[str] = None,
    ) -> str:
        """
        主动向用户提问

        Args:
            question: 问题内容
            title: 标题
            default: 默认值
            options: 选项列表

        Returns:
            str: 用户回答
        """
        extension = self._get_interaction_extension()
        return await extension.ask_user(
            question=question,
            title=title,
            default=default,
            options=options,
        )

    async def choose_plan(
        self, plans: List[Dict[str, Any]], title: str = "请选择执行方案"
    ) -> str:
        """
        让用户选择执行方案

        Args:
            plans: 方案列表
            title: 标题

        Returns:
            str: 选择的方案ID
        """
        extension = self._get_interaction_extension()
        return await extension.choose_plan(plans=plans, title=title)

    async def confirm_action(self, message: str, title: str = "确认操作") -> bool:
        """
        请求用户确认

        Args:
            message: 确认消息
            title: 标题

        Returns:
            bool: 是否确认
        """
        extension = self._get_interaction_extension()
        return await extension.confirm_action(message=message, title=title)

    async def _ensure_agent_file_system(self) -> Optional[Any]:
        """
        确保AgentFileSystem已初始化（懒加载）

        Returns:
            AgentFileSystem实例或None
        """
        if self._agent_file_system is not None:
            return self._agent_file_system

        if not self.not_null_agent_context:
            return None

        try:
            conv_id = self.not_null_agent_context.conv_id or "default"
            session_id = self.not_null_agent_context.conv_session_id or conv_id

            # 尝试获取 FileStorageClient
            file_storage_client = None
            try:
                from gyra.core.interface.file import FileStorageClient
                from gyra._private.config import Config

                CFG = Config()
                system_app = CFG.SYSTEM_APP
                if system_app:
                    file_storage_client = FileStorageClient.get_instance(system_app)
            except Exception:
                pass  # FileStorageClient 不可用

            # 获取 sandbox 客户端
            sandbox = None
            if self.sandbox_manager and self.sandbox_manager.client:
                sandbox = self.sandbox_manager.client

            # 创建AgentFileSystem实例（V3 集成在默认版本中）
            self._agent_file_system = AgentFileSystem(
                conv_id=conv_id,
                session_id=session_id,
                metadata_storage=self.memory.gpts_memory if self.memory else None,
                file_storage_client=file_storage_client,
                sandbox=sandbox,
            )

            # 同步工作区（恢复文件）
            await self._agent_file_system.sync_workspace()

            # 注入 AgentFileSystem 到 sandbox 客户端
            if sandbox:
                sandbox.agent_file_system = self._agent_file_system
                logger.info("Injected AgentFileSystem into Sandbox client")

            # 更新截断器的AFS引用
            if self._truncator:
                self._truncator.agent_file_system = self._agent_file_system

            logger.info(
                f"AgentFileSystem initialized with conv_id={conv_id}, "
                f"session_id={session_id}, storage_type={self._agent_file_system.get_storage_type()}"
            )
            return self._agent_file_system

        except Exception as e:
            logger.warning(
                f"Failed to initialize AgentFileSystem: {e}, using legacy mode"
            )
            return None

    async def _ensure_compaction_pipeline(self):
        """确保统一压缩管道已初始化（懒加载）"""
        if self._pipeline_initialized:
            return self._compaction_pipeline

        afs = await self._ensure_agent_file_system()
        if not afs:
            self._pipeline_initialized = True
            return None

        try:
            from gyra.agent.core.memory.compaction_pipeline import (
                UnifiedCompactionPipeline,
                HistoryCompactionConfig,
            )

            ctx = self.not_null_agent_context
            self._compaction_pipeline = UnifiedCompactionPipeline(
                conv_id=ctx.conv_id,
                session_id=ctx.conv_session_id or ctx.conv_id,
                agent_file_system=afs,
                work_log_storage=self.memory.gpts_memory if self.memory else None,
                llm_client=self._get_llm_client(),
                config=HistoryCompactionConfig(
                    context_window=self.context_window,
                    compaction_threshold_ratio=self.compaction_threshold_ratio,
                    prune_protect_tokens=self.prune_protect_tokens,
                    max_output_lines=(
                        self._truncator_max_lines
                        if hasattr(self, "_truncator_max_lines")
                        else 2000
                    ),
                    max_output_bytes=(
                        self._truncator_max_bytes
                        if hasattr(self, "_truncator_max_bytes")
                        else 50 * 1024
                    ),
                ),
            )
            self._pipeline_initialized = True
            logger.info("UnifiedCompactionPipeline initialized")
            return self._compaction_pipeline
        except Exception as e:
            logger.warning(f"Failed to initialize compaction pipeline: {e}")
            self._pipeline_initialized = True
            return None

    def _get_llm_client(self) -> Optional[Any]:
        """获取 LLM 客户端"""
        if (
            hasattr(self, "llm_config")
            and self.llm_config
            and self.llm_config.llm_client
        ):
            return self.llm_config.llm_client
        return None

    # _check_and_compact_context removed in Phase 2 - replaced by UnifiedCompactionPipeline
    # _prune_history removed in Phase 2 - replaced by UnifiedCompactionPipeline

    async def _check_doom_loop(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> bool:
        """
        检查是否存在末日循环

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            bool: 是否允许继续执行
        """
        if not self.enable_doom_loop_detection or not self._doom_loop_detector:
            return True

        # 记录工具调用
        self._doom_loop_detector.record_call(tool_name, args)

        # 检查是否触发 Doom Loop
        result: DoomLoopCheckResult = self._doom_loop_detector.check_doom_loop(
            tool_name, args, auto_record=False
        )

        if result.is_doom_loop:
            logger.warning(
                f"Doom loop detected for {tool_name}: {result.consecutive_count} consecutive calls"
            )

            # 通过权限系统请求确认
            allowed = await self._doom_loop_detector.check_and_ask_permission(
                tool_name, args
            )

            if not allowed:
                logger.info(f"Doom loop blocked for {tool_name}")
                return False

        return True

    async def _run_single_tool_with_protection(
        self,
        tool_name: str,
        args: Dict[str, Any],
        execution_func: Callable[..., Awaitable[ActionOutput]],
        **execution_kwargs,
    ) -> ActionOutput:
        """
        执行单个工具，包含完整的保护机制

        Args:
            tool_name: 工具名称
            args: 工具参数
            execution_func: 实际执行工具的功能函数
            **execution_kwargs: 传递给执行函数的额外参数

        Returns:
            ActionOutput: 工具执行结果
        """
        self._tool_call_count += 1

        # 1. 检查 Doom Loop
        allowed = await self._check_doom_loop(tool_name, args)
        if not allowed:
            return ActionOutput(
                action_id=f"doom_loop_blocked_{self._tool_call_count}",
                name="ToolExecution",
                action=tool_name,
                is_exe_success=False,
                content=f"Tool execution blocked due to detected doom loop pattern (tool: {tool_name})",
                state=Status.BLOCKED.value,
            )

        # 2. 执行工具
        try:
            result: ActionOutput = await execution_func(**execution_kwargs)
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return ActionOutput(
                action_id=f"error_{self._tool_call_count}",
                name="ToolExecution",
                action=tool_name,
                is_exe_success=False,
                content=f"Tool execution failed: {str(e)}",
                state=Status.FAILED.value,
            )

        # 3. 截断输出（使用统一压缩管道 Layer 1 或回退到旧逻辑）
        if result.content and self.enable_output_truncation:
            pipeline = await self._ensure_compaction_pipeline()
            if pipeline:
                tr = await pipeline.truncate_output(result.content, tool_name, args)
                result.content = tr.content
            elif self._truncator:
                tr_result = self._truncator.truncate(
                    result.content, tool_name=tool_name
                )
                result.content = tr_result.content

        return result

    async def load_thinking_messages(
        self,
        received_message: AgentMessage,
        sender: Agent,
        rely_messages: Optional[List[AgentMessage]] = None,
        **kwargs,
    ) -> Tuple[List[AgentMessage], Optional[Dict], Optional[str], Optional[str]]:
        """
        加载思考消息，包含四层上下文压缩

        改造：使用 PromptAssembler 分层组装 prompt，替代旧的模板变量替换

        四层架构：
        - Layer 1: 工具输出截断
        - Layer 2: 历史修剪
        - Layer 3: 上下文压缩
        - Layer 4: 跨轮次对话历史压缩

        Returns:
            Tuple: (消息列表, 上下文, 系统提示, 用户提示)
        """
        # Layer 4: 跨轮次历史管理
        user_question = received_message.content if received_message else ""

        # 开始/复用对话轮次，获取历史记录
        memory_content = None
        history_messages: List[Dict[str, Any]] = []

        try:
            pipeline = await self._ensure_compaction_pipeline()
            if pipeline:
                await pipeline.start_conversation_round(
                    user_question=user_question,
                    user_context=received_message.context if received_message else None,
                )

                if self.use_message_list_history:
                    history_messages = (
                        await pipeline.get_layer4_history_as_message_list(
                            max_tokens=self.message_list_history_max_tokens,
                        )
                    )
                else:
                    memory_content = await pipeline.get_layer4_history_for_prompt()
                    if memory_content:
                        logger.info(
                            f"[HistoryMessageBuilder] Text mode: {len(memory_content)} chars"
                        )
        except Exception as e:
            logger.warning(f"Layer 4: Failed to get history: {e}")

        # 获取基础消息列表（从基类获取消息组装逻辑，但我们会重新构建 prompt）
        # 首轮工具上下文刷新(原 load_resource 钩子职责,随 v1 resource 删除上移至此)
        self.function_calling_context = await self.function_calling_params()
        (
            messages,
            context,
            _,  # 忽略基类的 system_prompt
            _,  # 忽略基类的 user_prompt
        ) = await super().load_thinking_messages(
            received_message, sender, rely_messages, **kwargs
        )

        if not messages:
            return messages, context, "", ""


        # 确保AgentFileSystem已初始化（用于文件管理）
        await self._ensure_agent_file_system()

        # ========== 使用 PromptAssembler 分层组装 Prompt ==========
        system_prompt = ""
        user_prompt = ""

        try:
            assembler = self._get_prompt_assembler()
            logger.info(
                f"ReActMasterAgent: sandbox_manager="
                f"{getattr(self, 'sandbox_manager', None) is not None}"
            )

            # 获取用户配置的身份内容
            user_identity = None
            user_prompt_prefix = None

            if hasattr(self, "profile"):
                user_identity = getattr(self.profile, "system_prompt_template", None)
                user_prompt_prefix = getattr(self.profile, "user_prompt_template", None)

            # 构建模板变量
            template_vars = getattr(self.profile, "template_vars", None) or {}

            # 获取用户配置的基本变量
            ctx = self.agent_context
            base_vars = {
                "role": getattr(self.profile, "role", "")
                if hasattr(self, "profile")
                else "",
                "name": getattr(self.profile, "name", "")
                if hasattr(self, "profile")
                else "",
                "goal": getattr(self.profile, "goal", "")
                if hasattr(self, "profile")
                else "",
                "language": getattr(self.profile, "language", "zh")
                if hasattr(self, "profile")
                else "zh",
            }

            # 使用 generate_bind_variables 获取 Agent 注册的所有变量
            # （包括 now_time、conv_start_time 等 _vm 注册的变量）
            if received_message and sender:
                bind_vars = await self.generate_bind_variables(
                    received_message=received_message,
                    sender=sender,
                    rely_messages=rely_messages,
                    historical_dialogues=None,
                    context=None,
                    resource_info=None,
                )
                # 合并：base_vars 优先级较低，bind_vars 可以覆盖
                render_vars = {**base_vars, **bind_vars, **template_vars}
            else:
                # 无 received_message 时，直接合并 base_vars 和 template_vars
                # 需要手动添加时间变量
                logger.warning("load_thinking_messages: received_message or sender is None")
                render_vars = {**base_vars, **template_vars}
                render_vars["user_name"] = getattr(ctx, "user_name", "") if ctx else ""
                render_vars["user_id"] = getattr(ctx, "user_id", "") if ctx else ""
                render_vars["conv_start_time"] = getattr(ctx, "conv_start_time", None) if ctx else None
                # 添加时间变量
                try:
                    render_vars["now"] = await self._vm.get_value("now", instance=self)
                    render_vars["now_time"] = await self._vm.get_value("now_time", instance=self)
                except Exception as e:
                    logger.warning(f"Failed to get time variables from _vm: {e}")
                    from datetime import datetime
                    render_vars["now"] = datetime.now().strftime("%Y-%m-%d")
                    render_vars["now_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 根据 mode 选择组装方式
            # ========== system_prompt 组装（独立 try-catch）==========
            try:
                # 静态记忆层：从 read pipeline 取冻结块（session 级不变）
                memory_static_block = None
                try:
                    if (
                        hasattr(self, "_memory_bundle")
                        and self._memory_bundle
                        and self.not_null_agent_context
                        and self._memory_bundle.config.enable_long_term_use
                    ):
                        pipeline = self.memory.gpts_memory.get_memory_pipeline(
                            self.not_null_agent_context.conv_id
                        )
                        if pipeline is not None and not pipeline.static_loaded:
                            await self.memory.gpts_memory.load_memory_static_block(
                                self.not_null_agent_context.conv_id
                            )
                        if pipeline is not None:
                            memory_static_block = pipeline.static_block
                except Exception as _static_err:  # noqa: BLE001
                    logger.debug(f"[MemoryRead] static block load skipped: {_static_err}")

                # 分层组装：身份层 + 静态记忆层 + 资源层 + 控制层
                # S10: 经 ResourceFacade 产完整 system 快照(四层 Contribution)。
                # 用现有 PromptAssembler 产身份层/控制层文本(复用渲染,不重写),
                # 资源层由 facade 经各 capability wrapper 原生 declare 注入(legacy 桥接已移除)。
                identity_text = await assembler._assemble_identity(
                    user_identity, **render_vars
                )
                control_text = await assembler._assemble_control_flow(**render_vars)

                facade = self._get_resource_facade()

                # S14/S20: 沙箱作为 Capability 投影——env 进 system、
                # 委托沙箱的文件/脚本类工具(Bash/Read/Write/Edit/deliver_file)归 sandbox 能力。
                # 有沙箱时这些工具从 builtin 移出、由 SandboxResource.declare_tools 归 sandbox;
                # 无沙箱时仍是本地默认工具(builtin)。capability_id 标归属,executor_id 仍 builtin
                # (工具执行体自处理沙箱/本地切换,选B 务实方案)。
                sandbox_contribs, sandbox_tool_entries, non_sandbox_builtin = (
                    await self._build_sandbox_capability()
                )

                snapshot = await facade.assemble(
                    agent_id=(self.agent_context.agent_app_code if self.agent_context else None) or self.name,
                    conv_id=self.agent_context.conv_id if self.agent_context else "",
                    agent=self,
                    identity=identity_text,
                    control_block=control_text,
                    memory_static_block=memory_static_block,
                    builtin_tools=non_sandbox_builtin,
                    extra_static_contribs=sandbox_contribs,
                    extra_tools=sandbox_tool_entries,
                )
                # 降级合并 system 块为 str(legacy separator 保向前兼容),
                # 真实 cache_control 由 provider 层 S12 消费 full_system_blocks()。
                system_prompt = separator_join_system_blocks(
                    snapshot.full_system_blocks(),
                    separator=assembler.config.section_separator,
                )
                self._last_snapshot = snapshot
                logger.info(
                    "ResourceFacade: system 快照组装完成（身份层+记忆层+资源层+控制层）"
                )
            except Exception as e:
                logger.warning(f"PromptAssembler: system_prompt 组装失败，回退到默认 prompt: {e}")
                import traceback
                traceback.print_exc()
                try:
                    from gyra.util.template_utils import render
                    from datetime import datetime

                    # 获取时间变量（回退时也需要）
                    ctx = self.agent_context
                    now_time_fallback = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conv_start_time_fallback = getattr(ctx, "conv_start_time", "") if ctx else ""

                    system_prompt = render(
                        REACT_MASTER_FC_SYSTEM_TEMPLATE_CN,
                        {
                            "agent_name": getattr(self.profile, "name", "Assistant")
                            if hasattr(self, "profile")
                            else "Assistant",
                            "max_steps": "20",
                            "resource_prompt": "",
                            "sandbox_prompt": "",
                            "sandbox": {"enable": False, "prompt": ""},
                            "available_agents": "",
                            "available_knowledges": "",
                            "available_skills": "",
                            "now_time": now_time_fallback,
                            "conv_start_time": conv_start_time_fallback,
                        },
                    )
                except Exception as render_error:
                    logger.error(f"回退渲染也失败: {render_error}")
                    system_prompt = "你是一个 AI 助手，请帮助用户完成任务。"

            # ========== user_prompt 组装（独立 try-catch，不影响 system_prompt）==========
            try:
                # 移除 render_vars 中可能存在的 question，避免参数重复
                # question 在 base_agent.py 的 _vm 中已注册，会出现在 bind_vars 中
                user_render_vars = {k: v for k, v in render_vars.items() if k != 'question'}

                # ========== Memory Read Pipeline (hermes-aligned) ==========
                # Dynamic layer: consume the prefetch cache warmed by the
                # previous turn's turn_complete hook (non-blocking). First
                # turn or not-ready prefetch falls back to sync retrieval.
                # Static layer (room=profile/preference) is injected into
                # system_prompt separately, not here.
                memory_context = None
                if (
                    hasattr(self, "_memory_bundle")
                    and self._memory_bundle
                    and self._memory_bundle.config.enable_long_term_use
                ):
                    try:
                        bundle = self._memory_bundle
                        conv_id = self.not_null_agent_context.conv_id
                        pipeline = self.memory.gpts_memory.get_memory_pipeline(conv_id)
                        if pipeline is not None:
                            # Non-blocking consume of last turn's prefetch.
                            # consumer=self.name：同 conv 多 agent 各自消费一次
                            # （prefetch cache 按消费方 key 去重）。
                            memory_context = await pipeline.consume_prefetch(
                                timeout=0.0, consumer=self.name
                            )
                            if memory_context:
                                logger.info(
                                    f"[MemoryRead] prefetch hit: {len(memory_context)} chars"
                                )
                        # Sync fallback: first turn, prefetch not ready, or no pipeline.
                        if not memory_context:
                            memory_context = await bundle.manager.retrieve_relevant_memories(
                                query=user_question,
                                top_k=bundle.config.top_k,
                                use_hybrid_search=True,
                                exclude_rooms=["profile", "preference"],
                            )
                            if memory_context:
                                logger.info(
                                    f"[MemoryRead] sync fallback: {len(memory_context)} chars"
                                )
                        if memory_context:
                            # Store for potential use in other methods
                            self._memory_context = memory_context
                            # Wrap in <memory-context> fence so the LLM
                            # treats it as reference data, and the stream
                            # scrubber can strip it from UI output.
                            from gyra.agent.core.memory.read_pipeline import (
                                build_memory_context_block,
                            )
                            memory_context = build_memory_context_block(memory_context)
                    except Exception as e:
                        logger.warning(f"[MemoryRead] pipeline consume failed: {e}")

                # Determine memory_content for user_prompt:
                # - If memory bundle exists and retrieved content, use that
                # - Otherwise, use Layer 4 history content if not using message_list_history
                final_memory_content = None
                if memory_context:
                    # Memory bundle retrieval takes precedence
                    final_memory_content = memory_context
                elif not self.use_message_list_history and memory_content:
                    # Fall back to Layer 4 history (conversation history)
                    final_memory_content = memory_content

                user_prompt = await assembler.assemble_user_prompt(
                    user_prompt_prefix=user_prompt_prefix,
                    memory_content=final_memory_content,
                    question=user_question,
                    **user_render_vars,
                )
            except Exception as e:
                logger.warning(f"PromptAssembler: user_prompt 组装失败，使用原始问题: {e}")
                import traceback
                traceback.print_exc()
                # user_prompt 失败不影响 system_prompt，直接使用用户问题
                user_prompt = user_question

        except Exception as e:
            # 外层异常：初始化阶段失败（assembler 创建、变量准备等）
            logger.warning(f"PromptAssembler: 初始化阶段失败，回退到默认 prompt: {e}")
            import traceback
            traceback.print_exc()
            from datetime import datetime
            ctx = self.agent_context
            now_time_fallback = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conv_start_time_fallback = getattr(ctx, "conv_start_time", "") if ctx else ""
            try:
                from gyra.util.template_utils import render
                system_prompt = render(
                    REACT_MASTER_FC_SYSTEM_TEMPLATE_CN,
                    {
                        "agent_name": getattr(self.profile, "name", "Assistant")
                        if hasattr(self, "profile")
                        else "Assistant",
                        "max_steps": "20",
                        "resource_prompt": "",
                        "sandbox_prompt": "",
                        "sandbox": {"enable": False, "prompt": ""},
                        "available_agents": "",
                        "available_knowledges": "",
                        "available_skills": "",
                        "now_time": now_time_fallback,
                        "conv_start_time": conv_start_time_fallback,
                    },
                )
            except Exception as render_error:
                logger.error(f"回退渲染也失败: {render_error}")
                system_prompt = "你是一个 AI 助手，请帮助用户完成任务。"
            user_prompt = user_question

        filtered_messages = [
            msg
            for msg in messages
            if not (hasattr(msg, "role") and msg.role == ModelMessageRoleType.SYSTEM)
            and not (isinstance(msg, dict) and msg.get("role") == "system")
        ]

        if filtered_messages:
            last_idx = len(filtered_messages) - 1
            last_msg = filtered_messages[last_idx]
            is_human = (
                hasattr(last_msg, "role")
                and last_msg.role == ModelMessageRoleType.HUMAN
            ) or (isinstance(last_msg, dict) and last_msg.get("role") == "human")
            if is_human:
                filtered_messages.pop()

        if system_prompt:
            from gyra.agent.core.types import AgentMessage

            filtered_messages.insert(
                0,
                AgentMessage(
                    content=system_prompt,
                    role=ModelMessageRoleType.SYSTEM,
                ),
            )

        # Message List 模式：插入历史消息到消息列表
        if self.use_message_list_history and history_messages:
            from gyra.agent.core.types import AgentMessage

            for hist_msg in history_messages:
                filtered_messages.append(
                    AgentMessage(
                        content=hist_msg.get("content", ""),
                        role=hist_msg.get("role", "user"),
                        context=hist_msg,
                    )
                )
            logger.info(
                f"[HistoryMessageBuilder] Injected {len(history_messages)} history messages"
            )

        if user_prompt:
            from gyra.agent.core.types import AgentMessage

            filtered_messages.append(
                AgentMessage(
                    content=user_prompt,
                    role=ModelMessageRoleType.HUMAN,
                    context=received_message.context if received_message else None,
                    content_types=received_message.content_types
                    if received_message
                    else None,
                ),
            )

        return filtered_messages, context, system_prompt, user_prompt

    @staticmethod
    def _extract_text_from_content(content) -> str:
        """从 LLM 消息的 content 字段提取纯文本。"""
        if not content:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    obj = item.get("object", {})
                    if isinstance(obj, dict):
                        text_parts.append(obj.get("data", ""))
                elif hasattr(item, "object"):
                    obj = getattr(item, "object", None)
                    if obj and hasattr(obj, "data"):
                        text_parts.append(getattr(obj, "data", ""))
            return "\n".join(filter(None, text_parts))
        return str(content)

    def _estimate_context_tokens(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """估算实际上下文窗口的 token 使用情况。

        计算规则（优先级从上到下）：
        1. 实时计算：优先用 tiktoken 精确切分（真实 token 数）；
        2. 兜底推算：tokenizer 不可用/失败时按「字符数/4」估算。

        返回的明细用于环形图/详情抽屉分层展示：
        - system_tokens: system 消息占用（不含技能指令）
        - conversation_tokens: 非 system 消息占用（历史 + 当前用户消息）
        - tool_tokens: 工具列表占用
        - skill_tokens: 技能指令（`<skill>` 指令/索引）占用，是 system_tokens 的子集
        """
        from gyra.agent.core.usage_metric import count_tokens

        system_tokens = 0
        conversation_tokens = 0
        tool_tokens = 0
        skill_tokens = 0

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                chunk = content
            else:
                try:
                    chunk = json.dumps(content, ensure_ascii=False)
                except Exception:  # noqa: BLE001
                    chunk = str(content)

            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                try:
                    chunk += json.dumps(tool_calls, ensure_ascii=False)
                except Exception:  # noqa: BLE001
                    chunk += str(tool_calls)

            msg_token_estimate = count_tokens(chunk)
            if msg.get("role") == "system":
                system_tokens += msg_token_estimate
                skill_tokens += self._count_skill_tokens(chunk)
            else:
                conversation_tokens += msg_token_estimate

        if tools:
            try:
                tool_tokens = count_tokens(json.dumps(tools, ensure_ascii=False))
            except Exception:  # noqa: BLE001
                tool_tokens = count_tokens(str(tools))

        message_tokens = system_tokens + conversation_tokens
        return {
            "total_tokens": message_tokens + tool_tokens,
            "message_tokens": message_tokens,
            "system_tokens": system_tokens,
            "conversation_tokens": conversation_tokens,
            "tool_tokens": tool_tokens,
            "skill_tokens": skill_tokens,
        }

    @staticmethod
    def _count_skill_tokens(text: str) -> int:
        """统计 system 提示里 `<skill>...</skill>` 指令/索引块的 token 占用。

        技能以 <skill>…</skill> 标记注入系统提示（见 var_skills / 项目生态），
        这里单独切分出来，让前端「技能」分类能真实反映技能上下文占用，
        而不是全部并入「系统提示词」。
        """
        from gyra.agent.core.usage_metric import count_tokens

        if not text:
            return 0
        blocks = re.findall(r"<skill>.*?</skill>", text, re.S)
        if not blocks:
            return 0
        return count_tokens("".join(blocks))

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
        """重写 thinking 方法 - 使用 Message List 模式注入历史对话。

        核心改动：
        1. 将用户消息记录到 WorkLog
        2. 通过 HistoryMessageBuilder 从 WorkLog + GptsMessage 统一构建消息列表
        3. 不使用 base_agent 的 tool_messages 机制，改由 builder 统一管理
        4. 确保工具列表每轮刷新
        """
        from datetime import datetime
        from gyra.agent.core.base_agent import _new_system_message

        # 每轮 think 开始时重置"背景异步任务通知已下发"标记，
        # 仅本轮真正收集到完成通知时才置 True，供 act() 判断是否强制续跑。
        self._bg_notif_delivered = False

        # ========== 确保核心组件已初始化 ==========
        await self._ensure_work_log_manager()
        await self._ensure_context_engine()

        # ========== 获取基本上下文 ==========
        conv_id = "default"
        session_id = "default"
        if self.not_null_agent_context:
            conv_id = self.not_null_agent_context.conv_id or "default"
            session_id = self.not_null_agent_context.conv_session_id or conv_id

        # ========== 提取当前用户消息 ==========
        current_user_content = None
        if received_message and received_message.content:
            current_user_content = self._extract_text_from_content(
                received_message.content
            )

        # ========== 记录用户消息到 WorkLog ==========
        # 仅在首次调用时录入（current_retry_counter == 0）
        if current_user_content and self._work_log_manager and self.current_retry_counter == 0:
            try:
                await self._work_log_manager.record_user_message(
                    user_content=current_user_content,
                    conv_id=conv_id,
                )
            except Exception as e:
                logger.warning(f"Failed to record user message to work_log: {e}")

        # ========== 清理上一轮工具失败熔断状态 ==========
        # 失败计数 / 熔断状态挂在 agent 实例上，conv_id 跨用户消息不变，
        # 会残留到新一轮提问：上一轮某工具连续失败被熔断后，追问仍被阻止。
        # 每个新用户消息首轮（current_retry_counter == 0）清空计数 + 解除熔断。
        if self.current_retry_counter == 0:
            self._reset_tool_failure_count(None)

        # ========== 确保工具列表每轮刷新 ==========
        if self.current_retry_counter > 0:
            try:
                self.function_calling_context = await self.function_calling_params()
                logger.info(
                    f"[ToolRefresh] Refreshed function_calling_context on retry {self.current_retry_counter}"
                )
            except Exception as e:
                logger.warning(f"Failed to refresh function_calling_context: {e}")

        # ========== 计算上下文预算 ==========
        context_window = await self.get_agent_llm_context_length()
        history_budget = int(context_window * 0.85)

        logger.info(
            f"[ContextBudget] context_window={context_window}, "
            f"history_budget={history_budget}"
        )

        # ========== 通过 ContextEngine 统一构建消息 ==========
        # 单一权威路径：装配(唯一join+排序) → 分段 → 分层+剪枝 → cold重整 → 发送前不变量门禁
        all_conversation_messages = []
        history_layer_tokens = {"compressed": 0, "retained": 0}
        build_result = None  # BuildOutput（含 cleanup_hints）

        try:
            build_result = await self._compute_context_engine_messages(
                conv_id=conv_id,
                session_id=session_id,
                context_window=context_window,
                current_user_content=current_user_content,
            )
            if build_result is not None:
                all_conversation_messages = build_result.messages
                history_layer_tokens = build_result.history_breakdown
                guard_report = build_result.guard_report
                if guard_report and guard_report.repairs:
                    logger.info(
                        f"[ContextEngine] InvariantGuard repaired: {guard_report.repairs}"
                    )
                logger.info(
                    f"[ContextEngine] Built {len(all_conversation_messages)} messages, "
                    f"layer_tokens={history_layer_tokens}, "
                    f"total_tokens={build_result.total_tokens}"
                )
        except Exception as e:
            logger.error(f"[CRITICAL] ContextEngine build failed: {e}", exc_info=True)
            build_result = None

        # ========== Fallback: 若 builder 不可用，使用 base_agent 的 tool_messages ==========
        if not all_conversation_messages:
            logger.info("[Fallback] HistoryMessageBuilder unavailable, using base tool_messages")

            # 异步任务完成通知注入（并入 system，不占 user 末位）
            _fb_op = []
            _fb_notif = await self._collect_background_notifications()
            if _fb_notif:
                self._bg_notif_delivered = True
                _fb_op.append("[异步任务完成通知]\n" + _fb_notif)
            _fb_supp = await self._collect_supplemental_user_input(session_id)
            if _fb_supp:
                _fb_op.append("[用户补充输入]\n" + _fb_supp)
            if _fb_op:
                tool_msgs = kwargs.get("tool_messages") or []
                tool_msgs.append({"role": "system", "content": "\n\n".join(_fb_op)})
                kwargs["tool_messages"] = tool_msgs

            if self._system_event_manager:
                self._system_event_manager.add_event(
                    event_type=SystemEventType.LLM_THINKING,
                    title="LLM 思考",
                    description=f"Agent: {self.name}",
                )

            return await super().thinking(
                messages,
                reply_message_id,
                sender,
                prompt=prompt,
                received_message=received_message,
                reply_message=reply_message,
                **kwargs,
            )

        # ========== 收集运行时上下文（通知/补充输入/todo）-- 并入 system prompt ==========
        # 不再作为 role=user 追加到末尾，确保"最后一条 user 消息 = 当前用户指令"。
        _operational_parts = []
        async_notification = await self._collect_background_notifications()
        if async_notification:
            self._bg_notif_delivered = True
            _operational_parts.append("[异步任务完成通知]\n" + async_notification)
        supplemental_input = await self._collect_supplemental_user_input(session_id)
        if supplemental_input:
            _operational_parts.append("[用户补充输入]\n" + supplemental_input)
        try:
            from gyra.agent.tools.builtin.todo.todo_reminder import build_todo_reminder
            _todo_reminder = await build_todo_reminder(self.memory, conv_id)
            if _todo_reminder:
                _operational_parts.append(_todo_reminder)
        except Exception as _todo_e:
            logger.debug(f"[TodoReminder] inject failed: {_todo_e}")

        # ========== 构建最终 LLM 消息列表 ==========
        llm_messages = []

        # 1. System message（运行时上下文追加到 system prompt 末尾）
        system_prompt_text = prompt
        if not system_prompt_text and reply_message:
            system_prompt_text = getattr(reply_message, "system_prompt", None)
        if not system_prompt_text and messages:
            for m in messages:
                m_role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
                if m_role and str(m_role).lower() in ("system", ModelMessageRoleType.SYSTEM):
                    m_content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
                    if m_content:
                        system_prompt_text = str(m_content)
                    break
        if _operational_parts:
            _op = "\n\n".join(_operational_parts)
            system_prompt_text = (system_prompt_text + "\n\n" + _op) if system_prompt_text else _op
        if system_prompt_text:
            llm_messages.extend(_new_system_message(system_prompt_text))

        # 2. 所有对话消息（摘要 + 保留区，末条为当前 user prompt）
        if all_conversation_messages:
            llm_messages.extend(all_conversation_messages)

        logger.info(
            f"[MSG_DEBUG] Final llm_messages: count={len(llm_messages)}, "
            f"roles={[m.get('role') for m in llm_messages[:10]]}"
        )

        # ========== 记录 LLM 思考事件 ==========
        if self._system_event_manager:
            self._system_event_manager.add_event(
                event_type=SystemEventType.LLM_THINKING,
                title="LLM 思考",
                description=f"Agent: {self.name}",
            )

        # ========== 调用 LLM ==========
        if not self.llm_client:
            raise ValueError("LLM client is not initialized!")

        last_model = None
        last_err = None
        retry_count = 0
        start_time: datetime = datetime.now()
        MAX_ATTEMPTS = 3

        while retry_count < MAX_ATTEMPTS:
            llm_model = None
            llm_context = None
            try:
                llm_model, llm_context = await self.select_llm_model(last_model)

                # 统计上下文使用
                tools_for_context = None
                if self.function_calling_context and "tools" in self.function_calling_context:
                    tools_for_context = self.function_calling_context.get("tools")

                context_stats = self._estimate_context_tokens(
                    llm_messages, tools_for_context
                )
                logger.info(
                    f"[ContextWindow] Total tokens: {context_stats['total_tokens']}, "
                    f"messages: {context_stats['message_tokens']}, "
                    f"tools: {context_stats['tool_tokens']}, "
                    f"history_layers: {history_layer_tokens}"
                )

                # 当前上下文空间占用（实时环形图）：把**当前这一轮真正加载进上下文的
                # message+tool 占用**推给 SSE。注意不是累计 token 消耗。
                # 明细分类：system / history / 当前用户消息 / 工具列表 / 分层 compressed/retained
                # 计算规则：本轮增量用 tiktoken 实时计算，tokenizer 不可用则兜底字符/4。
                try:
                    from gyra.agent.core.usage_metric import (
                        count_tokens,
                        emit_context_usage,
                    )

                    _cur_user_tokens = count_tokens(current_user_content or "")
                    _history_tokens = max(
                        0,
                        context_stats["conversation_tokens"] - _cur_user_tokens,
                    )
                    _skill_tokens = context_stats.get("skill_tokens", 0) or 0
                    emit_context_usage(
                        conv_id=self.not_null_agent_context.conv_id,
                        total_tokens=context_stats["total_tokens"],
                        context_window=context_window,
                        prompt_tokens=context_stats["message_tokens"],
                        completion_tokens=context_stats["tool_tokens"],
                        model_name=llm_model or "",
                        system_prompt_tokens=context_stats["system_tokens"]
                        - _skill_tokens,
                        history_tokens=_history_tokens,
                        user_message_tokens=_cur_user_tokens,
                        layer_tokens=history_layer_tokens,
                        skills=_skill_tokens,
                    )
                except Exception as _ctx_err:  # noqa: BLE001
                    logger.debug(f"[usage] context emit skipped: {_ctx_err}")

                prev_thinking = ""
                prev_content = ""
                agent_llm_out = None
                thinking_chunk_count = 0
                content_chunk_count = 0
                import time as time_mod
                start_ms = int(time_mod.time() * 1000)

                # 传 system_blocks 到 context.extra,供 Anthropic provider 用
                # to_anthropic_system 产数组+cache_control;OpenAI provider 忽略(用 str)。
                _llm_ctx = llm_messages[-1].pop("context", None) if llm_messages else None
                if self._last_snapshot is not None:
                    _blocks = self._last_snapshot.full_system_blocks()
                    if _blocks:
                        if _llm_ctx is None:
                            from gyra.core.interface.llm import ModelRequestContext
                            _llm_ctx = ModelRequestContext()
                        _extra = getattr(_llm_ctx, "extra", None) or {}
                        _extra["system_blocks"] = _blocks
                        if hasattr(_llm_ctx, "extra"):
                            _llm_ctx.extra = _extra
                        elif isinstance(_llm_ctx, dict):
                            _llm_ctx["extra"] = _extra

                async for output in self.llm_client.create(
                    context=_llm_ctx,
                    messages=llm_messages,
                    llm_model=llm_model,
                    mist_keys=self.mist_keys,
                    max_new_tokens=self.not_null_agent_context.max_new_tokens,
                    temperature=self.not_null_agent_context.temperature,
                    top_p=self.not_null_agent_context.top_p,
                    reasoning_effort=self.not_null_agent_context.reasoning_effort,
                    llm_context=llm_context,
                    verbose=self.not_null_agent_context.verbose,
                    trace_id=self.not_null_agent_context.trace_id,
                    rpc_id=self.not_null_agent_context.rpc_id,
                    function_calling_context=self.function_calling_context,
                    staff_no=self.not_null_agent_context.staff_no,
                ):
                    agent_llm_out = output
                    current_thinking = output.thinking_content
                    current_content = output.content

                    if self.not_null_agent_context.incremental:
                        res_thinking = current_thinking[len(prev_thinking):]
                        res_content = current_content[len(prev_content):]
                        prev_thinking = current_thinking
                        temp_prev_content = current_content
                    else:
                        res_thinking = (
                            current_thinking.strip().replace("\\n", "\n")
                            if current_thinking
                            else current_thinking
                        )
                        res_content = (
                            current_content.strip().replace("\\n", "\n")
                            if current_content
                            else current_content
                        )
                        prev_thinking = res_thinking
                        temp_prev_content = res_content

                    if len(prev_thinking) > 0 and len(temp_prev_content) <= 0:
                        thinking_chunk_count += 1
                    if len(prev_content) > 0:
                        content_chunk_count += 1
                    is_first_chunk = thinking_chunk_count == 1
                    is_first_content = content_chunk_count == 1

                    await self.listen_thinking_stream(
                        output,
                        reply_message_id,
                        start_time=start_time,
                        cu_thinking_incr=res_thinking,
                        cu_content_incr=res_content,
                        is_first_chunk=is_first_chunk,
                        is_first_content=is_first_content,
                        received_message=received_message,
                        reply_message=reply_message,
                        sender=sender,
                        prev_content=prev_content,
                    )

                    prev_content = temp_prev_content

                if agent_llm_out is None:
                    raise Exception(f"Model {llm_model} returned empty response")

                logger.info(
                    f"[LLM_RESPONSE] model={llm_model}, "
                    f"content_length={len(agent_llm_out.content) if agent_llm_out.content else 0}"
                )

                # 推理服务已返回权威 token 数：用它校正当前上下文占用（服务计算 > 实时估算）。
                # 若服务返回了 prompt_tokens，按「服务值/本地方案估值」比例缩放各明细段，
                # 使 system/history/user/tools/layers 与权威总额保持一致。
                try:
                    if agent_llm_out is not None and agent_llm_out.metrics is not None:
                        from gyra.agent.core.usage_metric import emit_context_usage

                        svc_prompt = int(
                            getattr(agent_llm_out.metrics, "prompt_tokens", 0) or 0
                        )
                        est_total = context_stats["total_tokens"]
                        if svc_prompt > 0 and est_total > 0:
                            _scale = svc_prompt / est_total
                            _sc = lambda v: int(round(v * _scale))  # noqa: E731
                            _skill_tokens = context_stats.get("skill_tokens", 0) or 0
                            emit_context_usage(
                                conv_id=self.not_null_agent_context.conv_id,
                                total_tokens=svc_prompt,
                                context_window=context_window,
                                prompt_tokens=_sc(context_stats["message_tokens"]),
                                completion_tokens=_sc(context_stats["tool_tokens"]),
                                model_name=llm_model or "",
                                system_prompt_tokens=_sc(
                                    context_stats["system_tokens"] - _skill_tokens
                                ),
                                history_tokens=_sc(
                                    max(
                                        0,
                                        context_stats["conversation_tokens"]
                                        - _cur_user_tokens,
                                    )
                                ),
                                user_message_tokens=_sc(_cur_user_tokens),
                                layer_tokens={
                                    k: _sc(v)
                                    for k, v in history_layer_tokens.items()
                                },
                                skills=_sc(_skill_tokens),
                            )
                except Exception as _svc_err:  # noqa: BLE001
                    logger.debug(f"[usage] service-corrected emit skipped: {_svc_err}")

                # ========== 应用 BuildResult 清理 ==========
                if build_result and self.memory and hasattr(self.memory, "gpts_memory"):
                    try:
                        cleanup_hints = build_result.get_cache_cleanup_hints()
                        if cleanup_hints.get("can_evict_message_ids") or cleanup_hints.get("can_evict_entry_message_ids"):
                            cleanup_stats = await self.memory.gpts_memory.apply_build_result_cleanup(
                                conv_id, cleanup_hints
                            )
                            if self._work_log_manager:
                                evictable = set(cleanup_hints.get("can_evict_entry_message_ids", []))
                                self._work_log_manager.trim_work_log(evictable)
                            logger.info(f"[Cleanup] Applied: {cleanup_stats}")
                    except Exception as cleanup_err:
                        logger.warning(f"[Cleanup] Failed to apply build result cleanup: {cleanup_err}")

                return agent_llm_out

            except Exception as e:
                last_model = llm_model
                last_err = str(e)
                retry_count += 1
                logger.warning(
                    f"[LLM Retry] Attempt {retry_count}/{MAX_ATTEMPTS}, "
                    f"model {llm_model} failed: {str(e)[:200]}"
                )

        raise Exception(
            f"Failed to get response from LLM after {MAX_ATTEMPTS} attempts. "
            f"Last error: {last_err}"
        )

    async def act(
        self,
        message: AgentMessage,
        sender: Agent,
        reviewer: Optional[Agent] = None,
        is_retry_chat: bool = False,
        last_speaker_name: Optional[str] = None,
        received_message: Optional[AgentMessage] = None,
        **kwargs,
    ) -> List[ActionOutput]:
        """
        执行动作，包含完整保护机制
        """
        if not message:
            raise ValueError("The message content is empty!")

        act_outs: List[ActionOutput] = []

        # 异步任务完成后的 resume 轮次：LLM 若只返回占位文本（无工具调用），
        # 不应就此 terminate 结束，而应强制其继续把异步结果加工成最终交付物，
        # 避免主对话在子任务/媒体任务都完成后"卡住"。
        # 用 received_message（当前用户指令）而非 message（助手回复）判定：
        # coordinator 把完成通知作为 user 消息注入，整个 resume 轮次内 received_message
        # 都带 "[异步任务完成通知]"，跨多次 LLM 迭代保持一致；think-time 注入路径则靠
        # _bg_notif_delivered 抬升。任一命中即视为 async resume 轮次。
        _rm_id = getattr(received_message, "message_id", None)
        if self._async_resume_received_id != _rm_id:
            # 新的用户消息：重置持久标记，避免跨用户轮次误判
            self._async_resume_received_id = _rm_id
            self._async_resume_active = False
        is_async_resume_round = (
            "[异步任务完成通知]"
            in (getattr(received_message, "content", None) or "")
        ) or getattr(self, "_bg_notif_delivered", False)
        if is_async_resume_round:
            self._async_resume_active = True
        # 非异步 resume 轮次时清零强制续跑计数，避免跨轮次累计
        if not self._async_resume_active:
            self._async_resume_force_count = 0
        # 输出截断续跑计数按"用户消息"维度重置：同一用户消息内的多次 LLM 迭代累计，
        # 换新用户消息时清零，避免跨轮次累计。
        if self._length_received_id != _rm_id:
            self._length_received_id = _rm_id
            self._length_force_count = 0

        # 阶段 1：解析所有可能的 action
        real_actions = self.agent_parser.parse_actions(
            llm_out=kwargs.get("agent_llm_out"), action_cls_list=self.actions, **kwargs
        )

        # 阶段 2：并行执行所有解析出的 action
        if real_actions:
            explicit_keys = [
                "ai_message",
                "resource",
                "rely_action_out",
                "render_protocol",
                "message_id",
                "sender",
                "agent",
                "received_message",
                "agent_context",
                "memory",
            ]

            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k not in explicit_keys
            }

            # 传入 AgentFileSystem 和截断配置用于大结果归档
            afs = await self._ensure_agent_file_system()
            filtered_kwargs["agent_file_system"] = afs
            filtered_kwargs["max_output_bytes"] = (
                self._truncator_max_bytes
                if hasattr(self, "_truncator_max_bytes")
                else 5 * 1024
            )
            filtered_kwargs["max_output_lines"] = (
                self._truncator_max_lines
                if hasattr(self, "_truncator_max_lines")
                else 50
            )

            tasks = []
            batch_init_action_reports = []
            has_blank_action = False

            for real_action in real_actions:
                if isinstance(real_action, BlankAction):
                    has_blank_action = True
                    logger.warning(
                        "⚠️ No tool call returned by LLM, will inject system reminder"
                    )

                # 预检查：获取工具名称并检查是否被禁止
                tool_name_to_check = None
                if hasattr(real_action, "action_input") and hasattr(
                    real_action.action_input, "tool_name"
                ):
                    tool_name_to_check = real_action.action_input.tool_name
                elif hasattr(real_action, "name"):
                    tool_name_to_check = real_action.name

                if tool_name_to_check and self._is_tool_blocked(tool_name_to_check):
                    logger.warning(
                        f"🚫 Tool '{tool_name_to_check}' is blocked due to consecutive failures. Skipping execution."
                    )
                    # 获取失败追踪器用于格式化消息
                    tracker = self._get_failure_tracker()
                    failure_msg = tracker.format_failure_message(
                        tool_name_to_check, include_count=True
                    )
                    # 直接创建失败结果，跳过执行
                    blocked_output = ActionOutput(
                        content=failure_msg,
                        name=real_action.name
                        if hasattr(real_action, "name")
                        else tool_name_to_check,
                        action=tool_name_to_check,
                        action_name=tool_name_to_check,
                        is_exe_success=False,
                        state=Status.FAILED.value,
                        have_retry=False,
                        view=f"❌ **工具执行被阻止**\n\n{failure_msg}",
                    )
                    act_outs.append(blocked_output)
                    continue

                # PR 3: step-level resume — retry 时复用已成功的 work_log 结果，跳过工具执行
                if (
                    self.recovering
                    and isinstance(real_action, (FunctionTool, ToolAction))
                    and tool_name_to_check
                ):
                    cached_output = await self._lookup_cached_tool_result(
                        tool_name=tool_name_to_check,
                        tool_args=getattr(real_action, "execute_params", None) or {},
                        tool_call_id=getattr(real_action, "action_uid", None),
                    )
                    if cached_output is not None:
                        logger.info(
                            f"[step-resume] reuse work_log entry for "
                            f"{tool_name_to_check}, skipping execution"
                        )
                        act_outs.append(cached_output)
                        await self.push_context_event(
                            EventType.AfterAction,
                            ActionPayload(action_output=cached_output),
                            await self.task_id_by_received_message(received_message),
                        )
                        continue

                if hasattr(real_action, "prepare_init_msg"):
                    init_report = await real_action.prepare_init_msg(
                        ai_message=message.content if message.content else "",
                        render_protocol=await self.memory.gpts_memory.async_vis_converter(
                            self.not_null_agent_context.conv_id
                        ),
                        message_id=message.message_id,
                        current_message=message,
                        sender=sender,
                        agent=self,
                        received_message=received_message,
                        agent_context=self.agent_context,
                        memory=self.memory,
                        **filtered_kwargs,
                    )
                    if init_report:
                        batch_init_action_reports.append(init_report)

                task = real_action.run(
                    ai_message=message.content if message.content else "",
                    render_protocol=await self.memory.gpts_memory.async_vis_converter(
                        self.not_null_agent_context.conv_id
                    ),
                    message_id=message.message_id,
                    current_message=message,
                    sender=sender,
                    agent=self,
                    received_message=received_message,
                    agent_context=self.agent_context,
                    memory=self.memory,
                    skip_init_push=True,
                    **filtered_kwargs,
                )
                tasks.append((real_action, task))

            if batch_init_action_reports:
                await self.memory.gpts_memory.push_message(
                    conv_id=self.not_null_agent_context.conv_id,
                    stream_msg={
                        "uid": message.message_id,
                        "type": "all",
                        "sender": self.name or self.role,
                        "sender_role": self.role,
                        "message_id": message.message_id,
                        "avatar": self.avatar,
                        "goal_id": message.goal_id,
                        "conv_id": self.not_null_agent_context.conv_id,
                        "conv_session_uid": self.not_null_agent_context.conv_session_id,
                        "app_code": self.not_null_agent_context.gpts_app_code,
                        "start_time": None,
                        "action_report": batch_init_action_reports,
                    },
                )

            # 并行执行所有任务
            # PR 4: act 前 touch 心跳，fire-and-forget
            try:
                from gyra.agent.core.heartbeat_hook import touch_heartbeat as _touch_hb
                if self.not_null_agent_context and self.not_null_agent_context.conv_id:
                    _touch_hb(self.not_null_agent_context.conv_id)
            except Exception:
                pass

            # Tier 3.1: emit act_start 事件到 event log（每个工具一次）
            try:
                from gyra.agent.core.event_log import emit_act_start
                _conv_id = self.not_null_agent_context.conv_id
                _msg_id = message.message_id
                for real_action, _ in tasks:
                    _tool_name = getattr(real_action, "name", None) or "unknown"
                    _args = getattr(real_action, "execute_params", None) or {}
                    emit_act_start(
                        conv_id=_conv_id,
                        tool_name=_tool_name,
                        message_id=_msg_id,
                        args=_args if isinstance(_args, dict) else {},
                    )
            except Exception:
                pass

            results = await asyncio.gather(
                *[task for _, task in tasks], return_exceptions=True
            )

            # PR 4: act 后 touch 心跳，fire-and-forget
            try:
                from gyra.agent.core.heartbeat_hook import touch_heartbeat as _touch_hb2
                if self.not_null_agent_context and self.not_null_agent_context.conv_id:
                    _touch_hb2(self.not_null_agent_context.conv_id)
            except Exception:
                pass

            # Tier 3.1: emit act_end 事件到 event log（每个工具一次）
            try:
                from gyra.agent.core.event_log import emit_act_end
                _conv_id = self.not_null_agent_context.conv_id
                _msg_id = message.message_id
                for (real_action, _), result in zip(tasks, results):
                    _tool_name = getattr(real_action, "name", None) or "unknown"
                    _success = not isinstance(result, Exception)
                    _summary = ""
                    if _success and hasattr(result, "content"):
                        _summary = str(result.content or "")[:200]
                    elif isinstance(result, Exception):
                        _summary = str(result)[:200]
                    emit_act_end(
                        conv_id=_conv_id,
                        tool_name=_tool_name,
                        success=_success,
                        message_id=_msg_id,
                        result_summary=_summary,
                    )
            except Exception:
                pass

            # 处理执行结果
            for (real_action, _), result in zip(tasks, results):
                # 获取工具名称（用于失败追踪）
                tool_name_for_tracking = None

                if isinstance(result, Exception):
                    logger.exception(f"Action execution failed: {result}")
                    # 从 action 中提取工具名称和参数
                    tool_name_for_tracking = None
                    tool_params = None

                    action_input = getattr(real_action, "action_input", None)
                    if action_input and hasattr(action_input, "tool_name"):
                        tool_name_for_tracking = action_input.tool_name
                        # 提取参数
                        if hasattr(action_input, "__dict__"):
                            tool_params = {
                                k: v
                                for k, v in action_input.__dict__.items()
                                if k != "tool_name" and not k.startswith("_")
                            }
                    else:
                        tool_name_for_tracking = real_action.name

                    # 检查工具失败次数
                    should_stop = self._check_and_record_tool_failure(
                        tool_name_for_tracking, error=str(result), params=tool_params
                    )

                    # 获取失败追踪器用于格式化消息
                    tracker = self._get_failure_tracker()
                    failure_count = tracker.get_failure_count(tool_name_for_tracking)

                    # 创建完整的失败 ActionOutput
                    # 前3次只提醒，不终止
                    failure_msg = tracker.format_failure_message(
                        tool_name_for_tracking, include_count=False
                    )
                    failed_output = ActionOutput(
                        content=failure_msg,
                        name=real_action.name,
                        action=tool_name_for_tracking,
                        action_name=tool_name_for_tracking,
                        is_exe_success=False,
                        state=Status.FAILED.value,
                        have_retry=not should_stop,
                    )

                    if should_stop:
                        # 5次以上终止，显示完整信息
                        failed_output.content = tracker.format_failure_message(
                            tool_name_for_tracking, include_count=True
                        )
                        failed_output.view = f"❌ **工具执行失败**\n\n{failed_output.content}"

                    act_outs.append(failed_output)

                    # 失败也要记录到 WorkLog（确保消息列表中有对应的 tool result）
                    if isinstance(real_action, (FunctionTool, ToolAction)):
                        tc_id_fail = getattr(real_action, "action_uid", None)
                        await self._record_action_to_work_log(
                            tool_name_for_tracking, {}, failed_output,
                            tool_call_id=tc_id_fail,
                        )
                else:
                    if result:
                        # 提取工具信息
                        tool_name = result.action or real_action.name
                        tool_args = {}

                        # 从 action 中获取参数
                        if hasattr(real_action, "execute_params"):
                            tool_args = getattr(real_action, "execute_params", {})

                        logger.info(
                            f"🎯 Tool executed: {tool_name}, success={result.is_exe_success if hasattr(result, 'is_exe_success') else 'unknown'}"
                        )


                        # 记录系统事件
                        if self._system_event_manager:
                            event_type = (
                                SystemEventType.ACTION_COMPLETE
                                if result.is_exe_success
                                else SystemEventType.ACTION_FAILED
                            )
                            self._system_event_manager.add_event(
                                event_type=event_type,
                                title=f"{tool_name} {'完成' if result.is_exe_success else '失败'}",
                            )

                        # 记录到 PhaseManager
                        self.record_phase_action(tool_name, result.is_exe_success)

                        # 工具执行成功或失败时，重置该工具的连续失败计数
                        if result.is_exe_success:
                            self._reset_tool_failure_count(tool_name)
                        else:
                            # 工具执行失败（非异常），也记录失败次数
                            should_stop = self._check_and_record_tool_failure(
                                tool_name,
                                error=result.content if hasattr(result, "content") else None,
                                params=tool_args if tool_args else None,
                            )
                            if should_stop:
                                # 5次以上终止，显示完整信息
                                tracker = self._get_failure_tracker()
                                result.content = tracker.format_failure_message(
                                    tool_name, include_count=True
                                )
                                result.view = f"❌ **工具执行失败**\n\n{result.content}"

                        # ========== 集成：记录到 WorkLog ==========
                        # 重要：只有真正的工具调用才应该记录到 WorkLog
                        # 真正的工具包括两类：
                        # 1. FunctionTool 的 Action 子类：AgentStart, KnowledgeSearch 等
                        # 2. ToolAction 的子类：执行外部工具的基础 Action
                        # BlankAction 不是工具，它只是 LLM 返回纯文本时的占位 Action
                        # 记录非工具会导致生成假的 tool_calls 消息，引发 OpenAI API 错误
                        if isinstance(real_action, (FunctionTool, ToolAction)):
                            # WAITING 状态区分两种场景：
                            # 1. 工具授权 WAITING：工具尚未执行，等待用户授权 → 不记录 work_log
                            # 2. ask_user WAITING：工具已执行（问题已推送给用户），等待用户回复 → 需要记录
                            is_waiting = getattr(result, "state", None) == Status.WAITING.value
                            ask_type = getattr(result, "ask_type", None)
                            # 工具授权待确认(ask_type=before_action)：工具尚未执行，不记 work_log，
                            # 恢复时重新执行（已授权则放行）。ask_user(after_action)则照常记录复用。
                            is_auth_pending = is_waiting and ask_type == "before_action"
                            if is_auth_pending:
                                logger.info(
                                    f"📝 Skipping WorkLog for {tool_name} (WAITING for authorization)"
                                )
                            else:
                                tc_id = getattr(real_action, "action_uid", None) or getattr(result, "action_id", None)
                                assistant_content = message.content if message else None
                                await self._record_action_to_work_log(
                                    tool_name, tool_args, result,
                                    tool_call_id=tc_id,
                                    assistant_content=assistant_content,
                                )
                        else:
                            logger.info(
                                f"📝 Skipping WorkLog record for {real_action.__class__.__name__} (not a tool)"
                            )

                        # ========== 异步任务完成 resume 的 BlankAction 兜底 ==========
                        # LLM 对本轮完成通知只返回占位文本（BlankAction 无工具调用）时，
                        # 取消 terminate，让 loop 继续并注入引导，强制把异步结果处理成最终交付物，
                        # 否则主对话会在子任务/媒体任务都完成后直接 complete，看不到继续输出。
                        # 用计数器兜底，避免 LLM 反复返回占位文本导致死循环。
                        #
                        # 仅当 LLM 没有产出实质内容（空或极短占位，如"收到，继续"）时才强制
                        # 续推；若已产出实质最终答案（长文本），说明本轮已有交付物，应直接
                        # terminate，否则会把同一段最终答案重复输出多遍（1668/1669/1670）。
                        _resume_content = (getattr(result, "content", "") or "").strip()
                        if (
                            self._async_resume_active
                            and getattr(result, "action", None) == "blank"
                            and getattr(result, "terminate", False)
                            and len(_resume_content) < 50
                            and self._async_resume_force_count
                            < self._async_resume_force_limit
                        ):
                            result.terminate = False
                            self._async_resume_force_count += 1
                            logger.info(
                                f"[ReActMasterAgent] async-resume round returned BlankAction; "
                                f"forcing continuation ({self._async_resume_force_count}/"
                                f"{self._async_resume_force_limit}) instead of terminate"
                            )

                        # ========== 输出超长截断(finish_reason=length)的 BlankAction 兜底 ==========
                        # 模型单次输出达到 max_new_tokens 被截断(无工具调用)时，默认 terminate
                        # 会把截断的半截结果当最终答案交付。改为强制续跑(同异步 resume 模式)，
                        # 并注入"用 Write/Edit 分段写文件"引导，让模型把超长结果分块落盘。
                        # 按用户消息维度计数兜底，避免死循环。必须在 terminate 收尾逻辑之前翻转，
                        # 否则交付/完成钩子已执行，续跑就失去意义。
                        if (
                            getattr(kwargs.get("agent_llm_out"), "finish_reason", None)
                            == "length"
                            and getattr(result, "action", None) == "blank"
                            and getattr(result, "terminate", False)
                            and self._length_force_count < self._length_force_limit
                        ):
                            result.terminate = False
                            self._length_force_count += 1
                            logger.warning(
                                f"[ReActMasterAgent] LLM output truncated by max_new_tokens "
                                f"(finish_reason=length); forcing continuation "
                                f"({self._length_force_count}/{self._length_force_limit}) "
                                f"to write result to file in chunks instead of terminating"
                            )

                        # ========== 集成：判断是否需要自动生成报告 ==========
                        # 如果是 terminate action 且启用了自动报告
                        if (
                            self._is_terminate_action(result)
                            and self.report_auto_generate
                        ):
                            self.set_phase("reporting", "任务完成，生成报告")

                        # 如果是terminate action，附加交付文件
                        # 仅真正任务终止(terminate 且非 ask_user/授权等待)才走完成逻辑：
                        # ask_user/工具授权等待虽终止 loop，但对话进入 WAITING，不应生成报告/置 complete。
                        if (
                            isinstance(result, ActionOutput)
                            and result.terminate
                            and not getattr(result, "ask_user", False)
                        ):
                            result = await self._attach_delivery_files(result)

                            # ========== 集成：自动生成报告 ==========
                            if self.report_auto_generate:
                                try:
                                    report_content = await self.generate_report(
                                        report_type=self.report_default_type,
                                        report_format=self.report_default_format,
                                        save_to_file=True,
                                    )
                                    if report_content:
                                        if result.extra is None:
                                            result.extra = {}
                                        result.extra["report"] = report_content
                                        if result.view:
                                            result.view += f"\n\n---\n## 📋 Task Report\n\n{report_content[:2000]}"
                                        else:
                                            result.view = f"## 📋 Task Report\n\n{report_content[:2000]}"
                                        logger.info(
                                            f"Auto-generated report attached to result"
                                        )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to auto-generate report: {e}"
                                    )

                            # 切换到完成阶段
                            self.set_phase("complete", "任务全部完成")

                            # Layer 4: 完成当前对话轮次
                            try:
                                pipeline = await self._ensure_compaction_pipeline()
                                if pipeline:
                                    ai_response = result.view or result.content or ""
                                    await pipeline.complete_conversation_round(
                                        ai_response=ai_response,
                                        ai_thinking=result.content or "",
                                    )
                                    logger.info("Layer 4: Completed conversation round")
                            except Exception as e:
                                logger.warning(
                                    f"Layer 4: Failed to complete conversation round: {e}"
                                )

                            # 统一 Hook：触发 conversation_complete（fire-and-forget）
                            try:
                                if (
                                    self.memory
                                    and self.memory.gpts_memory
                                    and self.not_null_agent_context
                                ):
                                    # 拉取对话历史给 tier3 curate_agent。
                                    # curate_agent 读 extra.conversation_history
                                    # 重建 turns 做兜底 tier2 reflect，并喂给
                                    # curate_session；不传则两者都是 0ms no-op。
                                    conv_id = self.not_null_agent_context.conv_id
                                    conversation_history: list = []
                                    try:
                                        msgs = await self.memory.gpts_memory.get_messages(conv_id)
                                        for m in msgs:
                                            content = m.content
                                            if not isinstance(content, str):
                                                content = str(content) if content else ""
                                            conversation_history.append({
                                                "role": m.role or "",
                                                "content": content,
                                            })
                                    except Exception as hist_e:  # noqa: BLE001
                                        logger.debug(
                                            f"[ReActMasterAgent] fetch conversation_history failed: {hist_e}"
                                        )
                                    await self.memory.gpts_memory.trigger_hook(
                                        conv_id,
                                        "conversation_complete",
                                        build_conversation_complete_context(
                                            agent_name=self.name,
                                            agent_role=getattr(self, "role", None),
                                            session_id=getattr(
                                                self.not_null_agent_context,
                                                "conv_session_id",
                                                None,
                                            ),
                                            app_code=getattr(
                                                self.not_null_agent_context,
                                                "gpts_app_code",
                                                None,
                                            ),
                                            final_answer=result.view
                                            or result.content
                                            or "",
                                            success=bool(result.is_exe_success),
                                            extra={
                                                "conversation_history": conversation_history,
                                            },
                                        ),
                                    )
                            except Exception as _hook_err:  # noqa: BLE001
                                logger.debug(
                                    f"[ReActMasterAgent] conversation_complete hook skipped: {_hook_err}"
                                )

                        act_outs.append(result)
                    else:
                        logger.warning(
                            f"⚠️ Tool execution returned None/empty result for action: {real_action.name}"
                        )

                await self.push_context_event(
                    EventType.AfterAction,
                    ActionPayload(action_output=result),
                    await self.task_id_by_received_message(received_message),
                )

            # 只在BlankAction不终止时才注入提醒（避免简单对话进入死循环）
            if has_blank_action and act_outs:
                # 检查BlankAction是否应该终止（terminate=True表示应该结束任务）
                blank_action_output = act_outs[0]

                # 输出超长截断(length)时，强制续跑已在循环内完成（见上方 BlankAction 兜底）；
                # 这里按 finish_reason 选择注入"分段用工具写文件"引导而非通用无工具提醒。
                _length_out = kwargs.get("agent_llm_out")
                _length_fr = getattr(_length_out, "finish_reason", None)
                if not blank_action_output.terminate:
                    if _length_fr == "length":
                        await self._inject_length_reminder(
                            blank_action_output, message.message_id, _length_out
                        )
                    else:
                        await self._inject_no_tool_call_reminder(
                            blank_action_output, message.message_id
                        )

        return act_outs

    async def _inject_no_tool_call_reminder(
        self, action_output: ActionOutput, message_id: str
    ):
        """
        当没有工具调用时，注入系统提醒消息，引导继续推进任务

        Args:
            action_output: 当前执行的 ActionOutput
            message_id: 关联的消息ID
        """
        from gyra.agent.core.memory.gpts.agent_system_message import (
            AgentSystemMessage,
            AgentPhase,
            SystemMessageType,
        )

        if not self.not_null_agent_context:
            return

        reminder_content = """【系统提醒】你没有调用任何工具来推进任务。

请遵循以下原则继续执行：
1. **必须使用工具**：调用合适的工具来完成任务，不能只输出文本
2. **循环只能通过 terminate 工具结束**：如果你想结束任务，请调用 terminate 工具
3. **推进任务**：根据当前任务目标，选择下一步操作

可用工具包括：
- 信息获取：read_file, search, grep 等
- 任务执行：调用相关工具执行具体操作
- 任务结束：terminate（仅在任务完成时使用）

请立即调用工具继续执行任务！"""

        try:
            system_message = AgentSystemMessage.build(
                agent_context=self.agent_context,
                agent=self,
                type=SystemMessageType.STATUS,
                phase=AgentPhase.ACTION_RUN,
                content=reminder_content,
                final_status=Status.RUNNING,
                reply_message_id=message_id,
            )

            if self.memory and self.memory.gpts_memory:
                await self.memory.gpts_memory.append_system_message(system_message)
                logger.info(
                    "✅ Injected no-tool-call reminder to guide task continuation"
                )
        except Exception as e:
            logger.warning(f"Failed to inject no-tool-call reminder: {e}")

    async def _inject_length_reminder(
        self, action_output: ActionOutput, message_id: str, llm_out
    ):
        """
        单次输出超出 max_new_tokens 被截断(finish_reason=length)时的续跑引导。

        模型在一条消息里直接输出超长结果会被截断；这里提示它改用工具分段写文件，
        避免截断的半截内容被当成最终答案交付。
        """
        from gyra.agent.core.memory.gpts.agent_system_message import (
            AgentSystemMessage,
            AgentPhase,
            SystemMessageType,
        )

        if not self.not_null_agent_context:
            return

        # 拿到本次输出的截断上限，用于在提醒里给模型一个具体的量级参考
        try:
            _cap = getattr(
                self.not_null_agent_context, "max_new_tokens", DEFAULT_MAX_NEW_TOKENS
            )
        except Exception:  # noqa: BLE001
            _cap = DEFAULT_MAX_NEW_TOKENS

        reminder_content = f"""【系统提醒】你上一条回复因超过模型单次最大输出长度（约 {_cap} tokens）而被截断，未能产出完整结果。

请不要再在消息文本里一次性输出长内容，改用工具分段完成：
1. 用 Write 工具把完整结果写入文件（可分多次 Write 拼出完整内容）
2. 若文件已存在，用 Edit 工具分块追加，不要在单个工具参数里塞入超长内容
3. 大段 HTML / 代码 / 报告请拆成多段，逐段用 Write / Edit 落盘
4. 全部写完后用 Read 确认内容完整、再调用交付工具结束任务"""

        try:
            system_message = AgentSystemMessage.build(
                agent_context=self.agent_context,
                agent=self,
                type=SystemMessageType.STATUS,
                phase=AgentPhase.ACTION_RUN,
                content=reminder_content,
                final_status=Status.RUNNING,
                reply_message_id=message_id,
            )

            if self.memory and self.memory.gpts_memory:
                await self.memory.gpts_memory.append_system_message(system_message)
                logger.info(
                    "✅ Injected output-length-truncation reminder to continue "
                    "writing result in chunks via tools"
                )
        except Exception as e:
            logger.warning(f"Failed to inject length reminder: {e}")

    async def _attach_delivery_files(
        self, action_out: "ActionOutput"
    ) -> "ActionOutput":
        """为 action 附加交付文件.

        从AgentFileSystem收集所有结论文件和交付物文件，
        附加到ActionOutput的output_files字段中。
        """
        try:
            # 确保AgentFileSystem已初始化
            afs = await self._ensure_agent_file_system()
            if not afs:
                logger.warning("AgentFileSystem not available, skip file collection")
                return action_out

            # 收集交付文件
            delivery_files = await afs.collect_delivery_files()

            if delivery_files:
                # 附加到ActionOutput
                action_out.output_files = delivery_files
                logger.info(f"Attached {len(delivery_files)} files to terminate action")
                # 暂存到 agent_context.extra，让 base_agent 的 turn_complete
                # 钩子把交付信息塞进 event.extra.delivery_files —— tier1
                # memory_write_turn_function 会把它追加到 per-turn verbat
                # content，跟 user/assistant 文本写在同一个文件里。
                try:
                    ctx = self.not_null_agent_context
                    if ctx.extra is None:
                        ctx.extra = {}
                    ctx.extra["delivery_files"] = delivery_files
                except Exception as stash_e:
                    logger.warning(
                        f"Failed to stash delivery_files on agent_context: {stash_e}"
                    )

        except Exception as e:
            logger.error(f"Failed to attach delivery files: {e}")

        return action_out

    def _check_and_record_tool_failure(
        self, tool_name: str, error: Optional[str] = None, params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        记录工具失败并检查是否应停止执行

        PR 7: 委托给 ToolFailureTracker，拿到 cooldown + record_success 能力。
        返回 True 表示工具已被熔断（连续失败超阈值）。
        """
        if not tool_name:
            return False
        tracker = self._get_failure_tracker()
        tracker.record_failure(tool_name, error or "tool execution failed", params=params)
        # 同步旧字段（向后兼容 snapshot 读取）
        self._tool_failure_counts[tool_name] = tracker.get_failure_count(tool_name)
        return tracker.is_disabled(tool_name)

    def _is_tool_blocked(self, tool_name: str) -> bool:
        """
        检查工具是否已被禁止执行（失败次数超过阈值且在 cooldown 期内）。

        PR 7: 委托给 ToolFailureTracker.is_disabled（含 cooldown 过期 lazy 清理）。
        """
        if not tool_name:
            return False
        tracker = self._get_failure_tracker()
        blocked = tracker.is_disabled(tool_name)
        if not blocked:
            # cooldown 过期后 lazy 清理，同步旧字段
            self._tool_failure_counts.pop(tool_name, None)
        return blocked

    def _reset_tool_failure_count(self, tool_name: str = None):
        """
        重置工具失败计数。

        PR 7: tool_name 指定时调 tracker.record_success（清空 + 解除熔断）；
        tool_name=None 时调 tracker.reset()（清空所有）。
        """
        tracker = self._get_failure_tracker()
        if tool_name is None:
            tracker.reset()
            self._tool_failure_counts.clear()
        else:
            tracker.record_success(tool_name)
            self._tool_failure_counts.pop(tool_name, None)

    def _get_failure_tracker(self):
        """lazy 初始化 ToolFailureTracker（per conv_id）。"""
        if self._failure_tracker is None:
            from gyra.agent.core.tool_failure_tracker import ToolFailureTracker
            conv_id = (
                self.not_null_agent_context.conv_id
                if self.not_null_agent_context
                else "default"
            )
            self._failure_tracker = ToolFailureTracker(
                conv_id=conv_id,
                max_consecutive_failures=self._max_tool_failure_count,
                cooldown_seconds=300,  # PR 7 新增：5 分钟自动解除熔断
            )
        return self._failure_tracker

    def get_stats(self) -> Dict[str, Any]:
        """获取 Agent 运行统计信息"""
        stats = {
            "tool_call_count": self._tool_call_count,
            "compaction_count": self._compaction_count,
            "prune_count": self._prune_count,
            "tool_failure_counts": dict(self._tool_failure_counts),
        }

        # PR 7: 加 ToolFailureTracker snapshot（含 cooldown 状态）
        if self._failure_tracker is not None:
            stats["failure_tracker"] = self._failure_tracker.snapshot()

        if self._doom_loop_detector:
            stats["doom_loop"] = self._doom_loop_detector.get_stats()

        if getattr(self, "_session_compaction", None):
            stats["compaction"] = self._session_compaction.get_stats()

        if getattr(self, "_history_pruner", None):
            stats["prune"] = self._history_pruner.get_stats()

        return stats

    def reset_stats(self):
        """重置统计信息"""
        self._tool_call_count = 0
        self._compaction_count = 0
        self._prune_count = 0
        self._tool_failure_counts.clear()

        # PR 7: 同步重置 ToolFailureTracker
        if self._failure_tracker is not None:
            self._failure_tracker.reset()

        if self._doom_loop_detector:
            self._doom_loop_detector.reset()

        if getattr(self, "_session_compaction", None):
            self._session_compaction.clear_history()

        if getattr(self, "_history_pruner", None):
            self._history_pruner._prune_history.clear()

    async def save_conclusion_file(
        self,
        content: Any,
        file_name: str,
        extension: str = "md",
        task_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        保存结论文件并自动推送d-attach组件到前端

        Args:
            content: 文件内容
            file_name: 文件名
            extension: 文件扩展名
            task_id: 关联任务ID

        Returns:
            文件元数据字典，失败返回None
        """
        afs = await self._ensure_agent_file_system()
        if not afs:
            logger.warning("AgentFileSystem not available, cannot save conclusion file")
            return None

        try:
            from gyra.agent.core.memory.gpts import AgentFileMetadata

            file_metadata = await afs.save_conclusion(
                data=content,
                file_name=file_name,
                extension=extension,
                created_by=self.name,
                task_id=task_id,
            )
            logger.info(f"Saved conclusion file: {file_name}")
            return file_metadata.to_attach_content()
        except Exception as e:
            logger.error(f"Failed to save conclusion file: {e}")
            return None

    async def get_agent_files(
        self,
        file_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取当前Agent的所有文件

        Args:
            file_type: 文件类型过滤

        Returns:
            文件信息列表
        """
        afs = await self._ensure_agent_file_system()
        if not afs:
            return []

        try:
            files = await afs.list_files(file_type=file_type)
            return files
        except Exception as e:
            logger.error(f"Failed to list agent files: {e}")
            return []

    async def push_all_conclusions(self):
        """推送所有结论文件到前端"""
        afs = await self._ensure_agent_file_system()
        if not afs:
            return

        try:
            await afs.push_conclusion_files()
            logger.info("Pushed all conclusion files")
        except Exception as e:
            logger.error(f"Failed to push conclusion files: {e}")

    async def sync_file_workspace(self):
        """同步文件工作区（用于会话恢复）"""
        afs = await self._ensure_agent_file_system()
        if not afs:
            return

        try:
            await afs.sync_workspace()
            logger.info("File workspace synced")
        except Exception as e:
            logger.error(f"Failed to sync file workspace: {e}")

    async def compress_session(self, force: bool = False) -> Optional[Any]:
        """手动触发会话压缩（已废弃）。

        历史的 SessionCompaction 已被 ContextEngine 取代，压缩在每个 ReAct step
        由引擎自动按需进行（cold 重整 + 持久化复用），无需手动触发。保留此方法
        仅为向后兼容，直接返回 None。
        """
        logger.info(
            "[compress_session] 已废弃：压缩由 ContextEngine 自动管理，无需手动触发"
        )
        return None

    def record_phase_action(self, tool_name: str, success: bool):
        """记录到阶段管理器（在工具执行后调用）"""
        if (
            self.enable_phase_management
            and hasattr(self, "_phase_manager")
            and self._phase_manager
        ):
            self._phase_manager.record_action(tool_name, success)

    def register_variables(self):
        """子类通过重写此方法注册变量"""
        logger.info(f"register_variables {self.role}")
        super().register_variables()

        @self._vm.register("available_agents", "可用Agents资源")
        async def var_available_agents(instance):
            logger.info("注入agent资源")
            prompts = ""
            if self.capability_pack:
                for cap in self.capability_pack.get_all("app"):
                    prompts += f"- <agent><code>{cap.app_code}</code><name>{cap.app_name}</name><description>{cap.app_desc}</description>\n</agent>\n"
            return prompts

        @self._vm.register("available_knowledges", "可用知识库")
        async def var_available_knowledges(instance):
            logger.info("注入knowledges资源")

            prompts = ""
            if self.capability_pack:
                for cap in self.capability_pack.get_all("knowledge"):
                    spaces = getattr(cap, "_spaces", None) or []
                    if not spaces:
                        logger.error("当前知识资源无法使用!knowledge")
                        continue
                    for sp in spaces:
                        prompts += f"- <knowledge><id>{sp.get('knowledge_id','')}</id><name>{sp.get('name','')}</name><description>{sp.get('desc','')}</description></knowledge>\n"
            return prompts

        @self._vm.register("available_skills", "可用技能")
        async def var_skills(instance):
            logger.info("注入技能资源")

            # Sandbox mode: skill_dir comes from the sandbox client
            # (e.g. /mnt/gyra/skills set in [sandbox].skill_dir of the toml).
            # Local mode: default to DATA_DIR/skill (pilot/data/skill).
            sandbox_skill_dir: Optional[str] = None
            sandbox_enabled = False
            if instance and getattr(instance, "sandbox_manager", None):
                sb_client = getattr(instance.sandbox_manager, "client", None)
                if sb_client:
                    sandbox_skill_dir = getattr(sb_client, "skill_dir", None)
                    sandbox_enabled = True

            local_skill_dir = os.path.join(DATA_DIR, "skill")
            logger.info(
                f"var_skills: sandbox_enabled={sandbox_enabled}, "
                f"sandbox_skill_dir={sandbox_skill_dir!r}, "
                f"local_skill_dir={local_skill_dir!r}"
            )

            prompts = ""
            # Add sandbox environment info if sandbox is enabled
            if sandbox_enabled and sandbox_skill_dir:
                prompts += (
                    "以下技能存储在沙箱环境中，路径为沙箱内的绝对路径。\n"
                    f"技能目录：{sandbox_skill_dir}\n"
                    "使用方式：使用 `Skill` 工具加载技能的 SKILL.md 指令，使用 `bash` 工具执行技能目录中的脚本(指定 cwd=技能目录)。\n\n"
                )

            if self.capability_pack:
                for cap in self.capability_pack.get_all("skill"):
                    for sk in getattr(cap, "_skills", None) or []:
                        branch = sk.get("branch") or "master"
                        debug_info = sk.get("debug_info")
                        if debug_info and debug_info.get("is_debug"):
                            branch = debug_info.get("branch")

                        skill_code = sk.get("skill_code") or ""
                        if not skill_code and sk.get("path"):
                            skill_code = os.path.basename(sk["path"])

                        # Determine skill path based on sandbox mode
                        # If sandbox is enabled, use sandbox_skill_dir + skill_code (absolute path in sandbox)
                        # If sandbox is disabled, use local_skill_dir + skill_code (absolute path locally)
                        if sandbox_enabled and sandbox_skill_dir and skill_code:
                            skill_path = os.path.join(sandbox_skill_dir, skill_code)
                        elif skill_code:
                            skill_path = os.path.join(local_skill_dir, skill_code)
                        else:
                            skill_path = sk.get("path")

                        prompts += (
                            f"- <skill>"
                            f"<name>{sk.get('name','')}</name>"
                            f"<description>{sk.get('description','')}</description>"
                            f"<path>{skill_path}</path>"
                            f"<branch>{branch}</branch>"
                            f"<load_command>Skill(skill_name=\"{skill_code}\")</load_command>"
                            f"\n</skill>\n"
                        )

            return prompts

        @self._vm.register("project_context", "项目生态上下文(Claude Code / Cursor)")
        async def var_project_context(instance):
            """注入工程目录生态配置：CLAUDE.md / AGENTS.md 项目记忆 + 项目技能列表。

            配置来源：app.ext_config.project_ecosystem = {project_dir, type}。
            探测结果按 (project_dir, type) 缓存，仅首轮做 FS 扫描。无配置/无内容
            返回空串（模板层 `is defined` 保护，不影响其它资源渲染）。
            """
            return await _build_project_context(instance)

        @self._vm.register("other_resources", "其他资源")
        async def var_other_resources(instance):
            logger.info("注入其他资源")

            # Phase D:从 capability_pack 渲染。v1 此处对 DBResource.get_prompt 做
            # schema I/O;v2 用 DBCapability 基本信息(无 I/O,facade declare 同款
            # 文本),schema 明细由 declare 的 DataRequirement 占位回填。
            prompts = ""
            if self.capability_pack:
                for cap in self.capability_pack.get_all("db"):
                    try:
                        basic_info = cap._build_basic_info()
                        if basic_info:
                            prompts += (
                                f"- <database><name>{cap.db_name}</name>"
                                f"<prompt>{basic_info}</prompt>\n</database>\n"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to render database resource {getattr(cap, 'db_name', '?')}: {e}"
                        )
                        continue
            return prompts

        @self._vm.register("sandbox", "沙箱配置")
        async def var_sandbox(instance):
            logger.info("注入沙箱配置信息，如果存在沙箱客户端即默认使用沙箱")
            if instance and instance.sandbox_manager:
                if instance.sandbox_manager.initialized == False:
                    logger.warning(
                        f"沙箱尚未准备完成!({instance.sandbox_manager.client.provider}-{instance.sandbox_manager.client.sandbox_id})"
                    )
                sandbox_client: SandboxBase = instance.sandbox_manager.client

                from gyra.agent.core.sandbox.prompt import (
                    AGENT_SKILL_SYSTEM_PROMPT,
                    SANDBOX_ENV_PROMPT,
                    SANDBOX_TOOL_BOUNDARIES,
                    sandbox_prompt,
                )

                env_param = {
                    "sandbox": {
                        "work_dir": sandbox_client.work_dir,
                        "skill_dir": sandbox_client.skill_dir,
                        "system_info": _get_sandbox_system_info(sandbox_client),
                    }
                }
                skill_param = {"sandbox": {"agent_skill_dir": sandbox_client.skill_dir}}

                param = {
                    "sandbox": {
                        "tool_boundaries": render(SANDBOX_TOOL_BOUNDARIES, {}),
                        "execution_env": render(SANDBOX_ENV_PROMPT, env_param),
                        "agent_skill_system": render(
                            AGENT_SKILL_SYSTEM_PROMPT, skill_param
                        )
                        if sandbox_client.enable_skill
                        else "",
                        "use_agent_skill": sandbox_client.enable_skill,
                    }
                }

                return {
                    "enable": True if sandbox_client else False,
                    "prompt": render(sandbox_prompt, param),
                }
            else:
                return {"enable": False, "prompt": ""}

        @self._vm.register("input", "用户输入")
        def var_input(received_message):
            if received_message:
                return received_message.content
            return ""

        @self._vm.register("memory", "工作日志")
        async def var_memory(instance):
            """获取Layer 4压缩的历史对话记录作为 memory 变量

            四层架构设计：
            - Layer 1-3: 处理当前轮次的工具输出（截断、修剪、压缩）
            - Layer 4: 处理跨轮次对话历史的压缩

            memory 变量现在包含：
            - 历史轮次的压缩摘要（用户提问 + WorkLog摘要 + 答案摘要）
            - 不包含当前轮次的详细工具执行（通过原生Function Call传递）

            这种设计避免了重复：
            - 历史轮次：通过 memory 变量以摘要形式提供
            - 当前轮次：通过原生 tool messages 直接传递
            """
            logger.info("var_memory: fetching Layer 4 compressed history...")
            return await instance._get_layer4_history_for_memory()

        @self._vm.register("work_log", "工作日志")
        async def var_work_log(instance):
            logger.info("var_work_log: fetching work log...")
            if not instance.enable_work_log:
                logger.info("var_work_log: work_log is disabled")
                return ""

            await instance._ensure_work_log_manager()
            if not instance._work_log_manager or not instance._work_log_initialized:
                logger.warning("var_work_log: WorkLogManager not initialized")
                return ""

            await instance._work_log_manager.initialize()
            context = await instance._work_log_manager.get_context_for_prompt(
                max_entries=50
            )
            logger.info(
                f"var_work_log: fetched work log, entries={len(instance._work_log_manager.work_log)}"
            )
            return context

        logger.info(f"register_variables end {self.role}")

    async def _get_work_log_context_for_memory(self) -> str:
        """获取工具执行记录(WorkLog)上下文，用于整合到 memory 变量"""
        if not self.enable_work_log:
            return ""

        try:
            await self._ensure_work_log_manager()
            if not self._work_log_manager or not self._work_log_initialized:
                return ""

            await self._work_log_manager.initialize()
            context = await self._work_log_manager.get_context_for_prompt(
                max_entries=50
            )
            logger.info(
                f"_get_work_log_context_for_memory: entries={len(self._work_log_manager.work_log)}"
            )
            return context
        except Exception as e:
            logger.warning(f"Failed to get work log context: {e}")
            return ""

    async def _get_layer4_history_for_memory(self) -> str:
        """获取 Layer 4 压缩的跨轮次对话历史

        四层架构中的 Layer 4：处理多轮对话历史的压缩
        - 返回历史轮次的压缩摘要
        - 当前轮次的工具执行通过原生 Function Call 传递
        """
        try:
            pipeline = await self._ensure_compaction_pipeline()
            if not pipeline:
                logger.debug(
                    "Layer 4: Pipeline not available, falling back to work log"
                )
                return await self._get_work_log_context_for_memory()

            # 获取 Layer 4 压缩的历史记录
            history = await pipeline.get_layer4_history_for_prompt()
            if history:
                logger.info(
                    f"Layer 4: Retrieved compressed history ({len(history)} chars)"
                )
                return history
            else:
                logger.debug("Layer 4: No compressed history available")
                return ""
        except Exception as e:
            logger.warning(f"Layer 4: Failed to get compressed history: {e}")
            # 降级到 WorkLog
            return await self._get_work_log_context_for_memory()

    async def _ensure_work_log_manager(self):
        """确保 WorkLog 管理器已初始化

        存储策略：
        1. 优先使用 self.memory.gpts_memory 作为 WorkLogStorage（推荐）
        2. 回退使用 AgentFileSystem（向后兼容）
        """
        if not self.enable_work_log:
            logger.debug("_ensure_work_log_manager: work_log is disabled")
            return

        # 添加锁保护防止并发初始化
        if not hasattr(self, "_work_log_initialization_lock"):
            self._work_log_initialization_lock = asyncio.Lock()

        async with self._work_log_initialization_lock:
            # 双重检查
            if self._work_log_manager and self._work_log_initialized:
                logger.info(
                    "WorkLogManager already initialized, skipping re-initialization"
                )
                return

            logger.info("Initializing WorkLogManager...")

            conv_id = "default"
            session_id = "default"

            if self.not_null_agent_context:
                conv_id = self.not_null_agent_context.conv_id or "default"
                session_id = self.not_null_agent_context.conv_session_id or conv_id

            logger.info(
                f"WorkLogManager session info: conv_id={conv_id}, session_id={session_id}"
            )

            # 优先使用 gpts_memory 作为 WorkLogStorage
            work_log_storage = None
            afs = None
            if (
                self.memory
                and hasattr(self.memory, "gpts_memory")
                and self.memory.gpts_memory
            ):
                # GptsMemory 实现了 WorkLogStorage 接口
                work_log_storage = self.memory.gpts_memory  # type: ignore[assignment]
                logger.info("Using gpts_memory as WorkLogStorage (recommended)")

            # 回退到 AgentFileSystem
            if not work_log_storage:
                afs = await self._ensure_agent_file_system()
                if afs:
                    logger.info("Using AgentFileSystem for WorkLog (fallback mode)")

            self._work_log_manager = await create_work_log_manager(
                agent_id=self.name,
                session_id=session_id,
                agent_file_system=afs,
                work_log_storage=work_log_storage,
                context_window_tokens=self.work_log_context_window,
                compression_threshold_ratio=self.work_log_compression_ratio,
            )

            self._work_log_initialized = True
            logger.info(
                f"WorkLogManager initialized: agent_id={self.name}, session_id={session_id}, "
                f"storage_mode={self._work_log_manager.storage_mode}"
            )

            await self._work_log_manager.initialize()
            logger.info(
                f"WorkLogManager loaded: {len(self._work_log_manager.work_log)} entries"
            )

    @staticmethod
    def _build_engine_config():
        """Build ContextEngine config with env-var overrides (defaults in CompressionConfig).

        Env vars:
        - GYRA_COMPRESS_THRESHOLD_RATIO (float, default 0.92): token ratio to trigger compression
        - GYRA_COMPRESS_RETAIN_RATIO (float, default 0.30): retained-zone fraction of window
        - GYRA_COMPRESS_MIN_INTERVAL_TURNS (int, default 3): min turns between compressions (anti-thrash)
        - GYRA_COMPRESS_RETAIN_TOOL_RESULT_MAX_LENGTH (int, default 8000): retained tool result truncation
        - GYRA_COMPRESS_MAX_SUMMARY_CHARS (int, default 1200): max summary chars
        - GYRA_HISTORY_BUDGET_RATIO (float, default 0.85): history budget fraction of context_window
        """
        import os
        from .context_engine import CompressionConfig, EngineConfig

        def _f(name, default):
            try:
                v = os.getenv(name)
                return float(v) if v is not None else default
            except (TypeError, ValueError):
                return default

        def _i(name, default):
            try:
                v = os.getenv(name)
                return int(v) if v is not None else default
            except (TypeError, ValueError):
                return default

        return EngineConfig(
            compression=CompressionConfig(
                threshold_ratio=_f("GYRA_COMPRESS_THRESHOLD_RATIO", 0.92),
                retain_ratio=_f("GYRA_COMPRESS_RETAIN_RATIO", 0.30),
                min_interval_turns=_i("GYRA_COMPRESS_MIN_INTERVAL_TURNS", 3),
                retain_tool_result_max_length=_i(
                    "GYRA_COMPRESS_RETAIN_TOOL_RESULT_MAX_LENGTH", 8000
                ),
                max_summary_chars=_i("GYRA_COMPRESS_MAX_SUMMARY_CHARS", 1200),
            ),
            history_budget_ratio=_f("GYRA_HISTORY_BUDGET_RATIO", 0.85),
        )

    async def _ensure_context_engine(self):
        """确保 ContextEngine 已初始化（统一上下文管理引擎）。

        一次性装配：summarize_fn 闭包 llm_client；events 对接 SystemEventManager；
        compression_persistence 对接 gpts_cold_segments（不可用时降级内存）；
        token_counter 注入 tiktoken count_tokens（真实 token 计数）。
        """
        if self._context_engine_initialized and self._context_engine:
            return self._context_engine

        if not hasattr(self, "_context_engine_init_lock"):
            self._context_engine_init_lock = asyncio.Lock()

        async with self._context_engine_init_lock:
            if self._context_engine_initialized and self._context_engine:
                return self._context_engine
            try:
                from .context_engine import ContextEngine
                from .cold_persistence import DbCompressionPersistenceAdapter
                from .engine_wiring import SystemEventAdapter, make_summarize_fn
                from gyra.agent.core.usage_metric import count_tokens

                llm_client = getattr(self, "llm_client", None)
                self._context_engine = ContextEngine(
                    config=self._build_engine_config(),
                    compression_persistence=DbCompressionPersistenceAdapter(),
                    summarize_fn=make_summarize_fn(llm_client),
                    token_counter=count_tokens,
                    events=SystemEventAdapter(self._system_event_manager),
                )
                self._context_engine_initialized = True
                logger.info("ContextEngine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to init ContextEngine: {e}", exc_info=True)
                self._context_engine = None
            return self._context_engine

    async def _compute_context_engine_messages(
        self, conv_id: str, session_id: str, context_window: int,
        current_user_content: Optional[str] = None,
    ):
        """统一上下文构建路径：从权威存储装配 → 分层 → 压缩 → 门禁。

        Returns:
            BuildOutput（含 messages / layer_tokens / cleanup_hints / guard_report）
            或 None（引擎不可用，调用方落回 fallback）。
        """
        engine = await self._ensure_context_engine()
        if engine is None:
            return None
        if not (self.memory and hasattr(self.memory, "gpts_memory")):
            return None

        gpts_memory = self.memory.gpts_memory
        # 1) 加载整个 session 的消息（按 session 存）
        messages = await gpts_memory.get_session_messages(session_id)
        if not messages:
            return None

        # 1.5) Merge current-conv cache messages: append_message is a fire-and-forget
        #      DB write, so just-appended current-turn messages (incl. ReAct tool calls)
        #      may not be in DB yet. get_messages reads cache (same source as get_work_log),
        #      filling in not-yet-persisted messages so the message view matches work_log
        #      and the assembler can bind tool results. Dedup by message_id.
        try:
            _existing_ids = {getattr(m, "message_id", None) for m in messages}
            _cache_msgs = await gpts_memory.get_messages(conv_id)
            for _m in _cache_msgs:
                _mid = getattr(_m, "message_id", None)
                if _mid and _mid not in _existing_ids:
                    messages.append(_m)
                    _existing_ids.add(_mid)
        except Exception as _e:
            logger.warning(f"[ContextEngine] merge cache messages failed: {_e}")

        # 2) 加载每个 conv 的 work_log（按 conv 存）
        conv_ids = {getattr(m, "conv_id", None) for m in messages}
        conv_ids.discard(None)
        conv_ids.add(conv_id)
        work_logs_by_conv = {}
        for cid in conv_ids:
            try:
                work_logs_by_conv[cid] = await gpts_memory.get_work_log(cid)
            except Exception as e:
                logger.warning(f"[ContextEngine] get_work_log({cid}) failed: {e}")
                work_logs_by_conv[cid] = []

        subagent_goal_id = getattr(self, "_subagent_goal_id", None)
        return await engine.build_messages(
            messages=messages,
            work_logs_by_conv=work_logs_by_conv,
            current_conv_id=conv_id,
            session_id=session_id,
            context_window=context_window,
            subagent_goal_id=subagent_goal_id,
            current_user_content=current_user_content,
        )

    async def _ensure_system_event_manager(self):
        """确保 SystemEventManager 已初始化并设置到 GptsMemory"""
        if self._system_event_manager:
            return

        conv_id = "default"
        if self.not_null_agent_context:
            conv_id = self.not_null_agent_context.conv_id or "default"

        self._system_event_manager = SystemEventManager(conv_id=conv_id)

        # 记录初始化事件
        self._system_event_manager.add_event(
            event_type=SystemEventType.AGENT_BUILD_START,
            title="初始化 Agent 环境",
            description=f"Agent: {self.name}",
        )
        self._system_event_manager.add_event(
            event_type=SystemEventType.ENVIRONMENT_READY,
            title="运行环境就绪",
        )

        # 设置到 GptsMemory
        if (
            self.memory
            and hasattr(self.memory, "gpts_memory")
            and self.memory.gpts_memory
        ):
            await self.memory.gpts_memory.init(
                conv_id=conv_id,
                event_manager=self._system_event_manager,
            )
            logger.info(
                f"[ReActMasterAgent] SystemEventManager 已设置: conv_id={conv_id[:8]}"
            )

            # 统一 Hook：根据 team_context.hook_config 装配 HookManager 并触发 conversation_start
            try:
                team_context = None
                if self.not_null_agent_context:
                    team_context = getattr(
                        self.not_null_agent_context, "team_context", None
                    )
                runtime: Dict[str, Any] = {}
                sb_manager = getattr(self, "sandbox_manager", None)
                if sb_manager is not None:
                    runtime["sandbox_client"] = getattr(sb_manager, "client", None)
                manager = await self.memory.gpts_memory.init_hook_manager(
                    conv_id=conv_id,
                    team_context=team_context,
                    runtime=runtime,
                )
                if manager is not None:
                    await self.memory.gpts_memory.trigger_hook(
                        conv_id,
                        "conversation_start",
                        {
                            "agent_name": self.name,
                            "agent_role": getattr(self, "role", None),
                            "session_id": getattr(
                                self.not_null_agent_context,
                                "conv_session_id",
                                None,
                            ),
                            "app_code": getattr(
                                self.not_null_agent_context,
                                "gpts_app_code",
                                None,
                            ),
                        },
                    )
            except Exception as _hook_err:  # noqa: BLE001
                logger.warning(
                    f"[ReActMasterAgent] HookManager init/start trigger failed: {_hook_err}"
                )

    async def _lookup_cached_tool_result(
        self,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]],
        tool_call_id: Optional[str] = None,
    ) -> Optional[ActionOutput]:
        """PR 3: step-level resume — 查 work_log 缓存复用已成功的工具结果。

        匹配优先级：
        1. tool_call_id 精确匹配（DB 不持久化此字段，仅内存 cache 命中）
        2. (tool_name, args) 元组匹配（DB 加载的 entry 走这条）

        命中条件：success=True 且 status=active（done）。失败/running 的 entry 不复用。

        Args:
            tool_name: 工具名
            tool_args: 工具参数
            tool_call_id: LLM 返回的 tool_call id（action_uid）

        Returns:
            复用的 ActionOutput，或 None 表示未命中需重跑。
        """
        if not self.memory or not self.memory.gpts_memory:
            return None
        if not self.not_null_agent_context:
            return None
        conv_id = self.not_null_agent_context.conv_id

        try:
            cache = await self.memory.gpts_memory._get_cache(conv_id)
        except Exception as e:
            logger.warning(f"[step-resume] failed to get cache for {conv_id}: {e}")
            return None
        if not cache:
            return None

        # 优先按 tool_call_id 精确匹配（仅内存 cache 有此字段）
        if tool_call_id:
            for entry in cache.work_logs:
                if (
                    entry.tool_call_id
                    and entry.tool_call_id == tool_call_id
                    and entry.tool == tool_name
                    and entry.success
                    and entry.status == WorkLogStatus.ACTIVE.value
                ):
                    return self._build_action_output_from_work_entry(entry, tool_name)

        # 回退：按 (tool_name, args) 匹配，取最后一条（最近一次成功调用）
        if tool_name:
            args_normalized = self._normalize_args(tool_args)
            matched_entry = None
            for entry in cache.work_logs:
                if entry.tool != tool_name:
                    continue
                if not entry.success:
                    continue
                if entry.status != WorkLogStatus.ACTIVE.value:
                    continue
                if args_normalized is not None:
                    entry_args = self._normalize_args(entry.args)
                    if entry_args != args_normalized:
                        continue
                matched_entry = entry  # 覆盖，最终保留最后一条
            if matched_entry:
                return self._build_action_output_from_work_entry(matched_entry, tool_name)

        return None

    @staticmethod
    def _normalize_args(args: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """规范化 args 用于稳定匹配（去掉 None 值，排序 key）。"""
        if args is None:
            return None
        if not isinstance(args, dict):
            return None
        return {k: args[k] for k in sorted(args.keys()) if args[k] is not None}

    @staticmethod
    def _build_action_output_from_work_entry(
        entry: "WorkEntry", tool_name: str
    ) -> ActionOutput:
        """从 WorkEntry 重建 ActionOutput（用于 step-resume 复用）。"""
        return ActionOutput(
            content=entry.result or "",
            name=tool_name,
            action=tool_name,
            action_name=tool_name,
            is_exe_success=True,
            state=Status.COMPLETE.value,
            have_retry=False,
            view=entry.result or "",
        )

    async def _record_action_to_work_log(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]],
        action_output: ActionOutput,
        tool_call_id: Optional[str] = None,
        assistant_content: Optional[str] = None,
    ):
        """记录操作到 WorkLog

        Args:
            tool_name: 工具名称
            args: 工具参数
            action_output: 工具执行结果
            tool_call_id: LLM 返回的 tool_call id（用于与消息列表中的 tool_calls 关联）
            assistant_content: LLM 生成的 assistant 消息内容
        """
        if not self.enable_work_log:
            return

        await self._ensure_work_log_manager()

        if not self._work_log_manager:
            logger.warning(
                "Failed to initialize WorkLogManager, skipping work log recording"
            )
            return

        tags = []
        if not action_output.is_exe_success:
            tags.append("error")
        if action_output.content and len(action_output.content) > 10000:
            tags.append("large_output")

        # 获取当前 conv_id
        conv_id = None
        if self.not_null_agent_context:
            conv_id = self.not_null_agent_context.conv_id

        try:
            entry = await self._work_log_manager.record_action(
                tool_name=tool_name,
                args=args if args is not None else {},
                action_output=action_output,
                tags=tags,
                tool_call_id=tool_call_id,
                assistant_content=assistant_content,
                conv_id=conv_id,
            )
            logger.info(
                f"Recorded work log: tool={tool_name}, tool_call_id={tool_call_id}, "
                f"conv_id={conv_id}, success={action_output.is_exe_success}, "
                f"total_entries={len(self._work_log_manager.work_log)}"
            )
        except Exception as e:
            logger.exception(f"Failed to record work log for {tool_name}: {e}")

    def _is_terminate_action(self, action_output: ActionOutput) -> bool:
        """判断是否为 terminate action"""
        if not action_output:
            return False
        if not action_output.content:
            return False

        content_lower = action_output.content.lower()
        return any(
            keyword in content_lower
            for keyword in [
                "terminate",
                "finish",
                "complete",
                "end",
                "done",
                "stop",
                "final",
            ]
        )

    def set_phase(self, phase: str, reason: str = ""):
        """手动设置阶段"""
        if self.enable_phase_management and self._phase_manager:
            phase_enum = TaskPhase(phase.lower())
            self._phase_manager.set_phase(phase_enum, reason)
            logger.info(f"Phase set to {phase}: {reason}")
        else:
            logger.warning("PhaseManager is not enabled")

    async def generate_report(
        self,
        report_type: str = "detailed",
        report_format: str = "markdown",
        save_to_file: bool = False,
    ) -> str:
        """
        生成任务报告

        Args:
            report_type: 报告类型（summary/detailed/technical/executive/progress/final）
            report_format: 报告格式（markdown/html/json/plain）
            save_to_file: 是否保存到文件系统

        Returns:
            报告内容字符串
        """
        if not self.enable_auto_report:
            logger.warning(
                "ReportGenerator is not enabled. Set enable_auto_report=True"
            )
            return ""

        await self._ensure_work_log_manager()

        if not self._work_log_manager or not self._work_log_initialized:
            logger.warning("WorkLog must be initialized for report generation")
            return ""

        report_generator = ReportGenerator(
            work_log_manager=self._work_log_manager,
            agent_id=self.name,
            task_id=self.not_null_agent_context.conv_id
            if self.not_null_agent_context
            else "unknown",
            llm_client=None,
        )

        try:
            report_type_enum = ReportType(report_type.lower())
        except ValueError:
            report_type_enum = ReportType.DETAILED

        try:
            report_format_enum = ReportFormat(report_format.lower())
        except ValueError:
            report_format_enum = ReportFormat.MARKDOWN

        report = await report_generator.generate_report(
            report_type=report_type_enum,
            report_format=report_format_enum,
        )

        if report_format_enum == ReportFormat.MARKDOWN:
            content = report.to_markdown()
        elif report_format_enum == ReportFormat.HTML:
            content = report.to_html()
        elif report_format_enum == ReportFormat.JSON:
            content = report.to_json()
        else:
            content = report.to_plain_text()

        if save_to_file:
            await self._save_report_to_file(content, report_format_enum)

        logger.info(f"Report generated: {report_type}/{report_format}")
        return content

    async def _save_report_to_file(
        self,
        content: str,
        report_format: ReportFormat,
    ):
        """保存报告到文件系统"""
        if not self._agent_file_system:
            logger.warning("AgentFileSystem not available, cannot save report to file")
            return

        import time

        timestamp = int(time.time())

        extension = {
            ReportFormat.MARKDOWN: "md",
            ReportFormat.HTML: "html",
            ReportFormat.JSON: "json",
        }.get(report_format, "md")

        report_key = f"{self.name}_report_{timestamp}"

        await self._agent_file_system.save_file(
            file_key=report_key,
            data=content,
            file_type="report",
            extension=extension,
        )

        logger.info(f"Report saved: {report_key}")

    async def _ensure_kanban_manager(self) -> Optional[KanbanManager]:
        """
        确保 Kanban 管理器已初始化（懒加载）

        Returns:
            KanbanManager 实例或 None
        """
        if not self.enable_kanban:
            return None

        if self._kanban_manager is not None and self._kanban_initialized:
            return self._kanban_manager

        if not self.not_null_agent_context:
            return None

        try:
            conv_id = self.not_null_agent_context.conv_id or "default"
            session_id = self.not_null_agent_context.conv_session_id or conv_id

            afs = await self._ensure_agent_file_system()

            kanban_storage = None
            if (
                self.memory
                and hasattr(self.memory, "gpts_memory")
                and self.memory.gpts_memory
            ):
                kanban_storage = self.memory.gpts_memory

            self._kanban_manager = await create_kanban_manager(
                agent_id=self.name,
                session_id=session_id,
                agent_file_system=afs,
                kanban_storage=kanban_storage,
                exploration_limit=self.kanban_exploration_limit,
            )

            self._kanban_initialized = True
            logger.info(
                f"KanbanManager initialized: agent_id={self.name}, session_id={session_id}, "
                f"storage_mode={self._kanban_manager.storage_mode}"
            )
            return self._kanban_manager

        except Exception as e:
            logger.warning(f"Failed to initialize KanbanManager: {e}")
            return None

    async def create_kanban(
        self, mission: str, stages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        创建看板

        Args:
            mission: 任务描述
            stages: 阶段列表，每个阶段包含:
                - stage_id: 阶段ID
                - description: 阶段描述
                - deliverable_type: 交付物类型
                - deliverable_schema: 交付物 Schema（可选）
                - depends_on: 依赖的阶段ID列表（可选）

        Returns:
            操作结果
        """
        if not self.enable_kanban:
            return {
                "status": "error",
                "message": "Kanban is not enabled. Set enable_kanban=True",
            }

        await self._ensure_kanban_manager()

        if not self._kanban_manager:
            return {"status": "error", "message": "Failed to initialize KanbanManager"}

        result = await self._kanban_manager.create_kanban(mission, stages)

        if result.get("status") == "success":
            self.set_phase("planning", "Kanban created, starting planning phase")

        return result

    async def submit_deliverable(
        self,
        stage_id: str,
        deliverable: Dict[str, Any],
        reflection: str = "",
    ) -> Dict[str, Any]:
        """
        提交当前阶段的交付物

        Args:
            stage_id: 阶段ID
            deliverable: 交付物数据
            reflection: 自我评估

        Returns:
            操作结果
        """
        if not self.enable_kanban or not self._kanban_manager:
            return {"status": "error", "message": "Kanban is not available"}

        result = await self._kanban_manager.submit_deliverable(
            stage_id, deliverable, reflection
        )

        if result.get("status") == "success":
            if result.get("all_completed"):
                self.set_phase("complete", "All stages completed")
            elif result.get("next_stage"):
                self.set_phase(
                    "execution", f"Moving to stage: {result['next_stage']['stage_id']}"
                )

        return result

    async def read_deliverable(self, stage_id: str) -> Dict[str, Any]:
        """
        读取指定阶段的交付物

        Args:
            stage_id: 阶段ID

        Returns:
            交付物内容
        """
        if not self.enable_kanban or not self._kanban_manager:
            return {"status": "error", "message": "Kanban is not available"}

        return await self._kanban_manager.read_deliverable(stage_id)

    async def get_kanban_status(self) -> str:
        """
        获取看板状态（用于 Prompt 注入）

        Returns:
            看板状态的 Markdown 文本
        """
        if not self.enable_kanban:
            return ""

        await self._ensure_kanban_manager()

        if not self._kanban_manager:
            return ""

        return await self._kanban_manager.get_kanban_status()

    async def get_current_stage_detail(self) -> str:
        """
        获取当前阶段详情（用于 Prompt 注入）

        Returns:
            当前阶段详情的 Markdown 文本
        """
        if not self.enable_kanban:
            return ""

        await self._ensure_kanban_manager()

        if not self._kanban_manager:
            return ""

        return await self._kanban_manager.get_current_stage_detail()

    def is_exploration_limit_reached(self) -> bool:
        """
        检查是否达到探索限制

        Returns:
            True 如果达到限制
        """
        if not self.enable_kanban or not self._kanban_manager:
            return False

        return self._kanban_manager.is_exploration_limit_reached()


# 导入需要的东西
from gyra.context.event import ActionPayload, EventType

# 导出
__all__ = [
    "ReActMasterAgent",
    "DoomLoopDetector",
    "KanbanManager",
    "validate_deliverable_schema",
]
