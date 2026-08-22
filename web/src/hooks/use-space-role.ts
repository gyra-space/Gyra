'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiInterceptors, listMembers } from '@/client/api';
import { getUserId } from '@/utils/storage';

/** 场景空间内置三角色(与后端 permissions/modules/space.py 的 seed 矩阵对齐) */
export type SpaceRole = 'owner' | 'contributor' | 'viewer';

/**
 * 内置空间角色 -> space.* 权限键矩阵。
 * owner(space.admin)全量;contributor(space.member)可对话/发起任务/看产出;
 * viewer(space.viewer)纯只读。 '*' 表示全部权限。
 */
export const SPACE_ROLE_PERMISSIONS: Record<SpaceRole, string[] | '*'> = {
  owner: '*',
  contributor: [
    'space.workspace.view',
    'space.chat.use',
    'space.task.view',
    'space.task.start',
    'space.file.read',
    'space.asset.view',
    'space.capability.view',
    'space.playbook.view',
  ],
  viewer: [
    'space.workspace.view',
    'space.task.view',
    'space.file.read',
    'space.asset.view',
    'space.capability.view',
    'space.playbook.view',
  ],
};

/** 按矩阵判定角色是否持有权限键;角色未知(null)时一律拒绝 */
export function spaceRoleCan(role: SpaceRole | null, permKey: string): boolean {
  if (!role) return false;
  const perms = SPACE_ROLE_PERMISSIONS[role];
  return perms === '*' || perms.includes(permKey);
}

/** 同一空间的成员列表请求缓存(去重:多个组件同时挂载只发一次) */
const rolePromiseCache = new Map<number, Promise<SpaceRole | null>>();

async function fetchSpaceRole(workspaceId: number): Promise<SpaceRole | null> {
  const [err, res] = await apiInterceptors(listMembers({ workspace_id: workspaceId }));
  if (err) return null;
  const list = Array.isArray(res) ? res : ((res as any)?.data || []);
  const me = list.find((m: any) => String(m.user_id) === String(getUserId()));
  return (me?.role as SpaceRole) ?? null;
}

/**
 * 当前用户在指定空间的角色 + 权限判定。
 * 返回 { role, loading, can };can(permKey) 在角色未加载/非成员时返回 false。
 */
export function useSpaceRole(workspaceId?: number | null) {
  const [role, setRole] = useState<SpaceRole | null>(null);
  const [loading, setLoading] = useState<boolean>(!!workspaceId);

  useEffect(() => {
    if (!workspaceId) {
      setRole(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const cached = rolePromiseCache.get(workspaceId);
    const promise = cached ?? fetchSpaceRole(workspaceId);
    rolePromiseCache.set(workspaceId, promise);
    promise
      .then((r) => {
        if (!cancelled) setRole(r);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  const can = useCallback(
    (permKey: string) => spaceRoleCan(role, permKey),
    [role],
  );

  return { role, loading, can };
}
