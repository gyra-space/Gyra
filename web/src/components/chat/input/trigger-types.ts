/**
 * 场景空间统一输入协议 —— 引用数据类型。
 *
 * 放这一层(而非 app/workspaces/detail)是为了避免组件层反向依赖页面层:
 * components/chat/input/ 的菜单组件与 app 下的 payload 组装都从这里取类型,
 * 保证「菜单选中的东西」与「发给后端的东西」是同一份契约。
 */

/** 会话命令动作标识:即时执行型(clear)/ 模式开关型(plan、compact)/ 空间自定义(custom) */
export type SessionCommandAction = 'compact' | 'clear' | 'plan' | 'custom';

/** 会话命令项(命令组数据;结构兼容 PlusMenuCommandRef,额外带行为标识) */
export interface SessionCommandItem {
  command: string;
  name: string;
  description?: string;
  action: SessionCommandAction;
  /**
   * 自定义 toggle 命令发送时合并进 ext_info 的键值对。
   * 例:{"permission_mode":"plan"}、{"force_compress":true}。
   * 内置命令不依赖此字段(各自有硬编码行为)。
   */
  payload?: Record<string, unknown>;
  /** 数据来源:内置种子 or 空间自定义(workspace_resource type='command') */
  source?: 'builtin' | 'workspace';
}

/** `@` 子 Agent 引用(数据源:workspace_resource,type='app') */
export interface SubAgentRef {
  resource_id: number;
  /** 展示名 */
  name: string;
  /** app_code —— 传给后端用于接管主 Agent */
  physical_ref: string;
  description?: string;
}

/** `#` 交付产物引用(Artifact) */
export interface ArtifactRef {
  artifact_id: number;
  title: string;
  /** 文件路径,已落盘,不重复上传 */
  content_ref?: string;
  type?: string;
}

/** `#` 空间资产引用(Asset,带成熟度沉淀) */
export interface AssetRef {
  asset_id: number;
  name: string;
  description?: string;
  content_ref?: string;
  /** 成熟度阶梯:draft → proposed → confirmed → published → canonical */
  maturity?: string;
}

/**
 * `#` 选中的资源引用(统一载体)。
 *
 * start/end 是内联化预留:P0 阶段引用只进附件区、区间恒为文本末尾;
 * P1 输入框升级为 contenteditable 后,同一份数据即可驱动真内联 chip,
 * 数据协议无需再改。
 */
export interface ResourceRef {
  /** 前端唯一 key,用于引用列表渲染 */
  id: string;
  kind: 'artifact' | 'asset' | 'file' | 'task';
  label: string;
  ref_id?: number;
  content_ref?: string;
  start: number;
  end: number;
}
