/**
 * manus → WorkspaceView 适配器。
 *
 * vis_manus 布局的对话数据经 running_window(manus-right-panel 围栏)与
 * planning_window(VIS 卡片)两条通道下发;渲染"工作流"风格视图(图2 场景空间简洁模式)
 * 需要 WorkspaceView(execution / summary / deliverable_files / task_files / panel_view)。
 *
 * 本模块把 manus 视图数据转换为 WorkspaceView:
 * - human 消息 → user 步骤;view 消息 → 解析 running_window 的 steps_map 为 tool_call 步骤;
 *   旁白/结论不在步骤流里注入(planning_window 正文是累加流,注入会把最终结论放到工具
 *   步骤之前),最终结论由 summary_content 映射为 view.summary,在 feed 底部渲染,保证
 *   「工具步骤在前、结论在后」的正确时序;
 * - summary/deliverable/task_files/panel_view 直接由 manus right panel 映射。
 *
 * 纯函数、无 React 依赖,便于对拍测试。
 */

import type { ManusRightPanelData } from '@/types/manus';
import type {
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspacePanelView,
  WorkspaceTaskFile,
  WorkspaceView,
} from './agent-workspace-types';

/** 一条对话消息的最小形状(ManusChatContent 的 history 项) */
export interface ManusViewMessage {
  role: string;
  context?: string;
  order?: number;
  thinking?: boolean;
}

const RIGHT_PANEL_FENCE = /```manus-right-panel\s*\n([\s\S]*?)\n```/;

/** 解析围栏 JSON;非 JSON 或结构不符返回 null */
function parseFenceJson(body: string): Record<string, unknown> | null {
  const trimmed = body.trim();
  if (!trimmed.startsWith('{')) return null;
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

const STATUS_MAP: Record<string, WorkspaceExecutionStep['status']> = {
  running: 'running',
  completed: 'done',
  done: 'done',
  success: 'done',
  pending: 'running',
  error: 'failed',
  failed: 'failed',
  interrupted: 'failed',
};

function toWsStatus(status?: string): WorkspaceExecutionStep['status'] {
  const key = (status || '').toLowerCase();
  return STATUS_MAP[key] || 'done';
}

/** 取步骤首个可读文本 output(用于左侧 summary/展开) */
function firstOutputText(outputs?: Array<{ content?: unknown }>): string | null {
  if (!outputs || !outputs.length) return null;
  for (const o of outputs) {
    if (typeof o.content === 'string' && o.content.trim()) return o.content;
  }
  return null;
}

function toPanelView(v: string): WorkspacePanelView {
  if (v === 'deliverable') return 'deliverable';
  if (v === 'summary') return 'summary';
  if (v === 'files' || v === 'task_files') return 'task_files';
  return 'execution';
}

function toDeliverable(f: any): WorkspaceDeliverableFile | null {
  if (!f || typeof f.file_id !== 'string' || typeof f.file_name !== 'string') return null;
  return {
    file_id: f.file_id,
    file_name: f.file_name,
    mime_type: f.mime_type,
    file_size: f.file_size || 0,
    content_url: f.content_url,
    download_url: f.download_url,
    object_path: f.object_path,
    render_type: (f.render_type as WorkspaceDeliverableFile['render_type']) || 'iframe',
  };
}

function toTaskFile(f: any): WorkspaceTaskFile | null {
  if (!f || typeof f.file_id !== 'string' || typeof f.file_name !== 'string') return null;
  return {
    file_id: f.file_id,
    file_name: f.file_name,
    file_type: f.file_type || '',
    file_size: f.file_size || 0,
    mime_type: f.mime_type,
    oss_url: f.oss_url,
    preview_url: f.preview_url,
    download_url: f.download_url,
    description: f.description,
    created_at: f.created_at,
    object_path: f.object_path,
  };
}

/** 把 manus right panel 的 steps_map 转成有序的 tool_call 步骤 */
function stepsMapToExecution(stepsMap: Record<string, any> | undefined): WorkspaceExecutionStep[] {
  const out: WorkspaceExecutionStep[] = [];
  const seen = new Set<string>();
  if (!stepsMap) return out;
  for (const sd of Object.values(stepsMap)) {
    const step = sd?.active_step;
    if (!step || typeof step.id !== 'string' || seen.has(step.id)) continue;
    seen.add(step.id);
    out.push({
      id: step.id,
      type: 'tool_call',
      title: step.title || step.action || '工具步骤',
      status: toWsStatus(step.status),
      action: step.action || null,
      action_input: step.action_input && typeof step.action_input === 'object' ? (step.action_input as Record<string, unknown>) : null,
      output: firstOutputText(sd?.outputs),
    });
  }
  return out;
}

/**
 * 由 manus 视图消息 + 最新 right panel 汇总 WorkspaceView。
 * @param messages view/human 消息(按 order 排列)
 * @param latestRight 最新的 manus-right-panel 数据(提供文件/摘要/panel_view)
 */
export function buildManusWorkspaceView(
  messages: ManusViewMessage[],
  latestRight: ManusRightPanelData | null,
): WorkspaceView {
  const execution: WorkspaceExecutionStep[] = [];
  const stepIds = new Set<string>();

  const pushStep = (s: WorkspaceExecutionStep) => {
    if (stepIds.has(s.id)) return;
    stepIds.add(s.id);
    execution.push(s);
  };

  for (const msg of messages) {
    if (msg.role === 'human') {
      const text = typeof msg.context === 'string' ? msg.context.trim() : '';
      if (!text) continue;
      pushStep({
        id: `user-${msg.order ?? execution.length}-${text.slice(0, 8)}`,
        type: 'user',
        title: '我',
        status: 'done',
        output: text,
      });
      continue;
    }
    if (msg.role !== 'view') continue;
    let rightData: ManusRightPanelData | null = null;
    if (typeof msg.context === 'string') {
      try {
        const ctx = JSON.parse(msg.context);
        if (typeof ctx.running_window === 'string') {
          const fm = RIGHT_PANEL_FENCE.exec(ctx.running_window);
          if (fm) {
            const parsed = parseFenceJson(fm[1]);
            if (parsed) rightData = parsed as unknown as ManusRightPanelData;
          }
        }
      } catch {
        // 非 JSON 视图忽略
      }
    }
    // 工具步骤(按真实时序,跨消息累积去重)。旁白/结论一律不在此注入 ——
    // planning_window 的正文是累加流,若按 thinking 步骤注入会把最终结论放到
    // 工具步骤之前;结论统一走 view.summary 在 feed 底部渲染,顺序才正确。
    for (const s of stepsMapToExecution(rightData?.steps_map)) pushStep(s);
  }

  const source = latestRight;
  return {
    planning: null,
    execution,
    summary: source?.summary_content || null,
    deliverable_files: (source?.deliverable_files || []).map(toDeliverable).filter((f): f is WorkspaceDeliverableFile => f !== null),
    task_files: (source?.task_files || []).map(toTaskFile).filter((f): f is WorkspaceTaskFile => f !== null),
    panel_view: source ? toPanelView(source.panel_view) : 'execution',
    lobby_exhibits: [],
    subagents: [],
  };
}
