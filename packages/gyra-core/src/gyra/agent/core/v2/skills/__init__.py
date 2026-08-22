"""V2 Skill 模块——对齐 DeepSeek Harness 的 skill 能力族。

导出：
  - :class:`SkillRegistry`（harness 总线 ``ctx.skills``）
  - :class:`SkillProvider` / :class:`SkillDefinition` / :class:`SkillSummary` / :class:`SkillInvocation`
  - :class:`SkillCatalogConsumer`（目录 digest 变化时注入 user-role reminder）
  - :class:`FilesystemSkillProvider`（本地 / 沙箱 skill 目录 provider 实现）
  - :class:`SkillTool`（统一 ``skill({name})`` 工具，合并 list/read）

设计依据：[DSH skills.md](../../../../../../../../docs/subsystems/skills.md) +
[DSH skills.zh.md](../../../../../../../../docs/subsystems/skills.zh.md)。
"""
from gyra.agent.core.v2.skills.registry import (
    SkillDefinition,
    SkillInvocation,
    SkillLookupOptions,
    SkillProvider,
    SkillRegistry,
    SkillSummary,
    LAYER_HOST,
    LAYER_SCOPE,
)
from gyra.agent.core.v2.skills.catalog_consumer import (
    SkillCatalogConsumer,
    build_initial_reminder,
    build_replacement_reminder,
)
from gyra.agent.core.v2.skills.filesystem_provider import (
    FilesystemSkillProvider,
)
from gyra.agent.core.v2.skills.skill_tool import SkillTool, SKILL_TOOL_NAME

__all__ = [
    "SkillDefinition",
    "SkillInvocation",
    "SkillLookupOptions",
    "SkillProvider",
    "SkillRegistry",
    "SkillSummary",
    "LAYER_HOST",
    "LAYER_SCOPE",
    "SkillCatalogConsumer",
    "build_initial_reminder",
    "build_replacement_reminder",
    "FilesystemSkillProvider",
    "SkillTool",
    "SKILL_TOOL_NAME",
]
