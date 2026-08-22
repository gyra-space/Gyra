"""FilesystemSkillProvider——本地 / 沙箱 skill 目录的 SkillProvider 实现。

对齐 DSH dsh-skill-filesystem：扫描磁盘目录，把 ``<name>/SKILL.md`` 解析为
SkillSummary / SkillDefinition。

  - 路径约定：base_skill_dir 下的每个子目录是一个 skill（``SKILL.md`` 是默认正文）；
  - 摘要：从前置元数据（YAML frontmatter）的 ``name`` / ``description`` 取；
    若 frontmatter 缺失，则用目录名作为 name、description 留空；
  - 正文：加载 ``SKILL.md``，去掉 frontmatter 后保留为 content；
  - 文件系统错误（如个别 skill 缺 SKILL.md）记 debug 日志后跳过；
  - 远程 / 沙箱场景下 base_skill_dir 可来自 sandbox_client（由 caller 注入）；
  - 沙箱模式可选（``sandbox_client`` 不为 None）：list / get 走 sandbox
    ``shell.exec_command`` + ``file.read``；本地模式走 stdlib pathlib。

设计依据：[DSH skills.md §Local discovery priority](../../../../../../../../../docs/subsystems/skills.md)
+ 现有 [ReadSkillTool] 的解析约定（共享 ``_skill_path_utils``）。
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from gyra.agent.core.v2.skills.registry import (
    SkillDefinition,
    SkillInvocation,
    SkillLookupOptions,
    SkillProvider,
    SkillSummary,
)
from gyra.agent.tools.builtin.skill._skill_path_utils import (
    normalize_skill_name,
    resolve_local_skill_dir,
)

logger = logging.getLogger(__name__)


def _default_skill_root() -> Optional[str]:
    """默认 skill 根目录（对齐 DSH ~/.skills）。

    顺序：
      1. ``$GYRA_SKILLS_DIR`` 显式环境变量
      2. ``~/skills``
      3. ``~/.gyra/skills``（项目级，与 ``~/.gyra`` 资源约定一致）

    返回 ``None`` 表示"全部不存在"——caller 据此跳过默认 provider 注册。
    """
    import os
    env = os.environ.get("GYRA_SKILLS_DIR")
    if env and os.path.isdir(env):
        return env
    home = os.path.expanduser("~")
    for cand in (os.path.join(home, "skills"), os.path.join(home, ".gyra", "skills")):
        if os.path.isdir(cand):
            return cand
    return env or None


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """简单 YAML frontmatter 解析——只取 name / description / invocation，避开 yaml 依赖。"""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    out: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not value or value in ("|", ">"):
            continue
        # 去掉行内注释与多余引号
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        if key in ("name", "description", "invocation"):
            out[key] = value
    return out


def _strip_frontmatter(content: str) -> str:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return content
    return content[match.end():]


def _is_invocation(value: Optional[str]) -> SkillInvocation:
    """把 frontmatter 的 disable-model-invocation / user-invocable 字符串映射到 SkillInvocation。

    DSH 语义：默认两字段均为 true；本项目简化为单一 ``invocation`` 字段。
    """
    if not value:
        return SkillInvocation.BOTH
    v = value.strip().lower()
    if v in ("model_only", "model-only"):
        return SkillInvocation.MODEL_ONLY
    if v in ("user_only", "user-only"):
        return SkillInvocation.USER_ONLY
    if v in ("none", "false", "off"):
        return SkillInvocation.NONE
    return SkillInvocation.BOTH


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #

class FilesystemSkillProvider(SkillProvider):
    """本地 / 沙箱 skill 目录 provider。

    Args:
        base_skill_dir: skill 根目录（本地路径，或沙箱 client 的 skill_dir）。
        source_bucket: 写到 summary.source 的桶（默认 ``filesystem``）。
        sandbox_client: 可选；有则走 sandbox shim，无则本地。
        ttl: 缓存 TTL（秒）；None=不缓存。0 也不缓存。
    """

    def __init__(
        self,
        base_skill_dir: str,
        *,
        source_bucket: str = "filesystem",
        sandbox_client: Optional[Any] = None,
        ttl: float = 5.0,
    ):
        super().__init__(name=f"fs:{base_skill_dir}")
        self._base = base_skill_dir
        self._source = source_bucket
        self._sandbox = sandbox_client
        self._ttl = ttl
        self._cache_summaries: Optional[List[SkillSummary]] = None
        self._cache_expires_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def list(
        self, options: SkillLookupOptions,
    ) -> List[SkillSummary]:
        """列举 skill 摘要（缓存受 TTL 约束）。"""
        if self._ttl and self._cache_summaries is not None and time.monotonic() < self._cache_expires_at:
            return list(self._cache_summaries)
        if self._sandbox is not None:
            summaries = await self._list_sandbox()
        else:
            summaries = self._list_local()
        if self._ttl:
            self._cache_summaries = list(summaries)
            self._cache_expires_at = time.monotonic() + self._ttl
        return list(summaries)

    async def get(
        self, name: str, options: SkillLookupOptions,
    ) -> Optional[SkillDefinition]:
        """按 name 加载完整 skill 定义。"""
        if not name:
            return None
        if self._sandbox is not None:
            return await self._get_sandbox(name)
        return self._get_local(name)

    def invalidate(self) -> None:
        """清缓存——file system watcher / provider 替换时调用。"""
        self._cache_summaries = None
        self._cache_expires_at = 0.0

    # ------------------------------------------------------------------ #
    # Local
    # ------------------------------------------------------------------ #

    def _list_local(self) -> List[SkillSummary]:
        if not self._base:
            return []
        base = Path(self._base)
        if not base.is_dir():
            return []
        out: List[SkillSummary] = []
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            name = entry.name
            skill_md = entry / "SKILL.md"
            # 没有 SKILL.md 的目录不算合法 skill（DSH：list 是有可用 skill 的视图），
            # 跳过——避免把空目录/无元数据条目暴露给模型。
            if not skill_md.is_file():
                logger.debug(
                    f"[FilesystemSkillProvider] skip {name}: missing SKILL.md",
                )
                continue
            desc = ""
            invocation = SkillInvocation.BOTH
            try:
                text = skill_md.read_text(encoding="utf-8")
                fm = _parse_frontmatter(text)
                desc = fm.get("description", "")
                invocation = _is_invocation(fm.get("invocation"))
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[FilesystemSkillProvider] {name}: parse failed: {e}")
            out.append(
                SkillSummary(
                    name=name,
                    description=desc,
                    invocation=invocation,
                    source=self._source,
                    provider=self.name,
                    path=str(entry),
                    rank=0,
                )
            )
        return out

    def _get_local(self, name: str) -> Optional[SkillDefinition]:
        resolved = resolve_local_skill_dir(self._base, name)
        if not resolved:
            return None
        skill_md = Path(resolved) / "SKILL.md"
        if not skill_md.is_file():
            return None
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError as e:
            logger.debug(f"[FilesystemSkillProvider] read {name} failed: {e}")
            return None
        fm = _parse_frontmatter(text)
        return SkillDefinition(
            name=normalize_skill_name(name),
            description=fm.get("description", ""),
            invocation=_is_invocation(fm.get("invocation")),
            source=self._source,
            provider=self.name,
            path=str(skill_md),
            content=_strip_frontmatter(text),
            metadata={"skill_dir": resolved, "skill_md": str(skill_md)},
        )

    # ------------------------------------------------------------------ #
    # Sandbox (shell + file.read via sandbox_client)
    # ------------------------------------------------------------------ #

    async def _list_sandbox(self) -> List[SkillSummary]:
        client = self._sandbox
        if client is None:
            return []
        # 用 `ls -d` 列子目录（沿用 V1 skill 列目录约定的解析风格）
        try:
            import shlex
            result = await client.shell.exec_command(
                command=f"ls -d {shlex.quote(self._base)}/*/ 2>/dev/null | xargs -I{{}} basename {{}}",
                work_dir=getattr(client, "work_dir", "/"),
                timeout=60.0,
            )
            from gyra.sandbox.sandbox_utils import collect_shell_output
            output = collect_shell_output(result) or ""
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[FilesystemSkillProvider] sandbox list failed: {e}")
            return []
        names = [n.strip() for n in output.strip().splitlines() if n.strip()]
        out: List[SkillSummary] = []
        for n in names:
            # 沙箱不读 frontmatter，仅 name/description 留空（model 调 skill({n}) 加载后才有）
            out.append(
                SkillSummary(
                    name=n,
                    description="",
                    invocation=SkillInvocation.BOTH,
                    source=self._source,
                    provider=self.name,
                    path=f"{self._base.rstrip('/')}/{n}",
                    rank=0,
                )
            )
        return out

    async def _get_sandbox(self, name: str) -> Optional[SkillDefinition]:
        client = self._sandbox
        if client is None:
            return None
        canonical = normalize_skill_name(name)
        skill_md = f"{self._base.rstrip('/')}/{canonical}/SKILL.md"
        try:
            file_info = await client.file.read(skill_md)
            content = getattr(file_info, "content", None)
            if content is None:
                return None
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[FilesystemSkillProvider] sandbox read {name} failed: {e}")
            return None
        fm = _parse_frontmatter(content)
        return SkillDefinition(
            name=canonical,
            description=fm.get("description", ""),
            invocation=_is_invocation(fm.get("invocation")),
            source=self._source,
            provider=self.name,
            path=skill_md,
            content=_strip_frontmatter(content),
            metadata={"skill_dir": f"{self._base.rstrip('/')}/{canonical}", "skill_md": skill_md},
        )
