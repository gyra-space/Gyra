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
 *
 * 浮层定位策略(修复弹窗冲出屏幕):
 *   - 输入框贴近视口底部时,antd 的 autoAdjustOverflow 只能在「上方放不下就翻转
 *     到下方」,两侧都放不下时无法收缩自身,弹窗必然溢出。这里改为测量锚点到
 *     视口上/下两侧的可用空间,动态收缩列表高度,保证弹窗整体始终装得下屏幕。
 *
 * 内嵌搜索框(过滤增强):
 *   - 原先「在输入框 trigger 字符后继续打字」的过滤保留不变;
 *   - 表头升级为可点击输入的搜索框,鼠标用户不用回键盘也能检索;
 *   - 搜索框内 ↑↓/Enter/Esc 直接复用同一套键盘导航;
 *   - 两个过滤入口不叠加:输入框过滤词变化即清空搜索框(后打字的一方生效)。
 */

import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { Popover } from 'antd';
import { CloseCircleFilled, LoadingOutlined, SearchOutlined } from '@ant-design/icons';
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

// ---- 视口自适应尺寸 ----
/** 列表默认最大高度(px) */
const MAX_LIST_HEIGHT = 340;
/** 收缩下限:再小就交给 antd 的翻转/平移兜底 */
const MIN_LIST_HEIGHT = 140;
/** 弹窗外沿与视口边缘的安全边距 */
const VIEWPORT_MARGIN = 12;
/** 表头 + 底部提示栏 + 列表内边距的固定高度开销估值 */
const POPOVER_CHROME = 72;

interface IndexedItem<T> extends TriggerMenuItem<T> {
  /** 全局序号,用于键盘导航与高亮 */
  index: number;
}

const rowCls =
  'flex w-full items-center gap-3 px-3 py-2.5 text-left rounded-lg transition-colors cursor-pointer';

const NAVI_KEYS = new Set(['ArrowDown', 'ArrowUp', 'Enter', 'Escape']);

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
  /** 搜索框输入的过滤词;null 表示尚未在搜索框主动输入(跟随输入框过滤词 query) */
  const [ownSearch, setOwnSearch] = useState<string | null>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [listMaxH, setListMaxH] = useState(MAX_LIST_HEIGHT);

  const q = query.trim();
  /** 搜索框回显:优先展示搜索框自己的输入,否则回显输入框过滤词 */
  const searchValue = ownSearch ?? q;
  /**
   * 实际参与过滤的关键词:
   * - 未在搜索框输入过 → 沿用输入框过滤词(既有行为);
   * - 在搜索框输入过(含清空)→ 以搜索框为准,不再叠加输入框过滤词
   *   (两者叠加会让「搜索框改词后仍被旧 token 卡成空列表」)。
   */
  const filterQuery = ownSearch === null ? q : ownSearch.trim();

  // 输入框过滤词变化(含菜单关闭复位)即放弃搜索框的独立过滤,高亮回到首项
  useEffect(() => {
    setOwnSearch(null);
    setActive(0);
  }, [q, open]);

  // 打开时测量锚点到视口上下两侧的空间,收缩列表高度防止弹窗溢出屏幕
  useEffect(() => {
    if (!open) return;
    const el = anchorRef.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      const viewportH = window.innerHeight || document.documentElement.clientHeight;
      const spaceAbove = rect.top - VIEWPORT_MARGIN;
      const spaceBelow = viewportH - rect.bottom - VIEWPORT_MARGIN;
      // 取上下两侧更宽裕的一侧:antd 在 topLeft 放不下时会自动翻转到下方,
      // 只要弹窗总高不超过较大一侧的空间,就不会溢出视口
      const available = Math.max(spaceAbove, spaceBelow) - POPOVER_CHROME;
      setListMaxH(Math.max(MIN_LIST_HEIGHT, Math.min(MAX_LIST_HEIGHT, Math.round(available))));
    };
    measure();
    window.addEventListener('resize', measure);
    // 捕获阶段监听:会话区等内部容器的滚动同样会改变锚点相对视口的位置
    window.addEventListener('scroll', measure, true);
    // 输入框随内容增高/分组数据异步载入也会改变可用空间
    let ro: ResizeObserver | undefined;
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(measure);
      ro.observe(el);
    }
    return () => {
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
      ro?.disconnect();
    };
  }, [open]);

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
        items: filterQuery
          ? g.items.filter((it) =>
              matches(filterQuery, it.title, it.description, ...(it.keywords ?? [])),
            )
          : g.items,
      }))
      .filter((g) => g.items.length > 0 || g.loading)
      .map((g) => ({
        ...g,
        items: g.items.map((item) => ({ ...item, index: i++ })),
      }));
  }, [groups, filterQuery]);

  const flatItems = useMemo<IndexedItem<T>[]>(
    () => indexedGroups.flatMap((g) => g.items),
    [indexedGroups],
  );
  const itemCount = flatItems.length;
  const clampedActive = itemCount === 0 ? 0 : Math.min(active, itemCount - 1);

  /** 键盘导航核心,输入框与搜索框共用(搜索框直呼,输入框经 ref 转交) */
  const handleKeyInternal = (e: React.KeyboardEvent): boolean => {
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
  };

  useImperativeHandle(ref, () => ({
    handleKey: (e) => handleKeyInternal(e),
  }));

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // 输入法组词阶段的按键只作用于候选词,不触发菜单导航/选中
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    if (NAVI_KEYS.has(e.key)) handleKeyInternal(e);
  };

  const content = (
    <div className="w-[380px]">
      <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1.5 border-b border-gray-100 dark:border-gray-700/60">
        <SearchOutlined className="text-[11px] text-gray-400 flex-shrink-0" />
        {/* 触发字符前缀:与旧版「#过滤词」提示保持同一视觉上下文 */}
        <span className="flex-shrink-0 font-mono text-[12px] text-gray-400 dark:text-gray-500">
          {triggerChar}
        </span>
        <input
          ref={searchInputRef}
          value={searchValue}
          placeholder={placeholder}
          onChange={(e) => {
            setOwnSearch(e.target.value);
            setActive(0);
          }}
          onKeyDown={handleSearchKeyDown}
          className="min-w-0 flex-1 bg-transparent text-[12px] text-gray-700 dark:text-gray-200 placeholder:text-gray-400 outline-none"
        />
        {searchValue && (
          <button
            type="button"
            className="flex-shrink-0 text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400 transition-colors cursor-pointer"
            onClick={() => {
              setOwnSearch('');
              setActive(0);
              searchInputRef.current?.focus();
            }}
            title="清空过滤"
          >
            <CloseCircleFilled className="text-[11px]" />
          </button>
        )}
      </div>
      <div className="overflow-y-auto py-1.5 px-1.5" style={{ maxHeight: listMaxH }}>
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
      {/* 锚点容器:测量上下可用空间的参照(children 外再包一层不改变布局) */}
      <div ref={anchorRef}>{children}</div>
    </Popover>
  );
}

/** 泛型 + forwardRef 组合:外层断言保留 forwardRef 的 ref 类型推导 */
export const TriggerMenu = forwardRef(TriggerMenuInner) as <T = unknown>(
  props: TriggerMenuProps<T> & { ref?: React.Ref<TriggerMenuHandle> },
) => React.ReactElement;
