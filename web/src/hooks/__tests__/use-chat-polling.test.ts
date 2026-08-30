import { normalizeConversationState, useChatPolling } from '../use-chat-polling';
import { queryChatStatus } from '@/client/api/chat';
import { act, renderHook } from '@testing-library/react';

jest.mock('@/client/api/chat', () => ({
  queryChatStatus: jest.fn(),
}));

const queryChatStatusMock = queryChatStatus as jest.Mock;

function makeQueryRes(state: string) {
  return {
    data: {
      data: {
        conv_id: 'c1',
        state,
        is_final: false,
        vis_final: '{}',
        user_answer: '',
        vis_render: 'chat',
      },
    },
  };
}

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

describe('useChatPolling 轮询防泄露', () => {
  beforeEach(() => {
    queryChatStatusMock.mockReset();
  });

  test('页面隐藏暂停轮询,恢复可见后按会话状态决定是否重启;隐藏期间不轮询', async () => {
    jest.useFakeTimers();
    queryChatStatusMock.mockResolvedValue(makeQueryRes('running'));

    const { result, unmount } = renderHook(() =>
      useChatPolling({ conversationId: 'c1', enabled: true, interval: 1000 }),
    );

    // 初始 checkStatus → RUNNING → 启动轮询
    await act(async () => {
      await Promise.resolve();
    });
    expect(queryChatStatusMock).toHaveBeenCalledTimes(1);
    expect(result.current.isPolling).toBe(true);

    // 页面切走(隐藏) → 暂停轮询
    Object.defineProperty(document, 'hidden', { value: true, configurable: true });
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(result.current.isPolling).toBe(false);

    // 隐藏期间不发起任何查询(不泄露)
    const callsBefore = queryChatStatusMock.mock.calls.length;
    await act(async () => {
      jest.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(queryChatStatusMock.mock.calls.length).toBe(callsBefore);

    // 回到页面 → 重新 checkStatus,仍 RUNNING → 重启轮询
    Object.defineProperty(document, 'hidden', { value: false, configurable: true });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
    });
    expect(queryChatStatusMock.mock.calls.length).toBe(callsBefore + 1);
    expect(result.current.isPolling).toBe(true);

    jest.useRealTimers();
    unmount();
  });

  test('页面失焦(blur)暂停轮询,重新聚焦后恢复', async () => {
    jest.useFakeTimers();
    queryChatStatusMock.mockResolvedValue(makeQueryRes('running'));

    const { result, unmount } = renderHook(() =>
      useChatPolling({ conversationId: 'c1', enabled: true, interval: 1000 }),
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.isPolling).toBe(true);

    act(() => {
      window.dispatchEvent(new Event('blur'));
    });
    expect(result.current.isPolling).toBe(false);

    await act(async () => {
      window.dispatchEvent(new Event('focus'));
      await Promise.resolve();
    });
    expect(result.current.isPolling).toBe(true);

    jest.useRealTimers();
    unmount();
  });

  test('pagehide(整页关闭/刷新)时停止轮询并清理 interval', async () => {
    jest.useFakeTimers();
    queryChatStatusMock.mockResolvedValue(makeQueryRes('running'));

    const { result, unmount } = renderHook(() =>
      useChatPolling({ conversationId: 'c1', enabled: true, interval: 1000 }),
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.isPolling).toBe(true);

    act(() => {
      window.dispatchEvent(new Event('pagehide'));
    });
    expect(result.current.isPolling).toBe(false);

    // interval 已清理,不再发起查询
    const callsBefore = queryChatStatusMock.mock.calls.length;
    await act(async () => {
      jest.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(queryChatStatusMock.mock.calls.length).toBe(callsBefore);

    jest.useRealTimers();
    unmount();
  });

  test('回到无会话态(conversationId=null / 欢迎态)时复位残留 RUNNING 状态', async () => {
    jest.useFakeTimers();
    queryChatStatusMock.mockResolvedValue(makeQueryRes('running'));

    const { result, rerender, unmount } = renderHook(
      ({ conversationId, enabled }: { conversationId: string | null; enabled: boolean }) =>
        useChatPolling({ conversationId, enabled, interval: 1000 }),
      { initialProps: { conversationId: 'c1', enabled: true } },
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.state).toBe('RUNNING');

    // 点击「新任务」回到欢迎态:conversationId/enabled 归零,残留 RUNNING 必须被复位为 UNKNOWN,
    // 否则外层会把它误判为活跃执行,新任务发送被当作上一会话的补充输入投递到旧队列。
    rerender({ conversationId: null, enabled: false });
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.state).toBe('UNKNOWN');
    expect(result.current.isPolling).toBe(false);

    jest.useRealTimers();
    unmount();
  });

  test('对话到达终态(COMPLETE)时停止轮询', async () => {
    jest.useFakeTimers();
    queryChatStatusMock.mockResolvedValue(makeQueryRes('running'));

    const { result, unmount } = renderHook(() =>
      useChatPolling({ conversationId: 'c1', enabled: true, interval: 1000 }),
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.isPolling).toBe(true);

    // 下一次轮询返回终态 → 停止轮询
    queryChatStatusMock.mockResolvedValue(makeQueryRes('complete'));
    await act(async () => {
      jest.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(result.current.isPolling).toBe(false);

    jest.useRealTimers();
    unmount();
  });
});
