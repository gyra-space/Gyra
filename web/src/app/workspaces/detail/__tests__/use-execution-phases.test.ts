import { buildExecutionPhases } from '../use-execution-phases';
import type { WorkspaceExecutionStep, WorkspacePlanning } from '../agent-workspace-types';

function step(id: string, type: WorkspaceExecutionStep['type'], title: string, action?: string, ts?: string, status: WorkspaceExecutionStep['status'] = 'done'): WorkspaceExecutionStep {
  return { id, type, title, status, action: action ?? null, ts: ts ?? null };
}

describe('buildExecutionPhases', () => {
  test('过滤非胶囊步骤类型(user/answer/task_created 不参与归组)', () => {
    const execution = [
      step('u1', 'user', '我', undefined, '2026-08-21T10:00:00'),
      step('s1', 'tool_call', '搜索资料', 'search', '2026-08-21T10:00:01'),
      step('a1', 'answer', '回复', undefined, '2026-08-21T10:00:02'),
    ];
    const phases = buildExecutionPhases(execution, null);
    expect(phases).toHaveLength(1);
    expect(phases[0].steps.map((s) => s.id)).toEqual(['s1']);
  });

  test('无 todo 时单分组「执行步骤」(零嵌套,不做语义聚类)', () => {
    const execution = [
      step('s1', 'tool_call', '搜索资料', 'search', '2026-08-21T10:00:01'),
      step('s2', 'tool_call', '执行计算', 'python', '2026-08-21T10:00:02'),
      step('s3', 'tool_call', '撰写报告', 'write', '2026-08-21T10:00:03'),
      step('t1', 'thinking', '阶段回复', undefined, '2026-08-21T10:00:04'),
    ];
    const phases = buildExecutionPhases(execution, null);
    expect(phases).toHaveLength(1);
    expect(phases[0].title).toBe('执行步骤');
    expect(phases[0].steps).toHaveLength(4);
  });

  test('单分组状态:含失败步骤 → failed;末步运行中 → running', () => {
    const failed = buildExecutionPhases(
      [
        step('s1', 'tool_call', '搜索资料', 'search', '2026-08-21T10:00:01'),
        step('s2', 'tool_call', '查询库存', 'sql', '2026-08-21T10:00:02', 'failed'),
      ],
      null,
    );
    expect(failed[0].status).toBe('failed');

    const running = buildExecutionPhases(
      [
        step('s1', 'tool_call', '搜索资料', 'search', '2026-08-21T10:00:01'),
        step('s2', 'tool_call', '执行中', 'python', '2026-08-21T10:00:02', 'running'),
      ],
      null,
    );
    expect(running[0].status).toBe('running');
  });

  const planning: WorkspacePlanning = {
    goal: '生成周报',
    steps: [
      { id: 'p1', title: '检索数据', status: 'done' },
      { id: 'p2', title: '分析计算', status: 'running' },
      { id: 'p3', title: '生成交付', status: 'pending' },
    ],
  };

  test('planning 时间线归组:步骤按时间窗落入 todo item', () => {
    const execution = [
      step('s1', 'tool_call', '查询订单', 'sql', '2026-08-21T10:00:01'),
      step('s2', 'tool_call', '查询分销商', 'sql', '2026-08-21T10:00:02'),
      step('s3', 'tool_call', '计算环比', 'python', '2026-08-21T10:00:03'),
    ];
    const timeline = new Map<string, number>([
      ['p1', Date.parse('2026-08-21T10:00:00')],
      ['p2', Date.parse('2026-08-21T10:00:02.500')],
    ]);
    const phases = buildExecutionPhases(execution, planning, timeline);
    expect(phases.map((p) => p.title)).toEqual(['检索数据', '分析计算', '生成交付']);
    expect(phases[0].steps.map((s) => s.id)).toEqual(['s1', 's2']);
    expect(phases[1].steps.map((s) => s.id)).toEqual(['s3']);
    // pending 的 planning item 也列出(空阶段,待开始)
    expect(phases[2].steps).toHaveLength(0);
    expect(phases[2].status).toBe('pending');
  });

  test('时间线首窗口之前的步骤归入「先前执行」(恢复场景历史)', () => {
    const execution = [
      step('s0', 'tool_call', '历史步骤', 'sql', '2026-08-21T09:00:00'),
      step('s1', 'tool_call', '当前步骤', 'sql', '2026-08-21T10:00:01'),
    ];
    const timeline = new Map<string, number>([['p1', Date.parse('2026-08-21T09:59:59')]]);
    const phases = buildExecutionPhases(execution, planning, timeline);
    expect(phases[0].title).toBe('先前执行');
    expect(phases[0].steps.map((s) => s.id)).toEqual(['s0']);
  });

  test('时间线为空时回退到单分组(刷新恢复的已完成会话)', () => {
    const execution = [
      step('s1', 'tool_call', '搜索资料', 'search', '2026-08-21T10:00:01'),
      step('s2', 'tool_call', '执行计算', 'python', '2026-08-21T10:00:02'),
    ];
    const phases = buildExecutionPhases(execution, planning);
    // 无 timeline → 单分组,而非 planning 空阶段
    expect(phases).toHaveLength(1);
    expect(phases[0].title).toBe('执行步骤');
  });
});
