import type { WorkspaceDeliverableFile, WorkspaceExecutionStep } from './agent-workspace-types';

/** 一轮对话:user 步骤(可无,恢复场景) + 后续步骤序列 */
export interface ConversationRound {
  key: string;
  user?: WorkspaceExecutionStep;
  steps: WorkspaceExecutionStep[];
}

/** 按 user 步骤把执行记录切成对话轮次 */
export function splitRounds(execution: WorkspaceExecutionStep[]): ConversationRound[] {
  const rounds: ConversationRound[] = [];
  let current: ConversationRound = { key: 'round-0', steps: [] };
  for (const step of execution) {
    if (step.type === 'user') {
      if (current.user || current.steps.length) rounds.push(current);
      current = { key: `round-${rounds.length + 1}`, user: step, steps: [] };
    } else {
      current.steps.push(step);
    }
  }
  if (current.user || current.steps.length) rounds.push(current);
  return rounds;
}

/** 解析 ts 字符串为毫秒(与 parse-workspace-view.tsToMs 一致;无法解析返回 null) */
function tsToMsLocal(ts: string): number | null {
  let norm = ts.includes(' ') ? ts.replace(' ', 'T') : ts;
  norm = norm.replace(/\.(\d{3})\d+/, '.$1');
  const ms = Date.parse(norm);
  return Number.isNaN(ms) ? null : ms;
}

/** 取轮次起始时间(ms):有用户步骤用 user.ts,否则用轮内最早步骤的 ts;无 ts 返回 null */
export function roundStartMs(round: ConversationRound): number | null {
  const ts = round.user?.ts ?? round.steps.find((s) => s.ts)?.ts;
  return ts ? tsToMsLocal(ts) : null;
}

/** 把交付文件按时间归属到轮次:文件落在「最近一个起始时间 <= 文件时间」的轮次。
 *  无时间戳或找不到归属轮次(如穿插在轮间)的文件进 leftover,在 feed 底部兜底展示。
 *  使得一轮产生的交付文件跟在那一轮答复后面,而非全部堆在 feed 底部。 */
export function groupDeliverablesByRound(
  rounds: ConversationRound[],
  deliverables: WorkspaceDeliverableFile[],
): { byRound: Map<string, WorkspaceDeliverableFile[]>; leftover: WorkspaceDeliverableFile[] } {
  const byRound = new Map<string, WorkspaceDeliverableFile[]>();
  const leftover: WorkspaceDeliverableFile[] = [];
  const starts: { key: string; ms: number }[] = [];
  for (const round of rounds) {
    const ms = roundStartMs(round);
    if (ms !== null) starts.push({ key: round.key, ms });
  }
  starts.sort((a, b) => a.ms - b.ms);
  for (const f of deliverables) {
    const fMs = f.ts ? tsToMsLocal(f.ts) : null;
    if (fMs === null) {
      leftover.push(f);
      continue;
    }
    // 找「起始时间 <= 文件时间」的最晚一轮
    let target: string | null = null;
    for (const s of starts) {
      if (s.ms <= fMs) target = s.key;
      else break;
    }
    if (target === null) {
      leftover.push(f);
      continue;
    }
    const arr = byRound.get(target) ?? [];
    arr.push(f);
    byRound.set(target, arr);
  }
  return { byRound, leftover };
}
