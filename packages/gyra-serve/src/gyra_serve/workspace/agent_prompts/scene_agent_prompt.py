from typing import List

from gyra_serve.workspace.agent_tools.context_builder import (
    WorkspaceContextSnapshot,
)

SCENE_AGENT_STATIC_PROMPT = """\
你是 Gyra 场景空间助手（Scene Workspace Agent），当前工作空间的协作者。
你不是通用聊天助手；你的目标是理解用户在该场景空间中的工作目标，调用合适的工具推进任务，并把结果沉淀为可复用的资产或报告。

执行方式遵循「非二选一不可互斥」的准则：
- 默认：在当前主会话里直接完成用户的分析类请求。加载所需的 skill / 数据工具，
  分析并直接产出结果，不要为此创建任务。
- 仅当用户明确要求异步/后台执行，或这是订阅/触发类流程时，才调用 start_task 创建任务。
- 任务一旦创建并交付给异步执行，就不要再在当前会话里重复做一遍相同的分析。
"""

# 场景 Agent 动态上下文中追加的执行方式约束(渲染进 system prompt)
EXECUTION_MODE_GUIDANCE = """\
## 执行方式选择(重要)
请先判断本次请求应采用哪种执行方式，二者互斥，不要同时进行：
- 当前会话直接执行（默认）：大多数分析/查询/写作类请求，直接在当前对话里加载
  skill 与数据工具完成并回复即可，**不要创建任务**。
- 创建任务（start_task）：仅当 (a) 用户明确要求异步/后台执行，或 (b) 属于订阅/触发
  类流程时才使用。创建任务后它会在后台独立执行，**不要在当前会话里再重复做一遍**，
  只需向用户确认任务已创建并说明其状态。
"""

_LOBBY_TOOLS = [
    "list_tasks", "get_task_info", "list_artifacts", "list_deliveries", "list_assets",
    "get_workspace_memory", "list_workspace_members", "get_playbook_detail",
    "list_triggers",
    "start_task", "close_task", "publish_asset", "create_delivery", "update_workspace",
    "update_trigger", "delete_trigger", "fire_trigger",
]

_WORKBENCH_TOOLS = [
    "list_tasks", "get_task_info", "list_artifacts", "list_deliveries", "list_assets",
    "list_playbooks", "get_playbook_detail", "list_interventions", "list_triggers",
    "start_task", "close_task", "publish_asset", "create_delivery", "update_workspace",
    "create_playbook", "update_playbook", "delete_playbook",
    "update_trigger", "delete_trigger", "fire_trigger",
]


def render_scene_dynamic_context(ctx: WorkspaceContextSnapshot, mode: str = "lobby") -> str:
    """Render the dynamic workspace/playbook/task/tools block for the scene agent."""
    lines: List[str] = []

    # Layer 1: active tasks (lobby only)
    if mode == "lobby" and ctx.active_tasks:
        lines.append("## 进行中任务")
        for t in ctx.active_tasks:
            tid = getattr(t, "id", "")
            title = getattr(t, "title", "")
            status = getattr(t, "status", "")
            lines.append(f"- id={tid} 标题：{title} 状态：{status}")

    # Layer 2: current task detail (workbench only)
    if mode == "workbench" and ctx.task:
        lines.append("## 当前任务详情")
        task = ctx.task
        lines.append(f"- id={getattr(task, 'id', '')} 标题：{getattr(task, 'title', '')}")
        if getattr(task, "description", None):
            lines.append(f"- 描述：{task.description}")
        if getattr(task, "status", None):
            lines.append(f"- 状态：{task.status}")

    # Layer 2.5: user's currently focused artifact (implicit context)
    if ctx.focused_artifact:
        lines.append("## 用户当前关注")
        art = ctx.focused_artifact
        art_id = getattr(art, "id", "")
        art_title = getattr(art, "title", "") or f"artifact_{art_id}"
        art_type = getattr(art, "type", "") or ""
        lines.append(f"- id={art_id} 标题：{art_title} 类型：{art_type}")
        content = getattr(art, "content_text", None)
        if content:
            snippet = content[:500]
            if len(content) > 500:
                snippet += "…"
            lines.append(f"- 内容摘要：{snippet}")

    # Layer 3: available tools
    tool_names = _LOBBY_TOOLS if mode == "lobby" else _WORKBENCH_TOOLS
    lines.append("## 当前可用工具")
    lines.append(
        "当前模式下常用的工具参考：" + ", ".join(f"`{n}`" for n in tool_names)
    )

    # Layer 4: execution mode guidance (default self-analysis; task only for async/trigger)
    lines.append(EXECUTION_MODE_GUIDANCE)

    return "\n\n".join(lines)
