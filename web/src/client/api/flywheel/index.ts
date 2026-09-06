/**
 * 飞轮体系前端 API 客户端 —— 资产成熟度/Agent 成长/评委动作/演化审批。
 *
 * 后端端点约定:
 *   - 资产成熟度: /api/v1/serve_workspace_asset_service/assets/maturity/*
 *   - 索引对账:   /api/v1/serve_workspace_asset_service/assets/index/*
 *   - 记忆沉淀:   /api/v1/serve_workspace_asset_service/assets/sediment/*
 *   - Agent 成长: /api/v1/serve_workspace_service/agent_maturity/*
 *   - 职能角色:   /api/v1/serve_workspace_service/agent_roles/*
 *   - 场景模式:   /api/v1/serve_workspace_service/scene_modes/*
 *   - 评委动作:   /api/v1/serve_intervention_service/interventions/*
 *   - 合约演化:   /api/v1/serve_playbook_service/evolution/*
 */
import { GET, POST } from '..';

const ASSET_PREFIX = '/api/v1/serve_workspace_asset_service';
const WORKSPACE_PREFIX = '/api/v1/serve_workspace_service';
const INTERVENTION_PREFIX = '/api/v1/serve_intervention_service';
const PLAYBOOK_PREFIX = '/api/v1/serve_playbook_service';

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

/** 资产成熟度五级 */
export type AssetMaturityLevel =
  | 'draft'
  | 'proposed'
  | 'confirmed'
  | 'published'
  | 'canonical';

/** Agent 成长四阶段 */
export type AgentStage = 'novice' | 'proficient' | 'expert' | 'master';

/** Agent 职能角色 */
export type AgentRole =
  | 'fetcher'
  | 'analyzer'
  | 'reporter'
  | 'coordinator'
  | 'reviewer';

/** 场景模式 */
export type SceneMode = 'task' | 'decision' | 'knowledge' | 'monitoring';

/** 评委动作 */
export type JudgeAction = 'attest' | 'coach' | 'escalate' | 'reconcile';

/** 通用键值负载(后端 JSON 字段) */
export type JsonPayload = Record<string, unknown>;

/** 通用 OK 响应(仅确认操作成功) */
export interface OkResponse {
  ok?: boolean;
  message?: string;
}

/** 资产成熟度记录 */
export interface AssetMaturityRecord {
  id: number;
  asset_id: number;
  workspace_id: number;
  from_level: string;
  to_level: string;
  actor: string;
  note?: string;
  evidence?: JsonPayload;
  gmt_created: string;
}

/** 资产(含成熟度) */
export interface AssetWithMaturity {
  id: number;
  workspace_id: number;
  type: string;
  name: string;
  description?: string;
  maturity: AssetMaturityLevel;
  attest_count: number;
  reference_count: number;
  maturity_at?: string;
  source_agent_id?: string;
  gmt_created: string;
}

/** Agent 成长记录 */
export interface AgentMaturityRecord {
  id: number;
  agent_id: string;
  workspace_id: number;
  stage: AgentStage;
  total_score: number;
  attest_count: number;
  execution_count: number;
  success_rate: number;
  evolution_count: number;
  evaluation_score: number;
  coach_penalty_count: number;
  gmt_created: string;
  gmt_modified: string;
}

/** 合约演化提议 */
export interface EvolutionProposal {
  proposal_id: string;
  playbook_id: number;
  workspace_id: number;
  detector_name: string;
  change_type: string;
  description: string;
  diff?: JsonPayload;
  proposed_by: string;
  status: 'pending' | 'approved' | 'rejected';
  gmt_created: string;
}

/** 评委介入记录 */
export interface InterventionRecord {
  id: number;
  task_id?: number;
  workspace_id: number;
  type: string;
  status: string;
  requested_by: string;
  assignee_user_id?: number;
  question?: JsonPayload;
  context?: JsonPayload;
  resolved_by_user_id?: number;
  resolved_at?: string;
  decision?: JsonPayload;
  gmt_created: string;
}

/** 场景模式配置 */
export interface SceneModeConfig {
  mode: SceneMode;
  label: string;
  description: string;
  default_tools: string[];
  require_gate: boolean;
}

// ---------------------------------------------------------------------------
// 资产成熟度 API
// ---------------------------------------------------------------------------

/** 按成熟度列出资产 */
export const listAssetsByMaturity = (data: {
  workspace_id: number;
  min_maturity?: string;
  limit?: number;
}) =>
  POST<typeof data, AssetWithMaturity[]>(
    `${ASSET_PREFIX}/assets/maturity/list_by_maturity`,
    data,
  );

/** 资产晋升 */
export const promoteAssetMaturity = (data: {
  asset_id: number;
  to_level: AssetMaturityLevel;
  actor: string;
  note?: string;
}) =>
  POST<typeof data, AssetMaturityRecord>(
    `${ASSET_PREFIX}/assets/maturity/promote`,
    data,
  );

/** 资产背书 */
export const attestAsset = (data: {
  asset_id: number;
  actor: string;
  note?: string;
}) => POST<typeof data, AssetWithMaturity>(`${ASSET_PREFIX}/assets/maturity/attest`, data);

/** 资产教练(降级) */
export const coachAsset = (data: {
  asset_id: number;
  user_id: number;
  coach_note: string;
  severity?: 'minor' | 'major';
}) =>
  POST<typeof data, AssetWithMaturity>(
    `${ASSET_PREFIX}/assets/maturity/coach`,
    data,
  );

/** 资产成熟度日志 */
export const getAssetMaturityLogs = (asset_id: number) =>
  GET<null, AssetMaturityRecord[]>(
    `${ASSET_PREFIX}/assets/maturity/${asset_id}/logs`,
  );

/** 索引检索响应 */
export interface IndexedAssetsResponse {
  assets: AssetWithMaturity[];
  total: number;
}

/** 索引检索 */
export const searchAssetsByIndex = (data: {
  workspace_id: number;
  query?: string;
  asset_type?: string;
  min_maturity?: string;
  limit?: number;
}) =>
  POST<typeof data, IndexedAssetsResponse>(`${ASSET_PREFIX}/assets/search_indexed`, data);

/** 索引对账响应 */
export interface ReconcileResponse {
  added: number;
  removed: number;
  updated: number;
}

/** 索引对账 */
export const reconcileAssetIndex = (data: { workspace_id: number }) =>
  POST<typeof data, ReconcileResponse>(`${ASSET_PREFIX}/assets/index/reconcile`, data);

/** 沉淀检查响应 */
export interface SedimentCheckResponse {
  sedimented: number;
  skipped: number;
  candidates: Array<{ trace_id: string; reason: string }>;
}

/** 沉淀检查 */
export const checkSediment = (data: {
  agent_id: string;
  workspace_id: number;
}) =>
  POST<typeof data, SedimentCheckResponse>(`${ASSET_PREFIX}/assets/sediment/check`, data);

// ---------------------------------------------------------------------------
// Agent 成长 API
// ---------------------------------------------------------------------------

/** 列出 workspace 下 Agent 成长状态 */
export const listAgentMaturity = (
  workspace_id: number,
  stage?: AgentStage,
) => {
  const qs = new URLSearchParams({ workspace_id: String(workspace_id) });
  if (stage) qs.set('stage', stage);
  return GET<null, AgentMaturityRecord[]>(
    `${WORKSPACE_PREFIX}/agent_maturity/list?${qs.toString()}`,
  );
};

/** 查询单个 Agent 成长状态 */
export const getAgentMaturity = (agent_id: string, workspace_id: number) =>
  GET<null, AgentMaturityRecord>(
    `${WORKSPACE_PREFIX}/agent_maturity/${agent_id}?workspace_id=${workspace_id}`,
  );

/** 背书 Agent */
export const attestAgent = (
  agent_id: string,
  data: { user_id: number; workspace_id: number },
) =>
  POST<typeof data, AgentMaturityRecord>(
    `${WORKSPACE_PREFIX}/agent_maturity/${agent_id}/attest`,
    data,
  );

/** 晋升 Agent */
export const promoteAgent = (
  agent_id: string,
  data: { to_stage: AgentStage; actor: string; workspace_id: number; force?: boolean },
) =>
  POST<typeof data, AgentMaturityRecord>(
    `${WORKSPACE_PREFIX}/agent_maturity/${agent_id}/promote`,
    data,
  );

/** 重算 Agent 成熟度 */
export const recalculateAgent = (agent_id: string, workspace_id: number) =>
  POST<null, AgentMaturityRecord>(
    `${WORKSPACE_PREFIX}/agent_maturity/${agent_id}/recalculate?workspace_id=${workspace_id}`,
    null,
  );

// ---------------------------------------------------------------------------
// 职能角色 API
// ---------------------------------------------------------------------------

/** 角色分配记录 */
export interface AgentRoleAssignment {
  agent_id: string;
  role: AgentRole;
  workspace_id: number;
  stage: AgentStage;
}

/** 角色成熟度校验响应 */
export interface RoleMaturityCheck {
  agent_id: string;
  role: AgentRole;
  current_stage: AgentStage;
  required_stage: AgentStage;
  satisfied: boolean;
}

/** 分配角色 */
export const assignAgentRole = (data: {
  agent_id: string;
  role: AgentRole;
  workspace_id: number;
}) =>
  POST<typeof data, AgentRoleAssignment>(
    `${WORKSPACE_PREFIX}/agent_roles/assign`,
    data,
  );

/** 列出 workspace 下角色分配 */
export const listAgentRoles = (workspace_id: number) =>
  GET<null, AgentRoleAssignment[]>(
    `${WORKSPACE_PREFIX}/agent_roles/list?workspace_id=${workspace_id}`,
  );

/** 校验 Agent 成熟度是否满足角色要求 */
export const checkAgentRoleMaturity = (
  agent_id: string,
  workspace_id: number,
  role: AgentRole,
) =>
  GET<null, RoleMaturityCheck>(
    `${WORKSPACE_PREFIX}/agent_roles/${agent_id}/check?workspace_id=${workspace_id}&role=${role}`,
  );

/** 装配团队蓝图 */
export const assembleTeam = (data: {
  workspace_id: number;
  declaration?: JsonPayload;
}) =>
  POST<typeof data, AgentRoleAssignment[]>(
    `${WORKSPACE_PREFIX}/agent_roles/assemble_team`,
    data,
  );

// ---------------------------------------------------------------------------
// 场景模式 API
// ---------------------------------------------------------------------------

/** 列出场景模式 */
export const listSceneModes = () =>
  GET<null, SceneModeConfig[]>(`${WORKSPACE_PREFIX}/scene_modes/list`);

/** 当前场景模式响应 */
export interface CurrentSceneModeResponse {
  workspace_id: number;
  mode: SceneMode;
  config?: SceneModeConfig;
}

/** 获取 workspace 当前场景模式 */
export const getWorkspaceSceneMode = (workspace_id: number) =>
  GET<null, CurrentSceneModeResponse>(`${WORKSPACE_PREFIX}/workspaces/${workspace_id}/scene_mode`);

/** 设置 workspace 场景模式 */
export const setWorkspaceSceneMode = (
  workspace_id: number,
  data: { mode: SceneMode },
) =>
  POST<typeof data, CurrentSceneModeResponse>(
    `${WORKSPACE_PREFIX}/workspaces/${workspace_id}/scene_mode`,
    data,
  );

// ---------------------------------------------------------------------------
// 评委动作 API
// ---------------------------------------------------------------------------

/** 创建 attest 背书介入 */
export const createAttestIntervention = (data: {
  workspace_id: number;
  task_id?: number;
  user_id: number;
  agent_id: string;
  asset_id?: number;
  note?: string;
}) =>
  POST<typeof data, InterventionRecord>(
    `${INTERVENTION_PREFIX}/interventions/attest`,
    data,
  );

/** 创建 coach 纠偏介入 */
export const createCoachIntervention = (data: {
  workspace_id: number;
  task_id?: number;
  user_id: number;
  agent_id: string;
  asset_id?: number;
  coach_note: string;
  severity?: 'minor' | 'major';
}) =>
  POST<typeof data, InterventionRecord>(
    `${INTERVENTION_PREFIX}/interventions/coach`,
    data,
  );

/** 创建 escalate 升级介入 */
export const createEscalateIntervention = (data: {
  workspace_id: number;
  task_id?: number;
  user_id: number;
  reason: string;
  target_user_id?: number;
}) =>
  POST<typeof data, InterventionRecord>(
    `${INTERVENTION_PREFIX}/interventions/escalate`,
    data,
  );

/** 创建 reconcile 对账介入 */
export const createReconcileIntervention = (data: {
  workspace_id: number;
  task_id?: number;
  user_id: number;
  description: string;
}) =>
  POST<typeof data, InterventionRecord>(
    `${INTERVENTION_PREFIX}/interventions/reconcile`,
    data,
  );

/** 列出介入记录(待评委列表) */
export const listInterventions = (data: {
  workspace_id: number;
  task_id?: number;
  status?: string;
  limit?: number;
}) =>
  POST<typeof data, InterventionRecord[]>(
    `${INTERVENTION_PREFIX}/interventions/list`,
    data,
  );

// ---------------------------------------------------------------------------
// 合约演化 API
// ---------------------------------------------------------------------------

/** 手动触发演化分析 */
export const analyzeEvolution = (data: { playbook_id: number }) =>
  POST<typeof data, EvolutionProposal[]>(
    `${PLAYBOOK_PREFIX}/evolution/analyze`,
    data,
  );

/** 列出待审批演化提议 */
export const listEvolutionProposals = (data: { workspace_id: number }) =>
  POST<typeof data, EvolutionProposal[]>(
    `${PLAYBOOK_PREFIX}/evolution/proposals/list`,
    data,
  );

/** 审批演化提议 */
export const approveEvolutionProposal = (
  proposal_id: string,
  data: { reviewer: string },
) =>
  POST<typeof data, EvolutionProposal>(
    `${PLAYBOOK_PREFIX}/evolution/proposals/${proposal_id}/approve`,
    data,
  );

/** 拒绝演化提议 */
export const rejectEvolutionProposal = (
  proposal_id: string,
  data: { reviewer: string; reason?: string },
) =>
  POST<typeof data, EvolutionProposal>(
    `${PLAYBOOK_PREFIX}/evolution/proposals/${proposal_id}/reject`,
    data,
  );

/** 获取演化提议详情 */
export const getEvolutionProposal = (proposal_id: string) =>
  GET<null, EvolutionProposal>(
    `${PLAYBOOK_PREFIX}/evolution/proposals/${proposal_id}`,
  );

/** 执行轨迹记录 */
export interface EvolutionTrace {
  trace_id: string;
  playbook_id: number;
  task_id?: number;
  status: string;
  duration_ms?: number;
  gmt_created: string;
}

/** 列出执行轨迹 */
export const listEvolutionTraces = (data: {
  playbook_id: number;
  limit?: number;
}) =>
  POST<typeof data, EvolutionTrace[]>(`${PLAYBOOK_PREFIX}/evolution/traces/list`, data);
