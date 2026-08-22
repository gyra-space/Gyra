'use client';

import ChatContent from './chat-content';
import CompressionPoint from './compression-point';
import { ChatContentContext } from '@/contexts';
import { CompressionSegmentVo, IChatDialogueMessageSchema } from '@/types/chat';
import React, { memo, useContext, useEffect, useMemo, useRef, useState, useCallback } from 'react';
import ChatHeader from '../header/chat-header';
import UnifiedChatInput from '../input/unified-chat-input';
import { AgentAvatar } from '@/components/common/agent-avatar';
import { Tooltip } from 'antd';
import { LeftOutlined, DesktopOutlined, CloseOutlined } from '@ant-design/icons';
import classNames from 'classnames';
import { ee, EVENTS } from '@/utils/event-emitter';
import markdownComponents, { markdownPlugins } from '@/components/chat/chat-content-components/config';
import DockPanel from '@/components/chat/dock/dock-panel';
import { GPTVis } from '@antv/gpt-vis';
import { useSearchParams } from 'next/navigation';
import { AgentWorkspaceRenderer } from '@/app/workspaces/detail/agent-workspace-renderer';
import { buildManusWorkspaceView } from '@/app/workspaces/detail/manus-to-workspace-view';
import type { ManusRightPanelData } from '@/types/manus';
// 左栏「工作流」风格步骤进展复用 AgentWorkspaceRenderer,其布局样式(ws-*)来自场景空间 CSS,
// /chat 独立页默认不加载该 CSS,此处显式引入以避免左栏失去骨架样式。
import '@/app/workspaces/detail/scene-workspace.css';

type ShareMode = 'conversation' | 'process' | 'report' | null;

interface ManusChatContentProps {
  ctrl: AbortController;
  hideRightPanel?: boolean;
}

// Data size limits to prevent browser crash
const MAX_RENDER_COUNT = 200;          // Maximum number of messages to render (sliding window)
const MAX_CONTEXT_SIZE = 10_000_000;   // Maximum characters per message context (10MB)

/**
 * Check if a single message is too large to safely render
 */
const isMessageTooLarge = (msg: IChatDialogueMessageSchema): boolean => {
  return !!(msg.context && typeof msg.context === 'string' && msg.context.length > MAX_CONTEXT_SIZE);
};

/**
 * Extract the latest running_window and build routing maps for cross-round switching:
 * - fileRunningWindowMap: deliverable file_id → running_window
 *
 * Optimized: only scan the last N messages to reduce parsing overhead
 * Also tracks meta_window and the latest active_step id (for stream-follow logic).
 */
function useRunningWindows(
  showMessages: Array<IChatDialogueMessageSchema & { key: string }>
): {
  latestRunningWindow: string;
  latestHasData: boolean;
  fileRunningWindowMap: Map<string, string>;
  metaWindow: { total_steps?: number; visible_steps?: number; evicted_steps?: number } | null;
  latestActiveStepId: string | null;
} {
  return useMemo(() => {
    let latestRunningWindow = '';
    let latestActiveStepId: string | null = null;
    const fileMap = new Map<string, string>();
    let metaWindow: any = null;

    // Only scan the last 50 messages to reduce overhead
    const messagesToScan = showMessages.slice(-50);

    for (const msg of messagesToScan) {
      if (msg.role !== 'view') continue;
      try {
        const contextStr = msg.context;
        if (typeof contextStr !== 'string' || !contextStr.trim().startsWith('{')) continue;
        // Skip if context is too large to parse safely
        if (contextStr.length > MAX_CONTEXT_SIZE) continue;
        const context = JSON.parse(contextStr);
        const rw = context.running_window || '';

        // Parse meta_window if present
        if (context.meta_window) {
          try {
            metaWindow = typeof context.meta_window === 'string'
              ? JSON.parse(context.meta_window)
              : context.meta_window;
          } catch {
            // skip
          }
        }

        if (!rw) continue;

        latestRunningWindow = rw;

        // Parse manus-right-panel to index file_ids and step UIDs → this running_window
        const match = rw.match(/```manus-right-panel\s*\n([\s\S]*?)\n```/);
        if (match) {
          try {
            const data = JSON.parse(match[1]);

            // 跟踪最新 active step id,供流式阶段判断「新步骤开始」(同步骤的增量 chunk 不应清 override)
            if (data.active_step?.id) {
              latestActiveStepId = data.active_step.id;
            }

            // Index deliverable files
            for (const f of data.deliverable_files || []) {
              if (f.file_id) fileMap.set(f.file_id, rw);
            }
            if ((data.task_files || []).length > 0) {
              fileMap.set('task_files', rw);
            }
          } catch {
            // skip
          }
        }
      } catch {
        // Skip parse errors
      }
    }

    return {
      latestRunningWindow,
      latestHasData: !!latestRunningWindow,
      fileRunningWindowMap: fileMap,
      metaWindow,
      latestActiveStepId,
    };
  }, [showMessages]);
}

const ManusChatContent: React.FC<ManusChatContentProps> = ({ ctrl, hideRightPanel }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();
  const shareMode = (searchParams?.get('share_mode') as ShareMode) || null;
  const isSharedView = !!shareMode;
  const { history, compressionSegments, replyLoading, dockWidgets, appInfo, handleChat } = useContext(ChatContentContext);
  const [userClosedPanel, setUserClosedPanel] = useState(false);
  const [overrideRunningWindow, setOverrideRunningWindow] = useState<string | null>(null);
  // 状态事件 badge 数据(由 SystemEventsBridge 从消息流中桥接出来)
  const [systemEvents, setSystemEvents] = useState<any>(null);

  useEffect(() => {
    const handler = (data: any) => setSystemEvents(data);
    ee.on(EVENTS.SYSTEM_EVENTS, handler);
    return () => { ee.off(EVENTS.SYSTEM_EVENTS, handler); };
  }, []);

  // 会话清空/切换时重置 badge
  useEffect(() => {
    if (history.length === 0) setSystemEvents(null);
  }, [history.length]);

  // Sliding window: only render the last MAX_RENDER_COUNT messages, skip oversized ones
  const showMessages = useMemo(() => {
    const filtered = history
      .filter((item) => ['view', 'human'].includes(item.role) && !isMessageTooLarge(item));
    const windowed = filtered.length > MAX_RENDER_COUNT
      ? filtered.slice(-MAX_RENDER_COUNT)
      : filtered;
    return windowed.map((item, index) => ({
      ...item,
      key: `${item.role}_${item.order ?? index}`,
    }));
  }, [history]);

  const compressionPoints = useMemo(() => {
    const points: Record<number, CompressionSegmentVo> = {};
    if (!compressionSegments || compressionSegments.length === 0) return points;
    for (const seg of compressionSegments) {
      const covered = new Set(seg.source_message_ids);
      let lastIdx = -1;
      for (let i = 0; i < showMessages.length; i++) {
        const mid = showMessages[i].message_id;
        if (mid && covered.has(mid)) lastIdx = i;
      }
      if (lastIdx >= 0) points[lastIdx] = seg;
    }
    return points;
  }, [compressionSegments, showMessages]);

  const { latestRunningWindow, latestHasData, fileRunningWindowMap, metaWindow, latestActiveStepId } = useRunningWindows(showMessages);

  // The running window shown in right panel: override (from deliverable click) or latest
  const displayRunningWindow = overrideRunningWindow || latestRunningWindow;

  // 解析最新 manus-right-panel → WorkspaceView,驱动左栏「工作流」风格步骤进展(图2 简洁模式),
  // 替代原来的执行胶囊分组卡片。无数据时回退原有 planning_window 渲染。
  const manusRight = useMemo<ManusRightPanelData | null>(() => {
    const rw = displayRunningWindow || latestRunningWindow;
    if (!rw) return null;
    const fm = rw.match(/```manus-right-panel\s*\n([\s\S]*?)\n```/);
    if (!fm) return null;
    try {
      const parsed = JSON.parse(fm[1]);
      return parsed && typeof parsed === 'object' ? (parsed as ManusRightPanelData) : null;
    } catch {
      return null;
    }
  }, [displayRunningWindow, latestRunningWindow]);

  const workspaceView = useMemo(
    () => buildManusWorkspaceView(showMessages, manusRight),
    [showMessages, manusRight],
  );
  const hasWorkspaceSteps = workspaceView.execution.length > 0;

  // Agent 预设提问:优先取 appInfo.recommend_questions,兼容多种字段形态
  const recommendQuestions = useMemo(() => {
    const raw = appInfo?.recommend_questions || [];
    return raw
      .map((item) => {
        if (typeof item === 'string') return item;
        return item?.content || item?.question || item?.title || item?.text || String(item);
      })
      .filter((q): q is string => typeof q === 'string' && q.length > 0);
  }, [appInfo?.recommend_questions]);

  // When hideRightPanel is true, always hide the right panel (for workspace mode)
  const effectiveHideRightPanel = hideRightPanel || userClosedPanel;

  // Listen for panel open/close events
  useEffect(() => {
    const handleClose = () => setUserClosedPanel(true);
    const handleOpen = () => setUserClosedPanel(false);
    ee.on(EVENTS.CLOSE_PANEL, handleClose);
    ee.on(EVENTS.OPEN_PANEL, handleOpen);
    return () => {
      ee.off(EVENTS.CLOSE_PANEL, handleClose);
      ee.off(EVENTS.OPEN_PANEL, handleOpen);
    };
  }, []);

  // Listen for SWITCH_TAB to route deliverable clicks to the correct round's running_window
  useEffect(() => {
    const handleSwitchTab = (payload: { tab?: string }) => {
      if (!payload?.tab) return;
      const tab = payload.tab;
      // Check if this is a deliverable or task_files tab that needs a running_window switch
      if (tab.startsWith('deliverable_')) {
        const fileId = tab.replace('deliverable_', '');
        const rw = fileRunningWindowMap.get(fileId);
        if (rw && rw !== displayRunningWindow) {
          setOverrideRunningWindow(rw);
        }
      } else if (tab === 'task_files') {
        const rw = fileRunningWindowMap.get('task_files');
        if (rw && rw !== displayRunningWindow) {
          setOverrideRunningWindow(rw);
        }
      }
    };
    ee.on(EVENTS.SWITCH_TAB, handleSwitchTab);
    return () => {
      ee.off(EVENTS.SWITCH_TAB, handleSwitchTab);
    };
  }, [fileRunningWindowMap, displayRunningWindow]);

  // Step clicks (CLICK_FOLDER) are handled entirely by VisManusRightPanel:
  // it selects the step and lazy-fetches its outputs via /api/unified/vis/step_detail.
  // The parent no longer intercepts step clicks.

  // 流式数据到达时:自动展开右面板;但手动 override 只在「新步骤开始(active step id 变化)」时清。
  // 之前每个增量 chunk 都清 override,导致流式阶段点步骤右侧不变(被下个 chunk 立即覆盖)。
  const prevLatestRef = useRef(latestRunningWindow);
  const prevActiveStepRef = useRef<string | null>(null);
  useEffect(() => {
    if (prevActiveStepRef.current !== latestActiveStepId) {
      prevActiveStepRef.current = latestActiveStepId;
      if (replyLoading) {
        setOverrideRunningWindow(null);
      }
    }
    if (prevLatestRef.current !== latestRunningWindow) {
      prevLatestRef.current = latestRunningWindow;
      if (latestHasData) {
        setUserClosedPanel(false);
      }
    }
  }, [latestActiveStepId, latestRunningWindow, latestHasData, replyLoading]);

  // Auto-scroll
  useEffect(() => {
    setTimeout(() => {
      scrollRef.current?.scrollTo(0, scrollRef.current?.scrollHeight);
    }, 50);
  }, [history, history[history.length - 1]?.context]);

  const hasMessages = showMessages.length > 0;
  const isProcessing = replyLoading || (history.length > 0 && history[history.length - 1]?.thinking);
  // conversation: only left panel (chat-only, read-only)
  // process: both panels (read-only)
  // report: only right panel (deliverable content)
  // hideRightPanel: workspace mode - always hide right panel
  const isRightPanelVisible = hideRightPanel ? false
    : shareMode === 'conversation' ? false
    : shareMode === 'report' ? true
    : !userClosedPanel && latestHasData;
  const showLeftPanel = shareMode !== 'report';
  const showInput = !isSharedView;

  return (
    // 小屏(<1536px)整体 zoom:0.9:字体/组件等比缩小换取内容空间;zoom 只缩放 px 长度,
    // % 布局不受影响(已验证 h-full 容器无空隙)。
    // 用注入 <style> 而非 tailwind arbitrary class:本项目 tailwind important:true,
    // 场景空间(scene-workspace.css)需要用普通选择器复原嵌套场景下的双重缩放。
    <div className="manus-chat-root flex h-full w-full overflow-hidden bg-[#f7f7f8] dark:bg-[#151622]">
      <style dangerouslySetInnerHTML={{ __html: `
        @media (max-width: 1535px) {
          .manus-chat-root { zoom: 0.9; }
        }
      `}} />
      {/* ═══ Left panel — conversation on canvas ═══ */}
      {showLeftPanel && (
        <div className={classNames(
          'flex flex-col h-full transition-all duration-300 ease-out',
          isRightPanelVisible
            ? (shareMode as string) === 'report' ? 'hidden' : 'w-[44%] min-w-[300px] 2xl:w-[38%] 2xl:min-w-[340px]'
            : 'flex-1'
        )}>
          {/* Left header */}
          {!isSharedView ? (
            <ChatHeader isProcessing={isProcessing} />
          ) : (
            <div className="px-5 py-3">
              <div className="text-sm text-gray-500">共享对话 · 只读</div>
            </div>
          )}

          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto min-w-0" ref={scrollRef}>
            {hasWorkspaceSteps ? (
              /* 图2 简洁模式:工作流风格左栏(用户消息 → 工具步骤顺序流 → 最终结论) */
              <div className={classNames("w-full px-4 py-3", !isRightPanelVisible && "max-w-[768px] mx-auto")}>
                <div className="ws-manus-renderer">
                  <AgentWorkspaceRenderer
                    view={workspaceView}
                    running={isProcessing}
                    agentIcon={appInfo?.icon}
                    agentName={appInfo?.app_name}
                    onStepClick={(step) => {
                      if (step.type !== 'tool_call') return;
                      const convId = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('conv_uid') || '' : '';
                      ee.emit(EVENTS.CLICK_FOLDER, { uid: step.id, conv_id: convId });
                      ee.emit(EVENTS.OPEN_PANEL);
                    }}
                    onDeliverableClick={(file) => {
                      ee.emit(EVENTS.SWITCH_TAB, { tab: `deliverable_${file.file_id}` });
                    }}
                    onInteractionResume={(text) => handleChat?.(text)}
                  />
                </div>
              </div>
            ) : hasMessages ? (
              <div className={classNames("w-full px-4 py-3", !isRightPanelVisible && "max-w-[768px] mx-auto")}>
                <div className="w-full space-y-1.5">
                  {showMessages.map((content, index) => (
                    // content-visibility:auto 让浏览器跳过屏外消息的渲染,
                    // 长会话(200 条滑动窗口)下大幅降低布局/绘制成本
                    <div key={content.key} className="[content-visibility:auto] [contain-intrinsic-size:auto_200px] animate-rise">
                      <ChatContent content={content} messages={showMessages} compact />
                      {compressionPoints[index] && (
                        <CompressionPoint segment={compressionPoints[index]} />
                      )}
                    </div>
                  ))}
                  <div className="h-4" />
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center px-6">
                <div className="text-center max-w-md">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-white flex items-center justify-center overflow-hidden shadow-sm border border-[#eeeff3]">
                    <AgentAvatar
                      icon={appInfo?.icon}
                      name={appInfo?.app_name}
                      size={56}
                      rounded={false}
                    />
                  </div>
                  <h3 className="text-[16px] font-medium text-[#3b4154] mb-1">{appInfo?.app_name || 'Agent 工作台'}</h3>
                  <p className="text-[#8a92a6] text-[13px] mb-6">
                    {appInfo?.app_describe || '输入消息开始对话'}
                  </p>
                  {recommendQuestions.length > 0 && (
                    <div className="flex flex-wrap justify-center gap-2">
                      {recommendQuestions.map((q, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleChat?.(q)}
                          className="max-w-[260px] px-3 py-2 text-[13px] text-[#3b4154] bg-white border border-[#e5e8ef] rounded-lg hover:border-[#4f46e5] hover:text-[#4f46e5] transition-colors text-left truncate"
                          title={q}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          {showInput && (
            <div className={classNames("flex-shrink-0 pb-4 pt-2 px-4", !isRightPanelVisible && "max-w-3xl mx-auto w-full")}>
              <div className="w-full">
                {/* Composer Dock：独立卡片附着在输入框上方，展开/收起不改变输入框大小。
                    is_running 与流式状态联动兜底:流结束后即使后端未推终态,
                    也不再显示"转圈"。 */}
                <DockPanel
                  widgets={dockWidgets || {}}
                  systemEvents={
                    systemEvents
                      ? { ...systemEvents, is_running: !!systemEvents.is_running && isProcessing }
                      : null
                  }
                />
                <UnifiedChatInput
                  ctrl={ctrl}
                  showFloatingActions={hasMessages}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══ Right panel — floating white card ═══ */}
      {isRightPanelVisible && (
        <div
          className={classNames(
            'h-full transition-all duration-300 ease-out pt-2 pr-2 pb-2',
            shareMode === 'report' ? 'flex-1 pl-2' : 'w-[56%] min-w-[400px] 2xl:w-[62%] 2xl:min-w-[480px]'
          )}
        >
          <div
            className="flex flex-col h-full glass-panel rounded-2xl overflow-hidden border border-[#eeeff3]"
            style={{ boxShadow: '0 2px 8px rgba(16,24,40,0.04), 0 16px 40px rgba(16,24,40,0.08)' }}
          >
            <WorkspaceHeader shareMode={shareMode} showLeftPanel={showLeftPanel} />
            <ManusRightPanelContent runningWindow={displayRunningWindow} isProcessing={!!isProcessing} />
          </div>
        </div>
      )}

      {/* Toggle button when right panel is hidden */}
      {!isSharedView && userClosedPanel && (
        <div className="fixed right-4 top-1/2 -translate-y-1/2 z-40">
          <Tooltip title="显示工作区" placement="left">
            <button
              onClick={() => setUserClosedPanel(false)}
              className="w-10 h-10 rounded-full bg-white shadow-lg border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors"
            >
              <LeftOutlined className="text-gray-500" />
            </button>
          </Tooltip>
        </div>
      )}
    </div>
  );
};

/**
 * Workspace header — 产品化标题栏(原 macOS 窗口灯改为品牌图标 + 关闭按钮)。
 */
const WorkspaceHeader: React.FC<{ shareMode: ShareMode; showLeftPanel: boolean }> = memo(({ shareMode, showLeftPanel }) => {
  const { appInfo } = useContext(ChatContentContext);
  const handleClose = useCallback(() => {
    ee.emit(EVENTS.CLOSE_PANEL);
  }, []);

  const headerTitle = useMemo(() => {
    const name = appInfo?.app_name;
    return name ? `${name} · 工作台` : 'Gyra 工作台';
  }, [appInfo?.app_name]);

  return (
    <div className="flex items-center px-3 h-10 flex-shrink-0 border-b border-[#eff1f6]">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="w-5 h-5 rounded-md bg-[#eef0fe] inline-flex items-center justify-center flex-shrink-0">
          <DesktopOutlined className="text-[#4f46e5] text-[11px]" />
        </span>
        <span className="text-[13px] font-medium text-[#3b4154] truncate">{headerTitle}</span>
      </div>
      <Tooltip title="收起面板" placement="left">
        <button
          onClick={handleClose}
          className="w-6 h-6 rounded-md inline-flex items-center justify-center text-[#8a92a6] hover:text-[#3b4154] hover:bg-[#f2f4f8] transition-colors flex-shrink-0"
        >
          <CloseOutlined className="text-[11px]" />
        </button>
      </Tooltip>
    </div>
  );
});
WorkspaceHeader.displayName = 'WorkspaceHeader';

/**
 * Right panel content — just the workspace content, no header (header is in the shared row).
 */
const ManusRightPanelContent: React.FC<{ runningWindow: string; isProcessing: boolean }> = memo(({ runningWindow, isProcessing }) => {
  return (
    <div className="flex-1 overflow-hidden h-full">
      {runningWindow ? (
        <div className="h-full [&>div]:h-full [&>div>div]:h-full [&>div>div>div]:h-full">
          <GPTVis
            components={markdownComponents}
            {...markdownPlugins}
          >
            {runningWindow}
          </GPTVis>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-full">
          <div className="relative w-16 h-16 mb-5">
            <div className={classNames(
              'w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-500',
              isProcessing ? 'bg-gradient-to-br from-blue-50 to-indigo-50' : 'bg-gray-50'
            )}>
              <DesktopOutlined className={classNames(
                'text-3xl transition-colors duration-500',
                isProcessing ? 'text-blue-400' : 'text-gray-300'
              )} />
            </div>
            {isProcessing && (
              <div className="absolute inset-0 rounded-2xl border-2 border-blue-200 animate-ping opacity-30" />
            )}
          </div>
          <div className={classNames(
            'text-sm font-medium mb-2 transition-colors duration-500',
            isProcessing ? 'text-gray-700' : 'text-gray-400'
          )}>Workspace</div>
          <div className="flex items-center gap-1.5 h-5">
            {isProcessing ? (
              <>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:0ms]" />
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:150ms]" />
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:300ms]" />
                <span className="ml-0.5 text-xs text-blue-400">准备中...</span>
              </>
            ) : (
              <span className="text-xs text-gray-300">等待开始</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
});
ManusRightPanelContent.displayName = 'ManusRightPanelContent';

export default memo(ManusChatContent);
