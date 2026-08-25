import { parseWorkspaceView } from '../parse-workspace-view';
import { splitRounds, groupDeliverablesByRound } from '../deliverable-rounds';
import type { WorkspaceDeliverableFile, WorkspaceExecutionStep, WorkspaceView } from '../agent-workspace-types';

const step = (overrides: Partial<WorkspaceExecutionStep> & { id: string }): WorkspaceExecutionStep => ({
  type: 'tool_call',
  title: 'A',
  status: 'done',
  ts: null,
  ...overrides,
});

/** 复刻 scene_agent_workspace 的一次「追问」会话:轮1 交付 index.html,轮2 追问(失败的 execute_raw_raw_sql) */
function followUpScenario(): WorkspaceView {
  // 第一轮(vis_final):完整含交付文件
  const round1Chunk = {
    render_name: 'scene_agent_workspace',
    planning: null,
    summary: '看板已生成并交付。',
    execution: [
      step({ id: 'user-r1', type: 'user', title: '我', output: '帮我生成运营看板', ts: '2026-08-01T09:00:00' }),
      step({ id: 'tool-r1-bash', title: 'Bash', action: 'Bash', ts: '2026-08-01T09:00:01' }),
      step({ id: 'tool-r1-deliver', title: 'deliver_file', action: 'deliver_file', ts: '2026-08-01T09:00:05' }),
      step({ id: 'narr-r1', type: 'answer', title: '回复', output: '看板已生成并交付。以下是完整总结：📊 智慧车空间运营数据看板', ts: '2026-08-01T09:00:06' }),
    ],
    deliverable_files: [{
      file_id: 'f1', file_name: 'index.html', file_size: 1024, mime_type: 'text/html', render_type: 'iframe',
      content_url: 'gyra-fs://x/index.html', ts: '2026-08-01T09:00:05',
    }],
    task_files: [
      { file_id: 'f1', file_name: 'index.html', file_type: 'deliverable', file_size: 1024 },
    ],
    panel_view: 'deliverable',
  };
  // 第二轮(追问):只推本轮文件,不带 index.html
  const round2Chunk = {
    render_name: 'scene_agent_workspace',
    planning: null,
    summary: '看板文件已成功交付！',
    execution: [
      step({ id: 'user-r2', type: 'user', title: '我', output: '看板文件交付了吗 我怎么看不到这个文件', ts: '2026-08-01T09:10:00' }),
      step({ id: 'tool-r2-bash', title: 'Bash', action: 'Bash', ts: '2026-08-01T09:10:01' }),
      step({ id: 'tool-r2-fail', title: 'execute_raw_raw_sql', action: 'execute_raw_raw_sql', status: 'failed', ts: '2026-08-01T09:10:02' }),
      step({ id: 'narr-r2', type: 'answer', title: '回复', output: '看板文件已成功交付！让我确认一下文件状态', ts: '2026-08-01T09:10:03' }),
    ],
    deliverable_files: [],
    task_files: [],
    panel_view: 'summary',
  };

  const v1 = parseWorkspaceView(round1Chunk, null);
  return parseWorkspaceView(round2Chunk, v1);
}

describe('scene_agent_workspace 追问轮交付文件归属', () => {
  test('追问轮不丢前轮交付物,且该交付物被归属到产出轮次(非底部 leftover)', () => {
    const view = followUpScenario();
    // 交付文件在前一轮留存
    expect(view.deliverable_files!.map((f) => f.file_id)).toContain('f1');

    const rounds = splitRounds(view.execution);
    const { byRound, leftover } = groupDeliverablesByRound(rounds, view.deliverable_files!);

    // 交付物归属到轮1(产出轮),而不是 leftover
    expect(leftover.map((f) => f.file_id)).not.toContain('f1');
    const ownerRound = rounds.find((r) => (byRound.get(r.key) || []).some((f) => f.file_id === 'f1'));
    expect(ownerRound).toBeDefined();
    expect(ownerRound!.user?.output).toBe('帮我生成运营看板');
    // 轮2(追问)没有交付物
    const round2 = rounds.find((r) => r.user?.output === '看板文件交付了吗 我怎么看不到这个文件');
    expect(round2).toBeDefined();
    expect(byRound.get(round2!.key)?.length ?? 0).toBe(0);
  });
});
