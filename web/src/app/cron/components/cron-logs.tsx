'use client';

import { apiInterceptors, getCronJobLogs } from '@/client/api';
import { CronJobLog } from '@/client/api/cron';
import { HistoryOutlined, ReloadOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { Button, Drawer, Empty, Spin, Table, Tag, Typography } from 'antd';
import moment from 'moment';
import React from 'react';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

const STATUS_META: Record<string, { label: string; color: string }> = {
  ok: { label: 'success', color: 'success' as const },
  error: { label: 'error', color: 'error' as const },
  skipped: { label: 'skipped', color: 'default' as const },
};

function formatDuration(ms?: number): string {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export default function CronLogsTable({ jobId }: { jobId: string }) {
  const { t } = useTranslation();

  const { data: logs, loading, refresh } = useRequest(
    async () => {
      if (!jobId) return [];
      const [err, res] = await apiInterceptors(getCronJobLogs(jobId));
      if (err) return [];
      return res || [];
    },
    { refreshDeps: [jobId] }
  );

  const columns = [
    {
      title: t('cron_created_at'),
      dataIndex: 'run_at_ms',
      key: 'run_at',
      width: 170,
      render: (ms: number) => (ms ? moment(ms).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: t('cron_run_status'),
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        const meta = STATUS_META[status] || { label: status, color: 'default' as const };
        const labelMap: Record<string, string> = {
          ok: t('cron_ok'),
          error: t('cron_error'),
          skipped: t('cron_skipped'),
        };
        return <Tag color={meta.color}>{labelMap[status] || status}</Tag>;
      },
    },
    {
      title: t('cron_trigger'),
      dataIndex: 'trigger',
      key: 'trigger',
      width: 90,
      render: (trigger: string) =>
        trigger === 'manual' ? <Tag color="blue">{t('cron_manual')}</Tag> : <Tag>{t('cron_scheduled')}</Tag>,
    },
    {
      title: t('cron_duration'),
      dataIndex: 'duration_ms',
      key: 'duration',
      width: 100,
      render: (ms: number) => formatDuration(ms),
    },
    {
      title: t('cron_last_error'),
      dataIndex: 'error',
      key: 'error',
      render: (err: string) =>
        err ? <Text type="danger" style={{ wordBreak: 'break-all' }}>{err}</Text> : '-',
    },
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-end">
        <Button size="small" icon={<ReloadOutlined />} onClick={refresh}>
          {t('Refresh_status')}
        </Button>
      </div>
      <Table<CronJobLog>
        rowKey="id"
        size="small"
        columns={columns}
        dataSource={logs}
        loading={loading}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        locale={{
          emptyText: (
            <Empty description={t('cron_no_logs')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ),
        }}
      />
    </div>
  );
}

export function CronLogsDrawer({
  jobId,
  jobName,
  open,
  onClose,
}: {
  jobId?: string;
  jobName?: string;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Drawer
      title={
        <span className="flex items-center gap-2">
          <HistoryOutlined className="text-[var(--ws-accent)]" />
          {t('cron_execution_logs')}
          {jobName ? <span className="text-sm font-normal text-[var(--ws-ink-3)]">· {jobName}</span> : null}
        </span>
      }
      width={720}
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      {jobId ? <CronLogsTable jobId={jobId} /> : <Spin />}
    </Drawer>
  );
}