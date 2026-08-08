"""Gpts CompressionSegment 数据库模型和 DAO.

持久化 BAIZE ContextEngine 的"两段式压缩"摘要段。每行 = 一次压缩：
把"压缩区"内的全部消息（gpts_message + work_log）用 LLM 摘要成一条 user 消息，
记录边界（boundary_message_id）与增量链（prev_segment_id）。

加载时：最新段(summary) 作为 user 消息置于上下文开头，其 boundary 之后的消息
逐字保留；boundary 之前（含历史段覆盖的）不再单独喂 LLM。UI 侧按段渲染压缩点。
"""

import hashlib
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)

from gyra.storage.metadata import BaseDao, Model


class GptsColdSegmentEntity(Model):
    """压缩段实体（表名沿用 gpts_cold_segments，语义改为"压缩段"）。

    每行 = 一次压缩。segment_index = 压缩序号 seq（1,2,3...）。
    """

    __tablename__ = "gpts_cold_segments"
    __table_args__ = (
        UniqueConstraint("session_id", "content_hash", name="uk_cold_session_hash"),
        Index("idx_cold_session", "session_id"),
        Index("idx_compress_session_seq", "session_id", "segment_index"),
    )

    id = Column(Integer, primary_key=True, comment="autoincrement id")

    session_id = Column(
        String(255), nullable=False, comment="The session id of the conversation"
    )
    conv_id = Column(
        String(255), nullable=False, comment="The conv id that produced this compression"
    )
    content_hash = Column(
        String(64),
        nullable=False,
        comment="Stable fingerprint of this segment (source ids + seq); informational",
    )
    segment_index = Column(
        Integer, nullable=False, default=1, comment="Compression sequence number (1,2,3...)"
    )

    # 本次压缩覆盖的最后一条 message_id（压缩边界）
    boundary_message_id = Column(
        String(128), nullable=True, comment="Last message_id covered by this compression"
    )
    # 上一次压缩段 id（增量链）
    prev_segment_id = Column(
        Integer, nullable=True, comment="Previous compression segment id (incremental chain)"
    )

    # 摘要正文（作为 user 消息的完整 content）
    summary = Column(
        Text(length=2**31 - 1), nullable=True, comment="Compressed summary content (user msg)"
    )
    source_message_ids = Column(
        Text, nullable=True, comment="Source message ids covered (JSON array)"
    )
    original_tokens = Column(
        Integer, nullable=False, default=0, comment="Original token count of compressed zone"
    )
    compressed_tokens = Column(
        Integer, nullable=False, default=0, comment="Compressed summary token count"
    )
    degraded = Column(
        Integer,
        nullable=False,
        default=0,
        comment="1 if truncation fallback (not normally persisted)",
    )

    created_at = Column(
        DateTime, name="gmt_create", default=datetime.utcnow, comment="create time"
    )
    updated_at = Column(
        DateTime,
        name="gmt_modified",
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="last update time",
    )


def _compute_content_hash(source_message_ids: List[str], seq: int) -> str:
    raw = f"{','.join(source_message_ids)}|{seq}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class GptsColdSegmentDao(BaseDao):
    """压缩段 DAO。按 (session_id, segment_index) 组织增量链。"""

    def _to_dict(self, entity: GptsColdSegmentEntity) -> dict:
        return {
            "id": entity.id,
            "session_id": entity.session_id,
            "conv_id": entity.conv_id,
            "content_hash": entity.content_hash,
            "segment_index": entity.segment_index,
            "boundary_message_id": entity.boundary_message_id,
            "prev_segment_id": entity.prev_segment_id,
            "summary": entity.summary,
            "source_message_ids": json.loads(entity.source_message_ids)
            if entity.source_message_ids
            else [],
            "original_tokens": entity.original_tokens,
            "compressed_tokens": entity.compressed_tokens,
            "degraded": bool(entity.degraded),
        }

    # ------------------------------------------------------------------ #
    # 同步
    # ------------------------------------------------------------------ #
    def append_segment(
        self,
        session_id: str,
        conv_id: str,
        seq: int,
        summary: str,
        source_message_ids: List[str],
        boundary_message_id: Optional[str] = None,
        prev_segment_id: Optional[int] = None,
        original_tokens: int = 0,
        compressed_tokens: int = 0,
        degraded: bool = False,
    ) -> int:
        """追加一条压缩段（每次压缩都是新行，不 upsert）。"""
        session = self.get_raw_session()
        try:
            entity = GptsColdSegmentEntity(
                session_id=session_id,
                conv_id=conv_id,
                content_hash=_compute_content_hash(source_message_ids, seq),
                segment_index=seq,
                boundary_message_id=boundary_message_id,
                prev_segment_id=prev_segment_id,
                summary=summary,
                source_message_ids=json.dumps(source_message_ids, ensure_ascii=False),
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                degraded=1 if degraded else 0,
            )
            session.add(entity)
            session.commit()
            return entity.id
        finally:
            session.close()

    def get_latest_by_session(self, session_id: str) -> Optional[dict]:
        """取最新压缩段（segment_index 最大）。"""
        session = self.get_raw_session()
        try:
            entity = (
                session.query(GptsColdSegmentEntity)
                .filter(GptsColdSegmentEntity.session_id == session_id)
                .order_by(GptsColdSegmentEntity.segment_index.desc())
                .first()
            )
            return self._to_dict(entity) if entity else None
        finally:
            session.close()

    def get_all_by_session(self, session_id: str) -> List[dict]:
        """取全部压缩段（按 seq 升序，UI 压缩历史用）。"""
        session = self.get_raw_session()
        try:
            entities = (
                session.query(GptsColdSegmentEntity)
                .filter(GptsColdSegmentEntity.session_id == session_id)
                .order_by(GptsColdSegmentEntity.segment_index.asc())
                .all()
            )
            return [self._to_dict(e) for e in entities]
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # 异步
    # ------------------------------------------------------------------ #
    async def append_segment_async(
        self,
        session_id: str,
        conv_id: str,
        seq: int,
        summary: str,
        source_message_ids: List[str],
        boundary_message_id: Optional[str] = None,
        prev_segment_id: Optional[int] = None,
        original_tokens: int = 0,
        compressed_tokens: int = 0,
        degraded: bool = False,
    ) -> int:
        async with self.a_session(commit=True) as session:
            entity = GptsColdSegmentEntity(
                session_id=session_id,
                conv_id=conv_id,
                content_hash=_compute_content_hash(source_message_ids, seq),
                segment_index=seq,
                boundary_message_id=boundary_message_id,
                prev_segment_id=prev_segment_id,
                summary=summary,
                source_message_ids=json.dumps(source_message_ids, ensure_ascii=False),
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                degraded=1 if degraded else 0,
            )
            session.add(entity)
            await session.flush()
            return entity.id

    async def get_latest_by_session_async(self, session_id: str) -> Optional[dict]:
        async with self.a_session(commit=False) as session:
            result = await session.execute(
                select(GptsColdSegmentEntity)
                .where(GptsColdSegmentEntity.session_id == session_id)
                .order_by(GptsColdSegmentEntity.segment_index.desc())
                .limit(1)
            )
            entity = result.scalars().first()
            return self._to_dict(entity) if entity else None

    async def get_all_by_session_async(self, session_id: str) -> List[dict]:
        async with self.a_session(commit=False) as session:
            result = await session.execute(
                select(GptsColdSegmentEntity)
                .where(GptsColdSegmentEntity.session_id == session_id)
                .order_by(GptsColdSegmentEntity.segment_index.asc())
            )
            entities = result.scalars().all()
            return [self._to_dict(e) for e in entities]
