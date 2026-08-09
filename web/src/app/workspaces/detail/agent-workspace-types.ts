export interface WorkspaceArtifact {
  file_path: string;
  mime_type?: string;
  preview_url?: string;
}

/* ═══════════════════════════════════════════════════════════════
   大厅通用入驻内容协议(Lobby Exhibit)
   大厅容器是通用 Exhibit 宿主:一切可展示物抽象为 LobbyExhibit,
   前端按 kind 注册渲染器;新内容类型只加渲染器,不改协议。
   ═══════════════════════════════════════════════════════════════ */

/** 入驻内容类型 */
export type LobbyExhibitKind =
  | 'image'
  | 'video'
  | 'audio'
  | 'table'      // 表格:inline csv/json 或 xlsx/csv 文件
  | 'slides'     // PPT:单文件 HTML 幻灯片 / pdf / 图片序列
  | 'html'       // 富页面(沙箱 iframe)
  | 'pdf'
  | 'markdown'
  | 'code'
  | 'text'
  | 'chart'      // gpt-vis 图表 spec
  | 'data'       // 任意 JSON / kv
  | 'file';      // 兜底:仅下载

/** 内容来源:三者至少其一(inline 优先于 url/uri 渲染) */
export interface LobbyExhibitSource {
  /** gyra-fs:// 内部文件 */
  uri?: string;
  /** 外部或可访问 URL */
  url?: string;
  /** 内联内容(markdown/html/csv/json 文本) */
  inline?: string;
  mime_type?: string;
  file_size?: number;
}

/** 渲染提示(可选,缺省时前端按 kind 默认渲染) */
export interface LobbyExhibitRenderHints {
  /** 表格列定义;缺省从数据首行推断 */
  table?: { columns?: { key: string; title?: string; type?: 'string' | 'number' | 'boolean' }[] };
  /** 幻灯片渲染模式:html=单文件幻灯片;pdf=pdf 翻页;images=图片序列 */
  slides?: { mode?: 'html' | 'pdf' | 'images' };
  /** gpt-vis 图表 spec */
  chart?: Record<string, unknown>;
  /** 内容区建议高度(px) */
  height?: number;
}

/** 出处:哪个任务/步骤/Agent 产出 */
export interface LobbyExhibitProvenance {
  task_id?: number;
  step_id?: string;
  agent?: string;
  ts?: string;
}

export type LobbyExhibitAction = 'preview' | 'download' | 'open_external';

export interface LobbyExhibit {
  /** 唯一 ID,幂等更新(同 ID 新帧覆盖旧帧) */
  exhibit_id: string;
  kind: LobbyExhibitKind;
  title: string;
  source: LobbyExhibitSource;
  render_hints?: LobbyExhibitRenderHints;
  provenance?: LobbyExhibitProvenance;
  /** 可执行动作,缺省 ['preview','download'] */
  actions?: LobbyExhibitAction[];
}

export interface WorkspaceExecutionStep {
  id: string;
  type: 'tool_call' | 'thinking' | 'artifact' | 'delivery' | 'user' | 'task_created';
  title: string;
  status: 'running' | 'done' | 'failed';
  /** 时间戳(ISO 字符串),跨轮次合并时按此交错排序 */
  ts?: string | null;
  action?: string | null;
  action_input?: Record<string, unknown> | null;
  output?: string | null;
  artifact?: WorkspaceArtifact | null;
  vis?: unknown;
  /** 步骤关联的大厅入驻内容:点击步骤时大厅打开对应 Exhibit */
  exhibit?: LobbyExhibit | null;
  /** task_created 步骤:关联的任务信息 */
  task_id?: number;
  task_title?: string;
  task_status?: string;
  playbook_name?: string;
  triggered_by?: string;
}

export interface WorkspacePlanning {
  goal: string;
  steps: { id: string; title: string; status: 'pending' | 'running' | 'done' | 'failed' }[];
}

/** 交付文件(Agent 运行期间通过 deliver_file / create_file 标记) */
export interface WorkspaceDeliverableFile {
  file_id: string;
  file_name: string;
  mime_type?: string;
  file_size: number;
  content_url?: string;
  download_url?: string;
  object_path?: string;
  render_type:
    | 'iframe' | 'markdown' | 'code' | 'image' | 'pdf' | 'text' | 'video' | 'archive'
    | 'audio' | 'table' | 'slides' | 'chart';
}

/** 任务文件(运行期间产生的所有文件,含交付文件) */
export interface WorkspaceTaskFile {
  file_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  mime_type?: string;
  oss_url?: string;
  preview_url?: string;
  download_url?: string;
  description?: string;
  created_at?: string;
  object_path?: string;
}

export type WorkspacePanelView = 'execution' | 'deliverable' | 'summary' | 'task_files';

/** 异步子 agent 任务看板卡片项（与后端 SubagentBoard 看板同构） */
export interface WorkspaceSubagentItem {
  sub_conv_id: string;
  agent_name?: string;
  agent_display_name?: string;
  task?: string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'awaiting_authorization';
  mode?: string;
  authorization?: string;
  params?: Record<string, any>;
  progress?: number;
  steps?: string[];
  artifacts?: Array<{ name?: string; type?: string; url?: string; mime_type?: string }>;
  /** 子 Agent 回复文本(成功结果摘要 / 失败原因)。 */
  result?: string;
}

export interface WorkspaceView {
  planning: WorkspacePlanning | null;
  execution: WorkspaceExecutionStep[];
  summary: string | null;
  /** 交付文件列表(类似 vis manus) */
  deliverable_files?: WorkspaceDeliverableFile[];
  /** 任务文件列表(含交付文件) */
  task_files?: WorkspaceTaskFile[];
  /** 面板视图:任务结束时后端指示自动切换到哪个 tab */
  panel_view?: WorkspacePanelView;
  /** 大厅入驻内容(全量推送,按 exhibit_id 幂等更新) */
  lobby_exhibits?: LobbyExhibit[];
  /** 异步子 agent 任务看板卡片项(无子任务时为空数组) */
  subagents?: WorkspaceSubagentItem[];
}

export interface PlaybookCommand {
  playbook_id: number;
  playbook_name: string;
}

/** 对话中选用的技能(与 SelectedSkill 结构一致,避免依赖 context 模块) */
export interface SkillRef {
  skill_code: string;
  name: string;
  description?: string;
  type?: string;
  icon?: string;
  author?: string;
  version?: string;
}

export interface AgentWorkspaceInputHandle {
  focus: () => void;
  insertText: (text: string) => void;
}