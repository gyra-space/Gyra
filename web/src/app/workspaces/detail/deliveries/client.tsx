'use client';

import { apiInterceptors, getWorkspaceInfo } from '@/client/api';
import { useSpaceRole } from '@/hooks/use-space-role';
import { Empty, Button, Spin } from 'antd';
import { SendOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useRequest } from 'ahooks';
import { useSearchParams } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { DeliveryPanel } from '../assets/delivery-panel';
import '../../workspaces.css';

/** 交付沉淀页:空间内任务产出物、交付记录与归档输出。 */
export default function DeliveriesPage() {
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const { t } = useTranslation();

  const { data: ws, loading: wsLoading } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  const { can } = useSpaceRole(ws?.id);

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

  return (
    <div className="ws-page">
      <div className="ws-page-bg" />
      <div className="ws-page-content" style={{ paddingTop: 16, paddingBottom: 48 }}>
        <div className="ws-page-header mb-6">
          <div className="ws-page-header-left">
            <div className="ws-page-icon"><SendOutlined /></div>
            <div>
              <p className="ws-page-eyebrow">
                {ws.name}
                <span className="ws-page-eyebrow-code">{ws.workspace_code}</span>
              </p>
              <h1 className="ws-page-title">{t('deliveries.title') || '交付'}</h1>
              <p className="ws-page-subtitle">{t('deliveries.subtitle') || '该空间的产出物、交付记录与归档输出。'}</p>
            </div>
          </div>
          <div className="ws-page-actions">
            <Link href={`/workspaces/detail?id=${workspaceCode}`}>
              <Button icon={<ArrowLeftOutlined />}>{t('back') || 'Back'}</Button>
            </Link>
          </div>
        </div>
        <DeliveryPanel workspaceId={ws.id} />
      </div>
    </div>
  );
}
