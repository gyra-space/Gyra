"""Skill 工具 V2 签名测试 —— 验证 skill_dir / available_skills 从 ToolContext 直接字段读取。

skill_exec / skill_list 已废弃删除，统一为 ``skill``（SkillTool）。此处仅保留
V1 磁盘读取能力（ReadSkillTool，作为 SkillTool 无 registry 时的 fallback 实现）
相关的上下文字段解析测试。
"""
import pytest
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.builtin.skill.read_skill import ReadSkillTool


class TestSkillToolV2ContextFields:
    """验证 Skill 工具从 ToolContext 直接字段读取 skill_dir / available_skills。"""

    def test_read_skill_resolves_from_direct_fields(self):
        """ReadSkillTool 从 context.skill_dir 和 context.available_skills 解析路径。"""
        ctx = ToolContext(
            skill_dir="/skills",
            available_skills={"sql_review": "/skills/sql_review"},
        )
        tool = ReadSkillTool()
        resolved = tool._resolve_skill_dir("sql_review", ctx)
        assert resolved == "/skills/sql_review"

    def test_read_skill_falls_back_to_config(self):
        """ReadSkillTool 在直接字段为空时回退到 context.config。"""
        ctx = ToolContext()
        ctx.config["available_skills"] = {"sql_review": "/skills/sql_review"}
        tool = ReadSkillTool()
        resolved = tool._resolve_skill_dir("sql_review", ctx)
        assert resolved == "/skills/sql_review"

    def test_read_skill_skill_dir_fallback_to_config(self):
        """ReadSkillTool 的 skill_dir 在直接字段为空时回退到 context.config。"""
        ctx = ToolContext()
        ctx.config["skill_dir"] = "/skills"
        tool = ReadSkillTool()
        resolved = tool._resolve_skill_dir("sql_review", ctx)
        # available_skills 也没有，走 skill_dir 拼接
        assert resolved is not None
        assert "/skills" in resolved

    def test_context_none_handled_gracefully(self):
        """context=None 时各工具不崩溃。"""
        tool = ReadSkillTool()
        resolved = tool._resolve_skill_dir("any_skill", None)
        # 没有 context 时走本地 fallback 或返回 None
        assert resolved is None or isinstance(resolved, str)

    def test_empty_context_direct_fields(self):
        """空的 ToolContext（skill_dir=None, available_skills={}）不崩溃。"""
        ctx = ToolContext()
        tool = ReadSkillTool()
        resolved = tool._resolve_skill_dir("any_skill", ctx)
        assert resolved is None or isinstance(resolved, str)


class TestSkillToolV2ExecuteIntegration:
    """execute() 集成测试 —— 验证从 ToolContext 直接字段读取的完整流程。"""

    async def test_read_skill_execute_reads_from_context(self, tmp_path):
        """ReadSkillTool.execute() 从 context.available_skills 解析路径并读取 SKILL.md。"""
        skill_dir = tmp_path / "sql_review"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\nname: sql_review\ndescription: SQL review skill\n---\n\n# SQL Review\n\nThis skill reviews SQL queries.")

        ctx = ToolContext(
            available_skills={"sql_review": str(skill_dir)},
        )
        tool = ReadSkillTool()
        result = await tool.execute({"skill_name": "sql_review"}, context=ctx)
        assert result.success
        assert "SQL Review" in result.output
        assert result.metadata.get("is_skill_content") is True
        assert result.metadata.get("skill_name") == "sql_review"

    async def test_read_skill_execute_skill_not_found(self, tmp_path):
        """ReadSkillTool.execute() 在 skill 路径不存在时返回失败。"""
        ctx = ToolContext(
            available_skills={"missing_skill": str(tmp_path / "missing_skill")},
        )
        tool = ReadSkillTool()
        result = await tool.execute({"skill_name": "missing_skill"}, context=ctx)
        assert not result.success
        assert "not found" in result.error.lower()