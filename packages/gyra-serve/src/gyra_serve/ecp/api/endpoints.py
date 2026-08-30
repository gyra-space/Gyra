"""ECP API endpoints.

Mounted under /api/v1/serve/ecp. Covers the confirmation inbox, object
catalog browsing, version history, confirmer management and proposal
generation (DB asset path).
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from gyra.component import SystemApp
from gyra_serve.core import Result

from ..api.schemas import (
    AlignmentDecideRequest,
    AlignmentManualRequest,
    AssetRefRegisterRequest,
    AssetRefVO,
    CatalogEntryVO,
    ConfirmRequest,
    ConfirmerCreateRequest,
    ConfirmerVO,
    DebugPreviewRequest,
    DebugPreviewVO,
    DeprecateRequest,
    EcpImportRequest,
    EcpImportResultVO,
    GenerateProposalsRequest,
    GenerateProposalsTaskVO,
    GenerateProposalsVO,
    GraphVO,
    MissDetailVO,
    OpLogVO,
    ProposalViewVO,
    ProposeRequest,
    ReadinessVO,
    RejectRequest,
    SemanticAlignmentVO,
    SemanticObjectListVO,
    SemanticObjectVO,
    SpaceInfoVO,
    SqlAddRequest,
    SqlAddVO,
    WorkspaceConfigUpdateRequest,
    WorkspaceConfigVO,
)
from ..config import SERVE_SERVICE_COMPONENT_NAME, ServeConfig
from ..service.service import Service

logger = logging.getLogger(__name__)

router = APIRouter()

global_system_app: Optional[SystemApp] = None


def get_service() -> Service:
    """Get the service instance."""
    return global_system_app.get_component(SERVE_SERVICE_COMPONENT_NAME, Service)


# ------------------------------------------------------------------ proposals
@router.post("/objects/propose", response_model=Result[SemanticObjectVO])
async def propose_object(
    request: ProposeRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticObjectVO]:
    """Create a proposal (write rule 1: always lands in proposed)."""
    try:
        vo = service.propose(
            object_id=request.id,
            obj_type=request.obj_type,
            payload=request.payload,
            workspace_id=request.workspace_id,
            confidence=request.confidence,
            evidence=request.evidence,
            created_by=request.created_by,
            source=request.source,
            provenance=request.provenance,
        )
        return Result.succ(vo)
    except ValueError as e:
        return Result.failed(msg=str(e))


@router.post("/objects/manual", response_model=Result[SqlAddVO])
async def add_from_sql(
    request: SqlAddRequest,
    service: Service = Depends(get_service),
) -> Result[SqlAddVO]:
    """给 SQL 直接添加语义(添加即确认)。

    用户只需给一条 SQL(可附说明),其余(type/id/payload)由已配置的提案 Agent 提炼,
    提炼结果直接落库为 confirmed,不经待确认收件箱。需工作空间已配置 proposal_agent_id。
    """
    try:
        data = await service.add_from_sql(
            sql=request.sql,
            workspace_id=request.workspace_id,
            description=request.description,
            user_id=request.user_id,
            confirm=request.confirm,
        )
        return Result.succ(SqlAddVO(**data))
    except ValueError as e:
        return Result.failed(msg=str(e))


# 上传文件大小上限:文件落盘后由 Agent 用 read_report_file 分段读取,
# 不受提示词长度约束;50MB 对 SQL/代码脚本已非常宽松
_MAX_IMPORT_FILE_BYTES = 50 * 1024 * 1024


@router.post("/objects/manual/file", response_model=Result[GenerateProposalsTaskVO])
async def import_from_file(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    service: Service = Depends(get_service),
) -> Result[GenerateProposalsTaskVO]:
    """导入报表文件(SQL 脚本/代码),异步提炼语义提案(默认进待确认收件箱)。

    文件落盘到 ECP 导入目录,Agent 用 read_report_file 工具分段通读全文,
    整理学习出全部可识别的 metric/entity/dimension 提案。接口立即返回 task_id,
    前端轮询 GET /proposals/tasks/{task_id} 获取进度与结果。
    需工作空间已配置 proposal_agent_id。
    """
    import os
    import uuid

    from ..config import ecp_import_dir
    from ..service.proposal_runner import enqueue_file_import

    original = os.path.basename(file.filename or "report.sql")
    name_part, ext = os.path.splitext(original)
    saved_name = f"{name_part}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(ecp_import_dir(), saved_name)

    size = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > _MAX_IMPORT_FILE_BYTES:
                    break
                f.write(chunk)
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] save import file failed")
        _silent_unlink(file_path)
        return Result.failed(msg=f"保存上传文件失败: {e}")
    if size > _MAX_IMPORT_FILE_BYTES:
        _silent_unlink(file_path)
        return Result.failed(
            msg=f"文件过大(上限 {_MAX_IMPORT_FILE_BYTES // (1024 * 1024)}MB)"
        )
    if size == 0:
        _silent_unlink(file_path)
        return Result.failed(msg="文件内容为空")

    try:
        task_id = await enqueue_file_import(
            service,
            file_name=original,
            file_path=file_path,
            workspace_id=workspace_id,
            description=description,
        )
    except ValueError as e:
        _silent_unlink(file_path)
        return Result.failed(msg=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] enqueue file import task failed")
        _silent_unlink(file_path)
        return Result.failed(msg=f"提交文件导入任务失败: {e}")
    return Result.succ(GenerateProposalsTaskVO(task_id=task_id))


def _silent_unlink(path: str) -> None:
    import os

    try:
        os.unlink(path)
    except OSError:
        pass


@router.post("/proposals/generate", response_model=Result[GenerateProposalsTaskVO])
async def generate_proposals(
    request: GenerateProposalsRequest,
    service: Service = Depends(get_service),
) -> Result[GenerateProposalsTaskVO]:
    """Generate semantic proposals asynchronously.

    提案生成是真异步任务:立即返回 task_id 并在后台执行(agent 路径或 batch 路径),
    前端轮询 ``GET /proposals/tasks/{task_id}`` 获取进度与最终结果。这样全资产生成
    (agent ReAct 循环常达数分钟)不再受 HTTP 请求超时约束。任务记录持久化到
    ``gpts_async_tasks``(与 media-jobs 同表),跨进程/重启可见。
    """
    from ..service.proposal_runner import enqueue_proposal

    try:
        task_id = await enqueue_proposal(service, request)
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] enqueue proposal task failed")
        return Result.failed(msg=f"提交提案生成任务失败: {e}")
    return Result.succ(GenerateProposalsTaskVO(task_id=task_id))


@router.get("/proposals/tasks/{task_id}")
async def get_proposal_task(task_id: str) -> Result[dict]:
    """查询一个异步提案生成任务的状态与结果(投递物在 artifact 中)。"""
    try:
        from gyra_serve.agent.db.async_task_db import AsyncTaskDao

        job = AsyncTaskDao().get(task_id)
        if job is None:
            return Result.failed(msg=f"async proposal task {task_id} not found")
        return Result.succ(job)
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] query proposal task failed")
        return Result.failed(msg=str(e))


# -------------------------------------------------------------------- inbox
@router.get("/inbox", response_model=Result[SemanticObjectListVO])
async def inbox(
    workspace_id: Optional[str] = Query(default=None),
    obj_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    include_view: bool = Query(default=True),
    service: Service = Depends(get_service),
) -> Result[SemanticObjectListVO]:
    """Confirmation inbox: latest proposed versions.

    ``include_view``(默认开):每项挂业务视图(一句话口径/来源徽章/血缘
    chips)——收件箱卡片直接消费,不再由前端拼 payload。
    """
    return Result.succ(
        service.inbox(
            workspace_id=workspace_id, obj_type=obj_type,
            page=page, page_size=page_size, include_view=include_view,
        )
    )


@router.post(
    "/objects/{object_id}/versions/{version}/confirm",
    response_model=Result[SemanticObjectVO],
)
async def confirm_object(
    object_id: str,
    version: int,
    request: ConfirmRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticObjectVO]:
    """Confirm a proposed version (optionally with an edited payload)."""
    try:
        vo = service.confirm(
            object_id=object_id,
            version=version,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            edited_payload=request.edited_payload,
        )
        return Result.succ(vo)
    except (ValueError, PermissionError) as e:
        return Result.failed(msg=str(e))


@router.post(
    "/objects/{object_id}/versions/{version}/reject",
    response_model=Result[SemanticObjectVO],
)
async def reject_object(
    object_id: str,
    version: int,
    request: RejectRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticObjectVO]:
    """Reject a proposed version."""
    try:
        vo = service.reject(
            object_id=object_id,
            version=version,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            reason=request.reason,
        )
        return Result.succ(vo)
    except (ValueError, PermissionError) as e:
        return Result.failed(msg=str(e))


@router.post("/objects/{object_id}/deprecate", response_model=Result[SemanticObjectVO])
async def deprecate_object(
    object_id: str,
    request: DeprecateRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticObjectVO]:
    """Deprecate the confirmed version of an object."""
    try:
        vo = service.deprecate(
            object_id=object_id,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            reason=request.reason,
        )
        return Result.succ(vo)
    except (ValueError, PermissionError) as e:
        return Result.failed(msg=str(e))


# --------------------------------------------------------------------- reads
@router.get("/objects", response_model=Result[SemanticObjectListVO])
async def list_objects(
    workspace_id: Optional[str] = Query(default=None),
    obj_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    include_view: bool = Query(default=True),
    service: Service = Depends(get_service),
) -> Result[SemanticObjectListVO]:
    """Browse latest versions of semantic objects."""
    return Result.succ(
        service.list_objects(
            workspace_id=workspace_id,
            obj_type=obj_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
            include_view=include_view,
        )
    )


@router.get("/objects/{object_id}", response_model=Result[SemanticObjectVO])
async def get_object(
    object_id: str,
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[SemanticObjectVO]:
    vo = service.get_object(object_id, workspace_id=workspace_id)
    if not vo:
        return Result.failed(msg=f"Object {object_id} not found")
    return Result.succ(vo)


@router.get(
    "/objects/{object_id}/versions", response_model=Result[List[SemanticObjectVO]]
)
async def version_history(
    object_id: str,
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[List[SemanticObjectVO]]:
    return Result.succ(service.version_history(object_id, workspace_id=workspace_id))


@router.get(
    "/objects/{object_id}/versions/{version}/view",
    response_model=Result[ProposalViewVO],
)
async def proposal_view(
    object_id: str,
    version: int,
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[ProposalViewVO]:
    """单个版本的完整业务视图(详情页数据源)。

    读时派生:一句话口径 / 来源(MISS 学习带原始 SQL 快照) / 库表字段
    血缘 / 静态 SQL 组装效果 / 契约化证据引文。
    """
    try:
        return Result.succ(
            service.get_proposal_view(object_id, version, workspace_id)
        )
    except ValueError as e:
        return Result.failed(msg=str(e))


@router.get("/contracts", response_model=Result[dict])
async def payload_contracts() -> Result[dict]:
    """各对象类型的 payload 契约清单(前端编辑表单的单一事实来源)。"""
    from ..service.contracts import contract_spec

    return Result.succ(contract_spec())


@router.post(
    "/objects/{object_id}/versions/{version}/debug",
    response_model=Result[DebugPreviewVO],
)
async def debug_preview(
    object_id: str,
    version: int,
    request: DebugPreviewRequest,
    service: Service = Depends(get_service),
) -> Result[DebugPreviewVO]:
    """确认页调试验证:按提案版本只读 dry-run(试跑真实数据)。

    纯读、不落库、不改状态;结果 trust=preview,**永不** verified——仅供确认人
    在确认前核对提案的计算规则/口径是否拿到预期数据。文档类(claim/
    terminology/policy)走 anchor 出处校验;其余(metric/entity/dimension/
    relation)按 payload 组装 SQL 试跑。
    """
    from ..service.executor import DocBindingExecutor

    obj = service.get_version(object_id, version, request.workspace_id)
    if not obj:
        return Result.failed(msg=f"对象 {object_id}@v{version} 不存在")
    try:
        if obj.obj_type in DocBindingExecutor._DOC_TYPES:
            vo = await service.preview_canon(
                object_id, version, workspace_id=request.workspace_id
            )
        else:
            vo = service.preview_query(
                object_id=object_id,
                version=version,
                workspace_id=request.workspace_id,
                filters=request.filters,
                group_by=request.group_by,
                time_range=request.time_range,
                limit=request.limit,
            )
        return Result.succ(vo)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp] debug preview failed: {e}")
        return Result.failed(msg=f"试跑失败: {e}")


@router.get("/catalog", response_model=Result[List[CatalogEntryVO]])
async def catalog(
    workspace_id: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[List[CatalogEntryVO]]:
    """Confirmed-only catalog (write rule 4) for prompt injection / search."""
    return Result.succ(service.catalog(workspace_id=workspace_id, keyword=keyword))


# --------------------------------------------------------------------- admin
@router.get("/admin/contract_check", response_model=Result[dict])
async def contract_check(
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[dict]:
    """扫描 confirmed 对象的 payload 契约合规性(只读)。

    不合规对象会让 execute_metric_query 门禁拒绝(PAYLOAD_INVALID)——
    "已确认但不可执行"问题的体检入口。
    """
    return Result.succ(service.contract_check(workspace_id=workspace_id))


@router.post("/admin/normalize", response_model=Result[dict])
async def normalize_confirmed(
    workspace_id: Optional[str] = Query(default=None),
    user_id: str = Query(default="system"),
    service: Service = Depends(get_service),
) -> Result[dict]:
    """一键修复不合规 confirmed 对象(契约归一化,写新版本)。

    走应用自己的 DAO/版本化写入(create_confirmed_version),不外部直改库——
    规避外部写 WAL 竞态导致的数据回退。normalize 无法补的(如缺 entity
    引用)列入 skipped,需人工编辑后走 confirm 流程。
    """
    return Result.succ(
        service.normalize_confirmed(workspace_id=workspace_id, user_id=user_id)
    )


@router.get("/admin/miss_report", response_model=Result[dict])
async def miss_report(
    workspace_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: Service = Depends(get_service),
) -> Result[dict]:
    """miss 聚类报告:execute_raw_sql 兜底记录按归一化 SQL 模式分组计数。

    "大家在裸查什么"的可见化——高频 miss 是语义目录最需要覆盖的真实问题,
    也是 learn_from_misses 的输入(召回飞轮的学习侧)。
    """
    return Result.succ(service.miss_report(workspace_id=workspace_id, limit=limit))


@router.get("/admin/miss_detail", response_model=Result[MissDetailVO])
async def miss_detail(
    kind: str = Query(...),
    pattern: str = Query(...),
    datasource_id: Optional[int] = Query(default=None),
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[MissDetailVO]:
    """单个 miss 聚类的学习档案(飞轮视图点击聚类行展开 Drawer 用)。

    聚合聚类摘要、原始兜底记录、已学习标记与标记生命周期事件,
    前端据此渲染"这条问题从兜底到沉淀"的学习轨迹时间线。
    """
    return Result.succ(
        service.miss_detail(
            kind=kind,
            pattern=pattern,
            datasource_id=datasource_id,
            workspace_id=workspace_id,
        )
    )


@router.get("/admin/miss_learned", response_model=Result[list])
async def miss_learned(
    workspace_id: Optional[str] = Query(default=None),
    kind: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[list]:
    """列出工作空间已学习的 miss 标记(落盘回写表,按学习时间倒序)。

    用于观察飞轮学习侧记住了哪些聚类,以及核对是否应清除(clear)后重新曝光。
    """
    items = service.list_miss_learned(workspace_id=workspace_id, kind=kind)
    return Result.succ(
        [
            {
                "id": it.id,
                "workspace_id": it.workspace_id,
                "kind": it.kind,
                "datasource_id": it.datasource_id,
                "pattern": it.pattern,
                "example": it.example,
                "proposal_ids": it.proposal_ids,
                "trigger": it.trigger,
                "learned_at": it.learned_at,
            }
            for it in items
        ]
    )


@router.delete("/admin/miss_learned", response_model=Result[int])
async def clear_miss_learned(
    workspace_id: Optional[str] = Query(default=None),
    kind: Optional[str] = Query(default=None),
    pattern: Optional[str] = Query(default=None),
    datasource_id: Optional[int] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[int]:
    """清除已学习标记,允许对应 miss 聚类重新曝光(重新进入 miss 报告)。"""
    removed = service.clear_miss_learned(
        workspace_id=workspace_id, kind=kind, pattern=pattern,
        datasource_id=datasource_id,
    )
    return Result.succ(removed)


@router.post("/admin/learn_from_misses", response_model=Result[GenerateProposalsVO])
async def learn_from_misses(
    workspace_id: Optional[str] = Query(default=None),
    top: int = Query(default=10, ge=1, le=50),
    service: Service = Depends(get_service),
) -> Result[GenerateProposalsVO]:
    """从 miss 学习:高频未覆盖问题喂给提案 agent,生成的提案进收件箱。

    闭环:fallback miss(op_log)→ 聚类 → 提案 agent(带 miss 上下文)→
    提案进收件箱 → 人工 confirm → 目录覆盖增长 → 后续同类问题走可信路径。
    需要工作空间已配置 proposal_agent_id(ECP 设置)。
    """
    ws = workspace_id or None
    try:
        cfg = service.get_workspace_config(ws)
        agent_id = getattr(cfg, "proposal_agent_id", None) if cfg else None
    except Exception:  # noqa: BLE001
        agent_id = None
    if not agent_id:
        return Result.failed(
            msg="工作空间未配置提案 Agent(proposal_agent_id),"
            "请先在 ECP 设置中配置后再从 miss 学习"
        )

    report = service.miss_report(workspace_id=ws, limit=top)
    if not report["clusters"]:
        return Result.failed(msg="暂无 fallback miss 记录,无需学习")
    fed_clusters = report["clusters"]
    miss_context = Service.build_miss_context(fed_clusters, max_items=top)

    from ..service.proposal_runner import run_proposal_agent

    result = await run_proposal_agent(
        system_app=service._system_app,
        app_code=agent_id,
        workspace_id=ws,
        domain_hint=miss_context,
    )
    # 落盘回写:本次喂给 agent 学习的聚类标记为"已学习",避免每日重复曝光。
    # 若运行失败且无任何产出则跳过(允许下次重试);否则记录学习,已覆盖的
    # 概念不再反复出现。触发来源记为 learn_from_misses。
    if result.proposals_created > 0 or not result.errors:
        service.mark_miss_learned(
            fed_clusters, workspace_id=ws,
            proposal_ids=result.proposal_ids, trigger="learn_from_misses",
        )
    return Result.succ(result)


# ----------------------------------------------------------------- confirmers
@router.get("/confirmers", response_model=Result[List[ConfirmerVO]])
async def list_confirmers(
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[List[ConfirmerVO]]:
    return Result.succ(service.list_confirmers(workspace_id=workspace_id))


@router.post("/confirmers", response_model=Result[bool])
async def add_confirmer(
    request: ConfirmerCreateRequest,
    service: Service = Depends(get_service),
) -> Result[bool]:
    service.add_confirmer(
        user_id=request.user_id,
        workspace_id=request.workspace_id,
        scope=request.scope,
    )
    return Result.succ(True)


@router.delete("/confirmers/{confirmer_id}", response_model=Result[bool])
async def remove_confirmer(
    confirmer_id: int,
    service: Service = Depends(get_service),
) -> Result[bool]:
    return Result.succ(service.remove_confirmer(confirmer_id))


# -------------------------------------------------------------------- op log
@router.get("/op-log", response_model=Result[List[OpLogVO]])
async def op_log(
    workspace_id: Optional[str] = Query(default=None),
    op: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: Service = Depends(get_service),
) -> Result[List[OpLogVO]]:
    return Result.succ(
        service.list_op_log(
            workspace_id=workspace_id, op=op, page=page, page_size=page_size
        )
    )


# -------------------------------------------------------------- asset refs
@router.post("/assets", response_model=Result[AssetRefVO])
async def register_asset(
    request: AssetRefRegisterRequest,
    service: Service = Depends(get_service),
) -> Result[AssetRefVO]:
    """Register an original-asset reference (idempotent)."""
    try:
        return Result.succ(
            service.register_asset(
                kind=request.kind,
                ref_id=request.ref_id,
                workspace_id=request.workspace_id,
                ref_meta=request.ref_meta,
            )
        )
    except Exception as e:  # noqa: BLE001
        return Result.failed(msg=str(e))


@router.get("/assets", response_model=Result[List[AssetRefVO]])
async def list_assets(
    workspace_id: Optional[str] = Query(default=None),
    kind: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[List[AssetRefVO]]:
    return Result.succ(service.list_assets(workspace_id=workspace_id, kind=kind))


@router.delete("/assets/{asset_id}", response_model=Result[bool])
async def remove_asset(
    asset_id: int,
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[bool]:
    """Unregister an asset reference from a workspace.

    ECP owns only the reference, so this does NOT delete the original asset
    (DB / space / document) — it just removes it from the workspace's asset
    list. The original asset must be deleted in its owning module.
    """
    try:
        ok = service.remove_asset(asset_id, workspace_id=workspace_id)
        if not ok:
            return Result.failed(msg=f"Asset ref {asset_id} not found in workspace")
        return Result.succ(True)
    except Exception as e:  # noqa: BLE001
        return Result.failed(msg=str(e))


@router.get("/readiness", response_model=Result[ReadinessVO])
async def readiness(
    datasource_id: int = Query(...),
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[ReadinessVO]:
    """Check whether a DB asset's material is complete for proposals."""
    return Result.succ(
        service.readiness(datasource_id, workspace_id=workspace_id)
    )


# --------------------------------------------------------------------- graph
@router.get("/graph", response_model=Result[GraphVO])
async def graph(
    workspace_id: Optional[str] = Query(default=None),
    entity: Optional[str] = Query(
        default=None,
        description=(
            "按实体检索:命中节点(id/name/别名归一匹配)及其一跳邻域,"
            "含 kn 实体→语义对象的 aligns_to 对齐边"
        ),
    ),
    service: Service = Depends(get_service),
) -> Result[GraphVO]:
    """Asset-panorama graph: objects + registered assets + knowledge-layer
    nodes, with materialized semantic edges and aggregated knowledge edges.

    ``entity`` given → focus view: matched node(s) + 1-hop neighborhood
    (e.g. object ↔ aligned kn entity ↔ wiki docs) in a single call.
    """
    return Result.succ(
        await service.graph(workspace_id=workspace_id, entity=entity)
    )


@router.post("/graph/rebuild", response_model=Result[dict])
async def rebuild_graph(
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[dict]:
    """Idempotently rebuild the materialized edge projection of a workspace.

    Use after projection-rule upgrades or when assets were registered after
    their objects (edges pointing to assets are only emitted on write; a
    rebuild back-fills them for existing objects).
    """
    try:
        return Result.succ(service.rebuild_edges(workspace_id=workspace_id))
    except Exception as e:  # noqa: BLE001
        return Result.failed(msg=str(e))


# ------------------------------------------------- semantic alignment
@router.post("/graph/alignments/run", response_model=Result[dict])
async def run_alignment(
    workspace_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[dict]:
    """触发 LLM 语义对齐:知识实体 × 硬层对象 → 推理候选入库(待确认)。

    同步执行(LLM 批量推理,实体多时耗时数十秒到分钟级);候选一律
    proposed,不自动上图生效——confirm 后才生效。人工已决定
    (confirmed/rejected)的实体不重复推理。LLM 未配置时返回错误信息,
    可走手工添加兜底(POST /graph/alignments)。
    """
    try:
        return Result.succ(
            await service.align_entities(workspace_id=workspace_id, user_id=user_id)
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] alignment run failed")
        return Result.failed(msg=f"语义对齐执行失败: {e}")


@router.get("/graph/alignments", response_model=Result[List[SemanticAlignmentVO]])
async def list_alignments(
    workspace_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(
        default=None,
        description="按状态筛选:proposed(待确认)/confirmed/rejected",
    ),
    service: Service = Depends(get_service),
) -> Result[List[SemanticAlignmentVO]]:
    """语义对齐候选/决定列表(LLM 推理产出 + 人工决定)。"""
    return Result.succ(
        service.list_alignments(workspace_id=workspace_id, status=status)
    )


@router.post("/graph/alignments", response_model=Result[SemanticAlignmentVO])
async def add_alignment(
    request: AlignmentManualRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticAlignmentVO]:
    """手工添加对齐(直通 confirmed):LLM 不可用时的确定性兜底。"""
    try:
        return Result.succ(
            await service.add_alignment(
                workspace_id=request.workspace_id,
                entity_name=request.entity_name,
                object_id=request.object_id,
                user_id=request.user_id,
            )
        )
    except ValueError as e:
        return Result.failed(msg=str(e))


@router.post(
    "/graph/alignments/{alignment_id}/confirm",
    response_model=Result[SemanticAlignmentVO],
)
async def confirm_alignment(
    alignment_id: int,
    request: AlignmentDecideRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticAlignmentVO]:
    """确认一条对齐候选:生效并在全景图上以 confirmed 样式展示。"""
    try:
        return Result.succ(
            service.confirm_alignment(alignment_id, user_id=request.user_id)
        )
    except ValueError as e:
        return Result.failed(msg=str(e))


@router.post(
    "/graph/alignments/{alignment_id}/reject",
    response_model=Result[SemanticAlignmentVO],
)
async def reject_alignment(
    alignment_id: int,
    request: AlignmentDecideRequest,
    service: Service = Depends(get_service),
) -> Result[SemanticAlignmentVO]:
    """拒绝一条对齐候选:不上图,且该实体不再被 LLM 复跑重复提案。"""
    try:
        return Result.succ(
            service.reject_alignment(alignment_id, user_id=request.user_id)
        )
    except ValueError as e:
        return Result.failed(msg=str(e))


@router.delete("/graph/alignments/{alignment_id}", response_model=Result[bool])
async def remove_alignment(
    alignment_id: int,
    service: Service = Depends(get_service),
) -> Result[bool]:
    """删除一条对齐记录(手工纠错)。"""
    return Result.succ(service.remove_alignment(alignment_id))


# --------------------------------------------------------------------- space
@router.post("/space", response_model=Result[SpaceInfoVO])
async def get_or_create_space(
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[SpaceInfoVO]:
    """Get-or-create the ECP soft-layer knowledge space (ecp-<workspace>)."""
    try:
        return Result.succ(await service.get_or_create_space(workspace_id))
    except Exception as e:  # noqa: BLE001
        return Result.failed(msg=str(e))


# -------------------------------------------------------- workspace config
@router.get("/workspace-config", response_model=Result[WorkspaceConfigVO])
async def get_workspace_config(
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[WorkspaceConfigVO]:
    """Proposal-agent / domain settings of a workspace."""
    return Result.succ(service.get_workspace_config(workspace_id))


@router.put("/workspace-config", response_model=Result[WorkspaceConfigVO])
async def save_workspace_config(
    request: WorkspaceConfigUpdateRequest,
    service: Service = Depends(get_service),
) -> Result[WorkspaceConfigVO]:
    return Result.succ(
        service.save_workspace_config(
            workspace_id=request.workspace_id,
            proposal_agent_id=request.proposal_agent_id,
        )
    )


# ---------------------------------------------------------------- 资产迁移
@router.get("/export", response_model=Result[dict])
async def export_workspace(
    workspace_id: Optional[str] = Query(default=None),
    service: Service = Depends(get_service),
) -> Result[dict]:
    """Export a workspace's semantic assets as a portable JSON snapshot.

    语义资产快照(所有版本链 + 状态 + payload + db 资产引用),用于跨系统迁移:
    导入时通过 datasource_map 重绑 datasource_id 即可直接使用。
    """
    try:
        return Result.succ(service.export_workspace(workspace_id=workspace_id))
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] export workspace failed")
        return Result.failed(msg=str(e))


@router.post("/import", response_model=Result[EcpImportResultVO])
async def import_workspace(
    request: EcpImportRequest,
    service: Service = Depends(get_service),
) -> Result[EcpImportResultVO]:
    """Import a semantic-asset snapshot (merge into a workspace)."""
    try:
        result = service.import_workspace(
            data=request.data,
            workspace_id=request.workspace_id,
            datasource_map=request.datasource_map,
        )
        return Result.succ(EcpImportResultVO(**result))
    except Exception as e:  # noqa: BLE001
        logger.exception("[ecp] import workspace failed")
        return Result.failed(msg=str(e))


# ------------------------------------------------------------- linked resources
@router.get("/linked-resources")
async def get_linked_resources(
    workspace_id: Optional[str] = Query(default=None),
) -> Result[List[dict]]:
    """Return db assets registered in an ECP workspace, for auto-binding.

    When an Agent binds an ECP resource, the frontend calls this endpoint to
    discover which datasources the workspace's proposals were built on, and
    auto-adds them to resource_tool. Returns [{datasource_id, db_name, db_type}].
    """
    from ..config import DEFAULT_WORKSPACE_ID
    from ..models.models import AssetRefDao

    ws = workspace_id or DEFAULT_WORKSPACE_ID
    try:
        assets = AssetRefDao().list(ws) or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ecp] list linked assets failed: {e}")
        return Result.succ([])

    result = []
    for a in assets:
        if a.kind != "db":
            continue
        try:
            ds_id = int(a.ref_id)
        except (TypeError, ValueError):
            continue
        db_name = (a.ref_meta or {}).get("db_name") or ""
        db_type = (a.ref_meta or {}).get("db_type") or ""
        if not db_name:
            # Fallback: resolve from ConnectConfigDao
            try:
                from gyra_serve.datasource.manages.connect_config_db import (
                    ConnectConfigDao,
                )

                cfg = ConnectConfigDao().get_one({"id": ds_id})
                db_name = getattr(cfg, "db_name", "") or ""
                db_type = getattr(cfg, "db_type", "") or ""
            except Exception:  # noqa: BLE001
                pass
        result.append(
            {"datasource_id": ds_id, "db_name": db_name, "db_type": db_type}
        )
    return Result.succ(result)


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    """Initialize the endpoints."""
    global global_system_app
    system_app.register(Service, config=config)
    global_system_app = system_app
