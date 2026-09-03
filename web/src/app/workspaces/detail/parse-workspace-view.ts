import type {
  LobbyExhibit,
  LobbyExhibitKind,
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspacePanelView,
  WorkspaceSubagentItem,
  WorkspaceTaskFile,
  WorkspaceView,
} from './agent-workspace-types';

const VALID_TYPES = ['tool_call', 'thinking', 'artifact', 'delivery', 'user', 'task_created', 'answer', 'skill_loaded', 'memory_loaded', 'skill_published'];
const VALID_STATUS = ['running', 'done', 'failed'];
const VALID_PANEL_VIEWS = ['execution', 'deliverable', 'summary', 'task_files'];
const VALID_SUBAGENT_STATUS = ['pending', 'running', 'done', 'failed', 'awaiting_authorization'];

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
  // status 归一:识别 running/done/failed;未知值(completed/finished/executing 等
  // 后端变体)回退 done 而非 running —— 回退 running 会让历史恢复的已完成
  // 步骤永远停在转圈态。流式期间新步骤由后端显式下发 running,不受影响。
  const rawStatus = String(r.status || '').toLowerCase();
  const status: WorkspaceExecutionStep['status'] = VALID_STATUS.includes(rawStatus)
    ? (rawStatus as WorkspaceExecutionStep['status'])
    : 'done';
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
    narration: typeof r.narration === 'string' ? r.narration : null,
    exhibit: normalizeExhibit(r.exhibit),
    skill_xml: typeof r.skill_xml === 'string' ? r.skill_xml : null,
    task_id: typeof r.task_id === 'number' ? r.task_id : undefined,
    task_title: typeof r.task_title === 'string' ? r.task_title : undefined,
    task_status: typeof r.task_status === 'string' ? r.task_status : undefined,
    playbook_name: typeof r.playbook_name === 'string' ? r.playbook_name : undefined,
    triggered_by: typeof r.triggered_by === 'string' ? r.triggered_by : undefined,
    attachments: Array.isArray(r.attachments) ? (r.attachments as WorkspaceExecutionStep['attachments']) : null,
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
    ts: typeof r.ts === 'string' ? r.ts : (typeof r.created_at === 'string' ? r.created_at : null),
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

function normalizeSubagent(raw: unknown): WorkspaceSubagentItem | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.sub_conv_id !== 'string' || !r.sub_conv_id) return null;
  const status = VALID_SUBAGENT_STATUS.includes(r.status as string)
    ? (r.status as WorkspaceSubagentItem['status'])
    : 'running';
  return {
    sub_conv_id: r.sub_conv_id,
    agent_name: typeof r.agent_name === 'string' ? r.agent_name : undefined,
    task: typeof r.task === 'string' ? r.task : undefined,
    status,
    mode: typeof r.mode === 'string' ? r.mode : undefined,
    authorization: typeof r.authorization === 'string' ? r.authorization : undefined,
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

const EMPTY_VIEW: WorkspaceView = { planning: null, execution: [], summary: null, deliverable_files: [], task_files: [], panel_view: 'execution', lobby_exhibits: [], subagents: [] };

/** 按 file_id 合并交付/任务文件:同 id 取新值,旧条目保留(会话级累积,防御后端只推当前轮)。 */
function mergeFilesById<T extends { file_id: string }>(prev: T[], next: T[]): T[] {
  const seen = new Set(next.map((f) => f.file_id));
  const merged = [...next];
  for (const f of prev) {
    if (!seen.has(f.file_id)) {
      merged.push(f);
      seen.add(f.file_id);
    }
  }
  return merged;
}

/** 为缺失产出时间戳的新交付文件补上「首次进入视图」的当前时间。
 *  已带 ts 的文件原样返回;同一批文件共用同一锚点(它们同属一个 chunk)。
 *  补 ts 只发生在首次出现时 —— 后续 chunk 再带同一 file_id 时,mergeDeliverableFiles
 *  在内容相同分支会保留最早那份 ts,锚点不会被新 chunk 顶掉。 */
function stampMissingTs(files: WorkspaceDeliverableFile[]): WorkspaceDeliverableFile[] {
  if (!files.some((f) => !f.ts)) return files;
  const now = new Date().toISOString();
  return files.map((f) => (f.ts ? f : { ...f, ts: now }));
}

/** 判断两份交付文件是否指向同一版本内容(文件名、URL、渲染类型均相同)。
 *  用于区分"后端重复下发同一文件"与"同一 file_id 被修改/重新交付为新版本"。 */
function isSameDeliverableContent(a: WorkspaceDeliverableFile, b: WorkspaceDeliverableFile): boolean {
  return (
    a.file_name === b.file_name &&
    a.content_url === b.content_url &&
    a.download_url === b.download_url &&
    a.object_path === b.object_path &&
    a.render_type === b.render_type &&
    a.mime_type === b.mime_type &&
    a.file_size === b.file_size
  );
}

/** 交付文件合并:按 file_id 去重,同 file_id 只展示一份。
 *  - 内容真正变化(file_name/URL 等变了)时按新版本处理,ts 随新版本走;
 *  - 内容相同仅 ts 被后端刷新(每帧重复下发同一文件)时,保留最早 ts 作为产出时间锚点,
 *    避免历史交付物被错误归属到最新轮次。 */
function mergeDeliverableFiles(prev: WorkspaceDeliverableFile[], next: WorkspaceDeliverableFile[]): WorkspaceDeliverableFile[] {
  const byId = new Map<string, WorkspaceDeliverableFile>();
  // next 为本轮(较新)数据在前,prev 历史在后;先处理新 chunk 保持输出顺序
  for (const f of [...next, ...prev]) {
    const fid = f.file_id;
    const existing = byId.get(fid);
    if (!existing) {
      byId.set(fid, f);
      continue;
    }
    const curMs = tsToMs(existing.ts);
    const newMs = tsToMs(f.ts);
    const contentChanged = !isSameDeliverableContent(existing, f);
    if (contentChanged) {
      // 真实版本更新:保留 ts 更新的一份;都无 ts 时保留 next(existing)
      if (newMs !== null && (curMs === null || newMs > curMs)) {
        byId.set(fid, f);
      }
    } else {
      // 内容相同:保留 earliest ts 作为产出时间锚点,
      // 避免后端每帧/新轮重复下发同一文件时把归属推到最新轮次
      const earliestTs = curMs !== null && (newMs === null || curMs < newMs) ? existing.ts : f.ts;
      byId.set(fid, { ...f, ts: earliestTs });
    }
  }
  return Array.from(byId.values());
}

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
  // summary 兜底修正:execution 已按 ts 排序,时序最后一个 answer 步骤即最新回答;
  // 后端 summary 取自 narration 插入序,可能停在中间轮的过渡文本上
  let summary = typeof c.summary === 'string' ? c.summary : (prev?.summary ?? null);
  const lastAnswer = [...execution].reverse().find((s) => s.type === 'answer' && (s.output || '').trim());
  if (lastAnswer?.output) summary = lastAnswer.output;

  // 交付文件 / 任务文件:后端按当前轮次(agent conv)全量推送,新轮追问(新建
  // agent conv)只会带本轮文件。交付文件按 file_id+ts 合并(跨轮各轮保留自己的文件);
  // 任务文件按 file_id 合并(单个物理文件,同 id 取新值)。
  //
  // 产出时间戳兜底:后端未下发 ts/created_at 时,以「首次进入视图」的时间作为
  // 归属锚点。否则这些文件永远无法落到任何轮次区间,会被渲染到 feed 最底部,
  // 多轮追问时表现为「历史交付物跟着最新一轮跑」。
  const deliverable_files = Array.isArray(c.deliverable_files)
    ? mergeDeliverableFiles(
        prev?.deliverable_files ?? [],
        stampMissingTs(
          c.deliverable_files.map(normalizeDeliverableFile).filter((f): f is WorkspaceDeliverableFile => f !== null),
        ),
      )
    : (prev?.deliverable_files ?? []);
  const task_files = Array.isArray(c.task_files)
    ? mergeFilesById(prev?.task_files ?? [], c.task_files.map(normalizeTaskFile).filter((f): f is WorkspaceTaskFile => f !== null))
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

  // 异步子 agent 任务看板:后端每次全量推送,直接替换(与 deliverable_files 同语义)
  const subagents = Array.isArray(c.subagents)
    ? c.subagents.map(normalizeSubagent).filter((s): s is WorkspaceSubagentItem => s !== null)
    : (prev?.subagents ?? []);

  return { planning, execution, summary, deliverable_files, task_files, panel_view, lobby_exhibits, subagents };
}