'use client';

import './scene-workspace.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { App, Button, Modal, Drawer } from 'antd';
import { CloseOutlined, LeftOutlined, MenuFoldOutlined, MenuUnfoldOutlined, RightOutlined, ScheduleOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { apiInterceptors, createConversation, getTaskInfo, linkConversation, listConversations, listPlaybooks, setCurrentConversation, getAppInfo } from '@/client/api';
import { getUsageConversationSummary, type ConversationUsageSummary } from '@/client/api/usage';
import { convIdBase } from '@/types/context-metrics';
import { getUserId } from '@/utils';
import { useSpaceRole } from '@/hooks/use-space-role';
import { useUserInput } from '@/hooks/use-user-input';
import { useVisibilityPolling } from '@/hooks/use-visibility-polling';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { AgentStep, DetailContext } from './agent-types';
import { AgentWorkspace } from './agent-workspace';
import { AgentWorkspaceInput } from './agent-workspace-input';
import { CallDetailProvider } from '@/components/chat/call-detail/CallDetailProvider';
import { SceneSpace } from './scene-space';
import { SceneTaskRail, statusLabel } from './scene-task-rail';
import { SceneSimpleRail, type SimpleHistoryItem } from './scene-simple-rail';
import { SceneSimpleInbox } from './scene-simple-inbox';
import { SceneSimpleWorkspace } from './scene-simple-workspace';
import type { AgentWorkspaceInputHandle } from './agent-workspace-types';
import { useSceneAgentChat } from './use-scene-agent-chat';
import type { WorkspaceViewMode } from './use-view-mode';

/** 欢迎态「试试这些」预设问题的兜底默认值;工作空间 settings 未配置时使用 */
const DEFAULT_SUGGEST_QUESTIONS = ['帮我看看这周的数据情况'];

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
  /** 视图模式(由页面 header 持有,记忆到 localStorage) */
  viewMode: WorkspaceViewMode;
  /** 简洁模式抽屉状态(header 待办角标 / 左栏「待办收件箱」共用) */
  simpleDrawer?: 'inbox' | 'overview' | null;
  onSimpleDrawerChange?: (drawer: 'inbox' | 'overview' | null) => void;
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
  viewMode,
  simpleDrawer,
  onSimpleDrawerChange,
}: SceneWorkspaceShellProps) {
  const workspaceId = workspace?.id;
  // 权限门控:对话输入区需 space.chat.use(查看角色只读,不发对话)
  const { can } = useSpaceRole(workspaceId);
  const chatReadOnly = !can('space.chat.use');
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
  // 简洁模式:中间区是否显示欢迎页(无会话/任务时 true,有内容时 false)
  const [simpleShowWelcome, setSimpleShowWelcome] = useState(true);
  // 简洁模式输入框共享的选中模型:提升到 shell 层,避免欢迎态→运行态切换、
  // 会话切换(key 重挂载 SceneSimpleWorkspace)后输入框内部模型 state 丢失回退默认
  const [simpleInputModel, setSimpleInputModel] = useState<string>('');

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

  // 简洁模式:convUid 为空时,首次发送前创建会话并注入
  const ensureConversation = async (): Promise<string | null> => {
    if (!workspaceId) return null;
    const [, newConv] = await apiInterceptors(createConversation({ workspace_id: workspaceId }));
    if (!newConv?.conv_uid) return null;
    await apiInterceptors(linkConversation({ workspace_id: workspaceId, conv_uid: newConv.conv_uid, user_id: Number(getUserId()) || undefined }));
    await apiInterceptors(setCurrentConversation(workspaceId, newConv.conv_uid));
    onConvChanged?.(newConv.conv_uid);
    return newConv.conv_uid;
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

  // Agent 头像数据:appCode 对应 app 的 icon/name(与通用聊天页同源)
  const { data: appInfoTuple } = useRequest(
    async () => (appCode ? apiInterceptors(getAppInfo({ app_code: appCode })) : ([null, null] as any)),
    { refreshDeps: [appCode] },
  );
  const appInfo = appInfoTuple?.[1];

  // 会话维度列表:剧本任务会话 + 大厅会话统一按 conv 维度展示。
  // refreshDeps 含 workspaceConvUid/taskConvUid:清理(新开会话)/切换会话/进入任务对话后自动刷新,
  // 新会话按 gmt_modified 倒序自然置顶。listsRefreshKey:对话开始(onConversationStart)即刷新,
  // 让后端兜底 link 的新会话/出错对话第一时间进入任务列表。
  const { data: conversations } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [, data] = await apiInterceptors(listConversations({ workspace_id: workspaceId, user_id: Number(getUserId()) || undefined, limit: 200 }));
      return data || [];
    },
    { refreshDeps: [workspaceId, workspaceConvUid, taskConvUid, listsRefreshKey] },
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
  // 页面隐藏/失焦时暂停,回到可见立即补刷并恢复。
  useVisibilityPolling(hasActiveTask(tasks) && !!onRefreshLists, onRefreshLists, 4000);

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
      // 切任务后默认在大厅中间区展示该会话的最终结果;若当前大厅曾被折叠(上一轮对话提交后),
      // 这里展开确保最终回复默认可见。
      expandSpace();
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
    if (step.type === 'tool_call' || step.type === 'llm' || step.type === 'skill_loaded') {
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

  // ── 简洁模式:数据与回调 ──────────────────────────────────────────────
  const isSimple = viewMode === 'simple';
  // 简洁模式:欢迎态 = 当前未打开任何任务/会话(有历史时也展示,历史在左栏)
  const simpleWelcome = isSimple && simpleShowWelcome && !activeTaskId;

  // 欢迎态「试试这些」预设问题:优先读取工作空间配置 settings.suggest_questions,
  // 为空或未配置时回退到默认问题。
  const suggestQuestions = useMemo(() => {
    const cfg = (workspace as any)?.settings?.suggest_questions;
    if (Array.isArray(cfg)) {
      const list = cfg.filter((q: unknown) => typeof q === 'string' && q.trim().length > 0);
      if (list.length > 0) return list;
    }
    return DEFAULT_SUGGEST_QUESTIONS;
  }, [workspace]);

  // 简洁模式复用同一份会话(chat hook),保证与运维模式零数据孤岛;
  // enabled 仅在简洁模式开启(运维模式由 AgentWorkspace 自己接管,避免双轮询)。
  // 欢迎态不传 convUid:首页输入框提交即新建会话(onConvCreated -> ensureConversation),
  // 而不是续写页面加载时恢复的旧 current conversation。
  const simpleChat = useSceneAgentChat({
    convUid: simpleWelcome ? undefined : rightConvUid,
    appCode,
    workspaceId,
    taskId: rightTaskId,
    focusArtifactId: focus?.id,
    tasks,
    playbooks,
    enabled: viewMode === 'simple',
    onConvCreated: ensureConversation,
    onWorkspaceEvent: handleWorkspaceEvent,
    onConversationStart: () => {
      setSimpleShowWelcome(false);
      onRefreshLists?.();
    },
  });

  // 会话是否仍在运行(SSE 进行中 或 后台轮询恢复的 RUNNING)。
  // 中间区「运行中」badge、输入按钮 running 态、左栏当前会话状态都用它保持一致,
  // 避免「重开运行中对话」时出现中间显示运行中、按钮/左侧列表却显示就绪/已完成的不一致。
  const isRunning = simpleChat.loading || simpleChat.convState === 'RUNNING';

  // 记录「观测到仍在运行」的会话 conv_uid(用于左栏状态持久化)。
  // 只在本会话处于前台、能观测到真实状态时才增删。切到其它任务时,删除动作仅作用于
  // 当前会话,不会把仍在上一个会话运行的会话误删,从而避免「切换任务后运行中的对话
  // 在列表里被误判为已完成」;切回该会话时若已到终态,则由下方 effect 一并清除。
  const [runningConvIds, setRunningConvIds] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!rightConvUid) return;
    setRunningConvIds((prev) => {
      const next = new Set(prev);
      if (isRunning) next.add(rightConvUid);
      else next.delete(rightConvUid);
      return next;
    });
  }, [isRunning, rightConvUid]);

  // 简洁模式历史项:任务 + 大厅会话统一按时间倒序
  const simpleItems = useMemo<SimpleHistoryItem[]>(() => {
    const taskItems: SimpleHistoryItem[] = (tasks || []).map((t) => ({
      key: `task-${t.id}`,
      kind: 'task',
      id: t.id,
      title: t.title || `任务 #${t.id}`,
      status:
        // 进行中:running/pending_trigger + draft(准备中)/blocked(阻塞)都归入进行中,
        // 不能折叠成绿色「已完成」—— 与运维模式 statusToTab 的分组语义保持一致
        t.status === 'running' || t.status === 'pending_trigger' ||
        t.status === 'draft' || t.status === 'blocked'
          ? 'running'
          : t.status === 'awaiting_human'
            ? 'waiting'
            : t.status === 'failed'
              ? 'failed'
              : 'done',
      statusLabel: statusLabel(t.status),
      updatedAt: t.gmt_created || t.started_at || t.gmt_modified || '',
      convUid: t.conv_session_id || undefined,
      taskId: t.id,
    }));
    const lobbyItems: SimpleHistoryItem[] = (conversations || [])
      .filter((c: any) => c.task_id == null)
      .map((c: any) => {
        const running = runningConvIds.has(c.conv_uid);
        return {
          key: `conv-${c.conv_uid}`,
          kind: 'lobby',
          id: c.conv_uid,
          title: c.title || `会话 ${String(c.conv_uid || '').slice(0, 8)}`,
          status: running ? 'running' : 'done',
          statusLabel: running ? '运行中' : '大厅会话',
          updatedAt: c.gmt_created || c.gmt_modified || '',
          convUid: c.conv_uid,
          taskId: null,
        };
      });
    return [...taskItems, ...lobbyItems].sort((a, b) => {
      const ta = a.updatedAt ? new Date(a.updatedAt).getTime() : 0;
      const tb = b.updatedAt ? new Date(b.updatedAt).getTime() : 0;
      return tb - ta;
    });
  }, [tasks, conversations, runningConvIds]);

  // 批量拉取会话级用量（模型 + token），供左栏历史列表 chip 展示，避免 N+1
  const simpleConvUids = useMemo(
    () => simpleItems.map((it) => it.convUid).filter(Boolean) as string[],
    [simpleItems],
  );
  const { data: convUsageMap = {} } = useRequest(
    async () => {
      if (!simpleConvUids.length) return {};
      const [err, res] = await apiInterceptors(getUsageConversationSummary(simpleConvUids));
      if (err) return {};
      const map: Record<string, ConversationUsageSummary> = {};
      (res || []).forEach((s) => {
        map[convIdBase(s.conv_id)] = s;
      });
      return map;
    },
    { refreshDeps: [simpleConvUids.join(',')] },
  );

  // 简洁模式:点击历史项进入对应任务/会话
  // 大厅会话(lobby):切 conv → 继续该会话的对话
  // 任务会话(task):进任务对话(activeTaskId → taskConvUid),且当前任务已绑定大厅会话时,
  // 一并把大厅会话切到任务的 conv,保证返回大厅时停留在该任务会话(直接使用的延续感)
  const handleSimpleOpenItem = (item: SimpleHistoryItem) => {
    setSimpleShowWelcome(false);
    if (item.kind === 'task' && item.taskId) {
      handleEnterConversation(item.taskId);
      if (item.convUid && item.convUid !== workspaceConvUid) {
        onConvChanged?.(item.convUid, item.taskId);
      }
      return;
    }
    if (item.convUid) {
      handleOpenConversation(item.convUid, null);
    }
  };

  // 简洁模式:点击「新任务」回到欢迎态,等待输入;不立刻创建会话,
  // 首次发送时才新建(convUid 未传入 -> ensureConversation),避免遗留空会话
  const handleSimpleNew = () => {
    setSimpleShowWelcome(true);
    setActiveTaskId(null);
    setDetailContext('dashboard');
    setPreviewItem(null);
  };

  // 简洁模式:待办入口 → 右侧滑出待办抽屉(不切模式,不打断当前会话)
  const handleSimpleOpenInbox = () => {
    onSimpleDrawerChange?.('inbox');
  };

  // 简洁模式:推荐问题 → 填入输入框并聚焦
  const handleSimpleAsk = (text?: string) => {
    if (text) agentInputRef.current?.insertText(`${text} `);
    agentInputRef.current?.focus();
  };

  // 简洁模式:输入框发送后隐藏欢迎页;
  // 运行中追问复用与运维模式一致的「补充输入」链路(投递到后端队列,不开新 SSE)
  const { submitUserInput } = useUserInput(rightConvUid);
  const handleSimpleSend = async (payload: any) => {
    if (simpleChat.loading || simpleChat.convState === 'RUNNING') {
      setSimpleShowWelcome(false);
      // 投递补充输入队列;后端校验确有活跃执行才入队。若提交失败(会话无活跃
      // 执行/僵尸状态),回退为正常发起对话,避免追问被投入无消费者队列而静默吞掉。
      const ok = await submitUserInput(payload.text);
      if (ok) {
        simpleChat.appendOptimisticUser(payload.text);
      } else {
        await simpleChat.send(payload);
      }
    } else {
      // 首次发送(欢迎态):不要在 send 前关闭欢迎页 —— 新建会话是异步的
      // (ensureConversation 内 createConversation/link/setCurrent 多次网络请求),
      // 提前关闭会让运行态先以「最后一次会话」的 convUid 渲染并拉取其历史(闪烁跳转)。
      // 欢迎页统一由 send 内部的 onConversationStart 在 ensureConversation 完成、
      // 新会话已写回 workspaceConvUid 之后关闭,一次渲染直达当前新会话。
      await simpleChat.send(payload);
    }
  };

  // ── 渲染 ────────────────────────────────────────────────────────────

  return (
    <CallDetailProvider convId={rightConvUid}>
      <div
        className={`ws-scene-shell${railOpen ? '' : ' ws-scene-shell--rail-closed'}${spaceCollapsed ? ' ws-scene-shell--space-collapsed' : ''}${isSimple ? ' ws-scene-shell--simple' : ''}`}
        data-pane={mobilePane}
      >
      {isSimple ? (
        /* ── 简洁模式 ── */
        <>
          {/* 左栏折叠/展开按钮(简洁模式常驻) */}
          <button
            type="button"
            className="ws-scene-shell__rail-toggle"
            aria-label={railOpen ? '收起历史列表' : '展开历史列表'}
            onClick={() => setRailOpen((v) => !v)}
          >
            <span className="ws-scene-shell__rail-toggle__icon">{railOpen ? <LeftOutlined /> : <RightOutlined />}</span>
          </button>
          {/* 左栏:历史任务列表(可折叠) */}
          <div className="ws-scene-shell__rail">
            <SceneSimpleRail
              items={simpleItems}
              currentConvUid={rightConvUid}
              currentTaskId={activeTaskId}
              inboxCount={interventions?.length || 0}
              disabled={switchingTask}
              onOpenItem={handleSimpleOpenItem}
              onNewConversation={handleSimpleNew}
              onOpenInbox={handleSimpleOpenInbox}
              usageMap={convUsageMap}
            />
          </div>
          {/* 中间:欢迎态 或 运行态双栏(输入条在左侧步骤流卡片内底部) */}
          <div className="ws-scene-shell__space">
            {simpleWelcome ? (
              <div className="ws-simple-welcome">
                <div className="ws-simple-welcome__hero">
                  <span className="ws-simple-welcome__ava">✦</span>
                  <h1 className="ws-simple-welcome__title">{workspace?.name || '场景空间'}</h1>
                  <p className="ws-simple-welcome__sub">
                    {workspace?.description || '输入指令,Agent 帮你完成任务'}
                  </p>
                </div>
                <div className="ws-simple-welcome__composer">
                  <AgentWorkspaceInput
                    ref={agentInputRef}
                    convUid={rightConvUid}
                    appInfo={appInfo}
                    model={simpleInputModel}
                    onModelChange={setSimpleInputModel}
                    onSend={handleSimpleSend}
                    loading={isRunning}
                    onStop={simpleChat.abort}
                    disabled={switchingTask}
                    readOnly={chatReadOnly}
                    playbooks={playbooks || []}
                    focus={focus}
                    onClearFocus={() => setFocusDismissed(true)}
                    usageMetrics={simpleChat.usageMetrics}
                  />
                </div>
                <div className="ws-simple-welcome__sugg">
                  <div className="ws-simple-welcome__sugg-label">试试这些</div>
                  <div className="ws-simple-welcome__sugg-row">
                    {(playbooks || []).slice(0, 2).map((pb: any) => (
                      <button
                        key={pb.playbook_id}
                        type="button"
                        className="ws-simple-welcome__sugg-item"
                        onClick={() => handleSimpleAsk(`跑一下「${pb.playbook_name}」`)}
                      >
                        跑一下「{pb.playbook_name}」
                      </button>
                    ))}
                    {suggestQuestions.map((q) => (
                      <button
                        key={q}
                        type="button"
                        className="ws-simple-welcome__sugg-item"
                        onClick={() => handleSimpleAsk(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="ws-simple-run">
                <SceneSimpleWorkspace
                  // 切换会话/任务时强制重挂载:重置右侧已选步骤/文件等内部状态,
                  // 避免打开第二个任务后右侧仍停留第一个任务的步骤详情
                  key={rightConvUid}
                  view={simpleChat.workspaceView}
                  running={isRunning}
                  error={simpleChat.error}
                  switchingTask={switchingTask}
                  convLoadError={convLoadError}
                  retryLoadConv={retryLoadConv}
                  agentIcon={appInfo?.icon}
                  agentName={appInfo?.app_name}
                  modelName={simpleChat.modelName}
                  onInteractionResume={(msg) => simpleChat.send({ text: msg })}
                  onExit={() => {
                    setSimpleShowWelcome(true);
                    setActiveTaskId(null);
                  }}
                  inputSlot={
                    <AgentWorkspaceInput
                    ref={agentInputRef}
                    convUid={rightConvUid}
                    appInfo={appInfo}
                    model={simpleInputModel}
                    onModelChange={setSimpleInputModel}
                    onSend={handleSimpleSend}
                    loading={isRunning}
                    onStop={simpleChat.abort}
                    disabled={switchingTask}
                    readOnly={chatReadOnly}
                    playbooks={playbooks || []}
                    focus={focus}
                    onClearFocus={() => setFocusDismissed(true)}
                    onClearContext={() => handleNewConversation('已清空上下文')}
                    usageMetrics={simpleChat.usageMetrics}
                  />
                  }
                />
              </div>
            )}
          </div>
          {/* 简洁模式:待办抽屉(右侧滑出,不切模式不打断当前会话;内容为真实待办列表) */}
          <Drawer
            title="待办收件箱"
            placement="right"
            width={420}
            open={simpleDrawer === 'inbox'}
            onClose={() => onSimpleDrawerChange?.(null)}
          >
            <SceneSimpleInbox
              workspaceId={workspaceId}
              disabled={switchingTask}
              onOpenItem={(item) => {
                // 点击待办:关抽屉并按类型进入(任务对话 / 介入 / 提案 / 手动详情)
                onSimpleDrawerChange?.(null);
                handleSelectInbox(item);
              }}
              onResolved={onRefreshLists}
            />
          </Drawer>
        </>
      ) : (
        /* ── 运维模式(原有布局) ── */
        <>
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
            <span className="ws-scene-shell__rail-toggle__icon">{railOpen ? <LeftOutlined /> : <RightOutlined />}</span>
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
                <span className="ws-scene-shell__space-toggle__icon"><MenuUnfoldOutlined /></span>
                <span className="ws-scene-shell__space-toggle__label">展开大厅</span>
              </>
            ) : (
              <span className="ws-scene-shell__space-toggle__icon"><MenuFoldOutlined /></span>
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
              chatReadOnly={chatReadOnly}
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
        </>
      )}

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
    </CallDetailProvider>
  );
}