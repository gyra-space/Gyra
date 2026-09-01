import type { IChatDialogueMessageSchema } from '@/types/chat';
import { patchViewByOrder } from '../patch-round-view';

const view = (order: number, context = '', thinking = false): IChatDialogueMessageSchema => ({
  role: 'view',
  context,
  order,
  time_stamp: 0,
  model_name: '',
  thinking,
});

const human = (order: number, context = ''): IChatDialogueMessageSchema => ({
  role: 'human',
  context,
  order,
  time_stamp: 0,
  model_name: '',
});

describe('patchViewByOrder', () => {
  it('复现:第一轮报错不会跑到第二次提问下面(只更新第一轮的 view,保留第二轮消息及其顺序)', () => {
    // 第一轮提问 + 第一轮 view;随后第二轮提问已插入 history
    const history = [
      human(1, '生成一个视频'),
      view(1, '```d-agent-plan\n{}\n```'), // 第一轮的 view 已流式产出内容
      human(2, '再生成一个视频'),
      view(2, ''), // 第二轮 view(thinking)
    ];

    // 第一轮 onError:只就地更新 order=1 的 view,把 d-error 追加进 planning_window
    const next = patchViewByOrder(history, 1, m => ({
      ...m,
      context: m.context + '\n```d-error\n{"content":"请求失败"}\n```',
      thinking: false,
    }));

    // 断言 1:消息总数不变,没丢第二轮
    expect(next).toHaveLength(4);
    // 断言 2:顺序稳定 —— 第一轮 view 仍在第一条 human 之后、第二轮 human 之前
    expect(next.map(m => `${m.role}_${m.order}`)).toEqual(['human_1', 'view_1', 'human_2', 'view_2']);
    // 断言 3:错误确实挂在第一轮 view 上(而不是第二轮的 view)
    expect(next[1].context).toContain('```d-error');
    expect(next[3].context).toBe('');
  });

  it('找不到本轮 view 时原样返回,不做任何改动', () => {
    const history = [human(1, 'q'), view(2, '')];
    expect(patchViewByOrder(history, 1, m => ({ ...m, context: 'x' }))).toBe(history);
  });

  it('只替换目标 view,不影响同 order 的 human 消息', () => {
    const history = [human(1, 'q'), view(1, '')];
    const next = patchViewByOrder(history, 1, m => ({ ...m, context: 'patched', thinking: false }));
    expect(next[0]).toBe(history[0]); // human 引用不变
    expect(next[1].context).toBe('patched');
  });
});
