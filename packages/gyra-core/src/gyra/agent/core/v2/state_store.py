"""StateStore——V2 Runtime 持久化接口。

P0 实现 DbStateStore（SQLite，stdlib sqlite3 + asyncio.to_thread）。
后续阶段加 RedisStateStore / HybridStateStore。

``create_state_store`` 提供真实持久化入口（默认落 ``{DATA_DIR}/v2_state``，
按 conv/agent 隔离分文件），替换早期 per-agent ``tempfile`` 临时库——
保证事件溯源日志跨进程/重启可恢复。
"""
from __future__ import annotations
import asyncio
import json
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Tuple, List
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


class StateStore(ABC):
    """持久化接口。所有方法是 async。"""

    @abstractmethod
    async def append_event(self, event: StepEvent) -> None: ...

    async def append_events(self, events: List[StepEvent]) -> None:
        """原子批量追加事件（高频事件节流用）。

        默认逐条回退 :meth:`append_event`；高频场景（llm_token 逐 token）
        建议后端覆盖为单事务批量写入，减少 DB 往返。
        """
        for event in events:
            await self.append_event(event)

    @abstractmethod
    async def get_events(self, conv_id: str, since_seq: int = 0) -> List[StepEvent]: ...

    @abstractmethod
    async def get_step_state(self, step_id: str) -> Optional[Tuple[StepState, dict]]: ...

    @abstractmethod
    async def set_step_state(
        self, step_id: str, conv_id: str, state: StepState, snapshot: dict
    ) -> None: ...

    @abstractmethod
    async def acquire_lease(self, conv_id: str, agent_id: str, ttl_seconds: int) -> bool: ...

    @abstractmethod
    async def renew_lease(self, conv_id: str, agent_id: str, ttl_seconds: int) -> bool: ...

    @abstractmethod
    async def release_lease(self, conv_id: str) -> None: ...

    @abstractmethod
    async def scan_expired_leases(self) -> List[str]: ...

    @abstractmethod
    async def save_interaction_checkpoint(
        self, request_id: str, step_id: str, conv_id: str, request_payload: dict
    ) -> None: ...

    @abstractmethod
    async def get_interaction_checkpoint(self, request_id: str) -> Optional[dict]: ...

    @abstractmethod
    async def delete_interaction_checkpoint(self, request_id: str) -> None: ...

    @abstractmethod
    async def save_transcript(
        self, transcript_id: str, task_id: str, sub_conv_id: str,
        parent_step_id: str, parent_conv_id: str, agent_name: str,
        status: str, latest_event_seq: int, payload: dict,
    ) -> None: ...

    @abstractmethod
    async def get_transcript(self, transcript_id: str) -> Optional[dict]: ...

    @abstractmethod
    async def get_transcript_by_task_id(self, task_id: str) -> Optional[dict]: ...

    @abstractmethod
    async def list_transcripts_for_parent(self, parent_conv_id: str) -> List[dict]: ...

    @abstractmethod
    async def delete_transcript(self, transcript_id: str) -> None: ...

    @abstractmethod
    async def update_event_metadata(self, event_id: str, metadata: dict) -> None: ...


_SCHEMA = """
CREATE TABLE IF NOT EXISTS step_event (
    event_id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    conv_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    parent_step_id TEXT,
    state TEXT NOT NULL,
    event_type TEXT NOT NULL,
    input TEXT,
    output TEXT,
    metadata TEXT DEFAULT '{}',
    seq INTEGER NOT NULL,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_step_event_conv_seq ON step_event(conv_id, seq);

CREATE TABLE IF NOT EXISTS step_state (
    step_id TEXT PRIMARY KEY,
    conv_id TEXT NOT NULL,
    state TEXT NOT NULL,
    snapshot TEXT,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_step_state_conv ON step_state(conv_id);

CREATE TABLE IF NOT EXISTS agent_lease (
    conv_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    lease_expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lease_expires ON agent_lease(lease_expires_at);

CREATE TABLE IF NOT EXISTS interaction_checkpoint (
    request_id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    conv_id TEXT NOT NULL,
    request_payload TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_conv ON interaction_checkpoint(conv_id);

CREATE TABLE IF NOT EXISTS agent_transcript (
    transcript_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    sub_conv_id TEXT NOT NULL,
    parent_step_id TEXT NOT NULL,
    parent_conv_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    latest_event_seq INTEGER NOT NULL,
    payload TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transcript_parent ON agent_transcript(parent_conv_id);
CREATE INDEX IF NOT EXISTS idx_transcript_task ON agent_transcript(task_id);
"""


class DbStateStore(StateStore):
    """SQLite 实现。同步 sqlite3 调用全部包 asyncio.to_thread。"""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._tls = threading.local()  # 每线程一条长连接（to_thread 多线程安全）
        self._init_schema()

    def _init_schema(self):
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        """返回本线程的缓存连接（不存在则建立并配置 WAL/busy_timeout）。

        原实现每次操作新开连接（connect + fsync 握手开销 × 每事件/每查询），
        是流式期间与下一轮全量读的主要延迟来源之一。线程局部复用后：
        - WAL：读写不互斥，读（get_events 投影）不阻塞写（append_event）；
        - busy_timeout：跨线程并发写兜底等待而非 SQLITE_BUSY 报错；
        - close() 只在线程退出或显式 store.close() 时发生。
        """
        conn = getattr(self._tls, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._tls.conn = conn
        return conn

    def close(self) -> None:
        """关闭本线程的缓存连接（其他线程的连接随其线程退出回收）。

        供缓存淘汰/测试清理调用；未调用时连接随线程结束由 sqlite3 回收。
        """
        conn = getattr(self._tls, "conn", None)
        if conn is not None:
            try:
                conn.close()
            finally:
                self._tls.conn = None

    async def append_event(self, event: StepEvent) -> None:
        def _do():
            conn = self._connect()
            try:
                d = event.to_storage_dict()
                # INSERT (not INSERT OR REPLACE) 强制 append-only：
                # event_id 是 UUID，碰撞概率≈0；若碰撞应报错而非覆盖
                conn.execute(
                    "INSERT INTO step_event "
                    "(event_id, step_id, conv_id, agent_id, parent_step_id, state, "
                    " event_type, input, output, metadata, seq, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (d["event_id"], d["step_id"], d["conv_id"], d["agent_id"],
                     d["parent_step_id"], d["state"], d["event_type"],
                     d["input"], d["output"], d.get("metadata", "{}"),
                     d["seq"], d["timestamp"]),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def append_events(self, events: List[StepEvent]) -> None:
        """单事务批量写入（高频 llm_token 节流，减少磁盘 sync 往返）。"""
        if not events:
            return

        def _do():
            conn = self._connect()
            try:
                rows = []
                for event in events:
                    d = event.to_storage_dict()
                    rows.append(
                        (
                            d["event_id"], d["step_id"], d["conv_id"],
                            d["agent_id"], d["parent_step_id"], d["state"],
                            d["event_type"], d["input"], d["output"],
                            d.get("metadata", "{}"), d["seq"], d["timestamp"],
                        )
                    )
                conn.executemany(
                    "INSERT INTO step_event "
                    "(event_id, step_id, conv_id, agent_id, parent_step_id, state, "
                    " event_type, input, output, metadata, seq, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def get_events(self, conv_id: str, since_seq: int = 0) -> List[StepEvent]:
        def _do():
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM step_event WHERE conv_id = ? AND seq >= ? "
                    "ORDER BY seq ASC",
                    (conv_id, since_seq),
                ).fetchall()
                return [StepEvent.from_storage_dict(dict(r)) for r in rows]
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def get_step_state(self, step_id: str) -> Optional[Tuple[StepState, dict]]:
        def _do():
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT state, snapshot FROM step_state WHERE step_id = ?",
                    (step_id,),
                ).fetchone()
                if not row:
                    return None
                return StepState(row["state"]), json.loads(row["snapshot"] or "{}")
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def set_step_state(
        self, step_id: str, conv_id: str, state: StepState, snapshot: dict
    ) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO step_state "
                    "(step_id, conv_id, state, snapshot, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (step_id, conv_id, state.value, json.dumps(snapshot), time.time()),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def acquire_lease(self, conv_id: str, agent_id: str, ttl_seconds: int) -> bool:
        def _do():
            conn = self._connect()
            try:
                now = time.time()
                expires = now + ttl_seconds
                # 若无 lease 或已过期，抢到
                row = conn.execute(
                    "SELECT agent_id, lease_expires_at FROM agent_lease WHERE conv_id = ?",
                    (conv_id,),
                ).fetchone()
                if row is None or row["lease_expires_at"] < now:
                    conn.execute(
                        "INSERT OR REPLACE INTO agent_lease "
                        "(conv_id, agent_id, lease_expires_at) VALUES (?, ?, ?)",
                        (conv_id, agent_id, expires),
                    )
                    conn.commit()
                    return True
                if row["agent_id"] == agent_id:
                    conn.execute(
                        "UPDATE agent_lease SET lease_expires_at = ? WHERE conv_id = ?",
                        (expires, conv_id),
                    )
                    conn.commit()
                    return True
                return False
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def renew_lease(self, conv_id: str, agent_id: str, ttl_seconds: int) -> bool:
        return await self.acquire_lease(conv_id, agent_id, ttl_seconds)

    async def release_lease(self, conv_id: str) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute("DELETE FROM agent_lease WHERE conv_id = ?", (conv_id,))
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def scan_expired_leases(self) -> List[str]:
        def _do():
            conn = self._connect()
            try:
                now = time.time()
                rows = conn.execute(
                    "SELECT conv_id FROM agent_lease WHERE lease_expires_at < ?",
                    (now,),
                ).fetchall()
                return [r["conv_id"] for r in rows]
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def save_interaction_checkpoint(
        self, request_id: str, step_id: str, conv_id: str, request_payload: dict
    ) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO interaction_checkpoint "
                    "(request_id, step_id, conv_id, request_payload, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (request_id, step_id, conv_id,
                     json.dumps(request_payload, ensure_ascii=False), time.time()),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def get_interaction_checkpoint(self, request_id: str) -> Optional[dict]:
        def _do():
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT request_id, step_id, conv_id, request_payload, created_at "
                    "FROM interaction_checkpoint WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if not row:
                    return None
                d = dict(row)
                d["request_payload"] = json.loads(d["request_payload"])
                return d
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def delete_interaction_checkpoint(self, request_id: str) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM interaction_checkpoint WHERE request_id = ?",
                    (request_id,),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def save_transcript(
        self, transcript_id: str, task_id: str, sub_conv_id: str,
        parent_step_id: str, parent_conv_id: str, agent_name: str,
        status: str, latest_event_seq: int, payload: dict,
    ) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO agent_transcript "
                    "(transcript_id, task_id, sub_conv_id, parent_step_id, parent_conv_id, "
                    "agent_name, status, latest_event_seq, payload, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (transcript_id, task_id, sub_conv_id, parent_step_id, parent_conv_id,
                     agent_name, status, latest_event_seq,
                     json.dumps(payload, ensure_ascii=False), time.time()),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def get_transcript(self, transcript_id: str) -> Optional[dict]:
        def _do():
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT transcript_id, task_id, sub_conv_id, parent_step_id, "
                    "parent_conv_id, agent_name, status, latest_event_seq, payload, updated_at "
                    "FROM agent_transcript WHERE transcript_id = ?",
                    (transcript_id,),
                ).fetchone()
                if not row:
                    return None
                d = dict(row)
                d["payload"] = json.loads(d["payload"])
                return d
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def get_transcript_by_task_id(self, task_id: str) -> Optional[dict]:
        def _do():
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT transcript_id, task_id, sub_conv_id, parent_step_id, "
                    "parent_conv_id, agent_name, status, latest_event_seq, payload, updated_at "
                    "FROM agent_transcript WHERE task_id = ? ORDER BY updated_at DESC LIMIT 1",
                    (task_id,),
                ).fetchone()
                if not row:
                    return None
                d = dict(row)
                d["payload"] = json.loads(d["payload"])
                return d
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def list_transcripts_for_parent(self, parent_conv_id: str) -> List[dict]:
        def _do():
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT transcript_id, task_id, sub_conv_id, parent_step_id, "
                    "parent_conv_id, agent_name, status, latest_event_seq, payload, updated_at "
                    "FROM agent_transcript WHERE parent_conv_id = ? "
                    "ORDER BY updated_at ASC",
                    (parent_conv_id,),
                ).fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    d["payload"] = json.loads(d["payload"])
                    result.append(d)
                return result
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        return await asyncio.to_thread(_do)

    async def delete_transcript(self, transcript_id: str) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM agent_transcript WHERE transcript_id = ?",
                    (transcript_id,),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)

    async def update_event_metadata(self, event_id: str, metadata: dict) -> None:
        def _do():
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE step_event SET metadata = ? WHERE event_id = ?",
                    (json.dumps(metadata), event_id),
                )
                conn.commit()
            finally:
                pass  # 连接由 store 线程局部复用（见 _connect/close）
        await asyncio.to_thread(_do)


def create_state_store(
    agent_id: Optional[str] = None,
    conv_id: Optional[str] = None,
    data_dir: Optional[str] = None,
    db_path: Optional[str] = None,
    db_manager: Optional[Any] = None,
) -> StateStore:
    """创建 V2 事件溯源 StateStore（跟随系统数据库动态切换）。

    选择优先级：
      1. ``db_path`` 显式指定 → 本地 SQLite 文件（测试/调试）；
      2. ``data_dir`` 显式指定 → 隔离目录下 SQLite 文件（测试/沙箱隔离）；
      3. 系统数据库已初始化（serve ``[service.web.database]`` 配 sqlite/MySQL/PG）→
         :class:`SqlAlchemyStateStore`，事件日志与业务数据同库、跨实例共享
         （分布式部署支持）；
      4. 兜底 → ``{DATA_DIR}/v2_state`` 按 Agent 单库的 SQLite 文件
         （单机持久化，跨进程重启可恢复）。

    替换早期 ``tempfile.gettempdir()/gyra-v2-{id(self)}.db`` 的 per-agent
    临时库（临时库随进程销毁，事件溯源失去意义）。
    """
    if db_path:
        return DbStateStore(db_path)
    if data_dir is not None:
        # 显式隔离目录：SQLite（测试/沙箱）
        os.makedirs(data_dir, exist_ok=True)
        stem = _safe_stem(conv_id or agent_id)
        return DbStateStore(os.path.join(data_dir, f"{stem}.db"))

    # 系统数据库优先：跟随 sqlite/MySQL/PostgreSQL 动态切换（分布式共享）
    mgr = db_manager
    if mgr is None:
        from gyra.agent.core.v2.unified_state_store import (
            _get_system_db_manager,
        )
        mgr = _get_system_db_manager()
    if mgr is not None and getattr(mgr, "is_initialized", False):
        from gyra.agent.core.v2.unified_state_store import SqlAlchemyStateStore
        return SqlAlchemyStateStore(mgr)

    # 兜底：单机持久 SQLite（DATA_DIR/v2_state）
    try:
        from gyra.configs.model_config import DATA_DIR
    except Exception:  # noqa: BLE001
        DATA_DIR = os.path.join(str(Path.home()), ".gyra")
    data_dir = os.path.join(DATA_DIR, "v2_state")
    os.makedirs(data_dir, exist_ok=True)
    stem = _safe_stem(conv_id or agent_id)
    return DbStateStore(os.path.join(data_dir, f"{stem}.db"))


def _safe_stem(name: Optional[str]) -> str:
    """把会话/Agent 标识转成安全的文件名 stem。"""
    return (name or "default").replace("/", "_").replace("\\", "_")
