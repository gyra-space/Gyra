import { buildMemoryInjectionSteps } from '../use-scene-agent-chat';

describe('buildMemoryInjectionSteps', () => {
  test('按 kind 生成稳定 id 与标题', () => {
    const steps = buildMemoryInjectionSteps([
      { kind: 'agents_md', title: 'AGENTS.md注入上下文', chars: 120 },
      { kind: 'user_md', title: 'user.md注入上下文', chars: 80 },
    ]);
    expect(steps.map((s) => s.id)).toEqual(['mem-inject-agents_md', 'mem-inject-user_md']);
    expect(steps.map((s) => s.title)).toEqual(['AGENTS.md注入上下文', 'user.md注入上下文']);
    expect(steps.every((s) => s.type === 'memory_loaded' && s.status === 'done')).toBe(true);
  });

  test('同 kind 去重(每轮重复注入只保留一份)', () => {
    const blocks = [
      { kind: 'agents_md', title: 'AGENTS.md注入上下文' },
      { kind: 'agents_md', title: 'AGENTS.md注入上下文' },
    ];
    expect(buildMemoryInjectionSteps(blocks)).toHaveLength(1);
    // 与已有步骤(刷新重注入场景)去重
    expect(buildMemoryInjectionSteps(blocks, ['mem-inject-agents_md'])).toHaveLength(0);
  });

  test('空/非法 blocks 返回空数组', () => {
    expect(buildMemoryInjectionSteps(undefined)).toEqual([]);
    expect(buildMemoryInjectionSteps([])).toEqual([]);
    expect(buildMemoryInjectionSteps([null as any, 'x' as any])).toEqual([]);
  });

  test('缺 kind/title 时回退默认值', () => {
    const steps = buildMemoryInjectionSteps([{ title: 'AGENTS.md注入上下文' }]);
    expect(steps).toHaveLength(1);
    expect(steps[0].id).toBe('mem-inject-memory');
    expect(steps[0].title).toBe('AGENTS.md注入上下文');
  });
});
