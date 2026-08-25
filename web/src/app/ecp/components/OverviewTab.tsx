'use client';

import { apiInterceptors } from '@/client/api';
import {
  EcpSemanticObject,
  getEcpInbox,
  listEcpAssets,
  listEcpObjects,
} from '@/client/api/ecp';
import { useRequest } from 'ahooks';
import { useState } from 'react';

import OverviewGraphCard from './OverviewGraphCard';
import { Dot, EcpEmpty, StatusTag, TYPE_DOT } from './common';

/** Overview: semantic-asset solidification dashboard. */
export default function OverviewTab({
  onGoSemantics,
  onGoGraph,
  workspaceId,
}: {
  onGoSemantics: () => void;
  onGoGraph: () => void;
  workspaceId: string;
}) {
  const [assetExpanded, setAssetExpanded] = useState(false);

  const { data: confirmed } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpObjects({ status: 'confirmed', page_size: 1, workspace_id: workspaceId }),
      );
      return err ? null : res;
    },
    { refreshDeps: [workspaceId] },
  );
  const { data: inbox } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getEcpInbox({ page_size: 5, workspace_id: workspaceId }),
      );
      return err ? null : res;
    },
    { refreshDeps: [workspaceId] },
  );
  const { data: assets } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpAssets({ workspace_id: workspaceId }),
      );
      return err ? [] : res ?? [];
    },
    { refreshDeps: [workspaceId] },
  );

  const confirmedCount = confirmed?.total_count ?? 0;
  const pendingCount = inbox?.total_count ?? 0;
  const rate =
    confirmedCount + pendingCount
      ? Math.round((confirmedCount / (confirmedCount + pendingCount)) * 100)
      : 0;

  return (
    <>
      <div className="ecp-grid ecp-grid--4" style={{ marginBottom: 16, alignItems: 'start' }}>
        <div className="ecp-metric-card ecp-rise ecp-rise--1">
          <div className="ecp-metric-card__head">
            <Dot kind="ecp-dot--success" />
            已确认语义对象
          </div>
          <div className="ecp-metric-card__num">{confirmedCount}</div>
          <div className="ecp-metric-card__foot">confirmed 口径即刻参与查询</div>
        </div>

        <div className="ecp-metric-card ecp-rise ecp-rise--2">
          <div className="ecp-metric-card__head">
            <Dot kind="ecp-dot--warning" />
            待确认提案
          </div>
          <div className="ecp-metric-card__num">{pendingCount}</div>
          <div className="ecp-metric-card__foot">确认前不影响任何查询</div>
        </div>

        <div
          className="ecp-metric-card ecp-rise ecp-rise--3"
          onClick={() => setAssetExpanded(e => !e)}
          style={{ cursor: 'pointer' }}
        >
          <div className="ecp-metric-card__head" style={{ justifyContent: 'space-between' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Dot kind="ecp-dot--entity" />
              登记资产
            </span>
            {(assets ?? []).length > 0 && (
              <span style={{ fontSize: 11, color: 'var(--ink-400)' }}>
                {assetExpanded ? '收起' : '明细'}
              </span>
            )}
          </div>
          <div className="ecp-metric-card__num">{assets?.length ?? 0}</div>
          <div className="ecp-metric-card__foot">数据源 / 知识资产引用</div>
          {assetExpanded && (
            <div
              style={{
                marginTop: 10,
                fontSize: 12,
                color: 'var(--ink-500)',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              {(assets ?? []).length === 0 ? (
                <span style={{ color: 'var(--ink-400)' }}>尚未登记资产</span>
              ) : (
                (assets ?? []).map(a => (
                  <div
                    key={a.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      justifyContent: 'space-between',
                    }}
                  >
                    <span
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <Dot kind={`ecp-dot--${a.kind}`} /> {a.kind} ·{' '}
                      <code style={{ fontSize: 12 }}>{a.ref_id}</code>
                    </span>
                    <span className="ecp-status">
                      <Dot kind={a.status === 'active' ? 'ecp-dot--success' : 'ecp-dot--neutral'} />
                      {a.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <div className="ecp-metric-card ecp-rise ecp-rise--4">
          <div className="ecp-metric-card__head">
            <Dot kind="ecp-dot--metric" />
            资产固化率
          </div>
          <div className="ecp-metric-card__num">{rate}%</div>
          <div className="ecp-metric-card__foot">北极星：⚠️→✅ 的转化程度</div>
        </div>
      </div>

      <div className="ecp-grid ecp-grid--2">
        <div className="ecp-card">
          <div className="ecp-card__title">
            待确认 Top 5
            <span className="ecp-card__title-link" onClick={onGoSemantics}>
              去业务口径 →
            </span>
          </div>
          {(inbox?.items ?? []).length === 0 ? (
            <EcpEmpty title="收件箱为空" desc="没有等待确认的提案" />
          ) : (
            (inbox?.items ?? []).map((obj: EcpSemanticObject) => (
              <div
                key={`${obj.id}@${obj.version}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 4px',
                  borderBottom: '1px solid var(--line-soft)',
                }}
              >
                <Dot kind={TYPE_DOT[obj.obj_type] ?? 'ecp-dot--neutral'} />
                <span style={{ fontWeight: 600, color: 'var(--ink-900)', fontSize: 13 }}>
                  {obj.id}
                </span>
                <span style={{ color: 'var(--ink-400)', fontSize: 12, flex: 1 }}>
                  {obj.name ?? ''}
                </span>
                <StatusTag status={obj.status} />
              </div>
            ))
          )}
        </div>

        {/* 全景图速览：替代原「资产状态」，首屏右侧即可看到语义关系形状 */}
        <OverviewGraphCard workspaceId={workspaceId} onGoGraph={onGoGraph} />
      </div>
    </>
  );
}
