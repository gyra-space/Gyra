'use client';

import { apiInterceptors, getWorkspaceInfo, listMembers } from '@/client/api';
import { getUserId } from '@/utils';
import { Button, Card, Empty, Spin } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { CapabilityTab } from '../assets/capability-tab';
import '../assets/assets.css';

/**
 * 能力页:主 Agent 会"干"什么 —— 技能 / MCP / 子智能体 / 专属模型。
 * 与资产页分离:ECP 语义资产与降级数据资源留在「资产」,这里专管能力注入。
 */
export default function CapabilityPage() {
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const { t } = useTranslation();

  const { data: ws, loading: wsLoading } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  // 权限整合:空间管理员 owner(管理)才可维护能力,成员仅可查看/使用。
  const { data: myRole } = useRequest(async () => {
    if (!ws?.id) return '';
    const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
    if (err) return '';
    const list = Array.isArray(res) ? res : ((res as any)?.data || []);
    const me = list.find((m: any) => String(m.user_id) === String(getUserId()));
    return me?.role || '';
  }, { refreshDeps: [ws?.id] });
  const canManage = myRole === 'owner';

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
              <RobotOutlined />
            </div>
            <div>
              <p className="ws-page-eyebrow">
                {ws.name}
                <span className="ws-page-eyebrow-code">{ws.workspace_code}</span>
              </p>
              <h1 className="ws-page-title">{t('capability.title_page') || '能力'}</h1>
              <p className="ws-page-subtitle">
                {t('capability.subtitle') || '主 Agent 会"干"什么 —— 技能 / MCP / 子智能体 / 专属模型,按需注入给空间内的 Agent。'}
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
          <CapabilityTab workspaceId={ws.id} workspaceCode={ws.workspace_code} canManage={canManage} />
        </Card>
      </div>
    </div>
  );
}