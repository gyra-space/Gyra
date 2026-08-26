"""AppCard API schemas."""
from typing import Any, Dict, List, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field


class AppCardCreateRequest(BaseModel):
    workspace_id: int
    name: str
    description: Optional[str] = None
    kind: str = Field(default="dashboard", description="dashboard / board / custom")
    code: str = Field(..., description="自包含 HTML/JS 子应用代码")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="manifest: tabs / params / default_params / runtime_logic",
    )
    queries: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="命名查询数据契约: [{key, kind: metric|sql, ...}]",
    )
    source_task_id: Optional[int] = None
    created_by: Optional[str] = None
    icon: Optional[str] = None
    permissions: Optional[List[str]] = Field(default_factory=list, description="可访问角色(如 member/owner/all)")
    dry_run: bool = Field(default=False, description="创建前是否 dry-run 校验所有查询")


class AppCardUpdateRequest(BaseModel):
    id: int
    workspace_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    code: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    queries: Optional[List[Dict[str, Any]]] = None
    icon: Optional[str] = None
    permissions: Optional[List[str]] = None
    created_by: Optional[str] = None
    dry_run: bool = False


class AppCardDeleteRequest(BaseModel):
    id: int
    workspace_id: int


class AppCardListFilter(BaseModel):
    workspace_id: int
    limit: int = 100


class AppCardResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: Optional[str] = None
    kind: str = "dashboard"
    status: str = "draft"
    code: str
    config: Dict[str, Any] = Field(default_factory=dict)
    queries: List[Dict[str, Any]] = Field(default_factory=list)
    current_version: int = 1
    source_task_id: Optional[int] = None
    created_by: Optional[str] = None
    icon: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    gmt_created: str
    gmt_modified: str

    model_config = ConfigDict(from_attributes=True)


class AppCardInvokeRequest(BaseModel):
    op: str = Field(..., description="query.metric / query.sql / assets.get / preview.*")
    params: Dict[str, Any] = Field(default_factory=dict)
    query_key: Optional[str] = Field(default=None, description="引用卡片里命名的查询")


class AppCardValidateResult(BaseModel):
    ok: bool
    item_key: str
    kind: str
    trust: str = "none"
    error: Optional[str] = None


class AppCardValidateResponse(BaseModel):
    ok: bool = False
    items: List[AppCardValidateResult] = Field(default_factory=list)
