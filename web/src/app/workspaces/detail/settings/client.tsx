'use client';

import { apiInterceptors, getOrCreateHomeWorkspace, getWorkspaceInfo, updateWorkspace, setHomeWorkspace, releaseWorkspace } from '@/client/api';
import { addEcpConfirmer, listEcpConfirmers, removeEcpConfirmer, type EcpConfirmer } from '@/client/api/ecp';
import { usersService, type User } from '@/services/users';
import { getUserId } from '@/utils';
import { useSpaceRole } from '@/hooks/use-space-role';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Descriptions, Empty, Form, Input, Modal, Popconfirm, Select, Spin, Table, Tag, Alert } from 'antd';
import { useRequest } from 'ahooks';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SpaceModelsTab } from './space-models-tab';

/** 欢迎预设问题的默认值(与首页简洁模式兜底一致) */
const DEFAULT_SUGGEST_QUESTIONS = ['帮我看看这周的数据情况'];

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const workspaceCode = searchParams?.get('id') || '';
  const { t } = useTranslation();
  // ECP 语义层 workspace 由场景空间 code 派生(ecp_<workspace_code>,见 ecp_derive.py)
  const ecpWsId = workspaceCode ? `ecp_${workspaceCode}` : '';
  const [form] = Form.useForm();
  const [suggestForm] = Form.useForm();
  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingSuggest, setSavingSuggest] = useState(false);
  // 提案确认人(ECP confirmer)配置
  const [newConfirmerId, setNewConfirmerId] = useState<string>();
  const [confirmerOptions, setConfirmerOptions] = useState<User[]>([]);
  const [searchingConfirmer, setSearchingConfirmer] = useState(false);
  const [addingConfirmer, setAddingConfirmer] = useState(false);
  const [releaseOpen, setReleaseOpen] = useState(false);
  const [releaseConfirm, setReleaseConfirm] = useState('');
  const [releasing, setReleasing] = useState(false);
  const { message } = App.useApp();

  const { data: ws, loading, refresh } = useRequest(async () => {
    if (!workspaceCode) return null;
    const [err, res] = await apiInterceptors(getWorkspaceInfo(workspaceCode));
    return err ? null : res;
  }, { refreshDeps: [workspaceCode] });

  // 权限整合:空间管理(space.workspace.manage,owner)才可维护模型/确认人。
  const { can } = useSpaceRole(ws?.id);
  const canManage = can('space.workspace.manage');

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

  // 欢迎预设问题表单初始化:读取 workspace.settings.suggest_questions
  useEffect(() => {
    if (!ws) return;
    const list = (ws.settings as any)?.suggest_questions;
    suggestForm.setFieldsValue({
      suggest_questions: Array.isArray(list) && list.length ? list : DEFAULT_SUGGEST_QUESTIONS,
    });
  }, [ws, suggestForm]);

  const handleSaveSuggest = async () => {
    try {
      const values = await suggestForm.validateFields();
      const list = (values.suggest_questions || []).filter(
        (q: unknown) => typeof q === 'string' && q.trim().length > 0,
      );
      setSavingSuggest(true);
      const [err] = await apiInterceptors(updateWorkspace({
        workspace_code: ws?.workspace_code,
        // WorkspaceRequest.name 为必填校验字段;仅补 name 不改名,其余由后端按非 None 更新
        name: ws?.name,
        settings: {
          ...((ws?.settings as any) || {}),
          suggest_questions: list,
        },
      }));
      setSavingSuggest(false);
      if (err) { message.error(err.message); return; }
      message.success('已保存预设问题');
      refresh();
    } catch (e) {}
  };

  // ---------- 提案确认人(ECP confirmer)配置 ----------
  const { data: confirmers, refresh: refreshConfirmers } = useRequest(
    async () => {
      if (!ecpWsId) return [];
      const [err, res] = await apiInterceptors(listEcpConfirmers(ecpWsId));
      return err ? [] : (res ?? []);
    },
    { refreshDeps: [ecpWsId] },
  );

  const handleSearchConfirmer = async (keyword: string) => {
    setSearchingConfirmer(true);
    try {
      const res = await usersService.listUsers(1, 20, keyword);
      setConfirmerOptions(res?.list || []);
    } catch {
      setConfirmerOptions([]);
    } finally {
      setSearchingConfirmer(false);
    }
  };

  const handleAddConfirmer = async () => {
    if (!newConfirmerId) return;
    setAddingConfirmer(true);
    const [err] = await apiInterceptors(
      addEcpConfirmer({ user_id: newConfirmerId, workspace_id: ecpWsId }),
    );
    setAddingConfirmer(false);
    if (err) { message.error(err.message); return; }
    message.success('已添加提案确认人');
    setNewConfirmerId(undefined);
    refreshConfirmers();
  };

  const handleRemoveConfirmer = async (confirmerId: number) => {
    const [err] = await apiInterceptors(removeEcpConfirmer(confirmerId));
    if (err) { message.error(err.message); return; }
    message.success('已移除提案确认人');
    refreshConfirmers();
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

      <Card title="提案确认" className="mb-4">
        <p className="mb-3 text-xs text-gray-500">
          空间成员默认可确认提案（成员增删时自动同步确认权限），owner 始终可确认。可在下方按用户名搜索配置或移除确认人。
        </p>
        {canManage && (
          <div className="mb-3 flex gap-2">
            <Select
              showSearch
              filterOption={false}
              loading={searchingConfirmer}
              style={{ flex: 1 }}
              placeholder="按用户名 / 邮箱搜索用户"
              value={newConfirmerId}
              onChange={setNewConfirmerId}
              onSearch={handleSearchConfirmer}
              notFoundContent={searchingConfirmer ? <Spin size="small" /> : null}
              options={confirmerOptions.map((u) => ({
                value: String(u.id),
                label: `#${u.id} ${u.name}${u.fullname ? ` (${u.fullname})` : ''}${u.email ? ` · ${u.email}` : ''}`,
              }))}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              loading={addingConfirmer}
              disabled={!newConfirmerId}
              onClick={handleAddConfirmer}
            >
              添加
            </Button>
          </div>
        )}
        {(confirmers ?? []).length === 0 ? (
          <Empty description="暂无确认人（空间成员将自动获得确认权限）" />
        ) : (
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={confirmers || []}
            locale={{ emptyText: '暂无确认人' }}
            columns={[
              {
                title: '用户',
                dataIndex: 'user_name',
                render: (name: string | null, r: EcpConfirmer) => name || `#${r.user_id}`,
              },
              { title: 'User ID', dataIndex: 'user_id', width: 120 },
              {
                title: '范围',
                dataIndex: 'scope',
                width: 130,
                render: (s?: string | null) => s || '全部范围',
              },
              ...(canManage
                ? [
                    {
                      title: '',
                      key: 'actions',
                      width: 60,
                      render: (_: unknown, r: EcpConfirmer) => (
                        <Popconfirm title="移除该确认人？" onConfirm={() => handleRemoveConfirmer(r.id)}>
                          <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      ),
                    },
                  ]
                : []),
            ]}
          />
        )}
      </Card>

      <SpaceModelsTab workspaceId={ws.id} workspaceCode={ws.workspace_code} canManage={!!canManage} collapsible />

      {canManage && (
        <Card title="欢迎预设问题（简洁模式首页「试试这些」）" className="mb-4">
          <p className="mb-3 text-xs text-gray-500">
            配置场景空间简洁模式首页输入框下方的预设问题（每条占一个按钮，点按即发送）。
            留空或删除全部则回退到默认问题「帮我看看这周的数据情况」。
          </p>
          <Form form={suggestForm} layout="vertical">
            <Form.List name="suggest_questions">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => (
                    <div key={field.key} className="flex items-start gap-2 mb-2">
                      <Form.Item
                        {...field}
                        className="flex-1 mb-0"
                        rules={[{ required: true, message: '请输入问题' }]}
                      >
                        <Input placeholder="输入预设问题，如：帮我看看这周的数据情况" />
                      </Form.Item>
                      <Button icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                    </div>
                  ))}
                  <Button type="dashed" icon={<PlusOutlined />} block onClick={() => add('')}>
                    添加问题
                  </Button>
                </>
              )}
            </Form.List>
          </Form>
          <div className="mt-3">
            <Button type="primary" loading={savingSuggest} onClick={handleSaveSuggest}>保存</Button>
          </div>
        </Card>
      )}

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
