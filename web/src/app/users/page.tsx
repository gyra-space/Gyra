'use client';

import React, { useEffect, useRef, useState } from 'react';
import { App, Avatar, Badge, Button, Form, Input, Space, Switch, Table, Tag, Modal } from 'antd';
import { DeleteOutlined, SearchOutlined, UserOutlined, KeyOutlined } from '@ant-design/icons';
import { usersService, User } from '@/services/users';
import { authService } from '@/services/auth';
import { permissionsService, type MyPermissions } from '@/services/permissions';
import { useRouter } from 'next/navigation';

const { Search } = Input;

export default function UsersPage() {
  const router = useRouter();
  const { message, modal } = App.useApp();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [oauthEnabled, setOauthEnabled] = useState<boolean | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [myRbac, setMyRbac] = useState<MyPermissions | null>(null);
  const checkedRef = useRef(false);
  const [resetPwdOpen, setResetPwdOpen] = useState(false);
  const [resetPwdSaving, setResetPwdSaving] = useState(false);
  const [resetPwdUser, setResetPwdUser] = useState<User | null>(null);
  const [resetPwdForm] = Form.useForm();

  // admin 判断：兼容 legacy role=admin 和 RBAC 角色/权限
  const isCurrentUserAdmin = (() => {
    if (currentUser?.role === 'admin') return true;
    if (myRbac?.roles?.some((r) => r === 'admin' || r === 'superadmin')) return true;
    if (myRbac?.permissions && Array.isArray(myRbac.permissions['system']) && myRbac.permissions['system'].includes('admin')) return true;
    return false;
  })();

  useEffect(() => {
    if (checkedRef.current) return;
    checkedRef.current = true;
    authService.getOAuthStatus().then((status) => {
      setOauthEnabled(status.enabled);
      if (!status.enabled) {
        router.replace('/');
      }
    });
    // Get current user info
    authService.getCurrentUser().then((user) => {
      setCurrentUser(user);
    }).catch(() => {
      // Ignore error
    });
    permissionsService.getMyPermissions().then(setMyRbac).catch(() => setMyRbac(null));
  }, [router]);

  useEffect(() => {
    if (oauthEnabled) fetchUsers();
  }, [oauthEnabled, page, keyword]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const result = await usersService.listUsers(page, pageSize, keyword);
      setUsers(result.list);
      setTotal(result.total);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleRole = async (user: User) => {
    const newRole = user.role === 'admin' ? 'normal' : 'admin';
    try {
      const updated = await usersService.updateUser(user.id, { role: newRole });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      message.success(`已${newRole === 'admin' ? '设为' : '取消'}管理员`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const handleToggleActive = async (user: User, checked: boolean) => {
    const newActive = checked ? 1 : 0;
    try {
      const updated = await usersService.updateUser(user.id, { is_active: newActive });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      message.success(checked ? '用户已启用' : '用户已禁用');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const handleDelete = async (user: User) => {
    // Prevent self-deletion
    if (currentUser && currentUser.id === user.id) {
      message.error('不能删除自己的账号');
      return;
    }

    modal.confirm({
      title: '确认删除用户',
      content: `确定要删除用户 "${user.name || user.fullname || user.email || user.id}" 吗？此操作将禁用该用户账号。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await usersService.deleteUser(user.id);
          message.success('用户已删除');
          fetchUsers(); // Refresh list
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const handleResetPassword = async () => {
    if (!resetPwdUser) return;
    let values: { password: string };
    try {
      values = await resetPwdForm.validateFields();
    } catch {
      return; // validation failed
    }
    setResetPwdSaving(true);
    try {
      await usersService.updateUser(resetPwdUser.id, { password: values.password });
      message.success('密码已重置');
      setResetPwdOpen(false);
      resetPwdForm.resetFields();
      setResetPwdUser(null);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '重置密码失败');
    } finally {
      setResetPwdSaving(false);
    }
  };

  const openResetPassword = (user: User) => {
    setResetPwdUser(user);
    resetPwdForm.resetFields();
    setResetPwdOpen(true);
  };

  const columns = [
    {
      title: '头像',
      dataIndex: 'avatar',
      key: 'avatar',
      width: 64,
      render: (_: any, record: User) => (
        <Avatar
          src={record.avatar || undefined}
          icon={!record.avatar ? <UserOutlined /> : undefined}
          size={36}
          className="bg-gradient-to-tr from-[#31afff] to-[#4f46e5]"
        />
      ),
    },
    {
      title: '用户名',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => v || '-',
    },
    {
      title: '全名',
      dataIndex: 'fullname',
      key: 'fullname',
      render: (v: string) => v || '-',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      render: (v: string) => v || '-',
    },
    {
      title: 'OAuth 提供商',
      dataIndex: 'oauth_provider',
      key: 'oauth_provider',
      render: (v: string) => v ? <Tag>{v}</Tag> : '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (v: string) => (
        <Tag color={v === 'admin' ? 'gold' : 'default'}>
          {v === 'admin' ? '管理员' : '普通用户'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (v: number, record: User) => (
        <Switch
          checked={v === 1}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleToggleActive(record, checked)}
          size="small"
        />
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'gmt_create',
      key: 'gmt_create',
      render: (v: string | null) =>
        v ? new Date(v).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: User) => (
        <Space>
          <Button
            size="small"
            type={record.role === 'admin' ? 'default' : 'primary'}
            onClick={() => handleToggleRole(record)}
          >
            {record.role === 'admin' ? '取消管理员' : '设为管理员'}
          </Button>
          <Button
            size="small"
            icon={<KeyOutlined />}
            onClick={() => openResetPassword(record)}
          >
            重置密码
          </Button>
          {/* Show delete button only for admin users, hide for self */}
          {isCurrentUserAdmin && currentUser?.id !== record.id && (
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  if (oauthEnabled === null) {
    return null;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-1">用户管理</h1>
        <p className="text-sm text-gray-500">管理通过 OAuth2 登录的用户，设置角色与状态。</p>
      </div>

      <div className="mb-4">
        <Search
          placeholder="搜索用户名 / 邮箱"
          allowClear
          style={{ width: 300 }}
          onSearch={(v) => {
            setKeyword(v);
            setPage(1);
          }}
          prefix={<SearchOutlined className="text-gray-400" />}
        />
      </div>

      <Table<User>
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 条`,
        }}
        scroll={{ x: 1000 }}
        className="bg-white dark:bg-[#1a1a1a] rounded-xl shadow-sm"
      />

      {/* Reset Password Modal */}
      <Modal
        title={
          resetPwdUser
            ? `重置密码 - ${resetPwdUser.name || resetPwdUser.email || resetPwdUser.id}`
            : '重置密码'
        }
        open={resetPwdOpen}
        onOk={handleResetPassword}
        onCancel={() => {
          setResetPwdOpen(false);
          setResetPwdUser(null);
          resetPwdForm.resetFields();
        }}
        confirmLoading={resetPwdSaving}
        destroyOnClose
      >
        <Form form={resetPwdForm} layout="vertical">
          <Form.Item
            name="password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码长度不能少于 6 位' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="确认新密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请再次输入新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
