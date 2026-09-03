"""Utility helpers for executing operations inside the sandbox client."""

from __future__ import annotations

import os
import posixpath
import re
import shlex
from typing import Any, List, Optional, Sequence, Tuple, TYPE_CHECKING, Set, Union


def resolve_session_work_dir(client: Any, default: str = "/workspace") -> str:
    """解析沙箱的当前工作目录:会话目录优先,否则回退 ``work_dir``。

    场景空间下会话目录为 ``<work_dir>/sessions/<conv_uid>/``,相对路径落进
    会话私有区,同名文件不会跨会话覆盖;未启用会话隔离时(非场景空间、E2B)
    与 ``work_dir`` 完全一致,行为不变。

    对未实现 ``session_work_dir`` 的对象(尤其是测试里的 MagicMock)做防御性
    回退:只有**非空字符串**才采用,否则 MagicMock 属性会被当成路径拼进文件
    系统,在项目根目录造出 ``<MagicMock ...>/uploads`` 这类垃圾目录。
    """
    for attr in ("session_work_dir", "work_dir"):
        value = getattr(client, attr, None)
        if isinstance(value, str) and value:
            return value
    return default


# ---------------------------------------------------------------------------
# Shell command validation
# ---------------------------------------------------------------------------

# 高危命令模式：local 沙箱下需用户交互授权（见 is_high_risk_command）
# 注意 dd 不在此列：dd 写普通文件合法，写块设备的场景由 _BLOCK_DEVICE_WRITE_RE 兜底。
_HIGH_RISK_BINARY = {"shutdown", "reboot", "halt", "poweroff"}
# 只拦截写入真实块设备（磁盘）的命令。伪设备重定向（2>/dev/null、>/dev/stdout、
# >/dev/tty 等）无害且高频，绝不在此列——历史上宽泛的 r"of=/dev/|>\s*/dev/"
# 曾把 "grep ... 2>/dev/null | sort | head" 误判为高危导致整条命令被拦。
_BLOCK_DEVICE_PATH = (
    r"/dev/(?:sd[a-z]+|hd[a-z]+|vd[a-z]+|xvd[a-z]+"
    r"|nvme\d+(?:n\d+)?(?:p\d+)?|mmcblk\d+(?:p\d+)?"
    r"|loop\d+|ram\d+|dm-\d+|fd\d+|mapper/\S+|disk/\S+)"
)
_BLOCK_DEVICE_WRITE_RE = re.compile(r"(?:\bof=|>\s*)" + _BLOCK_DEVICE_PATH)
_FORK_BOMB_RE = re.compile(r":\s*\(\s*\)\s*\{.*:.*\|.*:.*\}")

# Characters that essentially never appear in a clean file-path argument but do
# appear in regex patterns / shell strings. A token containing any of them is
# treated as a pattern/string, not a path, and skipped by the path fence --
# otherwise ``grep '/[^/"]*/'`` is misread as an absolute path and rejected.
_NON_PATH_CHARS = frozenset("*?[]^(){}+|'`$<>" + '"')

def _tokenize_command(command: str) -> List[str]:
    """Split the shell command into arguments."""
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"命令解析失败: {exc}") from exc
    if not tokens:
        raise ValueError("command 不能为空")
    return tokens


def _validate_tokens(
    tokens: List[str],
    sandbox_work_dir: str,
    allowed_roots: Optional[List[str]] = None,
) -> None:
    """Ensure command arguments stay within the sandbox work directory (path fence).

    Command binaries and flags are not restricted; only path-like arguments are
    confined to *sandbox_work_dir* (plus any *allowed_roots*, e.g. skill_dir or
    /mnt, which the LocalShellClient already sanctions as cwd). Both sides are
    resolved with realpath so paths behind a symlinked temp dir (macOS
    /var -> /private/var) are not falsely rejected.
    """
    roots = [sandbox_work_dir]
    roots.extend(allowed_roots or [])

    idx = 1
    while idx < len(tokens):
        token = tokens[idx]
        if token.startswith("-"):
            idx += 1
            continue
        if token.startswith("~"):
            raise PermissionError(
                f"禁止访问 home 目录（参数 '{token}'）。请使用工作空间内的相对路径"
            )
        if any(part == ".." for part in token.split("/")):
            raise PermissionError(
                f"命令参数 '{token}' 尝试跳出工作空间目录，已被禁止"
            )
        if any(ch in _NON_PATH_CHARS for ch in token):
            # regex / shell pattern, not a file path -> skip the path fence
            idx += 1
            continue
        if token.startswith("/"):
            combined = token
        else:
            combined = posixpath.join(sandbox_work_dir, token)
        if not _within_roots(combined, roots):
            raise PermissionError(
                f"命令参数 '{token}' 超出了沙箱工作目录，已被禁止。"
                "命令中所有路径参数（包括 find/grep 的搜索起点、cd 的目标）"
                "都必须位于工作空间内，请改用以工作目录为起点的相对路径"
                "（如 find . 而非 find /）"
            )
        idx += 1


def _within_roots(candidate: str, roots: List[str]) -> bool:
    """Return True if *candidate* equals or is nested under any root.

    Mirrors LocalShellClient._ensure_inside_allowed: both sides are realpath-
    resolved so symlinked prefixes compare consistently.
    """
    real_candidate = os.path.realpath(candidate)
    for root in roots:
        if not root:
            continue
        real_root = os.path.realpath(root)
        if real_candidate == real_root or real_candidate.startswith(
            os.path.join(real_root, "")
        ):
            return True
    return False


def _strip_heredoc_bodies(command: str) -> str:
    """Remove heredoc bodies from *command* before path validation.

    A heredoc (``<< DELIM`` ... ``DELIM``) feeds lines to a program on stdin;
    those lines are not file path arguments and must not be path-validated --
    otherwise a Python snippet such as ``if '/' in repo:`` is rejected because
    ``'/'`` tokenises to the bare path ``/``. Only the body lines are removed;
    the command structure (including the ``<< DELIM`` marker and the closing
    delimiter) is preserved so real argument validation is unchanged.

    Quote-aware: ``<<`` inside a quoted string (e.g. a bit-shift in
    ``python3 -c "a << b"``) is not treated as a heredoc start. Here-strings
    (``<<<``) are not heredocs and are left intact.
    """
    lines = command.split("\n")
    kept: List[str] = []
    pending: List[Tuple[str, bool]] = []   # open heredocs: (delimiter, tab_strip)
    quote: Optional[str] = None            # quote char carried across lines

    for line in lines:
        if pending:
            delim, tab_strip = pending[0]
            candidate = line.lstrip("\t") if tab_strip else line
            if candidate == delim:
                pending.pop(0)
                kept.append(line)
            # heredoc body line -> dropped from validation
            continue

        kept.append(line)
        starts, quote = _find_heredoc_starts(line, quote)
        pending.extend(starts)
    return "\n".join(kept)


def _find_heredoc_starts(
    line: str, quote: Optional[str]
) -> Tuple[List[Tuple[str, bool]], Optional[str]]:
    """Scan *line* for heredoc starts outside quoted regions.

    Returns the ``(delimiter, tab_stripped)`` starts found and the quote state
    at end of line (carried to the next line so a quoted string spanning lines
    keeps an embedded ``<<`` from being misread as a heredoc).
    """
    starts: List[Tuple[str, bool]] = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if quote is not None:
            if ch == "\\" and quote == '"' and i + 1 < n:
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == "<" and i + 1 < n and line[i + 1] == "<":
            parsed = _parse_heredoc_op(line, i)
            if parsed is not None:
                delim, tab_strip, end = parsed
                starts.append((delim, tab_strip))
                i = end
                continue
        i += 1
    return starts, quote


def _parse_heredoc_op(line: str, pos: int) -> Optional[Tuple[str, bool, int]]:
    """Parse a heredoc start at *pos* (pointing at ``<<``).

    Returns ``(delimiter, tab_stripped, next_pos)`` or ``None`` when this is
    not a heredoc -- a here-string ``<<<`` or a missing delimiter word.
    """
    n = len(line)
    j = pos + 2                       # past "<<"
    tab_strip = False
    if j < n and line[j] == "-":      # <<- form
        tab_strip = True
        j += 1
    if j < n and line[j] == "<":      # "<<<" here-string -> not a heredoc
        return None
    while j < n and line[j] in (" ", "\t"):
        j += 1
    quote_delim: Optional[str] = None
    if j < n and line[j] in ("'", '"'):
        quote_delim = line[j]
        j += 1
    start = j
    while j < n and (line[j].isalnum() or line[j] == "_"):
        j += 1
    if j == start:
        return None                   # no delimiter word -> not a heredoc
    delim = line[start:j]
    if quote_delim is not None and j < n and line[j] == quote_delim:
        j += 1
    return delim, tab_strip, j


def is_high_risk_command(command: str) -> bool:
    """Return True if *command* is high-risk and needs user authorization (local sandbox).

    Covers: recursive deletion (rm -r/-R/--recursive), disk ops (mkfs*,
    writes to real block devices such as dd of=/dev/sda or > /dev/nvme0n1 --
    /dev/null、/dev/stdout 等伪设备重定向不算), system power commands, and
    fork bombs.
    """
    try:
        tokens = _tokenize_command(command)
    except ValueError:
        # 解析失败的命令保守视为高危
        return True
    if not tokens:
        return False

    binary = tokens[0]
    if binary == "rm":
        for tok in tokens[1:]:
            if tok.startswith("--"):
                if tok == "--recursive":
                    return True
            elif tok.startswith("-") and ("r" in tok or "R" in tok):
                return True
    if binary in _HIGH_RISK_BINARY or binary.startswith("mkfs"):
        return True
    if _BLOCK_DEVICE_WRITE_RE.search(command) or _FORK_BOMB_RE.search(command):
        return True
    return False


# ---------------------------------------------------------------------------
# Skill-script trust: skill 目录不在场景空间(work_dir)内,但其中的脚本默认
# 受信——高危授权门对整条命令做正则,skill 脚本参数里出现 "dd"、"of=/dev/.."
# 之类字样纯属误伤;同时脚本中间产物常写 /tmp,需要栅栏放行。
# ---------------------------------------------------------------------------

#: 常见脚本解释器:其后第一个含 "/" 的非 flag 参数视为被执行的脚本
_INTERPRETER_BINARIES = frozenset(
    {"bash", "sh", "zsh", "dash", "python", "python3", "node", "perl", "ruby"}
)
#: 一旦某个子命令以这些 binary 为入口,整条命令绝不按 skill 脚本放行——
#: 防止 "rm -rf x && python3 /skills/run.py" 之类的组合命令借 skill 名义
#: 绕过用户授权。dd 虽已移出无条件高危名单,仍要挡在这里。
_GATED_BINARIES = frozenset({"rm", "dd", "shutdown", "reboot", "halt", "poweroff"})
#: 执行 skill 脚本时路径栅栏额外放行的临时目录
_SKILL_EXTRA_ROOTS = ("/tmp",)


def get_skill_command_extra_roots() -> Tuple[str, ...]:
    """skill 脚本命令在路径栅栏下额外放行的目录。"""
    return _SKILL_EXTRA_ROOTS


def is_skill_script_command(
    command: str,
    skill_dirs: Optional[Union[str, Sequence[str]]],
    work_dir: Optional[str] = None,
) -> bool:
    """判断命令是否在执行 skill 目录内的脚本（受信入口，默认安全）。

    对命令按 ``&& / || / | / ;`` 拆出全部子命令，逐一判定：

    - 子命令入口是 skill 目录内**真实存在**的脚本（可执行文件本身，或
      解释器后的首个路径参数），视为受信；realpath + isfile 双重确认，
      参数字符串里的伪路径不会命中。
    - 入口为解释器但带 ``-c`` / ``-m`` 时内联代码/模块不是脚本文件，
      不提取（``python3 -c "..." /skills/x/a.py`` 里 a.py 只是 argv）。
    - 任何子命令入口命中 :data:`_GATED_BINARIES`（或 ``mkfs*``）→ 直接
      False，绝不放行。
    - 至少存在一个 skill 脚本入口才返回 True；普通管道段（cat/grep 等
      非高危入口）不影响判定。

    Args:
        command: 原始 shell 命令。
        skill_dirs: 受信的 skill 目录（单个或多个）。
        work_dir: 命令执行目录，用于解析相对路径脚本。
    """
    if not skill_dirs:
        return False
    if isinstance(skill_dirs, str):
        skill_dirs = [skill_dirs]
    skill_roots = [os.path.realpath(s) for s in skill_dirs if s]
    if not skill_roots:
        return False

    try:
        tokens = _tokenize_command(command)
    except ValueError:
        return False

    subcommands: List[List[str]] = []
    current: List[str] = []
    for tok in tokens:
        if tok in ("&&", "||", "|", ";"):
            subcommands.append(current)
            current = []
        else:
            current.append(tok)
    subcommands.append(current)

    base = work_dir or os.getcwd()

    def _resolve_script(token: str) -> Optional[str]:
        candidate = token if token.startswith("/") else posixpath.join(base, token)
        real = os.path.realpath(candidate)
        if not os.path.isfile(real):
            return None
        for root in skill_roots:
            if real == root or real.startswith(os.path.join(root, "")):
                return real
        return None

    has_skill_entry = False
    for sub in subcommands:
        if not sub:
            continue
        binary = sub[0]
        script: Optional[str] = None
        candidates: List[str] = []
        if "/" in binary:
            candidates.append(binary)
        # 解释器(含绝对路径解释器)才从参数中提取脚本文件
        if posixpath.basename(binary) in _INTERPRETER_BINARIES or "/" in binary:
            if "-c" in sub or "-m" in sub:
                candidates = []
            else:
                for tok in sub[1:]:
                    if tok.startswith("-"):
                        continue
                    if "/" in tok:
                        candidates.append(tok)
                        break
        for cand in candidates:
            script = _resolve_script(cand)
            if script:
                break
        if script:
            has_skill_entry = True
            continue
        if binary in _GATED_BINARIES or binary.startswith("mkfs"):
            return False
    return has_skill_entry


def validate_shell_command(
    command: str,
    sandbox_work_dir: str,
    sandbox_type: str = "local",
    allowed_roots: Optional[List[str]] = None,
) -> None:
    """
    Validate a shell command for sandbox execution.

    - Remote sandboxes (``sandbox_type != "local"``): no validation, fully open;
      isolation is enforced at the OS level.
    - Local sandbox: arguments must stay inside *sandbox_work_dir* (path fence),
      or within any of *allowed_roots* (e.g. skill_dir). Binaries/flags are not
      restricted; high-risk commands are routed to interactive authorization by
      the caller (ShellExecTool), not blocked here.

    Raises:
        ValueError: on parse error or empty command
        PermissionError: on path policy violation
    """
    if not command or not command.strip():
        raise ValueError("command 不能为空")

    if sandbox_type != "local":
        return

    command = _strip_heredoc_bodies(command)
    tokens = _tokenize_command(command)
    subcommand: List[str] = []

    def _flush() -> None:
        if not subcommand:
            return
        _validate_tokens(subcommand, sandbox_work_dir, allowed_roots)
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

    场景空间下锚点是**会话目录**(``session_work_dir``,即
    ``<work_dir>/sessions/<conv_uid>/``),相对路径落进会话私有区;
    空间公共层(``work_dir``)仍然放行,这样 ``../files/`` 之类的相对路径
    与公共资产绝对路径都可用(读数据集、promote 共享文件)。

    Raises:
        ValueError: 当路径逃离 sandbox 工作目录时抛出。
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("path 必须是非空字符串")

    # 未配置会话目录的沙箱(E2B / 非场景空间)回退到 work_dir,行为不变。
    session_dir = resolve_session_work_dir(client)
    base = posixpath.normpath(session_dir.rstrip("/")) or "/"

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
        # 会话目录之外,但仍在空间公共层之内 —— 允许访问公共资产。
        workspace_base = posixpath.normpath(client.work_dir.rstrip("/")) or "/"
        ws_prefix = "" if workspace_base == "/" else f"{workspace_base}/"
        if normalized == workspace_base or normalized.startswith(ws_prefix):
            return normalized
        raise ValueError(
            f"路径 {normalized} 不在沙箱工作目录 {session_dir} 范围内"
        )

    return normalized


async def ensure_directory(client: "SandboxBase", abs_path: str) -> None:
    """确保目标文件所在目录存在。"""
    directory = posixpath.dirname(abs_path)
    if not directory or directory == "/":
        return

    command = f"mkdir -p {shlex.quote(directory)}"
    result = await client.shell.exec_command(
        command=command,
        work_dir=resolve_session_work_dir(client),
    )
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

    result = await client.shell.exec_command(
        command=command,
        work_dir=resolve_session_work_dir(client),
    )
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
