"""扩展介入模式服务 —— coach / escalate / reconcile / attest(P1任务7)。

与 ``InterventionService``(approve/review 阻塞阀门)互补,落地4种非阻塞或
半阻塞的评委动作。所有模式都创建 Intervention 记录,便于审计追踪。

设计要点:
- coach / attest 非阻塞:创建即 resolved,不影响主流程
- escalate 可能阻塞:status=requested,等待转交确认
- reconcile 可能阻塞:status=requested,等待对账完成(成功则自动 resolved)
- 与成熟度服务联动:coach→降级,attest→晋升

为避免循环导入,成熟度/索引/任务等服务均采用延迟导入(方法内 import)。
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from gyra.component import SystemApp

from gyra_serve.core import BaseService

from ..api.schemas import (
    AttestInterventionRequest, CoachInterventionRequest,
    EscalateInterventionRequest, InterventionResponse,
    ReconcileInterventionRequest,
)
from ..config import ServeConfig
from ..models.models import InterventionDao, InterventionEntity

EXTENDED_INTERVENTION_SERVICE_COMPONENT_NAME = "serve_intervention_extended_service"
logger = logging.getLogger(__name__)


class ExtendedInterventionService(BaseService):
    """扩展介入模式服务——coach/escalate/reconcile/attest。"""

    name = EXTENDED_INTERVENTION_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        dao: Optional[InterventionDao] = None,
    ):
        self._system_app = None
        self._serve_config: ServeConfig = config
        self._dao: InterventionDao = dao
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or InterventionDao()
        self._system_app = system_app

    @property
    def dao(self) -> InterventionDao:
        return self._dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    # ------------------------------------------------------------------ #
    # coach: 纠偏(非阻塞,创建即resolved)
    # ------------------------------------------------------------------ #
    async def create_coach(self, req: CoachInterventionRequest) -> InterventionResponse:
        """创建coach纠偏介入记录。

        - 有 asset_id 时联动 AssetMaturityService.coach()(minor仅记录/major降一级/critical降到draft)
        - 非阻塞:status=resolved
        """
        context: Dict[str, Any] = {
            "mode": "coach",
            "agent_id": req.agent_id,
            "asset_id": req.asset_id,
            "coach_note": req.coach_note,
            "severity": req.severity,
            "user_id": req.user_id,
        }
        now = datetime.now()
        entity = self._dao.create(
            workspace_id=req.workspace_id,
            task_id=req.task_id,
            type="coach",
            status="resolved",
            requested_by=str(req.user_id),
            linked_asset_id=req.asset_id,
            context_json=context,
            resolved_by_user_id=req.user_id,
            resolved_at=now,
        )

        # 联动成熟度服务:coach 降级
        if req.asset_id is not None:
            try:
                from gyra_serve.workspace_asset.service.maturity import (
                    MATURITY_SERVICE_COMPONENT_NAME, AssetMaturityService,
                )
                maturity: AssetMaturityService = self._system_app.get_component(
                    MATURITY_SERVICE_COMPONENT_NAME, AssetMaturityService,
                )
                await maturity.coach(
                    asset_id=req.asset_id,
                    user_id=str(req.user_id),
                    coach_note=req.coach_note,
                    severity=req.severity,
                )
            except Exception as e:
                logger.warning(
                    "coach maturity link failed for asset %s: %s",
                    req.asset_id, e, exc_info=True,
                )

        return self._dao.to_response(entity)

    # ------------------------------------------------------------------ #
    # escalate: 升级(可能阻塞,等待转交确认)
    # ------------------------------------------------------------------ #
    async def create_escalate(self, req: EscalateInterventionRequest) -> InterventionResponse:
        """创建escalate升级介入。

        - status=requested(阻塞,等待转交确认)
        - 发布事件通知(workspace event + inbox 待办)
        - 实际任务转交在 resolve 阶段执行(转交确认)
        """
        context: Dict[str, Any] = {
            "mode": "escalate",
            "from_agent_id": req.from_agent_id,
            "to_agent_id": req.to_agent_id,
            "reason": req.reason,
            "urgency": req.urgency,
            "user_id": req.user_id,
        }
        entity = self._dao.create(
            workspace_id=req.workspace_id,
            task_id=req.task_id,
            type="escalate",
            status="requested",
            requested_by=str(req.user_id),
            context_json=context,
        )
        response = self._dao.to_response(entity)

        # 发布 workspace 事件通知前端
        self._emit_workspace_event(
            req.workspace_id,
            "intervention.escalate",
            {
                "intervention_id": response.id,
                "task_id": req.task_id,
                "from_agent_id": req.from_agent_id,
                "to_agent_id": req.to_agent_id,
                "reason": req.reason,
                "urgency": req.urgency,
            },
        )
        # 给 workspace owner 写待办(等待转交确认)
        self._sync_inbox_create(response, title=f"升级确认: {req.reason[:50]}")
        return response

    # ------------------------------------------------------------------ #
    # reconcile: 对账(可能阻塞,等待对账完成)
    # ------------------------------------------------------------------ #
    async def create_reconcile(self, req: ReconcileInterventionRequest) -> InterventionResponse:
        """创建reconcile对账介入。

        - status=requested(阻塞)
        - 触发对账逻辑:调用 AssetIndexService.reconcile() 修复索引不一致
        - 对账无错误则自动 resolved;有错误保持 requested 等待人工介入
        """
        context: Dict[str, Any] = {
            "mode": "reconcile",
            "task_id": req.task_id,
            "data_sources": req.data_sources,
            "reconciliation_type": req.reconciliation_type,
        }
        entity = self._dao.create(
            workspace_id=req.workspace_id,
            task_id=req.task_id,
            type="reconcile",
            status="requested",
            requested_by="system",
            context_json=context,
        )

        # 触发对账逻辑(调用索引服务对账)
        decision: Dict[str, Any] = {}
        auto_resolved = False
        try:
            from gyra_serve.workspace_asset.service.index_service import (
                INDEX_SERVICE_COMPONENT_NAME, AssetIndexService,
            )
            index_svc: AssetIndexService = self._system_app.get_component(
                INDEX_SERVICE_COMPONENT_NAME, AssetIndexService,
            )
            report = await index_svc.reconcile(req.workspace_id)
            decision = {
                "checked": getattr(report, "checked", 0),
                "added": getattr(report, "added", 0),
                "removed": getattr(report, "removed", 0),
                "errors": list(getattr(report, "errors", []) or []),
            }
            if not decision["errors"]:
                auto_resolved = True
        except Exception as e:
            logger.warning(
                "reconcile index link failed for ws %s: %s",
                req.workspace_id, e, exc_info=True,
            )
            decision = {"errors": [str(e)]}

        # 写回对账结果,无错误则自动 resolved
        self._update_decision_and_maybe_resolve(
            entity_id=entity.id,
            decision=decision,
            resolved=auto_resolved,
        )
        return self._get_response(entity.id)

    # ------------------------------------------------------------------ #
    # attest: 背书(非阻塞,创建即resolved)
    # ------------------------------------------------------------------ #
    async def create_attest(self, req: AttestInterventionRequest) -> InterventionResponse:
        """创建attest背书介入。

        - target_type=asset:联动 AssetMaturityService.attest()(累计attest,达标自动canonical)
        - target_type=agent:联动 AgentMaturityService.attest_agent()(若可用)
        - 非阻塞:status=resolved
        """
        context: Dict[str, Any] = {
            "mode": "attest",
            "target_type": req.target_type,
            "target_id": req.target_id,
            "note": req.note,
            "user_id": req.user_id,
        }
        now = datetime.now()
        linked_asset_id = req.target_id if req.target_type == "asset" else None
        entity = self._dao.create(
            workspace_id=req.workspace_id,
            type="attest",
            status="resolved",
            requested_by=str(req.user_id),
            linked_asset_id=linked_asset_id,
            context_json=context,
            resolved_by_user_id=req.user_id,
            resolved_at=now,
        )

        # 联动成熟度服务
        if req.target_type == "asset":
            try:
                from gyra_serve.workspace_asset.service.maturity import (
                    MATURITY_SERVICE_COMPONENT_NAME, AssetMaturityService,
                )
                maturity: AssetMaturityService = self._system_app.get_component(
                    MATURITY_SERVICE_COMPONENT_NAME, AssetMaturityService,
                )
                await maturity.attest(
                    asset_id=req.target_id,
                    user_id=str(req.user_id),
                    note=req.note,
                )
            except Exception as e:
                logger.warning(
                    "attest asset maturity link failed for asset %s: %s",
                    req.target_id, e, exc_info=True,
                )
        elif req.target_type == "agent":
            # agent 成熟度服务(若已注册则联动,否则仅记录介入供审计)
            try:
                from gyra_serve.workspace.agent_maturity import (
                    AGENT_MATURITY_SERVICE_COMPONENT_NAME, AgentMaturityService,
                )
                agent_maturity: AgentMaturityService = self._system_app.get_component(
                    AGENT_MATURITY_SERVICE_COMPONENT_NAME, AgentMaturityService,
                )
                await agent_maturity.attest_agent(
                    agent_id=str(req.target_id),
                    user_id=str(req.user_id),
                    workspace_id=req.workspace_id,
                )
            except ImportError:
                logger.info(
                    "AgentMaturityService not available, attest for agent %s recorded only",
                    req.target_id,
                )
            except Exception as e:
                logger.warning(
                    "attest agent maturity link failed for agent %s: %s",
                    req.target_id, e, exc_info=True,
                )

        return self._dao.to_response(entity)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _update_decision_and_maybe_resolve(
        self, entity_id: int, decision: Dict[str, Any], resolved: bool,
    ) -> None:
        """写回 decision_json,必要时标记 resolved。"""
        import json
        session = self._dao.get_raw_session()
        try:
            entity = session.query(InterventionEntity).filter(
                InterventionEntity.id == entity_id
            ).first()
            if not entity:
                return
            entity.decision_json = json.dumps(decision, ensure_ascii=False)
            if resolved:
                entity.status = "resolved"
                entity.resolved_at = datetime.now()
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get_response(self, entity_id: int) -> InterventionResponse:
        session = self._dao.get_raw_session()
        try:
            entity = session.query(InterventionEntity).filter(
                InterventionEntity.id == entity_id
            ).first()
            return self._dao.to_response(entity)
        finally:
            session.close()

    def _emit_workspace_event(
        self, workspace_id: int, event_type: str, payload: Dict[str, Any],
    ) -> None:
        """向 workspace 活跃对话广播事件;无活跃流时静默丢弃。"""
        try:
            from gyra_serve.workspace.event_bus import emit_workspace_event
            emit_workspace_event(workspace_id, event_type, payload)
        except Exception as e:
            logger.warning("emit workspace event failed: %s", e)

    def _sync_inbox_create(self, response: InterventionResponse, title: str) -> None:
        """阻塞型介入 -> 给 assignee(或 workspace owner 兜底)写待办。"""
        try:
            from gyra_serve.workspace.inbox import (
                INBOX_SERVICE_COMPONENT_NAME, SOURCE_INTERVENTION,
                VIS_PERSONAL, InboxService,
            )
            inbox: InboxService = self._system_app.get_component(
                INBOX_SERVICE_COMPONENT_NAME, InboxService,
            )
            assignee = getattr(response, "assignee_user_id", None)
            if assignee is None:
                assignee = self._resolve_workspace_owner(response.workspace_id)
            if assignee is None:
                return
            inbox.create_item(
                workspace_id=int(response.workspace_id),
                user_id=int(assignee),
                source_type=SOURCE_INTERVENTION,
                source_id=str(response.id),
                title=title,
                visibility=VIS_PERSONAL,
            )
        except Exception as e:
            logger.warning("extended intervention inbox sync failed: %s", e)

    def _resolve_workspace_owner(self, workspace_id):
        if not workspace_id:
            return None
        try:
            from gyra_serve.workspace.service.service import (
                WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
            )
            ws_service: WorkspaceService = self._system_app.get_component(
                WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
            )
            ws = ws_service.get_by_id(int(workspace_id))
            return getattr(ws, "owner_user_id", None) if ws else None
        except Exception:
            return None
