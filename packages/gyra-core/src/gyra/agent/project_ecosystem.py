"""Claude Code / Cursor 项目生态探测与加载器。

兼容本地 agent 生态（.claude / .cursor 目录）：
- 项目记忆：``CLAUDE.md`` / ``AGENTS.md`` / ``.claude/CLAUDE.md``
- 项目技能：``.claude/skills/<name>/SKILL.md`` / ``.cursor/skills/<name>/SKILL.md``
- 项目规则：``.claude/rules/*.md`` / ``.cursor/rules/**/*.mdc``（含 glob frontmatter）

纯 stdlib 实现（无 pyyaml 依赖）：SKILL.md / .mdc 的 frontmatter 用极简解析器
提取 name/description/globs 标量。扫描结果按 (project_dir, type) 做模块级缓存，
运行时每轮 prompt 渲染只做一次 FS 扫描。

注入语义：项目配置作为补充上下文，不覆盖 Gyra 自身 skill / 系统提示。
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ------------------------------ 生态类型 ------------------------------ #
ECOSYSTEM_AUTO = "auto"
ECOSYSTEM_CLAUDE_CODE = "claude_code"
ECOSYSTEM_CURSOR = "cursor"
VALID_ECOSYSTEM_TYPES = (ECOSYSTEM_AUTO, ECOSYSTEM_CLAUDE_CODE, ECOSYSTEM_CURSOR)

# 项目记忆注入默认预算（字符数，超长截断尾部）
DEFAULT_MEMORY_MAX_CHARS = 6000

# ------------------------------ 数据模型 ------------------------------ #


@dataclass
class ProjectSkill:
    """项目目录中发现的生态技能（SKILL.md）。"""

    name: str
    description: str
    path: str  # SKILL.md 绝对路径（宿主机）
    origin: str  # "claude" | "cursor"


@dataclass
class ProjectRule:
    """项目目录中发现的生态规则（.claude/rules/*.md / .cursor/rules/*.mdc）。"""

    path: str
    globs: List[str] = field(default_factory=list)
    content: str = ""


@dataclass
class ProjectMemorySection:
    """项目记忆片段（CLAUDE.md / AGENTS.md）。"""

    source: str  # 文件名，如 "CLAUDE.md"、"AGENTS.md"、".claude/CLAUDE.md"
    path: str
    content: str


@dataclass
class ProjectCommand:
    """Claude Code 斜杠命令（.claude/commands/*.md）。"""

    name: str  # 命令名（文件名去 .md）
    description: str  # frontmatter description
    path: str
    content: str  # body（提示词）
    argument_hint: str = ""
    allowed_tools: str = ""
    model: str = ""


@dataclass
class ProjectSubagent:
    """Claude Code 子 Agent（.claude/agents/*.md）。"""

    name: str  # frontmatter name 或文件名
    description: str
    path: str
    content: str  # body（系统提示词）
    tools: str = ""  # 允许工具列表（frontmatter tools）
    model: str = ""


@dataclass
class ProjectMcpServer:
    """项目声明的 MCP server（.mcp.json / .claude/settings.json mcpServers）。"""

    name: str
    transport: str  # "stdio" | "http"
    url: str = ""
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    source: str = ""  # 来源文件，如 ".mcp.json"


@dataclass
class ProjectEnvItem:
    """项目环境变量声明（.claude/settings.json env）。"""

    key: str
    value: str = ""  # 仅占位符（${ENV}）或掩码，不回显真实密钥
    source: str = ""


@dataclass
class ProjectEcosystem:
    """一次扫描的完整结果。"""

    project_dir: str
    ecosystem_type: str
    memory_sections: List[ProjectMemorySection] = field(default_factory=list)
    skills: List[ProjectSkill] = field(default_factory=list)
    rules: List[ProjectRule] = field(default_factory=list)
    commands: List[ProjectCommand] = field(default_factory=list)
    subagents: List[ProjectSubagent] = field(default_factory=list)
    mcp_servers: List[ProjectMcpServer] = field(default_factory=list)
    env: List[ProjectEnvItem] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(
            self.memory_sections
            or self.skills
            or self.rules
            or self.commands
            or self.subagents
            or self.mcp_servers
            or self.env
        )

    def render_memory(self, max_chars: int = DEFAULT_MEMORY_MAX_CHARS) -> str:
        """渲染项目记忆文本（按 AGENTS.md > CLAUDE.md > .claude/CLAUDE.md 优先级）。"""
        if not self.memory_sections:
            return ""
        # 高优先级在前
        order = {"AGENTS.md": 0, "CLAUDE.md": 1, ".claude/CLAUDE.md": 2}
        sections = sorted(
            self.memory_sections,
            key=lambda s: order.get(s.source, 3),
        )
        parts: List[str] = []
        budget = max_chars
        for sec in sections:
            if budget <= 0:
                break
            content = sec.content.strip()
            if not content:
                continue
            if len(content) > budget:
                content = content[:budget] + "\n...(内容过长已截断)"
            parts.append(f"<section source=\"{sec.source}\">\n{content}\n</section>")
            budget -= len(content)
        return "\n\n".join(parts)


# ------------------------------ frontmatter 解析 ------------------------------ #

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> Dict[str, str]:
    """极简 YAML frontmatter 解析：提取 ``---`` 包裹块的标量字段。

    SKILL.md / .mdc 的 frontmatter 均为 name/description/globs 等简单键值，
    无需完整 YAML 依赖。
    """
    m = _FRONTMATTER_RE.match(text or "")
    if not m:
        return {}
    data: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            continue
        # 去掉行内注释（空格后 #），保留值主体
        value = value.strip()
        value = value.split(" #")[0].strip()
        # 仅剥离首尾成对引号（如 description: "带引号的描述"）
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        data[key] = value
    return data


# ------------------------------ 扫描器 ------------------------------ #


class ProjectEcosystemLoader:
    """扫描宿主机项目目录，识别 Claude Code / Cursor 生态配置。"""

    @staticmethod
    @lru_cache(maxsize=128)
    def load(
        project_dir: str,
        ecosystem_type: str = ECOSYSTEM_AUTO,
    ) -> Optional[ProjectEcosystem]:
        """扫描项目目录（带缓存，同步阻塞式，调用方应放 to_thread）。"""
        project_dir = (project_dir or "").strip()
        if not project_dir or not os.path.isdir(project_dir):
            return None
        if ecosystem_type not in VALID_ECOSYSTEM_TYPES:
            ecosystem_type = ECOSYSTEM_AUTO

        eco = ProjectEcosystem(
            project_dir=os.path.abspath(project_dir),
            ecosystem_type=ecosystem_type,
        )
        want_claude = ecosystem_type in (ECOSYSTEM_AUTO, ECOSYSTEM_CLAUDE_CODE)
        want_cursor = ecosystem_type in (ECOSYSTEM_AUTO, ECOSYSTEM_CURSOR)

        # ---- 项目记忆 ----
        _collect_memory(project_dir, eco, want_claude, want_cursor)

        # ---- 项目技能（SKILL.md）----
        if want_claude:
            eco.skills.extend(
                _scan_skill_dir(project_dir, ".claude", "claude")
            )
        if want_cursor:
            eco.skills.extend(
                _scan_skill_dir(project_dir, ".cursor", "cursor")
            )

        # ---- 项目规则 ----
        if want_claude:
            eco.rules.extend(_scan_rules_dir(project_dir, ".claude"))
        if want_cursor:
            eco.rules.extend(_scan_rules_dir(project_dir, ".cursor"))

        # ---- Claude Code 命令 / 子 Agent ----
        if want_claude:
            eco.commands.extend(_scan_commands_dir(project_dir))
            eco.subagents.extend(_scan_subagents_dir(project_dir))
            _collect_settings(project_dir, eco)

        # ---- MCP（.mcp.json 共享配置；.cursor/mcp.json Cursor 生态）----
        _collect_mcp_json(project_dir, eco, want_claude, want_cursor)

        return eco

    @staticmethod
    def invalidate_cache(project_dir: str, ecosystem_type: str = ECOSYSTEM_AUTO) -> None:
        """清空单个目录缓存（配置变更时调用）。"""
        ProjectEcosystemLoader.load.cache_clear()


def _read_text(path: str, max_bytes: int = 512 * 1024) -> str:
    """安全读取文本文件（防超大文件 / 二进制）。"""
    try:
        with open(path, "rb") as f:
            raw = f.read(max_bytes + 1)
    except OSError as e:
        logger.debug(f"[project-ecosystem] read {path} failed: {e}")
        return ""
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _collect_memory(
    project_dir: str,
    eco: ProjectEcosystem,
    want_claude: bool,
    want_cursor: bool,
) -> None:
    """收集 CLAUDE.md / AGENTS.md / .claude/CLAUDE.md。

    AGENTS.md 是跨工具标准（Claude Code / Cursor 均读取），任意生态都纳入；
    CLAUDE.md 仅 Claude 生态（auto 下也纳入）。
    """
    candidates: List[tuple] = []
    if want_cursor or want_claude:
        candidates.append(("AGENTS.md", os.path.join(project_dir, "AGENTS.md")))
    if want_claude:
        candidates.append(("CLAUDE.md", os.path.join(project_dir, "CLAUDE.md")))
        candidates.append(
            (".claude/CLAUDE.md", os.path.join(project_dir, ".claude", "CLAUDE.md"))
        )
    for source, path in candidates:
        if not os.path.isfile(path):
            continue
        content = _read_text(path)
        if not content.strip():
            continue
        eco.memory_sections.append(
            ProjectMemorySection(source=source, path=path, content=content)
        )


def _scan_skill_dir(project_dir: str, rel_dir: str, origin: str) -> List[ProjectSkill]:
    """扫描技能目录，支持两种 Claude Code / Cursor 形态：
    - 子目录：``<rel_dir>/skills/<name>/SKILL.md``
    - 单文件：``<rel_dir>/skills/<name>.md``
    """
    skills_dir = os.path.join(project_dir, rel_dir, "skills")
    if not os.path.isdir(skills_dir):
        return []
    result: List[ProjectSkill] = []
    try:
        entries = sorted(os.listdir(skills_dir))
    except OSError as e:
        logger.debug(f"[project-ecosystem] list {skills_dir} failed: {e}")
        return result
    for entry in entries:
        entry_path = os.path.join(skills_dir, entry)
        if os.path.isdir(entry_path):
            skill_path = os.path.join(entry_path, "SKILL.md")
            if not os.path.isfile(skill_path):
                continue
        elif entry.endswith(".md") and os.path.isfile(entry_path):
            skill_path = entry_path
        else:
            continue
        content = _read_text(skill_path)
        meta = parse_frontmatter(content)
        if entry.endswith(".md"):
            name = meta.get("name") or entry[:-3]
        else:
            name = meta.get("name") or entry
        description = meta.get("description") or ""
        result.append(
            ProjectSkill(
                name=name,
                description=description,
                path=skill_path,
                origin=origin,
            )
        )
    return result


def _scan_rules_dir(project_dir: str, rel_dir: str) -> List[ProjectRule]:
    """扫描规则目录（.claude/rules/*.md、.cursor/rules/**/*.mdc）。"""
    rules_root = os.path.join(project_dir, rel_dir, "rules")
    if not os.path.isdir(rules_root):
        return []
    result: List[ProjectRule] = []
    for root, _dirs, files in os.walk(rules_root):
        for filename in sorted(files):
            if not filename.endswith((".md", ".mdc")):
                continue
            path = os.path.join(root, filename)
            content = _read_text(path)
            meta = parse_frontmatter(content)
            # 去掉 frontmatter 后的正文
            body = _FRONTMATTER_RE.sub("", content).strip()
            globs = [g.strip() for g in (meta.get("globs", "") or "").split(",") if g.strip()]
            if body:
                result.append(ProjectRule(path=path, globs=globs, content=body))
    return result


def _scan_commands_dir(project_dir: str) -> List[ProjectCommand]:
    """扫描 Claude Code 斜杠命令（.claude/commands/*.md）。"""
    commands_dir = os.path.join(project_dir, ".claude", "commands")
    if not os.path.isdir(commands_dir):
        return []
    result: List[ProjectCommand] = []
    try:
        filenames = sorted(os.listdir(commands_dir))
    except OSError as e:
        logger.debug(f"[project-ecosystem] list {commands_dir} failed: {e}")
        return result
    for filename in filenames:
        if not filename.endswith(".md"):
            continue
        path = os.path.join(commands_dir, filename)
        content = _read_text(path)
        if not content.strip():
            continue
        meta = parse_frontmatter(content)
        body = _FRONTMATTER_RE.sub("", content).strip()
        name = filename[:-3]  # 去 .md
        result.append(
            ProjectCommand(
                name=name,
                description=meta.get("description", ""),
                path=path,
                content=body,
                argument_hint=meta.get("argument-hint", ""),
                allowed_tools=meta.get("allowed-tools", ""),
                model=meta.get("model", ""),
            )
        )
    return result


def _scan_subagents_dir(project_dir: str) -> List[ProjectSubagent]:
    """扫描 Claude Code 子 Agent（.claude/agents/*.md）。"""
    agents_dir = os.path.join(project_dir, ".claude", "agents")
    if not os.path.isdir(agents_dir):
        return []
    result: List[ProjectSubagent] = []
    try:
        filenames = sorted(os.listdir(agents_dir))
    except OSError as e:
        logger.debug(f"[project-ecosystem] list {agents_dir} failed: {e}")
        return result
    for filename in filenames:
        if not filename.endswith(".md"):
            continue
        path = os.path.join(agents_dir, filename)
        content = _read_text(path)
        if not content.strip():
            continue
        meta = parse_frontmatter(content)
        body = _FRONTMATTER_RE.sub("", content).strip()
        result.append(
            ProjectSubagent(
                name=meta.get("name") or filename[:-3],
                description=meta.get("description", ""),
                path=path,
                content=body,
                tools=meta.get("tools", ""),
                model=meta.get("model", ""),
            )
        )
    return result


def _parse_json_file(path: str) -> Optional[dict]:
    """安全解析 JSON 配置文件。"""
    content = _read_text(path)
    if not content.strip():
        return None
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[project-ecosystem] parse {path} failed: {e}")
        return None


def _collect_settings(project_dir: str, eco: ProjectEcosystem) -> None:
    """收集 .claude/settings.json 的 env 与 mcpServers。"""
    settings_path = os.path.join(project_dir, ".claude", "settings.json")
    data = _parse_json_file(settings_path)
    if not data:
        return
    # env：只登记 key；值若是 ${ENV} 占位符保留，真实值一律不回显（防密钥泄漏）
    for key, value in (data.get("env") or {}).items():
        if not key:
            continue
        display = value if isinstance(value, str) and value.startswith("${") else ""
        eco.env.append(
            ProjectEnvItem(key=key, value=display, source=".claude/settings.json")
        )
    # mcpServers（项目私有 MCP 配置）
    for name, server in (data.get("mcpServers") or {}).items():
        mcp = _parse_mcp_server(name, server, source=".claude/settings.json")
        if mcp:
            eco.mcp_servers.append(mcp)


def _collect_mcp_json(
    project_dir: str, eco: ProjectEcosystem, want_claude: bool, want_cursor: bool
) -> None:
    """收集 .mcp.json（共享）与 .cursor/mcp.json（Cursor 生态）。"""
    candidates: List[tuple] = []
    if want_claude:
        candidates.append((".mcp.json", os.path.join(project_dir, ".mcp.json")))
    if want_cursor:
        candidates.append(
            (".cursor/mcp.json", os.path.join(project_dir, ".cursor", "mcp.json"))
        )
    for source, path in candidates:
        data = _parse_json_file(path)
        if not data:
            continue
        for name, server in (data.get("mcpServers") or {}).items():
            mcp = _parse_mcp_server(name, server, source=source)
            if mcp:
                eco.mcp_servers.append(mcp)


def _parse_mcp_server(name: str, server: Any, source: str) -> Optional[ProjectMcpServer]:
    """把单个 mcpServers 条目解析为 ProjectMcpServer。

    支持 Claude Code / Cursor 两种形态：
    - stdio：{"command": "...", "args": [...], "env": {...}}
    - http：{"url": "...", "type": "http"/"sse", "headers": {...}}
    """
    if not isinstance(server, dict):
        return None
    if server.get("url"):
        return ProjectMcpServer(
            name=name,
            transport="http",
            url=str(server.get("url", "")),
            headers=server.get("headers") or {},
            source=source,
        )
    command = (server.get("command") or "").strip()
    if command:
        return ProjectMcpServer(
            name=name,
            transport="stdio",
            command=command,
            args=list(server.get("args") or []),
            env=server.get("env") or {},
            source=source,
        )
    return None
