'use client';

import { useState } from 'react';
import { DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import { Button, Drawer, Input, Modal, Select, Tag, message } from 'antd';
import { apiInterceptors } from '@/client/api';
import { deleteAppCard, updateAppCard, type AppCardItem } from '@/client/api/app-card';
import { AppCardRenderer } from './AppCardRenderer';

const PRESET_ICONS = ['📊', '📈', '📉', '🧭', '🗂️', '⚙️', '🛰️', '🧮', '📋', '🔎'];
const PERMISSION_OPTIONS = [
  { value: 'all', label: '所有人' },
  { value: 'member', label: '空间成员' },
  { value: 'admin', label: '管理员' },
  { value: 'owner', label: '仅所有者' },
];

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
  const [card, setCard] = useState(initialCard);
  const [maintainOpen, setMaintainOpen] = useState(false);
  const [icon, setIcon] = useState(initialCard.icon || '📊');
  const [permissions, setPermissions] = useState<string[]>(initialCard.permissions ?? []);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const openMaintain = () => {
    setIcon(card.icon || '📊');
    setPermissions(card.permissions ?? []);
    setMaintainOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    const [err, res] = await apiInterceptors(
      updateAppCard({ id: card.id, workspace_id: workspaceId, icon, permissions }),
    );
    setSaving(false);
    if (err) {
      message.error((err as Error).message || '保存失败');
      return;
    }
    if (res) setCard((prev) => ({ ...prev, ...res }));
    message.success('已保存');
    setMaintainOpen(false);
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
      </Drawer>
    </div>
  );
}
