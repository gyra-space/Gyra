"""飞轮体系业务协议层。

六大协议覆盖飞轮全链路:
- Assetable: 可资产化(根协议)
- Maturable: 可成熟(五级阶梯)
- Indexable: 可索引(自动检索)
- Sedimentable: 可沉淀(个体→组织)
- Traceable: 可追踪(执行轨迹)
- Evolvable: 可演化(自我改进)

协议间联动全部走 AssetEventBus,不直接调用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# --------------------------------------------------------------------------- #
# 协议1: Assetable (可资产化) —— 根协议
# --------------------------------------------------------------------------- #
class AssetCategory(str, Enum):
    """资产大类——对应四类资产,扩展时加枚举"""
    FACT = "fact"              # 事实资产(ECP)
    EXPERIENCE = "experience"  # 经验资产(workspace_asset)
    CAPABILITY = "capability"  # 能力资产(Playbook)
    INDEX = "index"            # 检索资产


@dataclass
class AssetReference:
    """资产间引用关系(知识图谱边)"""
    from_asset_id: str
    to_asset_id: str
    ref_type: str          # uses/produces/derived_from/attests
    note: str = ""


@dataclass
class AssetRecord:
    """跨层引用记录——让不同资产层能互相引用,不强制统一存储"""
    asset_id: str
    category: AssetCategory
    type: str
    workspace_id: int
    ref_table: str         # 实际存储表名
    ref_id: str            # 实际存储ID
    summary: str           # 摘要(用于引用展示)
    version: int = 1
    references: List[AssetReference] = field(default_factory=list)


@runtime_checkable
class Assetable(Protocol):
    """可资产化协议——所有资产的根契约。

    任何可成为"组织资产"的主体都实现此协议。
    新增资产类型只需实现此协议,注册到 AssetRecord。
    """

    @property
    def asset_id(self) -> str:
        """全局唯一资产ID"""
        ...

    @property
    def asset_category(self) -> AssetCategory:
        """资产大类"""
        ...

    @property
    def asset_type(self) -> str:
        """资产具体类型(如 historical_artifact/case/entity/metric)"""
        ...

    @property
    def workspace_id(self) -> int:
        """所属场景空间(分区键)"""
        ...

    @property
    def source(self) -> str:
        """来源标识(task/memory/distill/discovery/manual)"""
        ...

    def to_asset_record(self) -> AssetRecord:
        """转换为统一资产记录(用于跨层引用)"""
        ...


class AssetRepository(Protocol):
    """资产仓储协议——分布式读写"""

    async def get(
        self,
        asset_id: str,
        consistency: "ConsistencyLevel" = None,
    ) -> Optional[Assetable]:
        """读取——强一致走主库,最终一致可读副本"""
        ...

    async def save(
        self,
        asset: Assetable,
        idempotency_key: str,
        expected_version: Optional[int] = None,
    ) -> Assetable:
        """保存——幂等+乐观锁。expected_version不匹配则冲突"""
        ...

    async def list_by_workspace(
        self,
        workspace_id: int,
        category: Optional[AssetCategory] = None,
        limit: int = 100,
    ) -> List[Assetable]:
        """列出workspace资产"""
        ...


# --------------------------------------------------------------------------- #
# 协议2: Maturable (可成熟) —— 五级阶梯
# --------------------------------------------------------------------------- #
class MaturityLevel(str, Enum):
    """成熟度阶梯——统一五级"""
    DRAFT = "draft"           # 刚产出,未沉淀
    PROPOSED = "proposed"     # 已沉淀,待确认
    CONFIRMED = "confirmed"   # 人确认,可复用
    PUBLISHED = "published"  # 已发布,可检索
    CANONICAL = "canonical"  # 标杆,可作教导素材

    def __ge__(self, other):
        levels = [MaturityLevel.DRAFT, MaturityLevel.PROPOSED,
                  MaturityLevel.CONFIRMED, MaturityLevel.PUBLISHED,
                  MaturityLevel.CANONICAL]
        return levels.index(self) >= levels.index(other)

    def __gt__(self, other):
        levels = [MaturityLevel.DRAFT, MaturityLevel.PROPOSED,
                  MaturityLevel.CONFIRMED, MaturityLevel.PUBLISHED,
                  MaturityLevel.CANONICAL]
        return levels.index(self) > levels.index(other)

    def __lt__(self, other):
        return not self.__ge__(other)


@dataclass
class MaturityTransition:
    """成熟度迁移记录"""
    from_level: MaturityLevel
    to_level: MaturityLevel
    timestamp: datetime
    actor: str              # user_id / system
    evidence: Dict[str, Any] = field(default_factory=dict)
    note: str = ""


@dataclass
class PromotionCheck:
    """晋升检查结果"""
    can_promote: bool
    gate: str = "auto"      # auto / human_review / human_attest
    missing: List[str] = field(default_factory=list)
    reason: str = ""


class PromotionRule(Protocol):
    """晋升规则协议——每种资产类型可注册不同规则"""

    @property
    def asset_type(self) -> str: ...

    @property
    def from_level(self) -> MaturityLevel: ...

    @property
    def to_level(self) -> MaturityLevel: ...

    def check(self, asset: "Maturable") -> PromotionCheck:
        """检查是否满足晋升条件"""
        ...


class PromotionRuleRegistry:
    """晋升规则注册表——扩展时注册新规则,不改核心"""

    _rules: Dict[tuple, PromotionRule] = {}

    @classmethod
    def register(cls, rule: PromotionRule) -> None:
        key = (rule.asset_type, rule.from_level, rule.to_level)
        cls._rules[key] = rule

    @classmethod
    def get(
        cls,
        asset_type: str,
        from_level: MaturityLevel,
        to_level: MaturityLevel,
    ) -> Optional[PromotionRule]:
        return cls._rules.get((asset_type, from_level, to_level))

    @classmethod
    def clear(cls) -> None:
        """测试用:清空注册表"""
        cls._rules.clear()


@runtime_checkable
class Maturable(Protocol):
    """可成熟协议——资产生命周期契约"""

    @property
    def maturity(self) -> MaturityLevel:
        """当前成熟度"""
        ...

    @property
    def maturity_history(self) -> List[MaturityTransition]:
        """成熟度迁移历史"""
        ...

    @property
    def attest_count(self) -> int:
        """attest累计数"""
        ...

    @property
    def reference_count(self) -> int:
        """被引用数"""
        ...

    def can_promote(self, to_level: MaturityLevel) -> PromotionCheck:
        """检查是否可晋升——返回门槛达标情况"""
        ...


# --------------------------------------------------------------------------- #
# 协议3: Indexable (可索引) —— 自动检索
# --------------------------------------------------------------------------- #
@dataclass
class IndexDocument:
    """索引文档——统一的检索层输入"""
    doc_id: str               # asset_id
    content: str              # 可检索内容
    metadata: Dict[str, Any]  # 检索过滤字段
    embedding: Optional[List[float]] = None  # 预计算向量(可选)


@dataclass
class SearchHit:
    """检索命中"""
    doc_id: str
    score: float
    content: str
    metadata: Dict[str, Any]


@runtime_checkable
class Indexable(Protocol):
    """可索引协议——资产可被检索层索引"""

    def to_index_document(self) -> IndexDocument:
        """转换为索引文档"""
        ...


class IndexSink(Protocol):
    """索引写入端协议——不同检索后端实现此协议"""

    async def upsert(self, doc: IndexDocument, idempotency_key: str) -> None:
        """幂等upsert"""
        ...

    async def remove(self, doc_id: str, idempotency_key: str) -> None: ...

    async def search(
        self, query: str, filters: Dict[str, Any], limit: int = 10
    ) -> List[SearchHit]: ...

    async def get(self, doc_id: str) -> Optional[IndexDocument]: ...

    async def list_by_workspace(self, workspace_id: int) -> List[str]:
        """列出workspace所有索引doc_id(对账用)"""
        ...


class IndexPolicy:
    """索引策略——声明式配置,哪些成熟度的哪些资产类型可索引"""

    _policies: Dict[str, MaturityLevel] = {}

    @classmethod
    def register(cls, asset_type: str, min_maturity: MaturityLevel) -> None:
        """注册:某类型资产达到某成熟度才索引"""
        cls._policies[asset_type] = min_maturity

    @classmethod
    def should_index(cls, asset: "Assetable & Maturable") -> bool:
        """判断资产是否应被索引"""
        min_level = cls._policies.get(asset.asset_type)
        if min_level is None:
            return False
        return asset.maturity >= min_level

    @classmethod
    def clear(cls) -> None:
        cls._policies.clear()


class IndexReconciler(Protocol):
    """索引对账协议——定期修复不一致"""

    async def reconcile(self, workspace_id: int) -> "ReconcileReport":
        """扫描workspace资产,对比索引,修复缺失/多余"""
        ...


@dataclass
class ReconcileReport:
    """对账报告"""
    workspace_id: int
    checked: int = 0
    added: int = 0
    removed: int = 0
    errors: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 协议4: Sedimentable (可沉淀) —— 个体→组织
# --------------------------------------------------------------------------- #
@dataclass
class SedimentProposal:
    """沉淀提案——个体经验→组织资产的转换契约"""
    source_agent_id: str
    source_memory_id: str      # L2记忆ID
    target_workspace_id: int
    asset_type: str            # 沉淀为哪种资产(case/pattern)
    title: str
    content: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5


@runtime_checkable
class Sedimentable(Protocol):
    """可沉淀协议——个体记忆可沉淀为组织资产"""

    def to_sediment_proposal(self) -> SedimentProposal:
        """生成沉淀提案"""
        ...


class SedimentSource(Protocol):
    """沉淀源协议——不同来源实现此协议"""

    async def collect_candidates(
        self,
        workspace_id: int,
        agent_id: Optional[str] = None,
    ) -> List[SedimentProposal]:
        """采集可沉淀的候选"""
        ...


class SedimentSink(Protocol):
    """沉淀端协议——资产层实现此协议"""

    async def receive(
        self,
        proposal: SedimentProposal,
        idempotency_key: str,
    ) -> str:
        """接收沉淀,返回创建的asset_id(maturity=draft)。幂等"""
        ...


# --------------------------------------------------------------------------- #
# 协议5: Traceable (可追踪) —— 执行轨迹
# --------------------------------------------------------------------------- #
@dataclass
class TraceContext:
    """轨迹上下文"""
    playbook_id: int
    playbook_version_id: int
    task_id: int
    workspace_id: int
    agent_id: str


@dataclass
class SkillCallRecord:
    """skill调用记录"""
    skill_name: str
    call_order: int
    success: bool
    duration_ms: int
    result_summary: str = ""


@dataclass
class GateTriggerRecord:
    """gate触发记录"""
    gate_name: str
    intervention_type: str
    resolved_by: str           # user_id / auto
    resolution: str            # approved/rejected/coached
    duration_ms: int = 0


@dataclass
class ExecutionTrace:
    """完整执行轨迹——演化引擎的输入"""
    trace_id: str
    context: TraceContext
    skill_calls: List[SkillCallRecord] = field(default_factory=list)
    gates: List[GateTriggerRecord] = field(default_factory=list)
    skips: List[tuple] = field(default_factory=list)  # (step_name, reason)
    status: str = "running"   # running/success/failed/partial/aborted
    failure_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    finalized_at: Optional[datetime] = None


class TraceCollector(Protocol):
    """轨迹采集器——执行过程中调用,缓冲批量发送"""

    async def record_skill(self, record: SkillCallRecord) -> None: ...
    async def record_gate(self, record: GateTriggerRecord) -> None: ...
    async def record_skip(self, step_name: str, reason: str) -> None: ...
    async def finalize(self, status: str, failure_reason: str = "") -> str: ...


class TraceSink(Protocol):
    """轨迹存储端——跨节点汇聚"""

    async def write(
        self,
        trace: ExecutionTrace,
        idempotency_key: str,
        final: bool = False,
    ) -> None:
        """写入轨迹——幂等,支持增量write(非final)"""
        ...

    async def list_recent(
        self, playbook_id: int, limit: int = 20
    ) -> List[ExecutionTrace]: ...

    async def list_by_workspace(
        self, workspace_id: int, limit: int = 100
    ) -> List[ExecutionTrace]: ...


# --------------------------------------------------------------------------- #
# 协议6: Evolvable (可演化) —— 自我改进
# --------------------------------------------------------------------------- #
@dataclass
class EvolutionProposal:
    """演化提议——能力资产改进的契约"""
    proposal_id: str = ""
    target_id: str = ""      # 被演化的资产ID(如Playbook ID)
    target_type: str = "playbook"
    proposal_type: str = ""  # add_skill/remove_step/modify_gate/...
    rationale: str = ""      # 统计依据
    evidence: List[str] = field(default_factory=list)  # trace_id列表
    proposed_change: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    status: str = "proposed"  # proposed/approved/rejected/applied
    proposed_at: datetime = field(default_factory=datetime.now)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    applied_version: Optional[int] = None


@dataclass
class EvolutionResult:
    """演化应用结果"""
    proposal_id: str
    new_version_id: Optional[int] = None
    success: bool = False
    error: str = ""


class EvolutionDetector(Protocol):
    """演化模式检测器协议——每种检测策略实现此协议"""

    @property
    def name(self) -> str: ...

    def detect(self, traces: List[ExecutionTrace]) -> List[EvolutionProposal]:
        """检测模式,返回提议"""
        ...


class EvolutionDetectorRegistry:
    """检测器注册表——扩展时注册新检测器"""

    _detectors: List[EvolutionDetector] = []

    @classmethod
    def register(cls, detector: EvolutionDetector) -> None:
        cls._detectors.append(detector)

    @classmethod
    def run_all(cls, traces: List[ExecutionTrace]) -> List[EvolutionProposal]:
        proposals = []
        for d in cls._detectors:
            try:
                proposals.extend(d.detect(traces))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"detector {d.name} failed: {e}"
                )
        return proposals

    @classmethod
    def clear(cls) -> None:
        cls._detectors.clear()


class EvolutionProposalStore(Protocol):
    """演化提议存储协议"""

    async def save(self, proposal: EvolutionProposal) -> str:
        """保存提议,返回proposal_id"""
        ...

    async def get(self, proposal_id: str) -> Optional[EvolutionProposal]: ...

    async def list_pending(self, workspace_id: int) -> List[EvolutionProposal]: ...

    async def list_by_target(
        self, target_id: str, status: Optional[str] = None
    ) -> List[EvolutionProposal]: ...

    async def update_status(
        self,
        proposal_id: str,
        status: str,
        reviewer: Optional[str] = None,
        applied_version: Optional[int] = None,
    ) -> None: ...


@runtime_checkable
class Evolvable(Protocol):
    """可演化协议——基于轨迹自我改进"""

    async def analyze(
        self,
        traces: List[ExecutionTrace],
    ) -> List[EvolutionProposal]:
        """分析轨迹,生成演化提议"""
        ...

    async def apply(
        self,
        proposal: EvolutionProposal,
        reviewer: str,
        idempotency_key: str,
    ) -> EvolutionResult:
        """应用演化提议(人审批后)"""
        ...
