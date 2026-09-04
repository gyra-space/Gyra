"""Recall stats persistence in the platform metadata database.

Implements the gyra-core ``RecallStatsBackend`` interface on top of the
main database (``[service.web.database]``), so memory promotion scoring
keeps consistent across process restarts and distributed nodes —
instead of a per-node local SQLite file under ``data/memory/``.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from gyra.storage.memory.recall_tracker import RecallStatsBackend
from gyra.storage.metadata import BaseDao, Model, db

logger = logging.getLogger(__name__)

RECALL_STATS_TABLE_NAME = "gyra_memory_recall_stats"


class RecallStatsEntity(Model):
    """Aggregated per-memory recall statistics (RecallTracker)."""

    __tablename__ = RECALL_STATS_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    memory_id = Column(String(255), nullable=False, unique=True, index=True)
    space_id = Column(String(255), index=True)
    recall_count = Column(Integer, nullable=False, default=0)
    total_score = Column(Float, nullable=False, default=0.0)
    query_hashes = Column(Text)
    recall_days = Column(Text)
    last_recalled = Column(DateTime)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class RecallStatsDao(BaseDao[RecallStatsEntity, Dict[str, Any], Dict[str, Any]]):
    """DAO for recall stats rows (portable upsert, no dialect SQL)."""

    def ensure_table(self) -> bool:
        """Create the table if missing. Returns False on failure."""
        try:
            RecallStatsEntity.__table__.create(
                RecallStatsEntity.db().engine, checkfirst=True
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("[recall-stats] ensure_table failed: %s", e)
            return False

    @staticmethod
    def _to_row(entity: RecallStatsEntity) -> Dict[str, Any]:
        return {
            "memory_id": entity.memory_id,
            "space_id": entity.space_id,
            "recall_count": entity.recall_count or 0,
            "total_score": entity.total_score or 0.0,
            "query_hashes": json.loads(entity.query_hashes or "[]"),
            "recall_days": json.loads(entity.recall_days or "[]"),
            "last_recalled": entity.last_recalled.isoformat()
            if entity.last_recalled
            else None,
        }

    def load_all(self) -> List[Dict[str, Any]]:
        with self.session() as session:
            entities = session.query(RecallStatsEntity).all()
            return [self._to_row(e) for e in entities]

    def upsert_stats(self, row: Dict[str, Any]) -> None:
        with self.session() as session:
            entity = (
                session.query(RecallStatsEntity)
                .filter(RecallStatsEntity.memory_id == row["memory_id"])
                .first()
            )
            if entity is None:
                entity = RecallStatsEntity(memory_id=row["memory_id"])
                session.add(entity)
            entity.space_id = row.get("space_id")
            entity.recall_count = row.get("recall_count") or 0
            entity.total_score = row.get("total_score") or 0.0
            entity.query_hashes = json.dumps(row.get("query_hashes") or [])
            entity.recall_days = json.dumps(row.get("recall_days") or [])
            entity.last_recalled = _parse_dt(row.get("last_recalled"))

    def delete_stats(self, memory_ids: Optional[Set[str]] = None) -> None:
        with self.session() as session:
            query = session.query(RecallStatsEntity)
            if memory_ids is None:
                query.delete(synchronize_session=False)
            elif memory_ids:
                query.filter(
                    RecallStatsEntity.memory_id.in_(memory_ids)
                ).delete(synchronize_session=False)


class DatabaseRecallStatsBackend(RecallStatsBackend):
    """Persist recall stats into the platform metadata database."""

    def __init__(self, dao: Optional[RecallStatsDao] = None):
        self._dao = dao or RecallStatsDao()

    def init(self) -> None:
        self._dao.ensure_table()

    def load(self) -> List[Dict[str, Any]]:
        return self._dao.load_all()

    def upsert(self, row: Dict[str, Any]) -> None:
        self._dao.upsert_stats(row)

    def delete(self, memory_ids: Optional[Set[str]] = None) -> None:
        self._dao.delete_stats(memory_ids)


def create_recall_stats_backend() -> Optional[RecallStatsBackend]:
    """Return a main-DB backend, or None for in-memory tracking.

    Falls back to None (in-memory) when the platform database is not
    initialized, e.g. unit tests or headless tooling.
    """
    try:
        if not db.is_initialized:
            logger.info(
                "[recall-stats] metadata DB not initialized; "
                "recall tracking falls back to in-memory"
            )
            return None
        return DatabaseRecallStatsBackend()
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "[recall-stats] main-DB backend unavailable, "
            "recall tracking falls back to in-memory: %s",
            e,
        )
        return None
