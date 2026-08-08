'use client';

import { formatTokens } from '@/types/context-metrics';
import { CompressionSegmentVo } from '@/types/chat';
import { useState } from 'react';

/**
 * 压缩点组件：在消息列表的压缩边界处渲染，提示"此处以上消息已压缩"，
 * 可展开查看该压缩段的 LLM 摘要。
 */
export default function CompressionPoint({ segment }: { segment: CompressionSegmentVo }) {
  const [expanded, setExpanded] = useState(false);
  const saved = Math.max(0, segment.original_tokens - segment.compressed_tokens);
  return (
    <div className="my-3 flex justify-center">
      <div className="w-full max-w-2xl rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50">
        <button
          type="button"
          className="flex w-full items-center justify-between px-3 py-2 text-xs text-gray-500 dark:text-gray-400"
          onClick={() => setExpanded(v => !v)}
        >
          <span>
            🗜 此处以上 {segment.source_message_ids.length} 条消息已压缩为摘要
            （第 {segment.segment_index} 次压缩，节省 ~{formatTokens(saved)} tokens）
          </span>
          <span>{expanded ? '收起 ▲' : '查看摘要 ▼'}</span>
        </button>
        {expanded && segment.summary && (
          <div className="mt-1 whitespace-pre-wrap border-t border-gray-200 px-3 pb-3 pt-2 text-xs text-gray-600 dark:border-gray-700 dark:text-gray-300">
            {segment.summary}
          </div>
        )}
      </div>
    </div>
  );
}
