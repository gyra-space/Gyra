import type {
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspaceTaskFile,
} from './agent-workspace-types';

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

export interface RoundFileGroups<T> {
  /** 轮次 key → 归属该轮的文件 */
  byRound: Map<string, T[]>;
  /** 无时间戳 / 早于所有轮次起始时间,无法归属的文件(由调用方在 feed 底部兜底) */
  leftover: T[];
}

/** 通用:把「带产出时间戳的文件」按时间归属到对话轮次。
 *  文件落在「最近一个起始时间 <= 文件时间」的轮次;无时间戳或早于所有轮次
 *  (穿插在轮间等)的文件进 leftover。
 *  交付文件与任务文件只是时间戳字段名不同(ts / created_at),共用同一套归属逻辑。 */
function groupFilesByRound<T>(
  rounds: ConversationRound[],
  files: T[],
  getTs: (file: T) => string | null | undefined,
): RoundFileGroups<T> {
  const byRound = new Map<string, T[]>();
  const leftover: T[] = [];
  const starts: { key: string; ms: number }[] = [];
  for (const round of rounds) {
    const ms = roundStartMs(round);
    if (ms !== null) starts.push({ key: round.key, ms });
  }
  starts.sort((a, b) => a.ms - b.ms);
  for (const f of files) {
    const ts = getTs(f);
    const fMs = ts ? tsToMsLocal(ts) : null;
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

/** 从步骤可文本化字段中抽取明确提及的文件名(引号/反引号包裹的常见扩展名)。
 *  用于 answer/tool_call 等步骤已说出文件名但 deliverable_files 时间戳/下发时机
 *  不准的场景,把文件绑定到真正提及它的轮次。 */
function extractMentionedFileNames(output: string): string[] {
  const names = new Set<string>();
  const regex = /["'`]([^"'`]*\.(?:html|htm|md|markdown|pdf|png|jpg|jpeg|gif|svg|webp|csv|xlsx|xls|py|js|jsx|ts|tsx|java|go|rs|sql|json|yaml|yml|xml|txt))["'`]/gi;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(output)) !== null) {
    names.add(m[1]);
  }
  return Array.from(names);
}

function stepSearchableText(step: WorkspaceExecutionStep): string {
  const parts: string[] = [
    step.output || '',
    step.title || '',
    step.action || '',
    step.narration || '',
  ];
  if (step.action_input && typeof step.action_input === 'object') {
    parts.push(JSON.stringify(step.action_input));
  }
  if (step.artifact && typeof step.artifact === 'object') {
    parts.push(JSON.stringify(step.artifact));
  }
  return parts.join(' ');
}

/** 交付文件按轮次归属:一轮产出的交付文件跟在那一轮答复后面,而非全部堆在 feed 底部。
 *  归属优先级:
 *  1. answer/tool_call 等步骤文本中明确提及的文件名 → 绑定到提及它的轮次;
 *  2. 产出 ts 落在某轮时间区间 → 归属该轮;
 *  3. ts 为空 / 早于所有轮次起始时间(时区格式差异、后端未下发)→ 归到最早一轮,
 *     不再进 leftover。交付文件必然在会话开始之后产出,堆在 feed 最底部会让
 *     多轮追问时历史交付物看起来"跟着最新一轮跑"。 */
export function groupDeliverablesByRound(
  rounds: ConversationRound[],
  deliverables: WorkspaceDeliverableFile[],
): RoundFileGroups<WorkspaceDeliverableFile> {
  // 步骤文本中明确提及的文件名 → 最早提到它的轮次 key
  const mentionedFileRound = new Map<string, string>();
  for (const round of rounds) {
    for (const step of round.steps) {
      for (const name of extractMentionedFileNames(stepSearchableText(step))) {
        if (!mentionedFileRound.has(name)) {
          mentionedFileRound.set(name, round.key);
        }
      }
    }
  }

  const byMention: WorkspaceDeliverableFile[] = [];
  const byTime: WorkspaceDeliverableFile[] = [];
  for (const f of deliverables) {
    if (mentionedFileRound.has(f.file_name)) {
      byMention.push(f);
    } else {
      byTime.push(f);
    }
  }

  const groups = groupFilesByRound(rounds, byTime, (f) => f.ts);
  const attach = (key: string, files: WorkspaceDeliverableFile[]) => {
    if (!files.length) return;
    const arr = groups.byRound.get(key) ?? [];
    arr.push(...files);
    groups.byRound.set(key, arr);
  };
  for (const f of byMention) {
    attach(mentionedFileRound.get(f.file_name)!, [f]);
  }

  // 无归属(ts 为空或早于所有轮次)的交付文件挂到最早一轮,而不是留在 feed 底部
  if (groups.leftover.length && rounds.length) {
    attach(rounds[0].key, groups.leftover);
    groups.leftover = [];
  }
  return groups;
}

/** 任务文件按轮次归属(时间戳字段为 created_at),与交付文件同一套归属逻辑。 */
export function groupTaskFilesByRound(
  rounds: ConversationRound[],
  taskFiles: WorkspaceTaskFile[],
): RoundFileGroups<WorkspaceTaskFile> {
  return groupFilesByRound(rounds, taskFiles, (f) => f.created_at);
}
