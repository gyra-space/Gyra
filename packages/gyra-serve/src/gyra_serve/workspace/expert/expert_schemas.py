"""专家团队 API schemas（Agent Team 空间重构 Phase 1.4）。"""
from typing import Any, Dict, List, Optional

from gyra._private.pydantic import BaseModel, Field


class ExpertEquipmentItem(BaseModel):
    resource_type: str = Field(..., description="data_source/knowledge_space/mcp/skill")
    resource_ref: str = Field(..., description="空间资源 name/physical_ref")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExpertUpsertRequest(BaseModel):
    """空间内创建/更新专家（编排写入 GptsApp + 成员行 + 外挂行）。"""
    app_code: Optional[str] = Field(None, description="更新时必传；创建时缺省自动生成 expert_{slug}")
    app_name: str
    app_describe: Optional[str] = ""
    icon: Optional[str] = None
    workspace_icon: Optional[str] = Field(
        None, description="空间级头像覆盖（写成员行，不动全局身份；''=清除覆盖回落全局）"
    )
    role_hint: Optional[str] = Field(None, description="空间内职责说明（prompt 补丁）")
    system_prompt_template: Optional[str] = Field(None, description="人设（身份层，全局）")
    default_contract_id: Optional[int] = None
    equipment: List[ExpertEquipmentItem] = Field(default_factory=list, description="空间外挂（全量替换式提交）")
    published: bool = True


class ExpertBindRequest(BaseModel):
    """把已存在的全局专家绑定进空间（仅写成员行 + 外挂行）。"""
    app_code: str
    role_hint: Optional[str] = None
    icon: Optional[str] = Field(
        None, description="空间级头像覆盖（写成员行，不动全局身份；''=清除覆盖回落全局）"
    )
    default_contract_id: Optional[int] = None
    equipment: List[ExpertEquipmentItem] = Field(default_factory=list)


class ExpertResponse(BaseModel):
    id: int
    workspace_id: int
    app_code: str
    app_name: Optional[str] = None
    icon: Optional[str] = None
    workspace_icon: Optional[str] = None
    app_describe: Optional[str] = None
    role_hint: Optional[str] = None
    default_contract_id: Optional[int] = None
    owner_workspace_id: Optional[int] = None
    is_active: bool = True
    equipment: List[ExpertEquipmentItem] = Field(default_factory=list)
    gmt_created: str = ""
    gmt_modified: str = ""


class TeamViewResponse(BaseModel):
    workspace_id: int
    leader_app_code: Optional[str] = None
    experts: List[ExpertResponse] = Field(default_factory=list)


class ExpertChatRequest(BaseModel):
    """专家直接对话（workspace 级会话，非任务）。"""
    app_code: str
    user_id: Optional[int] = None
    title: Optional[str] = None


class ExpertChatResponse(BaseModel):
    conv_uid: str
    app_code: str
    title: Optional[str] = None
