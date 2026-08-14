'use client';

import { apiInterceptors, getWorkspaceInfo, listMembers, listResources } from '@/client/api';
import { getUserId } from '@/utils';
import { Button, Card, Collapse, Empty, Spin, Tabs } from 'antd';
import {
  DatabaseOutlined,
  DeploymentUnitOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { DataAssetsTab } from './data-assets-tab';
import { CapabilityTab } from './capability-tab';
import { DeliveryPanel } from './delivery-panel';
import { EcpConsole } from '@/app/ecp/components/ecp-console';
import { listEcpAssets } from '@/client/api/ecp';

const TAB_KEYS = ['semantic', 'support', 'delivery'] as const;
type TabKey = typeof TAB_KEYS[number];

// 兼容旧 tab 参数:data 合并到 support(能力已独立为 /capability 页)
const LEGACY_TAB_MAP: Record<string, TabKey> = { data: 'support' };
const resolveTab = (raw: string | null | undefined): TabKey => {
  if (raw && (TAB_KEYS as readonly string[]).includes(raw)) return raw as TabKey;
  if (raw && LEGACY_TAB_MAP[raw]) return LEGACY_TAB_MAP[raw];
  return 'semantic';
};

/**
 * 资产页:ECP 语义资产为核心(默认第一 tab),支撑资源(数据/能力)为降级补充,交付沉淀为任务产出。
 * 设计动线:进空间 → ECP 直接可用 → 语义层覆盖不到时在「支撑资源」补数据/能力。
 */
export default function AssetsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const workspaceCode = searchParams?.get('id') || '';
  const tabParam = searchParams?.get('tab');
  const activeTab = resolveTab(tabParam);
  const { t } = useTranslation();

  const { data: ws, loading: wsLoading } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  // 权限整合:空间管理员 owner(管理)才可维护资源,成员仅可使用/确认待办。
  const { data: myRole } = useRequest(async () => {
    if (!ws?.id) return '';
    const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
    if (err) return '';
    const list = Array.isArray(res) ? res : ((res as any)?.data || []);
    const me = list.find((m: any) => String(m.user_id) === String(getUserId()));
    return me?.role || '';
  }, { refreshDeps: [ws?.id] });
  const canManage = myRole === 'owner';

  // 支撑资源分区折叠:资源数量加载完成后,空分区自动收起,避免整块空白。
  // 数据分区若有 ECP 入驻资产(含待接入)也保持展开,避免把 ECP 关联藏起来。
  const { data: supportRows, loading: supportLoading } = useRequest(async () => {
    if (!ws?.id) return [];
    const [err, res] = await apiInterceptors(listResources({ workspace_id: ws.id }));
    return err ? [] : res || [];
  }, { refreshDeps: [ws?.id] });
  const ecpWsId = ws?.workspace_code ? `ecp_${ws.workspace_code}` : null;
  const { data: ecpAssets, loading: ecpLoading } = useRequest(async () => {
    if (!ecpWsId) return [];
    const [err, res] = await apiInterceptors(listEcpAssets({ workspace_id: ecpWsId }));
    return err ? [] : res ?? [];
  }, { ready: !!ecpWsId, refreshDeps: [ecpWsId] });
  const hasDataAssets = useMemo(
    () => (supportRows || []).some((r: any) =>
      ['data_source', 'knowledge_space', 'environment'].includes(r.type)) ||
      (ecpAssets || []).length > 0,
    [supportRows, ecpAssets],
  );
  const hasCapabilities = useMemo(
    () => (supportRows || []).some((r: any) =>
      ['skill', 'mcp', 'app'].includes(r.type)),
    [supportRows],
  );
  const [openKeys, setOpenKeys] = useState<string[]>(['data', 'cap']);
  const [autoCollapsed, setAutoCollapsed] = useState(false);
  useEffect(() => {
    if (wsLoading || supportLoading || ecpLoading || autoCollapsed) return;
    setOpenKeys(['data', 'cap'].filter((k) => (k === 'data' ? hasDataAssets : hasCapabilities)));
    setAutoCollapsed(true);
  }, [wsLoading, supportLoading, ecpLoading, hasDataAssets, hasCapabilities, autoCollapsed]);

  const handleTabChange = (key: string) => {
    router.replace(`${pathname}?id=${workspaceCode}&tab=${key}`);
  };

  if (wsLoading || !searchParams) {
    return (
      <div className="flex justify-center py-20">
        <Spin size="large" />
      </div>
    );
  }

  if (!ws) {
    return (
      <div className="p-6">
        <Empty description="Workspace not found" />
      </div>
    );
  }

  const tabs = [
    {
      key: 'semantic',
      label: (
        <span>
          <DeploymentUnitOutlined style={{ marginRight: 6 }} />
          {t('assets.tab_semantic') || '语义资产'}
          <span className="ws-tab-tag-core">核心</span>
        </span>
      ),
      // 直接复用 ECP 控制台内容组件(无 hero/空间选择器/全局外壳),
      // 语义空间固定为本空间派生的 ecp_<code>
      children: <EcpConsole workspaceId={`ecp_${workspaceCode}`} />,
    },
    {
      key: 'support',
      label: (
        <span>
          <DatabaseOutlined style={{ marginRight: 6 }} />
          {t('assets.tab_support') || '支撑资源'}
        </span>
      ),
      // 支撑资源:ECP 语义层覆盖不到时,降级关联的数据(数据库/数据集/知识库/环境)
      // 与能力(技能/MCP/子智能体/专属模型)——"空间 = 注册/治理池"的统一货架。
      // 分区可折叠,空分区默认收起避免大片空白。
      children: (
        <div className="ws-support-wrap">
          <Collapse
            ghost
            className="ws-support-collapse"
            activeKey={openKeys}
            onChange={(keys) => setOpenKeys(keys as string[])}
            items={[
              {
                key: 'data',
                label: (
                  <header className="ws-support-section__head">
                    <span className="ws-support-section__icon"><DatabaseOutlined /></span>
                    <div>
                      <div className="ws-support-section__title">{t('assets.support_data') || '数据资源'}</div>
                      <div className="ws-support-section__desc">
                        {t('assets.support_data_desc') || 'ECP 覆盖不到时降级关联:数据库 / 数据集 / 知识库 / 环境。'}
                      </div>
                    </div>
                  </header>
                ),
                children: <DataAssetsTab workspaceId={ws.id} workspaceCode={ws.workspace_code} />,
              },
              {
                key: 'cap',
                label: (
                  <header className="ws-support-section__head">
                    <span className="ws-support-section__icon"><RobotOutlined /></span>
                    <div>
                      <div className="ws-support-section__title">{t('assets.support_capability') || '能力'}</div>
                      <div className="ws-support-section__desc">
                        {t('assets.support_capability_desc') || '主 Agent 会"干"什么:技能 / MCP / 子智能体 / 专属模型,按需注入给空间内的 Agent。'}
                      </div>
                    </div>
                  </header>
                ),
                children: <CapabilityTab workspaceId={ws.id} workspaceCode={ws.workspace_code} canManage={canManage} />,
              },
            ]}
          />
        </div>
      ),
    },
    {
      key: 'delivery',
      label: (
        <span>
          <SendOutlined style={{ marginRight: 6 }} />
          {t('assets.tab_delivery') || '交付沉淀'}
        </span>
      ),
      children: <DeliveryPanel workspaceId={ws.id} />,
    },
  ];

  return (
    <div className="ws-page">
      <div className="ws-page-bg" />
      <div className="ws-page-content" style={{ paddingTop: 16, paddingBottom: 48 }}>
        <div className="ws-page-header mb-6">
          <div className="ws-page-header-left">
            <div className="ws-page-icon">
              <DatabaseOutlined />
            </div>
            <div>
              <p className="ws-page-eyebrow">
                {ws.name}
                <span className="ws-page-eyebrow-code">{ws.workspace_code}</span>
              </p>
              <h1 className="ws-page-title">{t('assets.title_page') || '资产'}</h1>
              <p className="ws-page-subtitle">
                {t('assets.subtitle') || '以 ECP 语义资产为核心,支撑资源(数据)按需降级关联,交付沉淀为任务产出。'}
              </p>
            </div>
          </div>
          <div className="ws-page-actions">
            <Link href={`/workspaces/detail?id=${workspaceCode}`}>
              <Button>{t('back') || '返回'}</Button>
            </Link>
          </div>
        </div>

        <Card className="ws-surface">
          <Tabs activeKey={activeTab} onChange={handleTabChange} items={tabs} />
        </Card>
      </div>
    </div>
  );
}
