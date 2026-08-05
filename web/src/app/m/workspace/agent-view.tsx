'use client';

import { useMemo, useRef } from 'react';
import { AgentWorkspaceRenderer } from '@/app/workspaces/detail/agent-workspace-renderer';
import { AgentWorkspaceInput, type AgentWorkspaceInputHandle } from '@/app/workspaces/detail/agent-workspace-input';
import { useSceneAgentChat } from '@/app/workspaces/detail/use-scene-agent-chat';
import { useUserInput } from '@/hooks/use-user-input';
import type { WorkspaceDeliverableFile } from '@/app/workspaces/detail/agent-workspace-types';

export interface MobileAgentViewProps {
  convUid?: string;
  workspaceId?: number | string;
  appCode?: string;
  taskId?: number | string;
}

/**
 * 移动端 Agent 视图:
 * 复用桌面场景空间的 SSE 执行流(useSceneAgentChat)与渲染器(AgentWorkspaceRenderer),
 * 输入条复用 AgentWorkspaceInput,仅换为移动端布局。
 */
export function MobileAgentView({ convUid, workspaceId, appCode, taskId }: MobileAgentViewProps) {
  const inputRef = useRef<AgentWorkspaceInputHandle>(null);
  const { submitUserInput } = useUserInput(convUid);

  const { workspaceView, loading, error, lastInput, convState, usageMetrics, send, abort } =
    useSceneAgentChat({ convUid, appCode, workspaceId, taskId });

  const running = loading || convState === 'RUNNING';

  const handleOpenFile = useMemo(
    () => (file: WorkspaceDeliverableFile) => {
      const url = file.content_url || file.download_url;
      if (url) window.open(url, '_blank');
    },
    [],
  );

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
        <AgentWorkspaceInput
          ref={inputRef}
          convUid={convUid}
          onSend={(p) => (running ? submitUserInput(p.text) : send(p))}
          loading={loading}
          onStop={abort}
          disabled={!convUid}
          lastInput={lastInput ? { text: typeof lastInput.text === 'string' ? lastInput.text : '' } : null}
          onRetry={lastInput ? () => send(lastInput) : undefined}
          usageMetrics={usageMetrics}
        />
      </div>
    </div>
  );
}