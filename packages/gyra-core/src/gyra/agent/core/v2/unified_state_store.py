"""SqlAlchemyStateStore —— V2 事件溯源接入系统统一数据库层。

背景：项目业务数据层（``gyra.storage.metadata``，SQLAlchemy）支持 sqlite / MySQL /
PostgreSQL 动态切换（serve 层 ``[service.web.database]`` 配置初始化全局 ``db``）。
V2 早期实现（DbStateStore）用 stdlib sqlite3 直连本地文件，独立于系统 DB——
导致 MySQL 部署时事件溯源日志仍是本地 SQLite，多机不共享。

本后端把 5 张 V2 专用表（``v2_*``）建到**系统数据库**（跟随动态切换），
分布式部署时事件日志与业务数据同库，天然共享、跨进程可恢复。

使用：
    from gyra.storage.metadata import db  # 全局已 init_db 的 DatabaseManager
    store = SqlAlchemyStateStore(db)

或经 :func:`create_state_store` 自动选择（系统 DB 已初始化 → 本后端）。
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, List, Optional, Tuple

from sqlalchemy import Column, Float, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from gyra.agent.core.v2.state_store import StateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState

# 独立 declarative base：不污染系统 Model 的 metadata，建表由本后端负责
_V2Base = declarative_base()


class _StepEventRow(_V2Base):
    __tablename__ = "v2_step_event"

    event_id = Column(String(64), primary_key=True)
    step_id = Column(String(64), nullable=False)
    conv_id = Column(String(128), nullable=False)
    agent_id = Column(String(128), nullable=False)
    parent_step_id = Column(String(64), nullable=True)
    state = Column(String(32), nullable=False)
    event_type = Column(String(64), nullable=False)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False)
    seq = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)

    __table_args__ = (Index("idx_v2_step_event_conv_seq", "conv_id", "seq"),)


class _StepStateRow(_V2Base):
    __tablename__ = "v2_step_state"

    step_id = Column(String(64), primary_key=True)
    conv_id = Column(String(128), nullable=False)
    state = Column(String(32), nullable=False)
    snapshot = Column(Text, nullable=True)
    updated_at = Column(Float, nullable=False)

    __table_args__ = (Index("idx_v2_step_state_conv", "conv_id"),)


class _AgentLeaseRow(_V2Base):
    __tablename__ = "v2_agent_lease"

    conv_id = Column(String(128), primary_key=True)
    agent_id = Column(String(128), nullable=False)
    lease_expires_at = Column(Float, nullable=False)

    __table_args__ = (Index("idx_v2_lease_expires", "lease_expires_at"),)


class _InteractionCheckpointRow(_V2Base):
    __tablename__ = "v2_interaction_checkpoint"

    request_id = Column(String(64), primary_key=True)
    step_id = Column(String(64), nullable=False)
    conv_id = Column(String(128), nullable=False)
    request_payload = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)

    __table_args__ = (Index("idx_v2_checkpoint_conv", "conv_id"),)


class _ConfirmRecordRow(_V2Base):
    __tablename__ = "v2_confirm_record"

    request_id = Column(String(64), primary_key=True)
    record = Column(Text, nullable=False)
    responded_at = Column(Float, nullable=False)

    __table_args__ = (Index("idx_v2_confirm_record_time", "responded_at"),)


class _AgentTranscriptRow(_V2Base):
    __tablename__ = "v2_agent_transcript"

    transcript_id = Column(String(64), primary_key=True)
    task_id = Column(String(64), nullable=False)
    sub_conv_id = Column(String(128), nullable=False)
    parent_step_id = Column(String(64), nullable=False)
    parent_conv_id = Column(String(128), nullable=False)
    agent_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)
    latest_event_seq = Column(Integer, nullable=False)
    payload = Column(Text, nullable=False)
    updated_at = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_v2_transcript_parent", "parent_conv_id"),
        Index("idx_v2_transcript_task", "task_id"),
    )


class SqlAlchemyStateStore(StateStore):
    """基于系统数据库（DatabaseManager）的 V2 事件溯源后端。

    与 :class:`DbStateStore`（本地 SQLite）实现同一 :class:`StateStore` 契约，
    但表建在系统数据库（跟随 sqlite/MySQL/PostgreSQL 动态切换），
    分布式部署时事件日志跨实例共享。
    """

    def __init__(self, db_manager):
        """绑定已初始化的 DatabaseManager。

        Args:
            db_manager: ``gyra.storage.metadata`` 的 DatabaseManager 实例
                （要求 ``is_initialized`` 为 True）。
        """
        if db_manager is None or not getattr(db_manager, "is_initialized", False):
            raise ValueError(
                "SqlAlchemyStateStore requires an initialized DatabaseManager"
            )
        self._mgr = db_manager
        self._engine = db_manager.engine
        # 建 v2 表（幂等：IF NOT EXISTS）
        _V2Base.metadata.create_all(self._engine)
        self._session = sessionmaker(bind=self._engine)

    # ------------------------------------------------------------------
    # 通用执行（同步 SQLAlchemy session → to_thread）
    # ------------------------------------------------------------------

    def _do(self, fn, *args, **kwargs):
        return asyncio.to_thread(fn, *args, **kwargs)

    def _run_sync(self, fn, *args, **kwargs):
        session = self._session()
        try:
            return fn(session, *args, **kwargs)
        finally:
            session.close()

    # ------------------------------------------------------------------
    # step_event
    # ------------------------------------------------------------------

    async def append_event(self, event: StepEvent) -> None:
        d = event.to_storage_dict()

        def _append(session):
            row = _StepEventRow(
                event_id=d["event_id"],
                step_id=d["step_id"],
                conv_id=d["conv_id"],
                agent_id=d["agent_id"],
                parent_step_id=d.get("parent_step_id"),
                state=d["state"],
                event_type=d["event_type"],
                input=d["input"],
                output=d["output"],
                metadata_json=d.get("metadata", "{}"),
                seq=d["seq"],
                timestamp=d["timestamp"],
            )
            session.add(row)
            session.commit()

        await self._do(self._run_sync, _append)

    async def append_events(self, events: List[StepEvent]) -> None:
        """单事务批量写入（高频 llm_token 节流，减少 DB 往返）。"""
        if not events:
            return

        def _append_many(session):
            for event in events:
                d = event.to_storage_dict()
                session.add(
                    _StepEventRow(
                        event_id=d["event_id"],
                        step_id=d["step_id"],
                        conv_id=d["conv_id"],
                        agent_id=d["agent_id"],
                        parent_step_id=d.get("parent_step_id"),
                        state=d["state"],
                        event_type=d["event_type"],
                        input=d["input"],
                        output=d["output"],
                        metadata_json=d.get("metadata", "{}"),
                        seq=d["seq"],
                        timestamp=d["timestamp"],
                    )
                )
            session.commit()

        await self._do(self._run_sync, _append_many)

    async def get_events(self, conv_id: str, since_seq: int = 0) -> List[StepEvent]:
        def _get(session):
            rows = (
                session.query(_StepEventRow)
                .filter(_StepEventRow.conv_id == conv_id,
                        _StepEventRow.seq >= since_seq)
                .order_by(_StepEventRow.seq.asc())
                .all()
            )
            return [
                StepEvent.from_storage_dict(
                    {
                        "event_id": r.event_id,
                        "step_id": r.step_id,
                        "conv_id": r.conv_id,
                        "agent_id": r.agent_id,
                        "parent_step_id": r.parent_step_id,
                        "state": r.state,
                        "event_type": r.event_type,
                        "input": r.input,
                        "output": r.output,
                        "metadata": r.metadata_json,
                        "seq": r.seq,
                        "timestamp": r.timestamp,
                    }
                )
                for r in rows
            ]

        return await self._do(self._run_sync, _get)

    async def update_event_metadata(self, event_id: str, metadata: dict) -> None:
        def _update(session):
            row = session.get(_StepEventRow, event_id)
            if row is not None:
                row.metadata_json = json.dumps(metadata)
                session.commit()

        await self._do(self._run_sync, _update)

    # ------------------------------------------------------------------
    # step_state
    # ------------------------------------------------------------------

    async def get_step_state(self, step_id: str) -> Optional[Tuple[StepState, dict]]:
        def _get(session):
            row = session.get(_StepStateRow, step_id)
            if row is None:
                return None
            return StepState(row.state), json.loads(row.snapshot or "{}")

        return await self._do(self._run_sync, _get)

    async def set_step_state(
        self, step_id: str, conv_id: str, state: StepState, snapshot: dict
    ) -> None:
        def _set(session):
            row = session.get(_StepStateRow, step_id)
            if row is None:
                session.add(
                    _StepStateRow(
                        step_id=step_id,
                        conv_id=conv_id,
                        state=state.value,
                        snapshot=json.dumps(snapshot),
                        updated_at=time.time(),
                    )
                )
            else:
                row.state = state.value
                row.snapshot = json.dumps(snapshot)
                row.updated_at = time.time()
            session.commit()

        await self._do(self._run_sync, _set)

    # ------------------------------------------------------------------
    # agent_lease（分布式租约：多实例抢同会话处理权）
    # ------------------------------------------------------------------

    async def acquire_lease(self, conv_id: str, agent_id: str, ttl_seconds: int) -> bool:
        def _acquire(session):
            now = time.time()
            expires = now + ttl_seconds
            row = session.get(_AgentLeaseRow, conv_id)
            if row is None or row.lease_expires_at < now:
                session.merge(
                    _AgentLeaseRow(
                        conv_id=conv_id,
                        agent_id=agent_id,
                        lease_expires_at=expires,
                    )
                )
                session.commit()
                return True
            if row.agent_id == agent_id:
                row.lease_expires_at = expires
                session.commit()
                return True
            return False

        return await self._do(self._run_sync, _acquire)

    async def renew_lease(self, conv_id: str, agent_id: str, ttl_seconds: int) -> bool:
        return await self.acquire_lease(conv_id, agent_id, ttl_seconds)

    async def release_lease(self, conv_id: str) -> None:
        def _release(session):
            row = session.get(_AgentLeaseRow, conv_id)
            if row is not None:
                session.delete(row)
                session.commit()

        await self._do(self._run_sync, _release)

    async def scan_expired_leases(self) -> List[str]:
        def _scan(session):
            now = time.time()
            rows = (
                session.query(_AgentLeaseRow)
                .filter(_AgentLeaseRow.lease_expires_at < now)
                .all()
            )
            return [r.conv_id for r in rows]

        return await self._do(self._run_sync, _scan)

    # ------------------------------------------------------------------
    # interaction_checkpoint
    # ------------------------------------------------------------------

    async def save_interaction_checkpoint(
        self, request_id: str, step_id: str, conv_id: str, request_payload: dict
    ) -> None:
        def _save(session):
            session.merge(
                _InteractionCheckpointRow(
                    request_id=request_id,
                    step_id=step_id,
                    conv_id=conv_id,
                    request_payload=json.dumps(request_payload, ensure_ascii=False),
                    created_at=time.time(),
                )
            )
            session.commit()

        await self._do(self._run_sync, _save)

    async def get_interaction_checkpoint(self, request_id: str) -> Optional[dict]:
        def _get(session):
            row = session.get(_InteractionCheckpointRow, request_id)
            if row is None:
                return None
            return {
                "request_id": row.request_id,
                "step_id": row.step_id,
                "conv_id": row.conv_id,
                "request_payload": json.loads(row.request_payload),
                "created_at": row.created_at,
            }

        return await self._do(self._run_sync, _get)

    async def get_interaction_checkpoints_by_conv(self, conv_id: str) -> List[dict]:
        def _get(session):
            rows = (
                session.query(_InteractionCheckpointRow)
                .filter(_InteractionCheckpointRow.conv_id == conv_id)
                .order_by(_InteractionCheckpointRow.created_at.asc())
                .all()
            )
            return [
                {
                    "request_id": row.request_id,
                    "step_id": row.step_id,
                    "conv_id": row.conv_id,
                    "request_payload": json.loads(row.request_payload),
                    "created_at": row.created_at,
                }
                for row in rows
            ]

        return await self._do(self._run_sync, _get)

    async def delete_interaction_checkpoint(self, request_id: str) -> None:
        def _delete(session):
            row = session.get(_InteractionCheckpointRow, request_id)
            if row is not None:
                session.delete(row)
                session.commit()

        await self._do(self._run_sync, _delete)

    # ------------------------------------------------------------------
    # confirm_record（用户确认记录：谁在何时确认了什么）
    # ------------------------------------------------------------------

    async def save_confirm_record(self, request_id: str, record: dict) -> bool:
        """幂等写入确认记录；已存在返回 False（拒绝重复确认）。"""

        def _save(session):
            existing = session.get(_ConfirmRecordRow, request_id)
            if existing is not None:
                return False
            session.add(
                _ConfirmRecordRow(
                    request_id=request_id,
                    record=json.dumps(record, ensure_ascii=False),
                    responded_at=time.time(),
                )
            )
            session.commit()
            return True

        return await self._do(self._run_sync, _save)

    async def get_confirm_record(self, request_id: str) -> Optional[dict]:
        def _get(session):
            row = session.get(_ConfirmRecordRow, request_id)
            if row is None:
                return None
            return json.loads(row.record)

        return await self._do(self._run_sync, _get)

    # ------------------------------------------------------------------
    # agent_transcript
    # ------------------------------------------------------------------

    async def save_transcript(
        self, transcript_id: str, task_id: str, sub_conv_id: str,
        parent_step_id: str, parent_conv_id: str, agent_name: str,
        status: str, latest_event_seq: int, payload: dict,
    ) -> None:
        def _save(session):
            session.merge(
                _AgentTranscriptRow(
                    transcript_id=transcript_id,
                    task_id=task_id,
                    sub_conv_id=sub_conv_id,
                    parent_step_id=parent_step_id,
                    parent_conv_id=parent_conv_id,
                    agent_name=agent_name,
                    status=status,
                    latest_event_seq=latest_event_seq,
                    payload=json.dumps(payload, ensure_ascii=False),
                    updated_at=time.time(),
                )
            )
            session.commit()

        await self._do(self._run_sync, _save)

    def _transcript_row_to_dict(self, row: _AgentTranscriptRow) -> dict:
        return {
            "transcript_id": row.transcript_id,
            "task_id": row.task_id,
            "sub_conv_id": row.sub_conv_id,
            "parent_step_id": row.parent_step_id,
            "parent_conv_id": row.parent_conv_id,
            "agent_name": row.agent_name,
            "status": row.status,
            "latest_event_seq": row.latest_event_seq,
            "payload": json.loads(row.payload),
            "updated_at": row.updated_at,
        }

    async def get_transcript(self, transcript_id: str) -> Optional[dict]:
        def _get(session):
            row = session.get(_AgentTranscriptRow, transcript_id)
            return self._transcript_row_to_dict(row) if row is not None else None

        return await self._do(self._run_sync, _get)

    async def get_transcript_by_task_id(self, task_id: str) -> Optional[dict]:
        def _get(session):
            row = (
                session.query(_AgentTranscriptRow)
                .filter(_AgentTranscriptRow.task_id == task_id)
                .order_by(_AgentTranscriptRow.updated_at.desc())
                .first()
            )
            return self._transcript_row_to_dict(row) if row is not None else None

        return await self._do(self._run_sync, _get)

    async def list_transcripts_for_parent(self, parent_conv_id: str) -> List[dict]:
        def _list(session):
            rows = (
                session.query(_AgentTranscriptRow)
                .filter(_AgentTranscriptRow.parent_conv_id == parent_conv_id)
                .order_by(_AgentTranscriptRow.updated_at.asc())
                .all()
            )
            return [self._transcript_row_to_dict(r) for r in rows]

        return await self._do(self._run_sync, _list)

    async def delete_transcript(self, transcript_id: str) -> None:
        def _delete(session):
            row = session.get(_AgentTranscriptRow, transcript_id)
            if row is not None:
                session.delete(row)
                session.commit()

        await self._do(self._run_sync, _delete)


def _get_system_db_manager() -> Optional[Any]:
    """取全局系统数据库管理器（serve 层 init_db 后可用）。"""
    try:
        from gyra.storage.metadata import db as _system_db
        return _system_db
    except Exception:  # noqa: BLE001
        return None
