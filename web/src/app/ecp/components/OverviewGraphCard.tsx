'use client';

import { apiInterceptors } from '@/client/api';
import { EcpGraph, EcpGraphNode, getEcpGraph } from '@/client/api/ecp';
import { useLoadGraph, SigmaContainer } from '@react-sigma/core';
import '@react-sigma/core/lib/style.css';
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import { useRequest } from 'ahooks';
import { Spin } from 'antd';
import { useEffect, useMemo } from 'react';

import { Dot, EcpEmpty } from './common';

// 与 GraphTab 严格对齐的节点色板（同一来源，保证总览与全景图一致）
const OBJECT_HEX: Record<string, string> = {
  entity: '#4f46e5',
  metric: '#22c55e',
  relation: '#f59e0b',
  dimension: '#722ed1',
  claim: '#06b6d4',
  terminology: '#3b82f6',
  policy: '#ef4444',
};
const ASSET_HEX: Record<string, string> = {
  db: '#4f46e5',
  document: '#06b6d4',
  space: '#22c55e',
  api: '#f59e0b',
};
const KN_HEX = '#8a92a6';
const MAX_NODES = 220;

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

function MiniLoader({ data }: { data: EcpGraph }) {
  const loadGraph = useLoadGraph();
  useEffect(() => {
    const nodes = data.nodes.slice(0, MAX_NODES);
    const visibleIds = new Set(nodes.map(n => n.id));
    const graph: any = new Graph();
    const degrees = new Map<string, number>();
    for (const l of data.links) {
      if (!visibleIds.has(l.source) || !visibleIds.has(l.target)) continue;
      degrees.set(l.source, (degrees.get(l.source) || 0) + 1);
      degrees.set(l.target, (degrees.get(l.target) || 0) + 1);
    }
    const maxDegree = Math.max(1, ...degrees.values());
    for (const n of nodes) {
      const degree = degrees.get(n.id) || 0;
      graph.addNode(n.id, {
        label: n.name ?? n.id,
        size: 2.5 + Math.sqrt(degree / maxDegree) * 3.5,
        color: nodeColor(n),
        x: Math.random() * 100,
        y: Math.random() * 100,
      });
    }
    for (const l of data.links) {
      if (!visibleIds.has(l.source) || !visibleIds.has(l.target)) continue;
      const key = `${l.source}-[${l.edge_type}]->${l.target}`;
      if (!graph.hasEdge(key)) {
        graph.addEdgeWithKey(key, l.source, l.target, {
          size: 0.5,
          color: '#cbd5e1',
        });
      }
    }
    if (graph.order > 1) {
      forceAtlas2.assign(graph, {
        iterations: 50,
        settings: {
          ...forceAtlas2.inferSettings(graph),
          gravity: 1,
          strongGravityMode: true,
          barnesHutOptimize: graph.order > 60,
        },
      });
    }
    loadGraph(graph);
  }, [data, loadGraph]);
  return null;
}

/** 总览里的「全景图速览」小卡片：迷你 sigma 图 + 分层统计 + 跳转全景图。 */
export default function OverviewGraphCard({
  workspaceId,
  onGoGraph,
}: {
  workspaceId: string;
  onGoGraph: () => void;
}) {
  const { data, loading } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getEcpGraph(workspaceId));
      if (err) throw err;
      return res;
    },
    { refreshDeps: [workspaceId] },
  );

  const counts = useMemo(() => {
    const c = { object: 0, asset: 0, kn: 0 } as Record<NodeGroup, number>;
    for (const n of data?.nodes ?? []) c[nodeGroup(n)] += 1;
    return c;
  }, [data]);

  return (
    <div className="ecp-card">
      <div className="ecp-card__title">
        <span>全景图速览</span>
        <span className="ecp-card__title-link" onClick={onGoGraph}>
          查看全景图 →
        </span>
      </div>
      {loading ? (
        <Spin style={{ display: 'block', margin: '64px auto' }} />
      ) : !data?.nodes?.length ? (
        <EcpEmpty
          title="全景图为空"
          desc="接入数据资产并确认业务口径后，这里会形成语义关系图"
        />
      ) : (
        <div className="ecp-overview-graph">
          <div className="ecp-overview-graph__stats">
            <span className="ecp-status">
              <Dot kind="ecp-dot--entity" /> 语义对象 {counts.object}
            </span>
            <span className="ecp-status">
              <Dot kind="ecp-dot--document" /> 资产 {counts.asset}
            </span>
            <span className="ecp-status">
              <Dot kind="ecp-dot--neutral" /> 知识层 {counts.kn}
            </span>
          </div>
          <div className="ecp-overview-graph__canvas" style={{ height: 240 }}>
            <SigmaContainer style={{ height: '100%', width: '100%' }}>
              <MiniLoader data={data} />
            </SigmaContainer>
          </div>
        </div>
      )}
    </div>
  );
}
