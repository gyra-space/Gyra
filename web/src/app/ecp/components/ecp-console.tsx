'use client';

import { useState } from 'react';
import { apiInterceptors } from '@/client/api';
import { getEcpInbox } from '@/client/api/ecp';
import { useRequest } from 'ahooks';

import DataTab from './DataTab';
import GovernanceTab from './GovernanceTab';
import GraphTab from './GraphTab';
import KnowledgeTab from './KnowledgeTab';
import OverviewTab from './OverviewTab';
import SemanticsTab from './SemanticsTab';
import '../ecp.css';

export const VALID_TABS = [
  'overview',
  'semantics',
  'data',
  'knowledge',
  'graph',
  'governance',
] as const;
export type TabKey = (typeof VALID_TABS)[number];

export const TAB_LABELS: Record<TabKey, string> = {
  overview: '总览',
  semantics: '业务口径',
  data: '数据资产',
  knowledge: '知识资产',
  graph: '全景图',
  governance: '治理',
};

export interface EcpConsoleProps {
  workspaceId: string;
  /** 受控 tab(/ecp 整页用 URL 驱动);不传则内部 state(嵌入场景) */
  tab?: TabKey;
  onTabChange?: (key: TabKey) => void;
}

/** ECP 控制台内容区(nav + tab 内容),不含 hero / 空间选择器 / 全局外壳。
 *  /ecp 整页与场景空间资产 tab(语义资产)共用。 */
export function EcpConsole({ workspaceId, tab: controlledTab, onTabChange }: EcpConsoleProps) {
  const [innerTab, setInnerTab] = useState<TabKey>('overview');
  const tab = controlledTab ?? innerTab;
  const setTab = (key: TabKey) => (onTabChange ? onTabChange(key) : setInnerTab(key));

  // nav 收件箱角标(整页 hero 另有完整统计,这里是轻量 page_size=1)
  const { data: inbox } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getEcpInbox({ page_size: 1, workspace_id: workspaceId }),
      );
      return err ? null : res;
    },
    { refreshDeps: [workspaceId] },
  );
  const pendingCount = inbox?.total_count ?? 0;

  return (
    <>
      <nav className="ecp-nav">
        {VALID_TABS.map(key => (
          <span
            key={key}
            className={`ecp-nav__pill ${tab === key ? 'ecp-nav__pill--active' : ''}`}
            onClick={() => setTab(key)}
          >
            {TAB_LABELS[key]}
            {key === 'semantics' && pendingCount > 0 && (
              <span className="ecp-nav__count">{pendingCount}</span>
            )}
          </span>
        ))}
      </nav>

      <div className="ecp-tab-content">
        {tab === 'overview' && (
          <OverviewTab
            onGoSemantics={() => setTab('semantics')}
            onGoGraph={() => setTab('graph')}
            workspaceId={workspaceId}
          />
        )}
        {tab === 'data' && <DataTab workspaceId={workspaceId} />}
        {tab === 'semantics' && <SemanticsTab workspaceId={workspaceId} />}
        {tab === 'knowledge' && <KnowledgeTab workspaceId={workspaceId} />}
        {tab === 'graph' && <GraphTab workspaceId={workspaceId} />}
        {tab === 'governance' && <GovernanceTab workspaceId={workspaceId} />}
      </div>
    </>
  );
}
