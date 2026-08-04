"""Agent 成长模型服务 —— 四阶段跃迁(novice→proficient→expert→master)。

飞轮反哺: 采集三链信号(资产贡献/执行成功率/attest 数) → 多维评分 →
阶段跃迁 → 权限变化 → 反哺飞轮(资产/演化/审批阀门)。

职责:
- 评分采集: collect_signals 从轨迹/资产/记忆采集
- 评分计算: calculate_score 多维加权
- 阶段跃迁: check_promotion / promote(加锁+幂等+事件)
- 背书: attest_agent(expert→master 需 N 人 agent 背书)
- 权限查询: get_permissions 返回当前阶段权限

分布式语义:
- 评分写入最终一致(事件驱动累加)
- 跃迁走分布式锁防并发(同 agent 同时只能一个)
- 幂等: 已在目标阶段则跳过
"""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from gyra.component import SystemApp
from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    DistributedLock,
    LocalDistributedLock,
    LocalEventBus,
    PromotionCheck,
    get_shared_event_bus,
)
from gyra_serve.core import BaseService

from ..config import ServeConfig
from .models import AgentMaturityDao, _load_json

AGENT_MATURITY_SERVICE_COMPONENT_NAME = "serve_agent_maturity_service"
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 阶段定义
# --------------------------------------------------------------------------- #
class AgentStage(str, Enum):
    """Agent 成长四阶段"""
    NOVICE = "novice"          # 毕业生
    PROFICIENT = "proficient"  # 熟练
    EXPERT = "expert"          # 专家
    MASTER = "master"          # 大师


# 阶段顺序(用于比较/防降级误用)
_STAGE_ORDER: List[AgentStage] = [
    AgentStage.NOVICE,
    AgentStage.PROFICIENT,
    AgentStage.EXPERT,
    AgentStage.MASTER,
]


# --------------------------------------------------------------------------- #
# 阶段权限
# --------------------------------------------------------------------------- #
STAGE_PERMISSIONS: Dict[AgentStage, Dict[str, Any]] = {
    AgentStage.NOVICE: {
        "asset_access": "published",        # 只读 published
        "approval_required": "all",         # 所有产出 review
        "can_attest": False,
        "can_evolve_playbook": False,
        "promotion_weight": 1.0,
    },
    AgentStage.PROFICIENT: {
        "asset_access": "confirmed",
        "approval_required": "routine_auto",  # routine 可 auto
        "can_attest": False,
        "can_evolve_playbook": False,
        "promotion_weight": 0.9,
    },
    AgentStage.EXPERT: {
        "asset_access": "confirmed",
        "approval_required": "pipeline_auto",  # pipeline 可 auto
        "can_attest": True,                     # 可 attest 他人
        "can_evolve_playbook": True,            # 可主导演化
        "promotion_weight": 0.7,
    },
    AgentStage.MASTER: {
        "asset_access": "all",
        "approval_required": "minimal",
        "can_attest": True,
        "can_evolve_playbook": True,
        "can_certify_promotion": True,          # 可认证他人晋升
        "promotion_weight": 0.5,
    },
}


# --------------------------------------------------------------------------- #
# 晋升阈值(可配置)
# --------------------------------------------------------------------------- #
# expert→master 中的 agent_attests = len(attest_by) (N 个 expert/master 背书)
PROMOTION_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "novice_to_proficient": {
        "execution_count": 10,
        "success_rate": 0.7,
    },
    "proficient_to_expert": {
        "execution_count": 30,
        "success_rate": 0.8,
        "asset_contribution": 5,
    },
    "expert_to_master": {
        "asset_contribution": 10,
        "agent_attests": 3,
    },
}

# expert→master 所需 agent 背书人数
REQUIRED_AGENT_ATTESTS = 3


def _stage_permissions_dict(stage: AgentStage) -> Dict[str, Any]:
    """返回阶段权限的可序列化副本。"""
    return dict(STAGE_PERMISSIONS.get(stage, STAGE_PERMISSIONS[AgentStage.NOVICE]))


def _next_stage(stage: AgentStage) -> Optional[AgentStage]:
    idx = _STAGE_ORDER.index(stage)
    if idx + 1 >= len(_STAGE_ORDER):
        return None
    return _STAGE_ORDER[idx + 1]


# --------------------------------------------------------------------------- #
# 服务
# --------------------------------------------------------------------------- #
class AgentMaturityService(BaseService):
    """Agent 成长模型服务 —— 采集信号 / 评分 / 跃迁 / 背书 / 权限。"""

    name = AGENT_MATURITY_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        dao: Optional[AgentMaturityDao] = None,
        lock: Optional[DistributedLock] = None,
        event_bus: Optional[AssetEventBus] = None,
    ):
        self._system_app: Optional[SystemApp] = None
        self._serve_config: ServeConfig = config
        self._dao: AgentMaturityDao = dao
        self._lock: DistributedLock = lock or LocalDistributedLock()
        self._event_bus: AssetEventBus = event_bus or LocalEventBus()
        self._handlers_subscribed: bool = False
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or AgentMaturityDao()
        self._system_app = system_app
        # 飞轮联动: 接入共享事件总线(若未装配则降级为 LocalEventBus)
        # 确保能消费 AssetMaturityService 发布的 attest/coach 事件
        if self._event_bus is None or isinstance(self._event_bus, LocalEventBus):
            self._event_bus = get_shared_event_bus(system_app)
        # 订阅事件处理器(驱动三链信号反哺)
        # 延迟导入避免 service <-> handlers 循环依赖
        from .handlers import register_agent_maturity_handlers
        if not getattr(self, "_handlers_subscribed", False):
            register_agent_maturity_handlers(self)
            self._handlers_subscribed = True

    # ----- BaseService 抽象实现 -----
    @property
    def dao(self) -> AgentMaturityDao:
        return self._dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    @property
    def lock(self) -> DistributedLock:
        return self._lock

    @property
    def event_bus(self) -> AssetEventBus:
        return self._event_bus

    # ------------------------------------------------------------------ #
    # 信号采集
    # ------------------------------------------------------------------ #
    def collect_signals(
        self, agent_id: str, workspace_id: int
    ) -> Dict[str, Any]:
        """从三链采集 agent 信号——执行链/资产链/记忆链。

        - 执行链: PlaybookTrace 表按 agent_id 聚合(执行次数/成功率/失败率)
        - 资产链: Asset 表按 source_agent_id 聚合(资产贡献数)
        - 记忆链: L2 记忆晋升数(接口预留,默认 0)
        - 事件驱动信号(attest_count/coach_count/evolution_count):
          沿用当前 score_json 中已累计的值
        """
        signals: Dict[str, Any] = {
            "execution_count": 0,
            "success_rate": 0.0,
            "failure_rate": 1.0,
            "asset_contribution": 0,
            "attest_count": 0,
            "memory_promotions": 0,
            "recall_hit_rate": 0.0,
            "coach_count": 0,
            "evolution_count": 0,
        }

        session = self._dao.get_raw_session()
        try:
            # ----- 执行链 -----
            from gyra_serve.playbook.trace.models import PlaybookTraceEntity

            traces = (
                session.query(PlaybookTraceEntity)
                .filter(
                    PlaybookTraceEntity.agent_id == agent_id,
                    PlaybookTraceEntity.workspace_id == workspace_id,
                    PlaybookTraceEntity.gmt_finalized.isnot(None),
                )
                .all()
            )
            execution_count = len(traces)
            success_count = sum(
                1 for t in traces if (t.status or "") == "success"
            )
            signals["execution_count"] = execution_count
            if execution_count > 0:
                signals["success_rate"] = round(success_count / execution_count, 4)
                signals["failure_rate"] = round(
                    1.0 - signals["success_rate"], 4
                )

            # ----- 资产链 -----
            from gyra_serve.workspace_asset.models.models import AssetEntity

            asset_contribution = (
                session.query(AssetEntity)
                .filter(
                    AssetEntity.source_agent_id == agent_id,
                    AssetEntity.workspace_id == workspace_id,
                )
                .count()
            )
            signals["asset_contribution"] = int(asset_contribution or 0)
        finally:
            session.close()

        # ----- 事件驱动信号: 沿用已累计值 -----
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is not None:
            existing = _load_json(entity.score_json, default={}) or {}
            if isinstance(existing, dict):
                for k in ("attest_count", "coach_count", "evolution_count"):
                    if k in existing:
                        try:
                            signals[k] = int(existing[k] or 0)
                        except (TypeError, ValueError):
                            signals[k] = 0
                # 记忆链接口预留(若已有则沿用)
                for k in ("memory_promotions", "recall_hit_rate"):
                    if k in existing:
                        signals[k] = existing[k]

        return signals

    # ------------------------------------------------------------------ #
    # 评分计算
    # ------------------------------------------------------------------ #
    def calculate_score(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """多维加权评分 → 0-100 综合分。

        维度权重:
        - 执行量(25): min(execution_count/30, 1) * 25
        - 成功率(25): success_rate * 25
        - 资产贡献(20): min(asset_contribution/10, 1) * 20
        - attest 信用(15): min(attest_count/3, 1) * 15
        - 记忆晋升(10): min(memory_promotions/3, 1) * 10
        - 召回命中(5): recall_hit_rate * 5
        - 惩罚: -coach_count * 2
        - 演化加分: +min(evolution_count, 5) * 1
        """
        def _ratio(v: Any, denom: float) -> float:
            try:
                return min(float(v or 0) / denom, 1.0)
            except (TypeError, ValueError, ZeroDivisionError):
                return 0.0

        execution = _ratio(signals.get("execution_count", 0), 30.0) * 25.0
        success = float(signals.get("success_rate", 0.0) or 0.0) * 25.0
        asset = _ratio(signals.get("asset_contribution", 0), 10.0) * 20.0
        attest = _ratio(signals.get("attest_count", 0), 3.0) * 15.0
        memory = _ratio(signals.get("memory_promotions", 0), 3.0) * 10.0
        recall = float(signals.get("recall_hit_rate", 0.0) or 0.0) * 5.0
        coach_pen = -float(signals.get("coach_count", 0) or 0) * 2.0
        evo_bonus = min(float(signals.get("evolution_count", 0) or 0), 5.0) * 1.0

        total = execution + success + asset + attest + memory + recall
        total += coach_pen + evo_bonus
        total = max(0.0, min(100.0, round(total, 2)))

        score = dict(signals)
        score["total_score"] = total
        return score

    # ------------------------------------------------------------------ #
    # 评分写入
    # ------------------------------------------------------------------ #
    def recalculate(
        self, agent_id: str, workspace_id: int
    ) -> Dict[str, Any]:
        """重新采集信号 + 计算评分 + upsert。返回最新 score。"""
        signals = self.collect_signals(agent_id, workspace_id)
        score = self.calculate_score(signals)
        # 确保记录存在 + 权限同步
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is None:
            entity = self._dao.get_or_create(
                agent_id=agent_id,
                workspace_id=workspace_id,
                default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
            )
        self._dao.upsert_score(
            agent_id=agent_id,
            workspace_id=workspace_id,
            scores=score,
        )
        # 同步权限(防 stage 与 permissions 不一致)
        try:
            stage = AgentStage(entity.stage or "novice")
        except ValueError:
            stage = AgentStage.NOVICE
        self._dao.update_permissions(
            agent_id=agent_id,
            workspace_id=workspace_id,
            permissions=_stage_permissions_dict(stage),
        )
        return score

    # ------------------------------------------------------------------ #
    # 阶段跃迁检查
    # ------------------------------------------------------------------ #
    def check_promotion(self, agent_id: str, workspace_id: int) -> PromotionCheck:
        """检查是否满足下一阶段晋升条件。"""
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is None:
            return PromotionCheck(
                can_promote=False,
                gate="auto",
                missing=["agent_maturity_record_not_found"],
            )
        try:
            current = AgentStage(entity.stage or "novice")
        except ValueError:
            current = AgentStage.NOVICE

        nxt = _next_stage(current)
        if nxt is None:
            return PromotionCheck(
                can_promote=False,
                gate="auto",
                missing=["already_at_top_stage"],
                reason=f"agent {agent_id} already at master",
            )

        # 取最新评分
        score = _load_json(entity.score_json, default={}) or {}
        if not isinstance(score, dict):
            score = {}
        attest_by = _load_json(entity.attest_by_json, default=[]) or []
        agent_attests = len(attest_by) if isinstance(attest_by, list) else 0

        missing: List[str] = []

        if nxt == AgentStage.PROFICIENT:
            th = PROMOTION_THRESHOLDS["novice_to_proficient"]
            ec = int(score.get("execution_count", 0) or 0)
            sr = float(score.get("success_rate", 0.0) or 0.0)
            if ec < th["execution_count"]:
                missing.append(
                    f"execution_count({ec}/{int(th['execution_count'])})"
                )
            if sr < th["success_rate"]:
                missing.append(
                    f"success_rate({sr:.2f}/{th['success_rate']:.2f})"
                )
        elif nxt == AgentStage.EXPERT:
            th = PROMOTION_THRESHOLDS["proficient_to_expert"]
            ec = int(score.get("execution_count", 0) or 0)
            sr = float(score.get("success_rate", 0.0) or 0.0)
            ac = int(score.get("asset_contribution", 0) or 0)
            if ec < th["execution_count"]:
                missing.append(
                    f"execution_count({ec}/{int(th['execution_count'])})"
                )
            if sr < th["success_rate"]:
                missing.append(
                    f"success_rate({sr:.2f}/{th['success_rate']:.2f})"
                )
            if ac < th["asset_contribution"]:
                missing.append(
                    f"asset_contribution({ac}/{int(th['asset_contribution'])})"
                )
        elif nxt == AgentStage.MASTER:
            th = PROMOTION_THRESHOLDS["expert_to_master"]
            ac = int(score.get("asset_contribution", 0) or 0)
            if ac < th["asset_contribution"]:
                missing.append(
                    f"asset_contribution({ac}/{int(th['asset_contribution'])})"
                )
            if agent_attests < int(th["agent_attests"]):
                missing.append(
                    f"agent_attests({agent_attests}/{int(th['agent_attests'])})"
                )

        return PromotionCheck(
            can_promote=len(missing) == 0,
            gate="auto",
            missing=missing,
        )

    # ------------------------------------------------------------------ #
    # 执行晋升
    # ------------------------------------------------------------------ #
    async def promote(
        self,
        agent_id: str,
        to_stage: AgentStage,
        actor: str,
        workspace_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """执行晋升——加锁 + 幂等 + 规则校验 + 权限刷新 + 发布事件。

        Args:
            force: 管理员手动晋升时跳过规则校验
        """
        if workspace_id is None:
            raise ValueError("workspace_id is required")

        idempotency_key = idempotency_key or (
            f"agent-promote-{agent_id}-{to_stage.value}-{actor}"
        )

        # 1. 分布式锁(同 agent 同时只能一个晋升)
        lock_key = f"agent:maturity:{workspace_id}:{agent_id}"
        holder_id = f"{actor}-{idempotency_key[:8]}"
        handle = await self._lock.acquire(lock_key, holder_id, ttl_seconds=10)
        if not handle.acquired:
            raise AgentPromotionConcurrentError(
                f"agent {agent_id} is being promoted by another operation"
            )

        try:
            # 2. 读取当前状态(不存在则按 novice 新建)
            entity = self._dao.get_by_agent(agent_id, workspace_id)
            if entity is None:
                entity = self._dao.get_or_create(
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
                )
            try:
                current = AgentStage(entity.stage or "novice")
            except ValueError:
                current = AgentStage.NOVICE

            # 3. 幂等: 已在目标阶段
            if current == to_stage:
                logger.info(
                    f"agent {agent_id} already at {to_stage.value}, skip"
                )
                return self._dao.to_response(
                    self._dao.get_by_agent(agent_id, workspace_id)
                )

            # 4. 不允许跨级/降级
            if _STAGE_ORDER.index(to_stage) <= _STAGE_ORDER.index(current):
                raise AgentPromotionInvalidError(
                    f"cannot demote/skip {current.value} → {to_stage.value}"
                )

            # 5. 规则校验(除非 force)
            evidence: Dict[str, Any] = {}
            if not force:
                check = self.check_promotion(agent_id, workspace_id)
                if not check.can_promote:
                    raise AgentPromotionNotMetError(
                        f"promotion conditions not met: {check.missing}"
                    )
                evidence = {"missing_before": check.missing, "gate": check.gate}

            # 6. 刷新评分(确保证据是最新的)
            score = self.recalculate(agent_id, workspace_id)
            evidence["score"] = score

            # 7. 更新阶段 + 权限 + 历史
            permissions = _stage_permissions_dict(to_stage)
            self._dao.update_stage(
                agent_id=agent_id,
                workspace_id=workspace_id,
                new_stage=to_stage.value,
                actor=actor,
                evidence=evidence,
                permissions=permissions,
            )

            # 8. 发布事件(驱动飞轮反哺: 审批阀门/演化权限变化)
            await self._event_bus.publish(
                AssetEvent(
                    event_type=AssetEventType.MATURITY_PROMOTED,
                    asset_id=f"agent:{agent_id}",
                    workspace_id=workspace_id,
                    actor=actor,
                    payload={
                        "subject": "agent_maturity",
                        "agent_id": agent_id,
                        "from": current.value,
                        "to": to_stage.value,
                        "permissions": permissions,
                    },
                    idempotency_key=idempotency_key,
                ),
                partition_key=str(workspace_id),
            )

            updated = self._dao.get_by_agent(agent_id, workspace_id)
            return self._dao.to_response(updated) if updated else {}
        finally:
            await self._lock.release(handle)

    # ------------------------------------------------------------------ #
    # 背书(expert→master 需要 N 人 agent 背书)
    # ------------------------------------------------------------------ #
    async def attest_agent(
        self,
        agent_id: str,
        user_id: str,
        workspace_id: int,
    ) -> Dict[str, Any]:
        """agent 级背书——追加 attest_by(幂等),达标自动检查 master 晋升。"""
        # 确保记录存在
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is None:
            entity = self._dao.get_or_create(
                agent_id=agent_id,
                workspace_id=workspace_id,
                default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
            )

        attest_by = self._dao.add_attest(agent_id, workspace_id, user_id)

        # 发布 agent attest 事件(便于审计/反哺)
        await self._event_bus.publish(
            AssetEvent(
                event_type=AssetEventType.ASSET_ATTESTED,
                asset_id=f"agent:{agent_id}",
                workspace_id=workspace_id,
                actor=user_id,
                payload={
                    "subject": "agent_attest",
                    "agent_id": agent_id,
                    "attest_by": attest_by,
                    "attest_count": len(attest_by),
                },
                idempotency_key=f"agent-attest-{agent_id}-{user_id}",
            ),
            partition_key=str(workspace_id),
        )

        # 自动检查 master 晋升(仅在 expert 阶段)
        try:
            current = AgentStage(entity.stage or "novice")
        except ValueError:
            current = AgentStage.NOVICE
        if current == AgentStage.EXPERT and len(attest_by) >= REQUIRED_AGENT_ATTESTS:
            try:
                return await self.promote(
                    agent_id=agent_id,
                    to_stage=AgentStage.MASTER,
                    actor=f"system:{user_id}",
                    workspace_id=workspace_id,
                    idempotency_key=(
                        f"agent-auto-master-{agent_id}-{len(attest_by)}"
                    ),
                )
            except AgentPromotionNotMetError as e:
                logger.info(
                    f"agent {agent_id} attest reached but master not met: {e}"
                )

        return self._dao.to_response(
            self._dao.get_by_agent(agent_id, workspace_id)
        )

    # ------------------------------------------------------------------ #
    # 事件驱动: 加分/减分接口(供 handlers 调用)
    # ------------------------------------------------------------------ #
    def increment_attest_count(
        self, agent_id: str, workspace_id: int, delta: int = 1
    ) -> Optional[Dict[str, Any]]:
        """ASSET_ATTESTED 事件 → 产出 agent 的 attest_count 信用 +1。"""
        # 确保记录存在
        self._dao.get_or_create(
            agent_id=agent_id,
            workspace_id=workspace_id,
            default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
        )
        return self._dao.increment_score_field(
            agent_id=agent_id,
            workspace_id=workspace_id,
            field="attest_count",
            delta=delta,
        )

    def apply_coach_penalty(
        self, agent_id: str, workspace_id: int, severity: str = "minor"
    ) -> Optional[Dict[str, Any]]:
        """ASSET_COACHED 事件 → 产出 agent 的 coach_count 惩罚 +1。"""
        self._dao.get_or_create(
            agent_id=agent_id,
            workspace_id=workspace_id,
            default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
        )
        return self._dao.increment_score_field(
            agent_id=agent_id,
            workspace_id=workspace_id,
            field="coach_count",
            delta=1,
        )

    def increment_evolution_count(
        self, agent_id: str, workspace_id: int, delta: int = 1
    ) -> Optional[Dict[str, Any]]:
        """EVOLUTION_APPLIED 事件 → 主导 agent 的 evolution_count 加分 +1。"""
        self._dao.get_or_create(
            agent_id=agent_id,
            workspace_id=workspace_id,
            default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
        )
        return self._dao.increment_score_field(
            agent_id=agent_id,
            workspace_id=workspace_id,
            field="evolution_count",
            delta=delta,
        )

    def set_score_field(
        self, agent_id: str, workspace_id: int, field: str, value: Any
    ) -> Optional[Dict[str, Any]]:
        """测量型信号(如评测分数) → 直接设置 score_json 字段值(非累加)。

        供评测联动(maturity_link)写入 evaluation_score 等 float 字段使用。
        """
        self._dao.get_or_create(
            agent_id=agent_id,
            workspace_id=workspace_id,
            default_permissions=_stage_permissions_dict(AgentStage.NOVICE),
        )
        return self._dao.set_score_field(
            agent_id=agent_id,
            workspace_id=workspace_id,
            field=field,
            value=value,
        )

    def on_trace_finalized(
        self, agent_id: str, workspace_id: int
    ) -> Dict[str, Any]:
        """TRACE_FINALIZED 事件 → 重算执行统计(执行量/成功率)。"""
        return self.recalculate(agent_id, workspace_id)

    # ------------------------------------------------------------------ #
    # 权限查询
    # ------------------------------------------------------------------ #
    def get_permissions(
        self, agent_id: str, workspace_id: int
    ) -> Dict[str, Any]:
        """返回当前阶段权限——若记录缺失返回 novice 默认权限。"""
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is None:
            return _stage_permissions_dict(AgentStage.NOVICE)
        try:
            stage = AgentStage(entity.stage or "novice")
        except ValueError:
            stage = AgentStage.NOVICE
        perms = _load_json(entity.permissions_json, default={}) or {}
        if not isinstance(perms, dict) or not perms:
            perms = _stage_permissions_dict(stage)
        return perms

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get_maturity(
        self, agent_id: str, workspace_id: int
    ) -> Optional[Dict[str, Any]]:
        entity = self._dao.get_by_agent(agent_id, workspace_id)
        if entity is None:
            return None
        return self._dao.to_response(entity)

    def list_by_workspace(
        self,
        workspace_id: int,
        stage: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        entities = self._dao.list_by_workspace(workspace_id, stage=stage)
        return [self._dao.to_response(e) for e in entities]


# --------------------------------------------------------------------------- #
# 异常
# --------------------------------------------------------------------------- #
class AgentPromotionConcurrentError(Exception):
    """并发晋升冲突"""
    pass


class AgentPromotionInvalidError(Exception):
    """无效的晋升操作(降级/跨级)"""
    pass


class AgentPromotionNotMetError(Exception):
    """晋升条件未满足"""
    pass
