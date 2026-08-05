'use client';

import {
  apiInterceptors,
  listResources,
  listWorkspaceAvailableModels,
  addResource,
  updateResource,
  removeResource,
} from '@/client/api';
import { configService } from '@/services/config';
import {
  App, Alert, AutoComplete, Button, Form, Input, Modal, Spin, Switch, Tag,
} from 'antd';
import {
  CloudServerOutlined, PlusOutlined, EditOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useMemo, useState } from 'react';
import dayjs from 'dayjs';
import './space-models.css';

interface AvailableModel {
  key: string;
  provider: string;
  model: string;
  protocol?: string;
  base_url?: string;
  model_type?: string;
  capabilities?: string[];
  is_multimodal?: boolean;
}

interface SpaceModelForm {
  model: string;
  provider: string;
  base_url?: string;
  api_key?: string;
  is_active: boolean;
}

/** 生成空间专属 secret 名:space_<code>_<provider>_<model>_key */
function buildSecretName(workspaceCode: string, provider: string, model: string) {
  const sanitize = (s: string) => (s || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
  return `space_${sanitize(workspaceCode)}_${sanitize(provider)}_${sanitize(model)}_key`;
}

function getCfg(resource: any, key: string, fallback = '') {
  return resource?.config?.[key] ?? fallback;
}

/**
 * 空间模型:为空间绑定可用模型并配置专属 token(api_key_ref 引用加密 secrets)。
 * 未配置任何空间模型时,空间任务/对话回退到全局默认模型(agent 配置)。
 * 空间管理员(owner/approver)可维护,成员只读。
 */
export function SpaceModelsTab({
  workspaceId, workspaceCode, canManage = true,
}: {
  workspaceId: number;
  workspaceCode: string;
  canManage?: boolean;
}) {
  const { modal, message } = App.useApp();
  const [form] = Form.useForm<SpaceModelForm>();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [saving, setSaving] = useState(false);

  const { data: resources, loading, refresh } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listResources({ workspace_id: workspaceId, type: 'llm_model' }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId] });

  const { data: availableData } = useRequest(async () => {
    if (!workspaceId) return [];
    const [err, res] = await apiInterceptors(listWorkspaceAvailableModels(workspaceId));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId] });
  const availableModels: AvailableModel[] = availableData || [];

  const modelOptions = useMemo(
    () => availableModels.map((m) => ({
      value: m.model,
      provider: m.provider,
      base_url: m.base_url,
      is_multimodal: m.is_multimodal,
      capabilities: m.capabilities,
      label: `${m.provider}/${m.model}${m.protocol ? ` (${m.protocol})` : ''}`,
    })),
    [availableModels],
  );

  const openAdd = () => {
    setEditing(null);
    form.setFieldsValue({ model: '', provider: '', base_url: '', api_key: '', is_active: true });
    setOpen(true);
  };

  const openEdit = (r: any) => {
    setEditing(r);
    form.setFieldsValue({
      model: getCfg(r, 'model') || r.physical_ref || r.name,
      provider: getCfg(r, 'provider'),
      base_url: getCfg(r, 'base_url') || getCfg(r, 'api_base'),
      api_key: '',
      is_active: !!r.is_active,
    });
    setOpen(true);
  };

  const handleModelChange = (model: string) => {
    const opt = modelOptions.find((o) => o.value === model);
    if (opt) {
      form.setFieldsValue({ provider: opt.provider, base_url: opt.base_url });
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const model = (values.model || '').trim();
      const provider = (values.provider || '').trim();
      if (!model || !provider) {
        message.warning('请填写模型名称与 Provider');
        return;
      }

      setSaving(true);
      // 解析 token:实际值 -> 加密存 secret 并引用;${secrets.} 引用直接透传;留空表示沿用全局凭据
      let apiKeyRef = getCfg(editing, 'api_key_ref', '');
      const rawKey = (values.api_key || '').trim();
      if (rawKey) {
        if (rawKey.startsWith('${secrets.')) {
          apiKeyRef = rawKey;
        } else {
          const secretName = buildSecretName(workspaceCode, provider, model);
          await configService.setSecret(secretName, rawKey, `space(${workspaceCode}) ${provider}/${model} 专属 token`);
          apiKeyRef = `\${secrets.${secretName}}`;
        }
      }

      const config: Record<string, any> = {
        provider,
        model,
        base_url: (values.base_url || '').trim(),
        api_key_ref: apiKeyRef,
      };
      const opt = modelOptions.find((o) => o.value === model);
      if (opt?.is_multimodal) config.is_multimodal = true;
      if (opt?.capabilities?.length) config.capabilities = opt.capabilities;

      let err: any = null;
      if (editing) {
        [err] = await apiInterceptors(updateResource({
          resource_id: editing.id,
          resource: {
            workspace_id: workspaceId,
            type: 'llm_model',
            name: model,
            category: editing.category || 'scenario_bound',
            physical_ref: model,
            config,
            access_mode: editing.access_mode || 'read',
            is_active: values.is_active,
          },
        }));
      } else {
        [err] = await apiInterceptors(addResource({
          workspace_id: workspaceId,
          type: 'llm_model',
          name: model,
          physical_ref: model,
          category: 'scenario_bound',
          access_mode: 'read',
          is_active: values.is_active,
          config,
        }));
      }
      setSaving(false);
      if (err) { message.error(err.message); return; }
      message.success(editing ? '空间模型已更新' : '空间模型已添加');
      setOpen(false);
      refresh();
    } catch (e) {
      setSaving(false);
    }
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
      title: `移除空间模型「${r.name}」?`,
      content: '移除后该空间将不再使用此模型与专属 token;未配置其他空间模型时回退到全局默认模型。',
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
    const provider = getCfg(r, 'provider');
    const model = getCfg(r, 'model') || r.physical_ref || r.name;
    const baseUrl = getCfg(r, 'base_url') || getCfg(r, 'api_base');
    const apiKeyRef = getCfg(r, 'api_key_ref');
    const active = !!r.is_active;
    return (
      <div key={r.id} className={`wsm-card${active ? '' : ' wsm-card--off'}`}>
        <div className="wsm-card__head">
          <div className="wsm-card__tile"><CloudServerOutlined /></div>
          <div className="wsm-card__titles">
            <div className="wsm-card__name" title={model}>{model}</div>
            <div className="wsm-card__model">{provider || '—'}</div>
          </div>
          {canManage ? (
            <span className="wsm-card__status">
              <Switch size="small" checked={active} onChange={(c) => handleToggle(r, c)} />
            </span>
          ) : (
            <span className={`wsm-card__status ${active ? 'wsm-status-on' : 'wsm-status-off'}`}>
              <span className={`wsm-status-dot ${active ? 'wsm-status-dot--on' : 'wsm-status-dot--off'}`} />
              {active ? '启用' : '停用'}
            </span>
          )}
        </div>

        <div className="wsm-card__tags">
          <Tag color="cyan">模型</Tag>
          {getCfg(r, 'is_multimodal') ? <Tag color="purple">多模态</Tag> : <Tag color="blue">对话</Tag>}
          {apiKeyRef ? <Tag color="green">专属 token</Tag> : <Tag color="default">沿用全局凭据</Tag>}
        </div>

        <div className="wsm-card__meta">
          <div className="wsm-card__row">
            <span className="wsm-card__row-key">Provider</span>
            <span className="wsm-card__row-val">{provider || '—'}</span>
          </div>
          <div className="wsm-card__row">
            <span className="wsm-card__row-key">Base URL</span>
            <span className="wsm-card__row-val wsm-card__row-val--mono" title={baseUrl || ''}>
              {baseUrl || '沿用全局'}
            </span>
          </div>
          <div className="wsm-card__row">
            <span className="wsm-card__row-key">Token</span>
            <span className="wsm-card__row-val wsm-card__row-val--mono" title={apiKeyRef || ''}>
              {apiKeyRef ? apiKeyRef : '未设置'}
            </span>
          </div>
        </div>

        <div className="wsm-card__foot">
          <span className="wsm-card__time">
            {r.gmt_modified ? dayjs(r.gmt_modified).format('MM-DD HH:mm') : ''}
          </span>
          {canManage && (
            <span className="wsm-card__ops">
              <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
              <Button size="small" type="text" danger onClick={() => handleRemove(r)}>移除</Button>
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div>
      <Alert
        type="info"
        showIcon
        className="mb-4"
        message="空间模型与专属 token"
        description="为当前空间绑定可用于任务/对话的模型,并配置专属 API token(加密存储,引用 ${secrets.xxx})。未配置任何空间模型时,空间任务与对话回退到全局默认模型(agent 里配置的)。"
      />

      {canManage ? (
        <div className="flex justify-end mb-4">
          <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>添加空间模型</Button>
        </div>
      ) : (
        <div className="flex justify-end mb-4 text-xs text-gray-400">
          <span>只读 · 管理员可维护空间模型</span>
        </div>
      )}

      {loading ? <div className="flex justify-center py-8"><Spin /></div> : !resources?.length ? (
        <div className="wsm-empty">
          <div className="wsm-empty__art" aria-hidden="true">
            <svg viewBox="0 0 168 128" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="wsmEmptyBg" x1="0" y1="0" x2="168" y2="128" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#eef2ff"/>
                  <stop offset="1" stopColor="#f5f3ff"/>
                </linearGradient>
                <linearGradient id="wsmEmptyTile" x1="68" y1="40" x2="100" y2="72" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#6366f1"/>
                  <stop offset="1" stopColor="#8b5cf6"/>
                </linearGradient>
              </defs>
              <rect x="8" y="10" width="152" height="108" rx="18" fill="url(#wsmEmptyBg)" stroke="#e4e4f8" strokeWidth="1.5"/>
              <path d="M84 38a14 14 0 0 0-13.6 10.2A11 11 0 0 0 63 59h42a11 11 0 0 0-7.4-10.8A14 14 0 0 0 84 38Z" fill="#c7d2fe"/>
              <rect x="66" y="60" width="36" height="22" rx="7" fill="url(#wsmEmptyTile)"/>
              <rect x="74" y="66" width="20" height="3" rx="1.5" fill="#fff" opacity="0.9"/>
              <rect x="74" y="72" width="13" height="3" rx="1.5" fill="#fff" opacity="0.6"/>
              <circle cx="118" cy="92" r="8" fill="#a5b4fc"/>
              <circle cx="118" cy="92" r="3.4" fill="#fff" opacity="0.85"/>
              <path d="M52 92c-2.5-2-5-2-7.5 0" stroke="#c4b5fd" strokeWidth="2" strokeLinecap="round"/>
              <circle cx="44" cy="88" r="2" fill="#a78bfa"/>
              <circle cx="53" cy="88" r="2" fill="#a78bfa"/>
            </svg>
          </div>
          <div className="wsm-empty__title">还没有配置空间模型</div>
          <div className="wsm-empty__desc">
            为空间绑定专属模型并配置独立 token 后,空间内的任务与对话将使用这些自定义模型。
            未配置时,一切回退到全局默认模型(agent 里配置的)。
          </div>
          {canManage && (
            <div className="wsm-empty__action">
              <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>添加第一个空间模型</Button>
            </div>
          )}
        </div>
      ) : (
        <div className="wsm-grid">
          {resources.map(renderCard)}
        </div>
      )}

      <Button
        type="link"
        className="mt-2"
        onClick={() => window.open('/settings/config', '_blank')}
      >
        到系统配置管理全局模型与 API Keys
      </Button>

      <Modal
        open={open}
        onCancel={() => setOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        title={editing ? '编辑空间模型' : '添加空间模型'}
        okText="保存"
      >
        <Form form={form} layout="vertical" className="mt-2">
          <Form.Item
            name="model"
            label="模型"
            rules={[{ required: true, message: '请填写/选择模型' }]}
            tooltip="可从全局已注册模型中选择,也可手动输入不在全局列表中的模型名"
          >
            <AutoComplete
              options={modelOptions}
              placeholder="选择或输入模型名"
              onChange={handleModelChange}
              filterOption={(input, option) =>
                ((option?.label as string) || '').toLowerCase().includes(input.toLowerCase()) ||
                (option?.value as string).toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item
            name="provider"
            label="Provider"
            rules={[{ required: true, message: '请输入 Provider' }]}
          >
            <AutoComplete
              placeholder="如 openai / deepseek / zhipu"
              options={Array.from(new Set(availableModels.map((m) => m.provider))).map((p) => ({ value: p }))}
            />
          </Form.Item>
          <Form.Item name="base_url" label="API Base URL(可选,默认沿用全局)">
            <Input placeholder="https://api.deepseek.com/v1" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="专属 API token"
            tooltip="粘贴实际 token 保存时自动加密为 ${secrets.xxx};也可直接填 ${secrets.xxx} 引用。留空表示使用全局默认凭据。"
          >
            <Input.Password
              placeholder={getCfg(editing, 'api_key_ref') ? `已配置引用 ${getCfg(editing, 'api_key_ref')},重新粘贴可更新` : '粘贴专属 token(加密存储)'}
            />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}