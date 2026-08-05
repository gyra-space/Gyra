'use client';

import { useRef, useState, type ReactNode, type TouchEvent } from 'react';
import { LoadingOutlined, ArrowUpOutlined } from '@ant-design/icons';

/**
 * 移动端下拉刷新:
 * 在滚动容器顶部通过触控下拉触发 onRefresh,满足原生桌面的「下拉刷新」直觉。
 * 自带指示器(下拉箭头 / 刷新 loading),阈值 56px。
 */
export function PullToRefresh({
  onRefresh,
  children,
  className,
}: {
  onRefresh: () => Promise<void> | void;
  children: ReactNode;
  className?: string;
}) {
  const [pull, setPull] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const startY = useRef(0);
  const pulling = useRef(false);

  const onTouchStart = (e: TouchEvent<HTMLDivElement>) => {
    if (e.currentTarget.scrollTop <= 0) {
      startY.current = e.touches[0].screenY;
      pulling.current = true;
    }
  };

  const onTouchMove = (e: TouchEvent<HTMLDivElement>) => {
    if (!pulling.current) return;
    const delta = e.touches[0].screenY - startY.current;
    if (delta > 0) setPull(Math.min(delta * 0.4, 88));
  };

  const onTouchEnd = async () => {
    if (!pulling.current) return;
    pulling.current = false;
    if (pull >= 56 && !refreshing) {
      setRefreshing(true);
      setPull(56);
      try {
        await onRefresh();
      } finally {
        setRefreshing(false);
        setPull(0);
      }
    } else {
      setPull(0);
    }
  };

  return (
    <div
      className={`ms-ptr ${className || ''}`}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onTouchCancel={onTouchEnd}
    >
      <div className={`ms-ptr__indicator${refreshing ? ' ms-ptr__indicator--on' : ''}`} style={{ height: refreshing ? 56 : pull }}>
        {refreshing ? (
          <LoadingOutlined spin />
        ) : (
          <ArrowUpOutlined style={{ transform: `rotate(${(Math.min(pull, 56) / 56) * 180}deg)`, transition: 'transform 0.15s ease' }} />
        )}
        <span className="ms-ptr__text">
          {refreshing ? '刷新中…' : pull >= 56 ? '松开刷新' : '下拉刷新'}
        </span>
      </div>
      {children}
    </div>
  );
}