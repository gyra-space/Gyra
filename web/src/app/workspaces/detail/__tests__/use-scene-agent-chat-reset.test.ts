/** @jest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react';
import { useSceneAgentChat } from '../use-scene-agent-chat';
import type { ChatQueryResponse } from '@/client/api/chat';

// 模拟 useChat:捕获每次 send 传入的 ctrl 与 SSE 回调,便于测试切换时中断旧流
interface ChatCallbacks {
  ctrl?: AbortController;
  onMessage?: (message: string) => void;
  onClose?: () => void;
  onDone?: () => void;
  onError?: (content: string) => void;
  onStreamDrop?: (content: string) => void;
  onWorkspaceEvent?: (event: Record<string, unknown>) => void;
  onDock?: (frame: Record<string, unknown>) => void;
}
let lastChatCall: ChatCallbacks | null = null;
jest.mock('@/hooks/use-chat', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    chat: jest.fn((opts: ChatCallbacks) => {
      lastChatCall = opts;
    }),
    usageMetrics: null,
    resetUsageMetrics: jest.fn(),
  })),
}));

// 模拟 useChatPolling:捕获每次渲染传入的 onPoll,由测试主动推送 vis_final,
// 模拟「拉取历史 → 合并视图」的轮询链路
let pollingOptions: {
  conversationId: string | null;
  enabled: boolean;
  onPoll?: (res: ChatQueryResponse) => void;
} | null = null;
jest.mock('@/hooks/use-chat-polling', () => ({
  useChatPolling: (opts: {
    conversationId: string | null;
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

function makeRes(conversationId: string, stepId: string, stepTitle: string): ChatQueryResponse {
  return {
    conv_id: conversationId,
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

/** 构造 SSE onMessage 收到的 scene_agent_workspace 围栏字符串(与后端下发格式一致) */
function makeFence(stepId: string, stepTitle: string): string {
  return `\`\`\`scene_agent_workspace\n${JSON.stringify({
    render_name: 'scene_agent_workspace',
    planning: null,
    execution: [{ id: stepId, title: stepTitle, type: 'tool_call', status: 'done', ts: '2026-08-21T10:00:00' }],
    summary: null,
  })}\n\`\`\``;
}

describe('useSceneAgentChat conversationId 切换重置', () => {
  test('从任务1切到任务2时清空上一会话视图,新会话只展示自己的步骤', async () => {
    const { result, rerender } = renderHook(
      (props: { conversationId?: string }) => useSceneAgentChat({ ...props, enabled: true }),
      { initialProps: { conversationId: 'c1' } },
    );

    // 任务1 历史合并进视图
    act(() => {
      pollingOptions?.onPoll?.(makeRes('c1', 't1', '任务1步骤'));
    });
    await waitFor(() => {
      expect(result.current.workspaceView.execution.map((s) => s.id)).toEqual(['t1']);
    });

    // 切到任务2:视图必须被清空,而不是把任务1步骤残留并继续累积
    rerender({ conversationId: 'c2' });
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
    const useChatMock = jest.requireMock('@/hooks/use-chat').default as jest.Mock;
    const resetUsageMetrics = jest.fn();
    useChatMock.mockImplementation(() => ({
      chat: jest.fn((opts: ChatCallbacks) => {
        lastChatCall = opts;
      }),
      usageMetrics: null,
      resetUsageMetrics,
    }));

    const { rerender } = renderHook(
      (props: { conversationId?: string }) => useSceneAgentChat({ ...props, enabled: true }),
      { initialProps: { conversationId: 'c1' } },
    );
    expect(resetUsageMetrics).not.toHaveBeenCalled();

    // 切到任务2:会话切换必须触发用量清空
    rerender({ conversationId: 'c2' });
    await waitFor(() => {
      expect(resetUsageMetrics).toHaveBeenCalled();
    });
    // 同会话内 re-render 不再重复清空
    rerender({ conversationId: 'c2' });
    expect(resetUsageMetrics).toHaveBeenCalledTimes(1);
  });

  test('运行中切换会话:abort 旧 SSE 流、重置 loading,旧流迟到回调不污染新视图', async () => {
    const { result, rerender } = renderHook(
      (props: { conversationId?: string }) => useSceneAgentChat({ ...props, enabled: true }),
      { initialProps: { conversationId: 'c1' } },
    );

    // 发起一轮对话:chat mock 捕获 ctrl 与各回调,loading 进入 true
    await act(async () => {
      result.current.send({ text: '跑任务1' });
    });
    const c1 = lastChatCall!;
    expect(c1.ctrl).toBeDefined();
    await waitFor(() => expect(result.current.loading).toBe(true));
    // loading 期间轮询被禁用(SSE 接管)
    expect(pollingOptions?.enabled).toBe(false);

    // 切到任务2:旧流必须被 abort(后端 agent 继续后台运行),loading 重置,
    // 轮询重新启用 → 新会话降级为轮询渲染
    rerender({ conversationId: 'c2' });
    await waitFor(() => {
      expect(c1.ctrl!.signal.aborted).toBe(true);
      expect(result.current.loading).toBe(false);
    });
    expect(pollingOptions?.enabled).toBe(true);

    // 旧流迟到的消息/结束事件被流纪元守卫拦截:不注入旧会话步骤、不改动新会话状态
    act(() => {
      c1.onMessage?.(makeFence('old-step', '旧会话步骤'));
      c1.onClose?.();
    });
    expect(result.current.workspaceView.execution).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});
