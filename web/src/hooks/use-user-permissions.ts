'use client';

import { useCallback, useEffect, useState } from 'react';
import { permissionsService } from '@/services/permissions';
import { getUserId } from '@/utils/storage';
import { authService } from '@/services/auth';

export interface UserPermissions {
  roles: string[];
  /** { resource_type: [action, ...] };null 表示 RBAC 插件关闭(不做限制) */
  permissions: Record<string, string[]> | null;
  /** 资源实例级授权(GET /permissions/me 透出) */
  grants?: Record<string, unknown>[];
}

export function useUserPermissions() {
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [grants, setGrants] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [oauthEnabled, setOauthEnabled] = useState<boolean | null>(null);

  // First check OAuth status
  useEffect(() => {
    authService.getOAuthStatus().then((s) => setOauthEnabled(s.enabled));
  }, []);

  const fetchPermissions = useCallback(async () => {
    // Skip if OAuth is not enabled (no real login)
    if (oauthEnabled === false) {
      setLoading(false);
      return;
    }

    // Wait for OAuth status check
    if (oauthEnabled === null) {
      return;
    }

    // 本地开发无鉴权模式:localStorage 无用户信息时跳过拉取
    if (!getUserId()) {
      setLoading(false);
      return;
    }

    try {
      // /permissions/me 仅需登录(旧 effective-permissions 是管理员专用端点,普通用户 403)
      const data = await permissionsService.getMyPermissions();
      if (data) {
        setPermissions({
          roles: data.roles,
          permissions: data.permissions,
          grants: data.grants,
        });
        setGrants(data.grants ?? []);
      } else {
        setPermissions(null);
        setGrants([]);
      }
    } catch (e) {
      // Silent fail - permissions API might not be available
      console.debug('Failed to fetch user permissions:', e);
    } finally {
      setLoading(false);
    }
  }, [oauthEnabled]);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  const hasPermission = useCallback(
    (resourceType: string, action: string): boolean => {
      // 开发模式豁免:未登录(本地无鉴权模式,localStorage 无用户信息)时放行
      if (!getUserId()) return true;
      // OAuth 未开启(或状态未确定)时后端不做鉴权,前端同步放行
      if (oauthEnabled !== true) return true;
      // 权限未加载到(请求失败等)默认拒绝,避免越权
      if (!permissions) return false;
      // RBAC 插件关闭(permissions 为 null):不做限制
      if (permissions.permissions == null) return true;
      const actions = permissions.permissions[resourceType] || [];
      if (actions.includes('*') || actions.includes(action)) return true;
      // 资源授权(resource_grant):permission_key 形如 "model.read"。
      // 模块级授权(resource_id='*')亮起菜单;实例级授权不亮菜单(与角色
      // scoped 权限口径一致,避免"仅授权单个实例"泄漏成全模块入口);
      // 已过期的 grant 不放行
      const now = Date.now();
      return (permissions.grants ?? []).some((g) => {
        const grant = g as {
          permission_key?: string;
          resource_id?: string | null;
          expires_at?: string | null;
        };
        return (
          grant.permission_key === `${resourceType}.${action}` &&
          (grant.resource_id == null || grant.resource_id === '*') &&
          (!grant.expires_at || new Date(grant.expires_at).getTime() > now)
        );
      });
    },
    [permissions, oauthEnabled]
  );

  const hasResourceRead = useCallback(
    (resourceType: string): boolean => {
      return hasPermission(resourceType, 'read');
    },
    [hasPermission]
  );

  return {
    permissions,
    grants,
    loading,
    hasPermission,
    hasResourceRead,
    refresh: fetchPermissions,
  };
}
