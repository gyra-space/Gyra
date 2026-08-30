import { detectTrigger, stripTrigger, TRIGGER_CHARS } from '../trigger-detect';

describe('detectTrigger', () => {
  it('行首键入 / 触发', () => {
    expect(detectTrigger('/', 1)).toEqual({ char: '/', start: 0, end: 1, query: '' });
  });

  it('句中 @ 前置空白触发', () => {
    const text = '帮我看下 @';
    expect(detectTrigger(text, text.length)).toEqual({
      char: '@',
      start: 5,
      end: 6,
      query: '',
    });
  });

  it('带上过滤词时返回 query', () => {
    const text = '帮我看下 @数';
    expect(detectTrigger(text, text.length)?.query).toBe('数');
  });

  it('过滤词含空白时不触发(token 已打完)', () => {
    const text = '帮我看下 @数 据';
    // 光标停在「数」之后、空格之前:仍在过滤词中,应触发
    const atEndOfQuery = text.indexOf('数') + 1;
    expect(detectTrigger(text, atEndOfQuery)?.query).toBe('数');
    // 光标越过空格:token 已打完,菜单应关闭
    expect(detectTrigger(text, text.length)).toBeNull();
  });

  it('前置非空白时不触发(路径/网址里的斜杠)', () => {
    expect(detectTrigger('git diff a/b', 12)).toBeNull();
    expect(detectTrigger('a/b@c', 5)).toBeNull();
    expect(detectTrigger('https://x.com', 13)).toBeNull();
  });

  it('多个 trigger 时取最靠近光标的那个', () => {
    // `/` 前置空白合法但已被空格终结,应命中后面的 `#`
    const text = '/skill 报告 #';
    const state = detectTrigger(text, text.length);
    expect(state?.char).toBe('#');
    expect(state?.start).toBe(text.length - 1);
  });

  it('全角空格前置同样触发', () => {
    const text = '帮我看下　@';
    expect(detectTrigger(text, text.length)).not.toBeNull();
  });

  it('空文本 / 光标在 0 不触发', () => {
    expect(detectTrigger('', 0)).toBeNull();
    expect(detectTrigger('abc', 0)).toBeNull();
  });

  it('按 enabled 过滤:任务指令框只开 # 时 / 与 @ 不触发', () => {
    const enabled = ['#'] as const;
    expect(detectTrigger('/', 1, enabled)).toBeNull();
    expect(detectTrigger('@', 1, enabled)).toBeNull();
    expect(detectTrigger('#', 1, enabled)).not.toBeNull();
  });

  it('enabled 为空不触发', () => {
    expect(detectTrigger('/', 1, [])).toBeNull();
  });

  it('过滤词超长(>32)不再视为 trigger', () => {
    const long = 'x'.repeat(32);
    expect(detectTrigger(`#${long}`, long.length + 1)).not.toBeNull();
    const tooLong = 'x'.repeat(33);
    expect(detectTrigger(`#${tooLong}`, tooLong.length + 1)).toBeNull();
  });

  it('光标越界防御', () => {
    expect(detectTrigger('abc', 99)).toBeNull();
    expect(detectTrigger('abc', -1)).toBeNull();
  });

  it('默认全开三个 trigger', () => {
    expect(TRIGGER_CHARS).toEqual(['/', '@', '#']);
    expect(detectTrigger('/', 1)?.char).toBe('/');
    expect(detectTrigger('@', 1)?.char).toBe('@');
    expect(detectTrigger('#', 1)?.char).toBe('#');
  });
});

describe('stripTrigger', () => {
  it('删除行首 token(与原行首锚定正则语义一致,顺带吃掉后续空白)', () => {
    const state = detectTrigger('/skill 剩余文本', 6)!;
    expect(stripTrigger('/skill 剩余文本', state)).toBe('剩余文本');
  });

  it('删除句中 token 且保留前后文(旧的行首正则会误删前文)', () => {
    const text = '帮我看下 /skill 这个报告';
    // 光标停在过滤词末尾(token 尚未被空格终结)
    const caret = text.indexOf('/skill') + '/skill'.length;
    const state = detectTrigger(text, caret)!;
    const next = stripTrigger(text, state);
    expect(next).toContain('帮我看下');
    expect(next).toContain('这个报告');
    // token 后紧随的空白一并吃掉,不留双空格
    expect(next).toBe('帮我看下 这个报告');
  });

  it('删除空过滤词 token', () => {
    const text = '帮我看下 @';
    const state = detectTrigger(text, text.length)!;
    expect(stripTrigger(text, state)).toBe('帮我看下 ');
  });
});
