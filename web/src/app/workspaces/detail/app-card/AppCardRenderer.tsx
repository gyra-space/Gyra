'use client';

import { useEffect, useRef, useState } from 'react';
import { LoadingOutlined } from '@ant-design/icons';
import { apiInterceptors } from '@/client/api';
import { invokeAppCard, type AppCardItem } from '@/client/api/app-card';
import { APP_CARD_SDK_SOURCE } from './app-card-sdk';
import './app-card.css';

const BASE_CSS = `
  html, body { margin: 0; padding: 0; height: 100%; background: transparent; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; color: #1f2328; }
  #root { min-height: 100%; }
  .gyra-ac-err { padding: 32px; color: #b91c1c; font-size: 13px; line-height: 1.6; }
`;

/** 标准模板辅助函数: 沙箱内始终注入, 保证 el/take/setH 可用, 避免 "xxx is not defined"。 */
const CARD_HELPER_PRELUDE = [
  'function el(id){return document.getElementById(id);}',
  'function take(id,fn){var e=el(id);if(e)fn(e);}',
  'function setH(id,html){take(id,function(e){e.innerHTML=html;});}',
].join('');

/** 沙箱化 iframe 宿主:注入 SDK + 卡片代码,并桥接 postMessage → HTTP invoke。 */
export function AppCardRenderer({
  appCard,
  workspaceId,
  height = 520,
  fill = false,
  invoke,
}: {
  appCard: AppCardItem;
  workspaceId: number;
  height?: number;
  /** 撑满父容器(父需为 flex 容器);默认按固定 px 高度渲染。 */
  fill?: boolean;
  /** 自定 invoke 桥(如匿名分享走 token 端点);默认用登录鉴权的 invokeAppCard。 */
  invoke?: (op: string, params: Record<string, unknown>, queryKey?: string) => Promise<unknown>;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [booting, setBooting] = useState(true);
  const cardRef = useRef(appCard);
  cardRef.current = appCard;
  const invokeRef = useRef(invoke);
  invokeRef.current = invoke;

  const srcDoc = useSrcDoc(appCard, workspaceId);

  useEffect(() => {
    const onMessage = async (e: MessageEvent) => {
      const frame = iframeRef.current;
      if (!frame || e.source !== frame.contentWindow) return;
      const d = e.data;
      if (!d || d.type !== 'gyra-app-card') return;
      const { reqId, op, params, query_key } = d;
      try {
        let data: unknown;
        if (invokeRef.current) {
          data = await invokeRef.current(op, params, query_key);
        } else {
          const [err, res] = await apiInterceptors(invokeAppCard(workspaceId, cardRef.current.id, { op, params, query_key }));
          data = err ? null : res;
        }
        frame.contentWindow?.postMessage(
          { type: 'gyra-app-card-resp', reqId, data, error: data === null ? '请求失败' : null },
          '*',
        );
      } catch (e2) {
        frame.contentWindow?.postMessage({ type: 'gyra-app-card-resp', reqId, data: null, error: (e2 as Error).message }, '*');
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [workspaceId]);

  return (
    <div
      className={`ws-app-card${fill ? ' ws-app-card--fill' : ''}`}
      style={fill ? undefined : { height: `${height}px` }}
    >
      {booting && (
        <div className="ws-app-card__loading">
          <LoadingOutlined spin style={{ fontSize: 18 }} />
          <span>子应用加载中…</span>
        </div>
      )}
      <iframe
        ref={iframeRef}
        srcDoc={srcDoc}
        sandbox="allow-scripts"
        title={appCard.name}
        className={`ws-app-card__frame${loaded ? '' : ' ws-app-card__frame--loading'}`}
        onLoad={() => {
          setLoaded(true);
          setBooting(false);
        }}
      />
    </div>
  );
}

function useSrcDoc(appCard: AppCardItem, workspaceId: number): string {
  const code = appCard.code.replace(/<\/script/gi, '<\\/script');
  const cfg = JSON.stringify({
    workspaceId,
    cardId: appCard.id,
    initialParams: (appCard.config?.default_params as Record<string, unknown>) || {},
  });
  return [
    '<!doctype html><html><head><meta charset="utf-8"><style>',
    BASE_CSS,
    '</style></head><body><div id="root"></div>',
    '<script>window.__GYRA_APP_CARD__=',
    cfg,
    ';</script>',
    '<script>',
    APP_CARD_SDK_SOURCE,
    '</script>',
    '<script>try{(function(){',
    CARD_HELPER_PRELUDE,
    code,
    '})();}catch(e){var r=document.getElementById("root");if(r){r.innerHTML=\'<div class="gyra-ac-err">子应用渲染失败: \'+e.message+\'</div>\';}}</script>',
    '</body></html>',
  ].join('');
}
