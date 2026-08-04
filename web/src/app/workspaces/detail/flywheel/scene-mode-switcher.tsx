'use client';

/**
 * 场景模式切换器 —— 四种业务模式分段控件。
 *
 * 视觉:iOS 风格分段控件,激活 pill 浮起(白底 + 阴影),
 * 颜色随模式语义色变化。
 */
import { useState } from 'react';
import { Tooltip } from 'antd';
import {
  AuditOutlined,
  FileSearchOutlined,
  MonitorOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useRequest } from 'ahooks';
import {
  getWorkspaceSceneMode,
  setWorkspaceSceneMode,
  type SceneMode,
} from '@/client/api/flywheel';

interface SceneModeSwitcherProps {
  workspaceId: number;
}

/** 模式配置(color 直接用 hex,pill 激活时着色) */
const MODE_CONFIG: Record<
  SceneMode,
  { label: string; icon: React.ReactNode; color: string; description: string }
> = {
  task: {
    label: '任务执行',
    icon: <ThunderboltOutlined />,
    color: '#4f46e5',
    description: '按 playbook 执行任务,产出资产',
  },
  decision: {
    label: '决策讨论',
    icon: <AuditOutlined />,
    color: '#f59e0b',
    description: '多角色讨论,形成决策结论',
  },
  knowledge: {
    label: '知识整理',
    icon: <FileSearchOutlined />,
    color: '#22c55e',
    description: '沉淀知识,构建组织记忆',
  },
  monitoring: {
    label: '持续监控',
    icon: <MonitorOutlined />,
    color: '#06b6d4',
    description: '持续监控指标,异常自动告警',
  },
};

export function SceneModeSwitcher({ workspaceId }: SceneModeSwitcherProps) {
  const [currentMode, setCurrentMode] = useState<SceneMode>('task');

  // 获取当前模式
  useRequest(
    async () => {
      const res = await getWorkspaceSceneMode(workspaceId);
      if (res.data?.data?.mode) {
        setCurrentMode(res.data.data.mode as SceneMode);
      }
    },
    { refreshDeps: [workspaceId] },
  );

  const handleModeChange = async (mode: SceneMode) => {
    if (mode === currentMode) return;
    try {
      await setWorkspaceSceneMode(workspaceId, { mode });
      setCurrentMode(mode);
    } catch (e) {
      console.error('切换模式失败:', e);
    }
  };

  return (
    <div className="ws-flywheel__modes" role="tablist" aria-label="场景模式">
      {(Object.keys(MODE_CONFIG) as SceneMode[]).map((mode) => {
        const config = MODE_CONFIG[mode];
        const isActive = currentMode === mode;
        return (
          <Tooltip key={mode} title={config.description}>
            <button
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`ws-flywheel__mode${isActive ? ' ws-flywheel__mode--on' : ''}`}
              style={isActive ? ({ '--mode-color': config.color } as React.CSSProperties) : undefined}
              onClick={() => handleModeChange(mode)}
            >
              {config.icon}
              {config.label}
            </button>
          </Tooltip>
        );
      })}
    </div>
  );
}
