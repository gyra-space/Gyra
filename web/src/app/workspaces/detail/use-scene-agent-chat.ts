'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import useChat from '@/hooks/use-chat';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { UsageMetrics } from '@/types/context-metrics';
import { useChatPolling, type ConversationState } from '@/hooks/use-chat-polling';
import { stopChat, type ChatQueryResponse } from '@/client/api/chat';
import { applyDockFrame } from '@/components/chat/dock/apply-dock-frame';
import type { DockWidget, DockFrame } from '@/components/chat/dock/dock-types';
import type { AgentStep } from './agent-types';
import { parseAgentSteps } from './parse-agent-steps';
import { parseWorkspaceView } from './parse-workspace-view';
import { dedupOptimisticUser } from './dedup-optimistic-user';
import {
  buildSceneAgentSendData,
  resourcesToAttachments,
  type SceneAgentSendPayload,
} from './scene-agent-send-data';
import type {
  WorkspaceExecutionStep,
  WorkspaceUserAttachment,
  WorkspaceView,
} from './agent-workspace-types';
import { parseSceneAgentWorkspaceString } from './parse-scene-agent-workspace-string';

/**
 * 把 loaded_skills 事件的 <skill_content> XML 列表转换为 skill_loaded 执行步骤。
 * 纯函数(可单测):按技能名去重、从 XML 属性解析 name、透传完整 XML 供右侧渲染。
 */
export function buildSkillLoadedExecutionSteps(
  xmls: string[],
  existingTitles: string[] = [],
): WorkspaceExecutionStep[] {
  const existing = new Set(existingTitles);
  const now = new Date().toISOString();
  const steps: WorkspaceExecutionStep[] = [];
  for (const xml of xmls) {
    if (!xml || typeof xml !== 'string') continue;
    const nameMatch = xml.match(/<skill_content name="([^"]*)"/);
    const name = nameMatch ? nameMatch[1] : 'Skill';
    if (existing.has(name)) continue;
    existing.add(name);
    steps.push({
      id: `skill-loaded-${name}`,
      type: 'skill_loaded',
      title: name,
      status: 'done',
      ts: now,
      action: 'preload',
      skill_xml: xml,
    });
  }
  return steps;
}

/**
 * 把 loaded_memories 事件 / chat_query injected_context 的记忆块列表转换为
 * memory_loaded 执行步骤。纯函数(可单测):按 kind 生成稳定 id(mem-inject-{kind})
 * 去重 —— AGENTS.md/user.md 每轮都会注入但卡片只保留一份。
 */
export function buildMemoryInjectionSteps(
  blocks: { kind?: string; title?: string; chars?: number }[] | undefined,
  existingIds: string[] = [],
): WorkspaceExecutionStep[] {
  if (!Array.isArray(blocks)) return [];
  const existing = new Set(existingIds);
  const now = new Date().toISOString();
  const steps: WorkspaceExecutionStep[] = [];
  for (const block of blocks) {
    if (!block || typeof block !== 'object') continue;
    const kind = typeof block.kind === 'string' && block.kind ? block.kind : 'memory';
    const title = typeof block.title === 'string' && block.title ? block.title : kind;
    const id = `mem-inject-${kind}`;
    if (existing.has(id)) continue;
    existing.add(id);
    steps.push({
      id,
      type: 'memory_loaded',
      title,
      status: 'done',
      ts: now,
    });
  }
  return steps;
}

interface UseSceneAgentChatOptions {
  conversationId?: string;
  appCode?: string;
  workspaceId?: number | string;
  taskId?: number | string;
  focusArtifactId?: number | string;
  /** 工作空间全量任务列表:用于恢复视图时重注入绑定到当前会话的任务卡片 */
  tasks?: any[];
  /** 合约 id→名称映射:任务卡片展示合约名 */
  playbooks?: { playbook_id: number; playbook_name: string }[];
  onWorkspaceEvent?: (event: WorkspaceEvent) => void;
  /** 用户在 Agent 空间提交任务、开始一轮对话时触发(用于折叠中间内容区) */
  onConversationStart?: () => void;
  /** 是否启用轮询/连接:简洁模式与运维模式共用同一会话时,只让一个实例接管 */
  enabled?: boolean;
  /** 会话创建回调:conversationId 为空时由外层在首次发送前创建并注入 */
  onConvCreated?: (conversationId: string) => Promise<string | null>;
}

interface UseSceneAgentChatResult {
  steps: AgentStep[];
  workspaceView: WorkspaceView;
  loading: boolean;
  error: string | null;
  lastInput: SceneAgentSendPayload | null;
  /** 本次对话选用的模型名(与 lastInput.model 同源;运行中用于展示「xx模型 思考中」) */
  modelName?: string;
  /** SSE 断线自愈探测中(服务重启/网络抖动后的恢复窗口) */
  recovering: boolean;
  /** 手动重试断线恢复(错误横幅"重试连接"入口) */
  retryRecover: () => void;
  /** 后端会话运行状态:RUNNING 表示后台仍在执行(可关闭页面后恢复) */
  convState: ConversationState;
  /** 当前生效的会话 id(外部 conversationId ?? 懒创建的 internalConvUid)。
   *  「新任务」流不触发 onConvChanged,父层 conversationId 保持空串,
   *  调用详情抽屉等消费方需用本字段兜底,否则拿不到会话 id。 */
  convUid?: string;
  /** 会话切换后首次历史(vis_final)拉取中,供 UI 显示"会话加载中…" */
  convLoading: boolean;
  /** SSE usage_metric 事件推送的上下文消耗(实时) */
  usageMetrics: UsageMetrics | null;
  /** Composer Dock 协议:输入框上方固定区域 widget map(by id),由 SSE onDock/轮询 dock 帧合并而来 */
  dockWidgets: Record<string, DockWidget>;
  /** Agent 准备中:SSE 建立后 Agent 尚未产出内容(沙箱/MCP 加载期间),底部显示"正在启动 Agent"文案 */
  agentPreparing: boolean;
  /** 乐观上屏用户消息(发送/追问即插入视图,不等后端回显);纯文件消息可无文本仅有附件 */
  appendOptimisticUser: (text: string, attachments?: WorkspaceUserAttachment[]) => void;
  send: (payload: SceneAgentSendPayload, opts?: { forceNew?: boolean }) => void;
  /** 回到无会话态(新任务/退出任务):清掉懒创建的内部会话并断开其流/轮询 */
  resetConv: () => void;
  abort: () => void;
  clearSteps: () => void;
  clearWorkspaceView: () => void;
}

// Re-export so callers can import the payload/data types from the hook module.
export type { SceneAgentSendPayload } from './scene-agent-send-data';

const EMPTY_WORKSPACE_VIEW: WorkspaceView = { planning: null, execution: [], summary: null, deliverable_files: [], task_files: [], panel_view: 'execution' };

const MAX_RECENT_STEPS = 8;

/** 任务 → task_created 步骤(与 SSE 事件注入的卡片同 id,便于去重合并)。 */
export function taskToCreatedStep(
  task: any,
  playbooks?: { playbook_id: number; playbook_name: string }[],
): WorkspaceExecutionStep | null {
  if (!task || typeof task.id !== 'number') return null;
  const rawStatus = task.status || '';
  const status: WorkspaceExecutionStep['status'] =
    rawStatus === 'running' || rawStatus === 'pending_trigger' || rawStatus === 'awaiting_human'
      ? 'running'
      : rawStatus === 'delivered' || rawStatus === 'closed' || rawStatus === 'done'
      ? 'done'
      : 'failed';
  const playbookName = playbooks?.find((p) => p.playbook_id === task.playbook_id)?.playbook_name;
  return {
    id: `task-created-${task.id}`,
    type: 'task_created',
    title: task.title || `任务 #${task.id}`,
    status,
    ts: typeof task.gmt_created === 'string' ? task.gmt_created : null,
    task_id: task.id,
    task_title: typeof task.title === 'string' ? task.title : undefined,
    task_status: rawStatus,
    playbook_name: playbookName,
    triggered_by: typeof task.triggered_by === 'string' ? task.triggered_by : undefined,
  };
}

/** 把绑定到当前会话(conv_session_id === conversationId)的任务重注入执行记录。
 *
 * 任务卡片由 SSE task_created 事件在客户端注入,不落在后端 vis 数据里,
 * 刷新(vis_final 恢复)后卡片会消失。这里依据任务列表按会话维度重新注入,
 * 并按 task-created-{id} 去重/更新,保证刷新后卡片仍可见且状态正确。
 */
export function mergeTaskCards(
  prev: WorkspaceView,
  tasks: any[] | undefined,
  conversationId: string | undefined,
  playbooks?: { playbook_id: number; playbook_name: string }[],
): WorkspaceView {
  if (!conversationId || !Array.isArray(tasks)) return prev;
  const convTasks = tasks.filter((t) => t && t.conv_session_id === conversationId);
  if (!convTasks.length) return prev;
  const byId = new Map(prev.execution.map((s) => [s.id, s]));
  for (const task of convTasks) {
    const step = taskToCreatedStep(task, playbooks);
    if (!step) continue;
    const existing = byId.get(step.id);
    byId.set(step.id, existing
      ? { ...existing, ...step, ts: existing.ts ?? step.ts }
      : step);
  }
  const execution = Array.from(byId.values());
  return { ...prev, execution };
}

// Re-export the fence→object helper so callers can import it from the hook
// module. The implementation lives in a sibling file to keep it free of the
// hook's ESM-only `use-chat.ts` dependency (testable in plain Node).
export { parseSceneAgentWorkspaceString } from './parse-scene-agent-workspace-string';

export function useSceneAgentChat({
  conversationId,
  appCode,
  workspaceId,
  taskId,
  focusArtifactId,
  tasks,
  playbooks,
  onWorkspaceEvent,
  onConversationStart,
  enabled = true,
  onConvCreated,
}: UseSceneAgentChatOptions): UseSceneAgentChatResult {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastInput, setLastInput] = useState<SceneAgentSendPayload | null>(null);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>(EMPTY_WORKSPACE_VIEW);
  const [dockWidgets, setDockWidgets] = useState<Record<string, DockWidget>>({});
  const abortRef = useRef<AbortController | null>(null);
  // agent_preparing 占位状态:SSE 建立后 Agent 尚未产出内容时的独立 UI 状态,
  // 不注入 execution(避免被 parseWorkspaceView 排序/轮次切分影响),
  // Agent 产出首条内容时自动清除,由 RunningIndicator 渲染。
  const [agentPreparing, setAgentPreparing] = useState(false);
  // 流纪元:每次新 send / 会话切换时自增。SSE 回调据此判断是否仍属当前生效会话,
  // 避免切换会话后旧流迟到的消息、结束事件污染当前视图。
  const streamEpochRef = useRef(0);
  const { chat, usageMetrics, resetUsageMetrics } = useChat({ app_code: appCode || '' });
  // conversationId 内部态:外部未提供时(简洁模式延迟创建会话)由 ensureConvUid 填充,
  // 提供时跟随外部 prop;这样 send 不依赖外层 re-render。
  const [internalConvUid, setInternalConvUid] = useState<string | undefined>(undefined);
  // `||` 而非 `??`:conversationId 为空串(会话未写回)时回落 internalConvUid,
  // 避免空串劫持 effectiveConvUid 触发会话切换 effect 误 abort 进行中的 SSE 流。
  const effectiveConvUid = conversationId || internalConvUid;

  const ensureConvUid = useCallback(async (opts?: { forceNew?: boolean }): Promise<string | null> => {
    // forceNew(欢迎态/新任务首页发送):跳过一切已有会话,强制懒创建新会话。
    // internalConvUid 可能残留上一轮「新任务」流创建的会话(manualNew 流父层
    // conversationId 保持空串,清空 effect 因 prop 未变化而不会重跑),
    // 直接复用会把首页提问发进最后一个会话。
    if (!opts?.forceNew) {
      if (conversationId) return conversationId;
      if (internalConvUid) return internalConvUid;
    }
    if (onConvCreated) {
      const newUid = await onConvCreated('');
      if (newUid) {
        setInternalConvUid(newUid);
        return newUid;
      }
    }
    return null;
  }, [conversationId, internalConvUid, onConvCreated]);

  // 显式回到无会话态(新任务/退出任务):清掉懒创建的内部会话。
  // 生效会话随之 undefined → 会话切换 effect 自动中断旧流、清空视图;
  // 后端任务继续运行,重新打开该会话时由轮询恢复渲染。
  const resetConv = useCallback(() => {
    setInternalConvUid(undefined);
  }, []);

  // 外部 conversationId 回到 undefined(简洁模式返回欢迎态)时清掉内部会话:
  // 否则下次发送会复用上一轮 ensureConvUid 创建的旧会话,而不是新建。
  useEffect(() => {
    if (conversationId === undefined) setInternalConvUid(undefined);
  }, [conversationId]);

  // 会话/任务切换(effectiveConvUid 变化)时清空上一会话的视图与执行记录:
  // workspaceView 是会话级累积状态(步骤按 id 合并、旧条目保留),若不重置,
  // 新会话的 vis_final 会与旧会话的步骤混在一起 —— 任务列表里打开第二个任务时
  // 仍会展示第一个任务的内容。放在 mergeTaskCards 之前,保证先清空、
  // 再由任务卡片重注入与轮询重建新会话视图。
  // prev 为 undefined 时跳过:欢迎态首次发送新建会话(回到欢迎态时已清空过),
  // 再清一次会抹掉 send 刚上屏的乐观用户消息。
  const prevConvUidRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    const prev = prevConvUidRef.current;
    prevConvUidRef.current = effectiveConvUid;
    if (prev === undefined || prev === effectiveConvUid) return;
    // 诊断:此处 abort 会掐断进行中的 SSE(表现为对话直接被中断)。
    // 若复现「对话发不出去」,先看这行——prev→current 的翻转来源即根因。
    console.warn(`[scene-chat] conv switch, abort in-flight stream: ${prev} -> ${effectiveConvUid}`);
    // 会话切换:中断旧 SSE 连接(只断前端,后端 agent 继续后台运行,切回时由轮询恢复渲染),
    // 使旧流回调全部失效(streamEpochRef 自增),并解除 loading 对轮询的阻塞 ——
    // 新会话自动降级为轮询渲染,checkStatus 拉取 vis_final 重建历史视图。
    streamEpochRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
    setLastInput(null);
    setError(null);
    // 终止上一会话的断线恢复循环(若有),避免其迟到的 setError/步骤污染新会话
    recoverEpochRef.current += 1;
    recoveringRef.current = false;
    setRecovering(false);
    setWorkspaceView(EMPTY_WORKSPACE_VIEW);
    setSteps([]);
    setDockWidgets({});
    // 清空上一会话的上下文用量:useChat 的 usageMetrics 是 hook 级状态,
    // 仅由新的 SSE usage_metric 事件更新,不随会话切换自动重置,
    // 否则输入框环形图会残留上一会话的用量数据。
    resetUsageMetrics();
  }, [effectiveConvUid, resetUsageMetrics]);

  // 刷新/恢复视图后重注入任务卡片:任务卡片由 SSE task_created 事件注入,
  // 不落在后端 vis_final 数据中,刷新会消失。这里随任务列表/会话变化,
  // 把绑定到当前会话的任务按 task-created-{id} 去重/更新回执行记录,
  // 保证刷新后卡片仍可见且反映最新状态。
  useEffect(() => {
    if (!conversationId) return;
    setWorkspaceView((prev) => mergeTaskCards(prev, tasks, conversationId, playbooks));
  }, [tasks, conversationId, playbooks]);

  // 拦截 task_created workspace 事件:把任务卡片注入对话执行记录,
  // 用户可在对话中直接看到任务已创建并点击进入任务对话。
  // 仍调用原始 onWorkspaceEvent 让 shell 刷新任务列表。
  const handleWorkspaceEventInternal = useCallback(
    (event: WorkspaceEvent) => {
      if (event.type === 'task_created' && event.payload?.task_id) {
        const p = event.payload;
        const stepId = `task-created-${p.task_id}`;
        setWorkspaceView((prev) => {
          // 去重:同 task_id 的卡片已存在则不重复注入
          if (prev.execution.some((s) => s.id === stepId)) return prev;
          return {
            ...prev,
            execution: [
              ...prev.execution,
              {
                id: stepId,
                type: 'task_created' as const,
                title: p.title || `任务 #${p.task_id}`,
                status: 'running' as const,
                ts: new Date().toISOString(),
                task_id: p.task_id,
                task_title: p.title,
                task_status: p.status,
                playbook_name: p.playbook_name,
                triggered_by: p.triggered_by,
              },
            ],
          };
        });
      }
      // Agent 准备中事件:SSE 建立后立即推送。Agent 构建/沙箱创建/MCP 工具
      // 加载耗时期间无任何模型输出,用独立状态标记,由底部 RunningIndicator
      // 渲染"正在启动 Agent"文案;不注入 execution(避免排序/轮次切分影响)。
      // Agent 产出首条内容时由 routeObject 自动清除。
      if (event.type === 'agent_preparing') {
        console.log('[agent_preparing] received, setting agentPreparing=true');
        setAgentPreparing(true);
      }
      // 预加载技能事件:把本次对话预加载的 SKILL.md 以"已预加载技能"步骤注入
      // execution 区域(工具步骤区),点开由 StepPreview 渲染 SkillContentRenderer。
      if (event.type === 'loaded_skills' && Array.isArray(event.payload?.skills)) {
        const xmls = (event.payload.skills as string[]).filter(
          (x): x is string => typeof x === 'string' && x.length > 0,
        );
        if (xmls.length > 0) {
          setWorkspaceView((prev) => {
            const existingTitles = prev.execution
              .filter((s) => s.type === 'skill_loaded')
              .map((s) => s.title);
            const added = buildSkillLoadedExecutionSteps(xmls, existingTitles);
            if (added.length === 0) return prev;
            return {
              ...prev,
              execution: [...prev.execution, ...added],
            };
          });
        }
      }
      // 记忆注入事件:AGENTS.md / user.md 注入成功后渲染「上下文注入」卡片
      // (与 loaded_skills 同链路);刷新后由 chat_query injected_context 重注入。
      if (event.type === 'loaded_memories' && Array.isArray(event.payload?.blocks)) {
        setWorkspaceView((prev) => {
          const added = buildMemoryInjectionSteps(
            event.payload.blocks,
            prev.execution.map((s) => s.id),
          );
          if (added.length === 0) return prev;
          return { ...prev, execution: [...prev.execution, ...added] };
        });
      }
      // 技能发布事件:skill_publish 工具发布成功后渲染「技能已发布」卡片
      // (点击在右侧预览,详情跳技能资源库详情页);同 code 去重。
      if (event.type === 'skill_published' && event.payload?.skill_code) {
        const p = event.payload;
        const stepId = `skill-published-${p.skill_code}`;
        setWorkspaceView((prev) => {
          if (prev.execution.some((s) => s.id === stepId)) return prev;
          return {
            ...prev,
            execution: [
              ...prev.execution,
              {
                id: stepId,
                type: 'skill_published' as const,
                title: p.name || p.skill_code,
                status: 'done' as const,
                ts: new Date().toISOString(),
                skill_code: p.skill_code,
                output: p.description
                  ? `${p.description}(已发布到技能资源库)`
                  : '已发布到技能资源库',
              },
            ],
          };
        });
      }
      // 专家完成事件:专家任务(start_task 链路)delivered 时插入完成卡片。
      // 派单侧没有专用事件:协作调用走标准 SubAgent(工具调用渲染/子会话看板),
      // 任务化派单由 start_task 自身渲染任务卡片,这里只承接完成回执。
      if (event.type === 'expert_completed' && event.payload?.task_id) {
        const p = event.payload;
        setWorkspaceView((prev) => {
          // 如果没有派单卡片（页面刷新后），插入完成卡片
          const completedStepId = `expert-completed-${p.task_id}`;
          if (prev.execution.some((s) => s.id === completedStepId)) return prev;
          return {
            ...prev,
            execution: [
              ...prev.execution,
              {
                id: completedStepId,
                type: 'expert_completed' as const,
                title: p.title || `任务 #${p.task_id}`,
                status: p.status === 'delivered' ? 'done' as const : 'failed' as const,
                ts: new Date().toISOString(),
                task_id: p.task_id,
                task_title: p.title,
                expert_app_code: p.expert_app_code,
                expert_name: p.expert_name,
                expert_avatar: p.expert_avatar,
                output: p.status === 'delivered' ? '已完成交付' : '执行失败',
              },
            ],
          };
        });
      }
      onWorkspaceEvent?.(event);
    },
    [onWorkspaceEvent],
  );

  const appendStep = useCallback((step: AgentStep) => {
    setSteps((prev) => {
      const next = [...prev, step];
      if (next.length > MAX_RECENT_STEPS) next.shift();
      return next;
    });
  }, []);

  const clearSteps = useCallback(() => {
    setSteps([]);
    setWorkspaceView(EMPTY_WORKSPACE_VIEW);
    setDockWidgets({});
  }, []);

  const clearWorkspaceView = useCallback(() => {
    setWorkspaceView(EMPTY_WORKSPACE_VIEW);
  }, []);

  // SSE 结束(done/close/error)兜底:把仍停在 running 的工具/思考步骤翻成终态。
  // 后端工具结果帧可能因丢帧/WorkEntry 绑定失败未下发,前端若不兜底会永远转圈。
  // finalStatus:正常结束置 done,出错置 failed。answer/user 等其它类型不动。
  const settleRunningSteps = useCallback((finalStatus: 'done' | 'failed') => {
    const settles = (s: WorkspaceExecutionStep) =>
      (s.type === 'tool_call' || s.type === 'thinking') && s.status === 'running';
    setWorkspaceView((prev) => {
      if (!prev.execution.some(settles)) return prev;
      return {
        ...prev,
        execution: prev.execution.map((s) =>
          settles(s) ? { ...s, status: finalStatus } : s,
        ),
      };
    });
  }, []);

  // 乐观上屏:发送/追问即把用户消息插入视图,不等后端首帧。服务端回显同文本
  // user 步骤时由 dedupOptimisticUser 移除乐观步骤,避免重复。
  const appendOptimisticUser = useCallback(
    (text: string, attachments?: WorkspaceUserAttachment[]) => {
      const trimmed = text.trim();
      if (!trimmed && !(attachments && attachments.length)) return;
      const optimisticId = `user-optimistic-${Date.now()}`;
      setWorkspaceView((prev) =>
        parseWorkspaceView(
          {
            render_name: 'scene_agent_workspace',
            planning: null,
            execution: [
              {
                id: optimisticId,
                type: 'user',
                title: '我',
                status: 'done',
                output: trimmed,
                ...(attachments && attachments.length ? { attachments } : {}),
                ts: new Date().toISOString(),
              },
            ],
            summary: null,
          },
          prev,
        ),
      );
    },
    [],
  );

  // 历史恢复 + 运行中续传(关闭页面后重开可继续接收产出):
  // 由 useChatPolling 统一驱动,先拉 vis_final 全量渲染历史,再按 state 决定是否增量轮询。
  // - 首次 checkStatus 拉取 vis_final → onPoll 合并历史(先渲染历史所有)
  // - state===RUNNING → 自动 2.5s 轮询 → onPoll 持续增量合并新产出
  // - send 发起新对话 loading=true → enabled=false 停轮询,SSE 接管
  // - SSE 结束 loading=false → enabled true,conversationId effect 自动 checkStatus 恢复
  const handlePoll = useCallback(
    (res: ChatQueryResponse) => {
      // 过滤 conversationId 快速切换时滞后的旧会话响应,避免脏合并
      if (res.conv_id && effectiveConvUid && res.conv_id !== effectiveConvUid) return;
      // 轮询链路:回放 dock 帧,与 SSE onDock 共用同一份合并逻辑
      if (res.dock) {
        setDockWidgets((prev) => applyDockFrame(prev, res.dock!));
      }
      const parsed = parseSceneAgentWorkspaceString(res.vis_final);
      if (parsed && Array.isArray(parsed.execution)) {
        // 合并后去重乐观用户步骤(submitUserInput 追问路径仅靠轮询回显)
        setWorkspaceView((prev) => {
          const merged = parseWorkspaceView(parsed, prev);
          return { ...merged, execution: dedupOptimisticUser(merged.execution) };
        });
      }
      // 刷新重注入:记忆注入卡片不落在 vis_final 里,后端经 injected_context
      // 透出各轮注入标记,这里按稳定 id 去重合并,保证刷新后卡片仍可见。
      if (Array.isArray(res.injected_context) && res.injected_context.length > 0) {
        setWorkspaceView((prev) => {
          const added = buildMemoryInjectionSteps(
            res.injected_context!.flatMap((r) => r.blocks || []),
            prev.execution.map((s) => s.id),
          );
          if (added.length === 0) return prev;
          return { ...prev, execution: [...prev.execution, ...added] };
        });
      }
    },
    [effectiveConvUid],
  );

  const { state: convState, checkStatus, initialLoading: convLoading } = useChatPolling({
    conversationId: effectiveConvUid ?? null,
    enabled: enabled && !loading && !!effectiveConvUid,
    visRender: 'scene_agent_workspace',
    interval: 2500,
    onPoll: handlePoll,
  });

  // SSE 断线自愈:连接断开 ≠ agent 停止(服务重启/网络抖动都会断流)。
  // 经轮询链路探测会话真实状态(checkStatus 的 onPoll 顺带把 vis_final 合并回视图):
  // - 服务可达 → 清除错误;进行中状态由轮询接管(loading=false 已触发),继续合并产出
  // - 不可达(服务重启中)→ 5s 退避重试,超过上限才显示连接中断错误
  const RECOVER_MAX_ATTEMPTS = 12;
  const RECOVER_INTERVAL_MS = 5000;
  const [recovering, setRecovering] = useState(false);
  const recoveringRef = useRef(false);
  // 恢复纪元:新一轮 send 使旧恢复循环失效,避免其迟到的 setError 污染新会话
  const recoverEpochRef = useRef(0);
  const lastDropErrorRef = useRef<string | undefined>(undefined);

  const recover = useCallback(
    async (streamError?: string) => {
      if (!effectiveConvUid || recoveringRef.current) return;
      recoveringRef.current = true;
      setRecovering(true);
      const epoch = recoverEpochRef.current;
      try {
        for (let attempt = 0; attempt < RECOVER_MAX_ATTEMPTS; attempt++) {
          const result = await checkStatus();
          if (recoverEpochRef.current !== epoch) return; // 已发起新对话,放弃本次恢复
          if (result) {
            setError(null);
            return;
          }
          await new Promise((r) => setTimeout(r, RECOVER_INTERVAL_MS));
        }
        if (recoverEpochRef.current !== epoch) return;
        // 连续探测失败(服务长时间不可达):显示连接中断错误
        const content = streamError || '对话连接中断';
        setError(content);
        appendStep({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          type: 'unknown',
          title: 'Agent error',
          status: 'failed',
          timestamp: Date.now(),
          payload: { error: content },
        });
      } finally {
        if (recoverEpochRef.current === epoch) {
          recoveringRef.current = false;
          setRecovering(false);
        }
      }
    },
    [effectiveConvUid, checkStatus, appendStep],
  );

  const retryRecover = useCallback(() => {
    void recover(lastDropErrorRef.current);
  }, [recover]);

  const send = useCallback(
    async (payload: SceneAgentSendPayload, opts?: { forceNew?: boolean }) => {
      const { text, resources } = payload;
      const hasResources = Array.isArray(resources) && resources.length > 0;
      if (!text.trim() && !hasResources) return;
      // 简洁模式:无 conversationId 时先创建会话再发送;forceNew 强制新建(欢迎态首页)
      const uid = await ensureConvUid(opts);
      if (!uid) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      // 本轮新流纪元:使上一条流(若有)的迟到回调失效,也标记本流身份
      const epoch = ++streamEpochRef.current;
      setLoading(true);
      setLastInput(payload);
      setError(null);
      // 新对话使进行中的断线恢复失效
      recoverEpochRef.current += 1;
      recoveringRef.current = false;
      setRecovering(false);
      // 提交任务、开始对话 → 通知外层(如自动折叠中间内容区)
      onConversationStart?.();

      // 乐观上屏:不等 SSE 首帧,先把用户消息插入视图;服务端回显同文本 user 步骤
      // 时在 routeObject 里去重(服务端 output 会截断,用前缀匹配)。
      // 纯文件消息(无文本)也上屏,附件随气泡展示。
      appendOptimisticUser(text, hasResources ? resourcesToAttachments(resources!) : undefined);

      const data = buildSceneAgentSendData(payload, { workspaceId, taskId, focusArtifactId }, uid);

      chat({
        ctrl,
        data: {
          conv_uid: data.conv_uid,
          user_input: data.user_input,
          workspace_id: data.workspace_id,
          task_id: data.task_id,
          ...(data.model_name ? { model_name: data.model_name } : {}),
          ...(data.chat_in_params ? { chat_in_params: data.chat_in_params } : {}),
          team_mode: data.team_mode,
          app_config_code: data.app_config_code,
          agent_version: data.agent_version,
          ext_info: data.ext_info,
        },
        onMessage: (message: unknown) => {
          // 流身份守卫:切换会话/新开一轮后,旧流迟到消息不再污染当前视图
          if (streamEpochRef.current !== epoch) return;
          // Route a parsed vis object: step-list → appendStep, else
          // scene_agent_workspace → parseWorkspaceView.
          const routeObject = (obj: object) => {
            // Agent 产出首条内容(任何帧) → 清除 agent_preparing 占位状态
            console.log('[agent_preparing] routeObject called, clearing agentPreparing');
            setAgentPreparing(false);
            const step = parseAgentSteps(obj);
            if (step) {
              appendStep(step);
              return;
            }
            const mv = obj as Record<string, unknown>;
            if (mv.render_name === 'scene_agent_workspace' || Array.isArray(mv.execution)) {
              setWorkspaceView((prev) => {
                const merged = parseWorkspaceView(obj, prev);
                return { ...merged, execution: dedupOptimisticUser(merged.execution) };
              });
            }
          };

          if (message && typeof message === 'object') {
            routeObject(message as object);
            return;
          }
          // `use-chat.ts` forwards the vis fence as a STRING when
          // `ext_info.incremental` is unset (scene-agent case). Extract the
          // JSON body from the ```scene_agent_workspace fence (or bare JSON)
          // and feed it through the same routing path as objects.
          if (typeof message === 'string') {
            const parsed = parseSceneAgentWorkspaceString(message);
            if (parsed) routeObject(parsed);
          }
        },
        onDone: () => {
          if (streamEpochRef.current !== epoch) return;
          setLoading(false);
          setAgentPreparing(false);
          setLastInput(null);
          settleRunningSteps('done');
        },
        onClose: () => {
          if (streamEpochRef.current !== epoch) return;
          setLoading(false);
          setAgentPreparing(false);
          setLastInput(null);
          settleRunningSteps('done');
        },
        onError: (content: string) => {
          if (streamEpochRef.current !== epoch) return;
          // 服务端 [ERROR] 帧:Agent 真实报错,直接展示(连接断开走 onStreamDrop)
          setError(content || 'Agent error');
          setAgentPreparing(false);
          appendStep({
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
            type: 'unknown',
            title: 'Agent error',
            status: 'failed',
            timestamp: Date.now(),
            payload: { error: content || 'Agent error' },
          });
          setLoading(false);
          settleRunningSteps('failed');
        },
        onStreamDrop: (content: string) => {
          if (streamEpochRef.current !== epoch) return;
          setLoading(false);
          setAgentPreparing(false);
          setLastInput(null);
          lastDropErrorRef.current = content;
          void recover(content);
        },
        onWorkspaceEvent: (event: WorkspaceEvent) => {
          if (streamEpochRef.current !== epoch) return;
          handleWorkspaceEventInternal(event);
        },
        onDock: (frame: DockFrame) => {
          if (streamEpochRef.current !== epoch) return;
          setDockWidgets((prev) => applyDockFrame(prev, frame));
        },
      });
    },
    [workspaceId, taskId, focusArtifactId, chat, appendStep, appendOptimisticUser, handleWorkspaceEventInternal, onConversationStart, recover, ensureConvUid, settleRunningSteps],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
    setAgentPreparing(false);
    // 真正终止对话:取消后端 agent task。SSE 断开(abort)本身不终止 agent,
    // 主动停止需调 stop_chat 接口(状态置 INTERRUPTED)。
    const uid = effectiveConvUid;
    if (uid) {
      stopChat({ conv_session_id: uid }).catch(() => {
        /* 终止失败不阻塞 UI,后端 task 可能已结束 */
      });
    }
  }, [effectiveConvUid]);

  return { steps, workspaceView, loading, error, lastInput, modelName: lastInput?.model, recovering, retryRecover, convState, convUid: effectiveConvUid, convLoading: !!effectiveConvUid && convLoading, usageMetrics, dockWidgets, agentPreparing, send, resetConv, abort, appendOptimisticUser, clearSteps, clearWorkspaceView };
}