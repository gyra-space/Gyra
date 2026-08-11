'use client';

/** ECP 提案确认 -- 在场景空间中间内容区域展示(非抽屉)。

 * 由 SceneSpace 的 'ecp-proposal' 上下文渲染。点击左侧 rail 的 ECP 提案待办 ->
 * shell handlePreview -> detailContext='ecp-proposal' -> 本组件。
 * source_id 由后端构造为 `{ecp_ws}:{obj.id}@v{version}`,解析后定位到**该具体版本**
 * (待办指向的 proposed 版本),而非 getEcpObject 的"最新 confirmed/最新版本"--
 * 否则可能取到已确认版本,确认时报 "not in proposed"。仅在 status=proposed 时
 * 允许确认/否决;已处理则提示并刷新收件箱消除陈旧待办。
 */
import { apiInterceptors } from '@/client/api';
import {
  confirmEcpObject,
  debugEcpObject,
  getEcpObjectVersions,
  listEcpObjects,
  rejectEcpObject,
  type EcpDebugPreview,
  type EcpSemanticObject,
} from '@/client/api/ecp';
import { ObjectDetailContent, StatusTag, TypeChip } from '@/app/ecp/components/common';
import { getUserId } from '@/utils';
import {
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import {
  App,
  Button,
  DatePicker,
  Input,
  InputNumber,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useEffect, useRef, useState } from 'react';

import { parseEcpProposalSource } from './scene-task-rail';

export interface EcpProposalDetailProps {
  sourceId: string;
  /** 确认/否决/发现陈旧待办后回调(shell bump inboxTick -> rail 刷新待办)。 */
  onResolved: () => void;
  /** 返回大厅。 */
  onBack: () => void;
}

const DOC_TYPES = ['claim', 'terminology', 'policy'];

/** 试跑筛选条件的一行:维度 + 值(标签/编码) + 包含/排除。 */
interface DebugFilterRow {
  key: number;
  dim_id: string;
  values: string[];
  mode: 'include' | 'exclude';
}

/** 确认前调试验证区:按提案版本只读试跑真实数据(trust=preview,永不 verified)。 */
function DebugPreviewPanel({ obj }: { obj: EcpSemanticObject }) {
  const { message } = App.useApp();
  const isDoc = DOC_TYPES.includes(obj.obj_type);
  const isMetric = obj.obj_type === 'metric';

  // 工作空间已登记的维度(任意状态),用于分组/筛选下拉选择
  const { data: dims } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpObjects({
          workspace_id: obj.workspace_id,
          obj_type: 'dimension',
          page_size: 200,
        }),
      );
      return err ? [] : res?.items ?? [];
    },
    { refreshDeps: [obj?.id], ready: !!obj },
  );

  const [groupBy, setGroupBy] = useState<string[]>([]);
  const [filterRows, setFilterRows] = useState<DebugFilterRow[]>([]);
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [timeColumn, setTimeColumn] = useState('');
  const [limit, setLimit] = useState<number>(20);

  // 提案默认分组:指标 grain(维度列名/维度名/维度 id)匹配工作空间维度后自动带入,
  // 确认人无需手填即可先试跑提案本身的口径。
  const defaultGroupBy = (): string[] => {
    if (!isMetric) return [];
    const grain: string[] = (obj.payload?.grain as string[]) || [];
    if (!grain.length || !dims?.length) return [];
    const g = grain.map((x) => String(x).toLowerCase());
    return (dims || [])
      .filter((d) => {
        const candidates = [d.id, d.name, d.payload?.column]
          .filter(Boolean)
          .map((v) => String(v).toLowerCase());
        const aliases = ((d.payload?.aliases as string[]) || []).map((a) => String(a).toLowerCase());
        return g.some((item) => candidates.includes(item) || aliases.includes(item));
      })
      .map((d) => d.id);
  };

  // 首次进入自动带入提案默认分组(仅在用户尚未手动调整前生效一次)。
  const prefillDone = useRef(false);
  useEffect(() => {
    if (prefillDone.current || !dims?.length) return;
    const matched = defaultGroupBy();
    if (matched.length) setGroupBy(matched);
    prefillDone.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dims]);

  const dimOptions = (dims || []).map((d) => ({
    label: d.name ? `${d.name} · ${d.id}` : d.id,
    value: d.id,
  }));

  const { run, loading, data } = useRequest(
    async () => {
      const filters = filterRows
        .filter((r) => r.dim_id)
        .map((r) => ({ dim_id: r.dim_id, values: r.values, mode: r.mode }));
      const [err, res] = await apiInterceptors(
        debugEcpObject(obj.id, obj.version, {
          workspace_id: obj.workspace_id,
          group_by: groupBy.length ? groupBy : undefined,
          filters: filters.length ? filters : undefined,
          time_range: timeRange
            ? {
                range: `${timeRange[0].format('YYYY-MM-DD')}~${timeRange[1].format('YYYY-MM-DD')}`,
                ...(timeColumn.trim() ? { column: timeColumn.trim() } : {}),
              }
            : undefined,
          limit,
        }),
      );
      if (err) {
        message.error(err.message);
        return null;
      }
      return res ?? null;
    },
    { manual: true },
  );

  const preview: EcpDebugPreview | null = data ?? null;

  const addFilterRow = () =>
    setFilterRows((prev) => [
      ...prev,
      { key: Date.now() + Math.random(), dim_id: '', values: [], mode: 'include' },
    ]);

  const resetParams = () => {
    setGroupBy(defaultGroupBy());
    setFilterRows([]);
    setTimeRange(null);
    setTimeColumn('');
    setLimit(20);
  };

  return (
    <div className="ecp-drawer__section" style={{ marginTop: 16 }}>
      <div className="ecp-drawer__section-title">
        <ExperimentOutlined style={{ marginRight: 6 }} />
        调试验证（试跑真实数据）
      </div>

      {!isDoc && (
        <div style={{ display: 'grid', gap: 10, marginBottom: 12 }}>
          {/* 分组维度:下拉多选,也允许直接输入维度 id */}
          <Space size={8} wrap align="baseline">
            <span style={{ width: 110, color: 'var(--ink-500)', fontSize: 12 }}>
              分组维度 group_by
            </span>
            <Select
              size="small"
              mode="tags"
              style={{ minWidth: 300, flex: 1 }}
              placeholder="选择或输入维度 id(可多选)"
              value={groupBy}
              onChange={(v: string[]) => setGroupBy(v)}
              options={dimOptions}
              showSearch
              filterOption={(input, option) =>
                String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Space>

          {/* 筛选条件:结构化行,无需手写 JSON */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ width: 110, color: 'var(--ink-500)', fontSize: 12 }}>
                筛选条件 filters
              </span>
              <Button
                size="small"
                type="dashed"
                icon={<PlusOutlined />}
                onClick={addFilterRow}
              >
                添加筛选
              </Button>
            </div>
            {filterRows.length === 0 ? (
              <div style={{ color: 'var(--ink-400)', fontSize: 12, paddingLeft: 118 }}>
                不筛选时直接试跑指标原始口径;也可按维度添加筛选核对。
              </div>
            ) : (
              filterRows.map((row) => {
                const dict = (
                  (dims || []).find((d) => d.id === row.dim_id)?.payload?.values || []
                ) as Array<{ label: string }>;
                return (
                  <Space key={row.key} size={6} wrap style={{ marginBottom: 6, paddingLeft: 118 }}>
                    <Select
                      size="small"
                      showSearch
                      mode="tags"
                      maxCount={1}
                      style={{ minWidth: 180 }}
                      placeholder="维度"
                      value={row.dim_id ? [row.dim_id] : []}
                      onChange={(v: string[]) =>
                        setFilterRows((prev) =>
                          prev.map((r) =>
                            r.key === row.key ? { ...r, dim_id: v[v.length - 1] ?? '' } : r,
                          ),
                        )
                      }
                      options={dimOptions}
                    />
                    <Select
                      size="small"
                      mode="tags"
                      style={{ minWidth: 180 }}
                      placeholder={dict.length ? '选择或输入值' : '输入值(或编码)'}
                      value={row.values}
                      onChange={(v: string[]) =>
                        setFilterRows((prev) =>
                          prev.map((r) => (r.key === row.key ? { ...r, values: v } : r)),
                        )
                      }
                      options={dict.map((v) => ({ label: v.label, value: v.label }))}
                    />
                    <Select
                      size="small"
                      style={{ width: 110 }}
                      value={row.mode}
                      onChange={(v: 'include' | 'exclude') =>
                        setFilterRows((prev) =>
                          prev.map((r) => (r.key === row.key ? { ...r, mode: v } : r)),
                        )
                      }
                      options={[
                        { label: '包含 include', value: 'include' },
                        { label: '排除 exclude', value: 'exclude' },
                      ]}
                    />
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() =>
                        setFilterRows((prev) => prev.filter((r) => r.key !== row.key))
                      }
                    />
                  </Space>
                );
              })
            )}
          </div>

          {/* 时间范围:日期选择器 + 可选时间列 */}
          <Space size={8} wrap align="baseline">
            <span style={{ width: 110, color: 'var(--ink-500)', fontSize: 12 }}>
              时间范围 time_range
            </span>
            <DatePicker.RangePicker
              size="small"
              value={timeRange}
              onChange={(v) =>
                setTimeRange(v && v[0] && v[1] ? [v[0], v[1]] : null)
              }
            />
            <Input
              size="small"
              placeholder="时间列(可选)"
              style={{ width: 140 }}
              value={timeColumn}
              onChange={(e) => setTimeColumn(e.target.value)}
            />
            <span style={{ color: 'var(--ink-400)', fontSize: 12 }}>limit</span>
            <InputNumber
              size="small"
              min={1}
              max={200}
              value={limit}
              onChange={(v) => setLimit(v ?? 20)}
              style={{ width: 80 }}
            />
          </Space>
        </div>
      )}

      <Space size={8} wrap>
        <Button
          type="primary"
          size="small"
          icon={<ExperimentOutlined />}
          loading={loading}
          onClick={() => run()}
        >
          {isDoc ? '校验出处（anchor 回放）' : '试跑'}
        </Button>
        {!isDoc && (
          <Button size="small" onClick={resetParams}>
            重置参数
          </Button>
        )}
        {!isDoc && (
          <span style={{ color: 'var(--ink-400)', fontSize: 12 }}>
            参数均为可选,留空即按提案口径直接试跑
          </span>
        )}
      </Space>

      {preview && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
            <Tag color={preview.ok ? 'blue' : 'red'}>
              {preview.ok ? '试跑成功' : '试跑失败'}
            </Tag>
            <Tag>{preview.trust === 'preview' ? 'preview（未验证，仅供核对）' : preview.trust}</Tag>
            {preview.row_count > 0 && <Tag>返回 {preview.row_count} 行</Tag>}
            {typeof preview.anchor_verified === 'boolean' && (
              <Tag color={preview.anchor_verified ? 'green' : 'orange'}>
                出处{preview.anchor_verified ? '已匹配' : '漂移'}
              </Tag>
            )}
          </div>

          {preview.error && (
            <div style={{ color: 'var(--err-600)', fontSize: 12, marginBottom: 8 }}>
              错误：{preview.error}
            </div>
          )}

          {preview.warnings.length > 0 && (
            <ul
              style={{
                margin: '0 0 8px',
                paddingLeft: 18,
                fontSize: 12,
                color: 'var(--ink-600)',
              }}
            >
              {preview.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}

          {typeof preview.anchor_verified === 'boolean' && preview.quote && (
            <div
              style={{
                fontSize: 12,
                color: preview.anchor_verified ? 'var(--ink-600)' : 'var(--err-600)',
                marginBottom: 8,
                background: 'var(--bg-subtle)',
                padding: 8,
                borderRadius: 6,
              }}
            >
              冻结摘录：&ldquo;{preview.quote}&rdquo;
            </div>
          )}

          {preview.sql && (
            <pre
              style={{
                fontSize: 11,
                background: 'var(--bg-subtle)',
                padding: 8,
                borderRadius: 6,
                overflow: 'auto',
                maxHeight: 160,
              }}
            >
              {preview.sql}
            </pre>
          )}

          {preview.columns.length > 0 && (
            <Table
              size="small"
              rowKey={(_, i) => String(i)}
              pagination={{ pageSize: 10, showSizeChanger: false }}
              columns={preview.columns.map((c) => ({ title: c, dataIndex: c, ellipsis: true }))}
              dataSource={preview.rows}
              scroll={{ x: 'max-content' }}
            />
          )}
        </div>
      )}
    </div>
  );
}

export function EcpProposalDetail({ sourceId, onResolved, onBack }: EcpProposalDetailProps) {
  // 用 App.useApp() 取 message,避免静态 message 无法消费 antd 上下文主题的告警
  // (根 layout 已用 <App> 包裹)。
  const { message } = App.useApp();
  const parsed = parseEcpProposalSource(sourceId);

  // 取该提案全部版本,定位到 source_id 指定的具体版本(待办指向的 proposed 版本)。
  const { data: versions, loading } = useRequest(
    async () => {
      if (!parsed) return [];
      const [err, res] = await apiInterceptors(
        getEcpObjectVersions(parsed.objId, parsed.workspaceId),
      );
      if (err) {
        message.error(err.message);
        return [];
      }
      return res ?? [];
    },
    { refreshDeps: [sourceId], ready: !!parsed },
  );
  const obj = parsed
    ? (versions || []).find((v) => v.version === parsed.version) ?? null
    : null;

  // 提案已离开 proposed(已确认/否决/废弃)-> 待办陈旧,刷新收件箱让其消除,不报错。
  useEffect(() => {
    if (obj && obj.status !== 'proposed') {
      onResolved();
    }
  }, [obj?.status]);

  const { run: settle, loading: settling } = useRequest(
    async (action: 'confirm' | 'reject') => {
      if (!obj) return;
      const userId = String(getUserId() ?? 'unknown');
      const api = action === 'confirm' ? confirmEcpObject : rejectEcpObject;
      const [err] = await apiInterceptors(
        api(obj.id, obj.version, { user_id: userId, workspace_id: obj.workspace_id }),
      );
      if (err) {
        message.error(err.message);
        return;
      }
      message.success(
        action === 'confirm' ? `已确认 ${obj.id}，该口径即刻生效` : `已否决 ${obj.id}`,
      );
      onResolved();
      onBack();
    },
    { manual: true },
  );

  if (!parsed) {
    return (
      <div className="ws-scene-space__body">
        <div className="ws-preview">
          <div className="ws-preview__head">
            <span className="ws-preview__title">提案信息无法解析</span>
          </div>
        </div>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="ws-scene-space__body">
        <Spin style={{ display: 'block', margin: '64px auto' }} />
      </div>
    );
  }
  if (!obj) {
    return (
      <div className="ws-scene-space__body">
        <div className="ws-preview">
          <div className="ws-preview__head">
            <span className="ws-preview__title">提案未找到（可能已被删除）</span>
          </div>
        </div>
      </div>
    );
  }

  const header = (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
      <TypeChip type={obj.obj_type} />
      <span style={{ fontWeight: 650 }}>{obj.id}</span>
      <span style={{ color: 'var(--ink-400)', fontSize: 12 }}>v{obj.version}</span>
    </div>
  );

  if (obj.status !== 'proposed') {
    return (
      <div className="ws-scene-space__body">
        {header}
        <div className="ws-preview">
          <div className="ws-preview__head">
            <span className="ws-preview__title">该提案已处理</span>
          </div>
          <div style={{ marginTop: 8 }}>
            当前状态：<StatusTag status={obj.status} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ws-scene-space__body">
      {header}
      <ObjectDetailContent obj={obj} />
      <DebugPreviewPanel obj={obj} />
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
        <Popconfirm title="否决该提案？" onConfirm={() => settle('reject')}>
          <Button danger icon={<CloseOutlined />} loading={settling}>
            否决
          </Button>
        </Popconfirm>
        <Button
          type="primary"
          icon={<CheckOutlined />}
          loading={settling}
          onClick={() => settle('confirm')}
        >
          确认生效
        </Button>
      </div>
    </div>
  );
}
