'use client';

import './scene-workspace.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { App, Button, Modal } from 'antd';
import { CloseOutlined, RightOutlined, ScheduleOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { apiInterceptors, createConversation, getTaskInfo, linkConversation, listConversations, listPlaybooks, setCurrentConversation } from '@/client/api';
import { getUserId } from '@/utils';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { AgentStep, DetailContext } from './agent-types';
import { AgentWorkspace } from './agent-workspace';
import { SceneSpace } from './scene-space';
import { SceneTaskRail } from './scene-task-rail';
import type { AgentWorkspaceInputHandle } from './agent-workspace-types';

/** 判断当前任务列表里是否有活跃任务(running 等会变化的状态),决定是否开轮询。 */
export function hasActiveTask(tasks: any[]): boolean {
  const active = new Set(['running', 'pending_trigger', 'blocked', 'awaiting_human', 'draft']);
  return (tasks || []).some((t) => active.has(t?.status));
}

interface SceneWorkspaceShellProps {
  workspace: any;
  tasks: any[];
  interventions: any[];
  workspaceConvUid: string;
  appCode: string;
  onRefreshLists?: () => void;
  /** 任务/介入列表刷新信号(lobby 最近产出/交付/待办据此同步刷新) */
  listsRefreshKey?: number;
  onConvChanged?: (convUid: string, taskId?: number | null) => void;
  convLoadError?: string | null;
  retryLoadConv?: () => void;
  /** 从会话列表选中会话时携带的 task_id:number=进 task 对话,null=workspace 级会话,
   * undefined=非列表触发(初始/任务栏进入)。 */
  pendingTaskId?: number | null | undefined;
}

export function SceneWorkspaceShell({
  workspace,
  tasks,
  interventions,
  workspaceConvUid,
  appCode,
  onRefreshLists,
  listsRefreshKey,
  onConvChanged,
  convLoadError,
  retryLoadConv,
  pendingTaskId,
}: SceneWorkspaceShellProps) {
  const workspaceId = workspace?.id;
  const [previewItem, setPreviewItem] = useState<any>(null);
  const [detailContext, setDetailContext] = useState<DetailContext>('dashboard');
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [activeTask, setActiveTask] = useState<any>(null);
  const [taskConvUid, setTaskConvUid] = useState<string>('');
  const [switchingTask, setSwitchingTask] = useState(false);
  const { message } = App.useApp();
  // rail 抽屉(中屏)与单列 tab(小屏)状态
  const [railOpen, setRailOpen] = useState(true);
  const [mobilePane, setMobilePane] = useState<'rail' | 'space' | 'agent'>('space');
  // 大厅容器折叠:折叠后 Agent 空间占满主区,专注执行进展;
  // 点击步骤/文件卡片等主动查看动作会自动展开;折叠期间被动到达的新内容点亮角标。
  const [spaceCollapsed, setSpaceCollapsed] = useState(false);
  const [spaceHasNew, setSpaceHasNew] = useState(false);
  // 用户主动查看内容 → 展开大厅;被动事件 → 仅折叠时点亮角标
  const expandSpace = () => {
    setSpaceCollapsed(false);
    setSpaceHasNew(false);
  };
  const notifySpaceContent = () => {
    setSpaceCollapsed((collapsed) => {
      if (collapsed) setSpaceHasNew(true);
      return collapsed;
    });
  };
  // 隐式上下文:用户点 × 取消带入当前关注的交付物
  const [focusDismissed, setFocusDismissed] = useState(false);
  // 收件箱刷新信号:中间区域确认/否决 ECP 提案后 bump,通知左侧 rail 重新拉待办。
  const [inboxTick, setInboxTick] = useState(0);
  const bumpInbox = () => setInboxTick((t) => t + 1);
  const prevActiveTaskId = useRef<number | null>(null);
  const agentInputRef = useRef<AgentWorkspaceInputHandle>(null);

  // 隐式上下文:用户当前在中间区域查看的交付物(artifact),发消息时自动带入 agent 上下文。
  // 仅 file-preview/entity-card 且有 artifact_id 时生效;点 chip × 设 focusDismissed 取消带入。
  const focus = useMemo<{ id: number; title: string } | null>(() => {
    if (focusDismissed) return null;
    if (detailContext !== 'file-preview' && detailContext !== 'entity-card') return null;
    const p = previewItem;
    const id = p?.payload?.artifact_id || p?.payload?.file_id || p?.artifact_id;
    if (!id) return null;
    const title = p?.payload?.title || p?.title || `artifact_${id}`;
    return { id: Number(id), title };
  }, [detailContext, previewItem, focusDismissed]);

  // 双向联动:把场景内容(任务)引用进 Agent 输入框
  const handleReference = (task: any) => {
    const title = task?.title || `task_${task?.id}`;
    agentInputRef.current?.insertText(`@任务#${task.id}「${title}」`);
    setMobilePane('agent');
  };

  // 「新会话」(header 入口)与「清理上下文」(输入框浮动入口)共用的实现:
  // 新 conv_uid 在 gpts_messages/gpts_conversations/chat_history_message 三表无行,
  // agent 上下文天然干净;旧会话保留在左侧任务列表的会话记录里可回溯。
  const handleNewConversation = async (tip: string) => {
    if (!workspaceId) return;
    const [, newConv] = await apiInterceptors(createConversation({ workspace_id: workspaceId }));
    if (!newConv?.conv_uid) return;
    await apiInterceptors(linkConversation({ workspace_id: workspaceId, conv_uid: newConv.conv_uid, user_id: Number(getUserId()) || undefined }));
    await apiInterceptors(setCurrentConversation(workspaceId, newConv.conv_uid));
    onConvChanged?.(newConv.conv_uid);
    message.success(tip);
  };

  // 中屏(900–1279px)默认收起左 rail 为抽屉;小屏默认展示场景空间
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(max-width: 1279px)');
    const apply = () => setRailOpen(!mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);

  const { data: playbooks } = useRequest(async () => {
    if (!workspaceId) return [];
    const [, data] = await apiInterceptors(listPlaybooks({ workspace_id: Number(workspaceId) }));
    return (data || []).map((p: any) => ({ playbook_id: p.id, playbook_name: p.name }));
  }, { refreshDeps: [workspaceId] });

  // 会话维度列表:剧本任务会话 + 大厅会话统一按 conv 维度展示。
  // refreshDeps 含 workspaceConvUid/taskConvUid:清理(新开会话)/切换会话/进入任务对话后自动刷新,
  // 新会话按 gmt_modified 倒序自然置顶。
  const { data: conversations } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [, data] = await apiInterceptors(listConversations({ workspace_id: workspaceId, user_id: Number(getUserId()) || undefined, limit: 200 }));
      return data || [];
    },
    { refreshDeps: [workspaceId, workspaceConvUid, taskConvUid] },
  );

  useEffect(() => {
    if (activeTaskId === prevActiveTaskId.current) return;
    prevActiveTaskId.current = activeTaskId;

    if (!activeTaskId) {
      setTaskConvUid('');
      setActiveTask(null);
      setSwitchingTask(false);
      return;
    }

    setSwitchingTask(true);
    setActiveTask(null);
    let cancelled = false;
    apiInterceptors(getTaskInfo(activeTaskId))
      .then(([, res]) => {
        if (!cancelled) {
          setTaskConvUid(res?.conv_session_id || '');
          setActiveTask(res || null);
          setSwitchingTask(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSwitchingTask(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeTaskId]);

  // 运行时轮询:有活跃任务时每 4s 刷新任务/介入列表,无活跃任务时停。
  // 后台 run_task 的状态变更无法走 workspace 事件流(fire-and-forget,无 SSE 连接),
  // 用轮询替代;task_created 事件触发的 onRefreshLists 仍保留。
  useEffect(() => {
    if (!hasActiveTask(tasks) || !onRefreshLists) return;
    const timer = setInterval(onRefreshLists, 4000);
    return () => clearInterval(timer);
  }, [tasks, onRefreshLists]);

  const handlePreview = (item: any, kind: 'task' | 'intervention' | 'ecp_proposal') => {
    setPreviewItem(item);
    if (kind === 'task') setDetailContext('task-detail');
    else if (kind === 'ecp_proposal') setDetailContext('ecp-proposal');
    else setDetailContext('entity-card');
    expandSpace();
  };

  const handleEnterConversation = (taskId: number) => {
    setActiveTaskId(taskId);
    const task = tasks.find((t) => t.id === taskId);
    if (task) {
      setPreviewItem(task);
      setDetailContext('task-detail');
    }
  };

  // 从会话列表选中会话:有 task_id -> 进 task 对话(复用 handleEnterConversation,
  // 由 activeTaskId effect 调 getTaskInfo 恢复 taskConvUid);无 task_id -> 回 dashboard。
  // pendingTaskId === undefined 表示非列表触发,不动(初始/任务栏进入走各自路径)。
  useEffect(() => {
    if (pendingTaskId === undefined) return;
    if (pendingTaskId === null) {
      setActiveTaskId(null);
      setDetailContext('dashboard');
      setPreviewItem(null);
    } else {
      handleEnterConversation(pendingTaskId);
    }
  }, [pendingTaskId]);

  const handleBackToDashboard = () => {
    setDetailContext('dashboard');
    setPreviewItem(null);
    expandSpace();
  };

  // 点击异步子 agent 卡片:在中间容器内联展开子会话(不再新标签打开)
  const handleSubagentClick = (subConvId: string) => {
    setFocusDismissed(false);
    setPreviewItem({ sub_conv_id: subConvId });
    setDetailContext('subagent');
    expandSpace();
    setMobilePane('space');
  };

  // 大厅入口:进入飞轮工作台(中间区域切换,小屏定位到空间面板)
  const handleEnterFlywheel = () => {
    setDetailContext('flywheel');
    setPreviewItem(null);
    expandSpace();
    setMobilePane('space');
  };

  // 剧本快捷启动:选择剧本后以 @引用 带入输入框并聚焦,复用输入框的剧本执行链路
  const [quickPbOpen, setQuickPbOpen] = useState(false);
  const handleQuickRun = (pb: { playbook_id: number; playbook_name: string }) => {
    agentInputRef.current?.insertText(`@剧本#${pb.playbook_id}「${pb.playbook_name}」 `);
    setQuickPbOpen(false);
    agentInputRef.current?.focus();
    setMobilePane('agent');
  };

  // 推荐问题/随便问问:可带文本填入输入框并聚焦(带文本时作为问题预填)
  const handleAsk = (text?: string) => {
    if (text) agentInputRef.current?.insertText(`${text} `);
    agentInputRef.current?.focus();
    setMobilePane('agent');
  };

  // 导览卡动作:全部壳内化 —— 不再整页跳转离开三列壳
  const handleGuideAction = (action: 'ask' | 'run_playbook' | 'triggers' | 'data_assets') => {
    switch (action) {
      case 'ask':
        agentInputRef.current?.focus();
        setMobilePane('agent');
        break;
      case 'run_playbook':
        setQuickPbOpen(true);
        setMobilePane('space');
        break;
      case 'triggers':
        setPreviewItem(null);
        setDetailContext('triggers');
        expandSpace();
        setMobilePane('space');
        break;
      case 'data_assets':
        setPreviewItem(null);
        setDetailContext('data-assets');
        expandSpace();
        setMobilePane('space');
        break;
    }
  };

  // 工作台待办点击:与 rail 收件箱一致 —— task 进任务对话,intervention/提案进中屏处理
  const handleSelectInbox = (item: any) => {
    if (item.source_type === 'task') {
      handleEnterConversation(Number(item.source_id));
      setMobilePane('agent');
      return;
    }
    if (item.source_type === 'intervention') {
      handlePreview(
        { id: Number(item.source_id), question: { message: item.title }, status: 'requested' },
        'intervention',
      );
    } else if (item.source_type === 'ecp_proposal') {
      handlePreview(item, 'ecp_proposal');
    } else {
      setPreviewItem({ payload: { title: item.title, source_type: item.source_type } });
      setDetailContext('entity-card');
    }
    expandSpace();
    setMobilePane('space');
  };

  // 从「会话」视图进入对应对话:剧本任务会话(有 task_id)进任务对话,
  // 大厅会话(无 task_id)切回 workspace 级会话并回到 dashboard。
  const handleOpenConversation = async (convUid: string, taskId: number | null) => {
    if (taskId) {
      handleEnterConversation(taskId);
      return;
    }
    await apiInterceptors(setCurrentConversation(workspaceId, convUid));
    setActiveTaskId(null);
    setDetailContext('dashboard');
    setPreviewItem(null);
    onConvChanged?.(convUid, null);
  };

  const handleStepClick = (step: AgentStep) => {
    setFocusDismissed(false);
    expandSpace();
    // 步骤携带大厅入驻内容:直接以通用 Exhibit 渲染(图片/视频/表格/PPT 等)
    if (step.payload?.exhibit) {
      setPreviewItem({ payload: { exhibit: step.payload.exhibit } });
      setDetailContext('exhibit');
      setMobilePane('space');
      return;
    }
    if (step.type === 'tool_call' || step.type === 'llm') {
      setPreviewItem(step);
      setDetailContext('tool-result');
      setMobilePane('space');
    } else if (step.payload?.file_id || step.payload?.file_name) {
      setPreviewItem(step);
      setDetailContext('file-preview');
      setMobilePane('space');
    } else if (step.payload?.task_id || step.payload?.asset_id) {
      setPreviewItem(step);
      setDetailContext('entity-card');
      setMobilePane('space');
    }
  };

  const handleWorkspaceEvent = (event: WorkspaceEvent) => {
    switch (event.type) {
      case 'artifact_produced':
        onRefreshLists?.();
        if (event.payload?.file_id || event.payload?.artifact_id) {
          setPreviewItem(event);
          setDetailContext(event.payload?.file_id ? 'file-preview' : 'entity-card');
          setFocusDismissed(false);
          // 被动到达:不强行拉开大厅,折叠时点亮角标提示有新内容
          notifySpaceContent();
        }
        break;
      case 'task_created':
      case 'delivery_sent':
        onRefreshLists?.();
        break;
      case 'asset_referenced':
        setPreviewItem(event);
        setDetailContext('entity-card');
        setFocusDismissed(false);
        break;
      case 'intervention_triggered':
        onRefreshLists?.();
        if (event.payload?.task_id) {
          const task = tasks.find((t) => t.id === event.payload.task_id);
          if (task) {
            setPreviewItem(task);
            setDetailContext('task-detail');
          } else {
            setPreviewItem(event);
            setDetailContext('entity-card');
          }
        } else {
          setPreviewItem(event);
          setDetailContext('entity-card');
        }
        break;
      case 'context_loaded':
        // no-op: context was loaded
        break;
      default:
        break;
    }
  };

  const rightConvUid = activeTaskId ? taskConvUid : workspaceConvUid;
  const rightTaskId = activeTaskId ? activeTaskId : undefined;

  return (
    <div
      className={`ws-scene-shell${railOpen ? '' : ' ws-scene-shell--rail-closed'}${spaceCollapsed ? ' ws-scene-shell--space-collapsed' : ''}`}
      data-pane={mobilePane}
    >
      <div className="ws-scene-shell__mobile-tabs" role="tablist">
        {([['rail', '任务'], ['space', '空间'], ['agent', 'Agent']] as const).map(([key, label]) => (
          <span
            key={key}
            role="tab"
            aria-selected={mobilePane === key}
            className={`ws-scene-shell__mobile-tab${mobilePane === key ? ' ws-scene-shell__mobile-tab--on' : ''}`}
            onClick={() => setMobilePane(key)}
          >
            {label}
          </span>
        ))}
      </div>
      <button
        type="button"
        className="ws-scene-shell__rail-toggle"
        aria-label={railOpen ? '收起任务栏' : '展开任务栏'}
        onClick={() => setRailOpen((v) => !v)}
      >
        {railOpen ? '‹' : '›'}
      </button>
      {/* 大厅容器折叠开关:折叠后 Agent 空间占满主区专注执行;有新内容时亮角标 */}
      <button
        type="button"
        className={`ws-scene-shell__space-toggle${spaceHasNew ? ' ws-scene-shell__space-toggle--new' : ''}`}
        aria-label={spaceCollapsed ? '展开大厅' : '折叠大厅'}
        title={spaceCollapsed ? '展开大厅' : '折叠大厅,专注执行进展'}
        onClick={() => {
          if (spaceCollapsed) {
            expandSpace();
          } else {
            setSpaceCollapsed(true);
            setSpaceHasNew(false);
          }
        }}
      >
        {spaceCollapsed ? (
        <>
          <span className="ws-scene-shell__space-toggle__icon">›</span>
          <span className="ws-scene-shell__space-toggle__label">展开大厅</span>
        </>
      ) : (
        '‹'
      )}
      </button>
      <div className="ws-scene-shell__rail">
        <SceneTaskRail
          tasks={tasks}
          interventions={interventions}
          workspaceId={workspaceId}
          activeTaskId={activeTaskId}
          disabled={switchingTask}
          playbooks={playbooks}
          onRefreshLists={onRefreshLists}
          inboxTick={inboxTick}
          onPreview={(item, kind) => {
            handlePreview(item, kind);
            setMobilePane('space');
            if (window.matchMedia('(max-width: 1279px)').matches) setRailOpen(false);
          }}
          onEnterConversation={(taskId) => {
            handleEnterConversation(taskId);
            setMobilePane('agent');
          }}
          onReference={handleReference}
          conversations={conversations || []}
          currentConvUid={rightConvUid}
          onOpenConversation={(convUid, taskId) => {
            handleOpenConversation(convUid, taskId);
            setMobilePane(taskId ? 'agent' : 'space');
            if (window.matchMedia('(max-width: 1279px)').matches) setRailOpen(false);
          }}
        />
      </div>
      <div className="ws-scene-shell__space">
        <SceneSpace
          context={detailContext}
          previewItem={previewItem}
          activeTask={activeTask}
          workspaceId={workspaceId}
          workspaceCode={workspace?.workspace_code}
          appCode={appCode}
          playbooks={playbooks}
          onBack={handleBackToDashboard}
          onProposalResolved={bumpInbox}
          onEnterFlywheel={handleEnterFlywheel}
          onGuide={handleGuideAction}
          onSelectInbox={handleSelectInbox}
          onAsk={handleAsk}
          onRunPlaybook={handleQuickRun}
          listsRefreshKey={listsRefreshKey}
          onSelectTask={(taskId) => {
            const task = tasks.find((t) => t.id === taskId);
            if (task) handlePreview(task, 'task');
          }}
          onSelectArtifact={(artifact) => {
            setPreviewItem({ payload: { artifact_id: artifact.id, title: artifact.title, type: artifact.type } });
            setDetailContext('entity-card');
            setFocusDismissed(false);
            expandSpace();
          }}
          onSelectDelivery={(delivery) => {
            setPreviewItem({ payload: { delivery_id: delivery.id, title: delivery.title } });
            setDetailContext('delivery-detail');
            setFocusDismissed(false);
            expandSpace();
          }}
        />
      </div>
      <div className="ws-scene-shell__agent">
        {activeTaskId && (
          <div className="ws-scene-shell__agent-mode">
            <span>任务对话: {activeTaskId}</span>
            <Button size="small" icon={<CloseOutlined />} onClick={() => setActiveTaskId(null)}>退出任务对话</Button>
          </div>
        )}
        <AgentWorkspace
          convUid={rightConvUid}
          appCode={appCode}
          workspaceId={workspaceId}
          taskId={rightTaskId}
          focus={focus}
          onClearFocus={() => setFocusDismissed(true)}
          onClearContext={activeTaskId ? undefined : () => handleNewConversation('已清空上下文')}
          onNewSession={activeTaskId ? undefined : () => handleNewConversation('已开启新会话')}
          onStepClick={handleStepClick}
          onDeliverableClick={(file) => {
            setPreviewItem({ payload: { deliverable_file: file } });
            setDetailContext('file-preview');
            setFocusDismissed(false);
            expandSpace();
            setMobilePane('space');
          }}
          onTaskClick={(taskId) => {
            handleEnterConversation(taskId);
            setMobilePane('agent');
          }}
          onSubagentClick={handleSubagentClick}
          onWorkspaceEvent={handleWorkspaceEvent}
          onConversationStart={() => {
            setSpaceCollapsed(true);
            // 会话开始即刷新任务列表:回合前路由预建的会话内任务(页面输入命中剧本)
            // 在 chat 流里创建,不产生 task_created SSE 事件,靠这里第一时间入列表。
            onRefreshLists?.();
          }}
          inputRef={agentInputRef}
          switchingTask={switchingTask}
          convLoadError={convLoadError}
          retryLoadConv={retryLoadConv}
          playbooks={playbooks}
          tasks={tasks}
        />
      </div>

      {/* 剧本快捷启动:选择后 @引用 带入输入框(壳内执行,不跳转剧本页) */}
      <Modal
        open={quickPbOpen}
        onCancel={() => setQuickPbOpen(false)}
        footer={null}
        title="跑一个剧本"
        width={440}
      >
        <p style={{ fontSize: 13, color: 'var(--ws-ink-2)', margin: '12px 0 16px', lineHeight: 1.6 }}>
          选择一个剧本,将自动带入右侧输入框并聚焦。补充执行意图后回车即可运行,全程不出空间。
        </p>
        {(!playbooks || playbooks.length === 0) && (
          <div className="ws-rail-empty">
            <div className="ws-rail-empty-t">暂无剧本</div>
            <div className="ws-rail-empty-h">可在「剧本」页创建剧本后再回来运行。</div>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 380, overflowY: 'auto' }}>
          {(playbooks || []).map((pb: { playbook_id: number; playbook_name: string }) => (
            <div
              key={pb.playbook_id}
              role="button"
              tabIndex={0}
              className="ws-deliverable-card"
              style={{ width: '100%', cursor: 'pointer' }}
              onClick={() => handleQuickRun(pb)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleQuickRun(pb); }}
            >
              <span className="ws-deliverable-card__icon"><ScheduleOutlined /></span>
              <span className="ws-deliverable-card__info">
                <span className="ws-deliverable-card__name">{pb.playbook_name}</span>
                <span className="ws-deliverable-card__meta">点击引用到输入框并运行</span>
              </span>
              <RightOutlined className="ws-deliverable-card__chevron" />
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}