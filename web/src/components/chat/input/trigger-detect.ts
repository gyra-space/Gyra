/**
 * 场景空间统一输入协议 —— trigger 检测（`/` `@` `#`）。
 *
 * 纯函数、无 DOM 依赖，便于在 node 环境直接单测
 * (抽法对齐 scene-agent-send-data.ts)。
 *
 * 触发规则(三个 trigger 共用,见设计文档 §2.1):
 *   1. 光标前紧邻字符 c ∈ enabled
 *   2. c 位于文本开头,或其前一个字符是空白(含中文全角空格)
 *   3. c 与光标之间无空白字符(处于「过滤词」状态)
 *
 * 规则 2 保证 `git diff a/b` 里的 `/` 不会唤起菜单;
 * 规则 3 保证过滤词一旦打完(用户输入空格)菜单就关闭。
 */

/** 支持的 trigger 字符。顺序即检测时的优先级无关,取「最靠近光标的那个」。 */
export const TRIGGER_CHARS = ['/', '@', '#'] as const;

export type TriggerChar = (typeof TRIGGER_CHARS)[number];

export interface TriggerState {
  /** 命中的 trigger 字符 */
  char: TriggerChar;
  /** trigger 字符在全文中的下标(含) */
  start: number;
  /** token 结束位置(不含),即调用时传入的光标位置 */
  end: number;
  /** 过滤词:trigger 字符之后、光标之前的文本 */
  query: string;
}

/** 空白字符:ASCII 空白 + 中文全角空格 */
const BLANK_RE = /[\s\u3000]/;

/**
 * 过滤词长度上限。超过则不再视为 trigger —— 用户显然是在打正常文本,
 * 而不是在检索菜单项(对齐 Slack / Notion 的行为)。
 */
const MAX_QUERY_LENGTH = 32;

/**
 * 检测光标处是否处于 trigger 输入状态。
 *
 * @param text   输入框当前全文
 * @param caret  光标位置
 * @param enabled 该输入框启用的 trigger 集合(对话输入框全开,任务指令框只开 `#`)
 */
export function detectTrigger(
  text: string,
  caret: number,
  enabled: readonly TriggerChar[] = TRIGGER_CHARS,
): TriggerState | null {
  if (!text || caret <= 0 || caret > text.length) return null;
  if (!enabled.length) return null;

  const before = text.slice(0, caret);

  // 取「最靠近光标的」那个 trigger 字符,而非第一个
  let start = -1;
  for (const ch of enabled) {
    const idx = before.lastIndexOf(ch);
    if (idx > start) start = idx;
  }
  if (start < 0) return null;

  const char = text[start] as TriggerChar;

  // 前置必须是行首或空白,避免路径/网址里的 `/` 误触发
  if (start > 0 && !BLANK_RE.test(text[start - 1])) return null;

  const query = before.slice(start + 1);
  // 过滤词里出现空白 = 这个 token 已经打完了,菜单应该关闭
  if (BLANK_RE.test(query)) return null;
  if (query.length > MAX_QUERY_LENGTH) return null;

  return { char, start, end: caret, query };
}

/**
 * 删除 trigger token(trigger 字符 + 过滤词),返回新文本。
 *
 * 用于选中菜单项后清理输入:替换既有代码里散落的「行首锚定型」清理正则
 * (形如 replace(斜杠开头的 token, 空串))—— 那些正则只认行首,
 * 在句中触发时会误删前文。
 */
export function stripTrigger(text: string, state: TriggerState): string {
  const after = text.slice(state.end);
  // 顺带吃掉 token 后紧跟的空白:与原有「行首锚定型」清理正则保持同一语义,
  // 否则 '帮我看下 /skill 这个报告' 清理后会留下双空格。
  const trailing = /^[\s\u3000]*/.exec(after)?.[0].length ?? 0;
  return text.slice(0, state.start) + after.slice(trailing);
}
