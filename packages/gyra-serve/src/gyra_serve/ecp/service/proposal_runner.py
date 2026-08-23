"""Proposal runner: workspace-level, all registered assets as dynamic resources.

Trigger proposal generation for a workspace: gather all registered asset refs
(``ecp_asset_ref``), convert them to dynamic resources (db -> ``datasource`` so
``DBCapability`` materializes and injects db info + table list into the prompt;
doc/space -> ``knowledge_pack``), pass them to ``build_agent_by_app_code``, then
run the BAIZE proposal Agent (``EcpProposalAgent`` template) via
``UserProxyAgent.initiate_chat``.

The Agent discovers tables via the injected DBCapability (not a hardcoded list),
explores each (get_table_spec -> sample_distinct_values -> propose_semantic) in
its ReAct loop until all assets are done. Mirrors chat flow build + initiate_chat
(agent_chat.py:3170-3192).
"""

import logging
import uuid
from typing import Optional

from ..api.schemas import GenerateProposalsVO
from ..config import DEFAULT_WORKSPACE_ID, STATUS_PROPOSED

logger = logging.getLogger(__name__)

_ECP_TASK_KIND = "ecp_proposal"


def _proposed_ids(workspace_id: str) -> set:
    """Return the set of proposed object ids in a workspace (best-effort)."""
    from ..models.models import SemanticObjectDao

    try:
        vo = SemanticObjectDao().list_latest(
            workspace_id=workspace_id, status=STATUS_PROPOSED, page=1, page_size=1000
        )
        return {it.id for it in (vo.items or [])}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp-proposal-runner] count proposed failed: {e}")
        return set()


def _assets_to_dynamic_resources(workspace_id: str, result: GenerateProposalsVO):
    """Convert registered asset refs into dynamic AgentResources.

    db -> ``datasource`` (DBCapability injects db info + table list);
    doc/space -> ``knowledge_pack`` (KnowledgeCapability injects space list);
    api -> skipped (P3). db assets whose db_name can't be resolved are skipped
    with an error recorded.
    """
    from gyra.agent.resource.base import AgentResource

    from ..models.models import AssetRefDao

    dyn = []
    try:
        assets = AssetRefDao().list(workspace_id) or []
    except Exception as e:  # noqa: BLE001
        result.errors.append(f"读取登记资产失败: {e}")
        return dyn

    for a in assets:
        if a.kind == "db":
            try:
                ds_id = int(a.ref_id)
            except (TypeError, ValueError):
                result.errors.append(f"db 资产 ref_id 非法: {a.ref_id}")
                continue
            try:
                from gyra_serve.datasource.manages.connect_config_db import (
                    ConnectConfigDao,
                )

                cfg = ConnectConfigDao().get_one({"id": ds_id})
                db_name = getattr(cfg, "db_name", None)
            except Exception as e:  # noqa: BLE001
                result.errors.append(f"db 资产 {a.ref_id} 查询失败: {e}")
                continue
            if not db_name:
                result.errors.append(f"db 资产 {a.ref_id} 无 db_name(未就绪),跳过")
                continue
            dyn.append(
                AgentResource(
                    type="datasource",
                    value={"db_id": ds_id, "db_name": db_name},
                    is_dynamic=True,
                )
            )
        elif a.kind in ("document", "space"):
            name = (a.ref_meta or {}).get("name") or a.ref_id
            dyn.append(
                AgentResource(
                    type="knowledge_pack",
                    value={"knowledges": [{"name": name, "knowledge_id": a.ref_id}]},
                    is_dynamic=True,
                )
            )
        # api: P3, skipped
    return dyn


async def run_proposal_agent(
    system_app,
    app_code: str,
    workspace_id: Optional[str] = None,
    domain_hint: Optional[str] = None,
) -> GenerateProposalsVO:
    """Run the BAIZE proposal Agent over ALL registered assets of a workspace.

    Args:
        system_app: SystemApp (to resolve AgentChat).
        app_code: the selected proposal agent app (proposal_agent_id); should be
            based on the ECP_PROPOSAL_AGENT template.
        workspace_id: ECP workspace whose registered assets to propose for.
        domain_hint: optional domain context (prepended to the task message).
    """
    from gyra.agent import AgentContext, UserProxyAgent
    from gyra.component import ComponentType
    from gyra.core import HumanMessage
    from gyra_serve.agent.agents.chat.agent_chat import AgentChat, get_app_service

    ws = workspace_id or DEFAULT_WORKSPACE_ID
    # datasource_id=0 marks a workspace-level (multi-asset) run
    result = GenerateProposalsVO(datasource_id=0)

    dyn = _assets_to_dynamic_resources(ws, result)
    if not dyn:
        if not result.errors:
            result.errors.append(f"工作空间 {ws} 无可用登记资产")
        return result

    try:
        # AgentChat is NOT a registered component (it's an attribute of the
        # AgentsController / MULTI_AGENTS). build_agent_by_app_code uses the
        # global resource_manager + get_app_service, so a fresh SimpleAgentChat
        # instance works (its init_app is idempotent).
        from gyra_serve.agent.agents.chat.agent_chat_simple import SimpleAgentChat

        agent_chat = SimpleAgentChat(system_app)
    except Exception as e:  # noqa: BLE001
        result.errors.append(f"AgentChat 不可用: {e}")
        return result

    try:
        app = await get_app_service().app_detail(app_code, building_mode=False)
    except Exception as e:  # noqa: BLE001
        result.errors.append(f"找不到提案 Agent {app_code}: {e}")
        return result

    conv_id = f"ecp_proposal_ws{ws}_{uuid.uuid4().hex[:8]}"
    context = AgentContext(
        conv_id=conv_id,
        conv_session_id=conv_id,
        gpts_app_code=app_code,
        gpts_app_name=getattr(app, "app_name", app_code) or app_code,
        agent_app_code=app_code,
        extra={"dynamic_resources": dyn},  # Pass dynamic resources via extra
    )
    agent_memory = agent_chat.get_or_build_agent_memory(conv_id, app.app_name)

    logger.info(
        f"[ecp-proposal-runner] build agent {app_code} ws={ws} "
        f"assets={len(dyn)} conv={conv_id}"
    )
    try:
        # dynamic_resources now passed via context.extra, no need to pass here
        recipient = await agent_chat.build_agent_by_app_code(
            app_code, context, agent_memory
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[ecp-proposal-runner] build agent failed: {e}")
        result.errors.append(f"构建 Agent 失败: {e}")
        return result

    before = _proposed_ids(ws)

    user_proxy = await UserProxyAgent().bind(context).bind(agent_memory).build()

    task = (
        f"为工作空间 {ws} 的所有登记资产生成企业语义资产提案。"
        f"已为你注入所有登记资产(库/文档)为资源。"
        f"请逐库逐表用 get_table_spec(datasource_id=<database.datasource_id>, table_name='表名') 读取结构，"
        f"对低基数文本列用 sample_distinct_values 采样，"
        f"用 propose_semantic(..., workspace_id={ws}) 逐个落地 "
        f"entity/metric/dimension/relation 提案。所有资产全部完成后结束。"
        f"注意:表名必须与 get_table_spec 返回完全一致(多 schema 库如 Oracle 保留 "
        f"owner 前缀,如 OPR.OPR_REGISTRATION,禁止省略);日期/时间类型列在 entity "
        f"的 fields 中标注 role=time。"
    )
    if domain_hint:
        task = f"【领域背景】{domain_hint}\n\n{task}"
    logger.info(f"[ecp-proposal-runner] initiate_chat task for ws={ws}")
    try:
        await user_proxy.initiate_chat(
            recipient=recipient, message=HumanMessage(content=task)
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[ecp-proposal-runner] agent run failed: {e}")
        result.errors.append(f"Agent 运行失败: {e}")

    after = _proposed_ids(ws)
    new_ids = sorted(after - before)
    result.proposals_created = len(new_ids)
    result.proposal_ids = new_ids
    logger.info(
        f"[ecp-proposal-runner] done ws={ws}: +{result.proposals_created} "
        f"proposals {new_ids}"
    )
    return result


# --------------------------------------------------------------------- async
# 提案生成改为真异步任务:POST /proposals/generate 立即返回 task_id,生成在后台执行,
# 前端轮询任务状态。任务记录持久化到 gpts_async_tasks(AsyncTaskDao),与 media-jobs
# 同一张表,跨进程/重启可见。agent 路径(全资产生成)常达数分钟,不再受 HTTP 超时约束。


def _task_id(workspace_id: Optional[str]) -> str:
    return f"ecp_prop_{(workspace_id or 'default')}_{uuid.uuid4().hex[:8]}"


def _describe(request) -> str:
    if request.datasource_id:
        return f"为数据源 #{request.datasource_id} 生成语义提案"
    return f"为工作空间 {request.workspace_id or 'default'} 的所有资产生成语义提案"


def _resolve_agent_id(service, request) -> Optional[str]:
    try:
        cfg = service.get_workspace_config(request.workspace_id)
        return getattr(cfg, "proposal_agent_id", None) if cfg else None
    except Exception:  # noqa: BLE001
        return None


async def generate(service, request) -> GenerateProposalsVO:
    """执行完整提案生成逻辑(agent 路径或 batch 路径),返回结果。

    从 endpoint 抽出,供前台同步调用与后台任务共用。
    """
    from ..service.propose import DbSemanticsProposer

    agent_id = _resolve_agent_id(service, request)
    if agent_id:
        return await run_proposal_agent(
            system_app=service._system_app,
            app_code=agent_id,
            workspace_id=request.workspace_id,
            domain_hint=request.domain_hint,
        )

    proposer = DbSemanticsProposer(service)
    if request.datasource_id:
        return await proposer.generate(
            datasource_id=request.datasource_id,
            workspace_id=request.workspace_id,
            table_names=request.table_names,
            max_tables=request.max_tables,
            domain_hint=request.domain_hint,
        )

    # No datasource_id and no Agent: workspace-level all-asset generation REQUIRES
    # the configured proposal Agent. A silent batch fallback here would produce 0
    # proposals without surfacing any error, which is easy to miss on the UI——so
    # fail loudly instead of pretending success.
    return GenerateProposalsVO(
        datasource_id=0,
        errors=[
            f"工作空间 {request.workspace_id or 'default'} 未配置提案 Agent"
            "(proposal_agent_id),无法为全部资产生成提案;"
            "请先在 ECP 设置中配置提案 Agent"
        ],
    )


async def _deliver(result: str) -> str:
    """交付协程:resume 返回的人行摘要直接作为 result(落为 result_preview)。

    引擎 ``_run_task`` 会 ``await deliver(resume_result)`` 并把返回值写入
    ``state.result``;to_record 据此生成 result_preview。结构化解构不需要
    单独交付,resume 已写进 spec.context.artifact(落为 detail.artifact)。
    """
    return result


async def enqueue_proposal(service, request) -> str:
    """用通用异步任务引擎(AsyncTaskManager)提交提案生成任务,立即返回 task_id。

    ``kind='ecp_proposal'``。引擎统一承载生命周期(并发/超时/持久化),记录落
    ``gpts_async_tasks``(与 media-jobs 同表),前端轮询查询该表即可。resume 闭包
    执行生成,并把结构化解构写进 ``spec.context.artifact``(to_record 会落为记录的
    detail 字段),返回人行摘要(落为 result_preview)。
    """
    from gyra.agent.util.async_task_manager import AsyncTaskManager, AsyncTaskSpec

    agent_id = _resolve_agent_id(service, request)
    task_id = _task_id(request.workspace_id)
    # 结构化解构先占位,resume 完成后回填;to_record 会把 context 落为记录 detail
    result_box: dict = {}
    context: dict = {"artifact": result_box}

    async def _resume() -> str:
        result = await generate(service, request)
        if result.errors and not result.proposals_created:
            raise RuntimeError(result.errors[0])
        result_box.update(
            {
                "tables_processed": result.tables_processed,
                "proposals_created": result.proposals_created,
                "proposal_ids": result.proposal_ids,
                "errors": result.errors,
            }
        )
        return (
            f"处理 {result.tables_processed} 张表,"
            f"生成 {result.proposals_created} 条提案"
        )

    spec = AsyncTaskSpec(
        task_id=task_id,
        conv_id=request.workspace_id or "",
        kind=_ECP_TASK_KIND,
        model=agent_id or "batch",
        task_description=_describe(request),
        timeout=3600,
        context=context,
        resume=_resume,
        deliver=_deliver,
    )
    task_id = await AsyncTaskManager.media_instance().spawn(spec)
    logger.info(
        f"[ecp-proposal-runner] enqueued async task {task_id} "
        f"ws={request.workspace_id or 'default'}"
    )
    return task_id
