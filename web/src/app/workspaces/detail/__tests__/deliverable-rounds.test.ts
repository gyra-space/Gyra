import { splitRounds, groupDeliverablesByRound, groupTaskFilesByRound } from '../deliverable-rounds';
import type {
  WorkspaceExecutionStep,
  WorkspaceDeliverableFile,
  WorkspaceTaskFile,
} from '../agent-workspace-types';

const user = (id: string, ts: string, output: string): WorkspaceExecutionStep => ({
  id, type: 'user', title: '我', status: 'done', output, ts,
});
const tool = (id: string, ts: string): WorkspaceExecutionStep => ({
  id, type: 'tool_call', title: 'A', status: 'done', ts,
});
const answer = (id: string, ts: string): WorkspaceExecutionStep => ({
  id, type: 'answer', title: '回复', status: 'done', output: 'ok', ts,
});
const delivery = (id: string, ts?: string | null): WorkspaceDeliverableFile => ({
  file_id: id,
  file_name: `${id}.html`,
  file_size: 1,
  render_type: 'iframe',
  ts: ts ?? null,
});
const taskFile = (id: string, createdAt?: string | null): WorkspaceTaskFile => ({
  file_id: id,
  file_name: `${id}.csv`,
  file_type: 'tool_output',
  file_size: 1,
  created_at: createdAt ?? undefined,
});

describe('splitRounds', () => {
  test('按 user 步骤切分,每轮含 user + 后续步骤', () => {
    const rounds = splitRounds([
      user('u1', '2026-08-01T09:00:00', '第一问'),
      tool('t1', '2026-08-01T09:00:01'),
      answer('a1', '2026-08-01T09:00:02'),
      user('u2', '2026-08-01T09:10:00', '追问'),
      tool('t2', '2026-08-01T09:10:01'),
      answer('a2', '2026-08-01T09:10:02'),
    ]);
    expect(rounds).toHaveLength(2);
    expect(rounds[0].user?.output).toBe('第一问');
    expect(rounds[1].user?.output).toBe('追问');
    expect(rounds[1].steps.map((s) => s.id)).toEqual(['t2', 'a2']);
  });
});

describe('groupDeliverablesByRound', () => {
  const rounds = splitRounds([
    user('u1', '2026-08-01T09:00:00', '第一问'),
    tool('t1', '2026-08-01T09:00:01'),
    answer('a1', '2026-08-01T09:00:02'),
    user('u2', '2026-08-01T09:10:00', '追问'),
    tool('t2', '2026-08-01T09:10:01'),
    answer('a2', '2026-08-01T09:10:02'),
  ]);

  test('第一轮产出的交付文件归属第一轮,第二轮归属第二轮(不再全堆底部)', () => {
    const { byRound, leftover } = groupDeliverablesByRound(rounds, [
      delivery('f1', '2026-08-01T09:00:01.500'),
      delivery('f2', '2026-08-01T09:10:01.500'),
    ]);
    expect(leftover).toHaveLength(0);
    expect(byRound.get(rounds[0].key)?.map((f) => f.file_id)).toEqual(['f1']);
    expect(byRound.get(rounds[1].key)?.map((f) => f.file_id)).toEqual(['f2']);
  });

  test('缺时间戳的交付文件进 leftover(该轮无法归属时 feed 底部兜底)', () => {
    const { byRound, leftover } = groupDeliverablesByRound(rounds, [
      delivery('f1', '2026-08-01T09:00:01.500'),
      delivery('f3', null),
    ]);
    expect(byRound.get(rounds[0].key)?.map((f) => f.file_id)).toEqual(['f1']);
    expect(leftover.map((f) => f.file_id)).toEqual(['f3']);
  });

  test('在任意轮次发起前交付的文件(无归属轮次)进 leftover', () => {
    const { byRound, leftover } = groupDeliverablesByRound(rounds, [
      delivery('f0', '2026-08-01T08:59:00'),
    ]);
    expect(byRound.size).toBe(0);
    expect(leftover.map((f) => f.file_id)).toEqual(['f0']);
  });

  test('一轮内若没有 user 步骤(恢复场景),以轮内最早步骤 ts 作为归属基准', () => {
    const noUserRounds = splitRounds([
      tool('t0', '2026-08-01T08:58:00'),
      answer('a0', '2026-08-01T08:58:01'),
      user('u1', '2026-08-01T09:00:00', '第一问'),
    ]);
    const { byRound, leftover } = groupDeliverablesByRound(noUserRounds, [
      delivery('f0', '2026-08-01T08:58:00.500'),
      delivery('f1', '2026-08-01T09:00:01'),
    ]);
    expect(byRound.get(noUserRounds[0].key)?.map((f) => f.file_id)).toEqual(['f0']);
    expect(byRound.get(noUserRounds[1].key)?.map((f) => f.file_id)).toEqual(['f1']);
    expect(leftover).toHaveLength(0);
  });

  test('同一轮内多个文件按传入顺序一起归属该轮', () => {
    const { byRound, leftover } = groupDeliverablesByRound(rounds, [
      delivery('f1a', '2026-08-01T09:00:01.100'),
      delivery('f2a', '2026-08-01T09:10:01.100'),
      delivery('f1b', '2026-08-01T09:00:09.900'),
    ]);
    expect(leftover).toHaveLength(0);
    expect(byRound.get(rounds[0].key)?.map((f) => f.file_id)).toEqual(['f1a', 'f1b']);
    expect(byRound.get(rounds[1].key)?.map((f) => f.file_id)).toEqual(['f2a']);
  });
});

describe('groupTaskFilesByRound', () => {
  const rounds = splitRounds([
    user('u1', '2026-08-01T09:00:00', '第一问'),
    answer('a1', '2026-08-01T09:00:02'),
    user('u2', '2026-08-01T09:10:00', '追问'),
    answer('a2', '2026-08-01T09:10:02'),
  ]);

  test('任务文件按 created_at 归属轮次(与交付文件同一套逻辑)', () => {
    const { byRound, leftover } = groupTaskFilesByRound(rounds, [
      taskFile('t1', '2026-08-01T09:00:01.500'),
      taskFile('t2', '2026-08-01T09:10:01.500'),
    ]);
    expect(leftover).toHaveLength(0);
    expect(byRound.get(rounds[0].key)?.map((f) => f.file_id)).toEqual(['t1']);
    expect(byRound.get(rounds[1].key)?.map((f) => f.file_id)).toEqual(['t2']);
  });

  test('无 created_at 的任务文件进 leftover', () => {
    const { byRound, leftover } = groupTaskFilesByRound(rounds, [
      taskFile('t1', '2026-08-01T09:00:01.500'),
      taskFile('t3', null),
    ]);
    expect(byRound.get(rounds[0].key)?.map((f) => f.file_id)).toEqual(['t1']);
    expect(leftover.map((f) => f.file_id)).toEqual(['t3']);
  });

  test('交付文件与任务文件在两轮间归属一致(不串轮)', () => {
    const d = groupDeliverablesByRound(rounds, [
      delivery('f2', '2026-08-01T09:10:01.500'),
    ]);
    const t = groupTaskFilesByRound(rounds, [
      taskFile('t2', '2026-08-01T09:10:01.500'),
    ]);
    expect(d.byRound.get(rounds[1].key)?.map((f) => f.file_id)).toEqual(['f2']);
    expect(t.byRound.get(rounds[1].key)?.map((f) => f.file_id)).toEqual(['t2']);
    expect(d.byRound.get(rounds[0].key)).toBeUndefined();
    expect(t.byRound.get(rounds[0].key)).toBeUndefined();
  });
});
