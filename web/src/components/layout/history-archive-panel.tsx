'use client';

import { apiInterceptors, delDialogue, getDialogueListBByFilter } from '@/client/api';
import { ChatContext } from '@/contexts';
import { getUserId } from '@/utils/storage';
import { DeleteOutlined, MenuFoldOutlined, SearchOutlined } from '@ant-design/icons';
import { App, Input, Spin, Tooltip, Typography } from 'antd';
import cls from 'classnames';
import moment from 'moment';
import 'moment/locale/zh-cn';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Dialogue {
  chat_mode: string;
  conv_uid: string;
  conv_session_id?: string;
  user_input?: string;
  select_param?: string;
  app_code?: string;
  user_name?: string;
  gmt_created?: string;
  gmt_modified?: string;
  workspace_id?: number | null;
  task_id?: number | null;
  workspace_name?: string;
  workspace_code?: string;
  conv_type?: string;
}

type ConvType = 'agent' | 'workspace' | 'task';

const CONV_TYPE_LABEL: Record<ConvType, string> = {
  agent: 'Agent',
  workspace: '空间',
  task: '任务',
};

/** 由后端 conv_type 或 workspace_id/task_id 推导会话类型 */
function getConvType(dialogue: Dialogue): ConvType {
  if (dialogue.conv_type === 'task' || dialogue.conv_type === 'workspace' || dialogue.conv_type === 'agent') {
    return dialogue.conv_type;
  }
  if (dialogue.workspace_id && dialogue.task_id) return 'task';
  if (dialogue.workspace_id) return 'workspace';
  return 'agent';
}

/** 从 user_input(可能是 JSON 字符串)提取可读文本 */
function extractUserText(raw: unknown): string {
  if (typeof raw !== 'string' || !raw) return '';
  if (raw.startsWith('{')) {
    try {
      const obj = JSON.parse(raw);
      const content = obj.data?.content || obj.content;
      if (typeof content === 'string') return content;
      if (content && typeof content === 'object') return JSON.stringify(content);
      if (content) return String(content);
      return raw;
    } catch {
      return raw;
    }
  }
  return raw;
}

interface DialogueListItem {
  key: string;
  name: string | undefined;
  dialogue: Dialogue;
}

interface GroupedDialogues {
  [key: string]: DialogueListItem[];
}

const TYPE_TAG_CLS: Record<ConvType, string> = {
  workspace:
    'text-indigo-500 border-indigo-200 bg-indigo-50 dark:text-indigo-300 dark:border-indigo-800 dark:bg-indigo-900/30',
  task: 'text-amber-600 border-amber-200 bg-amber-50 dark:text-amber-300 dark:border-amber-800 dark:bg-amber-900/30',
  agent: 'text-gray-500 border-gray-200 bg-gray-50 dark:text-gray-400 dark:border-gray-700 dark:bg-gray-800',
};

const TYPE_DOT_CLS: Record<ConvType, string> = {
  workspace: 'bg-indigo-400 dark:bg-indigo-500',
  task: 'bg-amber-400 dark:bg-amber-500',
  agent: 'bg-gray-300 dark:bg-gray-600',
};

interface HistoryArchivePanelProps {
  /** 面板是否打开(inline 模式下忽略,恒为展示) */
  open: boolean;
  onClose?: () => void;
  /** 面板锚定位置:侧边栏宽度(展开 260 / 折叠 64),inline 模式下忽略 */
  anchorLeft?: number;
  /** 内嵌模式:作为对话页左侧常驻栏渲染,无遮罩/浮层定位/关闭按钮 */
  inline?: boolean;
  /** 仅展示该 Agent 的独立会话(无空间归属);设置后类型分类 tab 无意义,自动隐藏 */
  appCode?: string;
  /** inline 模式下渲染折叠按钮,点击收起面板 */
  onCollapse?: () => void;
}

/**
 * 用户维度历史会话档案浮层:从侧边栏右侧浮出。
 * 空间/任务会话在所属空间内管理,本面板承担"跨域找回 + 最近恢复"的档案职责,
 * 侧边栏不再常驻历史列表,避免与空间内列表重复。
 */
export default function HistoryArchivePanel({ open, onClose, anchorLeft = 0, inline = false, appCode, onCollapse }: HistoryArchivePanelProps) {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { modal, message } = App.useApp();
  const { dialogueList, refreshDialogList } = useContext(ChatContext);

  const [items, setItems] = useState<DialogueListItem[]>([]);
  const [searchValue, setSearchValue] = useState('');
  const [convTypeFilter, setConvTypeFilter] = useState<'all' | ConvType>('all');
  const [loading, setLoading] = useState(false);
  const searchSeqRef = useRef(0);

  const currentConvId = searchParams?.get('conv_uid') || '';

  useEffect(() => {
    if (i18n.language === 'zh') moment.locale('zh-cn');
    if (i18n.language === 'en') moment.locale('en');
  }, [i18n.language]);

  // Esc 关闭面板(仅浮层模式)
  useEffect(() => {
    if (!open || inline) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose, inline]);

  // 去重:同一 conv_uid 保留最后活动时间最新的一条
  const dedupByConvUid = useCallback((list: DialogueListItem[]): DialogueListItem[] => {
    const map = new Map<string, DialogueListItem>();
    for (const item of list) {
      const key = item.dialogue.conv_uid;
      if (!key) {
        map.set(`__no_key_${map.size}`, item);
        continue;
      }
      const prev = map.get(key);
      if (!prev) {
        map.set(key, item);
        continue;
      }
      const prevTime = prev.dialogue.gmt_modified || prev.dialogue.gmt_created || '';
      const curTime = item.dialogue.gmt_modified || item.dialogue.gmt_created || '';
      if (curTime > prevTime) map.set(key, item);
    }
    return Array.from(map.values());
  }, []);

  /** 从 ChatContext 的全量会话构建列表 */
  const buildFromContext = useCallback((): DialogueListItem[] => {
    const raw = (dialogueList?.[1] as unknown as Dialogue[] | undefined) || [];
    return dedupByConvUid(
      raw.map((dialogue): DialogueListItem => ({
        key: dialogue?.conv_uid,
        name: extractUserText(dialogue.user_input) || dialogue.select_param,
        dialogue,
      })),
    );
  }, [dialogueList, dedupByConvUid]);

  // 打开时重建列表;全局列表变化(新会话/标题更新)时同步(inline 模式常驻,始终同步)
  useEffect(() => {
    if (!open && !inline) return;
    setItems(buildFromContext());
  }, [open, inline, buildFromContext]);

  const handleSearch = async (value: string) => {
    setSearchValue(value);
    if (!value.trim()) {
      setItems(buildFromContext());
      return;
    }
    const seq = ++searchSeqRef.current;
    setLoading(true);
    const [, data] = await apiInterceptors(getDialogueListBByFilter(value, getUserId()));
    // 丢弃过期搜索响应(快速连续输入时只保留最后一次)
    if (seq !== searchSeqRef.current) return;
    if (data) {
      const di = (data as unknown as Dialogue[]).map(
        (dialogue): DialogueListItem => ({
          key: dialogue?.conv_uid,
          name: extractUserText(dialogue.user_input) || dialogue.select_param,
          dialogue,
        }),
      );
      setItems(dedupByConvUid(di));
    } else {
      setItems([]);
    }
    setLoading(false);
  };

  const handleDel = (d: Dialogue) => {
    modal.confirm({
      title: t('delete_chat'),
      content: t('delete_chat_confirm'),
      centered: true,
      onOk: async () => {
        const [err] = await apiInterceptors(delDialogue(d.conv_uid));
        if (err) return;
        message.success(t('delete_success'));
        await refreshDialogList?.();
        setItems(buildFromContext());
      },
    });
  };

  const handleOpen = (d: Dialogue) => {
    const sessionParam = d.conv_session_id || d.conv_uid;
    const convType = getConvType(d);
    // 空间/任务会话:跳回所属空间打开;Agent 会话:留在 /chat 对话页
    if ((convType === 'workspace' || convType === 'task') && d.workspace_code) {
      const params = new URLSearchParams();
      params.set('id', d.workspace_code);
      params.set('conv_uid', sessionParam);
      if (convType === 'task' && d.task_id) params.set('task_id', String(d.task_id));
      router.push(`/workspaces/detail?${params.toString()}`);
    } else {
      router.push(`/chat/?conv_uid=${sessionParam}&app_code=${d.app_code}`);
    }
    onClose?.();
  };

  const filtered = useMemo(() => {
    // appCode 过滤:只看该 Agent 的独立会话(无空间归属,空间内会话由空间管理)
    const scoped = appCode
      ? items.filter((item) => item.dialogue.app_code === appCode && !item.dialogue.workspace_id)
      : items;
    if (convTypeFilter === 'all') return scoped;
    return scoped.filter((item) => getConvType(item.dialogue) === convTypeFilter);
  }, [items, convTypeFilter, appCode]);

  const getWeekRange = useCallback(
    (date: string) => {
      const m = moment(date);
      const startOfWeek = m.clone().startOf('week');
      const now = moment();
      if (now.isSame(startOfWeek, 'week')) return t('this_week');
      if (now.clone().subtract(1, 'week').isSame(startOfWeek, 'week')) return t('last_week');
      const weeksAgo = Math.floor(now.diff(startOfWeek, 'weeks'));
      return `${weeksAgo} ${t('weeks_ago')}`;
    },
    [t],
  );

  const sortedGroups = useMemo(() => {
    // 按周分组
    const grouped = filtered.reduce((groups, item) => {
      const date = item.dialogue.gmt_modified || item.dialogue.gmt_created;
      const weekRange = date ? getWeekRange(date) : t('unknown');
      if (!groups[weekRange]) groups[weekRange] = [];
      groups[weekRange].push(item);
      return groups;
    }, {} as GroupedDialogues);
    // 组内按最近活跃倒序
    for (const [key, list] of Object.entries(grouped)) {
      grouped[key] = [...list].sort((a, b) => {
        const at = a.dialogue.gmt_modified || a.dialogue.gmt_created || '';
        const bt = b.dialogue.gmt_modified || b.dialogue.gmt_created || '';
        return bt.localeCompare(at);
      });
    }
    // 组间排序:本周 > 上周 > X周前 > 未知
    return Object.entries(grouped).sort((a, b) => {
      const thisWeekKey = t('this_week');
      const lastWeekKey = t('last_week');
      const weeksAgoKey = t('weeks_ago');
      const unknownKey = t('unknown');
      const getGroupOrder = (groupName: string): number => {
        if (groupName === thisWeekKey) return 1;
        if (groupName === lastWeekKey) return 2;
        if (groupName.includes(weeksAgoKey)) {
          const match = groupName.match(/\d+/);
          const weeksNum = match ? parseInt(match[0], 10) : 999;
          return 3 + weeksNum;
        }
        if (groupName === unknownKey) return 9999;
        return 9998;
      };
      return getGroupOrder(a[0]) - getGroupOrder(b[0]);
    });
  }, [filtered, getWeekRange, t]);

  if (!open && !inline) return null;

  const panelBody = (
    <>
        {/* 头部 */}
        <div className='flex items-center justify-between px-4 h-[52px] border-b border-gray-100 dark:border-gray-800 flex-shrink-0'>
          <div className='flex items-center gap-2'>
            <span className='text-[14px] font-medium text-gray-800 dark:text-gray-100'>{t('chat_history')}</span>
            <span className='text-[11px] text-gray-400'>{filtered.length}</span>
          </div>
          {!inline && (
            <Tooltip title={t('Close_Sidebar') || '关闭'}>
              <span
                className='w-7 h-7 flex items-center justify-center rounded-lg cursor-pointer text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800'
                onClick={onClose}
              >
                ✕
              </span>
            </Tooltip>
          )}
          {inline && onCollapse && (
            <Tooltip title={t('Close_Sidebar') || '收起'}>
              <span
                className='w-7 h-7 flex items-center justify-center rounded-lg cursor-pointer text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800'
                onClick={onCollapse}
              >
                <MenuFoldOutlined style={{ fontSize: 13 }} />
              </span>
            </Tooltip>
          )}
        </div>

        {/* 搜索 */}
        <div className='px-4 pt-3 flex-shrink-0'>
          <Input
            size='small'
            prefix={<SearchOutlined className='text-gray-300' />}
            placeholder='搜索历史会话…'
            allowClear
            value={searchValue}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>

        {/* 类型过滤:按 Agent 过滤时全是 Agent 类型,tab 无意义,隐藏 */}
        {!appCode && (
        <div className='flex items-center gap-2 px-4 py-2.5 flex-shrink-0'>
          {(['all', 'agent', 'workspace', 'task'] as const).map((key) => {
            const label = key === 'all' ? '全部' : CONV_TYPE_LABEL[key];
            return (
              <span
                key={key}
                className={cls(
                  'px-2.5 py-0.5 rounded-full text-[12px] cursor-pointer border transition-colors select-none',
                  convTypeFilter === key
                    ? 'bg-indigo-50 text-indigo-600 border-indigo-200 dark:bg-indigo-900/40 dark:text-indigo-300 dark:border-indigo-800'
                    : 'text-gray-500 border-gray-200 hover:bg-gray-50 dark:text-gray-400 dark:border-gray-700 dark:hover:bg-gray-800',
                )}
                onClick={() => setConvTypeFilter(key)}
              >
                {label}
              </span>
            );
          })}
        </div>
        )}

        {/* 列表 */}
        <div className='flex-1 min-h-0 overflow-y-auto custom-scrollbar px-2 pb-3'>
          {loading ? (
            <div className='flex justify-center py-8'><Spin size='small' /></div>
          ) : sortedGroups.length === 0 ? (
            <div className='px-4 text-gray-400 text-xs py-8 text-center'>
              {searchValue ? t('no_matching_session') : t('no_history_session')}
            </div>
          ) : (
            sortedGroups.map(([week, list], index) => (
              <div key={`group-${index}`} className='mb-3'>
                <div className='px-2 py-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wider'>
                  {week}
                </div>
                {list.map((item) => {
                  const d = item.dialogue;
                  const convType = getConvType(d);
                  const active = currentConvId === (d.conv_session_id || d.conv_uid);
                  return (
                    <div
                      key={item.key}
                      className={cls(
                        'group/item flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer mb-0.5 hover:bg-gray-50 dark:hover:bg-gray-800',
                        active && 'bg-gray-50 dark:bg-gray-800',
                      )}
                      onClick={() => handleOpen(d)}
                    >
                      <span className={cls('w-2 h-2 rounded-full flex-shrink-0', TYPE_DOT_CLS[convType])} />
                      <div className='flex-1 min-w-0'>
                        <div className='flex items-center justify-between gap-2'>
                          <Typography.Text
                            ellipsis={{ tooltip: false }}
                            className={cls('text-[13px] leading-5', active ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-700 dark:text-gray-200')}
                          >
                            {item.name || 'Untitled'}
                          </Typography.Text>
                          <span className='text-[10px] text-gray-300 dark:text-gray-600 flex-shrink-0'>
                            {d.gmt_modified ? moment(d.gmt_modified).format('MM-DD') : ''}
                          </span>
                        </div>
                        <div className='flex items-center gap-1.5 mt-0.5 min-w-0'>
                          {!appCode && (
                            <span className={cls('flex-shrink-0 inline-flex items-center px-1 rounded text-[10px] leading-4 border', TYPE_TAG_CLS[convType])}>
                              {CONV_TYPE_LABEL[convType]}
                            </span>
                          )}
                          {!appCode && convType !== 'agent' && d.workspace_name && (
                            <span className='text-[11px] text-gray-400 dark:text-gray-500 truncate'>{d.workspace_name}</span>
                          )}
                        </div>
                      </div>
                      <DeleteOutlined
                        className='text-gray-300 hover:text-red-500 opacity-0 group-hover/item:opacity-100 transition-opacity flex-shrink-0'
                        style={{ fontSize: 13 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDel(d);
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>
    </>
  );

  // 内嵌模式:作为对话页左侧常驻栏,无遮罩/浮层
  if (inline) {
    return (
      <div className='flex flex-col w-[300px] flex-shrink-0 h-full border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900'>
        {panelBody}
      </div>
    );
  }

  return (
    <>
      <style>{`
        @keyframes gyra-hpanel-in { from { transform: translateX(-18px); opacity: 0 } to { transform: none; opacity: 1 } }
        .gyra-hpanel { animation: gyra-hpanel-in 0.18s ease-out; }
        .gyra-hpanel-fade { animation: gyra-hpanel-in 0.18s ease-out; }
      `}</style>
      {/* 遮罩:仅覆盖内容区(不遮侧边栏) */}
      <div
        className='gyra-hpanel-fade fixed inset-y-0 z-[900] bg-black/25'
        style={{ left: anchorLeft, right: 0 }}
        onClick={onClose}
      />
      {/* 档案面板:从侧边栏右侧浮出 */}
      <div
        className='gyra-hpanel fixed inset-y-0 z-[901] flex flex-col w-[380px] bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 shadow-2xl'
        style={{ left: anchorLeft }}
      >
        {panelBody}
      </div>
    </>
  );
}
