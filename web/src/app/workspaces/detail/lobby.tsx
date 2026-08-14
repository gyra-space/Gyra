'use client';

import { useRequest } from 'ahooks';
import { useEffect, useRef, useState } from 'react';
import { CloudServerOutlined, SendOutlined, DeploymentUnitOutlined, InboxOutlined, RightOutlined } from '@ant-design/icons';
import { apiInterceptors } from '@/client/api';
import { getWorkspaceOverview } from '@/client/api/workspace';
import { ObjectDetailDrawer } from '@/app/ecp/components/common';
import { GrowthCard } from './growth-card';
import { SpaceGuideCard } from './space-guide-card';
import './lobby.css';

export interface LobbyProps {
  workspaceId: number;
  workspaceCode: string;
  /** 任务/介入刷新信号:列表变化时最近产出/交付/待办同步刷新 */
  refreshKey?: number;
  // 预留钩子:内容区域(大厅)开任务入口,待办卡片移除后待后续接 UI。
  onSelectTask?: (taskId: number) => void;
  onSelectArtifact?: (artifact: any) => void;
  onSelectDelivery?: (delivery: any) => void;
  /** 进入飞轮工作台 */
  onEnterFlywheel?: () => void;
  /** 导览卡动作(壳内切换,不整页跳转) */
  onGuide?: (action: 'ask' | 'run_playbook' | 'triggers' | 'data_assets') => void;
  /** 待办点击(与 rail 收件箱一致) */
  onSelectInbox?: (item: any) => void;
  /** 推荐问题:填入输入框并聚焦 */
  onAsk?: (text?: string) => void;
  /** 剧本快捷执行:@引用 带入输入框并聚焦 */
  onRunPlaybook?: (pb: { playbook_id: number; playbook_name: string }) => void;
}

const INBOX_SOURCE_LABEL: Record<string, string> = {
  task: '任务',
  intervention: '介入',
  ecp_proposal: '提案',
  manual: '手动',
};

function SectionHead({
  icon,
  title,
  count,
  sub,
}: {
  icon: React.ReactNode;
  title: string;
  count?: number;
  sub?: string;
}) {
  return (
    <div className="ws-lobby__section-head">
      <span className="ws-lobby__section-icon">{icon}</span>
      <span className="ws-lobby__section-title">{title}</span>
      {typeof count === 'number' && <span className="ws-lobby__section-count">{count}</span>}
      {sub && <span className="ws-lobby__section-sub">{sub}</span>}
    </div>
  );
}

function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="ws-lobby__empty">
      <div className="ws-lobby__empty-title">{title}</div>
      {hint && <div className="ws-lobby__empty-hint">{hint}</div>}
    </div>
  );
}

function fmtSize(bytes: number): string {
  if (!bytes) return '';
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export function Lobby({
  workspaceId,
  workspaceCode,
  refreshKey,
  onSelectArtifact,
  onSelectDelivery,
  onEnterFlywheel,
  onGuide,
  onSelectInbox,
  onAsk,
  onRunPlaybook,
}: LobbyProps) {
  // 空间首屏聚合:一次请求返回 交付/产出/待办/资源/剧本/触发/语义/成长,消灭多请求与数字跳变
  const { data: overview, loading: overviewLoading } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getWorkspaceOverview(workspaceId));
      if (err) return null;
      return res || null;
    },
    { refreshDeps: [workspaceId, refreshKey] },
  );

  const deliveries = overview?.deliveries ?? [];
  const artifacts = overview?.artifacts ?? [];
  const resources = overview?.resources ?? [];
  const playbooks = overview?.playbooks ?? [];
  const triggers = overview?.triggers ?? [];
  const pendingInbox = (overview?.inbox ?? []).filter((i: any) => i.inbox_status !== 'done');
  const semantics = overview?.semantics ?? [];

  // 语义资产详情抽屉:点击语义卡片打开(复用 ECP 控制台的对象详情视图)
  const [selectedSemantic, setSelectedSemantic] = useState<any>(null);

  const recentDeliveries = (deliveries || []).slice(0, 3);
  const recentArtifacts = (artifacts || []).slice(0, 4);
  const recentSemantics = semantics.slice(0, 5);

  // 今日待办:默认只展示前 5 条,点击"查看全部"展开为限高内滚列表,避免撑高首屏
  const INBOX_PREVIEW_COUNT = 5;
  const [inboxExpanded, setInboxExpanded] = useState(false);
  const visibleInbox = inboxExpanded ? pendingInbox : pendingInbox.slice(0, INBOX_PREVIEW_COUNT);

  // 空间动态:右侧还有内容时给轨道加渐隐提示(滚到底后消失)
  const feedTrackRef = useRef<HTMLDivElement>(null);
  const [feedHasMore, setFeedHasMore] = useState(false);
  useEffect(() => {
    const el = feedTrackRef.current;
    if (!el) {
      setFeedHasMore(false);
      return;
    }
    const check = () => setFeedHasMore(el.scrollWidth - el.clientWidth - el.scrollLeft > 2);
    check();
    el.addEventListener('scroll', check);
    window.addEventListener('resize', check);
    return () => {
      el.removeEventListener('scroll', check);
      window.removeEventListener('resize', check);
    };
  }, [recentArtifacts.length, recentDeliveries.length, recentSemantics.length]);

  return (
    <div className="ws-lobby">
      <div className="ws-lobby__scroll">
        {/* 空间问候条 + 开始工作区(推荐问题/可跑剧本,让用户不用想"问什么") */}
        <SpaceGuideCard
          workspaceId={workspaceId}
          workspaceCode={workspaceCode}
          pendingCount={pendingInbox.length}
          semanticNames={semantics.slice(0, 3).map((s: any) => s.name || s.id)}
          workspace={overview?.workspace}
          resources={resources}
          playbooks={playbooks}
          triggers={triggers}
          loading={overviewLoading}
          onGuide={onGuide}
          onAsk={onAsk}
          onRunPlaybook={onRunPlaybook}
        />

        {/* 今日待办:每天进空间的第一站,与 rail 收件箱同数据同视觉 */}
        <section className="ws-lobby__inbox">
          <div className="ws-lobby__section-head">
            <span className="ws-lobby__section-icon"><InboxOutlined /></span>
            <span className="ws-lobby__section-title">今日待办</span>
            {pendingInbox.length > 0 && (
              <span className="ws-lobby__section-count">{pendingInbox.length}</span>
            )}
            <span className="ws-lobby__section-sub">
              {pendingInbox.length > 0 ? '需要你介入的事项' : '待办已清零'}
            </span>
          </div>
          {pendingInbox.length === 0 ? (
            <div className="ws-lobby__inbox-empty">
              <div className="ws-lobby__empty-title">暂无待办</div>
              <div className="ws-lobby__empty-hint">没有需要你介入的事项。可以跑一个剧本,或上传数据让 Agent 干活。</div>
            </div>
          ) : (
            <>
              <div className={`ws-lobby__inbox-list${inboxExpanded ? ' ws-lobby__inbox-list--expanded' : ''}`}>
                {visibleInbox.map((item: any) => (
                  <div
                    key={item.id}
                    className="ws-lobby__inbox-item"
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectInbox?.(item)}
                    onKeyDown={(e) => { if (e.key === 'Enter') onSelectInbox?.(item); }}
                  >
                    <span className="ws-lobby__inbox-dot" />
                    <span className="ws-lobby__inbox-chip">{INBOX_SOURCE_LABEL[item.source_type] || item.source_type}</span>
                    <span className="ws-lobby__inbox-title">{item.title}</span>
                    <span className="ws-lobby__inbox-hint">点击处理</span>
                    <RightOutlined className="ws-lobby__inbox-arrow" />
                  </div>
                ))}
              </div>
              {pendingInbox.length > INBOX_PREVIEW_COUNT && (
                <div
                  className="ws-lobby__inbox-more"
                  role="button"
                  tabIndex={0}
                  onClick={() => setInboxExpanded((e) => !e)}
                  onKeyDown={(e) => { if (e.key === 'Enter') setInboxExpanded((v) => !v); }}
                >
                  {inboxExpanded ? '收起' : `查看全部 ${pendingInbox.length} 条`}
                </div>
              )}
            </>
          )}
        </section>

        {/* 空间动态:产出 / 交付 / 语义 横向一条,点击开预览 */}
        <section className="ws-lobby__feed">
          <SectionHead icon={<CloudServerOutlined />} title="空间动态" sub="产出 · 交付 · 语义" />
          {recentArtifacts.length === 0 && recentDeliveries.length === 0 && recentSemantics.length === 0 ? (
            <div className="ws-lobby__feed-empty">
              <EmptyState
                title="暂无动态"
                hint="任务产出的报告、交付记录和已确认的语义会出现在这里"
              />
            </div>
          ) : (
            <div
              ref={feedTrackRef}
              className={`ws-lobby__feed-track${feedHasMore ? ' ws-lobby__feed-track--more' : ''}`}
            >
              {recentArtifacts.map((a: any) => (
                <div
                  key={`a${a.id}`}
                  className="ws-lobby__feed-card"
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectArtifact?.(a)}
                  onKeyDown={(e) => { if (e.key === 'Enter') onSelectArtifact?.(a); }}
                >
                  <span className="ws-lobby__feed-icon ws-lobby__feed-icon--art"><CloudServerOutlined /></span>
                  <span className="ws-lobby__feed-name">{a.title || `artifact_${a.id}`}</span>
                  <span className="ws-lobby__feed-meta">{a.type}{a.provenance?.file_size ? ` · ${fmtSize(a.provenance.file_size)}` : ''}</span>
                </div>
              ))}
              {recentDeliveries.map((d: any) => (
                <div
                  key={`d${d.id}`}
                  className="ws-lobby__feed-card"
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectDelivery?.(d)}
                  onKeyDown={(e) => { if (e.key === 'Enter') onSelectDelivery?.(d); }}
                >
                  <span className="ws-lobby__feed-icon ws-lobby__feed-icon--del"><SendOutlined /></span>
                  <span className="ws-lobby__feed-name">{d.title || `delivery_${d.id}`}</span>
                  <span className="ws-lobby__feed-meta">{d.category || ''}{d.status ? ` · ${d.status}` : ''}</span>
                </div>
              ))}
              {recentSemantics.map((s: any) => (
                <div
                  key={`s${s.id}`}
                  className="ws-lobby__feed-card"
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedSemantic(s)}
                  onKeyDown={(e) => { if (e.key === 'Enter') setSelectedSemantic(s); }}
                >
                  <span className="ws-lobby__feed-icon ws-lobby__feed-icon--sem"><DeploymentUnitOutlined /></span>
                  <span className="ws-lobby__feed-name">{s.name || s.id}</span>
                  <span className="ws-lobby__feed-meta">{s.obj_type || '语义'}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 成长概览(收敛为一行,保留飞轮入口) */}
        <GrowthCard
          workspaceId={workspaceId}
          workspaceCode={workspaceCode}
          growth={overview?.growth}
          ecpConfirmedCount={overview?.ecp_confirmed_count}
          ecpPendingCount={overview?.ecp_pending_count}
          onEnterFlywheel={onEnterFlywheel}
        />
      </div>
      <ObjectDetailDrawer
        obj={selectedSemantic}
        open={!!selectedSemantic}
        onClose={() => setSelectedSemantic(null)}
      />
    </div>
  );
}
