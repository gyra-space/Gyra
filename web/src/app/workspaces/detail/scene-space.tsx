'use client';

import { useMemo } from 'react';
import { Button, Spin, Tag, Tooltip } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, ExportOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { GPTVis } from '@antv/gpt-vis';
import dayjs from 'dayjs';
import markdownComponents, { markdownPlugins, preprocessLaTeX } from '@/components/chat/chat-content-components/config';
import ChatSession from '@/components/chat/chat-session';
import { apiInterceptors, getArtifactInfo, getDeliveryInfo, listArtifacts } from '@/client/api';
import { resolveFileDownloadUrl, transformFileUrl } from '@/utils';
import { Lobby } from './lobby';
import { AppCardPage } from './app-card/AppCardPage';
import { type AppCardItem } from '@/client/api/app-card';
import { FlywheelWorkspace } from './flywheel';
import { AgentWorkspaceRenderer } from './agent-workspace-renderer';
import { extractAskUserData } from './scene-ask-user-card';
import { parseWorkspaceView, deliverableFileToExhibit } from './parse-workspace-view';
import { parseSceneAgentWorkspaceString } from './parse-scene-agent-workspace-string';
import { ExhibitHost, resolveAgentFilePreviewUrl } from './lobby-exhibit';
import { statusLabel } from './scene-task-rail';
import { EcpProposalDetail } from './ecp-proposal-detail';
import SkillContentRenderer from '@/components/chat/chat-content-components/VisComponents/VisManusRightPanel/renderers/SkillContentRenderer';
import { DataAssetsTab } from './assets/data-assets-tab';
import TriggersTable from './tasks/triggers-table';
import type { WorkspaceView } from './agent-workspace-types';
import type { WorkspaceDeliverableFile } from './agent-workspace-types';
import type { LobbyExhibit, LobbyExhibitKind } from './agent-workspace-types';
import type { DetailContext } from './agent-types';

export interface SceneSpaceProps {
  context: DetailContext;
  previewItem?: any;
  activeTask?: any;
  workspaceId: number;
  workspaceCode: string;
  /** 场景空间主 agent 的 app_code(子任务对话内联渲染时兜底) */
  appCode?: string;
  playbooks?: { playbook_id: number; playbook_name: string }[];
  onBack: () => void;
  onSelectTask?: (taskId: number) => void;
  onSelectArtifact?: (artifact: any) => void;
  onSelectDelivery?: (delivery: any) => void;
  /** 应用卡片:点击大厅应用图标 → 打开完整应用页 */
  onSelectAppCard?: (card: AppCardItem) => void;
  onProposalResolved?: () => void;
  /** 进入飞轮工作台 */
  onEnterFlywheel?: () => void;
  /** 导览卡动作(壳内切换,不整页跳转) */
  onGuide?: (action: 'ask' | 'run_playbook' | 'triggers' | 'data_assets') => void;
  /** 工作台待办点击(与 rail 收件箱一致) */
  onSelectInbox?: (item: any) => void;
  /** 推荐问题:填入输入框并聚焦 */
  onAsk?: (text?: string) => void;
  /** 剧本快捷执行:@引用 带入输入框并聚焦 */
  onRunPlaybook?: (pb: { playbook_id: number; playbook_name: string }) => void;
  /** 任务/介入刷新信号(最近产出/交付/待办同步刷新) */
  listsRefreshKey?: number;
}

const STATUS_COLOR: Record<string, string> = {
  running: 'processing',
  pending_trigger: 'warning',
  draft: 'default',
  blocked: 'warning',
  awaiting_human: 'warning',
  delivered: 'success',
  closed: 'success',
  done: 'success',
  failed: 'error',
  pending: 'default',
};

const DELIVERY_STATUS_COLOR: Record<string, string> = {
  sent: 'success',
  failed: 'error',
  pending: 'default',
};

function fmtTime(v?: string | null): string {
  return v ? dayjs(v).format('MM-DD HH:mm') : '—';
}

function fmtSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="ws-preview__field">
      <span className="ws-preview__field-key">{k}</span>
      <span className="ws-preview__field-value">{v}</span>
    </div>
  );
}

/** 任务最终结果(切换任务时中间区默认视图):
 * 聚焦展示最终回复(整段 markdown,Agent 空间过窄看不全) + 交付文件列表,
 * 去掉基本信息/消耗等杂项。由左栏任务/会话列表与大堂任务卡片切换任务时触发。 */
function TaskDetail({
  task,
  artifacts,
  onSelectArtifact,
}: {
  task: any;
  artifacts: any[];
  onSelectArtifact?: (a: any) => void;
}) {
  const finals = artifacts.filter((a: any) => a.type === 'final_message');
  const files = artifacts.filter((a: any) => a.type === 'file');
  const others = artifacts.filter((a: any) => a.type !== 'final_message' && a.type !== 'file');
  return (
    <div className="ws-preview">
      <div className="ws-preview__head">
        <span className="ws-preview__title">{task.title || `Task ${task.id}`}</span>
        <Tag color={STATUS_COLOR[task.status] || 'default'}>{statusLabel(task.status)}</Tag>
      </div>
      <section className="ws-preview__section">
        <div className="ws-preview__section-title">最终回复</div>
        {finals.length === 0 && <div className="ws-preview__empty">暂无文本回复</div>}
        {finals.map((a: any) => (
          <div key={a.id} className="ws-preview__markdown" style={{ marginBottom: 12 }}>
            {a.content_text ? <Markdown text={a.content_text} /> : <div className="ws-preview__empty">(无内容)</div>}
          </div>
        ))}
      </section>
      <section className="ws-preview__section">
        <div className="ws-preview__section-title">交付文件 ({files.length})</div>
        {files.length === 0 && <div className="ws-preview__empty">暂无交付文件</div>}
        {files.map((a: any) => (
          <div
            key={a.id}
            className="ws-preview__field ws-td-link"
            role="button"
            tabIndex={0}
            onClick={() => (a.content_ref ? window.open(a.content_ref, '_blank') : onSelectArtifact?.(a))}
            onKeyDown={(e) => { if (e.key === 'Enter') (a.content_ref ? window.open(a.content_ref, '_blank') : onSelectArtifact?.(a)); }}
          >
            <span className="ws-preview__field-value">{a.title || `artifact_${a.id}`}</span>
            <Tag color="blue">文件</Tag>
            {a.provenance?.file_size ? (
              <span className="ws-preview__field-key">{fmtSize(a.provenance.file_size)}</span>
            ) : null}
          </div>
        ))}
        {others.map((a: any) => (
          <div
            key={a.id}
            className="ws-preview__field ws-td-link"
            role="button"
            tabIndex={0}
            onClick={() => onSelectArtifact?.(a)}
            onKeyDown={(e) => { if (e.key === 'Enter') onSelectArtifact?.(a); }}
          >
            <span className="ws-preview__field-value">{a.title || `artifact_${a.id}`}</span>
            <Tag>{a.type}</Tag>
          </div>
        ))}
      </section>
    </div>
  );
}

// 按 key 识别长文本内容字段,走 markdown 渲染而非纯文本
const CONTENT_KEYS = new Set(['content_text', 'message', 'output', 'content', 'vis_final']);

function isHtml(text: string): boolean {
  const head = text.trimStart().slice(0, 200).toLowerCase();
  return head.startsWith('<!doctype') || head.startsWith('<html');
}

function Markdown({ text }: { text: string }) {
  return (
    // @ts-ignore rehypePlugins type mismatch is pre-existing repo-wide (see chat-detail-content.tsx)
    <GPTVis components={markdownComponents} {...markdownPlugins}>
      {preprocessLaTeX(text)}
    </GPTVis>
  );
}

/** 历史脏数据兜底:vis_final 协议帧曾被错存为交付物内容,识别后走 workspace 渲染而非 raw JSON。 */
function tryParseVisWorkspaceView(text: string): WorkspaceView | null {
  if (!text.includes('scene_agent_workspace')) return null;
  const parsed = parseSceneAgentWorkspaceString(text);
  if (!parsed || !Array.isArray(parsed.execution)) return null;
  return parseWorkspaceView(parsed, null);
}

/** 内容渲染器:html → 沙箱 iframe;JSON → 格式化代码块;长文本 → markdown。 */
function ContentView({ text }: { text: string }) {
  if (isHtml(text)) {
    return (
      <iframe
        className="ws-preview__html"
        sandbox="allow-same-origin"
        srcDoc={text}
        title="content preview"
      />
    );
  }
  const visView = tryParseVisWorkspaceView(text);
  if (visView) {
    return <AgentWorkspaceRenderer view={visView} />;
  }
  const trimmed = text.trim();
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      const pretty = JSON.stringify(JSON.parse(trimmed), null, 2);
      return (
        <div className="ws-preview__markdown">
          <Markdown text={'```json\n' + pretty + '\n```'} />
        </div>
      );
    } catch {
      // 非合法 JSON,按 markdown 渲染
    }
  }
  return (
    <div className="ws-preview__markdown">
      <Markdown text={text} />
    </div>
  );
}

/** 把 payload 的原始值字段渲染为键值列表,内容字段走渲染器,复杂字段兜底 JSON。 */
function PayloadFields({ payload }: { payload: Record<string, any> }) {
  const { contents, primitives, complex } = useMemo(() => {
    const contents: Array<[string, string]> = [];
    const primitives: Array<[string, string]> = [];
    const complex: Array<[string, string]> = [];
    Object.entries(payload || {}).forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      if (typeof v === 'string' && CONTENT_KEYS.has(k) && v.trim().length > 0) {
        contents.push([k, v]);
      } else if (['string', 'number', 'boolean'].includes(typeof v)) {
        primitives.push([k, String(v)]);
      } else {
        complex.push([k, JSON.stringify(v, null, 2)]);
      }
    });
    return { contents, primitives, complex };
  }, [payload]);

  return (
    <div className="ws-preview__fields">
      {contents.map(([k, v]) => (
        <section key={k} className="ws-preview__section">
          <div className="ws-preview__section-title">{k}</div>
          <ContentView text={v} />
        </section>
      ))}
      {primitives.length > 0 && (
        <div className="ws-preview__kv">
          {primitives.map(([k, v]) => (
            <div key={k} className="ws-preview__field">
              <span className="ws-preview__field-key">{k}</span>
              <span className="ws-preview__field-value">{v}</span>
            </div>
          ))}
        </div>
      )}
      {complex.map(([k, v]) => (
        <div key={k} className="ws-preview__field ws-preview__field--block">
          <span className="ws-preview__field-key">{k}</span>
          <pre className="ws-preview__json">{v}</pre>
        </div>
      ))}
      {contents.length === 0 && primitives.length === 0 && complex.length === 0 && (
        <div className="ws-preview__empty">暂无详情数据</div>
      )}
    </div>
  );
}

/** 解析 artifact content_ref 为可访问 URL(支持 gyra-fs:// / agent_files 下载 / 相对路径)。
 * agent_files 直接下载路径恒返回 octet-stream+attachment,iframe 无法内联渲染 HTML 等类型;
 * 统一路由到 preview 端点(按文件名推断 MIME,对 text/html 返回 inline),与对话侧交付文件预览行为一致。 */
function resolveArtifactFileUrl(raw: string): string {
  if (!raw) return '';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  if (raw.startsWith('gyra-fs://')) {
    return `${apiBaseUrl}/api/v2/serve/file/files/preview?uri=${encodeURIComponent(raw)}`;
  }
  const agentFilePreview = resolveAgentFilePreviewUrl(raw);
  if (agentFilePreview) return agentFilePreview;
  if (raw.startsWith('/')) return `${apiBaseUrl}${raw}`;
  return transformFileUrl(raw);
}

/** 触发文件下载(动态创建 a 标签) */
function downloadFile(url: string, fileName: string) {
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName || 'download';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/** 判断 content_ref 是否为可在浏览器预览的类型(html/pdf/image) */
function isPreviewableFile(contentRef: string): boolean {
  const ext = contentRef.split('.').pop()?.toLowerCase() || '';
  return ['html', 'htm', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext);
}

/* ═══════════════════════════════════════════════════════════════
   文件类文章物 → 大厅 Exhibit:让"最近产出"里的文件真正打开/预览
   ═══════════════════════════════════════════════════════════════ */

/** 扩展名 → Exhibit kind(与 agent-workspace-renderer 的 render_type 推断保持一致) */
const EXHIBIT_KIND_BY_EXT: Record<string, LobbyExhibitKind> = {
  png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', svg: 'image', webp: 'image',
  mp4: 'video', mov: 'video', webm: 'video', avi: 'video', mkv: 'video',
  mp3: 'audio', wav: 'audio', ogg: 'audio', m4a: 'audio', flac: 'audio',
  pdf: 'pdf',
  md: 'markdown', markdown: 'markdown',
  html: 'html', htm: 'html',
  csv: 'table', xls: 'file', xlsx: 'file',
  ppt: 'slides', pptx: 'slides',
  py: 'code', js: 'code', jsx: 'code', ts: 'code', tsx: 'code', java: 'code', go: 'code',
  rs: 'code', c: 'code', cpp: 'code', sql: 'code', xml: 'code', css: 'code', sh: 'code', vue: 'code',
  json: 'data', yaml: 'data', yml: 'data',
  txt: 'text', log: 'text',
  zip: 'file', tar: 'file', gz: 'file',
};

/** 由文件名 + mime_type 推断 Exhibit kind,未知类型兜底 file(仅下载) */
function inferExhibitKind(fileName: string, mime?: string): LobbyExhibitKind {
  const m = (mime || '').toLowerCase();
  if (m.startsWith('image/')) return 'image';
  if (m.startsWith('video/')) return 'video';
  if (m.startsWith('audio/')) return 'audio';
  if (m.includes('pdf')) return 'pdf';
  const ext = (fileName || '').split('.').pop()?.toLowerCase() || '';
  return EXHIBIT_KIND_BY_EXT[ext] || 'file';
}

/** 把文件类文章物适配为大厅 Exhibit(真正打开/预览文件内容) */
function buildArtifactExhibit(artifact: any, resolvedUrl: string): LobbyExhibit | null {
  if (!resolvedUrl) return null;
  const prov = artifact?.provenance || {};
  return {
    exhibit_id: `artifact_${artifact.id}`,
    kind: inferExhibitKind(artifact.title || '', prov.mime_type),
    title: artifact.title || `artifact_${artifact.id}`,
    source: {
      url: resolvedUrl,
      mime_type: prov.mime_type,
      file_size: prov.file_size,
    },
    actions: ['preview', 'download'],
  };
}

/** artifact_produced 等只带 id 的事件:拉取 artifact 详情后渲染内容 */
function ArtifactPreview({ artifactId, title, type }: { artifactId: number; title?: string; type?: string }) {
  const { data: res, loading } = useRequest(
    async () => apiInterceptors(getArtifactInfo(artifactId)),
    { refreshDeps: [artifactId] },
  );
  const artifact = res?.[1];
  if (loading) return <Spin />;
  if (!artifact) return <div className="ws-preview__empty">交付物不存在或已删除</div>;
  const content = artifact.content_text || '';
  const fileUrl = artifact.content_ref || '';
  const resolvedUrl = fileUrl ? resolveArtifactFileUrl(fileUrl) : '';
  const fileSize = artifact.provenance?.file_size;
  const previewable = fileUrl ? isPreviewableFile(fileUrl) : false;
  // 文件类文章物:用通用 ExhibitHost 真正打开/预览文件内容(优先于原文内容)
  const fileExhibit = buildArtifactExhibit(artifact, resolvedUrl);
  return (
    <div className="ws-preview">
      {fileExhibit ? (
        <ExhibitHost exhibit={fileExhibit} />
      ) : (
        <>
          <div className="ws-preview__head">
            <span className="ws-preview__title">{artifact.title || title || `artifact_${artifactId}`}</span>
            {(artifact.type || type) && <Tag color="blue">{artifact.type || type}</Tag>}
            {artifact.current_version != null && <Tag>v{artifact.current_version}</Tag>}
            {fileUrl && (
              <span className="ws-preview__head-tools">
                {previewable && (
                  <Tooltip title="新窗口打开">
                    <button type="button" className="ws-exhibit__tool" aria-label="新窗口打开" onClick={() => window.open(resolvedUrl, '_blank')}>
                      <ExportOutlined />
                    </button>
                  </Tooltip>
                )}
                <Tooltip title="下载">
                  <button
                    type="button"
                    className="ws-exhibit__tool"
                    aria-label="下载"
                    onClick={() => downloadFile(resolveFileDownloadUrl(resolvedUrl), artifact.title || `artifact_${artifactId}`)}
                  >
                    <DownloadOutlined />
                  </button>
                </Tooltip>
              </span>
            )}
          </div>
          {content ? (
            <section className="ws-preview__section">
              <div className="ws-preview__section-title">内容</div>
              <ContentView text={content} />
            </section>
          ) : (
            <PayloadFields payload={artifact} />
          )}
        </>
      )}
    </div>
  );
}

/** 交付详情:拉取 delivery 详情,展示基本信息 + 关联 artifact 内容/文件下载 */
function DeliveryPreview({ deliveryId, title }: { deliveryId: number; title?: string }) {
  const { data: res, loading } = useRequest(
    async () => apiInterceptors(getDeliveryInfo(deliveryId)),
    { refreshDeps: [deliveryId] },
  );
  const delivery = res?.[1];
  if (loading) return <Spin />;
  if (!delivery) return <div className="ws-preview__empty">交付记录不存在或已删除</div>;

  // 关联 artifact:delivery 通常引用一个 artifact_id,拉取其内容/文件
  const artifactId = delivery.artifact_id;
  return (
    <div className="ws-preview">
      <div className="ws-preview__head">
        <span className="ws-preview__title">{delivery.title || title || `delivery_${deliveryId}`}</span>
        <Tag color={DELIVERY_STATUS_COLOR[delivery.status] || 'default'}>{delivery.status}</Tag>
      </div>
      <section className="ws-preview__section">
        <div className="ws-preview__section-title">基本信息</div>
        <div>
          <KV k="分类" v={delivery.category || '—'} />
          <KV k="渠道" v={delivery.channel || '—'} />
          <KV k="目标" v={delivery.target || '—'} />
          <KV k="状态" v={delivery.status || '—'} />
          <KV k="发送时间" v={fmtTime(delivery.sent_at || delivery.gmt_created)} />
          {delivery.gmt_modified && <KV k="更新时间" v={fmtTime(delivery.gmt_modified)} />}
        </div>
      </section>
      {delivery.message && (
        <section className="ws-preview__section">
          <div className="ws-preview__section-title">投递消息</div>
          <div className="ws-preview__markdown">{delivery.message}</div>
        </section>
      )}
      {artifactId && (
        <section className="ws-preview__section">
          <div className="ws-preview__section-title">关联交付物</div>
          <ArtifactPreview artifactId={artifactId} />
        </section>
      )}
    </div>
  );
}

/** 交付文件预览:适配为大厅通用 Exhibit,由 ExhibitHost 按 kind 渲染
 * (图片/视频/音频/表格/幻灯片/HTML/PDF/Markdown/Code 等统一入口) */
function DeliverableFilePreview({ file }: { file: WorkspaceDeliverableFile }) {
  return <ExhibitHost exhibit={deliverableFileToExhibit(file)} />;
}

/** Agent 步骤(工具调用/思考)富预览 */
function StepPreview({ step }: { step: any }) {
  const payload = step?.payload || {};
  const output = typeof payload.output === 'string' ? payload.output : null;
  // 预加载技能步骤:复用 SkillContentRenderer 渲染 <skill_content>(技能头部 +
  // SKILL.md 全文 + 文件预览),与 skill 工具调用结果的右侧展示体验一致。
  if (step?.type === 'skill_loaded' && step?.skill_xml) {
    return (
      <div className="ws-preview">
        <div className="ws-preview__head">
          <span className="ws-preview__title">{step.title || '已预加载技能'}</span>
          <Tag color="geekblue">已预加载</Tag>
        </div>
        <div className="ws-preview__skill">
          <SkillContentRenderer
            outputs={[{ output_type: 'text', content: step.skill_xml }]}
            skillName={step.title}
          />
        </div>
      </div>
    );
  }
  const actionInput = payload.action_input;
  // ask_user 交互:确认卡片已渲染在 Agent 空间 feed(可交互并能续跑对话),
  // 此处避免再渲染一个无 ChatContentContext 的失效 VisConfirmCard,改为只读提示。
  const askUserData = output ? extractAskUserData(output) : null;
  return (
    <div className="ws-preview">
      <div className="ws-preview__head">
        <span className="ws-preview__title">{step?.title || '步骤详情'}</span>
        {payload.action && <Tag color="blue">{payload.action}</Tag>}
        {step?.status && <Tag color={STATUS_COLOR[step.status] || 'default'}>{step.status}</Tag>}
      </div>
      {actionInput && (
        <section className="ws-preview__section">
          <div className="ws-preview__section-title">输入参数</div>
          <pre className="ws-preview__json">{JSON.stringify(actionInput, null, 2)}</pre>
        </section>
      )}
      {askUserData ? (
        <section className="ws-preview__section">
          <div className="ws-preview__section-title">待你确认</div>
          <div className="ws-preview__ask-note">
            Agent 正在等待你的确认，请在右侧 Agent 空间的确认卡片中选择/输入后继续。
          </div>
        </section>
      ) : output ? (
        <section className="ws-preview__section">
          <div className="ws-preview__section-title">
            {payload.step_type === 'thinking' ? '内容' : '执行结果'}
          </div>
          <ContentView text={output} />
        </section>
      ) : null}
      {!actionInput && !output && <PayloadFields payload={payload} />}
    </div>
  );
}

export function SceneSpace({
  context,
  previewItem,
  activeTask,
  workspaceId,
  workspaceCode,
  appCode,
  playbooks,
  onBack,
  onSelectTask,
  onSelectArtifact,
  onSelectDelivery,
  onSelectAppCard,
  onProposalResolved,
  onEnterFlywheel,
  onGuide,
  onSelectInbox,
  onAsk,
  onRunPlaybook,
  listsRefreshKey,
}: SceneSpaceProps) {
  const taskId = context === 'task-detail' && previewItem?.id ? previewItem.id : undefined;
  // 点击任务卡片走 handlePreview(不进任务对话),activeTask 不会被填充;
  // 用列表已有的 previewItem 兜底,否则 Spin 永不结束
  const task = activeTask || (context === 'task-detail' ? previewItem : undefined);
  // 异步子 agent 会话 ID(点击子 agent 卡片内联展开时使用)
  const previewSubConvId = previewItem?.sub_conv_id || previewItem?.payload?.sub_conv_id;

  const { data: artifactsRes } = useRequest(
    async () => (taskId ? apiInterceptors(listArtifacts({ workspace_id: workspaceId, task_id: taskId })) : null),
    { refreshDeps: [taskId] }
  );
  const artifacts = artifactsRes?.[1] || [];

  if (context === 'dashboard') {
    return (
      <div className="ws-scene-space ws-scene-space--dashboard">
        <Lobby
          workspaceId={workspaceId}
          workspaceCode={workspaceCode}
          refreshKey={listsRefreshKey}
          onSelectTask={onSelectTask || (() => {})}
          onSelectArtifact={onSelectArtifact}
          onSelectDelivery={onSelectDelivery}
          onSelectAppCard={onSelectAppCard}
          onEnterFlywheel={onEnterFlywheel}
          onGuide={onGuide}
          onSelectInbox={onSelectInbox}
          onAsk={onAsk}
          onRunPlaybook={onRunPlaybook}
        />
      </div>
    );
  }

  const CONTEXT_TITLE: Record<string, string> = {
    'task-detail': '任务详情',
    'file-preview': '文件预览',
    'tool-result': '步骤详情',
    'entity-card': '实体信息',
    'delivery-detail': '交付详情',
    'ecp-proposal': '提案确认',
    'exhibit': '内容预览',
    'flywheel': '飞轮工作台',
    'subagent': '子任务对话',
    'triggers': '订阅提醒',
    'data-assets': '数据资产',
    'app-card': '应用卡片',
  };

  return (
    <div className="ws-scene-space">
      <div className="ws-scene-space__header">
        <Button icon={<ArrowLeftOutlined />} onClick={onBack} size="small" type="text">
          返回
        </Button>
        <span className="ws-scene-space__header-title">{CONTEXT_TITLE[context] || ''}</span>
      </div>
      {context === 'flywheel' && (
        <FlywheelWorkspace workspaceId={workspaceId} workspaceCode={workspaceCode} />
      )}
      {context === 'triggers' && (
        <div className="ws-scene-space__body">
          <TriggersTable workspaceId={workspaceId} workspaceCode={workspaceCode} />
        </div>
      )}
      {context === 'data-assets' && (
        <div className="ws-scene-space__body">
          <DataAssetsTab workspaceId={workspaceId} workspaceCode={workspaceCode} />
        </div>
      )}
      {context === 'task-detail' && (
        <div className="ws-scene-space__body">
          {!task && <Spin />}
          {task && (
            <TaskDetail
              task={task}
              artifacts={artifacts}
              onSelectArtifact={onSelectArtifact}
            />
          )}
        </div>
      )}
      {context === 'ecp-proposal' && previewItem?.source_id && (
        <EcpProposalDetail
          sourceId={previewItem.source_id}
          onResolved={onProposalResolved || (() => {})}
          onBack={onBack}
        />
      )}
      {context === 'tool-result' && (
        <div className="ws-scene-space__body">
          <StepPreview step={previewItem} />
        </div>
      )}
      {context === 'exhibit' && (
        <div className="ws-scene-space__body">
          {previewItem?.payload?.exhibit ? (
            <ExhibitHost exhibit={previewItem.payload.exhibit} />
          ) : (
            <div className="ws-preview__empty">暂无入驻内容</div>
          )}
        </div>
      )}
      {context === 'file-preview' && (
        <div className="ws-scene-space__body">
          {previewItem?.payload?.deliverable_file ? (
            <DeliverableFilePreview file={previewItem.payload.deliverable_file} />
          ) : previewItem?.payload?.artifact_id ? (
            <ArtifactPreview
              artifactId={previewItem.payload.artifact_id}
              title={previewItem.payload.title}
              type={previewItem.payload.type}
            />
          ) : (
            <div className="ws-preview">
              <div className="ws-preview__head">
                <span className="ws-preview__title">
                  {previewItem?.payload?.file_name || previewItem?.payload?.title || '文件预览'}
                </span>
              </div>
              <PayloadFields payload={previewItem?.payload || previewItem || {}} />
            </div>
          )}
        </div>
      )}
      {context === 'entity-card' && (
        <div className="ws-scene-space__body">
          {previewItem?.payload?.artifact_id ? (
            <ArtifactPreview
              artifactId={previewItem.payload.artifact_id}
              title={previewItem.payload.title}
              type={previewItem.payload.type}
            />
          ) : (
            <div className="ws-preview">
              <div className="ws-preview__head">
                <span className="ws-preview__title">实体信息</span>
              </div>
              <PayloadFields payload={previewItem?.payload || previewItem || {}} />
            </div>
          )}
        </div>
      )}
      {context === 'delivery-detail' && (
        <div className="ws-scene-space__body">
          {previewItem?.payload?.delivery_id ? (
            <DeliveryPreview
              deliveryId={previewItem.payload.delivery_id}
              title={previewItem.payload.title}
            />
          ) : (
            <div className="ws-preview">
              <div className="ws-preview__head">
                <span className="ws-preview__title">交付详情</span>
              </div>
              <PayloadFields payload={previewItem?.payload || previewItem || {}} />
            </div>
          )}
        </div>
      )}
      {/* 异步子 agent 对话:内联嵌入 ChatSession(minimal)渲染子会话完整消息流 */}
      {context === 'subagent' && (
        <div className="ws-scene-space__body ws-scene-space__body--subagent">
          {previewSubConvId ? (
            <ChatSession
              convUid={previewSubConvId}
              appCode={previewItem?.payload?.app_code || appCode || 'chat_normal'}
              workspaceId={workspaceId}
              minimal
            />
          ) : (
            <div className="ws-preview__empty">暂无子任务对话</div>
          )}
        </div>
      )}
      {/* 应用卡片:在场景空间渲染完整应用页 */}
      {context === 'app-card' && (
        <div className="ws-scene-space__body ws-scene-space__body--app-card">
          {previewItem?.payload?.card ? (
            <AppCardPage card={previewItem.payload.card} workspaceId={workspaceId} onDeleted={onBack} />
          ) : (
            <div className="ws-preview__empty">暂无应用卡片</div>
          )}
        </div>
      )}
    </div>
  );
}
