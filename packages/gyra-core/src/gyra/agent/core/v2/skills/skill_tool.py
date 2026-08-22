"""SkillTool——统一 ``skill`` 工具（对齐 DSH dsh-tool-skill，V1/V2 公用）。

把 V1 分散的三个工具 ``skill_list`` / ``read_skill`` (``Skill``) / ``skill_exec``
合并为一个面向模型的入口：

  - 输入：``{ "name": "kebab-case-name" }``（``skill_name`` 为别名）
  - V2（有 registry）：从 :class:`SkillRegistry` 加载完整定义。
  - V1（无 registry）：委托 ``ReadSkillTool`` 走磁盘/沙箱读取，保留既有分页
    与沙箱能力。
  - 不存在 / 不可调用：返回明确错误（unknown or no longer available）。
  - 校验：name 必须 kebab-case（V2 模式）；调用前查 ``is_model_invocable``。

输出格式（官方 Agent Skills 范式）：

    LLM 视角（ToolResult.output）：
    <skill_content name="...">
    {SKILL.md 正文（去掉 YAML frontmatter）}

    <file_preview>
    base_path: /abs/path/to/skill-dir
      SKILL.md (16.7K)
      references/db_analysis_guide.md (3.2K)
      ...
    </file_preview>
    </skill_content>

  - ``<skill_content>``：LLM 视角——SKILL.md 正文 + ``<file_preview>`` 文件
    清单，name 以标签属性携带（发现阶段已有 name/description，激活阶段不再重复）；
  - 完整 frontmatter 走 ``ToolResult.metadata["skill_meta"]``（工具 view 通道），
    由 action/vis 链路转为 ``<d-skill-meta>`` VIS 标签送给前端，渲染为可视化
    头部组件（name/description/author/version/扩展字段），**不进 LLM 上下文**；
  - ``<file_preview>`` 列出 skill 目录下可用文件（相对路径 + 大小），
    提示模型有哪些资源依赖可用，避免臆造不存在的文件名；
  - 前端独立渲染器解析该 XML：头部组件 + 内容区 + 文件预览。

V1 兼容：
  - 本工具是唯一注册的 ``skill`` 入口（``skill_list`` / ``skill_exec`` 已废弃删除）；
  - 无 registry 时委托 V1 ``ReadSkillTool``（磁盘/沙箱读取）；读取 SKILL.md 时
    同样包裹为上述标准格式，读其它文件（file_path 指定）保持原文返回。
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


# file_preview 文件列表条目上限（超出截断并注明）
_MAX_PREVIEW_FILES = 100


def _human_size(num_bytes: int) -> str:
    """人类可读大小：B 取整、K/M/G 保留 1 位小数（如 4.2K）。"""
    size = float(num_bytes)
    for unit in ("B", "K", "M", "G"):
        if size < 1024 or unit == "G":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}G"


def _build_file_preview(skill_dir: Optional[str]) -> str:
    """枚举 skill 目录文件，构造 ``<file_preview>`` 内容（不含标签本身）。

    本地目录可访问时列相对路径 + 大小（跳过隐藏目录/文件与 ``__pycache__``）；
    不可访问（沙箱等）时只含 base_path 一行。skill_dir 为空返回空串。
    """
    if not skill_dir:
        return ""
    import os
    from pathlib import Path

    lines = [f"base_path: {skill_dir}"]
    root = Path(skill_dir)
    if not root.is_dir():
        return "\n".join(lines)
    entries: List[str] = []
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if not d.startswith(".") and d != "__pycache__"
            ]
            for fn in sorted(filenames):
                if fn.startswith("."):
                    continue
                full = Path(dirpath) / fn
                total += 1
                if total > _MAX_PREVIEW_FILES:
                    continue
                rel = full.relative_to(root).as_posix()
                try:
                    size = _human_size(full.stat().st_size)
                except OSError:
                    size = ""
                entries.append(f"  {rel} ({size})" if size else f"  {rel}")
    except OSError:
        return "\n".join(lines)
    lines.extend(sorted(entries))
    if total > _MAX_PREVIEW_FILES:
        lines.append(f"  ... (truncated, {total} files total)")
    return "\n".join(lines)


def _render_skill_content_xml(
    name: str,
    body: str,
    file_preview: str = "",
) -> str:
    """构造官方 Agent Skills 范式的 ``<skill_content>`` 段（纯 LLM 视角）。

    只含 SKILL.md 正文（去 YAML 头）+ ``<file_preview>`` 文件清单（含
    base_path 绝对路径，提示模型资源依赖）。完整 frontmatter 走
    ``ToolResult.metadata["skill_meta"]``（工具 view 通道，用户视角可视化），
    不进 LLM 输出。
    """
    body = body or ""
    # 防御：截断超大正文（与 V1 ReadSkillTool _MAX_SKILL_CHARS 对齐 100K）
    if len(body) > 100_000:
        body = body[:99_999] + "\n…[truncated]"
    parts = [f'<skill_content name="{_xml_escape(name)}">', body]
    if file_preview:
        parts.append(f"<file_preview>\n{file_preview}\n</file_preview>")
    parts.append("</skill_content>")
    return "\n".join(parts)


def _skill_meta_view(meta_block: str) -> str:
    """把 frontmatter 原始块包装成 ``<d-skill-meta>`` VIS 标签（用户视角 view）。"""
    if not meta_block:
        return ""
    return f"<d-skill-meta>\n{meta_block}\n</d-skill-meta>"


def _skill_dir_of(defn: SkillDefinition) -> Optional[str]:
    """从 SkillDefinition 推导出 skill 目录路径。

    优先 metadata.skill_dir（本地 provider 会写入）；其次 path 为 SKILL.md
    文件路径时取 dirname；否则按目录路径原样返回。
    """
    meta_dir = (defn.metadata or {}).get("skill_dir")
    if meta_dir:
        return str(meta_dir)
    path = defn.path or ""
    if not path:
        return None
    if path.rstrip("/").endswith("SKILL.md"):
        return path.rsplit("/", 1)[0]
    return path


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

        file_preview = _build_file_preview(_skill_dir_of(defn))
        xml = _render_skill_content_xml(
            name=defn.name,
            body=body,
            file_preview=file_preview,
        )
        return ToolResult.ok(
            output=xml,
            tool_name=self.name,
            metadata={
                "skill_name": defn.name,
                "skill_description": defn.description or "",
                "skill_path": defn.path or "",
                "skill_dir": _skill_dir_of(defn) or "",
                # 完整 frontmatter（工具 view 通道，用户视角；不进 LLM 输出）
                "skill_meta": str((defn.metadata or {}).get("frontmatter_raw") or ""),
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
        result = await reader.execute(
            {
                "skill_name": skill_name,
                "file_path": file_path,
                "offset": offset,
                "limit": limit,
            },
            context,
        )
        # 仅 SKILL.md 正文包裹为官方标准 <skill_content> 格式；读其它文件
        # （references/scripts/templates 等）保持原文返回。
        if file_path != "SKILL.md" or not result.success:
            return result
        return self._wrap_v1_skill_md(skill_name, offset, result)

    def _wrap_v1_skill_md(
        self, skill_name: str, offset: int, result: ToolResult,
    ) -> ToolResult:
        """把 V1 读取的裸 SKILL.md 内容包裹为标准 ``<skill_content>`` XML。

        - 第 1 页（offset==1）strip YAML frontmatter，正文为指令本体；
        - name / description 从 frontmatter 解析，以标签属性携带；
        - file_preview 列 skill 目录文件（base_path + 相对路径 + 大小）。
        """
        from gyra.agent.core.v2.skills.filesystem_provider import (
            _parse_frontmatter,
            _raw_frontmatter,
            _strip_frontmatter,
        )

        raw = result.output if isinstance(result.output, str) else str(result.output or "")
        meta_in = result.metadata or {}
        abs_path = str(meta_in.get("file_path") or "")
        skill_dir = abs_path.rsplit("/", 1)[0] if abs_path.endswith("SKILL.md") else ""

        if offset > 1:
            # 分页续读：正文已经是去头后的中间段，不再重复 strip
            body = raw
            fm = {}
            meta_block = ""
        else:
            fm = _parse_frontmatter(raw)
            meta_block = _raw_frontmatter(raw)
            body = _strip_frontmatter(raw).strip("\n")

        file_preview = _build_file_preview(skill_dir)
        xml = _render_skill_content_xml(
            name=fm.get("name") or skill_name,
            body=body,
            file_preview=file_preview,
        )
        return ToolResult.ok(
            output=xml,
            tool_name=self.name,
            metadata={
                **meta_in,
                "skill_name": fm.get("name") or skill_name,
                "skill_description": fm.get("description", ""),
                "skill_dir": skill_dir,
                # 完整 frontmatter（工具 view 通道，用户视角；不进 LLM 输出）
                "skill_meta": meta_block,
            },
        )
