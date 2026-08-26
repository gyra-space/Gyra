'use client';

import { useRequest } from 'ahooks';
import { AppstoreOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiInterceptors } from '@/client/api';
import { listAppCards, type AppCardItem } from '@/client/api/app-card';

export interface AppCardsSectionProps {
  workspaceId: number;
  refreshKey?: number;
  onSelectAppCard?: (card: AppCardItem) => void;
}

/** 空间主页的应用入口:应用图标启动器。点击某张卡片 → 在场景空间打开完整应用页。 */
export function AppCardsSection({ workspaceId, refreshKey, onSelectAppCard }: AppCardsSectionProps) {
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
        <span className="ws-lobby__section-sub">点击图标在场景空间打开完整应用</span>
        <button type="button" className="ws-app-card__reload" onClick={() => refresh()} aria-label="刷新" title="刷新">
          <ReloadOutlined />
        </button>
      </div>
      <div className="ws-app-card__launcher">
        {cards.map((card: AppCardItem) => (
          <button
            key={card.id}
            type="button"
            className="ws-app-card__tile"
            onClick={() => onSelectAppCard?.(card)}
            aria-label={card.name}
            title={card.name}
          >
            <span className="ws-app-card__tile-icon">{card.icon || '📊'}</span>
            <span className="ws-app-card__tile-main">
              <span className="ws-app-card__tile-name">{card.name}</span>
              <span className="ws-app-card__tile-status">{card.status}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
