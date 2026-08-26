'use client';

/**
 * App Card 手动导入的共享能力:识别 Agent/delivery 产出的 App Card payload JSON,
 * 并提供"一键导入为场景空间子应用"按钮。供大厅导入弹窗与运行结果/交付文件预览复用。
 */
import { useState } from 'react';
import { App, Button } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { apiInterceptors } from '@/client/api';
import { createAppCard, type AppCardCreatePayload } from '@/client/api/app-card';
import { ee, EVENTS } from '@/utils/event-emitter';

/** App Card payload 的 meta 签名(用于可靠识别, 而非靠 name+code 启发式)。 */
export const APP_CARD_SCHEMA_NAME = 'gyra_app_card';
export const APP_CARD_SCHEMA_VERSION = 1;

/** 校验文本是否为 App Card payload JSON,并返回"为何不合法"的提示;合法则返回 null。
 *  若为非法 JSON,错误信息会明确指出,便于用户定位真实原因。 */
export function getAppCardPayloadError(text: string): string | null {
  if (!text) return '内容为空';
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return '不是合法的 JSON（可能被截断、混入说明文字，或 code/字段内引号未转义）';
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return 'JSON 顶层需为对象';
  const obj = data as Record<string, unknown>;
  // 签名优先: 显式标为 gyra_app_card 即可认定
  const meta = obj.meta as Record<string, unknown> | undefined;
  if (meta && typeof meta === 'object' && !Array.isArray(meta) && meta.schema_name === APP_CARD_SCHEMA_NAME) {
    return null;
  }
  // 兼容旧 payload: 有 name + code 即视为 app card
  const hasName = typeof obj.name === 'string' && obj.name.trim() !== '';
  const hasCode = typeof obj.code === 'string' && obj.code.trim() !== '';
  if (hasName && hasCode) return null;
  return '需含 meta.schema_name 签名，或 name 与 code 字段';
}

/** 判断文本是否为 App Card payload JSON:
 * 优先认 meta.schema_name 签名, 兼容旧格式(仅含 name+code)。 */
export function isAppCardPayloadText(text: string): boolean {
  return getAppCardPayloadError(text) === null;
}

/** 从 App Card payload JSON 提取落库字段;非法输入返回 null。 */
export function extractAppCardPayload(rawText: string, workspaceId: number): AppCardCreatePayload | null {
  let data: unknown;
  try {
    data = JSON.parse(rawText);
  } catch {
    return null;
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const obj = data as Record<string, unknown>;
  const meta = obj.meta && typeof obj.meta === 'object' && !Array.isArray(obj.meta)
    ? (obj.meta as Record<string, unknown>)
    : undefined;
  const isSigned = !!meta && meta.schema_name === APP_CARD_SCHEMA_NAME;
  const name = (typeof obj.name === 'string' && obj.name.trim()) ||
    (meta && typeof meta.card_name === 'string' ? meta.card_name : '');
  const code = typeof obj.code === 'string' ? obj.code : '';
  // 必须满足: 有签名 或 有 name+code(兜底旧格式)
  if (!isSigned && (!name || !code.trim())) return null;
  const config = obj.config && typeof obj.config === 'object' && !Array.isArray(obj.config)
    ? { ...(obj.config as Record<string, unknown>) }
    : {};
  // meta 随 config 一起持久化, 避免改动后端建表
  if (meta) config.meta = meta;
  return {
    workspace_id: workspaceId,
    name: name || '未命名应用',
    description: typeof obj.description === 'string' ? obj.description : undefined,
    kind: typeof obj.kind === 'string' ? obj.kind : 'dashboard',
    code,
    config,
    queries: Array.isArray(obj.queries) ? (obj.queries as AppCardCreatePayload['queries']) : [],
    icon: typeof obj.icon === 'string' ? obj.icon : (typeof meta?.icon === 'string' ? meta.icon : undefined),
    permissions: Array.isArray(obj.permissions) ? (obj.permissions as string[]) : [],
  };
}

/** 一键导入为子应用按钮(sourceText 为 App Card payload JSON 时才渲染)。 */
export function AppCardImportButton({
  workspaceId,
  sourceText,
  onImported,
  compact,
}: {
  workspaceId: number;
  sourceText: string;
  onImported?: () => void;
  compact?: boolean;
}) {
  const { message } = App.useApp();
  const [importing, setImporting] = useState(false);
  if (!isAppCardPayloadText(sourceText)) return null;

  const handleImport = async () => {
    const payload = extractAppCardPayload(sourceText, workspaceId);
    if (!payload) return;
    setImporting(true);
    message.open({ key: `appcard-import-${workspaceId}-${payload.name}`, type: 'loading', content: '正在导入为场景空间子应用…', duration: 0 });
    const [err] = await apiInterceptors(createAppCard(payload));
    setImporting(false);
    if (err) {
      message.open({ key: `appcard-import-${workspaceId}-${payload.name}`, type: 'error', content: (err as Error).message || '导入失败' });
      return;
    }
    message.open({ key: `appcard-import-${workspaceId}-${payload.name}`, type: 'success', content: `已导入子应用「${payload.name}」` });
    ee.emit(EVENTS.APP_CARD_CHANGED, { workspaceId });
    onImported?.();
  };

  return (
    <Button
      type="primary"
      size={compact ? 'small' : 'middle'}
      ghost
      icon={<UploadOutlined />}
      loading={importing}
      onClick={handleImport}
    >
      导入为场景空间子应用
    </Button>
  );
}