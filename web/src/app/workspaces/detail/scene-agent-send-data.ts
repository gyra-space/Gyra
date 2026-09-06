import type { PlaybookCommand, SkillRef, WorkspaceUserAttachment, ExpertCommand } from './agent-workspace-types';
import type { MediaParams, MediaImageRef, MediaImageRole } from '@/components/chat/input/media-params';
import type { PlusMenuMcpRef } from '@/components/chat/input/plus-menu';
import type { SubAgentRef, ResourceRef } from '@/components/chat/input/trigger-types';
import { transformFileUrl } from '@/utils';

/** 输入框上传资源项(与 agent-workspace-input 的 ResourceItem 同构):
 *  type 标记资源类别,URL 载荷按模态挂载在对应字段 */
export interface SceneAgentResource {
  type: string;
  image_url?: { url: string; preview_url?: string; file_name?: string };
  file_url?: { url: string; preview_url?: string; file_name?: string };
  audio_url?: { url: string; preview_url?: string; file_name?: string };
  video_url?: { url: string; preview_url?: string; file_name?: string };
  /** 图片角色标注:'auto' 表示交由主 Agent 自动判断(默认) */
  image_role?: MediaImageRole;
}

/** 把上传返回的 URL 解析成对外可访问的绝对 URL。
 *  local/本机服务下预览地址可能是相对路径(如 /api/v2/serve/file/...),
 *  直接给模型/多媒体 Provider 会被当成无 host 的地址而无法访问;
 *  这里对相对路径补全 API 基址,与 resolvePreviewUrl 逻辑保持一致。 */
export function resolveAbsolutePublicUrl(u?: string): string {
  if (!u) return '';
  const normalized = transformFileUrl(u);
  if (!normalized) return '';
  if (normalized.startsWith('http://') || normalized.startsWith('https://')) return normalized;
  if (normalized.startsWith('/')) {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || '';
    return `${apiBase}${normalized}`;
  }
  return normalized;
}

/** 取资源里对外可访问的公共 URL:优先公共预览地址,其次原始 url(同样补全绝对)。 */
function resourcePublicUrl(r: SceneAgentResource): string {
  const d = r.image_url || r.video_url || r.audio_url || r.file_url;
  if (!d) return '';
  return resolveAbsolutePublicUrl(d.preview_url || d.url);
}

/** 根据上传图片的角色标注,构建确定性媒体输入(mapping 到 image_url/image_url_last/reference_images)。
 *  仅处理标注了角色的图片(role 非 auto);未标注(auto)的不参与,交由主 Agent 自动判断。
 *  同时返回非 auto 角色的标注明细 image_refs,供后端渲染提示兜底。 */
export function buildMediaImageInputs(resources: SceneAgentResource[]): {
  image_url?: string;
  image_url_last?: string;
  reference_images?: string[];
  image_refs?: MediaImageRef[];
} {
  const refs: MediaImageRef[] = [];
  const first: string[] = [];
  const last: string[] = [];
  const refImages: string[] = [];
  for (const r of resources) {
    if (!r.image_url) continue;
    const url = resourcePublicUrl(r);
    if (!url) continue;
    const role: MediaImageRole = (r.image_role || 'auto') as MediaImageRole;
    if (role === 'auto') continue;
    refs.push({ url, role, name: r.image_url.file_name });
    if (role === 'first_frame') first.push(url);
    else if (role === 'last_frame') last.push(url);
    else if (role === 'reference') refImages.push(url);
  }
  const out: { image_url?: string; image_url_last?: string; reference_images?: string[]; image_refs?: MediaImageRef[] } = {};
  if (first.length) out.image_url = first[0];
  if (last.length) out.image_url_last = last[0];
  if (refImages.length) out.reference_images = refImages;
  if (refs.length) out.image_refs = refs;
  return out;
}

/** 未随消息发出的上传附件暂存(按空间维度,跨输入框重挂载存活):
 *  欢迎态↔运行态分支切换/会话切换会重建输入组件,实例 state 归零导致
 *  已上传附件从发送 payload 中丢失(文件已传 gyra-fs 但消息未携带引用)。 */
const pendingResourcesByScope = new Map<string, SceneAgentResource[]>();

/** 读取某空间的未发送附件(无则返回空数组) */
export function getPendingResources(scopeKey: string): SceneAgentResource[] {
  return pendingResourcesByScope.get(scopeKey) ?? [];
}

/** 覆写某空间的未发送附件;空数组时清除条目 */
export function setPendingResources(scopeKey: string, resources: SceneAgentResource[]): void {
  if (resources.length > 0) pendingResourcesByScope.set(scopeKey, resources);
  else pendingResourcesByScope.delete(scopeKey);
}

/** 未随消息发出的 `#` 资源引用暂存(按空间维度,跨输入框重挂载存活):
 *  与上传附件同理,实例 state 在输入框重建时归零会导致已选中的引用从
 *  发送 payload 中静默丢失,这里复用同一套暂存域机制兜底。 */
const pendingResourceRefsByScope = new Map<string, ResourceRef[]>();

/** 读取某空间的未发送 `#` 引用(无则返回空数组) */
export function getPendingResourceRefs(scopeKey: string): ResourceRef[] {
  return pendingResourceRefsByScope.get(scopeKey) ?? [];
}

/** 覆写某空间的未发送 `#` 引用;空数组时清除条目 */
export function setPendingResourceRefs(scopeKey: string, refs: ResourceRef[]): void {
  if (refs.length > 0) pendingResourceRefsByScope.set(scopeKey, refs);
  else pendingResourceRefsByScope.delete(scopeKey);
}

export interface SceneAgentSendPayload {
  text: string;
  resources?: SceneAgentResource[];
  model?: string;
  playbookCommand?: PlaybookCommand;
  /** 本次对话选用的专家(随 chat_in_params 下发,param_type='expert_command') */
  expertCommand?: ExpertCommand;
  /** 本次对话选用的技能(随 chat_in_params 下发,sub_type='skill(gyra)') */
  skills?: SkillRef[];
  /** 本次对话选用的 MCP 连接器(随 chat_in_params 下发,sub_type='mcp(gyra)') */
  mcps?: PlusMenuMcpRef[];
  /** 多媒体生成参数（图片/视频），场景空间输入框设定，随 chat_in_params 下发，由多媒体子 Agent 消费 */
  media?: MediaParams;
  /** 本次对话的 Agent 工具权限级别(plan/auto/manual),写入 ext_info.permission_mode,
   *  接入后端 5 级权限链(reader 只读 / 写工具按级别放行或 ASK) */
  permission?: string;
  /** 主动触发上下文压缩(/压缩上下文 会话命令):写入 ext_info.force_compress,
   *  后端在本轮推理前强制走历史摘要压缩(复用被动压缩逻辑) */
  forceCompress?: boolean;
  /**
   * `@` 选中的子 Agent(会话级接管)。随 chat_in_params 以
   * param_type='subagent' 下发,后端据此覆写本轮主 Agent。
   */
  subAgent?: SubAgentRef;
  /**
   * `#` 选中的资源引用(交付产物 / 空间资产)。文件已落盘,
   * 走 param_type='resource' + sub_type='artifact'/'asset',不重复上传。
   */
  resourceRefs?: ResourceRef[];
  /**
   * 已开启的空间自定义 toggle 命令合并后的键值对,
   * 直接并入 ext_info(如 {"permission_mode":"plan"})。
   */
  commandPayload?: Record<string, unknown>;
}

export interface SendDataOptions {
  workspaceId?: number | string;
  taskId?: number | string;
  focusArtifactId?: number | string;
}

export interface ChatInParam {
  param_type: string;
  param_value: string;
  sub_type?: string;
}

export interface SceneAgentSendData {
  conv_uid: string;
  user_input: string | { role: 'user'; content: unknown[] };
  workspace_id?: number | string;
  task_id?: number | string;
  model_name?: string;
  chat_in_params?: ChatInParam[];
  team_mode: string;
  app_config_code: string;
  agent_version: string;
  ext_info: {
    vis_render: 'scene_agent_workspace';
    workspace_id?: number;
    task_id?: number;
    /** 显式命中的合约:后端回合前路由据此预建会话内任务(in_session 同步执行) */
    playbook_id?: number;
    /** 当前关注的产出物 id(隐式上下文) */
    focus_artifact_id?: number;
    /** 工具权限级别(plan/auto/manual),接入后端 5 级权限链 */
    permission_mode?: string;
    /** 主动触发上下文压缩:本轮推理前强制走历史摘要压缩 */
    force_compress?: boolean;
  };
}

/** 资源项 → 用户附件(乐观上屏气泡展示用):按模态取 URL 载荷,mime_type 存模态标记。 */
export function resourcesToAttachments(resources: SceneAgentResource[]): WorkspaceUserAttachment[] {
  const out: WorkspaceUserAttachment[] = [];
  for (const r of resources) {
    if (!r || typeof r !== 'object') continue;
    const data = r.image_url || r.video_url || r.audio_url || r.file_url;
    if (!data || !data.url) continue;
    const mime = r.image_url ? 'image' : r.video_url ? 'video' : r.audio_url ? 'audio' : 'file';
    out.push({ name: data.file_name || '附件', url: data.url, mime_type: mime });
  }
  return out;
}

/**
 * 纯函数:构造 scene-agent send 载荷。对齐 chat-session.tsx:306-320 的多模态/参数构造。
 * 从 use-scene-agent-chat.ts 的 send 中抽出,便于单测(node env,无 DOM/依赖链)。
 */
export function buildSceneAgentSendData(
  payload: SceneAgentSendPayload,
  options: SendDataOptions,
  conversationId: string,
): SceneAgentSendData {
  const { text, resources = [], model, playbookCommand, expertCommand, skills, mcps, media, permission, forceCompress, subAgent, resourceRefs = [], commandPayload } = payload;
  const { workspaceId, taskId, focusArtifactId } = options;
  const trimmed = text.trim();

  const userInput =
    resources.length > 0
      ? {
          role: 'user' as const,
          content: [...resources, ...(trimmed ? [{ type: 'text', text: trimmed }] : [])],
        }
      : trimmed;

  const chatInParams: ChatInParam[] = [];
  if (resources.length > 0) {
    chatInParams.push({ param_type: 'resource', param_value: JSON.stringify(resources), sub_type: 'common_file' });
  }
  if (model) {
    chatInParams.push({ param_type: 'model', param_value: model });
  }
  if (playbookCommand) {
    chatInParams.push({
      param_type: 'playbook_command',
      sub_type: 'playbook',
      param_value: JSON.stringify(playbookCommand),
    });
  }
  if (expertCommand) {
    chatInParams.push({
      param_type: 'expert_command',
      sub_type: 'expert',
      param_value: JSON.stringify(expertCommand),
    });
  }
  if (skills && skills.length > 0) {
    skills.forEach((skill) => {
      chatInParams.push({
        param_type: 'resource',
        param_value: JSON.stringify(skill),
        sub_type: 'skill(gyra)',
      });
    });
  }
  if (mcps && mcps.length > 0) {
    mcps.forEach((mcp) => {
      chatInParams.push({
        param_type: 'resource',
        param_value: JSON.stringify({
          mcp_code: mcp.id || mcp.uuid || mcp.name,
          name: mcp.name,
        }),
        sub_type: 'mcp(gyra)',
      });
    });
  }
  // @ 接管:param_type='subagent',后端据此覆写本轮主 Agent(独立于 resource 通道,
  // 避免被 chat_in_params_to_resource 当成资源物化)
  if (subAgent) {
    chatInParams.push({
      param_type: 'subagent',
      sub_type: 'app',
      param_value: JSON.stringify({
        app_code: subAgent.physical_ref,
        app_name: subAgent.name,
      }),
    });
  }
  // # 引用的交付资源:文件已落盘,按 artifact / asset 分流,不重复走上传通道
  resourceRefs
    .filter((r) => r.kind === 'artifact' || r.kind === 'asset')
    .forEach((ref) => {
      chatInParams.push({
        param_type: 'resource',
        sub_type: ref.kind,
        param_value: JSON.stringify({
          ...(ref.kind === 'artifact' ? { artifact_id: ref.ref_id } : { asset_id: ref.ref_id }),
          title: ref.label,
          content_ref: ref.content_ref,
        }),
      });
    });
  // 多媒体生成参数(media)：合并「用户面板设置(media)」与「图片角色标注确定性透传」，
  // 只输出一条 media chat_in_param(后端以首个 param_type='media' 为准,重复会互相覆盖)。
  // 角色标注(image_url/image_url_last/reference_images/image_refs)覆盖用户面板的同类字段,
  // 使人工标注优先于主 Agent 猜测。
  const mediaImage = buildMediaImageInputs(resources);
  const mergedMedia: MediaParams | null =
    (media && Object.keys(media).length) ? { ...media } : (mediaImage.image_url || mediaImage.image_url_last || mediaImage.reference_images?.length || mediaImage.image_refs?.length ? { kind: 'video' } : null);
  if (mergedMedia) {
    if (mediaImage.image_url) mergedMedia.image_url = mediaImage.image_url;
    if (mediaImage.image_url_last) mergedMedia.image_url_last = mediaImage.image_url_last;
    if (mediaImage.reference_images?.length) mergedMedia.reference_images = mediaImage.reference_images;
    if (mediaImage.image_refs?.length) mergedMedia.image_refs = mediaImage.image_refs;
    chatInParams.push({
      param_type: 'media',
      param_value: JSON.stringify(mergedMedia),
      sub_type: '',
    });
  }

  return {
    conv_uid: conversationId,
    user_input: userInput,
    workspace_id: workspaceId,
    task_id: taskId,
    ...(model ? { model_name: model } : {}),
    ...(chatInParams.length ? { chat_in_params: chatInParams } : {}),
    team_mode: '',
    app_config_code: '',
    agent_version: 'v1',
    ext_info: {
      vis_render: 'scene_agent_workspace',
      ...(workspaceId !== undefined ? { workspace_id: Number(workspaceId) } : {}),
      ...(taskId !== undefined ? { task_id: Number(taskId) } : {}),
      // 显式命中合约:透传 playbook_id 给后端回合前路由,预建会话内任务
      // (execution_mode=in_session)并在当前对话同步执行。已绑定任务的
      // workbench 对话不受影响(路由对 task_id 已有时跳过)。
      ...(playbookCommand ? { playbook_id: Number(playbookCommand.playbook_id) } : {}),
      // 显式选中专家:透传 expert_app_code,后端回合前路由据此创建专家任务
      ...(expertCommand ? { expert_app_code: expertCommand.app_code } : {}),
      ...(focusArtifactId !== undefined ? { focus_artifact_id: Number(focusArtifactId) } : {}),
      // 自定义 toggle 命令的 payload:放在显式模式开关之前,让 plan/compact 可覆盖
      ...(commandPayload && Object.keys(commandPayload).length ? commandPayload : {}),
      // 工具权限级别:写入 extra.permission_mode,接入 Agent 5 级权限链
      // (plan=只读放行/写 ASK, auto=全放行, manual=全部 ASK)
      ...(permission ? { permission_mode: permission } : {}),
      // 主动触发上下文压缩:写入 extra.force_compress,后端本轮推理前强制摘要压缩
      ...(forceCompress ? { force_compress: true } : {}),
      // @ 接管态:供 UI 与审计;main_app_code 由后端在覆写 gpts_name 时补上
      ...(subAgent
        ? { active_agent: { app_code: subAgent.physical_ref, app_name: subAgent.name } }
        : {}),
      // # 引用明细(含 start/end 区间),P1 内联化后由渲染层消费
      ...(resourceRefs.length ? { refs: resourceRefs } : {}),
    },
  };
}