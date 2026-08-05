'use client';

import { apiInterceptors, getWorkspaceInfo, listMembers } from '@/client/api';
import { getUserId } from '@/utils';
import { Button, Card, Empty, Spin, Tabs } from 'antd';
import {
  DatabaseOutlined,
  DeploymentUnitOutlined,
  SendOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { DataAssetsTab } from './data-assets-tab';
import { DeliveryPanel } from './delivery-panel';
import { CapabilityTab } from './capability-tab';
import { EcpConsole } from '@/app/ecp/components/ecp-console';

const TAB_KEYS = ['semantic', 'support', 'delivery'] as const;
type TabKey = typeof TAB_KEYS[number];

// 兼容旧 tab 参数:data/capability 合并到 support
const LEGACY_TAB_MAP: Record<string, TabKey> = { data: 'support', capability: 'support' };
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

  // 权限整合:空间管理员(owner/approver)才可维护资源,成员仅可使用/确认待办。
  const { data: myRole } = useRequest(async () => {
    if (!ws?.id) return '';
    const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
    if (err) return '';
    const list = Array.isArray(res) ? res : ((res as any)?.data || []);
    const me = list.find((m: any) => String(m.user_id) === String(getUserId()));
    return me?.role || '';
  }, { refreshDeps: [ws?.id] });
  const canManage = myRole === 'owner' || myRole === 'approver';

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
      // 数据 + 能力聚合:ECP 语义层覆盖不到时,降级关联的原始资源。
      children: (
        <div className="ws-support-wrap">
          <section className="ws-support-section">
            <header className="ws-support-section__head">
              <span className="ws-support-section__icon"><DatabaseOutlined /></span>
              <div>
                <div className="ws-support-section__title">{t('assets.support_data') || '数据资源'}</div>
                <div className="ws-support-section__desc">
                  {t('assets.support_data_desc') || 'ECP 覆盖不到时降级关联:数据库 / 数据集 / 知识库 / 文档。'}
                </div>
              </div>
            </header>
            <DataAssetsTab workspaceId={ws.id} workspaceCode={ws.workspace_code} />
          </section>
          <section className="ws-support-section">
            <header className="ws-support-section__head">
              <span className="ws-support-section__icon"><ToolOutlined /></span>
              <div>
                <div className="ws-support-section__title">{t('assets.support_capability') || '能力资源'}</div>
                <div className="ws-support-section__desc">
                  {t('assets.support_capability_desc') || 'Agent 执行所需的技能 / MCP / 模型 / ECP 语义层注入。'}
                </div>
              </div>
            </header>
            <CapabilityTab workspaceId={ws.id} canManage={canManage} />
          </section>
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
                {t('assets.subtitle') || '以 ECP 语义资产为核心,支撑资源(数据/能力)按需降级关联,交付沉淀为任务产出。'}
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
