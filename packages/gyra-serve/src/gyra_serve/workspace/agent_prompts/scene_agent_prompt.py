"""场景空间 Agent 的动态上下文渲染。

职责单一：只渲染"当前场景事实"（进行中任务 / 当前任务 / 用户关注对象）。
- 执行决策与行为规则 → app 身份模板（gyra_app_define/scene-workspace-agent.json
  的 system_prompt_template），不在本模块重复；
- 工具用法 → WorkspaceSceneResource 的"场景空间工具速查"块，不在本模块重复。
"""

from typing import List

from gyra_serve.workspace.agent_tools.context_builder import (
    WorkspaceContextSnapshot,
)


def render_scene_dynamic_context(
    ctx: WorkspaceContextSnapshot, mode: str = "lobby"
) -> str:
    """渲染场景动态事实块，供注入 system prompt 的"当前场景上下文"。

    Args:
        ctx: 工作空间上下文快照。
        mode: "lobby" 渲染进行中任务列表；"workbench" 渲染当前任务详情。
    """
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
        lines.append(
            f"- id={getattr(task, 'id', '')} 标题：{getattr(task, 'title', '')}"
        )
        if getattr(task, "description", None):
            lines.append(f"- 描述：{task.description}")
        if getattr(task, "status", None):
            lines.append(f"- 状态：{task.status}")

    # Layer 3: user's currently focused artifact (implicit context)
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

    return "\n\n".join(lines)
