'use client';

import { useEffect, useRef } from 'react';
import { Alert, Button, Spin } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { AgentStep } from './agent-types';
import { AgentWorkspaceInput } from './agent-workspace-input';
import { AgentWorkspaceRenderer } from './agent-workspace-renderer';
import type { AgentWorkspaceInputHandle, WorkspaceDeliverableFile } from './agent-workspace-types';
import { useSceneAgentChat } from './use-scene-agent-chat';
import { useUserInput } from '@/hooks/use-user-input';

export interface AgentWorkspaceProps {
  convUid?: string;
  appCode?: string;
  workspaceId?: number | string;
  taskId?: number | string;
  focus?: { id: number; title: string } | null;
  onClearFocus?: () => void;
  onClearContext?: () => void;
  /** header「新会话」入口:任务对话模式下不传(任务会话与任务绑定,不可另开) */
  onNewSession?: () => void;
  onStepClick?: (step: AgentStep) => void;
  /** 点击执行记录结尾的交付文件卡片:在中间容器渲染文件内容 */
  onDeliverableClick?: (file: WorkspaceDeliverableFile) => void;
  /** 点击对话记录中的任务卡片:进入任务对话 */
  onTaskClick?: (taskId: number) => void;
  onWorkspaceEvent?: (event: WorkspaceEvent) => void;
  /** 用户在 Agent 空间提交任务、开始对话时触发(外层据此折叠中间内容区) */
  onConversationStart?: () => void;
  inputRef?: React.Ref<AgentWorkspaceInputHandle>;
  switchingTask?: boolean;
  convLoadError?: string | null;
  retryLoadConv?: () => void;
  playbooks?: { playbook_id: number; playbook_name: string }[];
}

export function AgentWorkspace({
  convUid,
  appCode,
  workspaceId,
  taskId,
  focus,
  onClearFocus,
  onClearContext,
  onNewSession,
  onStepClick,
  onDeliverableClick,
  onTaskClick,
  onWorkspaceEvent,
  onConversationStart,
  inputRef: inputRefProp,
  switchingTask,
  convLoadError,
  retryLoadConv,
  playbooks,
}: AgentWorkspaceProps) {
  const inputRefInner = useRef<AgentWorkspaceInputHandle>(null);
  const inputRef = inputRefProp ?? inputRefInner;
  const { steps, workspaceView, loading, error, lastInput, convState, usageMetrics, send, abort, clearSteps, clearWorkspaceView } = useSceneAgentChat({
    convUid,
    appCode,
    workspaceId,
    taskId,
    focusArtifactId: focus?.id,
    onWorkspaceEvent,
    onConversationStart,
  });

  useEffect(() => {
    clearSteps();
    clearWorkspaceView();
  }, [convUid, clearSteps, clearWorkspaceView]);

  // loading(SSE 进行中) 或后端会话仍 RUNNING(关闭页面后重开,轮询恢复中)均视为运行中
  const running = loading || convState === 'RUNNING';
  // 运行中提交作为"补充输入"投递到后端队列(不开新 SSE 流,不中止当前生成)
  const { submitUserInput } = useUserInput(convUid);

  return (
    <div className="ws-agent-workspace">
      <div className="ws-agent-workspace__header">
        <span
          className={`ws-agent-workspace__status${
            running ? ' ws-agent-workspace__status--running' : error ? ' ws-agent-workspace__status--error' : ''
          }`}
        />
        <span className="ws-agent-workspace__header-title">
          {taskId ? `任务 #${taskId} · Agent` : 'Agent 空间'}
        </span>
        <span className="ws-agent-workspace__header-state">
          {running ? '运行中…' : error ? '出错了' : convState === 'FAILED' ? '已失败' : '就绪'}
        </span>
        {onNewSession && !taskId && (
          <button
            type="button"
            className="ws-agent-workspace__new-session"
            onClick={onNewSession}
            title="开启新会话(历史会话可在左侧任务列表中回溯)"
          >
            <PlusOutlined />
            <span>新会话</span>
          </button>
        )}
      </div>
      <div className="ws-agent-workspace__content">
        <div className="ws-agent-workspace__process">
          {error && <Alert message={error} type="error" showIcon className="ws-agent-workspace__error" />}
          {switchingTask ? (
            <div className="ws-agent-workspace__loading">
              <Spin tip="切换任务对话中..." />
            </div>
          ) : convLoadError && !convUid ? (
            <div className="ws-agent-workspace__error-card">
              <Alert
                message="会话加载失败"
                description={convLoadError}
                type="error"
                showIcon
                action={
                  retryLoadConv ? (
                    <Button size="small" icon={<ReloadOutlined />} onClick={retryLoadConv}>重试</Button>
                  ) : undefined
                }
              />
            </div>
          ) : !convUid ? (
            <div className="ws-agent-workspace__loading"><Spin /></div>
          ) : (
            <AgentWorkspaceRenderer
              view={workspaceView}
              onStepClick={onStepClick ? (s) => onStepClick({
                id: s.id,
                type: s.type === 'thinking' ? 'llm' : 'tool_call',
                title: s.title,
                status: s.status === 'running' ? 'running' : s.status === 'failed' ? 'failed' : 'done',
                timestamp: Date.now(),
                payload: {
                  action: s.action,
                  action_input: s.action_input,
                  output: s.output,
                  step_type: s.type,
                  exhibit: s.exhibit || undefined,
                },
              }) : undefined}
              onDeliverableClick={onDeliverableClick}
              onTaskClick={onTaskClick}
            />
          )}
        </div>
        <div className="ws-agent-workspace__input">
          <AgentWorkspaceInput
            ref={inputRef}
            convUid={convUid}
            onSend={(p) => (running ? submitUserInput(p.text) : send(p))}
            loading={loading}
            onStop={abort}
            disabled={!convUid || switchingTask}
            lastInput={lastInput ? { text: typeof lastInput.text === 'string' ? lastInput.text : '' } : null}
            onRetry={lastInput ? () => send(lastInput) : undefined}
            playbooks={playbooks}
            focus={focus}
            onClearFocus={onClearFocus}
            onClearContext={onClearContext}
            usageMetrics={usageMetrics}
          />
        </div>
      </div>
    </div>
  );
}