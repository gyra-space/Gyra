'use client';

import { useRequest } from 'ahooks';
import { AppstoreOutlined } from '@ant-design/icons';
import { apiInterceptors } from '@/client/api';
import { listAppCards, type AppCardItem } from '@/client/api/app-card';

/**
 * 简洁模式欢迎态的应用卡片启动条:极简图标启动器,点击卡片 → 切换到全屏应用使用态。
 * 仅展示 icon + 名称,不承载导入/列表头等运维能力(运维入口仍在运维模式大厅)。
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
      <span className="ws-simple-apps__label"><AppstoreOutlined /> 应用卡片</span>
      <div className="ws-simple-apps__row">
        {cards.map((card) => (
          <button
            key={card.id}
            type="button"
            className="ws-simple-apps__item"
            onClick={() => onOpen(card)}
            aria-label={card.name}
            title={card.name}
          >
            <span className="ws-simple-apps__icon">{card.icon || '📊'}</span>
            <span className="ws-simple-apps__name">{card.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}