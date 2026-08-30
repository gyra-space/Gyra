'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, Alert } from 'antd';
import { useTranslation } from 'react-i18next';
import { TeamOutlined, UserOutlined, SafetyCertificateOutlined, KeyOutlined, CheckOutlined } from '@ant-design/icons';
import RoleManagement from '@/components/permissions/RoleManagement';
import UserManagement from '@/components/permissions/UserManagement';
import CustomPermissions from '@/components/permissions/CustomPermissions';
import GroupManagement from '@/components/permissions/GroupManagement';
import ApprovalManagement from '@/components/permissions/ApprovalManagement';
import GrantManagement from '@/components/permissions/GrantManagement';
import { permissionsService, type Role } from '@/services/permissions';
import { useUserPermissions } from '@/hooks/use-user-permissions';

type IdentityTabKey = 'users' | 'groups' | 'roles' | 'approvals';
type PermissionTabKey = 'policies' | 'grants';

export default function PermissionsPage() {
  const { t } = useTranslation();
  const [activeMainTab, setActiveMainTab] = useState<'identity' | 'permission'>('identity');
  const [activeIdentityTab, setActiveIdentityTab] = useState<IdentityTabKey>('users');
  const [activePermissionTab, setActivePermissionTab] = useState<PermissionTabKey>('policies');
  const [roles, setRoles] = useState<Role[]>([]);
  const { hasPermission, loading: permLoading } = useUserPermissions();
  const isAdmin = hasPermission('system', 'admin');

  const loadRoles = useCallback(async () => {
    try {
      const rolesData = await permissionsService.listRoles();
      setRoles(rolesData);
    } catch (e) {
      console.error('Failed to load roles:', e);
    }
  }, []);

  useEffect(() => {
    loadRoles();
  }, [loadRoles]);

  // 身份管理子 Tab(用户/用户组/角色仅管理员可见;审批对全员开放——
  // 普通用户有"我的申请",页面守卫不再整页拦截,后端 fail-closed 兜底)
  const identityItems = [
    ...(isAdmin
      ? [
          {
            key: 'users',
            label: (
              <span>
                <UserOutlined /> {t('permissions_col_user') || '用户'}
              </span>
            ),
            children: <UserManagement roles={roles} />,
          },
          {
            key: 'groups',
            label: (
              <span>
                <TeamOutlined /> {t('permissions_user_groups') || '用户组'}
              </span>
            ),
            children: <GroupManagement roles={roles} />,
          },
          {
            key: 'roles',
            label: (
              <span>
                <SafetyCertificateOutlined /> {t('permissions_role_management') || '角色'}
              </span>
            ),
            children: <RoleManagement roles={roles} onRolesChange={loadRoles} />,
          },
        ]
      : []),
    {
      key: 'approvals',
      label: (
        <span>
          <CheckOutlined /> {t('permissions_approvals') || '审批'}
        </span>
      ),
      children: <ApprovalManagement roles={roles} isAdmin={isAdmin} />,
    },
  ];

  // 权限管理子 Tab(仅管理员)
  const permissionItems = isAdmin
    ? [
        {
          key: 'policies',
          label: (
            <span>
              <KeyOutlined /> {t('permissions_policies') || '策略'}
            </span>
          ),
          children: <CustomPermissions roles={roles} />,
        },
        {
          key: 'grants',
          label: (
            <span>
              <KeyOutlined /> {t('permissions_grants') || '授权'}
            </span>
          ),
          children: <GrantManagement />,
        },
      ]
    : [];

  // 主 Tab(非管理员只留身份管理-审批)
  const mainItems = [
    {
      key: 'identity',
      label: t('permissions_identity_management') || '身份管理',
      children: (
        <Tabs
          activeKey={activeIdentityTab}
          onChange={(key) => setActiveIdentityTab(key as IdentityTabKey)}
          items={identityItems}
        />
      ),
    },
    ...(isAdmin
      ? [
          {
            key: 'permission',
            label: t('permissions_permission_management') || '权限管理',
            children: (
              <Tabs
                activeKey={activePermissionTab}
                onChange={(key) => setActivePermissionTab(key as PermissionTabKey)}
                items={permissionItems}
              />
            ),
          },
        ]
      : []),
  ];

  // 权限快照加载完成后,非管理员默认落到"审批" Tab
  useEffect(() => {
    if (!permLoading && !isAdmin) {
      setActiveIdentityTab('approvals');
      setActiveMainTab('identity');
    }
  }, [permLoading, isAdmin]);

  return (
    <div className="p-6 h-full overflow-auto">
      <Alert
        type="info"
        showIcon
        className="mb-4"
        message={t('permissions_title')}
        description={t('permissions_page_hint') || '基于角色的访问控制：在此统一管理身份与权限。身份管理用于管理用户、用户组和角色；权限管理用于管理策略。'}
      />
      <Tabs
        activeKey={activeMainTab}
        onChange={(key) => setActiveMainTab(key as 'identity' | 'permission')}
        items={mainItems}
      />
    </div>
  );
}