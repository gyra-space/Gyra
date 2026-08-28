/**
 * 交付文件 / 任务文件的「按轮次内联」渲染验证。
 *
 * @antv/gpt-vis 依赖链含纯 ESM 包(react-syntax-highlighter),在 jest 下无法
 * 直接加载(既有 scene-workspace-shell 套件同样因此失败),此处 mock 掉:本用例
 * 只关心文件卡片挂在哪个轮次下,markdown 渲染不是被测行为。
 */
jest.mock('@antv/gpt-vis', () => ({
  GPTVis: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

// markdown 配置拉起 rehype-katex / remark 生态(纯 ESM),同样无法在 jest 下加载
jest.mock('@/components/chat/chat-content-components/config', () => ({
  __esModule: true,
  default: {},
  markdownPlugins: {},
  preprocessLaTeX: (s: string) => s,
}));

import { fireEvent, render } from '@testing-library/react';
import { AgentWorkspaceRenderer } from '../agent-workspace-renderer';
import type {
  WorkspaceDeliverableFile,
  WorkspaceExecutionStep,
  WorkspaceTaskFile,
  WorkspaceView,
} from '../agent-workspace-types';

const user = (id: string, ts: string, output: string): WorkspaceExecutionStep => ({
  id, type: 'user', title: '我', status: 'done', output, ts,
});
const answer = (id: string, ts: string, output: string): WorkspaceExecutionStep => ({
  id, type: 'answer', title: '回复', status: 'done', output, ts,
});
const delivery = (id: string, ts: string | null): WorkspaceDeliverableFile => ({
  file_id: id, file_name: `${id}.html`, file_size: 1, render_type: 'iframe', ts,
});
const taskFile = (id: string, createdAt: string | null): WorkspaceTaskFile => ({
  file_id: id,
  file_name: `${id}.csv`,
  file_type: 'tool_output',
  file_size: 1,
  created_at: createdAt ?? undefined,
});

const view = (overrides: Partial<WorkspaceView>): WorkspaceView => ({
  planning: null,
  execution: [],
  summary: null,
  panel_view: 'execution',
  ...overrides,
});

/** 两轮对话:第一问产 f1/t1,追问产 f2/t2 */
const twoRounds: WorkspaceView = view({
  execution: [
    user('u1', '2026-08-01T09:00:00', '第一问'),
    answer('a1', '2026-08-01T09:00:02', '第一份回答'),
    user('u2', '2026-08-01T09:10:00', '追问'),
    answer('a2', '2026-08-01T09:10:02', '第二份回答'),
  ],
  deliverable_files: [
    delivery('f1', '2026-08-01T09:00:01.500'),
    delivery('f2', '2026-08-01T09:10:01.500'),
  ],
  task_files: [
    taskFile('t1', '2026-08-01T09:00:01.600'),
    taskFile('t2', '2026-08-01T09:10:01.600'),
  ],
});

/** 轮次容器顺序:即 feed 的 DOM 顺序,用于断言「文件跟在哪一轮后面」 */
function roundContainers(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll('.ws-agent-renderer > *'));
}

/** 把 feed 内容按「轮次片段」切分:每个 user 气泡开启一个新片段 */
function splitByRound(container: HTMLElement): string[][] {
  const chunks: string[][] = [];
  for (const el of roundContainers(container)) {
    const isUserBubble = el.querySelector('.ws-step-user__bubble') !== null;
    if (isUserBubble || chunks.length === 0) chunks.push([]);
    chunks[chunks.length - 1].push(el.textContent || '');
  }
  return chunks;
}

describe('AgentWorkspaceRenderer 文件按轮次内联', () => {
  test('每轮的交付文件跟在该轮回复后面,而不是全部堆在 feed 底部', () => {
    const { container } = render(
      <AgentWorkspaceRenderer view={twoRounds} onDeliverableClick={() => {}} />,
    );
    const chunks = splitByRound(container);

    // 两轮对话 → 两个片段(轮次头部 + 回答 + 本轮文件)
    expect(chunks).toHaveLength(2);

    // 第一轮片段含 f1 但不含 f2
    expect(chunks[0].join('\n')).toContain('f1.html');
    expect(chunks[0].join('\n')).not.toContain('f2.html');
    // 第二轮片段含 f2 但不含 f1
    expect(chunks[1].join('\n')).toContain('f2.html');
    expect(chunks[1].join('\n')).not.toContain('f1.html');
  });

  test('任务文件同样按轮次归属(不再是一条全局折叠条)', () => {
    const { container } = render(
      <AgentWorkspaceRenderer view={twoRounds} onDeliverableClick={() => {}} />,
    );
    // 每轮各有一条折叠条(2 轮 → 2 条),而非会话底部一条汇总
    const toggles = container.querySelectorAll('.ws-taskfiles__toggle');
    expect(toggles).toHaveLength(2);

    // 折叠条默认收起,展开后各自只列本轮的文件
    fireEvent.click(toggles[0]);
    fireEvent.click(toggles[1]);
    const chunks = splitByRound(container);
    expect(chunks[0].join('\n')).toContain('t1.csv');
    expect(chunks[0].join('\n')).not.toContain('t2.csv');
    expect(chunks[1].join('\n')).toContain('t2.csv');
    expect(chunks[1].join('\n')).not.toContain('t1.csv');
  });

  test('单轮对话时交付文件只有一个块,不存在重复的会话级汇总块', () => {
    const single = view({
      execution: [
        user('u1', '2026-08-01T09:00:00', '第一问'),
        answer('a1', '2026-08-01T09:00:02', '回答'),
      ],
      deliverable_files: [delivery('f1', '2026-08-01T09:00:01.500')],
    });
    const { container } = render(
      <AgentWorkspaceRenderer view={single} onDeliverableClick={() => {}} />,
    );
    // 「交付文件」标题只出现一次:不再既有轮内联块又有底部全局块
    const heads = container.querySelectorAll('.ws-agent-renderer__deliverables-head');
    expect(heads).toHaveLength(1);
    expect(container.textContent).toContain('f1.html');
  });

  test('无时间戳的文件无法归属轮次,仍在 feed 底部兜底展示(不丢文件)', () => {
    const noTs = view({
      execution: [
        user('u1', '2026-08-01T09:00:00', '第一问'),
        answer('a1', '2026-08-01T09:00:02', '回答'),
      ],
      deliverable_files: [delivery('fx', null)],
    });
    const { container } = render(
      <AgentWorkspaceRenderer view={noTs} onDeliverableClick={() => {}} />,
    );
    expect(container.textContent).toContain('fx.html');
    expect(container.querySelectorAll('.ws-agent-renderer__deliverables-head')).toHaveLength(1);
  });

  test('没有交付文件时不渲染交付文件块', () => {
    const none = view({
      execution: [user('u1', '2026-08-01T09:00:00', '第一问')],
    });
    const { container } = render(
      <AgentWorkspaceRenderer view={none} onDeliverableClick={() => {}} />,
    );
    expect(container.querySelectorAll('.ws-agent-renderer__deliverables')).toHaveLength(0);
  });
});
