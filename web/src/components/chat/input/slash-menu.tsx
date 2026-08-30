'use client';

/**
 * `/` 菜单(能力编排):剧本 / 技能 / MCP / 命令 四类 + 添加文件。
 *
 * 交互与浮层全部委托给通用 TriggerMenu,本文件只负责「按 `/` 语义构建分组」。
 * 与 + 菜单(PlusMenu)共享同一份数据与选中结果:`/` 是键盘入口,`+` 是鼠标入口。
 *
 * 「命令」组承载会话级行为命令(压缩上下文/清理会话/规划模式等),
 * 与剧本/技能/MCP 的"资源引用"语义不同:命令选中即执行或切换模式,不随消息发送。
 */

import { forwardRef, useMemo } from 'react';
import {
  ApiOutlined,
  AppstoreOutlined,
  ClearOutlined,
  CompressOutlined,
  FileOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import classNames from 'classnames';
import { TriggerMenu } from './trigger-menu';
import type { TriggerMenuGroup, TriggerMenuItem } from './trigger-menu';
import type {
  PlusMenuMcpRef,
  PlusMenuPlaybookRef,
  PlusMenuSkillRef,
} from './plus-menu';
import type { SessionCommandAction, SessionCommandItem } from './trigger-types';

// 对外保持原有导出,避免调用方改 import 路径
export type { SessionCommandAction, SessionCommandItem };

export interface SlashMenuSelection {
  type: 'playbook' | 'skill' | 'mcp' | 'command';
  playbook?: PlusMenuPlaybookRef;
  skill?: PlusMenuSkillRef;
  mcp?: PlusMenuMcpRef;
  command?: SessionCommandItem;
}

interface SlashMenuProps {
  open: boolean;
  /** 触发词:`/` 后的文本,作为搜索过滤 */
  query: string;
  playbooks?: PlusMenuPlaybookRef[];
  skills?: PlusMenuSkillRef[];
  mcps?: PlusMenuMcpRef[];
  mcpsLoading?: boolean;
  /** 会话命令(压缩/清理/规划),选中即执行或切换模式 */
  commands?: SessionCommandItem[];
  onSelect: (sel: SlashMenuSelection) => void;
  onAddFile?: () => void;
  /** 受控关闭(Esc / 失焦 / 选中后) */
  onClose: () => void;
  children: React.ReactNode;
}

export interface SlashMenuHandle {
  /** 处理输入框 keydown;返回 true 表示事件已被菜单消费 */
  handleKey: (e: React.KeyboardEvent) => boolean;
}

/** 回传给 onSelect 的原始引用,避免再按 key 反查列表 */
type SlashItemData =
  | { kind: 'addFile' }
  | { kind: 'playbook'; ref: PlusMenuPlaybookRef }
  | { kind: 'skill'; ref: PlusMenuSkillRef }
  | { kind: 'mcp'; ref: PlusMenuMcpRef }
  | { kind: 'command'; ref: SessionCommandItem };

const mcpKey = (m: PlusMenuMcpRef) => String(m.id || m.uuid || m.name);

function IconBox({ icon, fallback, gradient }: { icon?: string; fallback: React.ReactNode; gradient: string }) {
  return (
    <div className={classNames('h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-xs font-semibold overflow-hidden', gradient)}>
      {icon ? <img src={icon} alt="" className="h-full w-full object-cover" /> : fallback}
    </div>
  );
}

/** 会话命令图标:按行为定制 */
function SessionCommandIcon({ action }: { action: SessionCommandAction }) {
  const map: Record<SessionCommandAction, { icon: React.ReactNode; cls: string }> = {
    compact: { icon: <CompressOutlined className="text-sm" />, cls: 'bg-gradient-to-br from-slate-500 to-gray-600' },
    clear: { icon: <ClearOutlined className="text-sm" />, cls: 'bg-gradient-to-br from-orange-500 to-red-500' },
    plan: { icon: <ThunderboltOutlined className="text-sm" />, cls: 'bg-gradient-to-br from-cyan-500 to-blue-600' },
  };
  const { icon, cls } = map[action];
  return (
    <div className={classNames('h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white overflow-hidden', cls)}>
      {icon}
    </div>
  );
}

export const SlashMenu = forwardRef<SlashMenuHandle, SlashMenuProps>(function SlashMenu(
  { open, query, playbooks, skills, mcps, mcpsLoading, commands, onSelect, onAddFile, onClose, children },
  ref,
) {
  const groups = useMemo<TriggerMenuGroup<SlashItemData>[]>(() => {
    const out: TriggerMenuGroup<SlashItemData>[] = [];

    if (onAddFile) {
      out.push({
        key: 'addFile',
        label: '文件',
        items: [
          {
            key: 'addFile',
            icon: <FileOutlined className="text-base text-gray-500 dark:text-gray-400" />,
            title: '添加文件',
            description: '上传本地文件作为上下文',
            keywords: ['file', 'upload', '文件'],
            data: { kind: 'addFile' },
          },
        ],
      });
    }

    out.push({
      key: 'playbook',
      label: '剧本',
      items: (playbooks ?? []).map<TriggerMenuItem<SlashItemData>>((pb) => ({
        key: `playbook:${pb.playbook_id}`,
        icon: <IconBox gradient="bg-gradient-to-br from-indigo-500 to-blue-600" fallback={<RocketOutlined className="text-sm" />} />,
        title: pb.playbook_name,
        description: '以该剧本发起任务',
        data: { kind: 'playbook', ref: pb },
      })),
    });

    out.push({
      key: 'skill',
      label: '技能',
      items: (skills ?? []).map<TriggerMenuItem<SlashItemData>>((s) => ({
        key: `skill:${s.skill_code}`,
        icon: <IconBox icon={s.icon} gradient="bg-gradient-to-br from-violet-500 to-indigo-600" fallback={<AppstoreOutlined className="text-sm" />} />,
        title: s.name,
        description: s.description,
        data: { kind: 'skill', ref: s },
      })),
    });

    out.push({
      key: 'mcp',
      label: 'MCP',
      loading: mcpsLoading,
      items: (mcps ?? []).map<TriggerMenuItem<SlashItemData>>((m) => ({
        key: `mcp:${mcpKey(m)}`,
        icon: <IconBox icon={m.icon} gradient="bg-gradient-to-br from-emerald-500 to-teal-600" fallback={<ApiOutlined className="text-sm" />} />,
        title: m.name,
        description: m.description,
        data: { kind: 'mcp', ref: m },
      })),
    });

    out.push({
      key: 'command',
      label: '命令',
      items: (commands ?? []).map<TriggerMenuItem<SlashItemData>>((c) => ({
        key: `command:${c.command}`,
        icon: <SessionCommandIcon action={c.action} />,
        title: `/${c.command}`,
        description: c.description || c.name,
        mono: true,
        data: { kind: 'command', ref: c },
      })),
    });

    return out;
  }, [playbooks, skills, mcps, mcpsLoading, commands, onAddFile]);

  const handleSelect = (item: TriggerMenuItem<SlashItemData>) => {
    const d = item.data;
    if (!d) return;
    if (d.kind === 'addFile') {
      onAddFile?.();
      return;
    }
    if (d.kind === 'playbook') onSelect({ type: 'playbook', playbook: d.ref });
    else if (d.kind === 'skill') onSelect({ type: 'skill', skill: d.ref });
    else if (d.kind === 'mcp') onSelect({ type: 'mcp', mcp: d.ref });
    else if (d.kind === 'command') onSelect({ type: 'command', command: d.ref });
  };

  return (
    <TriggerMenu
      ref={ref}
      open={open}
      query={query}
      triggerChar="/"
      groups={groups}
      onSelect={handleSelect}
      onClose={onClose}
    >
      {children}
    </TriggerMenu>
  );
});
