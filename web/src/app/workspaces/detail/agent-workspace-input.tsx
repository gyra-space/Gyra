'use client';

import { forwardRef, useImperativeHandle, useEffect, useMemo, useRef, useState } from 'react';
import { Input, Popover, Drawer, Progress, Statistic, Row, Col, message } from 'antd';
import {
  ArrowUpOutlined,
  CheckOutlined,
  ClearOutlined,
  CloseOutlined,
  DownOutlined,
  FileOutlined,
  LoadingOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import classNames from 'classnames';
import { useRequest } from 'ahooks';
import { apiInterceptors, getModelList, getSkillList, getMCPList, postChatModeParamsFileLoad, listResources, listArtifacts, listAssets } from '@/client/api';
import ModelIcon from '@/components/icons/model-icon';
import { transformFileUrl } from '@/utils';
import type { IModelData } from '@/types/model';
import {
  formatTokens,
  getUsageColor,
  getUsageLevel,
  type UsageMetrics,
} from '@/types/context-metrics';
import type { AgentWorkspaceInputHandle, PlaybookCommand, SkillRef } from './agent-workspace-types';
import { getPendingResources, setPendingResources, getPendingResourceRefs, setPendingResourceRefs } from './scene-agent-send-data';
import {
  PlusMenu,
  SelectionChip,
  type PlusMenuMcpRef,
  type PlusMenuPermission,
} from '@/components/chat/input/plus-menu';
import { SceneTriggerMenu, type SceneTriggerMenuHandle, type SceneTriggerSelection } from '@/components/chat/input/scene-trigger-menu';
import type { SessionCommandItem, SessionCommandAction, SubAgentRef, ArtifactRef, AssetRef, ResourceRef } from '@/components/chat/input/trigger-types';
import { detectTrigger, stripTrigger, type TriggerState } from '@/components/chat/input/trigger-detect';
import { VoiceInputButton } from '@/components/chat/input/voice-input-button';
import {
  MediaParamsButton,
  getMultimediaConfig,
  isMultimediaApp,
  type MediaParams,
} from '@/components/chat/input/media-params';

/** 模型 → 提供商:优先取后端 host 的 `proxy@{provider}` 前缀(model_api 以该形式编码),
 *  其次按已知 model_name 前缀匹配,兜底归入「自定义模型」。 */
function getModelProvider(m: IModelData): string {
  if (m.host && m.host.startsWith('proxy@')) return m.host.slice('proxy@'.length);
  const name = (m.model_name || '').toLowerCase();
  const rules: [RegExp, string][] = [
    [/^qwen/, 'Qwen'],
    [/^deepseek/, 'DeepSeek'],
    [/^(glm|chatglm|zhipu)/, '智谱 GLM'],
    [/^moonshot|^kimi/, '月之暗面 Moonshot'],
    [/^baichuan/, '百川 Baichuan'],
    [/^minimax/, 'MiniMax'],
    [/^doubao|^skylark/, '豆包 Doubao'],
    [/^ernie|^wenxin/, '百度 ERNIE'],
    [/^hunyuan|^yi-/, '混元'],
    [/^spark|^xinghuo/, '讯飞星火'],
    [/^gpt|^o\d/, 'OpenAI'],
    [/^claude/, 'Anthropic'],
    [/^gemini/, 'Google'],
    [/^llama/, 'Meta'],
    [/^internlm/, '上海 AI Lab'],
  ];
  for (const [re, label] of rules) {
    if (re.test(name)) return label;
  }
  return '自定义模型';
}

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
 * 上下文用量分类（hover 卡片图例）。
 * 占比口径:各项 token / 上下文窗口,与总占比同口径,各行之和约等于总占比。
 */
function getUsageCategories(metrics: UsageMetrics) {
  return [
    { label: '系统提示词', value: metrics.system ?? 0, color: '#22c55e' },
    { label: '工具及子智能体', value: metrics.tools ?? metrics.completion ?? 0, color: '#faad14' },
    { label: '对话消息', value: (metrics.history ?? 0) + (metrics.user_msg ?? 0), color: '#8b5cf6' },
    { label: '连接器及MCP', value: metrics.mcp ?? 0, color: '#06b6d4' },
    { label: '技能', value: metrics.skills ?? 0, color: '#3b82f6' },
  ];
}

/** 分类占比文案:0 显示 "0%",其余保留一位小数。 */
function formatCategoryPct(value: number, contextWindow: number): string {
  if (contextWindow <= 0 || value <= 0) return '0%';
  return `${((value / contextWindow) * 100).toFixed(1)}%`;
}

/**
 * hover 弹出的上下文用量卡片:大号百分比 + 已用/窗口 + 多色分段条 + 分类图例。
 */
function ContextUsageCard({
  metrics,
  onClick,
}: {
  metrics: UsageMetrics;
  onClick?: () => void;
}) {
  const { context_window: contextWindow, total } = metrics;
  const ratio = Math.min(Math.max(metrics.ratio ?? 0, 0), 1);
  const categories = getUsageCategories(metrics);
  return (
    <div className="w-[280px]">
      <div className="text-sm font-medium text-gray-800 dark:text-gray-100">上下文用量</div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="text-2xl font-semibold leading-none text-gray-900 dark:text-gray-50">
          {(ratio * 100).toFixed(1)}%
        </span>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          已使用 {formatTokens(total)}/ {formatTokens(contextWindow)}
        </span>
      </div>
      {/* 多色分段条:各分类按占窗口比例拼接,余量为灰色轨道 */}
      <div className="mt-2.5 flex h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
        {categories.map((c) => {
          const width = contextWindow > 0 ? (c.value / contextWindow) * 100 : 0;
          if (width <= 0) return null;
          return (
            <div
              key={c.label}
              className="h-full shrink-0"
              style={{ width: `${Math.min(width, 100)}%`, background: c.color }}
            />
          );
        })}
      </div>
      {/* 分类图例:右侧同时展示 token 实际量与占比 */}
      <div className="mt-3 space-y-1.5">
        {categories.map((c) => (
          <div key={c.label} className="flex items-center text-xs">
            <span className="mr-2 h-2 w-2 shrink-0 rounded-full" style={{ background: c.color }} />
            <span className="text-gray-600 dark:text-gray-300">{c.label}</span>
            <span className="ml-auto tabular-nums text-gray-500 dark:text-gray-400">
              {formatTokens(c.value)}
            </span>
            <span className="ml-2 tabular-nums text-gray-400 dark:text-gray-500">
              {formatCategoryPct(c.value, contextWindow)}
            </span>
          </div>
        ))}
      </div>
      {onClick && (
        <div className="mt-2.5 text-xs text-indigo-500 dark:text-indigo-400">点击查看完整明细</div>
      )}
    </div>
  );
}

/**
 * 上下文空间消耗环形图:发送按钮旁的实时用量指示。
 * 数据来自 SSE usage_metric 事件;按使用率分级变色(绿→黄→橙→红)。
 * hover 弹出结构化用量卡片,点击打开详情抽屉。
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
    <Popover
      content={<ContextUsageCard metrics={metrics} onClick={onClick} />}
      trigger="hover"
      placement="top"
      arrow={false}
      styles={{ body: { padding: '14px 16px', borderRadius: 12 } }}
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
    </Popover>
  );
}

/**
 * 上下文空间占用明细抽屉:点击环形图打开,展示构成占比与分层(compressed/retained)占比。
 */
function ContextUsageDetail({
  metrics,
  open,
  onOpenChange,
}: {
  metrics: UsageMetrics | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!metrics) return null;
  const { context_window: contextWindow, total } = metrics;
  const ratio = Math.min(Math.max(metrics.ratio ?? 0, 0), 1);
  const level = getUsageLevel(ratio);
  const color = getUsageColor(level);
  const system = metrics.system ?? 0;
  const history = metrics.history ?? 0;
  const userMsg = metrics.user_msg ?? 0;
  const tools = metrics.tools ?? metrics.completion ?? 0;
  const skills = metrics.skills ?? 0;
  const mcp = metrics.mcp ?? 0;
  const layers = metrics.layers ?? { compressed: 0, retained: 0 };
  const layerTotal = layers.compressed + layers.retained;

  const pct = (n: number) => (total > 0 ? ((n / total) * 100).toFixed(1) : '0.0');
  const layerPct = (n: number) =>
    layerTotal > 0 ? ((n / layerTotal) * 100).toFixed(1) : '0.0';

  const segData = [
    { label: '系统提示词', value: system, color: '#22c55e' },
    { label: '历史消息', value: history, color: '#8b5cf6' },
    { label: '当前用户消息', value: userMsg, color: '#c4b5fd' },
    { label: '工具及子智能体', value: tools, color: '#faad14' },
    { label: '技能', value: skills, color: '#3b82f6' },
    { label: '连接器及MCP', value: mcp, color: '#06b6d4' },
  ];

  const layerData = [
    { label: '压缩摘要', value: layers.compressed, color: '#94a3b8' },
    { label: '保留区', value: layers.retained, color: '#0ea5e9' },
  ];

  return (
    <Drawer
      title="上下文空间占用明细"
      placement="right"
      width={480}
      open={open}
      onClose={() => onOpenChange(false)}
    >
      {/* 总览 */}
      <div className="mb-6">
        <div className="text-sm font-medium mb-2">总览</div>
        <Row gutter={16}>
          <Col span={12}>
            <Statistic
              title="上下文使用"
              value={Math.round(ratio * 100)}
              suffix="%"
              valueStyle={{ color }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="已用 / 窗口"
              value={formatTokens(total)}
              suffix={` / ${formatTokens(contextWindow)}`}
            />
          </Col>
        </Row>
        <Progress percent={Math.round(ratio * 100)} strokeColor={color} className="mt-2" />
      </div>

      {/* 构成占比 */}
      <div className="mb-6">
        <div className="text-sm font-medium mb-3">构成占比（占已用占比）</div>
        {segData.map((s) => (
          <div key={s.label} className="flex items-center gap-2 mb-2">
            <span className="w-3 h-3 rounded-full shrink-0" style={{ background: s.color }} />
            <span className="text-xs w-24 text-gray-600 dark:text-gray-300">{s.label}</span>
            <Progress
              percent={Number(pct(s.value))}
              size="small"
              strokeColor={s.color}
              style={{ width: 120 }}
              showInfo={false}
            />
            <span className="text-xs text-gray-500">
              {formatTokens(s.value)}（{pct(s.value)}%）
            </span>
          </div>
        ))}
      </div>

      {/* 分层占比 */}
      <div className="mb-6">
        <div className="text-sm font-medium mb-3">历史分区（压缩/保留）</div>
        {layerData.map((l) => (
          <div key={l.label} className="flex items-center gap-2 mb-2">
            <span className="w-3 h-3 rounded-full shrink-0" style={{ background: l.color }} />
            <span className="text-xs w-24 text-gray-600 dark:text-gray-300">{l.label}</span>
            <Progress
              percent={Number(layerPct(l.value))}
              size="small"
              strokeColor={l.color}
              style={{ width: 120 }}
              showInfo={false}
            />
            <span className="text-xs text-gray-500">
              {formatTokens(l.value)}（{layerPct(l.value)}%）
            </span>
          </div>
        ))}
      </div>
    </Drawer>
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
  conversationId?: string;
  onSend: (payload: { text: string; resources?: ResourceItem[]; model?: string; playbookCommand?: PlaybookCommand; skills?: SkillRef[]; mcps?: PlusMenuMcpRef[]; permission?: string; media?: MediaParams; forceCompress?: boolean }) => void;
  loading?: boolean;
  /** 运行中且无新内容时,按钮转为"进行中·可停止"状态,点击终止当前生成 */
  onStop?: () => void;
  disabled?: boolean;
  /** 只读模式(查看角色无 space.chat.use):禁用输入并提示不可发起对话 */
  readOnly?: boolean;
  lastInput?: { text: string } | null;
  onRetry?: () => void;
  playbooks?: { playbook_id: number; playbook_name: string }[];
  focus?: { id: number; title: string } | null;
  onClearFocus?: () => void;
  onClearContext?: () => void;
  /** SSE usage_metric 实时推送的上下文消耗,用于发送键旁的环形图 */
  usageMetrics?: UsageMetrics | null;
  /** 当前 app 信息（用于识别多媒体 Agent 的 capability/模型池；场景空间可 spawn 多媒体子 Agent） */
  appInfo?: any;
  /** 受控选中模型(可选):由外部管理模型选择,输入框重挂载(简洁模式欢迎态→运行态、会话切换)后不丢失 */
  model?: string;
  /** 模型选择变化回调(与 model 成对使用) */
  onModelChange?: (name: string) => void;
  /** 默认模型(可选):优先于全局模型列表首个;用于场景空间默认取「空间设置模型列表」首个配置模型 */
  defaultModel?: string;
  /** 场景空间 id:`@` 子 Agent 与 `#` 交付资源两个菜单的数据源都按空间维度拉取 */
  workspaceId?: number;
  /** 附件暂存域(可选):传入后已上传未发送的附件跨重挂载存活
   *  (欢迎态↔运行态分支切换/会话切换会重建输入框,实例 state 会归零) */
  attachmentScopeKey?: string;
  /** 会话缺失时的懒创建回调(可选):上传需要会话上下文,空间连当前会话都没有时由外部创建 */
  onEnsureConversation?: () => Promise<string | null>;
}

export const AgentWorkspaceInput = forwardRef<AgentWorkspaceInputHandle, AgentWorkspaceInputProps>(
  function AgentWorkspaceInput({ conversationId, onSend, loading, onStop, disabled, readOnly, lastInput, onRetry, playbooks, focus, onClearFocus, onClearContext, usageMetrics, appInfo, model, onModelChange, defaultModel, workspaceId, attachmentScopeKey, onEnsureConversation }, ref) {
    const [text, setText] = useState('');
    // 已上传未发送附件:挂载时从暂存域恢复(跨重挂载存活),变更统一走 applyResources 双写
    const [resources, setResources] = useState<ResourceItem[]>(() =>
      attachmentScopeKey ? getPendingResources(attachmentScopeKey) : [],
    );
    /** 附件变更统一入口:实例 state 与跨重挂载暂存同写 */
    const applyResources = (next: ResourceItem[]) => {
      setResources(next);
      if (attachmentScopeKey) setPendingResources(attachmentScopeKey, next);
    };
    const [uploading, setUploading] = useState<UploadingFile[]>([]);
    const [modelList, setModelList] = useState<IModelData[]>([]);
    const [internalSelectedModel, setInternalSelectedModel] = useState<string>('');
    // 受控(外部传入 model)与非受控(本地 state)共用同一读值:场景空间简洁模式由 shell 记忆,
    // 避免输入框因欢迎态→运行态切换 / key 重挂载丢失用户已选模型而回退默认
    const selectedModel = model ?? internalSelectedModel;
    // 模型列表异步返回时用 ref 判断「是否已有选中」,防止 onSuccess 闭包读到过期值覆盖用户选择
    const selectedModelRef = useRef(selectedModel);
    // 用户是否手动选过模型:区分「手动选择」与「系统回填默认」,使空间默认模型到达后不会覆盖手动选择
    const userSelectedRef = useRef(false);
    // 当前「默认值」是否由系统回填(而非用户选择/外部记忆):仅回填默认时,空间默认模型可以覆盖之
    const systemDefaultRef = useRef(false);
    const updateSelectedModel = (name: string) => {
      selectedModelRef.current = name;
      if (onModelChange) onModelChange(name);
      else setInternalSelectedModel(name);
    };
    const [mediaParams, setMediaParams] = useState<MediaParams>({});
    // 统一 trigger 状态:null = 未激活;char 决定当前唤起的是 `/` `@` `#` 中的哪一个
    const [activeTrigger, setActiveTrigger] = useState<TriggerState | null>(null);
    const [playbookCommand, setPlaybookCommand] = useState<PlaybookCommand | null>(null);
    // @ 接管态:会话级 sticky,选中后持续生效直到显式退出或改选他人
    const [activeSubAgent, setActiveSubAgent] = useState<SubAgentRef | null>(null);
    // # 引用的资源(交付产物/空间资产)。start/end 为 P1 内联化预留,P0 恒在文本末尾
    // 挂载时从暂存域恢复(跨重挂载存活),变更统一走 applyResourceRefs 双写
    const [resourceRefs, setResourceRefs] = useState<ResourceRef[]>(() =>
      attachmentScopeKey ? getPendingResourceRefs(attachmentScopeKey) : [],
    );
    /** `#` 引用变更统一入口:实例 state 与跨重挂载暂存同写 */
    const applyResourceRefs = (next: ResourceRef[]) => {
      setResourceRefs(next);
      if (attachmentScopeKey) setPendingResourceRefs(attachmentScopeKey, next);
    };
    const [selectedSkills, setSelectedSkills] = useState<SkillRef[]>([]);
    // + 菜单选中的 MCP 连接器
    const [selectedMcps, setSelectedMcps] = useState<PlusMenuMcpRef[]>([]);
    // 权限等级(默认 plan):对齐后端 agent_context.extra["permission_mode"] 的 5 级权限链
    const [permission, setPermission] = useState<string>('plan');
    // 规划模式(/规划模式 命令触发):开启后本回合按 plan 档发送,chip 展示在输入框上方
    const [planMode, setPlanMode] = useState(false);
    // 压缩模式(/压缩上下文 命令触发):下一条发送携带 forceCompress,本轮推理前强制压缩
    const [compactMode, setCompactMode] = useState(false);
    const [isFocus, setIsFocus] = useState(false);
    // 上下文用量详情抽屉开关
    const [usageDrawerOpen, setUsageDrawerOpen] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const triggerMenuRef = useRef<SceneTriggerMenuHandle>(null);

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
        // 只保留文本/视觉 LLM（媒体生成模型 model_type=image/video/audio 由后端过滤，
        // 此处按 model_type 兜底，防止多媒体模型混入普通聊天模型下拉）
        const llm = models.filter(m => m.worker_type === 'llm' && (!m.model_type || m.model_type === 'llm'));
        setModelList(llm);
        // 仅在尚未选中任何模型时回填默认模型:不覆盖用户已选/外部记忆的模型
        // (修复提交后输入框重挂载导致模型回退默认的 bug)
        if (llm.length && !selectedModelRef.current) {
          // 优先使用传入的默认模型(如空间设置模型列表首个)；其次全局默认模型(模型配置里
          // 指定的 is_default=全局唯一)；否则回退全局模型列表首个。避免空间默认为空时
          // 无脑选列表首个,而是尊重用户显式指定的全局默认模型。
          systemDefaultRef.current = true;
          const globalDefault = llm.find(m => m.is_default)?.model_name || '';
          updateSelectedModel(defaultModel || globalDefault || llm[0].model_name);
        }
      },
    });

    // 空间默认模型异步返回(晚于全局模型列表)时,仅当当前是「系统回填默认」(非用户选择/外部记忆)
    // 才用空间默认模型覆盖;避免覆盖用户手选或外部记忆的模型
    useEffect(() => {
      if (defaultModel && !userSelectedRef.current && systemDefaultRef.current) {
        updateSelectedModel(defaultModel);
      }
    }, [defaultModel, modelList]);

    // 技能列表:+ 号菜单「技能」面板的数据源
    const { data: skillList } = useRequest(async () => {
      const [err, res] = await apiInterceptors(getSkillList({ filter: '' }, { page: 1, page_size: 200 }));
      return err ? [] : (res?.items || []);
    });
    const allSkills: SkillRef[] = skillList ?? [];

    // MCP 列表:+ 菜单「MCP」面板的数据源
    const { data: mcpList, loading: mcpLoading } = useRequest(async () => {
      const [err, res] = await apiInterceptors(getMCPList({ filter: '' }, { page: '1', page_size: '100' }));
      return err ? [] : (((res as any)?.items || []) as PlusMenuMcpRef[]);
    });
    const allMcps: PlusMenuMcpRef[] = mcpList ?? [];

    // ---- `@` / `#` 数据源 ----
    // 首次唤起这两个菜单时才拉取:进场景空间不一定会用到,避免每次都多打三个接口。
    /** 是否已请求过 `@`/`#` 菜单数据(首次唤起时置 true,之后常驻不重复拉) */
    const [menuDataRequested, setMenuDataRequested] = useState(false);

    // `@` 子 Agent:空间绑定的 app 型资源(physical_ref = app_code)
    const { data: subAgentList, loading: subAgentsLoading } = useRequest(async () => {
      if (!workspaceId || !menuDataRequested) return [];
      const [err, res] = await apiInterceptors(listResources({ workspace_id: workspaceId, type: 'app' }));
      return err ? [] : (((res as any)?.items ?? res ?? []) as SubAgentRef[]);
    }, { refreshDeps: [workspaceId, menuDataRequested] });
    const allSubAgents: SubAgentRef[] = subAgentList ?? [];

    // `#` 交付产物(Artifact,会话/任务产出、已落盘)
    const { data: artifactList, loading: artifactsLoading } = useRequest(async () => {
      if (!workspaceId || !menuDataRequested) return [];
      const [err, res] = await apiInterceptors(listArtifacts({ workspace_id: workspaceId }));
      return err ? [] : (((res as any)?.items ?? res ?? []) as ArtifactRef[]);
    }, { refreshDeps: [workspaceId, menuDataRequested] });
    const allArtifacts: ArtifactRef[] = artifactList ?? [];

    // `#` 空间资产(Asset,带 maturity 沉淀)
    const { data: assetList, loading: assetsLoading } = useRequest(async () => {
      if (!workspaceId || !menuDataRequested) return [];
      const [err, res] = await apiInterceptors(listAssets({ workspace_id: workspaceId }));
      return err ? [] : (((res as any)?.items ?? res ?? []) as AssetRef[]);
    }, { refreshDeps: [workspaceId, menuDataRequested] });
    const allAssets: AssetRef[] = assetList ?? [];

    // 空间自定义命令:workspace_resource(type='command')。
    // physical_ref=命令标识,config_json={kind,description,payload}。
    // 与内置 3 条种子合并进 `/` 菜单「命令」组,新增命令无需发版。
    const { data: customCommandList } = useRequest(async () => {
      if (!workspaceId || !menuDataRequested) return [];
      const [err, res] = await apiInterceptors(listResources({ workspace_id: workspaceId, type: 'command' }));
      return err ? [] : ((res as any)?.items ?? res ?? []);
    }, { refreshDeps: [workspaceId, menuDataRequested] });

    // 权限等级选项:key 与后端 PermissionMode 对齐(plan/auto/manual),
    // 发送时写入 ext_info.permission_mode,接入 Agent 5 级工具权限链
    const permissionOptions: PlusMenuPermission[] = [
      { key: 'plan', label: '默认权限', description: '常规读写,敏感写操作需确认' },
      { key: 'auto', label: '完全访问', description: '放开全部工具与写操作权限' },
      { key: 'manual', label: '手动确认', description: '每个写工具都需人工确认' },
    ];

    // 后端上传返回的 preview_url 可能是相对路径(如 /api/v2/serve/file/files/...),
    // 前端静态导出可能与 API 不同源,直接放入 <img src> 会被浏览器按当前页面源解析,
    // 导致图片加载失败显示裂图。这里对相对路径补全 API 基址,与 resolveArtifactFileUrl 逻辑一致。
    const resolvePreviewUrl = (url: string): string => {
      if (!url) return '';
      if (url.startsWith('/')) {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || '';
        return `${apiBase}${url}`;
      }
      return transformFileUrl(url);
    };

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
      resolvePreviewUrl(r.image_url?.preview_url || r.file_url?.preview_url || r.audio_url?.preview_url || r.video_url?.preview_url || '');
    const isImageResource = (r: ResourceItem) => !!r.image_url;

    const hasContent = text.trim().length > 0 || resources.length > 0 || playbookCommand !== null;
    const popoverOverlay = '[&_.ant-popover-inner]:!p-0 [&_.ant-popover-inner]:!rounded-xl [&_.ant-popover-inner]:!shadow-xl';

    // 模型下拉:按提供商分组(组名来自 getModelProvider,保持添加顺序)
    const modelGroups = useMemo(() => {
      const map = new Map<string, IModelData[]>();
      for (const m of modelList) {
        const p = getModelProvider(m);
        if (!map.has(p)) map.set(p, []);
        map.get(p)!.push(m);
      }
      return [...map.entries()];
    }, [modelList]);

    const handleFileUpload = async (file: File) => {
      // 会话源:优先当前会话;缺失时经外部回调懒创建(不再静默跳过上传)
      let cid: string | undefined = conversationId;
      if (!cid && onEnsureConversation) {
        try {
          cid = (await onEnsureConversation()) ?? undefined;
        } catch {
          cid = undefined;
        }
      }
      if (!cid) {
        message.warning('当前没有可用的对话,无法上传文件,请先发起对话');
        return;
      }
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      setUploading(prev => [...prev, { id, file, status: 'uploading' }]);
      const formData = new FormData();
      formData.append('doc_files', file);
      const [err, res] = await apiInterceptors(
        postChatModeParamsFileLoad({ conversationId: cid, chatMode: 'chat_normal', data: formData, model: selectedModel, config: { timeout: 1000 * 60 * 60 } }),
      );
      setUploading(prev => prev.filter(u => u.id !== id));
      if (err) {
        setUploading(prev => [...prev, { id, file, status: 'error', error: String(err) }]);
        return;
      }
      const { fileUrl, previewUrl } = normalizeUploadRes(res);
      // 先写暂存域再写实例 state:若上传期间输入框因会话创建/分支切换被重挂载,
      // 旧实例的 setState 已失效,附件仍可由新实例从暂存域恢复
      const uploaded = buildResourceItem(file, fileUrl, previewUrl);
      const base = attachmentScopeKey ? getPendingResources(attachmentScopeKey) : resources;
      applyResources([...base, uploaded]);
    };

    const handleDrop = async (e: React.DragEvent) => {
      e.preventDefault();
      for (const f of Array.from(e.dataTransfer.files)) await handleFileUpload(f);
    };

    // 只读模式(查看角色):输入与发送整体禁用
    const inputDisabled = !!disabled || !!readOnly;

    const canSend = canSendSceneTask(text, resources.length > 0, playbookCommand);
    // 运行中且无可发送的新内容:提交按钮转为"进行中·可停止"状态;
    // 运行中继续输入了内容则恢复为可提交(发送新消息会先中止当前生成)
    const showStop = !!loading && !canSend;

    const handleSend = () => {
      if (readOnly || !canSend) return;
      const trimmed = text.trim();
      onSend({
        text: trimmed,
        resources: resources.length ? resources : undefined,
        model: selectedModel || undefined,
        playbookCommand: playbookCommand ?? undefined,
        skills: selectedSkills.length ? selectedSkills : undefined,
        mcps: selectedMcps.length ? selectedMcps : undefined,
        // @ 接管:会话级生效,每轮都带上,后端据此覆写主 Agent
        subAgent: activeSubAgent ?? undefined,
        // # 引用的交付资源(artifact/asset),已落盘不重复上传
        resourceRefs: resourceRefs.length ? resourceRefs : undefined,
        // 规划模式开启时强制 plan 档(消费侧写 ext_info.permission_mode)
        permission: planMode ? 'plan' : permission,
        media: Object.keys(mediaParams).length ? mediaParams : undefined,
        // 压缩模式开启时携带 forceCompress,本轮推理前强制压缩
        forceCompress: compactMode || undefined,
        // 已开启的自定义 toggle 命令:payload 合并后随 ext_info 下发
        commandPayload: activeCustomCommands.length
          ? activeCustomCommands.reduce((acc, c) => ({ ...acc, ...(c.payload || {}) }), {})
          : undefined,
      });
      setText('');
      applyResources([]);
      applyResourceRefs([]);
      setPlaybookCommand(null);
      setSelectedSkills([]);
      setSelectedMcps([]);
      setActiveTrigger(null);
      setPlanMode(false);
      setCompactMode(false);
      setActiveCustomCommands([]);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // 菜单打开时,方向键/回车/Esc 优先交给菜单消费(三个 trigger 共用同一套导航)
      if (activeTrigger && triggerMenuRef.current?.handleKey(e)) return;
      if (e.key === 'Enter' && !e.shiftKey) {
        // 输入法组词阶段的回车(选词/上屏)只作用于输入法,不触发提交,
        // 也不做 preventDefault,避免干扰候选词选择
        if (e.nativeEvent.isComposing || e.keyCode === 229) return;
        e.preventDefault();
        handleSend();
      }
    };

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const v = e.target.value;
      setText(v);
      // 统一 trigger 检测:`/` `@` `#` 在任意位置都能唤起(前置需为行首或空白),
      // 规则见 trigger-detect.ts。已选了剧本 chip 后 `/` 不再重复触发
      // (剧本单选,要换剧本先移除 chip)。
      const caret = (e.target as HTMLTextAreaElement).selectionStart ?? v.length;
      const next = detectTrigger(v, caret);
      // 首次唤起任一 trigger 时拉取 `@`/`#`/自定义命令数据源(进空间不一定用得到)
      if (next) setMenuDataRequested(true);
      setActiveTrigger(next && next.char === '/' && playbookCommand ? null : next);
    };

    /**
     * 清理输入里的 trigger token(`/xxx` `@xxx` `#xxx`)并关闭菜单、保留焦点。
     * 取代原先散落各处的行首锚定正则 —— 那些正则在句中触发时会误删前文。
     */
    const consumeTriggerToken = () => {
      if (activeTrigger) setText((prev) => stripTrigger(prev, activeTrigger));
      setActiveTrigger(null);
      textareaRef.current?.focus();
    };

    const pickPlaybook = (pb: { playbook_id: number; playbook_name: string }) => {
      setPlaybookCommand({ playbook_id: pb.playbook_id, playbook_name: pb.playbook_name });
      // 清掉触发用的 token,话题由用户随后输入
      consumeTriggerToken();
    };

    const toggleSkill = (skill: SkillRef) => {
      setSelectedSkills((prev) =>
        prev.some((s) => s.skill_code === skill.skill_code)
          ? prev.filter((s) => s.skill_code !== skill.skill_code)
          : [...prev, skill],
      );
    };

    const toggleMcp = (mcp: PlusMenuMcpRef) => {
      const key = String(mcp.id || mcp.uuid || mcp.name);
      setSelectedMcps((prev) =>
        prev.some((m) => String(m.id || m.uuid || m.name) === key)
          ? prev.filter((m) => String(m.id || m.uuid || m.name) !== key)
          : [...prev, mcp],
      );
    };

    // 会话命令数据源:`/` 菜单「命令」组 = 内置种子 + 空间自定义。
    // 与剧本/技能/MCP 的"资源引用"不同,命令选中即执行或切换模式。
    const builtinCommands: SessionCommandItem[] = [
      { command: '压缩上下文', name: '压缩上下文', description: '压缩当前会话上下文,释放上下文空间', action: 'compact', source: 'builtin' },
      { command: '清理会话', name: '清理会话', description: '开启新会话,清空当前上下文', action: 'clear', source: 'builtin' },
      { command: '规划模式', name: '规划模式', description: '本回合使用规划能力(plan 权限档)', action: 'plan', source: 'builtin' },
    ];

    const allCommands = useMemo<SessionCommandItem[]>(() => {
      const custom = (customCommandList ?? [])
        .filter((r: any) => r.is_active !== false)
        .map((r: any): SessionCommandItem => {
          let cfg: any = {};
          try {
            cfg = typeof r.config === 'string' ? JSON.parse(r.config || '{}') : r.config || {};
          } catch {
            cfg = {};
          }
          return {
            command: r.physical_ref || r.name,
            name: r.name,
            description: cfg.description,
            // 自定义命令统一按 toggle 处理:发送时 payload 合并进 ext_info
            action: 'custom',
            payload: cfg.payload,
            source: 'workspace',
          };
        });
      return [...builtinCommands, ...custom];
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [customCommandList]);

    // 已开启的自定义 toggle 命令(会话级 chip,发送时 payload 合并进 ext_info)
    const [activeCustomCommands, setActiveCustomCommands] = useState<SessionCommandItem[]>([]);

    /** `@` 选中:会话级接管,持续生效直到显式退出或改选他人 */
    const takeOverSubAgent = (agent: SubAgentRef) => {
      setActiveSubAgent(agent);
      consumeTriggerToken();
    };

    const removeSubAgent = () => setActiveSubAgent(null);

    /**
     * `#` 选中:加入引用列表。
     * P0 阶段引用进附件区展示,start/end 恒为当前文本末尾;
     * P1 输入框内联化后,同一份数据即可驱动真内联 chip。
     */
    const addResourceRef = (kind: 'artifact' | 'asset', ref: ArtifactRef | AssetRef) => {
      const meta =
        kind === 'artifact'
          ? {
              id: `artifact:${(ref as ArtifactRef).artifact_id}`,
              label: (ref as ArtifactRef).title,
              ref_id: (ref as ArtifactRef).artifact_id,
            }
          : {
              id: `asset:${(ref as AssetRef).asset_id}`,
              label: (ref as AssetRef).name,
              ref_id: (ref as AssetRef).asset_id,
            };
      setResourceRefs((prev) => {
        if (prev.some((r) => r.id === meta.id)) return prev;
        const next = [
          ...prev,
          { ...meta, kind, content_ref: ref.content_ref, start: text.length, end: text.length },
        ];
        if (attachmentScopeKey) setPendingResourceRefs(attachmentScopeKey, next);
        return next;
      });
      consumeTriggerToken();
    };

    const removeResourceRef = (id: string) =>
      applyResourceRefs(resourceRefs.filter((r) => r.id !== id));

    /** 会话命令:即时执行型(clear)与模式开关型(plan / compact) */
    const applySessionCommand = (cmd: SessionCommandItem) => {
      const action: SessionCommandAction = cmd.action;
      consumeTriggerToken();
      if (action === 'clear') {
        // 即时执行:清理会话(复用新建干净会话逻辑)
        onClearContext?.();
      } else if (action === 'plan') {
        // 模式 chip:规划模式开启,本回合按 plan 档发送
        setPlanMode(true);
      } else if (action === 'compact') {
        // 压缩模式:开启 chip,下一条发送携带 forceCompress,本轮推理前强制压缩
        setCompactMode(true);
      } else if (action === 'custom') {
        // 空间自定义 toggle 命令:chip 开关,发送时 payload 合并进 ext_info
        setActiveCustomCommands((prev) =>
          prev.some((c) => c.command === cmd.command)
            ? prev.filter((c) => c.command !== cmd.command)
            : [...prev, cmd],
        );
      }
    };

    /**
     * 三个 trigger 的统一选中入口。
     * `/` → 能力挂载(chip);`@` → 身份接管(banner,会话级);`#` → 对象引用(列表)。
     */
    const handleTriggerSelect = (sel: SceneTriggerSelection) => {
      switch (sel.type) {
        case 'addFile':
          fileInputRef.current?.click();
          consumeTriggerToken();
          break;
        case 'playbook':
          if (sel.playbook) pickPlaybook(sel.playbook);
          break;
        case 'skill':
          if (sel.skill) {
            toggleSkill(sel.skill);
            consumeTriggerToken();
          }
          break;
        case 'mcp':
          if (sel.mcp) {
            toggleMcp(sel.mcp);
            consumeTriggerToken();
          }
          break;
        case 'command':
          if (sel.command) applySessionCommand(sel.command);
          break;
        case 'subAgent':
          if (sel.subAgent) takeOverSubAgent(sel.subAgent);
          break;
        case 'artifact':
          if (sel.artifact) addResourceRef('artifact', sel.artifact);
          break;
        case 'asset':
          if (sel.asset) addResourceRef('asset', sel.asset);
          break;
      }
    };

    const visiblePlaybooks = playbooks ?? [];

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
          {/* 只读提示:查看角色(space.chat.use 无权限)不能发起对话 */}
          {readOnly && (
            <div className="px-4 pt-3 pb-1 text-xs text-gray-400 dark:text-gray-500">
              只读：查看角色不能发起对话
            </div>
          )}
          {/* SECTION 0 — `@` 接管态 banner(会话级 sticky,常驻直到显式退出或改选他人) */}
          {activeSubAgent && (
            <div className="mx-4 mt-3 flex items-center gap-2 rounded-lg border border-purple-200 dark:border-purple-800/60 bg-purple-50 dark:bg-purple-900/20 px-3 py-2">
              <RobotOutlined className="text-purple-500 text-sm flex-shrink-0" />
              <span className="min-w-0 flex-1 truncate text-xs text-purple-700 dark:text-purple-300">
                当前由 <span className="font-medium">{activeSubAgent.name}</span> 接管
                <span className="ml-1 text-purple-400 dark:text-purple-500">· 后续对话直接由它回复</span>
              </span>
              <button
                type="button"
                className="flex-shrink-0 text-xs text-purple-500 hover:text-purple-700 dark:hover:text-purple-300 px-1.5 py-0.5 rounded transition-colors"
                onClick={removeSubAgent}
                title="退出接管,恢复空间默认 Agent"
              >
                退出
              </button>
            </div>
          )}

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
                    onClick={() => { applyResources([]); setUploading([]); }}
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
                          ? <img src={preview} className="w-full h-full object-cover" onError={(e) => { const t = e.currentTarget; t.onerror = null; t.style.display = 'none'; if (t.parentElement) { t.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center ${theme.bg}"><span class="text-xl">📷</span></div>`; } }} />
                          : <div className={`w-full h-full flex items-center justify-center ${theme.bg}`}>
                              <FileOutlined className={`${theme.icon} text-xl`} />
                            </div>}
                      </div>
                      <div className="mt-1 max-w-[60px]">
                        <p className="text-xs text-gray-600 dark:text-gray-400 truncate">{name}</p>
                      </div>
                      <button
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200 shadow hover:bg-red-50 hover:border-red-300 hover:text-red-500"
                        onClick={() => applyResources(resources.filter((_, j) => j !== i))}
                      >
                        <CloseOutlined className="text-[10px]" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* SECTION 1.3 — `#` 引用的资源(交付产物/空间资产,可多选可移除) */}
          {resourceRefs.length > 0 && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              {resourceRefs.map((ref) => (
                <SelectionChip
                  key={ref.id}
                  theme={ref.kind === 'artifact' ? 'amber' : 'indigo'}
                  prefix={ref.kind === 'artifact' ? '交付' : '资产'}
                  label={ref.label}
                  onRemove={() => removeResourceRef(ref.id)}
                  removeTitle="移除引用"
                />
              ))}
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
          {/* SECTION 1.5 — selected playbook command chip (single, removable),前缀 / 标识剧本命令 */}
          {playbookCommand && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              <SelectionChip
                theme="indigo"
                prefix="/"
                label={playbookCommand.playbook_name}
                onRemove={() => setPlaybookCommand(null)}
                removeTitle="移除剧本"
              />
            </div>
          )}
          {/* SECTION 1.6 — selected skill chips (multi, removable),前缀 技能 标识 */}
          {selectedSkills.length > 0 && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              {selectedSkills.map((skill) => (
                <SelectionChip
                  key={skill.skill_code}
                  theme="violet"
                  prefix="技能"
                  icon={skill.icon
                    ? <img src={skill.icon} alt="" className="h-3.5 w-3.5 rounded object-cover" />
                    : undefined}
                  label={skill.name}
                  onRemove={() => toggleSkill(skill)}
                  removeTitle="移除技能"
                />
              ))}
            </div>
          )}
          {/* SECTION 1.7 — selected MCP chips (multi, removable),前缀 MCP 标识 */}
          {selectedMcps.length > 0 && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              {selectedMcps.map((mcp) => {
                const key = String(mcp.id || mcp.uuid || mcp.name);
                return (
                  <SelectionChip
                    key={key}
                    theme="emerald"
                    prefix="MCP"
                    icon={mcp.icon
                      ? <img src={mcp.icon} alt="" className="h-3.5 w-3.5 rounded object-cover" />
                      : undefined}
                    label={mcp.name}
                    onRemove={() => setSelectedMcps((prev) => prev.filter((m) => String(m.id || m.uuid || m.name) !== key))}
                    removeTitle="移除 MCP"
                  />
                );
              })}
            </div>
          )}

          {/* SECTION 1.8 — plan mode chip(/规划模式 命令触发,可移除) */}
          {planMode && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              <SelectionChip
                theme="cyan"
                prefix="规划"
                label="本回合使用规划能力"
                onRemove={() => setPlanMode(false)}
                removeTitle="退出规划模式"
              />
            </div>
          )}
          {/* SECTION 1.9 — compact mode chip(/压缩上下文 命令触发,可移除) */}
          {compactMode && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              <SelectionChip
                theme="amber"
                prefix="压缩"
                label="本回合发送前压缩上下文"
                onRemove={() => setCompactMode(false)}
                removeTitle="取消压缩"
              />
            </div>
          )}
          {/* SECTION 1.10 — 空间自定义 toggle 命令 chip(可多个,发送时 payload 合并进 ext_info) */}
          {activeCustomCommands.length > 0 && (
            <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
              {activeCustomCommands.map((cmd) => (
                <SelectionChip
                  key={cmd.command}
                  theme="cyan"
                  prefix="命令"
                  label={cmd.name}
                  onRemove={() =>
                    setActiveCustomCommands((prev) => prev.filter((c) => c.command !== cmd.command))
                  }
                  removeTitle="关闭该命令"
                />
              ))}
            </div>
          )}

          {/* SECTION 2 — textarea (borderless, card is the only border) */}
          <div className="relative">
            <SceneTriggerMenu
              ref={triggerMenuRef}
              trigger={activeTrigger}
              playbooks={visiblePlaybooks}
              skills={allSkills}
              mcps={allMcps}
              mcpsLoading={mcpLoading}
              commands={allCommands}
              subAgents={allSubAgents}
              subAgentsLoading={subAgentsLoading}
              artifacts={allArtifacts}
              artifactsLoading={artifactsLoading}
              assets={allAssets}
              assetsLoading={assetsLoading}
              onSelect={handleTriggerSelect}
              onAddFile={() => fileInputRef.current?.click()}
              onClose={() => setActiveTrigger(null)}
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
                  placeholder="输入指令给 Agent…(/ 选择剧本/技能/MCP/命令,+ 添加文件)"
                  className="!text-sm !bg-transparent !border-0 !resize-none placeholder:!text-gray-400 !text-gray-800 dark:!text-gray-200 !shadow-none !p-0 !min-h-[60px]"
                  autoSize={{ minRows: 2, maxRows: 8 }}
                  disabled={inputDisabled}
                />
              </div>
            </SceneTriggerMenu>

            {/* 清理上下文:浮动在输入区右上角,半透明毛玻璃圆形按钮,hover 点亮 */}
            {onClearContext && (
              <button
                type="button"
                className="absolute top-2 right-2 z-10 h-7 w-7 rounded-full flex items-center justify-center border border-gray-200/70 dark:border-gray-600/60 bg-white/70 dark:bg-[#232734]/70 backdrop-blur-sm text-gray-300 dark:text-gray-500 shadow-sm hover:text-red-500 hover:border-red-200 dark:hover:border-red-700 hover:bg-red-50/90 dark:hover:bg-red-900/30 transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                onClick={onClearContext}
                disabled={!conversationId || disabled || loading}
                title="清理上下文(新开会话)"
              >
                <ClearOutlined className="text-xs" />
              </button>
            )}
          </div>

          {/* SECTION 3 — footer toolbar: left tools / right send */}
          <div className="flex items-center justify-between gap-2 px-3 pb-3 min-w-0">
            <div className="flex items-center gap-2 min-w-0 flex-shrink overflow-visible">
              {/* + 菜单:添加文件 / 剧本 / 技能 / MCP / 命令(与 / 菜单同一套数据与选中结果) */}
              <PlusMenu
                onAddFile={() => fileInputRef.current?.click()}
                playbooks={visiblePlaybooks}
                selectedPlaybook={playbookCommand}
                onPlaybookChange={(pb) => { if (pb) pickPlaybook(pb); }}
                skills={allSkills}
                selectedSkills={selectedSkills}
                onSkillsChange={setSelectedSkills}
                mcps={allMcps}
                mcpsLoading={mcpLoading}
                selectedMcps={selectedMcps}
                onMcpsChange={setSelectedMcps}
                disabled={!conversationId || inputDisabled || loading}
              />
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
                  disabled={inputDisabled}
                  title="重试"
                >
                  <ReloadOutlined className="text-sm" />
                </button>
              )}

              {/* 权限等级 pill:常驻展示,点击弹层切换 */}
              <Popover
                trigger="click"
                placement="topLeft"
                arrow={false}
                overlayClassName={popoverOverlay}
                content={(
                  <div className="w-64 py-1">
                    {permissionOptions.map((p) => (
                      <button
                        type="button"
                        key={p.key}
                        className="flex w-full items-center gap-2.5 px-2.5 py-2 text-[13px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/60 rounded-lg transition-colors text-left"
                        onClick={() => setPermission(p.key)}
                      >
                        <SafetyOutlined className="text-xs text-amber-500" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate">{p.label}</span>
                          {p.description && <span className="block truncate text-[11px] text-gray-400">{p.description}</span>}
                        </span>
                        {permission === p.key && <CheckOutlined className="ml-auto text-xs text-indigo-500" />}
                      </button>
                    ))}
                  </div>
                )}
              >
                <button
                  type="button"
                  disabled={inputDisabled}
                  className={classNames(
                    'flex h-8 items-center gap-1 rounded-full px-2.5 text-xs font-medium transition-all flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed',
                    permission === 'auto'
                      ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40'
                      : 'bg-gray-100 dark:bg-gray-700/60 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                  )}
                >
                  <SafetyOutlined className="text-xs" />
                  {permissionOptions.find((p) => p.key === permission)?.label}
                  <DownOutlined className="text-[9px] opacity-60" />
                </button>
              </Popover>

              {/* 多媒体参数设定：仅多媒体 Agent 展示（与通用聊天页输入框一致） */}
              {isMultimediaApp(appInfo) && (
                <MediaParamsButton
                  capability={getMultimediaConfig(appInfo)?.capability}
                  modelPool={
                    getMultimediaConfig(appInfo)?.capability === 'video'
                      ? getMultimediaConfig(appInfo)?.video_models
                      : getMultimediaConfig(appInfo)?.image_models
                  }
                  value={mediaParams}
                  onChange={setMediaParams}
                />
              )}
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
              <ContextUsageDetail
                metrics={usageMetrics ?? null}
                open={usageDrawerOpen}
                onOpenChange={setUsageDrawerOpen}
              />
              {/* model selector pill */}
              <Popover
                content={(
                  <div className="w-64 max-h-64 overflow-y-auto py-1">
                    <div className="px-3 pt-1.5 pb-1 text-[11px] font-medium text-gray-400 dark:text-gray-500">选择模型</div>
                    {modelGroups.length === 0 && <div className="px-3 py-2 text-xs text-gray-400">暂无可用模型</div>}
                    {modelGroups.map(([provider, models]) => (
                      <div key={provider} className="mb-0.5">
                        <div className="px-3 pt-2 pb-1 text-[11px] font-semibold text-gray-400 dark:text-gray-500">{provider}</div>
                        {models.map(m => (
                          <button
                            type="button"
                            key={m.model_name}
                            className="flex w-full items-center gap-2.5 px-3 py-2 cursor-pointer rounded-lg transition-colors text-left hover:bg-gray-100 dark:hover:bg-gray-700/60"
                            onClick={() => {
                              userSelectedRef.current = true;
                              systemDefaultRef.current = false;
                              updateSelectedModel(m.model_name);
                            }}
                          >
                            <ModelIcon model={m.model_name} width={18} height={18} />
                            <span className="min-w-0 flex-1 truncate text-[13px] text-gray-700 dark:text-gray-300">{m.model_name}</span>
                            {selectedModel === m.model_name && (
                              <CheckOutlined className="ml-auto text-xs text-indigo-500" />
                            )}
                          </button>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
                trigger="click"
                placement="topRight"
                overlayClassName={popoverOverlay}
              >
                <button
                  type="button"
                  className="flex items-center gap-1.5 h-8 px-2.5 rounded-full bg-gray-100 dark:bg-gray-700/60 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all flex-shrink-0"
                >
                  <ModelIcon model={selectedModel} width={16} height={16} />
                  <span className="text-xs font-medium max-w-[96px] truncate">
                    {selectedModel || '选择模型'}
                  </span>
                  <DownOutlined className="text-[9px] text-gray-400" />
                </button>
              </Popover>
              {/* 语音输入:浏览器原生 SpeechRecognition 转文字 */}
              <VoiceInputButton
                disabled={inputDisabled}
                onTranscript={(t) => { setText((prev) => (prev ? `${prev}${t}` : t)); textareaRef.current?.focus(); }}
              />
              <button
                className={classNames(
                  'w-9 h-9 flex items-center justify-center transition-all !border-0 flex-shrink-0 rounded-full',
                  showStop || hasContent
                    ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 shadow-md hover:shadow-lg text-white'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed',
                  showStop && 'ws-stop-btn--running'
                )}
                onClick={showStop ? onStop : handleSend}
                disabled={showStop ? (!onStop || inputDisabled) : (!hasContent || inputDisabled || !canSend)}
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