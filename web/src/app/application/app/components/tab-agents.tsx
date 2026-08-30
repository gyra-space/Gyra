'use client';
import { getResourceV2, getAppList, apiInterceptors } from '@/client/api';
import { AppContext } from '@/contexts';
import { CheckCircleFilled, SearchOutlined, UsergroupAddOutlined, PlusOutlined, ReloadOutlined, RobotOutlined, SettingOutlined, PictureOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { Input, Spin, Tag, Tooltip, Modal, InputNumber, Checkbox, Button, Collapse, Switch } from 'antd';
import Image from 'next/image';
import { useContext, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

type AgentSource = 'all' | 'built-in' | 'custom';

interface SubagentDistributedConfig {
  max_instances?: number;
  timeout?: number;
  retry_count?: number;
  interactive?: boolean;
}

interface ResourceAgent {
  type: string;
  name: string;
  value: string;
  distributed_config?: SubagentDistributedConfig;
}

const DEFAULT_DISTRIBUTED_CONFIG: SubagentDistributedConfig = {
  max_instances: 5,
  timeout: 300,
  retry_count: 3,
  interactive: false,
};

export default function TabAgents() {
  const { t } = useTranslation();
  const { appInfo, fetchUpdateApp } = useContext(AppContext);
  const [searchValue, setSearchValue] = useState('');
  const [activeSource, setActiveSource] = useState<AgentSource>('all');
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configuringAgent, setConfiguringAgent] = useState<string | null>(null);
  const [tempConfig, setTempConfig] = useState<SubagentDistributedConfig>(DEFAULT_DISTRIBUTED_CONFIG);

  const { data: agentData, loading: loadingBuiltIn, refresh: refreshBuiltIn } = useRequest(async () => await getResourceV2({ type: 'app' }));

  const { data: appListData, loading: loadingAppList, refresh: refreshAppList } = useRequest(
    async () => await apiInterceptors(getAppList({ page: 1, page_size: 200 })),
  );

  const builtInAgents = useMemo(() => {
    const agents: any[] = [];
    agentData?.data?.data?.forEach((group: any) => {
      if (group.param_name === 'app_code') {
        group.valid_values?.forEach((item: any) => {
          agents.push({ ...item, isBuiltIn: true });
        });
      }
    });
    return agents;
  }, [agentData]);

  const customAgents = useMemo(() => {
    const [, res] = appListData || [];
    const appList = res?.app_list || [];
    const builtInKeys = new Set(builtInAgents.map((a: any) => a.key || a.name));
    return appList
      .filter((app: any) => app.app_code !== appInfo?.app_code && !builtInKeys.has(app.app_code))
      .map((app: any) => ({
        key: app.app_code,
        name: app.app_name || 'Untitled Agent',
        label: app.app_name || 'Untitled Agent',
        description: app.app_describe || '',
        icon: app.icon,
        isBuiltIn: false,
      }));
  }, [appListData, appInfo?.app_code, builtInAgents]);

  const allAgents = useMemo(() => {
    switch (activeSource) {
      case 'built-in':
        return builtInAgents;
      case 'custom':
        return customAgents;
      default:
        return [...builtInAgents, ...customAgents];
    }
  }, [builtInAgents, customAgents, activeSource]);

  const resourceAgents = useMemo(() => {
    return appInfo?.resource_agent || [];
  }, [appInfo?.resource_agent]);

  // 多媒体 Agent 模板（来自 ext_config.multimedia_agent，作为可关联的子 Agent 显示）
  const multimediaAgent = useMemo(() => {
    const cfg = appInfo?.ext_config?.multimedia_agent;
    return cfg || null;
  }, [appInfo?.ext_config?.multimedia_agent]);

  const handleToggleMultimedia = (checked: boolean) => {
    const ext = { ...(appInfo?.ext_config || {}) };
    ext.multimedia_agent = {
      ...(multimediaAgent || {}),
      enabled: checked,
    };
    fetchUpdateApp({ ...appInfo, ext_config: ext });
  };

  const enabledAgentKeys = useMemo(() => {
    return resourceAgents.map((item: ResourceAgent) => {
      try {
        return JSON.parse(item.value || '{}')?.key;
      } catch {
        return null;
      }
    }).filter(Boolean);
  }, [resourceAgents]);

  const getAgentDistributedConfig = (agentKey: string): SubagentDistributedConfig => {
    const agent = resourceAgents.find((item: ResourceAgent) => {
      try {
        return JSON.parse(item.value || '{}')?.key === agentKey;
      } catch {
        return false;
      }
    });
    return agent?.distributed_config || DEFAULT_DISTRIBUTED_CONFIG;
  };

  const filteredAgents = useMemo(() => {
    if (!searchValue) return allAgents;
    const lower = searchValue.toLowerCase();
    return allAgents.filter(a => (a.label || a.name || '').toLowerCase().includes(lower) || (a.key || '').toLowerCase().includes(lower));
  }, [allAgents, searchValue]);

  const builtInCount = builtInAgents.length;
  const customCount = customAgents.length;

  const handleToggle = (agent: any) => {
    const key = agent.key || agent.name;
    const isEnabled = enabledAgentKeys.includes(key);

    if (isEnabled) {
      const updatedAgents = resourceAgents.filter((item: ResourceAgent) => {
        try {
          return JSON.parse(item.value || '{}')?.key !== key;
        } catch {
          return true;
        }
      });
      fetchUpdateApp({ ...appInfo, resource_agent: updatedAgents });
    } else {
      const newAgent: ResourceAgent = {
        type: 'app',
        name: agent.label || agent.name,
        value: JSON.stringify({
          key: agent.key || agent.name,
          name: agent.label || agent.name,
          ...agent,
          app_code: agent.key || agent.app_code,
        }),
        distributed_config: DEFAULT_DISTRIBUTED_CONFIG,
      };
      fetchUpdateApp({ ...appInfo, resource_agent: [...resourceAgents, newAgent] });
    }
  };

  const handleOpenConfig = (agentKey: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConfiguringAgent(agentKey);
    setTempConfig(getAgentDistributedConfig(agentKey));
    setConfigModalOpen(true);
  };

  const handleSaveConfig = () => {
    if (!configuringAgent) return;
    
    const updatedAgents = resourceAgents.map((item: ResourceAgent) => {
      try {
        const parsed = JSON.parse(item.value || '{}');
        if (parsed.key === configuringAgent) {
          return { ...item, distributed_config: tempConfig };
        }
      } catch {}
      return item;
    });
    
    fetchUpdateApp({ ...appInfo, resource_agent: updatedAgents });
    setConfigModalOpen(false);
    setConfiguringAgent(null);
  };

  const handleRefresh = () => {
    refreshBuiltIn();
    refreshAppList();
  };

  const handleCreateAgent = () => {
    window.open('/application/explore', '_blank');
  };

  const loading = loadingBuiltIn || loadingAppList;

  return (
    <div className="flex-1 overflow-hidden flex flex-col h-full">
      <div className="px-5 py-3 border-b border-gray-100/40 flex items-center gap-2">
        <Input
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder={t('builder_search_placeholder')}
          value={searchValue}
          onChange={e => setSearchValue(e.target.value)}
          allowClear
          className="rounded-lg h-9 flex-1"
        />
        <Tooltip title={t('builder_refresh')}>
          <button
            onClick={handleRefresh}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200/80 bg-white hover:bg-gray-50 text-gray-400 hover:text-gray-600 transition-all flex-shrink-0"
          >
            <ReloadOutlined className={`text-sm ${loading ? 'animate-spin' : ''}`} />
          </button>
        </Tooltip>
        <button
          onClick={handleCreateAgent}
          className="h-9 px-3 flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-[13px] font-medium shadow-lg shadow-emerald-500/25 hover:shadow-xl hover:shadow-emerald-500/30 transition-all flex-shrink-0"
        >
          <PlusOutlined className="text-xs" />
          {t('builder_create_new')}
        </button>
      </div>

      <div className="px-5 pt-2 pb-0 border-b border-gray-100/40">
        <div className="flex items-center gap-0">
          {([
            { key: 'all', label: t('builder_agent_source_all'), count: builtInCount + customCount },
            { key: 'built-in', label: t('builder_agent_source_built_in'), count: builtInCount },
            { key: 'custom', label: t('builder_agent_source_custom'), count: customCount },
          ] as const).map(tab => (
            <button
              key={tab.key}
              className={`px-3 py-2 text-[12px] font-medium transition-all duration-200 border-b-2 ${
                activeSource === tab.key
                  ? 'text-emerald-600 border-emerald-500'
                  : 'text-gray-400 border-transparent hover:text-gray-600'
              }`}
              onClick={() => setActiveSource(tab.key)}
            >
              {tab.label}
              <span className={`ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full ${
                activeSource === tab.key ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-400'
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-3 custom-scrollbar">
        {/* 多媒体 Agent 模板（可关联的子 Agent 条目） */}
        {multimediaAgent && (
          <div className={`mb-3 flex items-center justify-between p-3 rounded-xl border transition-all duration-200 ${
            multimediaAgent.enabled
              ? 'border-fuchsia-200/80 bg-fuchsia-50/30 shadow-sm'
              : 'border-gray-100/80 bg-gray-50/20'
          }`}>
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${multimediaAgent.enabled ? 'bg-fuchsia-100' : 'bg-gray-100'}`}>
                <PictureOutlined className={`text-sm ${multimediaAgent.enabled ? 'text-fuchsia-500' : 'text-gray-400'}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium text-gray-700 truncate">
                    {multimediaAgent.name || 'multimedia_agent'}
                  </span>
                  <Tag className="mr-0 text-[10px] rounded-md border-0 font-medium px-1.5" color="magenta">
                    Multimedia
                  </Tag>
                </div>
                <div className="text-[11px] text-gray-400 truncate mt-0.5">
                  {multimediaAgent.description || '只使用多媒体生成模型的通用 Agent 模板'}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Switch
                size="small"
                checked={multimediaAgent.enabled !== false}
                onChange={handleToggleMultimedia}
                checkedChildren="已关联"
                unCheckedChildren="未关联"
              />
            </div>
          </div>
        )}
        <Spin spinning={loading}>
          {filteredAgents.length > 0 ? (
            <div className="grid grid-cols-1 gap-2">
              {filteredAgents.map((agent, idx) => {
                const key = agent.key || agent.name;
                const isEnabled = enabledAgentKeys.includes(key);
                const distConfig = getAgentDistributedConfig(key);
                return (
                  <div
                    key={`${key}-${idx}`}
                    className={`group flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all duration-200 ${
                      isEnabled
                        ? 'border-emerald-200/80 bg-emerald-50/30 shadow-sm'
                        : 'border-gray-100/80 bg-gray-50/20 hover:border-gray-200/80 hover:bg-gray-50/40'
                    }`}
                    onClick={() => handleToggle(agent)}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden ${
                        isEnabled ? 'bg-emerald-100' : 'bg-gray-100'
                      }`}>
                        {!agent.isBuiltIn && agent.icon ? (
                          <Image src={agent.icon} width={32} height={32} alt={agent.label || agent.name} className="object-cover w-full h-full" />
                        ) : agent.isBuiltIn ? (
                          <UsergroupAddOutlined className={`text-sm ${isEnabled ? 'text-emerald-500' : 'text-gray-400'}`} />
                        ) : (
                          <RobotOutlined className={`text-sm ${isEnabled ? 'text-orange-500' : 'text-gray-400'}`} />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-medium text-gray-700 truncate">{agent.label || agent.name}</span>
                          {isEnabled && (
                            <Tooltip title={`Max: ${distConfig.max_instances}, Timeout: ${distConfig.timeout}s`}>
                              <Tag className="text-[9px] rounded border-0 bg-blue-50 text-blue-600 px-1.5 py-0 m-0">
                                {distConfig.max_instances} inst
                              </Tag>
                            </Tooltip>
                          )}
                        </div>
                        <div className="text-[11px] text-gray-400 truncate mt-0.5">{agent.description || agent.key || '--'}</div>
                      </div>
                      <Tag className="mr-0 text-[10px] rounded-md border-0 font-medium px-1.5" color={agent.isBuiltIn ? 'blue' : 'orange'}>
                        {agent.isBuiltIn ? 'Built-IN' : 'Custom'}
                      </Tag>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {isEnabled && (
                        <Tooltip title={t('distributed_config_title', 'Distributed Config')}>
                          <Button
                            type="text"
                            size="small"
                            icon={<SettingOutlined className="text-gray-400 hover:text-blue-500" />}
                            onClick={(e) => handleOpenConfig(key, e)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                          />
                        </Tooltip>
                      )}
                      {isEnabled && (
                        <CheckCircleFilled className="text-emerald-500 text-base" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            !loading && (
              <div className="text-center py-12 text-gray-300 text-xs">
                {t('builder_no_items')}
              </div>
            )
          )}
        </Spin>
      </div>

      <Modal
        title={
          <div className="flex items-center gap-2">
            <SettingOutlined className="text-blue-500" />
            <span>{t('distributed_config_title', 'Distributed Config')}</span>
          </div>
        }
        open={configModalOpen}
        onCancel={() => setConfigModalOpen(false)}
        onOk={handleSaveConfig}
        okText={t('save', 'Save')}
        cancelText={t('cancel', 'Cancel')}
        width={480}
      >
        <div className="py-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t('distributed_subagent_max_instances', 'Max Instances')}</label>
              <InputNumber
                min={1}
                max={100}
                value={tempConfig.max_instances}
                onChange={(v) => setTempConfig({ ...tempConfig, max_instances: v || 5 })}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t('distributed_subagent_timeout', 'Timeout (s)')}</label>
              <InputNumber
                min={10}
                max={3600}
                value={tempConfig.timeout}
                onChange={(v) => setTempConfig({ ...tempConfig, timeout: v || 300 })}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t('distributed_subagent_retry', 'Retry Count')}</label>
              <InputNumber
                min={0}
                max={10}
                value={tempConfig.retry_count}
                onChange={(v) => setTempConfig({ ...tempConfig, retry_count: v || 3 })}
                className="w-full"
              />
            </div>
            <div className="flex items-end">
              <Checkbox
                checked={tempConfig.interactive}
                onChange={(e) => setTempConfig({ ...tempConfig, interactive: e.target.checked })}
              >
                {t('distributed_subagent_interactive', 'Interactive Mode')}
              </Checkbox>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}