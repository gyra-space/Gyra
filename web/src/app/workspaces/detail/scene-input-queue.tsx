'use client';

/**
 * 「运行中补充输入」队列的 Dock widget:对话运行中继续提交的消息先入后端队列
 * (agent_input_queue),由正在执行的 Agent 在下一轮 think 前消费。
 *
 * 作为 Composer Dock 的 `input_queue` widget 渲染(输入框上方贴合的「单行摘要 +
 * 向上展开」容器内),与待办/子任务等 widget 同处一条 dock,不再割裂成独立卡片。
 *
 * payload:
 *  - items: 仍在排队(未消费)的消息文本,有序;
 *  - total: 排队总数(与 items.length 一致,供摘要行直接取);
 *  - onClearQueue?: string 标记位 —— 实际动作经 DockWidgetProps 注入,见
 *    inputQueueActions(由场景 shell 持有真实 clearQueue,注册表经它调用)。
 */
import React from 'react';
import { DeleteOutlined } from '@ant-design/icons';

export interface InputQueuePayload {
  items?: string[];
  total?: number;
}

interface SceneInputQueueProps {
  payload: InputQueuePayload;
  /** dock tab 容器内嵌渲染:不自带卡片外壳/header,由 dock tab 栏承担摘要行。 */
  embedded?: boolean;
}

export function SceneInputQueue({ payload }: SceneInputQueueProps) {
  const items = payload?.items || [];
  if (items.length === 0) return null;
  return (
    <div className="ws-dock-queue">
      {items.map((text, i) => (
        <div key={`${i}-${text}`} className="ws-dock-queue__item">
          <span className="ws-dock-queue__idx">{i + 1}</span>
          <span className="ws-dock-queue__text">{text}</span>
        </div>
      ))}
    </div>
  );
}

export default SceneInputQueue;

/** 「取消排队」图标按钮:用在 dock 折叠行右侧进度位(点击触发 inputQueueActions.onClear)。 */
export function InputQueueClearButton() {
  return (
    <button
      type="button"
      className="ws-dock-queue__clear"
      title="取消排队"
      onClick={(e) => {
        e.stopPropagation();
        inputQueueActions.onClear?.();
      }}
    >
      <DeleteOutlined />
    </button>
  );
}

/** 队列动作回调:由场景 shell 注入真实 clearQueue,widget 注册表/按钮经这里调用,
 *  避免把 hook 依赖带进注册表。 */
export const inputQueueActions: { onClear?: () => void } = {};
