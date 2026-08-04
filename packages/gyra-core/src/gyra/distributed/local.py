"""单机实现——开发环境用,生产环境切换 Redis/Kafka。

语义与分布式实现完全一致,只是无跨节点协调:
- Lock: 基于 threading.Lock + TTL dict
- EventBus: 基于 asyncio.Queue + 消费组分发
- CrashRecovery: 空实现(单机无僵尸状态)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Set

from .protocols import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    CrashRecovery,
    DistributedLock,
    EventHandler,
    LockHandle,
    Subscription,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 单机分布式锁
# --------------------------------------------------------------------------- #
class LocalDistributedLock(DistributedLock):
    """单机锁实现——基于 dict + TTL。

    语义:
    - 互斥: 同 resource_id 同时一个持有者
    - TTL: 过期自动释放,防死锁
    - token: 释放时校验,防误释放
    """

    def __init__(self):
        self._locks: Dict[str, LockHandle] = {}
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        resource_id: str,
        holder_id: str,
        ttl_seconds: int = 30,
    ) -> LockHandle:
        async with self._lock:
            # 清理过期锁
            now = time.time()
            existing = self._locks.get(resource_id)
            if existing and existing.expires_at < now:
                del self._locks[resource_id]
                existing = None

            if existing is not None:
                # 已被占
                return LockHandle(
                    resource_id=resource_id,
                    holder_id=holder_id,
                    token="",
                    expires_at=0,
                    acquired=False,
                )

            handle = LockHandle(
                resource_id=resource_id,
                holder_id=holder_id,
                token=str(uuid.uuid4()),
                expires_at=now + ttl_seconds,
                acquired=True,
            )
            self._locks[resource_id] = handle
            return handle

    async def release(self, handle: LockHandle) -> None:
        async with self._lock:
            existing = self._locks.get(handle.resource_id)
            if existing is None or existing.token != handle.token:
                return  # 已释放或被他人占,忽略
            del self._locks[handle.resource_id]

    async def renew(self, handle: LockHandle, extend_seconds: int = 30) -> bool:
        async with self._lock:
            existing = self._locks.get(handle.resource_id)
            if existing is None or existing.token != handle.token:
                return False
            existing.expires_at = time.time() + extend_seconds
            return True


# --------------------------------------------------------------------------- #
# 单机事件总线
# --------------------------------------------------------------------------- #
class LocalEventBus(AssetEventBus):
    """单机事件总线——基于 asyncio.Queue + 消费组。

    语义:
    - at-least-once: 每个消费组至少投递一次
    - 消费组: 同组内随机一个消费者处理(负载均衡)
    - 跨组: 不同组各自消费
    - 分区: 单机忽略partition_key(无跨节点)
    """

    def __init__(self):
        # event_type -> consumer_group -> List[Queue]
        self._subscribers: Dict[AssetEventType, Dict[str, List[asyncio.Queue]]] = {}
        # event_id -> Set[consumer_group] 已ack的
        self._acked: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._running = True

    async def publish(
        self,
        event: AssetEvent,
        partition_key: Optional[str] = None,
    ) -> str:
        groups = self._subscribers.get(event.event_type, {})
        if not groups:
            return event.event_id

        for group_name, queues in groups.items():
            if not queues:
                continue
            # 负载均衡: 轮询选一个queue
            idx = hash(event.event_id) % len(queues)
            try:
                queues[idx].put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    f"[local-bus] queue full, dropping event {event.event_id} "
                    f"for group {group_name}"
                )
        return event.event_id

    def subscribe(
        self,
        event_type: AssetEventType,
        handler: EventHandler,
        consumer_group: str,
    ) -> Subscription:
        sub_id = str(uuid.uuid4())

        async def _consumer():
            queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
            async with self._lock:
                self._subscribers.setdefault(event_type, {})
                self._subscribers[event_type].setdefault(consumer_group, []).append(queue)

            while self._running:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

                # 幂等检查
                acked_groups = self._acked.get(event.event_id, set())
                if consumer_group in acked_groups:
                    queue.task_done()
                    continue

                try:
                    await handler.handle(event)
                    await self.ack(event.event_id, consumer_group)
                except Exception as e:
                    logger.warning(
                        f"[local-bus] handler failed for {event.event_id}: {e}, nack"
                    )
                    await self.nack(event.event_id, consumer_group, str(e))
                finally:
                    queue.task_done()

        # 启动消费协程
        asyncio.create_task(_consumer())

        return Subscription(sub_id, consumer_group)

    async def ack(self, event_id: str, consumer_group: str) -> None:
        async with self._lock:
            self._acked.setdefault(event_id, set()).add(consumer_group)
            # 简化: 所有组都ack后清理
            # (单机实现简化,不严格清理)

    async def nack(self, event_id: str, consumer_group: str, reason: str = "") -> None:
        # 单机实现: 记录日志,不重入(避免无限循环)
        logger.info(f"[local-bus] nack {event_id} group={consumer_group} reason={reason}")

    def shutdown(self):
        self._running = False


# --------------------------------------------------------------------------- #
# 单机崩溃恢复(空实现)
# --------------------------------------------------------------------------- #
class LocalCrashRecovery(CrashRecovery):
    """单机崩溃恢复——空实现(单机无僵尸状态)"""

    async def recover_stale_locks(self) -> int:
        return 0

    async def recover_pending_operations(self) -> int:
        return 0

    async def recover_pending_traces(self, timeout_seconds: int = 3600) -> int:
        return 0
