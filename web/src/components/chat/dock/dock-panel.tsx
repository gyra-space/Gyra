import React, { useEffect, useMemo, useRef, useState } from 'react';
import classNames from 'classnames';
import { CheckOutlined, DownOutlined, LoadingOutlined, UpOutlined } from '@ant-design/icons';
import { dockWidgetRegistry } from './dock-widget-registry';
import type { DockWidget } from './dock-types';
import { VisSystemEvents } from '@/components/chat/chat-content-components/VisComponents/VisSystemEvents';
import type { SystemEventsData } from '@/components/chat/chat-content-components/VisComponents/VisSystemEvents';

/**
 * 输入框上方固定区域（Composer Dock）— 单行 tab 栏 + 固定高度展开面板。
 *
 * - systemEvents（仅 manus 布局传入）作为第一个 tab「状态」，其余按 widgets
 *   查注册表生成 tab；未知 `type` 静默忽略（前向兼容）。
 * - 有进行中内容（is_running / working todo / running 子任务）时自动展开并
 *   切到第一个运行中的 tab；全部结束后自动收起为一行。手动展开/收起作用到
 *   下一个运行状态边沿为止。
 * - 无任何 tab 时不渲染。
 */

interface DockTab {
  key: string;
  /** widget.type，system_events tab 为 undefined；用于默认 tab 优先选中待办。 */
  type?: string;
  label: React.ReactNode;
  /** 运行指示：有 icon 时渲染 icon，否则渲染脉冲点。 */
  running: boolean;
  icon?: React.ReactNode;
  content: React.ReactNode;
}

const SYSTEM_EVENTS_KEY = 'system_events';

function buildSystemEventsTab(data: SystemEventsData): DockTab {
  const hasError =
    !data.is_running && (data.recent_events?.some(e => e.status === 'failed') ?? false);

  let icon: React.ReactNode;
  let text: string;
  let textColor: string | undefined;
  if (hasError) {
    icon = <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />;
    text = '执行出错';
    textColor = '#ef4444';
  } else if (data.is_running) {
    icon = <LoadingOutlined className="text-[#6366f1] text-[11px]" spin />;
    text = data.current_action || data.recent_events?.[0]?.title || '初始化中...';
    textColor = '#6366f1';
  } else {
    icon = <CheckOutlined className="text-green-500 text-[11px]" />;
    text = '执行完成';
  }

  return {
    key: SYSTEM_EVENTS_KEY,
    label: <span style={textColor ? { color: textColor } : undefined}>{text}</span>,
    running: !!data.is_running,
    icon,
    content: <VisSystemEvents data={data} embedded />,
  };
}

interface DockPanelProps {
  widgets: Record<string, DockWidget>;
  /** 仅 manus 布局传入；callsite 已完成 is_running && isProcessing 兜底合并。 */
  systemEvents?: SystemEventsData | null;
}

const DockPanel: React.FC<DockPanelProps> = ({ widgets, systemEvents }) => {
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const prevActiveRef = useRef(false);

  const tabs = useMemo<DockTab[]>(() => {
    const list: DockTab[] = [];
    if (systemEvents) {
      // 与原 VisSystemEvents 一致：非运行且无事件无耗时则不展示
      const empty =
        !systemEvents.is_running &&
        (!systemEvents.recent_events || systemEvents.recent_events.length === 0) &&
        !systemEvents.total_duration_ms;
      if (!empty) list.push(buildSystemEventsTab(systemEvents));
    }
    for (const widget of Object.values(widgets)) {
      const reg = dockWidgetRegistry[widget.type];
      if (!reg) continue;
      list.push({
        key: widget.id,
        type: widget.type,
        label: reg.getLabel(widget.payload),
        running: reg.isRunning(widget.payload),
        content: <reg.component widget={widget} embedded />,
      });
    }
    return list;
  }, [widgets, systemEvents]);

  const hasActiveContent = tabs.some(t => t.running);

  // 默认 tab：多个内容时优先待办列表，其次第一个运行中的 tab
  const defaultKey =
    (tabs.find(t => t.type === 'todo_list') ?? tabs.find(t => t.running) ?? tabs[0])?.key ?? null;

  // 运行状态边沿驱动自动展开/收起；两次边沿之间的手动操作不被打断
  useEffect(() => {
    const prev = prevActiveRef.current;
    prevActiveRef.current = hasActiveContent;
    if (hasActiveContent === prev) return;
    setExpanded(hasActiveContent);
    if (hasActiveContent) {
      setActiveKey(defaultKey);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActiveContent]);

  if (tabs.length === 0) return null;

  const currentKey = tabs.some(t => t.key === activeKey) ? activeKey! : defaultKey!;

  const handleTabClick = (key: string) => {
    if (key === currentKey) {
      setExpanded(!expanded);
    } else {
      setActiveKey(key);
      setExpanded(true);
    }
  };

  const activeTab = tabs.find(t => t.key === currentKey);

  return (
    <div className="w-full overflow-hidden mb-2 rounded-2xl border border-[#e5e7eb] dark:border-gray-700 bg-white dark:bg-[#232734] shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      {/* 单行 tab 栏 */}
      <div className="flex items-center h-9 px-2 gap-1">
        {tabs.map(tab => {
          const isActive = tab.key === currentKey;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabClick(tab.key)}
              className={classNames(
                'flex items-center gap-1.5 px-2.5 h-7 rounded-md text-xs transition-colors min-w-0',
                isActive
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-medium'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800',
              )}
            >
              {tab.icon ??
                (tab.running && (
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse flex-shrink-0" />
                ))}
              <span className="truncate max-w-[160px]">{tab.label}</span>
            </button>
          );
        })}
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center justify-center w-7 h-7 rounded-md text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300 transition-colors flex-shrink-0"
        >
          {expanded ? <UpOutlined className="text-[11px]" /> : <DownOutlined className="text-[11px]" />}
        </button>
      </div>

      {/* 固定高度内容区，内部滚动 */}
      {expanded && activeTab && (
        <div className="h-40 overflow-y-auto border-t border-gray-100 dark:border-gray-700">
          {activeTab.content}
        </div>
      )}
    </div>
  );
};

export default DockPanel;
