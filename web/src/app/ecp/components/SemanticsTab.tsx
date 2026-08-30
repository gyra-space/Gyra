'use client';

import { apiInterceptors } from '@/client/api';
import {
  EcpSemanticObject,
  confirmEcpObject,
  getEcpInbox,
  listEcpObjects,
  rejectEcpObject,
} from '@/client/api/ecp';
import { getUserId } from '@/utils';
import { CheckOutlined, CloseOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Input, Modal, Popconfirm, Segmented, Select, Spin } from 'antd';
import { useState } from 'react';

import {
  DeprecateFooter,
  Dot,
  EcpEmpty,
  LineageChips,
  ObjectDetailDrawer,
  OriginBadge,
  StatusTag,
  summarizePayload,
  TYPE_DOT,
} from './common';
import CreateProposalModal from './CreateProposalModal';
import PayloadEditor from './PayloadEditor';

const TYPES = ['entity', 'metric', 'relation', 'dimension', 'claim', 'terminology', 'policy'] as const;

type StatusMode = 'proposed' | 'confirmed' | 'all';

function Confidence({ value }: { value?: number | null }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  return (
    <span className="ecp-confidence">
      <span className="ecp-confidence__bar">
        <span className="ecp-confidence__fill" style={{ width: `${pct}%` }} />
      </span>
      {pct}%
    </span>
  );
}

function ProposalCard({
  obj,
  onConfirm,
  onReject,
  onDetail,
  onEdit,
  confirming,
  reject,
}: {
  obj: EcpSemanticObject;
  onConfirm: (o: EcpSemanticObject) => void;
  onReject: (o: EcpSemanticObject) => void;
  onDetail: (o: EcpSemanticObject) => void;
  onEdit: (o: EcpSemanticObject) => void;
  confirming: boolean;
  reject: boolean;
}) {
  return (
    <div className="ecp-proposal ecp-rise ecp-rise--1">
      <div className="ecp-proposal__head">
        <Dot kind={TYPE_DOT[obj.obj_type] ?? 'ecp-dot--neutral'} />
        <span className="ecp-proposal__id" onClick={() => onDetail(obj)}>
          {obj.id}
        </span>
        <span className="ecp-proposal__name">
          {obj.name ?? ''}
          {obj.payload?.aliases?.length ? `（${obj.payload.aliases.join('/')}）` : ''}
        </span>
        <span style={{ flex: 1 }} />
        <StatusTag status={obj.status} />
      </div>

      <div className="ecp-proposal__summary">{obj.view?.summary || summarizePayload(obj)}</div>

      {!!obj.view?.lineage && (
        <div style={{ margin: '4px 0 2px' }}>
          <LineageChips lineage={obj.view.lineage} />
        </div>
      )}

      {!!obj.evidence?.length && (
        <div className="ecp-proposal__evidence">
          「{obj.evidence[0].quote ?? ''}」
          <span style={{ fontStyle: 'normal', color: 'var(--ink-400)' }}>
            {' '}
            —— {obj.evidence[0].source ?? '来源未知'}
          </span>
        </div>
      )}

      <div className="ecp-proposal__foot">
        <div className="ecp-proposal__meta">
          <Confidence value={obj.confidence} />
          {obj.view?.origin ? (
            <OriginBadge origin={obj.view.origin} />
          ) : (
            <span>来源 {obj.source ?? '-'}</span>
          )}
          <span>{obj.created_at?.slice(0, 16) ?? ''}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button size="small" onClick={() => onDetail(obj)}>
            详情
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => onEdit(obj)}>
            编辑并确认
          </Button>
          <Popconfirm title="否决该提案？" onConfirm={() => onReject(obj)}>
            <Button size="small" danger icon={<CloseOutlined />} loading={reject} />
          </Popconfirm>
          <Button
            size="small"
            type="primary"
            icon={<CheckOutlined />}
            loading={confirming}
            onClick={() => onConfirm(obj)}
          >
            确认生效
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * 业务口径：一个空间内「AI 提案 → 人确认 → 版本冻结」的唯一视图。
 * 待确认列表直接确认/否决，已确认/全部以目录形式浏览，点击看版本/证据/Payload。
 */
export default function SemanticsTab({ workspaceId }: { workspaceId: string }) {
  const { message } = App.useApp();
  const [statusMode, setStatusMode] = useState<StatusMode>('proposed');
  const [typeFilter, setTypeFilter] = useState<string>();
  const [keyword, setKeyword] = useState<string>();
  const [detail, setDetail] = useState<EcpSemanticObject | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<EcpSemanticObject | null>(null);
  const [editPayload, setEditPayload] = useState<Record<string, any>>({});

  // 待确认：提案卡片（确认动线核心）
  const {
    data: inbox,
    loading: inboxLoading,
    refresh: refreshInbox,
  } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getEcpInbox({ obj_type: typeFilter, keyword, page_size: 50, workspace_id: workspaceId }),
      );
      if (err) throw err;
      return res;
    },
    { refreshDeps: [typeFilter, keyword, workspaceId] },
  );

  // 已确认 / 全部：语义目录列表
  const {
    data: catalog,
    loading: catalogLoading,
    refresh: refreshCatalog,
  } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpObjects({
          obj_type: typeFilter,
          status: statusMode === 'confirmed' ? 'confirmed' : undefined,
          keyword,
          page_size: 100,
          workspace_id: workspaceId,
        }),
      );
      if (err) throw err;
      return res;
    },
    { refreshDeps: [statusMode, typeFilter, keyword, workspaceId] },
  );

  const { run: confirm, loading: confirming } = useRequest(
    async (obj: EcpSemanticObject) => {
      const user_id = getUserId() ?? 'unknown';
      const [err] = await apiInterceptors(
        confirmEcpObject(obj.id, obj.version, { user_id, workspace_id: obj.workspace_id }),
      );
      if (err) throw err;
      message.success(`已确认 ${obj.id}，该口径即刻生效`);
      refreshInbox();
      refreshCatalog();
    },
    { manual: true },
  );

  const { run: reject, loading: rejecting } = useRequest(
    async (obj: EcpSemanticObject) => {
      const user_id = getUserId() ?? 'unknown';
      const [err] = await apiInterceptors(
        rejectEcpObject(obj.id, obj.version, { user_id, workspace_id: obj.workspace_id }),
      );
      if (err) throw err;
      message.success(`已否决 ${obj.id}`);
      refreshInbox();
      refreshCatalog();
    },
    { manual: true },
  );

  const openEdit = (obj: EcpSemanticObject) => {
    setEditPayload({ ...(obj.payload ?? {}) });
    setEditing(obj);
  };

  const { run: confirmEdited, loading: editConfirming } = useRequest(
    async (obj: EcpSemanticObject) => {
      const user_id = getUserId() ?? 'unknown';
      const [err] = await apiInterceptors(
        confirmEcpObject(obj.id, obj.version, {
          user_id,
          workspace_id: obj.workspace_id,
          edited_payload: editPayload,
        }),
      );
      if (err) throw err;
      message.success(`已确认 ${obj.id}（编辑后），该口径即刻生效`);
      setEditing(null);
      refreshInbox();
      refreshCatalog();
    },
    { manual: true },
  );

  const inboxItems = inbox?.items ?? [];
  const catalogItems = catalog?.items ?? [];
  const inboxCount = inbox?.total_count ?? 0;

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 16,
          flexWrap: 'wrap',
        }}
      >
        <Segmented
          value={statusMode}
          onChange={v => setStatusMode(v as StatusMode)}
          options={[
            { label: `待确认${inboxCount ? ` (${inboxCount})` : ''}`, value: 'proposed' },
            { label: '已确认', value: 'confirmed' },
            { label: '全部', value: 'all' },
          ]}
        />
        <div style={{ display: 'flex', gap: 10 }}>
          <Select
            allowClear
            placeholder="类型"
            style={{ width: 140 }}
            value={typeFilter}
            onChange={setTypeFilter}
            options={TYPES.map(v => ({ value: v, label: v }))}
          />
          <Input.Search
            allowClear
            placeholder="搜索名称 / id"
            style={{ width: 260 }}
            onSearch={setKeyword}
          />
          <Button icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新增语义
          </Button>
        </div>
      </div>

      {statusMode === 'proposed' ? (
        inboxLoading ? (
          <Spin style={{ display: 'block', margin: '64px auto' }} />
        ) : inboxItems.length === 0 ? (
          <EcpEmpty
            title="没有待确认的提案"
            desc="到「数据资产」对数据源执行「生成提案」，AI 提炼的业务口径会在这里等待你确认。"
          />
        ) : (
          inboxItems.map((obj, i) => (
            <div key={`${obj.id}@${obj.version}`} style={{ marginBottom: 12 }}>
              <ProposalCard
                obj={obj}
                onConfirm={o => confirm(o)}
                onReject={o => reject(o)}
                onDetail={setDetail}
                onEdit={openEdit}
                confirming={confirming}
                reject={rejecting}
              />
            </div>
          ))
        )
      ) : catalogLoading ? (
        <Spin style={{ display: 'block', margin: '64px auto' }} />
      ) : catalogItems.length === 0 ? (
        <EcpEmpty
          title={statusMode === 'confirmed' ? '暂无已确认口径' : '语义目录为空'}
          desc="到「数据资产」生成提案并在此确认后，这里会出现已确认的业务口径目录。"
        />
      ) : (
        <div className="ecp-card" style={{ padding: '8px 20px' }}>
          {catalogItems.map(obj => (
            <div
              key={`${obj.id}@${obj.version}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '13px 0',
                borderBottom: '1px solid var(--line-soft)',
                cursor: 'pointer',
              }}
              onClick={() => setDetail(obj)}
            >
              <Dot kind={TYPE_DOT[obj.obj_type] ?? 'ecp-dot--neutral'} />
              <div style={{ width: 220, flexShrink: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>
                  {obj.id}
                </div>
                <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                  {obj.name ?? ''}
                  {obj.payload?.aliases?.length ? `（${obj.payload.aliases.join('/')}）` : ''}
                </div>
              </div>
              <div
                style={{
                  flex: 1,
                  minWidth: 0,
                  fontSize: 12,
                  color: 'var(--ink-500)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {obj.view?.summary || summarizePayload(obj)}
              </div>
              {obj.view?.origin && <OriginBadge origin={obj.view.origin} />}
              <StatusTag status={obj.status} />
            </div>
          ))}
        </div>
      )}

      <ObjectDetailDrawer
        obj={detail}
        open={!!detail}
        onClose={() => setDetail(null)}
        footer={
          <DeprecateFooter
            obj={detail}
            onDone={() => {
              setDetail(null);
              refreshInbox();
              refreshCatalog();
            }}
          />
        }
      />

      <CreateProposalModal
        workspaceId={workspaceId}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          refreshInbox();
          refreshCatalog();
        }}
      />

      {editing && (
        <Modal
          title={`编辑并确认 ${editing.id}`}
          open={!!editing}
          okText="确认生效"
          cancelText="取消"
          confirmLoading={editConfirming}
          onOk={() => confirmEdited(editing)}
          onCancel={() => setEditing(null)}
        >
          <PayloadEditor objType={editing.obj_type} value={editPayload} onChange={setEditPayload} />
        </Modal>
      )}
    </>
  );
}
