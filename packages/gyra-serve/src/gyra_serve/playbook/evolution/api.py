"""Playbook 演化引擎 API endpoints。

飞轮体系任务4+5: 执行轨迹与演化引擎的对外接口。
- POST /evolution/analyze: 触发分析(基于未分析轨迹生成提议)
- POST /evolution/proposals/list: 列出 pending 提议
- POST /evolution/proposals/{proposal_id}/approve: 审批通过(应用提议,创建新版本)
- POST /evolution/proposals/{proposal_id}/reject: 驳回
- GET /evolution/proposals/{proposal_id}: 查看提议详情
- GET /evolution/traces/list: 列出执行轨迹(按 playbook_id 或 workspace_id)
"""
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from gyra._private.pydantic import BaseModel, Field
from gyra.component import SystemApp
from gyra.distributed import EvolutionProposal, EvolutionResult, ExecutionTrace

from gyra_serve.core import Result

from ..config import ServeConfig
from ..service.service import PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService
from ..trace.models import PlaybookTraceDao
from .engine import DBEvolutionProposalStore, PlaybookEvolutionEngine

router = APIRouter()
global_system_app: Optional[SystemApp] = None
logger = logging.getLogger(__name__)

# 演化引擎、提议存储、轨迹 DAO 单例(进程内,由 init_endpoints 初始化)
_evolution_engine: Optional[PlaybookEvolutionEngine] = None
_proposal_store: Optional[DBEvolutionProposalStore] = None
_trace_dao: Optional[PlaybookTraceDao] = None

get_bearer_token = HTTPBearer(auto_error=False)


def get_playbook_service() -> PlaybookService:
    if global_system_app is None:
        raise HTTPException(status_code=500, detail="System app not initialized")
    return global_system_app.get_component(
        PLAYBOOK_SERVICE_COMPONENT_NAME, PlaybookService
    )


async def check_api_key(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
    service: PlaybookService = Depends(get_playbook_service),
) -> Optional[str]:
    if service.config.api_keys:
        api_keys = [k.strip() for k in service.config.api_keys.split(",")]
        if auth is None or (token := auth.credentials) not in api_keys:
            raise HTTPException(status_code=401, detail="invalid api key")
        return token
    return None


def get_engine() -> PlaybookEvolutionEngine:
    if _evolution_engine is None:
        raise HTTPException(
            status_code=500, detail="evolution engine not initialized"
        )
    return _evolution_engine


def get_proposal_store() -> DBEvolutionProposalStore:
    if _proposal_store is None:
        raise HTTPException(
            status_code=500, detail="evolution proposal store not initialized"
        )
    return _proposal_store


def get_trace_dao() -> PlaybookTraceDao:
    if _trace_dao is None:
        raise HTTPException(
            status_code=500, detail="trace dao not initialized"
        )
    return _trace_dao


# --------------------------------------------------------------------------- #
# 请求模型
# --------------------------------------------------------------------------- #
class EvolutionAnalyzeRequest(BaseModel):
    """触发演化分析请求"""
    playbook_id: int
    workspace_id: int


class EvolutionProposalListRequest(BaseModel):
    """列出 pending 提议请求"""
    workspace_id: int


class EvolutionProposalActionRequest(BaseModel):
    """审批/驳回提议请求"""
    reviewer: str = Field(..., description="审批人 user_id")
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# 序列化辅助
# --------------------------------------------------------------------------- #
def _proposal_to_dict(proposal: EvolutionProposal) -> Dict[str, Any]:
    """EvolutionProposal dataclass -> dict(便于 JSON 序列化)。"""
    d = asdict(proposal)
    proposed_at = d.get("proposed_at")
    if isinstance(proposed_at, datetime):
        d["proposed_at"] = proposed_at.isoformat()
    reviewed_at = d.get("reviewed_at")
    if isinstance(reviewed_at, datetime):
        d["reviewed_at"] = reviewed_at.isoformat()
    return d


def _result_to_dict(result: EvolutionResult) -> Dict[str, Any]:
    """EvolutionResult dataclass -> dict。"""
    return asdict(result)


def _trace_to_dict(trace: ExecutionTrace) -> Dict[str, Any]:
    """ExecutionTrace dataclass -> dict(递归转换嵌套 dataclass)。"""
    d = asdict(trace)
    created_at = d.get("created_at")
    if isinstance(created_at, datetime):
        d["created_at"] = created_at.isoformat()
    finalized_at = d.get("finalized_at")
    if isinstance(finalized_at, datetime):
        d["finalized_at"] = finalized_at.isoformat()
    return d


# --------------------------------------------------------------------------- #
# 演化分析
# --------------------------------------------------------------------------- #
@router.post("/evolution/analyze", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def evolution_analyze(
    request: EvolutionAnalyzeRequest,
    engine: PlaybookEvolutionEngine = Depends(get_engine),
    trace_dao: PlaybookTraceDao = Depends(get_trace_dao),
) -> Result:
    try:
        # 取未分析的已完结轨迹作为分析输入
        traces = trace_dao.list_unanalyzed(request.playbook_id)
        if not traces:
            return Result.succ([])
        proposals = await engine.analyze(traces)
        return Result.succ([_proposal_to_dict(p) for p in proposals])
    except Exception as e:
        logger.exception("evolution analyze exception!")
        return Result.failed(str(e))


# --------------------------------------------------------------------------- #
# 演化提议
# --------------------------------------------------------------------------- #
@router.post("/evolution/proposals/list", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def list_pending_proposals(
    request: EvolutionProposalListRequest,
    store: DBEvolutionProposalStore = Depends(get_proposal_store),
) -> Result:
    try:
        proposals = await store.list_pending(request.workspace_id)
        return Result.succ([_proposal_to_dict(p) for p in proposals])
    except Exception as e:
        logger.exception("evolution proposals list exception!")
        return Result.failed(str(e))


@router.post("/evolution/proposals/{proposal_id}/approve", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def approve_proposal(
    proposal_id: str,
    request: EvolutionProposalActionRequest,
    engine: PlaybookEvolutionEngine = Depends(get_engine),
    store: DBEvolutionProposalStore = Depends(get_proposal_store),
) -> Result:
    try:
        proposal = await store.get(proposal_id)
        if proposal is None:
            return Result.failed(f"proposal {proposal_id} not found")
        # 幂等键: 基于提议 ID + 审批人
        idempotency_key = f"evolution-apply-{proposal_id}-{request.reviewer}"
        result = await engine.apply(
            proposal, reviewer=request.reviewer, idempotency_key=idempotency_key,
        )
        return Result.succ(_result_to_dict(result))
    except Exception as e:
        logger.exception("evolution proposal approve exception!")
        return Result.failed(str(e))


@router.post("/evolution/proposals/{proposal_id}/reject", response_model=Result,
             dependencies=[Depends(check_api_key)])
async def reject_proposal(
    proposal_id: str,
    request: EvolutionProposalActionRequest,
    store: DBEvolutionProposalStore = Depends(get_proposal_store),
) -> Result:
    try:
        await store.update_status(
            proposal_id, "rejected", reviewer=request.reviewer,
        )
        return Result.succ(True)
    except Exception as e:
        logger.exception("evolution proposal reject exception!")
        return Result.failed(str(e))


@router.get("/evolution/proposals/{proposal_id}", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def get_proposal(
    proposal_id: str,
    store: DBEvolutionProposalStore = Depends(get_proposal_store),
) -> Result:
    try:
        proposal = await store.get(proposal_id)
        if proposal is None:
            return Result.failed(f"proposal {proposal_id} not found")
        return Result.succ(_proposal_to_dict(proposal))
    except Exception as e:
        logger.exception("evolution proposal get exception!")
        return Result.failed(str(e))


# --------------------------------------------------------------------------- #
# 执行轨迹
# --------------------------------------------------------------------------- #
@router.get("/evolution/traces/list", response_model=Result,
            dependencies=[Depends(check_api_key)])
async def list_traces(
    playbook_id: Optional[int] = Query(None, description="按 playbook 过滤"),
    workspace_id: Optional[int] = Query(None, description="按 workspace 过滤"),
    limit: int = Query(50, description="返回条数上限"),
    trace_dao: PlaybookTraceDao = Depends(get_trace_dao),
) -> Result:
    try:
        if playbook_id is not None:
            traces: List[ExecutionTrace] = trace_dao.list_recent(
                playbook_id, limit=limit,
            )
        elif workspace_id is not None:
            traces = trace_dao.list_by_workspace(workspace_id, limit=limit)
        else:
            return Result.failed("playbook_id or workspace_id is required")
        return Result.succ([_trace_to_dict(t) for t in traces])
    except Exception as e:
        logger.exception("evolution traces list exception!")
        return Result.failed(str(e))


def init_endpoints(system_app: SystemApp, config: ServeConfig) -> None:
    """初始化演化引擎 API——构造引擎、提议存储、轨迹 DAO 单例。

    飞轮联动:
    - 引擎注入共享事件总线,publish EVOLUTION_PROPOSED/APPLIED 供 AgentMaturity 消费
    - 注册 TraceToEvolutionHandler 订阅 TRACE_FINALIZED,累积 N 条自动触发分析
    """
    global global_system_app
    global _evolution_engine, _proposal_store, _trace_dao
    global_system_app = system_app

    from gyra.distributed import AssetEventType, get_shared_event_bus
    shared_bus = get_shared_event_bus(system_app)

    _evolution_engine = PlaybookEvolutionEngine(event_bus=shared_bus)
    _proposal_store = DBEvolutionProposalStore()
    _trace_dao = PlaybookTraceDao()

    # 注册 TraceToEvolutionHandler: 监听 TRACE_FINALIZED → 累积触发 analyze
    try:
        from .engine import TraceToEvolutionHandler
        handler = TraceToEvolutionHandler(
            engine=_evolution_engine,
            trace_dao=_trace_dao,
        )
        shared_bus.subscribe(
            AssetEventType.TRACE_FINALIZED,
            handler,
            handler.consumer_group,
        )
        logger.info(
            "[evolution-api] TraceToEvolutionHandler subscribed to TRACE_FINALIZED"
        )
    except Exception as e:
        logger.warning(
            f"[evolution-api] register TraceToEvolutionHandler failed: {e}"
        )
