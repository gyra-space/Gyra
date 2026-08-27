'use client';

import type { CSSProperties } from 'react';
import { useRequest } from 'ahooks';
import { apiInterceptors } from '@/client/api';
import { listAppCards, type AppCardItem } from '@/client/api/app-card';

/** 每卡独立色相的莫兰迪色板档位数(与 scene-workspace.css 中 __icon--c0~c5 对应) */
const ICON_TINT_COUNT = 6;

/**
 * 简洁模式欢迎态的应用卡片启动区:方形大卡片网格(App 图标 + 名称 + 描述),
 * 点击卡片 → 切换到全屏应用使用态。
 * 与「试试这些」预设问题(轻量文字胶囊)刻意拉开视觉层级:应用是"实体",用大卡片承载。
 * 不承载导入/列表头等运维能力(运维入口仍在运维模式大厅)。
 */
export function SimpleAppCardLauncher({
  workspaceId,
  onOpen,
}: {
  workspaceId: number;
  onOpen: (card: AppCardItem) => void;
}) {
  const { data: cards = [] } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listAppCards(workspaceId));
    return err ? [] : (res ?? []);
  }, { refreshDeps: [workspaceId] });

  if (cards.length === 0) return null;

  return (
    <div className="ws-simple-apps">
      <div className="ws-simple-apps__label">
        <span>应用卡片</span>
        <span className="ws-simple-apps__count">{cards.length}</span>
      </div>
      <div className="ws-simple-apps__row">
        {cards.map((card: AppCardItem, i: number) => (
          <button
            key={card.id}
            type="button"
            className="ws-simple-apps__item"
            style={{ '--i': i } as CSSProperties}
            onClick={() => onOpen(card)}
            aria-label={card.name}
            title={card.description || card.name}
          >
            <span className={`ws-simple-apps__icon ws-simple-apps__icon--c${i % ICON_TINT_COUNT}`}>
              {card.icon || '📊'}
            </span>
            <span className="ws-simple-apps__meta">
              <span className="ws-simple-apps__name">{card.name}</span>
              {card.description && <span className="ws-simple-apps__desc">{card.description}</span>}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
