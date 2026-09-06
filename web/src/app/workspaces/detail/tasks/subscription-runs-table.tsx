'use client';

import { apiInterceptors, listTasks, listTriggers } from '@/client/api';
import { Empty, Spin } from 'antd';
import { useRequest } from 'ahooks';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import Table from 'antd/es/table';
import '../../workspaces.css';

interface RunRow {
  id: number;
  title: string;
  status: string;
  type?: string;
  triggered_by?: string;
  trigger_ref?: string;
  gmt_created?: string;
}

const STATUS_VARIANT: Record<string, string> = {
  draft: 'neutral',
  pending_trigger: 'attention',
  running: 'running',
  awaiting_human: 'attention',
  blocked: 'danger',
  delivered: 'success',
  closed: 'neutral',
  archived: 'neutral',
  failed: 'danger',
};

const TRIGGER_VARIANT: Record<string, string> = {
  timer: 'info',
  webhook: 'purple',
  alert: 'attention',
};

function statusVariant(s: string) { return STATUS_VARIANT[s] || 'neutral'; }
function statusLabel(s: string) { return (s || '').replace(/_/g, ' '); }

/**
 * 订阅执行记录(订阅触发产生的任务运行:按 triggered_by=timer/webhook/alert 过滤,
 * 传入 triggerId 时收敛到单个订阅)。嵌在订阅页「执行记录」Tab 中。
 */
export default function SubscriptionRunsTable({ workspaceId, workspaceCode, triggerId }: {
  workspaceId: number; workspaceCode: string; triggerId?: string;
}) {
  const { t } = useTranslation();

  const { data: triggers } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listTriggers({ workspace_id: workspaceId, limit: 200 }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId] });
  const triggerName = (ref?: string) => {
    const hit = (triggers || []).find((x: { id: number }) => String(x.id) === String(ref));
    return hit?.name;
  };

  const { data: runs, loading } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listTasks({
      workspace_id: workspaceId,
      triggered_by: 'timer,webhook,alert',
      trigger_ref: triggerId || undefined,
      limit: 200,
    }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, triggerId] });

  const columns: ColumnsType<RunRow> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 70,
      render: (v: number) => <span className="ws-table-id">#{v}</span>,
    },
    {
      title: t('tasks.title') || 'Title',
      dataIndex: 'title',
      render: (v: string, r: RunRow) => (
        <Link href={`/workspaces/detail/tasks/detail?id=${workspaceCode}&task_id=${r.id}`} className="ws-table-link">
          {v}
        </Link>
      ),
    },
    {
      title: t('workspaces.subscriptions') || '订阅',
      dataIndex: 'trigger_ref',
      width: 200,
      render: (v?: string) => v ? (
        <span className="ws-chip ws-chip--outline" title={`trigger #${v}`}>
          {triggerName(v) || `#${v}`}
        </span>
      ) : <span style={{ color: 'var(--ws-ink-3)' }}>—</span>,
    },
    {
      title: t('tasks.triggered_by') || 'Trigger',
      dataIndex: 'triggered_by',
      width: 110,
      render: (v?: string) => v ? (
        <span className={`ws-chip ws-chip--${TRIGGER_VARIANT[v] || 'outline'} ws-chip--mono`}>{v}</span>
      ) : <span style={{ color: 'var(--ws-ink-3)' }}>—</span>,
    },
    {
      title: t('tasks.status') || 'Status',
      dataIndex: 'status',
      width: 140,
      render: (s: string) => (
        <span className={`ws-status ws-status--${statusVariant(s)}`}>
          <span className="ws-status-dot" />
          {statusLabel(s)}
        </span>
      ),
    },
    {
      title: t('tasks.created') || 'Created',
      dataIndex: 'gmt_created',
      width: 170,
      render: (v?: string) => v ? <span className="ws-table-time">{new Date(v).toLocaleString()}</span> : <span style={{ color: 'var(--ws-ink-3)' }}>—</span>,
    },
  ];

  return (
    <div>
      {triggerId ? (
        <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="ws-chip ws-chip--outline">
            {t('workspaces.subscriptions') || '订阅'} #{triggerId}{triggerName(triggerId) ? ` · ${triggerName(triggerId)}` : ''}
          </span>
          <Link href={`/workspaces/detail/tasks?id=${workspaceCode}&tab=runs`} className="ws-table-link">
            {t('subscriptions.view_all') || '查看全部'}
          </Link>
        </div>
      ) : null}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}><Spin /></div>
      ) : (
        <Table<RunRow>
          rowKey="id"
          columns={columns}
          dataSource={runs || []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          locale={{
            emptyText: <Empty description={t('subscriptions.runs_empty') || 'No subscription runs yet'} style={{ padding: '48px 0' }} />,
          }}
        />
      )}
    </div>
  );
}
