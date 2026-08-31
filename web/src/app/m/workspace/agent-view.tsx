'use client';

import { useEffect, useMemo, useState, type KeyboardEvent } from 'react';
import { Drawer, Tag } from 'antd';
import { GPTVis } from '@antv/gpt-vis';
import { AgentWorkspaceRenderer } from '@/app/workspaces/detail/agent-workspace-renderer';
import { useSceneAgentChat } from '@/app/workspaces/detail/use-scene-agent-chat';
import { useUserInput } from '@/hooks/use-user-input';
import { formatTokens } from '@/types/context-metrics';
import markdownComponents, { markdownPlugins, preprocessLaTeX } from '@/components/chat/chat-content-components/config';
import type {
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
} from '@/app/workspaces/detail/agent-workspace-types';
import {
  ArrowUpOutlined,
  BorderOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const STEP_STATUS_COLOR: Record<string, string> = {
  running: 'processing',
  done: 'success',
  failed: 'error',
};

/** 步骤执行结果 markdown 渲染(与桌面 preview 一致) */
function StepMarkdown({ text }: { text: string }) {
  return (
    // @ts-ignore rehypePlugins type mismatch is pre-existing repo-wide (see chat-detail-content.tsx)
    <GPTVis components={markdownComponents} {...markdownPlugins}>
      {preprocessLaTeX(text)}
    </GPTVis>
  );
}

export interface MobileAgentViewProps {
  conversationId?: string;
  workspaceId?: number | string;
  appCode?: string;
  taskId?: number | string;
  /** 开启新会话入口(由空间页创建新会话并切换当前会话) */
  onNewSession?: () => void;
}

/**
 * 移动端 Agent 视图:
 * 复用桌面场景空间的 SSE 执行流(useSceneAgentChat)与渲染器(AgentWorkspaceRenderer),
 * 输入条使用移动端专属轻量输入条(避免桌面 AgentWorkspaceInput 的固定宽度布局破坏窄屏)。
 */
export function MobileAgentView({ conversationId, workspaceId, appCode, taskId, onNewSession }: MobileAgentViewProps) {
  const [text, setText] = useState('');
  const [selectedStep, setSelectedStep] = useState<WorkspaceExecutionStep | null>(null);

  const { workspaceView, loading, error, lastInput, modelName, convState, usageMetrics, send, abort, appendOptimisticUser } =
    useSceneAgentChat({ conversationId, appCode, workspaceId, taskId });

  const running = loading || convState === 'RUNNING';
  const canSend = !!conversationId && text.trim().length > 0;

  // 「先入队,agent 消费后才展示」:提交时不上屏,队列轮询检测到被消费时
  // (onConsumed)才上屏为独立用户气泡;运行结束兜底把滞留项上屏。
  const { submitUserInput, consumePendingInputs, startPolling: startQueuePolling, stopPolling: stopQueuePolling } =
    useUserInput(conversationId, {
      onConsumed: (items) => {
        items.forEach((i) => appendOptimisticUser(i.content));
      },
    });
  useEffect(() => {
    if (running) {
      startQueuePolling(2000);
    } else {
      stopQueuePolling();
      consumePendingInputs().forEach((i) => appendOptimisticUser(i.content));
    }
  }, [running, startQueuePolling, stopQueuePolling, consumePendingInputs, appendOptimisticUser]);

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
      // 「先入队,agent 消费后才展示」:提交时不上屏,由队列轮询检测到
      // 被 agent 消费后(onConsumed)上屏为独立用户气泡。
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
      {onNewSession && (
        <div className="ms-agent__toolbar">
          <span className="ms-agent__toolbar-title">Agent 对话</span>
          <button
            type="button"
            className="ms-agent__toolbar-new"
            onClick={onNewSession}
            aria-label="开启新会话"
          >
            <PlusOutlined /> 新会话
          </button>
        </div>
      )}
      <div className="ms-agent__feed">
        {!conversationId ? (
          <div className="ms-empty">
            <div className="ms-empty__title">会话加载中…</div>
          </div>
        ) : (
          <AgentWorkspaceRenderer
            view={workspaceView}
            running={running}
            modelName={modelName}
            onStepClick={setSelectedStep}
            onDeliverableClick={handleOpenFile}
          />
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
                  disabled={!conversationId}
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
              disabled={!conversationId}
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

      {/* 工具步骤详情:点击步骤行弹出,展示输入参数与执行结果 */}
      <Drawer
        title={selectedStep?.title || '步骤详情'}
        placement="bottom"
        height="min(72vh, 560px)"
        open={!!selectedStep}
        onClose={() => setSelectedStep(null)}
        destroyOnClose
        className="ms-step-drawer"
      >
        {selectedStep && (
          <div className="ms-step-detail">
            <div className="ms-step-detail__head">
              {selectedStep.action && <Tag color="geekblue">{selectedStep.action}</Tag>}
              <Tag color={STEP_STATUS_COLOR[selectedStep.status]}>
                {selectedStep.status === 'running'
                  ? '执行中'
                  : selectedStep.status === 'failed'
                    ? '执行失败'
                    : '已完成'}
              </Tag>
            </div>
            {selectedStep.action_input && (
              <section className="ms-step-detail__section">
                <div className="ms-step-detail__section-title">输入参数</div>
                <pre className="ms-step-detail__json">
                  {JSON.stringify(selectedStep.action_input, null, 2)}
                </pre>
              </section>
            )}
            {selectedStep.output ? (
              <section className="ms-step-detail__section">
                <div className="ms-step-detail__section-title">
                  {selectedStep.type === 'thinking' ? '思考内容' : '执行结果'}
                </div>
                <div className="ms-step-detail__markdown">
                  <StepMarkdown text={selectedStep.output} />
                </div>
              </section>
            ) : (
              !selectedStep.action_input && (
                <div className="ms-step-detail__empty">该步骤暂无结果内容</div>
              )
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}