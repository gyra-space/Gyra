'use client';

/**
 * 通用 trigger 浮层菜单(`/` `@` `#` 共用)。
 *
 * 从原 slash-menu.tsx 抽出:分组渲染 + 过滤 + ↑↓/Enter/Esc 键盘导航 + 受控 Popover。
 * 调用方只需按 trigger 类型构建 groups,交互行为与视觉完全一致 —— 这是
 * 「场景空间全局一致输入体验」的落点。
 *
 * 与原 slash-menu 的行为差异(均为体验修正):
 *   1. 过滤词变化时重置高亮到首项(原实现保留旧位置,搜索后高亮会漂到无关项)
 *   2. 行序号预计算,不再依赖渲染时的外部累加变量
 */

import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from 'react';
import { Popover } from 'antd';
import { LoadingOutlined, SearchOutlined } from '@ant-design/icons';
import classNames from 'classnames';

/** 菜单项。data 携带原始对象,供 onSelect 回传,避免调用方再按 key 反查。 */
export interface TriggerMenuItem<T = unknown> {
  key: string;
  icon: React.ReactNode;
  title: string;
  description?: string;
  /** 标题用等宽字体(命令类,如 `/compact`) */
  mono?: boolean;
  /** 额外匹配关键词(不展示),用于别名 / 中英文双命中 */
  keywords?: string[];
  /** 原始数据 */
  data?: T;
}

export interface TriggerMenuGroup<T = unknown> {
  key: string;
  label: string;
  items: TriggerMenuItem<T>[];
  /** 该组加载中且暂无数据(如 MCP 首屏),显示 loading 占位 */
  loading?: boolean;
}

export interface TriggerMenuProps<T = unknown> {
  open: boolean;
  /** 过滤词(trigger 字符之后到光标之间的文本) */
  query: string;
  /** trigger 字符,仅用于搜索提示前缀(如 `/compact`) */
  triggerChar: string;
  groups: TriggerMenuGroup<T>[];
  /** 无匹配项时的文案 */
  emptyText?: string;
  /** 未输入过滤词时的提示文案 */
  placeholder?: string;
  onSelect: (item: TriggerMenuItem<T>) => void;
  /** 受控关闭(Esc / 选中后) */
  onClose: () => void;
  children: React.ReactNode;
}

export interface TriggerMenuHandle {
  /** 处理输入框 keydown;返回 true 表示事件已被菜单消费 */
  handleKey: (e: React.KeyboardEvent) => boolean;
}

/** 大小写不敏感的多字段匹配:命中任一字段即保留 */
export function matches(q: string, ...fields: (string | undefined)[]): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  return fields.some((f) => (f || '').toLowerCase().includes(needle));
}

interface IndexedItem<T> extends TriggerMenuItem<T> {
  /** 全局序号,用于键盘导航与高亮 */
  index: number;
}

const rowCls =
  'flex w-full items-center gap-3 px-3 py-2.5 text-left rounded-lg transition-colors cursor-pointer';

function TriggerMenuInner<T>(
  {
    open,
    query,
    triggerChar,
    groups,
    emptyText = '无匹配项',
    placeholder = '选择类型或输入关键词过滤',
    onSelect,
    onClose,
    children,
  }: TriggerMenuProps<T>,
  ref: React.Ref<TriggerMenuHandle>,
) {
  const [active, setActive] = useState(0);
  const q = query.trim();

  // 过滤词变化后回到首项:否则上一次的高亮位置会漂到不相关的条目上
  useEffect(() => {
    setActive(0);
  }, [q]);

  /**
   * 过滤 + 过滤空组 + 预计算全局序号(供键盘导航与高亮对齐)。
   *
   * 过滤放在组件内而非调用方:三个 trigger 菜单共用同一套匹配规则,
   * 调用方只需给出全量条目,不必各自实现一遍过滤。
   * loading 组即使无数据也保留,以便显示加载占位。
   */
  const indexedGroups = useMemo(() => {
    let i = 0;
    return groups
      .map((g) => ({
        ...g,
        items: q
          ? g.items.filter((it) =>
              matches(q, it.title, it.description, ...(it.keywords ?? [])),
            )
          : g.items,
      }))
      .filter((g) => g.items.length > 0 || g.loading)
      .map((g) => ({
        ...g,
        items: g.items.map((item) => ({ ...item, index: i++ })),
      }));
  }, [groups, q]);

  const flatItems = useMemo<IndexedItem<T>[]>(
    () => indexedGroups.flatMap((g) => g.items),
    [indexedGroups],
  );
  const itemCount = flatItems.length;
  const clampedActive = itemCount === 0 ? 0 : Math.min(active, itemCount - 1);

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
        const item = flatItems[clampedActive];
        if (item) {
          onSelect(item);
          onClose();
        }
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

  const content = (
    <div className="w-[380px]">
      <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1 border-b border-gray-100 dark:border-gray-700/60">
        <SearchOutlined className="text-[11px] text-gray-400" />
        {q ? (
          <span className="text-[12px] text-indigo-500 font-medium truncate">
            {triggerChar}
            {q}
          </span>
        ) : (
          <span className="text-[12px] text-gray-400">{placeholder}</span>
        )}
      </div>
      <div className="max-h-[340px] overflow-y-auto py-1.5 px-1.5">
        {indexedGroups.length === 0 && (
          <div className="px-3 py-8 text-center text-xs text-gray-400">{emptyText}</div>
        )}
        {indexedGroups.map((g) => (
          <div key={g.key} className="mb-1 last:mb-0">
            <div className="px-2 pt-1.5 pb-1 text-[11px] font-medium text-gray-400 dark:text-gray-500">
              {g.label}
            </div>
            {g.loading && g.items.length === 0 ? (
              <div className="px-3 py-3 text-xs text-gray-400">
                <LoadingOutlined className="mr-1" />
                加载中…
              </div>
            ) : (
              g.items.map((item) => (
                <button
                  type="button"
                  key={item.key}
                  className={classNames(
                    rowCls,
                    item.index === clampedActive && 'bg-indigo-50 dark:bg-indigo-900/20',
                  )}
                  onMouseEnter={() => setActive(item.index)}
                  onClick={() => {
                    onSelect(item);
                    onClose();
                  }}
                  title={item.description || item.title}
                >
                  {item.icon}
                  <span className="min-w-0 flex-1">
                    <span
                      className={classNames(
                        'block truncate text-[13px] font-medium text-gray-800 dark:text-gray-100',
                        item.mono && 'font-mono',
                      )}
                    >
                      {item.title}
                    </span>
                    {item.description && (
                      <span className="block truncate text-[12px] text-gray-400 dark:text-gray-500">
                        {item.description}
                      </span>
                    )}
                  </span>
                </button>
              ))
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
}

/** 泛型 + forwardRef 组合:外层断言保留 forwardRef 的 ref 类型推导 */
export const TriggerMenu = forwardRef(TriggerMenuInner) as <T = unknown>(
  props: TriggerMenuProps<T> & { ref?: React.Ref<TriggerMenuHandle> },
) => React.ReactElement;
