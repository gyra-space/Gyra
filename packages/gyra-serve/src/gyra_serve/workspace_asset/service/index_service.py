"""索引服务 —— 实现 Indexable 协议。

职责:
- 监听 MATURITY_PROMOTED 事件,自动索引资产
- 提供 IndexSink 实现(基于DB,可扩展ES)
- 定时对账修复不一致
- 去重:已在assets_required中的不重复注入

分布式语义:
- 最终一致(事件驱动,有短暂延迟)
- 幂等消费(事件ID作幂等键)
- 定时对账修复
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Index, desc
from sqlalchemy import text as sql_text
from datetime import datetime

from gyra.component import SystemApp
from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    EventHandler,
    IndexDocument,
    IndexPolicy,
    IndexReconciler,
    IndexSink,
    LocalEventBus,
    MaturityLevel,
    ReconcileReport,
    SearchHit,
)
from gyra.storage.metadata import BaseDao, Model
from gyra_serve.core import BaseService

from ..config import ServeConfig
from ..models.models import AssetDao, AssetEntity

INDEX_SERVICE_COMPONENT_NAME = "serve_asset_index_service"
INDEX_TABLE_NAME = "server_app_asset_index"
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 索引存储模型
# --------------------------------------------------------------------------- #
class AssetIndexEntity(Model):
    """资产索引表——统一的检索层"""
    __tablename__ = INDEX_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(128), nullable=False, unique=True, index=True)
    # doc_id = f"{category}:{asset_id}"
    workspace_id = Column(Integer, nullable=False, index=True)
    asset_type = Column(String(32), nullable=False)
    maturity = Column(String(32), nullable=False)
    name = Column(String(256), nullable=False)
    content = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    source_table = Column(String(64), nullable=True)  # 原始表名
    source_id = Column(String(64), nullable=True)     # 原始ID

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AssetIndexDao(BaseDao[AssetIndexEntity, Dict[str, Any], Dict[str, Any]]):
    """索引DAO"""

    def from_request(self, request):
        raise NotImplementedError

    def to_request(self, entity):
        raise NotImplementedError

    def upsert(
        self,
        doc_id: str,
        workspace_id: int,
        asset_type: str,
        maturity: str,
        name: str,
        content: str,
        metadata_json: str,
        source_table: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> AssetIndexEntity:
        import json
        session = self.get_raw_session()
        try:
            entity = session.query(AssetIndexEntity).filter(
                AssetIndexEntity.doc_id == doc_id
            ).first()
            if entity:
                entity.workspace_id = workspace_id
                entity.asset_type = asset_type
                entity.maturity = maturity
                entity.name = name
                entity.content = content
                entity.metadata_json = metadata_json
                entity.source_table = source_table
                entity.source_id = source_id
            else:
                entity = AssetIndexEntity(
                    doc_id=doc_id,
                    workspace_id=workspace_id,
                    asset_type=asset_type,
                    maturity=maturity,
                    name=name,
                    content=content,
                    metadata_json=metadata_json,
                    source_table=source_table,
                    source_id=source_id,
                )
                session.add(entity)
            session.commit()
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def remove(self, doc_id: str) -> None:
        session = self.get_raw_session()
        try:
            entity = session.query(AssetIndexEntity).filter(
                AssetIndexEntity.doc_id == doc_id
            ).first()
            if entity:
                session.delete(entity)
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def get(self, doc_id: str) -> Optional[AssetIndexEntity]:
        session = self.get_raw_session()
        try:
            return session.query(AssetIndexEntity).filter(
                AssetIndexEntity.doc_id == doc_id
            ).first()
        finally:
            session.close()

    def search(
        self,
        workspace_id: int,
        query: Optional[str] = None,
        asset_type: Optional[str] = None,
        min_maturity: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """搜索索引(简单like,生产环境可换ES)"""
        session = self.get_raw_session()
        try:
            q = session.query(AssetIndexEntity).filter(
                AssetIndexEntity.workspace_id == workspace_id
            )
            if asset_type:
                q = q.filter(AssetIndexEntity.asset_type == asset_type)
            if min_maturity:
                levels = ["draft", "proposed", "confirmed", "published", "canonical"]
                idx = levels.index(min_maturity) if min_maturity in levels else 0
                q = q.filter(AssetIndexEntity.maturity.in_(levels[idx:]))
            if query:
                like = f"%{query}%"
                q = q.filter(
                    AssetIndexEntity.name.like(like)
                    | AssetIndexEntity.content.like(like)
                )
            entities = q.order_by(desc(AssetIndexEntity.gmt_modified)).limit(limit).all()
            import json
            results = []
            for e in entities:
                results.append({
                    "doc_id": e.doc_id,
                    "score": 1.0,  # 简单匹配,score=1
                    "content": e.content or "",
                    "metadata": json.loads(e.metadata_json) if e.metadata_json else {},
                    "name": e.name,
                    "asset_type": e.asset_type,
                    "maturity": e.maturity,
                    "source_id": e.source_id,
                })
            return results
        finally:
            session.close()

    def list_doc_ids_by_workspace(self, workspace_id: int) -> List[str]:
        session = self.get_raw_session()
        try:
            rows = session.query(AssetIndexEntity.doc_id).filter(
                AssetIndexEntity.workspace_id == workspace_id
            ).all()
            return [r[0] for r in rows]
        finally:
            session.close()

    def list_all_by_workspace(self, workspace_id: int) -> List[AssetIndexEntity]:
        session = self.get_raw_session()
        try:
            return session.query(AssetIndexEntity).filter(
                AssetIndexEntity.workspace_id == workspace_id
            ).all()
        finally:
            session.close()


# --------------------------------------------------------------------------- #
# IndexSink 实现
# --------------------------------------------------------------------------- #
class DBIndexSink(IndexSink):
    """基于DB的索引端实现——开发环境用,生产可换ES"""

    def __init__(self, dao: Optional[AssetIndexDao] = None):
        self._dao = dao or AssetIndexDao()

    async def upsert(self, doc: IndexDocument, idempotency_key: str) -> None:
        import json
        meta = doc.metadata or {}
        self._dao.upsert(
            doc_id=doc.doc_id,
            workspace_id=meta.get("workspace_id", 0),
            asset_type=meta.get("asset_type", ""),
            maturity=meta.get("maturity", ""),
            name=meta.get("name", ""),
            content=doc.content,
            metadata_json=json.dumps(meta, ensure_ascii=False),
            source_table=meta.get("source_table"),
            source_id=meta.get("source_id"),
        )

    async def remove(self, doc_id: str, idempotency_key: str) -> None:
        self._dao.remove(doc_id)

    async def search(
        self, query: str, filters: Dict[str, Any], limit: int = 10
    ) -> List[SearchHit]:
        results = self._dao.search(
            workspace_id=filters.get("workspace_id", 0),
            query=query,
            asset_type=filters.get("asset_type"),
            min_maturity=filters.get("min_maturity"),
            limit=limit,
        )
        return [
            SearchHit(
                doc_id=r["doc_id"],
                score=r["score"],
                content=r["content"],
                metadata=r["metadata"],
            )
            for r in results
        ]

    async def get(self, doc_id: str) -> Optional[IndexDocument]:
        entity = self._dao.get(doc_id)
        if not entity:
            return None
        import json
        return IndexDocument(
            doc_id=entity.doc_id,
            content=entity.content or "",
            metadata=json.loads(entity.metadata_json) if entity.metadata_json else {},
        )

    async def list_by_workspace(self, workspace_id: int) -> List[str]:
        return self._dao.list_doc_ids_by_workspace(workspace_id)


# --------------------------------------------------------------------------- #
# 事件处理器: 成熟度晋升 → 自动索引
# --------------------------------------------------------------------------- #
class MaturityToIndexHandler(EventHandler):
    """监听 MATURITY_PROMOTED 事件,触发索引

    幂等: 基于event.idempotency_key
    策略: IndexPolicy判断是否应索引
    """

    consumer_group = "index-updater"

    def __init__(
        self,
        asset_dao: AssetDao,
        index_sink: DBIndexSink,
    ):
        self._asset_dao = asset_dao
        self._index_sink = index_sink

    async def handle(self, event: AssetEvent) -> None:
        asset_id_str = event.payload.get("asset_id", event.asset_id)
        try:
            asset_id = int(asset_id_str)
        except (ValueError, TypeError):
            logger.warning(f"[index] invalid asset_id: {asset_id_str}")
            return

        # 读取资产
        session = self._asset_dao.get_raw_session()
        try:
            entity = session.query(AssetEntity).filter(
                AssetEntity.id == asset_id
            ).first()
        finally:
            session.close()

        if entity is None:
            logger.warning(f"[index] asset {asset_id} not found")
            return

        # 策略检查:是否应索引
        from gyra.distributed import MaturityLevel
        min_level = IndexPolicy._policies.get(entity.type)
        if min_level is None:
            return  # 无策略,不索引

        current_level = MaturityLevel(entity.maturity)
        if current_level < min_level:
            # 未达索引门槛,如果在索引中则移除
            doc_id = f"experience:{asset_id}"
            existing = await self._index_sink.get(doc_id)
            if existing:
                await self._index_sink.remove(
                    doc_id, idempotency_key=event.idempotency_key or ""
                )
            return

        # 索引文档
        doc = IndexDocument(
            doc_id=f"experience:{asset_id}",
            content=f"{entity.name}\n{entity.description or ''}\n{entity.content_text or ''}",
            metadata={
                "workspace_id": entity.workspace_id,
                "asset_type": entity.type,
                "maturity": entity.maturity,
                "name": entity.name,
                "source_table": "server_app",
                "source_id": str(asset_id),
                "tags": entity.tags_json,
            },
        )
        await self._index_sink.upsert(
            doc, idempotency_key=event.idempotency_key or f"index-{event.event_id}"
        )
        logger.info(f"[index] indexed asset {asset_id} at {entity.maturity}")


# --------------------------------------------------------------------------- #
# 索引服务
# --------------------------------------------------------------------------- #
class AssetIndexService(BaseService):
    """索引服务——自动索引+检索+对账"""

    name = INDEX_SERVICE_COMPONENT_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: ServeConfig,
        dao: Optional[AssetIndexDao] = None,
        asset_dao: Optional[AssetDao] = None,
        event_bus: Optional[AssetEventBus] = None,
    ):
        self._system_app = None
        self._config = config
        self._dao = dao or AssetIndexDao()
        self._asset_dao = asset_dao or AssetDao()
        self._event_bus = event_bus or LocalEventBus()
        self._sink = DBIndexSink(self._dao)
        self._subscribed = False
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        super().init_app(system_app)
        self._system_app = system_app
        # 订阅事件
        if not self._subscribed:
            self._event_bus.subscribe(
                AssetEventType.MATURITY_PROMOTED,
                MaturityToIndexHandler(self._asset_dao, self._sink),
                MaturityToIndexHandler.consumer_group,
            )
            self._event_bus.subscribe(
                AssetEventType.MATURITY_DEMOTED,
                MaturityToIndexHandler(self._asset_dao, self._sink),
                MaturityToIndexHandler.consumer_group,
            )
            self._subscribed = True

    @property
    def sink(self) -> DBIndexSink:
        return self._sink

    @property
    def dao(self) -> AssetIndexDao:
        return self._dao

    @property
    def config(self) -> ServeConfig:
        return self._config

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #
    async def search(
        self,
        workspace_id: int,
        query: Optional[str] = None,
        asset_type: Optional[str] = None,
        min_maturity: Optional[str] = None,
        limit: int = 10,
        exclude_asset_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """检索资产——去重:排除已在assets_required中的

        Args:
            exclude_asset_ids: Playbook.assets_required声明的,不重复推送
        """
        results = self._dao.search(
            workspace_id=workspace_id,
            query=query,
            asset_type=asset_type,
            min_maturity=min_maturity,
            limit=limit * 2 if exclude_asset_ids else limit,  # 多取以补偿去重
        )
        # 去重
        if exclude_asset_ids:
            exclude_set = set(str(aid) for aid in exclude_asset_ids)
            results = [r for r in results if r.get("source_id") not in exclude_set]
            results = results[:limit]
        return results

    # ------------------------------------------------------------------ #
    # 对账
    # ------------------------------------------------------------------ #
    async def reconcile(self, workspace_id: int) -> ReconcileReport:
        """对账——扫描workspace资产,对比索引,修复缺失/多余"""
        report = ReconcileReport(workspace_id=workspace_id)

        # 1. 列出所有应索引的资产(confirmed+)
        from gyra.distributed import MaturityLevel
        should_index_entities = self._asset_dao.list_by_maturity(
            workspace_id, min_maturity="confirmed", limit=10000
        )
        should_index_ids = {
            f"experience:{e.id}" for e in should_index_entities
        }
        report.checked = len(should_index_entities)

        # 2. 列出索引中所有文档
        indexed_ids = set(await self._sink.list_by_workspace(workspace_id))

        # 3. diff
        missing = should_index_ids - indexed_ids
        extra = indexed_ids - should_index_ids

        # 4. 修复缺失
        import json
        for doc_id in missing:
            try:
                asset_id = int(doc_id.split(":")[1])
                session = self._asset_dao.get_raw_session()
                try:
                    entity = session.query(AssetEntity).filter(
                        AssetEntity.id == asset_id
                    ).first()
                finally:
                    session.close()
                if entity:
                    doc = IndexDocument(
                        doc_id=doc_id,
                        content=f"{entity.name}\n{entity.description or ''}\n{entity.content_text or ''}",
                        metadata={
                            "workspace_id": entity.workspace_id,
                            "asset_type": entity.type,
                            "maturity": entity.maturity,
                            "name": entity.name,
                            "source_table": "server_app",
                            "source_id": str(asset_id),
                        },
                    )
                    await self._sink.upsert(
                        doc, idempotency_key=f"reconcile-{doc_id}-{uuid.uuid4().hex[:8]}"
                    )
                    report.added += 1
            except Exception as e:
                report.errors.append(f"add {doc_id}: {e}")

        # 5. 修复多余
        for doc_id in extra:
            try:
                await self._sink.remove(
                    doc_id, idempotency_key=f"reconcile-rm-{doc_id}"
                )
                report.removed += 1
            except Exception as e:
                report.errors.append(f"remove {doc_id}: {e}")

        logger.info(
            f"[reconcile] ws={workspace_id} checked={report.checked} "
            f"added={report.added} removed={report.removed} errors={len(report.errors)}"
        )
        return report
