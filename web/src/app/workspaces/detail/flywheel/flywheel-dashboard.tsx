'use client';

/**
 * 飞轮仪表盘 —— 数据飞轮闭环可视化 + 关键指标。
 *
 * 视觉:五环沿圆弧流动(虚线行进动画),节点软色徽章,
 * 中心品牌脉冲;右侧两张指标卡复用 ws 卡片语言。
 */
import { useMemo } from 'react';
import { Tooltip } from 'antd';
import {
  ApartmentOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  RightOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import {
  listAgentMaturity,
  listEvolutionProposals,
} from '@/client/api/flywheel';

/** 五环配置(key 对应 flywheel.css 的 --fw-* 语义色) */
const FLYWHEEL_NODES = [
  { key: 'asset', label: '资产', varName: '--fw-asset', angle: 90 },
  { key: 'agent', label: 'Agent', varName: '--fw-agent', angle: 18 },
  { key: 'trace', label: 'Trace', varName: '--fw-trace', angle: -54 },
  { key: 'evolution', label: '演化', varName: '--fw-evolution', angle: -126 },
  { key: 'evaluation', label: '评测', varName: '--fw-evaluation', angle: -198 },
] as const;

const LEGEND = [
  { varName: '--fw-asset', label: '资产沉淀' },
  { varName: '--fw-agent', label: 'Agent 执行' },
  { varName: '--fw-trace', label: '轨迹采集' },
  { varName: '--fw-evolution', label: '自动演化' },
  { varName: '--fw-evaluation', label: '评测反馈' },
];

interface FlywheelDashboardProps {
  workspaceId: number;
}

/** 飞轮中心 SVG:流动弧 + 节点 + 中心脉冲 */
function FlywheelCircle() {
  const size = 264;
  const center = size / 2;
  const radius = 88;
  const nodeR = 26;

  return (
    <div className="ws-flywheel__ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="数据飞轮闭环">
        <defs>
          <linearGradient id="fw-ring" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--fw-asset)" />
            <stop offset="25%" stopColor="var(--fw-agent)" />
            <stop offset="50%" stopColor="var(--fw-trace)" />
            <stop offset="75%" stopColor="var(--fw-evolution)" />
            <stop offset="100%" stopColor="var(--fw-evaluation)" />
          </linearGradient>
          <marker
            id="fw-arrow"
            markerWidth="7"
            markerHeight="6"
            refX="6"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 7 3, 0 6" fill="var(--ws-ink-3, #8a92a6)" />
          </marker>
        </defs>

        {/* 底环 */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="var(--ws-border-subtle, #eff1f6)"
          strokeWidth="1.5"
        />
        {/* 流动环(渐变 + 虚线行进) */}
        <circle
          className="ws-flywheel__ring-arc"
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="url(#fw-ring)"
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* 节点间引导箭头 */}
        {FLYWHEEL_NODES.map((node, i) => {
          const next = FLYWHEEL_NODES[(i + 1) % FLYWHEEL_NODES.length];
          const a1 = ((node.angle - 20) * Math.PI) / 180;
          const a2 = ((next.angle + 20) * Math.PI) / 180;
          const x1 = center + radius * Math.cos(a1);
          const y1 = center - radius * Math.sin(a1);
          const x2 = center + radius * Math.cos(a2);
          const y2 = center - radius * Math.sin(a2);
          return (
            <line
              key={`guide-${i}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="transparent"
              markerEnd="url(#fw-arrow)"
            />
          );
        })}

        {/* 中心脉冲 */}
        <circle cx={center} cy={center} r={30} fill="var(--fw-asset-soft, rgba(79,70,229,0.08))">
          <animate attributeName="r" values="26;34;26" dur="3s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.9;0.4;0.9" dur="3s" repeatCount="indefinite" />
        </circle>
        <text
          x={center}
          y={center - 4}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="13"
          fontWeight="700"
          fill="var(--ws-ink, #14161c)"
        >
          数据飞轮
        </text>
        <text
          x={center}
          y={center + 12}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="10"
          fill="var(--ws-ink-3, #8a92a6)"
        >
          Flywheel
        </text>

        {/* 五节点 */}
        {FLYWHEEL_NODES.map((node) => {
          const angle = (node.angle * Math.PI) / 180;
          const x = center + radius * Math.cos(angle);
          const y = center - radius * Math.sin(angle);
          return (
            <g key={node.key} className="ws-flywheel__node">
              <circle
                cx={x}
                cy={y}
                r={nodeR}
                fill="var(--ws-surface, #fff)"
                stroke={`var(${node.varName})`}
                strokeWidth="1.5"
              />
              <circle cx={x} cy={y} r={nodeR - 5} fill={`var(${node.varName}-soft)`} stroke="none" />
              <text
                x={x}
                y={y + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={node.label.length > 2 ? 9.5 : 11}
                fontWeight="600"
                fill={`var(${node.varName})`}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** 成熟度分布条 */
function MaturityDistribution({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const levels = [
    { key: 'draft', label: '草稿', color: 'var(--ws-ink-3, #b4bac8)' },
    { key: 'proposed', label: '待审', color: 'var(--fw-trace)' },
    { key: 'confirmed', label: '已确认', color: 'var(--fw-evaluation)' },
    { key: 'published', label: '已发布', color: 'var(--fw-agent)' },
    { key: 'canonical', label: '标杆', color: 'var(--fw-asset)' },
  ];
  return (
    <>
      {levels.map((l) => {
        const count = data[l.key] || 0;
        const pct = Math.round((count / total) * 100);
        return (
          <div key={l.key} className="ws-flywheel__bar-row">
            <span className="ws-flywheel__bar-label">{l.label}</span>
            <div className="ws-flywheel__bar-track">
              <div
                className="ws-flywheel__bar-fill"
                style={{ width: `${pct}%`, background: l.color }}
              />
            </div>
            <span className="ws-flywheel__bar-value">{count}</span>
          </div>
        );
      })}
    </>
  );
}

/** Agent 阶段四格 */
function StageGrid({ data }: { data: Record<string, number> }) {
  const stages = [
    { key: 'novice', label: '新手', color: 'var(--ws-ink-3, #b4bac8)' },
    { key: 'proficient', label: '熟练', color: 'var(--fw-trace)' },
    { key: 'expert', label: '专家', color: 'var(--fw-asset)' },
    { key: 'master', label: '大师', color: 'var(--fw-evolution)' },
  ];
  return (
    <div className="ws-flywheel__stage-grid">
      {stages.map((s) => (
        <div key={s.key} className="ws-flywheel__stage-cell">
          <span className="ws-flywheel__stage-dot" style={{ background: s.color }} />
          <span className="ws-flywheel__stage-name">{s.label}</span>
          <span className="ws-flywheel__stage-count">{data[s.key] || 0}</span>
        </div>
      ))}
    </div>
  );
}

export function FlywheelDashboard({ workspaceId }: FlywheelDashboardProps) {
  const { data: agentData } = useRequest(
    async () => {
      const res = await listAgentMaturity(workspaceId);
      return res.data?.data || [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { data: evolutionData } = useRequest(
    async () => {
      const res = await listEvolutionProposals({ workspace_id: workspaceId });
      return res.data?.data || [];
    },
    { refreshDeps: [workspaceId] },
  );

  // 资产成熟度分布(TODO: 接入真实资产聚合 API)
  const maturityStats = useMemo(
    () => ({ draft: 3, proposed: 5, confirmed: 8, published: 2, canonical: 1 }),
    [],
  );

  const stageStats = useMemo(() => {
    if (!agentData) return {};
    return agentData.reduce(
      (acc, a) => {
        acc[a.stage] = (acc[a.stage] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );
  }, [agentData]);

  const pendingProposals = (evolutionData || []).filter(
    (p) => p.status === 'pending',
  ).length;

  return (
    <div className="ws-flywheel__dash">
      {/* 飞轮闭环 */}
      <div className="ws-flywheel__card">
        <div className="ws-flywheel__card-head">
          <span className="ws-flywheel__card-icon"><ApartmentOutlined /></span>
          <span className="ws-flywheel__card-title">飞轮闭环</span>
          <span className="ws-flywheel__card-chip">实时</span>
        </div>
        <div className="ws-flywheel__card-body">
          <FlywheelCircle />
          <div className="ws-flywheel__legend">
            {LEGEND.map((l, i) => (
              <span key={l.label} style={{ display: 'contents' }}>
                {i > 0 && <RightOutlined className="ws-flywheel__legend-arrow" />}
                <span className="ws-flywheel__legend-item">
                  <span className="ws-flywheel__legend-dot" style={{ background: `var(${l.varName})` }} />
                  {l.label}
                </span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* 资产成熟度 */}
      <div className="ws-flywheel__card">
        <div className="ws-flywheel__card-head">
          <span className="ws-flywheel__card-icon" style={{ color: 'var(--fw-asset)' }}>
            <DeploymentUnitOutlined />
          </span>
          <span className="ws-flywheel__card-title">资产成熟度</span>
          <Tooltip title="五级成熟度:草稿 → 待审 → 已确认 → 已发布 → 标杆">
            <span className="ws-flywheel__card-chip">
              {Object.values(maturityStats).reduce((a, b) => a + b, 0)} 资产
            </span>
          </Tooltip>
        </div>
        <div className="ws-flywheel__card-body">
          <MaturityDistribution data={maturityStats} />
        </div>
      </div>

      {/* Agent 成长 + 演化提议 */}
      <div className="ws-flywheel__card">
        <div className="ws-flywheel__card-head">
          <span className="ws-flywheel__card-icon" style={{ color: 'var(--fw-agent)' }}>
            <RobotOutlined />
          </span>
          <span className="ws-flywheel__card-title">Agent 成长</span>
          <span className="ws-flywheel__card-chip">{agentData?.length || 0} 个</span>
        </div>
        <div className="ws-flywheel__card-body">
          <StageGrid data={stageStats} />
        </div>
        <div className="ws-flywheel__card-head" style={{ paddingTop: 4 }}>
          <span className="ws-flywheel__card-icon" style={{ color: 'var(--fw-evolution)' }}>
            <ExperimentOutlined />
          </span>
          <span className="ws-flywheel__card-title">演化提议</span>
          <span
            className="ws-flywheel__card-chip"
            style={
              pendingProposals > 0
                ? { color: 'var(--fw-trace)', background: 'var(--fw-trace-soft)' }
                : undefined
            }
          >
            {pendingProposals} 待审批
          </span>
        </div>
        <div className="ws-flywheel__card-body" style={{ paddingTop: 0 }}>
          {(evolutionData || []).slice(0, 3).map((p) => (
            <div key={p.proposal_id} className="ws-flywheel__item">
              <span className="ws-flywheel__card-icon" style={{ color: 'var(--fw-evolution)' }}>
                <ThunderboltOutlined />
              </span>
              <div className="ws-flywheel__item-main">
                <div className="ws-flywheel__item-title">{p.description || p.detector_name}</div>
              </div>
              <span className="ws-flywheel__item-meta">
                {p.status === 'pending' ? '待审批' : p.status}
              </span>
            </div>
          ))}
          {(evolutionData || []).length === 0 && (
            <div className="ws-flywheel__empty">
              <div className="ws-flywheel__empty-title">暂无演化提议</div>
              <div className="ws-flywheel__empty-hint">积累足够执行轨迹后自动产生优化建议</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
