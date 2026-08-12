'use client';

import { apiInterceptors, listResources } from '@/client/api';
import { AppstoreOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ResourcePicker from './resource-picker';
import type { ResourceItem, SkillRef } from './types';

interface SkillsSectionProps {
  value?: SkillRef[];
  onChange: (value: SkillRef[]) => void;
  workspaceId?: number;
}

/**
 * 技能选择器:与资源选择器同口径——只从空间资源池(skill 类型)里选。
 *
 * 分层模型:空间 = 注册/治理池(有什么、谁能碰),剧本 = 选配/编排子集(用什么、怎么用)。
 * 剧本能引用的能力必须是空间已绑定的能力,避免"技能走全局、资源走空间"的双轨混淆。
 * 已选但不在空间池的技能(历史数据)保留展示并标记「未绑定」,引导到「能力」页绑定。
 */
export default function SkillsSection({ value = [], onChange, workspaceId }: SkillsSectionProps) {
  const { t } = useTranslation();

  const { data: poolData, loading, refresh } = useRequest(
    async () => {
      if (!workspaceId) return [];
      const [err, res] = await apiInterceptors(
        listResources({ workspace_id: workspaceId, type: 'skill' }),
      );
      return err ? [] : res || [];
    },
    { ready: !!workspaceId, refreshDeps: [workspaceId] },
  );

  const skills = useMemo(() => {
    const items: ResourceItem[] = (poolData || []).map((r: any) => ({
      key: r.physical_ref || r.name,
      name: r.name,
      label: r.name,
      description: r.physical_ref || '',
      type: 'skill',
      skillCode: r.physical_ref || r.name,
    }));
    const poolKeys = new Set(items.map((i) => i.key));
    // 已选但不在空间池的技能(历史数据)-> 保留展示并标记未绑定,引导绑定
    value.forEach((skill) => {
      const code = typeof skill === 'string' ? skill : skill?.name;
      if (code && !poolKeys.has(code)) {
        items.push({
          key: code,
          name: code,
          label: code,
          description:
            t('playbooks.visual_editor.skill_unbound_desc') ||
            '未绑定到当前空间,请到「能力」页绑定后生效',
          type: 'skill',
          skillCode: code,
          unbound: true,
        });
      }
    });
    return items;
  }, [poolData, value, t]);

  const selectedRefs = useMemo(() => {
    return value
      .map((skill) => (typeof skill === 'string' ? skill : skill?.name))
      .filter((name): name is string => !!name);
  }, [value]);

  const handleToggle = (ref: string) => {
    const isEnabled = selectedRefs.includes(ref);
    if (isEnabled) {
      onChange(
        value.filter((skill) => {
          const name = typeof skill === 'string' ? skill : skill?.name;
          return name !== ref;
        }),
      );
    } else {
      onChange([...value, { type: 'skill', name: ref }]);
    }
  };

  return (
    <ResourcePicker
      items={skills}
      selectedRefs={selectedRefs}
      loading={loading}
      onRefresh={refresh}
      onToggle={handleToggle}
      getRef={(item: ResourceItem) => item.key}
      getLabel={(item: ResourceItem) => item.label || item.name || item.key}
      getDescription={(item: ResourceItem) => item.description || item.type || ''}
      getTag={(item: ResourceItem) =>
        item.unbound
          ? { label: t('playbooks.visual_editor.skill_unbound') || '未绑定', color: 'orange' }
          : null
      }
      icon={<AppstoreOutlined />}
      activeColor="orange"
      emptyText={
        t('playbooks.visual_editor.skill_empty_guide') ||
        '当前空间未绑定任何技能:剧本只能使用空间已绑定的能力,请先到「能力」页绑定技能'
      }
    />
  );
}
