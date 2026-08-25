'use client';

/**
 * 执行胶囊:过程步骤的容器组件(结果为主、过程随行、溯源可达)。
 * - L0 状态条:一行常驻 —— 运行中实时滚动当前动作+进度;完成收敛为
 *   一行摘要(点开可溯源);失败以警示态常驻并自动展开定位。
 * - L1 阶段组:阶段(= planning todo item / 语义聚类段)默认折叠,点击展开。
 * - L2 步骤行:轻量行(action tag + 标题 + 耗时),点击透传 onStepClick
 *   由外层打开工作空间预览(vis/output/入参)。
 * 视觉:状态用纯 CSS 节点(ws-cnode)与细线 spinner,不用 antd 实心图标,
 * 保持设计稿的轻量层级。
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { WorkspaceExecutionStep } from './agent-workspace-types';
import type { ExecutionPhase } from './use-execution-phases';

export interface ExecutionCapsuleProps {
  phases: ExecutionPhase[];
  /** 会话/一轮执行是否仍在运行(决定胶囊处于实时态还是收敛态) */
  running: boolean;
  onStepClick?: (step: WorkspaceExecutionStep) => void;
}

/** 步骤类型 → 短标签(展示在步骤行左侧,等宽字体) */
function stepTag(step: WorkspaceExecutionStep): string {
  if (step.type === 'thinking') return 'think';
  if (step.action) return step.action.length > 8 ? step.action.slice(0, 8) : step.action;
  return step.type === 'delivery' ? 'deliver' : step.type;
}

/** tag 着色类别(对齐 vis_manus 彩色 tag 语言):read 绿 / sql 青 / bash 紫 / python 蓝 / write 琥珀 / deliver 青绿 / metric 紫 */
function tagCategory(step: WorkspaceExecutionStep): string {
  const key = `${step.action || ''}`.toLowerCase();
  // 工具名多为 snake_case,`_` 属于 \w 会隔断 \b,故用 (^|[^a-z0-9]) / ([^a-z0-9]|$) 替代 \b
  if (/(?:^|[^a-z0-9])(?:metric|指标|measure)(?:[^a-z0-9]|$)/.test(key)) return 'metric';
  if (/(?:^|[^a-z0-9])(?:read|grep|glob|search|find|browse|list)(?:[^a-z0-9]|$)/.test(key)) return 'read';
  if (/(?:^|[^a-z0-9])(?:sql|query|db)(?:[^a-z0-9]|$)/.test(key)) return 'sql';
  if (/(?:^|[^a-z0-9])(?:bash|shell|sh|terminal)(?:[^a-z0-9]|$)/.test(key)) return 'bash';
  if (/(?:^|[^a-z0-9])(?:python|py)(?:[^a-z0-9]|$)/.test(key)) return 'python';
  if (/(?:^|[^a-z0-9])(?:write|edit|create|generate)(?:[^a-z0-9]|$)/.test(key)) return 'write';
  if (/(?:^|[^a-z0-9])(?:deliver|send)(?:[^a-z0-9]|$)/.test(key)) return 'deliver';
  if (/(?:^|[^a-z0-9])(?:preload|loaded)(?:[^a-z0-9]|$)/.test(key)) return 'skill';
  if (/(?:^|[^a-z0-9])(?:skill|plugin)(?:[^a-z0-9]|$)/.test(key)) return 'skill';
  return 'default';
}

/** LLM 思考块:thinking 不是工具步骤,弱化为灰字行 + 内联可展开内容,不参与步骤计数 */
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
        <span className={`ws-cchev ws-cchev--sm${open ? ' ws-cchev--up' : ''}`} aria-hidden />
        <img src="/icons/thinking.svg" className="ws-capsule-think__icon" alt="" />
        <span className="ws-capsule-think__label">{step.title}</span>
        {step.status === 'running' && <span className="ws-capsule-step__spin" aria-label="运行中" />}
      </button>
      {open && text && (
        <div className="ws-capsule-think__text">{text}</div>
      )}
    </div>
  );
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

/** 相邻步骤时间戳差值 → 每步耗时(首步无前序,计 0) */
function buildDurations(phases: ExecutionPhase[]): Map<string, number> {
  const flat = phases.flatMap((p) => p.steps);
  const map = new Map<string, number>();
  for (let i = 1; i < flat.length; i++) {
    const cur = tsToMs(flat[i].ts);
    const prev = tsToMs(flat[i - 1].ts);
    if (cur !== null && prev !== null && cur > prev) map.set(flat[i].id, cur - prev);
  }
  return map;
}

function PhaseStepRow({
  step,
  duration,
  onStepClick,
}: {
  step: WorkspaceExecutionStep;
  duration?: number;
  onStepClick?: (s: WorkspaceExecutionStep) => void;
}) {
  if (step.type === 'thinking') return <ThinkingRow step={step} />;
  const clickable = !!onStepClick && step.type !== 'artifact';
  return (
    <div
      className={`ws-capsule-step${step.status === 'running' ? ' ws-capsule-step--running' : ''}${step.status === 'failed' ? ' ws-capsule-step--failed' : ''}`}
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
      <span className={`ws-capsule-step__tag ws-capsule-step__tag--${tagCategory(step)}`}>{stepTag(step)}</span>
      <span className="ws-capsule-step__title">{step.title}</span>
      {step.status === 'running' && <span className="ws-capsule-step__spin" aria-label="运行中" />}
      {step.status === 'failed' && <span className="ws-capsule-step__failed-label">失败</span>}
      {step.status === 'done' && duration !== undefined && (
        <span className="ws-capsule-step__dur">{fmtDuration(duration)}</span>
      )}
      {step.narration && <div className="ws-capsule-step__narration">{step.narration}</div>}
    </div>
  );
}

export function ExecutionCapsule({ phases, running, onStepClick }: ExecutionCapsuleProps) {
  // 整体收敛:完成(或挂载即完成)时胶囊默认折叠为一行摘要,点击展开溯源
  const prevRunningRef = useRef(running);
  const [expanded, setExpanded] = useState(running);

  useEffect(() => {
    // 运行结束 → 自动收敛(用户随后的点击为主动溯源)
    if (prevRunningRef.current && !running) setExpanded(false);
    prevRunningRef.current = running;
  }, [running]);

  const totalSteps = useMemo(
    () => phases.reduce((n, p) => n + p.steps.filter((s) => s.type !== 'thinking').length, 0),
    [phases],
  );
  const failedSteps = useMemo(
    () => phases.reduce((n, p) => n + p.steps.filter((s) => s.type !== 'thinking' && s.status === 'failed').length, 0),
    [phases],
  );
  const doneSteps = useMemo(
    () => phases.reduce((n, p) => n + p.steps.filter((s) => s.type !== 'thinking' && s.status === 'done').length, 0),
    [phases],
  );
  const durations = useMemo(() => buildDurations(phases), [phases]);
  const phaseDuration = (phase: ExecutionPhase) =>
    phase.steps.reduce((sum, s) => sum + (durations.get(s.id) ?? 0), 0);

  // 当前阶段:优先 running 阶段;否则最后一个有步骤的阶段
  const currentPhase = useMemo(() => {
    const runningPhase = phases.find((p) => p.status === 'running');
    if (runningPhase) return runningPhase;
    const withSteps = [...phases].reverse().find((p) => p.steps.length > 0);
    return withSteps ?? null;
  }, [phases]);
  const currentStep = useMemo(() => {
    if (!currentPhase) return null;
    const toolSteps = currentPhase.steps.filter((s) => s.type !== 'thinking');
    if (!toolSteps.length) return null;
    const running = toolSteps.filter((s) => s.status === 'running');
    return running.length ? running[running.length - 1] : toolSteps[toolSteps.length - 1] ?? null;
  }, [currentPhase]);

  // 阶段展开:用户手动操作优先;未操作时自动展开 running/failed 阶段
  const [manualOpen, setManualOpen] = useState<Set<string> | null>(null);
  const isPhaseOpen = (phase: ExecutionPhase) => {
    if (manualOpen) return manualOpen.has(phase.id);
    return expanded && (phase.status === 'running' || phase.status === 'failed');
  };
  const togglePhase = (phase: ExecutionPhase) => {
    setManualOpen((prev) => {
      const base = prev ?? new Set(expanded ? phases.filter((p) => p.status === 'running' || p.status === 'failed').map((p) => p.id) : []);
      const next = new Set(base);
      if (next.has(phase.id)) next.delete(phase.id);
      else next.add(phase.id);
      return next;
    });
  };

  // 一轮新执行开始:重置手动展开状态,回到自动跟随
  useEffect(() => {
    if (running) setManualOpen(null);
  }, [running]);

  // 总耗时(相邻步骤 ts 差值求和,无 ts 数据时为 0 不展示)
  const totalDuration = useMemo(
    () => phases.reduce((sum, p) => sum + p.steps.reduce((s, st) => s + (durations.get(st.id) ?? 0), 0), 0),
    [phases, durations],
  );

  if (!phases.length || totalSteps === 0) return null;

  const pct = totalSteps > 0 ? Math.round((doneSteps / totalSteps) * 100) : 0;
  const hasFailed = failedSteps > 0;
  const durationLabel = totalDuration > 0 ? ` · ${fmtDuration(totalDuration)}` : '';

  return (
    <div className={`ws-capsule${hasFailed ? ' ws-capsule--failed' : ''}${running ? ' ws-capsule--running' : ''}`}>
      <button
        type="button"
        className={`ws-capsule__head${running ? ' ws-capsule__head--running' : ''}${hasFailed && !running ? ' ws-capsule__head--warn' : ''}`}
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {running ? (
          <span className="ws-capsule__head-spinner" aria-label="运行中" />
        ) : (
          <span className={`ws-cnode ws-cnode--${hasFailed ? 'failed' : 'done'}`} />
        )}
        <span className="ws-capsule__head-title">
          {running
            ? // 单阶段时标题直接落到当前步骤,避免「正在执行记录」这类无意义层级
              phases.length === 1 && !phases[0].planStepId
              ? `正在执行${currentStep ? ` — ${currentStep.title}` : ''}`
              : `正在${currentPhase?.title ?? '执行'}${currentStep ? ` — ${currentStep.title}` : ''}`
            : hasFailed
              ? `执行完成 · ${doneSteps}/${totalSteps} 步${durationLabel} · ${failedSteps} 步失败`
              : `执行完成 · ${totalSteps} 步${durationLabel}`}
        </span>
        {running && (
          <>
            <span className="ws-capsule__head-meta">
              {doneSteps}/{totalSteps}
            </span>
            <span className="ws-capsule__pbar">
              <i style={{ width: `${pct}%` }} />
            </span>
          </>
        )}
        <span className={`ws-cchev${expanded ? ' ws-cchev--up' : ''}`} aria-hidden />
      </button>

      {expanded && (
        <div className="ws-capsule__body">
          {(() => {
            // 单阶段(无 planning 归组的轻量场景):去掉阶段头,步骤直接平铺,避免双层折叠
            if (phases.length === 1 && !phases[0].planStepId) {
              return (
                <div className="ws-capsule__rail">
                  {phases[0].steps.map((step) => (
                    <PhaseStepRow key={step.id} step={step} duration={durations.get(step.id)} onStepClick={onStepClick} />
                  ))}
                </div>
              );
            }
            return phases.map((phase) => {
              const open = isPhaseOpen(phase);
              const phaseFailed = phase.status === 'failed' || phase.steps.some((s) => s.status === 'failed');
              const toolStepCount = phase.steps.filter((s) => s.type !== 'thinking').length;
              const empty = phase.steps.length === 0;
              const meta = empty
                ? '待开始'
                : `${toolStepCount} 步${phaseDuration(phase) > 0 ? ` · ${fmtDuration(phaseDuration(phase))}` : ''}`;
              return (
                <div key={phase.id} className={`ws-capsule-phase${phase.status === 'running' ? ' ws-capsule-phase--running' : ''}${phaseFailed ? ' ws-capsule-phase--failed' : ''}`}>
                  <button
                    type="button"
                    className={`ws-capsule-phase__head${empty ? ' ws-capsule-phase__head--empty' : ''}`}
                    onClick={() => !empty && togglePhase(phase)}
                    aria-expanded={open}
                  >
                    <span className={`ws-cnode ws-cnode--${phase.status}`} />
                    <span className="ws-capsule-phase__title">{phase.title}</span>
                    <span className="ws-capsule-phase__meta">{meta}</span>
                    {!empty && <span className={`ws-cchev ws-cchev--sm${open ? ' ws-cchev--up' : ''}`} aria-hidden />}
                  </button>
                  {open && !empty && (
                    <div className="ws-capsule-phase__steps">
                      {phase.steps.map((step) => (
                        <PhaseStepRow key={step.id} step={step} duration={durations.get(step.id)} onStepClick={onStepClick} />
                      ))}
                    </div>
                  )}
                </div>
              );
            });
          })()}
        </div>
      )}
    </div>
  );
}
