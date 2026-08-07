import type { DockFrame, DockWidget } from './dock-types';

/**
 * 增量合并 dock 帧：按 `widget.id` + `kind` 合并到现有 widget map。
 *
 * - `replace`：整体覆盖该 id 的 widget。
 * - `patch`：与现有 payload 深合并（用于交互回写等局部更新）。
 * - `remove`：从 map 删除该 id（清理 / 新开会话时 widget 消失）。
 *
 * SSE onDock 与轮询 onPoll 共用此函数，两条链路只有一份合并逻辑。
 */
export function applyDockFrame(
  prev: Record<string, DockWidget>,
  frame?: DockFrame | null,
): Record<string, DockWidget> {
  if (!frame || !frame.widgets || frame.widgets.length === 0) {
    return prev;
  }
  const next = { ...prev };
  for (const w of frame.widgets) {
    if (!w || !w.id) continue;
    const kind = w.kind || 'replace';
    if (kind === 'remove') {
      delete next[w.id];
    } else if (kind === 'patch') {
      const existing = next[w.id];
      next[w.id] = existing
        ? {
            ...existing,
            type: w.type || existing.type,
            payload: { ...existing.payload, ...(w.payload || {}) },
          }
        : { ...w, kind: 'replace', payload: w.payload || {} };
    } else {
      next[w.id] = { ...w, payload: w.payload || {} };
    }
  }
  return next;
}