import { act, renderHook } from '@testing-library/react';
import { useVisibilityPolling } from '../use-visibility-polling';

describe('useVisibilityPolling', () => {
  beforeEach(() => {
    Object.defineProperty(document, 'hidden', { value: false, configurable: true });
  });

  test('页面隐藏暂停轮询,恢复可见立即补刷并重启', () => {
    jest.useFakeTimers();
    const cb = jest.fn();
    renderHook(() => useVisibilityPolling(true, cb, 1000));

    // 启动即调用一次,随后按间隔轮询
    expect(cb).toHaveBeenCalledTimes(1);
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    expect(cb).toHaveBeenCalledTimes(4);

    // 页面切走(隐藏) → 暂停,不再调用
    Object.defineProperty(document, 'hidden', { value: true, configurable: true });
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    const calls = cb.mock.calls.length;
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(cb.mock.calls.length).toBe(calls);

    // 回到可见 → 立即补一次并恢复轮询
    Object.defineProperty(document, 'hidden', { value: false, configurable: true });
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(cb.mock.calls.length).toBe(calls + 1);
    act(() => {
      jest.advanceTimersByTime(2000);
    });
    expect(cb.mock.calls.length).toBe(calls + 3);

    jest.useRealTimers();
  });

  test('窗口失焦暂停,重新聚焦恢复', () => {
    jest.useFakeTimers();
    const cb = jest.fn();
    renderHook(() => useVisibilityPolling(true, cb, 1000));
    expect(cb).toHaveBeenCalledTimes(1);

    act(() => {
      window.dispatchEvent(new Event('blur'));
    });
    const calls = cb.mock.calls.length;
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(cb.mock.calls.length).toBe(calls);

    act(() => {
      window.dispatchEvent(new Event('focus'));
    });
    expect(cb.mock.calls.length).toBe(calls + 1);

    jest.useRealTimers();
  });

  test('enabled=false 时完全不轮询', () => {
    jest.useFakeTimers();
    const cb = jest.fn();
    renderHook(() => useVisibilityPolling(false, cb, 1000));
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(cb).not.toHaveBeenCalled();

    jest.useRealTimers();
  });
});
