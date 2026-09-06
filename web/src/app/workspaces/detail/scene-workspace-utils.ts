/** 场景空间纯工具函数(无组件/重依赖,便于单测直接导入) */

/** 判断当前任务列表里是否有活跃任务(running 等会变化的状态),决定是否开轮询。 */
export function hasActiveTask(tasks: any[]): boolean {
  const active = new Set(['running', 'pending_trigger', 'blocked', 'awaiting_human', 'draft']);
  return (tasks || []).some((t) => active.has(t?.status));
}
