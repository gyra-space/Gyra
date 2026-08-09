'use client';

import { apiInterceptors } from '@/client/api';
import {
  EcpAssetRef,
  EcpReadiness,
  deleteEcpAsset,
  generateEcpProposals,
  getEcpProposalTask,
  getEcpReadiness,
  getEcpWorkspaceConfig,
  listEcpAssets,
  registerEcpAsset,
} from '@/client/api/ecp';
import { createSpace, listSpaces } from '@/client/api/knowledge-vault';
import { getDbList, getDbSupportType } from '@/client/api/request';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  ExportOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { Alert, App, Button, Input, Modal, Popconfirm, Select, Space, Spin, Tooltip } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import DatabaseAddModal from '@/app/database/components/DatabaseAddModal';

import { Dot, EcpEmpty } from './common';

const KIND_META: Record<string, { icon: React.ReactNode; label: string }> = {
  db: { icon: <DatabaseOutlined />, label: 'DB 数据源' },
  space: { icon: <FileTextOutlined />, label: '知识空间' },
  document: { icon: <FileTextOutlined />, label: '文档' },
  api: { icon: <ApiOutlined />, label: 'API' },
};

function ReadinessList({ readiness }: { readiness: EcpReadiness }) {
  return (
    <div style={{ marginTop: 10 }}>
      {readiness.checks.map(c => (
        <div
          key={c.item}
          style={{ display: 'flex', gap: 8, fontSize: 12, padding: '3px 0' }}
        >
          {c.ready ? (
            <CheckCircleOutlined style={{ color: 'var(--success)' }} />
          ) : (
            <CloseCircleOutlined style={{ color: 'var(--danger)' }} />
          )}
          <span style={{ color: 'var(--ink-500)' }}>
            {c.item}: {c.detail ?? ''}
          </span>
        </div>
      ))}
    </div>
  );
}

function resolveAssetTitle(
  asset: EcpAssetRef,
  dbList?: any[],
  spaceList?: any[],
): { title: string; subtitle: string } {
  const meta = KIND_META[asset.kind] ?? { icon: null, label: asset.kind };
  const refMeta = asset.ref_meta || {};

  if (asset.kind === 'db') {
    const db = dbList?.find(d => String(d.id) === asset.ref_id);
    const dbName = refMeta.name || refMeta.db_name || db?.name || db?.db_name || asset.ref_id;
    const dbType = refMeta.db_type || db?.db_type || '';
    return {
      title: dbName,
      subtitle: dbType ? `${meta.label} · ${dbType}` : meta.label,
    };
  }

  if (asset.kind === 'space') {
    const space = spaceList?.find(s => s.slug === asset.ref_id);
    const name = refMeta.name || space?.name || asset.ref_id;
    return { title: name, subtitle: meta.label };
  }

  if (asset.kind === 'document') {
    return {
      title: refMeta.name || asset.ref_id,
      subtitle: meta.label,
    };
  }

  return { title: refMeta.name || meta.label, subtitle: asset.ref_id };
}

function AssetCard({
  asset,
  onGenerate,
  onDelete,
  disabled,
  deleting,
  index,
  dbList,
  spaceList,
}: {
  asset: EcpAssetRef;
  onGenerate: (a: EcpAssetRef) => void;
  onDelete: (a: EcpAssetRef) => void;
  disabled?: boolean;
  deleting: boolean;
  index: number;
  dbList?: any[];
  spaceList?: any[];
}) {
  const [readiness, setReadiness] = useState<EcpReadiness | null>(null);
  const { run: check, loading: checking } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getEcpReadiness(Number(asset.ref_id), asset.workspace_id),
      );
      if (err) throw err;
      setReadiness(res ?? null);
    },
    { manual: true },
  );

  const meta = KIND_META[asset.kind] ?? { icon: null, label: asset.kind };
  const { title, subtitle } = resolveAssetTitle(asset, dbList, spaceList);
  return (
    <div className={`ecp-card ecp-rise ecp-rise--${(index % 4) + 1}`} style={{ marginTop: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span
          style={{
            width: 34,
            height: 34,
            borderRadius: 10,
            background: 'var(--bg-fill)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--ink-500)',
            fontSize: 16,
          }}
        >
          {meta.icon}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>
            {title}
          </div>
          <code style={{ fontSize: 12, color: 'var(--ink-400)' }}>{subtitle}</code>
        </div>
        <span className="ecp-status">
          <Dot kind={asset.status === 'active' ? 'ecp-dot--success' : 'ecp-dot--neutral'} />
          {asset.status}
        </span>
        <Popconfirm
          title="移除该资产引用？"
          description="仅从 ECP 工作空间移除引用，不会删除原始数据源/空间。"
          okText="移除"
          cancelText="取消"
          okButtonProps={{ danger: true, loading: deleting }}
          onConfirm={() => onDelete(asset)}
        >
          <Button
            size="small"
            type="text"
            danger
            icon={<DeleteOutlined />}
            loading={deleting}
          />
        </Popconfirm>
      </div>

      <div
        style={{
          marginTop: 10,
          fontSize: 12,
          color: 'var(--ink-400)',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>最近检查 {asset.last_checked_at ?? '从未'}</span>
      </div>

      {asset.kind === 'db' && readiness && <ReadinessList readiness={readiness} />}

      {asset.kind === 'db' && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <Button size="small" loading={checking} onClick={() => check()}>
            就绪检查
          </Button>
          <Button
            size="small"
            type="primary"
            ghost
            icon={<ExperimentOutlined />}
            disabled={disabled}
            onClick={() => onGenerate(asset)}
          >
            生成提案
          </Button>
        </div>
      )}
    </div>
  );
}

/** Asset layer: references to original assets (ECP owns refs, not assets). */
export default function AssetsTab({ workspaceId }: { workspaceId: string }) {
  const { message } = App.useApp();
  const [registerOpen, setRegisterOpen] = useState(false);
  const [kind, setKind] = useState<string>('db');
  const [refId, setRefId] = useState<string>();
  const [genAsset, setGenAsset] = useState<EcpAssetRef | null>(null);
  const [domainHint, setDomainHint] = useState<string>();
  const [genReadiness, setGenReadiness] = useState<EcpReadiness | null>(null);
  // 页面级生成进度条:生成提案耗时长,不在卡片/弹窗里原地转圈,改为页面顶部进度条展示
  const [genTask, setGenTask] = useState<{ label: string } | null>(null);
  // 资源闭环:登记 Modal 内内联创建(数据库/知识空间)
  const [addDbOpen, setAddDbOpen] = useState(false);
  const [newSpaceSlug, setNewSpaceSlug] = useState('');
  const [creatingSpace, setCreatingSpace] = useState(false);

  // 异步提案任务轮询计时器(卸载时清理)。
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(
    () => () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    },
    [],
  );

  // 提交后轮询任务状态直到终态,返回最终任务记录(加载中更新顶部进度条文案)。
  const waitForTask = useCallback(
    async (taskId: string, label: string): Promise<any> => {
      return new Promise(resolve => {
        const done = (res: any) => {
          if (pollTimer.current) clearInterval(pollTimer.current);
          setGenTask(null);
          resolve(res);
        };
        const tick = async () => {
          const [err, res] = await apiInterceptors(getEcpProposalTask(taskId));
          if (err) {
            done({ error: err.message || '任务查询失败' });
            return;
          }
          if (
            res?.status === 'completed' ||
            res?.status === 'failed' ||
            res?.status === 'timeout' ||
            res?.status === 'cancelled'
          ) {
            done(res);
            return;
          }
          setGenTask({
            label: `${label}（${res?.status === 'running' ? '生成中' : '排队中'}，可能需数分钟…）`,
          });
        };
        tick();
        pollTimer.current = setInterval(tick, 2000);
      });
    },
    [],
  );

  const { data: assets, loading, refresh } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpAssets({ workspace_id: workspaceId }),
      );
      if (err) throw err;
      return res ?? [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { data: dbList, refresh: refreshDbList } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getDbList());
    return err ? [] : res ?? [];
  });

  // 工作空间配置:全资产生成必须已配置提案 Agent,否则任务会在后台静默产出 0 条
  // 提案而被误认为成功。这里提前读取配置,未配置时禁用「为所有资产生成提案」。
  const { data: wsConfig } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getEcpWorkspaceConfig(workspaceId));
      return err ? null : res ?? null;
    },
    { refreshDeps: [workspaceId] },
  );
  const hasProposalAgent = !!wsConfig?.proposal_agent_id;

  // 数据库类型(内联创建数据源时按类型渲染表单)
  const { data: supportTypes } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getDbSupportType());
    if (err) return [];
    const types = (res as any)?.types || res || [];
    return Array.isArray(types) ? types : [];
  });

  const { data: spaceList, refresh: refreshSpaces } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listSpaces());
    return err ? [] : (res as any[]) ?? [];
  });

  const { run: doRegister, loading: registering } = useRequest(
    async () => {
      if (!refId) return;
      let refMeta: Record<string, any> | undefined;
      if (kind === 'db') {
        const db = dbList?.find(d => String(d.id) === refId);
        if (db) {
          refMeta = {
            name: db.name || db.db_name,
            db_name: db.db_name,
            db_type: db.db_type,
          };
        }
      } else if (kind === 'space') {
        const space = spaceList?.find(s => s.slug === refId);
        if (space) {
          refMeta = { name: space.name || space.slug };
        }
      }
      const [err] = await apiInterceptors(
        registerEcpAsset({
          kind,
          ref_id: refId,
          workspace_id: workspaceId,
          ref_meta: refMeta,
        }),
      );
      if (err) throw err;
      message.success('资产已登记（只建立引用，不复制数据）');
      setRegisterOpen(false);
      setRefId(undefined);
      refresh();
    },
    { manual: true },
  );

  // 内联创建知识空间:创建后自动选中为登记目标,一步登记引用。
  const handleCreateSpace = async () => {
    const slug = newSpaceSlug.trim();
    if (!slug) { message.warning('请输入知识空间标识'); return; }
    setCreatingSpace(true);
    const [err] = await apiInterceptors(createSpace({ slug }));
    setCreatingSpace(false);
    if (err) { message.error(`创建失败:${err.message}`); return; }
    message.success('知识空间已创建,已自动选中,点「登记」即可引用');
    setNewSpaceSlug('');
    refreshSpaces();
    setRefId(slug);
  };

  const { run: openGenerate, loading: checking } = useRequest(
    async (asset: EcpAssetRef) => {
      const [err, res] = await apiInterceptors(
        getEcpReadiness(Number(asset.ref_id), asset.workspace_id),
      );
      if (err) throw err;
      setGenReadiness(res ?? null);
      setGenAsset(asset);
    },
    { manual: true },
  );

  const { run: doDelete, loading: deleting } = useRequest(
    async (asset: EcpAssetRef) => {
      const [err] = await apiInterceptors(
        deleteEcpAsset(asset.id, asset.workspace_id),
      );
      if (err) throw err;
      message.success('已从 ECP 工作空间移除资产引用');
      refresh();
    },
    { manual: true },
  );

  const { run: doGenerate } = useRequest(
    async () => {
      const asset = genAsset;
      if (!asset) return;
      const hint = domainHint;
      // 立即关闭弹窗,不再让卡片/弹窗原地转圈等待,改为页面顶部进度条展示进展
      setGenAsset(null);
      setDomainHint(undefined);
      const label = `正在为数据源 ${asset.ref_id} 生成语义提案…`;
      setGenTask({ label });
      const [err, res] = await apiInterceptors(
        generateEcpProposals({
          datasource_id: Number(asset.ref_id),
          workspace_id: workspaceId,
          domain_hint: hint || undefined,
        }),
      );
      if (err) {
        setGenTask(null);
        message.error(`提交生成失败：${err.message || err}`);
        return;
      }
      if (!res?.task_id) {
        setGenTask(null);
        message.error('提交生成失败：未返回任务 ID');
        return;
      }
      const task = await waitForTask(res.task_id, label);
      if (task?.error) {
        message.error(`生成提案失败：${task.error}`);
        return;
      }
      if (task?.status !== 'completed') {
        message.error(
          task?.status === 'failed'
            ? `生成提案失败：${task?.error || task?.result_preview || '未知原因'}`
            : `生成提案未完成：${task?.status}`,
        );
        return;
      }
      const art = task?.detail?.artifact ?? {};
      message.success(
        `提案完成：处理 ${art.tables_processed ?? 0} 张表，生成 ${art.proposals_created ?? 0} 条提案，请到收件箱确认`,
      );
      refresh();
    },
    { manual: true },
  );

  // Workspace-level proposal generation: runs the configured proposal Agent over
  // ALL registered assets. It REQUIRES a configured proposal Agent (proposal_agent_id);
  // without one the backend reports an error instead of silently producing 0 proposals,
  // and the button below is disabled with an explanatory tooltip.
  const { run: doGenerateAll } = useRequest(
    async () => {
      if (!hasProposalAgent) {
        message.warning(
          '未配置提案 Agent,无法为全部资产生成提案;请先在 ECP 设置中配置提案 Agent',
        );
        return;
      }
      const hint = domainHint;
      setDomainHint(undefined);
      const label = '正在为所有资产生成语义提案…';
      setGenTask({ label });
      const [err, res] = await apiInterceptors(
        generateEcpProposals({
          workspace_id: workspaceId,
          domain_hint: hint || undefined,
        }),
      );
      if (err) {
        setGenTask(null);
        message.error(`提交生成失败：${err.message || err}`);
        return;
      }
      if (!res?.task_id) {
        setGenTask(null);
        message.error('提交生成失败：未返回任务 ID');
        return;
      }
      const task = await waitForTask(res.task_id, label);
      if (task?.error) {
        message.error(`生成提案失败：${task.error}`);
        return;
      }
      if (task?.status !== 'completed') {
        message.error(
          task?.status === 'failed'
            ? `生成提案失败：${task?.error || '未知原因'}`
            : `生成提案未完成：${task?.status}`,
        );
        return;
      }
      const art = task?.detail?.artifact ?? {};
      if ((art.errors ?? []).length > 0 && !art.proposals_created) {
        message.warning(`提案未生成：${art.errors?.[0] ?? '未知原因'}`);
        return;
      }
      message.success(
        `工作空间级提案完成：生成 ${art.proposals_created ?? 0} 条提案，请到收件箱确认`,
      );
      refresh();
    },
    { manual: true },
  );

  const refOptions =
    kind === 'db'
      ? (dbList ?? []).map((d: any) => ({
          value: String(d.id),
          label: `${d.db_name}（${d.db_type}）`,
        }))
      : kind === 'space'
        ? (spaceList ?? []).map((s: any) => ({
            value: s.slug,
            label: `${s.name ?? s.slug}（${s.slug}）`,
          }))
        : [];

  return (
    <>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <span style={{ fontSize: 13, color: 'var(--ink-500)' }}>
          ECP 不拥有原始资产，只登记引用——就绪后再生成提案。
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input
            size="small"
            allowClear
            placeholder="领域背景(可选,注入提案提示)"
            value={domainHint}
            onChange={e => setDomainHint(e.target.value)}
            style={{ width: 220 }}
          />
          <Tooltip
            title={
              hasProposalAgent
                ? undefined
                : '未配置提案 Agent,无法为全部资产生成提案;请先在 ECP 设置中配置提案 Agent'
            }
          >
            <Button
              size="small"
              type="primary"
              icon={<ExperimentOutlined />}
              disabled={!!genTask || !hasProposalAgent}
              onClick={() => doGenerateAll()}
            >
              为所有资产生成提案
            </Button>
          </Tooltip>
          <Button icon={<ReloadOutlined />} onClick={refresh} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setRegisterOpen(true)}>
            登记资产
          </Button>
        </div>
      </div>

      {genTask && (
        <div className="ecp-gen-progress">
          <div className="ecp-gen-progress__label">
            <span className="ecp-gen-progress__spinner" />
            {genTask.label}
          </div>
          <div className="ecp-gen-progress__bar">
            <div className="ecp-gen-progress__fill" />
          </div>
          <div className="ecp-gen-progress__hint">
            处理中，通常需数十秒到数分钟；完成后提案进入收件箱，确认前不影响任何查询。
          </div>
        </div>
      )}

      {loading ? (
        <Spin style={{ display: 'block', margin: '64px auto' }} />
      ) : (assets ?? []).length === 0 ? (
        <EcpEmpty
          title="尚未登记资产"
          desc="接入 DB 数据源、知识空间或文档，ECP 才能开始提炼业务语义"
          action={
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setRegisterOpen(true)}>
              登记第一个资产
            </Button>
          }
        />
      ) : (
        <div className="ecp-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          {(assets ?? []).map((a, i) => (
            <AssetCard
              key={a.id}
              asset={a}
              index={i}
              disabled={!!genTask}
              onGenerate={asset => openGenerate(asset)}
              onDelete={asset => doDelete(asset)}
              deleting={deleting}
              dbList={dbList}
              spaceList={spaceList}
            />
          ))}
        </div>
      )}

      <Modal
        title="登记资产引用"
        open={registerOpen}
        onOk={() => doRegister()}
        confirmLoading={registering}
        onCancel={() => setRegisterOpen(false)}
        okText="登记"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span style={{ fontSize: 13 }}>资产类型：</span>
          <Select
            style={{ width: '100%' }}
            value={kind}
            onChange={v => {
              setKind(v);
              setRefId(undefined);
            }}
            options={Object.entries(KIND_META).map(([v, m]) => ({
              value: v,
              label: m.label,
            }))}
          />
          <span style={{ fontSize: 13 }}>引用目标：</span>
          {kind === 'db' ? (
            <>
              <Space.Compact style={{ width: '100%' }}>
                <Select
                  showSearch
                  style={{ flex: 1, minWidth: 0 }}
                  placeholder="选择已有数据源"
                  value={refId}
                  onChange={setRefId}
                  options={refOptions}
                />
                <Button icon={<PlusOutlined />} onClick={() => setAddDbOpen(true)}>
                  新建
                </Button>
              </Space.Compact>
              {(refOptions ?? []).length === 0 && (
                <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                  还没有可选数据源,点「新建」创建一个。
                </span>
              )}
            </>
          ) : kind === 'space' ? (
            <>
              <Select
                showSearch
                style={{ width: '100%' }}
                placeholder="选择知识空间"
                value={refId}
                onChange={setRefId}
                options={refOptions}
              />
              <div style={{ borderTop: '1px solid var(--border-subtle, #f0f0f0)', paddingTop: 8 }}>
                <div style={{ fontSize: 12, color: 'var(--ink-400)', marginBottom: 4 }}>
                  没有合适的?新建一个
                </div>
                <Space.Compact style={{ width: '100%' }}>
                  <Input
                    placeholder="空间标识(slug),如 team-wiki"
                    value={newSpaceSlug}
                    onChange={e => setNewSpaceSlug(e.target.value)}
                    onPressEnter={handleCreateSpace}
                  />
                  <Button type="primary" loading={creatingSpace} onClick={handleCreateSpace}>
                    创建并选中
                  </Button>
                </Space.Compact>
              </div>
            </>
          ) : kind === 'document' ? (
            <>
              <Input
                placeholder="space_slug:verbat_id"
                value={refId}
                onChange={e => setRefId(e.target.value)}
              />
              <Alert
                type="info"
                showIcon
                message={
                  <span>
                    文档引用需指定「知识空间:文档ID」。可在
                    <Link href="/knowledge-vault" target="_blank">
                      {' '}知识库模块{' '}
                      <ExportOutlined />
                    </Link>
                    上传文档后复制 verbat_id。
                  </span>
                }
              />
            </>
          ) : (
            <>
              <Input
                placeholder="api_resource_id（P3 开放）"
                value={refId}
                onChange={e => setRefId(e.target.value)}
              />
              <Alert
                type="info"
                showIcon
                message={
                  <span>
                    API 资源 ID 需在
                    <Link href="/application/app" target="_blank">
                      {' '}应用模块{' '}
                      <ExportOutlined />
                    </Link>
                    注册后获取。
                  </span>
                }
              />
            </>
          )}
          <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            登记只建立引用,不复制任何数据。
          </span>
        </div>
      </Modal>

      {/* 内联创建数据库:复用数据库模块创建表单,创建后刷新列表并自动选中 */}
      <DatabaseAddModal
        open={addDbOpen}
        supportTypes={(supportTypes ?? []) as any}
        onCancel={() => setAddDbOpen(false)}
        onSuccess={async (newDbId) => {
          setAddDbOpen(false);
          await refreshDbList();
          if (newDbId) {
            setRefId(newDbId);
            message.success('数据库已创建并自动选中,点「登记」即可引用');
          } else {
            message.success('数据库已创建,请在列表中选择并登记');
          }
        }}
      />

      <Modal
        title={`生成语义提案（${genAsset?.ref_id ?? ''}）`}
        open={!!genAsset}
        onOk={() => doGenerate()}
        onCancel={() => setGenAsset(null)}
        okText="开始生成"
        okButtonProps={{ disabled: genReadiness ? !genReadiness.ready : false }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {genReadiness && (
            <div className="ecp-card" style={{ padding: 14, marginTop: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                {genReadiness.ready ? '✅ 材料就绪' : '❌ 材料不完整'}
              </div>
              <ReadinessList readiness={genReadiness} />
            </div>
          )}
          <span style={{ fontSize: 13 }}>领域背景（可选，注入提案提示词）：</span>
          <Input.TextArea
            rows={3}
            placeholder="例：零售行业，口径以《财务核算办法》为准"
            value={domainHint}
            onChange={e => setDomainHint(e.target.value)}
          />
          <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            提案全部进入「收件箱」，确认前不影响任何查询。
          </span>
        </div>
      </Modal>
    </>
  );
}
