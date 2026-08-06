'use client';

import { CronJobCreate } from '@/client/api/cron';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { DatePicker, Form, Input, InputNumber, Select, Switch } from 'antd';
import dayjs from 'dayjs';
import React from 'react';
import { useTranslation } from 'react-i18next';
import CronEditor from '../../workspaces/detail/tasks/create/cron-editor';

const { TextArea } = Input;

interface CronFormProps {
  form: any;
  initialValues?: Partial<CronJobCreate>;
}

function SectionHeader({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-2 mb-5">
      <div className="w-1 h-5 bg-[var(--ws-accent)] rounded-full" />
      <span className="text-[var(--ws-accent)] flex items-center">{icon}</span>
      <h3 className="text-sm font-semibold text-[var(--ws-ink)]">{title}</h3>
      <span className="text-xs text-[var(--ws-ink-3)]">{subtitle}</span>
    </div>
  );
}

export default function CronForm({ form, initialValues }: CronFormProps) {
  const { t } = useTranslation();

  const scheduleKind = Form.useWatch(['schedule', 'kind'], form);
  const sessionMode = Form.useWatch(['payload', 'session_mode'], form);
  const payloadKind = Form.useWatch(['payload', 'kind'], form);
  const tz = Form.useWatch(['schedule', 'tz'], form) || 'Asia/Shanghai';

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        enabled: true,
        ...initialValues,
        schedule: {
          kind: 'cron',
          tz: 'Asia/Shanghai',
          ...initialValues?.schedule,
        },
        payload: {
          kind: 'agentTurn',
          session_mode: 'isolated',
          ...initialValues?.payload,
        },
      }}
    >
      {/* 基础信息 */}
      <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5 mb-5">
        <SectionHeader
          icon={<SettingOutlined />}
          title={t('baseinfo_basic_info')}
          subtitle="任务的基本信息"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Form.Item
            name="name"
            label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_name')}</span>}
            rules={[{ required: true, message: t('Please_Input') + t('cron_name') }]}
          >
            <Input size="large" placeholder={t('Please_Input') + t('cron_name')} className="!rounded-lg" />
          </Form.Item>
          <Form.Item
            name="enabled"
            label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_status')}</span>}
            valuePropName="checked"
          >
            <Switch checkedChildren={t('cron_enabled')} unCheckedChildren={t('cron_disabled')} />
          </Form.Item>
        </div>
        <Form.Item
          name="description"
          label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_description')}</span>}
        >
          <TextArea rows={2} placeholder={t('Please_Input') + t('cron_description')} />
        </Form.Item>
        <Form.Item
          name="delete_after_run"
          label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_delete_after_run')}</span>}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </section>

      {/* 调度配置 */}
      <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5 mb-5">
        <SectionHeader
          icon={<CalendarOutlined />}
          title={t('cron_schedule')}
          subtitle="任务何时执行"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <Form.Item
            name={['schedule', 'kind']}
            label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_schedule_type')}</span>}
            rules={[{ required: true }]}
          >
            <Select size="large">
              <Select.Option value="cron">{t('cron_cron_expr')}</Select.Option>
              <Select.Option value="every">{t('cron_interval')}</Select.Option>
              <Select.Option value="at">{t('cron_once')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name={['schedule', 'tz']}
            label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_timezone')}</span>}
          >
            <Select size="large" showSearch allowClear>
              <Select.Option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</Select.Option>
              <Select.Option value="UTC">UTC</Select.Option>
              <Select.Option value="America/New_York">America/New_York (EST)</Select.Option>
              <Select.Option value="Europe/London">Europe/London (GMT)</Select.Option>
              <Select.Option value="Asia/Tokyo">Asia/Tokyo (JST)</Select.Option>
            </Select>
          </Form.Item>
        </div>

        {scheduleKind === 'cron' && (
          <div className="bg-[var(--ws-border-subtle)] rounded-xl border border-[var(--ws-border)] p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <ClockCircleOutlined className="text-[var(--ws-accent)]" />
              <span className="text-sm font-medium text-[var(--ws-ink)]">{t('cron_cron_expression')}</span>
            </div>
            <Form.Item name={['schedule', 'expr']} rules={[{ required: true, message: t('Please_Input') + t('cron_cron_expression') }]}>
              <CronEditor tz={tz} />
            </Form.Item>
          </div>
        )}

        {scheduleKind === 'every' && (
          <div className="bg-[var(--ws-border-subtle)] rounded-xl border border-[var(--ws-border)] p-4">
            <Form.Item
              name={['schedule', 'every_ms']}
              label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_interval_ms')}</span>}
              rules={[{ required: true, message: t('Please_Input') + t('cron_interval_ms') }]}
              extra="例如: 60000 表示 1 分钟, 3600000 表示 1 小时"
            >
              <InputNumber min={1000} step={1000} style={{ width: '100%' }} size="large" />
            </Form.Item>
          </div>
        )}

        {scheduleKind === 'at' && (
          <div className="bg-[var(--ws-border-subtle)] rounded-xl border border-[var(--ws-border)] p-4">
            <Form.Item
              name={['schedule', 'at']}
              label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_run_at')}</span>}
              getValueProps={(value: string) => ({
                value: value ? dayjs(value) : undefined,
              })}
              normalize={(value: any) => (value ? value.toISOString() : value)}
              rules={[{ required: true, message: t('Please_Input') + t('cron_run_at') }]}
            >
              <DatePicker showTime style={{ width: '100%' }} size="large" />
            </Form.Item>
          </div>
        )}
      </section>

      {/* 任务负载 */}
      <section className="bg-[var(--ws-surface)] rounded-xl border border-[var(--ws-border)] shadow-sm p-5">
        <SectionHeader
          icon={<RocketOutlined />}
          title={t('cron_payload')}
          subtitle="任务要执行的操作"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Form.Item
            name={['payload', 'kind']}
            label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_payload_type')}</span>}
            rules={[{ required: true }]}
          >
            <Select size="large">
              <Select.Option value="agentTurn">{t('cron_agent_turn')}</Select.Option>
              <Select.Option value="toolCall">{t('cron_tool_call')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name={['payload', 'timeout_seconds']}
            label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_timeout')}</span>}
            extra="任务执行超时时间(秒)"
          >
            <InputNumber min={1} max={3600} style={{ width: '100%' }} size="large" placeholder="默认600秒" />
          </Form.Item>
        </div>

        <div className="my-4 border-t border-[var(--ws-border-subtle)]" />

        {/* Agent 调用 (agentTurn) */}
        {payloadKind === 'agentTurn' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Form.Item
                name={['payload', 'agent_id']}
                label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_agent_id')}</span>}
                rules={[{ required: true, message: t('Please_Input') + t('cron_agent_id') }]}
                extra="要调用的 Agent ID"
              >
                <Input size="large" placeholder={t('Please_Input') + t('cron_agent_id')} />
              </Form.Item>
              <Form.Item
                name={['payload', 'session_mode']}
                label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_session_mode')}</span>}
                extra={t('cron_session_mode_desc')}
              >
                <Select size="large">
                  <Select.Option value="isolated">{t('cron_session_isolated')}</Select.Option>
                  <Select.Option value="shared">{t('cron_session_shared')}</Select.Option>
                </Select>
              </Form.Item>
            </div>
            {sessionMode === 'shared' && (
              <Form.Item
                name={['payload', 'conv_session_id']}
                label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_session_id')}</span>}
                extra={t('cron_session_id_desc')}
              >
                <Input size="large" placeholder={t('Please_Input') + t('cron_session_id')} />
              </Form.Item>
            )}
            <Form.Item
              name={['payload', 'message']}
              label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_message')}</span>}
              rules={[{ required: true, message: t('Please_Input') + t('cron_message') }]}
              extra="发送给 Agent 的消息内容"
            >
              <TextArea rows={3} placeholder={t('Please_Input') + t('cron_message')} />
            </Form.Item>
          </>
        )}

        {/* 工具调用 (toolCall) */}
        {payloadKind === 'toolCall' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Form.Item
                name={['payload', 'tool_name']}
                label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_tool_name')}</span>}
                rules={[{ required: true, message: t('Please_Input') + t('cron_tool_name') }]}
                extra="要执行的工具名,如 call_agent / fire_trigger / execute_sql"
              >
                <Input size="large" placeholder="call_agent" />
              </Form.Item>
              <Form.Item
                name={['payload', 'workspace_id']}
                label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_workspace_id')}</span>}
                extra="工作空间 ID。设置后可装配该空间资源(DB/知识库)"
              >
                <InputNumber min={1} style={{ width: '100%' }} size="large" placeholder="可选" />
              </Form.Item>
            </div>
            <Form.Item
              name={['payload', 'tool_args']}
              label={<span className="font-medium text-[var(--ws-ink)]">{t('cron_tool_args')}</span>}
              rules={[
                {
                  validator: (_, value) => {
                    if (!value) return Promise.resolve();
                    try {
                      JSON.parse(value);
                      return Promise.resolve();
                    } catch {
                      return Promise.reject('tool_args 必须是合法 JSON');
                    }
                  },
                },
              ]}
              extra='工具参数 JSON,如 {"agent_id":"x","message":"hi","session_mode":"isolated"}'
            >
              <TextArea rows={4} placeholder='{"agent_id":"data_analyst","message":"生成报告"}' />
            </Form.Item>
          </>
        )}
      </section>
    </Form>
  );
}