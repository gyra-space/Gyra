'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  App,
  Button,
  DatePicker,
  Form,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import {
  permissionsService,
  type PermissionDefinition,
  type ResourceGrant,
} from '@/services/permissions';
import { usersService } from '@/services/users';
import ResourceSelector from '@/components/permissions/ResourceSelector';

const { Text } = Typography;

function isExpired(g: ResourceGrant): boolean {
  return !!g.expires_at && new Date(g.expires_at).getTime() < Date.now();
}

export default function GrantManagement() {
  const { t } = useTranslation();
  const { message } = App.useApp();

  const [grants, setGrants] = useState<ResourceGrant[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterResourceType, setFilterResourceType] = useState<string | undefined>(undefined);
  const [userNames, setUserNames] = useState<Record<number, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await permissionsService.listGrants(
        filterResourceType ? { resource_type: filterResourceType } : undefined,
      );
      setGrants(data);
      // 补用户名展示(只查缺失的)
      const missing = [...new Set(data.map((g) => g.user_id))].filter((id) => !(id in userNames));
      if (missing.length) {
        const patch: Record<number, string> = {};
        await Promise.all(
          missing.map(async (id) => {
            try {
              const res = await usersService.listUsers(1, 1, String(id));
              const u = res.list?.[0];
              patch[id] = u ? u.name : `#${id}`;
            } catch {
              patch[id] = `#${id}`;
            }
          }),
        );
        setUserNames((prev) => ({ ...prev, ...patch }));
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载授权列表失败');
    } finally {
      setLoading(false);
    }
  }, [filterResourceType, message, userNames]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterResourceType]);

  // ========== 创建授权 ==========
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();
  const [grantableDefs, setGrantableDefs] = useState<PermissionDefinition[]>([]);
  const [userOptions, setUserOptions] = useState<{ value: number; label: string }[]>([]);
  const [resourceIds, setResourceIds] = useState<string[]>([]);
  const selectedDefId = Form.useWatch('permission_def_id', form);
  const selectedDef = grantableDefs.find((d) => d.id === selectedDefId);

  useEffect(() => {
    if (!createOpen) return;
    permissionsService
      .listPermissionDefinitions({ is_active: true })
      .then((defs) => setGrantableDefs(defs.filter((d) => d.grantable)))
      .catch(() => setGrantableDefs([]));
    searchUsers('');
  }, [createOpen]);

  const searchUsers = async (keyword: string) => {
    try {
      const res = await usersService.listUsers(1, 50, keyword);
      setUserOptions(
        (res.list || []).map((u) => ({
          value: u.id,
          label: `${u.name}${u.fullname && u.fullname !== u.name ? `(${u.fullname})` : ''}`,
        })),
      );
    } catch {
      /* 忽略搜索失败 */
    }
  };

  const submitCreate = async () => {
    const values = await form.validateFields();
    if (!selectedDef) {
      message.error('请选择权限');
      return;
    }
    if (!resourceIds.length) {
      message.error('请选择资源实例');
      return;
    }
    setCreating(true);
    try {
      await permissionsService.createGrant({
        user_id: values.user_id,
        permission_key: `${selectedDef.resource_type}.${selectedDef.action}`,
        resource_id: resourceIds[0],
        expires_at: values.expires_at ? (values.expires_at as dayjs.Dayjs).toISOString() : null,
      });
      message.success('授权已创建');
      setCreateOpen(false);
      form.resetFields();
      setResourceIds([]);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const revoke = async (g: ResourceGrant) => {
    try {
      await permissionsService.deleteGrant(g.id);
      message.success('已回收');
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '回收失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    {
      title: '用户',
      dataIndex: 'user_id',
      width: 120,
      render: (v: number) => userNames[v] || `#${v}`,
    },
    {
      title: '权限',
      dataIndex: 'permission_key',
      render: (v: string) => <Tag color="purple">{v}</Tag>,
    },
    {
      title: '资源实例',
      dataIndex: 'resource_id',
      render: (v: string, g: ResourceGrant) => (
        <Text>
          <Tag>{g.resource_type}</Tag>
          {v}
        </Text>
      ),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      width: 190,
      render: (v: string | null, g: ResourceGrant) =>
        v ? (
          <Text type={isExpired(g) ? 'danger' : undefined}>
            {new Date(v).toLocaleString()}
            {isExpired(g) ? '(已过期)' : ''}
          </Text>
        ) : (
          <Text type="secondary">永久</Text>
        ),
    },
    { title: '创建时间', dataIndex: 'gmt_create', width: 170 },
    {
      title: '操作',
      key: 'ops',
      width: 90,
      render: (_: unknown, g: ResourceGrant) => (
        <Popconfirm title="回收这条授权?" onConfirm={() => revoke(g)}>
          <Button size="small" danger>
            回收
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const resourceTypes = [...new Set(grantableDefs.map((d) => d.resource_type))];

  return (
    <div>
      <Space className="mb-3" wrap>
        <Select
          value={filterResourceType}
          onChange={setFilterResourceType}
          style={{ width: 150 }}
          allowClear
          placeholder="全部资源类型"
          options={resourceTypes.map((rt) => ({ value: rt, label: rt }))}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新建授权
        </Button>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
          刷新
        </Button>
      </Space>

      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns as any}
        dataSource={grants}
        pagination={{ pageSize: 20, showTotal: (n) => `共 ${n} 条` }}
      />

      <Modal
        open={createOpen}
        title="新建实例级授权"
        onOk={submitCreate}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={creating}
        okText="创建"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="user_id" label="授权用户" rules={[{ required: true, message: '请选择用户' }]}>
            <Select
              showSearch
              filterOption={false}
              onSearch={searchUsers}
              placeholder="输入用户名搜索"
              options={userOptions}
            />
          </Form.Item>
          <Form.Item
            name="permission_def_id"
            label="权限"
            rules={[{ required: true, message: '请选择权限' }]}
            extra="仅列出支持实例级授权(grantable)的权限"
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="选择权限 key"
              options={grantableDefs.map((d) => ({
                value: d.id,
                label: `${d.name}(${d.resource_type}.${d.action})`,
              }))}
            />
          </Form.Item>
          <Form.Item label="资源实例" required>
            <ResourceSelector
              resourceType={selectedDef?.resource_type || 'agent'}
              selectedResourceIds={resourceIds}
              onChange={(ids) => setResourceIds(ids.slice(-1))}
              allowWildcard={false}
            />
          </Form.Item>
          <Form.Item name="expires_at" label="过期时间" extra="留空为永久授权">
            <DatePicker showTime className="w-full" disabledDate={(d) => d.isBefore(dayjs())} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
