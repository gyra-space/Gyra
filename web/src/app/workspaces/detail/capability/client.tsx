'use client';

import { apiInterceptors, getWorkspaceInfo } from '@/client/api';
import { useSpaceRole } from '@/hooks/use-space-role';
import { Button, Empty, Spin } from 'antd';
import { RobotOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useRequest } from 'ahooks';
import { useSearchParams } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { CapabilityTab } from '../assets/capability-tab';
import '../../workspaces.css';

/** 能力页:空间内能力绑定(技能/MCP/子智能体/专属模型,按需注入空间内 Agent)。 */
export default function CapabilityPage() {
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const { t } = useTranslation();

  const { data: ws, loading: wsLoading } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  const { can } = useSpaceRole(ws?.id);
  const canManage = can('space.capability.manage');

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
            <div className="ws-page-icon"><RobotOutlined /></div>
            <div>
              <p className="ws-page-eyebrow">
                {ws.name}
                <span className="ws-page-eyebrow-code">{ws.workspace_code}</span>
              </p>
              <h1 className="ws-page-title">{t('capability.title_page') || '能力'}</h1>
              <p className="ws-page-subtitle">{t('capability.subtitle') || '主 Agent 会"干"什么 —— 技能 / MCP / 子智能体 / 专属模型,按需注入给空间内的 Agent。'}</p>
            </div>
          </div>
          <div className="ws-page-actions">
            <Link href={`/workspaces/detail?id=${workspaceCode}`}>
              <Button icon={<ArrowLeftOutlined />}>{t('back') || 'Back'}</Button>
            </Link>
          </div>
        </div>
        <CapabilityTab workspaceId={ws.id} workspaceCode={ws.workspace_code} canManage={canManage} />
      </div>
    </div>
  );
}
