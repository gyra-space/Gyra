'use client';

/**
 * 场景空间「简洁模式」待办收件箱:抽屉/弹层里展示真实待办列表(listInbox),
 * 与运维模式 SceneTaskRail 的「待办」视图同源同渲染,但聚焦在抽屉场景:
 * 来源筛选 + 快速处理(manual 标记完成 / ecp_proposal 确认生效),
 * 点击条目由外层决定跳转(任务对话 / 介入 / 提案)。
 */

import { useCallback, useEffect, useState } from 'react';
import { App } from 'antd';
import { CheckOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { apiInterceptors } from '@/client/api';
import { listInbox, updateInboxStatus, type InboxItem } from '@/client/api/workspace';
import { confirmEcpObject } from '@/client/api/ecp';
import { getUserId } from '@/utils';
import { parseEcpProposalSource } from './scene-task-rail';

const SOURCE_LABEL: Record<string, string> = {
  all: '全部',
  task: '任务',
  intervention: '介入',
  ecp_proposal: '提案',
  manual: '手动',
};

interface SceneSimpleInboxProps {
  workspaceId?: number;
  disabled?: boolean;
  /** 点击待办条目:由外层决定跳转/打开(关闭抽屉 + 进入任务/介入/提案) */
  onOpenItem: (item: InboxItem) => void;
  /** 快速处理后通知外层(刷新任务/介入等列表) */
  onResolved?: () => void;
}

export function SceneSimpleInbox({ workspaceId, disabled, onOpenItem, onResolved }: SceneSimpleInboxProps) {
  const { message } = App.useApp();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState('all');

  const refresh = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    const [err, res] = await apiInterceptors(listInbox(workspaceId));
    setLoading(false);
    if (err) return;
    setItems(Array.isArray(res) ? res : ((res as { data?: InboxItem[] } | null)?.data || []));
  }, [workspaceId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // 快速处理协议:与运维模式 rail 一致 —— manual 自含待办直接完成,
  // ecp_proposal 源端确认生效;task/intervention 需进入处理,不提供一键完成。
  const quickResolveMap: Record<
    string,
    { title: string; run: (item: InboxItem) => Promise<{ ok: boolean; msg?: string }> } | null
  > = {
    manual: {
      title: '标记完成',
      run: async (item) => {
        if (!workspaceId) return { ok: false, msg: '缺少工作区' };
        const [err] = await apiInterceptors(updateInboxStatus(workspaceId, item.id, 'done'));
        if (err) return { ok: false, msg: err.message };
        return { ok: true };
      },
    },
    ecp_proposal: {
      title: '确认生效',
      run: async (item) => {
        const parsed = parseEcpProposalSource(item.source_id);
        if (!parsed) return { ok: false, msg: '提案来源无法解析,请打开提案详情处理' };
        const userId = String(getUserId() ?? 'unknown');
        const [err] = await apiInterceptors(
          confirmEcpObject(parsed.objId, parsed.version, {
            user_id: userId,
            workspace_id: parsed.workspaceId,
          }),
        );
        if (err) return { ok: false, msg: err.message };
        return { ok: true };
      },
    },
    task: null,
    intervention: null,
  };

  const handleDone = async (item: InboxItem) => {
    if (!workspaceId) return;
    const action = quickResolveMap[item.source_type];
    if (!action) return;
    const { ok, msg } = await action.run(item);
    if (!ok) { message.error(msg || '处理失败'); return; }
    message.success(`${action.title}成功`);
    refresh();
    onResolved?.();
  };

  const filtered = items.filter((it) => source === 'all' || it.source_type === source);

  return (
    <div className="ws-simple-inbox">
      <div className="ws-rail-inbox-filter">
        {(['all', 'intervention', 'ecp_proposal', 'task', 'manual'] as const).map((s) => {
          const count = s === 'all'
            ? items.length
            : items.filter((it) => it.source_type === s).length;
          if (s !== 'all' && count === 0 && source !== s) return null;
          return (
            <span
              key={s}
              role="button"
              tabIndex={0}
              className={`ws-rail-inbox-chip${source === s ? ' ws-rail-inbox-chip--on' : ''}`}
              onClick={() => setSource(s)}
              onKeyDown={(e) => { if (e.key === 'Enter') setSource(s); }}
            >
              {SOURCE_LABEL[s] || s}{count > 0 ? ` ${count}` : ''}
            </span>
          );
        })}
      </div>
      {loading && (
        <div className="ws-rail-empty"><div className="ws-rail-empty-t">加载中...</div></div>
      )}
      {!loading && items.length === 0 && (
        <div className="ws-rail-inbox-clear">
          <CheckOutlined />
          <span>待办已清空</span>
        </div>
      )}
      {filtered.map((item) => (
        <div
          key={item.id}
          role="button"
          tabIndex={0}
          className={`ws-rail-card ws-rail-card--inbox${item.inbox_status === 'doing' ? ' ws-rail-card--inbox-doing' : ''}`}
          onClick={() => !disabled && onOpenItem(item)}
          onKeyDown={(e) => {
            if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              onOpenItem(item);
            }
          }}
        >
          <div className="ws-rail-ttl">{item.title}</div>
          <div className="ws-rail-meta">
            <span className="ws-rail-src">{SOURCE_LABEL[item.source_type] || item.source_type}</span>
            <span className="ws-rail-meta-sep">·</span>
            <span>{item.visibility === 'shared' ? '共享' : '个人'}</span>
            {item.inbox_status === 'doing' && (
              <>
                <span className="ws-rail-meta-sep">·</span>
                <span>处理中</span>
              </>
            )}
          </div>
          <div className="ws-rail-foot">
            <span className="ws-rail-tm">{dayjs(item.gmt_modified).format('MM-DD HH:mm')}</span>
            <div className="ws-rail-card-actions">
              {item.inbox_status !== 'done' && quickResolveMap[item.source_type] ? (
                <span
                  role="button"
                  tabIndex={0}
                  title={quickResolveMap[item.source_type]?.title}
                  className="ws-rail-card-act"
                  onClick={(e) => { e.stopPropagation(); void handleDone(item); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); void handleDone(item); } }}
                >
                  <CheckOutlined />
                </span>
              ) : item.inbox_status !== 'done' ? (
                <span className="ws-rail-int-hint">点击进入处理</span>
              ) : null}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
