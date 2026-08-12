import { useState, useEffect, useRef, useCallback } from 'react';
import { queryChatStatus, ChatQueryResponse } from '@/client/api/chat';

export type ConversationState = 'RUNNING' | 'COMPLETE' | 'FAILED' | 'WAITING' | 'UNKNOWN';

// 会话是否处于"进行中"（RUNNING 或 WAITING）：
// WAITING 表示正在等后台子任务/异步任务恢复，完成后主会话会自动 resume。
// 仅终态（COMPLETE/FAILED）才停止轮询并触发 onComplete，从而刷新历史看到恢复内容。
const isInProgress = (s: string | undefined) => s === 'RUNNING' || s === 'WAITING';

interface UseChatPollingOptions {
  convId: string | null;
  enabled?: boolean;
  interval?: number;
  /** 强制历史/轮询用指定 converter 组装 vis_final(如通用页传 vis_manus) */
  visRender?: string;
  onComplete?: (response: ChatQueryResponse) => void;
  onError?: (error: Error) => void;
  /** 每次成功 queryChatStatus(含首次历史拉取与后续轮询)回调,供调用方增量合并 vis_final */
  onPoll?: (response: ChatQueryResponse) => void;
}

interface UseChatPollingReturn {
  state: ConversationState;
  isPolling: boolean;
  data: ChatQueryResponse | null;
  startPolling: () => void;
  stopPolling: () => void;
  checkStatus: () => Promise<ChatQueryResponse | null>;
}

export function useChatPolling({
  convId,
  enabled = true,
  interval = 2000,
  visRender,
  onComplete,
  onError,
  onPoll,
}: UseChatPollingOptions): UseChatPollingReturn {
  const [state, setState] = useState<ConversationState>('UNKNOWN');
  const [isPolling, setIsPolling] = useState(false);
  const [data, setData] = useState<ChatQueryResponse | null>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);
  // 回调用 ref 承载,避免进入 checkStatus/startPolling 依赖导致频繁重建/重复请求。
  // 调用方(如 chat-session)传内联函数,每次渲染新身份 -> startPolling 重建 ->
  // convId effect 重跑 -> 每帧发起一次 /chat/query,页面疯狂刷新无法渲染。
  const onPollRef = useRef(onPoll);
  onPollRef.current = onPoll;
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const checkStatus = useCallback(async (): Promise<ChatQueryResponse | null> => {
    if (!convId) return null;
    
    try {
      const response = await queryChatStatus(convId, visRender);
      const result = response.data?.data;
      if (!result) {
        // 后端返回 success:false / 无 data(如会话尚未生成),不更新状态,避免读 undefined 崩溃
        return null;
      }

      if (mountedRef.current) {
        setData(prev => {
          if (prev?.vis_final === result.vis_final && prev?.state === result.state) {
            return prev;
          }
          return result;
        });
        setState(result.state as ConversationState);
        // 每次成功拉取(首次历史 + 后续轮询)都通知调用方增量合并 vis_final;
        // parseWorkspaceView 按 id 幂等合并,重复推送相同内容无害
        onPollRef.current?.(result);
      }
      
      return result;
    } catch (error) {
      if (mountedRef.current) {
        setState('UNKNOWN');
      }
      onErrorRef.current?.(error as Error);
      return null;
    }
  }, [convId, visRender]);

  const startPolling = useCallback(() => {
    if (!convId || !enabled) return;

    setIsPolling(true);

    // convId effect 已确认会话处于 inProgress(RUNNING/WAITING)才调本方法,这里
    // 不再重复 checkStatus:第二次查询会与后端 save_conversation(可能瞬时把状态
    // 置 COMPLETE)/resume 竞争,误读终态而放弃轮询,导致异步任务 resume 后的输出
    // 页面收不到(用户只看到"已提交后台执行"就结束,看不到子 Agent 回复/后续)。
    // setInterval 内部 checkStatus 负责在真正到达终态时停止,且每次都触发 onPoll
    // 合并 vis_final(含 resume 内容),终态那次也会刷新视图。
    intervalRef.current = setInterval(async () => {
      const status = await checkStatus();

      if (status && !isInProgress(status.state)) {
        // 对话完成或失败，停止轮询
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setIsPolling(false);
        onCompleteRef.current?.(status);
      }
    }, interval);
  }, [convId, enabled, checkStatus, interval]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    mountedRef.current = true;
    
    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [stopPolling]);

  // enabled 变为 false 时主动停止轮询(如 SSE 接管)。
  // 恢复由下方 convId effect 负责:其依赖含 enabled,false→true 时会自动 checkStatus + 按需 startPolling。
  useEffect(() => {
    if (!enabled && isPolling) {
      stopPolling();
    }
  }, [enabled, isPolling, stopPolling]);

  // convId 变化时，检查状态
  useEffect(() => {
    if (convId && enabled) {
      checkStatus().then(result => {
        if (result && isInProgress(result.state)) {
          startPolling();
        }
      });
    }
    
    return () => {
      stopPolling();
    };
  }, [convId, enabled, checkStatus, startPolling, stopPolling]);

  return {
    state,
    isPolling,
    data,
    startPolling,
    stopPolling,
    checkStatus,
  };
}

export default useChatPolling;