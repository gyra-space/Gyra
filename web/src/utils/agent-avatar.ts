/**
 * 统一的 Agent 头像工具函数。
 *
 * 所有 Agent 身份展示位置共用这套逻辑，保证「上传了就用图片，没上传就显示首字母头像」的
 * 全链路一致体验，避免各处各自为政的默认头像。
 */

import { transformFileUrl } from './index';

/** 无头像时的背景色板（由名称哈希稳定取色） */
export const AVATAR_COLORS = [
  '#4f46e5',
  '#00b96b',
  '#722ed1',
  '#eb2f96',
  '#fa8c16',
  '#13c2c2',
  '#2f54eb',
  '#52c41a',
  '#f5222d',
  '#faad14',
  '#9254de',
  '#08979c',
];

/** 历史上被当作“默认/占位”的头像值，命中即视为未上传，回退到首字母头像。 */
const DEFAULT_AVATAR_VALUES: string[] = [
  'smart-plugin',
  '/agents/default_avatar.png',
  '/agents/chat_avatar_default.png',
  '/agents/robot.png',
  '/agents/agent_default.svg',
  '/icons/colorful-plugin.png',
];

function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

/** 按名称稳定取头像底色 */
export function getAvatarColor(name: string): string {
  return AVATAR_COLORS[hashCode(name || '') % AVATAR_COLORS.length];
}

/** 取名称首字符：CJK 直接取首字，ASCII 转大写 */
export function getInitial(name: string): string {
  if (!name) return '?';
  const trimmed = name.trim();
  const first = trimmed[0];
  if (!first) return '?';
  if (first.charCodeAt(0) > 0x4e00) {
    return first;
  }
  return first.toUpperCase();
}

/** 判断 icon 是否可视为“未上传”（空、magic 值或历史默认占位图） */
export function isDefaultAvatar(icon?: string | null): boolean {
  const raw = (icon || '').trim();
  if (!raw) return true;
  return DEFAULT_AVATAR_VALUES.some((v) => raw === v || raw.endsWith(v));
}

/** 将 icon 解析为可渲染的图片地址（兼容 gyra-fs:// 与历史 http 地址） */
export function resolveAvatarUrl(icon?: string | null): string {
  const raw = (icon || '').trim();
  if (!raw || isDefaultAvatar(raw)) return '';
  return transformFileUrl(raw);
}