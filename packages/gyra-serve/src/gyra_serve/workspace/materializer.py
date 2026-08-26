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
    """物化结果：dynamic_resources 给 Agent 工具列表。

    type=app（子 Agent）现在也物化成 AppResource 进 dynamic_resources，由运行时
    按需构建（AppCapability + GptAppResource._start_app），不再预构建为
    extra_agents。extra_agents 字段保留为空以兼容下游读取。
    """

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
        logger.warning(
            f"[materializer] mcp not found for physical_ref={physical_ref!r}: "
            f"workspace 绑定的 MCP 资源 physical_ref 必须是 MCP 模块的精确 mcp_code。"
        )
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
    """type=knowledge_space → AgentResource(type=knowledge_pack,v2 JSON value)。

    Phase D:旧版产 type="knowledge" + 纯字符串 value(未注册类型,from_dict 转换
    直接 raise);改为 knowledge_pack + v2 JSON,由 KnowledgeCapability 接管。
    """
    return AgentResource.from_dict(
        {
            "type": "knowledge_pack",
            "name": config.get("name") or physical_ref,
            "value": {"knowledges": [{"knowledge_id": physical_ref}], **config},
        }
    )


def _materialize_app(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=app（子 Agent）→ AgentResource(type=app)，运行时按需构建。

    物化成 AppResource 进 dynamic_resources：AppCapability 声明 app 描述，
    派发时经 _resolve_app_code 命中后由 GptAppResource._start_app 按需构建，
    不预构建、不 hire。
    """
    app_code = physical_ref
    app_name = config.get("app_name") or config.get("name") or app_code
    app_desc = config.get("app_desc") or config.get("description") or ""
    return AgentResource.from_dict(
        {
            "type": "app",
            "name": app_name,
            "value": {
                "app_code": app_code,
                "app_name": app_name,
                "app_desc": app_desc,
            },
        }
    )


def _materialize_llm_model(
    physical_ref: str, config: Dict[str, Any]
) -> Optional[AgentResource]:
    """type=llm_model → 设置空间级模型配置覆盖(ContextVar)。

    空间绑定的 llm_model 资源决定该空间可用的专属模型/token:
    物化时把模型配置写入 ModelConfigCache 的空间级 ContextVar,该作用域内后续
    LLM 调用经 get_config/has_model 以"空间模型 > 全局回退"解析,实现空间专属
    token 管控。不落明文 token:仅引用 api_key_ref,运行时由 ConfigReferenceResolver
    解析。

    Phase D:不再产出 AgentResource(llm_model 类型已下线,旧产出本就被所有消费方
    丢弃);只保留 ModelConfigCache 副作用,返回 None。
    """
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    model = (config.get("model") or physical_ref or "").strip()
    if not model:
        return None
    ModelConfigCache.set_space_model_config(
        {
            # provider 不在覆盖里硬编码成 openai:空间绑定语义是「对全局同名模型的
            # 配置覆盖」,缺省时由 _normalize_space_model 继承全局 provider/protocol/
            # base_url/api_key,避免把本来可用的全局模型覆盖坏(不重新注册)。
            "provider": config.get("provider"),
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
    return None


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
    "app": "_materialize_app",
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


def _load_pool_by_ref(
    system_app, workspace_id: int
) -> Dict[str, Any]:
    """加载空间资源池,按引用键(physical_ref / name)索引。

    剧本引用物化时优先对齐空间资源池:命中的引用以空间绑定记录为准物化
    (type/physical_ref/config 用绑定记录),使剧本引用与空间绑定物化结果
    一致——这是「剧本 = 空间池子集」分层模型与权限投影的前提。

    查询失败或空间无资源时返回空 dict,调用方降级为全局兜底(存量兼容)。
    """
    pool: Dict[str, Any] = {}
    try:
        ws_service = WorkspaceService(system_app=system_app, config=ServeConfig())
        records = ws_service.list_resources(workspace_id) or []
    except Exception as e:
        logger.warning(f"materializer load workspace pool failed: {e}")
        return pool
    for rec in records:
        if not getattr(rec, "is_active", True):
            continue
        for key in (getattr(rec, "physical_ref", None), getattr(rec, "name", None)):
            if key:
                pool.setdefault(key, rec)
    return pool


def _materialize_declared_item(
    system_app, item: Any, item_type: Optional[str],
    pool_by_ref: Optional[Dict[str, Any]] = None,
) -> Optional["AgentResource"]:
    """物化单个声明项(skill / resource),优先对齐空间资源池。

    规则:
    - 空间池命中:以绑定记录为准物化(type/physical_ref/config 用绑定记录)。
    - 空间池未命中:按声明类型走全局兜底(存量兼容),并记 warning 引导绑定。
    - ``app`` 类型跳过(playbook 子 Agent 由 roles 块装配,不走技能物化)。
    """
    if item_type == "app":
        return None
    physical_ref, config = _declaration_item_to_ref_config(item, item_type)
    if physical_ref is None:
        return None

    if pool_by_ref is not None:
        pool_rec = pool_by_ref.get(physical_ref)
        if pool_rec is not None:
            rec_type = getattr(pool_rec, "type", None)
            if not rec_type:
                return None
            rec_handler_name = _MATERIALIZE_DISPATCH.get(rec_type)
            rec_handler = globals().get(rec_handler_name) if rec_handler_name else None
            if rec_handler is None:
                logger.warning(
                    f"materializer skip pool type={rec_type} name={physical_ref} "
                    f"(资源已绑定到空间但类型不支持物化)"
                )
                return None
            raw_config = getattr(pool_rec, "config", None)
            if raw_config is None:
                raw_config = getattr(pool_rec, "config_json", None)
            pool_config = _parse_config(raw_config)
            pool_ref = getattr(pool_rec, "physical_ref", None) or physical_ref
            try:
                materialized = rec_handler(pool_ref, pool_config)
                if materialized is not None:
                    return materialized
                return None
            except Exception as e:
                logger.warning(
                    f"materializer pool fail type={rec_type} name={physical_ref}: {e}"
                )
                return None

    # 池外兜底:按声明类型全局解析(存量/seed 兼容)
    handler_name = _MATERIALIZE_DISPATCH.get(item_type) or _MATERIALIZE_DISPATCH.get("skill")
    handler = globals().get(handler_name) if handler_name else None
    if handler is None:
        return None
    try:
        return handler(physical_ref, config)
    except Exception as e:
        logger.warning(
            f"materializer playbook fail type={item_type} name={physical_ref}: {e}"
        )
        return None


def _materialize_declared_skill(skill_item: Any) -> Optional["AgentResource"]:
    """物化单个声明技能项 -> AgentResource 或 None。

    复用 ``_MATERIALIZE_DISPATCH`` 分派;``app`` 类型跳过(playbook 子 Agent 由
    roles 块/AgentRoleService 装配,不走技能物化)。供顶层 skills 与 roles 块角色技能共用。
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
    system_app, declaration_dsl_json: Optional[Dict[str, Any]],
    workspace_id: Optional[int] = None,
) -> List["AgentResource"]:
    """Materialize skills + context.resources from a playbook declaration.

    Reuses ``_MATERIALIZE_DISPATCH`` handlers. Returns a flat list of
    ``AgentResource`` objects; ``app`` resources are skipped because they
    produce ``extra_agents`` dicts rather than ``AgentResource``.

    传入 ``workspace_id`` 时,引用优先对齐空间资源池(空间=注册/治理池,
    剧本=选配/编排子集):命中的引用按空间绑定记录物化,未命中的走全局兜底
    (存量兼容)。不传则保持原行为(直接按声明类型全局物化)。
    """
    if not declaration_dsl_json:
        return []

    pool_by_ref = _load_pool_by_ref(system_app, workspace_id) if workspace_id is not None else None

    resources: List["AgentResource"] = []

    skills = declaration_dsl_json.get("skills") or []
    for skill in skills:
        skill_type = "skill" if isinstance(skill, str) else (skill.get("type") or "skill")
        materialized = _materialize_declared_item(system_app, skill, skill_type, pool_by_ref)
        if materialized is not None:
            resources.append(materialized)

    ctx = declaration_dsl_json.get("context") or {}
    for res in ctx.get("resources") or []:
        if not isinstance(res, dict):
            continue
        res_type = res.get("type")
        if res_type == "app":
            continue
        materialized = _materialize_declared_item(system_app, res, res_type, pool_by_ref)
        if materialized is not None:
            resources.append(materialized)

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

    # llm_model 特殊处理:空间可绑定多个可用模型,但空间级模型覆盖(ContextVar)只承载
    # 一个「默认模型」。统一物化顺序 = is_default 标记者 > 列表首个(当前默认模型),
    # 以避免旧实现「遍历中被最后一个覆盖」导致的顺序歧义(oldest-wins)。
    llm_records: List[Any] = []
    for r in resources:
        if not getattr(r, "is_active", True):
            continue
        if getattr(r, "type", None) == "llm_model":
            llm_records.append(r)
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
            # 统一按需构建：type=app 也进 dynamic_resources（AppResource），
            # 运行时经 AppCapability/_resolve_app_code 按需构建，不再产 extra_agents。
            result.dynamic_resources.append(materialized)
        except Exception as e:
            logger.warning(
                f"materializer fail type={rtype} name={r.name}: {e}"
            )

    if llm_records:
        chosen = llm_records[0]
        for rec in llm_records[1:]:
            raw = getattr(rec, "config", None)
            if raw is None:
                raw = getattr(rec, "config_json", None)
            if _parse_config(raw).get("is_default"):
                chosen = rec
                break
        raw_config = getattr(chosen, "config", None)
        if raw_config is None:
            raw_config = getattr(chosen, "config_json", None)
        try:
            _materialize_llm_model(
                getattr(chosen, "physical_ref", None), _parse_config(raw_config)
            )
        except Exception as e:
            logger.warning(
                f"materializer fail type=llm_model name={getattr(chosen, 'name', None)}: {e}"
            )
    return result
