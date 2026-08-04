"""沉淀管线服务 —— 实现 Sedimentable 协议。

职责:
- L2MemorySedimentSource: 从agent L2记忆采集高频召回的promoted记忆作为沉淀候选
- AssetSedimentSink: 接收沉淀提案,创建workspace_asset(maturity=draft),幂等去重
- SedimentPipeline: 编排沉淀流程(采集→接收→发布事件)
- SedimentToInterventionHandler: 监听SEDIMENT_RECEIVED事件,创建人审Intervention

边界:
- L2记忆晋升 = agent个体经验变重要(私有)
- 沉淀为ws_asset = 组织资产(共享,需人review)
- 单向: L2 → ws_asset

分布式语义:
- 幂等: 基于source_memory_id生成幂等键,重复沉淀不重复创建
- 事件驱动: 沉淀完成后发布SEDIMENT_RECEIVED,触发人审
- 跨进程: agent节点采集候选,沉淀worker节点接收
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from gyra.component import SystemApp
from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    EventHandler,
    LocalEventBus,
    SedimentProposal,
    SedimentSink,
    SedimentSource,
)
from gyra_serve.core import BaseService

from ..api.schemas import AssetRequest
from ..config import ServeConfig
from ..models.models import AssetDao, AssetEntity
from .service import ASSET_SERVICE_COMPONENT_NAME, AssetService

SEDIMENT_SERVICE_COMPONENT_NAME = "serve_sediment_service"
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# L2记忆沉淀源
# --------------------------------------------------------------------------- #
class L2MemorySedimentSource:
    """L2记忆沉淀源 —— 从agent L2记忆采集高频召回的promoted记忆。

    采集逻辑:
    1. 查询recall_tracker中recall_count >= min_recall的记忆
    2. 过滤已promoted的记忆(promotion_engine设置的metadata.promoted=True)
    3. 生成SedimentProposal

    依赖 LongTermMemoryManager 提供的:
    - memory_stores: 绑定的记忆空间
    - get_recall_stats(space_id): 召回统计
    - config.wing: 记忆归属标识
    """

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        memory_manager_factory: Optional[Callable[[str], Any]] = None,
        min_recall: int = 5,
        asset_type: str = "case",
    ):
        """
        Args:
            memory_manager: LongTermMemoryManager实例(单agent场景)
            memory_manager_factory: 按agent_id解析manager的工厂(多agent场景)
            min_recall: 最小召回次数阈值,默认5
            asset_type: 沉淀为哪种资产类型,默认case
        """
        self._memory_manager = memory_manager
        self._memory_manager_factory = memory_manager_factory
        self._min_recall = min_recall
        self._asset_type = asset_type

    def _resolve_manager(self, agent_id: Optional[str]) -> Optional[Any]:
        """解析agent对应的LongTermMemoryManager"""
        if agent_id and self._memory_manager_factory:
            return self._memory_manager_factory(agent_id)
        return self._memory_manager

    async def collect_candidates(
        self,
        workspace_id: int,
        agent_id: Optional[str] = None,
    ) -> List[SedimentProposal]:
        """采集可沉淀的候选——查询高频召回的promoted记忆

        Args:
            workspace_id: 目标workspace ID
            agent_id: agent标识,用于解析对应的memory manager

        Returns:
            沉淀提案列表
        """
        manager = self._resolve_manager(agent_id)
        if manager is None:
            logger.info("[Sediment:Source] no memory manager, skip")
            return []

        proposals: List[SedimentProposal] = []

        # 遍历所有绑定的记忆空间
        for space_id, store in manager.memory_stores.items():
            try:
                # 获取召回统计
                stats = await manager.get_recall_stats(space_id)
                if not stats:
                    continue

                for memory_id, stat in stats.items():
                    recall_count = self._get_stat(stat, "recall_count", 0)
                    # 过滤:召回次数达标
                    if recall_count < self._min_recall:
                        continue

                    # 尝试读取记忆内容和promoted标记
                    content, is_promoted = await self._fetch_memory(
                        store, memory_id, manager,
                    )

                    # 只采集promoted的记忆;无法确认promoted时,
                    # 召回次数达到2倍阈值视为已promoted(高频即重要)
                    if not is_promoted and recall_count < self._min_recall * 2:
                        continue

                    proposals.append(SedimentProposal(
                        source_agent_id=agent_id or "unknown",
                        source_memory_id=memory_id,
                        target_workspace_id=workspace_id,
                        asset_type=self._asset_type,
                        title=self._build_title(memory_id, content),
                        content=content or (
                            f"从L2记忆{memory_id}沉淀"
                            f"(召回{recall_count}次)"
                        ),
                        evidence={
                            "recall_count": recall_count,
                            "average_score": self._get_stat(
                                stat, "average_score", 0.0,
                            ),
                            "unique_queries": self._get_stat(
                                stat, "unique_queries", 0,
                            ),
                            "space_id": space_id,
                            "promoted": is_promoted,
                        },
                        confidence=min(1.0, recall_count / 20.0),
                    ))
            except Exception as e:
                logger.warning(
                    f"[Sediment:Source] collect from space {space_id} failed: {e}"
                )
                continue

        logger.info(
            f"[Sediment:Source] collected {len(proposals)} candidates "
            f"for workspace={workspace_id} agent={agent_id}"
        )
        return proposals

    async def _fetch_memory(
        self,
        store: Any,
        memory_id: str,
        manager: Any,
    ) -> Tuple[str, bool]:
        """从store读取记忆内容和promoted标记

        Returns:
            (content, is_promoted)
        """
        # 优先: store支持aget_memory_by_id
        if hasattr(store, "aget_memory_by_id"):
            try:
                entry = await store.aget_memory_by_id(memory_id)
                if entry:
                    is_promoted = (entry.metadata or {}).get("promoted", False)
                    return entry.content, is_promoted
            except Exception as e:
                logger.debug(f"[Sediment:Source] aget_memory_by_id failed: {e}")

        # 回退: asearch_memory按memory_id搜索,匹配ID
        try:
            wing = getattr(manager.config, "wing", None)
            entries = await store.asearch_memory(
                query=memory_id,
                top_k=5,
                wing=wing,
            )
            for entry in entries:
                if entry.id == memory_id:
                    is_promoted = (entry.metadata or {}).get("promoted", False)
                    return entry.content, is_promoted
        except Exception as e:
            logger.debug(f"[Sediment:Source] asearch_memory fallback failed: {e}")

        # 无法读取,返回空内容和未promoted(由上层根据recall_count判断)
        return "", False

    @staticmethod
    def _get_stat(stat: Any, key: str, default: Any) -> Any:
        """从recall统计中取字段(兼容dict和对象)"""
        if isinstance(stat, dict):
            return stat.get(key, default)
        return getattr(stat, key, default)

    @staticmethod
    def _build_title(memory_id: str, content: str) -> str:
        """生成沉淀提案标题"""
        if content:
            snippet = content[:40].replace("\n", " ")
            return f"L2记忆沉淀: {snippet}"
        return f"L2记忆沉淀: {memory_id[:12]}"


# --------------------------------------------------------------------------- #
# 资产沉淀端
# --------------------------------------------------------------------------- #
class AssetSedimentSink:
    """资产沉淀端 —— 接收沉淀提案,创建workspace_asset(maturity=draft)。

    幂等:
    - 基于source_agent_id + content_ref(=source_memory_id)查重
    - 同一source_memory_id不重复创建
    - idempotency_key作为辅助去重键
    """

    def __init__(self, asset_service: AssetService):
        """
        Args:
            asset_service: workspace_asset服务,用于创建资产
        """
        self._asset_service = asset_service

    async def receive(
        self,
        proposal: SedimentProposal,
        idempotency_key: str,
    ) -> str:
        """接收沉淀,返回创建的asset_id(maturity=draft)。幂等。

        Args:
            proposal: 沉淀提案
            idempotency_key: 幂等键(基于source_memory_id)

        Returns:
            asset_id字符串
        """
        # 幂等检查: 同source_agent_id + content_ref(=source_memory_id)不重复创建
        existing_id = self._find_existing(proposal)
        if existing_id is not None:
            logger.info(
                f"[Sediment:Sink] duplicate sediment for "
                f"agent={proposal.source_agent_id} "
                f"memory={proposal.source_memory_id}, "
                f"return existing asset_id={existing_id}"
            )
            return str(existing_id)

        # 创建case类型资产,maturity=draft(DB默认)
        # content_ref存source_memory_id用于幂等查重
        request = AssetRequest(
            workspace_id=proposal.target_workspace_id,
            type=proposal.asset_type,
            name=proposal.title,
            description=f"从agent L2记忆沉淀(来源: {proposal.source_agent_id})",
            scope="workspace",
            content_ref=proposal.source_memory_id,
            content_text=proposal.content,
            tags=["sediment", "l2-memory"],
            is_published=False,
            created_by=f"system:sediment:{proposal.source_agent_id}",
            source_agent_id=proposal.source_agent_id,
        )

        response = self._asset_service.create(request)
        logger.info(
            f"[Sediment:Sink] created asset_id={response.id} "
            f"from memory={proposal.source_memory_id} "
            f"agent={proposal.source_agent_id}"
        )
        return str(response.id)

    def _find_existing(self, proposal: SedimentProposal) -> Optional[int]:
        """查重: 同source_agent_id + content_ref(=source_memory_id)的资产"""
        session = self._asset_service.dao.get_raw_session()
        try:
            entity = session.query(AssetEntity).filter(
                AssetEntity.source_agent_id == proposal.source_agent_id,
                AssetEntity.content_ref == proposal.source_memory_id,
            ).first()
            return entity.id if entity else None
        finally:
            session.close()


# --------------------------------------------------------------------------- #
# 沉淀管线
# --------------------------------------------------------------------------- #
class SedimentPipeline(BaseService):
    """沉淀管线 —— 编排采集→接收→发布事件。

    职责:
    - 从source采集候选
    - 调用sink接收(创建draft资产)
    - 发布SEDIMENT_RECEIVED事件(驱动人审Intervention)

    使用模式:
        pipeline = SedimentPipeline(
            system_app, config,
            source=L2MemorySedimentSource(memory_manager=manager),
        )
        await pipeline.run_sediment_check(agent_id="agent-1", workspace_id=1)
    """

    name = SEDIMENT_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        source: Optional[SedimentSource] = None,
        sink: Optional[SedimentSink] = None,
        event_bus: Optional[AssetEventBus] = None,
        dao: Optional[AssetDao] = None,
    ):
        self._system_app = None
        self._serve_config: ServeConfig = config
        self._source: Optional[SedimentSource] = source
        self._sink: Optional[SedimentSink] = sink
        self._event_bus: AssetEventBus = event_bus or LocalEventBus()
        self._dao: AssetDao = dao
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._dao = self._dao or AssetDao()
        self._system_app = system_app
        # 延迟初始化sink(需要AssetService)
        if self._sink is None:
            asset_service = self._get_asset_service()
            if asset_service:
                self._sink = AssetSedimentSink(asset_service=asset_service)

    def _get_asset_service(self) -> Optional[AssetService]:
        """从system_app获取AssetService"""
        try:
            return self._system_app.get_component(
                ASSET_SERVICE_COMPONENT_NAME, AssetService,
            )
        except Exception:
            return None

    @property
    def dao(self) -> AssetDao:
        return self._dao

    @property
    def config(self) -> ServeConfig:
        return self._serve_config

    @property
    def source(self) -> Optional[SedimentSource]:
        return self._source

    @property
    def sink(self) -> Optional[SedimentSink]:
        return self._sink

    @property
    def event_bus(self) -> AssetEventBus:
        return self._event_bus

    async def run_sediment_check(
        self,
        agent_id: str,
        workspace_id: int,
    ) -> List[str]:
        """执行沉淀检查——采集→接收→发布事件

        Args:
            agent_id: agent标识
            workspace_id: workspace ID

        Returns:
            创建的asset_id列表
        """
        if self._source is None or self._sink is None:
            logger.warning(
                "[Sediment:Pipeline] source or sink not initialized, skip"
            )
            return []

        # 1. 采集候选
        proposals = await self._source.collect_candidates(workspace_id, agent_id)
        if not proposals:
            logger.info(
                f"[Sediment:Pipeline] no candidates for "
                f"agent={agent_id} workspace={workspace_id}"
            )
            return []

        asset_ids: List[str] = []
        for proposal in proposals:
            # 幂等键: 基于source_memory_id
            idempotency_key = self._build_idempotency_key(proposal)

            try:
                # 2. 接收(创建draft资产)
                asset_id = await self._sink.receive(proposal, idempotency_key)
                asset_ids.append(asset_id)

                # 3. 发布SEDIMENT_RECEIVED事件(驱动人审)
                await self._event_bus.publish(
                    AssetEvent(
                        event_type=AssetEventType.SEDIMENT_RECEIVED,
                        asset_id=asset_id,
                        workspace_id=workspace_id,
                        actor=agent_id,
                        payload={
                            "source_agent_id": proposal.source_agent_id,
                            "source_memory_id": proposal.source_memory_id,
                            "asset_type": proposal.asset_type,
                            "title": proposal.title,
                            "confidence": proposal.confidence,
                            "evidence": proposal.evidence,
                        },
                        idempotency_key=idempotency_key,
                    ),
                    partition_key=str(workspace_id),
                )
            except Exception as e:
                logger.warning(
                    f"[Sediment:Pipeline] sediment failed for "
                    f"memory={proposal.source_memory_id}: {e}"
                )
                continue

        logger.info(
            f"[Sediment:Pipeline] sediment check done: "
            f"{len(asset_ids)}/{len(proposals)} created for "
            f"agent={agent_id} workspace={workspace_id}"
        )
        return asset_ids

    @staticmethod
    def _build_idempotency_key(proposal: SedimentProposal) -> str:
        """生成幂等键——基于source_memory_id"""
        return f"sediment-{proposal.source_memory_id}"

    def register_intervention_handler(self) -> None:
        """注册SEDIMENT_RECEIVED事件处理器(创建人审Intervention)"""
        handler = SedimentToInterventionHandler(self._system_app)
        self._event_bus.subscribe(
            AssetEventType.SEDIMENT_RECEIVED,
            handler,
            handler.consumer_group,
        )
        logger.info(
            "[Sediment:Pipeline] registered intervention handler "
            "for SEDIMENT_RECEIVED"
        )


# --------------------------------------------------------------------------- #
# 事件处理器: 沉淀 → 人审Intervention
# --------------------------------------------------------------------------- #
class SedimentToInterventionHandler:
    """沉淀事件处理器 —— 监听SEDIMENT_RECEIVED,创建review介入。

    消费组: sediment-to-intervention
    幂等: 基于event.idempotency_key(InterventionService自身也做幂等)
    """

    consumer_group = "sediment-to-intervention"

    def __init__(self, system_app: SystemApp):
        self._system_app = system_app

    async def handle(self, event: AssetEvent) -> None:
        """处理SEDIMENT_RECEIVED事件——创建review介入"""
        from gyra_serve.intervention.api.schemas import InterventionRequest
        from gyra_serve.intervention.service.service import (
            INTERVENTION_SERVICE_COMPONENT_NAME,
            InterventionService,
        )

        try:
            intervention_service = self._system_app.get_component(
                INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService,
            )
            if intervention_service is None:
                logger.warning(
                    "[Sediment:Handler] InterventionService not found, skip"
                )
                return

            payload = event.payload or {}
            request = InterventionRequest(
                workspace_id=event.workspace_id,
                type="review",
                requested_by="system:sediment",
                question={
                    "tool": "sediment_review",
                    "asset_id": event.asset_id,
                    "title": payload.get("title", ""),
                    "source_agent_id": payload.get("source_agent_id", ""),
                    "source_memory_id": payload.get("source_memory_id", ""),
                },
                context={
                    "asset_id": event.asset_id,
                    "confidence": payload.get("confidence", 0.5),
                    "evidence": payload.get("evidence", {}),
                    "idempotency_key": event.idempotency_key,
                },
            )
            response = intervention_service.create(request)
            logger.info(
                f"[Sediment:Handler] created intervention id={response.id} "
                f"for asset={event.asset_id}"
            )
        except Exception as e:
            logger.warning(
                f"[Sediment:Handler] create intervention failed for "
                f"asset={event.asset_id}: {e}"
            )
