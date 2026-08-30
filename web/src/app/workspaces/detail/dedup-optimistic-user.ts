import type { WorkspaceExecutionStep, WorkspaceUserAttachment } from './agent-workspace-types';

/** 归一化时间戳为毫秒(与 parse-workspace-view.ts 的 tsToMs 语义一致),无法解析返回 null。 */
function tsToMs(ts: string | null | undefined): number | null {
  if (!ts) return null;
  let norm = ts.includes(' ') ? ts.replace(' ', 'T') : ts;
  norm = norm.replace(/\.(\d{3})\d+/, '.$1');
  const ms = Date.parse(norm);
  return Number.isNaN(ms) ? null : ms;
}

/** 去重乐观用户步骤:后端回显(type=user、非 user-optimistic- 前缀)同文本消息后,
 *  移除对应的乐观步骤,避免用户气泡重复。服务端 output 可能截断,用前缀匹配。
 *
 *  send(SSE 回显)与 handlePoll(轮询 vis_final 回显)共用,使运行中追问(submitUserInput
 *  路径,仅靠轮询回显)的乐观气泡也能被正确去重。
 *
 *  为避免把「历史轮次的用户消息」误判为当前提交的回显(追问的新消息以某条旧消息开头时,
 *  纯前缀匹配会提前删掉乐观气泡,导致用户消息要等 AI 输出才重新出现),仅接受时间戳不早于
 *  乐观步骤(即在该消息提交之后才落库)的回显作为当前回显;时间戳缺失时回退到原文本匹配。
 *
 *  附件闭环:后端回显 user 步骤不携带 attachments 结构,删除乐观步骤时把其附件
 *  转移挂到匹配的回显步骤上,保证去重后气泡仍展示文件附件。
 *
 *  独立成文件(而非放在 use-scene-agent-chat.ts)以避开 hook 模块 ESM-only 的
 *  remark-parse 依赖,便于在 Node 测试环境直接断言。 */
export function dedupOptimisticUser(execution: WorkspaceExecutionStep[]): WorkspaceExecutionStep[] {
  const echoed = execution.filter(
    (s) => s.type === 'user' && !s.id.startsWith('user-optimistic-') && typeof s.output === 'string' && s.output.length > 0,
  );
  if (!echoed.length) return execution;
  const dropIds = new Set<string>();
  const attachToEcho = new Map<string, WorkspaceUserAttachment[]>();
  for (const s of execution) {
    if (s.type !== 'user' || !s.id.startsWith('user-optimistic-')) continue;
    const text = s.output || '';
    const attachments = Array.isArray(s.attachments) ? s.attachments : [];
    if (!text && !attachments.length) continue;
    const om = tsToMs(s.ts);
    const matchedEcho = echoed.find((e) => {
      const et = e.output as string;
      let matched: boolean;
      if (text) {
        // 双向前缀:回显 output 可能截断(比乐观短),也可能注入「📎 上传文件」提示(比乐观长)
        matched = et === text || text.startsWith(et) || et.startsWith(text);
      } else {
        // 纯文件无文本:乐观 output 为空,按附件名在回显的文件提示中匹配
        matched = attachments.some((a) => !!a && !!a.name && et.includes(a.name));
      }
      if (!matched) return false;
      const em = tsToMs(e.ts);
      // 双方时间戳可比较时,仅接受「不早于乐观步骤」的回显,防止旧轮次消息前缀误删;
      // 时间戳缺失时无法判定新旧,回退到文本匹配(兼容无 ts 的历史数据/单测)。
      if (em !== null && om !== null) return em >= om;
      return true;
    });
    if (!matchedEcho) continue;
    dropIds.add(s.id);
    if (attachments.length && !(matchedEcho.attachments && matchedEcho.attachments.length)) {
      attachToEcho.set(matchedEcho.id, attachments);
    }
  }
  if (!dropIds.size) return execution;
  return execution
    .filter((s) => !dropIds.has(s.id))
    .map((s) => (attachToEcho.has(s.id) ? { ...s, attachments: attachToEcho.get(s.id)! } : s));
}
