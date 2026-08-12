"""Tests for the explicit memory channel: `memory_remember` tool.

Covers the explicit AGENTS.md write path:
1. `_insert_agents_md_user_item` routes user items into the right
   section, tags them `[来源: user]`, dedupes, and preserves existing
   content
2. `MemoryToolPack._do_remember` writes into the vault AGENTS.md when
   the store exposes it, and falls back to a normal memory_save
   otherwise
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from gyra_serve.agent.resource.tool.memory_tool import (
    MemoryToolPack,
    _insert_agents_md_user_item,
)


def _make_vault(agents_md: str = "") -> Any:
    vault = MagicMock()
    written: dict = {}

    async def _read():
        return agents_md
    vault.read_agents_md = _read

    async def _write(content):
        written["content"] = content
    vault.write_agents_md = _write
    vault._written = written
    return vault


def _make_store(vault: Any = None) -> Any:
    store = MagicMock()
    store.vault = vault
    store.write_memory = MagicMock(return_value=_fake_entry("e1"))
    return store


def _fake_entry(entry_id: str) -> Any:
    e = MagicMock()
    e.id = entry_id
    e.wing = "default"
    e.room = "lesson"
    return e


def _make_pack(store: Any) -> MemoryToolPack:
    return MemoryToolPack(memory_store=store, wing="default")


class TestInsertAgentsMdUserItem:
    def test_routes_to_section_with_user_tag(self):
        existing = "# Agent 整体记忆（AGENTS.md）\n\n## Identity\n\n## Lessons\n"
        out = _insert_agents_md_user_item(existing, "不要用 str() 转 bytes", "lesson")
        assert "[来源: user]" in out
        assert "不要用 str() 转 bytes" in out
        lessons = out.split("## Lessons", 1)[1].split("##", 1)[0]
        assert "不要用 str() 转 bytes" in lessons

    def test_creates_missing_section(self):
        existing = "# Agent 整体记忆（AGENTS.md）\n\n## Identity\n我是身份\n"
        out = _insert_agents_md_user_item(existing, "用户要求记住 API key 位置", "data")
        assert "## References" in out
        assert "用户要求记住 API key 位置" in out
        assert "我是身份" in out  # 已有内容保留

    def test_dedupes_identical_item(self):
        existing = (
            "# Agent 整体记忆（AGENTS.md）\n\n## Lessons\n"
            "- 不要用 str() 转 bytes [来源: user]\n"
        )
        out = _insert_agents_md_user_item(existing, "不要用 str() 转 bytes", "lesson")
        assert out == existing  # 已存在，no-op
        assert out.count("不要用 str() 转 bytes") == 1

    def test_unknown_category_defaults_to_conventions(self):
        existing = "# Agent 整体记忆（AGENTS.md）\n\n## Identity\n"
        out = _insert_agents_md_user_item(existing, "默认条目", "weird")
        assert "## Conventions" in out
        assert "默认条目" in out

    def test_empty_existing_gets_default_header(self):
        out = _insert_agents_md_user_item("", "记住一件事", "decision")
        assert out.startswith("# Agent 整体记忆（AGENTS.md）")
        assert "记住一件事" in out
        assert "## Decisions" in out


class TestDoRemember:
    def test_writes_to_vault_agents_md(self):
        vault = _make_vault(agents_md="# Agent 整体记忆（AGENTS.md）\n\n## Identity\n")
        store = _make_store(vault=vault)
        pack = _make_pack(store)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            pack._do_remember(content="用户要求记住：数据库用户表位置", category="data")
        )
        import json
        payload = json.loads(result)
        assert payload["status"] == "remembered"
        assert payload["source"] == "user"
        assert payload["section"] == "References"
        out = vault._written.get("content", "")
        assert "数据库用户表位置" in out
        assert "[来源: user]" in out
        # 无 vault 降级路径不应被触发
        store.write_memory.assert_not_called()

    def test_falls_back_to_memory_save_without_vault(self):
        store = _make_store(vault=None)
        pack = _make_pack(store)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            pack._do_remember(content="没有 vault 时的降级条目", category="lesson")
        )
        import json
        payload = json.loads(result)
        assert payload["status"] == "saved"
        assert payload["fallback"] is True
        store.write_memory.assert_called_once()
        assert store.write_memory.call_args.kwargs["room"] == "lesson"

    def test_empty_content_rejected(self):
        store = _make_store(vault=_make_vault())
        pack = _make_pack(store)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(pack._do_remember(content="   "))
        import json
        assert json.loads(result)["status"] == "error"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
