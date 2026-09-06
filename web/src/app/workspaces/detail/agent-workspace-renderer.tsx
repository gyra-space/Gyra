'use client';

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { GPTVis } from '@antv/gpt-vis';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  RightOutlined,
  DownOutlined,
  DesktopOutlined,
  FileOutlined,
  FolderOpenOutlined,
  DownloadOutlined,
  LoadingOutlined,
  RocketOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';
import { Tooltip } from 'antd';
import markdownComponents, { markdownPlugins, preprocessLaTeX } from '@/components/chat/chat-content-components/config';
import { resolveFileDownloadUrl, transformFileUrl } from '@/utils';
import { useCallDetail } from '@/components/chat/call-detail/CallDetailProvider';
import { AgentAvatar } from '@/components/common/agent-avatar';
import UserAvatar from '@/components/common/user-avatar';
import { STORAGE_USERINFO_KEY } from '@/utils/constants/index';
import type { UserInfoResponse } from '@/types/userinfo';
import VisSubagentBoard from '@/components/chat/chat-content-components/VisComponents/VisSubagentBoard';
import { SceneAskUserCard, extractAskUserData } from './scene-ask-user-card';
import { statusLabel } from './scene-task-rail';
import { StepFlow, RoundProcessBar } from './step-flow';
import { buildExecutionPhases, usePlanningTimeline } from './use-execution-phases';
import {
  openAttachmentPreview,
  makePreviewPayload,
} from '@/components/chat/input/attachment-preview';
import { groupDeliverablesByRound, groupTaskFilesByRound, splitRounds } from './deliverable-rounds';
import type {
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspaceTaskFile,
  WorkspaceUserAttachment,
  WorkspaceView,
} from './agent-workspace-types';

/** 进入执行胶囊归组的步骤类型(user/answer/task_created 等由 feed 直接渲染) */
const CAPSULE_STEP_TYPES = new Set(['tool_call', 'thinking', 'artifact', 'delivery', 'skill_loaded', 'skill_published']);

/** 轮次无归属文件时复用同一空数组,避免每次渲染新建数组触发子组件无谓更新 */
const NO_DELIVERABLES: WorkspaceDeliverableFile[] = [];
const NO_TASK_FILES: WorkspaceTaskFile[] = [];

/** 用户消息气泡(manus left panel 风格):气泡(文本+附件) + 用户头像(右侧) */
function UserBubble({
  text,
  attachments,
  avatarUrl,
  name,
}: {
  text: string;
  attachments?: WorkspaceUserAttachment[] | null;
  avatarUrl?: string | null;
  name?: string | null;
  onAttachmentsClick?: () => void;
}) {
  const files = (attachments || []).filter((a) => a && a.url);
  const images = files.filter((a) => (a.mime_type || '').startsWith('image'));
  const docs = files.filter((a) => !(a.mime_type || '').startsWith('image'));
  return (
    <div className="ws-step-user">
      <div className="ws-step-user__bubble">
        {text}
        {files.length > 0 && (
          <div className="ws-step-user__attachments">
            {images.map((a, i) => (
              <button
                type="button"
                key={`${a.url}-${i}`}
                className="ws-step-user__attachment-img"
                onClick={() =>
                  openAttachmentPreview(
                    makePreviewPayload(a.name, a.url, { mimeType: a.mime_type })
                  )
                }
                title={`预览 ${a.name}`}
              >
                <img src={transformFileUrl(a.url)} alt={a.name} loading="lazy" />
              </button>
            ))}
            {docs.map((a, i) => (
              <button
                type="button"
                key={`${a.url}-${i}`}
                className="ws-step-user__attachment-file"
                onClick={() =>
                  openAttachmentPreview(
                    makePreviewPayload(a.name, a.url, { mimeType: a.mime_type })
                  )
                }
                title={`预览 ${a.name}`}
              >
                <FileOutlined />
                <span className="ws-step-user__attachment-name">{a.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <span className="ws-step-user__avatar">
        <UserAvatar avatarUrl={avatarUrl} name={name} size={28} />
      </span>
    </div>
  );
}

/** Agent 最终回复:markdown 回复(头像/名称由轮次头部统一展示,不重复) */
function AnswerBlock({ step }: { step: WorkspaceExecutionStep }) {
  const text = step.output || '';
  if (!text) return null;
  return (
    <div className="ws-step-answer">
      <div className="ws-step-answer__content">
        <GPTVis components={markdownComponents} {...markdownPlugins}>
          {preprocessLaTeX(text)}
        </GPTVis>
      </div>
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

const TRIGGER_LABEL: Record<string, string> = {
  manual: '手动',
  timer: '定时',
  webhook: 'Webhook',
  alert: '告警',
};

/** 运行中文案:按当前产出推导具体动作 —— 工具执行 / 模型思考 / todo 阶段 */
function deriveRunningLabel(
  view: WorkspaceView,
  agentName?: string | null,
  modelName?: string | null,
): string | null {
  // 最近的 running 步骤:thinking 优先「模型思考中」,其余(工具/产物/自定义类型)
  // 只要能取到标题或动作,统一「xx 执行中…」。避免非标准 type 被跳过落到兜底。
  for (let i = view.execution.length - 1; i >= 0; i--) {
    const step = view.execution[i];
    if (step.status !== 'running') continue;
    if (step.type === 'thinking') {
      return `${modelName || agentName || 'Agent'} 思考中…`;
    }
    const tool = step.action || step.title;
    if (tool) return `${tool} 执行中…`;
  }
  // planning 当前进行中的 todo 阶段
  const activePlan = view.planning?.steps.find((s) => s.status === 'running');
  if (activePlan?.title) return `${activePlan.title} 阶段进行中…`;
  // V1 manus 等无 planning 数据的视图:由左面板阶段标题推导「阶段进行中」
  if (view.running_phase_title) return `${view.running_phase_title} 阶段进行中…`;
  // V1 manus 等:无进行中工具/阶段时的「模型思考中」(初始/工具间隙思考)
  if (view.running_thinking) return `${modelName || agentName || 'Agent'} 思考中…`;
  // 兜底:Agent 名称 + 运行中
  return agentName ? `${agentName} 运行中…` : null;
}

/** 运行中指示器:Agent 流式产出时置底展示「正在运行」loading 效果,让人感知任务仍在推进 */
function RunningIndicator({ label }: { label?: string | null }) {
  return (
    <div className="ws-agent-running" role="status" aria-live="polite">
      <span className="ws-agent-running__dots" aria-hidden>
        <i /><i /><i />
      </span>
      <span className="ws-agent-running__text">{label || 'Agent 运行中…'}</span>
    </div>
  );
}

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
  const label = statusLabel(rawStatus);
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
          <span className={`ws-task-card__status ws-task-card__status--${rawStatus}`}>{label}</span>
        </div>
      </div>
      {clickable && <RightOutlined className="ws-task-card__chevron" />}
    </div>
  );
}

/** 专家卡片:专家任务完成(expert_completed)时在对话记录中渲染。
 *  派单侧无专用事件:协作调用走标准 SubAgent(工具调用渲染/子会话看板),
 *  任务化派单由 start_task 渲染任务卡片。 */
function ExpertCard({ step }: { step: WorkspaceExecutionStep }) {
  const isCompleted = step.type === 'expert_completed';
  const isFailed = step.status === 'failed';

  return (
    <div className={`ws-expert-card${isCompleted ? ' ws-expert-card--completed' : ''}${isFailed ? ' ws-expert-card--failed' : ''}`}>
      <div className="ws-expert-card__avatar">
        {step.expert_avatar ? (
          <img src={step.expert_avatar} alt={step.expert_name || ''} />
        ) : (
          <span className="ws-expert-card__avatar-placeholder">{(step.expert_name || '专')[0]}</span>
        )}
      </div>
      <div className="ws-expert-card__info">
        <div className="ws-expert-card__header">
          <span className="ws-expert-card__name">{step.expert_name || step.expert_app_code || '专家'}</span>
          <span className={`ws-expert-card__status ws-expert-card__status--${step.status}`}>
            {isFailed ? '失败' : '已完成'}
          </span>
        </div>
        <div className="ws-expert-card__title">{step.task_title || step.title}</div>
        {step.output && <div className="ws-expert-card__output">{step.output}</div>}
      </div>
    </div>
  );
}

/** 子 Agent 卡片:leader 经标准 spawn_subagent 委托子 Agent 协作时,在对话流中
 *  渲染为一个独立的协作单元(身份/任务/模式/执行状态/结果),区别于普通工具胶囊。 */
function SubAgentCard({ step }: { step: WorkspaceExecutionStep }) {
  const isRunning = step.status === 'running';
  const isFailed = step.status === 'failed';
  const isAsync = step.mode === 'async';
  const name = step.expert_name || step.expert_app_code || '子 Agent';
  const modeLabel = isAsync ? '异步' : '同步';
  // 异步派单在 spawn_subagent 工具完成时子 Agent 仍在后台运行，故 done 态
  // 展示"已派发"而非"已完成"，实时进展交给子 Agent 看板(VisSubagentBoard)轮询。
  let statusText = '已完成';
  if (isFailed) statusText = '失败';
  else if (isRunning) statusText = '执行中';
  else if (isAsync) statusText = '已派发';
  return (
    <div className={`ws-subagent-card${isRunning ? ' ws-subagent-card--running' : ''}${isFailed ? ' ws-subagent-card--failed' : ''}`}>
      <div className="ws-subagent-card__avatar">
        <RocketOutlined className="ws-subagent-card__avatar-icon" />
      </div>
      <div className="ws-subagent-card__body">
        <div className="ws-subagent-card__header">
          <span className="ws-subagent-card__name">{name}</span>
          <span className="ws-subagent-card__mode">{modeLabel}协作</span>
          <span className={`ws-subagent-card__status ws-subagent-card__status--${step.status}`}>
            {statusText}
          </span>
        </div>
        {step.task && <div className="ws-subagent-card__task">{step.task}</div>}
        {(step.output || step.narration) && (
          <div className="ws-subagent-card__output">{step.output || step.narration}</div>
        )}
      </div>
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
  if (raw.startsWith('http')) return resolveFileDownloadUrl(raw);
  if (raw.startsWith('gyra-fs://')) return resolveFileDownloadUrl(raw);
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
   Context injection — 「上下文注入」区(参考图2):
   默认注入的协议文件(skill / agents.md 等 preload 内容)在用户消息后、
   Agent 回复前展示,点击展开查看每条注入项。
   ═══════════════════════════════════════════════════════════════ */

function ContextInjectionSection({ steps }: { steps: WorkspaceExecutionStep[] }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  const names = steps.map((s) => s.title).filter(Boolean);
  const display = names.join(' · ');
  return (
    <div className="ws-context-inject">
      <button
        type="button"
        className="ws-context-inject__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <FileOutlined className="ws-context-inject__icon" />
        <span className="ws-context-inject__label">上下文注入</span>
        <span className="ws-context-inject__name">{display}</span>
        {steps.length > 1 && <span className="ws-context-inject__count">{steps.length}</span>}
        <span className={`ws-cchev ws-cchev--sm${open ? ' ws-cchev--up' : ''}`} aria-hidden />
      </button>
      {open && (
        <div className="ws-context-inject__items">
          {steps.map((s) => (
            <div key={s.id} className="ws-context-inject__item">
              <FileOutlined className="ws-context-inject__item-icon" />
              <span className="ws-context-inject__item-name">{s.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Main component — 按轮次的对话 feed:用户消息 → StepFlow 顺序流(过程,
   按 Todo 分组折叠 / 无 Todo 平铺展开) → 回答/交付文件卡片(结果)。
   结果占据主视觉;交付文件默认展示在 feed 底部,不折叠。
   ═══════════════════════════════════════════════════════════════ */

export interface AgentWorkspaceRendererProps {
  view: WorkspaceView;
  /** 会话是否运行中(决定末轮胶囊处于实时态还是收敛态) */
  running?: boolean;
  onStepClick?: (step: WorkspaceExecutionStep) => void;
  /** 当前选中步骤 id:用于左侧步骤行的高亮选中态 */
  selectedStepId?: string | null;
  /** 点击交付文件卡片:在中间容器渲染文件内容 */
  onDeliverableClick?: (file: WorkspaceDeliverableFile) => void;
  /** 点击任务卡片:进入任务对话 */
  onTaskClick?: (taskId: number) => void;
  /** 点击异步子 agent 卡片:在中间容器内联展开子会话(不传则默认新标签) */
  onSubagentClick?: (subConvId: string) => void;
  /** 点击用户附件「查看任务文件」入口:跳转右侧任务文件 tab(仅简洁模式生效) */
  onAttachmentsClick?: () => void;
  /** ask_user 交互确认后续跑 Agent 对话(复用同一 conv_uid 恢复 WAITING 会话) */
  onInteractionResume?: (userMessage: string) => void;
  /** Agent 头像 icon(appCode 对应 app 的 icon) */
  agentIcon?: string | null;
  /** Agent 名称(头像回退首字母) */
  agentName?: string | null;
  /** 本次对话选用的模型名(运行中文案「xx模型 思考中」使用) */
  modelName?: string | null;
  /** compactProcess:执行过程折叠成单行「Agent 思考」(简洁模式全员启用,结果为主、过程随行) */
  compactProcess?: boolean;
}

/** 交付文件分组块:标题 + 文件卡片列表(点击在中间容器渲染文件内容) */
function DeliverablesBlock({ files, onDeliverableClick }: { files: WorkspaceDeliverableFile[]; onDeliverableClick: (file: WorkspaceDeliverableFile) => void }) {
  return (
    <div className="ws-agent-renderer__deliverables">
      <div className="ws-agent-renderer__deliverables-head">
        <span className="ws-agent-renderer__deliverables-badge">
          <FileOutlined />
        </span>
        <span className="ws-agent-renderer__deliverables-title">交付文件</span>
        <span className="ws-agent-renderer__deliverables-count">{files.length}</span>
      </div>
      {files.map((file) => {
        const downloadUrl = file.download_url || file.content_url;
        return (
          <div
            key={`${file.file_id}-${file.ts || ''}`}
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
                    a.href = resolveFileDownloadUrl(downloadUrl);
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
  );
}

export function AgentWorkspaceRenderer({ view, running = false, onStepClick, selectedStepId, onDeliverableClick, onTaskClick, onSubagentClick, onAttachmentsClick, onInteractionResume, agentIcon, agentName, modelName, compactProcess = false }: AgentWorkspaceRendererProps) {
  // 单次调用还原（排查定位）：深层组件通过 context 打开抽屉，未挂 Provider 时为 no-op
  const { openCallDetail, enabled: callDetailEnabled } = useCallDetail();
  const deliverable_files = useMemo(() => view.deliverable_files ?? [], [view.deliverable_files]);
  const task_files = useMemo(() => view.task_files ?? [], [view.task_files]);
  // 运行中置底文案:按当前产出动态推导(工具执行 / 模型思考 / todo 阶段)
  const runningLabel = useMemo(
    () => deriveRunningLabel(view, agentName, modelName),
    [view, agentName, modelName],
  );
  // 用户头像数据:localStorage 一次性读取(全 feed 共享,避免每个 UserBubble 重复 parse)
  const userInfo = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_USERINFO_KEY) ?? '') as UserInfoResponse | null;
    } catch {
      return null;
    }
  }, []);
  // 流式跟随:底部哨兵,运行中每条新内容都把最新产出滚入可视区;
  // 非运行态加载历史时同样默认定位到最新一屏。只滚动最近的
  // 「overflow-y 容器」,避免连带把整页/外层壳也带滚。
  // 用户干预(向上滚动离开底部)会暂停跟随,避免输出过程中无法操作页面;
  // 回到底部并停留 5 秒后自动恢复跟随。
  const endRef = useRef<HTMLDivElement>(null);
  // 是否跟随最新(运行中 / 初次加载 / 用户贴近底部时为 true)
  const followRef = useRef(true);
  const prevExecLenRef = useRef(0);
  // 「回到底部并停留 5s」后恢复跟随的计时器
  const resumeTimerRef = useRef<number | null>(null);

  const getScrollContainer = useCallback(() => {
    const el = endRef.current;
    if (!el) return null;
    let node: HTMLElement | null = el.parentElement;
    while (node) {
      const overflowY = getComputedStyle(node).overflowY;
      if (overflowY === 'auto' || overflowY === 'scroll') return node;
      node = node.parentElement;
    }
    return null;
  }, []);

  const scrollToBottom = useCallback(() => {
    const c = getScrollContainer();
    if (c) {
      c.scrollTop = c.scrollHeight;
    } else {
      try {
        endRef.current?.scrollIntoView({ block: 'end' });
      } catch {
        /* 兜底:jsdom 等环境未实现 scrollIntoView */
      }
    }
  }, [getScrollContainer]);

  // 内容高度变化(图片/代码高亮/新步骤渲染导致增长)时,若处于跟随则重滚到底,
  // 解决「加载历史后图片才加载、仍停留在旧高度」的问题。
  useEffect(() => {
    if (typeof ResizeObserver === 'undefined') return;
    const feed = endRef.current?.parentElement;
    if (!feed) return;
    const ro = new ResizeObserver(() => {
      if (followRef.current) scrollToBottom();
    });
    ro.observe(feed);
    return () => ro.disconnect();
  }, [scrollToBottom]);

  // 内容 / 运行状态变化:初次加载(0→N)强制跟随到最新;
  // 其余情况仅在用户未干预(followRef=true)且仍贴近底部时继续跟随。
  useEffect(() => {
    const len = view.execution.length;
    const fresh = prevExecLenRef.current === 0 && len > 0;
    prevExecLenRef.current = len;
    if (fresh) {
      followRef.current = true;
      scrollToBottom();
      return;
    }
    if (!followRef.current) return;
    const c = getScrollContainer();
    if (!c) return;
    const distance = c.scrollHeight - c.scrollTop - c.clientHeight;
    if (distance < 80) {
      scrollToBottom();
    } else {
      followRef.current = false;
    }
  }, [view.execution, view, scrollToBottom, getScrollContainer]);

  // 用户手动滚动:离开底部立即暂停跟随(并取消恢复计时);
  // 回到底部并停留 5 秒后自动恢复跟随。
  useEffect(() => {
    const c = getScrollContainer();
    if (!c) return;
    const onScroll = () => {
      const distance = c.scrollHeight - c.scrollTop - c.clientHeight;
      if (distance < 80) {
        // 停留在底部:启动 5s 计时,期间未再次离开底部则恢复跟随
        if (resumeTimerRef.current == null) {
          resumeTimerRef.current = window.setTimeout(() => {
            resumeTimerRef.current = null;
            followRef.current = true;
          }, 5000);
        }
      } else {
        // 离开底部:立即停止跟随并取消计时
        followRef.current = false;
        if (resumeTimerRef.current != null) {
          window.clearTimeout(resumeTimerRef.current);
          resumeTimerRef.current = null;
        }
      }
    };
    c.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      c.removeEventListener('scroll', onScroll);
      if (resumeTimerRef.current != null) {
        window.clearTimeout(resumeTimerRef.current);
        resumeTimerRef.current = null;
      }
    };
  }, [getScrollContainer]);
  // 已有完整回复(answer step)时,summary 不再单独渲染,避免重复
  const hasAnswer = view.execution.some((s) => s.type === 'answer');
  // 任务文件含交付文件,过滤掉已在交付卡片中展示的,避免重复
  const extraTaskFiles = useMemo(
    () => task_files.filter((f) => !deliverable_files.some((d) => d.file_id === f.file_id)),
    [task_files, deliverable_files],
  );

  // 上下文注入:默认注入的协议文件(skill / 记忆等 preload 内容)抽离到
  // 用户消息之后、Agent 回复之前展示(参考图2),不再混入执行步骤流。
  const injectedSteps = useMemo(
    () => (view.execution || []).filter((s) => s.type === 'skill_loaded' || s.type === 'memory_loaded'),
    [view.execution],
  );

  // planning 状态观测时间线(planning 属于最新一轮);归组按胶囊批次执行,避免跨轮次步骤混入
  const planningTimeline = usePlanningTimeline(view.planning);
  const rounds = useMemo(() => {
    // 会话不在运行时,步骤的 running 状态视为遗留脏数据(历史恢复/中断会话),
    // 展示层统一归正为 done —— 避免「外层已完成、内层转圈圈」的矛盾态。
    const execution = running
      ? view.execution
      : view.execution.map((s) => (s.status === 'running' ? { ...s, status: 'done' as const } : s));
    // 上下文注入步骤已抽离到 feed 顶部(用户消息后/Agent 回复前),步骤流里不再重复渲染
    return splitRounds(execution.filter((s) => s.type !== 'skill_loaded' && s.type !== 'memory_loaded'));
  }, [view.execution, running]);

  // 上下文注入插到「首个用户消息之后、Agent 回复之前」:取首个带 user 步骤的轮次。
  // 无用户消息(恢复会话等)时回退到首轮,避免注入区因找不到锚点而缺失。
  const injectionRoundIdx = useMemo(() => {
    const idx = rounds.findIndex((r) => r.user);
    return idx >= 0 ? idx : 0;
  }, [rounds]);

  // 交付文件 / 任务文件按轮次归属:一轮提问产出的文件跟在该轮回复末尾,
  // 而不是会话级全局组件把所有轮次的文件堆在 feed 底部(追问 N 轮后无法区分
  // 哪个文件属于哪次提问)。归属依据是后端下发的文件产出时间戳(交付文件 ts /
  // 任务文件 created_at)落在哪一轮的时间区间内。
  const { byRound: deliverablesByRound, leftover: leftoverDeliverables } = useMemo(
    () => groupDeliverablesByRound(rounds, deliverable_files),
    [rounds, deliverable_files],
  );
  const { byRound: taskFilesByRound, leftover: leftoverTaskFiles } = useMemo(
    () => groupTaskFilesByRound(rounds, extraTaskFiles),
    [rounds, extraTaskFiles],
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
      {/* 异步子 agent 任务看板:点击卡片内联/新标签打开子会话 */}
      {view.subagents && view.subagents.length > 0 && (
        <VisSubagentBoard data={{ items: view.subagents }} onOpenSubagent={onSubagentClick} />
      )}
      {rounds.map((round, roundIdx) => {
        const isLastRound = roundIdx === rounds.length - 1;
        // 本轮产出的文件(按产出时间戳归属到本轮)
        const roundDeliverables = deliverablesByRound.get(round.key) ?? NO_DELIVERABLES;
        const roundTaskFiles = taskFilesByRound.get(round.key) ?? NO_TASK_FILES;
        // compact(简洁模式):整轮过程合并成「一行折叠条」。后端已保证 answer 步骤只含
        // 「发给 human 的最终答复」(过程叙述 agent→agent 不生成 answer),故折叠条只收
        // 工具/思考等过程步骤,answer 一律留正文。
        const roundProcessSteps = compactProcess
          ? round.steps.filter(
              (s) => CAPSULE_STEP_TYPES.has(s.type) && !extractAskUserData(s.output || s.vis),
            )
          : [];
        // 轮内节点:连续过程步骤攒批成 StepFlow。answer 按时间序排在对应工具批次之后
        // (先冲刷前置工具批次,再渲染答案),运行中与完成后同一套顺序。
        const nodes: ReactNode[] = [];
        let batch: WorkspaceExecutionStep[] = [];
        let batchKey = '';
        const flushBatch = () => {
          if (!batch.length) return;
          const batchSteps = batch;
          batch = [];
          // 归组只作用于当前批次(时序:流内的步骤即轮内该区间,绝不混入其它轮次);
          // planning 时间线仅对末轮有意义
          const phases = buildExecutionPhases(
            batchSteps,
            isLastRound ? view.planning : null,
            planningTimeline,
          );
          const flowRunning = running && isLastRound && batchSteps[batchSteps.length - 1].status === 'running';
          nodes.push(
            <StepFlow
              key={batchKey}
              phases={phases}
              running={flowRunning}
              onStepClick={onStepClick}
              selectedStepId={selectedStepId}
            />,
          );
        };
        for (const step of round.steps) {
          // ask_user 步骤本身是 tool_call,必须先于胶囊归组判定:
          // 否则会被当作普通工具步骤压进 StepFlow,无法渲染可交互的确认卡片。
          if (extractAskUserData(step.output || step.vis)) {
            flushBatch();
            if (onInteractionResume) {
              nodes.push(<SceneAskUserCard key={step.id} step={step} onResume={onInteractionResume} />);
            }
            continue;
          }
          // compact:过程步骤已由轮级折叠条统一渲染,这里跳过,避免重复/碎块
          if (compactProcess && CAPSULE_STEP_TYPES.has(step.type)) continue;
          if (CAPSULE_STEP_TYPES.has(step.type)) {
            if (!batch.length) batchKey = `flow-${step.id}`;
            batch.push(step);
            continue;
          }
          // answer 步骤在时间序上位于其前置工具批次之后:先冲刷此前累积的工具批次,
          // 再渲染答案,保证「工具步骤在前、最终回答在后」的 feed 时序(与 ask_user/
          // task_created 分支一致),否则最后一组工具调用会被排到答案之后。
          if (step.type === 'answer') {
            flushBatch();
            nodes.push(<AnswerBlock key={step.id} step={step} />);
          } else {
            flushBatch();
            if (step.type === 'task_created') {
              nodes.push(<TaskCreatedCard key={step.id} step={step} onTaskClick={onTaskClick} />);
            } else if (step.type === 'expert_completed') {
              nodes.push(<ExpertCard key={step.id} step={step} />);
            } else if (step.type === 'subagent') {
              nodes.push(<SubAgentCard key={step.id} step={step} />);
            }
          }
        }
        flushBatch();
        // 轮次头部:仅当本轮含 Agent 侧产出(步骤流/回复/任务卡片)时展示
        const hasAgentOutput = round.steps.some(
          (s) => s.type !== 'user',
        );
        return (
          <Fragment key={round.key}>
            {round.user && (
              <UserBubble
                text={round.user.output || ''}
                attachments={round.user.attachments}
                avatarUrl={userInfo?.avatar_url}
                name={userInfo?.nick_name}
                onAttachmentsClick={onAttachmentsClick}
              />
            )}
            {/* 上下文注入:插到用户消息之后、Agent 回复之前(仅首个用户轮次展示) */}
            {roundIdx === injectionRoundIdx && injectedSteps.length > 0 && (
              <ContextInjectionSection steps={injectedSteps} />
            )}
            {hasAgentOutput && (
              <div className="ws-round-head">
                <span className="ws-round-head__avatar">
                  <AgentAvatar icon={agentIcon} name={agentName} size={22} />
                </span>
                <span className="ws-round-head__name">{agentName || 'Agent'}</span>
                {callDetailEnabled && (
                  <button
                    type="button"
                    className="ws-round-head__debug"
                    title="查看本次模型调用详情（系统/用户提示词、输出、工具、token）"
                    aria-label="查看本次模型调用详情"
                    onClick={() => openCallDetail()}
                  >
                    <FileSearchOutlined style={{ fontSize: 11 }} />
                    <span>调用详情</span>
                  </button>
                )}
              </div>
            )}
            {/* compact:整轮过程合并成一行折叠条(仅本轮有过程步骤时渲染,避免空块) */}
            {compactProcess && roundProcessSteps.length > 0 && (
              <RoundProcessBar
                steps={roundProcessSteps}
                running={running && isLastRound}
                onStepClick={onStepClick}
                selectedStepId={selectedStepId}
              />
            )}
            {nodes}
            {/* 本轮产出的文件:跟在该轮回复末尾,随对话滚动而非会话级固定组件 */}
            {roundDeliverables.length > 0 && onDeliverableClick && (
              <DeliverablesBlock files={roundDeliverables} onDeliverableClick={onDeliverableClick} />
            )}
            {roundTaskFiles.length > 0 && (
              <TaskFilesStrip files={roundTaskFiles} onOpen={handleTaskFileOpen} />
            )}
          </Fragment>
        );
      })}
      {!view.execution.length && !view.summary && <EmptyState />}
      {view.summary && !hasAnswer && (
        <div className="ws-step-answer">
          <div className="ws-step-answer__content">
            <GPTVis components={markdownComponents} {...markdownPlugins}>
              {preprocessLaTeX(view.summary)}
            </GPTVis>
          </div>
        </div>
      )}
      {/* 兜底:无产出时间戳 / 早于所有轮次而无法归属的文件仍在 feed 底部展示,
          避免文件丢失;能归属的文件都已内联到对应轮次末尾。 */}
      {leftoverDeliverables.length > 0 && onDeliverableClick && (
        <DeliverablesBlock files={leftoverDeliverables} onDeliverableClick={onDeliverableClick} />
      )}
      {leftoverTaskFiles.length > 0 && (
        <TaskFilesStrip files={leftoverTaskFiles} onOpen={handleTaskFileOpen} />
      )}
      {/* 运行中:底部 loading 指示 + 自动滚动哨兵 */}
      <div ref={endRef} className="ws-agent-renderer__end" aria-hidden />
      {running && <RunningIndicator label={runningLabel} />}
    </div>
  );
}
