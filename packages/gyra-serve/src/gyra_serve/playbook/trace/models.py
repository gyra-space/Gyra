"""Playbook 执行轨迹与演化提议存储模型。

Traceable(可追踪) + Evolvable(可演化) 两协议的 DB 落地:
- PlaybookTraceEntity: 每次 run_task 产一条执行轨迹
- PlaybookEvolutionProposalEntity: 演化引擎基于轨迹统计生成的修改提议
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Column, DateTime, Integer, String, Text, Boolean, Float, Index, desc,
)

from gyra.distributed import (
    ExecutionTrace, GateTriggerRecord, SkillCallRecord, TraceContext,
    EvolutionProposal,
)
from gyra.storage.metadata import BaseDao, Model

from ..config import SERVER_APP_TABLE_NAME

PLAYBOOK_TRACE_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_trace"
PLAYBOOK_EVOLUTION_PROPOSAL_TABLE_NAME = (
    f"{SERVER_APP_TABLE_NAME}_evolution_proposal"
)


def _dump_json(v):
    """序列化为 JSON 字符串(已是字符串则原样返回)。"""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _load_json(v, default=None):
    """反序列化 JSON,失败返回 default(默认 {})。"""
    if v is None or v == "":
        return {} if default is None else default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return {} if default is None else default


# --------------------------------------------------------------------------- #
# 执行轨迹
# --------------------------------------------------------------------------- #
class PlaybookTraceEntity(Model):
    """Playbook 执行轨迹表——一次 run_task 对应一条记录。

    skill_calls/gates/skips 用 JSON Text 存储,由 DAO 负责与
    ExecutionTrace dataclass 互转。
    """
    __tablename__ = PLAYBOOK_TRACE_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(64), nullable=False, unique=True, index=True)
    playbook_id = Column(Integer, nullable=False, index=True)
    playbook_version_id = Column(Integer, nullable=True)
    task_id = Column(Integer, nullable=False, index=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(String(128), nullable=True)

    # JSON: [{skill, call_order, success, duration_ms, result_summary}]
    skill_calls_json = Column(Text, nullable=True)
    # JSON: [{gate, intervention_type, resolved_by, resolution, duration_ms}]
    gates_json = Column(Text, nullable=True)
    # JSON: [[step_name, reason]]
    skips_json = Column(Text, nullable=True)

    # running/success/failed/partial/aborted
    status = Column(String(32), nullable=False, default="running")
    failure_reason = Column(Text, nullable=True)
    # 演化引擎是否分析过本条轨迹
    analyzed = Column(Boolean, nullable=False, default=False)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_finalized = Column(DateTime, nullable=True)


class PlaybookTraceDao(BaseDao[PlaybookTraceEntity, Dict[str, Any], Dict[str, Any]]):
    """轨迹 DAO——幂等写入(基于 trace_id)、按 playbook/workspace 查询、标记已分析。"""

    def from_request(self, request):
        raise NotImplementedError

    def to_request(self, entity):
        raise NotImplementedError

    def to_response(self, entity: PlaybookTraceEntity) -> Dict[str, Any]:
        return self.to_trace_dict(entity)

    # ----- entity <-> ExecutionTrace dataclass 互转 -----
    def to_trace(self, entity: PlaybookTraceEntity) -> ExecutionTrace:
        """DB entity -> ExecutionTrace dataclass。"""
        skill_calls_raw = _load_json(entity.skill_calls_json, default=[])
        gates_raw = _load_json(entity.gates_json, default=[])
        skips_raw = _load_json(entity.skips_json, default=[])

        skill_calls = [
            SkillCallRecord(
                skill_name=s.get("skill_name") or s.get("skill", ""),
                call_order=s.get("call_order", 0),
                success=s.get("success", False),
                duration_ms=s.get("duration_ms", 0),
                result_summary=s.get("result_summary", ""),
            )
            for s in (skill_calls_raw or [])
        ]
        gates = [
            GateTriggerRecord(
                gate_name=g.get("gate_name") or g.get("gate", ""),
                intervention_type=g.get("intervention_type", ""),
                resolved_by=g.get("resolved_by", ""),
                resolution=g.get("resolution", ""),
                duration_ms=g.get("duration_ms", 0),
            )
            for g in (gates_raw or [])
        ]
        skips = [tuple(s) for s in (skips_raw or []) if isinstance(s, (list, tuple))]

        context = TraceContext(
            playbook_id=entity.playbook_id,
            playbook_version_id=entity.playbook_version_id or 0,
            task_id=entity.task_id,
            workspace_id=entity.workspace_id,
            agent_id=entity.agent_id or "",
        )
        return ExecutionTrace(
            trace_id=entity.trace_id,
            context=context,
            skill_calls=skill_calls,
            gates=gates,
            skips=skips,
            status=entity.status or "running",
            failure_reason=entity.failure_reason or "",
            created_at=entity.gmt_created or datetime.now(),
            finalized_at=entity.gmt_finalized,
        )

    def to_trace_dict(self, entity: PlaybookTraceEntity) -> Dict[str, Any]:
        """DB entity -> dict(便于事件 payload/日志)。"""
        return {
            "trace_id": entity.trace_id,
            "playbook_id": entity.playbook_id,
            "playbook_version_id": entity.playbook_version_id,
            "task_id": entity.task_id,
            "workspace_id": entity.workspace_id,
            "agent_id": entity.agent_id,
            "skill_calls": _load_json(entity.skill_calls_json, default=[]),
            "gates": _load_json(entity.gates_json, default=[]),
            "skips": _load_json(entity.skips_json, default=[]),
            "status": entity.status,
            "failure_reason": entity.failure_reason,
            "analyzed": entity.analyzed,
            "gmt_created": entity.gmt_created.isoformat() if entity.gmt_created else "",
            "gmt_finalized": entity.gmt_finalized.isoformat() if entity.gmt_finalized else "",
        }

    def _from_trace(self, trace: ExecutionTrace) -> PlaybookTraceEntity:
        """ExecutionTrace dataclass -> DB entity(未持久化)。"""
        skill_calls_json = _dump_json([
            {
                "skill_name": s.skill_name,
                "skill": s.skill_name,
                "call_order": s.call_order,
                "success": s.success,
                "duration_ms": s.duration_ms,
                "result_summary": s.result_summary,
            }
            for s in trace.skill_calls
        ])
        gates_json = _dump_json([
            {
                "gate_name": g.gate_name,
                "gate": g.gate_name,
                "intervention_type": g.intervention_type,
                "resolved_by": g.resolved_by,
                "resolution": g.resolution,
                "duration_ms": g.duration_ms,
            }
            for g in trace.gates
        ])
        skips_json = _dump_json([list(s) for s in trace.skips])
        return PlaybookTraceEntity(
            trace_id=trace.trace_id,
            playbook_id=trace.context.playbook_id,
            playbook_version_id=trace.context.playbook_version_id or None,
            task_id=trace.context.task_id,
            workspace_id=trace.context.workspace_id,
            agent_id=trace.context.agent_id,
            skill_calls_json=skill_calls_json,
            gates_json=gates_json,
            skips_json=skips_json,
            status=trace.status,
            failure_reason=trace.failure_reason,
            gmt_created=trace.created_at,
            gmt_finalized=trace.finalized_at,
        )

    # ----- 写入(幂等,基于 trace_id upsert) -----
    def write(
        self,
        trace: ExecutionTrace,
        idempotency_key: str,
        final: bool = False,
    ) -> PlaybookTraceEntity:
        """幂等写入/更新轨迹——基于 trace_id 去重。

        final=True 时设置 gmt_finalized 与最终 status。
        """
        session = self.get_raw_session()
        try:
            entity = session.query(PlaybookTraceEntity).filter(
                PlaybookTraceEntity.trace_id == trace.trace_id
            ).first()
            skill_calls_json = _dump_json([
                {
                    "skill_name": s.skill_name,
                    "skill": s.skill_name,
                    "call_order": s.call_order,
                    "success": s.success,
                    "duration_ms": s.duration_ms,
                    "result_summary": s.result_summary,
                }
                for s in trace.skill_calls
            ])
            gates_json = _dump_json([
                {
                    "gate_name": g.gate_name,
                    "gate": g.gate_name,
                    "intervention_type": g.intervention_type,
                    "resolved_by": g.resolved_by,
                    "resolution": g.resolution,
                    "duration_ms": g.duration_ms,
                }
                for g in trace.gates
            ])
            skips_json = _dump_json([list(s) for s in trace.skips])

            if entity is None:
                entity = PlaybookTraceEntity(
                    trace_id=trace.trace_id,
                    playbook_id=trace.context.playbook_id,
                    playbook_version_id=trace.context.playbook_version_id or None,
                    task_id=trace.context.task_id,
                    workspace_id=trace.context.workspace_id,
                    agent_id=trace.context.agent_id,
                    skill_calls_json=skill_calls_json,
                    gates_json=gates_json,
                    skips_json=skips_json,
                    status=trace.status,
                    failure_reason=trace.failure_reason,
                    gmt_created=trace.created_at,
                    gmt_finalized=trace.finalized_at if final else None,
                )
                session.add(entity)
            else:
                entity.skill_calls_json = skill_calls_json or entity.skill_calls_json
                entity.gates_json = gates_json or entity.gates_json
                entity.skips_json = skips_json
                entity.status = trace.status
                entity.failure_reason = trace.failure_reason
                if final:
                    entity.gmt_finalized = trace.finalized_at or datetime.now()
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_recent(self, playbook_id: int, limit: int = 20) -> List[ExecutionTrace]:
        """最近 N 条已完结轨迹(按创建时间倒序)。"""
        session = self.get_raw_session()
        try:
            rows = (
                session.query(PlaybookTraceEntity)
                .filter(PlaybookTraceEntity.playbook_id == playbook_id)
                .order_by(desc(PlaybookTraceEntity.gmt_created))
                .limit(limit)
                .all()
            )
            return [self.to_trace(r) for r in rows]
        finally:
            session.close()

    def list_by_workspace(
        self, workspace_id: int, limit: int = 100
    ) -> List[ExecutionTrace]:
        session = self.get_raw_session()
        try:
            rows = (
                session.query(PlaybookTraceEntity)
                .filter(PlaybookTraceEntity.workspace_id == workspace_id)
                .order_by(desc(PlaybookTraceEntity.gmt_created))
                .limit(limit)
                .all()
            )
            return [self.to_trace(r) for r in rows]
        finally:
            session.close()

    def list_unanalyzed(self, playbook_id: int) -> List[ExecutionTrace]:
        """未分析且已完结的轨迹(演化引擎输入)。"""
        session = self.get_raw_session()
        try:
            rows = (
                session.query(PlaybookTraceEntity)
                .filter(
                    PlaybookTraceEntity.playbook_id == playbook_id,
                    PlaybookTraceEntity.analyzed.is_(False),
                    PlaybookTraceEntity.gmt_finalized.isnot(None),
                )
                .order_by(desc(PlaybookTraceEntity.gmt_created))
                .all()
            )
            return [self.to_trace(r) for r in rows]
        finally:
            session.close()

    def mark_analyzed(self, trace_id: str) -> None:
        """标记轨迹已被演化引擎分析。"""
        session = self.get_raw_session()
        try:
            entity = session.query(PlaybookTraceEntity).filter(
                PlaybookTraceEntity.trace_id == trace_id
            ).first()
            if entity:
                entity.analyzed = True
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# --------------------------------------------------------------------------- #
# 演化提议
# --------------------------------------------------------------------------- #
class PlaybookEvolutionProposalEntity(Model):
    """Playbook 演化提议表——演化引擎产出,owner 审批后应用。"""
    __tablename__ = PLAYBOOK_EVOLUTION_PROPOSAL_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(String(64), nullable=False, unique=True, index=True)
    playbook_id = Column(Integer, nullable=False, index=True)
    workspace_id = Column(Integer, nullable=False, index=True)

    # add_skill/remove_step/modify_gate/reduce_gate/...
    proposal_type = Column(String(64), nullable=False)
    rationale = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)       # [trace_id, ...]
    proposed_change_json = Column(Text, nullable=True)  # Dict
    confidence = Column(Float, nullable=False, default=0.5)

    # proposed/approved/rejected/applied
    status = Column(String(32), nullable=False, default="proposed")
    proposed_by = Column(String(128), nullable=True)
    proposed_at = Column(DateTime, default=datetime.now)
    reviewed_by = Column(String(128), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    applied_version = Column(Integer, nullable=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PlaybookEvolutionProposalDao(
    BaseDao[PlaybookEvolutionProposalEntity, Dict[str, Any], Dict[str, Any]]
):
    """演化提议 DAO——save/get/list_pending/list_by_target/update_status。"""

    def from_request(self, request):
        raise NotImplementedError

    def to_request(self, entity):
        raise NotImplementedError

    def to_response(self, entity: PlaybookEvolutionProposalEntity) -> Dict[str, Any]:
        return self.to_proposal_dict(entity)

    # ----- entity <-> EvolutionProposal dataclass 互转 -----
    def to_proposal(self, entity: PlaybookEvolutionProposalEntity) -> EvolutionProposal:
        return EvolutionProposal(
            proposal_id=entity.proposal_id,
            target_id=str(entity.playbook_id),
            target_type="playbook",
            proposal_type=entity.proposal_type,
            rationale=entity.rationale or "",
            evidence=_load_json(entity.evidence_json, default=[]) or [],
            proposed_change=_load_json(entity.proposed_change_json, default={}) or {},
            confidence=entity.confidence or 0.5,
            status=entity.status or "proposed",
            proposed_at=entity.proposed_at or datetime.now(),
            reviewed_by=entity.reviewed_by,
            reviewed_at=entity.reviewed_at,
            applied_version=entity.applied_version,
        )

    def to_proposal_dict(self, entity: PlaybookEvolutionProposalEntity) -> Dict[str, Any]:
        return {
            "proposal_id": entity.proposal_id,
            "playbook_id": entity.playbook_id,
            "workspace_id": entity.workspace_id,
            "proposal_type": entity.proposal_type,
            "rationale": entity.rationale,
            "evidence": _load_json(entity.evidence_json, default=[]) or [],
            "proposed_change": _load_json(entity.proposed_change_json, default={}) or {},
            "confidence": entity.confidence,
            "status": entity.status,
            "proposed_by": entity.proposed_by,
            "proposed_at": entity.proposed_at.isoformat() if entity.proposed_at else "",
            "reviewed_by": entity.reviewed_by,
            "reviewed_at": entity.reviewed_at.isoformat() if entity.reviewed_at else "",
            "applied_version": entity.applied_version,
        }

    # ----- 写入(幂等,基于 proposal_id upsert) -----
    def save(self, proposal: EvolutionProposal) -> str:
        """幂等保存提议——基于 proposal_id 去重,返回 proposal_id。"""
        if not proposal.proposal_id:
            proposal.proposal_id = str(uuid.uuid4())

        # playbook_id 优先从 proposed_change/workspace 推断;target_id 是 str
        playbook_id = proposal.proposed_change.get("playbook_id")
        if not playbook_id:
            try:
                playbook_id = int(proposal.target_id)
            except (TypeError, ValueError):
                playbook_id = 0
        workspace_id = proposal.proposed_change.get("workspace_id", 0)

        session = self.get_raw_session()
        try:
            entity = session.query(PlaybookEvolutionProposalEntity).filter(
                PlaybookEvolutionProposalEntity.proposal_id == proposal.proposal_id
            ).first()
            evidence_json = _dump_json(list(proposal.evidence))
            change_json = _dump_json(proposal.proposed_change)
            if entity is None:
                entity = PlaybookEvolutionProposalEntity(
                    proposal_id=proposal.proposal_id,
                    playbook_id=int(playbook_id),
                    workspace_id=int(workspace_id),
                    proposal_type=proposal.proposal_type,
                    rationale=proposal.rationale,
                    evidence_json=evidence_json,
                    proposed_change_json=change_json,
                    confidence=proposal.confidence,
                    status=proposal.status,
                    proposed_by=proposal.proposed_change.get("proposed_by", "system"),
                    proposed_at=proposal.proposed_at,
                )
                session.add(entity)
            else:
                entity.rationale = proposal.rationale
                entity.evidence_json = evidence_json
                entity.proposed_change_json = change_json
                entity.confidence = proposal.confidence
                entity.status = proposal.status
                if entity.playbook_id in (None, 0):
                    entity.playbook_id = int(playbook_id)
                if entity.workspace_id in (None, 0):
                    entity.workspace_id = int(workspace_id)
            session.commit()
            return proposal.proposal_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, proposal_id: str) -> Optional[EvolutionProposal]:
        session = self.get_raw_session()
        try:
            entity = session.query(PlaybookEvolutionProposalEntity).filter(
                PlaybookEvolutionProposalEntity.proposal_id == proposal_id
            ).first()
            return self.to_proposal(entity) if entity else None
        finally:
            session.close()

    def list_pending(self, workspace_id: int) -> List[EvolutionProposal]:
        session = self.get_raw_session()
        try:
            rows = (
                session.query(PlaybookEvolutionProposalEntity)
                .filter(
                    PlaybookEvolutionProposalEntity.workspace_id == workspace_id,
                    PlaybookEvolutionProposalEntity.status == "proposed",
                )
                .order_by(desc(PlaybookEvolutionProposalEntity.proposed_at))
                .all()
            )
            return [self.to_proposal(r) for r in rows]
        finally:
            session.close()

    def list_by_target(
        self, target_id: str, status: Optional[str] = None
    ) -> List[EvolutionProposal]:
        session = self.get_raw_session()
        try:
            try:
                playbook_id = int(target_id)
            except (TypeError, ValueError):
                playbook_id = 0
            query = session.query(PlaybookEvolutionProposalEntity).filter(
                PlaybookEvolutionProposalEntity.playbook_id == playbook_id
            )
            if status:
                query = query.filter(
                    PlaybookEvolutionProposalEntity.status == status
                )
            rows = query.order_by(
                desc(PlaybookEvolutionProposalEntity.proposed_at)
            ).all()
            return [self.to_proposal(r) for r in rows]
        finally:
            session.close()

    def update_status(
        self,
        proposal_id: str,
        status: str,
        reviewer: Optional[str] = None,
        applied_version: Optional[int] = None,
    ) -> None:
        session = self.get_raw_session()
        try:
            entity = session.query(PlaybookEvolutionProposalEntity).filter(
                PlaybookEvolutionProposalEntity.proposal_id == proposal_id
            ).first()
            if not entity:
                return
            entity.status = status
            if reviewer is not None:
                entity.reviewed_by = reviewer
                entity.reviewed_at = datetime.now()
            if applied_version is not None:
                entity.applied_version = applied_version
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
