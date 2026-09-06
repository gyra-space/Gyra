"""专家团队 API 端点（Agent Team 空间重构 Phase 1.4）。

路由挂载在 workspace router 之下（/workspaces/{workspace_id}/experts ...）：
- 创建/更新专家：编排写入 GptsApp（身份）+ workspace_expert（成员）+ 外挂行
- 绑定：已有全局专家进空间（只写成员行 + 外挂行）
- team：团队视图；dispatch：显式派单；chat：专家直接对话会话
- 外挂引用优先对齐空间资源池（空间绑定 = 治理/权限投影）；skill/MCP 池未命中
  时回退全局注册表直引（playbook validate_references 同语义）；
  知识库/数据源等空间域资源必须先在空间「能力绑定」中绑定。
"""
import json
import logging
import re
import unicodedata
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException

from gyra.component import SystemApp
from gyra_serve.core import Result

from ..expert.expert_schemas import (
    ExpertBindRequest,
    ExpertChatRequest,
    ExpertChatResponse,
    ExpertResponse,
    ExpertUpsertRequest,
    TeamViewResponse,
)
from ..expert.expert_service import WorkspaceExpertService

logger = logging.getLogger(__name__)

router = APIRouter()

global_system_app: Optional[SystemApp] = None


def init_expert_endpoints(system_app: SystemApp) -> None:
    global global_system_app
    global_system_app = system_app


def _workspace_service():
    from ..service.service import (
        WORKSPACE_SERVICE_COMPONENT_NAME,
        WorkspaceService,
    )

    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(
        WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService
    )


def slugify_app_code(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name).strip().lower()
    slug = re.sub(r"[^\w一-鿿]+", "_", normalized).strip("_")
    return f"expert_{slug or uuid.uuid4().hex[:8]}"


def _service() -> WorkspaceExpertService:
    return WorkspaceExpertService()


def _get_app_info(app_code: str):
    """查 GptsApp 身份层信息（app_name/icon/describe/owner_workspace_id）。"""
    from gyra_serve.building.app.config import ServeConfig as AppServeConfig
    from gyra_serve.building.app.models.models import ServeDao, ServeEntity

    dao = ServeDao(serve_config=AppServeConfig())
    session = dao.get_raw_session()
    try:
        return (
            session.query(ServeEntity)
            .filter(ServeEntity.app_code == app_code)
            .first()
        )
    finally:
        session.close()


def _skill_exists_globally(skill_ref: str) -> Optional[bool]:
    """全局技能库是否存在该引用（尽力校验）。None 表示无法校验。"""
    try:
        from gyra_serve.skill.service.service import (
            SKILL_SERVICE_COMPONENT_NAME,
            Service as SkillService,
        )

        skill_service = (
            global_system_app.get_component(
                SKILL_SERVICE_COMPONENT_NAME, SkillService, default=None
            )
            if global_system_app is not None
            else None
        )
        if skill_service is None:
            return None
        return skill_service.get_by_skill_code(skill_ref) is not None
    except Exception as e:
        logger.warning(f"expert equipment: skill global check failed: {e}")
        return None


def _mcp_exists_globally(mcp_code: str) -> Optional[bool]:
    """全局 MCP 注册表是否存在该 mcp_code（尽力校验）。None 表示无法校验。"""
    try:
        from gyra_serve.agent.resource.tool.mcp_collect import get_mcp_info

        return get_mcp_info(mcp_code) is not None
    except Exception as e:
        logger.warning(f"expert equipment: mcp global check failed: {e}")
        return None


def _validate_equipment_against_pool(workspace_id: int, equipment) -> None:
    """外挂引用校验（playbook validate_references 同语义）：

    - 池命中（workspace_resource.physical_ref/name）→ 放行（空间治理投影）；
    - skill/MCP 池未命中 → 回退全局注册表，确认存在即放行（空间绑定非必需），
      确认不存在 → 400；无法校验 → 放行（尽力而为，不误伤）；
    - 其他类型（知识库/数据源等空间域资源）→ 必须先在空间绑定，否则 400。
    """
    pool = _workspace_service().list_resources(workspace_id)
    pool_keys = set()
    for rec in pool:
        if rec.is_active:
            pool_keys.add(rec.physical_ref)
            pool_keys.add(rec.name)
    dangling = []
    for item in equipment:
        if item.resource_ref in pool_keys:
            continue
        if item.resource_type in ("skill", "agent_skill"):
            exists = _skill_exists_globally(item.resource_ref)
        elif item.resource_type == "mcp":
            exists = _mcp_exists_globally(item.resource_ref)
        else:
            exists = False
        if exists is False:
            dangling.append(
                f"{item.resource_type}:{item.resource_ref}"
            )
    if dangling:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": (
                        "外挂引用不存在（skill/MCP 请先在全局注册；"
                        f"知识库/数据源请先到空间「能力绑定」绑定）: {dangling}"
                    ),
                    "type": "invalid_request_error",
                }
            },
        )


def _replace_equipment(expert_id: int, equipment) -> None:
    """全量替换式：提交列表即目标态（多余的软删除，缺的新增/复用）。"""
    service = _service()
    existing = { (e.resource_type, e.resource_ref): e
                 for e in service.list_equipment(expert_id, active_only=False) }
    wanted = {(item.resource_type, item.resource_ref) for item in equipment}
    for key, row in existing.items():
        if key not in wanted and row.is_active:
            service._equipment_dao.upsert(
                expert_id=expert_id, resource_type=row.resource_type,
                resource_ref=row.resource_ref, is_active=False,
            )
    for item in equipment:
        service.upsert_equipment(
            expert_id=expert_id,
            resource_type=item.resource_type,
            resource_ref=item.resource_ref,
            config=item.config,
            is_active=True,
        )



def _to_response(member, app_info) -> ExpertResponse:
    service = _service()
    equipment = service.list_equipment(member.id)
    return ExpertResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        app_code=member.app_code,
        app_name=getattr(app_info, "app_name", None),
        # icon：空间级覆盖优先，未覆盖回落 GptsApp 身份层
        icon=member.icon or getattr(app_info, "icon", None),
        workspace_icon=member.icon,
        app_describe=getattr(app_info, "app_describe", None),
        role_hint=member.role_hint,
        default_contract_id=member.default_contract_id,
        owner_workspace_id=getattr(app_info, "owner_workspace_id", None),
        is_active=bool(member.is_active),
        equipment=[
            {
                "resource_type": e.resource_type,
                "resource_ref": e.resource_ref,
                "config": json.loads(e.config_json) if e.config_json else {},
            }
            for e in equipment
        ],
        gmt_created=member.gmt_created.isoformat() if member.gmt_created else "",
        gmt_modified=member.gmt_modified.isoformat() if member.gmt_modified else "",
    )


# ----------------------- 专家团队 CRUD -----------------------

@router.post("/workspaces/{workspace_id}/experts/upsert",
             response_model=Result[ExpertResponse])
async def upsert_expert(workspace_id: int, request: ExpertUpsertRequest) -> Result[ExpertResponse]:
    """空间内创建/更新专家：GptsApp（身份）+ 成员行 + 外挂行 三处编排写入。

    身份区（app_name/prompt/icon）写全局 GptsApp：归属本空间的专家直接保存；
    全局/他空间专家的身份修改由前端先提示影响范围后放行（接口不阻断）。
    """
    try:
        app_code = request.app_code or slugify_app_code(request.app_name)
        app_info = _get_app_info(app_code)

        # 1. GptsApp 身份层（不存在则创建；存在则仅更新身份字段）
        from gyra_serve.building.app.config import ServeConfig as AppServeConfig
        from gyra_serve.building.app.models.models import ServeDao, ServeEntity

        app_dao = ServeDao(serve_config=AppServeConfig())
        session = app_dao.get_raw_session()
        try:
            row = session.query(ServeEntity).filter(
                ServeEntity.app_code == app_code).first()
            if row is None:
                row = ServeEntity(
                    app_code=app_code,
                    app_name=request.app_name,
                    app_describe=request.app_describe or request.app_name,
                    language="zh",
                    team_mode="auto_plan",
                    icon=request.icon,
                    published="true" if request.published else "false",
                    agent_version="v2",
                    owner_workspace_id=workspace_id,
                )
                session.add(row)
            else:
                row.app_name = request.app_name
                if request.app_describe:
                    row.app_describe = request.app_describe
                if request.icon:
                    row.icon = request.icon
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        # 人设落库:gpts_app_detail.prompt_template（身份层；与详情版本链路对齐,
        # 未接入版本表时直接写 detail 当前版本,保证"选择模板/从零构建"可编辑人设）
        if request.system_prompt_template:
            try:
                from gyra_serve.building.app.models.models_details import (
                    AppDetailServeDao,
                    AppDetailServeEntity,
                )

                detail_dao = AppDetailServeDao(serve_config=AppServeConfig())
                detail_session = detail_dao.get_raw_session()
                try:
                    detail_row = detail_session.query(AppDetailServeEntity).filter(
                        AppDetailServeEntity.app_code == app_code
                    ).first()
                    if detail_row:
                        detail_row.prompt_template = request.system_prompt_template
                        detail_row.agent_name = request.app_name
                        detail_row.agent_describe = request.app_describe or request.app_name
                    else:
                        detail_session.add(AppDetailServeEntity(
                            app_code=app_code,
                            app_name=request.app_name,
                            type="agent",
                            agent_name=request.app_name,
                            agent_role="expert",
                            agent_describe=request.app_describe or request.app_name,
                            node_id=app_code,
                            resources="[]",
                            prompt_template=request.system_prompt_template,
                        ))
                    detail_session.commit()
                except Exception:
                    detail_session.rollback()
                    raise
                finally:
                    detail_session.close()
            except Exception:
                logger.exception("expert upsert: write system_prompt_template failed (non-fatal)")

        # 2. 成员行（workspace_icon 仅写成员行，不动全局身份）
        service = _service()
        member = service.upsert_member(
            workspace_id=workspace_id,
            app_code=app_code,
            role_hint=request.role_hint,
            default_contract_id=request.default_contract_id,
            icon=request.workspace_icon,
        )

        # 3. 外挂行（校验空间池后全量替换）
        _validate_equipment_against_pool(workspace_id, request.equipment)
        _replace_equipment(member.id, request.equipment)

        return Result.succ(_to_response(member, _get_app_info(app_code)))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("expert upsert exception!")
        return Result.failed(str(e))


@router.post("/workspaces/{workspace_id}/experts/bind",
             response_model=Result[ExpertResponse])
async def bind_expert(workspace_id: int, request: ExpertBindRequest) -> Result[ExpertResponse]:
    """把已存在的全局专家绑定进空间（只写成员行 + 外挂行，不动身份）。"""
    try:
        app_info = _get_app_info(request.app_code)
        if app_info is None:
            return Result.failed(f"专家不存在: {request.app_code}")
        _validate_equipment_against_pool(workspace_id, request.equipment)
        service = _service()
        member = service.upsert_member(
            workspace_id=workspace_id,
            app_code=request.app_code,
            role_hint=request.role_hint,
            default_contract_id=request.default_contract_id,
            icon=request.icon,
        )
        _replace_equipment(member.id, request.equipment)
        return Result.succ(_to_response(member, app_info))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("expert bind exception!")
        return Result.failed(str(e))


@router.post("/workspaces/{workspace_id}/experts/unbind",
             response_model=Result[bool])
async def unbind_expert(workspace_id: int, app_code: str) -> Result[bool]:
    """解绑：成员行与外挂行软删除（身份 GptsApp 保留，可再绑定）。"""
    try:
        service = _service()
        member = service.get_member_by_app_code(workspace_id, app_code)
        if member is None:
            return Result.failed(f"专家未绑定本空间: {app_code}")
        service.upsert_member(workspace_id=workspace_id, app_code=app_code,
                              is_active=False)
        for e in service.list_equipment(member.id):
            service._equipment_dao.upsert(
                expert_id=member.id, resource_type=e.resource_type,
                resource_ref=e.resource_ref, is_active=False,
            )
        return Result.succ(True)
    except Exception as e:
        logger.exception("expert unbind exception!")
        return Result.failed(str(e))


@router.get("/workspaces/{workspace_id}/experts",
            response_model=Result[list])
async def list_experts(workspace_id: int) -> Result[list]:
    """空间专家团队列表（成员 + 身份摘要 + 外挂）。"""
    try:
        service = _service()
        members = service.list_members(workspace_id)
        return Result.succ([
            _to_response(m, _get_app_info(m.app_code)).dict() for m in members
        ])
    except Exception as e:
        logger.exception("expert list exception!")
        return Result.failed(str(e))


@router.get("/workspaces/{workspace_id}/team",
            response_model=Result[TeamViewResponse])
async def team_view(workspace_id: int) -> Result[TeamViewResponse]:
    """团队视图：Leader + 各专家（含外挂摘要）。"""
    try:
        ws = _workspace_service().get_by_id(workspace_id)
        service = _service()
        members = service.list_members(workspace_id)
        return Result.succ(TeamViewResponse(
            workspace_id=workspace_id,
            leader_app_code=getattr(ws, "default_agent_app_code", None),
            experts=[_to_response(m, _get_app_info(m.app_code)) for m in members],
        ))
    except Exception as e:
        logger.exception("team view exception!")
        return Result.failed(str(e))


@router.post("/workspaces/{workspace_id}/experts/chat",
             response_model=Result[ExpertChatResponse])
async def expert_chat(
    workspace_id: int, request: ExpertChatRequest
) -> Result[ExpertChatResponse]:
    """专家直接对话：创建 workspace 级会话（task_id=NULL，config 记专家）。"""
    try:
        service = _service()
        member = service.get_member_by_app_code(workspace_id, request.app_code)
        if member is None:
            return Result.failed(f"专家未绑定本空间: {request.app_code}")

        from ..models.models import WorkspaceConversationLinkDao

        conv_uid = f"expert_chat_{uuid.uuid4().hex[:16]}"
        title = request.title or f"与 {request.app_code} 的对话"
        WorkspaceConversationLinkDao().link(
            workspace_id=workspace_id,
            conv_uid=conv_uid,
            task_id=None,
            user_id=request.user_id,
            title=title,
        )
        return Result.succ(ExpertChatResponse(
            conv_uid=conv_uid, app_code=request.app_code, title=title,
        ))
    except Exception as e:
        logger.exception("expert chat exception!")
        return Result.failed(str(e))


@router.get("/workspaces/{workspace_id}/contracts",
            response_model=Result[list])
async def list_contracts(workspace_id: int) -> Result[list]:
    """交付合约只读视图（playbook 表收窄语义：deliverables/distill）。"""
    try:
        from gyra_serve.playbook.models.models import PlaybookDao, PlaybookEntity

        dao = PlaybookDao()
        session = dao.get_raw_session()
        try:
            rows = (
                session.query(PlaybookEntity)
                .filter(PlaybookEntity.workspace_id == workspace_id)
                .all()
            )
            contracts = []
            for row in rows:
                declaration = {}
                if row.declaration_dsl_json:
                    try:
                        declaration = json.loads(row.declaration_dsl_json)
                    except Exception:
                        declaration = {}
                contracts.append({
                    "id": row.id,
                    "name": row.name,
                    "target_app_code": row.target_app_code,
                    "deliverables": declaration.get("deliverables") or [],
                    "distill": declaration.get("distill") or {},
                    "is_active": bool(row.is_active),
                })
            return Result.succ(contracts)
        finally:
            session.close()
    except Exception as e:
        logger.exception("contracts list exception!")
        return Result.failed(str(e))

