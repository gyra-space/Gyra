'use client';

import { apiInterceptors, getWorkspaceInfo } from '@/client/api';
import { Button, Tabs } from 'antd';
import { BellOutlined, PlusOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useSpaceRole } from '@/hooks/use-space-role';
import TriggersTable from './triggers-table';
import SubscriptionRunsTable from './subscription-runs-table';
import '../../workspaces.css';

export default function SubscriptionsPage() {
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const activeTab = searchParams?.get('tab') === 'runs' ? 'runs' : 'triggers';
  const triggerId = searchParams?.get('trigger_id') || '';
  const { t } = useTranslation();

  const { data: ws } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  // 权限门控:新建订阅需要 space.task.start
  const { can } = useSpaceRole(ws?.id);

  return (
    <div className="ws-page">
      <div className="ws-page-bg" />
      <div className="ws-page-content">
        <div className="ws-page-header">
          <div className="ws-page-header-left">
            <div className="ws-page-icon"><BellOutlined /></div>
            <div>
              <div className="ws-page-eyebrow">
                {t('workspaces.subscriptions') || '订阅'}
              </div>
              <h1 className="ws-page-title">{t('workspaces.subscriptions') || '订阅'}</h1>
              <p className="ws-page-subtitle">
                {t('tasks.subtitle') || '为场景配置订阅:定时 / Webhook / 告警,到点或事件发生时自动按合约创建任务;「执行记录」查看每次触发的运行。'}
              </p>
            </div>
          </div>
          <div className="ws-page-actions">
            <Link href={`/workspaces/detail?id=${workspaceCode}`}>
              <Button icon={<ArrowLeftOutlined />}>{t('back') || 'Back'}</Button>
            </Link>
            {can('space.task.start') && (
              <Link href={`/workspaces/detail/tasks/create?id=${workspaceCode}&type=timer`}>
                <Button type="primary" icon={<PlusOutlined />}>新建订阅</Button>
              </Link>
            )}
          </div>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={(key) => {
            window.history.replaceState(null, '', `/workspaces/detail/tasks?id=${workspaceCode}&tab=${key}`);
          }}
          items={[
            {
              key: 'triggers',
              label: t('subscriptions.tab_rules') || '订阅',
              children: ws?.id ? (
                <div className="ws-table-wrap">
                  <TriggersTable workspaceId={ws.id} workspaceCode={workspaceCode} />
                </div>
              ) : null,
            },
            {
              key: 'runs',
              label: t('subscriptions.tab_runs') || '执行记录',
              children: ws?.id ? (
                <div className="ws-table-wrap">
                  <SubscriptionRunsTable workspaceId={ws.id} workspaceCode={workspaceCode} triggerId={triggerId} />
                </div>
              ) : null,
            },
          ]}
        />
      </div>
    </div>
  );
}
