import type { ChatHistoryResponse, IChatDialogueMessageSchema } from '@/types/chat';

/**
 * 仅就地更新「本轮 view 消息」(以 role='view' + order 作为稳定锚点),返回新数组,
 * 不整体覆盖 history。用于修复 vis manus 连续对话中,第一轮报错被写到第二轮
 * 问题之后的排序 bug:此前各 SSE 回调直接 setHistory([...tempHistory]) 用整份
 * 本轮快照回写,多轮/并发时会把其他轮消息覆盖或错位。
 *
 * @param history  当前完整消息列表
 * @param roundOrder 本轮(order.current)锚点,human 与 view 共用同一 order
 * @param patch    对目标 view 消息的更新函数(返回新消息对象)
 * @returns 更新后的新数组;找不到目标 view 时原样返回
 */
export function patchViewByOrder(
  history: ChatHistoryResponse,
  roundOrder: number,
  patch: (msg: IChatDialogueMessageSchema) => IChatDialogueMessageSchema,
): ChatHistoryResponse {
  const idx = history.findIndex(m => m.role === 'view' && m.order === roundOrder);
  if (idx < 0) return history;
  const updated = [...history];
  updated[idx] = patch(updated[idx]);
  return updated;
}
