'use client';

import { useMemo, useState, type KeyboardEvent } from 'react';
import { AgentWorkspaceRenderer } from '@/app/workspaces/detail/agent-workspace-renderer';
import { useSceneAgentChat } from '@/app/workspaces/detail/use-scene-agent-chat';
import { useUserInput } from '@/hooks/use-user-input';
import { formatTokens } from '@/types/context-metrics';
import type { WorkspaceDeliverableFile } from '@/app/workspaces/detail/agent-workspace-types';
import { ArrowUpOutlined, BorderOutlined, ReloadOutlined } from '@ant-design/icons';

export interface MobileAgentViewProps {
  convUid?: string;
  workspaceId?: number | string;
  appCode?: string;
  taskId?: number | string;
}

/**
 * 移动端 Agent 视图:
 * 复用桌面场景空间的 SSE 执行流(useSceneAgentChat)与渲染器(AgentWorkspaceRenderer),
 * 输入条使用移动端专属轻量输入条(避免桌面 AgentWorkspaceInput 的固定宽度布局破坏窄屏)。
 */
export function MobileAgentView({ convUid, workspaceId, appCode, taskId }: MobileAgentViewProps) {
  const { submitUserInput } = useUserInput(convUid);
  const [text, setText] = useState('');

  const { workspaceView, loading, error, lastInput, convState, usageMetrics, send, abort } =
    useSceneAgentChat({ convUid, appCode, workspaceId, taskId });

  const running = loading || convState === 'RUNNING';
  const canSend = !!convUid && text.trim().length > 0;

  const handleOpenFile = useMemo(
    () => (file: WorkspaceDeliverableFile) => {
      const url = file.content_url || file.download_url;
      if (url) window.open(url, '_blank');
    },
    [],
  );

  const doSend = () => {
    const t = text.trim();
    if (!canSend) return;
    // 运行中发送 → 走用户输入(介入/补充);空闲发送 → 发起新任务
    if (running) {
      submitUserInput(t);
    } else {
      send({ text: t });
    }
    setText('');
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      doSend();
    }
  };

  const onStop = () => abort();

  const usageText = usageMetrics?.context_window
    ? `${formatTokens(usageMetrics.total)} / ${formatTokens(usageMetrics.context_window)}`
    : null;

  return (
    <div className="ms-agent">
      <div className="ms-agent__feed">
        {!convUid ? (
          <div className="ms-empty">
            <div className="ms-empty__title">会话加载中…</div>
          </div>
        ) : (
          <AgentWorkspaceRenderer view={workspaceView} onDeliverableClick={handleOpenFile} />
        )}
        {error && (
          <div className="ms-muted" style={{ marginTop: 12, color: 'var(--ms-red)' }}>
            {error}
          </div>
        )}
      </div>
      <div className="ms-agent__input">
        <div className="ms-agent-composer">
          {(usageText || lastInput) && (
            <div className="ms-agent-composer__meta">
              <span className="ms-agent-composer__usage">{usageText}</span>
              {lastInput && !running && (
                <button
                  type="button"
                  className="ms-agent-composer__retry"
                  disabled={!convUid}
                  onClick={() => send(lastInput)}
                >
                  <ReloadOutlined /> 重试
                </button>
              )}
            </div>
          )}
          <div className="ms-agent-composer__bar">
            <textarea
              className="ms-agent-composer__ta"
              rows={2}
              placeholder={running ? '输入补充指令…' : '输入指令给 Agent…'}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={!convUid}
            />
            {running ? (
              <button
                type="button"
                className="ms-agent-composer__send ms-agent-composer__send--stop"
                onClick={onStop}
                aria-label="停止"
              >
                <BorderOutlined />
              </button>
            ) : (
              <button
                type="button"
                className="ms-agent-composer__send"
                disabled={!canSend}
                onClick={doSend}
                aria-label="发送"
              >
                <ArrowUpOutlined />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}