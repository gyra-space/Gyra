"""Traceable 可追踪——执行轨迹采集与持久化。

- BufferedTraceCollector: 执行过程中缓冲 skill/gate/skip,finalize 落盘
- DBTraceSink: 轨迹 DB 写入端(TraceSink 实现)
- PlaybookTraceDao / PlaybookTraceEntity: 轨迹表 DAO
"""
from .collector import BufferedTraceCollector
from .models import (
    PLAYBOOK_EVOLUTION_PROPOSAL_TABLE_NAME,
    PLAYBOOK_TRACE_TABLE_NAME,
    PlaybookEvolutionProposalDao,
    PlaybookEvolutionProposalEntity,
    PlaybookTraceDao,
    PlaybookTraceEntity,
)
from .sink import DBTraceSink

__all__ = [
    "BufferedTraceCollector",
    "DBTraceSink",
    "PlaybookTraceDao",
    "PlaybookTraceEntity",
    "PlaybookEvolutionProposalDao",
    "PlaybookEvolutionProposalEntity",
    "PLAYBOOK_TRACE_TABLE_NAME",
    "PLAYBOOK_EVOLUTION_PROPOSAL_TABLE_NAME",
]
