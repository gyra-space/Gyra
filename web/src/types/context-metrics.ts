/**
 * 上下文压缩监控类型定义
 * 
 * 用于三层压缩机制的实时监控
 */

/**
 * 压缩层级枚举
 */
export type CompressionLayer = 'truncation' | 'pruning' | 'compaction';

/**
 * Layer 1: 截断指标
 */
export interface TruncationMetrics {
  total_count: number;
  total_bytes_truncated: number;
  total_bytes_original: number;
  total_lines_truncated: number;
  total_files_archived: number;
  last_tool_name: string;
  last_original_size: number;
  last_truncated_size: number;
  last_file_key: string | null;
  last_timestamp: number;
  tool_stats: Record<string, { count: number; bytes: number }>;
}

/**
 * Layer 2: 修剪指标
 */
export interface PruningMetrics {
  total_count: number;
  total_messages_pruned: number;
  total_tokens_saved: number;
  last_messages_count: number;
  last_tokens_saved: number;
  last_trigger_reason: string;
  last_usage_ratio: number;
  last_timestamp: number;
  usage_history: Array<{
    timestamp: number;
    usage_ratio: number;
    tokens: number;
    message_count: number;
  }>;
}

/**
 * Layer 3: 压缩归档指标
 */
export interface CompactionMetrics {
  total_count: number;
  total_messages_archived: number;
  total_tokens_saved: number;
  total_chapters_created: number;
  current_chapters: number;
  current_chapter_index: number;
  last_messages_archived: number;
  last_tokens_saved: number;
  last_chapter_index: number;
  last_summary_length: number;
  last_timestamp: number;
  chapter_stats: Array<{
    index: number;
    messages: number;
    tokens_saved: number;
    summary_length: number;
    key_tools: string[];
    timestamp: number;
  }>;
}

/**
 * 上下文压缩总指标
 */
export interface ContextMetrics {
  conv_id: string;
  session_id: string;
  current_tokens: number;
  context_window: number;
  usage_ratio: number;
  usage_percent: string;
  message_count: number;
  round_counter: number;
  config: Record<string, unknown>;
  truncation: TruncationMetrics;
  pruning: PruningMetrics;
  compression: CompactionMetrics;
  created_at: number;
  updated_at: number;
  duration_seconds: number;
}

/**
 * 轻量上下文用量指标（来自 SSE usage_metric 事件）
 */
export interface UsageMetrics {
  total: number;
  prompt: number;
  completion: number;
  context_window: number;
  ratio: number;
  step_state?: string;
  /** system prompt 占用 token */
  system?: number;
  /** 历史消息（不含当前用户消息）占用 token */
  history?: number;
  /** 当前用户消息占用 token */
  user_msg?: number;
  /** 工具列表及子智能体占用 token */
  tools?: number;
  /** 连接器及 MCP 占用 token */
  mcp?: number;
  /** 技能占用 token */
  skills?: number;
  /** 分层 compressed/retained 占用 */
  layers?: { compressed: number; retained: number };
}

/**
 * WebSocket 推送事件类型
 */
export interface ContextMetricsEvent {
  type: 'event';
  event_type: 'context_metrics_update' | 'context_metrics_full';
  conv_id: string;
  timestamp: string;
  data: ContextMetrics;
}

/**
 * 空的三层压缩指标，用于从 UsageMetrics 合成 ContextMetrics
 */
export const DEFAULT_TRUNCATION_METRICS: TruncationMetrics = {
  total_count: 0,
  total_bytes_truncated: 0,
  total_bytes_original: 0,
  total_lines_truncated: 0,
  total_files_archived: 0,
  last_tool_name: '',
  last_original_size: 0,
  last_truncated_size: 0,
  last_file_key: null,
  last_timestamp: 0,
  tool_stats: {},
};

export const DEFAULT_PRUNING_METRICS: PruningMetrics = {
  total_count: 0,
  total_messages_pruned: 0,
  total_tokens_saved: 0,
  last_messages_count: 0,
  last_tokens_saved: 0,
  last_trigger_reason: '',
  last_usage_ratio: 0,
  last_timestamp: 0,
  usage_history: [],
};

export const DEFAULT_COMPRESSION_METRICS: CompactionMetrics = {
  total_count: 0,
  total_messages_archived: 0,
  total_tokens_saved: 0,
  total_chapters_created: 0,
  current_chapters: 0,
  current_chapter_index: 0,
  last_messages_archived: 0,
  last_tokens_saved: 0,
  last_chapter_index: 0,
  last_summary_length: 0,
  last_timestamp: 0,
  chapter_stats: [],
};

/**
 * 把轻量的 UsageMetrics 转成 ContextMetrics，供详情抽屉展示。
 * 三层压缩数据暂时补零，后续接入完整的 context_metrics_* SSE 事件后可替换。
 */
export function usageMetricsToContextMetrics(usage: UsageMetrics): ContextMetrics {
  return {
    conv_id: '',
    session_id: '',
    current_tokens: usage.total,
    context_window: usage.context_window,
    usage_ratio: usage.ratio,
    usage_percent: `${(usage.ratio * 100).toFixed(1)}%`,
    message_count: 0,
    round_counter: 0,
    config: {},
    truncation: DEFAULT_TRUNCATION_METRICS,
    pruning: DEFAULT_PRUNING_METRICS,
    compression: DEFAULT_COMPRESSION_METRICS,
    created_at: Date.now(),
    updated_at: Date.now(),
    duration_seconds: 0,
  };
}

/**
 * 格式化 token 数量
 */
export function formatTokens(tokens: number): string {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  } else if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`;
  }
  return tokens.toString();
}

/**
 * 轮次 id 归一化为会话 id（幂等）—— 与后端
 * `gyra_serve/conversation/ids.py::to_conversation_id` 同语义。
 * 兼容前端传 conv_id(uuid_N，轮次) 或 conv_session_id(纯 uuid，会话) 两种来源。
 * 术语见 docs/naming-conversation-ids.md：会话 conversationId / 轮次 turnId。
 */
export function toConversationId(id?: string | null): string {
  if (!id) return '';
  const parts = id.split('_');
  if (parts.length > 1 && /^\d+$/.test(parts[parts.length - 1])) {
    return parts.slice(0, -1).join('_');
  }
  return id;
}

/**
 * 获取使用率等级
 */
export function getUsageLevel(usageRatio: number): 'low' | 'medium' | 'high' | 'critical' {
  if (usageRatio < 0.5) return 'low';
  if (usageRatio < 0.7) return 'medium';
  if (usageRatio < 0.85) return 'high';
  return 'critical';
}

/**
 * 获取使用率颜色
 */
export function getUsageColor(level: 'low' | 'medium' | 'high' | 'critical'): string {
  const colors = {
    low: '#52c41a',
    medium: '#faad14',
    high: '#fa8c16',
    critical: '#ff4d4f',
  };
  return colors[level];
}