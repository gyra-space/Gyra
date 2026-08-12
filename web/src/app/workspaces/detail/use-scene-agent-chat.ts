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
}

interface UseSceneAgentChatResult {
  steps: AgentStep[];
  workspaceView: WorkspaceView;
  loading: boolean;
  error: string | null;
  lastInput: SceneAgentSendPayload | null;
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
}: UseSceneAgentChatOptions): UseSceneAgentChatResult {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastInput, setLastInput] = useState<SceneAgentSendPayload | null>(null);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>(EMPTY_WORKSPACE_VIEW);
  const [dockWidgets, setDockWidgets] = useState<Record<string, DockWidget>>({});
  const abortRef = useRef<AbortController | null>(null);
  const { chat, usageMetrics } = useChat({ app_code: appCode || '' });

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
      if (res.conv_id && convUid && res.conv_id !== convUid) return;
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
    [convUid],
  );

  const { state: convState } = useChatPolling({
    convId: convUid ?? null,
    enabled: !loading,
    visRender: 'scene_agent_workspace',
    interval: 2500,
    onPoll: handlePoll,
  });

  const send = useCallback(
    (payload: SceneAgentSendPayload) => {
      const { text } = payload;
      if (!convUid || !text.trim()) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      setLastInput(payload);
      setError(null);
      // 提交任务、开始对话 → 通知外层(如自动折叠中间内容区)
      onConversationStart?.();

      // 乐观上屏:不等 SSE 首帧,先把用户消息插入视图;服务端回显同文本 user 步骤
      // 时在 routeObject 里去重(服务端 output 会截断,用前缀匹配)
      appendOptimisticUser(text);

      const data = buildSceneAgentSendData(payload, { workspaceId, taskId, focusArtifactId }, convUid);

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
        },
        onClose: () => {
          setLoading(false);
          setLastInput(null);
        },
        onError: (content: string) => {
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
        },
        onWorkspaceEvent: handleWorkspaceEventInternal,
        onDock: (frame) => setDockWidgets((prev) => applyDockFrame(prev, frame)),
      });
    },
    [convUid, workspaceId, taskId, focusArtifactId, chat, appendStep, appendOptimisticUser, handleWorkspaceEventInternal, onConversationStart],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
    // 真正终止对话:取消后端 agent task。SSE 断开(abort)本身不终止 agent,
    // 主动停止需调 stop_chat 接口(状态置 INTERRUPTED)。
    if (convUid) {
      stopChat({ conv_session_id: convUid }).catch(() => {
        /* 终止失败不阻塞 UI,后端 task 可能已结束 */
      });
    }
  }, [convUid]);

  return { steps, workspaceView, loading, error, lastInput, convState, usageMetrics, dockWidgets, send, abort, appendOptimisticUser, clearSteps, clearWorkspaceView };
}