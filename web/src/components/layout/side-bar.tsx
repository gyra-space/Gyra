'use client';
import { ChatContext } from '@/contexts';
import { STORAGE_LANG_KEY, STORAGE_THEME_KEY } from '@/utils/constants/index';
import Icon, {
  ApiOutlined,
  BookOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  FileTextOutlined,
  GlobalOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MessageOutlined,
  SettingOutlined,
  RobotOutlined,
  ExperimentOutlined,
  SafetyOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  MoonOutlined,
  SunOutlined,
  RightOutlined,
  DeploymentUnitOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Popover, Tooltip } from 'antd';
import cls from 'classnames';
import moment from 'moment';
import 'moment/locale/zh-cn';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ModelSvg from '../icons/model-svg';
import UserBar from './user-bar';
import { useUserPermissions } from '@/hooks/use-user-permissions';

type SettingItem = {
  key: string;
  name: string;
  icon: ReactNode;
  noDropdownItem?: boolean;
  onClick?: () => void;
  items?: any[];
  onSelect?: (p: { key: string }) => void;
  defaultSelectedKeys?: string[];
  placement?: 'top' | 'topLeft';
  disable?: boolean;
};

export type RouteItem = {
  key: string;
  name: string;
  icon?: ReactNode;
  path?: string;
  isActive?: boolean;
  children?: RouteItem[];
  hideInMenu?: boolean;
  /** 非导航型菜单项(如打开历史档案面板) */
  onClick?: () => void;
};

function SideBar() {
  const { isMenuExpand, setIsMenuExpand, mode, setMode } = useContext(ChatContext);
  const pathname = usePathname();
  const { t, i18n } = useTranslation();
  const [logo, setLogo] = useState<string>('/logo_zh_latest.png');
  const [closedSections, setClosedSections] = useState<Record<string, boolean>>({});
  const { hasResourceRead, hasPermission } = useUserPermissions();

  const handleToggleMenu = useCallback(() => {
    setIsMenuExpand(!isMenuExpand);
  }, [isMenuExpand, setIsMenuExpand]);

  const handleToggleTheme = useCallback(() => {
    const theme = mode === 'light' ? 'dark' : 'light';
    setMode(theme);
    localStorage.setItem(STORAGE_THEME_KEY, theme);
  }, [mode, setMode]);

  // 暂时注释，后续完善中英文
  const handleChangeLang = useCallback(() => {
    const language = i18n.language === 'en' ? 'zh' : 'en';
    i18n.changeLanguage(language);
    if (language === 'zh') moment.locale('zh-cn');
    if (language === 'en') moment.locale('en');
    localStorage.setItem(STORAGE_LANG_KEY, language);
  }, [i18n]);
  const settings = useMemo(() => {
    const items: SettingItem[] = [
      {
        key: 'language',
        name: t('language'),
        icon: <GlobalOutlined />,
        items: [
          {
            key: 'en',
            label: (
              <div className='py-1 flex justify-between gap-8 '>
                <span className='flex gap-2'>
                  <Image src='/icons/english.png' alt='english' width={21} height={21}></Image>
                  <span>English</span>
                </span>
                <span
                  className={cls({
                    block: i18n.language === 'en',
                    hidden: i18n.language !== 'en',
                  })}
                >
                  ✓
                </span>
              </div>
            ),
          },
          {
            key: 'zh',
            label: (
              <div className='py-1 flex justify-between gap-8 '>
                <span className='flex gap-2'>
                  <Image src='/icons/zh.png' alt='english' width={21} height={21}></Image>
                  <span>简体中文</span>
                </span>
                <span
                  className={cls({
                    block: i18n.language === 'zh',
                    hidden: i18n.language !== 'zh',
                  })}
                >
                  ✓
                </span>
              </div>
            ),
          },
        ],
        onSelect: ({ key }: { key: string }) => {
          if (i18n.language === key) return;
          i18n.changeLanguage(key);
          if (key === 'zh') moment.locale('zh-cn');
          if (key === 'en') moment.locale('en');
          localStorage.setItem(STORAGE_LANG_KEY, key);
        },
        onClick: handleChangeLang,
        defaultSelectedKeys: [i18n.language],
      },
      {
        key: 'theme',
        name: mode === 'light' ? t('dark_mode') : t('light_mode'),
        icon: mode === 'light' ? <MoonOutlined /> : <SunOutlined />,
        onClick: handleToggleTheme,
        noDropdownItem: true,
      },
      {
        key: 'fold',
        name: t(isMenuExpand ? 'Close_Sidebar' : 'Show_Sidebar'),
        icon: isMenuExpand ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />,
        onClick: handleToggleMenu,
        noDropdownItem: true,
      },
    ];
    return items;
  }, [t, mode, handleToggleTheme, i18n, handleChangeLang, isMenuExpand, handleToggleMenu, setMode]);

  // 扁平分区导航(Linear 式):主导航 / 资源与能力 / 系统,无折叠组
  const navIcon = (el: ReactNode) => (
    <span className='w-5 h-5 flex items-center justify-center text-[15px] flex-shrink-0'>{el}</span>
  );

  const navSections = useMemo(() => {
    // ── 核心入口:场景空间 ──
    const mainItems: RouteItem[] = [
      {
        key: 'workspaces',
        name: t('workspaces'),
        isActive: pathname.startsWith('/workspaces'),
        icon: navIcon(<TeamOutlined />),
        path: '/workspaces',
      },
    ];

    // 中文模式下菜单名显示为 中文名(英文名)
    const isZh = i18n.language === 'zh';
    const menuName = (zhName: string, enName: string) =>
      isZh ? `${zhName}(${enName})` : enName;

    // ── 能力:专家(Agent) / 技能(Skill) / 链接(MCP) / 定时任务 / 任务引擎 / 消息渠道 ──
    const capabilityItems: RouteItem[] = [
      ...(hasResourceRead('agent') ? [{
        key: 'agents',
        name: menuName('专家', 'Agent'),
        isActive: pathname.startsWith('/application'),
        icon: navIcon(<RobotOutlined />),
        path: '/application/explore',
      }] : []),
      ...(hasResourceRead('tool') ? [{
        key: 'agent_skills',
        name: menuName('技能', 'Skill'),
        isActive: pathname.startsWith('/agent-skills'),
        icon: navIcon(<ExperimentOutlined />),
        path: '/agent-skills',
      }] : []),
      ...(hasResourceRead('tool') ? [{
        key: 'MCP',
        name: menuName('链接', 'MCP'),
        isActive: pathname.startsWith('/mcp'),
        icon: navIcon(<ApiOutlined />),
        path: '/mcp',
      }] : []),
      ...(hasResourceRead('cron') || hasPermission('system', 'admin') ? [{
        key: 'cron',
        name: t('cron_page_title'),
        isActive: pathname.startsWith('/cron'),
        icon: navIcon(<ClockCircleOutlined />),
        path: '/cron',
      }] : []),
      ...(hasResourceRead('tool') ? [{
        key: 'jobs',
        name: '任务引擎',
        isActive: pathname.startsWith('/jobs'),
        icon: navIcon(<ThunderboltOutlined />),
        path: '/jobs',
      }] : []),
      ...(hasResourceRead('channel') || hasPermission('system', 'admin') ? [{
        key: 'channel',
        name: t('channel_page_title'),
        isActive: pathname.startsWith('/channel'),
        icon: navIcon(<MessageOutlined />),
        path: '/channel',
      }] : []),
    ];

    // ── 资产:知识库 / 语义资产 / 数据库 / 模型管理 ──
    const assetItems: RouteItem[] = [
      ...(hasResourceRead('knowledge') ? [{
        key: 'knowledge',
        name: t('knowledge_base'),
        isActive: pathname.startsWith('/knowledge-vault'),
        icon: navIcon(<BookOutlined />),
        path: '/knowledge-vault',
      }] : []),
      ...(hasResourceRead('ecp') ? [{
        key: 'ecp',
        name: t('ecp_page_title'),
        isActive: pathname.startsWith('/ecp'),
        icon: navIcon(<DeploymentUnitOutlined />),
        path: '/ecp',
      }] : []),
      ...(hasResourceRead('database') || hasResourceRead('tool') ? [{
        key: 'database',
        name: t('Database'),
        isActive: pathname.startsWith('/database'),
        icon: navIcon(<DatabaseOutlined />),
        path: '/database',
      }] : []),
      ...(hasResourceRead('model') ? [{
        key: 'models',
        name: t('model_manage'),
        isActive: pathname.startsWith('/models'),
        icon: navIcon(<Icon component={ModelSvg} />),
        path: '/models',
      }] : []),
    ];

    // ── 设置:监控 / 用量 / 系统配置 / 权限 / 审计日志 / GUI ──
    const settingItems: RouteItem[] = [
      ...(hasPermission('system', 'admin') ? [{
        key: 'monitoring',
        name: t('monitoring_page_title'),
        isActive: pathname.startsWith('/monitoring'),
        icon: navIcon(<DashboardOutlined />),
        path: '/monitoring',
      }] : []),
      ...(hasPermission('system', 'admin') ? [{
        key: 'usage',
        name: t('usage_page_title'),
        isActive: pathname.startsWith('/usage'),
        icon: navIcon(<BarChartOutlined />),
        path: '/usage',
      }] : []),
      ...(hasPermission('system', 'admin') ? [{
        key: 'system_config',
        name: t('system_config'),
        isActive: pathname.startsWith('/settings/config'),
        icon: navIcon(<SettingOutlined />),
        path: '/settings/config',
      }] : []),
      ...(hasPermission('system', 'admin') ? [{
        key: 'permissions',
        name: t('permissions_title'),
        isActive: pathname.startsWith('/settings/permissions'),
        icon: navIcon(<SafetyOutlined />),
        path: '/settings/permissions',
      }] : []),
      ...(hasPermission('system', 'admin') ? [{
        key: 'audit_logs',
        name: t('audit_logs_title'),
        isActive: pathname.startsWith('/audit-logs'),
        icon: navIcon(<FileTextOutlined />),
        path: '/audit-logs',
      }] : []),
      ...(hasPermission('system', 'admin') ? [{
        key: 'vis_merge_test',
        name: 'GUI',
        isActive: pathname.startsWith('/vis-merge-test'),
        icon: navIcon(<DesktopOutlined />),
        path: '/vis-merge-test',
      }] : []),
    ];

    return [
      { key: 'main', label: '', icon: null, items: mainItems, defaultOpen: true, flat: true },
      { key: 'capability', label: t('capability'), icon: navIcon(<ThunderboltOutlined />), items: capabilityItems, defaultOpen: false },
      { key: 'assets', label: t('assets'), icon: navIcon(<DatabaseOutlined />), items: assetItems, defaultOpen: false },
      { key: 'settings', label: t('settings_group'), icon: navIcon(<SettingOutlined />), items: settingItems, defaultOpen: false },
    ].filter(s => s.items.length > 0);
  }, [t, i18n.language, pathname, hasResourceRead, hasPermission]);

  useEffect(() => {
    const language = i18n.language;
    if (language === 'zh') moment.locale('zh-cn');
    if (language === 'en') moment.locale('en');
  }, []);

  useEffect(() => {
    setLogo(mode === 'dark' ? '/logo_s_latest.png' : '/logo_zh_latest.png');
  }, [mode]);

  // Agent 对话页(/chat)与场景空间(/workspaces)默认折叠主菜单,把横向空间留给对话区
  // 与工作台三栏;仅在路径变化时折叠,用户在页内手动展开不干预
  useEffect(() => {
    if (pathname.startsWith('/chat') || pathname.startsWith('/workspaces')) setIsMenuExpand(false);
  }, [pathname, setIsMenuExpand]);

  // if (pathname === '/') return null;

  if (!isMenuExpand) {
    return (
      <div className='flex flex-col justify-between items-center pt-3 h-screen w-[64px] bg-[var(--bg-elev)] border-r border-[var(--line-soft)] animate-fade animate-duration-300'>
        <div className='flex flex-col items-center'>
          <Link
            href='/'
            className='flex justify-center items-center w-11 h-11 mb-2 mt-0.5 rounded-[14px] bg-white dark:bg-[#232734] border border-[var(--line-soft)] shadow-[0_1px_3px_rgba(16,24,40,0.08)] hover:shadow-[0_4px_12px_rgba(16,24,40,0.12)] transition-shadow'
          >
            <Image src='/LOGO_SMALL.png' alt='Gyra' width={24} height={24} className='object-contain' />
          </Link>
          <div className='flex flex-col gap-1.5 items-center px-2'>
            {navSections.map(section => {
              // 一级单项(智能体空间/场景空间/历史记录):图标链接或点击项
              if ((section as any).flat) {
                return section.items.map(item => (
                  <Tooltip key={item.key} title={item.name} placement='right'>
                    {item.path ? (
                      <Link
                        className={cls(
                          'h-10 w-10 flex items-center justify-center rounded-xl transition-colors text-[#8a92a6] hover:bg-[#f2f4f8] hover:text-[#3b4154] dark:hover:bg-gray-800',
                          item.isActive && 'bg-[#e9eaee] text-[#3b4154]'
                        )}
                        href={item.path}
                      >
                        {item.icon}
                      </Link>
                    ) : (
                      <div
                        className={cls(
                          'h-10 w-10 flex items-center justify-center rounded-xl cursor-pointer transition-colors text-[#8a92a6] hover:bg-[#f2f4f8] hover:text-[#3b4154] dark:hover:bg-gray-800',
                          item.isActive && 'bg-[#e9eaee] text-[#3b4154]'
                        )}
                        onClick={item.onClick}
                      >
                        {item.icon}
                      </div>
                    )}
                  </Tooltip>
                ));
              }
              // 分组: hover 显示子菜单(带图标),点击展开侧边栏
              const anyActive = section.items.some(i => i.isActive);
              return (
                <Popover
                  key={section.key}
                  placement='right'
                  trigger='hover'
                  styles={{ body: { padding: 4 } }}
                  content={
                    <div className='flex flex-col gap-0.5 min-w-[168px]'>
                      <div className='px-2.5 py-1.5 text-xs font-medium text-gray-400 dark:text-gray-500'>
                        {section.label}
                      </div>
                      {section.items.map(item => (
                        <Link
                          key={item.key}
                          href={item.path ?? '/'}
                          className={cls(
                            'flex items-center h-8 px-2.5 rounded-md transition-colors text-[13px]',
                            item.isActive
                              ? 'bg-[#f2f4f8] dark:bg-gray-700 text-[#14161c] dark:text-white font-medium'
                              : 'text-[#3b4154] dark:text-gray-300 hover:bg-[#f2f4f8] dark:hover:bg-gray-800'
                          )}
                        >
                          <span className='mr-2.5 flex items-center justify-center flex-shrink-0 text-[#5d6577] dark:text-gray-400'>
                            {item.icon}
                          </span>
                          <span className='truncate'>{item.name}</span>
                        </Link>
                      ))}
                    </div>
                  }
                >
                  <div
                    className={cls(
                      'h-10 w-10 flex items-center justify-center rounded-xl cursor-pointer transition-colors text-[#8a92a6] hover:bg-[#f2f4f8] hover:text-[#3b4154] dark:hover:bg-gray-800',
                      anyActive && 'bg-[#e9eaee] text-[#3b4154]'
                    )}
                    onClick={() => {
                      setClosedSections(prev => ({ ...prev, [section.key]: false }));
                      setIsMenuExpand(true);
                    }}
                  >
                    {(section as any).icon}
                  </div>
                </Popover>
              );
            })}
          </div>
        </div>
        <div className='py-4 flex flex-col items-center gap-1.5'>
          <UserBar onlyAvatar />
          {settings
            .filter(item => item.noDropdownItem)
            .map(item => (
              <Tooltip key={item.key} title={item.name} placement='right'>
                <div className='w-10 h-10 flex items-center justify-center hover:bg-[#f2f4f8] dark:hover:bg-gray-800 rounded-xl cursor-pointer transition-colors' onClick={item.onClick}>
                  {item.icon}
                </div>
              </Tooltip>
            ))}
        </div>
        {/* 历史记录浮层档案面板(折叠态锚定 64px 图标栏右侧) */}
      </div>
    );
  }

  return (
    <div
      className={cls(
        'flex flex-col justify-between flex-1 pt-3 overflow-hidden h-screen',
        'bg-[var(--bg-elev)] border-r border-[var(--line-soft)]',
        'animate-fade animate-duration-300 max-w-[260px] w-[260px]',
      )}
    >
      <div className='flex flex-col w-full px-4 shrink-0'>
        {/* LOGO */}
        <Link href='/' className='flex flex-row justify-between items-center mb-4 pl-1'>
          <Image src={isMenuExpand ? logo : '/LOGO_SMALL.png'} alt='Gyra' width={120} height={30} className="object-contain" />
        </Link>

        </div>

      <div className="flex-1 min-h-0 flex flex-col px-4">
        <div className='flex-1 min-h-0 overflow-y-auto -mx-2 px-2 custom-scrollbar pr-1'>
        {/* Navigation Menu — 一级分组:Agent / 场景空间 / 资源 / 设置 */}
        <nav className='flex flex-col w-full mb-4'>
          {navSections.map((section) => {
            const linkCls = (active?: boolean) => cls(
              'flex items-center w-full h-8 cursor-pointer px-2.5 rounded-lg transition-all duration-150',
              active
                ? 'bg-[#e9eaee] dark:bg-gray-800 text-[#14161c] dark:text-white font-medium'
                : 'text-[#3b4154] dark:text-gray-400 hover:bg-[#efeff1] dark:hover:bg-gray-800'
            );
            const iconCls = (active?: boolean) => cls(
              'mr-2.5 flex items-center justify-center flex-shrink-0',
              active ? 'text-[#3b4154]' : 'text-[#5d6577]'
            );

            // 场景空间等一级单项:导航链接或点击项(如历史记录)
            if ((section as any).flat) {
              return section.items.map(item => item.path ? (
                <Link href={item.path} className={cls(linkCls(item.isActive), 'h-9 px-3 font-medium')} key={item.key}>
                  <span className={iconCls(item.isActive)}>{item.icon}</span>
                  <span className='text-[13px] truncate'>{item.name}</span>
                </Link>
              ) : (
                <div
                  className={cls(linkCls(item.isActive), 'h-9 px-3 font-medium')}
                  key={item.key}
                  onClick={item.onClick}
                >
                  <span className={iconCls(item.isActive)}>{item.icon}</span>
                  <span className='text-[13px] truncate'>{item.name}</span>
                </div>
              ));
            }

            const anyActive = section.items.some(i => i.isActive);
            const open = closedSections[section.key] !== undefined
              ? !closedSections[section.key]
              : (section as any).defaultOpen || anyActive;

            return (
              <div key={section.key} className='mb-1'>
                {/* 分组头:一级分类,可折叠 */}
                <div
                  className='flex items-center w-full h-9 px-3 rounded-lg cursor-pointer select-none hover:bg-[#efeff1] dark:hover:bg-gray-800 transition-colors group/nav'
                  onClick={() => setClosedSections(prev => ({ ...prev, [section.key]: open }))}
                >
                  <span className={cls('mr-2.5 flex items-center justify-center flex-shrink-0', anyActive ? 'text-[#3b4154]' : 'text-[#5d6577]')}>
                    {(section as any).icon}
                  </span>
                  <span className='text-[13px] truncate flex-1 font-medium text-[#14161c] dark:text-gray-300'>
                    {section.label}
                  </span>
                  <RightOutlined className={cls(
                    'text-[9px] text-[#b4bac8] group-hover/nav:text-[#8a92a6] transition-transform duration-200',
                    open && 'rotate-90'
                  )} />
                </div>
                {/* 子项:带图标与引导线缩进 */}
                {open && (
                  <div className='flex flex-col gap-0.5 ml-[21px] pl-2.5 mt-0.5 mb-1 border-l border-[#eff1f6] dark:border-gray-800'>
                    {section.items.map(item => (
                      <Link href={item.path ?? '/'} className={cls(linkCls(item.isActive), 'h-9 px-3')} key={item.key}>
                        <span className={iconCls(item.isActive)}>{item.icon}</span>
                        <span className='text-[13px] truncate'>{item.name}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
        </div>
      </div>

      {/* User & Settings */}
      <div className='px-4 py-4 mt-2 border-t border-[var(--line-soft)] dark:border-gray-800 bg-[var(--bg-elev)] flex items-center justify-between gap-2'>
        <div className='flex-1 min-w-0 overflow-hidden'>
           <UserBar />
        </div>
        <div className='flex items-center gap-1 shrink-0'>
          {settings.map(item => (
            <Tooltip key={item.key} title={item.name} placement='top'>
              <div 
                className={cls(
                  'w-8 h-8 flex items-center justify-center rounded-lg cursor-pointer transition-colors text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800', 
                  { 'text-gray-300 cursor-not-allowed': item.disable }
                )} 
                onClick={item.onClick}
              >
                {item.icon}
              </div>
            </Tooltip>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SideBar;
