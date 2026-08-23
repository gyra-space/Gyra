'use client';

import { forwardRef, useImperativeHandle, useMemo, useState } from 'react';
import { Popover } from 'antd';
import {
  ApiOutlined,
  AppstoreOutlined,
  ClearOutlined,
  CompressOutlined,
  FileOutlined,
  LoadingOutlined,
  RocketOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import classNames from 'classnames';
import type {
  PlusMenuCommandRef,
  PlusMenuMcpRef,
  PlusMenuPlaybookRef,
  PlusMenuSkillRef,
} from './plus-menu';

/**
 * 统一斜杠命令菜单(/ 唤起):剧本(场景)/技能/MCP/命令 四类。
 * 与 + 菜单(PlusMenu)共享同一份数据与选中结果,/ 是键盘快捷入口,+ 是鼠标入口。
 * 触发词(输入框开头 / 后的文本)即搜索词,实时过滤;支持 ↑↓ 导航、Enter 选中、Esc 关闭。
 * 布局按类型分组(分组小标题 + 每行 图标/名称/描述),同类目聚合展示。
 *
 * 「命令」组承载会话级行为命令(压缩上下文/清理会话/规划模式等),
 * 与剧本/技能/MCP 的"资源引用"语义不同:命令选中即执行或切换模式,不随消息发送。
 */

/** 会话命令标识 */
export type SessionCommandAction = 'compact' | 'clear' | 'plan';

/** 会话命令项(命令组数据,带行为标识) */
export interface SessionCommandItem extends PlusMenuCommandRef {
  action: SessionCommandAction;
}

export interface SlashMenuSelection {
  type: 'playbook' | 'skill' | 'mcp' | 'command';
  playbook?: PlusMenuPlaybookRef;
  skill?: PlusMenuSkillRef;
  mcp?: PlusMenuMcpRef;
  command?: SessionCommandItem;
}

interface SlashMenuProps {
  open: boolean;
  /** 触发词:输入框开头 / 后的文本,作为搜索过滤 */
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

type ItemType = SlashMenuSelection['type'] | 'addFile';

interface FlatItem {
  key: string;
  type: ItemType;
  icon: React.ReactNode;
  title: string;
  description?: string;
  mono?: boolean;
}

interface Group {
  type: ItemType;
  label: string;
  items: FlatItem[];
}

const mcpKey = (m: PlusMenuMcpRef) => String(m.id || m.uuid || m.name);

const rowCls =
  'flex w-full items-center gap-3 px-3 py-2.5 text-left rounded-lg transition-colors cursor-pointer';

function matches(q: string, ...fields: (string | undefined)[]) {
  if (!q) return true;
  const needle = q.toLowerCase();
  return fields.some((f) => (f || '').toLowerCase().includes(needle));
}

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
  const [active, setActive] = useState(0);

  const q = query.trim();

  // 分组构建:文件/剧本/技能/MCP/命令,同类目聚合,带分组小标题
  const groups = useMemo<Group[]>(() => {
    const out: Group[] = [];

    if (onAddFile) {
      const items: FlatItem[] = matches(q, '添加文件', '文件', 'file', 'upload')
        ? [{ key: 'addFile', type: 'addFile', icon: <FileOutlined className="text-base text-gray-500 dark:text-gray-400" />, title: '添加文件', description: '上传本地文件作为上下文' }]
        : [];
      if (items.length) out.push({ type: 'addFile', label: '文件', items });
    }

    const pbItems: FlatItem[] = (playbooks ?? [])
      .filter((pb) => matches(q, pb.playbook_name))
      .map((pb) => ({
        key: `playbook:${pb.playbook_id}`,
        type: 'playbook',
        icon: <IconBox gradient="bg-gradient-to-br from-indigo-500 to-blue-600" fallback={<RocketOutlined className="text-sm" />} />,
        title: pb.playbook_name,
        description: '以该剧本发起任务',
      }));
    if (pbItems.length) out.push({ type: 'playbook', label: '剧本', items: pbItems });

    const skillItems: FlatItem[] = (skills ?? [])
      .filter((s) => matches(q, s.name, s.description))
      .map((s) => ({
        key: `skill:${s.skill_code}`,
        type: 'skill',
        icon: <IconBox icon={s.icon} gradient="bg-gradient-to-br from-violet-500 to-indigo-600" fallback={<AppstoreOutlined className="text-sm" />} />,
        title: s.name,
        description: s.description,
      }));
    if (skillItems.length) out.push({ type: 'skill', label: '技能', items: skillItems });

    const mcpItems: FlatItem[] = (mcps ?? [])
      .filter((m) => matches(q, m.name, m.description))
      .map((m) => ({
        key: `mcp:${mcpKey(m)}`,
        type: 'mcp',
        icon: <IconBox icon={m.icon} gradient="bg-gradient-to-br from-emerald-500 to-teal-600" fallback={<ApiOutlined className="text-sm" />} />,
        title: m.name,
        description: m.description,
      }));
    if (mcpItems.length || mcpsLoading) out.push({ type: 'mcp', label: 'MCP', items: mcpItems });

    const cmdItems: FlatItem[] = (commands ?? [])
      .filter((c) => matches(q, c.command, c.name, c.description))
      .map((c) => ({
        key: `command:${c.command}`,
        type: 'command',
        icon: <SessionCommandIcon action={c.action} />,
        title: `/${c.command}`,
        description: c.description || c.name,
        mono: true,
      }));
    if (cmdItems.length) out.push({ type: 'command', label: '命令', items: cmdItems });

    return out;
  }, [q, playbooks, skills, mcps, mcpsLoading, commands, onAddFile]);

  // 扁平化用于键盘导航(保持分组顺序)
  const flatItems = useMemo<FlatItem[]>(() => groups.flatMap((g) => g.items), [groups]);
  const itemCount = flatItems.length;
  const clampedActive = itemCount === 0 ? 0 : Math.min(active, itemCount - 1);

  const choose = (item: FlatItem | undefined) => {
    if (!item) return;
    if (item.type === 'addFile') {
      onAddFile?.();
      onClose();
      return;
    }
    if (item.type === 'playbook') {
      const pb = (playbooks ?? []).find((p) => `playbook:${p.playbook_id}` === item.key);
      if (pb) onSelect({ type: 'playbook', playbook: pb });
    } else if (item.type === 'skill') {
      const s = (skills ?? []).find((x) => `skill:${x.skill_code}` === item.key);
      if (s) onSelect({ type: 'skill', skill: s });
    } else if (item.type === 'mcp') {
      const m = (mcps ?? []).find((x) => `mcp:${mcpKey(x)}` === item.key);
      if (m) onSelect({ type: 'mcp', mcp: m });
    } else if (item.type === 'command') {
      const c = (commands ?? []).find((x) => `command:${x.command}` === item.key);
      if (c) onSelect({ type: 'command', command: c });
    }
    onClose();
  };

  useImperativeHandle(ref, () => ({
    handleKey: (e) => {
      if (!open) return false;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActive((a) => (itemCount === 0 ? 0 : (a + 1) % itemCount));
        return true;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActive((a) => (itemCount === 0 ? 0 : (a - 1 + itemCount) % itemCount));
        return true;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        choose(flatItems[clampedActive]);
        return true;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return true;
      }
      return false;
    },
  }));

  // 渲染分组:小标题 + 行;给每行分配全局序号以对齐键盘高亮
  let rowIndex = -1;
  const renderRow = (item: FlatItem) => {
    rowIndex += 1;
    const idx = rowIndex;
    return (
      <button
        type="button"
        key={item.key}
        className={classNames(rowCls, idx === clampedActive && 'bg-indigo-50 dark:bg-indigo-900/20')}
        onMouseEnter={() => setActive(idx)}
        onClick={() => choose(item)}
        title={item.description || item.title}
      >
        {item.icon}
        <span className="min-w-0 flex-1">
          <span className={classNames('block truncate text-[13px] font-medium text-gray-800 dark:text-gray-100', item.mono && 'font-mono')}>
            {item.title}
          </span>
          {item.description && <span className="block truncate text-[12px] text-gray-400 dark:text-gray-500">{item.description}</span>}
        </span>
      </button>
    );
  };

  const content = (
    <div className="w-[380px]">
      {/* 搜索词提示 */}
      <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1 border-b border-gray-100 dark:border-gray-700/60">
        <SearchOutlined className="text-[11px] text-gray-400" />
        {q ? (
          <span className="text-[12px] text-indigo-500 font-medium truncate">/{q}</span>
        ) : (
          <span className="text-[12px] text-gray-400">选择类型或输入关键词过滤</span>
        )}
      </div>
      <div className="max-h-[340px] overflow-y-auto py-1.5 px-1.5">
        {groups.length === 0 && !mcpsLoading && (
          <div className="px-3 py-8 text-center text-xs text-gray-400">无匹配项</div>
        )}
        {groups.map((g) => (
          <div key={g.type} className="mb-1 last:mb-0">
            <div className="px-2 pt-1.5 pb-1 text-[11px] font-medium text-gray-400 dark:text-gray-500">{g.label}</div>
            {g.type === 'mcp' && mcpsLoading && g.items.length === 0 ? (
              <div className="px-3 py-3 text-xs text-gray-400"><LoadingOutlined className="mr-1" />加载中…</div>
            ) : (
              g.items.map(renderRow)
            )}
          </div>
        ))}
      </div>
      <div className="px-3 py-1.5 border-t border-gray-100 dark:border-gray-700/60 text-[10px] text-gray-400 flex items-center gap-3">
        <span>↑↓ 选择</span>
        <span>Enter 确认</span>
        <span>Esc 关闭</span>
      </div>
    </div>
  );

  return (
    <Popover
      open={open}
      content={content}
      placement="topLeft"
      trigger={[]}
      arrow={false}
      overlayClassName="[&_.ant-popover-inner]:!p-0 [&_.ant-popover-inner]:!rounded-xl [&_.ant-popover-inner]:!shadow-xl"
    >
      {children}
    </Popover>
  );
});
