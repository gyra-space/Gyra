'use client';

import { useMemo, useRef, useState } from 'react';
import { Popover, Badge } from 'antd';
import {
  ApiOutlined,
  AppstoreOutlined,
  BookOutlined,
  CheckOutlined,
  CodeOutlined,
  DatabaseOutlined,
  LeftOutlined,
  LoadingOutlined,
  PaperClipOutlined,
  PlusOutlined,
  RightOutlined,
  RocketOutlined,
  SafetyOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import classNames from 'classnames';

/** 剧本引用 */
export interface PlusMenuPlaybookRef {
  playbook_id: number;
  playbook_name: string;
}

/** 技能引用 */
export interface PlusMenuSkillRef {
  skill_code: string;
  name: string;
  description?: string;
  icon?: string;
  author?: string;
  version?: string;
  type?: string;
}

/** MCP 连接器引用 */
export interface PlusMenuMcpRef {
  id?: string;
  uuid?: string;
  name: string;
  description?: string;
  icon?: string;
  available?: boolean;
}

/** 斜杠命令(剧本以 / 前缀形式快捷唤起) */
export interface PlusMenuCommandRef {
  command: string;
  name: string;
  description?: string;
}

/** 权限等级 */
export interface PlusMenuPermission {
  key: string;
  label: string;
  description?: string;
}

/** 自定义资源类型(如数据源/知识库) */
export interface PlusMenuResourceType {
  key: string;
  label: string;
  icon: React.ReactNode;
}

/** 通用列表项(数据源/知识库等自定义面板的数据) */
export interface PlusMenuListItem {
  key: string;
  title: string;
  description?: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
}

export type PlusMenuPanel =
  | 'root'
  | 'playbook'
  | 'skill'
  | 'mcp'
  | 'command'
  | 'permission'
  | `custom:${string}`;

export interface PlusMenuProps {
  /** 点击「添加文件」 */
  onAddFile?: () => void;
  /** 权限等级 */
  permissions?: PlusMenuPermission[];
  selectedPermission?: string;
  onPermissionChange?: (key: string) => void;
  /** 剧本 */
  playbooks?: PlusMenuPlaybookRef[];
  playbooksLoading?: boolean;
  selectedPlaybook?: PlusMenuPlaybookRef | null;
  onPlaybookChange?: (pb: PlusMenuPlaybookRef | null) => void;
  /** 技能 */
  skills?: PlusMenuSkillRef[];
  skillsLoading?: boolean;
  selectedSkills?: PlusMenuSkillRef[];
  onSkillsChange?: (skills: PlusMenuSkillRef[]) => void;
  /** MCP 连接器 */
  mcps?: PlusMenuMcpRef[];
  mcpsLoading?: boolean;
  selectedMcps?: PlusMenuMcpRef[];
  onMcpsChange?: (mcps: PlusMenuMcpRef[]) => void;
  /** 斜杠命令 */
  commands?: PlusMenuCommandRef[];
  onCommandSelect?: (cmd: PlusMenuCommandRef) => void;
  /** 自定义资源类型(数据源/知识库等) */
  customTypes?: PlusMenuResourceType[];
  /** 自定义类型面板:数据(受控,由外层按 panel 提供) */
  customPanelItems?: PlusMenuListItem[];
  customPanelLoading?: boolean;
  customPanelSelectedKeys?: string[];
  onCustomPanelToggle?: (typeKey: string, item: PlusMenuListItem) => void;
  /** 面板切到自定义类型时回调(用于懒加载数据) */
  onCustomPanelEnter?: (typeKey: string) => void;
  /** 底部「管理」入口 */
  onManage?: (panel: 'skill' | 'mcp') => void;
  /** 面板选中态高亮色(默认 indigo) */
  accentColor?: string;
  disabled?: boolean;
  title?: string;
}

const mcpKey = (m: PlusMenuMcpRef) => String(m.id || m.uuid || m.name);

const itemCls =
  'flex w-full items-center gap-2.5 px-2.5 py-2 text-[13px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/60 rounded-lg transition-colors cursor-pointer text-left';

const searchInputCls =
  'w-full h-8 pl-8 pr-2.5 rounded-lg bg-gray-100 dark:bg-gray-700/60 text-[13px] text-gray-700 dark:text-gray-200 placeholder:text-gray-400 outline-none focus:ring-1 focus:ring-indigo-300 dark:focus:ring-indigo-600 transition-shadow';

function PanelSearch({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative px-2 pb-1.5">
      <SearchOutlined className="absolute left-4.5 top-1/2 -translate-y-[calc(50%+3px)] text-xs text-gray-400 pointer-events-none" style={{ left: 18 }} />
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={searchInputCls} />
    </div>
  );
}

function PanelHeader({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-gray-100 dark:border-gray-700/60">
      <button
        type="button"
        className="h-6 w-6 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/60 transition-colors"
        onClick={onBack}
        title="返回"
      >
        <LeftOutlined className="text-[10px]" />
      </button>
      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{title}</span>
    </div>
  );
}

function EmptyText({ children }: { children: React.ReactNode }) {
  return <div className="px-3 py-6 text-center text-xs text-gray-400">{children}</div>;
}

export function PlusMenu({
  onAddFile,
  permissions,
  selectedPermission,
  onPermissionChange,
  playbooks,
  playbooksLoading,
  selectedPlaybook,
  onPlaybookChange,
  skills,
  skillsLoading,
  selectedSkills = [],
  onSkillsChange,
  mcps,
  mcpsLoading,
  selectedMcps = [],
  onMcpsChange,
  commands,
  onCommandSelect,
  customTypes,
  customPanelItems = [],
  customPanelLoading,
  customPanelSelectedKeys = [],
  onCustomPanelToggle,
  onCustomPanelEnter,
  onManage,
  accentColor = '#4f46e5',
  disabled,
  title,
}: PlusMenuProps) {
  const [open, setOpen] = useState(false);
  const [panel, setPanel] = useState<PlusMenuPanel>('root');
  const [search, setSearch] = useState('');
  const searchRef = useRef('');

  const badgeCount = selectedSkills.length + selectedMcps.length + customPanelSelectedKeys.length;

  const close = () => {
    setOpen(false);
    setPanel('root');
    setSearch('');
  };

  const goPanel = (p: PlusMenuPanel) => {
    setPanel(p);
    setSearch('');
    if (p.startsWith('custom:')) onCustomPanelEnter?.(p.slice(7));
  };

  const filter = <T,>(list: T[] | undefined, pick: (item: T) => string): T[] => {
    if (!list) return [];
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter((item) => pick(item).toLowerCase().includes(q));
  };

  const selectedSkillCodes = useMemo(() => new Set(selectedSkills.map((s) => s.skill_code)), [selectedSkills]);
  const selectedMcpKeys = useMemo(() => new Set(selectedMcps.map(mcpKey)), [selectedMcps]);
  const customSelectedSet = useMemo(() => new Set(customPanelSelectedKeys), [customPanelSelectedKeys]);

  const toggleSkill = (skill: PlusMenuSkillRef) => {
    if (!onSkillsChange) return;
    onSkillsChange(
      selectedSkillCodes.has(skill.skill_code)
        ? selectedSkills.filter((s) => s.skill_code !== skill.skill_code)
        : [...selectedSkills, skill],
    );
  };

  const toggleMcp = (mcp: PlusMenuMcpRef) => {
    if (!onMcpsChange) return;
    const key = mcpKey(mcp);
    onMcpsChange(
      selectedMcpKeys.has(key)
        ? selectedMcps.filter((m) => mcpKey(m) !== key)
        : [...selectedMcps, mcp],
    );
  };

  /** 列表项右侧选中标记 */
  const CheckMark = () => <CheckOutlined className="ml-auto text-xs flex-shrink-0" style={{ color: accentColor }} />;

  /** 列表项图标盒子(图标/首字母回退) */
  const IconBox = ({ icon, fallback, gradient }: { icon?: string; fallback: React.ReactNode; gradient: string }) => (
    <div className={classNames('h-7 w-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-xs font-semibold overflow-hidden', gradient)}>
      {icon ? <img src={icon} alt="" className="h-full w-full object-cover" /> : fallback}
    </div>
  );

  const renderCheckableRow = (opts: {
    key: string;
    checked: boolean;
    onClick: () => void;
    icon: React.ReactNode;
    title: string;
    description?: string;
    badge?: React.ReactNode;
    titleExtra?: React.ReactNode;
  }) => (
    <button type="button" key={opts.key} className={itemCls} onClick={opts.onClick} title={opts.description || opts.title}>
      {opts.icon}
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5">
          <span className="truncate">{opts.title}</span>
          {opts.titleExtra}
        </span>
        {opts.description && <span className="block truncate text-[11px] text-gray-400 dark:text-gray-500">{opts.description}</span>}
      </span>
      {opts.badge}
      {opts.checked && <CheckMark />}
    </button>
  );

  const renderContent = () => {
    if (panel === 'root') {
      return (
        <div className="w-56 py-1">
          {onAddFile && (
            <button type="button" className={itemCls} onClick={() => { onAddFile(); close(); }}>
              <PaperClipOutlined className="text-sm text-gray-500 dark:text-gray-400" />
              <span>添加文件</span>
            </button>
          )}
          {permissions && permissions.length > 0 && (
            <button type="button" className={itemCls} onClick={() => goPanel('permission')}>
              <SafetyOutlined className="text-sm text-amber-500" />
              <span>权限</span>
              <span className="ml-auto truncate text-[11px] text-gray-400 max-w-[88px]">
                {permissions.find((p) => p.key === selectedPermission)?.label}
              </span>
              <RightOutlined className="text-[10px] text-gray-400" />
            </button>
          )}
          {(playbooksLoading || (playbooks?.length ?? 0) > 0) && (
            <button type="button" className={itemCls} onClick={() => goPanel('playbook')}>
              <RocketOutlined className="text-sm text-indigo-500" />
              <span>剧本</span>
              {selectedPlaybook && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: accentColor }} />
              )}
              <RightOutlined className={classNames('text-[10px] text-gray-400', !selectedPlaybook && 'ml-auto')} />
            </button>
          )}
          {onSkillsChange && (
            <button type="button" className={itemCls} onClick={() => goPanel('skill')}>
              <AppstoreOutlined className="text-sm text-violet-500" />
              <span>技能</span>
              {selectedSkills.length > 0 ? (
                <span className="ml-auto text-[11px] font-medium" style={{ color: accentColor }}>{selectedSkills.length}</span>
              ) : (
                <RightOutlined className="ml-auto text-[10px] text-gray-400" />
              )}
            </button>
          )}
          {onMcpsChange && (
            <button type="button" className={itemCls} onClick={() => goPanel('mcp')}>
              <ApiOutlined className="text-sm text-emerald-500" />
              <span>MCP</span>
              {selectedMcps.length > 0 ? (
                <span className="ml-auto text-[11px] font-medium" style={{ color: accentColor }}>{selectedMcps.length}</span>
              ) : (
                <RightOutlined className="ml-auto text-[10px] text-gray-400" />
              )}
            </button>
          )}
          {commands && commands.length > 0 && (
            <button type="button" className={itemCls} onClick={() => goPanel('command')}>
              <CodeOutlined className="text-sm text-cyan-600" />
              <span>命令</span>
              <RightOutlined className="ml-auto text-[10px] text-gray-400" />
            </button>
          )}
          {customTypes?.map((ct) => (
            <button type="button" key={ct.key} className={itemCls} onClick={() => goPanel(`custom:${ct.key}`)}>
              {ct.icon}
              <span>{ct.label}</span>
              <RightOutlined className="ml-auto text-[10px] text-gray-400" />
            </button>
          ))}
        </div>
      );
    }

    if (panel === 'permission' && permissions) {
      return (
        <div className="w-64">
          <PanelHeader title="权限" onBack={() => setPanel('root')} />
          <div className="max-h-64 overflow-y-auto py-1">
            {permissions.map((p) =>
              renderCheckableRow({
                key: p.key,
                checked: selectedPermission === p.key,
                onClick: () => { onPermissionChange?.(p.key); close(); },
                icon: <SafetyOutlined className="text-sm text-amber-500" />,
                title: p.label,
                description: p.description,
              }),
            )}
          </div>
        </div>
      );
    }

    if (panel === 'playbook') {
      const list = filter(playbooks, (p) => `${p.playbook_name}`);
      return (
        <div className="w-72">
          <PanelHeader title="选择剧本" onBack={() => setPanel('root')} />
          <PanelSearch value={search} onChange={setSearch} placeholder="搜索剧本" />
          <div className="max-h-64 overflow-y-auto py-1">
            {playbooksLoading && <EmptyText><LoadingOutlined className="mr-1" />加载中…</EmptyText>}
            {!playbooksLoading && list.length === 0 && <EmptyText>暂无剧本</EmptyText>}
            {!playbooksLoading && list.map((pb) =>
              renderCheckableRow({
                key: String(pb.playbook_id),
                checked: selectedPlaybook?.playbook_id === pb.playbook_id,
                onClick: () => { onPlaybookChange?.(pb); close(); },
                icon: <RocketOutlined className="text-sm text-indigo-400" />,
                title: pb.playbook_name,
              }),
            )}
          </div>
        </div>
      );
    }

    if (panel === 'skill') {
      const list = filter(skills, (s) => `${s.name} ${s.description ?? ''}`);
      return (
        <div className="w-72">
          <PanelHeader title="选择技能" onBack={() => setPanel('root')} />
          <PanelSearch value={search} onChange={setSearch} placeholder="搜索技能" />
          <div className="max-h-64 overflow-y-auto py-1">
            {skillsLoading && <EmptyText><LoadingOutlined className="mr-1" />加载中…</EmptyText>}
            {!skillsLoading && list.length === 0 && <EmptyText>暂无可用技能</EmptyText>}
            {!skillsLoading && list.map((skill) =>
              renderCheckableRow({
                key: skill.skill_code,
                checked: selectedSkillCodes.has(skill.skill_code),
                onClick: () => toggleSkill(skill),
                icon: (
                  <IconBox
                    icon={skill.icon}
                    gradient="bg-gradient-to-br from-violet-500 to-indigo-600"
                    fallback={<AppstoreOutlined className="text-xs" />}
                  />
                ),
                title: skill.name,
                description: skill.description,
              }),
            )}
          </div>
          {onManage && (
            <div className="border-t border-gray-100 dark:border-gray-700/60 py-1">
              <button type="button" className={itemCls} onClick={() => { onManage('skill'); close(); }}>
                <SettingOutlined className="text-sm text-gray-400" />
                <span>管理技能</span>
              </button>
            </div>
          )}
        </div>
      );
    }

    if (panel === 'mcp') {
      const list = filter(mcps, (m) => `${m.name} ${m.description ?? ''}`);
      return (
        <div className="w-72">
          <PanelHeader title="选择 MCP 连接器" onBack={() => setPanel('root')} />
          <PanelSearch value={search} onChange={setSearch} placeholder="搜索 MCP" />
          <div className="max-h-64 overflow-y-auto py-1">
            {mcpsLoading && <EmptyText><LoadingOutlined className="mr-1" />加载中…</EmptyText>}
            {!mcpsLoading && list.length === 0 && <EmptyText>暂无可用 MCP</EmptyText>}
            {!mcpsLoading && list.map((mcp) => {
              const key = mcpKey(mcp);
              return renderCheckableRow({
                key,
                checked: selectedMcpKeys.has(key),
                onClick: () => toggleMcp(mcp),
                icon: (
                  <IconBox
                    icon={mcp.icon}
                    gradient="bg-gradient-to-br from-emerald-500 to-teal-600"
                    fallback={<ApiOutlined className="text-xs" />}
                  />
                ),
                title: mcp.name,
                description: mcp.description,
                titleExtra: mcp.available ? (
                  <span className="flex-shrink-0 rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-1.5 py-0.5 text-[10px] text-emerald-600 dark:text-emerald-400">Active</span>
                ) : undefined,
              });
            })}
          </div>
          {onManage && (
            <div className="border-t border-gray-100 dark:border-gray-700/60 py-1">
              <button type="button" className={itemCls} onClick={() => { onManage('mcp'); close(); }}>
                <SettingOutlined className="text-sm text-gray-400" />
                <span>管理 MCP</span>
              </button>
            </div>
          )}
        </div>
      );
    }

    if (panel === 'command' && commands) {
      const list = filter(commands, (c) => `${c.command} ${c.name} ${c.description ?? ''}`);
      return (
        <div className="w-72">
          <PanelHeader title="命令" onBack={() => setPanel('root')} />
          <PanelSearch value={search} onChange={setSearch} placeholder="搜索命令" />
          <div className="max-h-64 overflow-y-auto py-1">
            {list.length === 0 && <EmptyText>暂无可用命令</EmptyText>}
            {list.map((cmd) => (
              <button
                type="button"
                key={cmd.command}
                className={itemCls}
                onClick={() => { onCommandSelect?.(cmd); close(); }}
                title={cmd.description || cmd.name}
              >
                <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700/70 font-mono text-xs text-gray-500 dark:text-gray-300">/</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-mono text-[12px] text-gray-800 dark:text-gray-100">/{cmd.command}</span>
                  <span className="block truncate text-[11px] text-gray-400 dark:text-gray-500">{cmd.description || cmd.name}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (panel.startsWith('custom:')) {
      const typeKey = panel.slice(7);
      const meta = customTypes?.find((ct) => ct.key === typeKey);
      const list = filter(customPanelItems, (i) => `${i.title} ${i.description ?? ''}`);
      return (
        <div className="w-72">
          <PanelHeader title={meta?.label ?? ''} onBack={() => setPanel('root')} />
          <PanelSearch value={search} onChange={setSearch} placeholder={`搜索${meta?.label ?? ''}`} />
          <div className="max-h-64 overflow-y-auto py-1">
            {customPanelLoading && <EmptyText><LoadingOutlined className="mr-1" />加载中…</EmptyText>}
            {!customPanelLoading && list.length === 0 && <EmptyText>暂无数据</EmptyText>}
            {!customPanelLoading && list.map((item) =>
              renderCheckableRow({
                key: item.key,
                checked: customSelectedSet.has(item.key),
                onClick: () => onCustomPanelToggle?.(typeKey, item),
                icon: item.icon ?? <DatabaseOutlined className="text-sm text-gray-400" />,
                title: item.title,
                description: item.description,
                badge: item.badge,
              }),
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <Popover
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) { setPanel('root'); setSearch(''); }
      }}
      content={renderContent()}
      trigger="click"
      placement="topLeft"
      arrow={false}
      overlayClassName="[&_.ant-popover-inner]:!p-0 [&_.ant-popover-inner]:!rounded-xl [&_.ant-popover-inner]:!shadow-xl"
    >
      <Badge count={badgeCount} size="small" offset={[-4, 4]} color={accentColor}>
        <button
          type="button"
          disabled={disabled}
          title={title ?? '添加文件 / 剧本 / 技能 / MCP / 命令'}
          className={classNames(
            'h-8 w-8 rounded-full flex items-center justify-center border transition-all flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed',
            open
              ? 'border-indigo-300 dark:border-indigo-600 text-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 rotate-45'
              : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-indigo-500 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20',
          )}
        >
          <PlusOutlined className="text-sm transition-transform" />
        </button>
      </Badge>
    </Popover>
  );
}

/** 输入框上方选中项 chip(参考 WorkBuddy 选中态):图标/斜杠前缀 + 名称 + 移除按钮 */
export function SelectionChip({
  icon,
  prefix,
  label,
  onRemove,
  removeTitle = '移除',
  theme = 'indigo',
}: {
  icon?: React.ReactNode;
  prefix?: string;
  label: string;
  onRemove?: () => void;
  removeTitle?: string;
  theme?: 'indigo' | 'violet' | 'emerald' | 'amber' | 'cyan';
}) {
  const themeCls: Record<string, string> = {
    indigo: 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-700 text-indigo-600 dark:text-indigo-300',
    violet: 'bg-violet-50 dark:bg-violet-900/30 border-violet-200 dark:border-violet-700 text-violet-600 dark:text-violet-300',
    emerald: 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-700 text-emerald-600 dark:text-emerald-300',
    amber: 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-700 text-amber-600 dark:text-amber-300',
    cyan: 'bg-cyan-50 dark:bg-cyan-900/30 border-cyan-200 dark:border-cyan-700 text-cyan-600 dark:text-cyan-300',
  };
  return (
    <span className={classNames('inline-flex items-center gap-1 rounded-md border px-2 py-1 text-sm', themeCls[theme])}>
      {prefix && <span className="text-xs opacity-60">{prefix}</span>}
      {icon}
      <span className="max-w-[200px] truncate font-medium">{label}</span>
      {onRemove && (
        <button type="button" className="ml-0.5 opacity-60 transition-colors hover:text-red-500 hover:opacity-100" onClick={onRemove} title={removeTitle}>
          ×
        </button>
      )}
    </span>
  );
}
