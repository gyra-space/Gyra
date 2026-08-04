'use client';

import { useCallback, useRef, useState } from 'react';
import useChat from '@/hooks/use-chat';
import type { WorkspaceEvent } from '@/hooks/use-chat';
import { useChatPolling, type ConversationState } from '@/hooks/use-chat-polling';
import type { ChatQueryResponse } from '@/client/api/chat';
import type { AgentStep } from './agent-types';
import { parseAgentSteps } from './parse-agent-steps';
import { parseWorkspaceView } from './parse-workspace-view';
import {
  buildSceneAgentSendData,
  type SceneAgentSendPayload,
} from './scene-agent-send-data';
import type { WorkspaceView } from './agent-workspace-types';
import { parseSceneAgentWorkspaceString } from './parse-scene-agent-workspace-string';

interface UseSceneAgentChatOptions {
  convUid?: string;
  appCode?: string;
  workspaceId?: number | string;
  taskId?: number | string;
  focusArtifactId?: number | string;
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
  send: (payload: SceneAgentSendPayload) => void;
  abort: () => void;
  clearSteps: () => void;
  clearWorkspaceView: () => void;
}

// Re-export so callers can import the payload/data types from the hook module.
export type { SceneAgentSendPayload } from './scene-agent-send-data';

const EMPTY_WORKSPACE_VIEW: WorkspaceView = { planning: null, execution: [], summary: null, deliverable_files: [], task_files: [], panel_view: 'execution' };

const MAX_RECENT_STEPS = 8;

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
  onWorkspaceEvent,
  onConversationStart,
}: UseSceneAgentChatOptions): UseSceneAgentChatResult {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastInput, setLastInput] = useState<SceneAgentSendPayload | null>(null);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>(EMPTY_WORKSPACE_VIEW);
  const abortRef = useRef<AbortController | null>(null);
  // 乐观插入的用户消息:发送即上屏,服务端回显同文本 user 步骤后移除,避免重复
  const optimisticUserRef = useRef<{ id: string; text: string } | null>(null);
  const { chat } = useChat({ app_code: appCode || '' });

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
    optimisticUserRef.current = null;
  }, []);

  const clearWorkspaceView = useCallback(() => {
    setWorkspaceView(EMPTY_WORKSPACE_VIEW);
    optimisticUserRef.current = null;
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
      const parsed = parseSceneAgentWorkspaceString(res.vis_final);
      if (parsed && Array.isArray(parsed.execution)) {
        setWorkspaceView((prev) => parseWorkspaceView(parsed, prev));
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

      // 乐观上屏:不等 SSE 首帧,先把用户消息插入视图;服务端回显同文本
      // user 步骤时在 routeObject 里去重(服务端 output 会截断,用前缀匹配)
      const optimisticId = `user-optimistic-${Date.now()}`;
      optimisticUserRef.current = { id: optimisticId, text: text.trim() };
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
                output: text.trim(),
                ts: new Date().toISOString(),
              },
            ],
            summary: null,
          },
          prev,
        ),
      );

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
                // 服务端回显了同文本 user 步骤 → 先移除乐观步骤再合并,避免重复
                const opt = optimisticUserRef.current;
                let base = prev;
                if (opt && Array.isArray(mv.execution)) {
                  const echoed = (mv.execution as any[]).some(
                    (e) =>
                      e?.type === 'user' &&
                      typeof e?.output === 'string' &&
                      e.output.length > 0 &&
                      (opt.text === e.output || opt.text.startsWith(e.output)),
                  );
                  if (echoed) {
                    base = { ...prev, execution: prev.execution.filter((s) => s.id !== opt.id) };
                    optimisticUserRef.current = null;
                  }
                }
                return parseWorkspaceView(obj, base);
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
      });
    },
    [convUid, workspaceId, taskId, focusArtifactId, chat, appendStep, handleWorkspaceEventInternal, onConversationStart],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  return { steps, workspaceView, loading, error, lastInput, convState, send, abort, clearSteps, clearWorkspaceView };
}