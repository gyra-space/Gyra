import { GET, POST } from '..';

export interface AppCardQuery {
  key: string;
  kind: 'metric' | 'sql';
  metric_id?: string;
  sql?: string;
  datasource_id?: number;
  bind_params?: Record<string, unknown>;
  version?: number;
  group_by?: string[];
  filters?: unknown[];
  time_range?: Record<string, unknown>;
  limit?: number;
}

export interface AppCardItem {
  id: number;
  workspace_id: number;
  name: string;
  description?: string | null;
  kind: string;
  status: string;
  code: string;
  config: Record<string, unknown>;
  queries: AppCardQuery[];
  current_version: number;
  source_task_id?: number | null;
  created_by?: string | null;
  gmt_created: string;
  gmt_modified: string;
}

export interface AppCardCreatePayload {
  workspace_id: number;
  name: string;
  description?: string;
  kind?: string;
  code: string;
  config?: Record<string, unknown>;
  queries?: AppCardQuery[];
  source_task_id?: number;
  created_by?: string;
  dry_run?: boolean;
}

/** 统一调用协议: op ∈ query.metric / query.sql / assets.get / preview.* */
export function invokeAppCard(
  workspaceId: number,
  cardId: number,
  data: { op: string; params?: Record<string, unknown>; query_key?: string },
) {
  return POST(
    `/api/v1/serve_app_card_service/app_cards/${cardId}/invoke?workspace_id=${workspaceId}`,
    data,
  );
}

export function listAppCards(workspaceId: number, limit = 50) {
  return POST('/api/v1/serve_app_card_service/app_cards/list', { workspace_id: workspaceId, limit });
}

export function getAppCard(cardId: number, workspaceId: number) {
  return GET('/api/v1/serve_app_card_service/app_cards/info', { card_id: cardId, workspace_id: workspaceId });
}

export function createAppCard(payload: AppCardCreatePayload) {
  return POST('/api/v1/serve_app_card_service/app_cards/create', payload);
}

export function updateAppCard(payload: Record<string, unknown>) {
  if (payload.workspace_id === undefined) {
    throw new Error('updateAppCard requires workspace_id');
  }
  return POST('/api/v1/serve_app_card_service/app_cards/update', payload);
}
