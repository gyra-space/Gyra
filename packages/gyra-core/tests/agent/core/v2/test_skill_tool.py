"""SkillTool 测试——DSH tool-skill 风格 ``skill({name})`` 工具。

覆盖：
  - 成功返回 ``<skill_content>`` + ``<skill_resources>`` + ``<skill_instructions>``；
  - XML 转义（name / path / source / provider 都不能破坏标签）；
  - name 校验：空 / 非 kebab-case / 含 ``..`` 失败；
  - file_path 校验：含 ``..`` 失败；非 SKILL.md 暂不支持；
  - invocation 限制：USER_ONLY / NONE 拒绝模型调用；
  - 找不到 skill：明确错误；
  - 行分页 offset / limit；
  - 与 V1 Skill 工具**不**冲突：V1 ``read_skill`` 仍是独立工具。
"""
from __future__ import annotations

import asyncio
import pytest

from gyra.agent.core.v2.skills.registry import (
    LAYER_HOST,
    SkillDefinition,
    SkillInvocation,
    SkillLookupOptions,
    SkillProvider,
    SkillRegistry,
)
from gyra.agent.core.v2.skills.skill_tool import (
    SKILL_TOOL_NAME,
    SkillTool,
)


class _StaticProvider(SkillProvider):
    def __init__(self, name: str, items: list):
        super().__init__(name=name)
        self._items = list(items)

    async def list(self, options):
        return list(self._items)

    async def get(self, name, options):
        for it in self._items:
            if it.name == name:
                return it
        return None


def _defn(
    name: str,
    content: str = "Hello body",
    *,
    invocation: SkillInvocation = SkillInvocation.BOTH,
    path: str | None = "/skills/foo/SKILL.md",
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        description="desc",
        invocation=invocation,
        source="test",
        provider="static",
        path=path,
        rank=0,
        content=content,
        metadata={},
    )


# --------------------------------------------------------------------------- #
# 成功路径：返回 <skill_content>
# --------------------------------------------------------------------------- #


async def test_skill_load_returns_skill_content_xml():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("hello-world", "First line\nSecond line\nThird line",
              path="/skills/hello-world/SKILL.md"),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "hello-world"}))
    assert result.success is True
    out = result.output
    assert '<skill_content name="hello-world">' in out
    assert "<skill_instructions>" in out
    assert "First line" in out
    assert "Second line" in out
    assert "<skill_resources>" in out
    assert "</skill_content>" in out
    # metadata 含 skill_name
    assert result.metadata.get("skill_name") == "hello-world"


async def test_skill_content_escapes_metadata_fields():
    """name / path / source / provider 转义；body 不转义（保持原始 markdown）。"""
    reg = SkillRegistry()
    raw_body = 'Body has & < > " chars'  # body 保留原文（markdown）
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("x", raw_body, path="/skills/x/&<path>/SKILL.md"),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "x"}))
    assert result.success is True
    out = result.output
    # name 在 attribute 中转义
    assert '<skill_content name="x">' in out
    # path 转义
    assert "/skills/x/&amp;&lt;path&gt;/SKILL.md" in out
    # body 保留原样（不强制 XML 转义——skill 内容是 markdown）
    assert "Body has & < > \" chars" in out


async def test_skill_content_truncates_over_100k():
    reg = SkillRegistry()
    big = "x" * 200_000
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("big", big),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "big"}))
    assert result.success is True
    out = result.output
    # 截断到 100K 附近 + 提示
    assert "truncated" in out.lower()
    # body 部分不超过 ~100K
    body_start = out.find("<skill_instructions>") + len("<skill_instructions>")
    body_end = out.find("</skill_instructions>")
    assert body_end - body_start < 110_000


# --------------------------------------------------------------------------- #
# name 校验
# --------------------------------------------------------------------------- #


async def test_skill_load_rejects_empty_name():
    reg = SkillRegistry()
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": ""}))
    assert result.success is False
    assert "name" in (result.error or "")
    assert "required" in (result.error or "")


async def test_skill_load_rejects_non_kebab_case():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("My_Skill"),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    for bad in ("NotKebab", "with space", "UPPER", "under_score", "dot.dot"):
        result = await _await(tool.execute({"name": bad}))
        assert result.success is False, f"expected fail for {bad!r}"
        assert "kebab-case" in (result.error or "")


async def test_skill_load_accepts_kebab_case_names():
    """DSH kebab-case 正则覆盖典型合法名。"""
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("a"),
        _defn("hello-world"),
        _defn("foo-bar-baz"),
        _defn("a1b2"),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    for n in ("a", "hello-world", "foo-bar-baz", "a1b2"):
        result = await _await(tool.execute({"name": n}))
        assert result.success is True, f"expected success for {n!r}"


# --------------------------------------------------------------------------- #
# file_path / offset / limit
# --------------------------------------------------------------------------- #


async def test_skill_load_rejects_dotdot_in_file_path():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_defn("x")]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "x", "file_path": "../etc/passwd"}))
    assert result.success is False
    assert ".." in (result.error or "")


async def test_skill_load_rejects_non_skill_md_file_path():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_defn("x")]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "x", "file_path": "README.md"}))
    assert result.success is False
    assert "not supported" in (result.error or "")


async def test_skill_load_pagination_offset_limit():
    reg = SkillRegistry()
    body = "\n".join(f"line {i}" for i in range(1, 11))  # 10 lines
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("x", body),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({
        "name": "x", "offset": 3, "limit": 3,
    }))
    assert result.success is True
    out = result.output
    assert "line 3" in out
    assert "line 5" in out
    assert "line 1" not in out
    assert "line 6" not in out


async def test_skill_load_pagination_offset_only():
    reg = SkillRegistry()
    body = "\n".join(f"line {i}" for i in range(1, 6))
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("x", body),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "x", "offset": 4, "limit": 0}))
    assert result.success is True
    out = result.output
    assert "line 4" in out
    assert "line 5" in out
    assert "line 1" not in out


# --------------------------------------------------------------------------- #
# invocation 限制
# --------------------------------------------------------------------------- #


async def test_skill_load_rejects_user_only_invocation():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("ui-only", "body", invocation=SkillInvocation.USER_ONLY),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "ui-only"}))
    assert result.success is False
    assert "not model-invocable" in (result.error or "")


async def test_skill_load_rejects_none_invocation():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("hidden", "body", invocation=SkillInvocation.NONE),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "hidden"}))
    assert result.success is False
    assert "not model-invocable" in (result.error or "")


async def test_skill_load_accepts_model_only_invocation():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("ml", "body", invocation=SkillInvocation.MODEL_ONLY),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "ml"}))
    assert result.success is True


# --------------------------------------------------------------------------- #
# 找不到
# --------------------------------------------------------------------------- #


async def test_skill_load_unknown_returns_clear_error():
    reg = SkillRegistry()
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "ghost"}))
    assert result.success is False
    assert "Unknown or no longer available" in (result.error or "")


# --------------------------------------------------------------------------- #
# 与 V1 不冲突
# --------------------------------------------------------------------------- #


def test_v1_skill_read_fallback_available():
    """V1 磁盘读取能力（ReadSkillTool）仍存在，作为 SkillTool 无 registry 的 fallback。

    ``skill_exec`` / ``skill_list`` 已废弃删除；V1 现在也注册统一的 ``skill`` 工具。
    """
    from gyra.agent.tools.builtin.skill.read_skill import ReadSkillTool

    assert ReadSkillTool.__name__ == "ReadSkillTool"
    # V2 工具名统一为 skill（对齐 DSH dsh-tool-skill）
    assert SKILL_TOOL_NAME == "skill"


def test_v1_list_exec_tools_removed():
    """``skill_exec`` / ``skill_list`` 工具类已删除。"""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(
            "gyra.agent.tools.builtin.skill.list_skills",
        )
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(
            "gyra.agent.tools.builtin.skill.execute_skill",
        )


def test_skill_tool_name_is_distinct():
    """V2 tool name (``skill``) 与 V1 ``Skill``（读写 fallback）区分。"""
    assert SKILL_TOOL_NAME == "skill"
    assert SKILL_TOOL_NAME != "Skill"


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
