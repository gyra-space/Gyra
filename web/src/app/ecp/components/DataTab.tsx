'use client';

import { apiInterceptors } from '@/client/api';
import { getDbList, getDbSupportType } from '@/client/api/request';
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
import DatabaseAddModal from '@/app/database/components/DatabaseAddModal';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Modal, Popconfirm, Spin, Tooltip } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Dot, EcpEmpty } from './common';

interface EcpDbAsset extends EcpAssetRef {
  dbName?: string;
  dbType?: string;
}

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

function DbCard({
  asset,
  dbName,
  dbType,
  onRemove,
  onGenerate,
  disabled,
  removing,
}: {
  asset: EcpAssetRef;
  dbName: string;
  dbType: string;
  onRemove: (a: EcpAssetRef) => void;
  onGenerate: (a: EcpAssetRef) => void;
  disabled?: boolean;
  removing: boolean;
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

  return (
    <div className="ecp-card" style={{ marginTop: 0 }}>
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
          <DatabaseOutlined />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>
            {dbName}
          </div>
          <code style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            DB · {dbType}
          </code>
        </div>
        <span className="ecp-status">
          <Dot kind={asset.status === 'active' ? 'ecp-dot--success' : 'ecp-dot--neutral'} />
          {asset.status}
        </span>
        <Popconfirm
          title="移除该数据源引用？"
          description="仅从 ECP 工作空间移除引用，不会删除原始数据源。"
          okText="移除"
          cancelText="取消"
          okButtonProps={{ danger: true, loading: removing }}
          onConfirm={() => onRemove(asset)}
        >
          <Button size="small" type="text" danger icon={<DeleteOutlined />} loading={removing} />
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

      {readiness && <ReadinessList readiness={readiness} />}

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
    </div>
  );
}

/**
 * 数据资产：在 ECP 内直接管理数据源（数据库）。
 * 已接入的数据源可一键登记进 ECP、就绪检查、生成语义提案；
 * 未登记的数据源在下方「可接入数据源」中登记，无需跳转数据库模块。
 */
export default function DataTab({ workspaceId }: { workspaceId: string }) {
  const { message } = App.useApp();
  const [addDbOpen, setAddDbOpen] = useState(false);
  const [genAsset, setGenAsset] = useState<EcpAssetRef | null>(null);
  const [domainHint, setDomainHint] = useState<string>();
  const [genReadiness, setGenReadiness] = useState<EcpReadiness | null>(null);
  const [genTask, setGenTask] = useState<{ label: string } | null>(null);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const visibilityHandlerRef = useRef<(() => void) | null>(null);
  useEffect(
    () => () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      if (visibilityHandlerRef.current) {
        document.removeEventListener('visibilitychange', visibilityHandlerRef.current);
        visibilityHandlerRef.current = null;
      }
    },
    [],
  );

  const waitForTask = useCallback(
    async (taskId: string, label: string): Promise<any> => {
      return new Promise(resolve => {
        let settled = false;
        let handleVisibility: () => void = () => {};
        const done = (res: any) => {
          if (settled) return;
          settled = true;
          if (pollTimer.current) clearInterval(pollTimer.current);
          pollTimer.current = null;
          document.removeEventListener('visibilitychange', handleVisibility);
          visibilityHandlerRef.current = null;
          setGenTask(null);
          resolve(res);
        };
        const tick = async () => {
          const [err, res] = await apiInterceptors(getEcpProposalTask(taskId, workspaceId));
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
        const stop = () => {
          if (pollTimer.current) clearInterval(pollTimer.current);
          pollTimer.current = null;
        };
        const start = () => {
          tick();
          if (pollTimer.current) clearInterval(pollTimer.current);
          pollTimer.current = setInterval(tick, 2000);
        };
        handleVisibility = () => {
          if (document.hidden) stop();
          else start();
        };
        document.addEventListener('visibilitychange', handleVisibility);
        visibilityHandlerRef.current = handleVisibility;
        start();
      });
    },
    [workspaceId],
  );

  const { data: registered, loading, refresh } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        listEcpAssets({ workspace_id: workspaceId, kind: 'db' }),
      );
      if (err) throw err;
      return res ?? [];
    },
    { refreshDeps: [workspaceId] },
  );

  const { data: dbList, refresh: refreshDbList } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getDbList());
    if (err) return [];
    return (res ?? []).map((d: any) => ({
      id: String(d.id),
      name: d.name || d.db_name || d.params?.database || d.params?.db_name || '未命名',
      db_type: d.db_type || d.type || '',
      host: d.db_host || d.params?.host || '',
      port: d.db_port || d.params?.port || 0,
    }));
  });

  const { data: supportTypes } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getDbSupportType());
    if (err) return [];
    const types = (res as any)?.types || res || [];
    return Array.isArray(types) ? types : [];
  });

  const { data: wsConfig } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getEcpWorkspaceConfig(workspaceId));
      return err ? null : res ?? null;
    },
    { refreshDeps: [workspaceId] },
  );
  const hasProposalAgent = !!wsConfig?.proposal_agent_id;

  const enrich = (assets: EcpAssetRef[]) =>
    (assets ?? []).map(a => {
      const db = dbList?.find(d => d.id === String(a.ref_id));
      return {
        ...a,
        dbName: a.ref_meta?.name || db?.name || a.ref_id,
        dbType: a.ref_meta?.db_type || db?.db_type || '',
      } as EcpDbAsset;
    });

  const registeredIds = new Set((registered ?? []).map(a => String(a.ref_id)));
  const readyToRegister = (dbList ?? []).filter(d => !registeredIds.has(d.id));

  const { run: doRegister, loading: registering } = useRequest(
    async (db: any) => {
      const [err] = await apiInterceptors(
        registerEcpAsset({
          kind: 'db',
          ref_id: db.id,
          workspace_id: workspaceId,
          ref_meta: { name: db.name, db_name: db.name, db_type: db.db_type },
        }),
      );
      if (err) throw err;
      message.success(`已接入数据源「${db.name}」到 ECP`);
      refresh();
    },
    { manual: true },
  );

  const { run: doRemove, loading: removing } = useRequest(
    async (asset: EcpAssetRef) => {
      const [err] = await apiInterceptors(deleteEcpAsset(asset.id, asset.workspace_id));
      if (err) throw err;
      message.success('已从 ECP 移除数据源引用');
      refresh();
    },
    { manual: true },
  );

  const { run: openGenerate } = useRequest(
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

  const { run: doGenerate } = useRequest(
    async () => {
      const asset = genAsset;
      if (!asset) return;
      const hint = domainHint;
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
        `提案完成：处理 ${art.tables_processed ?? 0} 张表，生成 ${art.proposals_created ?? 0} 条提案，请到「业务口径」确认`,
      );
      refresh();
    },
    { manual: true },
  );

  const { run: doGenerateAll } = useRequest(
    async () => {
      if (!hasProposalAgent) {
        message.warning(
          '未配置提案 Agent，无法为全部资产生成提案；请先在「治理」中配置提案 Agent',
        );
        return;
      }
      const hint = domainHint;
      setDomainHint(undefined);
      const label = '正在为所有资产生成语义提案…';
      setGenTask({ label });
      const [err, res] = await apiInterceptors(
        generateEcpProposals({ workspace_id: workspaceId, domain_hint: hint || undefined }),
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
        message.error(`生成提案未完成：${task?.status}`);
        return;
      }
      const art = task?.detail?.artifact ?? {};
      if ((art.errors ?? []).length > 0 && !art.proposals_created) {
        message.warning(`提案未生成：${art.errors?.[0] ?? '未知原因'}`);
        return;
      }
      message.success(
        `工作空间级提案完成：生成 ${art.proposals_created ?? 0} 条提案，请到「业务口径」确认`,
      );
      refresh();
    },
    { manual: true },
  );

  const enrichedRegistered = enrich(registered ?? []);

  return (
    <>
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
            处理中，通常需数十秒到数分钟；完成后提案进入「业务口径」，确认前不影响任何查询。
          </div>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <span style={{ fontSize: 13, color: 'var(--ink-500)', maxWidth: 640 }}>
          直接接入已有数据库，让 ECP 持续学习并沉淀业务口径；确认后即可用可信数字回答业务问题。
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Tooltip
            title={
              hasProposalAgent
                ? undefined
                : '未配置提案 Agent，无法为全部资产生成提案；请先在「治理」中配置提案 Agent'
            }
          >
            <Button
              type="primary"
              icon={<ExperimentOutlined />}
              disabled={!!genTask || !hasProposalAgent}
              onClick={() => doGenerateAll()}
            >
              为所有已接入数据源生成提案
            </Button>
          </Tooltip>
          <Button icon={<ReloadOutlined />} onClick={refresh} />
          <Button icon={<PlusOutlined />} onClick={() => setAddDbOpen(true)}>
            连接数据源
          </Button>
        </div>
      </div>

      {/* 已接入 ECP */}
      <div className="ecp-card__title" style={{ marginBottom: 12 }}>
        <span>已接入 ECP 的数据源</span>
        <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--ink-400)' }}>
          {enrichedRegistered.length} 个
        </span>
      </div>
      {loading ? (
        <Spin style={{ display: 'block', margin: '64px auto' }} />
      ) : enrichedRegistered.length === 0 ? (
        <EcpEmpty
          title="尚未接入数据源"
          desc="从下方「可接入数据源」选择一个登记，或点「连接数据源」新建"
        />
      ) : (
        <div className="ecp-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          {enrichedRegistered.map(a => (
            <DbCard
              key={a.id}
              asset={a}
              dbName={a.dbName ?? a.ref_id}
              dbType={a.dbType ?? 'DB'}
              disabled={!!genTask}
              onRemove={o => doRemove(o)}
              onGenerate={o => openGenerate(o)}
              removing={removing}
            />
          ))}
        </div>
      )}

      {/* 可接入数据源 */}
      <div className="ecp-card__title" style={{ margin: '28px 0 12px' }}>
        <span>可接入的数据源</span>
        <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--ink-400)' }}>
          来自「数据库」模块已连接的连接
        </span>
      </div>
      {readyToRegister.length === 0 ? (
        <EcpEmpty
          title="没有更多可接入的数据源"
          desc="数据库模块中的连接都已接入 ECP，或还没有创建数据库连接"
        />
      ) : (
        <div className="ecp-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          {readyToRegister.map(d => (
            <div className="ecp-card ecp-rise ecp-rise--1" key={d.id} style={{ marginTop: 0 }}>
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
                  <DatabaseOutlined />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>
                    {d.name}
                  </div>
                  <code style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                    {d.db_type}{d.host ? ` · ${d.host}${d.port ? `:${d.port}` : ''}` : ''}
                  </code>
                </div>
                <Button
                  size="small"
                  type="primary"
                  ghost
                  loading={registering}
                  onClick={() => doRegister(d)}
                >
                  接入 ECP
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <DatabaseAddModal
        open={addDbOpen}
        supportTypes={(supportTypes ?? []) as any}
        onCancel={() => setAddDbOpen(false)}
        onSuccess={async (newDbId) => {
          setAddDbOpen(false);
          await refreshDbList();
          if (newDbId) message.success('数据库已连接，请在「可接入数据源」中接入 ECP');
          else message.success('数据库已连接，请在「可接入数据源」中接入 ECP');
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
          <textarea
            rows={3}
            placeholder="例：零售行业，口径以《财务核算办法》为准"
            value={domainHint}
            onChange={e => setDomainHint(e.target.value)}
            style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid var(--line-soft)', fontSize: 13 }}
          />
          <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            提案全部进入「业务口径」等待确认，确认前不影响任何查询。
          </span>
        </div>
      </Modal>
    </>
  );
}
