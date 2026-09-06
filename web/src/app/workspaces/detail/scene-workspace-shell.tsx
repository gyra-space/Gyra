'use client';

import './scene-workspace.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { App, Button, Input, Modal, Drawer } from 'antd';
import { CloseOutlined, LeftOutlined, MenuFoldOutlined, MenuUnfoldOutlined, RightOutlined, ScheduleOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { apiInterceptors, createConversation, getTaskInfo, linkConversation, listConversations, listPlaybooks, setCurrentConversation, getAppInfo, listResources, deleteTask, deleteConversation, favoriteConversation, renameConversation } from '@/client/api';
import { getUsageConversationSummary, type ConversationUsageSummary } from '@/client/api/usage';
import { toConversationId } from '@/types/context-metrics';
import { getUserId } from '@/utils';
import { useSpaceRole } from '@/hooks/use-space-role';
import { useUserInput } from '@/hooks/use-user-input';
import { useVisibilityPolling } from '@/hooks/use-visibility-polling';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { AgentStep, DetailContext } from './agent-types';
import { AgentWorkspace } from './agent-workspace';
import { AgentWorkspaceInput } from './agent-workspace-input';
import { inputQueueActions } from './scene-input-queue';
import DockPanel from '@/components/chat/dock/dock-panel';
import { CallDetailProvider } from '@/components/chat/call-detail/CallDetailProvider';
import { SceneSpace } from './scene-space';
import { SceneTaskRail, statusLabel } from './scene-task-rail';
import { SceneSimpleRail, type SimpleHistoryItem } from './scene-simple-rail';
import { SceneSimpleInbox } from './scene-simple-inbox';
import { SceneSimpleWorkspace } from './scene-simple-workspace';
import { SimpleAppCardLauncher } from './app-card/SimpleAppCardLauncher';
import { AppCardPage } from './app-card/AppCardPage';
import type { AgentWorkspaceInputHandle } from './agent-workspace-types';
import type { SubAgentRef } from '@/components/chat/input/trigger-types';
import { useSceneAgentChat } from './use-scene-agent-chat';
import { hasActiveTask } from './scene-workspace-utils';
import type { WorkspaceViewMode } from './use-view-mode';

/** 欢迎态「试试这些」预设问题的兜底默认值;工作空间 settings 未配置时使用 */
const DEFAULT_SUGGEST_QUESTIONS = ['帮我看看这周的数据情况'];

interface SceneWorkspaceShellProps {
  workspace: any;
  tasks: any[];
  interventions: any[];
  workspaceConvUid: string;
  appCode: string;
  onRefreshLists?: () => void;
  /** 任务/介入列表刷新信号(lobby 最近产出/交付/待办据此同步刷新) */
  listsRefreshKey?: number;
  onConvChanged?: (conversationId: string, taskId?: number | null) => void;
  convLoadError?: string | null;
  retryLoadConv?: () => void;
  /** 从会话列表选中会话时携带的 task_id:number=进 task 对话,null=workspace 级会话,
   * undefined=非列表触发(初始/任务栏进入)。 */
  pendingTaskId?: number | null | undefined;
  /** 视图模式(由页面 header 持有,记忆到 localStorage) */
  viewMode: WorkspaceViewMode;
  /**
   * 仅把「当前打开的会话/任务」回写地址栏,不改任何 React state。
   * 刷新恢复的唯一通道:状态切换即写入 URL,刷新后由上层把 URL 还原成同一现场。
   */
  onUrlSync?: (patch: { convUid?: string | null; taskId?: number | null; newTask?: boolean }) => void;
  /** 简洁模式「新任务」:清空会话进欢迎态,由上层打 new_task=1 标记并复位当前会话 */
  onNewTask?: () => void;
  /** 简洁模式欢迎页初始值:URL 不带深链(conv_uid/task_id)时才展示欢迎页 */
  initialShowWelcome?: boolean;
  /** 「新任务」态(上层 handleNewTask 置位,URL new_task=1):首条发送懒创建会话时
   * 不触发 onConvChanged,避免 URL 从 new_task=1 跳回 conv_uid、conversationId 翻转打断 SSE 流 */
  manualNew?: boolean;
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
  onUrlSync,
  onNewTask,
  initialShowWelcome = true,
  manualNew,
  simpleDrawer,
  onSimpleDrawerChange,
}: SceneWorkspaceShellProps) {
  const workspaceId = workspace?.id;
  // 权限门控:对话输入区需 space.chat.use(查看角色只读,不发对话)
  const { can, role } = useSpaceRole(workspaceId);
  const chatReadOnly = !can('space.chat.use');
  const canManageTask = can('space.task.manage');
  const canUseChat = can('space.chat.use');
  // 过程洞察:owner/contributor 可查看执行步骤详情;viewer(业务用户)只看结果,
  // 执行过程折叠成单行且步骤不可点开(本期仅前端隐藏,接口数据仍下发)
  const canViewProcess = role === 'owner' || role === 'contributor';
  const [previewItem, setPreviewItem] = useState<any>(null);
  const [detailContext, setDetailContext] = useState<DetailContext>('dashboard');
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [activeTask, setActiveTask] = useState<any>(null);
  const [taskConvUid, setTaskConvUid] = useState<string>('');
  const [switchingTask, setSwitchingTask] = useState(false);
  const { message, modal } = App.useApp();
  // rail 抽屉(中屏)与单列 tab(小屏)状态
  const [railOpen, setRailOpen] = useState(true);
  const [mobilePane, setMobilePane] = useState<'rail' | 'space' | 'agent'>('space');
  // 大厅容器折叠:折叠后 Agent 空间占满主区,专注执行进展;
  // 点击步骤/文件卡片等主动查看动作会自动展开;折叠期间被动到达的新内容点亮角标。
  const [spaceCollapsed, setSpaceCollapsed] = useState(false);
  const [spaceHasNew, setSpaceHasNew] = useState(false);
  // 场景空间最大化:中间 space 占满整个壳区,隐藏左侧任务栏与右侧 Agent 对话窗口。
  // 典型场景:在空间内使用应用卡片/大屏看板等需要最大显示面积时,可最大化并随时还原。
  const [spaceMaximized, setSpaceMaximized] = useState(false);
  const toggleSpaceMaximized = () => {
    // 最大化与「折叠大厅」互斥:最大化时强制展开大厅,避免双状态叠加冲突
    setSpaceCollapsed(false);
    setSpaceMaximized((v) => !v);
  };
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
  // 简洁模式应用使用态:欢迎态点击应用卡片 → 中间区切换为全屏应用页(不创建会话)。
  const [simpleAppCard, setSimpleAppCard] = useState<any>(null);
  const prevActiveTaskId = useRef<number | null>(null);
  const agentInputRef = useRef<AgentWorkspaceInputHandle>(null);
  // URL 回写通道用 ref 持有:onUrlSync 依赖 searchParams 会随 URL 变化重建,
  // 若直接进入下方任务的 effect 依赖数组,会导致任务详情被反复重新拉取。
  const onUrlSyncRef = useRef(onUrlSync);
  useEffect(() => {
    onUrlSyncRef.current = onUrlSync;
  }, [onUrlSync]);
  // 简洁模式:中间区是否显示欢迎页(无会话/任务时 true,有内容时 false)。
  // 初始值由 URL 深链决定:带 conv_uid/task_id 说明是刷新恢复或分享进入,直达会话内容。
  const [simpleShowWelcome, setSimpleShowWelcome] = useState(initialShowWelcome);
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

  // 会话缺失时(欢迎态/新进入空间)首次发送或上传前创建会话并注入。
  // 不在进入页面时预建,避免堆积空会话。
  const ensureConversation = async (): Promise<string | null> => {
    if (!workspaceId) return null;
    const [, newConv] = await apiInterceptors(createConversation({ workspace_id: workspaceId }));
    if (!newConv?.conv_uid) return null;
    await apiInterceptors(linkConversation({ workspace_id: workspaceId, conv_uid: newConv.conv_uid, user_id: Number(getUserId()) || undefined }));
    await apiInterceptors(setCurrentConversation(workspaceId, newConv.conv_uid));
    // 「新任务」欢迎态首次发送懒创建(manualNew=true):不触发 onConvChanged,
    // 否则父组件会把 URL 从 new_task=1 翻回 conv_uid、并在发送窗口内翻转 conversationId,
    // 打断刚发起的 SSE 流(表现为「对话直接被中断」)。会话已由 setCurrentConversation 持久化,
    // 消息经 send 内部 internalConvUid 正常投递,列表刷新(onRefreshLists)后出现在历史中。
    if (!manualNew) {
      onConvChanged?.(newConv.conv_uid);
    }
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

  // 空间配置模型:取「空间设置 → 空间模型」列表里默认(is_default)的模型作为输入框默认模型。
  // 无默认标记时按原逻辑取第一个启用的模型;未配置空间模型时为空字符串,
  // 输入框内部回退到全局模型列表首个(与旧逻辑一致)。
  const { data: spaceModels } = useRequest(async () => {
    if (!workspaceId) return [];
    const [, data] = await apiInterceptors(listResources({ workspace_id: workspaceId, type: 'llm_model' }));
    return data || [];
  }, { refreshDeps: [workspaceId] });

  const spaceDefaultModel = useMemo(() => {
    const list = spaceModels || [];
    if (!list.length) return '';
    // 优先取空间「设为默认」标记的模型(is_default);无标记时取第一个启用的模型,
    // 避免后端按 gmt_modified 倒序返回时误选最近修改而非默认模型。
    const isDefault = (m: any) => !!(m?.config && m.config.is_default);
    const first =
      list.find((m: any) => m.is_active !== false && isDefault(m)) ||
      list.find((m: any) => isDefault(m)) ||
      list.find((m: any) => m.is_active !== false) ||
      list[0];
    return first?.config?.model || first?.physical_ref || first?.name || '';
  }, [spaceModels]);

  // Agent 头像数据:appCode 对应 app 的 icon/name(与通用聊天页同源)
  const { data: appInfoTuple } = useRequest(
    async () => (appCode ? apiInterceptors(getAppInfo({ app_code: appCode })) : ([null, null] as any)),
    { refreshDeps: [appCode] },
  );
  const appInfo = appInfoTuple?.[1];

  // `@` 接管态(会话级):提升到本层持有,供会话头部/轮次头部显示实际执行的子 Agent。
  // 仅当前会话生效(刷新后回退默认主 Agent),不做持久化。
  const [simpleSubAgent, setSimpleSubAgent] = useState<SubAgentRef | null>(null);
  // 界面归属:被 @ 的子 Agent 接管时显示子 Agent 名/头像,否则显示空间默认主 Agent。
  const simpleDisplayAgentName = simpleSubAgent?.name || appInfo?.app_name || 'Agent';
  const simpleDisplayAgentIcon = simpleSubAgent?.physical_ref ? null : appInfo?.icon;

  // 会话维度列表:合约任务会话 + 大厅会话统一按 conv 维度展示。
  // refreshDeps 含 workspaceConvUid/taskConvUid:清理(新开会话)/切换会话/进入任务对话后自动刷新,
  // 新会话按 gmt_modified 倒序自然置顶。listsRefreshKey:对话开始(onConversationStart)即刷新,
  // 让后端兜底 link 的新会话/出错对话第一时间进入任务列表。
  const { data: conversations, mutate: mutateConversations } = useRequest(
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
      // 退出任务对话:清掉 URL 上的 task_id,刷新后停在会话工作台而非回到旧任务
      onUrlSyncRef.current?.({ taskId: null });
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
          // 任务会话 conv 解析完成后补齐 URL:刷新时右侧 Agent 直接用它渲染,
          // 不再先闪一下 workspace 级会话再去换任务会话。
          if (res?.conv_session_id) {
            onUrlSyncRef.current?.({ convUid: res.conv_session_id, taskId: activeTaskId });
          }
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
    // 刷新恢复路径(pendingTaskId)也走这里:关闭简洁模式欢迎页,直达任务会话
    setSimpleShowWelcome(false);
    // 进任务对话立刻把 task_id 写进 URL:即便后续 getTaskInfo 失败,
    // 刷新也能靠 task_id 重新走一遍 handleEnterConversation 恢复现场。
    onUrlSync?.({ taskId });
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
    // 返回工作台(无顶栏)时退出最大化,避免失去还原入口
    setSpaceMaximized(false);
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

  // 合约快捷启动:选择后以 @引用 带入输入框并聚焦,复用输入框的合约执行链路
  const [quickPbOpen, setQuickPbOpen] = useState(false);
  const handleQuickRun = (pb: { playbook_id: number; playbook_name: string }) => {
    agentInputRef.current?.insertText(`@剧本#${pb.playbook_id}「${pb.playbook_name}」 `);
    setQuickPbOpen(false);
    agentInputRef.current?.focus();
    setMobilePane('agent');
  };

  // 专家团队卡动作(Agent Team 空间重构 Phase 2.3):
  // 对话 → @专家 带入输入框;编辑 → 空间内专家编辑器;派单 → 专家 dispatch。
  const handleTalkExpert = (expert: any) => {
    const name = expert?.app_name || expert?.app_code;
    agentInputRef.current?.insertText(`@${name} `);
    agentInputRef.current?.focus();
    setMobilePane('agent');
  };
  const handleEditExpert = (expert: any) => {
    window.location.href = `/workspaces/detail/${workspaceId}/experts`;
  };
  const handleDispatchExpert = async (expert: any) => {
    handleTalkExpert(expert);
    setMobilePane('agent');
  };

  // 能力管理权限(空间 owner):能力绑定 tab 的编辑/移除是否可用。
  const canManageCapability = can('space.capability.manage');

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

  // 从「会话」视图进入对应对话:合约任务会话(有 task_id)进任务对话,
  // 大厅会话(无 task_id)切回 workspace 级会话并回到 dashboard。
  const handleOpenConversation = async (conversationId: string, taskId: number | null) => {
    if (taskId) {
      handleEnterConversation(taskId);
      return;
    }
    // 乐观切换:先切 UI(onConvChanged 仅上层 setState,零耗时),右侧立即出现
    // "会话加载中…";setCurrentConversation 持久化放后台,不再阻塞等待网络往返
    // (失败仅影响"最近会话"记忆,不回滚 UI)。
    setActiveTaskId(null);
    setDetailContext('dashboard');
    setPreviewItem(null);
    onConvChanged?.(conversationId, null);
    if (workspaceId != null) {
      await apiInterceptors(setCurrentConversation(workspaceId, conversationId));
    }
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
  // 欢迎态不传 conversationId:首页输入框提交即新建会话(onConvCreated -> ensureConversation),
  // 而不是续写历史会话。
  const simpleChat = useSceneAgentChat({
    // rightConvUid 为 ''(会话未创建/未写回)时归一化为 undefined:
    // 空串会绕过 hook 里 `conversationId ?? internalConvUid` 的空值合并,
    // 把 effectiveConvUid 从刚创建的会话劫持成 '' → 会话切换 effect 误判
    // 为切换会话而 abort 刚发出的 SSE(表现为对话直接被中断)。
    conversationId: simpleWelcome ? undefined : rightConvUid || undefined,
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
    // 收藏状态统一以 conversations 的 conv 为准:任务项按 conv_session_id 回查
    const favSet = new Set(
      (conversations || []).filter((c: any) => c.is_favorited).map((c: any) => String(c.conv_uid)),
    );
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
      conversationId: t.conv_session_id || undefined,
      taskId: t.id,
      isFavorited: t.conv_session_id ? favSet.has(String(t.conv_session_id)) : false,
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
          conversationId: c.conv_uid,
          taskId: null,
          isFavorited: favSet.has(String(c.conv_uid)),
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
    () => simpleItems.map((it) => it.conversationId).filter(Boolean) as string[],
    [simpleItems],
  );
  const { data: convUsageMap = {} } = useRequest(
    async () => {
      if (!simpleConvUids.length) return {};
      const [err, res] = await apiInterceptors(getUsageConversationSummary(simpleConvUids));
      if (err) return {};
      const map: Record<string, ConversationUsageSummary> = {};
      (res || []).forEach((s) => {
        map[toConversationId(s.conv_id)] = s;
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
      if (item.conversationId && item.conversationId !== workspaceConvUid) {
        onConvChanged?.(item.conversationId, item.taskId);
      }
      return;
    }
    if (item.conversationId) {
      handleOpenConversation(item.conversationId, null);
    }
  };

  // 简洁模式:点击「新任务」回到欢迎态,等待输入;不立刻创建会话,
  // 首次发送时才新建(conversationId 未传入 -> ensureConversation),避免遗留空会话。
  // 同时交给上层(handleNewTask)清空会话并给 URL 打 new_task=1 标记:
  // 点了新任务即关闭最后一个默认打开的任务,刷新时不然会因深链(hasDeepLink)
  // 再次跳到旧会话,而非停在新建首页。
  const handleSimpleNew = () => {
    // eslint-disable-next-line no-console
    console.log('[DEBUG handleSimpleNew] onNewTask?', typeof onNewTask);
    // 清掉 chat hook 懒创建的内部会话:上一轮「新任务」流里父层 conversationId
    // 保持空串,prop 无变化时 hook 内部的清空 effect 不会重跑,不显式清掉的话
    // 下次首页发送会复用上一轮懒创建的会话(首页提问跑进最后一个会话)。
    simpleChat.resetConv();
    setSimpleShowWelcome(true);
    setActiveTaskId(null);
    setDetailContext('dashboard');
    setPreviewItem(null);
    setSimpleAppCard(null);
    onNewTask?.();
  };

  // 简洁模式:待办入口 → 右侧滑出待办抽屉(不切模式,不打断当前会话)
  const handleSimpleOpenInbox = () => {
    onSimpleDrawerChange?.('inbox');
  };

  // 简洁模式:删除历史项(任务/会话)。按 kind 路由到对应删除接口并刷新列表。
  const handleSimpleDelete = (item: SimpleHistoryItem) => {
    const wsId = workspaceId;
    if (!wsId) return;
    if (item.kind === 'task' && item.taskId != null) {
      const taskId = item.taskId;
      modal.confirm({
        title: '删除任务',
        content: '删除后任务记录不可恢复(运行中/待介入的任务需先终止)。',
        okText: '删除',
        okButtonProps: { danger: true },
        onOk: async () => {
          const [err] = await apiInterceptors(deleteTask(taskId));
          if (err) { message.error(err.message); return; }
          message.success('已删除');
          onRefreshLists?.();
          // 删除的是当前打开的任务时,回到欢迎态/工作台,避免停留死引用
          if (activeTaskId === taskId) {
            setActiveTaskId(null);
            setDetailContext('dashboard');
            setPreviewItem(null);
          }
        },
      });
      return;
    }
    if (item.conversationId) {
      const conversationId = item.conversationId;
      modal.confirm({
        title: '删除会话',
        content: '删除后该会话将从空间任务列表移除,不可恢复。',
        okText: '删除',
        okButtonProps: { danger: true },
        onOk: async () => {
          const [err] = await apiInterceptors(deleteConversation({ workspace_id: wsId, conv_uid: conversationId }));
          if (err) { message.error(err.message); return; }
          message.success('已删除');
          onRefreshLists?.();
        },
      });
    }
  };

  // 简洁模式:收藏/取消收藏(任务/会话统一挂到其 conv 上)。
  // 成功后仅本地替换该会话的收藏状态,避免整表刷新导致列表跳动。
  const handleSimpleToggleFavorite = async (item: SimpleHistoryItem) => {
    const wsId = workspaceId;
    if (!wsId || !item.conversationId) return;
    const conversationId = item.conversationId;
    const nextFav = !item.isFavorited;
    const [err] = await apiInterceptors(
      favoriteConversation({ workspace_id: wsId, conv_uid: conversationId, favorited: nextFav }),
    );
    if (err) {
      message.error(err.message);
      return;
    }
    message.success(nextFav ? '已收藏' : '已取消收藏');
    mutateConversations((list: any[] = []) =>
      list.map((c: any) =>
        c.conv_uid === conversationId
          ? { ...c, is_favorited: nextFav, favorited_at: nextFav ? new Date().toISOString() : null }
          : c,
      ),
    );
  };

  // 简洁模式:重命名会话(lobby 项)。弹窗收集新名称 -> renameConversation -> 刷新列表。
  const [renameItem, setRenameItem] = useState<SimpleHistoryItem | null>(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [renaming, setRenaming] = useState(false);

  const handleSimpleRename = (item: SimpleHistoryItem) => {
    setRenameItem(item);
    setRenameTitle(item.title);
  };

  const handleSimpleRenameSubmit = async () => {
    if (!renameItem?.conversationId) return;
    const title = renameTitle.trim();
    if (!title) { message.warning('请输入会话名称'); return; }
    setRenaming(true);
    const [err] = await apiInterceptors(renameConversation(renameItem.conversationId, title));
    setRenaming(false);
    if (err) { message.error(err.message); return; }
    message.success('已重命名');
    setRenameItem(null);
    onRefreshLists?.();
  };

  // 简洁模式:推荐问题 → 填入输入框并聚焦
  const handleSimpleAsk = (text?: string) => {
    if (text) agentInputRef.current?.insertText(`${text} `);
    agentInputRef.current?.focus();
  };

  // 简洁模式:输入框发送后隐藏欢迎页;
  // 运行中追问复用与运维模式一致的「补充输入」链路(投递到后端队列,不开新 SSE)。
  // 队列条:对话运行中轮询拉取权威 queue 计数,展示「排队 N 条 + 具体消息」,
  // 被消费后由轮询回显为独立用户气泡。
  const {
    submitUserInput,
    hasPendingInput,
    queueLength,
    getPendingInputs,
    consumePendingInputs,
    clearQueue,
    startPolling: startQueuePolling,
    stopPolling: stopQueuePolling,
  } = useUserInput(rightConvUid, {
    // 补充输入「先入队,agent 消费后才展示」:队列轮询检测到被消费时,
    // 才把该消息上屏为独立用户气泡(不再提交即上屏)。
    onConsumed: (items) => {
      items.forEach((i) => simpleChat.appendOptimisticUser(i.content));
    },
  });
  // 对话运行中开启队列轮询(每 2s 拉取 queueState 刷新计数),停运即停,
  // 让「排队 N 条」随后端消费进度实时变化。
  useEffect(() => {
    if (isRunning) {
      startQueuePolling(2000);
    } else {
      stopQueuePolling();
      // 兜底:运行结束(轮询停)时,本地仍滞留未确认消费的消息直接上屏,
      // 避免追问永久不可见(例如消费发生在最后一次轮询之后)。
      consumePendingInputs().forEach((i) => simpleChat.appendOptimisticUser(i.content));
    }
  }, [isRunning, startQueuePolling, stopQueuePolling, consumePendingInputs, simpleChat.appendOptimisticUser]);
  // 「取消排队」真实动作注入到 widget 注册表(input_queue 的「取消排队」按钮经它调用),
  // 避免把 hook 依赖带进组件注册表;clearQueue 清空后端队列并复位本地计数。
  useEffect(() => {
    inputQueueActions.onClear = clearQueue;
    return () => {
      inputQueueActions.onClear = undefined;
    };
  }, [clearQueue]);
  // 运行中补充输入队列作为 Composer Dock 的 input_queue widget:与待办/子任务同处
  // 输入框上方的 dock 容器(单行摘要 + 向上展开),不再割裂成独立卡片。无排队时不注入。
  const queueDockWidget = useMemo(() => {
    if (!hasPendingInput || queueLength <= 0) return null;
    const items = getPendingInputs().map((i) => i.content);
    // 后端按 FIFO 消费:仍在排队的是本地提交列表末尾 queueLength 条。
    const shown = items.slice(Math.max(0, items.length - queueLength));
    return {
      id: 'input-queue',
      type: 'input_queue',
      payload: { items: shown, total: queueLength },
    } as const;
  }, [hasPendingInput, queueLength, getPendingInputs]);
  const simpleDockWidgets = useMemo(() => {
    const base = simpleChat.dockWidgets || {};
    return queueDockWidget ? { ...base, 'input-queue': queueDockWidget } : base;
  }, [simpleChat.dockWidgets, queueDockWidget]);
  // 上传附件用:优先复用空间当前会话;仅在连当前会话都没有时才懒创建。
  // 上传接口本身不落会话(文件存 gyra-fs,引用随消息载荷下发),此处会话
  // 只为满足上传请求的参数上下文,避免为上传无谓产生空会话。
  const ensureConversationForUpload = async (): Promise<string | null> => {
    if (rightConvUid) return rightConvUid;
    return ensureConversation();
  };
  const handleSimpleSend = async (payload: any) => {
    // 欢迎态首页提交:无论上一轮会话是否仍在运行(loading/RUNNING 残留态),
    // 一律 forceNew 新建会话,不与任何已存在/运行中的会话纠缠。否则上一轮会话
    // 的残留态(含懒创建残留的 internalConvUid)会让本次请求被当作「补充输入」
    // 投递到旧会话队列,追问承接在旧对话里,而不是真正新开会话。
    if (simpleWelcome) {
      await simpleChat.send(payload, { forceNew: true });
      return;
    }
    if (simpleChat.loading || simpleChat.convState === 'RUNNING') {
      setSimpleShowWelcome(false);
      // 投递补充输入队列;后端校验确有活跃执行才入队。若提交失败(会话无活跃
      // 执行/僵尸状态),回退为正常发起对话,避免追问被投入无消费者队列而静默吞掉。
      // 入队成功不在此上屏:消息展示由队列轮询检测到被 agent 消费后(onConsumed)
      // 才上屏,与「先入队、消费后展示」语义一致。
      const ok = await submitUserInput(payload.text);
      if (!ok) {
        await simpleChat.send(payload);
      }
    } else {
      // 运行态下、会话空闲时继续发送:复用当前会话;新建会话的欢迎态
      // 已由上方 simpleWelcome 分支处理。不要在 send 前关闭欢迎页 ——
      // 新建会话是异步的(ensureConversation 内 createConversation/link/setCurrent
      // 多次网络请求),提前关闭会让运行态先以「最后一次会话」的 conversationId
      // 渲染并拉取其历史(闪烁跳转)。欢迎页统一由 send 内部的 onConversationStart
      // 在 ensureConversation 完成、新会话已写回 workspaceConvUid 之后关闭,
      // 一次渲染直达当前新会话。
      await simpleChat.send(payload);
    }
  };

  // ── 渲染 ────────────────────────────────────────────────────────────

  return (
    // 调用详情抽屉的会话 id:优先父层写回的 rightConvUid;「新任务」流父层保持空串
    //(懒创建不触发 onConvChanged,避免翻转 conversationId 打断 SSE),此时用
    // chat hook 内部生效的 convUid 兜底,否则抽屉因 conversationId 为空而不发请求。
    <CallDetailProvider conversationId={rightConvUid || simpleChat.convUid || undefined}>
      <div
        className={`ws-scene-shell${railOpen ? '' : ' ws-scene-shell--rail-closed'}${spaceCollapsed ? ' ws-scene-shell--space-collapsed' : ''}${spaceMaximized ? ' ws-scene-shell--space-maximized' : ''}${isSimple ? ' ws-scene-shell--simple' : ''}`}
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
              onDeleteItem={handleSimpleDelete}
              onRenameItem={handleSimpleRename}
              onToggleFavorite={handleSimpleToggleFavorite}
              canDeleteTask={canManageTask}
              canDeleteConversation={canUseChat}
              canRenameConversation={canUseChat}
              canFavoriteConversation={canUseChat}
            />
          </div>
          {/* 中间:欢迎态 或 运行态双栏(输入条在左侧步骤流卡片内底部) */}
          <div className="ws-scene-shell__space">
            {simpleAppCard && isSimple ? (
              /* 简洁模式 · 应用使用态:全屏常驻子应用,不创建会话 */
              <div className="ws-simple-app">
                <div className="ws-simple-app__bar">
                  <button type="button" className="ws-simple-app__back" onClick={() => setSimpleAppCard(null)}>
                    <LeftOutlined /> 返回
                  </button>
                  <span className="ws-simple-app__hint">正在运行子应用,不进入任务记录</span>
                </div>
                <AppCardPage card={simpleAppCard} workspaceId={workspaceId} onDeleted={() => setSimpleAppCard(null)} />
              </div>
            ) : simpleWelcome ? (
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
                    conversationId={rightConvUid}
                    workspaceId={workspaceId}
                    attachmentScopeKey={workspaceId != null ? `ws:${workspaceId}` : undefined}
                    onEnsureConversation={ensureConversationForUpload}
                    appInfo={appInfo}
                    model={simpleInputModel}
                    defaultModel={spaceDefaultModel}
                    onModelChange={setSimpleInputModel}
                    subAgent={simpleSubAgent ?? undefined}
                    onSubAgentChange={setSimpleSubAgent}
                    onSend={handleSimpleSend}
                    loading={isRunning}
                    onStop={simpleChat.abort}
                    disabled={switchingTask || simpleChat.convLoading}
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
                <SimpleAppCardLauncher workspaceId={workspaceId} onOpen={(card) => setSimpleAppCard(card)} />
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
                  convLoading={simpleChat.convLoading}
                  convLoadError={convLoadError}
                  retryLoadConv={retryLoadConv}
                  agentIcon={simpleDisplayAgentIcon}
                  agentName={simpleDisplayAgentName}
                  modelName={simpleChat.modelName}
                  workspaceId={workspaceId}
                  canViewProcess={canViewProcess}
                  onInteractionResume={(msg) => simpleChat.send({ text: msg })}
                  onExit={() => {
                    // 退出任务回欢迎页:同样清掉懒创建的内部会话,保证首页提问新建
                    simpleChat.resetConv();
                    setSimpleShowWelcome(true);
                    setActiveTaskId(null);
                  }}
                  inputSlot={
                    <div className="ws-agent-workspace__input">
                      {/* Composer Dock:输入框上方贴合的「单行摘要 + 向上展开」容器,
                          待办/子任务/排队消息(运行中补充输入队列)同处一条 dock */}
                      <DockPanel widgets={simpleDockWidgets} />
                      <AgentWorkspaceInput
                        ref={agentInputRef}
                        conversationId={rightConvUid}
                        workspaceId={workspaceId}
                        attachmentScopeKey={workspaceId != null ? `ws:${workspaceId}` : undefined}
                        onEnsureConversation={ensureConversationForUpload}
                        appInfo={appInfo}
                        model={simpleInputModel}
                        defaultModel={spaceDefaultModel}
                        onModelChange={setSimpleInputModel}
                        subAgent={simpleSubAgent ?? undefined}
                        onSubAgentChange={setSimpleSubAgent}
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
                    </div>
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
              onOpenConversation={(conversationId, taskId) => {
                handleOpenConversation(conversationId, taskId);
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
              isMaximized={spaceMaximized}
              onToggleMaximize={toggleSpaceMaximized}
              onBack={handleBackToDashboard}
              onProposalResolved={bumpInbox}
              onEnterFlywheel={handleEnterFlywheel}
              onGuide={handleGuideAction}
              onSelectInbox={handleSelectInbox}
              onAsk={handleAsk}
              onTalkExpert={handleTalkExpert}
              onEditExpert={handleEditExpert}
              onDispatchExpert={handleDispatchExpert}
              canManage={canManageCapability}
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
              onSelectAppCard={(card) => {
                setPreviewItem({ payload: { card } });
                setDetailContext('app-card');
                setFocusDismissed(false);
                expandSpace();
                setMobilePane('space');
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
              conversationId={rightConvUid}
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
                // 会话开始即刷新任务列表:回合前路由预建的会话内任务(页面输入命中合约)
                // 在 chat 流里创建,不产生 task_created SSE 事件,靠这里第一时间入列表。
                onRefreshLists?.();
              }}
              inputRef={agentInputRef}
              switchingTask={switchingTask}
              convLoadError={convLoadError}
              retryLoadConv={retryLoadConv}
              // 无会话进入(新 tab/新任务)时,首次发送/上传懒创建会话
              onEnsureConversation={ensureConversation}
              playbooks={playbooks}
              tasks={tasks}
            />
          </div>
        </>
      )}

      {/* 合约快捷启动:选择后 @引用 带入输入框(壳内执行,不跳转合约页) */}
      <Modal
        open={quickPbOpen}
        onCancel={() => setQuickPbOpen(false)}
        footer={null}
        title="发起专家任务"
        width={440}
      >
        <p style={{ fontSize: 13, color: 'var(--ws-ink-2)', margin: '12px 0 16px', lineHeight: 1.6 }}>
          选择一个合约,将自动带入右侧输入框并聚焦。补充执行意图后回车即可运行,全程不出空间。
        </p>
        {(!playbooks || playbooks.length === 0) && (
          <div className="ws-rail-empty">
            <div className="ws-rail-empty-t">暂无专家</div>
            <div className="ws-rail-empty-h">可在「专家团队」页创建专家并挂载合约后再回来运行。</div>
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

      {/* 简洁模式:重命名会话弹窗 */}
      <Modal
        open={!!renameItem}
        title="重命名会话"
        okText="保存"
        cancelText="取消"
        confirmLoading={renaming}
        onCancel={() => setRenameItem(null)}
        onOk={handleSimpleRenameSubmit}
      >
        <Input
          value={renameTitle}
          maxLength={255}
          placeholder="输入新的会话名称"
          autoFocus
          onChange={(e) => setRenameTitle(e.target.value)}
          onPressEnter={handleSimpleRenameSubmit}
        />
      </Modal>
      </div>
    </CallDetailProvider>
  );
}