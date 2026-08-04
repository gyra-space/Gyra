"""Intervention API schemas."""
from typing import Any, Dict, List, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field

from ..config import SERVE_APP_NAME_HUMP


class InterventionRequest(BaseModel):
    id: Optional[int] = None
    task_id: Optional[int] = None
    conv_uid: Optional[str] = None
    parent_conv_id: Optional[str] = None
    workspace_id: int
    type: str = Field(default="review", description="MVP only: review")
    requested_by: str = Field(default="system", description="system / agent / user")
    assignee_user_id: Optional[int] = None
    question: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


class InterventionResponse(BaseModel):
    id: int
    task_id: Optional[int] = None
    conv_uid: Optional[str] = None
    parent_conv_id: Optional[str] = None
    workspace_id: int
    type: str
    status: str = "requested"
    requested_by: str
    assignee_user_id: Optional[int] = None
    requested_at: str
    question: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    resolved_by_user_id: Optional[int] = None
    resolved_at: Optional[str] = None
    decision: Optional[Dict[str, Any]] = None
    distillation: Optional[Dict[str, Any]] = None
    linked_asset_id: Optional[int] = None
    gmt_created: str
    gmt_modified: str

    model_config = ConfigDict(from_attributes=True)


class InterventionResolveRequest(BaseModel):
    decision: Optional[Dict[str, Any]] = None
    distillation: Optional[Dict[str, Any]] = None
    linked_asset_id: Optional[int] = None
    resolved_by_user_id: Optional[int] = None


class InterventionListFilter(BaseModel):
    workspace_id: int
    task_id: Optional[int] = None
    status: Optional[str] = None
    limit: int = 100


# --------------------------------------------------------------------------- #
# 扩展介入模式(P1任务7): coach / escalate / reconcile / attest
# --------------------------------------------------------------------------- #
class CoachInterventionRequest(BaseModel):
    """coach纠偏请求——非阻塞,记录后即resolved。

    与成熟度服务联动:有asset_id时调用AssetMaturityService.coach()降级。
    """
    workspace_id: int
    agent_id: Optional[str] = None
    asset_id: Optional[int] = None
    task_id: Optional[int] = None
    coach_note: str = Field(..., description="纠偏说明")
    severity: str = Field(
        default="minor",
        description="严重程度: minor(仅记录) / major(降一级) / critical(降到draft)",
    )
    user_id: int = Field(..., description="执行coach的评委user_id")


class EscalateInterventionRequest(BaseModel):
    """escalate升级请求——可能阻塞(等待转交确认)。"""
    workspace_id: int
    task_id: int
    from_agent_id: str = Field(..., description="发起升级的agent")
    to_agent_id: Optional[str] = Field(
        default=None, description="升级目标agent;为空则升级给人"
    )
    reason: str = Field(..., description="升级原因")
    urgency: str = Field(
        default="medium", description="紧急程度: low / medium / high"
    )
    user_id: int = Field(..., description="触发升级的user_id")


class ReconcileInterventionRequest(BaseModel):
    """reconcile对账请求——可能阻塞(等待对账完成)。"""
    workspace_id: int
    task_id: Optional[int] = None
    data_sources: List[str] = Field(
        default_factory=list, description="需要对账的数据源列表"
    )
    reconciliation_type: str = Field(
        default="consistency",
        description="对账类型: consistency(一致性) / accuracy(准确性) / completeness(完整性)",
    )


class AttestInterventionRequest(BaseModel):
    """attest背书请求——非阻塞,记录后即resolved。

    与成熟度服务联动:asset→AssetMaturityService.attest();agent→AgentMaturityService.attest_agent()。
    """
    workspace_id: int
    target_type: str = Field(..., description="背书目标: asset / agent")
    target_id: int = Field(..., description="目标ID(asset_id或agent标识)")
    user_id: int = Field(..., description="执行attest的评委user_id")
    note: Optional[str] = None
