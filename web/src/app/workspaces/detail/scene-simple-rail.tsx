'use client';

/**
 * 场景空间「简洁模式」左栏:仅历史任务/会话列表 + 待办角标入口。
 * 与运维模式的 SceneTaskRail 共享数据源(tasks/conversations/interventions),
 * 但不做收件箱/状态 tab/批量操作,保持「一个能干的列表」。
 */

import { useMemo, useState } from 'react';
import { Input } from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  InboxOutlined,
  PlusOutlined,
  RightOutlined,
  SearchOutlined,
  StarFilled,
  StarOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { ConversationUsageChip } from '@/components/chat/ConversationUsageChip';
import type { ConversationUsageSummary } from '@/client/api/usage';
import { toConversationId } from '@/types/context-metrics';

export interface SimpleHistoryItem {
  key: string;
  kind: 'task' | 'lobby';
  id: number | string;
  title: string;
  status: 'running' | 'done' | 'failed' | 'waiting';
  statusLabel: string;
  updatedAt: string;
  conversationId?: string;
  taskId?: number | null;
  /** 收藏状态(挂在对应会话 conv 上) */
  isFavorited?: boolean;
  /** 是否当前已选中的会话/任务(由外层按 conversationId/taskId 判定) */
  active?: boolean;
}

interface SceneSimpleRailProps {
  items: SimpleHistoryItem[];
  /** 当前会话 conv_uid(用于高亮) */
  currentConvUid?: string;
  /** 当前任务 id(用于高亮) */
  currentTaskId?: number | null;
  /** 待办数量:>0 时底部入口点亮红点 */
  inboxCount?: number;
  disabled?: boolean;
  onOpenItem?: (item: SimpleHistoryItem) => void;
  onNewConversation?: () => void;
  onOpenInbox?: () => void;
  /** 会话级用量（模型 + token）map，key=conversationId，用于列表 chip 展示 */
  usageMap?: Record<string, ConversationUsageSummary>;
  /** 删除单个历史项(任务/会话)。按 kind 由外层决定调用任务/会话删除接口。 */
  onDeleteItem?: (item: SimpleHistoryItem) => void;
  /** 重命名会话项(lobby)。由外层弹窗收集新名称并调用重命名接口。 */
  onRenameItem?: (item: SimpleHistoryItem) => void;
  /** 收藏/取消收藏历史项。由外层调用收藏接口。 */
  onToggleFavorite?: (item: SimpleHistoryItem) => void;
  /** 是否允许删除任务项(space.task.manage) */
  canDeleteTask?: boolean;
  /** 是否允许删除会话项(space.chat.use) */
  canDeleteConversation?: boolean;
  /** 是否允许重命名会话项(space.chat.use) */
  canRenameConversation?: boolean;
  /** 是否允许收藏会话(space.chat.use) */
  canFavoriteConversation?: boolean;
}

function StatusDot({ status }: { status: SimpleHistoryItem['status'] }) {
  if (status === 'running') return <span className="ws-simple-item__dot ws-simple-item__dot--running" />;
  if (status === 'waiting') return <span className="ws-simple-item__dot ws-simple-item__dot--waiting" />;
  if (status === 'failed') return <span className="ws-simple-item__dot ws-simple-item__dot--failed" />;
  return <span className="ws-simple-item__dot ws-simple-item__dot--done" />;
}

/** 时间分段:今天/昨天/本周/更早 */
function segLabel(iso: string): string {
  if (!iso) return '更早';
  const d = dayjs(iso);
  if (!d.isValid()) return '更早';
  const now = dayjs();
  if (d.isSame(now, 'day')) return '今天';
  if (d.isSame(now.subtract(1, 'day'), 'day')) return '昨天';
  if (d.isAfter(now.startOf('week'))) return '本周';
  return '更早';
}

function fmtTime(iso: string): string {
  if (!iso) return '—';
  const d = dayjs(iso);
  return d.isValid() ? d.format('MM-DD HH:mm') : '—';
}

export function SceneSimpleRail({
  items,
  currentConvUid,
  currentTaskId,
  inboxCount = 0,
  disabled,
  onOpenItem,
  onNewConversation,
  onOpenInbox,
  usageMap = {},
  onDeleteItem,
  onRenameItem,
  onToggleFavorite,
  canDeleteTask,
  canDeleteConversation,
  canRenameConversation,
  canFavoriteConversation,
}: SceneSimpleRailProps) {
  const [filter, setFilter] = useState('');
  const [collapsedSegs, setCollapsedSegs] = useState<Set<string>>(() => new Set());

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (it) =>
        it.title.toLowerCase().includes(q) ||
        String(it.id).toLowerCase().includes(q) ||
        (it.conversationId || '').toLowerCase().includes(q),
    );
  }, [items, filter]);

  const groups = useMemo(() => {
    const out: Array<{ label: string; items: SimpleHistoryItem[] }> = [];
    // 收藏分组置顶:已收藏项只出现在收藏分组,不再重复进入时间段
    const favs = filtered.filter((it) => it.isFavorited);
    if (favs.length > 0) {
      out.push({ label: '收藏', items: favs });
    }
    let last = '';
    filtered.forEach((item) => {
      if (item.isFavorited) return;
      const seg = segLabel(item.updatedAt);
      if (seg !== last) {
        out.push({ label: seg, items: [] });
        last = seg;
      }
      out[out.length - 1].items.push(item);
    });
    return out;
  }, [filtered]);

  const toggleSeg = (label: string) => {
    setCollapsedSegs((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  return (
    <div className="ws-simple-rail">
      <div className="ws-simple-rail__head">
        <span className="ws-simple-rail__title">历史任务</span>
        <button
          type="button"
          className="ws-simple-rail__new"
          onClick={onNewConversation}
          disabled={disabled}
        >
          <PlusOutlined /> 新任务
        </button>
      </div>
      <div className="ws-simple-rail__search">
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索任务…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          size="small"
        />
      </div>
      <div className="ws-simple-rail__list">
        {filtered.length === 0 && (
          <div className="ws-simple-rail__empty">
            <div className="ws-simple-rail__empty-t">暂无历史任务</div>
            <div className="ws-simple-rail__empty-h">在右侧输入框发起第一个任务</div>
          </div>
        )}
        {groups.map((g) => {
          const isCollapsed = collapsedSegs.has(g.label);
          return (
            <div key={`seg-${g.label}`} className="ws-simple-rail__group">
              <div
                className="ws-simple-rail__seg"
                role="button"
                tabIndex={0}
                onClick={() => toggleSeg(g.label)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleSeg(g.label);
                  }
                }}
              >
                <span className={`ws-simple-rail__seg-caret${isCollapsed ? ' ws-simple-rail__seg-caret--closed' : ''}`}>
                  <RightOutlined />
                </span>
                <span className="ws-simple-rail__seg-label">{g.label}</span>
                <span className="ws-simple-rail__seg-count">{g.items.length}</span>
              </div>
              {!isCollapsed &&
                g.items.map((it) => {
                  const isActive =
                    it.active ||
                    (it.kind === 'task' && it.taskId != null && it.taskId === currentTaskId) ||
                    (it.conversationId != null && it.conversationId === currentConvUid);
                  // 悬浮操作胶囊:收藏/重命名/删除,按权限与回调逐项启用。
                  const canFavorite = !disabled && !!onToggleFavorite && !!it.conversationId && !!canFavoriteConversation;
                  const canRename = !disabled && !!onRenameItem && it.kind === 'lobby' && !!canRenameConversation;
                  const canDelete = !disabled && !!onDeleteItem && (
                    (it.kind === 'task' && !!canDeleteTask) ||
                    (it.kind === 'lobby' && !!canDeleteConversation)
                  );
                  return (
                    <div
                      key={it.key}
                      className={`ws-simple-item${isActive ? ' ws-simple-item--active' : ''}`}
                    role={disabled ? undefined : 'button'}
                    tabIndex={disabled ? -1 : 0}
                    aria-disabled={disabled}
                    onClick={() => !disabled && onOpenItem?.(it)}
                    onKeyDown={(e) => {
                      if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        onOpenItem?.(it);
                      }
                    }}
                  >
                      <StatusDot status={it.status} />
                      <div className="ws-simple-item__tx">
                        <div className="ws-simple-item__ti">{it.title}</div>
                        <div className="ws-simple-item__tm">
                          {fmtTime(it.updatedAt)} · {it.statusLabel}
                        </div>
                        {it.conversationId && usageMap[toConversationId(it.conversationId)] && (
                          <div className="ws-simple-item__usage">
                            <ConversationUsageChip summary={usageMap[toConversationId(it.conversationId)]} />
                          </div>
                        )}
                      </div>
                      {it.isFavorited && (
                        <span className="ws-simple-item__favflag" aria-label="已收藏">
                          <StarFilled />
                        </span>
                      )}
                      {(canFavorite || canRename || canDelete) && (
                        <div
                          className="ws-simple-item__ops"
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => e.stopPropagation()}
                        >
                          {canFavorite && (
                            <span
                              className={`ws-simple-item__op ws-simple-item__op--fav${it.isFavorited ? ' ws-simple-item__op--on' : ''}`}
                              role="button"
                              tabIndex={-1}
                              title={it.isFavorited ? '取消收藏' : '收藏'}
                              aria-label={it.isFavorited ? '取消收藏' : '收藏'}
                              onClick={(e) => { e.stopPropagation(); onToggleFavorite?.(it); }}
                              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onToggleFavorite?.(it); } }}
                            >
                              {it.isFavorited ? <StarFilled /> : <StarOutlined />}
                            </span>
                          )}
                          {canRename && (
                            <span
                              className="ws-simple-item__op ws-simple-item__op--rename"
                              role="button"
                              tabIndex={-1}
                              title="重命名"
                              aria-label="重命名"
                              onClick={(e) => { e.stopPropagation(); onRenameItem?.(it); }}
                              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onRenameItem?.(it); } }}
                            >
                              <EditOutlined />
                            </span>
                          )}
                          {canDelete && (
                            <span
                              className="ws-simple-item__op ws-simple-item__op--delete"
                              role="button"
                              tabIndex={-1}
                              title="删除"
                              aria-label="删除"
                              onClick={(e) => { e.stopPropagation(); onDeleteItem?.(it); }}
                              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onDeleteItem?.(it); } }}
                            >
                              <DeleteOutlined />
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          );
        })}
      </div>
      <button
        type="button"
        className={`ws-simple-rail__inbox${inboxCount > 0 ? ' ws-simple-rail__inbox--has' : ''}`}
        onClick={onOpenInbox}
        disabled={disabled}
      >
        <InboxOutlined />
        <span>待办收件箱</span>
        {inboxCount > 0 && <span className="ws-simple-rail__inbox-n">{inboxCount}</span>}
        <RightOutlined className="ws-simple-rail__inbox-arrow" />
      </button>
    </div>
  );
}
