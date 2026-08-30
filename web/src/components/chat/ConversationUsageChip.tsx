'use client';

/**
 * 会话级「模型 + token」汇总 chip。
 *
 * 两种用法：
 * - 传 `summary`：由父级批量拉取后传入（历史列表），纯展示，避免 N+1；
 * - 传 `conversationId`：自身按单个会话懒加载（会话头部）。
 * 无数据（total_tokens=0）时隐藏，不占位。
 */

import React, { useEffect, useState } from 'react';
import { getUsageConversationSummary, type ConversationUsageSummary } from '@/client/api/usage';
import { apiInterceptors } from '@/client/api';
import { formatTokens } from '@/types/context-metrics';

interface ConversationUsageChipProps {
  /** 已有汇总数据（批量列表场景），优先于 conversationId */
  summary?: ConversationUsageSummary | null;
  /** 单个会话懒加载（会话头部场景） */
  conversationId?: string;
  onClick?: () => void;
}

export const ConversationUsageChip: React.FC<ConversationUsageChipProps> = ({
  summary,
  conversationId,
  onClick,
}) => {
  const [fetched, setFetched] = useState<ConversationUsageSummary | null>(null);

  useEffect(() => {
    if (summary || !conversationId) return;
    let cancelled = false;
    apiInterceptors(getUsageConversationSummary([conversationId]))
      .then(([err, res]) => {
        if (cancelled) return;
        setFetched(err ? null : res?.[0] || null);
      })
      .catch(() => {
        if (!cancelled) setFetched(null);
      });
    return () => {
      cancelled = true;
    };
  }, [summary, conversationId]);

  const data = summary || fetched;
  if (!data || !data.total_tokens) return null;

  const models = data.model_names || [];
  const primary = models[0];
  const extra = models.length > 1 ? ` +${models.length - 1}` : '';

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
      className="inline-flex items-center gap-1 rounded-full border border-solid border-[#e4e9f0] bg-gray-50 px-2 py-0.5 text-[11px] text-gray-500 hover:border-[#0069fe]/40 hover:text-[#0069fe]"
      title={`本次会话使用 ${models.join(', ') || '未知'} · 共 ${formatTokens(data.total_tokens)} tokens`}
    >
      <span className="font-medium">{primary || '未知'}{extra}</span>
      <span className="text-gray-400">·</span>
      <span>⛁ {formatTokens(data.total_tokens)}</span>
    </button>
  );
};

export default ConversationUsageChip;
