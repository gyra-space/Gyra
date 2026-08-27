'use client';

import { apiInterceptors } from '@/client/api';
import {
  EcpMissCluster,
  EcpMissLearn,
  clearEcpMissLearned,
  getEcpMissReport,
  learnEcpFromMisses,
  listEcpMissLearned,
} from '@/client/api/ecp';
import {
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Popconfirm, Segmented, Table, Tag, Tooltip } from 'antd';
import React, { useState } from 'react';

import { Dot, EcpEmpty } from './common';
import MissDetailDrawer, { MissClusterRef } from './MissDetailDrawer';

type View = 'miss' | 'learned';

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div style={{ flex: 1, minWidth: 120, padding: '12px 16px', borderLeft: '1px solid var(--line-soft)' }}>
      <div style={{ fontSize: 22, fontWeight: 650, color: 'var(--ink-900)', lineHeight: 1.2 }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 4 }}>
        {label}
        {hint && (
          <Tooltip title={hint}>
            <span style={{ marginLeft: 4, color: 'var(--ink-400)', cursor: 'help' }}>ⓘ</span>
          </Tooltip>
        )}
      </div>
    </div>
  );
}

/**
 * Miss 飞轮视图 — 未覆盖问题(execute_raw_sql 兜底记录)的聚类 + 已学习标记(落盘回写)。
 * 上半屏：飞轮概览指标；下半屏用 Segmented 在「未覆盖问题 / 已学习标记」两组表格间切换。
 * 已学习标记是 flywheel 学习侧的持久记忆：被标记的聚类不会在「未覆盖问题」里重复曝光，
 * 可一键清除标记让其重新曝光(重新学习)。
 */
export default function MissTab({ workspaceId }: { workspaceId: string }) {
  const [view, setView] = useState<View>('miss');
  const [detailCluster, setDetailCluster] = useState<MissClusterRef | null>(null);
  const [learnResult, setLearnResult] = useState<string | null>(null);
  const { message } = App.useApp();

  const { data, loading, refresh } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getEcpMissReport({ limit: 50, workspace_id: workspaceId }),
      );
      if (err) throw err;
      return res;
    },
    { refreshDeps: [workspaceId] },
  );

  const {
    data: learned,
    loading: learnedLoading,
    refresh: refreshLearned,
  } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpMissLearned({ workspace_id: workspaceId }),
      );
      if (err) throw err;
      return res ?? [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { run: clear, loading: clearing } = useRequest(
    async (rec: EcpMissLearn) => {
      const [err, removed] = await apiInterceptors(
        clearEcpMissLearned({
          workspace_id: workspaceId,
          kind: rec.kind,
          pattern: rec.pattern,
          datasource_id: rec.datasource_id ?? undefined,
        }),
      );
      if (err) throw err;
      message.success(`已清除标记${removed ? `（${removed} 条）` : ''}，聚类将重新出现在「未覆盖问题」`);
      refreshLearned();
      refresh();
    },
    { manual: true },
  );

  const { run: learn, loading: learning } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        learnEcpFromMisses({ top: 10, workspace_id: workspaceId }),
      );
      if (err) throw err;
      return res;
    },
    {
      manual: true,
      onSuccess: res => {
        if (!res) return;
        if (res.errors?.length) {
          setLearnResult(`学习完成但有错误: ${res.errors[0]}`);
        } else {
          setLearnResult(
            `已生成 ${res.proposals_created} 个提案进收件箱，请前往「收件箱」确认；本次喂入的 miss 聚类已标记为已学习`,
          );
        }
        refresh();
        refreshLearned();
      },
      onError: () => message.error('学习触发失败(需工作空间已配置提案 Agent)'),
    },
  );

  /** 打开聚类学习档案抽屉(行点击/操作列共用入口) */
  const openDetail = (
    kind?: string | null,
    pattern?: string | null,
    datasourceId?: number | null,
  ) => {
    if (!pattern) return;
    setDetailCluster({
      kind: kind ?? 'db',
      pattern,
      datasource_id: datasourceId ?? undefined,
    });
  };

  const missColumns = [
    {
      title: '类型',
      dataIndex: 'kind',
      key: 'kind',
      width: 70,
      render: (kind: string) =>
        kind === 'doc' ? <Tag color="purple">doc</Tag> : <Tag color="blue">db</Tag>,
    },
    {
      title: '频次',
      dataIndex: 'count',
      key: 'count',
      width: 90,
      sorter: (a: EcpMissCluster, b: EcpMissCluster) => b.count - a.count,
      defaultSortOrder: 'descend' as const,
      render: (count: number) => (
        <span className="ecp-status">
          <Dot
            kind={
              count >= 5
                ? 'ecp-dot--danger'
                : count >= 2
                  ? 'ecp-dot--warning'
                  : 'ecp-dot--neutral'
            }
          />
          {count} 次
        </span>
      ),
    },
    {
      title: '示例',
      dataIndex: 'example_sql',
      key: 'example_sql',
      render: (sql: string, record: EcpMissCluster) => (
        <pre
          style={{
            margin: 0,
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            maxWidth: 460,
            color: 'var(--ink-700)',
          }}
        >
          {record.kind === 'doc' ? `问题: ${sql}` : sql}
        </pre>
      ),
    },
    {
      title: '未命中原因',
      dataIndex: 'reasonings',
      key: 'reasonings',
      width: 240,
      render: (reasonings: string[]) => (
        <>
          {(reasonings ?? []).slice(0, 3).map((r, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
              · {r}
            </div>
          ))}
        </>
      ),
    },
    {
      title: '数据源',
      dataIndex: 'datasource_id',
      key: 'datasource_id',
      width: 90,
      render: (id: number) => <Tag>#{id}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: EcpMissCluster) => (
        <span onClick={e => e.stopPropagation()}>
          <Button
            size="small"
            type="link"
            onClick={() => openDetail(record.kind, record.pattern, record.datasource_id)}
          >
            详情
          </Button>
        </span>
      ),
    },
  ];

  const learnedColumns = [
    {
      title: '类型',
      dataIndex: 'kind',
      key: 'kind',
      width: 70,
      render: (kind: string) =>
        kind === 'doc' ? <Tag color="purple">doc</Tag> : <Tag color="blue">db</Tag>,
    },
    {
      title: '归一化 pattern',
      dataIndex: 'pattern',
      key: 'pattern',
      ellipsis: { showTitle: true },
      render: (pattern: string) => (
        <Tooltip title={pattern}>
          <code style={{ fontSize: 12, color: 'var(--ink-700)', wordBreak: 'break-all' }}>
            {pattern}
          </code>
        </Tooltip>
      ),
    },
    {
      title: '示例',
      dataIndex: 'example',
      key: 'example',
      render: (example: string, record: EcpMissLearn) =>
        example ? (
          <pre
            style={{
              margin: 0,
              fontSize: 12,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              maxWidth: 320,
              color: 'var(--ink-500)',
            }}
          >
            {record.kind === 'doc' ? `问题: ${example}` : example}
          </pre>
        ) : (
          '-'
        ),
    },
    {
      title: '关联提案',
      dataIndex: 'proposal_ids',
      key: 'proposal_ids',
      width: 180,
      render: (ids: string[]) =>
        ids?.length ? (
          <>
            {ids.slice(0, 3).map(id => (
              <Tag key={id} style={{ marginBottom: 2 }}>
                {id}
              </Tag>
            ))}
            {ids.length > 3 && <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>+{ids.length - 3}</span>}
          </>
        ) : (
          '-'
        ),
    },
    {
      title: '触发方式',
      dataIndex: 'trigger',
      key: 'trigger',
      width: 110,
      render: (trigger: string) =>
        trigger === 'agent' ? (
          <Tag color="green">自动学习</Tag>
        ) : (
          <Tag color="blue">手动触发</Tag>
        ),
    },
    {
      title: '学习时间',
      dataIndex: 'learned_at',
      key: 'learned_at',
      width: 170,
      render: (at: string) =>
        at ? new Date(at).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: EcpMissLearn) => (
        <span onClick={e => e.stopPropagation()}>
          <Button
            size="small"
            type="link"
            onClick={() => openDetail(record.kind, record.pattern, record.datasource_id)}
          >
            详情
          </Button>
          <Popconfirm
            title="清除该已学习标记？"
            description="清除后该 miss 聚类会重新出现在「未覆盖问题」，可再次学习。"
            okText="清除标记"
            cancelText="取消"
            okButtonProps={{ danger: true, loading: clearing }}
            onConfirm={() => clear(record)}
          >
            <Button size="small" type="link" danger icon={<UndoOutlined />}>
              重新曝光
            </Button>
          </Popconfirm>
        </span>
      ),
    },
  ];

  const learnedCount = learned?.length ?? data?.learned_count ?? 0;

  return (
    <>
      {/* 飞轮概览指标 */}
      <div
        className="ecp-card"
        style={{
          display: 'flex',
          alignItems: 'stretch',
          padding: 0,
          overflow: 'hidden',
          marginBottom: 16,
        }}
      >
        <Metric label="总兜底次数" value={data?.total_fallbacks ?? 0} hint="累积 execute_raw_sql 兜底记录数" />
        <Metric label="待学习聚类" value={data?.cluster_count ?? 0} hint="当前未覆盖、且未标记学习的高频聚类" />
        <Metric label="已学习标记" value={learnedCount} hint="已沉淀为语义资产、被排除的聚类标记" />
        <Metric label="兜底/聚类 比" value={data?.total_fallbacks && data?.cluster_count ? `${(data.total_fallbacks / Math.max(1, data.cluster_count)).toFixed(1)}×` : '-'} hint="平均每个聚类由多少次兜底驱动" />
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Segmented
          value={view}
          onChange={v => setView(v as View)}
          options={[
            {
              label: `未覆盖问题${data?.clusters?.length ? `（${data.clusters.length}）` : ''}`,
              value: 'miss',
            },
            {
              label: `已学习标记${learned?.length ? `（${learned.length}）` : ''}`,
              value: 'learned',
            },
          ]}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <Button icon={<ReloadOutlined />} loading={loading || learnedLoading} onClick={() => { refresh(); refreshLearned(); }}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={learning}
            disabled={!data?.clusters?.length}
            onClick={() => learn()}
          >
            从 miss 学习
          </Button>
        </div>
      </div>

      {learnResult && (
        <div className="ecp-card" style={{ marginBottom: 16 }}>
          <span className="ecp-status">
            <Dot kind="ecp-dot--success" />
            {learnResult}
          </span>
        </div>
      )}

      {view === 'miss' ? (
        !loading && !data?.clusters?.length ? (
          <EcpEmpty
            title={
              data?.total_fallbacks
                ? '有兜底记录但暂未达到聚类频次，或已被标记学习'
                : '暂无 miss 记录——目录覆盖良好,或还没有探索发生'
            }
          />
        ) : (
          <div className="ecp-card">
            <div className="ecp-card__title">
              <span>
                <PlayCircleOutlined style={{ marginRight: 8 }} />
                miss 聚类（共 {data?.total_fallbacks ?? 0} 次兜底 / {data?.cluster_count ?? 0} 类 / 已学 {data?.learned_count ?? 0} 类）
                <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--ink-400)', marginLeft: 12 }}>
                  点击行查看学习档案
                </span>
              </span>
            </div>
            <Table
              rowKey={r => `${r.datasource_id}-${r.pattern}`}
              columns={missColumns}
              dataSource={data?.clusters ?? []}
              loading={loading}
              size="small"
              pagination={{ pageSize: 10, hideOnSinglePage: true }}
              onRow={(r: EcpMissCluster) => ({
                onClick: () => openDetail(r.kind, r.pattern, r.datasource_id),
                style: { cursor: 'pointer' },
              })}
            />
          </div>
        )
      ) : !learnedLoading && !learned?.length ? (
        <EcpEmpty
          title="暂无已学习标记"
          desc="点击左上「从 miss 学习」成功后，成功沉淀的 miss 聚类会记录在这里，不再重复曝光。"
        />
      ) : (
        <div className="ecp-card">
          <div className="ecp-card__title">
            <span>
              <PlayCircleOutlined style={{ marginRight: 8 }} />
              已学习标记（共 {learned?.length ?? 0} 条）
              <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--ink-400)', marginLeft: 12 }}>
                点击行查看学习档案
              </span>
            </span>
          </div>
          <Table
            rowKey={r => r.id}
            columns={learnedColumns}
            dataSource={learned ?? []}
            loading={learnedLoading}
            size="small"
            pagination={{ pageSize: 10, hideOnSinglePage: true }}
            onRow={(r: EcpMissLearn) => ({
              onClick: () => openDetail(r.kind, r.pattern, r.datasource_id),
              style: { cursor: 'pointer' },
            })}
          />
        </div>
      )}

      <MissDetailDrawer
        cluster={detailCluster}
        open={!!detailCluster}
        onClose={() => setDetailCluster(null)}
        onChanged={() => {
          refresh();
          refreshLearned();
        }}
      />
    </>
  );
}
