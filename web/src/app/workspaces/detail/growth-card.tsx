'use client';

import { useMemo, useState } from 'react';
import { useRequest } from 'ahooks';
import { ApartmentOutlined, DownOutlined, RightOutlined } from '@ant-design/icons';
import { GET, apiInterceptors } from '@/client/api';
import { getEcpInbox, listEcpObjects } from '@/client/api/ecp';

export interface GrowthCardProps {
  workspaceId: number;
  workspaceCode?: string;
  /** 进入飞轮工作台(成长数据的全量看板) */
  onEnterFlywheel?: () => void;
  /** 以下数据由 Lobby 聚合端点一次性下发,省略时回退到内部拉取(兼容独立使用) */
  growth?: any;
  ecpConfirmedCount?: number;
  ecpPendingCount?: number;
}

interface GrowthData {
  assets_count: number;
  evolution_proposals_count: number;
  tasks_trend: Array<{ date: string; count: number }>;
  knowledge_graph_nodes: number;
}

const EMPTY: GrowthData = {
  assets_count: 0,
  evolution_proposals_count: 0,
  tasks_trend: [],
  knowledge_graph_nodes: 0,
};

/* 北极星圆环:渐变描边 + 圆角端点 + 中心渐变百分比 */
function NorthStarRing({ percent }: { percent: number }) {
  const SIZE = 84;
  const STROKE = 7;
  const r = (SIZE - STROKE) / 2;
  const c = 2 * Math.PI * r;
  const p = Math.min(100, Math.max(0, percent));
  return (
    <span className="ws-growth__ring" style={{ width: SIZE, height: SIZE }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <defs>
          <linearGradient id="ws-ns-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="55%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={r}
          fill="none"
          stroke="rgba(99, 102, 241, 0.12)"
          strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={r}
          fill="none"
          stroke="url(#ws-ns-grad)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - p / 100)}
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
          className="ws-growth__ring-arc"
        />
      </svg>
      <span className="ws-growth__ring-value">{p}%</span>
    </span>
  );
}

/* 任务趋势迷你 sparkline(近 30 天,渐变线 + 半透明面积) */
function TrendSpark({ trend }: { trend: Array<{ date: string; count: number }> }) {
  const W = 140;
  const H = 26;
  const PAD = 2;
  const { line, area } = useMemo(() => {
    if (!trend.length) return { line: '', area: '' };
    const max = Math.max(...trend.map((t) => t.count), 1);
    const step = trend.length > 1 ? (W - PAD * 2) / (trend.length - 1) : 0;
    const pts = trend.map(
      (t, i) =>
        `${(PAD + i * step).toFixed(1)},${(H - PAD - (t.count / max) * (H - PAD * 2)).toFixed(1)}`,
    );
    return {
      line: pts.join(' '),
      area: `${PAD},${H - PAD} ${pts.join(' ')} ${(PAD + (trend.length - 1) * step).toFixed(1)},${H - PAD}`,
    };
  }, [trend]);

  if (!line) return <span className="ws-growth__trend-empty">暂无任务动态</span>;
  return (
    <svg
      className="ws-growth__trend-spark"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <defs>
        <linearGradient id="ws-trend-line" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
        <linearGradient id="ws-trend-fill" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(99, 102, 241, 0.22)" />
          <stop offset="100%" stopColor="rgba(99, 102, 241, 0)" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#ws-trend-fill)" />
      <polyline
        points={line}
        fill="none"
        stroke="url(#ws-trend-line)"
        strokeWidth="1.6"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function GrowthCard({ workspaceId, workspaceCode, onEnterFlywheel, growth: growthProp, ecpConfirmedCount: ecpConfirmedProp, ecpPendingCount: ecpPendingProp }: GrowthCardProps) {
  // 成长卡可折叠:默认收敛为一行(只留标题 + 飞轮入口),展开才显示指标,避免装饰性内容抢占首屏
  const storageKey = `ws-growth-collapsed-${workspaceId}`;
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    return window.localStorage.getItem(storageKey) !== '0';
  });
  const toggleCollapse = () => {
    setCollapsed((c) => {
      const next = !c;
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(storageKey, next ? '1' : '0');
      }
      return next;
    });
  };

  const { data: fetchedGrowth } = useRequest(
    async () => {
      if (growthProp) return null;
      const res = await GET<null, GrowthData>(
        `/api/v1/serve_workspace_service/workspaces/${workspaceId}/growth`,
      );
      if (res.data?.success && res.data.data) {
        return res.data.data;
      }
      return EMPTY;
    },
    { refreshDeps: [workspaceId, growthProp] },
  );
  const growth = growthProp ?? fetchedGrowth ?? EMPTY;

  // ECP 成长:派生空间 ecp_<code> 的语义口径
  const ecpWsId = workspaceCode ? `ecp_${workspaceCode}` : null;
  const { data: ecpConfirmedFetched } = useRequest(
    async () => {
      if (ecpConfirmedProp != null || !ecpWsId) return 0;
      const [err, res] = await apiInterceptors(
        listEcpObjects({ status: 'confirmed', page_size: 1, workspace_id: ecpWsId! }),
      );
      return err ? 0 : res?.total_count ?? 0;
    },
    { ready: !!ecpWsId, refreshDeps: [ecpWsId, ecpConfirmedProp] },
  );
  // 待确认提案数(收件箱),与 confirmed 一起算北极星
  const { data: ecpPendingFetched } = useRequest(
    async () => {
      if (ecpPendingProp != null || !ecpWsId) return 0;
      const [err, res] = await apiInterceptors(
        getEcpInbox({ page_size: 1, workspace_id: ecpWsId! }),
      );
      return err ? 0 : res?.total_count ?? 0;
    },
    { ready: !!ecpWsId, refreshDeps: [ecpWsId, ecpPendingProp] },
  );

  const confirmed = ecpConfirmedProp ?? ecpConfirmedFetched ?? 0;
  const pending = ecpPendingProp ?? ecpPendingFetched ?? 0;
  // 北极星:资产固化率 = 已确认 / (已确认 + 待确认),衡量 ⚠️->✅ 的转化程度
  const total = confirmed + pending;
  const solidificationRate = total > 0 ? Math.round((confirmed / total) * 100) : 0;

  const totalTasks = (growth.tasks_trend || []).reduce((sum: number, t: { count: number }) => sum + t.count, 0);

  // 折叠态摘要:关键指标内联在一行,让用户不展开也能看到成长概况
  const summaryBits = [
    ...(ecpWsId ? [`固化率 ${solidificationRate}%`] : []),
    `成果 ${growth.assets_count}`,
    `近30天任务 ${totalTasks}`,
  ];

  const metrics = [
    { label: '已沉淀成果', value: growth.assets_count },
    { label: '专家演化建议', value: growth.evolution_proposals_count },
    { label: '知识图谱节点', value: growth.knowledge_graph_nodes },
    ...(ecpWsId ? [{ label: '语义口径', value: confirmed }] : []),
  ];

  return (
    <section className="ws-growth">
      <header className="ws-growth__head">
        <span
          className="ws-growth__toggle"
          role="button"
          tabIndex={0}
          aria-label={collapsed ? '展开成长概览' : '收起成长概览'}
          onClick={toggleCollapse}
          onKeyDown={(e) => { if (e.key === 'Enter') toggleCollapse(); }}
        >
          {collapsed ? <RightOutlined /> : <DownOutlined />}
        </span>
        <span
          className="ws-growth__title"
          role="button"
          tabIndex={0}
          onClick={toggleCollapse}
          onKeyDown={(e) => { if (e.key === 'Enter') toggleCollapse(); }}
        >
          本月空间成长
        </span>
        {collapsed && (
          <span
            className="ws-growth__summary"
            role="button"
            tabIndex={0}
            onClick={toggleCollapse}
            onKeyDown={(e) => { if (e.key === 'Enter') toggleCollapse(); }}
          >
            {summaryBits.join(' · ')}
          </span>
        )}
        <div
          className="ws-growth__entry"
          role="button"
          tabIndex={0}
          title="资产沉淀 · Agent 成长 · 自动演化 · 评测反馈"
          onClick={onEnterFlywheel}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onEnterFlywheel?.();
          }}
        >
          <span className="ws-growth__entry-orb">
            <ApartmentOutlined />
          </span>
          <span className="ws-growth__entry-title">飞轮工作台</span>
          <RightOutlined className="ws-growth__entry-arrow" />
        </div>
      </header>

      {!collapsed && (
        <div className="ws-growth__body">
          {ecpWsId && (
            <div className="ws-growth__ns">
              <NorthStarRing percent={solidificationRate} />
              <div className="ws-growth__ns-meta">
                <span className="ws-growth__ns-label">北极星 · 资产固化率</span>
                <span className="ws-growth__ns-foot">
                  {total > 0 ? `⚠️→✅ ${confirmed}/${total} 已固化` : '暂无语义提案'}
                </span>
              </div>
            </div>
          )}

          <div className="ws-growth__metrics">
            {metrics.map((m) => (
              <div key={m.label} className="ws-growth__metric">
                <span className="ws-growth__metric-value">{m.value}</span>
                <span className="ws-growth__metric-label">{m.label}</span>
              </div>
            ))}
          </div>

          <div className="ws-growth__trend">
            <span className="ws-growth__trend-label">任务趋势</span>
            <TrendSpark trend={growth.tasks_trend || []} />
            <span className="ws-growth__trend-value">
              <b>{totalTasks}</b> 次 · 近 30 天
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
