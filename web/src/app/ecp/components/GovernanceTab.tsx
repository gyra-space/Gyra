'use client';

import { Segmented } from 'antd';
import { useState } from 'react';

import LintTab from './LintTab';
import MissTab from './MissTab';
import SettingsTab from './SettingsTab';

type Section = 'lint' | 'miss' | 'settings';

/**
 * 治理：把低频但必要的巡检、未命中学习、设置收拢到同一个视图，避免导航碎片化。
 */
export default function GovernanceTab({ workspaceId }: { workspaceId: string }) {
  const [section, setSection] = useState<Section>('settings');

  return (
    <>
      <Segmented
        value={section}
        onChange={v => setSection(v as Section)}
        options={[
          { label: '设置', value: 'settings' },
          { label: '巡检', value: 'lint' },
          { label: '未命中', value: 'miss' },
        ]}
      />
      <div style={{ marginTop: 16 }}>
        {section === 'settings' && <SettingsTab workspaceId={workspaceId} />}
        {section === 'lint' && <LintTab workspaceId={workspaceId} />}
        {section === 'miss' && <MissTab workspaceId={workspaceId} />}
      </div>
    </>
  );
}
