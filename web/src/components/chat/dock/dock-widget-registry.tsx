import React from 'react';
import VisTodoList from '@/components/chat/chat-content-components/VisComponents/VisTodoList';
import type { ITodoListData } from '@/components/chat/chat-content-components/VisComponents/VisTodoList';
import VisSubagentBoard from '@/components/chat/chat-content-components/VisComponents/VisSubagentBoard';
import type { ISubagentBoardData } from '@/components/chat/chat-content-components/VisComponents/VisSubagentBoard';
import type { DockWidgetProps, DockWidgetRegistration } from './dock-types';

/**
 * 输入区 Dock widget 注册表：`type` → 注册项（组件 + tab label/活跃度推导）。
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

const todoProgress = (payload: ITodoListData) => {
  const items = payload.items || [];
  return { completed: items.filter(i => i.status === 'completed').length, total: items.length };
};

const subagentProgress = (payload: ISubagentBoardData) => {
  const items = payload.items || [];
  const isTerminal = (s: string) => s === 'done' || s === 'failed';
  return {
    completed: items.filter(i => isTerminal(i.status)).length,
    total: items.length,
    hasAuth: items.some(i => i.status === 'awaiting_authorization'),
  };
};

export const dockWidgetRegistry: Record<string, DockWidgetRegistration> = {
  todo_list: {
    component: TodoListWidget,
    getLabel: payload => {
      const { completed, total } = todoProgress(payload as ITodoListData);
      return `待办 ${completed}/${total}`;
    },
    isRunning: payload =>
      ((payload as ITodoListData).items || []).some(i => i.status === 'working'),
  },
  subagent_board: {
    component: SubagentBoardWidget,
    getLabel: payload => {
      const { completed, total, hasAuth } = subagentProgress(payload as ISubagentBoardData);
      return (
        <>
          子任务 {completed}/{total}
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
