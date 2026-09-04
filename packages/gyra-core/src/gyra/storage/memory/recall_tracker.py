"""Recall tracking for memory promotion decisions.

This module tracks memory retrieval history to inform promotion
decisions. Similar to OpenClaw's ShortTermRecallEntry pattern,
it records which memories were retrieved, for what queries, and
how often — enabling multi-component scoring for promotion.

Persistence is pluggable via :class:`RecallStatsBackend`. Out of the box:

- ``RecallTracker()`` — purely in-memory (no persistence).
- ``RecallTracker(db_path=...)`` — SQLite file (single-node / local dev).
- ``RecallTracker(backend=...)`` — any custom backend, e.g. one backed
  by the platform metadata database so stats are shared across
  distributed nodes and survive restarts.
"""

import hashlib
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class RecallEntry:
    """A single recall event."""

    query: str
    space_id: str
    result_ids: List[str]
    result_scores: List[float]
    recalled_at: datetime = field(default_factory=datetime.now)

    @property
    def query_hash(self) -> str:
        return hashlib.md5(self.query.encode()).hexdigest()


@dataclass
class MemoryRecallStats:
    """Aggregated recall statistics for a memory."""

    memory_id: str
    recall_count: int = 0
    total_score: float = 0.0
    unique_queries: int = 0
    recall_days: List[str] = field(default_factory=list)
    last_recalled: Optional[datetime] = None
    concept_tags: List[str] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        return self.total_score / max(1, self.record_count)

    @property
    def record_count(self) -> int:
        return self.recall_count


class RecallStatsBackend(ABC):
    """Persistence backend for aggregated recall stats.

    Implementations persist the per-memory stats needed by the
    promotion score (recall_count, total_score, unique query hashes,
    recall days, last_recalled). Rows are plain dicts with
    JSON-friendly values:

    - ``memory_id``: str
    - ``space_id``: Optional[str]
    - ``recall_count``: int
    - ``total_score``: float
    - ``query_hashes``: List[str]
    - ``recall_days``: List[str] (YYYY-MM-DD)
    - ``last_recalled``: Optional[str] (ISO datetime)
    """

    def init(self) -> None:
        """Ensure the storage exists. Called once on construction."""

    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        """Load all persisted stats rows."""

    @abstractmethod
    def upsert(self, row: Dict[str, Any]) -> None:
        """Insert or update one stats row (keyed by ``memory_id``)."""

    @abstractmethod
    def delete(self, memory_ids: Optional[Set[str]] = None) -> None:
        """Delete rows for the given ``memory_ids``, or all when None."""


class SqliteStatsBackend(RecallStatsBackend):
    """SQLite-file persistence (single-node / local dev)."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def init(self) -> None:
        path = Path(self._db_path)
        if path.parent and str(path.parent) not in ("", "."):
            path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recall_stats (
                    memory_id TEXT PRIMARY KEY,
                    space_id TEXT,
                    recall_count INTEGER,
                    total_score REAL,
                    query_hashes TEXT,
                    recall_days TEXT,
                    last_recalled TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def load(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM recall_stats").fetchall()
        finally:
            conn.close()
        return [
            {
                "memory_id": row["memory_id"],
                "space_id": row["space_id"],
                "recall_count": row["recall_count"] or 0,
                "total_score": row["total_score"] or 0.0,
                "query_hashes": json.loads(row["query_hashes"] or "[]"),
                "recall_days": json.loads(row["recall_days"] or "[]"),
                "last_recalled": row["last_recalled"],
            }
            for row in rows
        ]

    def upsert(self, row: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO recall_stats
                (memory_id, space_id, recall_count, total_score,
                 query_hashes, recall_days, last_recalled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["memory_id"],
                    row.get("space_id"),
                    row.get("recall_count") or 0,
                    row.get("total_score") or 0.0,
                    json.dumps(row.get("query_hashes") or []),
                    json.dumps(row.get("recall_days") or []),
                    row.get("last_recalled"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, memory_ids: Optional[Set[str]] = None) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            if memory_ids is None:
                conn.execute("DELETE FROM recall_stats")
            else:
                for mid in memory_ids:
                    conn.execute(
                        "DELETE FROM recall_stats WHERE memory_id = ?", (mid,)
                    )
            conn.commit()
        finally:
            conn.close()


class RecallTracker:
    """Tracks memory retrieval history for promotion decisions.

    Args:
        db_path: Optional SQLite file path. Shorthand for
            ``backend=SqliteStatsBackend(db_path)`` — single-node
            persistence only.
        backend: Optional :class:`RecallStatsBackend` used to persist
            the per-memory stats needed by the five-component promotion
            score (recall_count, total_score, unique query hashes,
            recall days, last_recalled). Takes precedence over
            ``db_path``. When both are None, tracking is in-memory
            only.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        backend: Optional[RecallStatsBackend] = None,
    ):
        self._entries: List[RecallEntry] = []
        self._stats: Dict[str, MemoryRecallStats] = {}
        # memory_id -> set of query hashes (diversity component)
        self._query_hashes: Dict[str, Set[str]] = {}
        # memory_id -> space_id (a memory belongs to exactly one space)
        self._space_by_memory: Dict[str, str] = {}
        self._backend = backend
        if self._backend is None and db_path:
            self._backend = SqliteStatsBackend(db_path)
        if self._backend is not None:
            self._backend.init()
            self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            rows = self._backend.load()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "[RecallTracker] load persisted stats failed: %s", e
            )
            return
        for row in rows:
            mid = row["memory_id"]
            last_recalled = None
            if row.get("last_recalled"):
                try:
                    last_recalled = datetime.fromisoformat(row["last_recalled"])
                except ValueError:
                    last_recalled = None
            query_hashes = set(row.get("query_hashes") or [])
            self._stats[mid] = MemoryRecallStats(
                memory_id=mid,
                recall_count=row.get("recall_count") or 0,
                total_score=row.get("total_score") or 0.0,
                unique_queries=len(query_hashes),
                recall_days=row.get("recall_days") or [],
                last_recalled=last_recalled,
            )
            self._query_hashes[mid] = query_hashes
            if row.get("space_id"):
                self._space_by_memory[mid] = row["space_id"]
        if rows:
            logger.info(
                "[RecallTracker] loaded %d persisted recall stats from %s",
                len(rows),
                type(self._backend).__name__,
            )

    def _persist(self, memory_id: str) -> None:
        if self._backend is None:
            return
        stats = self._stats.get(memory_id)
        if stats is None:
            return
        row = {
            "memory_id": memory_id,
            "space_id": self._space_by_memory.get(memory_id),
            "recall_count": stats.recall_count,
            "total_score": stats.total_score,
            "query_hashes": sorted(self._query_hashes.get(memory_id, set())),
            "recall_days": list(stats.recall_days),
            "last_recalled": stats.last_recalled.isoformat()
            if stats.last_recalled
            else None,
        }
        try:
            self._backend.upsert(row)
        except Exception as e:  # noqa: BLE001
            logger.warning("[RecallTracker] persist failed for %s: %s", memory_id, e)

    def _delete_persisted(self, memory_ids: Optional[Set[str]] = None) -> None:
        if self._backend is None:
            return
        try:
            self._backend.delete(memory_ids)
        except Exception as e:  # noqa: BLE001
            logger.warning("[RecallTracker] delete persisted rows failed: %s", e)

    # ------------------------------------------------------------------
    # Recording / queries
    # ------------------------------------------------------------------

    async def record(
        self,
        query: str,
        results: List[Any],
        space_id: str,
    ) -> None:
        """Record a retrieval event.

        Args:
            query: The search query
            results: List of MemoryEntry results
            space_id: The memory space ID
        """
        entry = RecallEntry(
            query=query,
            space_id=space_id,
            result_ids=[r.id for r in results],
            result_scores=[r.score or 0.0 for r in results],
        )
        self._entries.append(entry)

        # Update per-memory stats
        day_str = entry.recalled_at.strftime("%Y-%m-%d")
        for mem_id, score in zip(entry.result_ids, entry.result_scores):
            if mem_id not in self._stats:
                self._stats[mem_id] = MemoryRecallStats(memory_id=mem_id)
            stats = self._stats[mem_id]
            stats.recall_count += 1
            stats.total_score += score
            if day_str not in stats.recall_days:
                stats.recall_days.append(day_str)
            stats.last_recalled = entry.recalled_at
            self._space_by_memory[mem_id] = space_id
            hashes = self._query_hashes.setdefault(mem_id, set())
            hashes.add(entry.query_hash)
            stats.unique_queries = len(hashes)
            self._persist(mem_id)

    async def get_recall_stats(
        self,
        space_id: str,
    ) -> Dict[str, MemoryRecallStats]:
        """Get recall statistics for a space.

        Args:
            space_id: The memory space ID

        Returns:
            Dict mapping memory_id to recall stats
        """
        return {
            mid: stats
            for mid, stats in self._stats.items()
            if self._space_by_memory.get(mid) == space_id
        }

    async def get_top_candidates(
        self,
        space_id: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top promotion candidates.

        Multi-component scoring:
        - recall_frequency (0.24): log(recall_count)
        - relevance (0.30): average search score
        - diversity (0.15): unique queries
        - recency (0.15): exponential decay
        - consolidation (0.10): recall day span

        Args:
            space_id: The memory space ID
            top_k: Number of candidates to return

        Returns:
            List of candidate dicts with scores
        """
        import math

        stats = await self.get_recall_stats(space_id)
        candidates = []

        for mid, s in stats.items():
            if s.recall_count == 0:
                continue

            # Frequency: log-scaled
            frequency = min(1.0, math.log1p(s.recall_count) / math.log1p(10))

            # Relevance: average score
            relevance = s.average_score

            # Diversity: unique queries / max
            diversity = min(1.0, s.unique_queries / 5.0)

            # Recency: exponential decay (halflife 30 days)
            if s.last_recalled:
                days_ago = (datetime.now() - s.last_recalled).days
                recency = math.exp(-math.log(2) / 30 * days_ago)
            else:
                recency = 0.0

            # Consolidation: span of recall days
            consolidation = min(1.0, len(s.recall_days) / 7.0)

            # Weighted score
            total = (
                frequency * 0.24
                + relevance * 0.30
                + diversity * 0.15
                + recency * 0.15
                + consolidation * 0.10
            )

            candidates.append({
                "memory_id": mid,
                "recall_count": s.recall_count,
                "average_score": s.average_score,
                "unique_queries": s.unique_queries,
                "recall_days": len(s.recall_days),
                "last_recalled": s.last_recalled,
                "score": round(total, 4),
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates[:top_k]

    async def clear(self, space_id: Optional[str] = None) -> int:
        """Clear recall history.

        Args:
            space_id: If provided, only clear entries for this space

        Returns:
            Number of entries cleared
        """
        if space_id:
            before = len(self._entries)
            self._entries = [e for e in self._entries if e.space_id != space_id]
            doomed = {
                mid
                for mid, sid in self._space_by_memory.items()
                if sid == space_id
            }
            for mid in doomed:
                self._stats.pop(mid, None)
                self._query_hashes.pop(mid, None)
                self._space_by_memory.pop(mid, None)
            self._delete_persisted(doomed)
            return before - len(self._entries)
        else:
            count = len(self._entries)
            self._entries.clear()
            self._stats.clear()
            self._query_hashes.clear()
            self._space_by_memory.clear()
            self._delete_persisted(None)
            return count
