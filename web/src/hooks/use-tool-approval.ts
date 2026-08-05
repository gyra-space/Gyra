import { useCallback, useEffect, useRef, useState } from 'react';

export interface PendingApproval {
  action_uid: string;
  tool_name: string;
  args: Record<string, unknown>;
}

export interface ToolApprovalState {
  hasPending: boolean;
  pending: PendingApproval[];
}

const apiBase = (): string => process.env.NEXT_PUBLIC_API_BASE_URL || '';

/**
 * 轮询当前会话的待授权工具调用，并提供 授权/拒绝 接口。
 *
 * 仅在对话非生成态(replyLoading=false)时轮询 —— 工具授权发生在对话 WAITING
 * 期间（Agent loop 已结束），此时前端处于空闲，可拉取待授权项渲染授权卡片。
 */
export function useToolApproval(
  sessionId: string | undefined,
  replyLoading: boolean,
  interval = 3000
) {
  const [state, setState] = useState<ToolApprovalState>({ hasPending: false, pending: [] });
  const [submitting, setSubmitting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPending = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`${apiBase()}/api/v2/tool/pending?conv_id=${encodeURIComponent(sessionId)}`, {
        credentials: 'include',
      });
      if (!res.ok) return;
      const data = await res.json();
      setState({
        hasPending: !!data.has_pending,
        pending: Array.isArray(data.pending) ? data.pending : [],
      });
    } catch {
      /* ignore */
    }
  }, [sessionId]);

  // 非生成态轮询；生成态停止并清空（新一轮开始，旧 pending 失效）。
  useEffect(() => {
    if (!sessionId || replyLoading) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      if (replyLoading) setState({ hasPending: false, pending: [] });
      return;
    }
    fetchPending();
    timerRef.current = setInterval(fetchPending, interval);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [sessionId, replyLoading, interval, fetchPending]);

  const approve = useCallback(
    async (actionUid: string, approved: boolean): Promise<boolean> => {
      if (!sessionId) return false;
      setSubmitting(true);
      try {
        const res = await fetch(`${apiBase()}/api/v2/tool/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ conv_id: sessionId, action_uid: actionUid, approved }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        return !!data.success;
      } catch {
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [sessionId]
  );

  return { ...state, submitting, approve, refresh: fetchPending };
}

export default useToolApproval;
