'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App,
  Badge,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { CheckOutlined, CloseOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  permissionRequestService,
  type PermissionRequest,
} from '@/services/permissionRequest';
import { permissionsService, type PermissionDefinition, type Role } from '@/services/permissions';
import ResourceSelector from '@/components/permissions/ResourceSelector';

const { Text } = Typography;

const TYPE_META: Record<PermissionRequest['request_type'], { label: string; color: string }> = {
  role_assign: { label: '角色申请', color: 'blue' },
  permission_grant: { label: '权限申请', color: 'purple' },
  account_activation: { label: '账号激活', color: 'orange' },
};

const STATUS_META: Record<PermissionRequest['status'], { label: string; color: string }> = {
  pending: { label: '待审批', color: 'gold' },
  approved: { label: '已通过', color: 'green' },
  rejected: { label: '已驳回', color: 'red' },
  cancelled: { label: '已撤销', color: 'default' },
};

function requestTarget(r: PermissionRequest): string {
  if (r.request_type === 'role_assign') return r.role_name || `角色 #${r.role_id}`;
  if (r.request_type === 'permission_grant')
    return `${r.resource_type}.${r.action} @ ${r.resource_id || '*'}`;
  return '激活当前账号';
}

interface ApprovalManagementProps {
  roles: Role[];
  isAdmin: boolean;
}

export default function ApprovalManagement({ roles, isAdmin }: ApprovalManagementProps) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [innerTab, setInnerTab] = useState<'console' | 'mine'>(isAdmin ? 'console' : 'mine');

  // ========== 审批台(管理员) ==========
  const [items, setItems] = useState<PermissionRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  const loadConsole = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const [result, count] = await Promise.all([
        permissionRequestService.listRequests({
          status: statusFilter || undefined,
          request_type: typeFilter,
          page,
          page_size: 20,
        }),
        permissionRequestService.getPendingCount(),
      ]);
      setItems(result.items);
      setTotal(result.total);
      setPendingCount(count);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载申请列表失败');
    } finally {
      setLoading(false);
    }
  }, [isAdmin, statusFilter, typeFilter, page, message]);

  useEffect(() => {
    if (innerTab === 'console') loadConsole();
  }, [innerTab, loadConsole]);

  // ========== 我的申请 ==========
  const [myItems, setMyItems] = useState<PermissionRequest[]>([]);
  const [myTotal, setMyTotal] = useState(0);
  const [myPage, setMyPage] = useState(1);
  const [myLoading, setMyLoading] = useState(false);

  const loadMine = useCallback(async () => {
    setMyLoading(true);
    try {
      const result = await permissionRequestService.getMyRequests({ page: myPage, page_size: 20 });
      setMyItems(result.items);
      setMyTotal(result.total);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载我的申请失败');
    } finally {
      setMyLoading(false);
    }
  }, [myPage, message]);

  useEffect(() => {
    if (innerTab === 'mine') loadMine();
  }, [innerTab, loadMine]);

  // ========== 审批操作 ==========
  const [reviewTarget, setReviewTarget] = useState<PermissionRequest | null>(null);
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject'>('approve');
  const [reviewComment, setReviewComment] = useState('');
  const [reviewing, setReviewing] = useState(false);

  const openReview = (r: PermissionRequest, action: 'approve' | 'reject') => {
    setReviewTarget(r);
    setReviewAction(action);
    setReviewComment('');
  };

  const submitReview = async () => {
    if (!reviewTarget) return;
    setReviewing(true);
    try {
      if (reviewAction === 'approve') {
        await permissionRequestService.approveRequest(reviewTarget.id, reviewComment || undefined);
        message.success('已通过');
      } else {
        await permissionRequestService.rejectRequest(reviewTarget.id, reviewComment || undefined);
        message.success('已驳回');
      }
      setReviewTarget(null);
      loadConsole();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    } finally {
      setReviewing(false);
    }
  };

  // ========== 发起申请 ==========
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();
  const applyType = Form.useWatch('request_type', form) as PermissionRequest['request_type'] | undefined;
  const [grantableDefs, setGrantableDefs] = useState<PermissionDefinition[]>([]);
  const [resourceIds, setResourceIds] = useState<string[]>([]);

  useEffect(() => {
    if (!createOpen) return;
    permissionsService
      .listPermissionDefinitions({ is_active: true })
      .then((defs) => setGrantableDefs(defs.filter((d) => d.grantable)))
      .catch(() => setGrantableDefs([]));
  }, [createOpen]);

  const submitCreate = async () => {
    const values = await form.validateFields();
    setCreating(true);
    try {
      const payload: any = {
        request_type: values.request_type,
        reason: values.reason,
      };
      if (values.request_type === 'role_assign') {
        payload.role_id = values.role_id;
      } else if (values.request_type === 'permission_grant') {
        const def = grantableDefs.find((d) => d.id === values.permission_def_id);
        if (!def) {
          message.error('请选择要申请的权限');
          return;
        }
        payload.resource_type = def.resource_type;
        payload.action = def.action;
        payload.resource_id = resourceIds[0];
      }
      await permissionRequestService.createRequest(payload);
      message.success('申请已提交,等待管理员审批');
      setCreateOpen(false);
      form.resetFields();
      setResourceIds([]);
      loadMine();
      if (isAdmin) loadConsole();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '提交失败');
    } finally {
      setCreating(false);
    }
  };

  const cancelRequest = async (r: PermissionRequest) => {
    try {
      await permissionRequestService.cancelRequest(r.id);
      message.success('已撤销');
      loadMine();
      if (isAdmin) loadConsole();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '撤销失败');
    }
  };

  // ========== 表格列 ==========
  const baseColumns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    {
      title: '类型',
      dataIndex: 'request_type',
      width: 110,
      render: (v: PermissionRequest['request_type']) => {
        const meta = TYPE_META[v] || { label: v, color: 'default' };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    {
      title: '目标',
      key: 'target',
      render: (_: unknown, r: PermissionRequest) => <Text>{requestTarget(r)}</Text>,
    },
    { title: '原因', dataIndex: 'reason', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: PermissionRequest['status']) => {
        const meta = STATUS_META[v] || { label: v, color: 'default' };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    { title: '申请时间', dataIndex: 'gmt_create', width: 170 },
  ];

  const consoleColumns = [
    { title: '申请人', dataIndex: 'user_name', width: 110, render: (v: string, r: PermissionRequest) => v || `#${r.user_id}` },
    ...baseColumns,
    {
      title: '操作',
      key: 'ops',
      width: 150,
      render: (_: unknown, r: PermissionRequest) =>
        r.status === 'pending' ? (
          <Space>
            <Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => openReview(r, 'approve')}>
              通过
            </Button>
            <Button size="small" danger icon={<CloseOutlined />} onClick={() => openReview(r, 'reject')}>
              驳回
            </Button>
          </Space>
        ) : (
          <Text type="secondary">{r.review_comment || '—'}</Text>
        ),
    },
  ];

  const myColumns = [
    ...baseColumns,
    {
      title: '操作',
      key: 'ops',
      width: 90,
      render: (_: unknown, r: PermissionRequest) =>
        r.status === 'pending' ? (
          <Popconfirm title="撤销这条申请?" onConfirm={() => cancelRequest(r)}>
            <Button size="small">撤销</Button>
          </Popconfirm>
        ) : (
          <Text type="secondary">{r.review_comment || '—'}</Text>
        ),
    },
  ];

  const tabItems = [
    ...(isAdmin
      ? [
          {
            key: 'console',
            label: (
              <Badge count={pendingCount} size="small" offset={[8, 0]}>
                审批台
              </Badge>
            ),
            children: (
              <>
                <Space className="mb-3" wrap>
                  <Select
                    value={statusFilter}
                    onChange={(v) => { setStatusFilter(v); setPage(1); }}
                    style={{ width: 130 }}
                    options={[
                      { value: 'pending', label: '待审批' },
                      { value: 'approved', label: '已通过' },
                      { value: 'rejected', label: '已驳回' },
                      { value: 'cancelled', label: '已撤销' },
                      { value: '', label: '全部' },
                    ]}
                  />
                  <Select
                    value={typeFilter}
                    onChange={(v) => { setTypeFilter(v); setPage(1); }}
                    style={{ width: 140 }}
                    allowClear
                    placeholder="全部类型"
                    options={Object.entries(TYPE_META).map(([v, m]) => ({ value: v, label: m.label }))}
                  />
                  <Button icon={<ReloadOutlined />} onClick={loadConsole} loading={loading}>
                    刷新
                  </Button>
                </Space>
                <Table
                  rowKey="id"
                  size="small"
                  loading={loading}
                  columns={consoleColumns as any}
                  dataSource={items}
                  pagination={{
                    current: page,
                    total,
                    pageSize: 20,
                    onChange: setPage,
                    showTotal: (n) => `共 ${n} 条`,
                  }}
                />
              </>
            ),
          },
        ]
      : []),
    {
      key: 'mine',
      label: '我的申请',
      children: (
        <>
          <Space className="mb-3">
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              发起申请
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadMine} loading={myLoading}>
              刷新
            </Button>
          </Space>
          <Table
            rowKey="id"
            size="small"
            loading={myLoading}
            columns={myColumns as any}
            dataSource={myItems}
            pagination={{
              current: myPage,
              total: myTotal,
              pageSize: 20,
              onChange: setMyPage,
              showTotal: (n) => `共 ${n} 条`,
            }}
          />
        </>
      ),
    },
  ];

  return (
    <div>
      <Tabs activeKey={innerTab} onChange={(k) => setInnerTab(k as 'console' | 'mine')} items={tabItems} />

      {/* 审批弹窗 */}
      <Modal
        open={!!reviewTarget}
        title={reviewAction === 'approve' ? '通过申请' : '驳回申请'}
        onOk={submitReview}
        onCancel={() => setReviewTarget(null)}
        confirmLoading={reviewing}
        okText={reviewAction === 'approve' ? '通过' : '驳回'}
        okButtonProps={reviewAction === 'reject' ? { danger: true } : {}}
      >
        {reviewTarget && (
          <Space direction="vertical" className="w-full">
            <Text>
              {TYPE_META[reviewTarget.request_type]?.label}:{requestTarget(reviewTarget)}
            </Text>
            {reviewTarget.request_type === 'permission_grant' && reviewAction === 'approve' && (
              <Text type="secondary">通过后将为该用户创建对应资源的实例级授权(resource_grant)。</Text>
            )}
            <Input.TextArea
              rows={3}
              placeholder="审批意见(可空)"
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
            />
          </Space>
        )}
      </Modal>

      {/* 发起申请弹窗 */}
      <Modal
        open={createOpen}
        title="发起权限申请"
        onOk={submitCreate}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={creating}
        okText="提交申请"
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={{ request_type: 'role_assign' }}>
          <Form.Item name="request_type" label="申请类型" rules={[{ required: true }]}>
            <Select
              options={Object.entries(TYPE_META).map(([v, m]) => ({ value: v, label: m.label }))}
            />
          </Form.Item>

          {applyType === 'role_assign' && (
            <Form.Item name="role_id" label="申请角色" rules={[{ required: true, message: '请选择角色' }]}>
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="选择要申请的角色"
                options={roles.map((r) => ({ value: r.id, label: `${r.name}${r.description ? ` — ${r.description}` : ''}` }))}
              />
            </Form.Item>
          )}

          {applyType === 'permission_grant' && (
            <>
              <Form.Item
                name="permission_def_id"
                label="申请权限"
                rules={[{ required: true, message: '请选择权限' }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="仅支持可实例级授权(grantable)的权限"
                  options={grantableDefs.map((d) => ({
                    value: d.id,
                    label: `${d.name}(${d.resource_type}.${d.action})`,
                  }))}
                />
              </Form.Item>
              <Form.Item
                label="资源实例"
                required
                help="权限申请必须指定具体资源(审批后创建实例级授权)"
                validateStatus={resourceIds.length && resourceIds[0] !== '*' ? undefined : 'error'}
              >
                <ResourceSelector
                  resourceType={
                    (grantableDefs.find((d) => d.id === form.getFieldValue('permission_def_id'))?.resource_type) || 'agent'
                  }
                  selectedResourceIds={resourceIds}
                  onChange={(ids) => setResourceIds(ids.slice(-1))}
                  allowWildcard={false}
                />
              </Form.Item>
            </>
          )}

          <Form.Item name="reason" label="申请原因" rules={[{ required: true, message: '请填写申请原因' }]}>
            <Input.TextArea rows={3} placeholder="说明为什么需要该权限" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
