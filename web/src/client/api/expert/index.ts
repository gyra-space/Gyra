import { POST, GET } from '..';

// 专家团队（Agent Team 空间重构 Phase 1.4）
// 路径在 workspace service 下（/api/v1/serve_workspace_service/...）
export const upsertExpert = (workspace_id: number, data: any) =>
  POST(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/experts/upsert`, data);
export const bindExpert = (workspace_id: number, data: any) =>
  POST(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/experts/bind`, data);
export const unbindExpert = (workspace_id: number, app_code: string) =>
  POST(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/experts/unbind?app_code=${encodeURIComponent(app_code)}`, {});
export const listExperts = (workspace_id: number) =>
  GET(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/experts`);
export const getTeamView = (workspace_id: number) =>
  GET(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/team`);
export const expertChat = (workspace_id: number, data: any) =>
  POST(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/experts/chat`, data);
export const listContracts = (workspace_id: number) =>
  GET(`/api/v1/serve_workspace_service/workspaces/${workspace_id}/contracts`);

export interface ExpertEquipmentItem {
  resource_type: string;
  resource_ref: string;
  config?: Record<string, any>;
}
export interface ExpertInfo {
  id: number;
  workspace_id: number;
  app_code: string;
  app_name?: string;
  icon?: string;
  /** 空间级头像覆盖原始值；空 = 未覆盖（icon 为回落后的全局身份头像） */
  workspace_icon?: string;
  app_describe?: string;
  role_hint?: string;
  default_contract_id?: number;
  owner_workspace_id?: number;
  is_active: boolean;
  equipment: ExpertEquipmentItem[];
  gmt_created?: string;
  gmt_modified?: string;
}
