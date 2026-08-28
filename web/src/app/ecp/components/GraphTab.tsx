'use client';

import { apiInterceptors } from '@/client/api';
import {
  EcpGraph,
  EcpGraphNode,
  confirmEcpAlignment,
  getEcpGraph,
  getEcpObject,
  listEcpAlignments,
  rebuildEcpGraph,
  rejectEcpAlignment,
  removeEcpAlignment,
  runEcpAlignment,
} from '@/client/api/ecp';
import { useLoadGraph, useSigma, SigmaContainer } from '@react-sigma/core';
import '@react-sigma/core/lib/style.css';
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import {
  Button,
  Drawer,
  Input,
  List,
  Popconfirm,
  Segmented,
  Spin,
  Tag,
  Tooltip,
  message,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useEffect, useMemo, useState } from 'react';

import { DeprecateFooter, Dot, EcpEmpty, ObjectDetailDrawer, StatusTag } from './common';
import type { EcpSemanticObject } from '@/client/api/ecp';
import { getUserId } from '@/utils';

// ---------------------------------------------------------------------------
// 节点视觉体系：与 ecp.css 的 ecp-dot 色板严格对齐(common.tsx TYPE_DOT 同源)
// ---------------------------------------------------------------------------

/** 语义对象(obj_kind=object)按 obj_type 着色;claim 族复用结构化四色。 */
const OBJECT_HEX: Record<string, string> = {
  entity: '#4f46e5',
  metric: '#22c55e',
  relation: '#f59e0b',
  dimension: '#722ed1',
  claim: '#06b6d4',
  terminology: '#3b82f6',
  policy: '#ef4444',
};

/** 资产(asset)与知识层(kn)颜色。 */
const ASSET_HEX: Record<string, string> = {
  db: '#4f46e5',
  document: '#06b6d4',
  space: '#22c55e',
  api: '#f59e0b',
};
const KN_HEX = '#8a92a6';

const ASSET_ICON: Record<string, string> = {
  db: '🛢',
  document: '📄',
  space: '📚',
  api: '🔌',
};
const KN_ICON: Record<string, string> = { wiki: '📝', verbat: '🧾' };

/** 知识层的边(derived-from/about 等)用更浅的颜色与语义边区分。 */
const KNOWLEDGE_EDGE_TYPES = new Set(['derived-from', 'about', 'supersedes']);

/** 对齐边(aligns_to):LLM 推理产出、人工确认后生效;候选态用浅色弱化。 */
const ALIGN_EDGE_HEX: Record<string, string> = {
  confirmed: '#6366f1',
  proposed: '#c7d2fe',
};

type NodeGroup = 'object' | 'asset' | 'kn';

function nodeGroup(n: EcpGraphNode): NodeGroup {
  return n.node_kind ?? 'object';
}

function nodeColor(n: EcpGraphNode): string {
  const g = nodeGroup(n);
  if (g === 'asset') return ASSET_HEX[n.obj_type] ?? '#8a92a6';
  if (g === 'kn') return KN_HEX;
  return OBJECT_HEX[n.obj_type] ?? '#8a92a6';
}

function nodeLabel(n: EcpGraphNode): string {
  const g = nodeGroup(n);
  const base = n.name ?? n.id;
  if (g === 'asset') return `${ASSET_ICON[n.obj_type] ?? '📦'} ${base}`;
  if (g === 'kn') return `${KN_ICON[n.obj_type] ?? '📄'} ${base}`;
  return n.status === 'confirmed' ? base : `${base} 🟡`;
}

// ---------------------------------------------------------------------------
// 图构建(过滤后数据 → graphology 实例 → forceAtlas2 布局)
// ---------------------------------------------------------------------------

function GraphLoader({
  data,
  hidden,
  onSelect,
}: {
  data: EcpGraph;
  hidden: Set<NodeGroup>;
  onSelect: (node: EcpGraphNode) => void;
}) {
  const loadGraph = useLoadGraph();
  const sigma = useSigma();
  const nodeMap = useMemo(
    () => new Map(data.nodes.map(n => [n.id, n])),
    [data],
  );

  useEffect(() => {
    const graph: any = new Graph();
    const visible = data.nodes.filter(n => !hidden.has(nodeGroup(n)));
    const visibleIds = new Set(visible.map(n => n.id));

    const degrees = new Map<string, number>();
    for (const l of data.links) {
      if (!visibleIds.has(l.source) || !visibleIds.has(l.target)) continue;
      degrees.set(l.source, (degrees.get(l.source) || 0) + 1);
      degrees.set(l.target, (degrees.get(l.target) || 0) + 1);
    }
    const maxDegree = Math.max(1, ...degrees.values());

    for (const n of visible) {
      const degree = degrees.get(n.id) || 0;
      const g = nodeGroup(n);
      const unregistered = g === 'asset' && n.status === 'unregistered';
      // 资产是图的锚点(最大);未登记的被引用资产小一号(引用未入治理);
      // 对象按度数缩放;知识层保持小节点
      const size =
        g === 'asset'
          ? unregistered
            ? 6
            : 10 + Math.sqrt(degree / maxDegree) * 12
          : g === 'kn'
            ? 3.5
            : 4 + Math.sqrt(degree / maxDegree) * 14;
      graph.addNode(n.id, {
        label: nodeLabel(n),
        size,
        color: nodeColor(n),
        forceLabel: g !== 'kn',
        x: Math.random() * 100,
        y: Math.random() * 100,
      });
    }
    for (const l of data.links) {
      if (!visibleIds.has(l.source) || !visibleIds.has(l.target)) continue;
      const key = `${l.source}-[${l.edge_type}]->${l.target}`;
      if (!graph.hasEdge(key)) {
        graph.addEdgeWithKey(key, l.source, l.target, {
          label: l.edge_type,
          size: 1,
          color: KNOWLEDGE_EDGE_TYPES.has(l.edge_type)
            ? '#cbd5e1'
            : '#94a3b8',
        });
      }
    }

    if (graph.order > 1) {
      forceAtlas2.assign(graph, {
        iterations: 120,
        settings: {
          ...forceAtlas2.inferSettings(graph),
          gravity: 1,
          strongGravityMode: true,
          barnesHutOptimize: graph.order > 50,
        },
      });
    }
    loadGraph(graph);
  }, [data, hidden, loadGraph]);

  // 点击节点 → 详情(语义对象拉完整详情,资产/知识层展示关联)
  useEffect(() => {
    const handler = ({ node }: { node: string }) => {
      const n = nodeMap.get(node);
      if (n) onSelect(n);
    };
    sigma.on('clickNode', handler);
    return () => {
      sigma.removeListener('clickNode', handler);
    };
  }, [sigma, nodeMap, onSelect]);

  return null;
}

// ---------------------------------------------------------------------------
// 详情抽屉:资产 / 知识层节点(object 走 ObjectDetailDrawer,复用完整体验)
// ---------------------------------------------------------------------------

function AssetDetailContent({
  node,
  data,
}: {
  node: EcpGraphNode;
  data: EcpGraph;
}) {
  const related = data.links.filter(
    l => l.source === node.id || l.target === node.id,
  );
  const kindLabel: Record<string, string> = {
    db: '数据源（DB）',
    document: '文档',
    space: '知识空间',
    api: 'API 资源',
  };
  return (
    <div className="ecp-drawer__section">
      <div className="ecp-drawer__section-title">资产信息</div>
      <div className="ecp-drawer__kv">
        <div className="ecp-drawer__kv-key">类型</div>
        <div className="ecp-drawer__kv-val">
          {kindLabel[node.obj_type] ?? node.obj_type}
        </div>
      </div>
      <div className="ecp-drawer__kv">
        <div className="ecp-drawer__kv-key">引用</div>
        <div className="ecp-drawer__kv-val">{node.id}</div>
      </div>
      <div className="ecp-drawer__kv">
        <div className="ecp-drawer__kv-key">状态</div>
        <div className="ecp-drawer__kv-val">
          {node.status === 'unregistered' ? (
            <span style={{ color: 'var(--warning)' }}>未登记（仅被引用）</span>
          ) : (
            <StatusTag status={node.status} />
          )}
        </div>
      </div>
      {node.status === 'unregistered' && (
        <div className="ecp-drawer__kv">
          <div className="ecp-drawer__kv-key">说明</div>
          <div className="ecp-drawer__kv-val">
            该资源被语义对象引用但尚未在资产层登记；登记后可纳入治理（就绪检查 / 提案 / 门禁）
          </div>
        </div>
      )}
      {!!related.length && (
        <div className="ecp-drawer__kv">
          <div className="ecp-drawer__kv-key">图上关联</div>
          <div className="ecp-drawer__kv-val">
            {related.map(l => (
              <div
                key={`${l.source}-${l.edge_type}-${l.target}`}
                style={{ fontSize: 12 }}
              >
                {l.edge_type}: {l.source === node.id ? l.target : l.source}
                {l.edge_type === 'aligns_to' && l.status === 'proposed' && (
                  <span style={{ color: 'var(--warning)' }}>（候选，未确认）</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------

/**
 * 空间资产全景图:一个场景空间内「资源 → 语义 → 知识」三层同图。
 *
 * - 语义对象(硬层):entity/metric/... 七类,🟡 = proposed 未确认
 * - 资产(入驻资源):db/document/space/api;被引用未登记的资源以
 *   小一号节点显示(引用可见,治理未入)
 * - 知识层:wiki 文档与原文 verbat,来自知识空间 L2 图的实时聚合
 * 三层的连通点:claim ─ref─▶ 文档资产 ◀─derived-from─ wiki 页。
 * 知识实体与硬层对象之间是 aligns_to 语义对齐边:由 LLM 推理产出候选、
 * 人工确认后生效,查询时从对齐表投影——渲染零 LLM 依赖。
 * 边为查询时实时投影——存量数据零物化冷启动即有连线。
 */
export default function GraphTab({ workspaceId }: { workspaceId: string }) {
  const [hidden, setHidden] = useState<Set<NodeGroup>>(new Set());
  const [selected, setSelected] = useState<EcpGraphNode | null>(null);
  const [objectDetail, setObjectDetail] = useState<EcpSemanticObject | null>(
    null,
  );
  const [entityQuery, setEntityQuery] = useState('');
  const [alignOpen, setAlignOpen] = useState(false);
  const [alignFilter, setAlignFilter] = useState<
    'proposed' | 'confirmed' | 'rejected'
  >('proposed');

  const { data, loading, refresh } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getEcpGraph(workspaceId, entityQuery || undefined),
      );
      if (err) throw err;
      return res;
    },
    { refreshDeps: [workspaceId, entityQuery] },
  );

  // 对齐候选(LLM 推理产出 + 人工决定):常驻拉取,供待确认角标与抽屉
  const {
    data: alignments,
    loading: alignmentsLoading,
    refresh: refreshAlignments,
  } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpAlignments({ workspace_id: workspaceId }),
      );
      if (err) throw err;
      return res ?? [];
    },
    { refreshDeps: [workspaceId] },
  );

  // 重建投影(幂等全量重算,资产后登记时补齐对象→资产边)
  const { run: rebuild, loading: rebuilding } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(rebuildEcpGraph(workspaceId));
      if (err) throw err;
      return res;
    },
    {
      manual: true,
      onSuccess: res => {
        message.success(
          `投影已重建：${res?.objects ?? 0} 个对象 → ${res?.edges ?? 0} 条边`,
        );
        refresh();
      },
      onError: e => message.error(String(e)),
    },
  );

  // LLM 语义对齐:推理知识实体 × 语义对象 → 候选入库(proposed,确认后才上图)
  const { run: runAlign, loading: aligning } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        runEcpAlignment(workspaceId, getUserId() ?? 'unknown'),
      );
      if (err) throw err;
      return res;
    },
    {
      manual: true,
      onSuccess: res => {
        const errs = res?.errors?.length ?? 0;
        message.success(
          `语义对齐完成：${res?.entities ?? 0} 个实体 → ${res?.candidates ?? 0} 条候选` +
            (errs ? `（${errs} 个批次失败）` : ''),
        );
        refreshAlignments();
        refresh();
      },
      onError: e => message.error(String(e)),
    },
  );

  // 候选人工决定:confirm 生效上图 / reject 永久静默(该实体不再被复跑提案)
  const { run: decideAlign, loading: deciding } = useRequest(
    async (payload: { id: number; action: 'confirm' | 'reject' }) => {
      const userId = getUserId() ?? 'unknown';
      const [err] = await apiInterceptors(
        payload.action === 'confirm'
          ? confirmEcpAlignment(payload.id, { user_id: userId })
          : rejectEcpAlignment(payload.id, { user_id: userId }),
      );
      if (err) throw err;
      return payload.action;
    },
    {
      manual: true,
      onSuccess: action => {
        message.success(
          action === 'confirm'
            ? '已确认，对齐边已生效'
            : '已拒绝，该实体不再重复提案',
        );
        refreshAlignments();
        refresh();
      },
      onError: e => message.error(String(e)),
    },
  );

  // 删除对齐记录(手工纠错;删除后 LLM 复跑可能再次提案)
  const { run: removeAlign } = useRequest(
    async (id: number) => {
      const [err] = await apiInterceptors(removeEcpAlignment(id));
      if (err) throw err;
      return id;
    },
    {
      manual: true,
      onSuccess: () => {
        message.success('已删除');
        refreshAlignments();
        refresh();
      },
      onError: e => message.error(String(e)),
    },
  );

  // 语义对象节点:点击时拉取完整详情(版本历史/证据/Payload)
  useRequest(
    async () => {
      if (!selected || nodeGroup(selected) !== 'object') return null;
      const [err, res] = await apiInterceptors(
        getEcpObject(selected.id, workspaceId),
      );
      if (err) return null;
      return res ?? null;
    },
    {
      refreshDeps: [selected?.id],
      ready: !!selected && nodeGroup(selected) === 'object',
      onSuccess: res => setObjectDetail(res),
    },
  );

  const counts = useMemo(() => {
    const c = { object: 0, asset: 0, kn: 0 } as Record<NodeGroup, number>;
    for (const n of data?.nodes ?? []) c[nodeGroup(n)] += 1;
    return c;
  }, [data]);

  const alignCount = (s: 'proposed' | 'confirmed' | 'rejected') =>
    (alignments ?? []).filter(a => a.status === s).length;
  const proposedCount = alignCount('proposed');
  const alignList = useMemo(
    () => (alignments ?? []).filter(a => a.status === alignFilter),
    [alignments, alignFilter],
  );

  const toggle = (g: NodeGroup) => {
    setHidden(prev => {
      const next = new Set(prev);
      if (next.has(g)) next.delete(g);
      else next.add(g);
      return next;
    });
  };

  if (loading) return <Spin style={{ display: 'block', margin: '64px auto' }} />;
  if (!data?.nodes?.length) {
    return (
      <EcpEmpty
        title="全景图为空"
        desc="入驻资源（数据源 / 文档 / 知识空间）与确认后的语义对象会在此成图：资源是锚点，语义对象是它长出的可信事实点"
      />
    );
  }

  const groupLabel: Record<NodeGroup, string> = {
    object: '语义对象',
    asset: '资产',
    kn: '知识层',
  };
  const groupDot: Record<NodeGroup, string> = {
    object: 'ecp-dot--entity',
    asset: 'ecp-dot--document',
    kn: 'ecp-dot--neutral',
  };

  return (
    <div className="ecp-panorama">
      <div className="ecp-panorama__toolbar">
        <div className="ecp-panorama__stats">
          {(['object', 'asset', 'kn'] as NodeGroup[]).map(g => (
            <button
              key={g}
              type="button"
              className={`ecp-panorama__stat${hidden.has(g) ? ' is-off' : ''}`}
              onClick={() => toggle(g)}
            >
              <Dot kind={groupDot[g]} />
              {groupLabel[g]}
              <span className="ecp-panorama__stat-num">{counts[g]}</span>
            </button>
          ))}
        </div>
        <Input.Search
          size="small"
          allowClear
          placeholder="实体检索（一跳邻域）"
          defaultValue={entityQuery}
          style={{ width: 190 }}
          onSearch={v => setEntityQuery(v.trim())}
        />
        <Tooltip title="LLM 推理知识实体与语义对象的语义对齐，产出候选（人工确认后才上图）；实体多时耗时数十秒">
          <Button
            size="small"
            icon={<ThunderboltOutlined />}
            loading={aligning}
            onClick={runAlign}
          >
            语义对齐
          </Button>
        </Tooltip>
        <Button size="small" onClick={() => setAlignOpen(true)}>
          对齐候选{proposedCount ? ` ${proposedCount}` : ''}
        </Button>
        <Tooltip title="全量重算物化边表（对象→对象边，供 Agent 图遍历与影响分析用；全景图本身实时投影，无需重建）">
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={rebuilding}
            onClick={rebuild}
          >
            重建投影
          </Button>
        </Tooltip>
      </div>

      <div className="ecp-graph">
        <div className="ecp-graph__legend">
          <div className="ecp-graph__legend-group">
            {(['entity', 'metric', 'relation', 'dimension', 'claim'] as const).map(
              tp => (
                <span key={tp} className="ecp-graph__legend-item">
                  <Dot kind={`ecp-dot--${tp === 'claim' ? 'document' : tp}`} />
                  {tp}
                </span>
              ),
            )}
          </div>
          <div className="ecp-graph__legend-group">
            {(['db', 'document', 'space'] as const).map(tp => (
              <span key={tp} className="ecp-graph__legend-item">
                <Dot kind={`ecp-dot--${tp}`} />
                {tp}
              </span>
            ))}
            <span className="ecp-graph__legend-item">
              <Dot kind="ecp-dot--neutral" />
              wiki / verbat
            </span>
          </div>
          <div className="ecp-graph__legend-hint">
            点击节点看详情 · 🟡 = proposed · 小资产 = 未登记引用 · aligns_to
            深色 = 已确认对齐 / 浅色 = LLM 候选 · 点击顶部统计可按层过滤
          </div>
        </div>
        <SigmaContainer style={{ height: '100%', width: '100%' }}>
          <GraphLoader
            data={data}
            hidden={hidden}
            onSelect={n => {
              setSelected(n);
              if (nodeGroup(n) !== 'object') setObjectDetail(null);
            }}
          />
        </SigmaContainer>
      </div>

      {/* 语义对象详情:复用完整抽屉(版本历史/证据/Payload) */}
      <ObjectDetailDrawer
        obj={objectDetail}
        open={!!selected && nodeGroup(selected) === 'object' && !!objectDetail}
        onClose={() => {
          setSelected(null);
          setObjectDetail(null);
        }}
        footer={
          <DeprecateFooter
            obj={objectDetail}
            onDone={() => {
              setSelected(null);
              setObjectDetail(null);
              refresh();
            }}
          />
        }
      />

      {/* 资产 / 知识层节点详情 */}
      <Drawer
        className="ecp-drawer"
        title={
          selected && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
              <Dot
                kind={
                  nodeGroup(selected) === 'asset'
                    ? `ecp-dot--${selected.obj_type}`
                    : 'ecp-dot--neutral'
                }
              />
              <span style={{ fontWeight: 650 }}>
                {selected.name ?? selected.id}
              </span>
            </span>
          )
        }
        width={520}
        open={
          !!selected && nodeGroup(selected) !== 'object'
        }
        onClose={() => setSelected(null)}
      >
        {selected && nodeGroup(selected) !== 'object' && (
          <AssetDetailContent node={selected} data={data} />
        )}
      </Drawer>

      {/* 对齐候选抽屉:LLM 推理产出的 实体↔对象 语义对齐,人工决定是否生效 */}
      <Drawer
        className="ecp-drawer"
        title="语义对齐候选"
        width={560}
        open={alignOpen}
        onClose={() => setAlignOpen(false)}
        extra={
          <Tooltip title="重新运行 LLM 推理（人工已决定过的实体自动跳过）">
            <Button
              size="small"
              icon={<ThunderboltOutlined />}
              loading={aligning}
              onClick={runAlign}
            >
              运行对齐
            </Button>
          </Tooltip>
        }
      >
        <Segmented
          size="small"
          block
          value={alignFilter}
          onChange={v => setAlignFilter(v as typeof alignFilter)}
          options={[
            { label: `待确认 ${alignCount('proposed')}`, value: 'proposed' },
            { label: `已确认 ${alignCount('confirmed')}`, value: 'confirmed' },
            { label: `已拒绝 ${alignCount('rejected')}`, value: 'rejected' },
          ]}
        />
        <List
          size="small"
          style={{ marginTop: 12 }}
          loading={alignmentsLoading}
          dataSource={alignList}
          locale={{
            emptyText:
              alignFilter === 'proposed'
                ? '暂无候选——点击「运行对齐」让 LLM 推理知识实体与语义对象的语义指向'
                : '暂无记录',
          }}
          renderItem={item => (
            <List.Item
              actions={
                item.status === 'proposed'
                  ? [
                      <Button
                        key="confirm"
                        size="small"
                        type="link"
                        icon={<CheckOutlined />}
                        loading={deciding}
                        onClick={() =>
                          decideAlign({ id: item.id, action: 'confirm' })
                        }
                      >
                        确认
                      </Button>,
                      <Button
                        key="reject"
                        size="small"
                        type="link"
                        danger
                        icon={<CloseOutlined />}
                        loading={deciding}
                        onClick={() =>
                          decideAlign({ id: item.id, action: 'reject' })
                        }
                      >
                        拒绝
                      </Button>,
                    ]
                  : [
                      <Popconfirm
                        key="remove"
                        title="删除该对齐记录？删除后 LLM 复跑可能再次提案"
                        onConfirm={() => removeAlign(item.id)}
                      >
                        <Button size="small" type="link" icon={<DeleteOutlined />}>
                          删除
                        </Button>
                      </Popconfirm>,
                    ]
              }
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>
                  {item.entity_name}
                  <span style={{ color: 'var(--ink-400)', fontWeight: 400 }}>
                    {' '}
                    →{' '}
                  </span>
                  {item.object_id}
                  {item.source === 'manual' && (
                    <Tag style={{ marginLeft: 8 }} color="blue">
                      人工
                    </Tag>
                  )}
                  {item.status === 'rejected' && (
                    <Tag style={{ marginLeft: 8 }}>已拒绝</Tag>
                  )}
                </div>
                <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
                  {item.confidence != null &&
                    `置信度 ${(item.confidence * 100).toFixed(0)}% · `}
                  {item.rationale || '—'}
                </div>
              </div>
            </List.Item>
          )}
        />
      </Drawer>
    </div>
  );
}
