'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * 页面可见性感知的轮询定时器：
 * - 页面隐藏 / 窗口失焦 → 停止定时器，不再向后端发请求（防后台轮询泄露）
 * - 回到可见 / 聚焦 → 立即补一次刷新并恢复轮询（隐藏期间状态可能已变化）
 *
 * 用法：替代手写 `setInterval` + `useEffect` 清理的轮询。
 *
 *   useVisibilityPolling(hasActiveTask(tasks), refreshLists, 4000);
 *
 * @param enabled  是否允许轮询（如无活跃任务/会话未就绪时为 false）
 * @param callback 每次轮询执行的回调（用 ref 承载，身份变化不重启定时器）
 * @param interval 轮询间隔（毫秒）
 * @returns 当前页面是否可见（可选，供调用方感知）
 */
export function useVisibilityPolling(
  enabled: boolean,
  callback: (() => void) | undefined,
  interval: number,
): boolean {
  // callback 用 ref 承载：调用方常传内联函数或 ahooks 的 refresh，身份每次渲染变化，
  // 若进依赖会重启定时器导致反复立即请求；用 ref 保证定时器只随 enabled/visible 变化启停。
  const callbackRef = useRef<(() => void) | undefined>(callback);
  callbackRef.current = callback;

  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const sync = () => setIsVisible(!document.hidden);
    const handleBlur = () => setIsVisible(false);
    const handleFocus = () => setIsVisible(true);
    sync();
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);
    return () => {
      document.removeEventListener('visibilitychange', sync);
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  useEffect(() => {
    if (!enabled || !isVisible || !callbackRef.current) return;
    // 启动即补一次（含隐藏期间恢复后的立即刷新），再进入定时轮询
    callbackRef.current();
    const timer = setInterval(() => callbackRef.current?.(), interval);
    return () => clearInterval(timer);
  }, [enabled, isVisible, interval]);

  return isVisible;
}

export default useVisibilityPolling;
