'use client';

import { apiInterceptors, createCronJob } from '@/client/api';
import { ArrowLeftOutlined, ClockCircleOutlined, SaveOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Form, Space } from 'antd';
import { useRouter } from 'next/navigation';
import React from 'react';
import { useTranslation } from 'react-i18next';
import CronForm from '../components/cron-form';
import '../../workspaces/workspaces.css';

export default function CreateCronPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  // Create job
  const { run: runCreateJob, loading: createLoading } = useRequest(
    async (values: any) => {
      // Parse tool_args if it's a string
      if (values.payload?.tool_args && typeof values.payload.tool_args === 'string') {
        try {
          values.payload.tool_args = JSON.parse(values.payload.tool_args);
        } catch {
          // Keep as is if not valid JSON
        }
      }
      const [err, res] = await apiInterceptors(createCronJob(values));
      if (err) {
        throw err;
      }
      return res;
    },
    {
      manual: true,
      onSuccess: () => {
        message.success(t('cron_save_success'));
        router.push('/cron');
      },
      onError: (err: any) => {
        message.error(t('Error_Message') + ': ' + (err?.message || 'Unknown error'));
      },
    }
  );

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await runCreateJob(values);
    } catch (error: any) {
      if (error?.errorFields) {
        message.warning(t('form_required'));
      } else {
        message.error(t('Error_Message'));
      }
    }
  };

  return (
    <div className="ws-page scrollbar-default">
      <div className="ws-page-bg" />

      {/* Sticky header */}
      <div
        className="sticky top-0 z-30 backdrop-blur border-b border-[var(--ws-border)]"
        style={{ backgroundColor: 'color-mix(in srgb, var(--ws-surface) 88%, transparent)' }}
      >
        <div className="ws-page-content">
          <header className="ws-page-header !mb-0 py-3">
            <div className="ws-page-header-left">
              <div className="ws-page-icon"><ClockCircleOutlined /></div>
              <div>
                <div className="ws-page-eyebrow">Cron · Scheduled Tasks</div>
                <h1 className="ws-page-title">{t('cron_create')}</h1>
                <p className="ws-page-subtitle">配置任务名称、执行频率与要执行的操作，到点自动运行</p>
              </div>
            </div>
            <div className="ws-page-actions">
              <Space>
                <Button icon={<ArrowLeftOutlined />} size="large" onClick={() => router.push('/cron')}>
                  {t('Back')}
                </Button>
                <Button type="primary" icon={<SaveOutlined />} size="large" loading={createLoading} onClick={handleSave}>
                  {t('save')}
                </Button>
              </Space>
            </div>
          </header>
        </div>
      </div>

      {/* Form - 可滚动区域 */}
      <div className="ws-page-content">
        <main className="pt-6 pb-24 max-w-3xl">
          <CronForm form={form} />
        </main>
      </div>
    </div>
  );
}