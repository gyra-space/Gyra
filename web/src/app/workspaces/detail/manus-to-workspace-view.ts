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

import type { ManusLeftPanelData, ManusRightPanelData, ManusThinkingSection } from '@/types/manus';
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
const LEFT_PANEL_FENCE = /```manus-left-panel\s*\n([\s\S]*?)\n```/;
// 思考围栏:d-thinking(drsk 思考卡片)/drsk-thinking(旧版思考卡片)。planning_window 的
// 正文(正文叙述/结论)是累加流,不能注入步骤流(会把最终结论排到工具步骤之前);
// 但思考(d-thinking)是纯推理过程,应注入为 thinking 步骤,否则对话页一旦进入
// "工作流"渲染(有工具步骤)就会切换到 AgentWorkspaceRenderer,把 thinking 完全隐藏。
const THINKING_FENCE = /```(?:d-thinking|drsk-thinking)\s*\n([\s\S]*?)\n```/g;

/** 从 planning_window 中提取思考内容(去重后返回 uid -> markdown)。
 *
 * thinking 围栏的 markdown 在流式阶段按 uid 累积,最后一帧携带完整文本;
 * 历史消息里同一 uid 会重复出现,故取"最后一次出现"的完整值,避免只渲染到片段。
 * 注:仅从 d-thinking / drsk-thinking 提取(唯一的「深度思考」块);drsk-content
 * 的 step_thought 块在 V2 里承载的是工具旁白(内容),不当作 thinking 步骤,避免
 * 把旁白误判成思考、并与工具胶囊的 narration 行重复。
 */
function extractThinkingFromPlanning(planningWindow: string): Map<string, string> {
  const byUid = new Map<string, string>();
  if (!planningWindow || typeof planningWindow !== 'string') return byUid;
  THINKING_FENCE.lastIndex = 0;
  let m: RegExpExecArray | null;
  // eslint-disable-next-line no-cond-assign
  while ((m = THINKING_FENCE.exec(planningWindow))) {
    try {
      const parsed = JSON.parse(m[1].trim());
      const uid = typeof parsed.uid === 'string' ? parsed.uid : '';
      const markdown = typeof parsed.markdown === 'string' ? parsed.markdown : '';
      if (uid && markdown) byUid.set(uid, markdown);
    } catch {
      // 非 JSON 围栏忽略
    }
  }
  return byUid;
}

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

/** 从步骤 outputs 中取「旁白」(thought 类型,即 LLM 调用工具前的叙述文本,由
 *  manus 转换器映射自 WorkEntry.assistant_content → ActionOutput.thoughts)。 */
function extractNarration(outputs?: Array<{ output_type?: string; content?: unknown }>): string | null {
  if (!outputs || !outputs.length) return null;
  const thought = outputs.find((o) => o?.output_type === 'thought' && typeof o.content === 'string' && o.content.trim());
  return typeof thought?.content === 'string' ? thought.content : null;
}

/** 取步骤首个可读的非旁白 output(工具结果正文):跳过 thought 类型,防止旁白被当成结果。 */
function firstOutputText(outputs?: Array<{ output_type?: string; content?: unknown }>): string | null {
  if (!outputs || !outputs.length) return null;
  for (const o of outputs) {
    if (o?.output_type === 'thought') continue;
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
    ts: f.ts || f.created_at || null,
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
      narration: extractNarration(sd?.outputs),
    });
  }
  return out;
}

/**
 * 从视图消息里提取最新的 manus 左面板数据(manus-left-panel 围栏,
 * 落在 planning_window 内)。倒序扫描取最新一份含 sections 的帧。
 */
function extractManusLeftPanel(messages: ManusViewMessage[]): ManusLeftPanelData | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role !== 'view' || typeof msg.context !== 'string') continue;
    try {
      const ctx = JSON.parse(msg.context);
      const pw = typeof ctx.planning_window === 'string' ? ctx.planning_window : '';
      const fm = LEFT_PANEL_FENCE.exec(pw);
      if (!fm) continue;
      const parsed = parseFenceJson(fm[1]);
      if (parsed && Array.isArray(parsed.sections)) {
        return parsed as unknown as ManusLeftPanelData;
      }
    } catch {
      // 非 JSON 视图忽略
    }
  }
  return null;
}

/** 当前进行中的 todo 阶段标题(仅工作中):含 running 步骤的段 → 含 active_step 的段 → 首个未完成段 */
function runningSectionTitle(left: ManusLeftPanelData | null): string | null {
  if (!left || !left.is_working) return null;
  if (!Array.isArray(left.sections) || left.sections.length === 0) return null;
  const sections = left.sections as ManusThinkingSection[];
  const byRunning = sections.find((sec) => sec.steps.some((s) => s.status === 'running'));
  if (byRunning?.title) return byRunning.title;
  if (left.active_step_id) {
    const byActive = sections.find((sec) => sec.steps.some((s) => s.id === left.active_step_id));
    if (byActive?.title) return byActive.title;
  }
  const first = sections.find((sec) => !sec.is_completed);
  if (first?.title) return first.title;
  return null;
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
  // 思考步骤按 uid 累积:同一 uid 在流式/历史消息里重复出现,取最后一次完整文本,
  // 但步骤位置固定在首次出现处(即该轮开头的思考),保证思考在工具步骤之前。
  const thinkingById = new Map<string, WorkspaceExecutionStep>();

  const pushStep = (s: WorkspaceExecutionStep) => {
    if (stepIds.has(s.id)) return;
    stepIds.add(s.id);
    execution.push(s);
  };

  const pushThinkingStep = (uid: string, markdown: string) => {
    const id = `think-${uid}`;
    const existing = thinkingById.get(id);
    if (existing) {
      // 只更新文本,不移动位置:同一轮思考的时序锚点固定在首次出现处
      existing.output = markdown;
      return;
    }
    const step: WorkspaceExecutionStep = {
      id,
      type: 'thinking',
      title: '深度思考',
      status: 'done',
      output: markdown,
    };
    thinkingById.set(id, step);
    execution.push(step);
  };

  // 交付/任务文件按消息顺序收集:前端 history 里每条 view 消息的 running_window
  // 都带有它当时下发的 deliverable_files/task_files。后端追问轮(新建 agent conv)
  // 只推本轮文件,若不累积,上轮交付物(如下发的 dashboard.html)会在追问轮消失。
  const deliverableInOrder: WorkspaceDeliverableFile[] = [];
  const taskFileInOrder: WorkspaceTaskFile[] = [];
  // summary 兜底:latestRight 未携带摘要时,回退到最近一条带 summary_content 的消息
  let fallbackSummary: string | null = null;

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
    let planningWindow = '';
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
        planningWindow = typeof ctx.planning_window === 'string' ? ctx.planning_window : '';
      } catch {
        // 非 JSON 视图忽略
      }
    }
    // 跨消息累积交付/任务文件:与步骤一样按真实时序收集,避免追问轮丢上轮交付物
    if (rightData) {
      if (rightData.summary_content) fallbackSummary = rightData.summary_content;
      for (const f of rightData.deliverable_files || []) {
        const d = toDeliverable(f);
        if (d) deliverableInOrder.push(d);
      }
      for (const f of rightData.task_files || []) {
        const t = toTaskFile(f);
        if (t) taskFileInOrder.push(t);
      }
    }
    // 思考(d-thinking)注入为 thinking 步骤:与工具步骤按同一消息帧穿插。
    // 旁白/结论(planning_window 的正文累加流)仍不注入 —— 最终结论统一走
    // view.summary 在 feed 底部渲染,避免把结论排到工具步骤之前。
    for (const [uid, markdown] of extractThinkingFromPlanning(planningWindow)) {
      pushThinkingStep(uid, markdown);
    }
    // 工具步骤(按真实时序,跨消息累积去重)
    for (const s of stepsMapToExecution(rightData?.steps_map)) pushStep(s);
  }

  const source = latestRight;
  // 运行中文案信号:由左面板阶段数据推导「阶段进行中」/「模型思考中」。
  // 注意不注入 view.planning —— manus 步骤无时间戳,若走 planning 时间线归组
  // 会被误归入「先前执行」;阶段标题用独立字段透传,仅由运行中文案消费。
  const leftPanel = extractManusLeftPanel(messages);
  const runningPhaseTitle = runningSectionTitle(leftPanel);
  const isWorking = !!latestRight?.is_running || !!leftPanel?.is_working;
  const hasRunningTool = execution.some((s) => s.type === 'tool_call' && s.status === 'running');
  const runningThinking = !!isWorking && !hasRunningTool && !runningPhaseTitle;

  // 旁白补全:流式阶段每条 view 消息的 steps_map 可能只是懒加载元信息(无 outputs),
  // 最新 right panel(source.steps_map)才带完整 outputs。据此为工具步骤回填 narration,
  // 使工具胶囊能稳定展示 LLM 调用工具前的旁白文本(与 scene workspace 折叠进工具步骤的语义对齐)。
  if (source?.steps_map) {
    for (const s of execution) {
      if (s.type !== 'tool_call' || s.narration) continue;
      const sd = source.steps_map[s.id];
      if (!sd) continue;
      const narr = extractNarration(sd.outputs);
      if (narr) s.narration = narr;
    }
  }

  // 交付文件按 file_id 去重:同一物理文件被多次修改/交付时,ts 会因来源不同
  // (增量 start_time 兜底 vs 全量 created_at)而变,按 file_id+ts 会把同一次交付
  // 识别成多条,导致同一文件展示多次且无版本记录。这里只保留 ts 最新的一份。
  // 任务文件同理按 file_id 合并(单个物理文件,同 id 取新值)。
  const seenDeliverable = new Set<string>();
  const deliverable_files: WorkspaceDeliverableFile[] = [];
  for (let i = deliverableInOrder.length - 1; i >= 0; i--) {
    const d = deliverableInOrder[i];
    if (seenDeliverable.has(d.file_id)) continue;
    seenDeliverable.add(d.file_id);
    deliverable_files.push(d);
  }
  const seenTask = new Set<string>();
  const task_files: WorkspaceTaskFile[] = [];
  for (let i = taskFileInOrder.length - 1; i >= 0; i--) {
    const t = taskFileInOrder[i];
    if (seenTask.has(t.file_id)) continue;
    seenTask.add(t.file_id);
    task_files.push(t);
  }

  return {
    planning: null,
    execution,
    summary: source?.summary_content || fallbackSummary || null,
    deliverable_files,
    task_files,
    panel_view: source ? toPanelView(source.panel_view) : 'execution',
    lobby_exhibits: [],
    subagents: [],
    running_phase_title: runningPhaseTitle,
    running_thinking: runningThinking,
  };
}
