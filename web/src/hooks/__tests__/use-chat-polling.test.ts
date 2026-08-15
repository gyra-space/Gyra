import { normalizeConversationState } from '../use-chat-polling';

describe('normalizeConversationState', () => {
  test('后端落库的小写状态归一化为大写枚举', () => {
    expect(normalizeConversationState('running')).toBe('RUNNING');
    expect(normalizeConversationState('waiting')).toBe('WAITING');
    expect(normalizeConversationState('retrying')).toBe('RETRYING');
    expect(normalizeConversationState('complete')).toBe('COMPLETE');
    expect(normalizeConversationState('failed')).toBe('FAILED');
    expect(normalizeConversationState('interrupted')).toBe('INTERRUPTED');
  });

  test('大写输入原样保留', () => {
    expect(normalizeConversationState('RUNNING')).toBe('RUNNING');
  });

  test('未知/空状态归一为 UNKNOWN', () => {
    expect(normalizeConversationState(undefined)).toBe('UNKNOWN');
    expect(normalizeConversationState('')).toBe('UNKNOWN');
    expect(normalizeConversationState('some_custom_state')).toBe('UNKNOWN');
  });
});
