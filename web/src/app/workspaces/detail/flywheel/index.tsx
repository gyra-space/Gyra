'use client';

/**
 * 飞轮工作台 —— 整合飞轮仪表盘、评委工作台、Agent 成长、演化审批。
 *
 * 布局:
 * ┌───────────────────────────────────────────────┐
 * │  标题 + 场景模式分段控件                       │
 * ├───────────────────────────────────────────────┤
 * │  飞轮闭环 │ 资产成熟度 │ Agent成长+演化提议    │
 * ├──────────────────────┬────────────────────────┤
 * │  评委工作台           │  Agent 成长面板        │
 * ├──────────────────────┴────────────────────────┤
 * │  剧本演化审批                                  │
 * └───────────────────────────────────────────────┘
 */
import { useState } from 'react';
import { App } from 'antd';
import { FlywheelDashboard } from './flywheel-dashboard';
import { JudgeBench } from './judge-bench';
import { AgentGrowthPanel } from './agent-growth-panel';
import { EvolutionApprovalPanel } from './evolution-approval-panel';
import { SceneModeSwitcher } from './scene-mode-switcher';
import './flywheel.css';

interface FlywheelWorkspaceProps {
  workspaceId: number;
  workspaceCode?: string;
}

export function FlywheelWorkspace({ workspaceId }: FlywheelWorkspaceProps) {
  const { message } = App.useApp();
  const [refreshKey, setRefreshKey] = useState(0);

  const handleActionComplete = () => {
    setRefreshKey((k) => k + 1);
    message.success('操作完成,飞轮数据已更新');
  };

  return (
    <div className="ws-flywheel">
      <div className="ws-flywheel__scroll">
        {/* 顶栏:副标题 + 场景模式(主标题由场景空间头部承载) */}
        <div className="ws-flywheel__topbar">
          <div className="ws-flywheel__heading">
            <span className="ws-flywheel__subtitle">
              资产沉淀 · Agent 成长 · 自动演化 · 评测反馈
            </span>
          </div>
          <SceneModeSwitcher workspaceId={workspaceId} />
        </div>

        {/* 飞轮仪表盘 */}
        <FlywheelDashboard workspaceId={workspaceId} key={`dash-${refreshKey}`} />

        {/* 评委工作台 + Agent 成长 */}
        <div className="ws-flywheel__duo">
          <JudgeBench workspaceId={workspaceId} onActionComplete={handleActionComplete} />
          <AgentGrowthPanel workspaceId={workspaceId} key={`growth-${refreshKey}`} />
        </div>

        {/* 剧本演化审批 */}
        <EvolutionApprovalPanel workspaceId={workspaceId} key={`evo-${refreshKey}`} />
      </div>
    </div>
  );
}
