"""ECP API schemas (request/response view objects)."""

from typing import Any, Dict, List, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field


class SemanticObjectVO(BaseModel):
    """One version of a semantic object."""

    model_config = ConfigDict(title="EcpSemanticObject")

    id: str
    version: int
    workspace_id: str = "default"
    obj_type: str
    status: str
    name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    evidence: Optional[List[Dict[str, Any]]] = None
    created_by: str = "llm"
    created_at: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    source: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "结构化溯源(config.make_provenance):origin(来源枚举)/actor/"
            "origin_sql(MISS 学习或手工 SQL 的原始 SQL 快照)/miss_ref(聚类回链)/"
            "derived_from(派生链)。老数据为空,视图层降级用 source"
        ),
    )
    supersedes: Optional[int] = None
    bucket: Optional[str] = Field(
        default=None,
        description=(
            "确认收件箱业务分桶(读时派生,不落库):"
            "new=全新候选(该 id 尚无 confirmed 版本) / "
            "revision=已确认概念的待确认修订(supersedes 指向已确认版本) / "
            "confirmed=已确认对象本身。前端据此分离『待确认新对象』与"
            "『待确认修订』，不再把已确认概念当未确认展示"
        ),
    )
    view: Optional["ProposalViewVO"] = Field(
        default=None,
        description=(
            "业务视图(service/proposal_view.py 读时派生,不落库):"
            "summary 一句话口径 / origin 来源 / lineage 库表字段血缘 / "
            "sql_preview 静态 SQL 组装效果 / evidence 契约化引文"
        ),
    )


class OriginVO(BaseModel):
    """提案来源(业务视角);kind 取 config.ORIGIN_* 枚举。"""

    model_config = ConfigDict(title="EcpOrigin")

    kind: str
    label: str = Field(description="中文标签(初始扫描/MISS 学习/手工 SQL 等)")
    actor: Optional[str] = None
    origin_sql: List[str] = Field(
        default_factory=list, description="原始 SQL 快照(MISS 学习/手工 SQL)"
    )
    miss_ref: Optional[Dict[str, Any]] = Field(
        default=None, description="miss 聚类回链 {kind, pattern, datasource_id}"
    )
    note: Optional[str] = None
    derived_from: Optional[str] = None
    legacy_source: Optional[str] = Field(
        default=None, description="老数据降级:原始 source 字符串"
    )


class ColumnRefVO(BaseModel):
    """字段级血缘:一列在提案中的用途与业务含义。"""

    model_config = ConfigDict(title="EcpColumnRef")

    column: str
    meaning: Optional[str] = None
    role: Optional[str] = None
    usage: str = Field(
        default="", description="度量表达式|筛选条件|分组粒度|维度列|主键|时间列"
    )
    declared: bool = Field(
        default=True, description="是否在 entity.fields 中声明(False=口径疑点)"
    )


class ObjectRefVO(BaseModel):
    """提案引用/参与组装的另一个语义对象(带状态,供前端 ✅/🟡 标识)。"""

    model_config = ConfigDict(title="EcpObjectRef")

    id: str
    obj_type: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    version: Optional[int] = None


class LineageVO(BaseModel):
    """数据血缘:提案从哪个库、哪张表、哪些字段组织起来。"""

    model_config = ConfigDict(title="EcpLineage")

    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    tables: List[str] = Field(default_factory=list)
    columns: List[ColumnRefVO] = Field(default_factory=list)
    objects: List[ObjectRefVO] = Field(
        default_factory=list, description="引用链上的语义对象(metric→entity→dimension)"
    )
    document: Optional[Dict[str, Any]] = Field(
        default=None, description="文档类定位 {space, doc_id, anchor}"
    )


class SqlPreviewVO(BaseModel):
    """静态 SQL 组装效果(不执行;试跑真数据走 /debug 端点)。"""

    model_config = ConfigDict(title="EcpSqlPreview")

    sql: Optional[str] = None
    scenario: str = Field(default="", description="预览口径说明(时间窗/筛选假设)")
    participants: List[ObjectRefVO] = Field(
        default_factory=list, description="参与组装的对象(含版本/状态)"
    )
    warnings: List[str] = Field(default_factory=list)


class EvidenceItemVO(BaseModel):
    """契约化证据引文(后端收窄,不再自由 dict)。"""

    model_config = ConfigDict(title="EcpEvidenceItem")

    source: Optional[str] = None
    quote: Optional[str] = None


class ProposalViewVO(BaseModel):
    """提案业务视图:业务人不看 payload JSON 也能回答
    「从哪来 / 生成什么 SQL / 怎么被提出来的」。"""

    model_config = ConfigDict(title="EcpProposalView")

    summary: str = ""
    origin: OriginVO
    lineage: Optional[LineageVO] = None
    sql_preview: Optional[SqlPreviewVO] = None
    evidence: List[EvidenceItemVO] = Field(default_factory=list)


# SemanticObjectVO.view 是前向引用,在此解析
SemanticObjectVO.model_rebuild()


class SemanticObjectListVO(BaseModel):
    """Paginated semantic object list."""

    model_config = ConfigDict(title="EcpSemanticObjectList")

    items: List[SemanticObjectVO] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 20


class ProposeRequest(BaseModel):
    """Create a semantic object proposal (LLM or user)."""

    model_config = ConfigDict(title="EcpProposeRequest")

    id: str = Field(..., description="Object id, e.g. 'ent.order' / 'mtr.net_sales'")
    obj_type: str = Field(..., description="entity | metric | relation | dimension")
    payload: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[List[Dict[str, Any]]] = None
    created_by: str = "llm"
    source: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = Field(
        default=None, description="结构化溯源(config.make_provenance 构造)"
    )


class SqlAddRequest(BaseModel):
    """给 SQL 直接添加语义(添加即确认)。

    用户只提供一条 SQL(可附一句业务说明),后端用已配置的提案 Agent 提炼出
    entity/metric/dimension 等语义对象,并**直接落库为 confirmed**——手动添加
    即确认,不经过待确认收件箱。
    """

    model_config = ConfigDict(title="EcpSqlAdd")

    sql: str = Field(..., description="用户手写的 SQL,助手据此提炼语义资产")
    description: Optional[str] = Field(
        default=None, description="可选业务说明(提升提炼质量)"
    )
    workspace_id: Optional[str] = None
    user_id: str = Field(
        default="user", description="发起添加的用户;添加即确认,其作为确认人"
    )
    confirm: bool = Field(
        default=True, description="True=直接生效为已确认;False=仅进待确认收件箱"
    )


class SqlAddVO(BaseModel):
    """给 SQL 添加语义的结果。"""

    model_config = ConfigDict(title="EcpSqlAddResult")

    workspace_id: str
    added: int = 0
    confirmed_ids: List[str] = Field(default_factory=list)
    duplicate_existing: List[str] = Field(
        default_factory=list, description="已存在同名确认口径,未重复添加"
    )
    errors: List[str] = Field(default_factory=list)


class ConfirmRequest(BaseModel):
    """Confirm a proposed object version."""

    model_config = ConfigDict(title="EcpConfirmRequest")

    user_id: str
    workspace_id: Optional[str] = None
    # When set, confirm with edited payload: creates a new version created by
    # the user and confirms it ("edit then confirm").
    edited_payload: Optional[Dict[str, Any]] = None


class RejectRequest(BaseModel):
    """Reject a proposed object version."""

    model_config = ConfigDict(title="EcpRejectRequest")

    user_id: str
    workspace_id: Optional[str] = None
    reason: Optional[str] = None


class DeprecateRequest(BaseModel):
    """Deprecate a confirmed object."""

    model_config = ConfigDict(title="EcpDeprecateRequest")

    user_id: str
    workspace_id: Optional[str] = None
    reason: Optional[str] = None


class CatalogEntryVO(BaseModel):
    """One-line catalog entry for prompt injection / search results."""

    model_config = ConfigDict(title="EcpCatalogEntry")

    id: str
    obj_type: str
    name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    one_line: Optional[str] = None
    grain: Optional[List[str]] = None


class ConfirmerVO(BaseModel):
    """A confirmer entry."""

    model_config = ConfigDict(title="EcpConfirmer")

    id: int
    workspace_id: str
    user_id: str
    scope: Optional[str] = None
    user_name: Optional[str] = None


class ConfirmerCreateRequest(BaseModel):
    """Add a confirmer."""

    model_config = ConfigDict(title="EcpConfirmerCreate")

    workspace_id: Optional[str] = None
    user_id: str
    scope: Optional[str] = None


class OpLogVO(BaseModel):
    """One op-log entry."""

    model_config = ConfigDict(title="EcpOpLog")

    id: int
    workspace_id: str
    ts: Optional[str] = None
    op: str
    detail: Optional[Dict[str, Any]] = None


class MissLearnVO(BaseModel):
    """A miss cluster that has been learned (a proposal was generated for it).

    Persisted so the daily miss-learning cron stops re-surfacing the same high-
    frequency cluster once a proposal has been created for it — the flywheel's
    "learned" marker. ``pattern`` is the normalized cluster key produced by
    ``cluster_fallbacks`` (normalized SQL or question).
    """

    model_config = ConfigDict(title="EcpMissLearn")

    id: int
    workspace_id: str
    kind: str
    datasource_id: Optional[int] = None
    pattern: str
    example: Optional[str] = None
    proposal_ids: List[str] = Field(default_factory=list)
    trigger: str = "agent"
    learned_at: Optional[str] = None


class SemanticAlignmentVO(BaseModel):
    """知识层实体 ↔ 硬层语义对象的语义对齐记录(LLM 推理产出 + 人工决定)。

    对齐关系不是名字硬匹配:EntityAligner 让 LLM 在知识实体名与语义对象
    (name/description/aliases)之间做语义推理,候选以数据形式固化在本表;
    全景图的 aligns_to 边从本表投影——图渲染零 LLM 依赖。
    """

    model_config = ConfigDict(title="EcpSemanticAlignment")

    id: int
    workspace_id: str
    slug: str
    entity_name: str
    object_id: str
    status: str = "proposed"
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    source: str = "llm"
    decided_by: Optional[str] = None
    gmt_modify: Optional[str] = None


class AlignmentManualRequest(BaseModel):
    """手工添加一条实体↔对象语义对齐(LLM 不可用时的兜底,直通 confirmed)。"""

    model_config = ConfigDict(title="EcpAlignmentManualRequest")

    entity_name: str
    object_id: str
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None


class AlignmentDecideRequest(BaseModel):
    """Confirm/reject an alignment candidate."""

    model_config = ConfigDict(title="EcpAlignmentDecideRequest")

    user_id: Optional[str] = None
    workspace_id: Optional[str] = None


class MissRecordVO(BaseModel):
    """一条原始兜底(fallback)记录——聚类详情里的明细行。"""

    model_config = ConfigDict(title="EcpMissRecord")

    ts: Optional[str] = None
    sql: Optional[str] = None
    question: Optional[str] = None
    reasoning: Optional[str] = None
    datasource_id: Optional[int] = None
    spaces: Optional[List[str]] = None


class MissLearnEventVO(BaseModel):
    """学习标记生命周期事件(标记/清除),来自 op_log。"""

    model_config = ConfigDict(title="EcpMissLearnEvent")

    ts: Optional[str] = None
    op: str
    trigger: Optional[str] = None
    proposals: List[str] = Field(default_factory=list)


class MissClusterSummaryVO(BaseModel):
    """miss 聚类摘要(miss_report.clusters 同构,补充首末时间)。"""

    model_config = ConfigDict(title="EcpMissClusterSummary")

    kind: str
    datasource_id: Optional[int] = None
    pattern: str
    count: int
    example_sql: Optional[str] = None
    reasonings: List[str] = Field(default_factory=list)
    spaces: Optional[List[str]] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


class MissDetailVO(BaseModel):
    """单个 miss 聚类的学习档案:摘要+原始记录+已学习标记+生命周期事件。"""

    model_config = ConfigDict(title="EcpMissDetail")

    workspace_id: str
    cluster: MissClusterSummaryVO
    records: List[MissRecordVO] = Field(default_factory=list)
    learned: Optional[MissLearnVO] = None
    learn_events: List[MissLearnEventVO] = Field(default_factory=list)


class GenerateProposalsRequest(BaseModel):
    """Trigger proposal generation for a datasource (batch) or workspace (agent)."""

    model_config = ConfigDict(title="EcpGenerateProposals")

    datasource_id: Optional[int] = Field(
        default=None,
        description="Datasource to propose for (batch path). Omit for workspace-level "
        "agent run over all registered assets (when proposal_agent_id is configured).",
    )
    workspace_id: Optional[str] = None
    table_names: Optional[List[str]] = Field(
        default=None, description="Restrict to these tables; None means all learned"
    )
    max_tables: int = Field(default=50, ge=1, le=500)
    domain_hint: Optional[str] = Field(
        default=None,
        description="Workspace-level domain context injected into the proposal "
        "prompt (e.g. industry, authoritative caliber documents)",
    )


class GenerateProposalsVO(BaseModel):
    """Result of a proposal generation run."""

    model_config = ConfigDict(title="EcpGenerateProposalsResult")

    datasource_id: int
    tables_processed: int = 0
    proposals_created: int = 0
    proposal_ids: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class GenerateProposalsTaskVO(BaseModel):
    """Async proposal generation task handle.

    生成提案改为真异步:接口立即返回 task_id,前端轮询
    GET /proposals/tasks/{task_id} 获取进度与最终结果。
    """

    model_config = ConfigDict(title="EcpGenerateProposalsTask")

    task_id: str


class AssetRefVO(BaseModel):
    """A registered original-asset reference."""

    model_config = ConfigDict(title="EcpAssetRef")

    id: int
    workspace_id: str
    kind: str
    ref_id: str
    ref_meta: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    last_checked_at: Optional[str] = None


class AssetRefRegisterRequest(BaseModel):
    """Register an original-asset reference."""

    model_config = ConfigDict(title="EcpAssetRefRegister")

    kind: str = Field(..., description="db | document | space | api")
    ref_id: str = Field(
        ...,
        description="datasource_id | space_slug | space_slug:verbat_id | api_resource_id",
    )
    workspace_id: Optional[str] = None
    ref_meta: Optional[Dict[str, Any]] = None


class ReadinessCheckVO(BaseModel):
    """One readiness check item."""

    model_config = ConfigDict(title="EcpReadinessCheck")

    item: str
    ready: bool
    detail: Optional[str] = None


class ReadinessVO(BaseModel):
    """Readiness of an asset for proposal generation."""

    model_config = ConfigDict(title="EcpReadiness")

    kind: str
    ref_id: str
    ready: bool
    checks: List[ReadinessCheckVO] = Field(default_factory=list)


class GraphNodeVO(BaseModel):
    """A node in the semantic graph view.

    node_kind: object = hard-layer semantic object (default);
               asset  = registered original-asset reference (db/document/space/api);
               kn     = knowledge-layer node (wiki doc / cross-doc entity,
                        aggregated from the knowledge space L2 graph).
    """

    model_config = ConfigDict(title="EcpGraphNode")

    id: str
    obj_type: str
    name: Optional[str] = None
    status: str
    version: int = 0
    node_kind: str = "object"


class GraphLinkVO(BaseModel):
    """A link in the semantic graph view."""

    model_config = ConfigDict(title="EcpGraphLink")

    source: str
    target: str
    edge_type: str
    status: Optional[str] = None


class GraphVO(BaseModel):
    """Semantic graph: objects as nodes, materialized edges as links."""

    model_config = ConfigDict(title="EcpGraph")

    nodes: List[GraphNodeVO] = Field(default_factory=list)
    links: List[GraphLinkVO] = Field(default_factory=list)
    # entity 检索视图附加:命中 kn 实体名 → 图上下文证据(一跳关联实体
    # + 来源文档片段,vault 图查询确定性收集,零 LLM)——前端展示与
    # 下游 LLM 复用同一份证据
    entity_context: Optional[Dict[str, str]] = None


class SpaceInfoVO(BaseModel):
    """The ECP soft-layer knowledge space of a workspace."""

    model_config = ConfigDict(title="EcpSpaceInfo")

    slug: str
    workspace_id: str
    created: bool = False


class WorkspaceConfigVO(BaseModel):
    """Per-workspace ECP settings.

    The proposal agent is a standard agent from the agent store; ECP does
    not duplicate the agent platform's model/prompt configuration.
    """

    model_config = ConfigDict(title="EcpWorkspaceConfig")

    workspace_id: str = "default"
    proposal_agent_id: Optional[str] = Field(
        default=None,
        description="提案 Agent（Agent 空间中的标准 Agent，绑定 ECP 工具）；"
        "空则使用内置批处理提案管线",
    )


class WorkspaceConfigUpdateRequest(BaseModel):
    """Update workspace ECP settings."""

    model_config = ConfigDict(title="EcpWorkspaceConfigUpdate")

    workspace_id: Optional[str] = None
    proposal_agent_id: Optional[str] = None


class EcpImportRequest(BaseModel):
    """Import a semantic-asset snapshot (from an export) into a workspace.

    ``datasource_map`` rewrites ``entity.binding.datasource_id`` and ``db``
    asset refs, so assets from another system bind to the target's datasources.
    """

    model_config = ConfigDict(title="EcpImportRequest")

    workspace_id: Optional[str] = None
    data: Dict[str, Any] = Field(
        default_factory=dict, description="导出的语义资产 JSON(export_workspace 产物)"
    )
    datasource_map: Dict[str, Any] = Field(
        default_factory=dict,
        description="str(旧 datasource_id) -> 新 datasource_id",
    )


class EcpImportResultVO(BaseModel):
    """Result of an import run."""

    model_config = ConfigDict(title="EcpImportResult")

    workspace_id: str
    imported: int = 0
    skipped: int = 0
    assets_imported: int = 0
    errors: List[str] = Field(default_factory=list)


class DebugPreviewRequest(BaseModel):
    """确认页调试验证(dry-run)请求参数。

    filters: [{ dim_id | dim, values: [label...], mode: include|exclude }]
    group_by: [dim_id...]
    time_range: { range: "start~end", column: "ts" (可选,缺省取实体 role=time 字段) }
    仅 metric 使用上述参数;entity/dimension/relation 无需参数即试跑。
    """

    model_config = ConfigDict(title="EcpDebugPreviewRequest")

    workspace_id: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    group_by: Optional[List[str]] = None
    time_range: Optional[Dict[str, Any]] = None
    limit: int = Field(default=20, ge=1, le=200)


class DebugPreviewVO(BaseModel):
    """调试验证结果。trust=preview(永不 verified);ok=false 时 error 说明原因。"""

    model_config = ConfigDict(title="EcpDebugPreviewResult")

    trust: str = "preview"  # preview | none
    ok: bool = False
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    sql: Optional[str] = None
    # 文档类(claim/terminology/policy)出处校验结果
    anchor_verified: Optional[bool] = None
    quote: Optional[str] = None
    lineage: Optional[Dict[str, Any]] = None
