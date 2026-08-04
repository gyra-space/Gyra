"""Playbook 演化引擎——基于轨迹统计生成提议,owner 审批后应用。

实现 Evolvable 协议:
- analyze(traces): 运行所有检测器 → 去重 → 保存提议 → 发布 EVOLUTION_PROPOSED
- apply(proposal, reviewer, idempotency_key): 人审批后应用 → 创建 Playbook 新版本 → 发布 EVOLUTION_APPLIED

分布式协调:
- analyze 用分布式锁防并发(lock_key = "evolution:analyze:{playbook_id}")
- TraceToEvolutionHandler 监听 TRACE_FINALIZED,累积够 N 条触发分析
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    DistributedLock,
    EvolutionProposal,
    EvolutionProposalStore,
    EvolutionResult,
    Evolvable,
    EventHandler,
    ExecutionTrace,
    LocalDistributedLock,
)

from ..trace.models import (
    PlaybookEvolutionProposalDao,
    PlaybookTraceDao,
)
from ..models.models import (
    PlaybookDao, PlaybookEntity, PlaybookVersionDao,
)
from .detectors import default_detectors

logger = logging.getLogger(__name__)

# 触发分析所需的最少已完结未分析轨迹数
DEFAULT_ANALYZE_TRIGGER = 5


class DBEvolutionProposalStore(EvolutionProposalStore):
    """EvolutionProposalStore 实现——基于 PlaybookEvolutionProposalDao。"""

    def __init__(self, dao: Optional[PlaybookEvolutionProposalDao] = None):
        self._dao = dao or PlaybookEvolutionProposalDao()

    async def save(self, proposal: EvolutionProposal) -> str:
        return self._dao.save(proposal)

    async def get(self, proposal_id: str) -> Optional[EvolutionProposal]:
        return self._dao.get(proposal_id)

    async def list_pending(self, workspace_id: int) -> List[EvolutionProposal]:
        return self._dao.list_pending(workspace_id)

    async def list_by_target(
        self, target_id: str, status: Optional[str] = None
    ) -> List[EvolutionProposal]:
        return self._dao.list_by_target(target_id, status)

    async def update_status(
        self,
        proposal_id: str,
        status: str,
        reviewer: Optional[str] = None,
        applied_version: Optional[int] = None,
    ) -> None:
        self._dao.update_status(proposal_id, status, reviewer, applied_version)


class PlaybookEvolutionEngine(Evolvable):
    """Evolvable 实现——Playbook 自我演化引擎。

    依赖注入(均可在构造时覆盖,默认用单机实现):
    - proposal_store: 演化提议存储
    - event_bus: 事件总线(发布 EVOLUTION_PROPOSED/APPLIED)
    - lock: 分布式锁(防并发分析)
    - playbook_dao / version_dao: 读写 Playbook 与版本
    - trace_dao: 标记轨迹已分析
    """

    def __init__(
        self,
        proposal_store: Optional[EvolutionProposalStore] = None,
        event_bus: Optional[AssetEventBus] = None,
        lock: Optional[DistributedLock] = None,
        playbook_dao: Optional[PlaybookDao] = None,
        version_dao: Optional[PlaybookVersionDao] = None,
        trace_dao: Optional[PlaybookTraceDao] = None,
    ):
        self._store = proposal_store or DBEvolutionProposalStore()
        self._event_bus = event_bus
        self._lock = lock or LocalDistributedLock()
        self._playbook_dao = playbook_dao or PlaybookDao()
        self._version_dao = version_dao or PlaybookVersionDao()
        self._trace_dao = trace_dao or PlaybookTraceDao()

    # ------------------------------------------------------------------ #
    # analyze: 分析轨迹 → 生成提议
    # ------------------------------------------------------------------ #
    async def analyze(
        self,
        traces: List[ExecutionTrace],
    ) -> List[EvolutionProposal]:
        """分析轨迹,运行所有检测器,去重保存提议,发布 EVOLUTION_PROPOSED 事件。

        分布式锁防并发: 同一 playbook 同时只允许一个分析任务。
        """
        if not traces:
            return []

        playbook_id = traces[0].context.playbook_id
        workspace_id = traces[0].context.workspace_id
        lock_key = f"evolution:analyze:{playbook_id}"
        holder_id = f"evolution-engine-{uuid.uuid4().hex[:8]}"

        handle = await self._lock.acquire(lock_key, holder_id, ttl_seconds=60)
        if not handle.acquired:
            logger.info(
                f"[evolution] analyze skipped, lock busy playbook={playbook_id}"
            )
            return []

        try:
            # 加载当前声明,供需要 declared_skills 的检测器使用
            declared_skills = self._load_declared_skills(playbook_id)
            detectors = default_detectors(declared_skills=declared_skills)

            raw_proposals: List[EvolutionProposal] = []
            for detector in detectors:
                try:
                    raw_proposals.extend(detector.detect(traces))
                except Exception as e:
                    logger.warning(
                        f"[evolution] detector {detector.name} failed: {e}"
                    )

            # 去重: 同 (proposal_type, target_id, 主键字段) 只保留 confidence 最高的
            deduped = self._dedup_proposals(raw_proposals)

            # 持久化 + 发布事件
            saved: List[EvolutionProposal] = []
            for proposal in deduped:
                try:
                    await self._store.save(proposal)
                    saved.append(proposal)
                    await self._publish_proposed(proposal, workspace_id)
                except Exception as e:
                    logger.warning(
                        f"[evolution] save proposal failed: {e}"
                    )

            # 标记轨迹已分析(避免重复分析)
            for trace in traces:
                try:
                    self._trace_dao.mark_analyzed(trace.trace_id)
                except Exception as e:
                    logger.warning(
                        f"[evolution] mark_analyzed failed trace={trace.trace_id}: {e}"
                    )

            logger.info(
                f"[evolution] analyze done playbook={playbook_id} "
                f"traces={len(traces)} proposals={len(saved)}"
            )
            return saved
        finally:
            await self._lock.release(handle)

    # ------------------------------------------------------------------ #
    # apply: 人审批后应用提议 → 创建新版本
    # ------------------------------------------------------------------ #
    async def apply(
        self,
        proposal: EvolutionProposal,
        reviewer: str,
        idempotency_key: str,
    ) -> EvolutionResult:
        """应用演化提议——创建 Playbook 新版本,标记 applied,发布 EVOLUTION_APPLIED。"""
        try:
            playbook_id = int(proposal.target_id)
        except (TypeError, ValueError):
            return EvolutionResult(
                proposal_id=proposal.proposal_id,
                success=False,
                error=f"invalid target_id: {proposal.target_id}",
            )

        # 加载当前 playbook + 声明
        session = self._playbook_dao.get_raw_session()
        try:
            entity = session.query(PlaybookEntity).filter(
                PlaybookEntity.id == playbook_id
            ).first()
            if not entity:
                return EvolutionResult(
                    proposal_id=proposal.proposal_id,
                    success=False,
                    error=f"playbook {playbook_id} not found",
                )
            declaration = _load_declaration(entity.declaration_dsl_json)
            new_declaration = self._apply_change(declaration, proposal)
            new_version = (entity.current_version or 1) + 1
            entity.current_version = new_version
            entity.declaration_dsl_json = _dump_declaration(new_declaration)
            session.commit()
            workspace_id = entity.workspace_id
        except Exception as e:
            session.rollback()
            return EvolutionResult(
                proposal_id=proposal.proposal_id,
                success=False,
                error=f"update playbook failed: {e}",
            )
        finally:
            session.close()

        # 创建版本快照
        try:
            self._version_dao.create_version(
                playbook_id=playbook_id,
                version=new_version,
                declaration=new_declaration,
                changelog=(
                    f"[evolution] {proposal.proposal_type}: {proposal.rationale}"
                ),
            )
        except Exception as e:
            logger.warning(
                f"[evolution] create version failed playbook={playbook_id}: {e}"
            )

        # 标记提议 applied
        try:
            await self._store.update_status(
                proposal.proposal_id, "applied",
                reviewer=reviewer, applied_version=new_version,
            )
        except Exception as e:
            logger.warning(
                f"[evolution] update_status failed proposal={proposal.proposal_id}: {e}"
            )

        # 发布 EVOLUTION_APPLIED 事件
        await self._publish_applied(
            proposal, playbook_id, workspace_id, new_version
        )

        return EvolutionResult(
            proposal_id=proposal.proposal_id,
            new_version_id=new_version,
            success=True,
        )

    # ------------------------------------------------------------------ #
    # 内部: 声明加载 / 变更应用 / 去重
    # ------------------------------------------------------------------ #
    def _load_declared_skills(self, playbook_id: int) -> List[str]:
        """加载当前 Playbook 声明的 skills 列表。"""
        session = self._playbook_dao.get_raw_session()
        try:
            entity = session.query(PlaybookEntity).filter(
                PlaybookEntity.id == playbook_id
            ).first()
            if not entity:
                return []
            declaration = _load_declaration(entity.declaration_dsl_json)
            skills = declaration.get("skills") or []
            return [s for s in skills if isinstance(s, str)]
        finally:
            session.close()

    def _dedup_proposals(
        self, proposals: List[EvolutionProposal]
    ) -> List[EvolutionProposal]:
        """去重: 同 (proposal_type, target_id, 主键字段) 保留 confidence 最高。"""
        best: Dict[tuple, EvolutionProposal] = {}
        for p in proposals:
            key_field = self._proposal_key_field(p)
            key = (p.proposal_type, p.target_id, key_field)
            existing = best.get(key)
            if existing is None or p.confidence > existing.confidence:
                best[key] = p
        return list(best.values())

    @staticmethod
    def _proposal_key_field(proposal: EvolutionProposal) -> str:
        """提取提议的主键字段用于去重。"""
        change = proposal.proposed_change or {}
        for k in ("add_skill", "remove_step", "modify_gate", "reduce_gate"):
            if k in change:
                return str(change[k])
        return proposal.rationale

    def _apply_change(
        self,
        declaration: Dict[str, Any],
        proposal: EvolutionProposal,
    ) -> Dict[str, Any]:
        """将提议变更应用到声明副本(不修改原对象)。"""
        import copy
        new_decl = copy.deepcopy(declaration)
        change = proposal.proposed_change or {}
        ptype = proposal.proposal_type

        if ptype == "add_skill":
            skill = change.get("add_skill")
            skills = new_decl.setdefault("skills", [])
            if skill and skill not in skills:
                skills.append(skill)
        elif ptype == "remove_step":
            step = change.get("remove_step")
            skills = new_decl.get("skills") or []
            if step and step in skills:
                skills.remove(step)
                new_decl["skills"] = skills
        elif ptype in ("modify_gate", "reduce_gate"):
            # gate 配置若无显式结构,记录到 gates 块
            gates = new_decl.setdefault("gates", [])
            gates.append({
                "gate": change.get("modify_gate") or change.get("reduce_gate"),
                "action": change.get("action", "reduce_to_auto"),
                "to": change.get("to"),
                "from_proposal": proposal.proposal_id,
            })
        return new_decl

    # ------------------------------------------------------------------ #
    # 内部: 事件发布
    # ------------------------------------------------------------------ #
    async def _publish_proposed(
        self, proposal: EvolutionProposal, workspace_id: int
    ) -> None:
        if self._event_bus is None:
            return
        try:
            event = AssetEvent(
                event_type=AssetEventType.EVOLUTION_PROPOSED,
                asset_id=f"playbook:{proposal.target_id}",
                workspace_id=workspace_id,
                actor=proposal.proposed_change.get("proposed_by", "system"),
                payload={
                    "proposal_id": proposal.proposal_id,
                    "target_id": proposal.target_id,
                    "proposal_type": proposal.proposal_type,
                    "confidence": proposal.confidence,
                    "rationale": proposal.rationale,
                },
                idempotency_key=f"evolution-proposed-{proposal.proposal_id}",
            )
            await self._event_bus.publish(
                event, partition_key=str(workspace_id)
            )
        except Exception as e:
            logger.warning(f"[evolution] publish PROPOSED failed: {e}")

    async def _publish_applied(
        self,
        proposal: EvolutionProposal,
        playbook_id: int,
        workspace_id: int,
        new_version: int,
    ) -> None:
        if self._event_bus is None:
            return
        try:
            event = AssetEvent(
                event_type=AssetEventType.EVOLUTION_APPLIED,
                asset_id=f"playbook:{playbook_id}",
                workspace_id=workspace_id,
                actor=proposal.reviewed_by or "system",
                payload={
                    "proposal_id": proposal.proposal_id,
                    "playbook_id": playbook_id,
                    "new_version": new_version,
                    "proposal_type": proposal.proposal_type,
                },
                idempotency_key=f"evolution-applied-{proposal.proposal_id}",
            )
            await self._event_bus.publish(
                event, partition_key=str(workspace_id)
            )
        except Exception as e:
            logger.warning(f"[evolution] publish APPLIED failed: {e}")


# --------------------------------------------------------------------------- #
# TraceToEvolutionHandler: 监听 TRACE_FINALIZED,触发分析
# --------------------------------------------------------------------------- #
class TraceToEvolutionHandler(EventHandler):
    """EventHandler 实现——监听轨迹完结事件,累积够 N 条触发演化分析。

    消费组固定为 "evolution-engine"(同组负载均衡,避免重复分析)。
    """

    consumer_group = "evolution-engine"

    def __init__(
        self,
        engine: PlaybookEvolutionEngine,
        trace_dao: Optional[PlaybookTraceDao] = None,
        trigger_threshold: int = DEFAULT_ANALYZE_TRIGGER,
    ):
        self._engine = engine
        self._trace_dao = trace_dao or PlaybookTraceDao()
        self._trigger_threshold = trigger_threshold

    async def handle(self, event: AssetEvent) -> None:
        """处理 TRACE_FINALIZED 事件——幂等(基于 event.idempotency_key)。"""
        if event.event_type != AssetEventType.TRACE_FINALIZED:
            return

        payload = event.payload or {}
        playbook_id = payload.get("playbook_id")
        if not playbook_id:
            return

        try:
            unanalyzed = self._trace_dao.list_unanalyzed(playbook_id)
        except Exception as e:
            logger.warning(
                f"[evolution-handler] list_unanalyzed failed "
                f"playbook={playbook_id}: {e}"
            )
            return

        if len(unanalyzed) < self._trigger_threshold:
            logger.info(
                f"[evolution-handler] playbook={playbook_id} unanalyzed="
                f"{len(unanalyzed)} < {self._trigger_threshold}, skip"
            )
            return

        logger.info(
            f"[evolution-handler] trigger analyze playbook={playbook_id} "
            f"traces={len(unanalyzed)}"
        )
        try:
            await self._engine.analyze(unanalyzed)
        except Exception as e:
            logger.warning(
                f"[evolution-handler] analyze failed playbook={playbook_id}: {e}"
            )


# --------------------------------------------------------------------------- #
# 辅助: 声明 JSON 序列化(与 models._dump_json/_load_json 语义一致)
# --------------------------------------------------------------------------- #
def _dump_declaration(declaration: Dict[str, Any]) -> Optional[str]:
    if declaration is None:
        return None
    return json.dumps(declaration, ensure_ascii=False)


def _load_declaration(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}
