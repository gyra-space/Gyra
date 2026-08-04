'use client';

/**
 * Agent 成长面板 —— 四阶段进度 + 评分维度 + 权限徽章。
 *
 * 视觉:阶段软色头像 + 四段式进度轨道 + 等宽数字总分,
 * 维度细条与飞轮语义色一致。
 */
import { useMemo } from 'react';
import { Tooltip } from 'antd';
import { RobotOutlined, TrophyOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import {
  listAgentMaturity,
  type AgentMaturityRecord,
  type AgentStage,
} from '@/client/api/flywheel';

interface AgentGrowthPanelProps {
  workspaceId: number;
}

/** 阶段配置(varName 对应 flywheel.css 语义色) */
const STAGE_CONFIG: Record<
  AgentStage,
  { label: string; varName: string; next: AgentStage | null }
> = {
  novice: { label: '新手', varName: '--fw-novice', next: 'proficient' },
  proficient: { label: '熟练', varName: '--fw-trace', next: 'expert' },
  expert: { label: '专家', varName: '--fw-asset', next: 'master' },
  master: { label: '大师', varName: '--fw-evolution', next: null },
};

const STAGE_ORDER: AgentStage[] = ['novice', 'proficient', 'expert', 'master'];

/** 阶段主色(novice 用中性灰,其余语义色) */
function stageColor(stage: AgentStage): string {
  return stage === 'novice' ? 'var(--ws-ink-3, #b4bac8)' : `var(${STAGE_CONFIG[stage].varName})`;
}

function stageSoft(stage: AgentStage): string {
  return stage === 'novice'
    ? 'var(--ws-bg, #f7f8fa)'
    : `var(${STAGE_CONFIG[stage].varName}-soft)`;
}

/** 晋升门槛提示 */
const PROMOTION_HINT: Record<AgentStage, string> = {
  novice: '10 次执行',
  proficient: '30 次执行 + 5 资产',
  expert: '3 人背书',
  master: '',
};

/** 单个 Agent 成长卡片 */
function AgentCard({ agent }: { agent: AgentMaturityRecord }) {
  const stage: AgentStage = agent.stage || 'novice';
  const currentIndex = STAGE_ORDER.indexOf(stage);
  const next = STAGE_CONFIG[stage].next;

  const dimensions = [
    { label: '背书', value: agent.attest_count, max: 10, color: 'var(--fw-asset)' },
    { label: '执行', value: agent.execution_count, max: 50, color: 'var(--fw-agent)' },
    { label: '演化', value: agent.evolution_count, max: 10, color: 'var(--fw-trace)' },
    {
      label: '评测',
      value: Math.round((agent.evaluation_score || 0) * 10),
      max: 10,
      color: 'var(--fw-evaluation)',
    },
  ];

  const permissions = useMemo(() => {
    const map: Record<AgentStage, string[]> = {
      novice: ['产出需审批'],
      proficient: ['routine 可自动'],
      expert: ['可自动发布', '可背书他人', '可主导演化'],
      master: ['最小审批', '可认证晋升'],
    };
    return map[stage] || [];
  }, [stage]);

  return (
    <div
      className="ws-flywheel__agent"
      style={{ '--stage-color': stageColor(stage), '--stage-soft': stageSoft(stage) } as React.CSSProperties}
    >
      {/* 头部:头像 + 名称 + 阶段徽章 */}
      <div className="ws-flywheel__agent-head">
        <span className="ws-flywheel__agent-avatar"><RobotOutlined /></span>
        <span className="ws-flywheel__agent-name">{agent.agent_id}</span>
        <span className="ws-flywheel__agent-stage">{STAGE_CONFIG[stage].label}</span>
      </div>

      {/* 四段阶段轨道 */}
      <div className="ws-flywheel__agent-track">
        {STAGE_ORDER.map((s, i) => (
          <span
            key={s}
            className={`ws-flywheel__agent-seg${i <= currentIndex ? ' ws-flywheel__agent-seg--done' : ''}`}
          />
        ))}
      </div>
      <div className="ws-flywheel__agent-stage-labels">
        {STAGE_ORDER.map((s, i) => (
          <span
            key={s}
            className={`ws-flywheel__agent-stage-label${i === currentIndex ? ' ws-flywheel__agent-stage-label--on' : ''}`}
          >
            {STAGE_CONFIG[s].label}
          </span>
        ))}
      </div>

      {/* 总分 */}
      <div className="ws-flywheel__agent-score">
        <span className="ws-flywheel__agent-score-label">综合评分</span>
        <span className="ws-flywheel__agent-score-value">
          {agent.total_score?.toFixed(1) || '0.0'}
        </span>
      </div>

      {/* 评分维度 */}
      {dimensions.map((d) => (
        <div key={d.label} className="ws-flywheel__bar-row" style={{ marginBottom: 6 }}>
          <span className="ws-flywheel__bar-label">{d.label}</span>
          <div className="ws-flywheel__bar-track">
            <div
              className="ws-flywheel__bar-fill"
              style={{ width: `${Math.min(Math.round((d.value / d.max) * 100), 100)}%`, background: d.color }}
            />
          </div>
          <span className="ws-flywheel__bar-value">{d.value}</span>
        </div>
      ))}

      {/* 权限徽章 */}
      <div className="ws-flywheel__agent-perms">
        {permissions.map((p) => (
          <span key={p} className="ws-flywheel__agent-perm">{p}</span>
        ))}
        {next && (
          <Tooltip title={`晋升${STAGE_CONFIG[next].label}还需:${PROMOTION_HINT[stage]}`}>
            <span
              className="ws-flywheel__agent-perm"
              style={{ color: 'var(--ws-accent)', background: 'var(--ws-accent-light)' }}
            >
              距{STAGE_CONFIG[next].label}:{PROMOTION_HINT[stage]}
            </span>
          </Tooltip>
        )}
      </div>
    </div>
  );
}

export function AgentGrowthPanel({ workspaceId }: AgentGrowthPanelProps) {
  const { data: agents } = useRequest(
    async () => {
      const res = await listAgentMaturity(workspaceId);
      return res.data?.data || [];
    },
    { refreshDeps: [workspaceId] },
  );

  // 按阶段排序: master > expert > proficient > novice
  const sortedAgents = useMemo(() => {
    if (!agents) return [];
    return [...agents].sort(
      (a, b) => STAGE_ORDER.indexOf(b.stage) - STAGE_ORDER.indexOf(a.stage),
    );
  }, [agents]);

  return (
    <div className="ws-flywheel__card">
      <div className="ws-flywheel__card-head">
        <span className="ws-flywheel__card-icon" style={{ color: 'var(--fw-agent)' }}>
          <TrophyOutlined />
        </span>
        <span className="ws-flywheel__card-title">Agent 成长</span>
        <span className="ws-flywheel__card-chip">{agents?.length || 0} 个</span>
      </div>
      <div className="ws-flywheel__card-body">
        {sortedAgents.length > 0 ? (
          <div className="ws-flywheel__agent-grid">
            {sortedAgents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        ) : (
          <div className="ws-flywheel__empty">
            <div className="ws-flywheel__empty-title">暂无 Agent 成长数据</div>
            <div className="ws-flywheel__empty-hint">
              Agent 执行任务后自动积累成长评分,从新手逐步晋升
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
