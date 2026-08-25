import { buildManusWorkspaceView, type ManusViewMessage } from '../manus-to-workspace-view';

const view = (order: number, rightPanel: any): ManusViewMessage => {
  const rw = `\`\`\`manus-right-panel\n${JSON.stringify(rightPanel)}\n\`\`\``;
  return { role: 'view', order, context: JSON.stringify({ running_window: rw, planning_window: '' }) };
};

const human = (order: number, text: string): ManusViewMessage => ({ role: 'human', order, context: text });

const step = (id: string, title: string, status = 'completed', action = title) => ({
  active_step: { id, type: 'bash', title, status, action },
  outputs: [],
});

const rightPanel = (overrides: Record<string, unknown> = {}) => ({
  is_running: false,
  active_step: null,
  outputs: [],
  artifacts: [],
  panel_view: 'execution',
  task_files: [],
  deliverable_files: [],
  ...overrides,
});

describe('buildManusWorkspaceView', () => {
  test('追问轮只推本轮文件时,前轮交付文件按 file_id+ts 保留(不再只看 latestRight)', () => {
    const v1 = view(1, rightPanel({
      panel_view: 'deliverable',
      summary_content: '看板已生成并交付。以下是完整总结：📊 智慧车空间运营数据看板',
      deliverable_files: [{
        file_id: 'f1', file_name: 'dashboard.html', render_type: 'iframe',
        content_url: 'gyra-fs://x/dashboard.html', ts: '2026-08-01T10:00:00',
      }],
      task_files: [{ file_id: 'f1', file_name: 'dashboard.html', file_type: 'deliverable', file_size: 951 }],
      steps_map: { s1: step('s1', 'deliver_file') },
    }));
    // 追问轮(新建 agent conv):后端只推本轮文件,上一轮交付物为空
    const v2 = view(2, rightPanel({
      steps_map: { s2: step('s2', 'Bash'), s3: step('s3', 'execute_raw_raw_sql', 'error') },
    }));
    const latestRight = rightPanel({
      steps_map: { s2: step('s2', 'Bash'), s3: step('s3', 'execute_raw_raw_sql', 'error') },
    });

    const ws = buildManusWorkspaceView(
      [human(0, '帮我生成运营看板'), v1, human(3, '看板文件交付了吗 我怎么看不到这个文件'), v2],
      latestRight as any,
    );

    // 上轮交付文件被保留(即使 latestRight 为空)
    expect(ws.deliverable_files!.map((f) => f.file_id)).toContain('f1');
    expect(ws.deliverable_files!.find((f) => f.file_id === 'f1')?.file_name).toBe('dashboard.html');
    expect(ws.deliverable_files!.find((f) => f.file_id === 'f1')?.ts).toBe('2026-08-01T10:00:00');
    // 任务文件同样保留
    expect(ws.task_files!.some((f) => f.file_id === 'f1')).toBe(true);
    // 回顾历史步骤:交付步骤来自前轮
    const delivered = ws.execution.find((s) => s.action === 'deliver_file');
    expect(delivered).toBeDefined();
    // 失败步骤仍按真实时序出现在执行流中
    const failed = ws.execution.find((s) => s.title === 'execute_raw_raw_sql');
    expect(failed).toBeDefined();
    expect(failed?.status).toBe('failed');
  });

  test('前轮 summary 在追问轮缺失时兜底保留(latestRight 未携带摘要)', () => {
    const v1 = view(1, rightPanel({ summary_content: '看板已生成并交付。' }));
    const v2 = view(2, rightPanel({}));
    const latestRight = rightPanel({});

    const ws = buildManusWorkspaceView([human(0, '第一问'), v1, human(3, '追问'), v2], latestRight as any);
    expect(ws.summary).toBe('看板已生成并交付。');
  });

  test('latestRight 携带摘要时优先使用 latestRight', () => {
    const v1 = view(1, rightPanel({ summary_content: '前轮摘要' }));
    const latestRight = rightPanel({ summary_content: '本轮最新摘要' });

    const ws = buildManusWorkspaceView([human(0, '第一问'), v1], latestRight as any);
    expect(ws.summary).toBe('本轮最新摘要');
  });

  test('同一交付文件多次出现(含不同 ts)按 file_id 去重,只展示一份', () => {
    // 同一 file_id 被重复交付/多次修改(ts 不同),无版本记录 → 只保留一份
    const ws = buildManusWorkspaceView(
      [
        human(0, '问'),
        view(1, rightPanel({ panel_view: 'deliverable', deliverable_files: [{ file_id: 'f1', file_name: 'index.html', render_type: 'iframe', ts: '2026-08-01T10:00:00' }] })),
        view(2, rightPanel({ panel_view: 'deliverable', deliverable_files: [{ file_id: 'f1', file_name: 'index.html', render_type: 'iframe', ts: '2026-08-01T10:00:05' }] })),
      ],
      null,
    );
    expect(ws.deliverable_files!.filter((f) => f.file_id === 'f1')).toHaveLength(1);
  });
});
