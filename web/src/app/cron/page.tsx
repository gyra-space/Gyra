'use client';

import { apiInterceptors, getCronJobs, getCronStatus, deleteCronJob, runCronJob } from '@/client/api';
import { CronJob } from '@/client/api/cron';
import {
  ClockCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Space, Switch, Table, Tag, Typography, Popconfirm, Tooltip, Empty } from 'antd';
import moment from 'moment';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CronLogsDrawer } from './components/cron-logs';
import '../workspaces/workspaces.css';

const { Text } = Typography;

export default function CronPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { message } = App.useApp();
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [logsTarget, setLogsTarget] = useState<{ jobId: string; name: string } | null>(null);

  // Fetch status
  const { data: statusData, loading: statusLoading, refresh: refreshStatus } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getCronStatus());
    if (err) {
      return null;
    }
    return res;
  });

  // Fetch jobs
  const {
    data: jobsData,
    loading: jobsLoading,
    refresh: refreshJobs,
  } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getCronJobs(includeDisabled));
      if (err) {
        return [];
      }
      return res || [];
    },
    {
      refreshDeps: [includeDisabled],
    }
  );

  // Delete job
  const { run: runDeleteJob, loading: deleteLoading } = useRequest(
    async (jobId: string) => {
      const [err] = await apiInterceptors(deleteCronJob(jobId));
      if (err) {
        throw err;
      }
    },
    {
      manual: true,
      onSuccess: () => {
        message.success(t('cron_delete_success'));
        refreshJobs();
        refreshStatus();
      },
      onError: () => {
        message.error(t('Error_Message'));
      },
    }
  );

  // Run job now
  const { run: runJobNow, loading: runLoading } = useRequest(
    async (jobId: string) => {
      const [err] = await apiInterceptors(runCronJob(jobId, true));
      if (err) {
        throw err;
      }
    },
    {
      manual: true,
      onSuccess: () => {
        message.success(t('cron_run_success'));
        refreshJobs();
      },
      onError: () => {
        message.error(t('Error_Message'));
      },
    }
  );

  const columns = [
    {
      title: t('cron_name'),
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: CronJob) => (
        <Link href={`/cron/edit?id=${record.id}`} className="text-[var(--ws-accent)] hover:opacity-80">
          {name}
        </Link>
      ),
    },
    {
      title: t('cron_description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: t('cron_created_at'),
      dataIndex: 'gmt_created',
      key: 'created_at',
      width: 160,
      render: (created: string) => created ? moment(created).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: t('cron_schedule_type'),
      dataIndex: ['schedule', 'kind'],
      key: 'schedule_kind',
      width: 100,
      render: (kind: string) => {
        const kindMap: Record<string, { label: string; color: string }> = {
          cron: { label: t('cron_cron_expr'), color: 'blue' },
          every: { label: t('cron_interval'), color: 'green' },
          at: { label: t('cron_once'), color: 'orange' },
        };
        const item = kindMap[kind] || { label: kind, color: 'default' as string };
        return <Tag color={item.color}>{item.label}</Tag>;
      },
    },
    {
      title: t('cron_schedule'),
      key: 'schedule',
      width: 130,
      render: (_: any, record: CronJob) => {
        const { schedule } = record;
        if (schedule.kind === 'cron') {
          return <Text code>{schedule.expr}</Text>;
        } else if (schedule.kind === 'every') {
          const seconds = Math.floor((schedule.every_ms || 0) / 1000);
          if (seconds < 60) return `${seconds}s`;
          if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
          return `${Math.floor(seconds / 3600)}h`;
        } else if (schedule.kind === 'at') {
          return moment(schedule.at).format('YYYY-MM-DD HH:mm');
        }
        return '-';
      },
    },
    {
      title: t('cron_status'),
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? t('cron_enabled') : t('cron_disabled')}</Tag>
      ),
    },
    {
      title: t('cron_last_run'),
      dataIndex: ['state', 'last_run_at_ms'],
      key: 'last_run',
      width: 160,
      render: (ms: number, record: CronJob) => {
        const status = record.state?.last_status;
        const color = status === 'error' ? 'error' : status === 'ok' ? 'success' : 'default';
        return (
          <Space size={4}>
            <span>{ms ? moment(ms).format('YYYY-MM-DD HH:mm:ss') : '-'}</span>
            {status && (
              <Tag color={color} style={{ marginInlineEnd: 0 }}>
                {status === 'ok' ? t('cron_ok') : status === 'error' ? t('cron_error') : t('cron_skipped')}
              </Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: t('cron_next_run'),
      dataIndex: ['state', 'next_run_at_ms'],
      key: 'next_run',
      width: 160,
      render: (ms: number) => (ms ? moment(ms).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: t('Operation'),
      key: 'action',
      width: 150,
      render: (_: any, record: CronJob) => (
        <Space size="small">
          <Tooltip title={t('Edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => router.push(`/cron/edit?id=${record.id}`)}
            />
          </Tooltip>
          <Tooltip title={t('cron_execution_logs')}>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setLogsTarget({ jobId: record.id, name: record.name })}
            />
          </Tooltip>
          <Tooltip title={t('cron_run_now')}>
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              loading={runLoading}
              onClick={() => runJobNow(record.id)}
            />
          </Tooltip>
          <Popconfirm
            title={t('cron_confirm_delete')}
            onConfirm={() => runDeleteJob(record.id)}
            okText={t('Yes')}
            cancelText={t('No')}
          >
            <Tooltip title={t('Delete')}>
              <Button type="text" danger icon={<DeleteOutlined />} loading={deleteLoading} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="ws-page scrollbar-default">
      <div className="ws-page-bg" />

      {/* Sticky header */}
      <div
        className="ws-surface-veil sticky top-0 z-30 backdrop-blur border-b border-[var(--ws-border)]"
      >
        <div className="ws-page-content">
          <header className="ws-page-header !mb-0 py-3">
            <div className="ws-page-header-left">
              <div className="ws-page-icon"><ClockCircleOutlined /></div>
              <div>
                <div className="ws-page-eyebrow">Cron · Scheduled Tasks</div>
                <h1 className="ws-page-title">{t('cron_page_title')}</h1>
                <p className="ws-page-subtitle">管理定时任务，查看调度状态与历史执行记录</p>
              </div>
            </div>
            <div className="ws-page-actions">
              <Space wrap>
                <Button icon={<ReloadOutlined />} size="large" onClick={() => { refreshJobs(); refreshStatus(); }}>
                  {t('Refresh_status')}
                </Button>
                <Link href="/cron/create">
                  <Button type="primary" icon={<PlusOutlined />} size="large">
                    {t('cron_create')}
                  </Button>
                </Link>
              </Space>
            </div>
          </header>
        </div>
      </div>

      <div className="ws-page-content">
        <main className="pt-6 pb-24 space-y-5">
          {/* Status strip */}
          <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-8">
                <div>
                  <Text type="secondary">{t('cron_scheduler_status')}</Text>
                  <div className="mt-1">
                    <Tag color={statusData?.running ? 'processing' : 'default'}>
                      {statusData?.running ? t('cron_running') : t('cron_stopped')}
                    </Tag>
                  </div>
                </div>
                <div>
                  <Text type="secondary">{t('cron_total_jobs')}</Text>
                  <div className="mt-1 text-xl font-semibold text-[var(--ws-ink)]">{statusData?.jobs || 0}</div>
                </div>
                <div>
                  <Text type="secondary">{t('cron_enabled_jobs')}</Text>
                  <div className="mt-1 text-xl font-semibold" style={{ color: 'var(--ws-success)' }}>
                    {statusData?.enabled_jobs || 0}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Text type="secondary">{t('cron_show_disabled')}</Text>
                <Switch checked={includeDisabled} onChange={setIncludeDisabled} />
              </div>
            </div>
          </section>

          {/* Jobs Table */}
          <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5">
            <Table<CronJob>
              rowKey="id"
              columns={columns}
              dataSource={jobsData}
              loading={jobsLoading}
              pagination={{ pageSize: 10 }}
              locale={{
                emptyText: (
                  <Empty description={t('cron_no_jobs')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ),
              }}
            />
          </section>
        </main>
      </div>

      {/* Execution logs drawer */}
      <CronLogsDrawer
        open={!!logsTarget}
        jobId={logsTarget?.jobId}
        jobName={logsTarget?.name}
        onClose={() => setLogsTarget(null)}
      />
    </div>
  );
}