import { ChatContentContext, ChatContext } from '@/contexts';
import i18n from '@/app/i18n';
import { getUserId } from '@/utils';
import { HEADER_USER_ID_KEY } from '@/utils/constants/index';
import { EventStreamContentType, fetchEventSource } from '@microsoft/fetch-event-source';
import { App } from 'antd';
import { useCallback, useState } from 'react';
import { VisParser } from '@/utils/parse-vis';
import type { UsageMetrics } from '@/types/context-metrics';
import type { DockFrame } from '@/components/chat/dock/dock-types';

export type WorkspaceEventType =
  | 'task_created'
  | 'context_loaded'
  | 'intervention_triggered'
  | 'artifact_produced'
  | 'delivery_sent'
  | 'asset_referenced'
  | 'inbox_created'
  | 'inbox_resolved'
  | 'loaded_skills';

export interface WorkspaceEvent {
  type: WorkspaceEventType;
  payload: Record<string, any>;
}

type Props = {
  queryAgentURL?: string;
  app_code?: string;
};

type ChatParams = {
  chatId?: string;
  ctrl?: AbortController;
  data?: any;
  query?: Record<string, string>;
  onMessage: (message: string) => void;
  onClose?: () => void;
  onDone?: () => void;
  onError?: (content: string, error?: Error) => void;
  /** 流传输层断开(网络错误/服务重启)。与 onError([ERROR] 帧,Agent 真实报错)区分:
   *  传入时连接断开走本回调(调用方可做断线自愈),不传则回退到 onError。 */
  onStreamDrop?: (content: string, error?: Error) => void;
  onWorkspaceEvent?: (event: WorkspaceEvent) => void;
  /** Composer Dock 协议：输入框上方固定区域渲染数据帧。 */
  onDock?: (frame: DockFrame) => void;
};

export function parseChunkData(
  preText: string,
  preMidMsg: { nodeId: string; text: string },
  data: any,
  visParser: VisParser,
) {

  const answerText = preText || '';
  const midMsgObject = preMidMsg || {
    nodeId: '',
    text: '',
  }; 
  // 中间态消息, 如果下次的nodeId相同，追加；不同，则覆盖
  const answer: string = data.vis;
  midMsgObject.text = visParser.update(answer);
  return { answerText, midMsgObject };
}

const useChat = ({ queryAgentURL = '/api/v1/chat/completions', app_code }: Props) => {
  const { message } = App.useApp();
  const [ctrl, setCtrl] = useState<AbortController>({} as AbortController);
  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics | null>(null);

  const chatV1 = useCallback(
    async ({ data, onMessage, onClose, onDone, onError, onStreamDrop, onWorkspaceEvent, onDock, ctrl }: ChatParams) => {
      ctrl && setCtrl(ctrl);
      if (!data?.user_input && !data?.doc_id) {
        message.warning(i18n.t('no_context_tip'));
        return;
      }

      const params = { ...data, app_code };
      const isIncremental = data?.ext_info?.incremental;
      const visParser = new VisParser();
      // 是否已收到流末尾 [DONE]:用于区分"正常结束"与"服务端流提前中断"。
      // onclose 对两类都触发,但只有收到 [DONE] 才是正常收尾;否则应视为异常中断。
      let streamDone = false;

      // rAF 合帧:高频流式 chunk 先做增量合并(O(k)),markdown 全量序列化
      // 与 React 更新每帧最多一次,避免 token 级 chunk 造成 O(N²) 序列化与渲染风暴
      let rafId: ReturnType<typeof requestAnimationFrame> | null = null;
      let visDirty = false;
      const flushVis = () => {
        rafId = null;
        if (!visDirty) return;
        visDirty = false;
        onMessage?.(visParser.flush());
      };
      const scheduleVisFlush = () => {
        visDirty = true;
        if (rafId !== null) return;
        if (typeof requestAnimationFrame !== 'undefined') {
          rafId = requestAnimationFrame(flushVis);
        } else {
          flushVis();
        }
      };
      const cancelVisFlush = () => {
        if (rafId !== null && typeof cancelAnimationFrame !== 'undefined') {
          cancelAnimationFrame(rafId);
        }
        rafId = null;
      };

      try {
        await fetchEventSource(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ''}${queryAgentURL}`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            [HEADER_USER_ID_KEY]: getUserId() ?? '',
          },
          body: JSON.stringify(params),
          signal: ctrl ? ctrl.signal : null,
          openWhenHidden: true,
          async onopen(response) {
            if (response.ok && response.headers.get('content-type') === EventStreamContentType) return;
            if (response.headers.get('content-type') === 'application/json') {
              response.json().then(data => { onMessage?.(data); onDone?.(); ctrl && ctrl.abort(); });
            }
          },
          onclose() {
            flushVis();
            ctrl && ctrl.abort();
            // 只有收到过 [DONE] 才视为正常结束;否则说明服务端在流中途提前关闭
            // (如 agent 卡在工具/MCP 调用、异常等),此时若静默 onClose,页面会停留在
            // 第一个字且无任何提示、也不会重连——正是"追问后直接结束且无报错"的表现。
            // 走断线自愈/错误提示,让用户能看到并重试。
            if (!streamDone) {
              const content = '对话连接中断';
              if (onStreamDrop) onStreamDrop(content);
              else onError?.(content);
            } else {
              onClose?.();
            }
          },
          onerror(err) {
            flushVis();
            console.error('err', err);
            throw err instanceof Error ? err : new Error(String(err));
          },
          onmessage: event => {
            let message = event.data;
            try {
              const parsedData = JSON.parse(message);

              // Check if it's a metadata or interrupt message first
              if (parsedData?.vis && typeof parsedData.vis === 'object') {
                const vis = parsedData.vis;
                if (vis.type === 'metadata' || vis.type === 'interrupt') {
                  onMessage?.(vis);
                  return;
                } else if (vis.type === 'error') {
                  onError?.(vis.content || '对话发生错误');
                  return;
                } else if (vis.type === 'usage_metric') {
                  setUsageMetrics(vis.payload);
                  return;
                } else if (
                  vis.type === 'task_created' ||
                  vis.type === 'context_loaded' ||
                  vis.type === 'intervention_triggered' ||
                  vis.type === 'artifact_produced' ||
                  vis.type === 'delivery_sent' ||
                  vis.type === 'asset_referenced' ||
                  vis.type === 'inbox_created' ||
                  vis.type === 'inbox_resolved' ||
                  vis.type === 'loaded_skills'
                ) {
                  onWorkspaceEvent?.(vis as WorkspaceEvent);
                  return;
                }
              }

              // Composer Dock 协议：输入框上方固定区域数据帧，原样回调由上层合并渲染
              if (parsedData?.dock) {
                onDock?.(parsedData.dock);
                return;
              }

              if (!isIncremental) {
                message = parsedData.vis;
              } else {
                // 增量模式:只合并不序列化,序列化与渲染交给 rAF 合帧
                visParser.update(parsedData.vis, false);
                scheduleVisFlush();
                return;
              }
            } catch { message = message.replace(/\\n/g, '\n'); }
            if (typeof message === 'string') {
              if (message === '[DONE]') { streamDone = true; flushVis(); onDone?.(); }
              else if (message?.startsWith('[ERROR]')) { flushVis(); onError?.(message?.replace('[ERROR]', '')); }
              else onMessage?.(message);
            } else if (typeof message === 'object' && message !== null) {
              // Handle other object messages
              onMessage?.(message);
            }
          },
        });
      } catch (err) {
        ctrl && ctrl.abort();
        const error = err as Error;
        if (error?.name === 'AbortError') {
          // 用户主动中断(或流正常关闭后的 abort),不算错误,保留已产出内容
          onClose?.();
        } else {
          const content = `对话连接中断: ${error?.message || '未知网络错误'}`;
          if (onStreamDrop) onStreamDrop(content, error);
          else onError?.(content, error);
        }
      }
    },
    [queryAgentURL, app_code],
  );

  const chat = useCallback(
    async (params: ChatParams) => {
      return chatV1(params);
    },
    [chatV1],
  );

  const resetUsageMetrics = useCallback(() => {
    setUsageMetrics(null);
  }, []);

  return { chat, ctrl, usageMetrics, resetUsageMetrics };
};

export default useChat;
