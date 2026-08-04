"""Evolvable 可演化——基于轨迹自我改进。

- PlaybookEvolutionEngine: Evolvable 实现,analyze 生成提议 / apply 应用提议
- TraceToEvolutionHandler: 监听 TRACE_FINALIZED,累积触发分析
- DBEvolutionProposalStore: EvolutionProposalStore 实现
- 检测器: RecurringExtraStepDetector / SkippedStepDetector /
  FailurePatternDetector / AutoPathCandidateDetector
"""
from .detectors import (
    AutoPathCandidateDetector,
    FailurePatternDetector,
    RecurringExtraStepDetector,
    SkippedStepDetector,
    default_detectors,
)
from .engine import (
    DBEvolutionProposalStore,
    DEFAULT_ANALYZE_TRIGGER,
    PlaybookEvolutionEngine,
    TraceToEvolutionHandler,
)

__all__ = [
    "PlaybookEvolutionEngine",
    "TraceToEvolutionHandler",
    "DBEvolutionProposalStore",
    "DEFAULT_ANALYZE_TRIGGER",
    "RecurringExtraStepDetector",
    "SkippedStepDetector",
    "FailurePatternDetector",
    "AutoPathCandidateDetector",
    "default_detectors",
]
