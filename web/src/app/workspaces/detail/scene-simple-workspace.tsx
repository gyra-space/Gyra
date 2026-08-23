'use client';

/**
 * 场景空间「简洁模式」运行态:左侧对话 feed + 右侧工作空间预览。
 * 左侧:过程步骤由 AgentWorkspaceRenderer 折叠进「执行胶囊」内嵌对话流,
 * 回答/交付占据主视觉(结果为主,过程随行)。
 * 右侧:工作空间预览面板,能力对齐 vis_manus right panel —— 专用步骤渲染器
 * (Terminal/代码执行/SQL/HTML,复用 VisManusRightPanel 渲染器)、流式期间
 * 自动跟随当前步骤、步骤 prev/next 导航、任务文件 / 总结 / 交付物、
 * panel_view 自动切 tab、PDF 导出。默认收起,点击左侧步骤/文件触发展开。
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import SkillContentRenderer from '@/components/chat/chat-content-components/VisComponents/VisManusRightPanel/renderers/SkillContentRenderer';
import { Button, Spin } from 'antd';
import { GPTVis } from '@antv/gpt-vis';
import {
  CodeOutlined,
  CloseOutlined,
  DoubleRightOutlined,
  DownloadOutlined,
  ExpandOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  InboxOutlined,
  LeftOutlined,
  RightOutlined,
} from '@ant-design/icons';
import markdownComponents, { markdownPlugins, preprocessLaTeX } from '@/components/chat/chat-content-components/config';
import {
  CodeExecutionRenderer,
  HtmlTabbedRenderer,
  OutputRenderer,
  SqlQueryRenderer,
  TerminalRenderer,
} from '@/components/chat/chat-content-components/VisComponents/VisManusRightPanel/renderers';
import type { ManusExecutionOutput, ManusStepStatus } from '@/types/manus';
import { AgentWorkspaceRenderer } from './agent-workspace-renderer';
import { ExhibitHost, resolveExhibitDownloadUrl } from './lobby-exhibit';
import { transformFileUrl } from '@/utils';
import type {
  LobbyExhibit,
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspaceTaskFile,
  WorkspaceView,
} from './agent-workspace-types';

export interface SceneSimpleWorkspaceProps {
  view: WorkspaceView;
  running: boolean;
  error?: string | null;
  switchingTask?: boolean;
  convLoadError?: string | null;
  retryLoadConv?: () => void;
  agentIcon?: string | null;
  agentName?: string | null;
  /** 本次对话选用的模型名(运行中文案「xx模型 思考中」使用) */
  modelName?: string | null;
  onInteractionResume?: (userMessage: string) => void;
  /** 返回欢迎态(退出任务/会话详情) */
  onExit?: () => void;
  /** 输入条:渲染在左侧对话 feed 底部(与对话同列) */
  inputSlot?: React.ReactNode;
}

type RightTabKey = 'execution' | 'task_files' | 'summary';

function fmtSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function getFileEmoji(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  const map: Record<string, string> = {
    html: '🌐', htm: '🌐', md: '📝', pdf: '📕',
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', svg: '🖼️', webp: '🖼️',
    py: '🐍', js: '📜', ts: '📜', java: '☕', go: '🔵', rs: '🦀',
    sql: '🗄️', csv: '📊', xlsx: '📊', xls: '📊',
    json: '📋', yaml: '📋', yml: '📋', xml: '📋',
    txt: '📄', log: '📄', zip: '📦', tar: '📦', gz: '📦',
    mp4: '🎬', mov: '🎬', webm: '🎬', avi: '🎬', mkv: '🎬',
    mp3: '🎵', wav: '🎵', ogg: '🎵', m4a: '🎵', flac: '🎵',
  };
  return map[ext] || '📄';
}

/** 文件 tab 项:exhibit + 所属功能 tab(用于标题/归属显示) + 物理文件唯一 key */
type FileTabItem = { exhibit: LobbyExhibit; owner: RightTabKey; fileKey: string };

/** 提取文件的物理唯一 key(同一文件在不同入口打开应视为同一文件)。
 * 优先取内部 uri 的 file_id,其次从预览/下载 URL 提取 bucket+file_id,最后回退 exhibit_id。 */
function getExhibitFileKey(exhibit: LobbyExhibit): string {
  const { uri, url } = exhibit.source;
  const raw = uri || url || '';
  const fs = raw.match(/gyra-fs:\/\/[^/]+\/([^?#]+)/);
  if (fs) return fs[1];
  const u = raw.match(/[?&]uri=([^&]+)/);
  if (u) {
    const decoded = decodeURIComponent(u[1]);
    const fs2 = decoded.match(/gyra-fs:\/\/[^/]+\/([^?#]+)/);
    if (fs2) return fs2[1];
    return decoded;
  }
  const bucket = raw.match(/[?&]bucket=([^&]+)/)?.[1];
  const fileId = raw.match(/[?&]file_id=([^&]+)/)?.[1];
  if (bucket && fileId) return `${bucket}/${fileId}`;
  const dl = raw.match(/\/serve\/file\/files\/([^/?#]+)\/([^/?#]+)/);
  if (dl) return `${dl[1]}/${dl[2]}`;
  return exhibit.exhibit_id;
}

/** 加入(或复用已存在)文件 tab,按物理文件 key 去重 */
function addFileTab(prev: FileTabItem[], exhibit: LobbyExhibit, owner: RightTabKey): FileTabItem[] {
  const fileKey = getExhibitFileKey(exhibit);
  if (prev.some((f) => f.fileKey === fileKey)) return prev;
  return [...prev, { exhibit, owner, fileKey }];
}

const OWNER_LABEL: Record<RightTabKey, string> = {
  execution: '执行过程',
  task_files: '任务文件',
  summary: '总结',
};

function deliverableToExhibit(file: WorkspaceDeliverableFile): LobbyExhibit {
  return {
    exhibit_id: `deliverable-${file.file_id}`,
    kind: (file.render_type === 'iframe' ? 'html' : file.render_type) as LobbyExhibit['kind'],
    title: file.file_name,
    source: {
      url: file.content_url || file.download_url,
      uri: file.object_path ? `gyra-fs://${file.object_path}` : undefined,
      mime_type: file.mime_type,
      file_size: file.file_size,
    },
    actions: ['preview', 'download'],
  };
}

function taskFileToExhibit(file: WorkspaceTaskFile): LobbyExhibit {
  const ext = file.file_name.split('.').pop()?.toLowerCase() || '';
  const kindMap: Record<string, LobbyExhibit['kind']> = {
    png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', svg: 'image', webp: 'image',
    mp4: 'video', mov: 'video', webm: 'video', avi: 'video', mkv: 'video',
    mp3: 'audio', wav: 'audio', ogg: 'audio', m4a: 'audio', flac: 'audio',
    pdf: 'pdf', md: 'markdown', markdown: 'markdown', html: 'html', htm: 'html',
    csv: 'table', xlsx: 'table', xls: 'table', pptx: 'slides', ppt: 'slides',
    py: 'code', js: 'code', jsx: 'code', ts: 'code', tsx: 'code', java: 'code', go: 'code', rs: 'code',
    sql: 'code', json: 'code', yaml: 'code', yml: 'code', xml: 'code', css: 'code', sh: 'code', vue: 'code',
    txt: 'text', log: 'text',
  };
  return {
    exhibit_id: `taskfile-${file.file_id}`,
    kind: kindMap[ext] || 'file',
    title: file.file_name,
    source: {
      url: file.preview_url || file.download_url,
      uri: file.oss_url || (file.object_path ? `gyra-fs://${file.object_path}` : undefined),
      mime_type: file.mime_type,
      file_size: file.file_size,
    },
    actions: ['preview', 'download'],
  };
}

/* ═══════════════════════════════════════════════════════════════
   步骤详情渲染:复用 vis_manus right panel 的专用渲染器
   (Terminal / 代码执行 notebook / SQL 查询表格 / HTML tabbed),
   markdown/vis 内容走 GPTVis 兜底,保持场景空间原有渲染链路。
   ═══════════════════════════════════════════════════════════════ */

type ManusLikeType = 'bash' | 'python' | 'sql' | 'html' | 'other';

/** action 精确映射(优先于关键词嗅探),与 vis_manus 协议 step-type 对齐 */
const ACTION_TYPE_MAP: Record<string, ManusLikeType> = {
  run_terminal_cmd: 'bash', execute_command: 'bash', run_command: 'bash', shell: 'bash',
  bash: 'bash', terminal: 'bash',
  execute_code: 'python', run_python: 'python', python_execute: 'python',
  execute_raw_sql: 'sql', sql_query: 'sql', run_sql: 'sql', query_database: 'sql',
  browser: 'html', browse: 'html', open_url: 'html', render_html: 'html',
};

/** action/类型 → 专用渲染器类别:action 精确映射为主,关键词嗅探兜底 */
function manusLikeType(step: WorkspaceExecutionStep): ManusLikeType {
  const action = (step.action || '').toLowerCase();
  for (const [k, v] of Object.entries(ACTION_TYPE_MAP)) {
    if (action === k || action.includes(k)) return v;
  }
  const key = `${action} ${step.type === 'thinking' ? '' : step.title || ''}`.toLowerCase();
  if (/\b(bash|shell|terminal)\b/.test(key)) return 'bash';
  if (/\b(python)\b/.test(key)) return 'python';
  if (/\b(sql|database)\b/.test(key)) return 'sql';
  if (/\bhtml\b|\bweb\b/.test(key)) return 'html';
  return 'other';
}

/** SQL 工具结果(JSON 文本) → SqlQueryRenderer 可消费的 sql_query 结构化输出 */
function toSqlQueryOutput(parsed: Record<string, unknown>): ManusExecutionOutput | null {
  const normalized: Record<string, unknown> = {
    sql: '', db_name: '', db_type: '', page: 1, page_size: 0, has_more: false,
    ...parsed,
  };
  // 错误交给调用方错误分支处理;其余(含「成功但无结果/无列」)统一以 SQL 组件展示,
  // 保证 SQL 与返回文本可读,不再因缺列/缺 raw_result 静默降级为通用文本
  if (normalized.error) return null;
  return { output_type: 'sql_query', content: normalized };
}

/** 通用 JSON 结果 → table/error/image/video 等结构化输出 */
function toStructuredOutput(parsed: Record<string, unknown>): ManusExecutionOutput | null {
  if (typeof parsed.error === 'string' && parsed.error.trim()) {
    return { output_type: 'error', content: parsed.error };
  }
  for (const k of ['image_url', 'image', 'screenshot', 'screenshot_url']) {
    const v = parsed[k];
    if (typeof v === 'string' && /^https?:\/\//.test(v)) return { output_type: 'image', content: v };
  }
  for (const k of ['video_url', 'video']) {
    const v = parsed[k];
    if (typeof v === 'string' && /^https?:\/\//.test(v)) return { output_type: 'video', content: v };
  }
  for (const k of ['html', 'html_content', 'page_html']) {
    const v = parsed[k];
    if (typeof v === 'string' && /<\s*\w+[^>]*>/.test(v)) return { output_type: 'html', content: v };
  }
  for (const k of ['rows', 'data', 'records', 'result']) {
    const v = parsed[k];
    if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object' && v[0] !== null) {
      return { output_type: 'table', content: JSON.stringify(v) };
    }
  }
  return null;
}

/** 解析步骤原始输出:支持纯 JSON(对象/数组)与 ```lang\n{...}\n``` 围栏包裹的 JSON。
 *  execute_raw_sql / execute_sql 等工具以 d-sql-query VIS 围栏返回结果,须剥壳提取结构化数据。
 *  兼容被 _MAX_OUTPUT_CHARS 等截断的围栏:缺闭合 ``` 时也尝试剥掉首行围栏标记,
 *  并对截断的 JSON 提取最长的合法对象/数组前缀,避免整段降级为裸 JSON 渲染。 */
function parseOutputJson(s: string): unknown {
  let body = (s || '').trim();
  // 剥掉 ```lang 围栏首行(闭合 ``` 可能因截断缺失,不能用 endsWith 判定)
  if (body.startsWith('```')) {
    const newlineIdx = body.indexOf('\n');
    if (newlineIdx === -1) return null;
    body = body.slice(newlineIdx + 1).replace(/\n```\s*$/, '');
  }
  body = body.trim();
  if (!body) return null;
  if (!(body.startsWith('{') || body.startsWith('['))) return null;
  try {
    return JSON.parse(body);
  } catch {
    // 截断 JSON(缺尾 } / ]):提取最长的合法对象/数组前缀,尽量保留能恢复的字段
    const open = body[0];
    const close = open === '{' ? '}' : ']';
    let depth = 0;
    let inStr = false;
    let esc = false;
    for (let i = 0; i < body.length; i++) {
      const ch = body[i];
      if (esc) { esc = false; continue; }
      if (ch === '\\') { esc = true; continue; }
      if (ch === '"') { inStr = !inStr; continue; }
      if (inStr) continue;
      if (ch === open) depth++;
      else if (ch === close) {
        depth--;
        if (depth === 0) {
          try { return JSON.parse(body.slice(0, i + 1)); } catch { return null; }
        }
      }
    }
    return null;
  }
}

/** 剥离 ```lang\n...\n``` 围栏外壳,只保留正文,供 raw_result 可读展示。
 *  兼容缺闭合 ``` 的截断围栏:去掉首行 lang 标记即可。 */
function stripVisFence(s: string): string {
  const body = (s || '').trim();
  if (!body.startsWith('```')) return body;
  const newlineIdx = body.indexOf('\n');
  if (newlineIdx === -1) return body;
  return body.slice(newlineIdx + 1).replace(/\n```\s*$/, '').trim();
}

/** 需要一律在内容区渲染执行入参的 ECP 语义工具(入参即查询/指标口径,不能折叠) */
const FORCE_PARAMS_ACTIONS = new Set(['search_semantics', 'execute_metric_query']);

/** 场景空间步骤 → vis_manus 渲染器可消费的 outputs */
function stepToOutputs(step: WorkspaceExecutionStep): ManusExecutionOutput[] {
  const outputs: ManusExecutionOutput[] = [];
  const type = manusLikeType(step);
  const ai = (step.action_input ?? {}) as Record<string, unknown>;
  const pickStr = (keys: string[]) =>
    keys.map((k) => (typeof ai[k] === 'string' ? (ai[k] as string) : undefined)).find((v) => v && v.trim().length > 0);

  if (type === 'bash') {
    const cmd = pickStr(['command', 'cmd']);
    const out = (step.output || '').trim();
    if (step.status === 'failed' && out) outputs.push({ output_type: 'error', content: out });
    else if (out) outputs.push({ output_type: 'text', content: out });
    if (!outputs.length) {
      if (step.status === 'failed') {
        // 失败但未捕获到输出:明确提示失败(而非空白「未返回可展示的输出」),
        // 便于用户感知这是个失败步骤;命令由 Terminal 头部单独展示不重复。
        outputs.push({ output_type: 'error', content: '工具执行失败，未返回输出' });
      } else if (cmd) {
        outputs.push({ output_type: 'text', content: '' });
      }
    }
    return outputs;
  }

  const codeKeys =
    type === 'sql' ? ['sql', 'query'] :
    type === 'python' ? ['code', 'script'] :
    // 普通工具:不把 query/content 这类入参误判成可执行代码(会导致按 python 块渲染)
    ['command', 'cmd', 'sql', 'code', 'script'];
  const codeLike = pickStr(codeKeys);
  if (codeLike && type !== 'sql') outputs.push({ output_type: 'code', content: codeLike });
  const visText = typeof step.vis === 'string' ? step.vis.trim() : '';
  // SQL 工具(execute_sql/execute_raw_sql)的 vis 是 d-sql-query 围栏,结构化数据已
  // 从 step.output 剥壳渲染成 SqlQueryRenderer 卡片;vis 再 push 成 markdown 会因该通道
  // 不经过 GPTVis fence 解析而把 ```d-sql-query{...}``` 原文裸渲染,故此处跳过。
  if (visText && type !== 'sql') outputs.push({ output_type: 'markdown', content: visText });
  const out = (step.output || '').trim();
  if (out) {
    let handled = false;
    const parsed = parseOutputJson(out);
    if (parsed && typeof parsed === 'object') {
      if (!Array.isArray(parsed)) {
        const rec = parsed as Record<string, unknown>;
        if (type === 'sql') {
          const sqlOut = toSqlQueryOutput(rec);
          if (sqlOut) {
            if (codeLike && typeof sqlOut.content === 'object' && !(sqlOut.content as Record<string, unknown>).sql) {
              (sqlOut.content as Record<string, unknown>).sql = codeLike;
            }
            outputs.push(sqlOut);
            handled = true;
          } else if (rec.error) {
            if (codeLike) outputs.push({ output_type: 'code', content: codeLike });
            outputs.push({ output_type: 'error', content: String(rec.error) });
            handled = true;
          }
        } else {
          const st = toStructuredOutput(rec);
          if (st) {
            if (st.output_type === 'error' && codeLike) outputs.push({ output_type: 'code', content: codeLike });
            outputs.push(st);
            handled = true;
          }
        }
      } else if (parsed.length > 0 && typeof parsed[0] === 'object' && parsed[0] !== null) {
        // 纯数组(如 [{...},{...}])→ 表格
        outputs.push({ output_type: 'table', content: out });
        handled = true;
      }
    }
    if (!handled) {
      if (type === 'sql' && codeLike) {
        // 执行成功但 output 非结构化 JSON(截断/「查询执行成功，无结果返回」等):
        // 仍以 SQL 组件渲染,头部展示 SQL(action_input.sql),结果区展示可读的原始文本。
        // raw_result 剥掉 ```d-sql-query 围栏外壳,避免把反引号/JSON 原文当正文裸展示。
        outputs.push({
          output_type: 'sql_query',
          content: { sql: codeLike, columns: [], rows: [], db_name: '', db_type: '', raw_result: stripVisFence(out) },
        });
      } else if (step.status === 'failed') {
        outputs.push({ output_type: 'error', content: out });
      } else {
        outputs.push({ output_type: 'markdown', content: out });
      }
    }
  }
  return outputs;
}

function toManusStatus(status: WorkspaceExecutionStep['status']): ManusStepStatus {
  if (status === 'running') return 'running';
  if (status === 'failed') return 'error';
  return 'completed';
}

/** 步骤详情:优先专用渲染器,无可渲染 outputs 时 GPTVis 兜底 */
function StepDetail({ step }: { step: WorkspaceExecutionStep }) {
  const visText = typeof step.vis === 'string' ? step.vis : '';
  const output = step.output || '';
  const hasVis = visText.trim().length > 0;
  const hasOutput = output.trim().length > 0;
  const hasInput = step.action_input && Object.keys(step.action_input).length > 0;
  const outputs = useMemo(() => stepToOutputs(step), [step]);
  const type = manusLikeType(step);
  const status = toManusStatus(step.status);
  const command = useMemo(() => {
    const ai = (step.action_input ?? {}) as Record<string, unknown>;
    if (typeof ai.command === 'string') return ai.command;
    if (typeof ai.cmd === 'string') return ai.cmd;
    return undefined;
  }, [step]);

  // 专用渲染器:仅当有可渲染输出时启用
  const renderer = useMemo(() => {
    // 预加载技能步骤:复用 SkillContentRenderer 渲染 <skill_content>(技能头部 +
    // SKILL.md 全文 + 文件预览),与 skill 工具调用结果的右侧展示体验一致。
    if (step.type === 'skill_loaded' && step.skill_xml) {
      return (
        <SkillContentRenderer
          outputs={[{ output_type: 'text', content: step.skill_xml }]}
          skillName={step.title}
        />
      );
    }
    if (!outputs.length) return null;
    switch (type) {
      case 'bash':
        return <TerminalRenderer command={command} outputs={outputs} status={status} title={`Terminal - ${step.title}`} />;
      case 'python':
        return <CodeExecutionRenderer outputs={outputs} language="python" />;
      case 'sql': {
        // 有结构化 sql_query 输出时走 SQL 专用渲染器(高亮 + 表格 + 分页),
        // 否则(如执行失败的 {error:...} JSON)退回通用 OutputRenderer
        const hasSqlQuery = outputs.some((o) => o.output_type === 'sql_query');
        return hasSqlQuery ? <SqlQueryRenderer outputs={outputs} /> : <OutputRenderer outputs={outputs} />;
      }
      case 'html': {
        // 有 html 内容时走「预览/源码」双 Tab,否则(如浏览器步骤只返回截图/文本)退回通用渲染
        const hasHtml = outputs.some((o) => o.output_type === 'html');
        return hasHtml ? <HtmlTabbedRenderer outputs={outputs} title={step.title} /> : <OutputRenderer outputs={outputs} />;
      }
      default:
        return <OutputRenderer outputs={outputs} />;
    }
  }, [type, outputs, command, status, step.title]);

  return (
    <div className="ws-simple-step flex-1 min-h-0">
      <div className="ws-simple-step__head">
        <span className={`ws-simple-step__status ws-simple-step__status--${step.status}`}>
          {step.status === 'running' ? '运行中' : step.status === 'failed' ? '失败' : '完成'}
        </span>
        {step.action && <span className="ws-simple-step__action">{step.action}</span>}
        {step.ts && <span className="ws-simple-step__ts">{step.ts}</span>}
      </div>
      {renderer}
      {/* 专用渲染器之外的内容(纯文本 output / 入参)兜底展示 */}
      {!renderer && (hasVis || hasOutput) && (
        <div className="ws-simple-step__vis">
          <GPTVis components={markdownComponents} {...markdownPlugins}>
            {preprocessLaTeX(hasVis ? visText : output)}
          </GPTVis>
        </div>
      )}
      {/* 工具执行入参:统一以 JSON 块渲染。专用渲染器存在时仅 ECP 语义类工具强制展示,
         其余仍按原逻辑(无渲染器)兜底,避免与终端/SQL 等已有入参展示重复 */}
      {hasInput && (!renderer || FORCE_PARAMS_ACTIONS.has((step.action || '').toLowerCase())) && (
        <div className="ws-simple-step__in">
          <div className="ws-simple-step__in-label">入参</div>
          <pre className="ws-simple-step__in-pre">
            {JSON.stringify(step.action_input, null, 2)}
          </pre>
        </div>
      )}
      {!renderer && !hasVis && !hasOutput && !hasInput && (
        <div className="ws-simple-right__empty" style={{ minHeight: 120 }}>
          <InboxOutlined />
          <div>{step.status === 'failed' ? '该步骤执行失败，无返回输出' : '该步骤暂无可展示内容'}</div>
        </div>
      )}
    </div>
  );
}

export function SceneSimpleWorkspace({
  view,
  running,
  error,
  switchingTask,
  convLoadError,
  retryLoadConv,
  agentIcon,
  agentName,
  modelName,
  onInteractionResume,
  onExit,
  inputSlot,
}: SceneSimpleWorkspaceProps) {
  const [rightTab, setRightTab] = useState<RightTabKey>('execution');
  // 已打开的文件 tab(一个文件一个 tab,窗口共享)
  const [openedFiles, setOpenedFiles] = useState<FileTabItem[]>([]);
  const [activeFileKey, setActiveFileKey] = useState<string | null>(null);
  // 用户手动选中的步骤(点击左侧胶囊内步骤后展示其执行结果)
  const [selectedStep, setSelectedStep] = useState<WorkspaceExecutionStep | null>(null);
  // 右侧工作空间预览:默认收起(对话流全宽,结果为主),点击步骤/文件触发展开,可手动收起
  const [rightOpen, setRightOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const deliverables = useMemo(() => view.deliverable_files ?? [], [view]);
  // 任务文件(含交付文件):后端 task_files 可能不含交付文件,按 file_id 补齐合并
  const taskFiles = useMemo(() => {
    const base = view.task_files ?? [];
    const missing = deliverables.filter((d) => !base.some((f) => f.file_id === d.file_id));
    if (!missing.length) return base;
    const converted: WorkspaceTaskFile[] = missing.map((d) => ({
      file_id: d.file_id,
      file_name: d.file_name,
      file_type: 'deliverable',
      file_size: d.file_size,
      mime_type: d.mime_type,
      preview_url: d.content_url,
      download_url: d.download_url,
      object_path: d.object_path,
    }));
    return [...base, ...converted];
  }, [view, deliverables]);
  // 面板视图自动切换不应反复覆盖用户手动选择:任务级只生效一次
  const panelHandledRef = useRef<string | null>(null);

  // 交付物就绪后默认打开第一个(仅自动一次;其余由用户点击触发)
  useEffect(() => {
    if (!deliverables.length) return;
    if (panelHandledRef.current) return;
    panelHandledRef.current = 'deliverable';
    const exhibit = deliverableToExhibit(deliverables[0]);
    setSelectedStep(null);
    setOpenedFiles((prev) => addFileTab(prev, exhibit, 'task_files'));
    setActiveFileKey(getExhibitFileKey(exhibit));
    setRightTab('task_files');
    setRightOpen(true);
  }, [deliverables]);

  // 自动跟随:流式期间右侧「执行过程」实时展示最新步骤的工具输出;
  // 用户点击某步骤后转为手动浏览,新步骤开跑时自动恢复跟随。
  const latestStep = useMemo(
    () => [...view.execution].reverse().find((s) => s.type === 'tool_call' || s.type === 'thinking' || s.type === 'skill_loaded') ?? null,
    [view.execution],
  );
  useEffect(() => {
    if (latestStep?.status === 'running') setSelectedStep(null);
  }, [latestStep?.id, latestStep?.status]);
  const displayStep = selectedStep ?? latestStep;

  // 步骤 prev/next 导航:按执行序列浏览历史步骤(问题溯源)
  const navSteps = useMemo(
    () => view.execution.filter((s) => s.type === 'tool_call' || s.type === 'thinking' || s.type === 'skill_loaded'),
    [view.execution],
  );
  const currentStepIndex = useMemo(
    () => (displayStep ? navSteps.findIndex((s) => s.id === displayStep.id) : -1),
    [navSteps, displayStep],
  );
  const navigateStep = (dir: -1 | 1) => {
    const base = currentStepIndex >= 0 ? currentStepIndex : navSteps.length - 1;
    const next = base + dir;
    if (next < 0 || next >= navSteps.length) return;
    setActiveFileKey(null);
    setSelectedStep(navSteps[next]);
    setRightTab('execution');
  };

  // panel_view:后端指示任务结束时自动切 tab(每个视图信号只消费一次,
  // 用户后续手动切 tab / 关预览不再被覆盖)
  useEffect(() => {
    const pv = view.panel_view;
    if (!pv || panelHandledRef.current === pv) return;
    if (pv === 'deliverable' && deliverables.length) {
      panelHandledRef.current = pv;
      const exhibit = deliverableToExhibit(deliverables[0]);
      setSelectedStep(null);
      setOpenedFiles((prev) => addFileTab(prev, exhibit, 'task_files'));
      setActiveFileKey(getExhibitFileKey(exhibit));
      setRightTab('task_files');
      setRightOpen(true);
    } else if (pv === 'summary' && view.summary) {
      panelHandledRef.current = pv;
      setRightTab('summary');
    } else if (pv === 'task_files' && taskFiles.length) {
      panelHandledRef.current = pv;
      setRightTab('task_files');
    }
  }, [view.panel_view, view.summary, deliverables, taskFiles]);
  const handleTabChange = (k: RightTabKey) => {
    setActiveFileKey(null);
    setRightTab(k);
  };

  const activeFile = openedFiles.find((f) => f.fileKey === activeFileKey) ?? null;

  const rightTitle = useMemo(() => {
    if (activeFile) return OWNER_LABEL[activeFile.owner] || '工作空间';
    if (selectedStep) return selectedStep.title || '步骤详情';
    if (rightTab === 'task_files') return '任务文件';
    if (rightTab === 'summary') return '总结';
    return displayStep?.title || '任务详情';
  }, [activeFile, selectedStep, rightTab, displayStep]);

  const handleOpenDeliverable = (file: WorkspaceDeliverableFile) => {
    const exhibit = deliverableToExhibit(file);
    setSelectedStep(null);
    setOpenedFiles((prev) => addFileTab(prev, exhibit, 'task_files'));
    setActiveFileKey(getExhibitFileKey(exhibit));
    setRightTab('task_files');
    setRightOpen(true);
  };

  const handleOpenTaskFile = (file: WorkspaceTaskFile) => {
    const exhibit = taskFileToExhibit(file);
    setSelectedStep(null);
    setOpenedFiles((prev) => addFileTab(prev, exhibit, 'task_files'));
    setActiveFileKey(getExhibitFileKey(exhibit));
    setRightTab('task_files');
    setRightOpen(true);
  };

  // 点击胶囊内步骤 → 触发展开右侧,展示该步骤的执行结果(专用渲染器优先)
  const handleStepClick = (step: WorkspaceExecutionStep) => {
    setActiveFileKey(null);
    setSelectedStep(step);
    setRightTab('execution');
    setRightOpen(true);
  };

  // 收起右侧:清空手动选择,回到全宽对话流(展开时自动跟随最新步骤)
  const collapseRight = () => {
    setRightOpen(false);
    setSelectedStep(null);
    setActiveFileKey(null);
  };

  const clearStepSelection = () => setSelectedStep(null);

  // 关闭指定文件 tab(按物理文件 key)
  const closeFileTab = (fileKey: string) => {
    setOpenedFiles((prev) => prev.filter((f) => f.fileKey !== fileKey));
    setActiveFileKey((prev) => (prev === fileKey ? null : prev));
  };

  const tabs: { key: RightTabKey; icon: React.ReactNode; label: string }[] = [
    { key: 'execution', icon: <CodeOutlined />, label: '执行过程' },
    { key: 'task_files', icon: <FolderOpenOutlined />, label: `任务文件${taskFiles.length ? ` ${taskFiles.length}` : ''}` },
    { key: 'summary', icon: <FileTextOutlined />, label: '总结' },
  ];

  const fileRow = (
    key: string,
    icon: string,
    name: string,
    meta: React.ReactNode,
    onOpen: () => void,
    onDownload?: (e: React.MouseEvent) => void,
  ) => (
    <div
      key={key}
      className="ws-simple-file-row"
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <span className="ws-simple-file-row__icon">{icon}</span>
      <div className="ws-simple-file-row__info">
        <div className="ws-simple-file-row__name">{name}</div>
        <div className="ws-simple-file-row__meta">{meta}</div>
      </div>
      {onDownload && (
        <Button type="text" size="small" icon={<DownloadOutlined />} onClick={onDownload} />
      )}
    </div>
  );

  return (
    <div className={`ws-simple-workspace${rightOpen ? ' ws-simple-workspace--right-open' : ''}`}>
      {/* 左侧:对话 feed(用户消息 → 执行胶囊 → 回答/交付),右侧收起时占满全宽 */}
      <section className="ws-simple-chat">
        <div className="ws-simple-chat__hd">
          <span className="ws-simple-chat__title">{agentName || '任务执行'}</span>
          {running && (
            <span className="ws-simple-chat__running">运行中</span>
          )}
          {onExit && (
            <Button type="text" size="small" icon={<CloseOutlined />} onClick={onExit} />
          )}
        </div>
        <div className="ws-simple-chat__flow">
          {error && (
            <div className="ws-simple-chat__error">
              <span>{error}</span>
              {retryLoadConv && (
                <Button size="small" onClick={retryLoadConv}>重试连接</Button>
              )}
            </div>
          )}
          {switchingTask ? (
            <div className="ws-simple-chat__loading"><Spin tip="切换任务对话中…" /></div>
          ) : convLoadError ? (
            <div className="ws-simple-chat__error">
              <span>会话加载失败:{convLoadError}</span>
              {retryLoadConv && <Button size="small" onClick={retryLoadConv}>重试</Button>}
            </div>
          ) : (
            <AgentWorkspaceRenderer
              view={view}
              running={running}
              onStepClick={handleStepClick}
              selectedStepId={selectedStep?.id ?? null}
              onDeliverableClick={handleOpenDeliverable}
              onInteractionResume={onInteractionResume}
              agentIcon={agentIcon}
              agentName={agentName}
              modelName={modelName}
            />
          )}
        </div>
        {/* 输入条:对话 feed 底部(与对话同列) */}
        {inputSlot && <div className="ws-simple-chat__input">{inputSlot}</div>}
      </section>

      {/* 右侧:工作空间预览。默认收起,点击左侧步骤/交付文件触发展开 */}
      {rightOpen && (
        <section className="ws-simple-right">
          <div className="ws-simple-right__hd">
            {/* 步骤 prev/next 导航(执行过程 tab 且存在步骤序列时) */}
            {rightTab === 'execution' && navSteps.length > 1 && (
              <div className="ws-simple-right__nav">
                <Button
                  type="text"
                  size="small"
                  icon={<LeftOutlined />}
                  disabled={currentStepIndex <= 0}
                  title="上一个步骤"
                  onClick={() => navigateStep(-1)}
                />
                <Button
                  type="text"
                  size="small"
                  icon={<RightOutlined />}
                  disabled={currentStepIndex < 0 || currentStepIndex >= navSteps.length - 1}
                  title="下一个步骤"
                  onClick={() => navigateStep(1)}
                />
              </div>
            )}
            <span className="ws-simple-right__title">{rightTitle}</span>
            <div className="ws-simple-right__acts">
              {selectedStep && (
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  title="关闭步骤详情"
                  onClick={clearStepSelection}
                />
              )}
              <Button type="text" size="small" icon={<ExpandOutlined />} title="全屏" />
              <Button
                type="text"
                size="small"
                icon={<DoubleRightOutlined />}
                title="收起工作空间"
                onClick={collapseRight}
              />
            </div>
          </div>

          {/* 下划线式 tab(对齐 vis_manus right panel 风格) */}
          <div className="ws-simple-right__tabs">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                className={`ws-rtab${rightTab === t.key && !activeFile ? ' ws-rtab--active' : ''}`}
                onClick={() => handleTabChange(t.key)}
              >
                <span className="ws-rtab__icon">{t.icon}</span>
                <span>{t.label}</span>
              </button>
            ))}
            {openedFiles.map(({ exhibit, owner, fileKey }) => {
              const isActive = activeFileKey === fileKey;
              return (
                <span
                  key={fileKey}
                  className={`ws-rtab ws-rtab--file${isActive ? ' ws-rtab--active' : ''}`}
                  onClick={() => {
                    setActiveFileKey(fileKey);
                    setRightTab(owner);
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setActiveFileKey(fileKey);
                      setRightTab(owner);
                    }
                  }}
                >
                  <span className="ws-rtab__icon">{getFileEmoji(exhibit.title)}</span>
                  <span>{exhibit.title}</span>
                  <button
                    type="button"
                    className="ws-rtab__close"
                    aria-label="关闭"
                    onClick={(e) => {
                      e.stopPropagation();
                      closeFileTab(fileKey);
                    }}
                  >
                    ×
                  </button>
                </span>
              );
            })}
          </div>

          <div className="ws-simple-right__scroll" ref={contentRef}>
            {activeFile ? (
              <div className="ws-simple-right__preview">
                <ExhibitHost exhibit={activeFile.exhibit} />
              </div>
            ) : (
              <>
            {!activeFile && rightTab === 'execution' && (
              <>
                {selectedStep || displayStep ? (
                  <StepDetail step={(selectedStep ?? displayStep)!} />
                ) : (
                  <div className="ws-simple-right__empty">
                    <InboxOutlined />
                    <div>{running ? 'Agent 正在执行…' : '点击左侧步骤查看详情'}</div>
                  </div>
                )}
              </>
            )}
            {!activeFile && rightTab === 'task_files' && (
              <>
                {taskFiles.length === 0 ? (
                  <div className="ws-simple-right__empty">
                    <InboxOutlined />
                    <div>暂无任务文件</div>
                  </div>
                ) : (
                  taskFiles.map((f) =>
                    fileRow(
                      f.file_id,
                      getFileEmoji(f.file_name),
                      f.file_name,
                      <>
                        {f.file_size > 0 && <span>{fmtSize(f.file_size)}</span>}
                        {f.file_type && <span className="ws-simple-file-row__type">{f.file_type}</span>}
                      </>,
                      () => handleOpenTaskFile(f),
                      (e) => {
                        e.stopPropagation();
                        const exhibit = taskFileToExhibit(f);
                        const url = resolveExhibitDownloadUrl(exhibit) || transformFileUrl(f.download_url || f.preview_url || f.oss_url || '');
                        if (url) {
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = f.file_name || 'download';
                          a.click();
                        }
                      },
                    ),
                  )
                )}
              </>
            )}
            {!activeFile && rightTab === 'summary' && (
              <>
                {view.summary ? (
                  <div className="ws-simple-right__summary">{view.summary}</div>
                ) : (
                  <div className="ws-simple-right__empty">
                    <InboxOutlined />
                    <div>任务完成后生成总结</div>
                  </div>
                )}
              </>
            )}
              </>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
