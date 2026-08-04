"""分布式原语协议定义。

所有协议显式声明一致性语义:
- 强一致(STRONG): 走主库事务,读己写
- 最终一致(EVENTUAL): 走事件+幂等,有短暂延迟

所有写操作必须携带 IdempotencyKey 去重。
所有跨节点并发操作走 DistributedLock。
所有协议间联动走 AssetEventBus,不直接调用。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Optional, Protocol, runtime_checkable


# --------------------------------------------------------------------------- #
# 一致性级别
# --------------------------------------------------------------------------- #
class ConsistencyLevel(str, Enum):
    """一致性级别——每个操作必须声明"""
    STRONG = "strong"          # 强一致(走主库事务)
    EVENTUAL = "eventual"      # 最终一致(走事件+幂等)
    READ_YOUR_WRITES = "ryw"   # 读己写(会话级一致)


class IdempotencyKey(str):
    """幂等键——所有写操作必须携带,基于此去重。

    生成规则:
    - 业务操作: f"{operation}-{entity_id}-{version}"
    - 事件消费: f"event-{event_id}"
    - 重试安全: 相同key的重复请求被忽略
    """
    pass


# --------------------------------------------------------------------------- #
# 分布式锁
# --------------------------------------------------------------------------- #
@dataclass
class LockHandle:
    """锁句柄——持有者用于安全释放和续约"""
    resource_id: str
    holder_id: str
    token: str              # 锁token(防误释放)
    expires_at: float       # 过期时间戳(秒)
    acquired: bool = True   # 是否成功获取


class LeaseRenewer(Protocol):
    """租约续约协议——长任务持有锁期间持续续约"""

    async def renew(self, handle: LockHandle, extend_seconds: int = 30) -> bool:
        """续约,返回是否成功。失败需放弃操作"""
        ...

    async def release(self, handle: LockHandle) -> None:
        """安全释放(校验token,防误释放他人的锁)"""
        ...


class DistributedLock(ABC):
    """分布式锁协议——跨节点互斥。

    使用模式:
        handle = await lock.acquire("asset:123", "worker-1", ttl_seconds=30)
        if handle.acquired:
            try:
                # 临界区操作
                ...
            finally:
                await lock.release(handle)
    """

    @abstractmethod
    async def acquire(
        self,
        resource_id: str,
        holder_id: str,
        ttl_seconds: int = 30,
    ) -> LockHandle:
        """获取锁。返回handle(检查.acquired判断是否成功)。

        TTL过期自动释放,防止崩溃死锁。
        holder_id用于崩溃恢复识别持有者。
        """
        ...

    @abstractmethod
    async def release(self, handle: LockHandle) -> None:
        """释放锁。校验token,防误释放"""
        ...

    @abstractmethod
    async def renew(self, handle: LockHandle, extend_seconds: int = 30) -> bool:
        """续约。长任务用"""
        ...


# --------------------------------------------------------------------------- #
# 事件总线
# --------------------------------------------------------------------------- #
class AssetEventType(str, Enum):
    """资产事件类型——所有协议的状态变更都通过事件广播"""

    # Maturable 事件
    MATURITY_PROMOTED = "maturity_promoted"
    MATURITY_DEMOTED = "maturity_demoted"

    # Indexable 事件
    ASSET_INDEXED = "asset_indexed"
    ASSET_DEINDEXED = "asset_deindexed"

    # Sedimentable 事件
    SEDIMENT_PROPOSED = "sediment_proposed"
    SEDIMENT_RECEIVED = "sediment_received"

    # Traceable 事件
    TRACE_RECORDED = "trace_recorded"
    TRACE_FINALIZED = "trace_finalized"

    # Evolvable 事件
    EVOLUTION_PROPOSED = "evolution_proposed"
    EVOLUTION_APPLIED = "evolution_applied"
    EVOLUTION_REJECTED = "evolution_rejected"

    # 评委事件
    ASSET_ATTESTED = "asset_attested"
    ASSET_COACHED = "asset_coached"
    ASSET_REVIEWED = "asset_reviewed"

    # 通用
    ASSET_CREATED = "asset_created"
    ASSET_UPDATED = "asset_updated"


@dataclass
class AssetEvent:
    """资产事件——统一事件结构"""
    event_type: AssetEventType
    asset_id: str               # 相关资产ID
    workspace_id: int           # 分区键(保证同workspace事件顺序)
    actor: str                  # user_id / agent_id / system
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    idempotency_key: Optional[str] = None  # 消费用幂等键


class Subscription:
    """订阅句柄"""

    def __init__(self, sub_id: str, consumer_group: str):
        self.sub_id = sub_id
        self.consumer_group = consumer_group
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def unsubscribe(self) -> None:
        self._active = False


class EventHandler(Protocol):
    """事件处理器协议——消费者实现此协议,必须幂等"""

    consumer_group: str  # 消费组(同组负载均衡,不同组各自消费)

    async def handle(self, event: AssetEvent) -> None:
        """处理事件。必须幂等(基于event.idempotency_key去重)"""
        ...


class AssetEventBus(ABC):
    """分布式事件总线协议——可靠投递。

    语义:
    - at-least-once: 事件至少投递一次,可能重复
    - 消费者幂等: 基于idempotency_key去重
    - 分区顺序: 同partition_key的事件按序投递
    - 消费组: 同组负载均衡,不同组各自消费
    """

    @abstractmethod
    async def publish(
        self,
        event: AssetEvent,
        partition_key: Optional[str] = None,  # 默认workspace_id
    ) -> str:
        """发布事件,返回event_id。at-least-once投递"""
        ...

    @abstractmethod
    def subscribe(
        self,
        event_type: AssetEventType,
        handler: EventHandler,
        consumer_group: str,
    ) -> Subscription:
        """订阅事件。同消费组内负载均衡"""
        ...

    @abstractmethod
    async def ack(self, event_id: str, consumer_group: str) -> None:
        """确认处理成功"""
        ...

    @abstractmethod
    async def nack(self, event_id: str, consumer_group: str, reason: str = "") -> None:
        """处理失败,重入队列"""
        ...


# --------------------------------------------------------------------------- #
# 崩溃恢复
# --------------------------------------------------------------------------- #
class CrashRecovery(ABC):
    """崩溃恢复协议——处理节点宕机后的僵尸状态"""

    @abstractmethod
    async def recover_stale_locks(self) -> int:
        """扫描过期锁,释放。返回清理数"""
        ...

    @abstractmethod
    async def recover_pending_operations(self) -> int:
        """恢复中断的操作(基于幂等键重试)。返回恢复数"""
        ...

    @abstractmethod
    async def recover_pending_traces(self, timeout_seconds: int = 3600) -> int:
        """恢复未finalize的轨迹(标记aborted)。返回恢复数"""
        ...
