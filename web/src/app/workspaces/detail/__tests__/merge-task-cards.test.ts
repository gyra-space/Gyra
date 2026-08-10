import { mergeTaskCards, taskToCreatedStep } from '../use-scene-agent-chat';
import type { WorkspaceView } from '../agent-workspace-types';

const EMPTY_VIEW: WorkspaceView = {
  planning: null,
  execution: [],
  summary: null,
  deliverable_files: [],
  task_files: [],
  panel_view: 'execution',
};

describe('taskToCreatedStep', () => {
  test('running 任务 → running 步骤, 携带 task_id/title/playbook_name', () => {
    const step = taskToCreatedStep(
      { id: 12, title: '沃尔玛运营数据分析', status: 'running', conv_session_id: 'c1', playbook_id: 4, triggered_by: 'manual' },
      [{ playbook_id: 4, playbook_name: '零售分析' }],
    );
    expect(step).toEqual({
      id: 'task-created-12',
      type: 'task_created',
      title: '沃尔玛运营数据分析',
      status: 'running',
      ts: null,
      task_id: 12,
      task_title: '沃尔玛运营数据分析',
      task_status: 'running',
      playbook_name: '零售分析',
      triggered_by: 'manual',
    });
  });

  test('delivered 任务 → done 步骤', () => {
    const step = taskToCreatedStep({ id: 12, status: 'delivered' });
    expect(step?.status).toBe('done');
  });

  test('无 id / 空对象 → null', () => {
    expect(taskToCreatedStep(null)).toBeNull();
    expect(taskToCreatedStep({})).toBeNull();
    expect(taskToCreatedStep({ id: 'x' })).toBeNull();
  });
});

describe('mergeTaskCards', () => {
  test('把绑定到当前会话的任务卡片重注入执行记录', () => {
    const prev: WorkspaceView = {
      ...EMPTY_VIEW,
      execution: [{ id: 'tool-1', type: 'tool_call', title: '查询', status: 'done', ts: null }],
    };
    const tasks = [
      { id: 12, title: '沃尔玛运营数据分析', status: 'running', conv_session_id: 'c1', playbook_id: 4 },
      { id: 99, title: '其他会话任务', status: 'running', conv_session_id: 'c-other' },
    ];
    const next = mergeTaskCards(prev, tasks, 'c1', [{ playbook_id: 4, playbook_name: '零售分析' }]);
    const card = next.execution.find((s) => s.id === 'task-created-12');
    expect(card).toBeDefined();
    expect(card?.task_id).toBe(12);
    expect(card?.status).toBe('running');
    // 保留原步骤 + 仅注入本会话任务
    expect(next.execution.some((s) => s.id === 'tool-1')).toBe(true);
    expect(next.execution.some((s) => s.id === 'task-created-99')).toBe(false);
  });

  test('同 id 卡片去重合并:已存在则更新状态而非重复插入', () => {
    const prev: WorkspaceView = {
      ...EMPTY_VIEW,
      execution: [
        { id: 'task-created-12', type: 'task_created', title: '旧标题', status: 'running', ts: '2026-01-01T00:00:00Z', task_id: 12 },
      ],
    };
    const tasks = [{ id: 12, title: '新标题', status: 'delivered', conv_session_id: 'c1' }];
    const next = mergeTaskCards(prev, tasks, 'c1');
    const cards = next.execution.filter((s) => s.id === 'task-created-12');
    expect(cards).toHaveLength(1);
    expect(cards[0].status).toBe('done');
    expect(cards[0].title).toBe('新标题');
    expect(cards[0].ts).toBe('2026-01-01T00:00:00Z'); // 保留已有 ts
  });

  test('无 convUid 或无任务时原样返回', () => {
    const prev: WorkspaceView = { ...EMPTY_VIEW, execution: [{ id: 'a', type: 'tool_call', title: 'a', status: 'done', ts: null }] };
    expect(mergeTaskCards(prev, undefined, 'c1')).toBe(prev);
    expect(mergeTaskCards(prev, [], 'c1')).toBe(prev);
    expect(mergeTaskCards(prev, [{ id: 1, conv_session_id: 'c1' }], undefined)).toBe(prev);
  });

  test('绑定其他会话的任务不注入', () => {
    const next = mergeTaskCards(EMPTY_VIEW, [{ id: 1, conv_session_id: 'other' }], 'c1');
    expect(next.execution).toHaveLength(0);
  });
});