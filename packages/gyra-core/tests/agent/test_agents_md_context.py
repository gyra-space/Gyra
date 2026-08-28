"""gyra.agent.agents_md_context 公共模块单测（V1/V2 共用注入逻辑）。"""

import os

import pytest

from gyra.agent.agents_md_context import (
    AGENTS_MD_MAINTENANCE_GUIDANCE,
    detect_project_agents_md,
    is_agents_md_placeholder,
    parse_agents_md_config,
    read_agents_md_file,
    render_agents_md_block,
)


# --------------------------- 占位判断 --------------------------- #


def test_placeholder_empty():
    assert is_agents_md_placeholder("") is True
    assert is_agents_md_placeholder("   \n  ") is True


def test_placeholder_seed_template():
    assert (
        is_agents_md_placeholder(
            "# Agent 整体记忆（AGENTS.md）\n\n## Identity\n<你的身份描述>\n"
        )
        is True
    )


def test_placeholder_real_content():
    assert (
        is_agents_md_placeholder("# AGENTS.md\n\n## Identity\n我是数据分析助手\n")
        is False
    )


# --------------------------- 配置解析 --------------------------- #


def test_parse_config_missing():
    assert parse_agents_md_config({}) == (False, "")
    assert parse_agents_md_config(None) == (False, "")
    assert parse_agents_md_config({"agents_md": "not-a-dict"}) == (False, "")


def test_parse_config_ok():
    assert parse_agents_md_config({"agents_md": {"path": "AGENTS.md"}}) == (
        True,
        "AGENTS.md",
    )


def test_parse_config_disabled():
    assert parse_agents_md_config(
        {"agents_md": {"enabled": False, "path": "a.md"}}
    ) == (False, "a.md")


# --------------------------- 文件读取 --------------------------- #


@pytest.fixture()
def rules_dir(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# 项目规则\n\n只许用 pytest\n", "utf-8")
    (tmp_path / "empty.md").write_text("", "utf-8")
    (tmp_path / "sub").mkdir()
    return tmp_path


def test_read_absolute(rules_dir):
    content = read_agents_md_file(str(rules_dir / "AGENTS.md"))
    assert content and "pytest" in content


def test_read_relative_with_base(rules_dir):
    content = read_agents_md_file("AGENTS.md", str(rules_dir))
    assert content and "pytest" in content


def test_read_relative_traversal_rejected(rules_dir):
    assert read_agents_md_file("../x/AGENTS.md", str(rules_dir)) is None


def test_read_missing_returns_none(rules_dir):
    assert read_agents_md_file("nope.md", str(rules_dir)) is None
    assert read_agents_md_file("empty.md", str(rules_dir)) is None


def test_read_truncates_large_file(tmp_path):
    big = tmp_path / "big.md"
    big.write_text("x" * (512 * 1024 + 4096), "utf-8")
    content = read_agents_md_file(str(big))
    assert content is not None and len(content) <= 512 * 1024


# --------------------------- project_dir 探测 --------------------------- #


def test_detect_project_agents_md(rules_dir):
    assert "pytest" in (detect_project_agents_md(str(rules_dir)) or "")


def test_detect_missing_dir(rules_dir):
    assert detect_project_agents_md(str(rules_dir / "sub")) is None
    assert detect_project_agents_md("") is None
    assert detect_project_agents_md(None) is None


# --------------------------- 渲染 --------------------------- #


def test_render_three_sources_merged_and_ordered():
    block = render_agents_md_block(
        [
            ("explicit-config", "规则A内容"),
            ("memory-space", "记忆B内容"),
            ("project-dir", "项目C内容"),
        ]
    )
    assert block is not None
    assert "规则A内容" in block and "记忆B内容" in block and "项目C内容" in block
    assert block.index("规则A内容") < block.index("记忆B内容") < block.index("项目C内容")
    assert '<section source="explicit-config">' in block
    assert AGENTS_MD_MAINTENANCE_GUIDANCE in block


def test_render_skips_placeholder_sections():
    block = render_agents_md_block(
        [("explicit-config", ""), ("memory-space", "  \n ")]
    )
    assert block is None


def test_render_budget_truncation():
    block = render_agents_md_block([("x", "字" * 9000)], max_chars=4000)
    assert block is not None
    assert len(block) < 4400
    assert "内容过长已截断" in block


def test_render_without_guidance():
    block = render_agents_md_block([("x", "内容")], include_guidance=False)
    assert block is not None
    assert "维护说明" not in block
