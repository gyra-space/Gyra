from typing import Any, Dict, List, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field

from ..config import SERVE_APP_NAME_HUMP


class ArtifactRequest(BaseModel):
    id: Optional[int] = None
    task_id: int
    workspace_id: int
    # 大厅会话级交付(task_id=0)的归属会话 id,用于不同会话之间彻底隔离
    conv_id: Optional[str] = None
    type: str = Field(..., description="report/analysis/dataset")
    title: str
    content_ref: Optional[str] = None
    content_text: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_shared: bool = False
    created_by_agent: Optional[str] = None
    created_by_user: Optional[int] = None


class ArtifactResponse(BaseModel):
    id: int
    task_id: int
    workspace_id: int
    conv_id: Optional[str] = None
    type: str
    title: str
    content_ref: Optional[str] = None
    content_text: Optional[str] = None
    current_version: int = 1
    provenance: Dict[str, Any] = Field(default_factory=dict)
    is_shared: bool = False
    created_by_agent: Optional[str] = None
    created_by_user: Optional[int] = None
    gmt_created: str
    gmt_modified: str

    model_config = ConfigDict(from_attributes=True)


class ArtifactListFilter(BaseModel):
    workspace_id: int
    task_id: Optional[int] = None
    conv_id: Optional[str] = None
    type: Optional[str] = None
    limit: int = 100


class ArtifactVersionResponse(BaseModel):
    id: int
    artifact_id: int
    version: int
    content_ref: Optional[str] = None
    diff_summary: Optional[str] = None
    created_by: Optional[str] = None
    gmt_created: str

    model_config = ConfigDict(from_attributes=True)
