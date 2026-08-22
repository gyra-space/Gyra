"""
Skill 工具模块

提供统一的 Skill 操作工具：
- skill: 读取 Skill 的 SKILL.md 内容 / 加载指令（V1/V2 公用的唯一入口）

V1 原先的 ``skill_exec`` / ``skill_list`` 已废弃删除：脚本执行用 Bash 替代，
skill 目录信息由 V2 的 SkillCatalogConsumer / available_skills 预注入。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...registry import ToolRegistry


def register_skill_tools(registry: "ToolRegistry") -> None:
    """注册 Skill 工具（统一 ``skill`` 入口，V1/V2 公用）。"""
    from gyra.agent.core.v2.skills import SKILL_TOOL_NAME, SkillTool

    registry.register(SkillTool())
