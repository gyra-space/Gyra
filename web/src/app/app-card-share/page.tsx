'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Button, Spin } from 'antd';
import { apiInterceptors } from '@/client/api';
import {
  getAppCardShare,
  getAppCardShareLogin,
  invokeAppCardShare,
  invokeAppCardShareLogin,
  type AppCardItem,
} from '@/client/api/app-card';
import { AppCardRenderer } from '../workspaces/detail/app-card/AppCardRenderer';

/**
 * 应用卡片独立分享页。
 * 两种打开方式:
 *   - ?card_id=..            → 登录分享(走 cookie 鉴权, 受卡片权限控制)
 *   - ?card_id=..&token=..   → 匿名公开分享(凭分享令牌, 无需登录)
 */
function ShareContent() {
  const sp = useSearchParams();
  const cardId = sp.get('card_id');
  const token = sp.get('token');
  const anonymous = Boolean(token);

  const [card, setCard] = useState<AppCardItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!cardId) {
      setError('缺少子应用参数（card_id）');
      setLoading(false);
      return;
    }
    const id = Number(cardId);
    if (!id) {
      setError('子应用参数不合法');
      setLoading(false);
      return;
    }
    (async () => {
      setLoading(true);
      setError('');
      let err: unknown;
      let res: AppCardItem | null | undefined;
      if (anonymous) {
        [err, res] = await apiInterceptors(getAppCardShare(id, token as string));
      } else {
        [err, res] = await apiInterceptors(getAppCardShareLogin(id));
      }
      setLoading(false);
      if (err || !res) {
        setError((err as Error)?.message || '无法打开子应用，请确认链接有效，或已登录且有查看权限。');
        return;
      }
      setCard(res);
    })();
  }, [cardId, token, anonymous]);

  const anonymousInvoke = useCallback(
    async (op: string, params: Record<string, unknown>, queryKey?: string): Promise<unknown> => {
      const [err, res] = await apiInterceptors(
        invokeAppCardShare(card!.id, token as string, { op, params, query_key: queryKey }),
      );
      return err ? null : res;
    },
    [card, token],
  );

  const loginInvoke = useCallback(
    async (op: string, params: Record<string, unknown>, queryKey?: string): Promise<unknown> => {
      const [err, res] = await apiInterceptors(
        invokeAppCardShareLogin(card!.id, { op, params, query_key: queryKey }),
      );
      return err ? null : res;
    },
    [card],
  );

  return (
    <div
      style={{
        padding: 16,
        background: '#f7f8fa',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      {card && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '10px 12px',
            background: '#fff',
            border: '1px solid #eef0f3',
            borderRadius: 12,
            marginBottom: 12,
            flexShrink: 0,
          }}
        >
          <span style={{ fontSize: 22 }}>{card.icon || '📊'}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {card.name}
            </div>
            <div style={{ color: '#8c8c8c', fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {card.description || 'Agent 生成的常驻子应用'}
            </div>
          </div>
          <span style={{ fontSize: 12, color: '#389e0d', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6, padding: '1px 8px' }}>
            {anonymous ? '匿名分享' : '登录可见'}
          </span>
        </div>
      )}

      {loading && (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin />
        </div>
      )}
      {!loading && error && (
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#b91c1c',
            fontSize: 13,
            lineHeight: 1.8,
          }}
        >
          {error}
          <div style={{ marginTop: 16 }}>
            {anonymous ? (
              <Button type="primary" onClick={() => { window.location.reload(); }}>
                重试
              </Button>
            ) : (
              <Button type="primary" onClick={() => { window.location.href = '/login'; }}>
                去登录
              </Button>
            )}
          </div>
        </div>
      )}
      {!loading && !error && card && (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <AppCardRenderer
            appCard={card}
            workspaceId={card.workspace_id}
            height={720}
            fill
            invoke={anonymous ? anonymousInvoke : loginInvoke}
          />
        </div>
      )}
    </div>
  );
}

export default function AppCardSharePage() {
  return (
    <Suspense fallback={<div style={{ textAlign: 'center', padding: 80 }}><Spin /></div>}>
      <ShareContent />
    </Suspense>
  );
}