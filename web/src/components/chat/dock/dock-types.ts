/**
 * Composer Dock 协议类型定义（输入框上方固定渲染区域）。
 *
 * 与后端 gpts_memory.push_dock_widget / query_chat._build_dock_frame 输出同构：
 * - SSE chunk 顶层 `{"dock": {version, widgets}}`
 * - 轮询 `/api/v1/chat/query` 响应 `dock` 字段
 *
 * 前端按 `widget.type` 查注册表渲染对应组件，按 `widget.id` + `kind` 做增量合并。
 */

import type React from 'react';

export type DockWidgetKind = 'replace' | 'patch' | 'remove';

export interface DockWidget {
  /** 稳定 id，前端按它做增量合并。 */
  id: string;
  /** 组件寻址符，type → 注册表组件。 */
  type: string;
  /** replace 整体覆盖 / patch 深合并 / remove 移除该 widget。 */
  kind?: DockWidgetKind;
  /** 组件私有数据，schema 由对应组件定义。 */
  payload: Record<string, any>;
}

export interface DockFrame {
  /** 协议版本，用于前向兼容。 */
  version?: number;
  widgets: DockWidget[];
}

/** DockPanel 渲染时传给每个注册组件的 props。 */
export interface DockWidgetProps {
  widget: DockWidget;
  /** tab 容器内嵌渲染：组件跳过自带卡片外壳/header，由 dock tab 栏承担。 */
  embedded?: boolean;
}

/**
 * Dock widget 注册项：DockPanel 不认识具体 payload schema，
 * 摘要/进度/活跃度推导由注册项提供；新增 widget 仍只需注册一项。
 */
export interface DockWidgetRegistration {
  component: React.ComponentType<DockWidgetProps>;
  /** 折叠行左侧的 widget 图标（多 widget 时作切换器）。 */
  icon: React.ReactNode;
  /** 折叠行摘要主文本（如进行中/最近一条待办的标题）。 */
  getTitle: (payload: Record<string, any>) => React.ReactNode;
  /** 折叠行右侧进度文本（如 `3/3`）。 */
  getProgress?: (payload: Record<string, any>) => React.ReactNode;
  /** 是否有进行中内容（驱动脉冲点与结束自动收起）。 */
  isRunning: (payload: Record<string, any>) => boolean;
}