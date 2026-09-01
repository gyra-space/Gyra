'use client';

import React, { useCallback, useEffect, useState } from 'react';
import FilePreviewModal, {
  type PreviewFilePayload,
} from '@/components/chat/chat-content-components/VisComponents/FilePreviewModal';
import { transformFileUrl } from '@/utils';

export type { PreviewFilePayload } from '@/components/chat/chat-content-components/VisComponents/FilePreviewModal';

/**
 * 附件预览 —— 三份输入框实现（unified / home / agent-workspace）+ 消息流共用。
 *
 * 背景：三处输入框各自维护一份上传中(uploading)与已上传(resources)附件列表，结构略有差异；
 * 消息流里的用户附件又是一套。这里统一归一化成 FilePreviewModal 能吃的 payload。
 *
 * 形态上采用「模块级广播 + 全局宿主」而不是每个调用点各自挂一个 Modal：
 * 消息流每条消息都是一个组件实例，逐个挂 Modal 会有几十上百个实例开销。
 * 宿主 <AttachmentPreviewHost /> 在 app/layout.tsx 挂载一次即可。
 */

const IMAGE_RE = /\.(jpg|jpeg|png|gif|bmp|webp|svg|avif|heic|ico)$/i;

/**
 * 归一化「已上传资源」→ 预览 payload。
 * 兼容三种形态：
 *   { type: 'image_url', image_url: { url, preview_url, file_name } }  (unified / home / workspace)
 *   { type: 'file_url' | 'audio_url' | 'video_url', ... }
 *   { file_name, file_path, url, preview_url }                          (旧格式)
 */
export function normalizeResourceItem(item: unknown): PreviewFilePayload | null {
  if (!item || typeof item !== 'object') return null;
  const raw = item as Record<string, unknown>;
  const asString = (v: unknown): string => (typeof v === 'string' ? v : '');

  let name = '';
  let url = '';

  const nested =
    (raw.type === 'image_url' && raw.image_url) ||
    (raw.type === 'file_url' && raw.file_url) ||
    (raw.type === 'audio_url' && raw.audio_url) ||
    (raw.type === 'video_url' && raw.video_url) ||
    raw.image_url ||
    raw.file_url ||
    raw.audio_url ||
    raw.video_url ||
    null;

  if (nested && typeof nested === 'object') {
    const n = nested as Record<string, unknown>;
    name = asString(n.file_name) || asString(n.name);
    url = asString(n.preview_url) || asString(n.url);
  } else {
    name = asString(raw.file_name) || asString(raw.name);
    url = asString(raw.preview_url) || asString(raw.url) || asString(raw.file_path);
  }

  if (!name && !url) return null;

  const finalUrl = url ? transformFileUrl(url) : '';
  const mimeType = asString(raw.mime_type) || (IMAGE_RE.test(name) ? 'image/*' : undefined);

  return {
    file_name: name || '未命名文件',
    url: finalUrl || undefined,
    mime_type: mimeType || undefined,
    file_size: typeof raw.file_size === 'number' ? raw.file_size : undefined,
  };
}

/** 归一化「上传中的本地文件」→ 预览 payload（带 File，预览时走 objectURL） */
export function normalizeUploadingFile(file: File): PreviewFilePayload | null {
  if (!file) return null;
  return {
    file_name: file.name,
    local_file: file,
    mime_type: file.type || undefined,
    file_size: file.size,
  };
}

/** 从任意文件名 + URL 直接构造 payload（消息流历史附件场景） */
export function makePreviewPayload(
  name: string,
  url: string,
  extra?: { mimeType?: string; size?: number }
): PreviewFilePayload {
  return {
    file_name: name || '未命名文件',
    url: url ? transformFileUrl(url) : undefined,
    mime_type: extra?.mimeType,
    file_size: extra?.size,
  };
}

/* ------------------------------------------------------------------ *
 * 全局预览宿主
 * ------------------------------------------------------------------ */

type PreviewListener = (payload: PreviewFilePayload) => void;

const listeners = new Set<PreviewListener>();

/** 任意位置调用即可打开附件预览弹窗 */
export function openAttachmentPreview(payload: PreviewFilePayload | null): void {
  if (!payload) return;
  listeners.forEach((listener) => listener(payload));
}

/**
 * 预览弹窗宿主，全局挂载一次（见 app/layout.tsx）。
 */
export function AttachmentPreviewHost() {
  const [payload, setPayload] = useState<PreviewFilePayload | null>(null);

  useEffect(() => {
    const listener: PreviewListener = (next) => setPayload(next);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return (
    <FilePreviewModal
      visible={!!payload}
      file={payload}
      onClose={() => setPayload(null)}
    />
  );
}

/* ------------------------------------------------------------------ *
 * 本地文件缩略图
 * ------------------------------------------------------------------ */

/**
 * 为本地 File 创建 objectURL 并在卸载/切换时释放。
 * 三处输入框此前都是把 `URL.createObjectURL(file)` 内联写进 <img src>，
 * 每次 render 都新建一个且从不 revoke —— 这里统一收敛掉泄漏。
 */
export function useObjectUrl(file?: File | null): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
      setUrl(null);
    };
  }, [file]);

  return url;
}

/** 本地文件缩略图，内部用 useObjectUrl 管理生命周期 */
export const LocalFileThumb: React.FC<{
  file: File;
  className?: string;
  alt?: string;
}> = ({ file, className, alt }) => {
  const url = useObjectUrl(file);
  if (!url) return null;
  return <img src={url} alt={alt || file.name} className={className} />;
};

/**
 * 输入框内便捷入口：把归一化函数与广播函数打包，省去逐处 import 两个函数。
 */
export function useAttachmentPreview() {
  const openResource = useCallback(
    (item: unknown) => openAttachmentPreview(normalizeResourceItem(item)),
    []
  );
  const openLocalFile = useCallback(
    (file: File) => openAttachmentPreview(normalizeUploadingFile(file)),
    []
  );
  return { openResource, openLocalFile };
}
