"""分布式原语与飞轮协议层。

提供 Gyra 飞轮体系的基础设施协议 + 业务协议:
- 基础设施: DistributedLock / AssetEventBus / CrashRecovery
- 业务协议: Assetable / Maturable / Indexable / Sedimentable / Traceable / Evolvable

单机实现用于开发,生产环境可切换 Redis/Kafka 后端,协议不变。
"""

# 基础设施协议
from .protocols import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    ConsistencyLevel,
    CrashRecovery,
    DistributedLock,
    EventHandler,
    IdempotencyKey,
    LockHandle,
    LeaseRenewer,
    Subscription,
)
from .local import (
    LocalDistributedLock,
    LocalEventBus,
    LocalCrashRecovery,
)
from .bus_component import (
    SHARED_EVENT_BUS_COMPONENT_NAME,
    SharedEventBusComponent,
    get_shared_event_bus,
)

# 业务协议
from .asset_protocols import (
    # Assetable
    AssetCategory,
    AssetRecord,
    AssetReference,
    Assetable,
    AssetRepository,
    # Maturable
    MaturityLevel,
    MaturityTransition,
    PromotionCheck,
    PromotionRule,
    PromotionRuleRegistry,
    Maturable,
    # Indexable
    IndexDocument,
    SearchHit,
    Indexable,
    IndexSink,
    IndexPolicy,
    IndexReconciler,
    ReconcileReport,
    # Sedimentable
    SedimentProposal,
    Sedimentable,
    SedimentSource,
    SedimentSink,
    # Traceable
    TraceContext,
    SkillCallRecord,
    GateTriggerRecord,
    ExecutionTrace,
    TraceCollector,
    TraceSink,
    # Evolvable
    EvolutionProposal,
    EvolutionResult,
    EvolutionDetector,
    EvolutionDetectorRegistry,
    EvolutionProposalStore,
    Evolvable,
)

__all__ = [
    # 基础设施
    "AssetEvent",
    "AssetEventBus",
    "AssetEventType",
    "ConsistencyLevel",
    "CrashRecovery",
    "DistributedLock",
    "EventHandler",
    "IdempotencyKey",
    "LockHandle",
    "LeaseRenewer",
    "Subscription",
    "LocalDistributedLock",
    "LocalEventBus",
    "LocalCrashRecovery",
    "SHARED_EVENT_BUS_COMPONENT_NAME",
    "SharedEventBusComponent",
    "get_shared_event_bus",
    # Assetable
    "AssetCategory",
    "AssetRecord",
    "AssetReference",
    "Assetable",
    "AssetRepository",
    # Maturable
    "MaturityLevel",
    "MaturityTransition",
    "PromotionCheck",
    "PromotionRule",
    "PromotionRuleRegistry",
    "Maturable",
    # Indexable
    "IndexDocument",
    "SearchHit",
    "Indexable",
    "IndexSink",
    "IndexPolicy",
    "IndexReconciler",
    "ReconcileReport",
    # Sedimentable
    "SedimentProposal",
    "Sedimentable",
    "SedimentSource",
    "SedimentSink",
    # Traceable
    "TraceContext",
    "SkillCallRecord",
    "GateTriggerRecord",
    "ExecutionTrace",
    "TraceCollector",
    "TraceSink",
    # Evolvable
    "EvolutionProposal",
    "EvolutionResult",
    "EvolutionDetector",
    "EvolutionDetectorRegistry",
    "EvolutionProposalStore",
    "Evolvable",
]
