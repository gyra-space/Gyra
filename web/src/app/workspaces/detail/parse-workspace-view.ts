import type {
  LobbyExhibit,
  LobbyExhibitKind,
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspacePanelView,
  WorkspaceTaskFile,
  WorkspaceView,
} from './agent-workspace-types';

const VALID_TYPES = ['tool_call', 'thinking', 'artifact', 'delivery', 'user', 'task_created'];
const VALID_STATUS = ['running', 'done', 'failed'];
const VALID_PANEL_VIEWS = ['execution', 'deliverable', 'summary', 'task_files'];

const VALID_EXHIBIT_KINDS: LobbyExhibitKind[] = [
  'image', 'video', 'audio', 'table', 'slides', 'html', 'pdf',
  'markdown', 'code', 'text', 'chart', 'data', 'file',
];

/** render_type → Exhibit kind 映射(deliverable_files 适配迁入大厅协议) */
const RENDER_TYPE_TO_KIND: Record<string, LobbyExhibitKind> = {
  iframe: 'html',
  image: 'image',
  video: 'video',
  audio: 'audio',
  pdf: 'pdf',
  markdown: 'markdown',
  code: 'code',
  text: 'text',
  table: 'table',
  slides: 'slides',
  chart: 'chart',
  archive: 'file',
};

function normalizeExhibit(raw: unknown): LobbyExhibit | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.exhibit_id !== 'string' || typeof r.title !== 'string') return null;
  const kind = VALID_EXHIBIT_KINDS.includes(r.kind as LobbyExhibitKind)
    ? (r.kind as LobbyExhibitKind)
    : 'file';
  const source = (r.source && typeof r.source === 'object' ? r.source : {}) as LobbyExhibit['source'];
  return {
    exhibit_id: r.exhibit_id,
    kind,
    title: r.title,
    source: {
      uri: typeof source.uri === 'string' ? source.uri : undefined,
      url: typeof source.url === 'string' ? source.url : undefined,
      inline: typeof source.inline === 'string' ? source.inline : undefined,
      mime_type: typeof source.mime_type === 'string' ? source.mime_type : undefined,
      file_size: typeof source.file_size === 'number' ? source.file_size : undefined,
    },
    render_hints:
      r.render_hints && typeof r.render_hints === 'object'
        ? (r.render_hints as LobbyExhibit['render_hints'])
        : undefined,
    provenance:
      r.provenance && typeof r.provenance === 'object'
        ? (r.provenance as LobbyExhibit['provenance'])
        : undefined,
    actions: Array.isArray(r.actions)
      ? (r.actions.filter((a) => typeof a === 'string') as LobbyExhibit['actions'])
      : undefined,
  };
}

/** 交付文件 → 大厅 Exhibit 适配器:旧链路产物无缝迁入通用容器 */
export function deliverableFileToExhibit(file: WorkspaceDeliverableFile): LobbyExhibit {
  return {
    exhibit_id: `deliverable_${file.file_id}`,
    kind: RENDER_TYPE_TO_KIND[file.render_type] || 'file',
    title: file.file_name,
    source: {
      url: file.content_url || file.download_url,
      mime_type: file.mime_type,
      file_size: file.file_size,
    },
    actions: ['preview', 'download'],
  };
}

function normalizeStep(raw: unknown): WorkspaceExecutionStep | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.id !== 'string' || typeof r.title !== 'string') return null;
  const type = VALID_TYPES.includes(r.type as string) ? (r.type as WorkspaceExecutionStep['type']) : 'tool_call';
  const status = VALID_STATUS.includes(r.status as string) ? (r.status as WorkspaceExecutionStep['status']) : 'running';
  return {
    id: r.id,
    type,
    title: r.title,
    status,
    ts: typeof r.ts === 'string' ? r.ts : null,
    action: typeof r.action === 'string' ? r.action : null,
    action_input: r.action_input && typeof r.action_input === 'object' ? (r.action_input as Record<string, unknown>) : null,
    output: typeof r.output === 'string' ? r.output : null,
    artifact: r.artifact && typeof r.artifact === 'object' ? (r.artifact as WorkspaceExecutionStep['artifact']) : null,
    vis: r.vis ?? null,
    exhibit: normalizeExhibit(r.exhibit),
    task_id: typeof r.task_id === 'number' ? r.task_id : undefined,
    task_title: typeof r.task_title === 'string' ? r.task_title : undefined,
    task_status: typeof r.task_status === 'string' ? r.task_status : undefined,
    playbook_name: typeof r.playbook_name === 'string' ? r.playbook_name : undefined,
    triggered_by: typeof r.triggered_by === 'string' ? r.triggered_by : undefined,
  };
}

function normalizeDeliverableFile(raw: unknown): WorkspaceDeliverableFile | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.file_id !== 'string' || typeof r.file_name !== 'string') return null;
  return {
    file_id: r.file_id,
    file_name: r.file_name,
    mime_type: typeof r.mime_type === 'string' ? r.mime_type : undefined,
    file_size: typeof r.file_size === 'number' ? r.file_size : 0,
    content_url: typeof r.content_url === 'string' ? r.content_url : undefined,
    download_url: typeof r.download_url === 'string' ? r.download_url : undefined,
    object_path: typeof r.object_path === 'string' ? r.object_path : undefined,
    render_type: (r.render_type as WorkspaceDeliverableFile['render_type']) || 'iframe',
  };
}

function normalizeTaskFile(raw: unknown): WorkspaceTaskFile | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.file_id !== 'string' || typeof r.file_name !== 'string') return null;
  return {
    file_id: r.file_id,
    file_name: r.file_name,
    file_type: typeof r.file_type === 'string' ? r.file_type : '',
    file_size: typeof r.file_size === 'number' ? r.file_size : 0,
    mime_type: typeof r.mime_type === 'string' ? r.mime_type : undefined,
    oss_url: typeof r.oss_url === 'string' ? r.oss_url : undefined,
    preview_url: typeof r.preview_url === 'string' ? r.preview_url : undefined,
    download_url: typeof r.download_url === 'string' ? r.download_url : undefined,
    description: typeof r.description === 'string' ? r.description : undefined,
    created_at: typeof r.created_at === 'string' ? r.created_at : undefined,
    object_path: typeof r.object_path === 'string' ? r.object_path : undefined,
  };
}

/**
 * ts 归一化为毫秒数。服务端步骤是本地时间 naive ISO(可能带 6 位微秒或空格
 * 分隔),乐观用户步骤是 UTC ISO(带 Z);Date.parse 对 naive 按本地时区、
 * 带 Z 按 UTC 解析,两者可正确对齐。无法解析返回 null(排最后)。
 */
function tsToMs(ts: string | null | undefined): number | null {
  if (!ts) return null;
  let norm = ts.includes(' ') ? ts.replace(' ', 'T') : ts;
  // 微秒(>3 位小数)截断为毫秒,避免老引擎解析失败
  norm = norm.replace(/\.(\d{3})\d+/, '.$1');
  const ms = Date.parse(norm);
  return Number.isNaN(ms) ? null : ms;
}

const EMPTY_VIEW: WorkspaceView = { planning: null, execution: [], summary: null, deliverable_files: [], task_files: [], panel_view: 'execution', lobby_exhibits: [] };

export function parseWorkspaceView(chunk: unknown, prev: WorkspaceView | null): WorkspaceView {
  if (!chunk || typeof chunk !== 'object') return prev ?? EMPTY_VIEW;
  const c = chunk as Record<string, unknown>;
  if (!Array.isArray(c.execution)) return prev ?? EMPTY_VIEW;

  const prevById = new Map((prev?.execution ?? []).map(e => [e.id, e]));
  const execution: WorkspaceExecutionStep[] = [];
  for (const raw of c.execution) {
    const step = normalizeStep(raw);
    if (!step) continue;
    const existing = prevById.get(step.id);
    execution.push(existing ? { ...existing, ...step } : step);
    prevById.delete(step.id);
  }
  // 保留 prev 中未被本 chunk 覆盖的旧步骤(前轮 agent conv 的步骤)
  for (const leftover of prevById.values()) {
    execution.push(leftover);
  }
  // 跨轮次合并按时间戳交错(用户消息/工具/回复按真实时序排列);
  // 必须解析成毫秒再比:字符串直接比较会把 UTC(带 Z)和本地 naive 两种格式
  // 排错(时区偏移导致 user 气泡聚堆、当前步骤被埋进历史中间)。无 ts 排后。
  execution.sort((a, b) => {
    const ma = tsToMs(a.ts);
    const mb = tsToMs(b.ts);
    if (ma === null && mb === null) return 0;
    if (ma === null) return 1;
    if (mb === null) return -1;
    return ma - mb;
  });

  const planning = c.planning && typeof c.planning === 'object'
    ? (c.planning as WorkspaceView['planning'])
    : (prev?.planning ?? null);
  const summary = typeof c.summary === 'string' ? c.summary : (prev?.summary ?? null);

  // 交付文件 / 任务文件:后端每次全量推送,直接替换(不做合并)
  const deliverable_files = Array.isArray(c.deliverable_files)
    ? c.deliverable_files.map(normalizeDeliverableFile).filter((f): f is WorkspaceDeliverableFile => f !== null)
    : (prev?.deliverable_files ?? []);
  const task_files = Array.isArray(c.task_files)
    ? c.task_files.map(normalizeTaskFile).filter((f): f is WorkspaceTaskFile => f !== null)
    : (prev?.task_files ?? []);

  // panel_view: 后端指示自动切换; 前端可在用户手动切换后忽略后续自动切换
  const panel_view_raw = typeof c.panel_view === 'string' ? c.panel_view : (prev?.panel_view ?? 'execution');
  const panel_view = VALID_PANEL_VIEWS.includes(panel_view_raw)
    ? (panel_view_raw as WorkspacePanelView)
    : 'execution';

  // 大厅入驻内容:后端全量推送时按 exhibit_id 幂等合并(同 ID 覆盖,旧条目保留);
  // 未推送时保留 prev(与 deliverable_files 直替不同:exhibit 可由多来源增量入驻)
  let lobby_exhibits = prev?.lobby_exhibits ?? [];
  if (Array.isArray(c.lobby_exhibits)) {
    const byId = new Map(lobby_exhibits.map((e) => [e.exhibit_id, e]));
    for (const raw of c.lobby_exhibits) {
      const ex = normalizeExhibit(raw);
      if (ex) byId.set(ex.exhibit_id, ex);
    }
    lobby_exhibits = Array.from(byId.values());
  }

  return { planning, execution, summary, deliverable_files, task_files, panel_view, lobby_exhibits };
}