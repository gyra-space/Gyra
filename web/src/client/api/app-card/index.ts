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
  icon?: string | null;
  permissions?: string[];
  is_owner?: boolean;
  can_manage?: boolean;
  share_mode?: string | null;
  share_token?: string | null;
  /** 是否在应用卡片启动条展示(False = 仅维护者可见, 便于重新开启) */
  show_in_launcher?: boolean;
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
  icon?: string;
  permissions?: string[];
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

/** 开发期预览取数: 用编辑器里(未落库)的查询契约走运行期 dispatch, 不依赖已落库卡片。
 *  供「JSON 写完 → 先预览真实取数效果 → 再导入落库」使用。 */
export function previewInvokeAppCard(
  workspaceId: number,
  data: { queries: AppCardQuery[]; op: string; params?: Record<string, unknown>; query_key?: string },
) {
  return POST('/api/v1/serve_app_card_service/app_cards/preview/invoke', {
    workspace_id: workspaceId,
    ...data,
  });
}

/** 匿名分享: 凭分享令牌加载子应用渲染信息(无需登录)。 */
export function getAppCardShare(cardId: number, token: string) {
  return GET(
    `/api/v1/serve_app_card_service/app_cards/share/render?card_id=${cardId}&token=${encodeURIComponent(token)}`,
  );
}

/** 匿名分享: 凭分享令牌走统一 invoke 协议取数(无需登录)。 */
export function invokeAppCardShare(
  cardId: number,
  token: string,
  data: { op: string; params?: Record<string, unknown>; query_key?: string },
) {
  return POST(
    `/api/v1/serve_app_card_service/app_cards/share/invoke?card_id=${cardId}&token=${encodeURIComponent(token)}`,
    data,
  );
}

/** 登录分享: 已登录用户凭卡片 id 加载渲染信息(受卡片查看权限约束)。 */
export function getAppCardShareLogin(cardId: number) {
  return GET(`/api/v1/serve_app_card_service/app_cards/share/login/render?card_id=${cardId}`);
}

/** 登录分享: 已登录用户凭卡片 id 走统一 invoke 协议取数(受卡片查看权限约束)。 */
export function invokeAppCardShareLogin(
  cardId: number,
  data: { op: string; params?: Record<string, unknown>; query_key?: string },
) {
  return POST(`/api/v1/serve_app_card_service/app_cards/share/login/invoke?card_id=${cardId}`, data);
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

export function deleteAppCard(cardId: number, workspaceId: number) {
  return POST('/api/v1/serve_app_card_service/app_cards/delete', { id: cardId, workspace_id: workspaceId });
}
