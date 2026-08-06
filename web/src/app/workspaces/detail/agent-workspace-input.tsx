'use client';

import { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { Input, Popover, Tooltip } from 'antd';
import {
  AppstoreOutlined,
  ArrowUpOutlined,
  CheckOutlined,
  ClearOutlined,
  CloseOutlined,
  DownOutlined,
  FileOutlined,
  LeftOutlined,
  LoadingOutlined,
  PaperClipOutlined,
  PlusOutlined,
  ReloadOutlined,
  RightOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import classNames from 'classnames';
import { useRequest } from 'ahooks';
import { apiInterceptors, getModelList, getSkillList, postChatModeParamsFileLoad } from '@/client/api';
import ModelIcon from '@/components/icons/model-icon';
import { transformFileUrl } from '@/utils';
import type { IModelData } from '@/types/model';
import {
  formatTokens,
  getUsageColor,
  getUsageLevel,
  usageMetricsToContextMetrics,
  type UsageMetrics,
} from '@/types/context-metrics';
import { ContextMetricsDisplay } from '@/components/chat/chat-content-components/ContextMetricsDisplay';
import type { AgentWorkspaceInputHandle, PlaybookCommand, SkillRef } from './agent-workspace-types';

/** 选了剧本时必须输入任务目标;没选剧本按原逻辑(有文本或有资源即可)。 */
export function canSendSceneTask(
  text: string,
  hasResources: boolean,
  playbookCommand: { playbook_id: number; playbook_name: string } | null,
): boolean {
  const trimmed = text.trim();
  if (playbookCommand) return trimmed.length > 0;
  return trimmed.length > 0 || hasResources;
}

/**
 * 上下文空间消耗环形图:发送按钮旁的实时用量指示。
 * 数据来自 SSE usage_metric 事件;按使用率分级变色(绿→黄→橙→红)。
 */
function ContextUsageRing({
  metrics,
  onClick,
}: {
  metrics: UsageMetrics | null;
  onClick?: () => void;
}) {
  if (!metrics || !metrics.context_window) return null;
  const ratio = Math.min(Math.max(metrics.ratio ?? 0, 0), 1);
  const level = getUsageLevel(ratio);
  const color = getUsageColor(level);
  const size = 20;
  const stroke = 2.5;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const dash = circumference * ratio;
  const pct = (ratio * 100).toFixed(1);
  return (
    <Tooltip
      title={
        <div className="text-xs leading-5">
          <div>上下文空间 {formatTokens(metrics.total)} / {formatTokens(metrics.context_window)} tokens ({pct}%)</div>
          <div className="text-gray-400">输入 {formatTokens(metrics.prompt)} · 输出 {formatTokens(metrics.completion)}</div>
          {onClick && <div className="text-indigo-400 mt-1">点击查看详情</div>}
        </div>
      }
      placement="top"
    >
      <div
        className="relative flex items-center justify-center h-8 w-8 rounded-full cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/60 transition-colors"
        role="img"
        aria-label={`上下文空间使用率 ${pct}%`}
        onClick={onClick}
      >
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            strokeWidth={stroke}
            className="stroke-gray-200 dark:stroke-gray-600"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
            style={{ transition: 'stroke-dasharray 0.4s ease, stroke 0.4s ease' }}
          />
        </svg>
      </div>
    </Tooltip>
  );
}

interface ResourceItem {
  type: string;
  image_url?: { url: string; preview_url?: string; file_name?: string };
  file_url?: { url: string; preview_url?: string; file_name?: string };
  audio_url?: { url: string; preview_url?: string; file_name?: string };
  video_url?: { url: string; preview_url?: string; file_name?: string };
}

interface UploadingFile { id: string; file: File; status: 'uploading' | 'success' | 'error'; error?: string }

interface AgentWorkspaceInputProps {
  convUid?: string;
  onSend: (payload: { text: string; resources?: ResourceItem[]; model?: string; playbookCommand?: PlaybookCommand; skills?: SkillRef[] }) => void;
  loading?: boolean;
  /** 运行中且无新内容时,按钮转为"进行中·可停止"状态,点击终止当前生成 */
  onStop?: () => void;
  disabled?: boolean;
  lastInput?: { text: string } | null;
  onRetry?: () => void;
  playbooks?: { playbook_id: number; playbook_name: string }[];
  focus?: { id: number; title: string } | null;
  onClearFocus?: () => void;
  onClearContext?: () => void;
  /** SSE usage_metric 实时推送的上下文消耗,用于发送键旁的环形图 */
  usageMetrics?: UsageMetrics | null;
}

export const AgentWorkspaceInput = forwardRef<AgentWorkspaceInputHandle, AgentWorkspaceInputProps>(
  function AgentWorkspaceInput({ convUid, onSend, loading, onStop, disabled, lastInput, onRetry, playbooks, focus, onClearFocus, onClearContext, usageMetrics }, ref) {
    const [text, setText] = useState('');
    const [resources, setResources] = useState<ResourceItem[]>([]);
    const [uploading, setUploading] = useState<UploadingFile[]>([]);
    const [modelList, setModelList] = useState<IModelData[]>([]);
    const [selectedModel, setSelectedModel] = useState<string>('');
    const [showPlaybook, setShowPlaybook] = useState(false);
    const [playbookCommand, setPlaybookCommand] = useState<PlaybookCommand | null>(null);
    const [selectedSkills, setSelectedSkills] = useState<SkillRef[]>([]);
    const [isFocus, setIsFocus] = useState(false);
    // + 号菜单:root=一级菜单(文件/剧本/技能), playbook/skill=二级选择面板
    const [plusMenuOpen, setPlusMenuOpen] = useState(false);
    const [plusPanel, setPlusPanel] = useState<'root' | 'playbook' | 'skill'>('root');
    // 上下文用量详情抽屉开关
    const [usageDrawerOpen, setUsageDrawerOpen] = useState(false);
    const contextMetrics = usageMetrics ? usageMetricsToContextMetrics(usageMetrics) : null;
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useImperativeHandle(ref, () => ({
      focus: () => textareaRef.current?.focus(),
      insertText: (t: string) => {
        setText((prev) => (prev.trim() ? `${prev} ${t}` : t));
        textareaRef.current?.focus();
      },
    }));

    useRequest(async () => {
      const [, data] = await apiInterceptors(getModelList());
      return data || [];
    }, {
      onSuccess: (models: IModelData[]) => {
        const llm = models.filter(m => m.worker_type === 'llm');
        setModelList(llm);
        if (llm.length) setSelectedModel(llm[0].model_name);
      },
    });

    // 技能列表:+ 号菜单「技能」面板的数据源
    const { data: skillList } = useRequest(async () => {
      const [err, res] = await apiInterceptors(getSkillList({ filter: '' }, { page: 1, page_size: 200 }));
      return err ? [] : (res?.items || []);
    });
    const allSkills: SkillRef[] = skillList ?? [];

    const normalizeUploadRes = (res: any): { fileUrl: string; previewUrl: string } => {
      let previewUrl = '', fileUrl = '';
      if (res?.preview_url) { previewUrl = res.preview_url; fileUrl = res.file_path || previewUrl; }
      else if (res?.file_path) { fileUrl = res.file_path; previewUrl = transformFileUrl(fileUrl); }
      else if (res?.url || res?.file_url) { fileUrl = res.url || res.file_url; previewUrl = fileUrl; }
      else if (res?.path) { fileUrl = res.path; previewUrl = transformFileUrl(fileUrl); }
      else if (typeof res === 'string') { fileUrl = res; previewUrl = res; }
      else if (Array.isArray(res)) { const f = res[0]; previewUrl = f?.preview_url || ''; fileUrl = f?.file_path || f?.preview_url || previewUrl; if (!previewUrl && fileUrl) previewUrl = transformFileUrl(fileUrl); }
      return { fileUrl, previewUrl };
    };

    const buildResourceItem = (file: File, fileUrl: string, previewUrl: string): ResourceItem => {
      const common = { url: fileUrl, preview_url: previewUrl || fileUrl, file_name: file.name };
      if (file.type.startsWith('image/')) return { type: 'image_url', image_url: common };
      if (file.type.startsWith('audio/')) return { type: 'audio_url', audio_url: common };
      if (file.type.startsWith('video/')) return { type: 'video_url', video_url: common };
      return { type: 'file_url', file_url: common };
    };

    // File-type accent theme (mirrors home UnifiedChatInput chip theming).
    const getFileTheme = (name: string) => {
      const lower = name.toLowerCase();
      if (/\.(png|jpe?g|gif|bmp|webp)$/.test(lower)) return { bg: 'bg-purple-50 dark:bg-purple-900/30', border: 'border-purple-200 dark:border-purple-700', icon: 'text-purple-500' };
      if (/\.pdf$/.test(lower)) return { bg: 'bg-red-50 dark:bg-red-900/30', border: 'border-red-200 dark:border-red-700', icon: 'text-red-500' };
      if (/\.(doc|docx)$/.test(lower)) return { bg: 'bg-blue-50 dark:bg-blue-900/30', border: 'border-blue-200 dark:border-blue-700', icon: 'text-blue-500' };
      if (/\.(xlsx?|csv)$/.test(lower)) return { bg: 'bg-green-50 dark:bg-green-900/30', border: 'border-green-200 dark:border-green-700', icon: 'text-green-500' };
      if (/\.(ppt|pptx)$/.test(lower)) return { bg: 'bg-orange-50 dark:bg-orange-900/30', border: 'border-orange-200 dark:border-orange-700', icon: 'text-orange-500' };
      if (/\.(mp4|mov|avi|mkv)$/.test(lower)) return { bg: 'bg-pink-50 dark:bg-pink-900/30', border: 'border-pink-200 dark:border-pink-700', icon: 'text-pink-500' };
      if (/\.(mp3|wav|ogg|aac)$/.test(lower)) return { bg: 'bg-yellow-50 dark:bg-yellow-900/30', border: 'border-yellow-200 dark:border-yellow-700', icon: 'text-yellow-500' };
      return { bg: 'bg-gray-50 dark:bg-gray-800', border: 'border-gray-200 dark:border-gray-700', icon: 'text-gray-400' };
    };

    const resourceName = (r: ResourceItem) =>
      r.image_url?.file_name || r.file_url?.file_name || r.audio_url?.file_name || r.video_url?.file_name || '';
    const resourcePreview = (r: ResourceItem) =>
      r.image_url?.preview_url || r.file_url?.preview_url || r.audio_url?.preview_url || r.video_url?.preview_url || '';
    const isImageResource = (r: ResourceItem) => !!r.image_url;

    const hasContent = text.trim().length > 0 || resources.length > 0 || playbookCommand !== null;
    const popoverOverlay = '[&_.ant-popover-inner]:!p-0 [&_.ant-popover-inner]:!rounded-xl [&_.ant-popover-inner]:!shadow-xl';

    const handleFileUpload = async (file: File) => {
      if (!convUid) return;
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      setUploading(prev => [...prev, { id, file, status: 'uploading' }]);
      const formData = new FormData();
      formData.append('doc_files', file);
      const [err, res] = await apiInterceptors(
        postChatModeParamsFileLoad({ convUid, chatMode: 'chat_normal', data: formData, model: selectedModel, config: { timeout: 1000 * 60 * 60 } }),
      );
      setUploading(prev => prev.filter(u => u.id !== id));
      if (err) {
        setUploading(prev => [...prev, { id, file, status: 'error', error: String(err) }]);
        return;
      }
      const { fileUrl, previewUrl } = normalizeUploadRes(res);
      setResources(prev => [...prev, buildResourceItem(file, fileUrl, previewUrl)]);
    };

    const handleDrop = async (e: React.DragEvent) => {
      e.preventDefault();
      for (const f of Array.from(e.dataTransfer.files)) await handleFileUpload(f);
    };

    const canSend = canSendSceneTask(text, resources.length > 0, playbookCommand);
    // 运行中且无可发送的新内容:提交按钮转为"进行中·可停止"状态;
    // 运行中继续输入了内容则恢复为可提交(发送新消息会先中止当前生成)
    const showStop = !!loading && !canSend;

    const handleSend = () => {
      if (!canSend) return;
      const trimmed = text.trim();
      onSend({
        text: trimmed,
        resources: resources.length ? resources : undefined,
        model: selectedModel || undefined,
        playbookCommand: playbookCommand ?? undefined,
        skills: selectedSkills.length ? selectedSkills : undefined,
      });
      setText('');
      setResources([]);
      setPlaybookCommand(null);
      setSelectedSkills([]);
      setShowPlaybook(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const v = e.target.value;
      setText(v);
      // 只有输入框"最开始"的 / 才有命令效果：文本中间的 / 不触发。
      // 已选了剧本 chip 后不再触发（单选，要换剧本先移除 chip）。
      const isSlashCommand = v.startsWith('/') && !playbookCommand;
      setShowPlaybook(isSlashCommand && (playbooks?.length ?? 0) > 0);
    };

    const pickPlaybook = (pb: { playbook_id: number; playbook_name: string }) => {
      setPlaybookCommand({ playbook_id: pb.playbook_id, playbook_name: pb.playbook_name });
      // 清掉触发用的 "/"（用户在开头打的那个），话题由用户随后输入。
      setText(text.replace(/^\/\s*/, ''));
      setShowPlaybook(false);
      textareaRef.current?.focus();
    };

    // `/` at the very start of text pops the playbook list; the text the user
    // types after picking a chip is the task topic (sent as `text`). Show all
    // playbooks while the picker is open (no name filter).
    const visiblePlaybooks = (playbooks ?? []);

    const toggleSkill = (skill: SkillRef) => {
      setSelectedSkills((prev) =>
        prev.some((s) => s.skill_code === skill.skill_code)
          ? prev.filter((s) => s.skill_code !== skill.skill_code)
          : [...prev, skill],
      );
    };

    const closePlusMenu = () => {
      setPlusMenuOpen(false);
      setPlusPanel('root');
    };

    // + 号菜单项共用样式:图标 + 文字,hover 浅底,圆角
    const plusMenuItemCls =
      'flex w-full items-center gap-2.5 px-2.5 py-2 text-[13px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/60 rounded-lg transition-colors cursor-pointer text-left';

    const plusMenuContent = plusPanel === 'root' ? (
      <div className="w-52 py-1">
        <button
          type="button"
          className={plusMenuItemCls}
          onClick={() => { fileInputRef.current?.click(); closePlusMenu(); }}
        >
          <PaperClipOutlined className="text-sm text-gray-500 dark:text-gray-400" />
          <span>添加文件</span>
        </button>
        {(playbooks?.length ?? 0) > 0 && (
          <button type="button" className={plusMenuItemCls} onClick={() => setPlusPanel('playbook')}>
            <RocketOutlined className="text-sm text-gray-500 dark:text-gray-400" />
            <span>剧本</span>
            <RightOutlined className="ml-auto text-[10px] text-gray-400" />
          </button>
        )}
        <button type="button" className={plusMenuItemCls} onClick={() => setPlusPanel('skill')}>
          <AppstoreOutlined className="text-sm text-gray-500 dark:text-gray-400" />
          <span>技能</span>
          {selectedSkills.length > 0 && (
            <span className="ml-auto text-[11px] text-indigo-500 font-medium">{selectedSkills.length}</span>
          )}
          {selectedSkills.length === 0 && <RightOutlined className="ml-auto text-[10px] text-gray-400" />}
        </button>
      </div>
    ) : (
      <div className="w-64">
        <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-gray-100 dark:border-gray-700/60">
          <button
            type="button"
            className="h-6 w-6 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/60 transition-colors"
            onClick={() => setPlusPanel('root')}
            title="返回"
          >
            <LeftOutlined className="text-[10px]" />
          </button>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {plusPanel === 'playbook' ? '选择剧本' : '选择技能'}
          </span>
        </div>
        <div className="max-h-64 overflow-y-auto py-1">
          {plusPanel === 'playbook' && (
            <>
              {visiblePlaybooks.map((pb) => (
                <button
                  type="button"
                  key={pb.playbook_id}
                  className={plusMenuItemCls}
                  onClick={() => { pickPlaybook(pb); closePlusMenu(); }}
                >
                  <RocketOutlined className="text-sm text-gray-400" />
                  <span className="truncate">{pb.playbook_name}</span>
                  {playbookCommand?.playbook_id === pb.playbook_id && (
                    <CheckOutlined className="ml-auto text-xs text-indigo-500" />
                  )}
                </button>
              ))}
            </>
          )}
          {plusPanel === 'skill' && (
            <>
              {allSkills.length === 0 && (
                <div className="px-3 py-2 text-xs text-gray-400">暂无可用技能</div>
              )}
              {allSkills.map((skill) => {
                const checked = selectedSkills.some((s) => s.skill_code === skill.skill_code);
                return (
                  <button
                    type="button"
                    key={skill.skill_code}
                    className={plusMenuItemCls}
                    onClick={() => toggleSkill(skill)}
                    title={skill.description || skill.name}
                  >
                    <AppstoreOutlined className="text-sm text-gray-400" />
                    <span className="truncate">{skill.name}</span>
                    {checked && <CheckOutlined className="ml-auto text-xs text-indigo-500" />}
                  </button>
                );
              })}
            </>
          )}
        </div>
      </div>
    );

    const playbookPopover = (
      <div className="w-72 max-h-72 overflow-y-auto py-1">
        {visiblePlaybooks.length === 0 && (
          <div className="px-3 py-2 text-xs text-gray-400">暂无剧本</div>
        )}
        {visiblePlaybooks.map(pb => (
          <div
            key={pb.playbook_id}
            className="flex items-center gap-2 px-3 py-2 cursor-pointer rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors group"
            onClick={() => pickPlaybook(pb)}
            role="button"
          >
            <PlusOutlined className="text-xs text-gray-400 group-hover:text-indigo-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-indigo-600">{pb.playbook_name}</span>
          </div>
        ))}
      </div>
    );

    return (
      <div className="w-full relative">
        <div
          className={classNames(
            'w-full bg-white dark:bg-[#232734] rounded-2xl shadow-sm border transition-all duration-300',
            isFocus
              ? 'border-indigo-500/50 shadow-lg ring-4 ring-indigo-500/5'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          )}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          {/* SECTION 1 — attached file chips (only when files present) */}
          {(uploading.length > 0 || resources.length > 0) && (
            <div className="px-4 pt-3 pb-2">
              {(uploading.length + resources.length) > 1 && (
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    已上传文件 ({uploading.length + resources.length})
                  </span>
                  <button
                    className="text-xs text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 px-2 py-0.5 rounded transition-colors"
                    onClick={() => { setResources([]); setUploading([]); }}
                  >
                    全部清除
                  </button>
                </div>
              )}
              <div className="flex flex-wrap gap-3">
                {/* uploading cards */}
                {uploading.map(u => {
                  const theme = getFileTheme(u.file.name);
                  const isImg = u.file.type.startsWith('image/');
                  return (
                    <div key={u.id} className="relative">
                      <div className={`w-[60px] h-[60px] rounded-lg border-2 overflow-hidden bg-white dark:bg-gray-800 shadow-sm ${u.status === 'error' ? 'border-red-300' : theme.border}`}>
                        {isImg
                          ? <img src={URL.createObjectURL(u.file)} className="w-full h-full object-cover" />
                          : <div className={`w-full h-full flex items-center justify-center ${theme.bg}`}>
                              <FileOutlined className={`${theme.icon} text-xl`} />
                            </div>}
                        {u.status === 'uploading' && (
                          <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                            <LoadingOutlined className="text-white text-lg" spin />
                          </div>
                        )}
                        {u.status === 'error' && (
                          <div className="absolute inset-0 bg-red-500/80 flex flex-col items-center justify-center gap-0.5">
                            <CloseOutlined className="text-white text-xs" />
                            <span className="text-white text-[10px]">失败</span>
                          </div>
                        )}
                      </div>
                      <div className="mt-1 max-w-[60px]">
                        <p className={`text-xs truncate ${u.status === 'error' ? 'text-red-500' : 'text-gray-600 dark:text-gray-400'}`}>{u.file.name}</p>
                      </div>
                    </div>
                  );
                })}
                {/* uploaded chips */}
                {resources.map((r, i) => {
                  const name = resourceName(r);
                  const theme = getFileTheme(name);
                  const preview = resourcePreview(r);
                  const isImg = isImageResource(r);
                  return (
                    <div key={`${name}-${i}`} className="relative group">
                      <div className={`w-[60px] h-[60px] rounded-lg border-2 overflow-hidden bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-all duration-200 ${theme.border}`}>
                        {isImg && preview
                          ? <img src={preview} className="w-full h-full object-cover" />
                          : <div className={`w-full h-full flex items-center justify-center ${theme.bg}`}>
                              <FileOutlined className={`${theme.icon} text-xl`} />
                            </div>}
                      </div>
                      <div className="mt-1 max-w-[60px]">
                        <p className="text-xs text-gray-600 dark:text-gray-400 truncate">{name}</p>
                      </div>
                      <button
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200 shadow hover:bg-red-50 hover:border-red-300 hover:text-red-500"
                        onClick={() => setResources(prev => prev.filter((_, j) => j !== i))}
                      >
                        <CloseOutlined className="text-[10px]" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* SECTION 1.4 - focused artifact chip (implicit context, removable) */}
          {focus && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 text-amber-600 dark:text-amber-300 rounded-md px-2 py-1 text-sm">
                <FileOutlined className="text-xs" />
                <span className="text-xs text-amber-400">当前关注</span>
                <span className="font-medium max-w-[200px] truncate">{focus.title}</span>
                {onClearFocus && (
                  <button
                    className="ml-0.5 text-amber-400 hover:text-red-500 transition-colors"
                    onClick={onClearFocus}
                    title="取消带入当前关注"
                  >
                    <CloseOutlined className="text-[11px]" />
                  </button>
                )}
              </span>
            </div>
          )}
          {/* SECTION 1.5 — selected playbook command chip (single, removable) */}
          {playbookCommand && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700 text-indigo-600 dark:text-indigo-300 rounded-md px-2 py-1 text-sm">
                <span className="text-xs text-indigo-400">/</span>
                <span className="font-medium">{playbookCommand.playbook_name}</span>
                <button
                  className="ml-0.5 text-indigo-400 hover:text-red-500 transition-colors"
                  onClick={() => setPlaybookCommand(null)}
                  title="移除剧本"
                >
                  <CloseOutlined className="text-[11px]" />
                </button>
              </span>
            </div>
          )}
          {/* SECTION 1.6 — selected skill chips (multi, removable) */}
          {selectedSkills.length > 0 && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              {selectedSkills.map((skill) => (
                <span
                  key={skill.skill_code}
                  className="inline-flex items-center gap-1 bg-cyan-50 dark:bg-cyan-900/30 border border-cyan-200 dark:border-cyan-700 text-cyan-600 dark:text-cyan-300 rounded-md px-2 py-1 text-sm"
                >
                  <AppstoreOutlined className="text-xs text-cyan-400" />
                  <span className="font-medium max-w-[160px] truncate">{skill.name}</span>
                  <button
                    className="ml-0.5 text-cyan-400 hover:text-red-500 transition-colors"
                    onClick={() => toggleSkill(skill)}
                    title="移除技能"
                  >
                    <CloseOutlined className="text-[11px]" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* SECTION 2 — textarea (borderless, card is the only border) */}
          <div className="relative">
            <Popover
              open={showPlaybook}
              content={playbookPopover}
              placement="topLeft"
              trigger={[]}
              overlayClassName={popoverOverlay}
            >
              <div className={classNames('p-4', onClearContext && 'pr-12')}>
                <Input.TextArea
                  ref={textareaRef}
                  value={text}
                  onChange={handleChange}
                  onFocus={() => setIsFocus(true)}
                  onBlur={() => setIsFocus(false)}
                  onKeyDown={handleKeyDown}
                  onPaste={async (e) => {
                    const clipboardData = e.clipboardData;
                    if (!clipboardData || !clipboardData.files.length) return;
                    for (const f of Array.from(clipboardData.files)) {
                      if (f.type.startsWith('image/') || f.type.startsWith('video/') || f.type.startsWith('audio/')) {
                        e.preventDefault();
                        await handleFileUpload(f);
                      }
                    }
                  }}
                  placeholder="输入指令给 Agent…(+ 添加文件/剧本/技能,/ 快捷选剧本)"
                  className="!text-base !bg-transparent !border-0 !resize-none placeholder:!text-gray-400 !text-gray-800 dark:!text-gray-200 !shadow-none !p-0 !min-h-[60px]"
                  autoSize={{ minRows: 2, maxRows: 8 }}
                  disabled={disabled}
                />
              </div>
            </Popover>

            {/* 清理上下文:浮动在输入区右上角,半透明毛玻璃圆形按钮,hover 点亮 */}
            {onClearContext && (
              <button
                type="button"
                className="absolute top-2 right-2 z-10 h-7 w-7 rounded-full flex items-center justify-center border border-gray-200/70 dark:border-gray-600/60 bg-white/70 dark:bg-[#232734]/70 backdrop-blur-sm text-gray-300 dark:text-gray-500 shadow-sm hover:text-red-500 hover:border-red-200 dark:hover:border-red-700 hover:bg-red-50/90 dark:hover:bg-red-900/30 transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                onClick={onClearContext}
                disabled={!convUid || disabled || loading}
                title="清理上下文(新开会话)"
              >
                <ClearOutlined className="text-xs" />
              </button>
            )}
          </div>

          {/* SECTION 3 — footer toolbar: left tools / right send */}
          <div className="flex items-center justify-between gap-2 px-3 pb-3 min-w-0">
            <div className="flex items-center gap-2 min-w-0 flex-shrink overflow-visible">
              {/* + 号菜单:添加文件 / 剧本 / 技能 */}
              <Popover
                open={plusMenuOpen}
                onOpenChange={(open) => { setPlusMenuOpen(open); if (!open) setPlusPanel('root'); }}
                content={plusMenuContent}
                trigger="click"
                placement="topLeft"
                overlayClassName={popoverOverlay}
              >
                <button
                  type="button"
                  className={classNames(
                    'h-8 w-8 rounded-full flex items-center justify-center border transition-all flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed',
                    plusMenuOpen
                      ? 'border-indigo-300 dark:border-indigo-600 text-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 rotate-45'
                      : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-indigo-500 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'
                  )}
                  disabled={!convUid || disabled || loading}
                  title="添加文件 / 剧本 / 技能"
                >
                  <PlusOutlined className="text-sm transition-transform" />
                </button>
              </Popover>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                style={{ display: 'none' }}
                onChange={(e) => { for (const f of Array.from(e.target.files || [])) handleFileUpload(f); e.target.value = ''; }}
              />

              {/* retry (only when retryable) */}
              {lastInput && onRetry && !loading && (
                <button
                  className="h-8 w-8 rounded-full flex items-center justify-center border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-indigo-500 hover:border-indigo-300 transition-all hover:bg-indigo-50 dark:hover:bg-indigo-900/20 flex-shrink-0 disabled:opacity-40"
                  onClick={onRetry}
                  disabled={disabled}
                  title="重试"
                >
                  <ReloadOutlined className="text-sm" />
                </button>
              )}

              {/* model selector pill */}
              <Popover
                content={(
                  <div className="w-60 max-h-64 overflow-y-auto py-1">
                    <div className="px-3 pt-1.5 pb-1 text-[11px] font-medium text-gray-400 dark:text-gray-500">选择模型</div>
                    {modelList.length === 0 && <div className="px-3 py-2 text-xs text-gray-400">暂无可用模型</div>}
                    {modelList.map(m => (
                      <div
                        key={m.model_name}
                        className={classNames(
                          'flex items-center gap-2.5 px-3 py-2 cursor-pointer rounded-lg transition-colors group',
                          selectedModel === m.model_name
                            ? 'bg-indigo-50 dark:bg-indigo-900/20'
                            : 'hover:bg-gray-100 dark:hover:bg-gray-700/60'
                        )}
                        onClick={() => setSelectedModel(m.model_name)}
                      >
                        <ModelIcon model={m.model_name} width={18} height={18} />
                        <span className={classNames(
                          'text-[13px] truncate',
                          selectedModel === m.model_name ? 'text-indigo-600 dark:text-indigo-400 font-medium' : 'text-gray-700 dark:text-gray-300'
                        )}>{m.model_name}</span>
                        {selectedModel === m.model_name && (
                          <CheckOutlined className="ml-auto text-xs text-indigo-500" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
                trigger="click"
                placement="topLeft"
                overlayClassName={popoverOverlay}
              >
                <div className="flex items-center gap-1.5 h-8 px-2.5 rounded-full cursor-pointer text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/60 transition-all group flex-shrink-0">
                  <ModelIcon model={selectedModel} width={16} height={16} />
                  <span className="text-xs font-medium max-w-[96px] truncate">
                    {selectedModel || '选择模型'}
                  </span>
                  <DownOutlined className="text-[9px] text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
                </div>
              </Popover>
            </div>

            <div className="flex items-center gap-1.5 flex-shrink-0">
              {playbookCommand && !text.trim() && (
                <div className="text-[11px] text-amber-600 px-1 pb-1">
                  选了剧本要写本次任务目标 — 剧本只指定资源/能力,目标由你定。
                </div>
              )}
              {/* 上下文空间消耗环形图:实时显示当前 Agent 上下文用量，点击打开详情抽屉 */}
              <ContextUsageRing
                metrics={usageMetrics ?? null}
                onClick={() => setUsageDrawerOpen(true)}
              />
              {contextMetrics && (
                <ContextMetricsDisplay
                  metrics={contextMetrics}
                  compact={false}
                  showDetails={true}
                  open={usageDrawerOpen}
                  onOpenChange={setUsageDrawerOpen}
                />
              )}
              <button
                className={classNames(
                  'w-9 h-9 flex items-center justify-center transition-all !border-0 flex-shrink-0 rounded-full',
                  showStop || hasContent
                    ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 shadow-md hover:shadow-lg text-white'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed',
                  showStop && 'ws-stop-btn--running'
                )}
                onClick={showStop ? onStop : handleSend}
                disabled={showStop ? (!onStop || disabled) : (!hasContent || disabled || !canSend)}
                title={showStop ? '停止生成' : '发送'}
              >
                {showStop
                  // 进行中·可停止:实心方形停止符 + 呼吸缩放;按钮外扩光环表达 Agent 正在运行
                  ? <span className="ws-stop-btn__square" />
                  : <ArrowUpOutlined className="text-base" />}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  },
);