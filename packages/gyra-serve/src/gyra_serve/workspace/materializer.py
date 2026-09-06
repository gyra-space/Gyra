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

# 仅前端消费、不需要物化给 Agent 的资源类型。
# `command` 是场景空间 `/` 菜单的会话命令(压缩上下文/清理会话/规划模式等),
# 复用 workspace_resource 表存储以省掉一张表与配套 CRUD,但它是 UI 行为而非
# Agent 资源。这里显式白名单化,避免落到下面的「unsupported type」warning 里
# 污染日志(每轮对话都会物化一次)。
_NON_AGENT_RESOURCE_TYPES = {"command"}


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


def materialize_expert_equipment(
    system_app, workspace_id: int, app_code: str
) -> List["AgentResource"]:
    """组装专家在某空间的外挂资源为 AgentResource 列表。

    Agent Team 空间重构（Phase 1.2）：外挂 = workspace_expert_equipment 明细行。
    逐行先对齐空间资源池（workspace_resource）：命中的以空间绑定记录为准物化
    （type/config 用绑定记录，获得空间治理与权限投影）；池未命中时 skill/MCP
    回退全局注册表直引（playbook validate_references 同语义：空间绑定非必需）；
    其余类型（知识库/数据源等空间域资源）无全局兜底，按悬空跳过不阻断执行。

    无成员行 / 无外挂行 / 查询失败 → 返回 []（调用方以专家标准装备兜底）。
    """
    try:
        from gyra_serve.workspace.expert import WorkspaceExpertService

        service = WorkspaceExpertService()
        member = service.get_member_by_app_code(workspace_id, app_code)
        if member is None:
            return []
        equipment_rows = service.list_equipment(member.id)
    except Exception as e:
        logger.warning(
            f"materialize expert equipment failed (ws={workspace_id} app={app_code}): {e}"
        )
        return []

    if not equipment_rows:
        return []

    # P1 资产收口:把专家外挂的 datasource/knowledge 自动登记进本空间派生 ECP
    # workspace 的 asset_ref,使这些资产默认被 ECP 托管(asset_gate 据此拦截直连)。
    # 幂等(register 为 idempotent);失败仅记 warning,不阻断物化。
    try:
        from gyra_serve.workspace.ecp_derive import derived_ecp_workspace_id
        from gyra_serve.workspace.service.service import WorkspaceService

        ws_service = WorkspaceService(system_app=system_app, config=ServeConfig())
        ws = ws_service.get_by_id(workspace_id)
        ecp_ws = derived_ecp_workspace_id(getattr(ws, "workspace_code", str(workspace_id)))
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[expert-equipment] resolve ecp workspace failed (ws={workspace_id}): {e}"
        )
        ecp_ws = None

    def _register_asset(kind: str, ref_id: str) -> None:
        if not ecp_ws or not ref_id:
            return
        try:
            from gyra_serve.ecp.models.models import AssetRefDao

            AssetRefDao().register(kind, str(ref_id), ecp_ws)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[expert-equipment] register ecp asset {kind}:{ref_id} failed: {e}"
            )

    pool_by_ref = _load_pool_by_ref(system_app, workspace_id)
    resources: List["AgentResource"] = []
    for row in equipment_rows:
        equipment_config = _parse_config(row.config_json)
        pool_rec = pool_by_ref.get(row.resource_ref)
        if pool_rec is None:
            # 池未命中：skill/MCP 有全局注册表，回退全局直引（空间绑定非必需，
            # 绑定仅带来空间治理/权限投影）；其余类型无全局兜底，按悬空跳过。
            if row.resource_type in ("skill", "agent_skill"):
                logger.info(
                    f"[expert-equipment] pool miss, fallback global skill: "
                    f"app={app_code} ref={row.resource_ref!r}"
                )
                materialized = _materialize_skill(row.resource_ref, equipment_config)
                if materialized is not None:
                    resources.append(materialized)
                continue
            if row.resource_type == "mcp":
                logger.info(
                    f"[expert-equipment] pool miss, fallback global mcp: "
                    f"app={app_code} ref={row.resource_ref!r}"
                )
                try:
                    materialized = _materialize_mcp(row.resource_ref, equipment_config)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"[expert-equipment] global mcp fallback fail "
                        f"ref={row.resource_ref}: {e}"
                    )
                    materialized = None
                if materialized is not None:
                    resources.append(materialized)
                continue
            logger.warning(
                f"[expert-equipment] dangling ref: app={app_code} "
                f"type={row.resource_type} ref={row.resource_ref!r} "
                f"not in workspace pool (ws={workspace_id}), skipped"
            )
            continue
        rec_type = getattr(pool_rec, "type", None)
        handler_name = _MATERIALIZE_DISPATCH.get(rec_type)
        handler = globals().get(handler_name) if handler_name else None
        if handler is None:
            logger.warning(
                f"[expert-equipment] unsupported pool type={rec_type} ref={row.resource_ref}"
            )
            continue
        raw_config = getattr(pool_rec, "config", None)
        if raw_config is None:
            raw_config = getattr(pool_rec, "config_json", None)
        pool_config = _parse_config(raw_config)
        # 外挂级参数（如知识库 top_k）覆盖池配置同名键
        merged_config = {**pool_config, **equipment_config}
        pool_ref = getattr(pool_rec, "physical_ref", None) or row.resource_ref
        # P1 资产收口:datasource→kind=db, knowledge_space→kind=space(slug)
        if rec_type == "data_source":
            _register_asset("db", pool_ref)
        elif rec_type == "knowledge_space":
            _register_asset("space", pool_ref)
        try:
            materialized = handler(pool_ref, merged_config)
            if materialized is not None:
                resources.append(materialized)
        except Exception as e:
            logger.warning(
                f"[expert-equipment] materialize fail type={rec_type} "
                f"ref={row.resource_ref}: {e}"
            )
    return resources


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
        if rtype in _NON_AGENT_RESOURCE_TYPES:
            continue
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
