"""Utility helpers for executing operations inside the sandbox client."""

from __future__ import annotations

import posixpath
import re
import shlex
from typing import List, Optional, TYPE_CHECKING, Set


# ---------------------------------------------------------------------------
# Shell command validation
# ---------------------------------------------------------------------------

# 允许的命令白名单
_ALLOWED_COMMANDS = {
    "cat",
    "ls",
    "pwd",
    "echo",
    "head",
    "tail",
    "wc",
    "which",
    "nl",
    "grep",
    "find",
    "rg",
    "git",
    "sed",
    "pip3",
    "python3",
}

# 禁止的符号
_FORBIDDEN_SYMBOLS = {""}

# find 命令禁止的参数
_FIND_FORBIDDEN_ARGS = {
    "-delete",
    "-exec",
    "-execdir",
    "-fls",
    "-fprint",
    "-fprint0",
    "-fprintf",
    "-ok",
    "-okdir",
}
_FIND_FORBIDDEN_PREFIXES = ("-exec", "-ok")

# ripgrep 禁止的选项
_RG_FORBIDDEN_ARGS = {
    "--search-zip",
    "--pre",
    "--pre-glob",
    "--hostname-bin",
}

# Git 允许的子命令（只读）
_GIT_ALLOWED_SUBCMDS = {"status", "log", "diff", "show", "branch"}
_GIT_FORBIDDEN_ARGS = {
    "-d",
    "-D",
    "-m",
    "-M",
    "--delete",
    "--move",
    "--rename",
    "--force",
    "-f",
}

# 危险 shell 元字符：允许 && || | 作为子命令/管道分隔符，其余禁止
_DANGEROUS_METACHAR_RE = re.compile(r"[;`$\(\)\{\}<>]|\$\(")


def _tokenize_command(command: str) -> List[str]:
    """Split the shell command into arguments."""
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"命令解析失败: {exc}") from exc
    if not tokens:
        raise ValueError("command 不能为空")
    return tokens


def _validate_tokens(tokens: List[str], sandbox_work_dir: str) -> None:
    """Ensure the command and its arguments stay within the read-only constraints."""
    binary = tokens[0]
    idx = 1

    while idx < len(tokens):
        token = tokens[idx]
        if token in _FORBIDDEN_SYMBOLS:
            raise PermissionError(
                "命令包含被禁止的符号或重定向，请拆分成单独的只读命令执行"
            )

        if binary == "find":
            if token in _FIND_FORBIDDEN_ARGS or token.startswith(
                _FIND_FORBIDDEN_PREFIXES
            ):
                raise PermissionError(
                    "find 命令禁止使用 -exec/-ok/-delete 等执行或写入参数"
                )

        if binary == "rg":
            if token in _RG_FORBIDDEN_ARGS:
                raise PermissionError(
                    "rg 禁止使用 --search-zip/--pre 等可能执行外部命令或扩大搜索面的参数"
                )

        if binary == "git":
            if idx == 1:
                sub = token
                if sub not in _GIT_ALLOWED_SUBCMDS:
                    allowed_sub = ", ".join(sorted(_GIT_ALLOWED_SUBCMDS))
                    raise PermissionError(f"git 仅允许只读子命令: {allowed_sub}")
            if token in _GIT_FORBIDDEN_ARGS:
                raise PermissionError(
                    "git 命令包含危险选项（删除/重命名/强制），已禁止"
                )

        if token.startswith("-"):
            idx += 1
            continue

        if token.startswith("~"):
            raise PermissionError("禁止访问 home 目录")

        if any(part == ".." for part in token.split("/")):
            raise PermissionError("命令参数尝试跳出工作空间目录，已被禁止")

        if token.startswith("/"):
            combined = token
        else:
            combined = posixpath.join(sandbox_work_dir, token)
        normalized = posixpath.normpath(combined)
        base_norm = posixpath.normpath(sandbox_work_dir.rstrip("/")) or "/"
        prefix = "" if base_norm == "/" else f"{base_norm}/"
        if normalized != base_norm and not normalized.startswith(prefix):
            raise PermissionError("命令参数解析后超出了沙箱工作目录，已被禁止")

        idx += 1

    if binary == "sed":
        if len(tokens) != 4:
            raise PermissionError("仅允许只读 sed：`sed -n {N|M,N}p FILE` 格式")
        if tokens[1] != "-n":
            raise PermissionError("sed 仅允许使用 -n，打印指定行范围")
        expr = tokens[2]
        if not re.fullmatch(r"\d+p|\d+,\d+p", expr):
            raise PermissionError("sed 仅允许 {N|M,N}p 的打印表达式")


def _check_binary_and_injection(binary: str, tokens: List[str]) -> None:
    """Block disallowed binaries and code-injection patterns like python -c / bash -c."""
    if binary not in _ALLOWED_COMMANDS:
        allowed = ", ".join(sorted(_ALLOWED_COMMANDS))
        raise PermissionError(f"命令 {binary} 不在允许列表中，允许: {allowed}")

    if binary in ("python3", "python") and len(tokens) >= 2:
        if tokens[1] in ("-c", "-m"):
            raise PermissionError("禁止通过 python -c / python -m 执行代码")

    if binary in ("bash", "sh", "zsh") and len(tokens) >= 2:
        if tokens[1] == "-c":
            raise PermissionError("禁止通过 shell -c 执行代码")


def validate_shell_command(command: str, sandbox_work_dir: str) -> None:
    """
    Validate a shell command for sandbox execution.

    Splits the command on ``&&`` / ``||`` / ``|`` and validates each subcommand:
    - binary must be in the allowlist
    - blocks shell metacharacters (``, $, ;, <, >, braces, etc.)
    - blocks code-injection patterns (python -c, bash -c)
    - arguments must stay inside *sandbox_work_dir*

    Raises:
        ValueError: on parse error or empty command
        PermissionError: on policy violation
    """
    if not command or not command.strip():
        raise ValueError("command 不能为空")

    # Block dangerous metacharacters in the raw command string.
    if _DANGEROUS_METACHAR_RE.search(command) or "\n" in command:
        raise PermissionError(
            "命令包含危险 shell 元字符（; ` $ ( ) { } < > 等），已被禁止"
        )

    tokens = _tokenize_command(command)
    subcommand: List[str] = []

    def _flush() -> None:
        if not subcommand:
            return
        _check_binary_and_injection(subcommand[0], subcommand)
        _validate_tokens(subcommand, sandbox_work_dir)
        subcommand.clear()

    for token in tokens:
        if token in ("&&", "||", "|"):
            _flush()
        else:
            subcommand.append(token)
    _flush()


# ---------------------------------------------------------------------------
# Sandbox path helpers
# ---------------------------------------------------------------------------


def get_sandbox_whitelist(skill_dir: Optional[str] = None) -> Set[str]:
    """
    Get the sandbox whitelist paths.

    Args:
        skill_dir: The skill directory path. If None, uses default.

    Returns:
        Set of allowed paths.
    """
    from gyra.sandbox.base import DEFAULT_SKILL_DIR

    whitelist = {"/mnt"}
    if skill_dir:
        whitelist.add(skill_dir)
    elif DEFAULT_SKILL_DIR:
        whitelist.add(DEFAULT_SKILL_DIR)
    return whitelist


# Backward compatibility - default whitelist
_SANDBOX_WHITELIST = get_sandbox_whitelist()

_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_PROMPT_LINE_PATTERNS = (
    re.compile(r"^\s*[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:[^\r\n\$#]*[\$#](?:\s.*)?$"),
    re.compile(r"^\s*\[[^\]\n]+@[^\]\n]+\][\$#](?:\s.*)?$"),
    re.compile(
        r"^\s*(?:bash|zsh|sh|ksh|csh|tcsh|dash|ash|fish|rbash|busybox)[^$#\n]*[\$#](?:\s.*)?$"
    ),
)
_PROGRESS_NOISE_PATTERNS = (
    re.compile(r"\b\d{1,3}%\s*\[[^\]]+\]"),
    re.compile(
        r"^\s*(?:Reading package lists|Building dependency tree|Processing triggers for)\b"
    ),
    re.compile(r"^\s*(?:Get|Hit|Ign):\d+"),
    re.compile(r"^\s*Fetched\s+\d"),
    re.compile(
        r"^\s*(?:Selecting previously unselected|Preparing to unpack|Unpacking|Setting up)\b"
    ),
    re.compile(r"^\s*Reading state information\b"),
    re.compile(r"^\s*\(Reading database\b"),
    re.compile(r"^\s*debconf:\s+delaying package configuration\b", re.IGNORECASE),
)
_NOISE_KEYWORDS_BLOCK = ("error", "fail", "denied", "warning", "err:")


def normalize_sandbox_path(client: "SandboxBase", raw_path: str) -> str:
    """
    Normalise user supplied path to an absolute path anchored at sandbox work_dir.

    Raises:
        ValueError: 当路径逃离 sandbox 工作目录时抛出。
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("path 必须是非空字符串")

    base = posixpath.normpath(client.work_dir.rstrip("/")) or "/"

    if raw_path.startswith("/"):
        combined = raw_path
    else:
        combined = posixpath.join(base, raw_path)

    normalized = posixpath.normpath(combined)

    # Use dynamic whitelist based on client's skill_dir
    whitelist = get_sandbox_whitelist(client.skill_dir)
    for allowed in whitelist:
        allowed_norm = posixpath.normpath(allowed)
        if normalized == allowed_norm or normalized.startswith(f"{allowed_norm}/"):
            return normalized
    prefix = "" if base == "/" else f"{base}/"

    if normalized != base and not normalized.startswith(prefix):
        raise ValueError(f"路径 {normalized} 不在沙箱工作目录 {client.work_dir} 范围内")

    return normalized


async def ensure_directory(client: "SandboxBase", abs_path: str) -> None:
    """确保目标文件所在目录存在。"""
    directory = posixpath.dirname(abs_path)
    if not directory or directory == "/":
        return

    command = f"mkdir -p {shlex.quote(directory)}"
    result = await client.shell.exec_command(command=command, work_dir=client.work_dir)
    status = getattr(result, "status", None)
    if status != "completed":
        output = collect_shell_output(result)
        raise RuntimeError(f"创建目录失败: {output or status}")


async def detect_path_kind(client: "SandboxBase", abs_path: str) -> str:
    """
    判断路径类型。

    Returns:
        'dir' | 'file' | 'none'
    """
    command = (
        "if [ -d {0} ]; then echo DIR; "
        "elif [ -f {0} ]; then echo FILE; "
        "else echo NONE; fi"
    ).format(shlex.quote(abs_path))

    result = await client.shell.exec_command(command=command, work_dir=client.work_dir)
    if getattr(result, "status", None) != "completed":
        return "none"

    raw_output = collect_shell_output(result)
    if not raw_output:
        return "none"

    normalized = raw_output.replace("\r", "").upper()
    for line in normalized.splitlines():
        line_stripped = "".join(ch for ch in line if ch.isalpha())
        mapping = {"DIR": "dir", "FILE": "file", "NONE": "none"}
        if line_stripped in mapping:
            return mapping[line_stripped]
        if "DIR" in line_stripped:
            return "dir"
        if "FILE" in line_stripped:
            return "file"
        if "NONE" in line_stripped:
            return "none"

    return "none"


def collect_shell_output(result: "ShellCommandResult") -> str:
    """提取 ShellCommandResult 的输出文本。"""
    primary_output = getattr(result, "output", None)
    console = getattr(result, "console", None) or []

    if isinstance(primary_output, str) and primary_output:
        return _strip_prompt_lines(primary_output)

    texts = []
    if primary_output and isinstance(primary_output, (list, tuple)):
        for item in primary_output:
            chunk = getattr(item, "output", None)
            if not chunk:
                continue
            cleaned = _strip_prompt_lines(chunk)
            if cleaned:
                texts.append(cleaned)

    for record in console:
        segment = getattr(record, "output", None)
        if not segment:
            continue
        cleaned = _strip_prompt_lines(segment)
        if cleaned:
            texts.append(cleaned)

    return "\n".join(texts)


def _strip_prompt_lines(chunk: str) -> str:
    """移除通用 shell 提示符行，仅保留命令真实输出。"""
    if not chunk:
        return ""

    lines = chunk.splitlines()
    cleaned_lines = []
    previous_blank = False
    for line in lines:
        normalized = _ANSI_ESCAPE_RE.sub("", line).strip()
        if normalized and _is_prompt_line(normalized):
            continue
        if normalized and _is_progress_noise_line(normalized):
            continue
        if not normalized:
            if previous_blank:
                continue
            cleaned_lines.append("")
            previous_blank = True
            continue

        cleaned_lines.append(line.rstrip())
        previous_blank = False

    return "\n".join(cleaned_lines).strip("\n")


def _is_prompt_line(line: str) -> bool:
    """判断一行是否看起来像 shell 提示符."""
    for pattern in _PROMPT_LINE_PATTERNS:
        if pattern.match(line):
            return True
    return False


def _is_progress_noise_line(line: str) -> bool:
    """过滤 apt 等工具产生的冗长进度信息."""
    lowered = line.lower()
    if any(keyword in lowered for keyword in _NOISE_KEYWORDS_BLOCK):
        return False
    if not line.strip():
        return False
    for pattern in _PROGRESS_NOISE_PATTERNS:
        if pattern.search(line):
            return True
    return False


def extract_markdown_title(content: str, default_title: str = "文档") -> str:
    """
    从文件内容中提取 Markdown 标题，优先提取最显著的第一个标题。

    提取规则：
    1. 优先提取 # 一级标题
    2. 如果没有一级标题，提取 ## 二级标题
    3. 如果都没有，使用 default_title

    Args:
        content: 文件内容
        default_title: 默认标题（当没有找到 Markdown 标题时使用）

    Returns:
        str: 提取的标题或默认标题
    """
    if not content:
        return default_title

    lines = content.split("\n")

    # 首先查找一级标题
    for line in lines:
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            if title:
                return title

    # 如果没有一级标题，查找二级标题
    for line in lines:
        line = line.strip()
        if line.startswith("## ") and not line.startswith("### "):
            title = line[3:].strip()
            if title:
                return title

    # 都没有找到，返回默认标题
    return default_title


def calculate_file_size_kb(content: str) -> int:
    """
    计算文件内容的大小（单位：KB）。

    Args:
        content: 文件内容

    Returns:
        int: 文件大小（KB），向上取整
    """
    if not content:
        return 0

    # 计算字节大小（UTF-8 编码）
    byte_size = len(content.encode("utf-8"))
    # 转换为 KB，向上取整
    kb_size = (byte_size + 1023) // 1024
    return kb_size
