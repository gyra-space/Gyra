'use client';

import { useEffect, useMemo, useRef } from 'react';
import { Alert, Button, Spin } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { AgentStep } from './agent-types';
import { AgentWorkspaceInput } from './agent-workspace-input';
import { AgentWorkspaceRenderer } from './agent-workspace-renderer';
import DockPanel from '@/components/chat/dock/dock-panel';
import type { AgentWorkspaceInputHandle, WorkspaceDeliverableFile } from './agent-workspace-types';
import { useSceneAgentChat } from './use-scene-agent-chat';
import { useUserInput } from '@/hooks/use-user-input';
import { useRequest } from 'ahooks';
import { apiInterceptors, getAppInfo, listResources } from '@/client/api';

export interface AgentWorkspaceProps {
  conversationId?: string;
  appCode?: string;
  workspaceId?: number | string;
  taskId?: number | string;
  focus?: { id: number; title: string } | null;
  onClearFocus?: () => void;
  /** 只读模式(无 space.chat.use 权限):输入区禁用并提示,不可发起对话 */
  chatReadOnly?: boolean;
  onClearContext?: () => void;
  /** header「新会话」入口:任务对话模式下不传(任务会话与任务绑定,不可另开) */
  onNewSession?: () => void;
  onStepClick?: (step: AgentStep) => void;
  /** 点击执行记录结尾的交付文件卡片:在中间容器渲染文件内容 */
  onDeliverableClick?: (file: WorkspaceDeliverableFile) => void;
  /** 点击对话记录中的任务卡片:进入任务对话 */
  onTaskClick?: (taskId: number) => void;
  /** 点击异步子 agent 卡片:在中间容器内联展开子会话 */
  onSubagentClick?: (subConvId: string) => void;
  /** ask_user 交互确认后续跑 Agent 对话(复用同一 conv_uid 恢复 WAITING 会话) */
  onInteractionResume?: (userMessage: string) => void;
  onWorkspaceEvent?: (event: WorkspaceEvent) => void;
  /** 用户在 Agent 空间提交任务、开始对话时触发(外层据此折叠中间内容区) */
  onConversationStart?: () => void;
  inputRef?: React.Ref<AgentWorkspaceInputHandle>;
  switchingTask?: boolean;
  convLoadError?: string | null;
  retryLoadConv?: () => void;
  /** 会话缺失时(新 tab/新任务进入)首次发送或上传前懒创建会话的回调 */
  onEnsureConversation?: () => Promise<string | null>;
  playbooks?: { playbook_id: number; playbook_name: string }[];
  /** 工作空间全量任务列表(用于恢复视图时重注入当前会话的任务卡片) */
  tasks?: any[];
}

export function AgentWorkspace({
  conversationId,
  appCode,
  workspaceId,
  taskId,
  focus,
  onClearFocus,
  chatReadOnly,
  onClearContext,
  onNewSession,
  onStepClick,
  onDeliverableClick,
  onTaskClick,
  onSubagentClick,
  onInteractionResume: onInteractionResumeProp,
  onWorkspaceEvent,
  onConversationStart,
  inputRef: inputRefProp,
  switchingTask,
  convLoadError,
  retryLoadConv,
  onEnsureConversation,
  playbooks,
  tasks,
}: AgentWorkspaceProps) {
  const inputRefInner = useRef<AgentWorkspaceInputHandle>(null);
  const inputRef = inputRefProp ?? inputRefInner;
  const { steps, workspaceView, loading, error, lastInput, modelName, recovering, retryRecover, convState, convLoading, usageMetrics, dockWidgets, send, abort, appendOptimisticUser, clearSteps, clearWorkspaceView } = useSceneAgentChat({
    conversationId,
    appCode,
    workspaceId,
    taskId,
    focusArtifactId: focus?.id,
    tasks,
    playbooks,
    // 无会话时首次发送懒创建(与简洁模式欢迎态同一链路)
    onConvCreated: onEnsureConversation,
    onWorkspaceEvent,
    onConversationStart,
  });

  useEffect(() => {
    clearSteps();
    clearWorkspaceView();
  }, [conversationId, clearSteps, clearWorkspaceView]);

  // loading(SSE 进行中) 或后端会话仍 RUNNING(关闭页面后重开,轮询恢复中)均视为运行中
  const running = loading || convState === 'RUNNING';
  // 运行中提交作为"补充输入"投递到后端队列(不开新 SSE 流,不中止当前生成)。
  // 「先入队,agent 消费后才展示」:提交时不上屏,队列轮询检测到被消费时
  // (onConsumed)才上屏为独立用户气泡;运行结束兜底把滞留项上屏。
  const { submitUserInput, consumePendingInputs, startPolling: startQueuePolling, stopPolling: stopQueuePolling } = useUserInput(conversationId, {
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
  // Agent 头像数据:appCode 对应 app 的 icon/name(与通用聊天页同源)
  const { data: appInfoTuple } = useRequest(
    async () => (appCode ? apiInterceptors(getAppInfo({ app_code: appCode })) : ([null, null] as any)),
    { refreshDeps: [appCode] },
  );
  const appInfo = appInfoTuple?.[1];

  // 空间配置模型:任务级工作区输入框默认取「空间设置 → 空间模型」列表第一个启用的模型。
  // 未配置空间模型时为空字符串,输入框内部回退到全局模型列表首个(与旧逻辑一致)。
  const { data: spaceModels } = useRequest(async () => {
    if (!workspaceId) return [];
    const [, data] = await apiInterceptors(listResources({ workspace_id: Number(workspaceId), type: 'llm_model' }));
    return data || [];
  }, { refreshDeps: [workspaceId] });

  const spaceDefaultModel = useMemo(() => {
    const list = spaceModels || [];
    if (!list.length) return '';
    // 优先取空间「设为默认」标记的模型(is_default);无标记时沿用原逻辑取第一个启用的模型。
    const isDefault = (m: any) => !!(m?.config && m.config.is_default);
    const first =
      list.find((m: any) => m.is_active !== false && isDefault(m)) ||
      list.find((m: any) => isDefault(m)) ||
      list.find((m: any) => m.is_active !== false) ||
      list[0];
    return first?.config?.model || first?.physical_ref || first?.name || '';
  }, [spaceModels]);

  // ask_user 交互确认后续跑:复用同一 conv_uid 发一条新消息,后端
  // `_initialize_agent_conversation` 检测到 WAITING 会话后恢复 Agent loop。
  // 外层可传自定义 onInteractionResume(如带 original_message_id 做关联),缺省走 send。
  const resumeInteraction = (userMessage: string) => {
    if (onInteractionResumeProp) {
      onInteractionResumeProp(userMessage);
      return;
    }
    if (!conversationId || !userMessage.trim()) return;
    send({ text: userMessage });
  };

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
          {running ? '运行中…' : recovering ? '正在恢复连接…' : error ? '出错了' : convState === 'FAILED' ? '已失败' : '就绪'}
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
          {error && (
            <Alert
              message={error}
              type="error"
              showIcon
              className="ws-agent-workspace__error"
              action={
                <Button size="small" icon={<ReloadOutlined />} onClick={retryRecover}>
                  重试连接
                </Button>
              }
            />
          )}
          {switchingTask ? (
            <div className="ws-agent-workspace__loading">
              <Spin tip="切换任务对话中..." />
            </div>
          ) : convLoading ? (
            <div className="ws-agent-workspace__loading">
              <Spin tip="会话加载中..." />
            </div>
          ) : convLoadError && !conversationId ? (
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
          ) : !conversationId ? (
            <div className="ws-agent-workspace__empty">
              <span className="ws-agent-workspace__empty-icon">✦</span>
              <p className="ws-agent-workspace__empty-title">开启新会话</p>
              <p className="ws-agent-workspace__empty-desc">在下方输入指令即可开始;历史会话可从左侧列表回溯</p>
            </div>
          ) : (
            <AgentWorkspaceRenderer
              view={workspaceView}
              running={running}
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
              onSubagentClick={onSubagentClick}
              onInteractionResume={resumeInteraction}
              agentIcon={appInfo?.icon}
              agentName={appInfo?.app_name}
              modelName={modelName}
            />
          )}
        </div>
        <div className="ws-agent-workspace__input">
          {/* Composer Dock:独立卡片贴合在输入框上方,与通用聊天页同一组件/协议 */}
          <DockPanel widgets={dockWidgets} />
          <AgentWorkspaceInput
            ref={inputRef}
            conversationId={conversationId}
            appInfo={appInfo}
            defaultModel={spaceDefaultModel}
            onSend={async (p) => {
              if (running) {
                // 运行中追问:投递补充输入队列(后端校验确有活跃执行才入队)。
                // 若提交失败(会话无活跃执行/僵尸状态),回退为正常发起对话,
                // 避免追问被投入无消费者队列而静默吞掉(无报错、无回复)。
                // 入队成功不在此上屏:由队列轮询检测到被 agent 消费后(onConsumed)上屏。
                const ok = await submitUserInput(p.text);
                if (!ok) {
                  send(p);
                }
              } else {
                send(p);
              }
            }}
            loading={running}
            onStop={abort}
            disabled={switchingTask}
            onEnsureConversation={onEnsureConversation}
            readOnly={chatReadOnly}
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