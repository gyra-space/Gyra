'use client';

import { apiInterceptors, getOrCreateHomeWorkspace, getWorkspaceInfo, listMembers, addMember, removeMember, updateMemberRole, updateWorkspace, setHomeWorkspace, releaseWorkspace } from '@/client/api';
import { usersService, type User } from '@/services/users';
import { getUserId } from '@/utils';
import { App, Button, Card, Descriptions, Empty, Form, Input, Modal, Select, Spin, Table, Tag, Alert } from 'antd';
import { useRequest } from 'ahooks';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SpaceModelsTab } from './space-models-tab';

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const workspaceCode = searchParams?.get('id') || '';
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [memberForm] = Form.useForm();
  const [editOpen, setEditOpen] = useState(false);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [userOptions, setUserOptions] = useState<User[]>([]);
  const [searching, setSearching] = useState(false);
  const [releaseOpen, setReleaseOpen] = useState(false);
  const [releaseConfirm, setReleaseConfirm] = useState('');
  const [releasing, setReleasing] = useState(false);
  const { message } = App.useApp();

  const { data: ws, loading, refresh } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  const { data: members, refresh: refreshMembers } = useRequest(async () => {
    if (!ws?.id) return [];
    const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
    return err ? [] : res || [];
  }, { refreshDeps: [ws?.id] });

  // 权限整合:空间管理员 owner(管理)才可维护空间模型,成员只读。
  const { data: canManage } = useRequest(async () => {
    if (!ws?.id) return false;
    const [err, res] = await apiInterceptors(listMembers({ workspace_id: ws.id }));
    if (err) return false;
    const list = Array.isArray(res) ? res : ((res as any)?.data || []);
    const me = list.find((m: any) => String(m.user_id) === String(getUserId()));
    return me?.role === 'owner';
  }, { refreshDeps: [ws?.id] });

  // 当前用户的默认(主)空间:用于标记"已是默认空间"。
  const { data: homeWs, refresh: refreshHome } = useRequest(async () => {
    const [err, res] = await apiInterceptors(
      getOrCreateHomeWorkspace({ user_id: Number(getUserId()) || 0 }),
    );
    return err ? null : res;
  }, { refreshDeps: [ws?.id] });
  const isHome = !!ws && !!homeWs && (homeWs as any)?.workspace_code === ws.workspace_code;
  const [settingHome, setSettingHome] = useState(false);

  const handleSetHome = async () => {
    if (!ws?.id) return;
    setSettingHome(true);
    const [err] = await apiInterceptors(setHomeWorkspace({
      workspace_id: ws.id,
      user_id: Number(getUserId()) || 0,
    }));
    setSettingHome(false);
    if (err) { message.error(err.message); return; }
    message.success('已设为默认空间');
    refreshHome();
  };

  const handleEditSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const [err] = await apiInterceptors(updateWorkspace({
        ...values,
        workspace_code: ws?.workspace_code,
      }));
      setSaving(false);
      if (err) { message.error(err.message); return; }
      message.success('Saved');
      setEditOpen(false);
      refresh();
    } catch (e) {}
  };

  const handleSearchUser = async (keyword: string) => {
    setSearching(true);
    try {
      // 空关键词也加载全部用户，便于在“添加成员”下拉中直接浏览并选择所有平台用户
      const res = await usersService.listUsers(1, 20, keyword);
      setUserOptions(res?.list || []);
    } catch {
      setUserOptions([]);
    } finally {
      setSearching(false);
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
      message.success('Member added');
      setAddMemberOpen(false);
      memberForm.resetFields();
      refreshMembers();
    } catch (e) {}
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

  const handleRelease = async () => {
    if (!ws?.workspace_code) return;
    setReleasing(true);
    const [err] = await apiInterceptors(releaseWorkspace({ workspace_code: ws.workspace_code }));
    setReleasing(false);
    if (err) { message.error(err.message); return; }
    message.success('空间已释放');
    setReleaseOpen(false);
    // 释放后跳回空间列表(该空间已从列表隐藏)
    router.push('/workspaces');
  };

  if (loading) return <div className="flex justify-center py-20"><Spin /></div>;
  if (!ws) return <div className="p-6"><Empty /></div>;

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-semibold">{t('settings.title') || 'Workspace Settings'}</h1>
        <Link href={`/workspaces/detail?id=${workspaceCode}`}><Button>{t('back') || 'Back'}</Button></Link>
      </div>

      <Card title={t('settings.basic') || 'Basic Info'} className="mb-4"
        extra={<div className="flex items-center gap-2">
          {isHome && <Tag color="blue">默认空间</Tag>}
          <Button
            type={isHome ? 'default' : 'primary'}
            disabled={isHome}
            loading={settingHome}
            onClick={handleSetHome}
          >
            {isHome ? '已是默认空间' : '设为默认空间'}
          </Button>
          <Button onClick={() => { form.setFieldsValue(ws); setEditOpen(true); }}>Edit</Button>
        </div>}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Code">{ws.workspace_code}</Descriptions.Item>
          <Descriptions.Item label="Name">{ws.name}</Descriptions.Item>
          <Descriptions.Item label="Type">{ws.type}</Descriptions.Item>
          <Descriptions.Item label="Scenario">{ws.scenario_type || '-'}</Descriptions.Item>
          <Descriptions.Item label="Owner">{ws.owner_user_id}</Descriptions.Item>
          <Descriptions.Item label="Default Agent">{ws.default_agent_app_code || '-'}</Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>{ws.description || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={t('settings.members') || 'Members'}
        extra={<Button onClick={handleOpenAddMember}>+ {t('settings.add_member') || 'Add Member'}</Button>}>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={members || []}
          locale={{ emptyText: 'No members' }}
          columns={[
            { title: 'User ID', dataIndex: 'user_id', width: 100 },
            { title: 'Name', dataIndex: 'user_name' },
            {
              title: 'Role', dataIndex: 'role', width: 200,
              render: (role: string, r: any) => (
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
                />
              ),
            },
            {
              title: '', key: 'actions', width: 100,
              render: (_: any, r: any) => r.role !== 'owner' ? (
                <Button size="small" danger onClick={() => handleRemoveMember(r.user_id)}>Remove</Button>
              ) : null,
            },
          ]}
        />
      </Card>

      <Card title="空间模型" className="mb-4">
        <SpaceModelsTab workspaceId={ws.id} workspaceCode={ws.workspace_code} canManage={!!canManage} />
      </Card>

      {canManage && (
        <Card
          title="危险操作"
          className="mb-4"
          styles={{ body: { background: '#fff1f0', borderRadius: 8 } }}
        >
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <p className="m-0 font-medium">释放此空间</p>
              <p className="m-0 text-xs text-gray-500">
                释放后空间将从列表中隐藏,并移除成员/资源/会话关联等核心记录。底层数据保留,可恢复。此操作不可撤销,请谨慎。
              </p>
            </div>
            <Button danger type="primary" onClick={() => { setReleaseConfirm(''); setReleaseOpen(true); }}>
              释放空间
            </Button>
          </div>
        </Card>
      )}

      <Modal
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleEditSave}
        confirmLoading={saving}
        title="Edit Workspace"
        okText="Save"
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="scenario_type" label="Scenario Type"><Input /></Form.Item>
          <Form.Item name="default_agent_app_code" label="Default Agent App Code"><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal
        open={addMemberOpen}
        onCancel={() => setAddMemberOpen(false)}
        onOk={handleAddMember}
        title="Add Member"
        okText="Add"
      >
        <Form form={memberForm} layout="vertical" className="mt-4" initialValues={{ role: 'contributor' }}>
          <Form.Item name="user_id" label="User" rules={[{ required: true, message: 'Search and select a user' }]}>
            <Select
              showSearch
              filterOption={false}
              loading={searching}
              placeholder="Search by username / user code / email"
              onSearch={handleSearchUser}
              notFoundContent={searching ? <Spin size="small" /> : null}
              options={userOptions.map((u) => ({
                value: u.id,
                label: `#${u.id} ${u.name}${u.fullname ? ` (${u.fullname})` : ''}${u.email ? ` · ${u.email}` : ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="Role">
            <Select options={[
              { value: 'contributor', label: '使用' },
              { value: 'viewer', label: '查看' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={releaseOpen}
        onCancel={() => setReleaseOpen(false)}
        onOk={handleRelease}
        confirmLoading={releasing}
        okText="确认释放"
        cancelText="取消"
        okButtonProps={{ danger: true, disabled: releaseConfirm.trim() !== ws?.name }}
        title="释放场景空间"
      >
        <Alert
          type="warning"
          showIcon
          message="此操作不可撤销"
          description="释放后空间将从列表中隐藏,并移除成员、资源、会话关联等核心记录。底层数据保留但不可在列表中访问。"
          className="mb-4"
        />
        <p className="mb-2">请输入空间名称 <b>{ws?.name}</b> 以确认释放:</p>
        <Input
          value={releaseConfirm}
          onChange={(e) => setReleaseConfirm(e.target.value)}
          placeholder={ws?.name}
        />
      </Modal>
    </div>
  );
}
