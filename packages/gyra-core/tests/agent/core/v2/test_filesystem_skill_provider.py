"""FilesystemSkillProvider 测试——本地 skill 目录扫描 + frontmatter 解析。

覆盖：
  - 列出子目录作为 skill（``<base>/<name>/``）；
  - 解析 ``SKILL.md`` 的 YAML frontmatter（``name`` / ``description`` / ``invocation``）；
  - 缺 frontmatter 时用目录名作为 name、description 留空；
  - ``get(name)`` 加载正文（去 frontmatter 后保留 content）；
  - 缓存 TTL 生效；
  - 不存在的 base 路径返回空列表；
  - ``invalidate()`` 清缓存；
  - 单个 skill 错误不阻塞其他 skill。
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from gyra.agent.core.v2.skills.filesystem_provider import (
    FilesystemSkillProvider,
    _parse_frontmatter,
    _strip_frontmatter,
    _is_invocation,
)
from gyra.agent.core.v2.skills.registry import SkillInvocation, SkillLookupOptions


def _write_skill(base: Path, name: str, body: str, *, with_frontmatter: bool = True) -> Path:
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if with_frontmatter:
        skill_md.write_text(body, encoding="utf-8")
    else:
        skill_md.write_text(body, encoding="utf-8")
    return skill_md


# --------------------------------------------------------------------------- #
# frontmatter 解析
# --------------------------------------------------------------------------- #


def test_parse_frontmatter_basic():
    text = (
        "---\n"
        "name: hello-world\n"
        "description: A greeting skill\n"
        "---\n"
        "# Hello\n"
    )
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "hello-world"
    assert fm.get("description") == "A greeting skill"


def test_parse_frontmatter_strips_quotes():
    text = (
        '---\n'
        'name: "double"\n'
        "description: 'single'\n"
        "---\n"
        "body"
    )
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "double"
    assert fm.get("description") == "single"


def test_parse_frontmatter_missing_returns_empty():
    assert _parse_frontmatter("body without fm") == {}


def test_strip_frontmatter_removes_yaml_block():
    text = (
        "---\n"
        "name: foo\n"
        "---\n"
        "the body"
    )
    body = _strip_frontmatter(text)
    assert "the body" in body
    assert "name: foo" not in body


def test_strip_frontmatter_keeps_content_when_no_fm():
    text = "no fm here"
    assert _strip_frontmatter(text) == text


def test_is_invocation_recognizes_all_values():
    assert _is_invocation(None) == SkillInvocation.BOTH
    assert _is_invocation("") == SkillInvocation.BOTH
    assert _is_invocation("model_only") == SkillInvocation.MODEL_ONLY
    assert _is_invocation("model-only") == SkillInvocation.MODEL_ONLY
    assert _is_invocation("user_only") == SkillInvocation.USER_ONLY
    assert _is_invocation("user-only") == SkillInvocation.USER_ONLY
    assert _is_invocation("none") == SkillInvocation.NONE
    assert _is_invocation("off") == SkillInvocation.NONE
    assert _is_invocation("invalid-value") == SkillInvocation.BOTH


# --------------------------------------------------------------------------- #
# 列出 skills
# --------------------------------------------------------------------------- #


async def test_list_local_skills_reads_frontmatter(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    _write_skill(base, "alpha", (
        "---\n"
        "name: alpha\n"
        "description: First skill\n"
        "invocation: both\n"
        "---\n"
        "body of alpha"
    ))
    _write_skill(base, "beta", (
        "---\n"
        "name: beta\n"
        "description: Second skill\n"
        "invocation: user_only\n"
        "---\n"
        "body of beta"
    ))

    provider = FilesystemSkillProvider(str(base))
    summaries = await _await(provider.list(SkillLookupOptions()))
    by_name = {s.name: s for s in summaries}
    assert "alpha" in by_name
    assert "beta" in by_name
    assert by_name["alpha"].description == "First skill"
    assert by_name["alpha"].invocation == SkillInvocation.BOTH
    assert by_name["beta"].invocation == SkillInvocation.USER_ONLY


async def test_list_local_skills_uses_dirname_when_no_frontmatter(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    (base / "no-fm").mkdir()
    (base / "no-fm" / "SKILL.md").write_text("plain body", encoding="utf-8")

    provider = FilesystemSkillProvider(str(base))
    summaries = await _await(provider.list(SkillLookupOptions()))
    assert len(summaries) == 1
    assert summaries[0].name == "no-fm"
    assert summaries[0].description == ""


async def test_list_local_skills_empty_when_no_base(tmp_path):
    """base 路径不存在 → 空列表（不抛错）。"""
    provider = FilesystemSkillProvider(str(tmp_path / "nope"))
    summaries = await _await(provider.list(SkillLookupOptions()))
    assert summaries == []


async def test_list_local_skills_ignores_dotfiles_and_files(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    (base / "valid").mkdir()
    (base / "valid" / "SKILL.md").write_text("---\nname: v\n---\nbody", encoding="utf-8")
    (base / ".hidden").mkdir()  # 隐藏目录
    (base / "stray.txt").write_text("not a dir")  # 文件
    provider = FilesystemSkillProvider(str(base))
    summaries = await _await(provider.list(SkillLookupOptions()))
    names = [s.name for s in summaries]
    assert "valid" in names
    assert ".hidden" not in names
    assert "stray.txt" not in names


async def test_list_local_skill_without_skill_md_is_skipped(tmp_path):
    """个别 skill 缺 SKILL.md → 跳过（不阻塞其他 skill）。"""
    base = tmp_path / "skills"
    base.mkdir()
    (base / "no-md").mkdir()  # 缺 SKILL.md
    _write_skill(base, "has-md", "body")
    provider = FilesystemSkillProvider(str(base))
    summaries = await _await(provider.list(SkillLookupOptions()))
    names = [s.name for s in summaries]
    assert "no-md" not in names
    assert "has-md" in names


# --------------------------------------------------------------------------- #
# 加载 skill body
# --------------------------------------------------------------------------- #


async def test_get_local_returns_skill_definition_with_content(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    _write_skill(base, "alpha", (
        "---\n"
        "name: alpha\n"
        "description: First skill\n"
        "---\n"
        "BODY of alpha"
    ))
    provider = FilesystemSkillProvider(str(base))
    defn = await _await(provider.get("alpha", SkillLookupOptions()))
    assert defn is not None
    assert defn.name == "alpha"
    assert defn.description == "First skill"
    assert "BODY of alpha" in defn.content
    # frontmatter 已剥
    assert "name: alpha" not in defn.content


async def test_get_local_returns_none_for_missing_skill(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    provider = FilesystemSkillProvider(str(base))
    assert await _await(provider.get("ghost", SkillLookupOptions())) is None


async def test_get_local_returns_none_for_missing_skill_md(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    (base / "broken").mkdir()
    # 缺 SKILL.md
    provider = FilesystemSkillProvider(str(base))
    assert await _await(provider.get("broken", SkillLookupOptions())) is None


async def test_get_local_handles_legacy_hyphen_suffix(tmp_path):
    """老式 ``alpha-<hash>`` 目录名也能解析（V1 兼容）。"""
    base = tmp_path / "skills"
    base.mkdir()
    (base / "alpha-abc123").mkdir()
    (base / "alpha-abc123" / "SKILL.md").write_text(
        "---\nname: alpha\n---\nbody", encoding="utf-8",
    )
    provider = FilesystemSkillProvider(str(base))
    defn = await _await(provider.get("alpha", SkillLookupOptions()))
    assert defn is not None
    assert defn.name == "alpha"


# --------------------------------------------------------------------------- #
# 缓存
# --------------------------------------------------------------------------- #


async def test_list_uses_cache_within_ttl(tmp_path):
    base = tmp_path / "skills"
    base.mkdir()
    _write_skill(base, "a", "body")
    provider = FilesystemSkillProvider(str(base), ttl=10.0)
    s1 = await _await(provider.list(SkillLookupOptions()))
    _write_skill(base, "b", "body")  # 新增
    s2 = await _await(provider.list(SkillLookupOptions()))  # 缓存命中
    assert len(s1) == len(s2)
    provider.invalidate()
    s3 = await _await(provider.list(SkillLookupOptions()))
    assert len(s3) == 2


# --------------------------------------------------------------------------- #
# Provider 标识
# --------------------------------------------------------------------------- #


def test_provider_name_includes_base_dir():
    p = FilesystemSkillProvider("/tmp/anything")
    assert p.name.startswith("fs:")
    assert "/tmp/anything" in p.name


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
