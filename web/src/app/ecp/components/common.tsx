'use client';

import { apiInterceptors } from '@/client/api';
import {
  deprecateEcpObject,
  EcpLineage,
  EcpOrigin,
  EcpProposalView,
  EcpSemanticObject,
  EcpSqlPreview,
  getEcpObjectVersions,
  getEcpProposalView,
} from '@/client/api/ecp';
import { getUserId } from '@/utils';
import { useRequest } from 'ahooks';
import { App, Button, Drawer, Input, Popconfirm, Table, Tag, Tooltip } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import React, { useState } from 'react';

import '../ecp.css';

export const TYPE_DOT: Record<string, string> = {
  entity: 'ecp-dot--entity',
  metric: 'ecp-dot--metric',
  relation: 'ecp-dot--relation',
  dimension: 'ecp-dot--dimension',
  claim: 'ecp-dot--metric',
  terminology: 'ecp-dot--entity',
  policy: 'ecp-dot--relation',
};

const STATUS_DOT: Record<string, { dot: string; label: string }> = {
  confirmed: { dot: 'ecp-dot--success', label: 'confirmed' },
  proposed: { dot: 'ecp-dot--warning', label: 'proposed' },
  rejected: { dot: 'ecp-dot--danger', label: 'rejected' },
  deprecated: { dot: 'ecp-dot--neutral', label: 'deprecated' },
  superseded: { dot: 'ecp-dot--neutral', label: 'superseded' },
};

export function Dot({ kind }: { kind: string }) {
  return <span className={`ecp-dot ${kind}`} />;
}

export function StatusTag({ status }: { status: string }) {
  const meta = STATUS_DOT[status] ?? { dot: 'ecp-dot--neutral', label: status };
  return (
    <span className="ecp-status">
      <Dot kind={meta.dot} />
      {status === 'confirmed' ? `✅ ${meta.label}` : meta.label}
    </span>
  );
}

export function TypeChip({ type }: { type: string }) {
  return (
    <span className="ecp-type-chip">
      <Dot kind={TYPE_DOT[type] ?? 'ecp-dot--neutral'} />
      {type}
    </span>
  );
}

// ---------------------------------------------------------------- 来源徽章
const ORIGIN_COLOR: Record<string, string> = {
  discovery: 'blue',
  miss_learn: 'purple',
  manual_sql: 'cyan',
  rule5_gate: 'orange',
  edit: 'gold',
  agent: 'geekblue',
  import: 'green',
  legacy: 'default',
};

/** 提案来源徽章(MISS 学习/初始扫描/手工 SQL 等,中文标签由后端给)。 */
export function OriginBadge({ origin }: { origin?: EcpOrigin | null }) {
  if (!origin) return null;
  const tips = [
    origin.actor ? `发起: ${origin.actor}` : '',
    origin.note ?? '',
    origin.derived_from ? `派生: ${origin.derived_from}` : '',
    origin.legacy_source ? `原始 source: ${origin.legacy_source}` : '',
  ]
    .filter(Boolean)
    .join('\n');
  const badge = (
    <Tag color={ORIGIN_COLOR[origin.kind] ?? 'default'} style={{ marginInlineEnd: 0 }}>
      {origin.label}
    </Tag>
  );
  return tips ? (
    <Tooltip title={<span style={{ whiteSpace: 'pre-line' }}>{tips}</span>}>{badge}</Tooltip>
  ) : (
    badge
  );
}

// ---------------------------------------------------------------- 血缘 chips
/** 列表/卡片用的一行血缘:库名 · 表 + 引用对象(带状态点)。 */
export function LineageChips({ lineage }: { lineage?: EcpLineage | null }) {
  if (!lineage) return null;
  const ds =
    lineage.datasource_name ??
    (lineage.datasource_id != null ? `数据源#${lineage.datasource_id}` : null);
  return (
    <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
      {ds && <Tag color="blue">{ds}</Tag>}
      {lineage.tables.map(t => (
        <Tag key={t}>{t}</Tag>
      ))}
      {lineage.document?.doc_id && (
        <Tag color="green">
          文档 {lineage.document.doc_id}
          {lineage.document.anchor ? `@${lineage.document.anchor}` : ''}
        </Tag>
      )}
      {lineage.objects.map(o => (
        <Tag key={o.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Dot kind={o.status === 'confirmed' ? 'ecp-dot--success' : 'ecp-dot--warning'} />
          {o.id}
        </Tag>
      ))}
    </span>
  );
}

/** Natural-language-ish summary of a payload for list/cards. */
export function summarizePayload(obj: EcpSemanticObject): string {
  const p = obj.payload || {};
  if (obj.obj_type === 'entity') {
    const binding = p.binding || {};
    return `绑定表 ${binding.table ?? '?'}（PK: ${binding.pk ?? '?'}）· 默认过滤 ${(p.default_filters || []).join('; ') || '无'}`;
  }
  if (obj.obj_type === 'metric') {
    return `口径 ${p.expression ?? '?'} · 附加过滤 ${(p.extra_filters || []).join('; ') || '无'} · 粒度 ${(p.grain || []).join('/') || '未定义'} · 单位 ${p.unit ?? '-'}`;
  }
  if (obj.obj_type === 'relation') {
    return `join 路径 ${p.path ?? '?'}（${p.cardinality ?? '?'}）`;
  }
  if (obj.obj_type === 'dimension') {
    const values = (p.values || []).map((v: any) => v.label).join('、');
    return `维度列 ${p.column ?? '?'} · 值 ${values || '（待确认）'}`;
  }
  if (obj.obj_type === 'claim') {
    const binding = p.binding || {};
    return `${p.text ?? '?'} · 出处 ${binding.doc_id ?? '?'}${binding.anchor ? `@${binding.anchor}` : ''}`;
  }
  if (obj.obj_type === 'terminology') {
    return `定义 ${(p.definition ?? '?').slice(0, 80)} · 别名 ${(p.aliases || []).join('/') || '无'}`;
  }
  if (obj.obj_type === 'policy') {
    return `${p.rule ?? '?'} · 条件 ${p.condition ?? '通用'}`;
  }
  return '';
}

export function EcpEmpty({
  title,
  desc,
  action,
}: {
  title: string;
  desc?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="ecp-empty">
      <div className="ecp-empty__title">{title}</div>
      {desc && <div className="ecp-empty__desc">{desc}</div>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
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

const codeStyle: React.CSSProperties = {
  fontSize: 11,
  background: 'var(--bg-subtle)',
  padding: 8,
  borderRadius: 6,
  overflow: 'auto',
  maxHeight: 180,
  margin: '6px 0',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
};

// ------------------------------------------------------------ 业务定义(分类型)
function BusinessDefinition({ obj }: { obj: EcpSemanticObject }) {
  const p = obj.payload || {};
  if (obj.obj_type === 'metric') {
    return (
      <>
        <KV k="口径表达式" v={<code>{p.expression ?? '-'}</code>} />
        <KV k="附加过滤" v={(p.extra_filters || []).join('; ') || '无'} />
        <KV k="粒度" v={(p.grain || []).join(' / ') || '未定义'} />
        <KV k="单位" v={p.unit ?? '-'} />
      </>
    );
  }
  if (obj.obj_type === 'dimension') {
    const values = (p.values || []) as Array<{ label: string; aliases?: string[]; codes?: string[] }>;
    return (
      <>
        <KV k="维度列" v={<code>{p.column ?? '-'}</code>} />
        <div style={{ marginTop: 8 }}>
          <Table
            size="small"
            rowKey={r => r.label}
            pagination={false}
            dataSource={values}
            columns={[
              { title: '显示名 label', dataIndex: 'label', width: 140 },
              {
                title: '别名',
                dataIndex: 'aliases',
                width: 140,
                render: (a: string[]) => (a || []).join(' / ') || '-',
              },
              {
                title: '原始值 codes',
                dataIndex: 'codes',
                render: (c: string[]) => (c || []).join(', ') || '-',
              },
            ]}
          />
        </div>
      </>
    );
  }
  if (obj.obj_type === 'relation') {
    return (
      <>
        <KV k="连接" v={`${p.from ?? '?'} → ${p.to ?? '?'}`} />
        <KV k="join 路径" v={<code>{p.path ?? '（待确认人补全）'}</code>} />
        <KV k="基数" v={p.cardinality ?? '-'} />
      </>
    );
  }
  if (obj.obj_type === 'claim' || obj.obj_type === 'terminology' || obj.obj_type === 'policy') {
    return (
      <>
        <KV
          k={obj.obj_type === 'claim' ? '陈述' : obj.obj_type === 'terminology' ? '定义' : '规则'}
          v={p.text ?? p.definition ?? p.rule ?? '-'}
        />
        {p.condition && <KV k="适用条件" v={p.condition} />}
        {p.source_quote && <KV k="原文摘录" v={`「${p.source_quote}」`} />}
      </>
    );
  }
  // entity: 字段表由「数据血缘」区块承担,此处不再重复
  return null;
}

// ---------------------------------------------------------------- SQL 预览
function SqlPreviewSection({ preview }: { preview?: EcpSqlPreview | null }) {
  if (!preview) return null;
  return (
    <div className="ecp-drawer__section">
      <div className="ecp-drawer__section-title">SQL 生成效果（静态预览）</div>
      {preview.sql ? (
        <>
          <div style={{ fontSize: 12, color: 'var(--ink-400)', marginBottom: 4 }}>
            {preview.scenario}
          </div>
          <pre style={codeStyle}>{preview.sql}</pre>
          {!!preview.participants.length && (
            <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>
              参与组装：
              {preview.participants.map(pt => (
                <Tag key={pt.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <Dot kind={pt.status === 'confirmed' ? 'ecp-dot--success' : 'ecp-dot--warning'} />
                  {pt.id}
                  {pt.version != null ? `@v${pt.version}` : ''}
                </Tag>
              ))}
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>暂无法组装 SQL 预览</div>
      )}
      {!!preview.warnings.length && (
        <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12, color: 'var(--ink-600)' }}>
          {preview.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ------------------------------------------------------------ 数据血缘(字段级)
function LineageSection({ lineage }: { lineage?: EcpLineage | null }) {
  if (!lineage) return null;
  return (
    <div className="ecp-drawer__section">
      <div className="ecp-drawer__section-title">数据血缘（库 / 表 / 字段）</div>
      <div style={{ marginBottom: 8 }}>
        <LineageChips lineage={lineage} />
      </div>
      {!!lineage.columns.length && (
        <Table
          size="small"
          rowKey="column"
          pagination={false}
          dataSource={lineage.columns}
          columns={[
            { title: '字段', dataIndex: 'column', width: 140 },
            {
              title: '用途',
              dataIndex: 'usage',
              width: 150,
              render: (u: string) => u || '-',
            },
            {
              title: '业务含义',
              dataIndex: 'meaning',
              render: (m: string | null, row) =>
                row.declared ? (
                  m ?? <span style={{ color: 'var(--ink-400)' }}>未标注</span>
                ) : (
                  <Tag color="red">未在 entity.fields 声明（口径疑点）</Tag>
                ),
            },
            { title: 'role', dataIndex: 'role', width: 90, render: (r: string) => r ?? '-' },
          ]}
        />
      )}
    </div>
  );
}

// ------------------------------------------------------------ 来源与证据
function OriginSection({ view }: { view: EcpProposalView }) {
  const { origin, evidence } = view;
  const hasOriginSql = !!origin.origin_sql?.length;
  if (!hasOriginSql && !origin.miss_ref && !evidence.length) return null;
  return (
    <div className="ecp-drawer__section">
      <div className="ecp-drawer__section-title">来源与证据</div>
      {hasOriginSql && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
            原始 SQL（{origin.label}快照，确认人可核对提炼是否忠实）：
          </div>
          {origin.origin_sql.map((sql, i) => (
            <pre key={i} style={codeStyle}>
              {sql}
            </pre>
          ))}
        </div>
      )}
      {origin.miss_ref && (
        <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 8 }}>
          MISS 聚类回链：kind={origin.miss_ref.kind ?? '?'} · pattern=
          {origin.miss_ref.pattern ?? '?'} · 数据源#
          {origin.miss_ref.datasource_id ?? '?'}（可在「巡检 / MISS」中查完整学习轨迹）
        </div>
      )}
      {evidence.map((ev, i) => (
        <div key={i} className="ecp-proposal__evidence" style={{ marginTop: i ? 8 : 0 }}>
          {ev.source ?? '来源未知'}：{ev.quote ?? ''}
        </div>
      ))}
    </div>
  );
}

export function ObjectDetailContent({ obj }: { obj: EcpSemanticObject | null }) {
  const { data: versions } = useRequest(
    async () => {
      if (!obj) return [];
      const [err, res] = await apiInterceptors(
        getEcpObjectVersions(obj.id, obj.workspace_id),
      );
      return err ? [] : res ?? [];
    },
    { refreshDeps: [obj?.id], ready: !!obj },
  );

  // 业务视图(读时派生:summary/origin/lineage/sql_preview);失败降级 obj.view/无视图
  const { data: view } = useRequest(
    async () => {
      if (!obj) return null;
      const [err, res] = await apiInterceptors(
        getEcpProposalView(obj.id, obj.version, obj.workspace_id),
      );
      return err ? (obj.view ?? null) : (res ?? obj.view ?? null);
    },
    { refreshDeps: [obj?.id, obj?.version], ready: !!obj },
  );

  if (!obj) return null;
  const p = obj.payload || {};
  return (
    <>
      <div className="ecp-drawer__section">
        <div className="ecp-drawer__section-title">基本信息</div>
        <KV k="状态" v={<StatusTag status={obj.status} />} />
        <KV k="名称" v={obj.name ?? '-'} />
        <KV k="别名" v={(p.aliases || []).join(' / ') || '-'} />
        <KV k="说明" v={view?.summary || summarizePayload(obj)} />
        <KV
          k="来源"
          v={view?.origin ? <OriginBadge origin={view.origin} /> : (obj.source ?? '-')}
        />
        <KV
          k="确认"
          v={obj.confirmed_by ? `${obj.confirmed_by} @ ${obj.confirmed_at ?? ''}` : '未确认'}
        />
      </div>

      <div className="ecp-drawer__section">
        <div className="ecp-drawer__section-title">业务定义</div>
        <BusinessDefinition obj={obj} />
        {obj.obj_type === 'entity' && !view?.lineage && (
          <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>字段表见数据血缘区块</div>
        )}
      </div>

      <LineageSection lineage={view?.lineage} />

      <SqlPreviewSection preview={view?.sql_preview} />

      {view && <OriginSection view={view} />}

      <div className="ecp-drawer__section">
        <div className="ecp-drawer__section-title">版本历史</div>
        <Table
          size="small"
          rowKey="version"
          pagination={false}
          dataSource={versions ?? []}
          columns={[
            { title: 'v', dataIndex: 'version', width: 48 },
            {
              title: '状态',
              dataIndex: 'status',
              width: 150,
              render: (s: string) => <StatusTag status={s} />,
            },
            { title: '创建', dataIndex: 'created_by', width: 90 },
            { title: '时间', dataIndex: 'created_at', ellipsis: true },
            {
              title: 'supersedes',
              dataIndex: 'supersedes',
              width: 100,
              render: (v: number | null) => v ?? '-',
            },
          ]}
        />
      </div>
    </>
  );
}

export function ObjectDetailDrawer({
  obj,
  open,
  onClose,
  footer,
}: {
  obj: EcpSemanticObject | null;
  open: boolean;
  onClose: () => void;
  footer?: React.ReactNode;
}) {
  if (!obj) return null;
  return (
    <Drawer
      className="ecp-drawer"
      title={
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          <TypeChip type={obj.obj_type} />
          <span style={{ fontWeight: 650 }}>{obj.id}</span>
          <span style={{ color: 'var(--ink-400)', fontSize: 12 }}>v{obj.version}</span>
        </span>
      }
      width={640}
      open={open}
      onClose={onClose}
      footer={footer}
    >
      <ObjectDetailContent obj={obj} />
    </Drawer>
  );
}

export function DeprecateFooter({
  obj,
  onDone,
}: {
  obj: EcpSemanticObject | null;
  onDone?: () => void;
}) {
  const { message } = App.useApp();
  const [reason, setReason] = useState('');
  const { run: deprecate, loading } = useRequest(
    async () => {
      if (!obj) return;
      const user_id = getUserId() ?? 'unknown';
      const [err] = await apiInterceptors(
        deprecateEcpObject(obj.id, {
          user_id,
          workspace_id: obj.workspace_id,
          reason: reason || undefined,
        }),
      );
      if (err) throw err;
      message.success(`已弃用 ${obj.id}`);
      onDone?.();
    },
    { manual: true },
  );

  if (!obj || obj.status !== 'confirmed') return null;
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Input
        placeholder="弃用原因（可选）"
        size="small"
        value={reason}
        onChange={e => setReason(e.target.value)}
        style={{ flex: 1 }}
      />
      <Popconfirm
        title="弃用该语义口径？"
        description="弃用后将不再被目录/查询消费，需确认人权限。"
        okText="弃用"
        cancelText="取消"
        okButtonProps={{ danger: true, loading }}
        onConfirm={() => deprecate()}
      >
        <Button size="small" danger icon={<DeleteOutlined />} loading={loading}>
          弃用
        </Button>
      </Popconfirm>
    </div>
  );
}
