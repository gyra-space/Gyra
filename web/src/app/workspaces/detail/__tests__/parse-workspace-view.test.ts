import { parseWorkspaceView } from '../parse-workspace-view';
import type { WorkspaceView } from '../agent-workspace-types';

describe('parseWorkspaceView', () => {
  test('首次 chunk 建立 execution', () => {
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [{ id: 's1', type: 'tool_call', title: '搜索', status: 'running', action: 'search' }],
      summary: null,
    };
    const view = parseWorkspaceView(chunk, null);
    expect(view.execution).toHaveLength(1);
    expect(view.execution[0].id).toBe('s1');
    expect(view.execution[0].status).toBe('running');
  });

  test('同 id 步骤去重更新状态', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [{ id: 's1', type: 'tool_call', title: '搜索', status: 'running', action: 'search' }],
      summary: null,
    };
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [{ id: 's1', type: 'tool_call', title: '搜索', status: 'done', action: 'search', output: 'OK' }],
      summary: '完成',
    };
    const view = parseWorkspaceView(chunk, prev);
    expect(view.execution).toHaveLength(1);
    expect(view.execution[0].status).toBe('done');
    expect(view.execution[0].output).toBe('OK');
    expect(view.summary).toBe('完成');
  });

  test('新 id 步骤追加', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [{ id: 's1', type: 'tool_call', title: 'A', status: 'done' }],
      summary: null,
    };
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: { goal: 'G', steps: [{ id: 'p1', title: 'P1', status: 'done' }] },
      execution: [{ id: 's1', type: 'tool_call', title: 'A', status: 'done' }, { id: 's2', type: 'artifact', title: 'B', status: 'running' }],
      summary: null,
    };
    const view = parseWorkspaceView(chunk, prev);
    expect(view.execution.map(e => e.id)).toEqual(['s1', 's2']);
    expect(view.planning?.goal).toBe('G');
  });

  test('非法 payload 返回 prev', () => {
    const prev: WorkspaceView = { planning: null, execution: [], summary: null };
    expect(parseWorkspaceView(null, prev)).toBe(prev);
    expect(parseWorkspaceView({ execution: 'no' }, prev)).toBe(prev);
  });

  test('混合时区 ts 按真实时序排序(UTC Z vs 本地 naive)', () => {
    // 服务端步骤是本地 naive ISO,乐观用户步骤是 UTC 带 Z。
    // 本地 +08: 服务端 22:00 naive == UTC 14:00Z;乐观 14:05Z 应排在它后面。
    const prev: WorkspaceView = {
      planning: null,
      execution: [
        { id: 'user1', type: 'user', title: '我', status: 'done', output: 'q1', ts: '2026-07-25T22:00:00' },
        { id: 'tool1', type: 'tool_call', title: 'A', status: 'done', ts: '2026-07-25T22:01:03.123456' },
      ],
      summary: null,
    };
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [
        { id: 'user2-opt', type: 'user', title: '我', status: 'done', output: 'q2', ts: '2026-07-25T14:05:00.000Z' },
      ],
      summary: null,
    };
    const view = parseWorkspaceView(chunk, prev);
    expect(view.execution.map(e => e.id)).toEqual(['user1', 'tool1', 'user2-opt']);
  });

  test('task_created 步骤被正确解析并保留 task 字段', () => {
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [{
        id: 'task-created-42',
        type: 'task_created',
        title: '营收分析任务',
        status: 'running',
        task_id: 42,
        task_title: '营收分析任务',
        task_status: 'running',
        playbook_name: '营收分析',
        triggered_by: 'manual',
      }],
      summary: null,
    };
    const view = parseWorkspaceView(chunk, null);
    expect(view.execution).toHaveLength(1);
    expect(view.execution[0].type).toBe('task_created');
    expect(view.execution[0].task_id).toBe(42);
    expect(view.execution[0].playbook_name).toBe('营收分析');
    expect(view.execution[0].triggered_by).toBe('manual');
  });

  test('客户端注入的 task_created 步骤在 vis_final 轮询合并后保留', () => {
    // 模拟:客户端从 task_created 事件注入了 task-created-42 步骤,
    // 随后 vis_final 轮询返回了不含该步骤的 execution 列表。
    // 步骤应被保留(作为 leftover prev step)。
    const prev: WorkspaceView = {
      planning: null,
      execution: [
        { id: 'user1', type: 'user', title: '我', status: 'done', output: '帮我分析营收' },
        { id: 'task-created-42', type: 'task_created', title: '营收分析', status: 'running', task_id: 42, task_status: 'running', playbook_name: '营收分析', triggered_by: 'manual' },
      ],
      summary: null,
    };
    // vis_final 只返回 user 步骤,不包含 task_created 步骤
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [
        { id: 'user1', type: 'user', title: '我', status: 'done', output: '帮我分析营收' },
      ],
      summary: null,
    };
    const view = parseWorkspaceView(chunk, prev);
    const taskStep = view.execution.find(e => e.id === 'task-created-42');
    expect(taskStep).toBeDefined();
    expect(taskStep?.type).toBe('task_created');
    expect(taskStep?.task_id).toBe(42);
  });

  test('answer 步骤被解析(type=answer,承载 Agent 最终回复)', () => {
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [{ id: 'answer-m1', type: 'answer', title: '回复', status: 'done', output: '最终回复内容' }],
      summary: '最终回复内容',
    };
    const view = parseWorkspaceView(chunk, null);
    expect(view.execution).toHaveLength(1);
    expect(view.execution[0].type).toBe('answer');
    expect(view.execution[0].output).toBe('最终回复内容');
    expect(view.summary).toBe('最终回复内容');
  });

  test('跨轮 answer step 保留:新轮 chunk 不含前轮 answer 时 leftover 保留 + ts 交错排序', () => {
    // 后端每轮独立 conv,vis_final 只返最新轮。前端靠 leftover 保留前轮 answer step,
    // 避免历史回复丢失(summary 单值会被新轮覆盖,但 answer step 留在 execution)。
    const prev: WorkspaceView = {
      planning: null,
      execution: [
        { id: 'user-r1', type: 'user', title: '我', status: 'done', output: '问题1', ts: '2026-08-12T10:00:00' },
        { id: 'answer-r1', type: 'answer', title: '回复', status: 'done', output: '回复1', ts: '2026-08-12T10:00:05' },
      ],
      summary: '回复1',
    };
    const chunk = {
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [
        { id: 'user-r2', type: 'user', title: '我', status: 'done', output: '问题2', ts: '2026-08-12T10:01:00' },
        { id: 'answer-r2', type: 'answer', title: '回复', status: 'done', output: '回复2', ts: '2026-08-12T10:01:05' },
      ],
      summary: '回复2',
    };
    const view = parseWorkspaceView(chunk, prev);
    expect(view.execution.map(e => e.id)).toEqual(['user-r1', 'answer-r1', 'user-r2', 'answer-r2']);
    expect(view.summary).toBe('回复2'); // summary 被新轮覆盖,但 answer-r1 仍保留在 execution
  });
});

describe('subagents(异步子 agent 任务看板)', () => {
  const baseChunk = { render_name: 'scene_agent_workspace', planning: null, execution: [], summary: null };

  test('subagents 解析与规范化', () => {
    const view = parseWorkspaceView({
      ...baseChunk,
      subagents: [
        { sub_conv_id: 'sub_1', agent_name: 'multimedia', task: '生成视频', status: 'running', mode: 'async' },
        { sub_conv_id: 'sub_2', agent_name: 'expert', task: '分析数据', status: 'done', authorization: '确认执行?' },
      ],
    }, null);
    expect(view.subagents).toHaveLength(2);
    expect(view.subagents![0].status).toBe('running');
    expect(view.subagents![0].agent_name).toBe('multimedia');
    expect(view.subagents![1].status).toBe('done');
    expect(view.subagents![1].authorization).toBe('确认执行?');
  });

  test('未知状态回落 running;缺 sub_conv_id 的条目被丢弃', () => {
    const view = parseWorkspaceView({
      ...baseChunk,
      subagents: [
        { sub_conv_id: 'sub_1', status: 'hologram' },
        { status: 'running' },
      ],
    }, null);
    expect(view.subagents).toHaveLength(1);
    expect(view.subagents![0].status).toBe('running');
  });

  test('chunk 未携带 subagents 时保留 prev', () => {
    const prev = parseWorkspaceView({
      ...baseChunk,
      subagents: [{ sub_conv_id: 'sub_1', status: 'running' }],
    }, null);
    const view = parseWorkspaceView({
      ...baseChunk,
      execution: [{ id: 's1', type: 'tool_call', title: 'A', status: 'done' }],
    }, prev);
    expect(view.subagents).toHaveLength(1);
    expect(view.subagents![0].status).toBe('running');
  });
});

describe('lobby_exhibits(大厅通用内容协议)', () => {
  const baseChunk = { render_name: 'scene_agent_workspace', planning: null, execution: [], summary: null };

  test('lobby_exhibits 解析与规范化', () => {
    const view = parseWorkspaceView({
      ...baseChunk,
      lobby_exhibits: [{
        exhibit_id: 'file_f1',
        kind: 'table',
        title: 'report.csv',
        source: { url: 'gyra-fs://x/report.csv', mime_type: 'text/csv', file_size: 1024 },
        provenance: { step_id: 'tool-1' },
        actions: ['preview', 'download'],
      }],
    }, null);
    expect(view.lobby_exhibits).toHaveLength(1);
    const ex = view.lobby_exhibits![0];
    expect(ex.kind).toBe('table');
    expect(ex.source.url).toBe('gyra-fs://x/report.csv');
    expect(ex.provenance?.step_id).toBe('tool-1');
  });

  test('未知 kind 回落 file;缺 exhibit_id/title 的条目被丢弃', () => {
    const view = parseWorkspaceView({
      ...baseChunk,
      lobby_exhibits: [
        { exhibit_id: 'a', kind: 'hologram', title: 'X' },
        { kind: 'image', title: 'no id' },
        { exhibit_id: 'b' },
      ],
    }, null);
    expect(view.lobby_exhibits).toHaveLength(1);
    expect(view.lobby_exhibits![0].kind).toBe('file');
  });

  test('跨 chunk 按 exhibit_id 幂等合并(同 ID 覆盖,旧条目保留)', () => {
    const prev = parseWorkspaceView({
      ...baseChunk,
      lobby_exhibits: [
        { exhibit_id: 'f1', kind: 'table', title: 'a.csv' },
        { exhibit_id: 'f2', kind: 'image', title: 'b.png' },
      ],
    }, null);
    const view = parseWorkspaceView({
      ...baseChunk,
      lobby_exhibits: [{ exhibit_id: 'f1', kind: 'table', title: 'a-v2.csv' }],
    }, prev);
    expect(view.lobby_exhibits).toHaveLength(2);
    expect(view.lobby_exhibits!.find(e => e.exhibit_id === 'f1')?.title).toBe('a-v2.csv');
    expect(view.lobby_exhibits!.some(e => e.exhibit_id === 'f2')).toBe(true);
  });

  test('chunk 未携带 lobby_exhibits 时保留 prev', () => {
    const prev = parseWorkspaceView({
      ...baseChunk,
      lobby_exhibits: [{ exhibit_id: 'f1', kind: 'pdf', title: 'doc.pdf' }],
    }, null);
    const view = parseWorkspaceView({
      ...baseChunk,
      execution: [{ id: 's1', type: 'tool_call', title: 'A', status: 'done' }],
    }, prev);
    expect(view.lobby_exhibits).toHaveLength(1);
    expect(view.lobby_exhibits![0].kind).toBe('pdf');
  });

  test('execution 步骤携带 exhibit 被规范化(点击步骤 → 大厅展示对应内容)', () => {
    const view = parseWorkspaceView({
      ...baseChunk,
      execution: [{
        id: 's1', type: 'tool_call', title: '生成报表', status: 'done',
        exhibit: { exhibit_id: 'file_f1', kind: 'slides', title: 'deck.pptx', source: { url: 'u' } },
      }],
    }, null);
    expect(view.execution[0].exhibit?.exhibit_id).toBe('file_f1');
    expect(view.execution[0].exhibit?.kind).toBe('slides');
  });
});

describe('deliverable_files / task_files(追问轮不丢前轮交付物)', () => {
  const baseChunk = { render_name: 'scene_agent_workspace', planning: null, execution: [], summary: null };

  const file = (file_id: string, file_name: string, render_type = 'pdf') => ({
    file_id, file_name, file_size: 1024, mime_type: 'application/pdf', render_type,
  });

  test('新轮 chunk 只含本轮文件时,前轮交付文件按 file_id 合并保留', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [],
      summary: null,
      deliverable_files: [file('f1', 'report.pdf'), file('f2', 'chart.png', 'image')],
    };
    // 追问轮(新 agent conv)后端只推送本轮文件 f3
    const view = parseWorkspaceView({
      ...baseChunk,
      deliverable_files: [file('f3', 'deck.pptx', 'slides')],
    }, prev);
    expect(view.deliverable_files!.map(f => f.file_id)).toEqual(['f3', 'f1', 'f2']);
  });

  test('新轮 chunk 交付文件为空数组时不覆盖前轮交付物', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [],
      summary: null,
      deliverable_files: [file('f1', 'report.pdf')],
    };
    const view = parseWorkspaceView({ ...baseChunk, deliverable_files: [] }, prev);
    expect(view.deliverable_files!.map(f => f.file_id)).toEqual(['f1']);
  });

  test('同 file_id 重新交付时以新值更新(去重)', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [],
      summary: null,
      deliverable_files: [file('f1', 'report.pdf')],
    };
    const view = parseWorkspaceView({
      ...baseChunk,
      deliverable_files: [file('f1', 'report-v2.pdf')],
    }, prev);
    expect(view.deliverable_files).toHaveLength(1);
    expect(view.deliverable_files![0].file_name).toBe('report-v2.pdf');
  });

  test('task_files 同样按 file_id 合并保留(跨轮)', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [],
      summary: null,
      task_files: [file('t1', 'a.txt', 'text')],
    };
    const view = parseWorkspaceView({
      ...baseChunk,
      task_files: [file('t2', 'b.log', 'text')],
    }, prev);
    expect(view.task_files!.map(f => f.file_id)).toEqual(['t2', 't1']);
  });

  test('chunk 未携带 deliverable_files 时保留 prev', () => {
    const prev: WorkspaceView = {
      planning: null,
      execution: [],
      summary: null,
      deliverable_files: [file('f1', 'report.pdf')],
    };
    const view = parseWorkspaceView({
      ...baseChunk,
      execution: [{ id: 's1', type: 'tool_call', title: 'A', status: 'done' }],
    }, prev);
    expect(view.deliverable_files!.map(f => f.file_id)).toEqual(['f1']);
  });
});