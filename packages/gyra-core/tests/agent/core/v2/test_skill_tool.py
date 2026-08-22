"""SkillTool 测试——DSH tool-skill 风格 ``skill({name})`` 工具。

覆盖：
  - 成功返回官方标准 ``<skill_content name>``（正文无 YAML 头）
    + ``<file_preview>`` 文件清单；完整 frontmatter 走 metadata.skill_meta
    （工具 view 通道，不进 LLM 输出）；
  - XML 转义（name 属性不能破坏标签）；
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
    # 官方标准格式：LLM 视角只有 name 属性 + 正文 + file_preview
    assert '<skill_content name="hello-world">' in out
    assert "First line" in out
    assert "Second line" in out
    assert "<file_preview>" in out
    assert "base_path: /skills/hello-world" in out
    assert "</skill_content>" in out
    # metadata 含 skill_name / skill_description
    assert result.metadata.get("skill_name") == "hello-world"
    assert result.metadata.get("skill_description") == "desc"


async def test_skill_content_escapes_metadata_fields():
    """name 属性转义；body 不转义（保持原始 markdown）。"""
    reg = SkillRegistry()
    raw_body = 'Body has & < > " chars'  # body 保留原文（markdown）
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("x", raw_body, path="/skills/x/SKILL.md"),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "x"}))
    assert result.success is True
    out = result.output
    # name 在 attribute 中
    assert '<skill_content name="x">' in out
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
    assert len(out) < 110_000


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
# file_preview（真实目录枚举）
# --------------------------------------------------------------------------- #


async def test_skill_content_file_preview_lists_real_files(tmp_path):
    """file_preview 枚举 skill 目录下真实文件（相对路径 + 大小）。"""
    skill_dir = tmp_path / "data-analysis"
    (skill_dir / "templates").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# body", encoding="utf-8")
    (skill_dir / "templates" / "general_analysis.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _defn("data-analysis", "# body",
              path=str(skill_dir / "SKILL.md")),
    ]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "data-analysis"}))
    assert result.success is True
    out = result.output
    assert f"base_path: {skill_dir}" in out
    assert "templates/general_analysis.html" in out
    assert "SKILL.md" in out


# --------------------------------------------------------------------------- #
# V1 fallback：SKILL.md 包裹为标准格式
# --------------------------------------------------------------------------- #


async def test_v1_fallback_wraps_skill_md_into_skill_content(tmp_path):
    """无 registry（V1 fallback）时，读 SKILL.md 同样输出标准 <skill_content>。"""
    skill_dir = tmp_path / "data-analysis"
    (skill_dir / "templates").mkdir(parents=True)
    raw = (
        "---\n"
        "name: data-analysis\n"
        "description: |\n"
        "  全面的数据分析技能，支持多种数据源。\n"
        "version: 1.2.0\n"
        "author: Gyra Team\n"
        "tags: [analysis, report]\n"
        "---\n"
        "\n"
        "# 数据分析专家技能\n"
        "\n"
        "正文内容\n"
    )
    (skill_dir / "SKILL.md").write_text(raw, encoding="utf-8")
    (skill_dir / "templates" / "simple_answer.html").write_text(
        "<html></html>", encoding="utf-8"
    )

    from gyra.agent.tools.context import ToolContext

    tool = SkillTool()  # 无 registry → V1 fallback
    ctx = ToolContext(available_skills={"data-analysis": str(skill_dir)})
    result = await _await(tool.execute({"name": "data-analysis"}, ctx))
    assert result.success is True
    out = result.output
    # LLM 视角：只有 name 属性 + 正文 + file_preview，无 YAML 头、无 d-skill-meta
    assert '<skill_content name="data-analysis">' in out
    assert "# 数据分析专家技能" in out
    assert "正文内容" in out
    assert "<d-skill-meta>" not in out
    assert "---\nname: data-analysis" not in out
    # file_preview 列真实文件
    assert "<file_preview>" in out
    assert "templates/simple_answer.html" in out
    # 完整 frontmatter 走 metadata（工具 view 通道，用户视角）
    skill_meta = result.metadata.get("skill_meta") or ""
    assert "version: 1.2.0" in skill_meta
    assert "author: Gyra Team" in skill_meta
    assert "tags: [analysis, report]" in skill_meta
    assert result.metadata.get("skill_name") == "data-analysis"
    assert result.metadata.get("skill_description") == "全面的数据分析技能，支持多种数据源。"


async def test_skill_content_carries_frontmatter_raw(tmp_path):
    """V2 registry 模式：provider 的 frontmatter_raw 进 metadata.skill_meta（view 通道）。"""
    skill_dir = tmp_path / "x"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# body", encoding="utf-8")
    d = _defn("x", "# body", path=str(skill_dir / "SKILL.md"))
    d.metadata = {"skill_dir": str(skill_dir),
                  "frontmatter_raw": "name: x\nversion: 2.0.0\nauthor: Alice"}
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [d]))
    tool = SkillTool(reg, layer_chain=[LAYER_HOST])
    result = await _await(tool.execute({"name": "x"}))
    assert result.success is True
    out = result.output
    # LLM 输出不含 frontmatter；view 通道携带
    assert "<d-skill-meta>" not in out
    skill_meta = result.metadata.get("skill_meta") or ""
    assert "version: 2.0.0" in skill_meta
    assert "author: Alice" in skill_meta


async def test_v1_fallback_non_skill_md_passthrough(tmp_path):
    """V1 fallback 读其它文件保持原文返回，不包 XML。"""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# body", encoding="utf-8")
    (skill_dir / "notes.md").write_text("plain notes", encoding="utf-8")

    from gyra.agent.tools.context import ToolContext

    tool = SkillTool()
    ctx = ToolContext(available_skills={"my-skill": str(skill_dir)})
    result = await _await(
        tool.execute({"name": "my-skill", "file_path": "notes.md"}, ctx)
    )
    assert result.success is True
    assert result.output == "plain notes"
    assert "<skill_content" not in result.output


# --------------------------------------------------------------------------- #
# 工具 view 通道：WorkEntry.view → action_report
# --------------------------------------------------------------------------- #


def test_work_entry_view_channel_round_trip():
    """WorkEntry.view 序列化回环 + to_action_output 把 view 带给 ActionOutput。"""
    from gyra.agent.core.memory.gpts.file_base import WorkEntry

    meta_view = "<d-skill-meta>\nname: x\nversion: 2.0.0\n</d-skill-meta>"
    entry = WorkEntry(
        timestamp=1.0,
        tool="skill",
        args={"name": "x"},
        result="<skill_content name=\"x\">\n# body\n</skill_content>",
        view=meta_view,
        success=True,
        tool_call_id="call_1",
    )
    # 序列化回环
    restored = WorkEntry.from_dict(dict(entry.to_dict()))
    assert restored.view == meta_view
    # 重建 action_report：view 通道数据进 ActionOutput.view，content 保持 LLM 视角
    act_out = restored.to_action_output()
    assert meta_view in (act_out.view or "")
    assert "<d-skill-meta>" not in act_out.content
    # 老数据无 view 字段兼容
    legacy = entry.to_dict()
    legacy.pop("view")
    assert WorkEntry.from_dict(legacy).view is None


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
