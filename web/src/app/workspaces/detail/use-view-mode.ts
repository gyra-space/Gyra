'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

export type WorkspaceViewMode = 'simple' | 'ops';

const storageKey = (workspaceId?: number | string) => `ws-view-mode-${workspaceId ?? 'default'}`;

/**
 * 场景空间视图模式:simple(简单使用) / ops(运维管理)。
 * 优先级:URL ?mode= > localStorage(用户手动选择,按空间记忆) > 角色默认 defaultMode。
 * URL 参数命中时同步写入 localStorage,使深链选择也被记忆。
 * defaultMode 由调用方按空间角色计算(管理成员→ops,普通用户→simple),
 * 仅在没有手动记忆/深链时作为初始值生效。
 */
export function useWorkspaceViewMode(
  workspaceId?: number | string,
  defaultMode: WorkspaceViewMode = 'simple',
) {
  const searchParams = useSearchParams();
  const urlMode = searchParams?.get('mode');
  const [mode, setModeState] = useState<WorkspaceViewMode>(defaultMode);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    let next: WorkspaceViewMode = defaultMode;
    try {
      const saved = window.localStorage.getItem(storageKey(workspaceId));
      if (saved === 'simple' || saved === 'ops') next = saved;
    } catch {
      /* localStorage 不可用时保持默认 */
    }
    if (urlMode === 'simple' || urlMode === 'ops') {
      next = urlMode;
      try {
        window.localStorage.setItem(storageKey(workspaceId), urlMode);
      } catch {
        /* ignore */
      }
    }
    setModeState(next);
    setHydrated(true);
    // 依赖 defaultMode:角色权限异步加载完成后,无记忆时按角色默认模式进入
  }, [workspaceId, urlMode, defaultMode]);

  const setMode = useCallback(
    (m: WorkspaceViewMode) => {
      setModeState(m);
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(storageKey(workspaceId), m);
        } catch {
          /* ignore */
        }
      }
    },
    [workspaceId],
  );

  return { mode, setMode, hydrated };
}
