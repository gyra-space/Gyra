"""AsyncTask 异步任务数据库模型和 DAO（DB 持久化，替代 JSONL 台账）。

统一承载 media（生成图片/视频）与 subagent（spawn_agent_task）两类异步任务，
用独立的 ``gpts_async_tasks`` 表持久化任务状态，支持多实例/分布式查询与恢复
（JSONL 台账在分布式下每个进程各存一份，无法共享，故改为 DB）。

设计原则：
- 与 gpts_conversations 的 extra pending 台账互补：extra 只存「引用 + 状态」，
  extra 剩下的完整记录（结果预览、交付物 artifact）落本表，供查询 API / 恢复读取。
- 单 task_id 唯一，upsert 幂等；状态变更时覆盖写入。
- AsyncTaskManager（gyra-core）通过可注入 ledger 接口接入本 DAO，core 不反向依赖 serve。
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    select,
)

from gyra.storage.metadata import BaseDao, Model


class AsyncTaskEntity(Model):
    """异步任务实体：media 生成 / subagent 委派任务的一行记录。"""

    __tablename__ = "gpts_async_tasks"
    __table_args__ = (
        Index("idx_async_tasks_conv", "conv_id"),
        Index("idx_async_tasks_status", "status"),
    )

    id = Column(Integer, primary_key=True, comment="autoincrement id")
    task_id = Column(
        String(128), nullable=False, unique=True, comment="The unique async task id"
    )
    conv_id = Column(
        String(255), nullable=True, comment="The conversation id this task belongs to"
    )
    kind = Column(
        String(64), nullable=True, comment="Task kind: video / image / subagent ..."
    )
    model = Column(
        String(255), nullable=True, comment="Model name (media) or agent name (subagent)"
    )
    description = Column(
        Text, nullable=True, comment="Task description / prompt summary"
    )
    status = Column(
        String(32), nullable=False, default="pending",
        comment="pending / running / completed / failed / timeout / cancelled",
    )
    error = Column(Text, nullable=True, comment="Error message when failed")
    result_preview = Column(
        Text, nullable=True, comment="Result preview text (first N chars)"
    )
    artifact = Column(
        Text, nullable=True, comment="Deliverable artifact metadata (JSON)"
    )

    created_at = Column(
        DateTime, name="gmt_create", default=datetime.utcnow, comment="create time"
    )
    started_at = Column(
        DateTime, nullable=True, comment="task start time"
    )
    completed_at = Column(
        DateTime, nullable=True, comment="task completion/failure time"
    )
    updated_at = Column(
        DateTime,
        name="gmt_modified",
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="last update time",
    )


class AsyncTaskDao(BaseDao):
    """异步任务 DAO：按 task_id upsert + 查询。

    与 AsyncTaskManager 的 ledger 接口（upsert(record) / read_all()）对齐，
    使 core 层管理器可无感知切换 JSONL <-> DB 持久化。
    """

    def _parse_entity(self, e: AsyncTaskEntity) -> Dict[str, Any]:
        def _iso(dt: Optional[datetime]) -> Optional[str]:
            return dt.isoformat() if dt else None

        return {
            "task_id": e.task_id,
            "conv_id": e.conv_id or "",
            "kind": e.kind or "",
            "model": e.model or "",
            "description": e.description or "",
            "status": e.status,
            "error": e.error,
            "result_preview": e.result_preview,
            "artifact": json.loads(e.artifact) if e.artifact else None,
            "created_at": _iso(e.created_at),
            "started_at": _iso(e.started_at),
            "completed_at": _iso(e.completed_at),
        }

    def upsert(self, record: Dict[str, Any]) -> None:
        """按 task_id 幂等写入一条任务记录（覆盖旧记录）。"""
        record = dict(record or {})
        task_id = record.get("task_id")
        if not task_id:
            return

        def _dt(v):
            if not v:
                return None
            if isinstance(v, datetime):
                return v
            try:
                return datetime.fromisoformat(str(v))
            except (ValueError, TypeError):
                return None

        session = self.get_raw_session()
        try:
            existing = (
                session.query(AsyncTaskEntity)
                .filter(AsyncTaskEntity.task_id == task_id)
                .first()
            )
            if existing is None:
                existing = AsyncTaskEntity(task_id=task_id)
                session.add(existing)
            existing.conv_id = record.get("conv_id") or None
            existing.kind = record.get("kind") or None
            existing.model = record.get("model") or None
            existing.description = (record.get("description") or "")[:4000]
            existing.status = record.get("status") or "pending"
            existing.error = (record.get("error") or "")[:4000] or None
            existing.result_preview = (record.get("result_preview") or "")[:4000] or None
            existing.artifact = (
                json.dumps(record.get("artifact"), ensure_ascii=False)
                if record.get("artifact")
                else None
            )
            existing.created_at = _dt(record.get("created_at")) or existing.created_at
            existing.started_at = _dt(record.get("started_at"))
            existing.completed_at = _dt(record.get("completed_at"))
            session.commit()
        except Exception as e:  # noqa: BLE001 - 持久化失败不阻断主流程
            session.rollback()
            import logging

            logging.getLogger(__name__).warning(
                f"[AsyncTaskDao] upsert failed for {task_id}: {e}"
            )
        finally:
            session.close()

    def read_all(self) -> Dict[str, Dict[str, Any]]:
        """读取全部任务记录，按 task_id 去重。"""
        session = self.get_raw_session()
        try:
            rows = session.query(AsyncTaskEntity).all()
            return {e.task_id: self._parse_entity(e) for e in rows}
        except Exception as e:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(f"[AsyncTaskDao] read_all failed: {e}")
            return {}
        finally:
            session.close()

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """读取单个任务记录。"""
        session = self.get_raw_session()
        try:
            e = (
                session.query(AsyncTaskEntity)
                .filter(AsyncTaskEntity.task_id == task_id)
                .first()
            )
            return self._parse_entity(e) if e else None
        finally:
            session.close()

    def list(
        self,
        conv_id: str = "",
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """按 conv/status 过滤，创建时间倒序返回。"""
        session = self.get_raw_session()
        try:
            q = session.query(AsyncTaskEntity)
            if conv_id:
                q = q.filter(AsyncTaskEntity.conv_id == conv_id)
            if status:
                q = q.filter(AsyncTaskEntity.status == status)
            rows = q.order_by(AsyncTaskEntity.id.desc()).limit(limit).all()
            return [self._parse_entity(e) for e in rows]
        finally:
            session.close()