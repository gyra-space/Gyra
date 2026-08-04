'use client';

import { useState } from 'react';
import { GPTVis } from '@antv/gpt-vis';
import {
  LoadingOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  RightOutlined,
  DownOutlined,
  BulbOutlined,
  DesktopOutlined,
  FileOutlined,
  FileTextOutlined,
  FileSearchOutlined,
  EditOutlined,
  ConsoleSqlOutlined,
  SearchOutlined,
  CodeOutlined,
  PlayCircleOutlined,
  FolderOpenOutlined,
  DownloadOutlined,
  RocketOutlined,
  AimOutlined,
} from '@ant-design/icons';
import { Tooltip } from 'antd';
import markdownComponents, { markdownPlugins, preprocessLaTeX } from '@/components/chat/chat-content-components/config';
import { transformFileUrl } from '@/utils';
import type {
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspaceTaskFile,
  WorkspaceView,
} from './agent-workspace-types';

/** 长文本默认折叠的行数阈值(按字符粗估) */
const CLAMP_CHARS = 160;

/** 状态圆点 chip:18px 柔色底 + 语义 glyph,running 带脉冲光晕(CSS 实现) */
function StatusChip({ status }: { status: WorkspaceExecutionStep['status'] }) {
  if (status === 'running') {
    return (
      <span className="ws-status-chip ws-status-chip--running">
        <LoadingOutlined spin />
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="ws-status-chip ws-status-chip--failed">
        <CloseCircleFilled />
      </span>
    );
  }
  return (
    <span className="ws-status-chip ws-status-chip--done">
      <CheckCircleFilled />
    </span>
  );
}

/** 根据工具 action / title 匹配专属图标,参考 vis_manus 的 type-icon 映射 */
function getToolStepIcon(action?: string | null, title?: string) {
  const key = `${action || ''} ${title || ''}`.toLowerCase();
  if (/\b(read|file_search|file_read)\b|读取|搜索文件/.test(key)) {
    return <FileSearchOutlined className="text-emerald-500" />;
  }
  if (/\b(edit|write|modify|update)\b|编辑|写入|修改/.test(key)) {
    return <EditOutlined className="text-amber-500" />;
  }
  if (/\b(bash|shell|sh|terminal)\b|终端|命令行/.test(key)) {
    return <ConsoleSqlOutlined className="text-purple-500" />;
  }
  if (/\b(grep|glob|search|find)\b|搜索|查找/.test(key)) {
    return <SearchOutlined className="text-cyan-500" />;
  }
  if (/\b(python|py)\b|python/.test(key)) {
    return <CodeOutlined className="text-blue-500" />;
  }
  if (/\b(html|htm|web)\b|html/.test(key)) {
    return <CodeOutlined className="text-orange-500" />;
  }
  if (/\b(sql|query|db|database)\b|sql|数据库/.test(key)) {
    return <ConsoleSqlOutlined className="text-emerald-600" />;
  }
  if (/\b(task|todo|job)\b|任务/.test(key)) {
    return <PlayCircleOutlined className="text-indigo-500" />;
  }
  if (/\b(skill|plugin)\b|技能|插件/.test(key)) {
    return <CodeOutlined className="text-violet-500" />;
  }
  return <FileTextOutlined className="text-gray-400" />;
}

/** 用户消息气泡(manus left panel 风格) */
function UserBubble({ text }: { text: string }) {
  return (
    <div className="ws-step-user">
      <div className="ws-step-user__bubble">{text}</div>
    </div>
  );
}

/** 空态引导:图标 tile + 标题 + 提示 */
function EmptyState() {
  return (
    <div className="ws-agent-renderer__empty">
      <span className="ws-agent-renderer__empty-icon">
        <DesktopOutlined />
      </span>
      <span className="ws-agent-renderer__empty-title">Agent 就绪</span>
      <span className="ws-agent-renderer__empty-hint">输入指令，开始执行任务</span>
    </div>
  );
}

/** 工具步骤行:类型 tile + 标题 + 状态 chip + chevron,点击进场景空间看详情 */
function ToolStepRow({
  step,
  onStepClick,
}: {
  step: WorkspaceExecutionStep;
  onStepClick?: (s: WorkspaceExecutionStep) => void;
}) {
  return (
    <div
      className={`ws-step ws-step--tool${step.status === 'running' ? ' ws-step--running' : ''}${step.status === 'failed' ? ' ws-step--failed' : ''}`}
      role={onStepClick ? 'button' : undefined}
      tabIndex={onStepClick ? 0 : undefined}
      onClick={() => onStepClick?.(step)}
      onKeyDown={(e) => {
        if (onStepClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onStepClick(step);
        }
      }}
    >
      <span className="ws-step__badge">
        {getToolStepIcon(step.action, step.title)}
      </span>
      <span className="ws-step__title">{step.title}</span>
      <StatusChip status={step.status} />
      {onStepClick && <RightOutlined className="ws-step__chevron" />}
    </div>
  );
}

/** 思考/阶段回复:弱化内联文本,过长折叠 */
function ThinkingBlock({ step }: { step: WorkspaceExecutionStep }) {
  const [expanded, setExpanded] = useState(false);
  const text = step.output || '';
  const needClamp = text.length > CLAMP_CHARS;
  return (
    <div className={`ws-step-think${step.status === 'running' ? ' ws-step-think--running' : ''}`}>
      <div className="ws-step-think__head">
        <span className="ws-step-think__badge">
          <BulbOutlined />
        </span>
        <span className="ws-step-think__label">{step.title}</span>
        {step.status === 'running' && (
          <span className="ws-status-chip ws-status-chip--running">
            <LoadingOutlined spin />
          </span>
        )}
      </div>
      <div className={`ws-step-think__text${needClamp && !expanded ? ' ws-step-think__text--clamp' : ''}`}>
        {text}
      </div>
      {needClamp && (
        <button type="button" className="ws-step-think__toggle" onClick={() => setExpanded((v) => !v)}>
          {expanded ? '收起' : '展开全部'}
          <DownOutlined className={`ws-step-think__toggle-icon${expanded ? ' ws-step-think__toggle-icon--up' : ''}`} />
        </button>
      )}
    </div>
  );
}

/** 任务计划卡片:badge + goal + 进度计数 + hairline 进度条 + rail 步骤节点 */
function PlanningCard({ planning }: { planning: NonNullable<WorkspaceView['planning']> }) {
  const total = planning.steps.length;
  const done = planning.steps.filter((s) => s.status === 'done').length;
  const hasFailed = planning.steps.some((s) => s.status === 'failed');
  const allDone = total > 0 && done === total;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="ws-plan">
      <div className="ws-plan__head">
        <span className="ws-plan__badge">
          <AimOutlined />
        </span>
        <div className="ws-plan__head-text">
          <div className="ws-plan__label">任务计划</div>
          <div className="ws-plan__goal">{planning.goal}</div>
        </div>
        <span className={`ws-plan__count${allDone ? ' ws-plan__count--done' : ''}`}>
          {done}/{total}
        </span>
      </div>
      <div className="ws-plan__bar">
        <i
          className={`ws-plan__bar-fill${allDone ? ' ws-plan__bar-fill--done' : ''}${hasFailed ? ' ws-plan__bar-fill--failed' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="ws-plan__steps">
        {planning.steps.map((s) => (
          <div key={s.id} className={`ws-plan-step ws-plan-step--${s.status}`}>
            <span className="ws-plan-step__node" />
            <span className="ws-plan-step__title">{s.title}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const TASK_STATUS_LABEL: Record<string, string> = {
  running: '执行中',
  pending_trigger: '等待触发',
  delivered: '已交付',
  awaiting_human: '待介入',
  closed: '已关闭',
  failed: '已失败',
  done: '已完成',
};

const TRIGGER_LABEL: Record<string, string> = {
  manual: '手动',
  timer: '定时',
  webhook: 'Webhook',
  alert: '告警',
};

/** 任务卡片:Agent 创建任务后在对话记录中渲染,点击进入任务对话 */
function TaskCreatedCard({
  step,
  onTaskClick,
}: {
  step: WorkspaceExecutionStep;
  onTaskClick?: (taskId: number) => void;
}) {
  const taskId = step.task_id;
  const rawStatus = step.task_status || step.status;
  const statusLabel = TASK_STATUS_LABEL[rawStatus] || rawStatus;
  const isRunning = rawStatus === 'running' || rawStatus === 'pending_trigger';
  const isFailed = rawStatus === 'failed';
  const triggerLabel = step.triggered_by ? (TRIGGER_LABEL[step.triggered_by] || step.triggered_by) : null;
  const clickable = !!onTaskClick && !!taskId;

  return (
    <div
      className={`ws-task-card${isRunning ? ' ws-task-card--running' : ''}${isFailed ? ' ws-task-card--failed' : ''}`}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={() => clickable && onTaskClick!(taskId!)}
      onKeyDown={(e) => {
        if (clickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onTaskClick!(taskId!);
        }
      }}
    >
      <span className="ws-task-card__status-icon">
        {isRunning ? (
          <span className="ws-status-chip ws-status-chip--running"><LoadingOutlined spin /></span>
        ) : isFailed ? (
          <span className="ws-status-chip ws-status-chip--failed"><CloseCircleFilled /></span>
        ) : (
          <span className="ws-status-chip ws-status-chip--done"><CheckCircleFilled /></span>
        )}
      </span>
      <span className="ws-task-card__badge">
        <RocketOutlined />
      </span>
      <div className="ws-task-card__info">
        <div className="ws-task-card__title">{step.task_title || step.title}</div>
        <div className="ws-task-card__meta">
          {taskId && <span className="ws-task-card__id">#{taskId}</span>}
          {step.playbook_name && <span className="ws-task-card__playbook">{step.playbook_name}</span>}
          {triggerLabel && <span className="ws-task-card__trigger">{triggerLabel}</span>}
          <span className={`ws-task-card__status ws-task-card__status--${rawStatus}`}>{statusLabel}</span>
        </div>
      </div>
      {clickable && <RightOutlined className="ws-task-card__chevron" />}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   File helpers
   ═══════════════════════════════════════════════════════════════ */

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
};

const getFileIcon = (fileName: string): string => {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  const map: Record<string, string> = {
    html: '🌐', htm: '🌐', md: '📝', pdf: '📕',
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', svg: '🖼️', webp: '🖼️',
    py: '🐍', js: '📜', ts: '📜', java: '☕', go: '🔵', rs: '🦀',
    sql: '🗄️', csv: '📊', xlsx: '📊', xls: '📊',
    json: '📋', yaml: '📋', yml: '📋', xml: '📋',
    txt: '📄', log: '📄', zip: '📦', tar: '📦', gz: '📦',
    mp4: '🎬', mov: '🎬', webm: '🎬', avi: '🎬', mkv: '🎬',
  };
  return map[ext] || '📄';
};

const getFileTypeColor = (fileType: string): string => {
  const map: Record<string, string> = {
    deliverable: 'bg-blue-50 text-blue-600',
    conclusion: 'bg-green-50 text-green-600',
    tool_output: 'bg-purple-50 text-purple-600',
    write_file: 'bg-amber-50 text-amber-600',
  };
  return map[fileType] || 'bg-gray-50 text-gray-500';
};

/** 任务文件 → 交付文件 render_type 推断(点击后在中间容器按此渲染) */
const inferTaskFileRenderType = (
  file: WorkspaceTaskFile,
): WorkspaceDeliverableFile['render_type'] => {
  const ext = file.file_name.split('.').pop()?.toLowerCase() || '';
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) return 'image';
  if (['mp4', 'mov', 'webm', 'avi', 'mkv'].includes(ext)) return 'video';
  if (['mp3', 'wav', 'ogg', 'm4a', 'flac'].includes(ext)) return 'audio';
  if (ext === 'pdf') return 'pdf';
  if (ext === 'md' || ext === 'markdown') return 'markdown';
  if (ext === 'html' || ext === 'htm') return 'iframe';
  if (['csv', 'xlsx', 'xls'].includes(ext)) return 'table';
  if (['pptx', 'ppt'].includes(ext)) return 'slides';
  if (['py', 'js', 'jsx', 'ts', 'tsx', 'java', 'go', 'rs', 'sql', 'json', 'yaml', 'yml', 'xml', 'css', 'sh', 'vue'].includes(ext)) return 'code';
  if (['txt', 'log'].includes(ext)) return 'text';
  return 'archive';
};

/** 解析任务文件预览 URL */
const resolveTaskFilePreviewUrl = (file: WorkspaceTaskFile): string | null => {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  if (file.oss_url?.startsWith('gyra-fs://')) {
    return `${apiBaseUrl}/api/v2/serve/file/files/preview?uri=${encodeURIComponent(file.oss_url)}`;
  }
  if (file.preview_url?.startsWith('http')) return transformFileUrl(file.preview_url);
  if (file.object_path) {
    return `${apiBaseUrl}/api/oss/getFileByFileName?fileName=${encodeURIComponent(file.object_path)}`;
  }
  return null;
};

/** 解析任务文件下载 URL */
const resolveTaskFileDownloadUrl = (file: WorkspaceTaskFile): string | null => {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  const raw = file.download_url || file.oss_url;
  if (!raw) return null;
  if (raw.startsWith('http')) return transformFileUrl(raw);
  if (raw.startsWith('gyra-fs://')) return transformFileUrl(raw);
  if (raw.startsWith('/')) return `${apiBaseUrl}${raw}`;
  if (file.object_path) {
    return `${apiBaseUrl}/api/oss/getFileByFileName?fileName=${encodeURIComponent(file.object_path)}`;
  }
  return null;
};

const handleTaskFileDownload = (file: WorkspaceTaskFile) => {
  const url = resolveTaskFileDownloadUrl(file);
  if (!url) return;
  const a = document.createElement('a');
  a.href = url;
  a.download = file.file_name || 'download';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

/* ═══════════════════════════════════════════════════════════════
   Task files strip — 一行折叠开关,默认收起;展开后点击在中间容器预览
   ═══════════════════════════════════════════════════════════════ */

function TaskFilesStrip({
  files,
  onOpen,
}: {
  files: WorkspaceTaskFile[];
  onOpen?: (file: WorkspaceTaskFile) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const totalSize = files.reduce((sum, f) => sum + (f.file_size || 0), 0);

  return (
    <div className="ws-taskfiles">
      <button type="button" className="ws-taskfiles__toggle" onClick={() => setExpanded((v) => !v)}>
        <FolderOpenOutlined className="ws-taskfiles__toggle-icon" />
        <span>任务文件</span>
        <span className="ws-taskfiles__count">{files.length}</span>
        {totalSize > 0 && <span className="ws-taskfiles__size">{formatFileSize(totalSize)}</span>}
        <DownOutlined className={`ws-taskfiles__chevron${expanded ? ' ws-taskfiles__chevron--up' : ''}`} />
      </button>
      {expanded && (
        <div className="ws-taskfiles__list">
          {files.map((file) => {
            const canOpen = !!onOpen && !!resolveTaskFilePreviewUrl(file);
            const downloadUrl = resolveTaskFileDownloadUrl(file);
            return (
              <div
                key={file.file_id}
                className={`ws-renderer__file-item${canOpen ? ' ws-renderer__file-item--openable' : ''}`}
                role={canOpen ? 'button' : undefined}
                tabIndex={canOpen ? 0 : undefined}
                onClick={() => canOpen && onOpen!(file)}
                onKeyDown={(e) => {
                  if (canOpen && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    onOpen!(file);
                  }
                }}
              >
                <span className="ws-renderer__file-icon">{getFileIcon(file.file_name)}</span>
                <div className="ws-renderer__file-info">
                  <div className="ws-renderer__file-name">{file.file_name}</div>
                  <div className="ws-renderer__file-meta">
                    {file.file_size > 0 && <span>{formatFileSize(file.file_size)}</span>}
                    {file.file_type && (
                      <span className={`ws-renderer__file-type ${getFileTypeColor(file.file_type)}`}>
                        {file.file_type}
                      </span>
                    )}
                  </div>
                </div>
                {downloadUrl && (
                  <Tooltip title="下载">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleTaskFileDownload(file); }}
                      className="ws-renderer__file-action"
                    >
                      <DownloadOutlined />
                    </button>
                  </Tooltip>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Main component — 单一 feed:计划 → 步骤 → 摘要 → 交付文件卡片
   (交付/任务文件点击后在中间容器区域打开,不再使用 tab 切换)
   ═══════════════════════════════════════════════════════════════ */

export interface AgentWorkspaceRendererProps {
  view: WorkspaceView;
  onStepClick?: (step: WorkspaceExecutionStep) => void;
  /** 点击交付文件卡片:在中间容器渲染文件内容 */
  onDeliverableClick?: (file: WorkspaceDeliverableFile) => void;
  /** 点击任务卡片:进入任务对话 */
  onTaskClick?: (taskId: number) => void;
}

export function AgentWorkspaceRenderer({ view, onStepClick, onDeliverableClick, onTaskClick }: AgentWorkspaceRendererProps) {
  const deliverable_files = view.deliverable_files ?? [];
  const task_files = view.task_files ?? [];
  const hasDeliverables = deliverable_files.length > 0;
  // 任务文件含交付文件,过滤掉已在交付卡片中展示的,避免重复
  const extraTaskFiles = task_files.filter(
    (f) => !deliverable_files.some((d) => d.file_id === f.file_id),
  );

  // 任务文件点击 → 适配为交付文件形状,在中间容器预览
  const handleTaskFileOpen = onDeliverableClick
    ? (file: WorkspaceTaskFile) => {
        const previewUrl = resolveTaskFilePreviewUrl(file);
        if (!previewUrl) return;
        onDeliverableClick({
          file_id: file.file_id,
          file_name: file.file_name,
          mime_type: file.mime_type,
          file_size: file.file_size,
          content_url: previewUrl,
          download_url: resolveTaskFileDownloadUrl(file) || undefined,
          render_type: inferTaskFileRenderType(file),
        });
      }
    : undefined;

  return (
    <div className="ws-agent-renderer">
      {view.planning && <PlanningCard planning={view.planning} />}
      {view.execution.map((step) => {
        if (step.type === 'user') {
          return <UserBubble key={step.id} text={step.output || ''} />;
        }
        if (step.type === 'thinking') {
          return <ThinkingBlock key={step.id} step={step} />;
        }
        if (step.type === 'task_created') {
          return <TaskCreatedCard key={step.id} step={step} onTaskClick={onTaskClick} />;
        }
        return <ToolStepRow key={step.id} step={step} onStepClick={onStepClick} />;
      })}
      {!view.execution.length && !view.summary && <EmptyState />}
      {view.summary && (
        <div className="ws-agent-renderer__summary">
          {/* @ts-ignore rehypePlugins type mismatch is pre-existing repo-wide (see chat-detail-content.tsx) */}
          <GPTVis components={markdownComponents} {...markdownPlugins}>
            {preprocessLaTeX(view.summary)}
          </GPTVis>
        </div>
      )}
      {/* 执行记录结尾:交付文件卡片,点击在中间容器打开 */}
      {hasDeliverables && onDeliverableClick && (
        <div className="ws-agent-renderer__deliverables">
          <div className="ws-agent-renderer__deliverables-head">
            <span className="ws-agent-renderer__deliverables-badge">
              <FileOutlined />
            </span>
            <span className="ws-agent-renderer__deliverables-title">交付文件</span>
            <span className="ws-agent-renderer__deliverables-count">{deliverable_files.length}</span>
          </div>
          {deliverable_files.map((file) => {
            const downloadUrl = file.download_url || file.content_url;
            return (
              <div
                key={file.file_id}
                className="ws-deliverable-card"
                role="button"
                tabIndex={0}
                onClick={() => onDeliverableClick(file)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onDeliverableClick(file); } }}
              >
                <span className="ws-deliverable-card__icon">{getFileIcon(file.file_name)}</span>
                <div className="ws-deliverable-card__info">
                  <div className="ws-deliverable-card__name">{file.file_name}</div>
                  <div className="ws-deliverable-card__meta">
                    {file.file_size > 0 && <span>{formatFileSize(file.file_size)}</span>}
                    <span className="ws-deliverable-card__type">{file.render_type}</span>
                  </div>
                </div>
                {downloadUrl && (
                  <Tooltip title="下载">
                    <button
                      type="button"
                      className="ws-deliverable-card__download"
                      aria-label="下载"
                      onClick={(e) => {
                        e.stopPropagation();
                        const a = document.createElement('a');
                        a.href = transformFileUrl(downloadUrl);
                        a.download = file.file_name || 'download';
                        a.style.display = 'none';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                      }}
                    >
                      <DownloadOutlined />
                    </button>
                  </Tooltip>
                )}
                <RightOutlined className="ws-deliverable-card__chevron" />
              </div>
            );
          })}
        </div>
      )}
      {/* 其余任务文件:一行折叠开关,零视觉噪音 */}
      {extraTaskFiles.length > 0 && (
        <TaskFilesStrip files={extraTaskFiles} onOpen={handleTaskFileOpen} />
      )}
    </div>
  );
}
