'use client';

import { useRef, useState } from 'react';
import { useRequest } from 'ahooks';
import {
  AppstoreOutlined,
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { Button, Input, Modal, message } from 'antd';
import { apiInterceptors } from '@/client/api';
import { createAppCard, listAppCards, type AppCardItem } from '@/client/api/app-card';
import { extractAppCardPayload, isAppCardPayloadText } from './AppCardImportButton';
import './app-card.css';

export interface AppCardsSectionProps {
  workspaceId: number;
  refreshKey?: number;
  onSelectAppCard?: (card: AppCardItem) => void;
}

/**
 * 简易解析:返回可编辑的 name(供导入弹窗预填),非法输入返回 ''。
 */
function nameFromPayload(rawText: string): string {
  if (!isAppCardPayloadText(rawText)) return '';
  return extractAppCardPayload(rawText, 0)?.name ?? '';
}

/** 手动导入 Agent 生成的 App Card(json payload 落库)。 */
function AppCardImportModal({
  open,
  workspaceId,
  onClose,
  onImported,
}: {
  open: boolean;
  workspaceId: number;
  onClose: () => void;
  onImported: () => void;
}) {
  const [rawText, setRawText] = useState('');
  const [name, setName] = useState('');
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setRawText('');
    setName('');
  };

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = String(e.target?.result ?? '');
      setRawText(text);
      setTextName(text);
    };
    reader.readAsText(file);
  };

  const setTextName = (text: string) => {
    const n = nameFromPayload(text);
    if (n) setName(n);
  };

  const handleSubmit = async () => {
    const payload = extractAppCardPayload(rawText, workspaceId);
    if (!payload) {
      message.error('内容不是有效的 App Card payload(需含 meta.schema_name 签名, 或 name 与 code 字段的 JSON)');
      return;
    }
    payload.name = name || payload.name;
    setImporting(true);
    const [err] = await apiInterceptors(createAppCard(payload));
    setImporting(false);
    if (err) {
      message.error((err as Error).message || '导入失败');
      return;
    }
    message.success(`已导入「${payload.name}」`);
    reset();
    onImported();
    onClose();
  };

  return (
    <Modal
      title="手动导入子应用 (App Card)"
      open={open}
      onCancel={onClose}
      width={640}
      okText="导入落库"
      cancelText="取消"
      confirmLoading={importing}
      onOk={handleSubmit}
      destroyOnClose
    >
      <div className="ws-app-card-import__desc">
        上传或粘贴 Agent 生成的 app card payload JSON(含 <code>name</code> / <code>code</code> /{' '}
        <code>queries</code> / <code>config</code> 等字段)即可落库到当前空间。code 为自包含 JS 片段，无需额外 TS 源码。
      </div>
      <div className="ws-app-card-import__upload">
        <Button
          icon={<UploadOutlined />}
          onClick={() => fileInputRef.current?.click()}
        >
          选择 .json 文件
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          style={{ display: 'none' }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
            e.target.value = '';
          }}
        />
        <span className="ws-app-card-import__hint">也可直接粘贴到下方</span>
      </div>
      <Input.TextArea
        value={rawText}
        onChange={(e) => {
          setRawText(e.target.value);
          setTextName(e.target.value);
        }}
        placeholder='{"name":"容量看板","code":"(function(){...})()","config":{},"queries":[]}'
        autoSize={{ minRows: 10, maxRows: 16 }}
      />
      <div className="ws-app-card-import__name">
        <span>应用名称</span>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="未命名应用" maxLength={40} />
      </div>
    </Modal>
  );
}

/** 空间主页的应用入口:应用图标启动器。点击某张卡片 → 在场景空间打开完整应用页。 */
export function AppCardsSection({ workspaceId, refreshKey, onSelectAppCard }: AppCardsSectionProps) {
  const [importOpen, setImportOpen] = useState(false);
  const { data: cards = [], refresh } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listAppCards(workspaceId));
    return err ? [] : (res ?? []);
  }, { refreshDeps: [workspaceId, refreshKey] });

  return (
    <section className="ws-lobby__app-cards">
      <div className="ws-lobby__section-head">
        <span className="ws-lobby__section-icon"><AppstoreOutlined /></span>
        <span className="ws-lobby__section-title">应用卡片</span>
        <span className="ws-lobby__section-count">{cards.length}</span>
        <span className="ws-lobby__section-sub">点击图标在场景空间打开完整应用</span>
        <span className="ws-lobby__section-actions">
          <Button
            type="text"
            size="small"
            icon={<UploadOutlined />}
            onClick={() => setImportOpen(true)}
          >
            导入
          </Button>
          <button type="button" className="ws-app-card__reload" onClick={() => refresh()} aria-label="刷新" title="刷新">
            <ReloadOutlined />
          </button>
        </span>
      </div>

      {cards.length === 0 ? (
        <div className="ws-app-card__empty">
          <span className="ws-app-card__empty-icon"><AppstoreOutlined /></span>
          <span className="ws-app-card__empty-text">
            还没有应用卡片。让 Agent 生成一份 payload JSON，点击“导入”即可在场景空间常驻。
          </span>
          <Button type="link" onClick={() => setImportOpen(true)}>导入子应用</Button>
        </div>
      ) : (
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
          <button
            type="button"
            className="ws-app-card__tile ws-app-card__tile--add"
            onClick={() => setImportOpen(true)}
          >
            <span className="ws-app-card__tile-icon"><UploadOutlined /></span>
            <span className="ws-app-card__tile-main">
              <span className="ws-app-card__tile-name">导入子应用</span>
              <span className="ws-app-card__tile-status">上传 JSON</span>
            </span>
          </button>
        </div>
      )}

      <AppCardImportModal
        open={importOpen}
        workspaceId={workspaceId}
        onClose={() => setImportOpen(false)}
        onImported={refresh}
      />
    </section>
  );
}