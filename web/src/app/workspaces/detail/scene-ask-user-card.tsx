'use client';

import React, { useMemo } from 'react';
import VisConfirmCard from '@/components/chat/chat-content-components/VisComponents/VisConfirmCard';
import { ChatContentContext } from '@/contexts';
import { parseFirstJson } from '@/utils/json';
import type { IApp } from '@/types/app';
import type { WorkspaceExecutionStep } from './agent-workspace-types';

/**
 * 从 execution step 的 output/vis 中提取 ask_user 的 drsk-confirm 数据。
 * ask_user 工具(`AskUserTool`)把交互问题渲染为 ```drsk-confirm {...}``` fence,
 * 后端 scene_agent_workspace converter 把它放进 step.output。
 * 返回 null 表示该步骤不是 ask_user 交互。
 */
export function extractAskUserData(output: unknown): Record<string, unknown> | null {
  if (typeof output !== 'string' || !output) return null;
  const m = output.match(/```drsk-confirm\s*([\s\S]*?)```/);
  if (!m) return null;
  const data = parseFirstJson(m[1]);
  return data && typeof data === 'object' ? (data as Record<string, unknown>) : null;
}

/**
 * 构建 VisConfirmCard 可用的 ChatContentContext 值。
 * 场景空间渲染管线不依赖 ChatContentContext(独立渲染器),但 VisConfirmCard
 * 通过它读取 handleChat 来在用户确认后「续跑」对话。这里提供一个将 resume
 * 路由回场景空间 send() 的 handleChat,其余字段用安全默认值填充。
 */
function buildSceneChatContext(
  onResume: (userMessage: string) => void,
): React.ContextType<typeof ChatContentContext> {
  const scrollRef = { current: null } as React.RefObject<HTMLDivElement | null>;
  return {
    history: [],
    replyLoading: false,
    scrollRef,
    canAbort: false,
    chartsData: [],
    agent: '',
    currentDialogue: {} as React.ContextType<typeof ChatContentContext>['currentDialogue'],
    currentConvSessionId: '',
    appInfo: { app_code: '' } as IApp,
    temperatureValue: 0.5,
    maxNewTokensValue: 1024,
    resourceValue: {},
    chatInParams: [],
    selectedSkills: [],
    modelValue: '',
    setChatInParams: () => {},
    setModelValue: () => {},
    setResourceValue: () => {},
    setSelectedSkills: () => {},
    setTemperatureValue: () => {},
    setMaxNewTokensValue: () => {},
    setAppInfo: () => {},
    setAgent: () => {},
    setCanAbort: () => {},
    setReplyLoading: () => {},
    setCurrentConvSessionId: () => {},
    refreshDialogList: () => {},
    refreshHistory: () => {},
    refreshAppInfo: () => {},
    setHistory: () => {},
    // 关键:用户确认后续跑场景 Agent 对话(send 复用同一 conv_uid,
    // 后端 `_initialize_agent_conversation` 检测 WAITING 会话并恢复 loop)。
    handleChat: async (content) => {
      onResume(String(content));
    },
    isShowDetail: true,
    setIsShowDetail: () => {},
    isDebug: false,
    isPollingMode: false,
    dockWidgets: {},
  };
}

export function SceneAskUserCard({
  step,
  onResume,
}: {
  step: WorkspaceExecutionStep;
  onResume: (userMessage: string) => void;
}) {
  const data = useMemo(
    () => extractAskUserData(step.output ?? step.vis),
    [step.output, step.vis],
  );
  const contextValue = useMemo(() => buildSceneChatContext(onResume), [onResume]);

  if (!data) return null;

  return (
    <ChatContentContext.Provider value={contextValue}>
      <VisConfirmCard data={data} />
    </ChatContentContext.Provider>
  );
}