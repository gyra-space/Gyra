'use client';

import { apiInterceptors, getWorkspaceInfo } from '@/client/api';
import { Button, Card, Empty, Spin } from 'antd';
import { DeploymentUnitOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { EcpConsole } from '@/app/ecp/components/ecp-console';
import '../../workspaces.css';

/**
 * 资产页:只承载 ECP 语义资产(ECP 控制台)。
 * 数据资源/能力/交付沉淀已上移到场景空间页头的一级入口,不再作为资产页的 tab。
 */
export default function AssetsPage() {
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const { t } = useTranslation();

  const { data: ws, loading: wsLoading } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

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
            <div className="ws-page-icon">
              <DeploymentUnitOutlined />
            </div>
            <div>
              <p className="ws-page-eyebrow">
                {ws.name}
                <span className="ws-page-eyebrow-code">{ws.workspace_code}</span>
              </p>
              <h1 className="ws-page-title">{t('assets.title_page') || '资产'}</h1>
              <p className="ws-page-subtitle">
                {t('assets.subtitle') || 'ECP 语义资产(核心):空间的语义口径、数据资产与知识资产,统一经 ECP 管理与演进。'}
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
          {/* 资产页只承载 ECP 语义资产控制台,不再分 tab;数据资源/能力/交付
              已上移到场景空间页头的一级入口。 */}
          <EcpConsole workspaceId={`ecp_${workspaceCode}`} />
        </Card>
      </div>
    </div>
  );
}
