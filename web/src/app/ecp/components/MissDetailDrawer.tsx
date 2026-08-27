'use client';

import { apiInterceptors } from '@/client/api';
import {
  EcpMissDetail,
  clearEcpMissLearned,
  getEcpMissDetail,
  learnEcpFromMisses,
} from '@/client/api/ecp';
import {
  CheckCircleFilled,
  CopyOutlined,
  ThunderboltOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Drawer, Empty, Popconfirm, Skeleton, Tag, Timeline, Tooltip } from 'antd';
import React, { useState } from 'react';

import '../ecp.css';

/** 聚类唯一键(kind, datasource_id, pattern)——miss 表与已学习表共用的详情入口。 */
export interface MissClusterRef {
  kind: string;
  pattern: string;
  datasource_id?: number | null;
}

const fmt = (ts?: string | null) => (ts ? new Date(ts).toLocaleString() : '-');

function SectionTitle({ children, extra }: { children: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div className="ecp-drawer__section-title" style={{ marginBottom: 0 }}>
        {children}
      </div>
      {extra}
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="ecp-drawer__kv">
      <div className="ecp-drawer__kv-key">{k}</div>
      <div className="ecp-drawer__kv-val">{v}</div>
    </div>
  );
}

/**
 * miss 聚类学习档案抽屉——飞轮视图点击聚类行展开。
 * 结构：聚类摘要(pattern 可复制) → 学习轨迹时间线(兜底→标记→清除→当前状态) →
 * 原始兜底记录(可折叠) → 底部操作(待学习→从 miss 学习 / 已学习→重新曝光)。
 * 详情接口一次返回全部数据(后端按同一归一化键聚合 op_log 与 miss_learn)。
 */
export default function MissDetailDrawer({
  cluster,
  open,
  onClose,
  onChanged,
}: {
  cluster: MissClusterRef | null;
  open: boolean;
  onClose: () => void;
  /** 详情内学习/清除成功后通知父级刷新两个列表 */
  onChanged?: () => void;
}) {
  const { message } = App.useApp();
  const [expanded, setExpanded] = useState(false);

  const {
    data: detail,
    loading,
    error,
    refresh,
  } = useRequest(
    async () => {
      if (!cluster) return null;
      const [err, res] = await apiInterceptors(
        getEcpMissDetail({
          workspace_id: undefined,
          kind: cluster.kind,
          pattern: cluster.pattern,
          datasource_id: cluster.datasource_id ?? undefined,
        }),
      );
      if (err) throw err;
      return res;
    },
    {
      ready: open && !!cluster,
      refreshDeps: [cluster?.kind, cluster?.pattern, cluster?.datasource_id],
    },
  );

  const { run: learn, loading: learning } = useRequest(
    async () => {
      const [err] = await apiInterceptors(
        learnEcpFromMisses({ top: 10 }),
      );
      if (err) throw err;
    },
    {
      manual: true,
      onSuccess: () => {
        message.success('已交给提案 Agent 学习，生成的提案将进入收件箱');
        refresh();
        onChanged?.();
      },
      onError: () => message.error('学习触发失败(需工作空间已配置提案 Agent)'),
    },
  );

  const { run: clear, loading: clearing } = useRequest(
    async () => {
      if (!cluster) return;
      const [err] = await apiInterceptors(
        clearEcpMissLearned({
          kind: cluster.kind,
          pattern: cluster.pattern,
          datasource_id: cluster.datasource_id ?? undefined,
        }),
      );
      if (err) throw err;
    },
    {
      manual: true,
      onSuccess: () => {
        message.success('已清除标记，该聚类重新出现在「未覆盖问题」');
        refresh();
        onChanged?.();
      },
    },
  );

  const copyPattern = async () => {
    if (!cluster) return;
    try {
      await navigator.clipboard.writeText(cluster.pattern);
      message.success('已复制归一化 pattern');
    } catch {
      message.error('复制失败');
    }
  };

  const renderTimeline = (d: EcpMissDetail) => {
    const c = d.cluster;
    const items: Array<{
      key: string;
      color?: string;
      dot?: React.ReactNode;
      label?: React.ReactNode;
      children: React.ReactNode;
    }> = [];

    if (c.first_seen) {
      items.push({
        key: 'first',
        color: 'gray',
        label: <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>{fmt(c.first_seen)}</span>,
        children: (
          <>
            <div style={{ fontWeight: 550, color: 'var(--ink-900)' }}>首次兜底</div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
              目录未覆盖该问题，走了 execute_raw_sql 兜底
            </div>
          </>
        ),
      });
    }
    if (c.count > 1 && c.last_seen && c.last_seen !== c.first_seen) {
      items.push({
        key: 'repeat',
        color: 'gray',
        label: <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>{fmt(c.last_seen)}</span>,
        children: (
          <>
            <div style={{ fontWeight: 550, color: 'var(--ink-900)' }}>
              累计 {c.count} 次兜底
            </div>
            {(c.reasonings ?? []).slice(0, 3).map((r, i) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--ink-500)' }}>
                · 未命中原因: {r}
              </div>
            ))}
          </>
        ),
      });
    }
    for (const ev of d.learn_events ?? []) {
      if (ev.op === 'miss_learned') {
        items.push({
          key: `learned-${ev.ts}`,
          color: 'green',
          label: <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>{fmt(ev.ts)}</span>,
          children: (
            <>
              <div style={{ fontWeight: 550, color: 'var(--ink-900)' }}>标记已学习</div>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>
                {ev.trigger === 'agent' ? (
                  <Tag color="green" style={{ marginRight: 6 }}>自动学习</Tag>
                ) : (
                  <Tag color="blue" style={{ marginRight: 6 }}>手动触发</Tag>
                )}
                {(ev.proposals ?? []).map(id => (
                  <Tag key={id} style={{ marginBottom: 2 }}>{id}</Tag>
                ))}
              </div>
              {!!ev.proposals?.length && (
                <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
                  生成的提案已进入收件箱等待确认
                </div>
              )}
            </>
          ),
        });
      } else if (ev.op === 'miss_learn_clear') {
        items.push({
          key: `clear-${ev.ts}`,
          color: '#fa8c16',
          label: <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>{fmt(ev.ts)}</span>,
          children: (
            <>
              <div style={{ fontWeight: 550, color: 'var(--ink-900)' }}>
                清除标记（重新曝光）
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
                该聚类重新进入「未覆盖问题」，等待再次学习
              </div>
            </>
          ),
        });
      }
    }
    if (d.learned) {
      items.push({
        key: 'state-learned',
        color: 'green',
        dot: <CheckCircleFilled style={{ fontSize: 16, color: '#52c41a' }} />,
        label: (
          <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            {fmt(d.learned.learned_at)}
          </span>
        ),
        children: (
          <>
            <div style={{ fontWeight: 550, color: 'var(--ink-900)' }}>已沉淀，不再重复曝光</div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
              已学习标记持久生效，每日学习不再重复喂入该聚类；如需重新学习可清除标记
            </div>
          </>
        ),
      });
    } else {
      items.push({
        key: 'state-pending',
        color: 'blue',
        label: <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>当前</span>,
        children: (
          <>
            <div style={{ fontWeight: 550, color: 'var(--ink-900)' }}>待学习</div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
              尚未沉淀，点击下方「从 miss 学习」交给提案 Agent 提炼
            </div>
          </>
        ),
      });
    }
    return <Timeline mode="left" items={items} />;
  };

  const records = detail?.records ?? [];
  const shownRecords = expanded ? records : records.slice(0, 3);
  const isDoc = detail?.cluster.kind === 'doc';

  return (
    <Drawer
      className="ecp-drawer"
      width={640}
      open={open}
      onClose={onClose}
      destroyOnClose={false}
      title={
        detail ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {isDoc ? <Tag color="purple">doc</Tag> : <Tag color="blue">db</Tag>}
            {detail.cluster.datasource_id != null && <Tag>数据源 #{detail.cluster.datasource_id}</Tag>}
            <span style={{ fontSize: 13, color: 'var(--ink-700)' }}>
              兜底 {detail.cluster.count} 次
            </span>
            {detail.learned ? (
              <Tag color="green">已学习</Tag>
            ) : (
              <Tag color="orange">待学习</Tag>
            )}
          </span>
        ) : (
          '聚类学习档案'
        )
      }
      footer={
        detail ? (
          detail.learned ? (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                该聚类已沉淀为语义资产，学习侧不再重复喂入
              </span>
              <Popconfirm
                title="清除该已学习标记？"
                description="清除后该聚类重新出现在「未覆盖问题」，可再次学习。"
                okText="清除标记"
                cancelText="取消"
                okButtonProps={{ danger: true, loading: clearing }}
                onConfirm={() => clear()}
              >
                <Button danger icon={<UndoOutlined />} loading={clearing}>
                  重新曝光
                </Button>
              </Popconfirm>
            </div>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                将当前所有待学聚类(最多 10 个)交给提案 Agent
              </span>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={learning}
                onClick={() => learn()}
              >
                从 miss 学习
              </Button>
            </div>
          )
        ) : undefined
      }
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : error || !detail ? (
        <Empty
          description="详情加载失败"
          style={{ marginTop: 80 }}
        >
          <Button type="primary" onClick={() => refresh()}>
            重试
          </Button>
        </Empty>
      ) : (
        <>
          <div className="ecp-drawer__section">
            <SectionTitle
              extra={
                <Tooltip title="复制归一化 pattern">
                  <Button size="small" type="text" icon={<CopyOutlined />} onClick={copyPattern} />
                </Tooltip>
              }
            >
              聚类摘要
            </SectionTitle>
            <KV
              k="归一化 pattern"
              v={
                <code
                  style={{
                    fontSize: 12,
                    color: 'var(--ink-700)',
                    wordBreak: 'break-all',
                    display: 'block',
                    maxHeight: 88,
                    overflow: 'auto',
                  }}
                >
                  {detail.cluster.pattern}
                </code>
              }
            />
            <KV k="兜底频次" v={`${detail.cluster.count} 次`} />
            <KV
              k="首次 → 最近"
              v={`${fmt(detail.cluster.first_seen)} → ${fmt(detail.cluster.last_seen)}`}
            />
            <KV
              k="数据源"
              v={detail.cluster.datasource_id != null ? `#${detail.cluster.datasource_id}` : '-'}
            />
            {!!detail.cluster.spaces?.length && (
              <KV k="知识空间" v={detail.cluster.spaces.join('、')} />
            )}
            {!!detail.cluster.reasonings?.length && (
              <KV
                k="未命中原因"
                v={
                  <>
                    {detail.cluster.reasonings.slice(0, 4).map((r, i) => (
                      <div key={i} style={{ marginBottom: 2 }}>· {r}</div>
                    ))}
                    {detail.cluster.reasonings.length > 4 && (
                      <span style={{ color: 'var(--ink-400)' }}>
                        等 {detail.cluster.reasonings.length} 种
                      </span>
                    )}
                  </>
                }
              />
            )}
          </div>

          <div className="ecp-drawer__section">
            <div className="ecp-drawer__section-title">学习轨迹</div>
            {renderTimeline(detail)}
          </div>

          <div className="ecp-drawer__section">
            <SectionTitle
              extra={
                records.length > 3 ? (
                  <Button size="small" type="link" onClick={() => setExpanded(x => !x)}>
                    {expanded ? '收起' : `展开全部 ${records.length} 条`}
                  </Button>
                ) : undefined
              }
            >
              原始兜底记录（{records.length} 条）
            </SectionTitle>
            {records.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                近期兜底日志中未找到该聚类的记录（可能已被清理）
              </div>
            ) : (
              shownRecords.map((r, i) => (
                <div
                  key={i}
                  style={{
                    padding: '8px 0',
                    borderBottom:
                      i < shownRecords.length - 1 ? '1px dashed var(--line-soft)' : 'none',
                  }}
                >
                  <div style={{ fontSize: 12, color: 'var(--ink-400)', marginBottom: 4 }}>
                    {fmt(r.ts)}
                    {r.datasource_id != null && ` · 数据源 #${r.datasource_id}`}
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      fontSize: 12,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                      color: 'var(--ink-700)',
                    }}
                  >
                    {isDoc ? `问题: ${r.question ?? '-'}` : r.sql ?? '-'}
                  </pre>
                  {r.reasoning && (
                    <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>
                      · 未命中原因: {r.reasoning}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </>
      )}
    </Drawer>
  );
}
