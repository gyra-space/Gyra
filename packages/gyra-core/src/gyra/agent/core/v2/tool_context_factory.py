"""ToolContext 工厂。

根据 tool_call + capability_pack + sandbox_manager 构造 ToolContext，
按 tool 类型注入活资源句柄(DBCapability / KnowledgeCapability / AppCapability /
sandbox_client)。

Phase D:资源句柄来源从 v1 resource_map 改为 capability_pack。
"""
from typing import Any, Dict, List, Optional

from gyra.agent.tools.context import ToolContext
from gyra.agent.core.v2.tool_call_types import V2ToolCall


# tool_name → ToolContext resource key 的映射
_TOOL_RESOURCE_MAP = {
    "execute_sql": "db_resource",
    "list_tables": "db_resource",
    "get_table_spec": "db_resource",
    "KnowledgeSearch": "knowledge_retriever",
    "AgentStart": "app_resource",
}

# tool_name → capability_id 前缀(用于在 capability_pack 中查找)
_TOOL_CAPABILITY_PREFIX = {
    "execute_sql": "db",
    "list_tables": "db",
    "get_table_spec": "db",
    "KnowledgeSearch": "knowledge",
    "AgentStart": "app",
}


class ToolContextFactory:
    def __init__(
        self,
        *,
        agent_id: str,
        conv_id: str,
        user_id: Optional[str] = None,
        user_request: Optional[Any] = None,
        scene: Optional[str] = None,
        scenario_id: Optional[str] = None,
        language: str = "zh",
        capability_pack: Optional[Any] = None,
        sandbox_manager: Optional[Any] = None,
        skill_dir: Optional[str] = None,
        available_skills: Optional[Dict[str, str]] = None,
        agent_file_system: Optional[Any] = None,
        agent: Optional[Any] = None,
        multimedia_resolver: Optional[Any] = None,
    ):
        self._agent_id = agent_id
        self._conv_id = conv_id
        self._user_id = user_id
        self._user_request = user_request
        self._scene = scene
        self._scenario_id = scenario_id
        self._language = language
        self._capability_pack = capability_pack
        self._sandbox_manager = sandbox_manager
        self._skill_dir = skill_dir
        self._available_skills = available_skills or {}
        self._agent_file_system = agent_file_system
        self._agent = agent
        # 可选解析器：``(app_code) -> Optional[dict]``，返回目标 app 的
        # ``ext_config.multimedia_agent``（启用）。serve 层注入时按 app_code 解析。
        self._multimedia_resolver = multimedia_resolver

    def _resolve_multimedia(
        self, name: str
    ) -> tuple:
        """按名称（app_code / app_name）解析目标多媒体 app 的配置。

        返回 ``(config, app_code, app_name, app_desc)``；未命中返回 ``(None, "", "", "")``。
        优先用注入的 ``multimedia_resolver``，其次扫描 ``capability_pack`` 中匹配的
        ``AppCapability``（其 ``get_multimedia_config`` 只在 app 启用多媒体时返回配置）。
        """
        from gyra.agent.multimedia.delegate import resolve_multimedia_config

        return resolve_multimedia_config(
            name,
            capability_pack=self._capability_pack,
            multimedia_resolver=self._multimedia_resolver,
        )

    def _build_subagent_delegate_factory(self, **kwargs: Any) -> Any:
        """把名称解析为委派协程（按 app_code 寻址，多实例各自独立）。

        实现抽在 ``gyra.agent.multimedia.delegate.build_multimedia_delegate``,
        与 v1 路径（SpawnAgentTaskTool,context 即 agent 本身）共用同一解析逻辑。
        未命中/异常时返回 None,由 spawn_agent_task 回退 subagent_manager
        delegate 的完整 react 循环路径（独立子会话）。
        """
        from gyra.agent.multimedia.delegate import build_multimedia_delegate

        return build_multimedia_delegate(
            kwargs.get("subagent_name", "") or "",
            capability_pack=self._capability_pack,
            multimedia_resolver=self._multimedia_resolver,
            running_agent=kwargs.get("agent") or self._agent,
            afs=kwargs.get("afs") or self._agent_file_system,
            conv_id=kwargs.get("conv_id", ""),
        )

    def build(self, tool_call: V2ToolCall, tool: Optional[Any] = None) -> ToolContext:
        ctx = ToolContext(
            agent_id=self._agent_id,
            conversation_id=self._conv_id,
            user_id=self._user_id,
            scene=self._scene,
            scenario_id=self._scenario_id,
            language=self._language,
            skill_dir=self._skill_dir,
            available_skills=self._available_skills,
        )

        # 注入沙箱活句柄（G7）
        if self._sandbox_manager is not None:
            ctx.set_resource("sandbox_client", self._sandbox_manager.client)

        # 注入 agent_file_system（G4）
        if self._agent_file_system is not None:
            ctx.set_resource("agent_file_system", self._agent_file_system)

        # 注入 agent 引用（G4）
        if self._agent is not None:
            ctx.set_resource("agent", self._agent)

        # 注入用户上下文（RBAC 权限检查用）
        if self._user_request is not None:
            ctx.set_resource("user_request", self._user_request)
            # 同时挂到 config dict，兼容直接读 config 的路径
            ctx.config["user_request"] = self._user_request

        # 注入 subagent_delegate_factory：让 spawn_agent_task 能解析多媒体 Agent
        # （统一走协议层 AgentManager，未命中普通子 agent 时回退）。
        ctx.set_resource("subagent_delegate_factory", self._build_subagent_delegate_factory)

        # 按 tool 类型派发对应资源（G4）
        tool_name = tool_call.name
        cap_prefix = _TOOL_CAPABILITY_PREFIX.get(tool_name)
        resource_key = _TOOL_RESOURCE_MAP.get(tool_name)
        if cap_prefix and resource_key and self._capability_pack:
            caps = self._capability_pack.get_all(cap_prefix)
            if caps:
                ctx.set_resource(resource_key, caps[0])

        return ctx
