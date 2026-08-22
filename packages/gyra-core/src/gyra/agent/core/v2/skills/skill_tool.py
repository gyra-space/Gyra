"""SkillTool——统一 ``skill`` 工具（对齐 DSH dsh-tool-skill，V1/V2 公用）。

把 V1 分散的三个工具 ``skill_list`` / ``read_skill`` (``Skill``) / ``skill_exec``
合并为一个面向模型的入口：

  - 输入：``{ "name": "kebab-case-name" }``（``skill_name`` 为别名）
  - V2（有 registry）：从 :class:`SkillRegistry` 加载完整定义；返回
    ``<skill_content name="...">`` + ``<skill_resources>`` + ``<skill_instructions>``
    的 XML 段。
  - V1（无 registry）：委托 ``ReadSkillTool`` 走磁盘/沙箱读取，保留既有分页
    与沙箱能力。
  - 不存在 / 不可调用：返回明确错误（unknown or no longer available）。
  - 校验：name 必须 kebab-case（V2 模式）；调用前查 ``is_model_invocable``。

设计依据：[DSH skills.zh.md:234]（"返回包含 <skill_content name="...">、
<skill_resources>、<skill_instructions> 的工具结果"）。

V1 兼容：
  - 本工具是唯一注册的 ``skill`` 入口（``skill_list`` / ``skill_exec`` 已废弃删除）；
  - 无 registry 时委托 V1 ``ReadSkillTool``（磁盘/沙箱读取），前端 / V1 行为不变。
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from gyra.agent.core.v2.skills.registry import (
    SkillDefinition,
    SkillInvocation,
    SkillRegistry,
)
from gyra.agent.tools.base import ToolBase, ToolCategory, ToolRiskLevel
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.metadata import ToolMetadata
from gyra.agent.tools.result import ToolResult

logger = logging.getLogger(__name__)


# kebab-case：DSH ``^[a-z0-9]+(?:-[a-z0-9]+)*$``
_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


SKILL_TOOL_NAME = "skill"
SKILL_TOOL_DESCRIPTION = (
    "Load the full instructions for a named skill.\n\n"
    "Use this tool when the current task matches a skill listed in the available "
    "skills reminder. Returns the complete skill instructions in a single call. "
    "After loading, follow the skill's guidance immediately.\n\n"
    "Args:\n"
    "  - name: kebab-case skill identifier (matches the directory name on disk).\n"
    "  - file_path: optional relative path within the skill directory "
    "(default 'SKILL.md').\n"
    "  - offset / limit: optional line-based pagination for large files.\n\n"
    "If the skill name is unknown, no longer available, or restricted to "
    "non-model invocation, the tool reports a clear error."
)


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace("\"", "&quot;")
    )


def _is_model_invocable(inv: SkillInvocation) -> bool:
    return inv in (SkillInvocation.MODEL_ONLY, SkillInvocation.BOTH)


def _render_skill_content_xml(defn: SkillDefinition) -> str:
    """构造 DSH 风格的 ``<skill_content>`` 段。"""
    body = defn.content or ""
    # 防御：截断超大正文（与 V1 ReadSkillTool _MAX_SKILL_CHARS 对齐 100K）
    if len(body) > 100_000:
        body = body[:99_999] + "\n…[truncated]"
    return (
        f"<skill_content name=\"{_xml_escape(defn.name)}\">\n"
        f"<skill_instructions>\n{body}\n</skill_instructions>\n"
        f"<skill_resources>\n  base_path: {_xml_escape(defn.path or '')}\n"
        f"  source: {_xml_escape(defn.source)}\n"
        f"  provider: {_xml_escape(defn.provider)}\n"
        f"</skill_resources>\n"
        f"</skill_content>"
    )


class SkillTool(ToolBase):
    """对齐 DSH 的 ``skill({ name })`` 工具 —— V1/V2 公用的唯一 skill 入口。

    Args:
        registry: 可选的 :class:`SkillRegistry` 实例（建议从 harness.skills 取，
            V2 模式传入）。为 ``None`` 时退化为 V1 磁盘/沙箱读取（委托
            ``ReadSkillTool``），保证 V1 链路的 offset/limit 分页、沙箱读取等
            既有能力不变。两种模式都对外暴露同名 ``skill`` 工具。
        layer_chain: registry 读取时的 layer 链（``["scope", "host"]``）。
        cwd: registry 读取时的 cwd 上下文。
    """

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        *,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ):
        super().__init__()
        self._registry = registry
        self._layer_chain = layer_chain or ["scope", "host"]
        self._cwd = cwd

    # ------------------------------------------------------------------ #
    # ToolBase
    # ------------------------------------------------------------------ #

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=SKILL_TOOL_NAME,
            display_name="Skill",
            description=SKILL_TOOL_DESCRIPTION,
            category=ToolCategory.SKILL,
            risk_level=ToolRiskLevel.LOW,
            requires_permission=False,
            timeout=60,
            tags=["skill", "read", "knowledge", "v2", "dsh-style"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Kebab-case skill name (must match ^[a-z0-9]+(?:-[a-z0-9]+)*$).",
                },
                "skill_name": {
                    "type": "string",
                    "description": "Alias of ``name``. Either ``name`` or ``skill_name`` must be given.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional relative path within the skill directory (default 'SKILL.md').",
                    "default": "SKILL.md",
                },
                "offset": {
                    "type": "integer",
                    "description": "1-based starting line number for pagination (default 1).",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Max lines to return (0 = no limit, default 0).",
                    "default": 0,
                },
            },
            "required": ["name"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None,
    ) -> ToolResult:
        name = (args.get("name") or args.get("skill_name") or "").strip()
        file_path = args.get("file_path", "SKILL.md") or "SKILL.md"
        offset = int(args.get("offset", 1) or 1)
        limit = int(args.get("limit", 0) or 0)

        if not name:
            return ToolResult.fail(
                error="name (or skill_name) is required",
                tool_name=self.name,
            )

        # V1 无 registry：退化为磁盘/沙箱读取（委托 ReadSkillTool，保留
        # offset/limit 分页与沙箱读取能力）。
        if self._registry is None:
            return await self._execute_v1_fallback(
                name, file_path, offset, limit, context,
            )

        if not _KEBAB_RE.match(name):
            return ToolResult.fail(
                error=(
                    f"Invalid skill name {name!r}: must be kebab-case "
                    f"(^[a-z0-9]+(?:-[a-z0-9]+)*$)."
                ),
                tool_name=self.name,
            )
        if ".." in file_path:
            return ToolResult.fail(
                error="file_path cannot contain '..'",
                tool_name=self.name,
            )

        defn = await self._registry.get(
            name, layer_chain=self._layer_chain, cwd=self._cwd,
        )
        if defn is None:
            return ToolResult.fail(
                error=f"Unknown or no longer available skill: {name!r}",
                tool_name=self.name,
            )
        if not _is_model_invocable(defn.invocation):
            return ToolResult.fail(
                error=(
                    f"Skill {name!r} is not model-invocable "
                    f"(invocation={defn.invocation.value})."
                ),
                tool_name=self.name,
            )

        # 当前实现：仅加载 SKILL.md；file_path / offset / limit 暂作参数保留
        # 后续可走沙箱 file.read 扩展。V1 工具链仍负责其它资源读取。
        if file_path != "SKILL.md":
            return ToolResult.fail(
                error=(
                    f"file_path={file_path!r} not supported by V2 skill tool yet; "
                    f"use V1 Skill tool for non-SKILL.md reads."
                ),
                tool_name=self.name,
            )

        # 行分页（offset/limit）
        body = defn.content or ""
        if offset > 1 or limit > 0:
            lines = body.splitlines(keepends=True)
            start_idx = max(0, offset - 1)
            end_idx = (
                min(len(lines), start_idx + limit) if limit > 0 else len(lines)
            )
            body = "".join(lines[start_idx:end_idx])
            # 重新构造 SkillDefinition 子集（content 已被截断）
            defn = SkillDefinition(
                name=defn.name,
                description=defn.description,
                when_to_use=defn.when_to_use,
                invocation=defn.invocation,
                source=defn.source,
                provider=defn.provider,
                path=defn.path,
                rank=defn.rank,
                content=body,
                metadata=defn.metadata,
            )

        xml = _render_skill_content_xml(defn)
        return ToolResult.ok(
            output=xml,
            tool_name=self.name,
            metadata={
                "skill_name": defn.name,
                "skill_path": defn.path or "",
                "source": defn.source,
                "provider": defn.provider,
                "invocation": defn.invocation.value,
            },
        )

    async def _execute_v1_fallback(
        self,
        skill_name: str,
        file_path: str,
        offset: int,
        limit: int,
        context: Optional[ToolContext],
    ) -> ToolResult:
        """V1 无 registry 时委托 ``ReadSkillTool`` 做磁盘/沙箱读取。

        SkillTool 与 ReadSkillTool 的参数不同（``name`` vs ``skill_name``），
        这里做映射后转发，复用 V1 成熟的路径解析 + 分页 + 沙箱读取逻辑。
        """
        try:
            from gyra.agent.tools.builtin.skill.read_skill import ReadSkillTool
        except Exception as e:  # noqa: BLE001
            logger.exception("[SkillTool] V1 ReadSkillTool import failed")
            return ToolResult.fail(
                error=f"V1 disk reader unavailable: {e}",
                tool_name=self.name,
            )
        reader = ReadSkillTool()
        return await reader.execute(
            {
                "skill_name": skill_name,
                "file_path": file_path,
                "offset": offset,
                "limit": limit,
            },
            context,
        )
