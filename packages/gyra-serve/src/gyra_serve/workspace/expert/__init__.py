"""场景空间专家团队：成员名册 + 外挂资源明细。

模型分层（设计见 docs/superpowers/specs/2026-09-04-agent-team-space-refactor-design.md）：
- 专家身份 = GptsApp（全局，人设/icon/llm_config/resource_tool 标准装备）
- 空间成员 = WorkspaceExpertEntity（专家 × 空间，role_hint/default_contract_id）
- 空间外挂 = WorkspaceExpertEquipmentEntity（成员 × 资源，逐行明细）

运行时组装 = 标准装备（GptsApp.resource_tool）∪ 空间外挂行（物化注入）。
"""
from .expert_models import (
    EXPERT_EQUIPMENT_RESOURCE_TYPES,
    WORKSPACE_EXPERT_EQUIPMENT_TABLE_NAME,
    WORKSPACE_EXPERT_TABLE_NAME,
    WorkspaceExpertDao,
    WorkspaceExpertEntity,
    WorkspaceExpertEquipmentDao,
    WorkspaceExpertEquipmentEntity,
)
from .expert_service import WorkspaceExpertService

__all__ = [
    "EXPERT_EQUIPMENT_RESOURCE_TYPES",
    "WORKSPACE_EXPERT_TABLE_NAME",
    "WORKSPACE_EXPERT_EQUIPMENT_TABLE_NAME",
    "WorkspaceExpertEntity",
    "WorkspaceExpertEquipmentEntity",
    "WorkspaceExpertDao",
    "WorkspaceExpertEquipmentDao",
    "WorkspaceExpertService",
]
