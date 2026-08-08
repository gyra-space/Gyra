"""
ReadTool - 统一文件读取工具

支持两种执行环境：
- 有沙箱：通过 sandbox client 读取沙箱文件（支持目录列表、图片base64、交付物标记）
- 无沙箱：通过本地文件系统读取
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

from ..sandbox.base import SandboxToolBase
from ...base import ToolCategory, ToolRiskLevel
from ...metadata import ToolMetadata
from ...context import ToolContext
from ...result import ToolResult

logger = logging.getLogger(__name__)


def _segmented_read_prompt(seg_start: int, seg_end: int, total: int, unit: str) -> str:
    """构建分段读取提示。

    当文件内容超过单次读取上限时，不静默截断，而是提示 Agent 通过
    offset/limit 分段读取完整内容，避免在内容不完整的情况下继续后续操作。
    """
    chunk = max(1, seg_end - seg_start)
    next_offset = seg_end + 1
    return (
        "\n\n> ⚠️ **内容不完整**：文件较大，本次仅展示了第 "
        f"{seg_start}-{seg_end} {unit}（共 {total} {unit}）。\n"
        "> 请继续分段读取获取完整内容，切勿在内容不完整时继续后续操作：\n"
        f"> 继续读取：`Read(path=..., offset={next_offset}, limit={chunk})`"
    )


class ReadTool(SandboxToolBase):
    """统一文件读取工具 - 自动检测执行环境"""

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Read",
            display_name="Read File",
            description=(
                "Read the contents of a file or list a directory. "
                "By default, it returns up to 2000 lines.\n\n"
                "When running in a sandbox environment, additional capabilities are available:\n"
                "- Directory exploration (lists file tree up to 2 levels)\n"
                "- Image preview (returns base64)\n"
                "- Deliverable marking (mark files for delivery with download links)\n"
                "- Line range slicing via view_range parameter"
            ),
            category=ToolCategory.FILE_SYSTEM,
            capability_id="sandbox",
            risk_level=ToolRiskLevel.LOW,
            requires_permission=False,
            timeout=60,
            tags=["file", "read", "file-system", "view"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the file (or directory in sandbox mode) to read",
                },
                "mode": {
                    "type": "string",
                    "enum": ["line", "char"],
                    "default": "line",
                    "description": "Read mode: 'line' for line-based reading, 'char' for character-based reading (useful for single-line large files)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line mode: line number to start (1-based). Char mode: character offset to start (0-based).",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Line mode: max lines to read. Char mode: max characters to read.",
                    "default": 2000,
                },
                "view_range": {
                    "anyOf": [
                        {
                            "maxItems": 2,
                            "minItems": 2,
                            "prefixItems": [{"type": "integer"}, {"type": "integer"}],
                            "type": "array",
                        },
                        {"type": "null"},
                    ],
                    "default": None,
                    "description": "Line range [start, end] (1-based, sandbox mode). Use -1 for end of file.",
                },
                "mark_as_deliverable": {
                    "type": "boolean",
                    "default": False,
                    "description": "Mark this file as a deliverable with download link (sandbox mode only)",
                },
                "delivery_description": {
                    "type": "string",
                    "description": "Description for the deliverable (sandbox mode, when mark_as_deliverable=true)",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        client = self._get_sandbox_client(context)
        if client is not None:
            return await self._execute_sandbox(args, context, client)
        else:
            return await self._execute_local(args, context)

    async def _execute_sandbox(
        self, args: Dict[str, Any], context: Optional[ToolContext], client: Any
    ) -> ToolResult:
        """Delegate to sandbox ViewTool logic, with char mode support"""
        mode = args.get("mode", "line")

        if mode == "char":
            return await self._execute_sandbox_char_mode(args, context, client)

        from ..sandbox.view import ViewTool

        view_tool = ViewTool()
        sandbox_args = {
            "path": args["path"],
            "mark_as_deliverable": args.get("mark_as_deliverable", False),
            "delivery_description": args.get("delivery_description", ""),
        }

        view_range = args.get("view_range")
        if view_range is not None:
            sandbox_args["view_range"] = view_range
        elif args.get("offset", 1) != 1 or args.get("limit", 2000) != 2000:
            offset = args.get("offset", 1)
            limit = args.get("limit", 2000)
            sandbox_args["view_range"] = [offset, offset + limit - 1]

        return await view_tool.execute(sandbox_args, context)

    async def _execute_sandbox_char_mode(
        self, args: Dict[str, Any], context: Optional[ToolContext], client: Any
    ) -> ToolResult:
        """Character-based reading in sandbox mode"""
        from ..sandbox.view import _read_text_content

        path = args["path"]
        offset = args.get("offset", 0)
        limit = args.get("limit", 2000)

        from gyra.sandbox.sandbox_utils import (
            normalize_sandbox_path,
            detect_path_kind,
        )

        try:
            sandbox_path = normalize_sandbox_path(client, path)
        except ValueError as exc:
            return ToolResult.fail(error=f"错误: {exc}", tool_name=self.name)

        path_kind = await detect_path_kind(client, sandbox_path)
        if path_kind == "none":
            return ToolResult.fail(
                error=f"错误: 路径不存在: {sandbox_path}", tool_name=self.name
            )
        if path_kind == "dir":
            return ToolResult.fail(
                error=f"错误: 字符模式不支持目录，请使用行模式", tool_name=self.name
            )

        content = await _read_text_content(client, sandbox_path)
        if content.startswith("[错误:"):
            return ToolResult.fail(error=content, tool_name=self.name)

        total_chars = len(content)
        selected = content[offset : offset + limit]
        has_more = offset + limit < total_chars
        total_lines = len(content.splitlines())

        result_lines = [
            f"{i}: {line}"
            for i, line in enumerate(selected.splitlines(keepends=True), start=1)
        ]
        result = "".join(result_lines)

        if has_more:
            result += _segmented_read_prompt(
                seg_start=offset,
                seg_end=offset + limit,
                total=total_chars,
                unit="字符",
            )

        return ToolResult.ok(
            output=result,
            tool_name=self.name,
            metadata={
                "path": sandbox_path,
                "mode": "char",
                "char_offset": offset,
                "char_limit": limit,
                "chars_read": len(selected),
                "total_chars": total_chars,
                "total_lines": total_lines,
                "truncated": has_more,
            },
        )

    async def _execute_local(
        self, args: Dict[str, Any], context: Optional[ToolContext]
    ) -> ToolResult:
        """Execute locally using pathlib"""
        path = args["path"]
        mode = args.get("mode", "line")

        if context and context.working_directory:
            file_path = Path(context.working_directory) / path
        else:
            file_path = Path(path)

        if not file_path.exists():
            return ToolResult.fail(
                error=f"File does not exist: {path}",
                tool_name=self.name,
                error_code="FILE_NOT_FOUND",
            )

        if not file_path.is_file():
            return ToolResult.fail(
                error=f"Path is not a file: {path}",
                tool_name=self.name,
                error_code="NOT_A_FILE",
            )

        try:
            if mode == "char":
                return await self._read_char_mode(args, file_path)
            else:
                return await self._read_line_mode(args, file_path)
        except Exception as e:
            logger.error(f"[ReadTool] Failed: {e}")
            return ToolResult.fail(error=str(e), tool_name=self.name)

    async def _read_line_mode(
        self, args: Dict[str, Any], file_path: Path
    ) -> ToolResult:
        """Line-based reading mode"""
        offset = args.get("offset", 1)
        limit = args.get("limit", 2000)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)
        start_idx = max(0, offset - 1)
        end_idx = min(start_idx + limit, total_lines)
        selected = all_lines[start_idx:end_idx]

        content = "\n".join(
            f"{i}: {line.rstrip()}"
            for i, line in enumerate(selected, start=start_idx + 1)
        )

        truncated = end_idx < total_lines
        if truncated:
            content += _segmented_read_prompt(
                seg_start=offset,
                seg_end=end_idx,
                total=total_lines,
                unit="行",
            )

        return ToolResult.ok(
            output=content,
            tool_name=self.name,
            metadata={
                "path": str(file_path),
                "mode": "line",
                "lines_read": len(selected),
                "file_size": file_path.stat().st_size,
                "total_lines": total_lines,
                "truncated": truncated,
            },
        )


async def _read_char_mode(self, args: Dict[str, Any], file_path: Path) -> ToolResult:
    """Character-based reading mode - safe for multi-byte characters (Chinese, etc.)"""
    offset = args.get("offset", 1)
    limit = args.get("limit", 2000)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        total_chars = len(content)
        selected = content[offset : offset + limit]

    result = selected
    has_more = offset + limit < total_chars
    if has_more:
        result += _segmented_read_prompt(
            seg_start=offset,
            seg_end=offset + limit,
            total=total_chars,
            unit="字符",
        )

    return ToolResult.ok(
        output=result,
        tool_name=self.name,
        metadata={
            "path": str(file_path),
            "mode": "char",
            "char_offset": offset,
            "char_limit": limit,
            "chars_read": len(selected),
            "total_chars": total_chars,
            "file_size": file_path.stat().st_size,
            "truncated": has_more,
        },
    )
