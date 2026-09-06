'use client';

import { apiInterceptors, listExperts, upsertExpert, bindExpert, unbindExpert, getWorkspaceInfo, listResources, getAppList, getSkillList, getMCPList, listMembers, addMember, removeMember, updateMemberRole } from '@/client/api';
import { usersService, type User } from '@/services/users';
import { useSpaceRole } from '@/hooks/use-space-role';
import { AgentAvatar } from '@/components/common/agent-avatar';
import { AgentAvatarPicker } from '@/components/common/agent-avatar-picker';
import { Button, Empty, Input, Modal, Select, Spin, Table, Tag, App, Space, Popconfirm, Form, Avatar, Divider } from 'antd';
import { useRequest } from 'ahooks';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';
import '../../workspaces.css';
import type { ExpertInfo, ExpertEquipmentItem } from '@/client/api/expert';
import type { IApp } from '@/types/app';
import {
  UserOutlined,
  RobotOutlined,
  PlusOutlined,
  DatabaseOutlined,
  ToolOutlined,
  CloudServerOutlined,
  BookOutlined,
  DeleteOutlined,
  EditOutlined,
  CrownOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';

const RESOURCE_TYPE_MAP: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  skill: { label: '技能', icon: <ToolOutlined />, color: 'blue' },
  mcp: { label: 'MCP', icon: <CloudServerOutlined />, color: 'purple' },
  knowledge_space: { label: '知识库', icon: <BookOutlined />, color: 'green' },
  data_source: { label: '数据源', icon: <DatabaseOutlined />, color: 'orange' },
};

const normalizeResourceType = (t: string) => (t === 'datasource' ? 'data_source' : t);

const ROLE_LABELS: Record<string, string> = {
  owner: '管理',
  contributor: '使用',
  viewer: '查看',
};

type PoolResourceRow = { type: string; name: string; physical_ref?: string };
type GlobalSkillOption = { skill_code: string; name: string; description?: string };
type GlobalMcpOption = { mcp_code: string; name: string; description?: string };
type MemberRow = {
  id: number;
  user_id: number;
  user_name?: string;
  role: string;
};

export default function MembersPage() {
  const searchParams = useSearchParams();
  const workspaceCode = searchParams?.get('id') || '';
  const router = useRouter();
  const { message } = App.useApp();

  // ---- 专家创建/编辑状态 ----
  const [expertModalOpen, setExpertModalOpen] = useState(false);
  const [editingExpert, setEditingExpert] = useState<ExpertInfo | null>(null);
  const [createStep, setCreateStep] = useState<'select' | 'form'>('select');
  const [selectedApp, setSelectedApp] = useState<IApp | null>(null);
  // 空间头像：绑定/编辑时写成员行（空间级覆盖）；从零构建时写身份层
  const [avatar, setAvatar] = useState('');

  // ---- 成员添加状态 ----
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [memberForm] = Form.useForm();
  const [userOptions, setUserOptions] = useState<User[]>([]);
  const [searchingUser, setSearchingUser] = useState(false);

  const [expertForm] = Form.useForm();
  const expertNameValue = Form.useWatch('app_name', expertForm);
  const [equipment, setEquipment] = useState<ExpertEquipmentItem[]>([]);
  const [roleHint, setRoleHint] = useState('');

  // ---- 数据加载 ----
  const { data: ws } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  const { data: experts, loading: expertsLoading, refresh: refreshExperts } = useRequest(async () => {
    if (!ws?.id) return [];
    const [err, res] = await apiInterceptors(listExperts(ws.id));
    return err ? [] : (res || []);
  }, { refreshDeps: [ws?.id] });

  const { data: members, loading: membersLoading, refresh: refreshMembers } = useRequest(async () => {
    if (!ws?.id) return [];
    const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
    return err ? [] : res || [];
  }, { refreshDeps: [ws?.id] });

  // Agent 模块已有应用（GptsApp），供"选择已有 Agent"绑定进空间
  const { data: appList } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getAppList({ page: 1, page_size: 100 }));
    return err ? [] : (res?.app_list || []);
  });

  const { data: resourceOptions } = useRequest(async () => {
    if (!ws?.id) return [];
    const [err, res] = await apiInterceptors(listResources({ workspace_id: ws.id }));
    if (err || !res) return [];
    return ((res || []) as PoolResourceRow[]).filter((r) => ['skill', 'mcp', 'knowledge_space', 'data_source'].includes(r.type));
  }, { refreshDeps: [ws?.id] });

  // 全局技能库 / MCP 注册表：专家外挂可直接引用全局资源（skill/MCP），
  // 知识库/数据源属空间域资源，仍只能从空间资源池（能力绑定）选择
  const { data: globalSkills } = useRequest(async () => {
    const [, res] = await apiInterceptors(getSkillList({ filter: '' }, { page: 1, page_size: 200 }));
    return res?.items || [];
  });
  const { data: globalMcps } = useRequest(async () => {
    const [err, res] = await apiInterceptors(getMCPList({ filter: '' }, { page: '1', page_size: '200' }));
    if (err) return [];
    return (res as { items?: GlobalMcpOption[] })?.items || [];
  });

  const { can } = useSpaceRole(ws?.id);
  const canManage = can('space.workspace.manage');

  const resourceRefOptions = (type: string) => {
    const poolRows = ((resourceOptions || []) as PoolResourceRow[]).filter((r) => r.type === type);
    const poolRefs = new Set<string>();
    poolRows.forEach((r) => {
      if (r.name) poolRefs.add(String(r.name));
      if (r.physical_ref) poolRefs.add(String(r.physical_ref));
    });
    const poolOpts = poolRows.map((r) => ({ value: r.name, label: r.name }));
    if (type === 'skill') {
      const extra = ((globalSkills || []) as GlobalSkillOption[])
        .filter((s) => !poolRefs.has(String(s.skill_code)) && !poolRefs.has(String(s.name)))
        .map((s) => ({ value: s.skill_code, label: `${s.name}${s.description ? ` — ${s.description}` : ''}` }));
      return [...poolOpts, ...extra];
    }
    if (type === 'mcp') {
      const extra = ((globalMcps || []) as GlobalMcpOption[])
        .filter((m) => !poolRefs.has(String(m.mcp_code)) && !poolRefs.has(String(m.name)))
        .map((m) => ({ value: m.mcp_code, label: `${m.name}${m.description ? ` — ${m.description}` : ''}` }));
      return [...poolOpts, ...extra];
    }
    return poolOpts;
  };

  // 资源下拉空状态引导：告诉用户去哪里添加资源，而不是干巴巴的"暂无数据"
  const resourceNotFound = (type: string) => {
    if (type === 'skill') {
      return (
        <div className="py-3 px-4 text-center">
          <p className="text-xs text-gray-400 m-0 mb-1">全局技能库为空</p>
          <Link href="/agent-skills" target="_blank">去技能模块创建编排 →</Link>
        </div>
      );
    }
    if (type === 'mcp') {
      return (
        <div className="py-3 px-4 text-center">
          <p className="text-xs text-gray-400 m-0 mb-1">没有可用的 MCP 服务</p>
          <Link href="/mcp" target="_blank">去 MCP 模块配置 →</Link>
        </div>
      );
    }
    return (
      <div className="py-3 px-4 text-center">
        <p className="text-xs text-gray-400 m-0 mb-1">本空间还未绑定该资源</p>
        <Link href={`/workspaces/detail/capability?id=${workspaceCode}`} target="_blank">去「能力绑定」添加 →</Link>
      </div>
    );
  };

  // ---- 专家操作 ----
  const openCreateExpert = () => {
    setEditingExpert(null);
    setCreateStep('select');
    setSelectedApp(null);
    expertForm.resetFields();
    setEquipment([]);
    setRoleHint('');
    setAvatar('');
    setExpertModalOpen(true);
  };

  const openEditExpert = (ex: ExpertInfo) => {
    setEditingExpert(ex);
    setCreateStep('form');
    setSelectedApp(null);
    expertForm.setFieldsValue({
      app_name: ex.app_name || ex.app_code,
      app_describe: ex.app_describe || '',
      system_prompt_template: '',
    });
    setRoleHint(ex.role_hint || '');
    setAvatar(ex.workspace_icon || '');
    setEquipment((ex.equipment || []).map((e) => ({ ...e, resource_type: normalizeResourceType(e.resource_type) })));
    setExpertModalOpen(true);
  };

  // 从零构建：跳转到 Agent 模块的新增 Agent 页面，身份在 Agent 模块创建后再回来绑定
  const handleCreateFromScratch = () => {
    setExpertModalOpen(false);
    router.push('/application/app');
  };

  // 选择已有 Agent：身份已在 Agent 模块维护，空间只配置职责 + 头像覆盖 + 外挂（走 bind 链路）
  const handleSelectApp = (app: IApp | null) => {
    setSelectedApp(app);
    setAvatar('');
    expertForm.setFieldsValue(
      app
        ? { app_name: app.app_name, app_describe: app.app_describe, system_prompt_template: '' }
        : { app_name: '', app_describe: '', system_prompt_template: '' },
    );
    setCreateStep('form');
  };

  const handleSubmitExpert = async () => {
    if (!ws?.id) return;
    // 绑定已有 Agent：只写成员行 + 外挂行，不动 GptsApp 身份
    if (selectedApp && !editingExpert) {
      const [err] = await apiInterceptors(bindExpert(ws.id, {
        app_code: selectedApp.app_code,
        role_hint: roleHint,
        icon: avatar,
        equipment,
      }));
      if (err) { message.error(err.message); return; }
      message.success('专家已加入空间');
      setExpertModalOpen(false);
      refreshExperts();
      return;
    }
    const values = await expertForm.validateFields();
    const payload = {
      app_code: editingExpert?.app_code,
      app_name: values.app_name,
      app_describe: values.app_describe,
      system_prompt_template: values.system_prompt_template || '',
      role_hint: roleHint,
      equipment,
      // 编辑已有专家：头像走空间级覆盖，不影响全局身份；从零构建：头像写身份层
      ...(editingExpert ? { workspace_icon: avatar } : { icon: avatar }),
    };
    const [err] = await apiInterceptors(upsertExpert(ws.id, payload));
    if (err) { message.error(err.message); return; }
    message.success(editingExpert ? '专家已更新' : '专家已创建');
    setExpertModalOpen(false);
    refreshExperts();
  };

  const handleUnbindExpert = async (app_code: string) => {
    if (!ws?.id) return;
    const [err] = await apiInterceptors(unbindExpert(ws.id, app_code));
    if (err) { message.error(err.message); return; }
    message.success('已解绑');
    refreshExperts();
  };

  // ---- 成员操作 ----
  const handleSearchUser = async (keyword: string) => {
    setSearchingUser(true);
    try {
      const res = await usersService.listUsers(1, 20, keyword);
      setUserOptions(res?.list || []);
    } catch {
      setUserOptions([]);
    } finally {
      setSearchingUser(false);
    }
  };

  const handleOpenAddMember = () => {
    setAddMemberOpen(true);
    handleSearchUser('');
  };

  const handleAddMember = async () => {
    try {
      const values = await memberForm.validateFields();
      const [err] = await apiInterceptors(addMember({
        workspace_id: ws?.id,
        user_id: Number(values.user_id),
        role: values.role,
      }));
      if (err) { message.error(err.message); return; }
      message.success('成员已添加');
      setAddMemberOpen(false);
      memberForm.resetFields();
      refreshMembers();
    } catch {}
  };

  const handleRoleChange = async (userId: number, role: string) => {
    const [err] = await apiInterceptors(updateMemberRole({
      workspace_id: ws?.id, user_id: userId, role,
    }));
    if (err) { message.error(err.message); return; }
    refreshMembers();
  };

  const handleRemoveMember = async (userId: number) => {
    const [err] = await apiInterceptors(removeMember({ workspace_id: ws?.id, user_id: userId }));
    if (err) { message.error(err.message); return; }
    refreshMembers();
  };

  // ---- 成员列表列定义 ----
  const memberCols = [
    {
      title: '', key: 'avatar', width: 50,
      render: () => (
        <Avatar size={36} icon={<UserOutlined />} style={{ background: 'var(--ws-accent-light, #e6f4ff)', color: 'var(--ws-accent, #1677ff)' }} />
      ),
    },
    {
      title: '成员', dataIndex: 'user_name',
      render: (name: string, r: MemberRow) => (
        <div>
          <div className="font-medium">{name || `用户 ${r.user_id}`}</div>
          <div className="text-xs text-gray-400">ID: {r.user_id}</div>
        </div>
      ),
    },
    {
      title: '角色', dataIndex: 'role', width: 160,
      render: (role: string, r: MemberRow) => canManage ? (
        <Select
          size="small"
          value={role}
          onChange={(v) => handleRoleChange(r.user_id, v)}
          options={[
            { value: 'owner', label: '管理' },
            { value: 'contributor', label: '使用' },
            { value: 'viewer', label: '查看' },
          ]}
          disabled={role === 'owner'}
          style={{ width: 100 }}
        />
      ) : (
        <Tag icon={role === 'owner' ? <CrownOutlined /> : undefined} color={role === 'owner' ? 'gold' : 'default'}>
          {ROLE_LABELS[role] || role}
        </Tag>
      ),
    },
    {
      title: '', key: 'actions', width: 60,
      render: (_: MemberRow, r: MemberRow) => canManage && r.role !== 'owner' ? (
        <Popconfirm title="确认移除该成员？" onConfirm={() => handleRemoveMember(r.user_id)}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ) : null,
    },
  ];

  // ---- 专家列表列定义 ----
  const expertCols = [
    {
      title: '', key: 'avatar', width: 50,
      render: (_: ExpertInfo, r: ExpertInfo) => (
        <AgentAvatar icon={r.icon} name={r.app_name || r.app_code} size={36} />
      ),
    },
    {
      title: '专家', dataIndex: 'app_name',
      render: (name: string, r: ExpertInfo) => (
        <div>
          <div className="font-medium">{name || r.app_code}</div>
          <div className="text-xs text-gray-400 font-mono">{r.app_code}</div>
        </div>
      ),
    },
    {
      title: '职责', dataIndex: 'role_hint', width: 160,
      render: (v: string) => v || <span className="text-gray-400">-</span>,
    },
    {
      title: '外挂', dataIndex: 'equipment', width: 220,
      render: (eq: ExpertEquipmentItem[]) => (
        <Space wrap size={4}>
          {(eq || []).map((e, i) => {
            const meta = RESOURCE_TYPE_MAP[normalizeResourceType(e.resource_type)] || { label: e.resource_type, color: 'default' };
            return <Tag key={i} color={meta.color} icon={meta.icon}>{e.resource_ref}</Tag>;
          })}
          {!(eq || []).length && <span className="text-gray-400 text-xs">无外挂</span>}
        </Space>
      ),
    },
    {
      title: '状态', dataIndex: 'is_active', width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>,
    },
    {
      title: '', key: 'actions', width: 80,
      render: (_: ExpertInfo, r: ExpertInfo) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEditExpert(r)} />
          <Popconfirm title="确认解绑该专家？" onConfirm={() => handleUnbindExpert(r.app_code)}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="ws-page">
      <div className="ws-page-bg" />
      <div className="ws-page-content" style={{ paddingTop: 16, paddingBottom: 48 }}>
        <div className="ws-page-header mb-6">
          <div className="ws-page-header-left">
            <div className="ws-page-icon"><UserOutlined /></div>
            <div>
              <p className="ws-page-eyebrow">
                {ws?.name || '场景空间'}
                <span className="ws-page-eyebrow-code">{workspaceCode}</span>
              </p>
              <h1 className="ws-page-title">团队</h1>
              <p className="ws-page-subtitle">空间成员与 Agent 专家，共同组成工作团队</p>
            </div>
          </div>
          <div className="ws-page-actions">
            <Link href={`/workspaces/detail?id=${workspaceCode}`}>
              <Button className="ws-btn-icon" title="返回" icon={<ArrowLeftOutlined />} />
            </Link>
          </div>
        </div>

        {/* 空间成员 */}
        <div className="ws-surface mb-4">
          <div className="flex items-center justify-between px-5 pt-4 pb-3">
            <div>
              <h3 className="text-sm font-semibold m-0" style={{ color: 'var(--ws-ink)' }}>成员 ({members?.length || 0})</h3>
              <p className="text-xs m-0 mt-0.5" style={{ color: 'var(--ws-ink-3)' }}>可访问和操作本空间的人员</p>
            </div>
            {canManage && (
              <Button size="small" icon={<PlusOutlined />} onClick={handleOpenAddMember}>添加成员</Button>
            )}
          </div>
          <div className="px-2 pb-2">
            <Table
              rowKey="id"
              size="small"
              columns={memberCols}
              dataSource={members || []}
              pagination={false}
              showHeader={false}
              loading={membersLoading}
              locale={{ emptyText: <Empty description="暂无成员" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </div>
        </div>

        {/* Agent 专家 */}
        <div className="ws-surface">
          <div className="flex items-center justify-between px-5 pt-4 pb-3">
            <div>
              <h3 className="text-sm font-semibold m-0" style={{ color: 'var(--ws-ink)' }}>Agent 专家 ({experts?.length || 0})</h3>
              <p className="text-xs m-0 mt-0.5" style={{ color: 'var(--ws-ink-3)' }}>空间内的子 Agent，可被 Leader 调度执行，也可 @ 直接对话</p>
            </div>
            <Space>
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={openCreateExpert}>新建专家</Button>
            </Space>
          </div>
          <div className="px-2 pb-2">
            <Table
              rowKey="id"
              size="small"
              columns={expertCols}
              dataSource={experts || []}
              pagination={false}
              showHeader={false}
              loading={expertsLoading}
              locale={{
                emptyText: (
                  <div className="py-8 text-center">
                    <RobotOutlined className="text-2xl text-gray-300 mb-2" />
                    <p className="text-sm text-gray-400 m-0">暂无专家，点击上方「新建专家」开始</p>
                  </div>
                ),
              }}
            />
          </div>
        </div>
      </div>

      {/* 添加成员 Modal */}
      <Modal
        open={addMemberOpen}
        onCancel={() => setAddMemberOpen(false)}
        onOk={handleAddMember}
        title="添加成员"
        okText="添加"
        width={480}
      >
        <Form form={memberForm} layout="vertical" className="mt-4" initialValues={{ role: 'contributor' }}>
          <Form.Item name="user_id" label="用户" rules={[{ required: true, message: '搜索并选择用户' }]}>
            <Select
              showSearch
              filterOption={false}
              loading={searchingUser}
              placeholder="按用户名 / 邮箱搜索"
              onSearch={handleSearchUser}
              notFoundContent={searchingUser ? <Spin size="small" /> : null}
              options={userOptions.map((u) => ({
                value: u.id,
                label: `#${u.id} ${u.name}${u.fullname ? ` (${u.fullname})` : ''}${u.email ? ` · ${u.email}` : ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="角色">
            <Select options={[
              { value: 'contributor', label: '使用' },
              { value: 'viewer', label: '查看' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 新建/编辑专家 Modal */}
      <Modal
        title={null}
        open={expertModalOpen}
        onCancel={() => setExpertModalOpen(false)}
        footer={null}
        width={720}
        destroyOnClose
      >
        {createStep === 'select' ? (
          <div className="py-2">
            <h3 className="text-lg font-semibold mb-1">新建专家</h3>
            <p className="text-sm text-gray-500 mb-6">选择 Agent 模块的已有 Agent 加入空间，或从零构建自定义专家</p>

            <div className="mb-6">
              <div
                className="p-4 border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-all"
                onClick={handleCreateFromScratch}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500">
                    <PlusOutlined />
                  </div>
                  <div>
                    <div className="font-medium">从零构建</div>
                    <div className="text-xs text-gray-400">完全自定义名称、人设和资源配置</div>
                  </div>
                </div>
              </div>
            </div>

            <Divider className="my-4">或选择已有 Agent</Divider>

            <div className="grid grid-cols-2 gap-3 max-h-[320px] overflow-y-auto pr-1">
              {(appList || []).map((app) => (
                <div
                  key={app.app_code}
                  className="p-3 border border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 hover:shadow-sm transition-all"
                  onClick={() => handleSelectApp(app)}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <AgentAvatar icon={app.icon} name={app.app_name} size={26} />
                    <span className="font-medium text-sm truncate">{app.app_name}</span>
                  </div>
                  <div className="text-xs text-gray-400 line-clamp-2">{app.app_describe || 'Agent 模块应用'}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="py-2">
            <div className="flex items-center gap-3 mb-6">
              {selectedApp ? (
                <>
                  <AgentAvatar icon={selectedApp.icon} name={selectedApp.app_name} size={40} />
                  <div>
                    <h3 className="text-lg font-semibold m-0">{selectedApp.app_name}</h3>
                    <p className="text-sm text-gray-500 m-0">加入空间：身份在 Agent 模块维护，此处配置职责与外挂</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                    <PlusOutlined />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold m-0">{editingExpert ? '编辑专家' : '从零构建'}</h3>
                    <p className="text-sm text-gray-500 m-0">{editingExpert ? '修改专家配置' : '自定义专家身份与能力'}</p>
                  </div>
                </>
              )}
              {!editingExpert && (
                <Button type="link" className="ml-auto" onClick={() => setCreateStep('select')}>
                  重新选择
                </Button>
              )}
            </div>

            <Form form={expertForm} layout="vertical" initialValues={{
              app_name: selectedApp?.app_name || editingExpert?.app_name || '',
              app_describe: selectedApp?.app_describe || editingExpert?.app_describe || '',
              system_prompt_template: '',
            }}>
              <Form.Item
                label={selectedApp || editingExpert ? '空间头像' : '头像'}
                extra={
                  selectedApp
                    ? '覆盖本空间的展示头像，不影响 Agent 模块的全局头像；清除后回落全局头像'
                    : editingExpert
                      ? '仅本空间展示生效，不影响 Agent 模块的全局头像'
                      : '保存为该 Agent 的全局头像，点击头像可上传或清除'
                }
              >
                <div className="flex items-center gap-3">
                  <AgentAvatarPicker
                    value={avatar}
                    name={selectedApp?.app_name || expertNameValue || editingExpert?.app_name}
                    onChange={setAvatar}
                    size={56}
                  />
                  {selectedApp && (
                    <span className="text-xs text-gray-400">
                      全局头像：
                      <AgentAvatar icon={selectedApp.icon} name={selectedApp.app_name} size={18} className="inline-flex align-middle mx-0.5" />
                    </span>
                  )}
                </div>
              </Form.Item>
              <Form.Item name="app_name" label="专家名称" rules={[{ required: true, message: '请输入名称' }]}>
                <Input placeholder="如：数据周报专家" disabled={!!selectedApp} />
              </Form.Item>
              <Form.Item name="app_describe" label="描述">
                <Input.TextArea rows={2} placeholder="专业领域/能力概述" disabled={!!selectedApp} />
              </Form.Item>
              {!selectedApp && (
                <Form.Item name="system_prompt_template" label="人设提示词">
                  <Input.TextArea rows={4} placeholder="定义专家的角色、目标、工作流和行为约束" />
                </Form.Item>
              )}
              <Form.Item label="空间内职责">
                <Input placeholder="在本空间主要负责…" value={roleHint} onChange={(e) => setRoleHint(e.target.value)} />
              </Form.Item>
              <Form.Item label="空间外挂">
                <div className="space-y-2">
                  {equipment.map((eq, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <Select
                        className="w-32"
                        value={eq.resource_type}
                        options={Object.entries(RESOURCE_TYPE_MAP).map(([k, v]) => ({ value: k, label: v.label }))}
                        onChange={(v) => setEquipment(prev => prev.map((x, idx) => idx === i ? { ...x, resource_type: v, resource_ref: '' } : x))}
                      />
                      <Select
                        className="flex-1"
                        value={eq.resource_ref}
                        placeholder="选择资源"
                        options={resourceRefOptions(eq.resource_type)}
                        notFoundContent={resourceNotFound(eq.resource_type)}
                        onChange={(v) => setEquipment(prev => prev.map((x, idx) => idx === i ? { ...x, resource_ref: v } : x))}
                      />
                      <Button type="text" danger icon={<DeleteOutlined />} onClick={() => setEquipment(prev => prev.filter((_, idx) => idx !== i))} />
                    </div>
                  ))}
                  <Button
                    type="dashed"
                    block
                    icon={<PlusOutlined />}
                    onClick={() => setEquipment(prev => [...prev, { resource_type: 'skill', resource_ref: '' }])}
                  >
                    添加外挂
                  </Button>
                  <div className="text-xs text-gray-400">技能 / MCP 可直接选用全局注册的资源；知识库 / 数据源需先在空间「能力绑定」中绑定</div>
                </div>
              </Form.Item>
            </Form>

            <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-gray-100">
              <Button onClick={() => setExpertModalOpen(false)}>取消</Button>
              <Button type="primary" onClick={handleSubmitExpert}>{editingExpert ? '保存' : selectedApp ? '加入空间' : '创建'}</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
