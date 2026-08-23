'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  App,
  Divider,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { apiInterceptors, ins as axios } from '@/client/api';
import { listSpaces } from '@/client/api/knowledge-vault';
import {
  permissionsService,
  type PermissionDefinition,
  type PermissionDefinitionCreateBody,
  type PermissionDefinitionUpdateBody,
} from '@/services/permissions';

const { Text } = Typography;

const RESOURCE_PICKER_TYPES = ['agent', 'tool', 'knowledge', 'model', 'database'] as const;

/** 支持级联选择的资源类型（如 database 支持 库→表 两级） */
const HIERARCHICAL_RESOURCE_TYPES = ['database'] as const;

async function loadOptionsForResourceType(
  resourceType: string,
  parentId?: string,
): Promise<{ value: string; label: string }[]> {
  // 统一资源目录 API（支持级联）
  try {
    const params: Record<string, string> = { resource_type: resourceType };
    if (parentId) params.parent_id = parentId;
    const res = await axios.get('/api/v1/permissions/resources/catalog', { params });
    const items = res.data?.data?.items || [];
    if (items.length > 0) {
      return items.map((item: { id: string; name: string; description?: string }) => ({
        value: item.id,
        label: item.description ? `${item.name} (${item.description})` : item.name,
      }));
    }
  } catch {
    // 统一目录 API 不可用时回退到旧逻辑
  }

  // 旧逻辑：硬编码对接各业务模块 API（向后兼容）
  let resources: Array<{ name?: string; displayName?: string; id?: string | number }> = [];
  try {
    switch (resourceType) {
      case 'agent': {
        const res = await axios.get('/api/v1/config/agents');
        resources = res.data?.data?.list || res.data?.data || [];
        break;
      }
      case 'tool': {
        const res = await axios.get('/api/v1/tools/list');
        resources = res.data?.data?.list || res.data?.data || [];
        break;
      }
      case 'knowledge': {
        const [, spaces] = await apiInterceptors(listSpaces());
        resources = (spaces || []).map((s) => ({ name: s.slug }));
        break;
      }
      case 'model': {
        const res = await axios.get('/api/v1/serve/model/models');
        resources = res.data?.data?.list || res.data?.data || [];
        break;
      }
      default:
        return [];
    }
  } catch {
    return [];
  }

  return resources
    .map((item) => {
      const label =
        item.displayName != null && item.displayName !== ''
          ? String(item.displayName)
          : item.name != null && item.name !== ''
            ? String(item.name)
            : String(item.id ?? '');
      const value = item.name != null && item.name !== '' ? String(item.name) : String(item.id ?? '');
      return { value, label: label || value };
    })
    .filter((o) => o.value);
}

interface PermissionDefinitionsPanelProps {
  onDefinitionCreated?: () => void;
}

export default function PermissionDefinitionsPanel({ onDefinitionCreated }: PermissionDefinitionsPanelProps) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [definitions, setDefinitions] = useState<PermissionDefinition[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [selectedDef, setSelectedDef] = useState<PermissionDefinition | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [selectedResourceType, setSelectedResourceType] = useState<string>('agent');
  const [search, setSearch] = useState('');
  const [resourceIdOptions, setResourceIdOptions] = useState<{ value: string; label: string }[]>([]);
  const [resourceIdsLoading, setResourceIdsLoading] = useState(false);
  // 级联选择状态（database 等支持层级的资源类型）
  const [catalogParentOptions, setCatalogParentOptions] = useState<{ value: string; label: string }[]>([]);
  const [selectedParentId, setSelectedParentId] = useState<string | undefined>(undefined);
  const [catalogChildOptions, setCatalogChildOptions] = useState<{ value: string; label: string }[]>([]);
  const [catalogChildLoading, setCatalogChildLoading] = useState(false);

  const isHierarchical = HIERARCHICAL_RESOURCE_TYPES.includes(
    selectedResourceType as (typeof HIERARCHICAL_RESOURCE_TYPES)[number],
  );

  const resourceTypeOptions = useMemo(
    () => [
      { value: 'agent', label: t('permissions_resource_agent') },
      { value: 'tool', label: t('permissions_resource_tool') },
      { value: 'knowledge', label: t('permissions_resource_knowledge') },
      { value: 'model', label: t('permissions_resource_model') },
      { value: 'database', label: t('permissions_resource_database') },
      { value: 'cron', label: t('permissions_resource_cron') },
      { value: 'channel', label: t('permissions_resource_channel') },
      { value: 'system', label: t('permissions_resource_system') },
      { value: '*', label: t('permissions_resource_wildcard') },
    ],
    [t],
  );

  const actionOptionsMap = useMemo(
    () => ({
      agent: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'chat', label: t('permissions_action_chat') },
        { value: 'write', label: t('permissions_action_write') },
        { value: 'admin', label: t('permissions_action_admin') },
        { value: '*', label: t('permissions_action_all') },
      ],
      tool: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'execute', label: t('permissions_action_execute') },
        { value: 'manage', label: t('permissions_action_manage') },
        { value: 'admin', label: t('permissions_action_admin') },
        { value: '*', label: t('permissions_action_all') },
      ],
      knowledge: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'query', label: t('permissions_action_query') },
        { value: 'write', label: t('permissions_action_write') },
        { value: 'admin', label: t('permissions_action_admin') },
        { value: '*', label: t('permissions_action_all') },
      ],
      model: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'chat', label: t('permissions_action_chat') },
        { value: 'manage', label: t('permissions_action_manage') },
        { value: 'admin', label: t('permissions_action_admin') },
        { value: '*', label: t('permissions_action_all') },
      ],
      database: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'manage', label: t('permissions_action_manage') },
        { value: '*', label: t('permissions_action_all') },
      ],
      cron: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'manage', label: t('permissions_action_manage') },
        { value: '*', label: t('permissions_action_all') },
      ],
      channel: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'manage', label: t('permissions_action_manage') },
        { value: '*', label: t('permissions_action_all') },
      ],
      system: [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'write', label: t('permissions_action_write') },
        { value: 'admin', label: t('permissions_action_admin') },
        { value: '*', label: t('permissions_action_all') },
      ],
      '*': [
        { value: 'read', label: t('permissions_action_read') },
        { value: 'write', label: t('permissions_action_write') },
        { value: 'admin', label: t('permissions_action_admin') },
        { value: '*', label: t('permissions_action_all') },
      ],
    }),
    [t],
  );

  const loadDefinitions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await permissionsService.listPermissionDefinitions({});
      setDefinitions(data || []);
    } catch (e: unknown) {
      console.error('Failed to load permission definitions:', e);
      setDefinitions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Only load on client side
    if (typeof window === 'undefined') return;
    loadDefinitions();
  }, [loadDefinitions]);

  // Load resource IDs when resource type changes or modal opens
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!createOpen && !editOpen) {
      setResourceIdOptions([]);
      setCatalogParentOptions([]);
      setCatalogChildOptions([]);
      setSelectedParentId(undefined);
      return;
    }
    const rt = selectedResourceType;
    if (!RESOURCE_PICKER_TYPES.includes(rt as (typeof RESOURCE_PICKER_TYPES)[number])) {
      setResourceIdOptions([]);
      setCatalogParentOptions([]);
      setCatalogChildOptions([]);
      setSelectedParentId(undefined);
      return;
    }

    let cancelled = false;

    if (isHierarchical) {
      // 级联模式：先加载第一级（如数据源列表）
      (async () => {
        setResourceIdsLoading(true);
        const opts = await loadOptionsForResourceType(rt);
        if (!cancelled) {
          setCatalogParentOptions(opts);
          // 级联模式下 resource_id 由第二级选择决定，初始为空
          setResourceIdOptions([]);
        }
        if (!cancelled) {
          setResourceIdsLoading(false);
        }
      })();
    } else {
      // 平铺模式：直接加载资源列表
      (async () => {
        setResourceIdsLoading(true);
        const opts = await loadOptionsForResourceType(rt);
        if (!cancelled) {
          setResourceIdOptions(opts);
        }
        if (!cancelled) {
          setResourceIdsLoading(false);
        }
      })();
    }
    return () => {
      cancelled = true;
    };
  }, [selectedResourceType, createOpen, editOpen, isHierarchical]);

  // 级联模式：选择父级后加载子级（如选择数据源后加载表列表）
  useEffect(() => {
    if (!isHierarchical || !selectedParentId) {
      setCatalogChildOptions([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setCatalogChildLoading(true);
      const opts = await loadOptionsForResourceType(selectedResourceType, selectedParentId);
      if (!cancelled) {
        setCatalogChildOptions(opts);
      }
      if (!cancelled) {
        setCatalogChildLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isHierarchical, selectedParentId, selectedResourceType]);

  const filteredDefinitions = useMemo(() => {
    if (!search.trim()) return definitions;
    const q = search.trim().toLowerCase();
    return definitions.filter((d) => {
      const blob = [d.name, d.description, d.resource_type, d.resource_id, d.action]
        .join(' ')
        .toLowerCase();
      return blob.includes(q);
    });
  }, [definitions, search]);

  const getResourceTypeLabel = (type: string) => {
    const option = resourceTypeOptions.find((o) => o.value === type);
    return option?.label || type;
  };

  const getActionLabel = (resourceType: string, action: string) => {
    const actions = actionOptionsMap[resourceType as keyof typeof actionOptionsMap] || actionOptionsMap['*'];
    const option = actions.find((a) => a.value === action);
    return option?.label || action;
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      const resourceIds = values.resource_id as string[];

      if (resourceIds && resourceIds.length > 1) {
        const promises = resourceIds.map((resourceId) =>
          permissionsService.createPermissionDefinition({
            name: `${values.name}_${resourceId}`,
            description: values.description,
            resource_type: values.resource_type,
            resource_id: resourceId,
            action: values.action,
            effect: values.effect,
          })
        );
        await Promise.all(promises);
        message.success(t('permissions_definition_created'));
      } else {
        await permissionsService.createPermissionDefinition({
          name: values.name,
          description: values.description,
          resource_type: values.resource_type,
          resource_id: resourceIds?.[0] || '*',
          action: values.action,
          effect: values.effect,
        } as PermissionDefinitionCreateBody);
        message.success(t('permissions_definition_created'));
      }
      setCreateOpen(false);
      createForm.resetFields();
      await loadDefinitions();
      // Notify parent to refresh the list
      if (onDefinitionCreated) {
        onDefinitionCreated();
      }
    } catch (e: unknown) {
      if ((e as { errorFields?: unknown })?.errorFields) return;
      message.error(t('permissions_create_error') + ': ' + (e as Error).message);
    }
  };

  const handleEdit = async () => {
    if (!selectedDef) return;
    try {
      const values = await editForm.validateFields();
      const resourceId = values.resource_id;
      const updateData = {
        ...values,
        resource_id: Array.isArray(resourceId) ? resourceId.join(',') : resourceId,
      };
      await permissionsService.updatePermissionDefinition(
        selectedDef.id,
        updateData as PermissionDefinitionUpdateBody,
      );
      message.success(t('permissions_definition_updated'));
      setEditOpen(false);
      editForm.resetFields();
      setSelectedDef(null);
      await loadDefinitions();
    } catch (e: unknown) {
      if ((e as { errorFields?: unknown })?.errorFields) return;
      message.error(t('permissions_update_error') + ': ' + (e as Error).message);
    }
  };

  const handleDelete = async (def: PermissionDefinition) => {
    try {
      await permissionsService.deletePermissionDefinition(def.id);
      message.success(t('permissions_definition_deleted'));
      await loadDefinitions();
    } catch (e: unknown) {
      message.error(t('permissions_delete_error') + ': ' + (e as Error).message);
    }
  };

  const openEdit = (def: PermissionDefinition) => {
    setSelectedDef(def);
    setSelectedResourceType(def.resource_type);
    editForm.setFieldsValue({
      name: def.name,
      description: def.description,
      resource_type: def.resource_type,
      resource_id: def.resource_id,
      action: def.action,
      effect: def.effect,
      is_active: def.is_active,
    });
    setEditOpen(true);
  };

  const openCreate = () => {
    setSelectedResourceType('agent');
    createForm.resetFields();
    createForm.setFieldsValue({
      resource_type: 'agent',
      resource_id: ['*'],
      effect: 'allow',
      is_active: true,
    });
    setCreateOpen(true);
  };

  const tableColumns = [
    {
      title: t('permissions_col_name'),
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: t('permissions_col_description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('permissions_resource_type'),
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 100,
      render: (type: string) => <Tag color="blue">{getResourceTypeLabel(type)}</Tag>,
    },
    {
      title: t('permissions_resource_id'),
      dataIndex: 'resource_id',
      key: 'resource_id',
      width: 120,
      render: (id: string) => (
        <Tag color={id === '*' ? 'red' : 'green'}>
          {id === '*' ? t('permissions_all_resources_tag') : id}
        </Tag>
      ),
    },
    {
      title: t('permissions_action'),
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: string, record: PermissionDefinition) => (
        <Tag color="purple">{getActionLabel(record.resource_type, action)}</Tag>
      ),
    },
    {
      title: t('permissions_effect'),
      dataIndex: 'effect',
      key: 'effect',
      width: 80,
      render: (effect: string) => (
        <Tag color={effect === 'allow' ? 'green' : 'red'}>
          {effect === 'allow' ? t('permissions_effect_allow') : t('permissions_effect_deny')}
        </Tag>
      ),
    },
    {
      title: t('permissions_status'),
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? t('permissions_active') : t('permissions_inactive')}
        </Tag>
      ),
    },
    {
      title: t('permissions_col_actions'),
      key: 'actions',
      width: 120,
      render: (_: unknown, record: PermissionDefinition) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            {t('edit')}
          </Button>
          <Popconfirm
            title={t('permissions_remove_definition_confirm')}
            onConfirm={() => handleDelete(record)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              {t('delete')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="mt-6">
      <Divider />
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <Space>
          <SafetyOutlined className="text-xl" />
          <Text strong className="text-lg">
            {t('permissions_definition_library')}
          </Text>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {t('permissions_create_definition')}
        </Button>
      </div>

      <Alert
        type="info"
        showIcon
        className="mb-4"
        message={t('permissions_definition_library_hint')}
        description={
          <Text type="secondary">
            {t('permissions_definition_library_desc')}
          </Text>
        }
      />

      <Input.Search
        allowClear
        className="mb-4 max-w-md"
        placeholder={t('permissions_search_definitions_placeholder')}
        onSearch={setSearch}
        onChange={(e) => setSearch(e.target.value)}
      />

      <Table<PermissionDefinition>
        loading={loading}
        rowKey={(r) => r.id.toString()}
        dataSource={filteredDefinitions}
        columns={tableColumns}
        pagination={{ pageSize: 5, showSizeChanger: true }}
        size="small"
      />

      <Modal
        title={t('permissions_create_definition')}
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          createForm.resetFields();
        }}
        destroyOnClose
        width={600}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label={t('permissions_definition_name')}
            rules={[{ required: true, message: t('permissions_name_required') }]}
          >
            <Input placeholder={t('permissions_definition_name_placeholder')} />
          </Form.Item>
          <Form.Item name="description" label={t('permissions_col_description')}>
            <Input.TextArea placeholder={t('permissions_definition_desc_placeholder')} />
          </Form.Item>
          <Form.Item
            name="resource_type"
            label={t('permissions_resource_type')}
            rules={[{ required: true, message: t('permissions_select_resource') }]}
          >
            <Select
              options={resourceTypeOptions}
              onChange={(value) => {
                setSelectedResourceType(value);
                setSelectedParentId(undefined);
                createForm.setFieldsValue({ resource_id: ['*'], action: undefined });
              }}
            />
          </Form.Item>
          {/* 级联选择：支持层级的资源类型（如 database）先选父级再选子级 */}
          {isHierarchical && (
            <>
              <Form.Item
                label={t('permissions_resource_parent')}
                tooltip={t('permissions_resource_parent_hint')}
              >
                <Select
                  showSearch
                  allowClear
                  loading={resourceIdsLoading}
                  placeholder={t('permissions_resource_parent_placeholder')}
                  options={catalogParentOptions}
                  optionFilterProp="label"
                  value={selectedParentId}
                  onChange={(value) => {
                    setSelectedParentId(value);
                    // 选择父级后，默认选中该父级（代表全部子级）
                    createForm.setFieldsValue({ resource_id: value ? [value] : ['*'] });
                  }}
                />
              </Form.Item>
              {selectedParentId && (
                <Form.Item
                  name="resource_id"
                  label={t('permissions_resource_id')}
                  initialValue={['*']}
                  extra={t('permissions_resource_multi_placeholder')}
                  tooltip={t('permissions_resource_multi_hint')}
                >
                  <Select
                    mode="multiple"
                    showSearch
                    allowClear
                    loading={catalogChildLoading}
                    placeholder={t('permissions_resource_pick_placeholder')}
                    options={[
                      { value: '*', label: t('permissions_all_resources_tag') },
                      { value: selectedParentId, label: t('permissions_all_under_parent') },
                      ...catalogChildOptions,
                    ]}
                    optionFilterProp="label"
                    maxTagCount={3}
                  />
                </Form.Item>
              )}
            </>
          )}
          {/* 平铺选择：非层级资源类型 */}
          {!isHierarchical && (
            <Form.Item
              name="resource_id"
              label={t('permissions_resource_id')}
              initialValue={['*']}
              extra={t('permissions_resource_multi_placeholder')}
              tooltip={t('permissions_resource_multi_hint')}
            >
              <Select
                mode="multiple"
                showSearch
                allowClear
                loading={resourceIdsLoading}
                placeholder={t('permissions_resource_pick_placeholder')}
                options={[
                  { value: '*', label: t('permissions_all_resources_tag') },
                  ...resourceIdOptions,
                ]}
                optionFilterProp="label"
                maxTagCount={3}
              />
            </Form.Item>
          )}
          <Form.Item
            name="action"
            label={t('permissions_action')}
            rules={[{ required: true, message: t('permissions_action_required') }]}
          >
            <Select
              options={actionOptionsMap[selectedResourceType as keyof typeof actionOptionsMap] || actionOptionsMap['*']}
            />
          </Form.Item>
          <Form.Item name="effect" label={t('permissions_effect')} initialValue="allow">
            <Select
              options={[
                { value: 'allow', label: t('permissions_effect_allow') },
                { value: 'deny', label: t('permissions_effect_deny') },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_active" label={t('permissions_status')} initialValue={true} valuePropName="checked">
            <Select
              options={[
                { value: true, label: t('permissions_active') },
                { value: false, label: t('permissions_inactive') },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t('permissions_edit_definition')}
        open={editOpen}
        onOk={handleEdit}
        onCancel={() => {
          setEditOpen(false);
          editForm.resetFields();
          setSelectedDef(null);
        }}
        destroyOnClose
        width={600}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="name"
            label={t('permissions_definition_name')}
            rules={[{ required: true, message: t('permissions_name_required') }]}
          >
            <Input placeholder={t('permissions_definition_name_placeholder')} />
          </Form.Item>
          <Form.Item name="description" label={t('permissions_col_description')}>
            <Input.TextArea placeholder={t('permissions_definition_desc_placeholder')} />
          </Form.Item>
          <Form.Item
            name="resource_type"
            label={t('permissions_resource_type')}
            rules={[{ required: true, message: t('permissions_select_resource') }]}
          >
            <Select
              options={resourceTypeOptions}
              onChange={(value) => {
                setSelectedResourceType(value);
                setSelectedParentId(undefined);
                editForm.setFieldsValue({ action: undefined });
              }}
            />
          </Form.Item>
          {/* 级联选择：支持层级的资源类型（如 database）先选父级再选子级 */}
          {isHierarchical && (
            <>
              <Form.Item
                label={t('permissions_resource_parent')}
                tooltip={t('permissions_resource_parent_hint')}
              >
                <Select
                  showSearch
                  allowClear
                  loading={resourceIdsLoading}
                  placeholder={t('permissions_resource_parent_placeholder')}
                  options={catalogParentOptions}
                  optionFilterProp="label"
                  value={selectedParentId}
                  onChange={(value) => {
                    setSelectedParentId(value);
                    editForm.setFieldsValue({ resource_id: value ? [value] : ['*'] });
                  }}
                />
              </Form.Item>
              {selectedParentId && (
                <Form.Item
                  name="resource_id"
                  label={t('permissions_resource_id')}
                  extra={t('permissions_resource_multi_placeholder')}
                  tooltip={t('permissions_resource_multi_hint')}
                >
                  <Select
                    mode="multiple"
                    showSearch
                    allowClear
                    loading={catalogChildLoading}
                    placeholder={t('permissions_resource_pick_placeholder')}
                    options={[
                      { value: '*', label: t('permissions_all_resources_tag') },
                      { value: selectedParentId, label: t('permissions_all_under_parent') },
                      ...catalogChildOptions,
                    ]}
                    optionFilterProp="label"
                    maxTagCount={3}
                  />
                </Form.Item>
              )}
            </>
          )}
          {/* 平铺选择：非层级资源类型 */}
          {!isHierarchical && (
            <Form.Item
              name="resource_id"
              label={t('permissions_resource_id')}
              extra={t('permissions_resource_multi_placeholder')}
              tooltip={t('permissions_resource_multi_hint')}
            >
              <Select
                mode="multiple"
                showSearch
                allowClear
                loading={resourceIdsLoading}
                placeholder={t('permissions_resource_pick_placeholder')}
                options={[
                  { value: '*', label: t('permissions_all_resources_tag') },
                  ...resourceIdOptions,
                ]}
                optionFilterProp="label"
                maxTagCount={3}
              />
            </Form.Item>
          )}
          <Form.Item
            name="action"
            label={t('permissions_action')}
            rules={[{ required: true, message: t('permissions_action_required') }]}
          >
            <Select
              options={actionOptionsMap[selectedResourceType as keyof typeof actionOptionsMap] || actionOptionsMap['*']}
            />
          </Form.Item>
          <Form.Item name="effect" label={t('permissions_effect')}>
            <Select
              options={[
                { value: 'allow', label: t('permissions_effect_allow') },
                { value: 'deny', label: t('permissions_effect_deny') },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_active" label={t('permissions_status')} valuePropName="checked">
            <Select
              options={[
                { value: true, label: t('permissions_active') },
                { value: false, label: t('permissions_inactive') },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}