'use client';

/**
 * 执行阶段归组:把扁平的执行步骤流收敛为「阶段(phase)」数组,
 * 供 ExecutionCapsule 折叠展示(结果为主、过程随行、溯源可达)。
 *
 * 归组策略:
 * 1. planning 时间线 —— planning.todo item 进入 running 的时刻由 hook 观测记录,
 *    步骤按 ts 落入时间窗归入对应 item(阶段 = TODO item)。
 * 2. 单分组兜底 —— 无 todo 时(含刷新恢复、轻量单轮)全部归入单个「执行步骤」
 *    分组,不做语义聚类猜测;胶囊展开后步骤直接平铺,零嵌套层级。
 */

import { useEffect, useRef } from 'react';
import type { WorkspaceExecutionStep, WorkspaceView } from './agent-workspace-types';

export interface ExecutionPhase {
  id: string;
  title: string;
  /** 关联的 planning todo item id(有 planning 归组时存在) */
  planStepId?: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  steps: WorkspaceExecutionStep[];
}

/** planning todo item id → 进入 running 的时刻(ms,客户端时钟) */
export type PhaseTimeline = Map<string, number>;

/** 进入胶囊归组的步骤类型:user/answer/task_created 由 feed 直接渲染 */
const CAPSULE_STEP_TYPES = new Set(['tool_call', 'thinking', 'artifact', 'delivery']);

const tsToMs = (ts: string | null | undefined): number | null => {
  if (!ts) return null;
  let norm = ts.includes(' ') ? ts.replace(' ', 'T') : ts;
  norm = norm.replace(/\.(\d{3})\d+/, '.$1');
  const ms = Date.parse(norm);
  return Number.isNaN(ms) ? null : ms;
};

/** 分组状态:有失败→failed;末步运行中→running;否则 done */
function aggregateStatus(steps: WorkspaceExecutionStep[]): ExecutionPhase['status'] {
  if (steps.some((s) => s.status === 'failed')) return 'failed';
  if (steps.length > 0 && steps[steps.length - 1].status === 'running') return 'running';
  return 'done';
}

/** 单分组兜底:无 todo 时全部步骤归入「执行步骤」(零嵌套层级)。 */
function singlePhase(steps: WorkspaceExecutionStep[]): ExecutionPhase[] {
  if (!steps.length) return [];
  return [{ id: 'phase-run', title: '执行步骤', status: aggregateStatus(steps), steps }];
}

/**
 * planning 时间线归组:每个 todo item 占据 [enterMs, 下一 item enterMs) 时间窗;
 * 首个 item 窗口之前的步骤归入「先前执行」段(运行中刷新恢复的历史部分)。
 * timeline 为空(刷新恢复的已完成会话)时返回 null,由调用方回退到单分组。
 */
function planTimelinePhases(
  steps: WorkspaceExecutionStep[],
  planning: NonNullable<WorkspaceView['planning']>,
  timeline: PhaseTimeline,
): ExecutionPhase[] | null {
  const entries = planning.steps
    .map((item) => ({ item, enterMs: timeline.get(item.id) }))
    .sort((a, b) => (a.enterMs ?? Infinity) - (b.enterMs ?? Infinity) || 0);
  // 无任何观测记录:时间线不可用,回退
  if (!entries.some((e) => e.enterMs !== undefined)) return null;

  const phases: ExecutionPhase[] = [];
  const leftover: WorkspaceExecutionStep[] = [];
  const buckets = entries.map((e) => ({ entry: e, steps: [] as WorkspaceExecutionStep[] }));

  for (const step of steps) {
    const ms = tsToMs(step.ts);
    let target: { entry: (typeof entries)[number]; steps: WorkspaceExecutionStep[] } | null = null;
    if (ms !== null) {
      // 落入最后一个 enterMs <= ts 的窗口
      for (const b of buckets) {
        if (b.entry.enterMs !== undefined && b.entry.enterMs <= ms) target = b;
      }
    }
    if (target) {
      target.steps.push(step);
    } else {
      // 首窗口之前/无 ts:归「先前执行」(时间窗启发式的已知边界,只影响恢复场景)
      leftover.push(step);
    }
  }

  if (leftover.length) {
    phases.push({
      id: 'phase-prior',
      title: '先前执行',
      status: aggregateStatus(leftover),
      steps: leftover,
    });
  }
  for (const b of buckets) {
    phases.push({
      id: `phase-${b.entry.item.id}`,
      planStepId: b.entry.item.id,
      title: b.entry.item.title,
      status: b.entry.item.status,
      steps: b.steps,
    });
  }
  return phases;
}

/** 纯函数:执行步骤流 → 阶段数组(归组策略见文件头)。 */
export function buildExecutionPhases(
  execution: WorkspaceExecutionStep[],
  planning: WorkspaceView['planning'],
  timeline?: PhaseTimeline,
): ExecutionPhase[] {
  const steps = execution.filter((s) => CAPSULE_STEP_TYPES.has(s.type));
  if (!steps.length) return [];
  if (planning && timeline && timeline.size > 0) {
    const byTimeline = planTimelinePhases(steps, planning, timeline);
    if (byTimeline) return byTimeline;
  }
  return singlePhase(steps);
}

/**
 * 观测 planning todo 状态推进,记录每个 item 首次进入 running 的时刻,
 * 供时间线归组。全量覆盖帧只有终态,历史推进靠流式期间逐帧观测。
 * 只返回时间线;归组由调用方对当前胶囊批次执行(避免跨轮次步骤混入)。
 */
export function usePlanningTimeline(planning: WorkspaceView['planning']): PhaseTimeline {
  const timelineRef = useRef<PhaseTimeline>(new Map());

  useEffect(() => {
    if (!planning) return;
    const now = Date.now();
    for (const item of planning.steps) {
      if (item.status === 'running' && !timelineRef.current.has(item.id)) {
        timelineRef.current.set(item.id, now);
      }
    }
  }, [planning]);

  return timelineRef.current;
}
