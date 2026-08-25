'use client';

import { apiInterceptors } from '@/client/api';
import { getEcpContractCheck, getOrCreateEcpSpace, normalizeEcpConfirmed, type EcpContractCheck } from '@/client/api/ecp';
import { lintSpace } from '@/client/api/knowledge-vault';
import type { LintIssue } from '@/types/knowledge-vault';
import { PlayCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { App, Button, Popconfirm, Spin, Tag } from 'antd';
import { useState } from 'react';

import { Dot, EcpEmpty } from './common';

const SEVERITY_DOT: Record<string, string> = {
  info: 'ecp-dot--success',
  warning: 'ecp-dot--warning',
  error: 'ecp-dot--danger',
};

export default function LintTab({ workspaceId }: { workspaceId: string }) {
  const { message } = App.useApp();
  const [issues, setIssues] = useState<LintIssue[] | null>(null);
  const [contract, setContract] = useState<EcpContractCheck | null>(null);

  const { data: space } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getOrCreateEcpSpace(workspaceId));
      return err ? null : res;
    },
    { refreshDeps: [workspaceId] },
  );

  const { run, loading } = useRequest(
    async () => {
      if (!space?.slug) return;
      const [err, res] = await apiInterceptors(lintSpace(space.slug));
      if (err) throw err;
      setIssues(res?.issues ?? []);
    },
    { manual: true },
  );

  const { run: check, loading: checking } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getEcpContractCheck(workspaceId));
      if (err) throw err;
      setContract(res ?? null);
    },
    { manual: true },
  );

  const { run: normalize, loading: normalizing } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(normalizeEcpConfirmed(workspaceId));
      if (err) throw err;
      message.success(
        `已修复 ${res?.fixed?.length ?? 0} 个对象，跳过 ${res?.skipped?.length ?? 0} 个（需人工编辑后确认）`,
      );
      check();
    },
    { manual: true },
  );

  const grouped = (issues ?? []).reduce<Record<string, LintIssue[]>>((acc, i) => {
    (acc[i.rule] ??= []).push(i);
    return acc;
  }, {});

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
        <span style={{ fontSize: 13, color: 'var(--ink-500)', maxWidth: 640 }}>
          硬层契约体检：已确认但不可执行的语义对象（PAYLOAD_INVALID 根因）；软层结构巡检：孤儿页 / 断链 / 缺引用。
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={() => run()}>
            软层巡检
          </Button>
          <Button icon={<ThunderboltOutlined />} loading={checking} onClick={() => check()}>
            硬层体检
          </Button>
        </div>
      </div>

      <div className="ecp-card" style={{ marginBottom: 16 }}>
        <div className="ecp-card__title">
          硬层契约体检（已确认口径）
        </div>
        {checking ? (
          <Spin style={{ display: 'block', margin: '24px auto' }} />
        ) : contract === null ? (
          <EcpEmpty title="点击「硬层体检」扫描已确认对象是否可执行" />
        ) : contract.non_compliant_count === 0 ? (
          <div className="ecp-status" style={{ fontSize: 14 }}>
            <Dot kind="ecp-dot--success" />
            全部 {contract.total} 个已确认对象均满足可执行契约
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: 8, fontSize: 13, color: 'var(--ink-500)' }}>
              发现 {contract.non_compliant_count} 个不合规对象：
            </div>
            {(contract.non_compliant ?? []).map(item => (
              <div
                key={`${item.id}@${item.version}`}
                style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'flex-start',
                  padding: '8px 0',
                  borderBottom: '1px solid var(--line-soft)',
                  fontSize: 13,
                }}
              >
                <Dot kind="ecp-dot--danger" />
                <code style={{ fontSize: 12, color: 'var(--ink-700)' }}>
                  {item.id}@v{item.version}
                </code>
                <Tag style={{ margin: 0 }}>{item.obj_type}</Tag>
                <span style={{ flex: 1, color: 'var(--ink-500)', fontSize: 12 }}>
                  {item.problems.join('；')}
                </span>
              </div>
            ))}
            <div style={{ marginTop: 12 }}>
              <Popconfirm
                title="一键修复不合规对象？"
                description="会按契约归一化写新版本（不可执行项跳过，需人工编辑后确认）。"
                okText="修复"
                cancelText="取消"
                okButtonProps={{ loading: normalizing }}
                onConfirm={() => normalize()}
              >
                <Button type="primary" danger loading={normalizing}>
                  一键修复
                </Button>
              </Popconfirm>
            </div>
          </div>
        )}
      </div>

      <div className="ecp-card">
        <div className="ecp-card__title">软层结构巡检</div>
        {issues === null ? (
          <EcpEmpty title="点击「软层巡检」检查软知识层健康度" />
        ) : issues.length === 0 ? (
          <div className="ecp-status" style={{ fontSize: 14 }}>
            <Dot kind="ecp-dot--success" />
            未发现问题，软知识层结构健康
          </div>
        ) : (
          Object.entries(grouped).map(([rule, list]) => (
            <div key={rule} className="ecp-card" style={{ marginTop: 0 }}>
              <div className="ecp-card__title">
                <span>
                  {rule}
                  <span style={{ color: 'var(--ink-400)', fontWeight: 400, marginLeft: 8 }}>
                    {list.length} 项
                  </span>
                </span>
              </div>
              {list.map((i, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: idx < list.length - 1 ? '1px solid var(--line-soft)' : 'none',
                    fontSize: 13,
                  }}
                >
                  <Dot kind={SEVERITY_DOT[i.severity] ?? 'ecp-dot--neutral'} />
                  <span style={{ color: 'var(--ink-700)' }}>{i.message}</span>
                  {i.path && <code style={{ fontSize: 11, color: 'var(--ink-400)' }}>{i.path}</code>}
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </>
  );
}
