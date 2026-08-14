'use client';

import { apiInterceptors, getCronJob, updateCronJob, deleteCronJob, runCronJob } from '@/client/api';
import {
  ArrowLeftOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Descriptions, Form, Popconfirm, Space, Spin, Tag, Typography } from 'antd';
import moment from 'moment';
import { useRouter, useSearchParams } from 'next/navigation';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import CronForm from '../components/cron-form';
import CronLogsTable from '../components/cron-logs';
import '../../workspaces/workspaces.css';

const { Text } = Typography;

export default function EditCronPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams?.get('id');
  const { message, modal } = App.useApp();
  const [form] = Form.useForm();
  const [showLogs, setShowLogs] = useState(false);

  // Fetch job details
  const { data: jobData, loading: jobLoading, refresh: refreshJob } = useRequest(
    async () => {
      if (!jobId) return null;
      const [err, res] = await apiInterceptors(getCronJob(jobId));
      if (err) {
        throw err;
      }
      return res || null;
    },
    {
      ready: !!jobId,
      refreshDeps: [jobId],
    }
  );

  // Update job
  const { run: runUpdateJob, loading: updateLoading } = useRequest(
    async (values: any) => {
      if (!jobId) return;
      // Parse tool_args if it's a string
      if (values.payload?.tool_args && typeof values.payload.tool_args === 'string') {
        try {
          values.payload.tool_args = JSON.parse(values.payload.tool_args);
        } catch {
          // Keep as is if not valid JSON
        }
      }
      const [err] = await apiInterceptors(updateCronJob(jobId, values));
      if (err) {
        throw err;
      }
    },
    {
      manual: true,
      onSuccess: () => {
        message.success(t('cron_save_success'));
        refreshJob();
      },
      onError: () => {
        message.error(t('Error_Message'));
      },
    }
  );

  // Delete job
  const { run: runDeleteJob, loading: deleteLoading } = useRequest(
    async () => {
      if (!jobId) return;
      const [err] = await apiInterceptors(deleteCronJob(jobId));
      if (err) {
        throw err;
      }
    },
    {
      manual: true,
      onSuccess: () => {
        message.success(t('cron_delete_success'));
        router.push('/cron');
      },
      onError: () => {
        message.error(t('Error_Message'));
      },
    }
  );

  // Run job now
  const { run: runJobNow, loading: runLoading } = useRequest(
    async () => {
      if (!jobId) return;
      const [err] = await apiInterceptors(runCronJob(jobId, true));
      if (err) {
        throw err;
      }
    },
    {
      manual: true,
      onSuccess: () => {
        message.success(t('cron_run_success'));
        refreshJob();
      },
      onError: () => {
        message.error(t('Error_Message'));
      },
    }
  );

  // Initialize form with job data
  useEffect(() => {
    if (jobData) {
      form.setFieldsValue({
        name: jobData.name,
        description: jobData.description,
        enabled: jobData.enabled,
        delete_after_run: jobData.delete_after_run,
        schedule: {
          kind: jobData.schedule.kind,
          at: jobData.schedule.at,
          every_ms: jobData.schedule.every_ms,
          anchor_ms: jobData.schedule.anchor_ms,
          expr: jobData.schedule.expr,
          tz: jobData.schedule.tz,
        },
        payload: {
          kind: jobData.payload.kind,
          message: jobData.payload.message,
          agent_id: jobData.payload.agent_id,
          tool_name: jobData.payload.tool_name,
          tool_args: jobData.payload.tool_args,
          text: jobData.payload.text,
          timeout_seconds: jobData.payload.timeout_seconds,
          session_mode: jobData.payload.session_mode || 'isolated',
          conv_session_id: jobData.payload.conv_session_id,
        },
      });
    }
  }, [jobData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await runUpdateJob(values);
    } catch {
      // Form validation error
    }
  };

  const handleDelete = () => {
    modal.confirm({
      title: t('cron_confirm_delete'),
      onOk: () => runDeleteJob(),
      okText: t('Yes'),
      cancelText: t('No'),
    });
  };

  if (!jobId) {
    return (
      <div className="p-6">
        <Text type="secondary">Job ID is required</Text>
      </div>
    );
  }

  if (jobLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    );
  }

  if (!jobData) {
    return (
      <div className="p-6">
        <Text type="secondary">Job not found</Text>
      </div>
    );
  }

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
                <h1 className="ws-page-title">{t('cron_edit')}: {jobData.name}</h1>
                <p className="ws-page-subtitle">调整任务配置、立即执行或查看历史执行记录</p>
              </div>
            </div>
            <div className="ws-page-actions">
              <Space wrap>
                <Button icon={<ArrowLeftOutlined />} size="large" onClick={() => router.push('/cron')}>
                  {t('Back')}
                </Button>
                <Button
                  icon={<HistoryOutlined />}
                  size="large"
                  onClick={() => setShowLogs((v) => !v)}
                >
                  {t('cron_execution_logs')}
                </Button>
                <Button
                  icon={<PlayCircleOutlined />}
                  size="large"
                  loading={runLoading}
                  onClick={() => runJobNow()}
                >
                  {t('cron_run_now')}
                </Button>
                <Popconfirm
                  title={t('cron_confirm_delete')}
                  onConfirm={handleDelete}
                  okText={t('Yes')}
                  cancelText={t('No')}
                >
                  <Button danger icon={<DeleteOutlined />} size="large" loading={deleteLoading}>
                    {t('Delete')}
                  </Button>
                </Popconfirm>
                <Button type="primary" icon={<SaveOutlined />} size="large" loading={updateLoading} onClick={handleSave}>
                  {t('save')}
                </Button>
              </Space>
            </div>
          </header>
        </div>
      </div>

      <div className="ws-page-content">
        <main className="pt-6 pb-24 max-w-3xl space-y-5">
          {/* Job Status */}
          <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-1 h-5 bg-[var(--ws-accent)] rounded-full" />
              <h3 className="text-sm font-semibold text-[var(--ws-ink)]">{t('cron_status')}</h3>
            </div>
            <Descriptions column={{ xs: 1, sm: 2, md: 4 }} size="small">
              <Descriptions.Item label={t('cron_status')}>
                <Tag color={jobData.enabled ? 'success' : 'default'}>
                  {jobData.enabled ? t('cron_enabled') : t('cron_disabled')}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('cron_last_run')}>
                {jobData.state?.last_run_at_ms
                  ? moment(jobData.state.last_run_at_ms).format('YYYY-MM-DD HH:mm:ss')
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('cron_next_run')}>
                {jobData.state?.next_run_at_ms
                  ? moment(jobData.state.next_run_at_ms).format('YYYY-MM-DD HH:mm:ss')
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('cron_consecutive_errors')}>
                <Tag color={(jobData.state?.consecutive_errors || 0) > 0 ? 'error' : 'success'}>
                  {jobData.state?.consecutive_errors || 0}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
            {jobData.state?.last_error && (
              <div className="mt-3 bg-[var(--ws-danger)]/5 border border-[var(--ws-danger)]/20 rounded-lg p-3">
                <Text type="danger" style={{ wordBreak: 'break-all' }}>{jobData.state.last_error}</Text>
              </div>
            )}
          </section>

          {/* Edit Form */}
          <CronForm form={form} initialValues={jobData} />

          {/* Execution Logs */}
          {showLogs && (
            <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-1 h-5 bg-[var(--ws-accent)] rounded-full" />
                <span className="text-[var(--ws-accent)]"><HistoryOutlined /></span>
                <h3 className="text-sm font-semibold text-[var(--ws-ink)]">{t('cron_execution_logs')}</h3>
              </div>
              <CronLogsTable jobId={jobId} />
            </section>
          )}
        </main>
      </div>
    </div>
  );
}