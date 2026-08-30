import React from 'react';
import { AppstoreOutlined, CheckOutlined, InboxOutlined, UnorderedListOutlined } from '@ant-design/icons';
import VisTodoList from '@/components/chat/chat-content-components/VisComponents/VisTodoList';
import type { ITodoListData } from '@/components/chat/chat-content-components/VisComponents/VisTodoList';
import VisSubagentBoard from '@/components/chat/chat-content-components/VisComponents/VisSubagentBoard';
import type { ISubagentBoardData, SubagentItemData } from '@/components/chat/chat-content-components/VisComponents/VisSubagentBoard';
import SceneInputQueue, { InputQueueClearButton } from '@/app/workspaces/detail/scene-input-queue';
import type { InputQueuePayload } from '@/app/workspaces/detail/scene-input-queue';
import type { DockWidgetProps, DockWidgetRegistration } from './dock-types';

/**
 * 输入区 Dock widget 注册表：`type` → 注册项（组件 + 图标/摘要/进度/活跃度推导）。
 *
 * 组件只读 `widget.payload` 自行渲染；交互由组件自定（调后端 API 后经
 * 同一条 push_dock_widget 回推 patch 帧，applyDockFrame 合并后重渲染）。
 * 新增 widget 只需在此注册一项，无需改任何 if/switch / DockPanel。
 */

const TodoListWidget: React.FC<DockWidgetProps> = ({ widget, embedded }) => (
  <VisTodoList data={widget.payload} embedded={embedded} />
);

const SubagentBoardWidget: React.FC<DockWidgetProps> = ({ widget, embedded }) => (
  <VisSubagentBoard data={widget.payload} embedded={embedded} />
);

const isTerminal = (s: string) => s === 'done' || s === 'failed';

const todoProgress = (payload: ITodoListData) => {
  const items = payload.items || [];
  return { completed: items.filter(i => i.status === 'completed').length, total: items.length };
};

const subagentProgress = (payload: ISubagentBoardData) => {
  const items = payload.items || [];
  return {
    completed: items.filter(i => isTerminal(i.status)).length,
    total: items.length,
    hasAuth: items.some(i => i.status === 'awaiting_authorization'),
  };
};

/** 全部完成时：✓ + 最近一条标题（参考 Manus 折叠行）。 */
const completedTitle = (title: React.ReactNode): React.ReactNode => (
  <>
    <CheckOutlined className="text-green-500 text-[11px] mr-1" />
    {title}
  </>
);

export const dockWidgetRegistry: Record<string, DockWidgetRegistration> = {
  todo_list: {
    component: TodoListWidget,
    icon: <UnorderedListOutlined />,
    getTitle: payload => {
      const items = (payload as ITodoListData).items || [];
      if (items.length === 0) return '待办';
      const working = items.find(i => i.status === 'working');
      if (working) return working.title;
      const last = items[items.length - 1];
      if (items.every(i => i.status === 'completed')) return completedTitle(last.title);
      return (items.find(i => i.status === 'pending') ?? last).title;
    },
    getProgress: payload => {
      const { completed, total } = todoProgress(payload as ITodoListData);
      return `${completed}/${total}`;
    },
    isRunning: payload =>
      ((payload as ITodoListData).items || []).some(i => i.status === 'working'),
  },
  subagent_board: {
    component: SubagentBoardWidget,
    icon: <AppstoreOutlined />,
    getTitle: payload => {
      const items = (payload as ISubagentBoardData).items || [];
      if (items.length === 0) return '子任务';
      const nameOf = (i: SubagentItemData) => i.agent_display_name || i.agent_name || i.task || '子任务';
      const active = items.find(
        i => i.status === 'running' || i.status === 'awaiting_authorization',
      );
      if (active) return nameOf(active);
      const last = items[items.length - 1];
      if (items.every(i => isTerminal(i.status))) return completedTitle(nameOf(last));
      return nameOf(last);
    },
    getProgress: payload => {
      const { completed, total, hasAuth } = subagentProgress(payload as ISubagentBoardData);
      return (
        <>
          {completed}/{total}
          {hasAuth && <span className="ml-1 text-[#f59e0b]">待授权</span>}
        </>
      );
    },
    isRunning: payload =>
      ((payload as ISubagentBoardData).items || []).some(
        i => i.status === 'running' || i.status === 'awaiting_authorization',
      ),
  },
};
