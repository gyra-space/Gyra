'use client';

import { useRequest } from 'ahooks';
import { useRouter } from 'next/navigation';
import { AppstoreOutlined, TeamOutlined, ThunderboltOutlined, DesktopOutlined } from '@ant-design/icons';
import { apiInterceptors, listWorkspaces } from '@/client/api';
import { getUserId } from '@/utils/storage';
import { PullToRefresh } from './pull-to-refresh';

/** 移动端首页:我的场景空间(仅使用视角) */
export default function MobileHome() {
  const router = useRouter();

  const { data: list, loading, refresh } = useRequest(async () => {
    const [err, res] = await apiInterceptors(
      listWorkspaces({ user_id: Number(getUserId()) || 0 }),
    );
    if (err) return [];
    return (res || []).filter((w: any) => !w.is_archived);
  });

  const activeCount = (list || []).length;

  return (
    <>
      <header className="ms-header">
        <div className="ms-header__title-wrap">
          <div className="ms-eyebrow">GYRA · MOBILE</div>
        </div>
        <button
          type="button"
          className="ms-header__back"
          title="在桌面端打开"
          aria-label="在桌面端打开"
          onClick={() => router.push('/workspaces')}
        >
          <DesktopOutlined />
        </button>
      </header>

      <PullToRefresh onRefresh={refresh} className="ms-body">
        <div style={{ marginBottom: 18 }}>
          <h1 className="ms-title">我的场景空间</h1>
          <p className="ms-subtitle" style={{ marginTop: 6 }}>
            {activeCount > 0 ? `你有 ${activeCount} 个空间 · 随时发任务、看执行、做审批` : '创建的空间会出现在这里'}
          </p>
        </div>

        {loading ? (
          <div className="ms-empty">
            <div className="ms-empty__title">加载中…</div>
          </div>
        ) : !list || list.length === 0 ? (
          <div className="ms-empty">
            <div className="ms-empty__icon">
              <AppstoreOutlined />
            </div>
            <div className="ms-empty__title">还没有场景空间</div>
            <p className="ms-empty__hint">在桌面端创建空间后，这里会展示你的全部空间，方便随时使用。</p>
          </div>
        ) : (
          <div className="ms-list">
            {list.map((ws: any) => {
              const scenario = ws.scenario_type || ws.type || 'scenario';
              return (
                <div
                  key={ws.id}
                  className="ms-card ms-card--tap ms-ws-card"
                  role="button"
                  tabIndex={0}
                  onClick={() => router.push(`/m/workspace?id=${encodeURIComponent(ws.workspace_code)}`)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      router.push(`/m/workspace?id=${encodeURIComponent(ws.workspace_code)}`);
                    }
                  }}
                >
                  <div className="ms-ws-card__top">
                    <span className="ms-ws-card__code">{ws.workspace_code}</span>
                    <span className="ms-chip">{scenario}</span>
                  </div>
                  <div className="ms-ws-card__name">{ws.name}</div>
                  {ws.description && <div className="ms-ws-card__desc">{ws.description}</div>}
                  <div className="ms-ws-card__foot">
                    <span className="ms-ws-card__stat">
                      <TeamOutlined /> {ws.member_count || 0} 成员
                    </span>
                    {ws.task_count != null && (
                      <span className="ms-ws-card__stat">
                        <ThunderboltOutlined /> {ws.task_count} 任务
                      </span>
                    )}
                    <span style={{ flex: 1 }} />
                    <DesktopOutlined style={{ color: 'var(--ms-text-3)' }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </PullToRefresh>
    </>
  );
}