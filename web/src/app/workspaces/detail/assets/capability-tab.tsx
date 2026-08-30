'use client';

import {
  apiInterceptors,
  listResources,
  addResource,
  removeResource,
  updateResource,
  getSkillList,
  getMCPList,
  getAppList,
} from '@/client/api';
import {
  Alert, App, Button, Empty, Input, Modal, Select, Space, Spin, Switch, Tag,
} from 'antd';
import {
  ToolOutlined,
  ApiOutlined,
  RobotOutlined,
  PlusOutlined,
  ExportOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useMemo, useState } from 'react';
import dayjs from 'dayjs';
import Link from 'next/link';
import './assets.css';

const TYPE_META: Record<string, { label: string; tagColor: string; color: string; icon: React.ReactNode }> = {
  skill: { label: '技能', tagColor: 'geekblue', color: '#6366f1', icon: <ToolOutlined /> },
  mcp: { label: 'MCP', tagColor: 'purple', color: '#8b5cf6', icon: <ApiOutlined /> },
  app: { label: '智能体', tagColor: 'blue', color: '#3b82f6', icon: <RobotOutlined /> },
  command: { label: '命令', tagColor: 'cyan', color: '#06b6d4', icon: <ThunderboltOutlined /> },
};

/** 排序:启用在前,最近更新在前。 */
function sortCaps(rows: any[]) {
  return [...rows].sort((a, b) => {
    if (!!a.is_active !== !!b.is_active) return a.is_active ? -1 : 1;
    return dayjs(b.gmt_modified || 0).valueOf() - dayjs(a.gmt_modified || 0).valueOf();
  });
}

/** 能力:空间里的 Agent 会"干"什么 —— 技能 / MCP / 子智能体 / 专属模型。 */
export function CapabilityTab({ workspaceId, workspaceCode, canManage = true }: {
  workspaceId: number;
  workspaceCode?: string;
  /** 是否空间管理员 owner(管理)。成员只看不改,仅可使用资源。 */
  canManage?: boolean;
}) {
  // 静态 Modal/message 在本应用(React 19 静态渲染路径)下会静默失效,必须用 App.useApp() 上下文实例
  const { modal, message } = App.useApp();
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [addType, setAddType] = useState<'skill' | 'mcp' | 'app' | 'command'>('skill');
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [selectedMcp, setSelectedMcp] = useState<any>(null);
  const [selectedApp, setSelectedApp] = useState<string | null>(null);
  // 自定义命令表单(workspace_resource type='command' 的新建,非选择已有实体)
  const [cmdName, setCmdName] = useState('');
  const [cmdRef, setCmdRef] = useState('');
  const [cmdDesc, setCmdDesc] = useState('');
  const [cmdPayload, setCmdPayload] = useState('');

  const { data: resources, loading, refresh } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listResources({ workspace_id: workspaceId }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId] });

  const allResources = useMemo(() => {
    const rows = (resources || []).filter((r: any) => TYPE_META[r.type]);
    const byType = (types: string[]) => new Set(
      rows.filter((r: any) => types.includes(r.type)).map((r: any) => String(r.physical_ref || r.name)),
    );
    return { rows, byType };
  }, [resources]);

  const { data: skillData, refresh: refreshSkills } = useRequest(
    async () => await apiInterceptors(getSkillList({ filter: '' }, { page: 1, page_size: 200 })),
  );
  const allSkills = useMemo(() => {
    const [, res] = skillData || [];
    return res?.items || [];
  }, [skillData]);

  // 从 MCP 模块查询可用服务，供绑定 MCP 能力时选择（physical_ref 取 mcp_code）
  const { data: mcpData, refresh: refreshMcp } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(
        getMCPList({ filter: '' }, { page: '1', page_size: '200' }),
      );
      return err ? [] : (res as any)?.items || [];
    },
  );
  const allMcps = useMemo(() => mcpData || [], [mcpData]);

  // 可配置为子 Agent 的应用(物理引用取 app_code)
  const { data: appData, refresh: refreshApps } = useRequest(
    async () => {
      const [err, res] = await apiInterceptors(getAppList({ page: 1, page_size: 200 }));
      return err ? [] : res?.app_list || [];
    },
  );
  const allApps = useMemo(() => appData || [], [appData]);

  const sections = useMemo(() => {
    const rows = allResources.rows;
    return [
      { key: 'skill', title: '技能', items: sortCaps(rows.filter((r: any) => r.type === 'skill')) },
      { key: 'mcp', title: 'MCP 服务', items: sortCaps(rows.filter((r: any) => r.type === 'mcp')) },
      { key: 'app', title: '子智能体', items: sortCaps(rows.filter((r: any) => r.type === 'app')) },
      { key: 'command', title: '命令', items: sortCaps(rows.filter((r: any) => r.type === 'command')) },
    ].filter((s) => s.items.length > 0);
  }, [allResources]);

  const totalCount = useMemo(() => sections.reduce((n, s) => n + s.items.length, 0), [sections]);

  const candidateSkills = useMemo(
    () => allSkills.filter((s: any) => !allResources.byType(['skill']).has(String(s.skill_code)) && !allResources.byType(['skill']).has(String(s.name))),
    [allSkills, allResources],
  );
  const candidateApps = useMemo(
    () => allApps.filter((a: any) => !allResources.byType(['app']).has(String(a.app_code))),
    [allApps, allResources],
  );

  const handleAdd = async () => {
    setSaving(true);
    let err: any = null;
    if (addType === 'skill') {
      const skill = allSkills.find((s: any) => s.skill_code === selectedSkill);
      if (!skill) { setSaving(false); return; }
      [err] = await apiInterceptors(addResource({
        workspace_id: workspaceId,
        type: 'skill',
        name: skill.name,
        physical_ref: skill.skill_code,
        category: 'scenario_bound',
        access_mode: 'read',
        is_active: true,
        config: {},
      }));
    } else if (addType === 'mcp') {
      if (!selectedMcp?.mcp_code) { setSaving(false); message.warning('请选择 MCP 服务'); return; }
      [err] = await apiInterceptors(addResource({
        workspace_id: workspaceId,
        type: 'mcp',
        name: selectedMcp.name || selectedMcp.mcp_code,
        physical_ref: selectedMcp.mcp_code,
        category: 'scenario_bound',
        access_mode: 'read',
        is_active: true,
        config: {},
      }));
    } else if (addType === 'app') {
      const app = allApps.find((a: any) => a.app_code === selectedApp);
      if (!app) { setSaving(false); message.warning('请选择子智能体'); return; }
      [err] = await apiInterceptors(addResource({
        workspace_id: workspaceId,
        type: 'app',
        name: app.app_name || app.app_code,
        physical_ref: app.app_code,
        category: 'scenario_bound',
        access_mode: 'read',
        is_active: true,
        config: {},
      }));
    } else if (addType === 'command') {
      if (!cmdName.trim()) { setSaving(false); message.warning('请填写命令名称'); return; }
      let payload: Record<string, unknown> = {};
      if (cmdPayload.trim()) {
        try {
          const parsed = JSON.parse(cmdPayload);
          if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
            setSaving(false); message.warning('生效参数必须是 JSON 对象'); return;
          }
          payload = parsed;
        } catch {
          setSaving(false); message.warning('生效参数不是合法 JSON'); return;
        }
      }
      [err] = await apiInterceptors(addResource({
        workspace_id: workspaceId,
        type: 'command',
        name: cmdName.trim(),
        physical_ref: cmdRef.trim() || cmdName.trim(),
        category: 'scenario_bound',
        access_mode: 'read',
        is_active: true,
        config: { kind: 'toggle', description: cmdDesc.trim(), payload },
      }));
    }
    setSaving(false);
    if (err) { message.error(err.message); return; }
    message.success('能力已添加');
    setAddOpen(false);
    setSelectedSkill(null);
    setSelectedMcp(null);
    setSelectedApp(null);
    setCmdName('');
    setCmdRef('');
    setCmdDesc('');
    setCmdPayload('');
    refresh();
  };

  const handleToggle = async (r: any, checked: boolean) => {
    const [err] = await apiInterceptors(updateResource({
      resource_id: r.id,
      resource: {
        workspace_id: workspaceId,
        type: r.type,
        name: r.name,
        category: r.category,
        physical_ref: r.physical_ref,
        config: r.config || {},
        access_mode: r.access_mode,
        is_active: checked,
      },
    }));
    if (err) { message.error(err.message); return; }
    refresh();
  };

  const handleRemove = (r: any) => {
    modal.confirm({
      title: `移除能力「${r.name}」?`,
      content: '移除后空间内的主 Agent 将无法使用该能力。',
      okText: '移除',
      okButtonProps: { danger: true },
      onOk: async () => {
        const [err] = await apiInterceptors(removeResource({ resource_id: r.id }));
        if (err) { message.error(err.message); return; }
        message.success('已移除');
        refresh();
      },
    });
  };

  const renderCard = (r: any) => {
    const meta = TYPE_META[r.type] || TYPE_META.skill;
    const active = !!r.is_active;
    return (
      <div key={r.id} className={`ws-asset-card${active ? '' : ' ws-asset-card--off'}`}>
        <div className="ws-asset-card__top">
          <span
            className="ws-asset-card__icon"
            style={{ color: meta.color, background: `${meta.color}1a` }}
          >
            {meta.icon}
          </span>
          <span className="ws-asset-card__name" title={r.name}>{r.name}</span>
          {canManage && (
            <Switch size="small" checked={active} onChange={(c) => handleToggle(r, c)} />
          )}
        </div>
        <div className="ws-asset-card__tags">
          <Tag color={meta.tagColor}>{meta.label}</Tag>
          {active ? null : <Tag>已停用</Tag>}
        </div>
        <div className="ws-asset-card__source" title={r.physical_ref || r.name}>
          {r.physical_ref || r.name}
        </div>
        <div className="ws-asset-card__foot">
          <span className="ws-asset-card__time">
            {r.gmt_modified ? dayjs(r.gmt_modified).format('MM-DD HH:mm') : ''}
          </span>
          {canManage && (
            <span className="ws-asset-card__ops">
              <Button size="small" type="text" danger onClick={() => handleRemove(r)}>移除</Button>
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div>
      {canManage ? (
        <div className="ws-asset-toolbar">
          <span className="ws-asset-toolbar__stat">
            已挂载 <b>{totalCount}</b> 项能力
          </span>
          <div className="ws-asset-toolbar__actions">
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>添加能力</Button>
          </div>
        </div>
      ) : (
        <div className="flex justify-end mb-4 text-xs text-gray-400">
          <span>只读 · 管理员可维护资源</span>
        </div>
      )}

      {loading ? <div className="flex justify-center py-8"><Spin /></div> : totalCount === 0 ? (
        <Empty description="还没有能力" style={{ padding: '32px 0' }}>
          {canManage && <Button size="small" onClick={() => setAddOpen(true)}>添加第一个能力</Button>}
        </Empty>
      ) : (
        sections.map((s) => (
          <div key={s.key} className="ws-asset-section">
            <div className="ws-asset-section__head">
              <span className="ws-asset-section__icon">
                {s.key === 'skill' ? <ToolOutlined /> : s.key === 'mcp' ? <ApiOutlined /> : s.key === 'command' ? <ThunderboltOutlined /> : <RobotOutlined />}
              </span>
              <span className="ws-asset-section__title">{s.title}</span>
              <span className="ws-asset-section__count">{s.items.length}</span>
            </div>
            <div className="ws-asset-grid">
              {s.items.map(renderCard)}
            </div>
          </div>
        )))}

      <Modal
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        onOk={handleAdd}
        confirmLoading={saving}
        title="添加能力"
        okText="添加"
      >
        <div className="mb-3">
          <div className="text-sm text-gray-500 mb-2">能力类型</div>
          <div className="ws-capability-type">
            {[
              { v: 'skill', label: '技能', desc: '指导 Agent 做事的方法', icon: <ToolOutlined /> },
              { v: 'mcp', label: 'MCP', desc: '扩展 Agent 工具能力的服务', icon: <ApiOutlined /> },
              { v: 'app', label: '子智能体', desc: '主 Agent 可调用的协作 Agent', icon: <RobotOutlined /> },
              { v: 'command', label: '命令', desc: '输入框 / 唤起的会话开关', icon: <ThunderboltOutlined /> },
            ].map((opt) => (
              <div
                key={opt.v}
                className={`ws-capability-type__item${addType === opt.v ? ' ws-capability-type__item--on' : ''}`}
                onClick={() => setAddType(opt.v as any)}
              >
                <span className="ws-capability-type__title" style={{ color: TYPE_META[opt.v].color }}>
                  {opt.icon}
                  {opt.label}
                </span>
                <span className="ws-capability-type__desc">{opt.desc}</span>
              </div>
            ))}
          </div>
        </div>
        {addType === 'skill' && (
          <Alert
            type="info"
            showIcon
            className="mb-3"
            message="没有想要的技能?"
            description={
              <Space>
                <Link href="/agent-skills" target="_blank">
                  去技能模块创建编排 <ExportOutlined />
                </Link>
                <Button type="link" size="small" icon={<ReloadOutlined />} onClick={refreshSkills}>
                  刷新列表
                </Button>
              </Space>
            }
          />
        )}
        {addType === 'mcp' && (
          <Alert
            type="info"
            showIcon
            className="mb-3"
            message="从 MCP 模块选择服务，physical_ref 自动取服务编码"
            description={
              <Space>
                <Link href="/mcp" target="_blank">
                  去 MCP 模块配置 <ExportOutlined />
                </Link>
                <Button type="link" size="small" icon={<ReloadOutlined />} onClick={refreshMcp}>
                  刷新列表
                </Button>
              </Space>
            }
          />
        )}
        {addType === 'app' && (
          <Alert
            type="info"
            showIcon
            className="mb-3"
            message="勾选的子智能体将被物化为主 Agent 的协作 Agent(extra_agents)"
            description={
              <Space>
                <Link href="/apps" target="_blank">
                  去应用模块创建 <ExportOutlined />
                </Link>
                <Button type="link" size="small" icon={<ReloadOutlined />} onClick={refreshApps}>
                  刷新列表
                </Button>
              </Space>
            }
          />
        )}
        {addType === 'command' && (
          <Alert
            type="info"
            showIcon
            className="mb-3"
            message="自定义命令会出现在对话输入框 / 菜单的「命令」组"
            description="选中后作为会话开关(可取消),发送消息时「生效参数」会并入请求 ext_info。内置的 压缩上下文 / 清理会话 / 规划模式 无需在此配置。"
          />
        )}
        {addType === 'command' ? (
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-500 mb-2">命令名称(必填)</div>
              <Input
                value={cmdName}
                onChange={(e) => setCmdName(e.target.value)}
                placeholder="如:开启深度思考"
                maxLength={20}
              />
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-2">命令标识(选填,默认同名称)</div>
              <Input
                value={cmdRef}
                onChange={(e) => setCmdRef(e.target.value)}
                placeholder="如:deep-think"
                maxLength={32}
              />
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-2">描述(选填,展示在菜单里)</div>
              <Input
                value={cmdDesc}
                onChange={(e) => setCmdDesc(e.target.value)}
                placeholder="如:本回合开启更深度的推理"
                maxLength={50}
              />
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-2">生效参数(JSON 对象,选填)</div>
              <Input.TextArea
                value={cmdPayload}
                onChange={(e) => setCmdPayload(e.target.value)}
                placeholder='{"permission_mode":"plan"}'
                rows={2}
              />
              <div className="text-xs text-gray-400 mt-1">
                选中该命令后发送消息时,这些参数会并入请求 ext_info;留空则仅作为标记。
              </div>
            </div>
          </div>
        ) : addType === 'skill' ? (
          <div>
            <div className="text-sm text-gray-500 mb-2">选择技能</div>
            <Select
              style={{ width: '100%' }}
              placeholder="从技能库选择"
              value={selectedSkill}
              onChange={setSelectedSkill}
              showSearch
              optionFilterProp="label"
              options={candidateSkills.map((s: any) => ({
                value: s.skill_code,
                label: `${s.name}${s.description ? ` — ${s.description}` : ''}`,
              }))}
            />
          </div>
        ) : addType === 'mcp' ? (
          <div>
            <div className="text-sm text-gray-500 mb-2">选择 MCP 服务</div>
            <Select
              style={{ width: '100%' }}
              placeholder="从 MCP 模块选择"
              value={selectedMcp?.mcp_code}
              onChange={(code) => {
                const m = allMcps.find((x: any) => x.mcp_code === code);
                setSelectedMcp(m || null);
              }}
              showSearch
              optionFilterProp="label"
              notFoundContent={allMcps.length ? null : <Spin size="small" />}
              options={allMcps.map((m: any) => ({
                value: m.mcp_code,
                label: `${m.name}${m.description ? ` — ${m.description}` : ''}`,
              }))}
            />
          </div>
        ) : addType === 'app' ? (
          <div>
            <div className="text-sm text-gray-500 mb-2">选择子智能体</div>
            <Select
              style={{ width: '100%' }}
              placeholder="从应用列表选择"
              value={selectedApp}
              onChange={setSelectedApp}
              showSearch
              optionFilterProp="label"
              notFoundContent={allApps.length ? null : <Spin size="small" />}
              options={candidateApps.map((a: any) => ({
                value: a.app_code,
                label: `${a.app_name || a.app_code}${a.app_describe ? ` — ${a.app_describe}` : ''}`,
              }))}
            />
          </div>
        ) : null}
      </Modal>
    </div>
  );
}