'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import useChat from '@/hooks/use-chat';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import type { UsageMetrics } from '@/types/context-metrics';
import { useChatPolling, type ConversationState } from '@/hooks/use-chat-polling';
import { stopChat, type ChatQueryResponse } from '@/client/api/chat';
import { applyDockFrame } from '@/components/chat/dock/apply-dock-frame';
import type { DockWidget } from '@/components/chat/dock/dock-types';
import type { AgentStep } from './agent-types';
import { parseAgentSteps } from './parse-agent-steps';
import { parseWorkspaceView } from './parse-workspace-view';
import { dedupOptimisticUser } from './dedup-optimistic-user';
import {
  buildSceneAgentSendData,
  type SceneAgentSendPayload,
} from './scene-agent-send-data';
import type { WorkspaceExecutionStep, WorkspaceView } from './agent-workspace-types';
import { parseSceneAgentWorkspaceString } from './parse-scene-agent-workspace-string';

interface UseSceneAgentChatOptions {
  convUid?: string;
  appCode?: string;
  workspaceId?: number | string;
  taskId?: number | string;
  focusArtifactId?: number | string;
  /** 工作空间全量任务列表:用于恢复视图时重注入绑定到当前会话的任务卡片 */
  tasks?: any[];
  /** 剧本 id→名称映射:任务卡片展示剧本名 */
  playbooks?: { playbook_id: number; playbook_name: string }[];
  onWorkspaceEvent?: (event: WorkspaceEvent) => void;
  /** 用户在 Agent 空间提交任务、开始一轮对话时触发(用于折叠中间内容区) */
  onConversationStart?: () => void;
  /** 是否启用轮询/连接:简洁模式与运维模式共用同一会话时,只让一个实例接管 */
  enabled?: boolean;
  /** 会话创建回调:convUid 为空时由外层在首次发送前创建并注入 */
  onConvCreated?: (convUid: string) => Promise<string | null>;
}

interface UseSceneAgentChatResult {
  steps: AgentStep[];
  workspaceView: WorkspaceView;
  loading: boolean;
  error: string | null;
  lastInput: SceneAgentSendPayload | null;
  /** SSE 断线自愈探测中(服务重启/网络抖动后的恢复窗口) */
  recovering: boolean;
  /** 手动重试断线恢复(错误横幅"重试连接"入口) */
  retryRecover: () => void;
  /** 后端会话运行状态:RUNNING 表示后台仍在执行(可关闭页面后恢复) */
  convState: ConversationState;
  /** SSE usage_metric 事件推送的上下文消耗(实时) */
  usageMetrics: UsageMetrics | null;
  /** Composer Dock 协议:输入框上方固定区域 widget map(by id),由 SSE onDock/轮询 dock 帧合并而来 */
  dockWidgets: Record<string, DockWidget>;
  /** 乐观上屏用户消息(发送/追问即插入视图,不等后端回显) */
  appendOptimisticUser: (text: string) => void;
  send: (payload: SceneAgentSendPayload) => void;
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

/** 把绑定到当前会话(conv_session_id === convUid)的任务重注入执行记录。
 *
 * 任务卡片由 SSE task_created 事件在客户端注入,不落在后端 vis 数据里,
 * 刷新(vis_final 恢复)后卡片会消失。这里依据任务列表按会话维度重新注入,
 * 并按 task-created-{id} 去重/更新,保证刷新后卡片仍可见且状态正确。
 */
export function mergeTaskCards(
  prev: WorkspaceView,
  tasks: any[] | undefined,
  convUid: string | undefined,
  playbooks?: { playbook_id: number; playbook_name: string }[],
): WorkspaceView {
  if (!convUid || !Array.isArray(tasks)) return prev;
  const convTasks = tasks.filter((t) => t && t.conv_session_id === convUid);
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
  convUid,
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
  const { chat, usageMetrics, resetUsageMetrics } = useChat({ app_code: appCode || '' });
  // convUid 内部态:外部未提供时(简洁模式延迟创建会话)由 ensureConvUid 填充,
  // 提供时跟随外部 prop;这样 send 不依赖外层 re-render。
  const [internalConvUid, setInternalConvUid] = useState<string | undefined>(undefined);
  const effectiveConvUid = convUid ?? internalConvUid;

  const ensureConvUid = useCallback(async (): Promise<string | null> => {
    if (convUid) return convUid;
    if (internalConvUid) return internalConvUid;
    if (onConvCreated) {
      const newUid = await onConvCreated('');
      if (newUid) {
        setInternalConvUid(newUid);
        return newUid;
      }
    }
    return null;
  }, [convUid, internalConvUid, onConvCreated]);

  // 外部 convUid 回到 undefined(简洁模式返回欢迎态)时清掉内部会话:
  // 否则下次发送会复用上一轮 ensureConvUid 创建的旧会话,而不是新建。
  useEffect(() => {
    if (convUid === undefined) setInternalConvUid(undefined);
  }, [convUid]);

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
    if (!convUid) return;
    setWorkspaceView((prev) => mergeTaskCards(prev, tasks, convUid, playbooks));
  }, [tasks, convUid, playbooks]);

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
  const appendOptimisticUser = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
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
              ts: new Date().toISOString(),
            },
          ],
          summary: null,
        },
        prev,
      ),
    );
  }, []);

  // 历史恢复 + 运行中续传(关闭页面后重开可继续接收产出):
  // 由 useChatPolling 统一驱动,先拉 vis_final 全量渲染历史,再按 state 决定是否增量轮询。
  // - 首次 checkStatus 拉取 vis_final → onPoll 合并历史(先渲染历史所有)
  // - state===RUNNING → 自动 2.5s 轮询 → onPoll 持续增量合并新产出
  // - send 发起新对话 loading=true → enabled=false 停轮询,SSE 接管
  // - SSE 结束 loading=false → enabled true,convId effect 自动 checkStatus 恢复
  const handlePoll = useCallback(
    (res: ChatQueryResponse) => {
      // 过滤 convUid 快速切换时滞后的旧会话响应,避免脏合并
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
    },
    [effectiveConvUid],
  );

  const { state: convState, checkStatus } = useChatPolling({
    convId: effectiveConvUid ?? null,
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
    async (payload: SceneAgentSendPayload) => {
      const { text } = payload;
      if (!text.trim()) return;
      // 简洁模式:无 convUid 时先创建会话再发送
      const uid = await ensureConvUid();
      if (!uid) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
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
      // 时在 routeObject 里去重(服务端 output 会截断,用前缀匹配)
      appendOptimisticUser(text);

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
          // Route a parsed vis object: step-list → appendStep, else
          // scene_agent_workspace → parseWorkspaceView.
          const routeObject = (obj: object) => {
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
          setLoading(false);
          setLastInput(null);
          settleRunningSteps('done');
        },
        onClose: () => {
          setLoading(false);
          setLastInput(null);
          settleRunningSteps('done');
        },
        onError: (content: string) => {
          // 服务端 [ERROR] 帧:Agent 真实报错,直接展示(连接断开走 onStreamDrop)
          setError(content || 'Agent error');
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
          setLoading(false);
          setLastInput(null);
          lastDropErrorRef.current = content;
          void recover(content);
        },
        onWorkspaceEvent: handleWorkspaceEventInternal,
        onDock: (frame) => setDockWidgets((prev) => applyDockFrame(prev, frame)),
      });
    },
    [workspaceId, taskId, focusArtifactId, chat, appendStep, appendOptimisticUser, handleWorkspaceEventInternal, onConversationStart, recover, ensureConvUid, settleRunningSteps],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
    // 真正终止对话:取消后端 agent task。SSE 断开(abort)本身不终止 agent,
    // 主动停止需调 stop_chat 接口(状态置 INTERRUPTED)。
    const uid = effectiveConvUid;
    if (uid) {
      stopChat({ conv_session_id: uid }).catch(() => {
        /* 终止失败不阻塞 UI,后端 task 可能已结束 */
      });
    }
  }, [effectiveConvUid]);

  return { steps, workspaceView, loading, error, lastInput, recovering, retryRecover, convState, usageMetrics, dockWidgets, send, abort, appendOptimisticUser, clearSteps, clearWorkspaceView };
}