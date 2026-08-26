'use client';

import { type AppCardItem } from '@/client/api/app-card';
import { AppCardRenderer } from './AppCardRenderer';

/** 场景空间中间栏渲染的全屏应用页:在大 iframe 中渲染 agent 生成的复杂子应用。 */
export function AppCardPage({ card, workspaceId }: { card: AppCardItem; workspaceId: number }) {
  return (
    <div className="ws-app-card-page">
      <AppCardRenderer appCard={card} workspaceId={workspaceId} height={560} />
    </div>
  );
}
