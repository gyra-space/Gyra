/**
 * ECP (Enterprise Context Protocol) 语义资产 API Client
 * 对应后端 /api/v1/serve/ecp/*
 */

import { GET, POST, PUT, DELETE } from '../index';

// =============================================================================
// Types
// =============================================================================

export interface EcpSemanticObject {
  id: string;
  version: number;
  workspace_id: string;
  obj_type: 'entity' | 'metric' | 'relation' | 'dimension' | 'claim' | 'terminology' | 'policy';
  status: 'proposed' | 'confirmed' | 'rejected' | 'deprecated' | 'superseded';
  name?: string | null;
  payload: Record<string, any>;
  confidence?: number | null;
  evidence?: Array<{ source?: string; quote?: string }> | null;
  created_by: string;
  created_at?: string | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  source?: string | null;
  /** 结构化溯源(origin/actor/origin_sql/miss_ref/derived_from) */
  provenance?: Record<string, any> | null;
  supersedes?: number | null;
  /** 业务视图(include_view 时由后端读时派生) */
  view?: EcpProposalView | null;
}

// =============================================================================
// 提案业务视图(后端 service/proposal_view.py 读时派生)
// =============================================================================

export interface EcpOrigin {
  /** discovery|miss_learn|manual_sql|rule5_gate|edit|agent|import|legacy */
  kind: string;
  /** 中文标签(初始扫描/MISS 学习/手工 SQL 等) */
  label: string;
  actor?: string | null;
  /** 原始 SQL 快照(MISS 学习/手工 SQL) */
  origin_sql: string[];
  /** miss 聚类回链 {kind, pattern, datasource_id} */
  miss_ref?: { kind?: string; pattern?: string; datasource_id?: number | null } | null;
  note?: string | null;
  derived_from?: string | null;
  /** 老数据降级:原始 source 字符串 */
  legacy_source?: string | null;
}

export interface EcpColumnRef {
  column: string;
  meaning?: string | null;
  role?: string | null;
  /** 度量表达式|筛选条件|分组粒度|维度列|主键|时间列(可组合) */
  usage: string;
  /** false = expression 引用但 entity.fields 未声明(口径疑点) */
  declared: boolean;
}

export interface EcpObjectRef {
  id: string;
  obj_type?: string | null;
  name?: string | null;
  status?: string | null;
  version?: number | null;
}

export interface EcpLineage {
  datasource_id?: number | null;
  datasource_name?: string | null;
  tables: string[];
  columns: EcpColumnRef[];
  /** 引用链上的语义对象(metric→entity→dimension),带状态 */
  objects: EcpObjectRef[];
  /** 文档类定位 */
  document?: { space?: string; doc_id?: string; anchor?: string } | null;
}

export interface EcpSqlPreview {
  sql?: string | null;
  /** 预览口径说明(时间窗/筛选假设) */
  scenario: string;
  participants: EcpObjectRef[];
  warnings: string[];
}

export interface EcpProposalView {
  summary: string;
  origin: EcpOrigin;
  lineage?: EcpLineage | null;
  sql_preview?: EcpSqlPreview | null;
  evidence: Array<{ source?: string | null; quote?: string | null }>;
}

export interface EcpObjectListResult {
  items: EcpSemanticObject[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface EcpCatalogEntry {
  id: string;
  obj_type: string;
  name?: string | null;
  aliases: string[];
  one_line?: string | null;
  grain?: string[] | null;
}

export interface EcpConfirmer {
  id: number;
  workspace_id: string;
  user_id: string;
  scope?: string | null;
  user_name?: string | null;
}

export interface EcpOpLogEntry {
  id: number;
  workspace_id: string;
  ts?: string | null;
  op: string;
  detail?: Record<string, any> | null;
}

export interface EcpObjectFilters {
  workspace_id?: string;
  obj_type?: string;
  status?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}

// =============================================================================
// API
// =============================================================================

const API_PREFIX = '/api/v1/serve/ecp';

export const getEcpInbox = (params: EcpObjectFilters) =>
  GET<EcpObjectFilters, EcpObjectListResult>(`${API_PREFIX}/inbox`, params);

export const listEcpObjects = (params: EcpObjectFilters) =>
  GET<EcpObjectFilters, EcpObjectListResult>(`${API_PREFIX}/objects`, params);

export const getEcpObject = (id: string, workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpSemanticObject>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}`,
    { workspace_id },
  );

export const getEcpObjectVersions = (id: string, workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpSemanticObject[]>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}/versions`,
    { workspace_id },
  );

/** 单个版本的完整业务视图(含静态 SQL 预览),详情页数据源。 */
export const getEcpProposalView = (id: string, version: number, workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpProposalView>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}/versions/${version}/view`,
    { workspace_id },
  );

export interface EcpContractRule {
  path: string;
  message: string;
}

export interface EcpContractSpec {
  proposal: EcpContractRule[];
  executable: EcpContractRule[];
  notes: string[];
}

/** 各对象类型的 payload 契约清单(编辑表单的单一事实来源)。 */
export const getEcpContracts = () =>
  GET<Record<string, never>, Record<string, EcpContractSpec>>(`${API_PREFIX}/contracts`);

// =============================================================================
// Debug preview (确认页调试验证, trust=preview 只读 dry-run)
// =============================================================================

export interface EcpDebugFilter {
  /** 维度 id(dim_id 或 dim 均可) */
  dim_id?: string;
  dim?: string;
  /** 值字典 label(或原始 code) */
  values?: string[];
  values_label?: string[];
  mode?: 'include' | 'exclude';
}

export interface EcpDebugTimeRange {
  /** "start~end",如 "2024-01-01~2024-12-31" */
  range?: string;
  /** 时间列,可选;缺省取实体 role=time 字段 */
  column?: string;
}

export interface EcpDebugRequest {
  workspace_id?: string;
  filters?: EcpDebugFilter[];
  group_by?: string[];
  time_range?: EcpDebugTimeRange;
  limit?: number;
}

export interface EcpDebugPreview {
  trust: 'preview' | 'none';
  ok: boolean;
  error?: string | null;
  warnings: string[];
  columns: string[];
  rows: Array<Record<string, any>>;
  row_count: number;
  sql?: string | null;
  anchor_verified?: boolean | null;
  quote?: string | null;
  lineage?: Record<string, any> | null;
}

export const debugEcpObject = (
  id: string,
  version: number,
  data: EcpDebugRequest,
) =>
  POST<EcpDebugRequest, EcpDebugPreview>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}/versions/${version}/debug`,
    data,
  );

export const confirmEcpObject = (
  id: string,
  version: number,
  data: { user_id: string; workspace_id?: string; edited_payload?: Record<string, any> },
) =>
  POST<typeof data, EcpSemanticObject>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}/versions/${version}/confirm`,
    data,
  );

export const rejectEcpObject = (
  id: string,
  version: number,
  data: { user_id: string; workspace_id?: string; reason?: string },
) =>
  POST<typeof data, EcpSemanticObject>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}/versions/${version}/reject`,
    data,
  );

export const deprecateEcpObject = (
  id: string,
  data: { user_id: string; workspace_id?: string; reason?: string },
) =>
  POST<typeof data, EcpSemanticObject>(
    `${API_PREFIX}/objects/${encodeURIComponent(id)}/deprecate`,
    data,
  );

export const proposeEcpObject = (data: {
  id: string;
  obj_type: string;
  payload: Record<string, any>;
  workspace_id?: string;
  confidence?: number;
  evidence?: Array<{ source?: string; quote?: string }>;
  created_by?: string;
  source?: string;
}) =>
  POST<typeof data, EcpSemanticObject>(
    `${API_PREFIX}/objects/propose`,
    data,
  );

export interface EcpSqlAddResult {
  workspace_id: string;
  added: number;
  confirmed_ids: string[];
  duplicate_existing: string[];
  errors: string[];
}

/** 给 SQL 直接添加语义(添加即确认)。 */
export const addEcpObjectFromSql = (data: {
  sql: string;
  description?: string;
  workspace_id?: string;
  user_id: string;
  confirm?: boolean;
}) => POST<typeof data, EcpSqlAddResult>(`${API_PREFIX}/objects/manual`, data);

/**
 * 导入报表文件(SQL 脚本/代码),异步提炼语义提案(默认进待确认收件箱)。
 * 立即返回 task_id,可用 getEcpProposalTask 轮询进度。
 */
export const importEcpObjectFromFile = (data: FormData) =>
  POST<FormData, { task_id: string }>(`${API_PREFIX}/objects/manual/file`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const getEcpCatalog = (params?: { workspace_id?: string; keyword?: string }) =>
  GET<typeof params, EcpCatalogEntry[]>(`${API_PREFIX}/catalog`, params);

export const generateEcpProposals = (data: {
  datasource_id?: number;
  workspace_id?: string;
  table_names?: string[];
  max_tables?: number;
  domain_hint?: string;
}) =>
  POST<typeof data, { task_id: string }>(`${API_PREFIX}/proposals/generate`, data);

/** Async proposal generation task status/result (polled by the asset tab). */
export const getEcpProposalTask = (taskId: string) =>
  GET<{}, {
    task_id: string;
    conv_id: string;
    /** ecp_proposal */
    kind: string;
    model: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout' | 'cancelled';
    error?: string;
    result_preview?: string;
    /** 结构化解构(引擎 to_record 落于 detail.artifact) */
    detail?: {
      artifact?: {
        tables_processed?: number;
        proposals_created?: number;
        proposal_ids?: string[];
        errors?: string[];
      };
    };
    created_at?: string;
    started_at?: string;
    completed_at?: string;
  }>(`${API_PREFIX}/proposals/tasks/${encodeURIComponent(taskId)}`);

export const listEcpConfirmers = (workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpConfirmer[]>(`${API_PREFIX}/confirmers`, {
    workspace_id,
  });

export const addEcpConfirmer = (data: {
  user_id: string;
  workspace_id?: string;
  scope?: string;
}) => POST<typeof data, boolean>(`${API_PREFIX}/confirmers`, data);

export const removeEcpConfirmer = (id: number) =>
  DELETE<Record<string, never>, boolean>(`${API_PREFIX}/confirmers/${id}`);

export const getEcpOpLog = (params: {
  workspace_id?: string;
  op?: string;
  page?: number;
  page_size?: number;
}) => GET<typeof params, EcpOpLogEntry[]>(`${API_PREFIX}/op-log`, params);

// =============================================================================
// Asset refs / readiness / graph / space
// =============================================================================

export interface EcpAssetRef {
  id: number;
  workspace_id: string;
  kind: 'db' | 'document' | 'space' | 'api';
  ref_id: string;
  ref_meta: Record<string, any>;
  status: string;
  last_checked_at?: string | null;
}

export interface EcpReadinessCheck {
  item: string;
  ready: boolean;
  detail?: string | null;
}

export interface EcpReadiness {
  kind: string;
  ref_id: string;
  ready: boolean;
  checks: EcpReadinessCheck[];
}

export interface EcpGraphNode {
  id: string;
  obj_type: string;
  name?: string | null;
  status: string;
  version: number;
  /** object = 硬层语义对象（默认）；asset = 已登记资产引用；kn = 知识层节点 */
  node_kind?: 'object' | 'asset' | 'kn';
}

export interface EcpGraphLink {
  source: string;
  target: string;
  edge_type: string;
  status?: string | null;
}

export interface EcpGraph {
  nodes: EcpGraphNode[];
  links: EcpGraphLink[];
  /** entity 检索视图附加:命中 kn 实体名 → 图上下文证据(一跳关联 + 来源文档片段) */
  entity_context?: Record<string, string> | null;
}

export interface EcpGraphRebuildResult {
  workspace_id: string;
  objects: number;
  edges: number;
}

export interface EcpSpaceInfo {
  slug: string;
  workspace_id: string;
  created: boolean;
}

export const registerEcpAsset = (data: {
  kind: string;
  ref_id: string;
  workspace_id?: string;
  ref_meta?: Record<string, any>;
}) => POST<typeof data, EcpAssetRef>(`${API_PREFIX}/assets`, data);

export const listEcpAssets = (params?: { workspace_id?: string; kind?: string }) =>
  GET<typeof params, EcpAssetRef[]>(`${API_PREFIX}/assets`, params);

export const deleteEcpAsset = (asset_id: number, workspace_id?: string) =>
  DELETE<{ workspace_id?: string }, boolean>(
    `${API_PREFIX}/assets/${asset_id}`,
    { workspace_id },
  );

export const getEcpReadiness = (datasource_id: number, workspace_id?: string) =>
  GET<{ datasource_id: number; workspace_id?: string }, EcpReadiness>(
    `${API_PREFIX}/readiness`,
    { datasource_id, workspace_id },
  );

export const getEcpGraph = (workspace_id?: string, entity?: string) =>
  GET<{ workspace_id?: string; entity?: string }, EcpGraph>(
    `${API_PREFIX}/graph`,
    { workspace_id, entity },
  );

export const rebuildEcpGraph = (workspace_id?: string) =>
  POST<Record<string, never>, EcpGraphRebuildResult>(
    `${API_PREFIX}/graph/rebuild${workspace_id ? `?workspace_id=${encodeURIComponent(workspace_id)}` : ''}`,
    {},
  );

export const getOrCreateEcpSpace = (workspace_id?: string) =>
  POST<Record<string, never>, EcpSpaceInfo>(
    `${API_PREFIX}/space${workspace_id ? `?workspace_id=${encodeURIComponent(workspace_id)}` : ''}`,
    {},
  );

// =============================================================================
// Semantic alignment (知识实体 × 语义对象的 LLM 语义对齐)
// =============================================================================

export interface EcpSemanticAlignment {
  id: number;
  workspace_id: string;
  slug: string;
  entity_name: string;
  object_id: string;
  status: 'proposed' | 'confirmed' | 'rejected';
  confidence?: number | null;
  rationale?: string | null;
  /** llm = 推理产出;manual = 人工兜底(直通 confirmed) */
  source: 'llm' | 'manual';
  decided_by?: string | null;
  gmt_modify?: string | null;
}

export interface EcpAlignmentRunResult {
  workspace_id: string;
  entities: number;
  candidates: number;
  errors: string[];
}

export const runEcpAlignment = (workspace_id?: string, user_id?: string) => {
  const qs = [
    workspace_id ? `workspace_id=${encodeURIComponent(workspace_id)}` : '',
    user_id ? `user_id=${encodeURIComponent(user_id)}` : '',
  ]
    .filter(Boolean)
    .join('&');
  return POST<Record<string, never>, EcpAlignmentRunResult>(
    `${API_PREFIX}/graph/alignments/run${qs ? `?${qs}` : ''}`,
    {},
  );
};

export const listEcpAlignments = (params?: { workspace_id?: string; status?: string }) =>
  GET<typeof params, EcpSemanticAlignment[]>(
    `${API_PREFIX}/graph/alignments`,
    params,
  );

export const addEcpAlignment = (data: {
  entity_name: string;
  object_id: string;
  user_id?: string;
  workspace_id?: string;
}) => POST<typeof data, EcpSemanticAlignment>(`${API_PREFIX}/graph/alignments`, data);

export const confirmEcpAlignment = (id: number, data?: { user_id?: string }) =>
  POST<typeof data, EcpSemanticAlignment>(
    `${API_PREFIX}/graph/alignments/${id}/confirm`,
    data ?? {},
  );

export const rejectEcpAlignment = (id: number, data?: { user_id?: string }) =>
  POST<typeof data, EcpSemanticAlignment>(
    `${API_PREFIX}/graph/alignments/${id}/reject`,
    data ?? {},
  );

export const removeEcpAlignment = (id: number) =>
  DELETE<Record<string, never>, boolean>(`${API_PREFIX}/graph/alignments/${id}`);

// =============================================================================
// Workspace config (proposal agent settings)
// =============================================================================

export interface EcpWorkspaceConfig {
  workspace_id: string;
  proposal_agent_id?: string | null;
}

export const getEcpWorkspaceConfig = (workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpWorkspaceConfig>(
    `${API_PREFIX}/workspace-config`,
    { workspace_id },
  );

export const saveEcpWorkspaceConfig = (data: Partial<EcpWorkspaceConfig>) =>
  PUT<typeof data, EcpWorkspaceConfig>(`${API_PREFIX}/workspace-config`, data);

export interface EcpLinkedResource {
  datasource_id: number;
  db_name: string;
  db_type: string;
}

export const getEcpLinkedResources = (workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpLinkedResource[]>(
    `${API_PREFIX}/linked-resources`,
    { workspace_id },
  );

// =============================================================================
// Admin: contract check / normalize / miss flywheel
// =============================================================================

export interface EcpMissCluster {
  datasource_id?: number | null;
  pattern: string;
  count: number;
  example_sql: string;
  reasonings: string[];
  last_seen?: string | null;
  kind?: string;
}

export interface EcpMissReport {
  workspace_id: string;
  total_fallbacks: number;
  cluster_count: number;
  /** 已被标记为"已学习"、从 clusters 中排除掉的聚类数 */
  learned_count?: number;
  clusters: EcpMissCluster[];
}

export interface EcpMissLearn {
  id: number;
  workspace_id: string;
  kind: string;
  datasource_id?: number | null;
  pattern: string;
  example?: string | null;
  proposal_ids: string[];
  /** agent=自动学习(每日 cron 由提案 Agent 调用 mark_miss_learned)；learn_from_misses=手动触发 */
  trigger: string;
  learned_at?: string | null;
}

export interface EcpMissRecord {
  ts?: string | null;
  sql?: string | null;
  question?: string | null;
  reasoning?: string | null;
  datasource_id?: number | null;
  spaces?: string[] | null;
}

export interface EcpMissLearnEvent {
  ts?: string | null;
  /** miss_learned=标记已学习；miss_learn_clear=清除标记(重新曝光) */
  op: string;
  trigger?: string | null;
  proposals: string[];
}

export interface EcpMissClusterSummary {
  kind: string;
  datasource_id?: number | null;
  pattern: string;
  count: number;
  example_sql?: string | null;
  reasonings: string[];
  spaces?: string[] | null;
  first_seen?: string | null;
  last_seen?: string | null;
}

/** 单个 miss 聚类的学习档案(点击聚类行展开 Drawer) */
export interface EcpMissDetail {
  workspace_id: string;
  cluster: EcpMissClusterSummary;
  records: EcpMissRecord[];
  learned?: EcpMissLearn | null;
  learn_events: EcpMissLearnEvent[];
}

export interface EcpContractCheck {
  workspace_id: string;
  total: number;
  non_compliant_count: number;
  non_compliant: Array<{
    id: string;
    obj_type: string;
    version: number;
    problems: string[];
  }>;
}

export const getEcpMissReport = (params?: { workspace_id?: string; limit?: number }) =>
  GET<typeof params, EcpMissReport>(`${API_PREFIX}/admin/miss_report`, params);

export const getEcpMissDetail = (params: {
  workspace_id?: string;
  kind: string;
  pattern: string;
  datasource_id?: number;
}) => GET<typeof params, EcpMissDetail>(`${API_PREFIX}/admin/miss_detail`, params);

export const learnEcpFromMisses = (params?: { workspace_id?: string; top?: number }) =>
  POST<Record<string, never>, {
    datasource_id: number;
    tables_processed: number;
    proposals_created: number;
    proposal_ids: string[];
    errors: string[];
  }>(
    `${API_PREFIX}/admin/learn_from_misses${params?.workspace_id ? `?workspace_id=${encodeURIComponent(params.workspace_id)}` : ''}${params?.top ? `${params?.workspace_id ? '&' : '?'}top=${params.top}` : ''}`,
    {},
  );

export const listEcpMissLearned = (params?: { workspace_id?: string; kind?: string }) =>
  GET<typeof params, EcpMissLearn[]>(`${API_PREFIX}/admin/miss_learned`, params);

export const clearEcpMissLearned = (params?: {
  workspace_id?: string;
  kind?: string;
  pattern?: string;
  datasource_id?: number;
}) => DELETE<typeof params, number>(`${API_PREFIX}/admin/miss_learned`, params);

export const getEcpContractCheck = (workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpContractCheck>(`${API_PREFIX}/admin/contract_check`, {
    workspace_id,
  });

export const normalizeEcpConfirmed = (workspace_id?: string) =>
  POST<Record<string, never>, {
    workspace_id: string;
    checked: number;
    fixed: Array<{ id: string; version: number }>;
    skipped: Array<{ id: string; problems: string[] }>;
  }>(
    `${API_PREFIX}/admin/normalize${workspace_id ? `?workspace_id=${encodeURIComponent(workspace_id)}` : ''}`,
    {},
  );

// =============================================================================
// 资产迁移(导出 / 导入)
// =============================================================================

export interface EcpDatasourceRef {
  datasource_id: string;
  db_name?: string;
  db_type?: string;
  tables?: string[];
}

export interface EcpExportObject {
  id: string;
  version: number;
  workspace_id: string;
  obj_type: string;
  status: string;
  name?: string | null;
  payload: Record<string, any>;
  confidence?: number | null;
  evidence?: Array<{ source?: string; quote?: string }> | null;
  created_by: string;
  created_at?: string | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  source?: string | null;
  supersedes?: number | null;
}

export interface EcpExportAsset {
  id: number;
  workspace_id: string;
  kind: 'db' | 'document' | 'space' | 'api';
  ref_id: string;
  ref_meta: Record<string, any>;
  status: string;
  last_checked_at?: string | null;
}

export interface EcpExportPayload {
  format_version: number;
  exported_at: string;
  source_workspace_id: string;
  datasource_refs: EcpDatasourceRef[];
  objects: EcpExportObject[];
  assets: EcpExportAsset[];
}

export interface EcpImportResult {
  workspace_id: string;
  imported: number;
  skipped: number;
  assets_imported: number;
  errors: string[];
}

export const exportEcpWorkspace = (workspace_id?: string) =>
  GET<{ workspace_id?: string }, EcpExportPayload>(`${API_PREFIX}/export`, {
    workspace_id,
  });

export const importEcpWorkspace = (data: {
  workspace_id?: string;
  data: EcpExportPayload;
  datasource_map?: Record<string, string>;
}) => POST<typeof data, EcpImportResult>(`${API_PREFIX}/import`, data);
