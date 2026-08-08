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
        # 1) 注入的解析器（serve 层：app_code → 多媒体配置）
        if callable(self._multimedia_resolver):
            try:
                cfg = self._multimedia_resolver(name)
                if cfg:
                    return cfg, name, "", ""
            except Exception:  # noqa: BLE001
                pass
        # 2) capability_pack 里的 AppCapability（按 app_code 或 app_name 匹配）
        pack = self._capability_pack
        for cap in (pack.get_all("app") if pack else []):
            code = getattr(cap, "app_code", "") or ""
            app_name = getattr(cap, "app_name", "") or ""
            if name not in (code, app_name):
                continue
            getter = getattr(cap, "get_multimedia_config", None)
            if not callable(getter):
                continue
            try:
                cfg = getter()
            except Exception:  # noqa: BLE001
                cfg = None
            return (
                cfg,
                code,
                app_name or name,
                getattr(cap, "app_desc", "") or "",
            )
        return None, "", "", ""

    def _build_subagent_delegate_factory(self, **kwargs: Any) -> Any:
        """把名称解析为委派协程（按 app_code 寻址，多实例各自独立）。

        与普通子 agent 委派共用同一身份 id（app_code）。对多媒体子 agent：
        - 按 ``subagent_name``（app_code / app_name）解析目标 app 自身的多媒体配置，
          动态构造绑定该 app 配置的独立 ``MultimediaAgent`` 实例（互不覆盖）；
        - 未命中 app_code 时回退到协议层 AgentManager 按 role/别名（MULTIMEDIA）
          取共享模板（兼容既有行为）。
        """
        try:
            from gyra.agent.multimedia import MultimediaAgent

            name = kwargs.get("subagent_name", "") or ""
            if not name:
                return None

            config, code, app_name, app_desc = self._resolve_multimedia(name)
            if config is not None:
                cfg = dict(config)
                if not cfg.get("name"):
                    cfg["name"] = app_name or code or "multimedia_agent"
                if not cfg.get("description"):
                    cfg["description"] = (
                        app_desc or f"多媒体生成 Agent（{app_name or code}）"
                    )
                inst = MultimediaAgent(config=cfg)
            else:
                # 回退：role/别名 寻址到共享模板（兼容既有行为）
                from gyra.agent.core.agent_manage import get_agent_manager

                inst = get_agent_manager().get_agent(name)
                if not isinstance(inst, MultimediaAgent):
                    return None
                running_agent = kwargs.get("agent") or self._agent
                if running_agent is not None and getattr(
                    running_agent, "ext_config", None
                ):
                    inst.ext_config = running_agent.ext_config

            return inst.to_async_delegate(
                afs=kwargs.get("afs") or self._agent_file_system,
                conv_id=kwargs.get("conv_id", ""),
            )
        except Exception:  # noqa: BLE001 - 注册表未就绪时静默回退
            return None

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
