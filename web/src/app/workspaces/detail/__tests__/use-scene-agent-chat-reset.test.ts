/** @jest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react';
import { useSceneAgentChat } from '../use-scene-agent-chat';
import type { ChatQueryResponse } from '@/client/api/chat';

// 模拟 useChat:send 链路不在本测试覆盖范围
jest.mock('@/hooks/use-chat', () => ({
  __esModule: true,
  default: jest.fn(() => ({ chat: jest.fn(), usageMetrics: null, resetUsageMetrics: jest.fn() })),
}));

// 模拟 useChatPolling:捕获每次渲染传入的 onPoll,由测试主动推送 vis_final,
// 模拟「拉取历史 → 合并视图」的轮询链路
let pollingOptions: {
  convId: string | null;
  enabled: boolean;
  onPoll?: (res: ChatQueryResponse) => void;
} | null = null;
jest.mock('@/hooks/use-chat-polling', () => ({
  useChatPolling: (opts: {
    convId: string | null;
    enabled: boolean;
    onPoll?: (res: ChatQueryResponse) => void;
  }) => {
    pollingOptions = opts;
    return {
      state: 'COMPLETE',
      isPolling: false,
      data: null,
      startPolling: jest.fn(),
      stopPolling: jest.fn(),
      checkStatus: jest.fn().mockResolvedValue(null),
    };
  },
}));

function makeRes(convId: string, stepId: string, stepTitle: string): ChatQueryResponse {
  return {
    conv_id: convId,
    state: 'COMPLETE',
    is_final: true,
    vis_final: JSON.stringify({
      render_name: 'scene_agent_workspace',
      planning: null,
      execution: [{ id: stepId, title: stepTitle, type: 'tool_call', status: 'done', ts: '2026-08-21T10:00:00' }],
      summary: null,
    }),
    user_answer: '',
    vis_render: 'scene_agent_workspace',
  };
}

describe('useSceneAgentChat convUid 切换重置', () => {
  test('从任务1切到任务2时清空上一会话视图,新会话只展示自己的步骤', async () => {
    const { result, rerender } = renderHook(
      (props: { convUid?: string }) => useSceneAgentChat({ ...props, enabled: true }),
      { initialProps: { convUid: 'c1' } },
    );

    // 任务1 历史合并进视图
    act(() => {
      pollingOptions?.onPoll?.(makeRes('c1', 't1', '任务1步骤'));
    });
    await waitFor(() => {
      expect(result.current.workspaceView.execution.map((s) => s.id)).toEqual(['t1']);
    });

    // 切到任务2:视图必须被清空,而不是把任务1步骤残留并继续累积
    rerender({ convUid: 'c2' });
    await waitFor(() => {
      expect(result.current.workspaceView.execution).toEqual([]);
    });

    // 任务2 历史合并:只含任务2步骤
    act(() => {
      pollingOptions?.onPoll?.(makeRes('c2', 't2', '任务2步骤'));
    });
    await waitFor(() => {
      expect(result.current.workspaceView.execution.map((s) => s.id)).toEqual(['t2']);
    });
  });

  test('切换会话时调用 resetUsageMetrics 清空上一会话上下文用量(环形图不残留)', async () => {
    const useChatMock = (jest.requireMock('@/hooks/use-chat') as any).default;
    const resetUsageMetrics = jest.fn();
    useChatMock.mockImplementation(() => ({ chat: jest.fn(), usageMetrics: null, resetUsageMetrics }));

    const { result, rerender } = renderHook(
      (props: { convUid?: string }) => useSceneAgentChat({ ...props, enabled: true }),
      { initialProps: { convUid: 'c1' } },
    );
    expect(resetUsageMetrics).not.toHaveBeenCalled();

    // 切到任务2:会话切换必须触发用量清空
    rerender({ convUid: 'c2' });
    await waitFor(() => {
      expect(resetUsageMetrics).toHaveBeenCalled();
    });
    // 同会话内 re-render 不再重复清空
    rerender({ convUid: 'c2' });
    expect(resetUsageMetrics).toHaveBeenCalledTimes(1);
  });
});
