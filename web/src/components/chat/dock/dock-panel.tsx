import React, { useEffect, useMemo, useRef, useState } from 'react';
import classNames from 'classnames';
import { CheckOutlined, DownOutlined, LoadingOutlined, UpOutlined } from '@ant-design/icons';
import { dockWidgetRegistry } from './dock-widget-registry';
import type { DockWidget } from './dock-types';
import { VisSystemEvents } from '@/components/chat/chat-content-components/VisComponents/VisSystemEvents';
import type { SystemEventsData } from '@/components/chat/chat-content-components/VisComponents/VisSystemEvents';

/**
 * 输入框上方贴合区域（Composer Dock）— 参考 Manus/GLM 的「单行摘要 + 向上展开」：
 *
 * - 折叠行：左侧各 widget 图标（多个时可点击切换，运行中带脉冲点），中间当前
 *   widget 摘要（进行中/最近一条的标题），右侧进度（3/3）+ 展开箭头；
 *   单 widget 时图标内联在摘要里。点击摘要/箭头切换展开。
 * - systemEvents（仅 manus 布局传入）作为第一个 widget「状态」，其余按 widgets
 *   查注册表生成；未知 `type` 静默忽略（前向兼容）。
 * - 默认折叠，不自动展开；全部结束后自动收起为一行。手动展开/收起不被运行状态打断。
 * - 无任何 widget 时不渲染。
 */

interface DockTab {
  key: string;
  /** widget.type，system_events 为 undefined；用于默认 tab 优先选中待办。 */
  type?: string;
  /** 折叠行摘要主文本。 */
  title: React.ReactNode;
  titleColor?: string;
  /** 折叠行右侧进度，如 `3/3`。 */
  progress?: React.ReactNode;
  running: boolean;
  /** 折叠行左侧图标。 */
  icon: React.ReactNode;
  content: React.ReactNode;
}

const SYSTEM_EVENTS_KEY = 'system_events';

function buildSystemEventsTab(data: SystemEventsData): DockTab {
  const hasError =
    !data.is_running && (data.recent_events?.some(e => e.status === 'failed') ?? false);

  let icon: React.ReactNode;
  let title: string;
  let titleColor: string | undefined;
  if (hasError) {
    icon = <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />;
    title = '执行出错';
    titleColor = '#ef4444';
  } else if (data.is_running) {
    icon = <LoadingOutlined className="text-[#6366f1] text-[11px]" spin />;
    title = data.current_action || data.recent_events?.[0]?.title || '初始化中...';
    titleColor = '#6366f1';
  } else {
    icon = <CheckOutlined className="text-green-500 text-[11px]" />;
    title = '执行完成';
  }

  return {
    key: SYSTEM_EVENTS_KEY,
    title,
    titleColor,
    icon,
    running: !!data.is_running,
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
        title: reg.getTitle(widget.payload),
        progress: reg.getProgress?.(widget.payload),
        running: reg.isRunning(widget.payload),
        icon: reg.icon,
        content: <reg.component widget={widget} embedded />,
      });
    }
    return list;
  }, [widgets, systemEvents]);

  const hasActiveContent = tabs.some(t => t.running);

  // 默认 tab：多个内容时优先待办列表，其次第一个运行中的 tab
  const defaultKey =
    (tabs.find(t => t.type === 'todo_list') ?? tabs.find(t => t.running) ?? tabs[0])?.key ?? null;

  // 默认保持折叠，不自动展开；仅在「全部结束」边沿自动收起为一行。
  // 手动展开/收起不被运行状态打断。
  useEffect(() => {
    const prev = prevActiveRef.current;
    prevActiveRef.current = hasActiveContent;
    if (hasActiveContent === prev) return;
    if (!hasActiveContent) {
      setExpanded(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActiveContent]);

  if (tabs.length === 0) return null;

  const currentKey = tabs.some(t => t.key === activeKey) ? activeKey! : defaultKey!;
  const activeTab = tabs.find(t => t.key === currentKey);
  const toggleExpanded = () => setExpanded(!expanded);

  return (
    // -mb-4 让输入框卡片向上叠 16px 盖住 dock 底部(底部垫高区),dock 不定位,
    // 输入框(relative)自然绘制在上层 — 呈「输入框压在 dock 上」的贴合效果。
    <div className="w-[calc(100%-44px)] mx-[22px] overflow-hidden -mb-4 rounded-2xl border border-[#e5e7eb] dark:border-gray-700 bg-white dark:bg-[#232734]">
      {/* 单行摘要栏 */}
      <div className="flex items-center h-10 pl-3 pr-2 gap-1.5">
        {/* 多 widget 时：左侧图标切换器 */}
        {tabs.length > 1 && (
          <div className="flex items-center gap-0.5 flex-shrink-0">
            {tabs.map(tab => {
              const isActive = tab.key === currentKey;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveKey(tab.key)}
                  className={classNames(
                    'relative w-6 h-6 rounded-md flex items-center justify-center text-[13px] transition-colors',
                    isActive
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200'
                      : 'text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800',
                  )}
                >
                  {tab.icon}
                  {tab.running && (
                    <span className="absolute top-0 right-0 w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                  )}
                </button>
              );
            })}
            <div className="w-px h-4 bg-gray-200 dark:bg-gray-600 mx-1 flex-shrink-0" />
          </div>
        )}

        {/* 摘要区：点击切换展开 */}
        <button
          type="button"
          onClick={toggleExpanded}
          className="flex-1 flex items-center gap-2 min-w-0 text-left"
        >
          {tabs.length === 1 && activeTab && (
            <span className="flex-shrink-0 text-[13px] text-gray-400 inline-flex items-center">
              {activeTab.icon}
            </span>
          )}
          {tabs.length === 1 && activeTab?.type && activeTab.running && (
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse flex-shrink-0" />
          )}
          <span
            className="truncate text-[13px] text-gray-700 dark:text-gray-200"
            style={activeTab?.titleColor ? { color: activeTab.titleColor } : undefined}
          >
            {activeTab?.title}
          </span>
        </button>

        {activeTab?.progress && (
          <span className="flex-shrink-0 text-xs text-gray-400">{activeTab.progress}</span>
        )}
        <button
          type="button"
          onClick={toggleExpanded}
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

      {/* 底部叠合垫高区：被输入框顶边覆盖，避免遮住上面的内容 */}
      <div className="h-4" />
    </div>
  );
};

export default DockPanel;
