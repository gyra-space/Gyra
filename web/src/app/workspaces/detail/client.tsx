'use client';

import {
  apiInterceptors, getWorkspaceInfo, listTasks, listInterventions,
} from '@/client/api';
import { Button, Spin } from 'antd';
import { useRequest } from 'ahooks';
import { useSearchParams, usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getUserId } from '@/utils';
import {
  ScheduleOutlined,
  SettingOutlined,
  BookOutlined,
  AppstoreOutlined,
  HomeOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { SceneWorkspaceShell } from './scene-workspace-shell';
import { CallDetailProvider } from '@/components/chat/call-detail/CallDetailProvider';
import { useWorkspaceViewMode, type WorkspaceViewMode } from './use-view-mode';
import { ChatContext } from '@/contexts';
import { useSpaceRole } from '@/hooks/use-space-role';
import '../workspaces.css';

export default function WorkspaceDetailPage() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const workspaceCode = searchParams?.get('id') || '';
  // 深链打开指定会话(从全局历史会话等入口):?conv_uid=xxx&task_id=xxx
  const urlConvUid = searchParams?.get('conv_uid') || '';
  const urlTaskIdParam = searchParams?.get('task_id');
  const urlTaskId = urlTaskIdParam != null && urlTaskIdParam !== '' ? Number(urlTaskIdParam) : NaN;
  // 深链初始状态:task_id 与 conv_uid 各自独立生效 ——
  // 有 task_id -> 进任务对话(即便 conv_uid 尚未落到 URL,也能靠 getTaskInfo 还原);
  // 有 conv_uid 无 task_id -> workspace 级会话(回工作台);两者都无 -> 非深链,进入无会话欢迎态。
  const initialPendingTaskId = !Number.isNaN(urlTaskId)
    ? urlTaskId
    : urlConvUid
      ? null
      : undefined;
  // 深链打开态:URL 带 conv_uid/task_id 时说明用户已打开具体内容,
  // 简洁模式应直达会话运行态而非欢迎页(刷新恢复的关键)。
  const hasDeepLink = !!urlConvUid || !Number.isNaN(urlTaskId);
  // 「新任务」态标记:点新任务时写入 URL(new_task=1),刷新后据此跳过会话装载、
  // 直接保持欢迎态。打开任一真实会话时(onConvChanged)移除该标记。
  const urlNewTask = searchParams?.get('new_task') === '1';
  // 当前子页面导航激活态(分段控件高亮)
  const navActive = (segment: string) =>
    pathname?.includes(`/workspaces/detail/${segment}`) ? ' ws-console-nav-link--active' : '';
  // 资产页内部 tab:数据/能力/交付统一在「资产」导航下切换
  const isAssetsPage = !!pathname?.includes('/workspaces/detail/assets');
  const { t } = useTranslation();
  const [conversationId, setConvUid] = useState<string>('');
  const [convLoadError, setConvLoadError] = useState<string | null>(null);
  const [convLoadKey, setConvLoadKey] = useState(0);
  const [listsRefreshKey, setListsRefreshKey] = useState(0);
  // 从会话列表选中会话时携带的 task_id:number=进 task 对话,null=workspace 级会话,
  // undefined=非列表触发(初始/任务栏进入)。shell 据此恢复 activeTaskId。
  const [pendingTaskId, setPendingTaskId] = useState<number | null | undefined>(initialPendingTaskId);
  // 主动「新任务」态:点新任务置 true,刷新时由 URL new_task=1 恢复;打开任一真实会话后复位。
  // 用于抑制会话加载时恢复后端「当前会话」,否则新任务会立刻被旧会话覆盖。
  const [manualNew, setManualNew] = useState<boolean>(urlNewTask);
  // 简洁模式抽屉:待办收件箱(header 待办角标与左栏「待办收件箱」共用同一状态)
  const [simpleDrawer, setSimpleDrawer] = useState<'inbox' | 'overview' | null>(null);

  /**
   * 把当前打开的会话/任务写回地址栏(router.replace,不堆积浏览历史),
   * 使刷新、分享、新标签打开都能回到同一现场,而不是回到新建页。
   * 只改 URL query,不改任何 React state —— 避免与 pendingTaskId 恢复链路互相触发。
   * patch 里未出现的字段保持原样;显式传 null 表示从 URL 移除该参数。
   */
  const syncUrl = useCallback(
    (patch: { convUid?: string | null; taskId?: number | null; newTask?: boolean }) => {
      if (!pathname) return;
      const params = new URLSearchParams(searchParams?.toString() || '');
      let changed = false;
      if (patch.convUid !== undefined) {
        const next = patch.convUid || '';
        if ((params.get('conv_uid') || '') !== next) {
          if (next) params.set('conv_uid', next);
          else params.delete('conv_uid');
          changed = true;
        }
      }
      if (patch.taskId !== undefined) {
        const next =
          patch.taskId != null && Number.isFinite(patch.taskId) ? String(patch.taskId) : '';
        if ((params.get('task_id') || '') !== next) {
          if (next) params.set('task_id', next);
          else params.delete('task_id');
          changed = true;
        }
      }
      if (patch.newTask !== undefined) {
        const next = patch.newTask ? '1' : '';
        if ((params.get('new_task') || '') !== next) {
          if (next) params.set('new_task', next);
          else params.delete('new_task');
          changed = true;
        }
      }
      if (!changed) return;
      const qs = params.toString();
      // eslint-disable-next-line no-console
      console.log('[DEBUG syncUrl]', JSON.stringify(patch), '->', qs ? `${pathname}?${qs}` : pathname);
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, searchParams, router],
  );

  // 简洁模式「新任务」:清空当前会话并进入无会话欢迎态。
  // 同时给 URL 打 new_task=1 标记,刷新后据此跳过会话装载,保持欢迎态。
  const handleNewTask = useCallback(() => {
    // eslint-disable-next-line no-console
    console.log('[DEBUG handleNewTask] 触发');
    setManualNew(true);
    setConvUid('');
    setPendingTaskId(undefined);
    syncUrl({ convUid: null, taskId: null, newTask: true });
  }, [syncUrl]);

  // 场景空间三列布局需要宽度,进入时自动折叠左侧菜单
  const { setIsMenuExpand } = useContext(ChatContext);
  useEffect(() => {
    setIsMenuExpand(false);
  }, [setIsMenuExpand]);

  const { data: ws, loading: wsLoading } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  const workspaceId = ws?.id;
  const appCode = ws?.default_agent_app_code || 'main';

  // 权限门控:设置 tab 仅空间管理(space.workspace.manage,owner)可见,其余 tab 全角色可见
  const { role, can } = useSpaceRole(workspaceId);
  // 视图模式:按角色决定默认(owner 管理成员→运维,普通成员→简洁);
  // 用户手动选择(localStorage)与 URL ?mode= 优先于角色默认
  const defaultViewMode: WorkspaceViewMode = role === 'owner' ? 'ops' : 'simple';
  const { mode: viewMode, setMode: setViewMode } = useWorkspaceViewMode(workspaceId, defaultViewMode);

  // 会话装载:仅两类入口会打开具体会话 ——
  // 深链(URL 带 conv_uid/task_id)与列表/新建动作(onConvChanged 主动 set)。
  // 非深链直接进入空间(新 tab、地址栏裸访问)一律停在无会话欢迎态:
  // 后端「当前会话」是跨 tab 的全局状态,自动恢复会让多个 tab 互相抢占、
  // 无法并行开多个对话;首个会话由欢迎页发送时懒创建(shell ensureConversation),
  // 「继续上次会话」走欢迎页/左侧列表入口。
  useRequest(
    async () => {
      setConvLoadError(null);
      // 深链:URL 已携带 conv_uid 时直接打开该会话
      if (urlConvUid) {
        setConvUid(urlConvUid);
        return;
      }
      setConvUid('');
    },
    {
      ready: !!workspaceId && !manualNew,
      // urlConvUid 变化(同一空间内通过全局历史切换会话)也要重载;manualNew 变化用于新任务复位
      refreshDeps: [convLoadKey, workspaceId, urlConvUid, manualNew],
      onError: (e: any) => {
        setConvLoadError(e?.message || '会话加载失败');
      },
    }
  );

  // 任务列表:简单模式仅拉取「自己提交的 + 空间公共(订阅触发)」任务,
  // 别人的对话任务不可见;运维模式保持全量。切换模式时重新拉取。
  const { data: tasks } = useRequest(async () => {
    if (!workspaceId) return [];
    const [err, res] = await apiInterceptors(listTasks({
      workspace_id: workspaceId,
      limit: 200,
      ...(viewMode === 'simple'
        ? { own_and_public_only: true, user_id: Number(getUserId()) || undefined }
        : {}),
    }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, listsRefreshKey, viewMode] });

  const { data: interventions } = useRequest(async () => {
    if (!workspaceId) return [];
    const [err, res] = await apiInterceptors(listInterventions({
      workspace_id: workspaceId, status: 'requested', limit: 20,
    }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId, listsRefreshKey] });

  const retryLoadConv = useCallback(() => {
    setConvLoadKey((k) => k + 1);
  }, []);

  const handleRefreshLists = useCallback(() => {
    setListsRefreshKey((k) => k + 1);
  }, []);

  if (!searchParams || wsLoading) {
    return (
      <div className="ws-page">
        <div className="ws-page-bg" />
        <div className="ws-page-content ws-page-content--fluid" style={{ display: 'flex', justifyContent: 'center', padding: '120px 24px' }}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  if (!ws) {
    return (
      <div className="ws-page">
        <div className="ws-page-bg" />
        <div className="ws-page-content ws-page-content--fluid">
          <div className="ws-empty">
            <div className="ws-empty-icon"><AppstoreOutlined /></div>
            <p className="ws-empty-title">Workspace not found</p>
            <p className="ws-empty-desc">This workspace may have been archived or you lack access.</p>
            <Link href="/workspaces"><Button>Back to workspaces</Button></Link>
          </div>
        </div>
      </div>
    );
  }

  if (!workspaceId) {
    return null;
  }

  const scenario = ws.scenario_type || ws.type || 'scenario';

  return (
    <CallDetailProvider conversationId={conversationId}>
      <div className="ws-page" style={{ height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <div className="ws-page-bg" />
      <div
        className="ws-page-content ws-page-content--fluid"
        style={{ padding: '0', height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', gap: 0, boxSizing: 'border-box' }}
      >
        <div className="ws-console-header">
          <div className="ws-console-header-left">
            <div className="ws-console-avatar"><AppstoreOutlined /></div>
            <div style={{ minWidth: 0 }}>
              <h2 className="ws-console-title">{ws.name}</h2>
              <div className="ws-console-sub">
                {ws.workspace_code} · {scenario}
              </div>
            </div>
          </div>
          <nav className="ws-console-nav" aria-label="Workspace navigation">
            <Link href={`/workspaces/detail?id=${workspaceCode}`} className={`ws-console-nav-link${pathname === '/workspaces/detail' ? ' ws-console-nav-link--active' : ''}`}>
              <HomeOutlined />{t('workspaces.lobby') || '工作台'}
            </Link>
            <Link href={`/workspaces/detail/tasks?id=${workspaceCode}`} className={`ws-console-nav-link${navActive('tasks')}`}>
              <ScheduleOutlined />{t('workspaces.tasks') || '任务'}
            </Link>
            <Link href={`/workspaces/detail/playbooks?id=${workspaceCode}`} className={`ws-console-nav-link${navActive('playbooks')}`}>
              <BookOutlined />{t('workspaces.playbooks') || '剧本'}
            </Link>
            <Link href={`/workspaces/detail/assets?id=${workspaceCode}&tab=semantic`} className={`ws-console-nav-link${isAssetsPage ? ' ws-console-nav-link--active' : ''}`}>
              <DatabaseOutlined />{t('workspaces.assets') || '资产'}
            </Link>
            {can('space.workspace.manage') && (
              <Link href={`/workspaces/detail/settings?id=${workspaceCode}`} className={`ws-console-nav-link${navActive('settings')}`}>
                <SettingOutlined />{t('workspaces.settings') || '设置'}
              </Link>
            )}
          </nav>
          {/* 视图模式切换:简洁 / 运维(常驻 header 右侧) */}
          <div className="ws-console-viewmode" role="tablist" aria-label="视图模式">
            <span
              role="tab"
              aria-selected={viewMode === 'simple'}
              className={`ws-console-viewmode__tab${viewMode === 'simple' ? ' ws-console-viewmode__tab--on' : ''}`}
              onClick={() => setViewMode('simple')}
            >
              简洁
            </span>
            <span
              role="tab"
              aria-selected={viewMode === 'ops'}
              className={`ws-console-viewmode__tab${viewMode === 'ops' ? ' ws-console-viewmode__tab--on' : ''}`}
              onClick={() => setViewMode('ops')}
            >
              运维
            </span>
          </div>
        </div>

        <SceneWorkspaceShell
          workspace={ws}
          tasks={tasks || []}
          interventions={interventions || []}
          workspaceConvUid={conversationId}
          appCode={appCode}
          onRefreshLists={handleRefreshLists}
          listsRefreshKey={listsRefreshKey}
          onConvChanged={(uid: string, tid?: number | null) => {
            // 打开任一真实会话:退出「新任务」态(复位 manualNew、移除 URL new_task 标记),
            // 之后刷新恢复的是该会话而非新任务首页。
            setManualNew(false);
            setConvUid(uid);
            setPendingTaskId(tid ?? null);
            // tid 为 undefined 表示非列表触发(如新建/清理上下文),只换会话不动 task_id
            syncUrl({ convUid: uid, taskId: tid === undefined ? undefined : tid, newTask: false });
          }}
          // 简洁模式「新任务」:清空会话进欢迎态,并给 URL 打 new_task=1 标记
          onNewTask={handleNewTask}
          // 仅回写地址栏、不触碰 state:进入/退出任务对话、任务 conv 解析完成都走这里
          onUrlSync={syncUrl}
          initialShowWelcome={!hasDeepLink}
          manualNew={manualNew}
          convLoadError={convLoadError}
          retryLoadConv={retryLoadConv}
          pendingTaskId={pendingTaskId}
          viewMode={viewMode}
          simpleDrawer={simpleDrawer}
          onSimpleDrawerChange={setSimpleDrawer}
        />
      </div>
      </div>
    </CallDetailProvider>
  );
}
