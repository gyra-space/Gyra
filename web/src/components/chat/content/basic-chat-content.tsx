'use client';

import UnifiedChatInput from '@/components/chat/input/unified-chat-input';
import { ChatContentContext } from '@/contexts';
import { CompressionSegmentVo, IChatDialogueMessageSchema } from '@/types/chat';
import React, { memo, useContext, useEffect, useMemo, useRef, useState } from 'react';
import ChatHeader from '../header/chat-header';
import DockPanel from '@/components/chat/dock/dock-panel';
import ChatContent from './chat-content';
import CompressionPoint from './compression-point';
import { TaskCreatedCard, TaskCreatedCardPayload } from '../task-created-card';

interface BasicChatContentProps {
  ctrl: AbortController;
  workspaceId?: string | number;
}

const MAX_RENDER_COUNT = 200;
const MAX_CONTEXT_SIZE = 10_000_000;

const isMessageTooLarge = (msg: IChatDialogueMessageSchema): boolean => {
  return !!(msg.context && typeof msg.context === 'string' && msg.context.length > MAX_CONTEXT_SIZE);
};

function getTaskCreatedPayload(item: IChatDialogueMessageSchema): TaskCreatedCardPayload | null {
  if (item.role !== 'view') return null;
  try {
    const ctx = typeof item.context === 'string' ? JSON.parse(item.context) : item.context;
    if (ctx && ctx.type === 'task_created') {
      return ctx.payload as TaskCreatedCardPayload;
    }
  } catch {
    // ignore
  }
  return null;
}

const BasicChatContent: React.FC<BasicChatContentProps> = ({ ctrl, workspaceId }) => {
  const scrollableRef = useRef<HTMLDivElement>(null);
  const { history, compressionSegments, replyLoading, dockWidgets } = useContext(ChatContentContext);
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  const [jsonValue, setJsonValue] = useState<string>('');

  const showMessages = useMemo(() => {
    const filtered = history
      .filter(item => ['view', 'human'].includes(item.role) && !isMessageTooLarge(item));
    const windowed = filtered.length > MAX_RENDER_COUNT
      ? filtered.slice(-MAX_RENDER_COUNT)
      : filtered;
    return windowed.map((item, index) => ({
      ...item,
      key: `${item.role}_${item.order ?? index}`,
    }));
  }, [history]);

  // 压缩点定位：每个压缩段覆盖的最后一条可见消息的 index -> segment
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

  useEffect(() => {
    setTimeout(() => {
      scrollableRef.current?.scrollTo(0, scrollableRef.current?.scrollHeight);
    }, 50);
  }, [history, history[history.length - 1]?.context]);

  const hasMessages = showMessages.length > 0;
  const isProcessing = replyLoading || (history.length > 0 && history[history.length - 1]?.thinking);

  return (
    <div className="flex flex-col h-full bg-[#FAFAFA] dark:bg-[#111] overflow-hidden">
      {/* 标题栏 */}
      <ChatHeader isProcessing={isProcessing} />

      <div
        ref={scrollableRef}
        className="flex-1 overflow-y-auto min-h-0"
      >
        {hasMessages && (
          <div className="w-full px-3 py-4">
            <div className="w-full">
              {showMessages.map((content, index) => {
                const taskPayload = workspaceId ? getTaskCreatedPayload(content) : null;
                if (taskPayload) {
                  return (
                    <div key={content.key} className="mb-4">
                      <TaskCreatedCard
                        payload={taskPayload}
                        onViewTask={(taskId) => {
                          window.dispatchEvent(new CustomEvent('workspace:view-task', { detail: { taskId } }));
                        }}
                      />
                      {compressionPoints[index] && (
                        <CompressionPoint segment={compressionPoints[index]} />
                      )}
                    </div>
                  );
                }
                return (
                  <div key={content.key} className="mb-4 [content-visibility:auto] [contain-intrinsic-size:auto_200px]">
                    <ChatContent
                      content={content}
                      onLinkClick={() => {
                        setJsonModalOpen(true);
                        setJsonValue(JSON.stringify(content?.context, null, 2));
                      }}
                      messages={showMessages}
                    />
                    {compressionPoints[index] && (
                      <CompressionPoint segment={compressionPoints[index]} />
                    )}
                  </div>
                );
              })}
              <div className="h-8" />
            </div>
          </div>
        )}
      </div>

      <div className="flex-shrink-0 pt-2 pb-2 px-3">
        <div className="w-full">
          {/* Composer Dock：独立卡片附着在输入框上方 */}
          <DockPanel widgets={dockWidgets || {}} />
          <UnifiedChatInput
            ctrl={ctrl}
          />
        </div>
      </div>
    </div>
  );
};

export default memo(BasicChatContent);
