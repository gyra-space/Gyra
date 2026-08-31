import { useState, useCallback, useRef, useEffect } from 'react';
import { App } from 'antd';

export interface UserInputItem {
  content: string;
  input_type: string;
  metadata?: Record<string, any>;
}

export interface UserInputQueueState {
  hasPendingInput: boolean;
  queueLength: number;
  executionNode?: string;
  isLocal?: boolean;
}

export interface ExecutionNodeInfo {
  session_id: string;
  execution_node: string | null;
  is_local: boolean;
  current_node: string;
}

export function useUserInput(
  sessionId: string | undefined,
  options?: { onConsumed?: (items: UserInputItem[]) => void },
) {
  const { message } = App.useApp();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [queueState, setQueueState] = useState<UserInputQueueState>({
    hasPendingInput: false,
    queueLength: 0,
  });
  const pendingInputsRef = useRef<UserInputItem[]>([]);
  // 队列长度镜像:setQueueState 异步,getQueueStatus 需要同步对比上一次长度来检测消费
  const queueLengthRef = useRef(0);
  // 消费回调:队列轮询发现长度下降(后端 FIFO 消费)时,把被消费项交给调用方
  // 上屏为独立用户气泡 —— 运行中补充输入「先入队,agent 消费后才展示」。
  const onConsumedRef = useRef(options?.onConsumed);
  onConsumedRef.current = options?.onConsumed;
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  // 是否处于「外部要求轮询中」:与 interval 的实际存在解耦,供页面隐藏/恢复判断是否续跑。
  const pollActiveRef = useRef(false);
  const pollIntervalValueRef = useRef(2000);

  const getBaseUrl = useCallback(() => {
    return process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
  }, []);

  const submitUserInput = useCallback(async (
    content: string,
    inputType: string = 'text',
    metadata?: Record<string, any>
  ): Promise<boolean> => {
    if (!content.trim()) {
      return false;
    }

    if (!sessionId) {
      message.warning('Session not ready');
      return false;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(
        `${getBaseUrl()}/api/v2/input/submit`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            content,
            input_type: inputType,
            metadata,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        queueLengthRef.current = result.queue_length;
        setQueueState(prev => ({
          ...prev,
          hasPendingInput: true,
          queueLength: result.queue_length,
          executionNode: result.execution_node,
        }));

        pendingInputsRef.current.push({ content, input_type: inputType, metadata });

        return true;
      } else {
        message.warning(result.message || 'No active execution');
        return false;
      }
    } catch (error) {
      console.error('Failed to submit user input:', error);
      message.error('Failed to submit input');
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [sessionId, getBaseUrl]);

  const getQueueStatus = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${getBaseUrl()}/api/v2/input/queue/${sessionId}`
      );

      if (response.ok) {
        const result = await response.json();
        const nextLength: number = result.pending_count || (result.has_pending_input ? 1 : 0);
        // 消费检测:后端按 FIFO 清空式消费,队列长度下降的部分即被 agent 取走的消息。
        // 本地 pendingInputsRef 与后端入队顺序一致,取头部 prevLength - nextLength 条
        // 视为已消费,交给 onConsumed 上屏(「先入队,消费后才展示到消息列表」)。
        const prevLength = queueLengthRef.current;
        const consumedCount = prevLength - nextLength;
        let consumed: UserInputItem[] = [];
        if (consumedCount > 0 && pendingInputsRef.current.length > 0) {
          consumed = pendingInputsRef.current.splice(0, consumedCount);
        } else if (nextLength === 0 && pendingInputsRef.current.length > 0) {
          // 长度未变但队列已空(如并发清空/消费瞬时竞态):本地待展示项全部视为已消费
          consumed = pendingInputsRef.current.splice(0);
        }
        queueLengthRef.current = nextLength;
        setQueueState({
          hasPendingInput: result.has_pending_input,
          // 「排队 N 条」仅统计仍在排队的消息:本地提交列表末尾 queueLength 条,
          // 前面的已被消费(经 onConsumed 上屏),不再计入排队数。
          queueLength: Math.min(nextLength, pendingInputsRef.current.length),
          executionNode: result.execution_node,
          isLocal: result.is_local,
        });
        if (consumed.length > 0) onConsumedRef.current?.(consumed);
      }
    } catch (error) {
      console.error('Failed to get queue status:', error);
    }
  }, [sessionId, getBaseUrl]);

  const getExecutionNode = useCallback(async (): Promise<ExecutionNodeInfo | null> => {
    if (!sessionId) return null;

    try {
      const response = await fetch(
        `${getBaseUrl()}/api/v2/execution/node/${sessionId}`
      );

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to get execution node:', error);
    }
    return null;
  }, [sessionId, getBaseUrl]);

  const clearQueue = useCallback(async () => {
    if (!sessionId) return;

    try {
      await fetch(
        `${getBaseUrl()}/api/v2/input/queue/${sessionId}`,
        { method: 'DELETE' }
      );

      setQueueState({
        hasPendingInput: false,
        queueLength: 0,
      });
      queueLengthRef.current = 0;
      pendingInputsRef.current = [];
    } catch (error) {
      console.error('Failed to clear queue:', error);
    }
  }, [sessionId, getBaseUrl]);

  const getPendingInputs = useCallback(() => {
    return [...pendingInputsRef.current];
  }, []);

  const consumePendingInputs = useCallback(() => {
    const inputs = [...pendingInputsRef.current];
    pendingInputsRef.current = [];
    queueLengthRef.current = 0;
    setQueueState(prev => ({
      ...prev,
      hasPendingInput: false,
      queueLength: 0,
    }));
    return inputs;
  }, []);

  const startPolling = useCallback((interval: number = 2000) => {
    pollActiveRef.current = true;
    pollIntervalValueRef.current = interval;
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    
    getQueueStatus();
    pollIntervalRef.current = setInterval(getQueueStatus, interval);
  }, [getQueueStatus]);

  const stopPolling = useCallback(() => {
    pollActiveRef.current = false;
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // 页面隐藏/失焦时暂停队列轮询,回到可见时若仍在轮询则立即补查并恢复 —— 防后台泄露。
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const pause = () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
    const resume = () => {
      if (!pollActiveRef.current) return;
      getQueueStatus();
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(getQueueStatus, pollIntervalValueRef.current);
    };
    const handleVisibility = () => {
      if (document.hidden) pause();
      else resume();
    };
    const handleBlur = () => pause();
    const handleFocus = () => resume();
    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
    };
  }, [getQueueStatus]);

  return {
    submitUserInput,
    getQueueStatus,
    clearQueue,
    getPendingInputs,
    consumePendingInputs,
    getExecutionNode,
    startPolling,
    stopPolling,
    isSubmitting,
    queueState,
    hasPendingInput: queueState.hasPendingInput,
    queueLength: queueState.queueLength,
    executionNode: queueState.executionNode,
    isLocal: queueState.isLocal,
  };
}

export default useUserInput;