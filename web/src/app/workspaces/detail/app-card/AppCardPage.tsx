'use client';

import { useState } from 'react';
import { CopyOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import { App, Button, Drawer, Input, Modal, Select, Tag } from 'antd';
import { apiInterceptors } from '@/client/api';
import { deleteAppCard, updateAppCard, type AppCardItem } from '@/client/api/app-card';
import { ee, EVENTS } from '@/utils/event-emitter';
import { AppCardRenderer } from './AppCardRenderer';

const PRESET_ICONS = ['📊', '📈', '📉', '🧭', '🗂️', '⚙️', '🛰️', '🧮', '📋', '🔎'];
const PERMISSION_OPTIONS = [
  { value: 'all', label: '所有人' },
  { value: 'member', label: '空间成员' },
  { value: 'admin', label: '管理员' },
  { value: 'owner', label: '仅所有者' },
];
const SHARE_OPTIONS = [
  { value: 'login', label: '登录后分享', desc: '任何人打开链接, 需已登录且有查看权限' },
  { value: 'anonymous', label: '匿名公开分享', desc: '任何人都能打开, 无需登录' },
];

/** 分享链接(与分享模式对应的独立页 URL)。 */
function buildShareLink(card: AppCardItem): string {
  const base = `${window.location.origin}/app-card-share?card_id=${card.id}`;
  return card.share_mode === 'anonymous' && card.share_token ? `${base}&token=${card.share_token}` : base;
}

/** 场景空间中间栏渲染的全屏应用页:固定 header(应用信息 + 维护入口) + 完整子应用页面。 */
export function AppCardPage({
  card: initialCard,
  workspaceId,
  onDeleted,
}: {
  card: AppCardItem;
  workspaceId: number;
  onDeleted?: () => void;
}) {
  const { message } = App.useApp();
  const [card, setCard] = useState(initialCard);
  const [maintainOpen, setMaintainOpen] = useState(false);
  const [icon, setIcon] = useState(initialCard.icon || '📊');
  const [permissions, setPermissions] = useState<string[]>(initialCard.permissions ?? []);
  const [shareMode, setShareMode] = useState<'login' | 'anonymous'>(
    initialCard.share_mode === 'anonymous' ? 'anonymous' : 'login',
  );
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const openMaintain = () => {
    setIcon(card.icon || '📊');
    setPermissions(card.permissions ?? []);
    setShareMode(card.share_mode === 'anonymous' ? 'anonymous' : 'login');
    setMaintainOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    const [err, res] = await apiInterceptors(
      updateAppCard({ id: card.id, workspace_id: workspaceId, icon, permissions, share_mode: shareMode }),
    );
    setSaving(false);
    if (err) {
      message.error((err as Error).message || '保存失败');
      return;
    }
    if (res) setCard((prev) => ({ ...prev, ...res }));
    message.success('已保存');
    setMaintainOpen(false);
    ee.emit(EVENTS.APP_CARD_CHANGED, { workspaceId });
  };

  const handleCopyShare = async () => {
    let effective = card;
    // 匿名分享首次需生成令牌; 切换模式或需令牌时先保存一次
    const needGenToken = shareMode === 'anonymous' && !effective.share_token;
    const modeChanged = shareMode !== effective.share_mode;
    if (needGenToken || modeChanged) {
      setSaving(true);
      const [err, res] = await apiInterceptors(
        updateAppCard({
          id: card.id,
          workspace_id: workspaceId,
          share_mode: shareMode,
          ...(needGenToken ? { share_token_refresh: true } : {}),
        }),
      );
      setSaving(false);
      if (err || !res) {
        message.error((err as Error)?.message || '生成分享链接失败');
        return;
      }
      effective = res;
      setCard((prev) => ({ ...prev, ...res }));
      if (shareMode !== effective.share_mode) return;
    }
    try {
      await navigator.clipboard.writeText(buildShareLink(effective));
      message.success('分享链接已复制');
    } catch {
      message.error('复制链接失败，请手动复制');
    }
  };

  const handleDelete = () => {
    Modal.confirm({
      title: '删除应用',
      content: `确定删除「${card.name}」吗？删除后无法恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setDeleting(true);
        const [err] = await apiInterceptors(deleteAppCard(card.id, workspaceId));
        setDeleting(false);
        if (err) {
          message.error((err as Error).message || '删除失败');
          return;
        }
        message.success('已删除');
        setMaintainOpen(false);
        ee.emit(EVENTS.APP_CARD_CHANGED, { workspaceId });
        onDeleted?.();
      },
    });
  };

  return (
    <div className="ws-app-card-page">
      <div className="ws-app-card-page__header">
        <span className="ws-app-card-page__icon">{card.icon || '📊'}</span>
        <div className="ws-app-card-page__meta">
          <span className="ws-app-card-page__title">{card.name}</span>
          <span className="ws-app-card-page__desc">{card.description || 'Agent 生成的常驻子应用'}</span>
          <span className="ws-app-card-page__roles">
            {(card.permissions ?? []).map((p) => (
              <Tag key={p} bordered={false} color="blue">{p}</Tag>
            ))}
          </span>
        </div>
        <span className="ws-app-card-page__status">{card.status}</span>
        <span className="ws-app-card-page__owner-hint">{card.is_owner ? '我创建的' : ''}</span>
        {card.can_manage && (
          <Button icon={<SettingOutlined />} size="small" onClick={openMaintain}>
            维护
          </Button>
        )}
      </div>

      <AppCardRenderer appCard={card} workspaceId={workspaceId} height={560} />

      <Drawer
        title="维护应用"
        open={maintainOpen}
        onClose={() => setMaintainOpen(false)}
        width={420}
        destroyOnClose
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <Button danger icon={<DeleteOutlined />} loading={deleting} onClick={handleDelete}>
              删除应用
            </Button>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button onClick={() => setMaintainOpen(false)}>取消</Button>
              <Button type="primary" loading={saving} onClick={handleSave}>
                保存
              </Button>
            </div>
          </div>
        }
      >
        <div className="ws-app-card-page__field">
          <div className="ws-app-card-page__label">应用图标</div>
          <div className="ws-app-card-page__icons">
            {PRESET_ICONS.map((it) => (
              <button
                key={it}
                type="button"
                className={`ws-app-card-page__icon-opt${icon === it ? ' ws-app-card-page__icon-opt--active' : ''}`}
                onClick={() => setIcon(it)}
              >
                {it}
              </button>
            ))}
          </div>
          <Input
            value={icon}
            maxLength={16}
            placeholder="输入 emoji 或图标"
            onChange={(e) => setIcon(e.target.value || '📊')}
          />
        </div>
        <div className="ws-app-card-page__field">
          <div className="ws-app-card-page__label">应用权限</div>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            value={permissions}
            options={PERMISSION_OPTIONS}
            placeholder="选择可访问该应用的角色（不选则仅开发者可见）"
            onChange={(v) => setPermissions(v)}
          />
          <div className="ws-app-card-page__hint">
            默认为空 = 仅开发者可见。勾选后对应角色可见；owner/admin 同时可维护该应用。
          </div>
        </div>
        <div className="ws-app-card-page__field">
          <div className="ws-app-card-page__label">分享设置</div>
          <Select
            style={{ width: '100%' }}
            value={shareMode}
            options={SHARE_OPTIONS}
            onChange={(v) => setShareMode(v as 'login' | 'anonymous')}
          />
          <div className="ws-app-card-page__hint">
            {SHARE_OPTIONS.find((o) => o.value === shareMode)?.desc}
          </div>
          <div style={{ marginTop: 10 }}>
            <Button icon={<CopyOutlined />} loading={saving} onClick={handleCopyShare}>
              生成并复制分享链接
            </Button>
            {shareMode === 'anonymous' && card.share_token && (
              <Tag bordered={false} color="green" style={{ marginLeft: 8 }}>
                已开启匿名分享
              </Tag>
            )}
          </div>
        </div>
      </Drawer>
    </div>
  );
}
