'use client';

import {
  apiInterceptors, getWorkspaceInfo, listTasks, listInterventions,
  createConversation, getCurrentConversation, setCurrentConversation,
  linkConversation,
} from '@/client/api';
import { Button, Spin } from 'antd';
import { useRequest } from 'ahooks';
import { useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useCallback, useContext, useEffect, useState } from 'react';
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
import { CallDetailProvider, useCallDetail } from '@/components/chat/call-detail/CallDetailProvider';
import { ConversationUsageChip } from '@/components/chat/ConversationUsageChip';
import { useWorkspaceViewMode, type WorkspaceViewMode } from './use-view-mode';
import { ChatContext } from '@/contexts';
import { useSpaceRole } from '@/hooks/use-space-role';
import '../workspaces.css';

export default function WorkspaceDetailPage() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const workspaceCode = searchParams?.get('id') || '';
  // 深链打开指定会话(从全局历史会话等入口):?conv_uid=xxx&task_id=xxx
  const urlConvUid = searchParams?.get('conv_uid') || '';
  const urlTaskIdParam = searchParams?.get('task_id');
  // 深链初始状态:带 conv_uid 时,有 task_id -> 进任务对话;无 -> workspace 级会话
  const initialPendingTaskId = urlConvUid
    ? urlTaskIdParam
      ? Number(urlTaskIdParam)
      : null
    : undefined;
  // 当前子页面导航激活态(分段控件高亮)
  const navActive = (segment: string) =>
    pathname?.includes(`/workspaces/detail/${segment}`) ? ' ws-console-nav-link--active' : '';
  // 资产页内部 tab:数据/能力/交付统一在「资产」导航下切换
  const isAssetsPage = !!pathname?.includes('/workspaces/detail/assets');
  const { t } = useTranslation();
  const [convUid, setConvUid] = useState<string>('');
  const [convLoadError, setConvLoadError] = useState<string | null>(null);
  const [convLoadKey, setConvLoadKey] = useState(0);
  const [listsRefreshKey, setListsRefreshKey] = useState(0);
  // 从会话列表选中会话时携带的 task_id:number=进 task 对话,null=workspace 级会话,
  // undefined=非列表触发(初始/任务栏进入)。shell 据此恢复 activeTaskId。
  const [pendingTaskId, setPendingTaskId] = useState<number | null | undefined>(initialPendingTaskId);
  // 简洁模式抽屉:待办收件箱(header 待办角标与左栏「待办收件箱」共用同一状态)
  const [simpleDrawer, setSimpleDrawer] = useState<'inbox' | 'overview' | null>(null);

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
  const { openCallDetail } = useCallDetail();

  // 视图模式:按角色决定默认(owner 管理成员→运维,普通成员→简洁);
  // 用户手动选择(localStorage)与 URL ?mode= 优先于角色默认
  const defaultViewMode: WorkspaceViewMode = role === 'owner' ? 'ops' : 'simple';
  const { mode: viewMode, setMode: setViewMode } = useWorkspaceViewMode(workspaceId, defaultViewMode);

  useRequest(
    async () => {
      setConvLoadError(null);
      // 深链:URL 已携带 conv_uid 时直接打开该会话,不再取/建当前会话
      if (urlConvUid) {
        setConvUid(urlConvUid);
        return;
      }
      const [, current] = await apiInterceptors(getCurrentConversation(workspaceId));
      if (current?.conv_uid) {
        setConvUid(current.conv_uid);
        return;
      }
      const [newErr, newConv] = await apiInterceptors(createConversation({}));
      if (newErr || !newConv?.conv_uid) {
        setConvLoadError(newErr?.message || '无法创建会话，请稍后重试');
        return;
      }
      const [linkErr] = await apiInterceptors(
        linkConversation({ workspace_id: workspaceId, conv_uid: newConv.conv_uid, user_id: Number(getUserId()) || undefined })
      );
      if (linkErr) {
        setConvLoadError(`会话关联空间失败：${linkErr.message || '未知错误'}`);
        return;
      }
      const [currErr] = await apiInterceptors(setCurrentConversation(workspaceId, newConv.conv_uid));
      if (currErr) {
        setConvLoadError(`设置当前会话失败：${currErr.message || '未知错误'}`);
        return;
      }
      setConvUid(newConv.conv_uid);
    },
    {
      ready: !!workspaceId,
      // urlConvUid 变化(同一空间内通过全局历史切换会话)也要重载
      refreshDeps: [convLoadKey, workspaceId, urlConvUid],
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
    <CallDetailProvider convId={convUid}>
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
              <ConversationUsageChip convId={convUid} onClick={() => openCallDetail()} />
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
          workspaceConvUid={convUid}
          appCode={appCode}
          onRefreshLists={handleRefreshLists}
          listsRefreshKey={listsRefreshKey}
          onConvChanged={(uid: string, tid?: number | null) => {
            setConvUid(uid);
            setPendingTaskId(tid ?? null);
          }}
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
