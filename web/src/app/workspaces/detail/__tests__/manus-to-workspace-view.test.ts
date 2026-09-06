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

  // 构造带 planning_window(左面板)的 view 消息
  const viewWithPlanning = (order: number, planningWindow: string): ManusViewMessage => ({
    role: 'view',
    order,
    context: JSON.stringify({ running_window: '', planning_window: planningWindow }),
  });

  test('思考:d-thinking 围栏被提取为 thinking 步骤(实时流)', () => {
    const pw = '```d-thinking\n' + JSON.stringify({ uid: 'm2_thinking', markdown: '正在分析方案', type: 'incr', dynamic: true }) + '\n```';
    const ws = buildManusWorkspaceView([human(0, '帮我分析'), viewWithPlanning(1, pw)], null);
    const thinks = ws.execution.filter((s) => s.type === 'thinking');
    expect(thinks).toHaveLength(1);
    expect(thinks[0].output).toContain('正在分析方案');
  });

  test('思考:drsk-content 的正文块(manus_content_stream)不会被误判为思考', () => {
    // V2 工具旁白走 drsk-content(uid=manus_content_stream),不是深度思考,不应生成 thinking 步骤,
    // 避免旁白被误标成「深度思考」并与工具胶囊 narration 行重复。
    const pw = '```drsk-content\n' + JSON.stringify({ uid: 'manus_content_stream', markdown: '我先检查一下日志目录', type: 'incr', dynamic: true }) + '\n```';
    const ws = buildManusWorkspaceView([human(0, '查一下日志'), viewWithPlanning(1, pw)], null);
    const thinks = ws.execution.filter((s) => s.type === 'thinking');
    expect(thinks).toHaveLength(0);
  });

  test('旁白:thought 输出被折进工具步骤 narration,结果正文取非 thought 输出', () => {
    const s = {
      active_step: { id: 't1', type: 'bash', title: 'Bash', status: 'completed', action: 'Bash' },
      outputs: [
        { output_type: 'thought', content: '我先看一下当前目录结构' },
        { output_type: 'text', content: 'file1.txt' },
      ],
    };
    const v1 = view(1, rightPanel({ steps_map: { t1: s } }));
    const ws = buildManusWorkspaceView([human(0, '看看目录'), v1], rightPanel({ steps_map: { t1: s } }) as any);
    const tool = ws.execution.find((e) => e.id === 't1');
    expect(tool).toBeDefined();
    expect(tool?.narration).toBe('我先看一下当前目录结构');
    // 旁白不应被当作结果正文
    expect(tool?.output).toBe('file1.txt');
  });

  test('旁白补全:流式 steps_map 为懒加载(无 outputs)时,从 latestRight 回填 narration', () => {
    // 每条 view 消息的 steps_map 只有元信息(无 outputs)
    const lazyS = { active_step: { id: 't1', type: 'bash', title: 'Bash', status: 'running', action: 'Bash' }, outputs: [] };
    const v1 = view(1, rightPanel({ steps_map: { t1: lazyS } }));
    // 最新 right panel 才带完整 outputs(含 thought 旁白)
    const latest = rightPanel({
      steps_map: {
        t1: {
          active_step: { id: 't1', type: 'bash', title: 'Bash', status: 'completed', action: 'Bash' },
          outputs: [{ output_type: 'thought', content: '我准备执行这条命令了' }, { output_type: 'text', content: '' }],
        },
      },
    });
    const ws = buildManusWorkspaceView([human(0, '跑一下'), v1], latest as any);
    const tool = ws.execution.find((e) => e.id === 't1');
    expect(tool).toBeDefined();
    expect(tool?.narration).toBe('我准备执行这条命令了');
  });
});
