"""Skill 发布 Agent 工具 —— 把会话内创建的技能一键发布到技能资源库。

定位:薄封装层。内部直接复用 ``gyra_serve.skill.publish.publish_skill_from_dir``
(与 REST ``/upload`` 同一数据通路),不走 HTTP。

安全模型(fail-closed,对齐 feature_plugins/permissions/agent_tools.py):
- 从 ``ToolContext`` 取提问者的 ``user_request``(V2 tool_context_factory 注入);
- 取不到 → 拒绝(不允许无身份发布);
- 有身份但没有 ``skill.publish`` 权限(走 gyra_serve.permissions.has)→ 拒绝;
- 发布是全局生效的(server_app_skill 表不分租户/用户),故默认 ask_user 确认。

典型用法:skill-creator 在会话里创建完技能目录后,调用本工具把目录发布;
同名 skill_code 会原地覆盖更新。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from gyra.agent.tools.base import ToolCategory, ToolRiskLevel, ToolSource
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.decorators import tool

logger = logging.getLogger(__name__)

_PUBLISH_PERMISSION_KEY = "skill.publish"


def _deny(reason: str) -> Dict[str, Any]:
    return {"success": False, "error": reason, "code": "PERMISSION_DENIED"}


def _resolve_caller(context: Any):
    """兼容两种 context 注入形态,返回 (user_request, workspace_id)。

    - V2 引擎(tool_context_factory):context 是 ToolContext,
      user_request/workspace_id 经 set_resource 注入;
    - V1 引擎(react_master):tool_action 约定 context 即 agent 本身
      (见 tool_action.py "统一框架非沙箱 ToolBase 工具 context 即 agent"),
      身份/空间从 ``agent.agent_context.extra`` 取(由
      ``AgentContext(extra=ext_info)`` 注入,ext_info 含 user_request/workspace_id)。
    """
    if context is None:
        return None, None
    if isinstance(context, ToolContext):
        return (
            context.get_resource("user_request"),
            context.get_resource("workspace_id"),
        )
    # V1:context 是 agent(或包装对象,内含 .agent)
    agent = getattr(context, "agent", None) or context
    extra = getattr(getattr(agent, "agent_context", None), "extra", None) or {}
    return extra.get("user_request"), extra.get("workspace_id")


def _operator_name(user_request) -> str:
    return (
        getattr(user_request, "user_name", None)
        or getattr(user_request, "real_name", None)
        or "unknown"
    )


@tool(
    "skill_publish",
    description=(
        "把会话内创建的技能发布到技能资源库(全局生效,发布后所有 Agent/空间可用)。"
        "参数 skill_dir 传技能的独立子目录(含 SKILL.md,如 <work>/<skill-name>/),"
        "不要传工作目录根(根目录的无关文件会被一并发布,结果 warnings 会提示)。"
        "skill-creator 创建或修改完技能后调用;同名技能会被覆盖更新。"
    ),
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["skill", "publish", "write"],
    ask_user=True,
)
def skill_publish(
    skill_dir: str, context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """发布技能目录到技能资源库。

    Args:
        skill_dir: 技能目录路径(目录内含 SKILL.md;支持传父目录自动查找)
    """
    user_request, workspace_id = _resolve_caller(context)
    if user_request is None:
        return _deny("无法确认操作者身份(缺少用户上下文),拒绝发布技能")
    from gyra_serve.permissions import has as has_permission

    if not has_permission(user_request, _PUBLISH_PERMISSION_KEY):
        name = getattr(user_request, "user_name", None) or "unknown"
        return _deny(
            f"用户 {name} 没有技能发布权限({_PUBLISH_PERMISSION_KEY}),拒绝发布"
        )

    from gyra_serve.skill.publish import publish_skill_from_dir

    return publish_skill_from_dir(
        skill_dir,
        operator=_operator_name(user_request),
        workspace_id=workspace_id,
    )
