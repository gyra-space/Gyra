'use client';

import { useRequest } from 'ahooks';
import { AppstoreOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiInterceptors } from '@/client/api';
import { listAppCards, type AppCardItem } from '@/client/api/app-card';
import { AppCardRenderer } from './AppCardRenderer';

export interface AppCardsSectionProps {
  workspaceId: number;
  refreshKey?: number;
}

/** 空间主页常驻:由 agent 生成、冻结后可交互的应用卡片。 */
export function AppCardsSection({ workspaceId, refreshKey }: AppCardsSectionProps) {
  const { data: cards = [], refresh } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listAppCards(workspaceId));
    return err ? [] : (res ?? []);
  }, { refreshDeps: [workspaceId, refreshKey] });

  // 没有应用卡片时整块隐藏/折叠, 避免占位
  if (cards.length === 0) {
    return null;
  }

  return (
    <section className="ws-lobby__app-cards">
      <div className="ws-lobby__section-head">
        <span className="ws-lobby__section-icon"><AppstoreOutlined /></span>
        <span className="ws-lobby__section-title">应用卡片</span>
        <span className="ws-lobby__section-count">{cards.length}</span>
        <span className="ws-lobby__section-sub">Agent 生成的常驻子应用 · 每次打开实时取数</span>
        <button type="button" className="ws-app-card__reload" onClick={() => refresh()} aria-label="刷新" title="刷新">
          <ReloadOutlined />
        </button>
      </div>
      <div className="ws-app-card__grid">
        {cards.map((card: AppCardItem) => (
          <div key={card.id} className="ws-app-card__item">
            <div className="ws-app-card__head">
              <span className="ws-app-card__name">{card.name}</span>
              <span className="ws-app-card__status">{card.status}</span>
            </div>
            <AppCardRenderer appCard={card} workspaceId={workspaceId} />
          </div>
        ))}
      </div>
    </section>
  );
}
