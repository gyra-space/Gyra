import type { WorkspaceExecutionStep } from './agent-workspace-types';

/** 去重乐观用户步骤:后端回显(type=user、非 user-optimistic- 前缀)同文本消息后,
 *  移除对应的乐观步骤,避免用户气泡重复。服务端 output 可能截断,用前缀匹配。
 *
 *  send(SSE 回显)与 handlePoll(轮询 vis_final 回显)共用,使运行中追问(submitUserInput
 *  路径,仅靠轮询回显)的乐观气泡也能被正确去重。
 *
 *  独立成文件(而非放在 use-scene-agent-chat.ts)以避开 hook 模块 ESM-only 的
 *  remark-parse 依赖,便于在 Node 测试环境直接断言。 */
export function dedupOptimisticUser(execution: WorkspaceExecutionStep[]): WorkspaceExecutionStep[] {
  const echoed = execution.filter(
    (s) => s.type === 'user' && !s.id.startsWith('user-optimistic-') && typeof s.output === 'string' && s.output.length > 0,
  );
  if (!echoed.length) return execution;
  const echoedTexts = echoed.map((s) => s.output as string);
  return execution.filter((s) => {
    if (s.type !== 'user' || !s.id.startsWith('user-optimistic-')) return true;
    const text = s.output || '';
    if (!text) return true;
    return !echoedTexts.some((e) => e === text || text.startsWith(e));
  });
}
