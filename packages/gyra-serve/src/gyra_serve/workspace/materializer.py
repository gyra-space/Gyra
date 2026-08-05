"""Materialize workspace_resource.physical_ref into AgentResource at runtime.

这是场景空间能力的命脉——把空间挂载的资源从 prompt 字符串装饰
物化成 Agent 可实际调用的工具/能力。
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from gyra.agent.resource.base import AgentResource

from gyra_serve.workspace.config import ServeConfig
from gyra_serve.workspace.service.service import WorkspaceService

logger = logging.getLogger(__name__)


@dataclass
class MaterializedResources:
    """物化结果：dynamic_resources 给 Agent 工具列表，extra_agents 给多 Agent 协作。"""

    dynamic_resources: List[AgentResource] = field(default_factory=list)
    extra_agents: List[Dict[str, Any]] = field(default_factory=list)


def _parse_config(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except Exception:
        return {}


def _get_mcp_field(mcp_info: Any, key: str, default: Any = None) -> Any:
    """Support both dict-like mocks and ServerResponse objects."""
    if isinstance(mcp_info, dict):
        return mcp_info.get(key, default)
    return getattr(mcp_info, key, default)


def _materialize_mcp(physical_ref: str, config: Dict[str, Any]) -> Optional[AgentResource]:
    """type=mcp → AgentResource(type=mcp(gyra))，复用 get_mcp_info。"""
    # Lazy import: mcp_collect pulls heavy/optional runtime dependencies
    # (mcp, tenacity, gyra_app) that should not block importing this module.
    from gyra_serve.agent.resource.tool.mcp_collect import get_mcp_info

    mcp_info = get_mcp_info(physical_ref)
    if not mcp_info:
        logger.warning(f"mcp not found: {physical_ref}")
        return None
    return AgentResource.from_dict(
        {
            "type": "mcp(gyra)",
            "name": _get_mcp_field(mcp_info, "name") or physical_ref,
            "value": {
                "mcp_code": physical_ref,
                "name": _get_mcp_field(mcp_info, "name") or physical_ref,
                "mcp_servers": _get_mcp_field(mcp_info, "sse_url"),
                "headers": _get_mcp_field(mcp_info, "sse_headers") or {},
                "source": _get_mcp_field(mcp_info, "type") or "sse",
                "timeout": 30,
            },
        }
    )


def _materialize_datasource(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=data_source → AgentResource(type=datasource)。"""
    return AgentResource.from_dict(
        {"type": "datasource", "name": physical_ref,
         "value": {"db_name": physical_ref, **config}}
    )


def _materialize_skill(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=skill → AgentResource(type=agent_skill)。"""
    return AgentResource.from_dict(
        {"type": "skill(gyra)", "name": physical_ref,
         "value": {"skill_name": physical_ref, **config}}
    )


def _materialize_knowledge_space(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=knowledge_space → AgentResource(type=knowledge)。"""
    return AgentResource.from_dict(
        {"type": "knowledge", "value": physical_ref, **config}
    )


def _materialize_app_as_extra_agent(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """type=app（子 Agent）→ extra_agents 项。"""
    return {"app_code": physical_ref, **config}


def _materialize_llm_model(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=llm_model → 设置空间级模型配置覆盖(ContextVar)并注入 AgentInfo。

    空间绑定的 llm_model 资源决定该空间可用的专属模型/token:
    物化时把模型配置写入 ModelConfigCache 的空间级 ContextVar,该作用域内后续
    LLM 调用经 get_config/has_model 以"空间模型 > 全局回退"解析,实现空间专属
    token 管控。不落明文 token:仅引用 api_key_ref,运行时由 ConfigReferenceResolver
    解析。返回的 AgentResource 让 system prompt 能看到空间绑定的模型与协议。
    """
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    model = (config.get("model") or physical_ref or "").strip()
    if not model:
        return None
    ModelConfigCache.set_space_model_config(
        {
            "provider": config.get("provider") or "openai",
            "model": model,
            "base_url": config.get("base_url") or config.get("api_base"),
            "api_key_ref": config.get("api_key_ref") or "",
            "api_key": config.get("api_key"),
            # 透传空间级推理参数(思考深度等),未配置时回退全局/系统配置。
            "temperature": config.get("temperature"),
            "max_new_tokens": config.get("max_new_tokens") or config.get("max_tokens"),
            "top_p": config.get("top_p"),
            "reasoning_effort": config.get("reasoning_effort"),
        }
    )
    space_cfg = ModelConfigCache.get_space_model_config() or {}
    return AgentResource.from_dict(
        {
            "type": "llm_model",
            "name": space_cfg.get("model") or model,
            "value": {
                "model": space_cfg.get("model"),
                "provider": space_cfg.get("provider"),
                "protocol": space_cfg.get("protocol"),
                "base_url": space_cfg.get("base_url"),
                "api_key_ref": space_cfg.get("api_key_ref"),
                "source": "space_bound",
            },
        }
    )


def _materialize_ecp(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=ecp → AgentResource(type=ecp)。"""
    return AgentResource.from_dict(
        {
            "type": "ecp",
            "name": physical_ref or "ecp",
            "value": {
                "workspace_id": physical_ref or config.get("workspace_id", "default"),
            },
        }
    )


# type → 物化函数名分派表（字符串，便于运行时通过 globals 解析并支持 patch）
_MATERIALIZE_DISPATCH = {
    "mcp": "_materialize_mcp",
    "data_source": "_materialize_datasource",
    "datasource": "_materialize_datasource",
    "skill": "_materialize_skill",
    "agent_skill": "_materialize_skill",
    "knowledge_space": "_materialize_knowledge_space",
    "app": "_materialize_app_as_extra_agent",
    "llm_model": "_materialize_llm_model",
    "ecp": "_materialize_ecp",
}


def _declaration_item_to_ref_config(
    item: Any, item_type: Optional[str] = None
) -> tuple[Optional[str], Dict[str, Any]]:
    """Normalize a playbook declaration item into (physical_ref, config).

    Supports the v1 string form (skill code) as well as dict forms.
    """
    if isinstance(item, str):
        return item, {}
    if not isinstance(item, dict):
        return None, {}
    if item_type is None:
        item_type = item.get("type")
    if item_type == "mcp":
        physical_ref = item.get("server_name") or item.get("name") or item.get("ref")
    else:
        physical_ref = item.get("name") or item.get("ref")
    if not physical_ref:
        return None, {}
    config = {k: v for k, v in item.items() if k != "type"}
    return physical_ref, config


def _materialize_declared_skill(skill_item: Any) -> Optional["AgentResource"]:
    """物化单个声明技能项 -> AgentResource 或 None。

    复用 ``_MATERIALIZE_DISPATCH`` 分派;``app`` 类型跳过(它产出 extra_agents
    而非 AgentResource)。供顶层 skills 与 roles 块角色技能共用。
    """
    if isinstance(skill_item, str):
        skill_type = "skill"
    elif isinstance(skill_item, dict):
        skill_type = skill_item.get("type") or "skill"
    else:
        return None
    if skill_type == "app":
        return None
    handler_name = _MATERIALIZE_DISPATCH.get(skill_type) or _MATERIALIZE_DISPATCH.get("skill")
    if handler_name is None:
        return None
    # 通过 globals 解析,便于单元测试 patch 模块级 handler
    handler = globals().get(handler_name)
    if handler is None:
        return None
    physical_ref, config = _declaration_item_to_ref_config(skill_item, skill_type)
    if physical_ref is None:
        return None
    try:
        return handler(physical_ref, config)
    except Exception as e:
        logger.warning(
            f"materializer skill fail type={skill_type} name={physical_ref}: {e}"
        )
        return None


def materialize_playbook_declaration(
    system_app, declaration_dsl_json: Optional[Dict[str, Any]]
) -> List["AgentResource"]:
    """Materialize skills + context.resources from a playbook declaration.

    Reuses ``_MATERIALIZE_DISPATCH`` handlers. Returns a flat list of
    ``AgentResource`` objects; ``app`` resources are skipped because they
    produce ``extra_agents`` dicts rather than ``AgentResource``.
    """
    if not declaration_dsl_json:
        return []

    resources: List["AgentResource"] = []

    skills = declaration_dsl_json.get("skills") or []
    for skill in skills:
        if isinstance(skill, str):
            skill_type = "skill"
        else:
            skill_type = skill.get("type") or "skill"
        if skill_type == "app":
            continue
        handler_name = _MATERIALIZE_DISPATCH.get(skill_type) or _MATERIALIZE_DISPATCH.get("skill")
        if handler_name is None:
            continue
        # Resolve via globals so unit-test patches to module-level handlers apply.
        handler = globals().get(handler_name)
        if handler is None:
            continue
        physical_ref, config = _declaration_item_to_ref_config(skill, skill_type)
        if physical_ref is None:
            continue
        try:
            materialized = handler(physical_ref, config)
            if materialized is not None:
                resources.append(materialized)
        except Exception as e:
            logger.warning(
                f"materializer playbook fail type={skill_type} name={physical_ref}: {e}"
            )
            continue

    ctx = declaration_dsl_json.get("context") or {}
    for res in ctx.get("resources") or []:
        if not isinstance(res, dict):
            continue
        res_type = res.get("type")
        if res_type == "app":
            continue
        handler_name = _MATERIALIZE_DISPATCH.get(res_type)
        if handler_name is None:
            continue
        handler = globals().get(handler_name)
        if handler is None:
            continue
        physical_ref, config = _declaration_item_to_ref_config(res, res_type)
        if physical_ref is None:
            continue
        try:
            materialized = handler(physical_ref, config)
            if materialized is not None:
                resources.append(materialized)
        except Exception as e:
            logger.warning(
                f"materializer playbook fail type={res_type} name={physical_ref}: {e}"
            )
            continue

    # P2 任务10: 物化 roles 块中各角色声明的技能(按角色装配不同 skill 集)
    # 无 roles 块时此处为空操作,行为与原实现完全一致(向后兼容)。
    roles_block = declaration_dsl_json.get("roles") or {}
    if isinstance(roles_block, dict):
        for _role_key, role_decl in roles_block.items():
            if not isinstance(role_decl, dict):
                continue
            for skill in role_decl.get("skills") or []:
                materialized = _materialize_declared_skill(skill)
                if materialized is not None:
                    resources.append(materialized)

    return resources


def materialize_playbook_roles(
    system_app, declaration_dsl_json: Optional[Dict[str, Any]], workspace_id: int
) -> List[Dict[str, Any]]:
    """按 Playbook declaration 的 roles 块装配职能角色团队。

    P2 任务10: 把"裸 app_code"的多 Agent 协作抽象为职能角色团队。
    调用 ``AgentRoleService.assemble_team`` 产出角色蓝图(role/skills/
    maturity_min/prompt),并为每个角色物化其技能成 ``AgentResource`` 列表,
    供运行时按角色装配不同 skill 集与 prompt。

    无 roles 块时返回 [](向后兼容)。
    """
    if not declaration_dsl_json:
        return []
    roles_block = declaration_dsl_json.get("roles")
    if not isinstance(roles_block, dict) or not roles_block:
        return []

    try:
        from .agent_roles import AgentRoleService

        role_service = AgentRoleService(system_app=system_app, config=ServeConfig())
        try:
            role_service.init_app(system_app)
        except Exception:
            # assemble_team 不依赖 DAO,init_app 失败不阻断团队装配
            pass
        team = role_service.assemble_team(declaration_dsl_json, workspace_id)
    except Exception as e:
        logger.warning(f"materialize_playbook_roles assemble_team failed: {e}")
        return []

    # 为每个角色物化其技能 -> AgentResource(不同 skill 集)
    for entry in team:
        role_resources: List["AgentResource"] = []
        for skill in entry.get("skills") or []:
            materialized = _materialize_declared_skill(skill)
            if materialized is not None:
                role_resources.append(materialized)
        entry["resources"] = role_resources
    return team


def materialize_resources(system_app, workspace_id: int) -> MaterializedResources:
    """把 workspace 下所有 active 资源物化成 AgentResource / extra_agents。

    未知 type（slo/oncall_rotation/data_pipeline/bi_dashboard/code_repo/api_endpoint/
    environment/runbook_target）当前跳过——这些是场景专属逻辑资源，
    P2 阶段通过 ResourceManager.register_resource 注册自定义类型后再物化。
    """
    result = MaterializedResources()
    try:
        ws_service = WorkspaceService(system_app=system_app, config=ServeConfig())
        resources = ws_service.list_resources(workspace_id) or []
    except Exception as e:
        logger.warning(f"materializer list_resources failed: {e}")
        return result

    for r in resources:
        if not getattr(r, "is_active", True):
            continue
        rtype = r.type
        handler_name = _MATERIALIZE_DISPATCH.get(rtype)
        if handler_name is None:
            logger.warning(
                f"materializer skip unsupported type={rtype} name={r.name} "
                f"(P2 will register via ResourceManager)"
            )
            continue
        handler = globals().get(handler_name)
        if handler is None:
            continue
        try:
            raw_config = getattr(r, "config", None)
            if raw_config is None:
                raw_config = getattr(r, "config_json", None)
            config = _parse_config(raw_config)
            physical_ref = getattr(r, "physical_ref", None)
            materialized = handler(physical_ref, config)
            if materialized is None:
                continue
            if rtype == "app":
                result.extra_agents.append(materialized)
            else:
                result.dynamic_resources.append(materialized)
        except Exception as e:
            logger.warning(
                f"materializer fail type={rtype} name={r.name}: {e}"
            )
    return result
