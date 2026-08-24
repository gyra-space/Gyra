'use client';

/**
 * 单次模型调用详情抽屉（排查定位）。
 *
 * 懒加载 GET /api/v1/chat/dialogue/call-details?con_uid= ，按 conv 还原每次模型调用的
 * 输入（system/user 提示词）、输出、工具列表、工具调用与性能指标。
 * 与参考工具一致的 tab：模型选用 / 模型输出 / 工具列表 / 工具调用 / 系统提示词 / 用户提示词。
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Drawer, Tabs, Tag, Empty, Spin, Descriptions, Typography, Space } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import { getChatCallDetails } from '@/client/api/request';
import { apiInterceptors } from '@/client/api';
import type { IChatDialogueCallDetail } from '@/types/chat';
import { formatTokens } from '@/types/context-metrics';

const { Text, Paragraph } = Typography;

interface ConversationCallDetailDrawerProps {
  /** 会话 ID（conv_id 或 conv_session_id） */
  convId?: string;
  open: boolean;
  onClose: () => void;
  /** 打开时定位到某条消息（message_id，对应某次模型调用），为空则默认第一条 */
  activeMessageId?: string;
}

function formatTs(ms?: number | null): string {
  if (!ms) return '-';
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return '-';
  return `${d.getHours().toString().padStart(2, '0')}:${d
    .getMinutes()
    .toString()
    .padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
}

function formatDurationMs(start?: number | null, end?: number | null): string {
  if (!start || !end) return '-';
  const s = Math.max(0, (end - start) / 1000);
  return `${s.toFixed(1)}s`;
}

function jsonCell(value: unknown): React.ReactNode {
  if (value === undefined || value === null || value === '') {
    return <Text type="secondary">（无）</Text>;
  }
  if (typeof value === 'string') {
    return <pre className="m-0 whitespace-pre-wrap break-words font-mono text-xs">{value}</pre>;
  }
  return <pre className="m-0 whitespace-pre-wrap break-words font-mono text-xs">{JSON.stringify(value, null, 2)}</pre>;
}

function toolNames(inputTools: unknown): string[] {
  if (!inputTools) return [];
  if (Array.isArray(inputTools)) {
    return inputTools.map((t: any) =>
      typeof t === 'string' ? t : t?.name || t?.function?.name || JSON.stringify(t),
    );
  }
  return [String(inputTools)];
}

export const ConversationCallDetailDrawer: React.FC<ConversationCallDetailDrawerProps> = ({
  convId,
  open,
  onClose,
  activeMessageId,
}) => {
  const [calls, setCalls] = useState<IChatDialogueCallDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeKey, setActiveKey] = useState<string>('model');
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (open) {
      setSelectedId(activeMessageId);
    }
  }, [open, activeMessageId]);

  useEffect(() => {
    if (!open || !convId) return;
    let cancelled = false;
    setLoading(true);
    setCalls([]);
    apiInterceptors(getChatCallDetails(convId))
      .then(([err, res]) => {
        if (cancelled) return;
        setCalls(err ? [] : res || []);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, convId]);

  const targetId = selectedId ?? activeMessageId;
  const activeCall = useMemo(() => {
    if (!calls.length) return null;
    if (targetId) {
      const found = calls.find((c) => c.message_id === targetId);
      if (found) return found;
    }
    return calls[0];
  }, [calls, targetId]);

  const llm = (activeCall?.metrics as any)?.llm_metrics || {};

  const selectedItems = useMemo(() => {
    if (!activeCall) return [];
    return [
      { key: 'model', label: '模型选用' },
      { key: 'output', label: '模型输出' },
      { key: 'tools', label: '工具列表' },
      { key: 'calls', label: '工具调用' },
      { key: 'sys', label: '系统提示词' },
      { key: 'user', label: '用户提示词' },
    ];
  }, [activeCall]);

  const tabContent: Record<string, React.ReactNode> = useMemo(() => {
    if (!activeCall) return {};
    const metricsRow = (
      <Descriptions column={1} size="small">
        <Descriptions.Item label="模型名">{activeCall.model_name || '-'}</Descriptions.Item>
        <Descriptions.Item label="total_token">
          {llm.total_tokens != null ? formatTokens(llm.total_tokens) : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="output_token">
          {llm.completion_tokens != null ? formatTokens(llm.completion_tokens) : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="速度">
          {llm.speed_per_second != null ? `${llm.speed_per_second.toFixed(2)} tok/s` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="耗时">
          {formatDurationMs(llm.start_time_ms, llm.end_time_ms)}
        </Descriptions.Item>
        <Descriptions.Item label="开始时间">{formatTs(llm.start_time_ms)}</Descriptions.Item>
        <Descriptions.Item label="首 token 耗时">
          {llm.first_token_time_ms != null
            ? `${((llm.first_token_time_ms - llm.start_time_ms) / 1000).toFixed(2)}s`
            : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="首 completion">
          {llm.first_completion_time_ms != null
            ? `${((llm.first_completion_time_ms - llm.start_time_ms) / 1000).toFixed(2)}s`
            : '-'}
        </Descriptions.Item>
      </Descriptions>
    );

    return {
      model: (
        <div>
          {metricsRow}
          <div className="mt-2 whitespace-pre-wrap break-words font-mono text-xs text-gray-400">
            metrics.llm_metrics = {JSON.stringify(llm, null, 2)}
          </div>
        </div>
      ),
      output: (
        <div>
          {activeCall.thinking ? (
            <Paragraph className="mb-2 whitespace-pre-wrap text-sm text-gray-500">
              思考：{activeCall.thinking}
            </Paragraph>
          ) : null}
          {jsonCell(activeCall.content ?? activeCall.observation)}
        </div>
      ),
      tools: (
        <Space wrap>
          {toolNames(activeCall.input_tools).map((n, i) => (
            <Tag color="blue" key={`${n}-${i}`}>
              {n}
            </Tag>
          ))}
        </Space>
      ),
      calls: <>{jsonCell(activeCall.tool_calls)}</>,
      sys: <>{jsonCell(activeCall.system_prompt)}</>,
      user: <>{jsonCell(activeCall.user_prompt)}</>,
    };
  }, [activeCall, llm]);

  return (
    <Drawer
      title={
        <Space>
          <BarChartOutlined />
          <span>单次调用还原（排查定位）</span>
        </Space>
      }
      placement="right"
      width={560}
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      <Spin spinning={loading}>
        {!(calls.length > 0) && !loading ? (
          <Empty description="暂无该会话的模型调用详情（老会话可能未记录）" />
        ) : (
          <>
            <Space wrap className="mb-2">
              {calls.map((c) => (
                <Tag
                  key={c.message_id || c.round}
                  color={c.message_id === targetId ? 'blue' : 'default'}
                  className="cursor-pointer"
                  onClick={() => {
                    setSelectedId(c.message_id);
                    setActiveKey('model');
                  }}
                >
                  {c.model_name || 'model'} · 第 {c.round ?? '-'} 轮
                </Tag>
              ))}
            </Space>
            {activeCall && (
              <Paragraph className="mt-2 rounded-md bg-gray-50 px-2 py-1 text-xs text-gray-500" type="secondary">
                第 {activeCall.round ?? '-'} 轮 · 使用 {activeCall.model_name || '-'} · 开始{' '}
                {formatTs((activeCall.metrics as any)?.llm_metrics?.start_time_ms)} · 耗时{' '}
                {formatDurationMs(
                  (activeCall.metrics as any)?.llm_metrics?.start_time_ms,
                  (activeCall.metrics as any)?.llm_metrics?.end_time_ms,
                )}
              </Paragraph>
            )}
            <Tabs
              activeKey={activeKey}
              onChange={setActiveKey}
              items={selectedItems.map((it) => ({ key: it.key, label: it.label }))}
            />
            <div className="mt-2">{tabContent[activeKey]}</div>
          </>
        )}
      </Spin>
    </Drawer>
  );
};

export default ConversationCallDetailDrawer;
