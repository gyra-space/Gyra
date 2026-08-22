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
  App, Alert, AutoComplete, Button, Collapse, Form, Input, InputNumber, Modal, Select, Spin, Switch, Tag,
} from 'antd';
import {
  CloudServerOutlined, PlusOutlined, EditOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useEffect, useMemo, useRef, useState } from 'react';
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
  temperature?: number;
  max_new_tokens?: number;
  context_window?: number;
  top_p?: number;
  reasoning_effort?: string;
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
 * 空间管理员 owner(管理)可维护,成员只读。
 * collapsible=true 时渲染为可折叠区块(设置页用):未配置任何模型时默认折叠,减小占位。
 */
export function SpaceModelsTab({
  workspaceId, workspaceCode, canManage = true, collapsible = false,
}: {
  workspaceId: number;
  workspaceCode: string;
  canManage?: boolean;
  collapsible?: boolean;
}) {
  const { modal, message } = App.useApp();
  const [form] = Form.useForm<SpaceModelForm>();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [saving, setSaving] = useState(false);
  // 折叠区块展开状态:有模型时默认展开,无模型时默认折叠
  const [activeKeys, setActiveKeys] = useState<string[]>(['wsm-panel']);
  const collapsedInit = useRef(false);

  const { data: resources, loading, refresh } = useRequest(async () => {
    const [err, res] = await apiInterceptors(listResources({ workspace_id: workspaceId, type: 'llm_model' }));
    return err ? [] : res || [];
  }, { refreshDeps: [workspaceId] });

  // 首次加载完成后,未配置任何空间模型则默认折叠,减小占位高度
  useEffect(() => {
    if (loading || collapsedInit.current) return;
    collapsedInit.current = true;
    if (!resources?.length) setActiveKeys([]);
  }, [loading, resources]);

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
    form.setFieldsValue({ model: '', provider: '', base_url: '', api_key: '', temperature: undefined, max_new_tokens: undefined, context_window: undefined, top_p: undefined, reasoning_effort: undefined, is_active: true });
    setOpen(true);
  };

  const openEdit = (r: any) => {
    setEditing(r);
    form.setFieldsValue({
      model: getCfg(r, 'model') || r.physical_ref || r.name,
      provider: getCfg(r, 'provider'),
      base_url: getCfg(r, 'base_url') || getCfg(r, 'api_base'),
      api_key: '',
      temperature: getCfg(r, 'temperature', undefined),
      max_new_tokens: getCfg(r, 'max_new_tokens', undefined) ?? getCfg(r, 'max_tokens', undefined),
      context_window: getCfg(r, 'context_window', undefined),
      top_p: getCfg(r, 'top_p', undefined),
      reasoning_effort: getCfg(r, 'reasoning_effort', undefined),
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
      // 推理参数(思考深度等):留空表示沿用全局/系统配置
      if (values.temperature != null) config.temperature = values.temperature;
      if (values.max_new_tokens != null) config.max_new_tokens = values.max_new_tokens;
      if (values.context_window != null) config.context_window = values.context_window;
      if (values.top_p != null) config.top_p = values.top_p;
      if (values.reasoning_effort) config.reasoning_effort = values.reasoning_effort;
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
      // 添加/更新后展开区块,便于立即查看
      setActiveKeys(['wsm-panel']);
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
        // 移除最后一个模型后折叠
        if (resources?.length === 1) setActiveKeys([]);
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
          <div className="wsm-card__row">
            <span className="wsm-card__row-key">推理参数</span>
            <span className="wsm-card__row-val">
              {(() => {
                const parts: string[] = [];
                const t = getCfg(r, 'temperature', undefined);
                const m = getCfg(r, 'max_new_tokens', undefined) ?? getCfg(r, 'max_tokens', undefined);
                const cw = getCfg(r, 'context_window', undefined);
                const p = getCfg(r, 'top_p', undefined);
                const e = getCfg(r, 'reasoning_effort', undefined);
                if (t != null) parts.push(`temp=${t}`);
                if (m != null) parts.push(`max=${m}`);
                if (cw != null) parts.push(`ctx=${cw}`);
                if (p != null) parts.push(`top_p=${p}`);
                if (e) parts.push(`effort=${e}`);
                return parts.length ? parts.join(' · ') : '沿用全局';
              })()}
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

  const content = (
    <>
      <Alert
        type="info"
        showIcon
        className="mb-4"
        message="空间模型与专属 token"
        description="为当前空间绑定可用于任务/对话的模型,并配置专属 API token(加密存储,引用 ${secrets.xxx})。未配置任何空间模型时,空间任务与对话回退到全局默认模型(agent 里配置的)。"
      />

      {canManage ? (
        !collapsible && (
          <div className="flex justify-end mb-4">
            <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>添加空间模型</Button>
          </div>
        )
      ) : (
        <div className="flex justify-end mb-4 text-xs text-gray-400">
          <span>只读 · 管理员可维护空间模型</span>
        </div>
      )}

      {loading ? <div className="flex justify-center py-8"><Spin /></div> : !resources?.length ? (
        <div className="wsm-empty">
          <div className="wsm-empty__row">
            <CloudServerOutlined className="wsm-empty__icon" />
            <span className="wsm-empty__title">还没有配置空间模型</span>
          </div>
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
    </>
  );

  return (
    <div>
      {collapsible ? (
        <Collapse
          className="wsm-section mb-4"
          activeKey={activeKeys}
          onChange={(keys) => setActiveKeys(Array.isArray(keys) ? (keys as string[]) : [keys as string])}
          expandIconPosition="end"
          items={[{
            key: 'wsm-panel',
            label: (
              <div className="wsm-section__head">
                <div className="wsm-section__title">空间模型</div>
                <div className="wsm-section__status">
                  {loading ? (
                    <Spin size="small" />
                  ) : resources?.length ? (
                    <Tag color="blue">已配置 {resources.length} 个模型</Tag>
                  ) : (
                    <Tag>未配置空间模型</Tag>
                  )}
                </div>
                {canManage ? (
                  <Button
                    size="small"
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={(e) => { e.stopPropagation(); openAdd(); }}
                  >
                    添加空间模型
                  </Button>
                ) : (
                  <span className="wsm-section__readonly">只读</span>
                )}
              </div>
            ),
            children: content,
          }]}
        />
      ) : (
        content
      )}

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
          <Collapse
            ghost
            size="small"
            className="wsm-params"
            items={[{
              key: 'model-params',
              label: '推理参数(思考深度等,留空沿用系统配置)',
              children: (
                <div className="grid grid-cols-2 gap-x-4">
                  <Form.Item name="temperature" label="Temperature" tooltip="采样温度,留空沿用全局配置">
                    <InputNumber className="w-full" min={0} max={2} step={0.1} placeholder="沿用全局" />
                  </Form.Item>
                  <Form.Item name="max_new_tokens" label="最大输出 token" tooltip="单次最大生成 token 数,留空沿用全局配置">
                    <InputNumber className="w-full" min={1} step={100} placeholder="沿用全局" />
                  </Form.Item>
                  <Form.Item name="context_window" label="上下文空间" tooltip="模型上下文空间(输入+输出总预算),用于上下文压缩与用量统计,留空沿用全局配置">
                    <InputNumber className="w-full" min={0} step={1024} placeholder="沿用全局" />
                  </Form.Item>
                  <Form.Item name="top_p" label="Top P" tooltip="核采样参数,留空沿用全局配置">
                    <InputNumber className="w-full" min={0} max={1} step={0.05} placeholder="沿用全局" />
                  </Form.Item>
                  <Form.Item name="reasoning_effort" label="思考深度" tooltip="reasoning_effort,如 low/medium/high,留空沿用全局配置">
                    <Select
                      allowClear
                      placeholder="沿用全局"
                      options={[
                        { value: 'low', label: 'low(低深度)' },
                        { value: 'medium', label: 'medium(中深度)' },
                        { value: 'high', label: 'high(高深度)' },
                      ]}
                    />
                  </Form.Item>
                </div>
              ),
            }]}
          />
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}