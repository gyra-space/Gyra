'use client';

import { useMemo, useState } from 'react';
import { useRequest } from 'ahooks';
import { useRouter, useSearchParams } from 'next/navigation';
import { App, Spin, Modal, Input } from 'antd';
import {
  ArrowLeftOutlined,
  HomeOutlined,
  RocketOutlined,
  ScheduleOutlined,
  BellOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  CheckOutlined,
  MobileOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import {
  apiInterceptors,
  getWorkspaceInfo,
  listTasks,
  listArtifacts,
  listDeliveries,
  listInbox,
  createConversation,
  getCurrentConversation,
  setCurrentConversation,
  linkConversation,
  resolveAndExecuteIntervention,
  updateInboxStatus,
  type InboxItem,
} from '@/client/api';
import { confirmEcpObject } from '@/client/api/ecp';
import { getUserId } from '@/utils/storage';
import { MobileAgentView } from './agent-view';
import MobileProposalDetail from './proposal-detail';
import { PullToRefresh } from '../pull-to-refresh';

const INBOX_SOURCE_LABEL: Record<string, string> = {
  task: '任务',
  intervention: '介入',
  ecp_proposal: '提案',
  manual: '手动',
};

type MobileTab = 'overview' | 'agent' | 'tasks' | 'notifications';

const STATUS_LABEL: Record<string, string> = {
  running: '运行中',
  pending_trigger: '等待触发',
  blocked: '阻塞',
  draft: '准备中',
  awaiting_human: '待介入',
  delivered: '已交付',
  closed: '已关闭',
  failed: '失败',
  done: '已完成',
};

function statusChip(status?: string) {
  const s = status || 'unknown';
  if (s === 'running' || s === 'pending_trigger' || s === 'blocked' || s === 'draft')
    return 'ms-chip--running';
  if (s === 'awaiting_human') return 'ms-chip--awaiting';
  if (s === 'failed') return 'ms-chip--failed';
  return 'ms-chip--done';
}

const TABS: { key: MobileTab; label: string; icon: React.ReactNode }[] = [
  { key: 'overview', label: '概览', icon: <HomeOutlined /> },
  { key: 'agent', label: 'Agent', icon: <RocketOutlined /> },
  { key: 'tasks', label: '任务', icon: <ScheduleOutlined /> },
  { key: 'notifications', label: '通知', icon: <BellOutlined /> },
];

export default function MobileWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const { message } = App.useApp();

  const [tab, setTab] = useState<MobileTab>('overview');
  const [convUid, setConvUid] = useState<string>('');
  const [approveItem, setApproveItem] = useState<InboxItem | null>(null);
  const [proposalItem, setProposalItem] = useState<InboxItem | null>(null);
  const [comment, setComment] = useState('');
  const [acting, setActing] = useState<'approve' | 'reject' | null>(null);

  const { data: ws, loading: wsLoading } = useRequest(
    async () => {
      if (!workspaceCode) return null;
      const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
      return err ? null : res;
    },
    { refreshDeps: [workspaceCode] },
  );

  const workspaceId = ws?.id;
  const appCode = ws?.default_agent_app_code || 'main';

  // 会话:复用桌面空间逻辑(取当前/创建/关联/设为当前)
  useRequest(
    async () => {
      if (!workspaceId) return;
      const [, current] = await apiInterceptors(getCurrentConversation(workspaceId));
      if (current?.conv_uid) {
        setConvUid(current.conv_uid);
        return;
      }
      const [newErr, newConv] = await apiInterceptors(createConversation({}));
      if (newErr || !newConv?.conv_uid) return;
      await apiInterceptors(
        linkConversation({ workspace_id: workspaceId, conv_uid: newConv.conv_uid, user_id: undefined }),
      );
      await apiInterceptors(setCurrentConversation(workspaceId, newConv.conv_uid));
      setConvUid(newConv.conv_uid);
    },
    { ready: !!workspaceId },
  );

  const { data: tasks, refresh: refreshTasks } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [err, res] = await apiInterceptors(listTasks({ workspace_id: workspaceId, limit: 200 }));
      return err ? [] : res || [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { data: artifacts, refresh: refreshArtifacts } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [err, res] = await apiInterceptors(listArtifacts({ workspace_id: workspaceId }));
      return err ? [] : res || [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { data: deliveries, refresh: refreshDeliveries } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [err, res] = await apiInterceptors(listDeliveries({ workspace_id: workspaceId }));
      return err ? [] : res || [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { data: inbox, refresh: refreshInbox } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [err, res] = await apiInterceptors(
        listInbox(workspaceId, { status: 'unread', limit: 100 }),
      );
      return err ? [] : res || [];
    },
    { refreshDeps: [workspaceId] },
  );

  const pullRefresh = () => {
    refreshTasks?.();
    refreshArtifacts?.();
    refreshDeliveries?.();
    refreshInbox?.();
  };

  // 开启新会话:创建新会话并设为当前(历史会话保留,可在桌面端回溯)
  const handleNewSession = async () => {
    if (!workspaceId) return;
    const [err, newConv] = await apiInterceptors(createConversation({ workspace_id: workspaceId }));
    if (err || !newConv?.conv_uid) return;
    await apiInterceptors(
      linkConversation({ workspace_id: workspaceId, conv_uid: newConv.conv_uid, user_id: undefined }),
    );
    await apiInterceptors(setCurrentConversation(workspaceId, newConv.conv_uid));
    setConvUid(newConv.conv_uid);
    message.success('已开启新会话');
  };

  // 介入确认:批准/驳回后由后端继续执行(flywheel 联动)
  const resolveApprove = async (action: 'approved' | 'rejected') => {
    if (!approveItem || !workspaceId || acting) return;
    setActing(action === 'approved' ? 'approve' : 'reject');
    try {
      const uid = Number(getUserId()) || undefined;
      const [err] = await apiInterceptors(
        resolveAndExecuteIntervention(Number(approveItem.source_id), {
          decision: { action, comment: comment.trim() || undefined },
          resolved_by_user_id: uid,
        }),
      );
      if (err) { message.error(err.message); return; }
      message.success(action === 'approved' ? '已批准,Agent 继续执行' : '已驳回');
      setApproveItem(null);
      setComment('');
      refreshInbox?.();
      refreshTasks?.();
    } finally {
      setActing(null);
    }
  };

  // 可一键确认的来源:ecp 提案(源端确认生效)与 manual(标记完成)
  const quickDone = async (item: InboxItem, e?: any) => {
    e?.stopPropagation?.();
    if (!workspaceId) return;
    if (item.source_type === 'ecp_proposal') {
      const m = item.source_id.match(/^(.+):(.+)@v(\d+)$/);
      if (!m) { message.error('提案来源无法解析,请到桌面端处理'); return; }
      const [, ws, objId, ver] = m;
      const [err] = await apiInterceptors(
        confirmEcpObject(objId, Number(ver), {
          user_id: String(getUserId() ?? 'unknown'),
          workspace_id: ws,
        }),
      );
      if (err) { message.error(err.message); return; }
      message.success('已确认生效');
    } else if (item.source_type === 'manual') {
      const [err] = await apiInterceptors(updateInboxStatus(workspaceId, item.id, 'done'));
      if (err) { message.error(err.message); return; }
      message.success('已标记完成');
    }
    refreshInbox?.();
  };

  const hasActive = useMemo(
    () =>
      (tasks || []).some((t: any) =>
        ['running', 'pending_trigger', 'blocked', 'awaiting_human', 'draft'].includes(t?.status),
      ),
    [tasks],
  );

  const runningCount = (tasks || []).filter((t: any) => t?.status === 'running').length;
  const awaitingCount = (tasks || []).filter((t: any) => t?.status === 'awaiting_human').length;
  const unreadCount = (inbox || []).length;

  if (wsLoading) {
    return (
      <div className="ms-app">
        <div className="ms-frame" style={{ alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  if (!ws || !workspaceId) {
    return (
      <div className="ms-app">
        <div className="ms-frame">
          <div className="ms-empty">
            <div className="ms-empty__icon">
              <AppstoreOutlined />
            </div>
            <div className="ms-empty__title">空间不可用</div>
            <p className="ms-empty__hint">可能已被归档或你没有访问权限。</p>
            <button type="button" className="ms-ghost-btn" onClick={() => router.push('/m')}>
              返回空间列表
            </button>
          </div>
        </div>
      </div>
    );
  }

  const scenario = ws.scenario_type || ws.type || 'scenario';

  const renderBody = () => {
    if (tab === 'agent') {
      return (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <MobileAgentView
            convUid={convUid}
            workspaceId={workspaceId}
            appCode={appCode}
            onNewSession={handleNewSession}
          />
        </div>
      );
    }
    if (tab === 'tasks') {
      return (
        <PullToRefresh onRefresh={pullRefresh} className="ms-body">
          {(!tasks || tasks.length === 0) ? (
            <div className="ms-empty">
              <div className="ms-empty__icon"><ScheduleOutlined /></div>
              <div className="ms-empty__title">暂无任务</div>
              <p className="ms-empty__hint">在 Agent 下发起任务，或等待剧本自动触发。</p>
            </div>
          ) : (
            <div className="ms-list">
              {tasks.map((t: any) => (
                <div key={t.id} className="ms-card ms-ws-card">
                  <div className="ms-ws-card__top">
                    <span className={`ms-chip ${statusChip(t.status)}`}>
                      {STATUS_LABEL[t.status] || t.status || '未知'}
                    </span>
                    <span className="ms-ws-card__code">#{t.id}</span>
                  </div>
                  <div className="ms-ws-card__name">{t.title || `任务 #${t.id}`}</div>
                  {t.description && <div className="ms-ws-card__desc">{t.description}</div>}
                </div>
              ))}
            </div>
          )}
        </PullToRefresh>
      );
    }
    if (tab === 'notifications') {
      return (
        <PullToRefresh onRefresh={pullRefresh} className="ms-body">
          {unreadCount === 0 ? (
            <div className="ms-empty">
              <div className="ms-empty__icon"><BellOutlined /></div>
              <div className="ms-empty__title">没有待办通知</div>
              <p className="ms-empty__hint">需要你介入或确认的事项会出现在这里。</p>
            </div>
          ) : (
            <div className="ms-notif">
              {inbox.map((item: InboxItem) => (
                <div
                  key={item.id}
                  className="ms-notif__item ms-notif__item--unread"
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    if (item.source_type === 'intervention') setApproveItem(item);
                    if (item.source_type === 'ecp_proposal') setProposalItem(item);
                  }}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && item.source_type === 'intervention') {
                      e.preventDefault();
                      setApproveItem(item);
                    }
                    if ((e.key === 'Enter' || e.key === ' ') && item.source_type === 'ecp_proposal') {
                      e.preventDefault();
                      setProposalItem(item);
                    }
                  }}
                >
                  <span className="ms-notif__dot" />
                  <div className="ms-notif__main">
                    <div className="ms-notif__title">{item.title}</div>
                    {item.summary && <div className="ms-notif__summary">{item.summary}</div>}
                    <div className="ms-notif__time">
                      {INBOX_SOURCE_LABEL[item.source_type] || item.source_type}
                      {item.source_type === 'intervention' ? ' · 点击响应' : ''}
                    </div>
                    {item.source_type !== 'intervention' && (
                      <div className="ms-notif__actions">
                        {item.source_type === 'ecp_proposal' && (
                          <>
                            <button
                              type="button"
                              className="ms-notif__act"
                              onClick={(e) => {
                                e.stopPropagation();
                                setProposalItem(item);
                              }}
                            >
                              <EyeOutlined /> 查看详情
                            </button>
                            <button
                              type="button"
                              className="ms-notif__act ms-notif__act--primary"
                              onClick={(e) => quickDone(item, e)}
                            >
                              <CheckOutlined /> 确认生效
                            </button>
                          </>
                        )}
                        {item.source_type === 'manual' && (
                          <button
                            type="button"
                            className="ms-notif__act ms-notif__act--primary"
                            onClick={(e) => quickDone(item, e)}
                          >
                            <CheckOutlined /> 标记完成
                          </button>
                        )}
                        {item.source_type === 'task' && (
                          <span className="ms-notif__act">
                            <MobileOutlined /> 桌面端处理
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </PullToRefresh>
      );
    }
    // overview
    return (
      <PullToRefresh onRefresh={pullRefresh} className="ms-body">
        <div className="ms-metrics">
          <div className="ms-metric">
            <span className="ms-metric__value ms-metric__value--brand">{runningCount}</span>
            <span className="ms-metric__label">运行中</span>
          </div>
          <div className="ms-metric">
            <span className="ms-metric__value" style={{ color: 'var(--ms-amber)' }}>{awaitingCount}</span>
            <span className="ms-metric__label">待介入</span>
          </div>
          <div className="ms-metric">
            <span className="ms-metric__value">{artifacts?.length || 0}</span>
            <span className="ms-metric__label">产出</span>
          </div>
        </div>

        <div className="ms-section">
          <div className="ms-section__head">
            <span className="ms-section__title">最近产出</span>
            <span className="ms-section__count">{(artifacts || []).slice(0, 4).length}</span>
          </div>
          {!artifacts || artifacts.length === 0 ? (
            <div className="ms-list-row">
              <CloudServerOutlined className="ms-list-row__icon" />
              <div className="ms-list-row__main">
                <div className="ms-list-row__title">暂无产出物</div>
                <div className="ms-list-row__meta">任务产出的报告、数据集会沉淀在这里</div>
              </div>
            </div>
          ) : (
            artifacts.slice(0, 4).map((a: any) => (
              <div key={a.id} className="ms-list-row">
                <AppstoreOutlined className="ms-list-row__icon" />
                <div className="ms-list-row__main">
                  <div className="ms-list-row__title">{a.title || `artifact_${a.id}`}</div>
                  <div className="ms-list-row__meta">{a.type}</div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="ms-section">
          <div className="ms-section__head">
            <span className="ms-section__title">最近交付</span>
            <span className="ms-section__count">{(deliveries || []).slice(0, 3).length}</span>
          </div>
          {!deliveries || deliveries.length === 0 ? (
            <div className="ms-list-row">
              <CloudServerOutlined className="ms-list-row__icon" />
              <div className="ms-list-row__main">
                <div className="ms-list-row__title">暂无交付记录</div>
              </div>
            </div>
          ) : (
            deliveries.slice(0, 3).map((d: any) => (
              <div key={d.id} className="ms-list-row">
                <AppstoreOutlined className="ms-list-row__icon" />
                <div className="ms-list-row__main">
                  <div className="ms-list-row__title">{d.title || `delivery_${d.id}`}</div>
                  <div className="ms-list-row__meta">{d.channel} · {d.status}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </PullToRefresh>
    );
  };

  return (
    <>
      <header className="ms-header">
        <button
          type="button"
          className="ms-header__back"
          aria-label="返回"
          onClick={() => router.push('/m')}
        >
          <ArrowLeftOutlined />
        </button>
        <span className={`ms-status-dot${hasActive ? ' ms-status-dot--running' : ''}`} />
        <div className="ms-header__title-wrap">
          <div className="ms-header__title">{ws.name}</div>
          <div className="ms-header__sub">{ws.workspace_code} · {scenario}</div>
        </div>
        <span className="ms-chip ms-chip--neutral">{convUid ? '就绪' : '同步中'}</span>
      </header>

      <div className="ms-frame__body" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {renderBody()}
      </div>

      <nav className="ms-nav" aria-label="空间导航">
        {TABS.map((t) => (
          <span
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`ms-tab${tab === t.key ? ' ms-tab--on' : ''}`}
            onClick={() => setTab(t.key)}
          >
            <span className="ms-tab__icon">
              {t.icon}
              {t.key === 'notifications' && unreadCount > 0 && (
                <span className="ms-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
              )}
              {t.key === 'tasks' && awaitingCount > 0 && (
                <span className="ms-badge">{awaitingCount}</span>
              )}
            </span>
            <span className="ms-tab__label">{t.label}</span>
          </span>
        ))}
      </nav>

      <Modal
        open={!!approveItem}
        footer={null}
        centered
        destroyOnClose
        width={320}
        onCancel={() => { setApproveItem(null); setComment(''); }}
      >
        <div className="ms-approve">
          <div className="ms-approve__meta">需要你的介入确认</div>
          <div className="ms-approve__question">{approveItem?.title || '介入请求'}</div>
          {approveItem?.summary && <p className="ms-approve__summary">{approveItem.summary}</p>}
          <Input.TextArea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="补充说明(可选)"
            autoSize={{ minRows: 2, maxRows: 4 }}
          />
          <div className="ms-approve__actions">
            <button
              type="button"
              className="ms-approve__btn ms-approve__btn--danger"
              disabled={!!acting}
              onClick={() => resolveApprove('rejected')}
            >
              {acting === 'reject' ? '处理中…' : '驳回'}
            </button>
            <button
              type="button"
              className="ms-approve__btn ms-approve__btn--primary"
              disabled={!!acting}
              onClick={() => resolveApprove('approved')}
            >
              {acting === 'approve' ? '处理中…' : '批准'}
            </button>
          </div>
        </div>
      </Modal>

      <MobileProposalDetail
        item={proposalItem}
        onClose={() => setProposalItem(null)}
        onResolved={() => refreshInbox?.()}
      />
    </>
  );
}