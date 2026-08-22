"""
Todowrite Tool - 创建/更新任务列表工具

简洁的任务列表管理，LLM 自主决策何时使用。
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from ...base import ToolBase, ToolCategory, ToolRiskLevel
from ...metadata import ToolMetadata
from ...result import ToolResult

logger = logging.getLogger(__name__)


TODOWRITE_DESCRIPTION = """Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.

## When to Use This Tool
Use this tool proactively in these scenarios:

1. Complex multistep tasks - When a task requires 3 or more distinct steps or actions
2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
3. User explicitly requests todo list - When the user directly asks you to use the todo list
4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
5. After receiving new instructions - Immediately capture user requirements as todos. Feel free to edit the todo list based on new information.
6. After completing a task - Mark it complete and add any new follow-up tasks
7. When you start working on a new task, mark the todo as in_progress. Ideally you should only have one todo as in_progress at a time. Complete existing tasks before starting new ones.

## When NOT to Use This Tool

Skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial and tracking it provides no organizational benefit
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational

## Task States

Use these states to track progress:
- pending: Task not yet started
- in_progress: Currently working on (limit to ONE task at a time)
- completed: Task finished successfully
- cancelled: Task no longer needed

## Example

```json
{
    "todos": [
        {"content": "分析项目结构", "status": "completed"},
        {"content": "定位问题代码", "status": "in_progress"},
        {"content": "实现修复", "status": "pending"},
        {"content": "验证修复效果", "status": "pending"}
    ]
}
```"""


class TodowriteTool(ToolBase):
    """
    创建或更新任务列表工具
    """

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="todowrite",
            display_name="Write Todo List",
            description=TODOWRITE_DESCRIPTION,
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.SAFE,
            requires_permission=False,
            tags=["todo", "task", "tracking", "progress"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "任务列表，每项包含 content, status, priority(可选)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "任务内容描述",
                            },
                            "status": {
                                "type": "string",
                                "enum": [
                                    "pending",
                                    "in_progress",
                                    "completed",
                                    "cancelled",
                                ],
                                "description": "任务状态",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "任务优先级（可选，默认 medium）",
                            },
                            "id": {
                                "type": "string",
                                "description": "任务 ID（可选，不提供则自动生成）",
                            },
                        },
                        "required": ["content", "status"],
                    },
                },
            },
            "required": ["todos"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[Any] = None
    ) -> ToolResult:
        """执行任务列表更新"""
        todos = args.get("todos", [])

        if not todos:
            return ToolResult.fail(
                error="任务列表不能为空",
                tool_name=self.name,
            )

        try:
            # 获取存储和会话信息
            storage, conv_id = self._get_storage_and_conv_id(context)
            if not storage:
                return ToolResult.fail(
                    error="Todo 存储不可用",
                    tool_name=self.name,
                )

            # 获取现有任务列表以保留 ID
            existing_todos = await storage.read_todos(conv_id)
            existing_map = {t.content: t.id for t in existing_todos}

            # 构建新的任务列表
            from gyra.agent.core.memory.gpts import TodoItem, TodoStatus, TodoPriority

            new_todos = []
            for todo_data in todos:
                content = todo_data.get("content", "")
                if not content:
                    continue

                # 尝试复用现有 ID 或生成新 ID
                todo_id = (
                    todo_data.get("id")
                    or existing_map.get(content)
                    or str(uuid.uuid4())[:8]
                )
                status = todo_data.get("status", TodoStatus.PENDING.value)
                priority = todo_data.get("priority", TodoPriority.MEDIUM.value)

                todo_item = TodoItem(
                    id=todo_id,
                    content=content,
                    status=status,
                    priority=priority,
                )
                new_todos.append(todo_item)

            # 写入存储
            await storage.write_todos(conv_id, new_todos)

            # 推送可视化（dock widget；与 todo/write 事件互为冗余，
            # 任何一边丢了另一边都能恢复）
            await self._push_todolist_vis(context, new_todos)

            # 事件溯源：V2 上下文存在时 emit todo/write 事件（last-write-wins，
            # UI / 回放单一事实源；与 DSH tool-todo 的 session.append('todo/write', ...)
            # 等价）
            await self._emit_todo_write_event(context, new_todos)

            # 统计
            pending_count = sum(
                1 for t in new_todos if t.status == TodoStatus.PENDING.value
            )
            in_progress_count = sum(
                1 for t in new_todos if t.status == TodoStatus.IN_PROGRESS.value
            )
            completed_count = sum(
                1 for t in new_todos if t.status == TodoStatus.COMPLETED.value
            )

            # 工具结果格式：对齐 DSH tool-todo 的"简洁回显"。
            # - LLM 不需要再看到全部 todos（它的上一轮 tool_call 参数里已经有）
            # - 只回显 counts + 紧凑列表提示，让 LLM 验证自己的写入并规划下一步
            # - 完整 todos 通过 metadata 字段携带（不进 LLM 上下文，仅供 UI/审计）
            todos_payload = [t.to_dict() for t in new_todos]
            counts = {
                "pending": pending_count,
                "in_progress": in_progress_count,
                "completed": completed_count,
            }
            # 人类/LLM 双友好的回显文本
            overview = (
                f"已更新任务列表：{len(new_todos)} 项 "
                f"({pending_count} pending / {in_progress_count} in_progress / {completed_count} completed)"
            )
            items_line = "\n".join(
                f"  - [{t.status}] {t.content}" for t in new_todos
            )
            output_text = f"{overview}\n{items_line}"

            return ToolResult.ok(
                output=output_text,
                tool_name=self.name,
                metadata={
                    "total": len(new_todos),
                    "todos": todos_payload,
                    "counts": counts,
                },
            )

        except Exception as e:
            logger.exception(f"Failed to write todos: {e}")
            return ToolResult.fail(
                error=f"更新任务列表失败: {str(e)}",
                tool_name=self.name,
            )

    async def _emit_todo_write_event(
        self,
        context: Optional[Any],
        todos: List[Any],
    ) -> None:
        """向 V2 事件流 emit ``todo/write`` 事件（last-write-wins）。

        与 DSH tool-todo 的 ``exec.agent.session.append('todo/write', { todos })``
        语义等价：事件流是 UI / 回放的单一事实源，**不**进 LLM 上下文。

        - 失败吞掉（事件流是辅助通道，写入失败不能阻塞 todo 写入主流程）
        - 探测 context 上是否有 v2_event_stream / state_store 暴露点
        """
        if not context or not todos:
            return
        try:
            agent = getattr(context, "agent", None) or context
            # 优先级 1：直接挂在 context 上的 V2 event stream
            event_stream = (
                getattr(context, "v2_event_stream", None)
                or getattr(agent, "v2_event_stream", None)
            )
            # 优先级 2：通过 V2Agent._ensure_v2_state_store 获取 state store
            # （事件持久化走 StateStore；EventStream 是订阅层）
            state_store = (
                getattr(agent, "_ensure_v2_state_store", None)
                and agent._ensure_v2_state_store()
                if hasattr(agent, "_ensure_v2_state_store")
                else None
            )
            if state_store is None:
                return

            from gyra.agent.core.v2.step_event import StepEvent
            from gyra.agent.core.v2.step_state import StepState
            import time as _time
            import uuid as _uuid

            conv_id = "default"
            step_id = getattr(agent, "_v2_current_step_id", None) or "todo-write"
            agent_id = getattr(agent, "name", None) or "todowrite"
            if hasattr(agent, "not_null_agent_context"):
                ctx = agent.not_null_agent_context
                if ctx:
                    conv_id = ctx.conv_id or conv_id

            ev = StepEvent(
                event_id=f"todo-write-{_uuid.uuid4().hex[:8]}",
                step_id=step_id,
                conv_id=conv_id,
                agent_id=agent_id,
                state=StepState.OBSERVING,
                event_type="todo/write",
                input={"tool": "todowrite"},
                output={"todos": [t.to_dict() for t in todos]},
                seq=0,  # 由 StateStore.append_event 重新分配全局 seq
                timestamp=_time.time(),
            )
            await state_store.append_event(ev)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[todowrite] emit todo/write event skipped: {e}")

    def _get_storage_and_conv_id(self, context: Optional[Any]):
        """获取 TodoStorage 和 conv_id"""
        if not context:
            return None, None

        # 尝试从 context 获取 agent
        agent = getattr(context, "agent", None) or context
        # V2 路径：agent 经 ToolContextFactory 以 resource("agent") 注入，
        # 而 ToolContext 是 pydantic 模型，其 ``agent`` 字段不存在，
        # 需走 get_resource 探测。
        if not hasattr(agent, "memory") and hasattr(context, "get_resource"):
            agent = context.get_resource("agent") or agent

        # 获取存储
        storage = None
        if hasattr(agent, "memory") and hasattr(agent.memory, "gpts_memory"):
            storage = agent.memory.gpts_memory

        # 获取 conv_id
        conv_id = "default"
        if hasattr(agent, "not_null_agent_context"):
            ctx = agent.not_null_agent_context
            if ctx:
                conv_id = ctx.conv_id or ctx.conv_session_id or "default"

        return storage, conv_id

    async def _push_todolist_vis(
        self, context: Optional[Any], todos: List[Any]
    ) -> None:
        """将 TodoList 作为 dock widget 推入输入区 Dock（Composer Dock 协议）。

        取代旧的 d-todo-list 围栏字符串：构造结构化 widget 后调
        gpts_memory.push_dock_widget，前端凭 type 注册表渲染，无需字符串拦截。
        """
        try:
            agent = getattr(context, "agent", None) or context
            if not agent:
                return

            memory = getattr(agent, "memory", None)
            gpts_memory = getattr(memory, "gpts_memory", None) if memory else None
            conv_id = "default"
            if hasattr(agent, "not_null_agent_context"):
                ctx = agent.not_null_agent_context
                if ctx:
                    conv_id = ctx.conv_id or "default"

            if not gpts_memory:
                return

            from gyra.agent.tools.builtin.todo.todo_reminder import build_todo_widget

            widget = build_todo_widget(todos, conv_id)
            await gpts_memory.push_dock_widget(conv_id=conv_id, widget=widget)
            logger.debug(f"Pushed todolist dock widget with {len(todos)} items")

        except Exception as e:
            logger.warning(f"Failed to push todolist dock widget: {e}")
