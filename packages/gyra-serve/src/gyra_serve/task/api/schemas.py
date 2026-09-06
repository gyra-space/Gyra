from datetime import datetime
from typing import Any, Dict, List, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field

from ..config import SERVE_APP_NAME_HUMP


class TaskRequest(BaseModel):
    id: Optional[int] = None
    workspace_id: int
    parent_task_id: Optional[int] = None
    type: str = Field(
        "adhoc",
        description=(
            "routine/pipeline/incident/adhoc "
            "(routine:标准Playbook,auto多; "
            "pipeline:串行多阶段,每阶段有gate; "
            "incident:高优先级,跳过部分review,事后强制postmortem; "
            "adhoc:无Playbook,agent自由编排,产出强制review)"
        ),
    )
    title: str
    description: Optional[str] = None
    status: str = Field("draft", description="draft/pending_trigger/running/awaiting_human/blocked/delivered/closed/archived/failed")
    priority: Optional[str] = "normal"
    triggered_by: str = Field("manual", description="page/api/cron/webhook/alert/manual(page=页面输入命中剧本,会话内执行;api/cron/webhook/alert=后台异步)")
    trigger_ref: Optional[str] = None
    playbook_id: Optional[int] = None
    playbook_version_id: Optional[int] = None
    conv_session_id: Optional[str] = Field(None, description="conversation session id bound to this task")
    expert_app_code: Optional[str] = Field(None, description="执行专家（gpts_app.app_code），Agent Team 空间重构")
    contract_id: Optional[int] = Field(None, description="交付合约 id（playbook 表收窄语义）")
    created_by_user_id: Optional[int] = None
    assignee_user_id: Optional[int] = None
    assigned_agents: Optional[List[str]] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    due_at: Optional[datetime] = None

    model_config = ConfigDict(title=f"TaskRequest for {SERVE_APP_NAME_HUMP}")


class TaskResponse(BaseModel):
    id: int
    workspace_id: int
    parent_task_id: Optional[int] = None
    type: str
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    triggered_by: str
    trigger_ref: Optional[str] = None
    playbook_id: Optional[int] = None
    playbook_version_id: Optional[int] = None
    conv_session_id: Optional[str] = None
    expert_app_code: Optional[str] = None
    contract_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    assignee_user_id: Optional[int] = None
    assigned_agents: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    due_at: Optional[str] = None
    started_at: Optional[str] = None
    closed_at: Optional[str] = None
    gmt_created: str
    gmt_modified: str

    model_config = ConfigDict(from_attributes=True)


class TaskListFilter(BaseModel):
    workspace_id: int
    status: Optional[str] = None
    type: Optional[str] = None
    triggered_by: Optional[str] = Field(
        None, description="按触发来源过滤,逗号分隔多值,如 timer,webhook,alert"
    )
    trigger_ref: Optional[str] = Field(
        None, description="按关联订阅(trigger id)过滤,精确匹配"
    )
    user_id: Optional[int] = None
    assignee_user_id: Optional[int] = None
    mine: bool = Field(False, description="我发起的或指派给我的(created_by or assignee)")
    own_and_public_only: bool = Field(
        False,
        description=(
            "仅看自己提交的任务 + 空间公共任务(订阅/触发源产生的 timer/webhook/alert 等任务);"
            "别人的对话任务(page/manual 且非本人创建)不可见。简单页面模式使用。"
        ),
    )
    include_archived: bool = False
    limit: int = 100


class TaskRelationRequest(BaseModel):
    parent_task_id: int
    child_task_id: int
    relation_type: str = Field("spawned_by", description="spawned_by/escalated_to/blocked_by")


class TaskCloseRequest(BaseModel):
    task_id: int
    distill_completed: bool = Field(
        False, description="must be true — server enforces distill before close"
    )
