"""Agent 成长模型 (AgentMaturityModel) —— P1 任务 6。

采集三链信号(资产贡献/执行成功率/attest 数) → 多维评分 →
四阶段跃迁(novice→proficient→expert→master) → 权限变化 → 反哺飞轮。

模块组成:
- models:    AgentMaturityEntity / AgentMaturityDao (存储)
- service:   AgentMaturityService + AgentStage + STAGE_PERMISSIONS (评分/跃迁)
- handlers:  三链事件处理器 (ASSET_ATTESTED/COACHED/TRACE_FINALIZED/EVOLUTION_APPLIED)
- api:       REST 端点
"""
from .models import (
    AGENT_MATURITY_TABLE_NAME,
    AgentMaturityDao,
    AgentMaturityEntity,
)
from .service import (
    AGENT_MATURITY_SERVICE_COMPONENT_NAME,
    PROMOTION_THRESHOLDS,
    REQUIRED_AGENT_ATTESTS,
    STAGE_PERMISSIONS,
    AgentMaturityService,
    AgentStage,
    AgentPromotionConcurrentError,
    AgentPromotionInvalidError,
    AgentPromotionNotMetError,
)

__all__ = [
    "AGENT_MATURITY_SERVICE_COMPONENT_NAME",
    "AGENT_MATURITY_TABLE_NAME",
    "AgentMaturityDao",
    "AgentMaturityEntity",
    "AgentMaturityService",
    "AgentStage",
    "STAGE_PERMISSIONS",
    "PROMOTION_THRESHOLDS",
    "REQUIRED_AGENT_ATTESTS",
    "AgentPromotionConcurrentError",
    "AgentPromotionInvalidError",
    "AgentPromotionNotMetError",
]
