"""project_ecosystem 探测器 + project_context 注入变量测试。

覆盖：
- ProjectEcosystemLoader 对 .claude/.cursor/CLAUDE.md/AGENTS.md/SKILL.md/.mdc 的探测
- 生态类型过滤（claude_code / cursor / auto）
- project_context vm 变量从 agent.ext_config 读取并渲染
"""
import json
import os
import pytest

from gyra.agent.project_ecosystem import (
    ECOSYSTEM_AUTO,
    ECOSYSTEM_CLAUDE_CODE,
    ECOSYSTEM_CURSOR,
    ProjectEcosystemLoader,
    parse_frontmatter,
)


@pytest.fixture
def project_dir(tmp_path):
    """构造一个同时含 Claude Code 与 Cursor 生态配置的项目目录。"""
    (tmp_path / "CLAUDE.md").write_text(
        "# 项目说明\n\n本项目的技术栈与约定。\n", encoding="utf-8"
    )
    (tmp_path / "AGENTS.md").write_text(
        "# Agent 约定\n\n- 提交前必须运行测试\n", encoding="utf-8"
    )
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "CLAUDE.md").write_text("## 深层记忆\n\nclaude 专属约束。\n", encoding="utf-8")
    skill = claude / "skills" / "dev-review"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: dev-review\ndescription: 代码评审技能，用于代码审查\n---\n\n# Dev Review\n\n评审步骤...\n",
        encoding="utf-8",
    )
    rules = claude / "rules"
    rules.mkdir(parents=True)
    (rules / "style.md").write_text("## 代码风格\n\n使用 4 空格缩进。\n", encoding="utf-8")
    cursor = tmp_path / ".cursor"
    cskill = cursor / "skills" / "frontend"
    cskill.mkdir(parents=True)
    (cskill / "SKILL.md").write_text(
        "---\nname: frontend\ndescription: 前端开发技能\n---\n\n# Frontend\n",
        encoding="utf-8",
    )
    crules = cursor / "rules"
    crules.mkdir(parents=True)
    (crules / "ts.mdc").write_text(
        "---\ndescription: TS 规则\nglobs: **/*.ts, src/**/*.tsx\n---\n必须使用严格模式。\n",
        encoding="utf-8",
    )
    # Claude Code 单文件技能（.claude/skills/<name>.md 形态）
    (claude / "skills" / "rca.md").write_text(
        "---\nname: rca\ndescription: 根因分析技能\n---\n# RCA\n\n根因分析流程...\n",
        encoding="utf-8",
    )
    # Claude Code 斜杠命令
    commands = claude / "commands"
    commands.mkdir()
    (commands / "review.md").write_text(
        "---\ndescription: 代码审查命令\nallowed-tools: Bash, Read\n---\n请对当前变更做代码审查。\n",
        encoding="utf-8",
    )
    # Claude Code 子 Agent
    agents = claude / "agents"
    agents.mkdir()
    (agents / "analyst.md").write_text(
        "---\nname: analyst\ndescription: 数据分析专家\ntools: Bash, Read\n---\n你是数据分析专家，负责数据洞察。\n",
        encoding="utf-8",
    )
    # settings.json：env + 私有 mcpServers
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "env": {"MY_API_KEY": "${MY_API_KEY}", "PLAIN": "not-a-secret"},
                "mcpServers": {
                    "local-db": {"command": "npx", "args": ["-y", "mcp-server"], "env": {"K": "V"}}
                },
            }
        ),
        encoding="utf-8",
    )
    # .mcp.json：共享 MCP（远程 http）
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "remote-api": {"url": "https://example.com/sse", "headers": {"X-K": "V"}}
                }
            }
        ),
        encoding="utf-8",
    )
    return str(tmp_path)


def _fresh_loader():
    # 清缓存，避免跨用例复用
    ProjectEcosystemLoader.load.cache_clear()


# ------------------------------ frontmatter ------------------------------ #


def test_parse_frontmatter_basic():
    meta = parse_frontmatter(
        '---\nname: foo\ndescription: "带引号的描述"\n---\n\n# body\n'
    )
    assert meta == {"name": "foo", "description": "带引号的描述"}


def test_parse_frontmatter_no_block():
    assert parse_frontmatter("# no frontmatter\n") == {}


# ------------------------------ loader ------------------------------ #


def test_auto_detects_both_ecosystems(project_dir):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(project_dir, ECOSYSTEM_AUTO)
    assert eco is not None
    assert eco.has_content

    sources = [s.source for s in eco.memory_sections]
    assert "AGENTS.md" in sources
    assert "CLAUDE.md" in sources
    assert ".claude/CLAUDE.md" in sources

    names = {sk.name for sk in eco.skills}
    assert {"dev-review", "frontend", "rca"} <= names
    origins = {sk.origin for sk in eco.skills}
    assert origins == {"claude", "cursor"}
    assert all(sk.path.endswith(("SKILL.md", ".md")) for sk in eco.skills)

    assert len(eco.rules) == 2
    ts_rules = [r for r in eco.rules if r.path.endswith("ts.mdc")]
    assert ts_rules and ts_rules[0].globs == ["**/*.ts", "src/**/*.tsx"]


def test_detects_commands_subagents_env_mcp(project_dir):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(project_dir, ECOSYSTEM_AUTO)
    assert eco is not None

    # 命令
    assert [c.name for c in eco.commands] == ["review"]
    assert eco.commands[0].description == "代码审查命令"
    assert "代码审查" in eco.commands[0].content
    assert eco.commands[0].allowed_tools == "Bash, Read"

    # 子 Agent
    assert eco.subagents and eco.subagents[0].name == "analyst"
    assert eco.subagents[0].description == "数据分析专家"
    assert eco.subagents[0].tools == "Bash, Read"

    # MCP：stdio（settings）+ http（.mcp.json）
    assert len(eco.mcp_servers) == 2
    stdio = next(m for m in eco.mcp_servers if m.name == "local-db")
    assert stdio.transport == "stdio"
    assert stdio.command == "npx"
    assert stdio.args == ["-y", "mcp-server"]
    http = next(m for m in eco.mcp_servers if m.name == "remote-api")
    assert http.transport == "http"
    assert http.url == "https://example.com/sse"
    assert http.source == ".mcp.json"

    # env：仅 ${} 占位保留，真实值不回显
    env_map = {e.key: e.value for e in eco.env}
    assert env_map.get("MY_API_KEY") == "${MY_API_KEY}"
    assert env_map.get("PLAIN") == ""


def test_claude_type_filters_out_cursor_mcp(project_dir):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(project_dir, ECOSYSTEM_CLAUDE_CODE)
    assert eco is not None
    names = {m.name for m in eco.mcp_servers}
    assert {"local-db", "remote-api"} <= names


def test_cursor_type_skips_claude_commands_and_settings(project_dir):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(project_dir, ECOSYSTEM_CURSOR)
    assert eco is not None
    # Cursor 生态不读 .claude 的 commands/settings
    assert not eco.commands
    assert not eco.subagents
    assert not eco.env


def test_claude_code_type_filters(project_dir):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(project_dir, ECOSYSTEM_CLAUDE_CODE)
    assert eco is not None
    assert all(sk.origin == "claude" for sk in eco.skills)
    assert all(not r.path.endswith(".mdc") for r in eco.rules)
    # CLAUDE.md 系列 + AGENTS.md 保留
    sources = [s.source for s in eco.memory_sections]
    assert "CLAUDE.md" in sources and "AGENTS.md" in sources


def test_cursor_type_filters(project_dir):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(project_dir, ECOSYSTEM_CURSOR)
    assert eco is not None
    assert all(sk.origin == "cursor" for sk in eco.skills)
    # Cursor 生态不读 CLAUDE.md 专属文件
    assert all(s.source != ".claude/CLAUDE.md" for s in eco.memory_sections)
    assert eco.rules and all(r.path.endswith(".mdc") for r in eco.rules)


def test_load_missing_dir_returns_none():
    _fresh_loader()
    assert ProjectEcosystemLoader.load("/no/such/dir-xyz", ECOSYSTEM_AUTO) is None


def test_empty_project_dir(tmp_path):
    _fresh_loader()
    eco = ProjectEcosystemLoader.load(str(tmp_path), ECOSYSTEM_AUTO)
    assert eco is not None
    assert not eco.has_content


# ------------------------------ project_context 变量 ------------------------------ #


def _bare_agent_with_ext_config(ext_config):
    from types import SimpleNamespace

    from gyra.agent.core.variable import VariableManager
    from gyra.agent.expand.react_master_agent.react_master_agent import (
        ReActMasterAgent,
    )

    agent = object.__new__(ReActMasterAgent)
    object.__setattr__(
        agent,
        "__pydantic_private__",
        {
            "_inited_profile": SimpleNamespace(get_role=lambda: "test-role"),
            "_vm": VariableManager(),
        },
    )
    agent.__dict__["capability_pack"] = None
    agent.__dict__["sandbox_manager"] = None
    agent.__dict__["agent_context"] = None
    agent.__dict__["ext_config"] = ext_config
    agent.register_variables()
    return agent


async def test_project_context_var_renders(project_dir):
    _fresh_loader()
    agent = _bare_agent_with_ext_config(
        {
            "project_ecosystem": {
                "project_dir": project_dir,
                "type": ECOSYSTEM_AUTO,
            }
        }
    )
    out = await agent._vm.get_value("project_context", instance=agent)
    assert "项目生态上下文" in out
    assert "项目记忆" in out
    assert "CLAUDE.md" in out
    assert "dev-review" in out
    assert "frontend" in out
    assert "ts.mdc" in out
    # 新增：命令 / 子 Agent / MCP / env
    assert "项目命令" in out
    assert "/review" in out
    assert "项目子 Agent" in out
    assert "analyst" in out
    assert "项目 MCP" in out
    assert "remote-api" in out
    assert "local-db" in out
    assert "项目环境变量" in out
    assert "MY_API_KEY" in out


async def test_project_context_var_no_config_returns_empty():
    _fresh_loader()
    agent = _bare_agent_with_ext_config(None)
    out = await agent._vm.get_value("project_context", instance=agent)
    assert out == ""


async def test_project_context_var_bad_dir_returns_empty(tmp_path):
    _fresh_loader()
    agent = _bare_agent_with_ext_config(
        {"project_ecosystem": {"project_dir": str(tmp_path), "type": ECOSYSTEM_AUTO}}
    )
    out = await agent._vm.get_value("project_context", instance=agent)
    assert out == ""


async def test_identity_template_renders_project_context(project_dir):
    """身份层模板对 project_context 的 is defined 保护 + 渲染。"""
    from pathlib import Path

    from gyra.agent.shared.prompt_assembly.prompt_registry import (
        PromptRegistry,
    )

    prompts_dir = (
        Path(__file__).parent
        / "../../../../src/gyra/agent/expand/react_master_agent/prompts"
    ).resolve()
    registry = PromptRegistry.get_instance()
    registry.set_agent_prompts_dir(prompts_dir)
    registry.initialize(prompts_dir)
    template = registry.get("identity", "default")
    assert template is not None
    # 未定义 project_context 时不报错（模板用 is defined 保护）
    out_without = template.render(role="BAIZE")
    assert "项目生态上下文" not in out_without
    # 定义且有值时渲染
    out_with = template.render(role="BAIZE", project_context="## 项目生态上下文（测试）")
    assert "项目生态上下文（测试）" in out_with
