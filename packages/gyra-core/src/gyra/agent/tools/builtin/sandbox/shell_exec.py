"""
ShellExecTool - 沙箱内 Shell 命令执行工具

在沙箱工作空间中执行受限 Bash 命令
"""

from typing import Dict, Any, Optional
import re
import logging

from .base import SandboxToolBase
from ...base import ToolCategory, ToolRiskLevel, ToolEnvironment, ToolSource
from ...metadata import ToolMetadata
from ...context import ToolContext
from ...result import ToolResult
from gyra.sandbox.sandbox_utils import (
    validate_shell_command,
    collect_shell_output,
    is_high_risk_command,
    get_sandbox_whitelist,
)

logger = logging.getLogger(__name__)

# 默认超时时间
_DEFAULT_TIMEOUT: int = 60

# 输出限制
_MAX_BYTES = 16 * 1024  # 16KB
_MAX_LINES_DEFAULT = 500
_MAX_LINES_FILE_CHUNK = 500

# ANSI 转义序列正则
_ANSI_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


_PROMPT = """在沙箱工作空间中执行单条 Bash 命令。该工具属于执行层，同一轮回复内仅允许调用一次（一次回复只能使用一次 shell_exec），且不与依赖其结果的其他操作并发调用；若命令会写入状态，请在确认命令成功后，再发起后续读取/写入。

使用指南:
- 【最高优先级】同一轮回复内仅允许调用一次该工具（shell_exec），严禁并发或重复调用。
- 工作目录为沙箱工作空间根目录；优先使用相对路径（从工作空间根目录开始），或使用 pwd 命令确认当前工作目录。
- 沙箱已配置 sudo 免密，但避免任何交互式确认；对可能需要确认的命令加上 -y/-f 等非交互标志。
- 输出限制：最多 10KB 或 256 行，超出部分会被截断；大量输出请重定向到文件或通过管道进行过滤。
- 可以用 '&&' 串联子命令来减少多次调用并清晰处理错误；适当使用管道 '|' 在命令间传递输出。
- 可使用 python3 -c / bash -c 执行代码片段；复杂脚本建议先写入文件再执行，便于排查输出。
- 本地沙箱下高危命令（rm -rf、dd、mkfs、写块设备等）执行前需用户授权确认；远程沙箱无限制。
- 对长时间运行的服务（如 Web 服务器）必须设置5s超时并且后台运行，避免无意义等待。
- 禁止访问工作空间之外的路径（特别是 ~、.. 或绝对路径越界）。"""


def _strip_ansi_sequences(text: str) -> str:
    """Remove ANSI escape sequences from shell output."""
    if not text:
        return text
    cleaned = _ANSI_PATTERN.sub("", text)
    cleaned = cleaned.replace("\x1b", "")
    cleaned = cleaned.replace("\r", "")
    return cleaned


def _truncate_text(text: str, line_cap: int, byte_cap: int) -> str:
    """Truncate text by lines then by bytes."""
    if not text:
        return text
    lines = text.splitlines(True)
    if len(lines) > line_cap:
        lines = lines[:line_cap]
        text = "".join(lines)
    else:
        text = "".join(lines)
    b = text.encode("utf-8", errors="replace")
    if len(b) <= byte_cap:
        return text
    truncated = b[:byte_cap]
    try:
        safe = truncated.decode("utf-8", errors="ignore")
    except Exception:
        safe = text[:0]
    return safe


def _is_file_read_command(command: str) -> bool:
    """Heuristically decide if command is likely printing file content."""
    from gyra.sandbox.sandbox_utils import _tokenize_command

    try:
        tokens = _tokenize_command(command)
    except ValueError:
        return False

    # Only inspect the first subcommand before any separator.
    for sep in ("&&", "||", "|"):
        if sep in tokens:
            tokens = tokens[: tokens.index(sep)]
            break

    if not tokens:
        return False
    binary = tokens[0]
    if binary in {"cat", "nl", "head", "tail", "grep", "rg", "sed"}:
        return True
    return False


def _format_shell_exec_response(
    command: str, exit_code: Optional[int], stdout: str, stderr: str
) -> str:
    """Format shell output for display."""
    code_repr = "unknown" if exit_code is None else str(exit_code)
    if exit_code is None:
        status = "⚠️ 未知"
    elif exit_code == 0:
        status = "✅ 成功"
    else:
        status = "⚠️ 失败"

    lines = [f"命令: {command}", f"结果: {status} (退出码 {code_repr})"]

    if stdout:
        lines.extend(["", "📤 标准输出:", stdout.rstrip("\n")])
    if stderr:
        lines.extend(["", "⚠️ 标准错误:", stderr.rstrip("\n")])

    return "\n".join(lines).rstrip()


def _resolve_sandbox_type() -> str:
    """读取 sandbox.type 配置，默认 'local'。远程沙箱不校验命令。"""
    try:
        from gyra._private.config import Config as GyraConfig

        system_app = GyraConfig().SYSTEM_APP
        if system_app:
            app_config = system_app.config.configs.get("app_config")
            if app_config and hasattr(app_config, "sandbox"):
                return getattr(app_config.sandbox, "type", None) or "local"
    except Exception:
        logger.debug(
            "[shell_exec] failed to read sandbox.type, defaulting to local",
            exc_info=True,
        )
    return "local"


class ShellExecTool(SandboxToolBase):
    """沙箱内 Shell 命令执行工具"""

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="shell_exec",
            display_name="Shell Exec",
            description=_PROMPT,
            category=ToolCategory.SANDBOX,
            risk_level=ToolRiskLevel.MEDIUM,
            source=ToolSource.SYSTEM,
            requires_permission=False,
            timeout=120,
            environment=ToolEnvironment.SANDBOX,
            tags=["shell", "command", "execute", "sandbox"],
            author="tuyang.yhj",
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Bash 命令（单条）。若包含多步操作，请使用 '&&' 串联；避免交互式命令。",
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 10,
                    "description": "超时秒数（正整数）。默认 10；命令若可能长时间运行，请适当上调或后台执行。",
                },
            },
            "required": ["command"],
        }

    async def _request_high_risk_approval(self, command: str) -> bool:
        """请求高危命令执行授权（local 沙箱）。无网关 / 拒绝 / 超时返回 False。"""
        try:
            from gyra.agent.tools.authorization_middleware import (
                request_command_approval,
            )
            from gyra.agent.interaction.interaction_gateway import (
                get_interaction_gateway,
            )
        except Exception as exc:
            logger.warning(f"[shell_exec] auth module import failed: {exc}")
            return False
        gateway = get_interaction_gateway()
        return await request_command_approval(gateway, command, "高危命令执行确认")

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        command = args["command"]
        timeout = args.get("timeout", _DEFAULT_TIMEOUT)

        # 检查沙箱可用性
        client = self._get_sandbox_client(context)
        if client is None:
            return ToolResult.fail(
                error="错误: 当前任务未初始化沙箱环境，无法执行命令",
                tool_name=self.name,
            )

        if timeout <= 0:
            return ToolResult.fail(
                error="timeout 必须为正整数",
                tool_name=self.name,
            )

        sandbox_type = _resolve_sandbox_type()
        try:
            # 与 LocalShellClient 保持一致:路径栅栏额外放行 skill_dir 与 /mnt,
            # 避免把 skill 目录内的正常命令误判为越界。
            allowed_roots = list(
                get_sandbox_whitelist(getattr(client, "skill_dir", None))
            )
            # 命令默认在会话目录(session_work_dir)执行,同名文件不再跨会话覆盖;
            # 空间公共层(work_dir)同样放行进 allowed_roots,这样用绝对路径读
            # files/ 下的公共数据集不会被路径栅栏拦下。
            # 注意:命令参数中的 ".." 本来就一律禁止(见 _validate_tokens),
            # 因此访问公共层只能走绝对路径,promote 共享文件同理。
            from gyra.sandbox.sandbox_utils import resolve_session_work_dir

            work_dir = resolve_session_work_dir(client)
            if work_dir != client.work_dir:
                allowed_roots.append(client.work_dir)
            validate_shell_command(
                command,
                work_dir,
                sandbox_type,
                allowed_roots=allowed_roots,
            )
        except (ValueError, PermissionError) as e:
            return ToolResult.fail(error=str(e), tool_name=self.name)

        # local 沙箱下高危命令需用户交互授权；远程沙箱无限制
        if sandbox_type == "local" and is_high_risk_command(command):
            approved = await self._request_high_risk_approval(command)
            if not approved:
                return ToolResult.fail(
                    error=f"用户未授权执行高危命令: {command}",
                    tool_name=self.name,
                )

        try:
            result = await client.shell.exec_command(
                command=command, timeout=float(timeout), work_dir=work_dir
            )
        except Exception as exc:
            return ToolResult.ok(
                output=_format_shell_exec_response(
                    command, -1, "", f"命令执行失败: {exc}"
                ),
                tool_name=self.name,
            )

        # 获取输出
        stdout = collect_shell_output(result)
        stdout = _strip_ansi_sequences(stdout)
        line_cap = (
            _MAX_LINES_FILE_CHUNK
            if _is_file_read_command(command)
            else _MAX_LINES_DEFAULT
        )
        stdout = _truncate_text(stdout, line_cap, _MAX_BYTES)

        status = getattr(result, "status", None)
        exit_code = getattr(result, "exit_code", None)

        if status != "completed":
            output = _format_shell_exec_response(
                command,
                exit_code if exit_code is not None else -1,
                "",
                stdout or f"命令执行失败，状态: {status}",
            )
            return ToolResult.ok(output=output, tool_name=self.name)

        output = _format_shell_exec_response(
            command, exit_code if exit_code is not None else 0, stdout, ""
        )
        return ToolResult.ok(output=output, tool_name=self.name)
