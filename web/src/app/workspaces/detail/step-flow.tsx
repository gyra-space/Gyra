'use client';

/**
 * StepFlow —— 简洁模式执行过程顺序流。
 *
 * 设计目标(替代 ExecutionCapsule 的全折叠方案):
 * - 正常顺序展示 Agent 工作过程:思考 / 工具步骤 / 阶段回复按真实时序排列;
 * - 有 planning(Todo)时:步骤按 Todo item 分组,每组一个可折叠区块
 *   (组头 = Todo 标题 + 状态节点 + 步骤数;运行中/失败的组默认展开,
 *   已完成组默认折叠收敛);
 * - 无 planning 时:步骤直接顺序平铺,默认全部展开,不做额外折叠;
 * - thinking 弱化为灰字可展开行,不参与步骤计数(与胶囊语义一致);
 * - 交付文件 / 回答由 feed 主视觉渲染,不在本组件职责内。
 */

import { useMemo, useState } from 'react';
import {
  CodeOutlined,
  CompassOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  GlobalOutlined,
  ReadOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import type { WorkspaceExecutionStep } from './agent-workspace-types';
import type { ExecutionPhase } from './use-execution-phases';

export interface StepFlowProps {
  phases: ExecutionPhase[];
  /** 会话是否仍在运行(决定流末态是实时还是收敛) */
  running: boolean;
  onStepClick?: (step: WorkspaceExecutionStep) => void;
  /** 当前选中步骤 id:用于左侧步骤行的高亮选中态 */
  selectedStepId?: string | null;
}

/* ── 与 execution-capsule 保持一致的视觉语言 ─────────────────────── */

/** 工具类型 key:按 action 归类,决定专属图标 */
function toolTypeKey(action?: string | null): string {
  const key = `${action || ''}`.toLowerCase();
  // 工具名多为 snake_case(如 execute_metric_query),`_` 属于 \w 会隔断 \b 边界,
  // 故用 (^|[^a-z0-9]) 与 ([^a-z0-9]|$) 替代 \b,保证下划线连接词也被计入分隔。
  if (/(?:^|[^a-z0-9])(?:read|grep|glob|cat|view)(?:[^a-z0-9]|$)/.test(key)) return 'read';
  if (/(?:^|[^a-z0-9])(?:metric|指标|measure)(?:[^a-z0-9]|$)/.test(key)) return 'metric';
  if (/(?:^|[^a-z0-9])(?:search|find|query|list|get)(?:[^a-z0-9]|$)/.test(key)) return 'search';
  if (/(?:^|[^a-z0-9])(?:sql|db|database)(?:[^a-z0-9]|$)/.test(key)) return 'sql';
  if (/(?:^|[^a-z0-9])(?:bash|shell|terminal|cmd)(?:[^a-z0-9]|$)/.test(key)) return 'code';
  if (/(?:^|[^a-z0-9])(?:python|execute_code|run_code)(?:[^a-z0-9]|$)/.test(key)) return 'python';
  if (/(?:^|[^a-z0-9])(?:write|edit|create|generate|save)(?:[^a-z0-9]|$)/.test(key)) return 'write';
  if (/(?:^|[^a-z0-9])(?:browser|browse|open_url|visit|web)(?:[^a-z0-9]|$)/.test(key)) return 'browser';
  if (/(?:^|[^a-z0-9])(?:deliver|send)(?:[^a-z0-9]|$)/.test(key)) return 'deliver';
  if (/(?:^|[^a-z0-9])(?:skill)(?:[^a-z0-9]|$)/.test(key)) return 'skill';
  return 'other';
}

/** 工具类型 → 专属图标(展开明细行与折叠摘要行共用) */
const TOOL_ICONS: Record<string, React.ReactNode> = {
  read: <ReadOutlined />,
  metric: <CompassOutlined />,
  search: <SearchOutlined />,
  sql: <DatabaseOutlined />,
  code: <CodeOutlined />,
  python: <CodeOutlined />,
  write: <FileTextOutlined />,
  browser: <GlobalOutlined />,
  deliver: <FileTextOutlined />,
  skill: <ThunderboltOutlined />,
  other: <ToolOutlined />,
};

/** 工具步骤行首图标:按工具类型专属 logo,状态统一在行尾 */
function ToolTypeIcon({ step }: { step: WorkspaceExecutionStep }) {
  return <>{TOOL_ICONS[toolTypeKey(step.action)]}</>;
}

const tsToMs = (ts: string | null | undefined): number | null => {
  if (!ts) return null;
  let norm = ts.includes(' ') ? ts.replace(' ', 'T') : ts;
  norm = norm.replace(/\.(\d{3})\d+/, '.$1');
  const ms = Date.parse(norm);
  return Number.isNaN(ms) ? null : ms;
};

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${(ms / 1000).toFixed(1)}s`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m${s % 60}s`;
}

/** 每步耗时:优先取与上一步的时间差;首步/上一步无 ts 时,用与下一步的差值兜底,
 * 让未分组折叠的单个工具步骤也能显示耗时(数据层仅单 ts,为近似值)。 */
function buildDurations(phases: ExecutionPhase[]): Map<string, number> {
  const flat = phases.flatMap((p) => p.steps);
  const map = new Map<string, number>();
  for (let i = 0; i < flat.length; i++) {
    const cur = tsToMs(flat[i].ts);
    if (cur === null) continue;
    const prev = i > 0 ? tsToMs(flat[i - 1].ts) : null;
    if (prev !== null && cur > prev) {
      map.set(flat[i].id, cur - prev);
      continue;
    }
    const next = i < flat.length - 1 ? tsToMs(flat[i + 1].ts) : null;
    if (next !== null && next > cur) map.set(flat[i].id, next - cur);
  }
  return map;
}

/** thinking 行:简单 icon 标记,灰字弱化,可展开,不计步骤数 */
function ThinkingRow({ step }: { step: WorkspaceExecutionStep }) {
  const [open, setOpen] = useState(false);
  const text = (step.output || '').trim();
  return (
    <div className="ws-capsule-think">
      <button
        type="button"
        className="ws-capsule-think__head"
        onClick={text ? () => setOpen((v) => !v) : undefined}
        aria-expanded={open}
      >
        <span className="ws-capsule-think__label">{step.title}</span>
        {step.status === 'running' && <span className="ws-capsule-step__spin" aria-label="运行中" />}
        {text && <span className={`ws-cchev ws-cchev--sm${open ? ' ws-cchev--up' : ''}`} aria-hidden />}
      </button>
      {open && text && <div className="ws-capsule-think__text">{text}</div>}
    </div>
  );
}

function StepRow({
  step,
  duration,
  onStepClick,
  selectedStepId,
}: {
  step: WorkspaceExecutionStep;
  duration?: number;
  onStepClick?: (s: WorkspaceExecutionStep) => void;
  selectedStepId?: string | null;
}) {
  if (step.type === 'thinking') return <ThinkingRow step={step} />;
  const clickable = !!onStepClick && step.type !== 'artifact';
  const active = selectedStepId != null && step.id === selectedStepId;
  return (
    <div
      className={`ws-capsule-step${active ? ' ws-capsule-step--active' : ''}${step.status === 'running' ? ' ws-capsule-step--running' : ''}${step.status === 'failed' ? ' ws-capsule-step--failed' : ''}`}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={clickable ? () => onStepClick!(step) : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onStepClick!(step);
              }
            }
          : undefined
      }
    >
      <span className="ws-capsule-step__icon"><ToolTypeIcon step={step} /></span>
      <span className="ws-capsule-step__title">{step.title}</span>
      <span className="ws-capsule-step__status">
        {step.status === 'running' && <span className="ws-capsule-step__spin" aria-label="运行中" />}
        {step.status === 'failed' && <span className="ws-capsule-step__failed-label">失败</span>}
        {step.status === 'done' && duration !== undefined && (
          <span className="ws-capsule-step__dur">{fmtDuration(duration)}</span>
        )}
      </span>
    </div>
  );
}

/** 连续工具步骤折叠条:参考图为「缩进弱化的灰色摘要行 + chevron」,与普通步骤行区分 */
function ToolRunRow({
  steps,
  durations,
  onStepClick,
  selectedStepId,
}: {
  steps: WorkspaceExecutionStep[];
  durations: Map<string, number>;
  onStepClick?: (s: WorkspaceExecutionStep) => void;
  selectedStepId?: string | null;
}) {
  const running = steps.some((s) => s.status === 'running');
  const failed = steps.some((s) => s.status === 'failed');
  // 默认仅「最新执行中」的批次展开:批内末步仍在运行,或含失败需定位。
  // 已完成批次默认折叠收敛;不用 useEffect 强制重开 —— 运行中用户手动折叠后
  // 不应被下一帧弹开,交互状态以用户为准。
  const lastRunning = steps.length > 0 && steps[steps.length - 1].status === 'running';
  const [open, setOpen] = useState(lastRunning || failed);

  // 按工具名聚合计数,如“execute_raw_sql ×1 · run_terminal_cmd ×3”,每项带专属 icon
  const actionGroups = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of steps) {
      const a = s.action || 'tool';
      counts.set(a, (counts.get(a) ?? 0) + 1);
    }
    return Array.from(counts.entries()).map(([action, count]) => ({ action, count, key: toolTypeKey(action) }));
  }, [steps]);
  const totalDur = steps.reduce((sum, s) => sum + (durations.get(s.id) ?? 0), 0);

  return (
    <div className={`ws-toolrun${running ? ' ws-toolrun--running' : ''}${failed ? ' ws-toolrun--failed' : ''}`}>
      <button
        type="button"
        className="ws-toolrun__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="ws-toolrun__groups">
          <span className="ws-toolrun__prefix">工具使用</span>
          {actionGroups.map((g, i) => (
            <span key={g.action} className="ws-toolrun__group">
              {i > 0 && <i className="ws-toolrun__sep">，</i>}
              <span className="ws-toolrun__g-icon" aria-hidden>
                {TOOL_ICONS[g.key] || TOOL_ICONS.other}
              </span>
              <span className="ws-toolrun__g-name">{g.action}</span>
              <span className="ws-toolrun__g-x">×{g.count}</span>
            </span>
          ))}
        </span>
        {totalDur > 0 && <span className="ws-toolrun__dur">{fmtDuration(totalDur)}</span>}
        <span className={`ws-cchev ws-cchev--sm${open ? ' ws-cchev--up' : ''}`} aria-hidden />
      </button>
      {open && (
        <div className="ws-toolrun__steps">
          {steps.map((s) => (
            <StepRow key={s.id} step={s} duration={durations.get(s.id)} onStepClick={onStepClick} selectedStepId={selectedStepId} />
          ))}
        </div>
      )}
    </div>
  );
}

/** 阶段内步骤渲染:连续 ≥2 个工具步骤折叠为一条摘要行 */
function PhaseSteps({
  steps,
  durations,
  onStepClick,
  selectedStepId,
}: {
  steps: WorkspaceExecutionStep[];
  durations: Map<string, number>;
  onStepClick?: (s: WorkspaceExecutionStep) => void;
  selectedStepId?: string | null;
}) {
  const nodes: React.ReactNode[] = [];
  let run: WorkspaceExecutionStep[] = [];
  const flush = () => {
    if (!run.length) return;
    const group = run;
    run = [];
    if (group.length >= 2) {
      nodes.push(<ToolRunRow key={`run-${group[0].id}`} steps={group} durations={durations} onStepClick={onStepClick} selectedStepId={selectedStepId} />);
    } else {
      nodes.push(<StepRow key={group[0].id} step={group[0]} duration={durations.get(group[0].id)} onStepClick={onStepClick} selectedStepId={selectedStepId} />);
    }
  };
  for (const step of steps) {
    if (step.type === 'thinking') {
      flush();
      nodes.push(<ThinkingRow key={step.id} step={step} />);
    } else {
      run.push(step);
    }
  }
  flush();
  return <>{nodes}</>;
}

/** 单个 Todo 分组:组头可折叠,运行中/失败默认展开,完成默认折叠 */
function PhaseGroup({
  phase,
  durations,
  onStepClick,
  selectedStepId,
}: {
  phase: ExecutionPhase;
  durations: Map<string, number>;
  onStepClick?: (s: WorkspaceExecutionStep) => void;
  selectedStepId?: string | null;
}) {
  const phaseFailed = phase.status === 'failed' || phase.steps.some((s) => s.status === 'failed');
  const autoOpen = phase.status === 'running' || phaseFailed;
  // 默认仅运行中/失败组展开;不强制重开 —— 用户手动折叠后以用户交互为准,
  // 避免运行中下一帧把已折叠的组重新弹开。
  const [open, setOpen] = useState(autoOpen);

  const toolStepCount = phase.steps.filter((s) => s.type !== 'thinking').length;
  const empty = phase.steps.length === 0;
  const phaseDuration = phase.steps.reduce((sum, s) => sum + (durations.get(s.id) ?? 0), 0);
  const meta = empty
    ? '待开始'
    : `${toolStepCount} 步${phaseDuration > 0 ? ` · ${fmtDuration(phaseDuration)}` : ''}`;

  return (
    <div
      className={`ws-flow-group${phase.status === 'running' ? ' ws-flow-group--running' : ''}${phaseFailed ? ' ws-flow-group--failed' : ''}`}
    >
      <button
        type="button"
        className={`ws-flow-group__head${empty ? ' ws-flow-group__head--empty' : ''}`}
        onClick={() => !empty && setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className={`ws-cnode ws-cnode--${phase.status}`} />
        <span className="ws-flow-group__title">{phase.title}</span>
        <span className="ws-flow-group__meta">{meta}</span>
        {!empty && <span className={`ws-cchev ws-cchev--sm${open ? ' ws-cchev--up' : ''}`} aria-hidden />}
      </button>
      {open && !empty && (
        <div className="ws-flow-group__steps">
          <PhaseSteps steps={phase.steps} durations={durations} onStepClick={onStepClick} selectedStepId={selectedStepId} />
        </div>
      )}
    </div>
  );
}

export function StepFlow({ phases, running, onStepClick, selectedStepId }: StepFlowProps) {
  const durations = useMemo(() => buildDurations(phases), [phases]);

  // 无 planning 归组(单分组「执行步骤」):去掉组头,步骤顺序平铺直出
  const flatMode = phases.length === 1 && !phases[0].planStepId;

  if (!phases.length) return null;

  return (
    <div className={`ws-flow${running ? ' ws-flow--running' : ''}`}>
      {flatMode ? (
        <div className="ws-flow__flat">
          <PhaseSteps steps={phases[0].steps} durations={durations} onStepClick={onStepClick} selectedStepId={selectedStepId} />
        </div>
      ) : (
        phases.map((phase) => (
          <PhaseGroup key={phase.id} phase={phase} durations={durations} onStepClick={onStepClick} selectedStepId={selectedStepId} />
        ))
      )}
    </div>
  );
}
