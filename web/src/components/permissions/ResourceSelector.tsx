'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { Cascader, Select, Space, Tag, Typography, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import { ins as axios } from '@/client/api';

const { Text } = Typography;

export interface ResourceOption {
  value: string;
  label: string;
  type: string;
  disabled?: boolean;
}

export interface ResourceSelectorProps {
  resourceType: string;
  selectedResourceIds: string[];
  onChange: (resourceIds: string[]) => void;
  allowWildcard?: boolean;
}

interface CatalogItem {
  id: string | number;
  name?: string;
  parent_id?: string | null;
  description?: string | null;
}

interface CascadeOption {
  value: string;
  label: string;
  isLeaf?: boolean;
  loading?: boolean;
  children?: CascadeOption[];
}

async function fetchCatalog(resourceType: string, parentId?: string): Promise<{ items: CatalogItem[]; supportsHierarchy: boolean }> {
  const res = await axios.get('/api/v1/permissions/resources/catalog', {
    params: { resource_type: resourceType, parent_id: parentId, limit: 200 },
  });
  return {
    items: res.data?.data?.items || [],
    supportsHierarchy: !!res.data?.data?.supports_hierarchy,
  };
}

/**
 * Resource Selector Component (T2.1)
 *
 * 取数走统一资源目录 /permissions/resources/catalog(后端 catalog_registry
 * 的 7 个 provider:agent/tool/knowledge/model/database/channel/cron)。
 * 支持级联的资源类型(如 database:数据源→表→列)用 Cascader 逐级懒加载,
 * 其余类型用多选 Select。
 */
export default function ResourceSelector({
  resourceType,
  selectedResourceIds,
  onChange,
  allowWildcard = true,
}: ResourceSelectorProps) {
  const { t } = useTranslation();
  const [options, setOptions] = useState<ResourceOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [hierarchical, setHierarchical] = useState(false);
  const [cascadeOptions, setCascadeOptions] = useState<CascadeOption[]>([]);

  useEffect(() => {
    setLoading(true);
    fetchCatalog(resourceType)
      .then(({ items, supportsHierarchy }) => {
        setHierarchical(supportsHierarchy);
        if (supportsHierarchy) {
          setCascadeOptions(
            items.map((it) => ({
              value: String(it.id),
              label: it.name || String(it.id),
              isLeaf: false,
            })),
          );
        } else {
          const newOptions: ResourceOption[] = [];
          if (allowWildcard) {
            newOptions.push({ value: '*', label: t('permissions_all_resources'), type: 'wildcard' });
          }
          items.forEach((it) => {
            const value = String(it.id);
            newOptions.push({ value, label: it.name || value, type: resourceType });
          });
          setOptions(newOptions);
        }
      })
      .catch((error) => {
        console.error(`Failed to load ${resourceType} resources:`, error);
      })
      .finally(() => setLoading(false));
  }, [resourceType, t, allowWildcard]);

  // Cascader 懒加载子级:选中节点的 value 即 parent_id
  // (数据源 "3" → 表;表 "3.orders" → 列,isLeaf)
  const loadCascadeChildren = useCallback(
    (selectedOptions: CascadeOption[]) => {
      const target = selectedOptions[selectedOptions.length - 1];
      if (!target || target.children) return;
      target.loading = true;
      setCascadeOptions((prev) => [...prev]);
      const isTableLevel = target.value.includes('.');
      fetchCatalog(resourceType, target.value)
        .then(({ items }) => {
          target.loading = false;
          target.children = items.map((it) => ({
            value: String(it.id),
            label: it.name || String(it.id),
            isLeaf: isTableLevel ? true : items.length === 0,
          }));
          if (items.length === 0) {
            target.isLeaf = true;
            target.children = undefined;
          }
          setCascadeOptions((prev) => [...prev]);
        })
        .catch(() => {
          target.loading = false;
          target.isLeaf = true;
          setCascadeOptions((prev) => [...prev]);
        });
    },
    [resourceType],
  );

  const handleChange = (values: string[]) => {
    // If wildcard is selected, clear other selections
    if (values.includes('*')) {
      onChange(['*']);
    } else {
      // Remove wildcard if present when selecting specific resources
      onChange(values.filter((v) => v !== '*'));
    }
  };

  const renderTag = (value: string) => {
    if (value === '*') {
      return (
        <Tag color="red" className="mr-1">
          {t('permissions_all_resources')}
        </Tag>
      );
    }

    const colorMap: Record<string, string> = {
      agent: 'blue',
      tool: 'green',
      knowledge: 'orange',
      model: 'purple',
      database: 'cyan',
      wildcard: 'red',
    };

    return (
      <Tag color={colorMap[resourceType] || 'default'} className="mr-1">
        {value}
      </Tag>
    );
  };

  if (loading && options.length === 0 && cascadeOptions.length === 0) {
    return <Spin size="small" />;
  }

  // 级联模式(database 等):Cascader 多选,option value 为全路径 id,
  // 选中路径的最后一段即 resource_id
  if (hierarchical) {
    const idToPath = (id: string): string[] => {
      const segs = id.split('.');
      return segs.map((_, i) => segs.slice(0, i + 1).join('.'));
    };
    return (
      <div className="resource-selector">
        <Space direction="vertical" className="w-full">
          <Text type="secondary" className="text-xs">
            {t('permissions_cascade_hint') || '逐级展开选择(数据源 → 表 → 列),可选中任意层级'}
          </Text>
          <Cascader
            multiple
            changeOnSelect
            expandTrigger="click"
            options={cascadeOptions}
            loadData={loadCascadeChildren as any}
            value={selectedResourceIds.filter((id) => id !== '*').map(idToPath)}
            onChange={(paths) => {
              const ids = (paths as string[][]).map((p) => p[p.length - 1]);
              onChange(ids);
            }}
            displayRender={(labels: string[]) => labels[labels.length - 1]}
            placeholder={t('permissions_select_resource')}
            className="w-full"
            showSearch={{
              filter: (inputValue: string, path: any[]) =>
                path.some((o) => (o.label as string).toLowerCase().includes(inputValue.toLowerCase())),
            }}
            maxTagCount="responsive"
          />
        </Space>
      </div>
    );
  }

  return (
    <div className="resource-selector">
      <div className="mb-2">
        <Space>
          <Text strong>{t('permissions_resource_scope')}:</Text>
          {allowWildcard && (
            <Text type="secondary" className="text-xs">
              {t('permissions_scoped_permission_hint')}
            </Text>
          )}
        </Space>
      </div>
      {loading ? (
        <Spin size="small" />
      ) : (
        <Select
          mode="multiple"
          value={selectedResourceIds}
          onChange={handleChange}
          options={options.map((opt) => ({
            value: opt.value,
            label: opt.label,
            disabled: opt.disabled,
          }))}
          placeholder={t('permissions_select_resource')}
          loading={loading}
          showSearch
          filterOption={(input, option) =>
            (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
          }
          tagRender={({ value }) => renderTag(String(value))}
          className="w-full"
          maxTagCount="responsive"
          allowClear
        />
      )}
    </div>
  );
}
