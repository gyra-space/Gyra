"""资产成熟度服务 —— 实现 Maturable 协议。

职责:
- 晋升流程(分布式锁+幂等+乐观锁)
- 注册晋升规则(策略模式)
- attest/coach 评委动作
- 发布事件驱动联动(索引/沉淀等)

分布式语义:
- 强一致(走主库事务)
- 分布式锁防并发晋升
- 幂等键去重
- 事件驱动联动
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from gyra.component import SystemApp
from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    DistributedLock,
    IndexPolicy,
    LocalDistributedLock,
    LocalEventBus,
    MaturityLevel,
    MaturityTransition,
    PromotionCheck,
    PromotionRule,
    PromotionRuleRegistry,
    get_shared_event_bus,
)
from gyra_serve.core import BaseService

from ..api.schemas import (
    AssetListFilter, AssetMaturityLogResponse, AssetRequest, AssetResponse,
    AssetSearchRequest, AssetVersionResponse, TaskAssetLinkRequest,
    TaskAssetLinkResponse,
)
from ..config import ServeConfig
from ..models.models import (
    AssetDao, AssetEntity, AssetMaturityLogDao, AssetMaturityLogEntity,
    AssetVersionDao, TaskAssetLinkDao,
)

ASSET_SERVICE_COMPONENT_NAME = "serve_workspace_asset_service"
MATURITY_SERVICE_COMPONENT_NAME = "serve_asset_maturity_service"
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 晋升规则 (策略模式,可扩展)
# --------------------------------------------------------------------------- #
class DraftToProposedRule(PromotionRule):
    """draft → proposed: distill自动沉淀,无阀门"""
    asset_type = "*"  # 通配,适用所有类型
    from_level = MaturityLevel.DRAFT
    to_level = MaturityLevel.PROPOSED

    def check(self, asset) -> PromotionCheck:
        return PromotionCheck(
            can_promote=True,
            gate="auto",
            missing=[],
        )


class ProposedToConfirmedRule(PromotionRule):
    """proposed → confirmed: 需人review"""
    asset_type = "*"
    from_level = MaturityLevel.PROPOSED
    to_level = MaturityLevel.CONFIRMED

    def check(self, asset) -> PromotionCheck:
        return PromotionCheck(
            can_promote=True,
            gate="human_review",
            missing=[],
            reason="requires human review",
        )


class ConfirmedToPublishedRule(PromotionRule):
    """confirmed → published: owner主动发布"""
    asset_type = "*"
    from_level = MaturityLevel.CONFIRMED
    to_level = MaturityLevel.PUBLISHED

    def check(self, asset) -> PromotionCheck:
        return PromotionCheck(
            can_promote=True,
            gate="auto",  # 发布动作本身就是人触发,无额外阀门
            missing=[],
        )


class PublishedToCanonicalRule(PromotionRule):
    """published → canonical: 需N人attest + 引用数达标"""
    asset_type = "*"
    from_level = MaturityLevel.PUBLISHED
    to_level = MaturityLevel.CANONICAL
    REQUIRED_ATTESTS = 3
    REQUIRED_REFS = 2

    def check(self, asset) -> PromotionCheck:
        attest_count = getattr(asset, "attest_count", 0) or 0
        ref_count = getattr(asset, "reference_count", 0) or 0
        missing = []
        if attest_count < self.REQUIRED_ATTESTS:
            missing.append(f"attest_count({attest_count}/{self.REQUIRED_ATTESTS})")
        if ref_count < self.REQUIRED_REFS:
            missing.append(f"reference_count({ref_count}/{self.REQUIRED_REFS})")
        return PromotionCheck(
            can_promote=len(missing) == 0,
            gate="auto",  # 达标自动晋升
            missing=missing,
        )


def register_default_promotion_rules() -> None:
    """注册默认晋升规则(应用启动时调用)"""
    PromotionRuleRegistry.register(DraftToProposedRule())
    PromotionRuleRegistry.register(ProposedToConfirmedRule())
    PromotionRuleRegistry.register(ConfirmedToPublishedRule())
    PromotionRuleRegistry.register(PublishedToCanonicalRule())


def register_default_index_policies() -> None:
    """注册默认索引策略——confirmed及以上才索引"""
    # 所有经验资产类型,confirmed才索引
    for asset_type in [
        "historical_artifact", "case", "checklist",
        "decision_log", "pattern", "sop", "postmortem",
    ]:
        IndexPolicy.register(asset_type, MaturityLevel.CONFIRMED)


# --------------------------------------------------------------------------- #
# 成熟度服务
# --------------------------------------------------------------------------- #
class AssetMaturityService(BaseService):
    """资产成熟度服务——实现 Maturable 协议的晋升流程"""

    name = MATURITY_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        dao: Optional[AssetDao] = None,
        log_dao: Optional[AssetMaturityLogDao] = None,
        lock: Optional[DistributedLock] = None,
        event_bus: Optional[AssetEventBus] = None,
    ):
        self._system_app = None
        self._serve_config: ServeConfig = config
        self._dao: AssetDao = dao
        self._log_dao: AssetMaturityLogDao = log_dao
        self._lock: DistributedLock = lock or LocalDistributedLock()
        self._event_bus: AssetEventBus = event_bus or LocalEventBus()
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or AssetDao()
        self._log_dao = self._log_dao or AssetMaturityLogDao()
        self._system_app = system_app
        # 飞轮联动: 接入共享事件总线(若未装配则降级为 LocalEventBus)
        # 确保资产 attest/coach 事件能被 AgentMaturityService 等下游消费
        if self._event_bus is None or isinstance(self._event_bus, LocalEventBus):
            self._event_bus = get_shared_event_bus(system_app)
        # 注册默认规则和策略
        register_default_promotion_rules()
        register_default_index_policies()

    @property
    def dao(self) -> AssetDao:
        return self._dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    @property
    def log_dao(self) -> AssetMaturityLogDao:
        return self._log_dao

    @property
    def lock(self) -> DistributedLock:
        return self._lock

    @property
    def event_bus(self) -> AssetEventBus:
        return self._event_bus

    # ------------------------------------------------------------------ #
    # 晋升流程
    # ------------------------------------------------------------------ #
    async def promote(
        self,
        asset_id: int,
        to_level: MaturityLevel,
        actor: str,
        idempotency_key: Optional[str] = None,
        note: str = "",
    ) -> AssetMaturityLogResponse:
        """晋升——加锁+幂等+规则校验+事件发布

        分布式语义:
        - 分布式锁防并发晋升(同asset同时只能一个)
        - 幂等:已是指定level则跳过
        - 规则校验:不满足条件抛异常
        - 事件发布:驱动索引/沉淀等联动
        """
        idempotency_key = idempotency_key or f"promote-{asset_id}-{to_level.value}-{actor}"

        # 1. 获取分布式锁
        lock_key = f"asset:maturity:{asset_id}"
        holder_id = f"{actor}-{idempotency_key[:8]}"
        handle = await self._lock.acquire(lock_key, holder_id, ttl_seconds=10)
        if not handle.acquired:
            raise ConcurrentPromotionError(
                f"asset {asset_id} is being promoted by another operation"
            )

        try:
            # 2. 读取当前状态
            asset_response = self._get_entity_response(asset_id)
            if asset_response is None:
                raise AssetNotFoundError(f"asset {asset_id} not found")

            current_level = MaturityLevel(asset_response.maturity)

            # 幂等:已是指定level
            if current_level == to_level:
                logger.info(
                    f"asset {asset_id} already at {to_level.value}, skip"
                )
                logs = self._log_dao.list_by_asset(asset_id)
                return logs[0] if logs else None

            # 不允许降级(降级走demote)
            if current_level > to_level:
                raise InvalidPromotionError(
                    f"cannot demote {current_level.value} → {to_level.value}, use demote()"
                )

            # 3. 查找晋升规则
            rule = PromotionRuleRegistry.get("*", current_level, to_level)
            if rule is None:
                # 尝试具体类型
                rule = PromotionRuleRegistry.get(
                    asset_response.type, current_level, to_level
                )
            if rule is None:
                raise InvalidPromotionError(
                    f"no promotion rule for {asset_response.type}: "
                    f"{current_level.value} → {to_level.value}"
                )

            # 4. 校验晋升条件
            check = rule.check(asset_response)
            if not check.can_promote:
                raise PromotionNotMetError(
                    f"promotion conditions not met: {check.missing}"
                )

            # 5. 人阀门检查
            if check.gate == "human_review":
                # 人触发即视为已通过review,记录actor
                note = note or f"human review by {actor}"

            # 6. 执行晋升(写DB)
            maturity_at = self._update_maturity_at(asset_response, to_level)
            self._dao.update_maturity(
                asset_id=asset_id,
                new_maturity=to_level.value,
                maturity_at_json=json.dumps(maturity_at),
            )

            # 7. 记录日志
            log_entity = self._log_dao.log(
                asset_id=asset_id,
                workspace_id=asset_response.workspace_id,
                from_level=current_level.value,
                to_level=to_level.value,
                actor=actor,
                note=note,
                evidence={
                    "attest_count": asset_response.attest_count,
                    "reference_count": asset_response.reference_count,
                    "idempotency_key": idempotency_key,
                },
            )

            # 8. 发布事件(驱动索引等联动)
            await self._event_bus.publish(
                AssetEvent(
                    event_type=AssetEventType.MATURITY_PROMOTED,
                    asset_id=str(asset_id),
                    workspace_id=asset_response.workspace_id,
                    actor=actor,
                    payload={
                        "from": current_level.value,
                        "to": to_level.value,
                        "asset_type": asset_response.type,
                    },
                    idempotency_key=idempotency_key,
                ),
                partition_key=str(asset_response.workspace_id),
            )

            return self._log_dao.to_response(log_entity)

        finally:
            await self._lock.release(handle)

    async def demote(
        self,
        asset_id: int,
        to_level: MaturityLevel,
        actor: str,
        reason: str,
        idempotency_key: Optional[str] = None,
    ) -> AssetMaturityLogResponse:
        """降级——用于coach纠偏或质量问题"""
        idempotency_key = idempotency_key or f"demote-{asset_id}-{to_level.value}-{actor}"

        lock_key = f"asset:maturity:{asset_id}"
        handle = await self._lock.acquire(
            lock_key, f"{actor}-{idempotency_key[:8]}", ttl_seconds=10
        )
        if not handle.acquired:
            raise ConcurrentPromotionError(f"asset {asset_id} locked")

        try:
            asset_response = self._get_entity_response(asset_id)
            if asset_response is None:
                raise AssetNotFoundError(f"asset {asset_id} not found")

            current_level = MaturityLevel(asset_response.maturity)
            if current_level <= to_level:
                raise InvalidPromotionError("cannot promote via demote()")

            self._dao.update_maturity(asset_id, to_level.value)
            log_entity = self._log_dao.log(
                asset_id=asset_id,
                workspace_id=asset_response.workspace_id,
                from_level=current_level.value,
                to_level=to_level.value,
                actor=actor,
                note=f"demoted: {reason}",
                evidence={"idempotency_key": idempotency_key},
            )

            await self._event_bus.publish(
                AssetEvent(
                    event_type=AssetEventType.MATURITY_DEMOTED,
                    asset_id=str(asset_id),
                    workspace_id=asset_response.workspace_id,
                    actor=actor,
                    payload={
                        "from": current_level.value,
                        "to": to_level.value,
                        "reason": reason,
                    },
                    idempotency_key=idempotency_key,
                ),
                partition_key=str(asset_response.workspace_id),
            )
            return self._log_dao.to_response(log_entity)
        finally:
            await self._lock.release(handle)

    # ------------------------------------------------------------------ #
    # 评委动作: attest / coach
    # ------------------------------------------------------------------ #
    async def attest(
        self,
        asset_id: int,
        user_id: str,
        note: Optional[str] = None,
    ) -> AssetResponse:
        """attest背书——影响资产成熟度和agent成长

        语义:
        - 累计attest数
        - 达标自动检查canonical晋升
        - 发布ASSET_ATTESTED事件(驱动agent成长加分)
        """
        lock_key = f"asset:attest:{asset_id}"
        handle = await self._lock.acquire(lock_key, user_id, ttl_seconds=5)
        if not handle.acquired:
            raise ConcurrentPromotionError(f"asset {asset_id} attest locked")

        try:
            asset_response = self._get_entity_response(asset_id)
            if asset_response is None:
                raise AssetNotFoundError(f"asset {asset_id} not found")

            # 幂等:同一user不重复attest
            attest_by = list(asset_response.attest_by or [])
            if user_id in attest_by:
                logger.info(f"user {user_id} already attested asset {asset_id}")
                return asset_response

            attest_by.append(user_id)
            attest_count = len(attest_by)

            self._dao.update_maturity(
                asset_id=asset_id,
                new_maturity=asset_response.maturity,
                attest_count=attest_count,
                attest_by_json=json.dumps(attest_by),
            )

            # 发布attest事件(驱动agent成长)
            await self._event_bus.publish(
                AssetEvent(
                    event_type=AssetEventType.ASSET_ATTESTED,
                    asset_id=str(asset_id),
                    workspace_id=asset_response.workspace_id,
                    actor=user_id,
                    payload={
                        "attest_count": attest_count,
                        "source_agent_id": asset_response.source_agent_id,
                    },
                    idempotency_key=f"attest-{asset_id}-{user_id}",
                ),
                partition_key=str(asset_response.workspace_id),
            )

            # 自动检查canonical晋升
            if asset_response.maturity == MaturityLevel.PUBLISHED.value:
                try:
                    await self.promote(
                        asset_id=asset_id,
                        to_level=MaturityLevel.CANONICAL,
                        actor="system",
                        idempotency_key=f"auto-canonical-{asset_id}-{attest_count}",
                        note=f"auto-promote: {attest_count} attests",
                    )
                except (PromotionNotMetError, InvalidPromotionError):
                    pass  # 条件未满足,正常

            return self._get_entity_response(asset_id)
        finally:
            await self._lock.release(handle)

    async def coach(
        self,
        asset_id: int,
        user_id: str,
        coach_note: str,
        severity: str = "minor",
    ) -> AssetMaturityLogResponse:
        """coach纠偏——记录负反馈,严重时降级

        语义:
        - minor: 仅记录,不降级
        - major: 降一级
        - critical: 直接降到draft
        """
        asset_response = self._get_entity_response(asset_id)
        if asset_response is None:
            raise AssetNotFoundError(f"asset {asset_id} not found")

        current_level = MaturityLevel(asset_response.maturity)

        # 发布coach事件(驱动agent成长减分 + 记忆负样本)
        await self._event_bus.publish(
            AssetEvent(
                event_type=AssetEventType.ASSET_COACHED,
                asset_id=str(asset_id),
                workspace_id=asset_response.workspace_id,
                actor=user_id,
                payload={
                    "coach_note": coach_note,
                    "severity": severity,
                    "source_agent_id": asset_response.source_agent_id,
                },
                idempotency_key=f"coach-{asset_id}-{user_id}-{uuid.uuid4().hex[:8]}",
            ),
            partition_key=str(asset_response.workspace_id),
        )

        # 降级
        if severity == "major" and current_level > MaturityLevel.DRAFT:
            target = MaturityLevel.DRAFT
            levels = list(MaturityLevel)
            idx = levels.index(current_level)
            if idx > 0:
                target = levels[idx - 1]
            return await self.demote(
                asset_id=asset_id,
                to_level=target,
                actor=user_id,
                reason=f"coach(major): {coach_note}",
            )
        elif severity == "critical":
            return await self.demote(
                asset_id=asset_id,
                to_level=MaturityLevel.DRAFT,
                actor=user_id,
                reason=f"coach(critical): {coach_note}",
            )
        else:
            # minor: 仅记录日志
            self._log_dao.log(
                asset_id=asset_id,
                workspace_id=asset_response.workspace_id,
                from_level=current_level.value,
                to_level=current_level.value,
                actor=user_id,
                note=f"coach(minor): {coach_note}",
                evidence={"severity": severity},
            )
            return self._log_dao.list_by_asset(asset_id)[0]

    # ------------------------------------------------------------------ #
    # 引用计数(任务复用时调用)
    # ------------------------------------------------------------------ #
    async def increment_reference(self, asset_id: int) -> None:
        """引用计数+1,并检查canonical晋升"""
        self._dao.increment_reference(asset_id)

        # 异步检查canonical
        asset_response = self._get_entity_response(asset_id)
        if asset_response and asset_response.maturity == MaturityLevel.PUBLISHED.value:
            try:
                await self.promote(
                    asset_id=asset_id,
                    to_level=MaturityLevel.CANONICAL,
                    actor="system",
                    idempotency_key=f"auto-canonical-ref-{asset_id}-{asset_response.reference_count}",
                    note="auto-promote: reference count met",
                )
            except (PromotionNotMetError, InvalidPromotionError):
                pass

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def list_maturity_logs(self, asset_id: int) -> List[AssetMaturityLogResponse]:
        return self._log_dao.list_by_asset(asset_id)

    def list_by_maturity(
        self,
        workspace_id: int,
        min_maturity: str = "confirmed",
        limit: int = 100,
    ) -> List[AssetResponse]:
        """列出达到某成熟度及以上的资产"""
        entities = self._dao.list_by_maturity(workspace_id, min_maturity, limit)
        return [self._dao.to_response(e) for e in entities]

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _get_entity_response(self, asset_id: int) -> Optional[AssetResponse]:
        session = self._dao.get_raw_session()
        try:
            entity = session.query(AssetEntity).filter(
                AssetEntity.id == asset_id
            ).first()
            return self._dao.to_response(entity) if entity else None
        finally:
            session.close()

    def _update_maturity_at(
        self,
        asset_response: AssetResponse,
        to_level: MaturityLevel,
    ) -> Dict[str, str]:
        """更新各级达成时间戳"""
        # 解析已有的maturity_at
        from ..models.models import _load_json
        session = self._dao.get_raw_session()
        try:
            entity = session.query(AssetEntity).filter(
                AssetEntity.id == asset_response.id
            ).first()
            maturity_at = _load_json(entity.maturity_at_json) if entity else {}
            if not isinstance(maturity_at, dict):
                maturity_at = {}
            maturity_at[to_level.value] = datetime.now().isoformat()
            return maturity_at
        finally:
            session.close()


# --------------------------------------------------------------------------- #
# 异常
# --------------------------------------------------------------------------- #
class ConcurrentPromotionError(Exception):
    """并发晋升冲突"""
    pass


class AssetNotFoundError(Exception):
    """资产不存在"""
    pass


class InvalidPromotionError(Exception):
    """无效的晋升操作"""
    pass


class PromotionNotMetError(Exception):
    """晋升条件未满足"""
    pass
