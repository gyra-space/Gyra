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
        result = asyncio.run(
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
        result = asyncio.run(
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
        result = asyncio.run(pack._do_remember(content="   "))
        import json
        assert json.loads(result)["status"] == "error"


class TestDoSaveDoSearchAsync:
    """memory_save / memory_search async 修复:knowledge-vault(async-only)
    store 不再踩 sync NotImplementedError;SQLite 等同步 store 走回退分支。"""

    def test_save_uses_async_path_on_vault_store(self):
        store = MagicMock(spec=["vault", "awrite_memory"])
        store.awrite_memory = AsyncMock(return_value=_fake_entry("e-async"))
        pack = _make_pack(store)
        result = asyncio.run(pack._do_save(content="异步写入", room="general"))
        import json

        payload = json.loads(result)
        assert payload["status"] == "saved"
        assert payload["id"] == "e-async"
        store.awrite_memory.assert_awaited_once()

    def test_save_sync_fallback_for_sqlite_store(self):
        store = MagicMock(spec=["write_memory"])
        store.write_memory = MagicMock(return_value=_fake_entry("e-sync"))
        pack = _make_pack(store)
        result = asyncio.run(pack._do_save(content="同步写入", room="general"))
        import json

        assert json.loads(result)["status"] == "saved"
        store.write_memory.assert_called_once()

    def test_search_uses_async_path_on_vault_store(self):
        store = MagicMock(spec=["asearch_memory"])
        entry = _fake_entry("e-1")
        entry.content = "相关记忆内容"
        entry.score = 0.9
        store.asearch_memory = AsyncMock(return_value=[entry])
        pack = _make_pack(store)
        result = asyncio.run(pack._do_search(query="查询"))
        assert "相关记忆内容" in result
        store.asearch_memory.assert_awaited_once()

    def test_search_sync_fallback(self):
        store = MagicMock(spec=["search_memory"])
        store.search_memory = MagicMock(return_value=[])
        pack = _make_pack(store)
        result = asyncio.run(pack._do_search(query="查询"))
        assert "No relevant memories found." in result
        store.search_memory.assert_called_once()


class TestDoUserRemember:
    def _make_user_vault(self, user_md: str = ""):
        vault = MagicMock()
        written: dict = {}

        async def _read():
            return user_md

        async def _write(content):
            written["content"] = content

        vault.read_user_md = _read
        vault.write_user_md = _write
        vault._written = written
        return vault

    def _pack_with_user_vault(self, vault):
        store = _make_store(vault=None)
        return MemoryToolPack(memory_store=store, wing="default", user_vault=vault)

    def test_writes_user_md(self):
        vault = self._make_user_vault(
            "# 用户私有记忆（user.md）\n\n## Preferences\n"
        )
        pack = self._pack_with_user_vault(vault)
        result = asyncio.run(
            pack._do_user_remember(content="偏好简洁回复", category="preference")
        )
        import json

        payload = json.loads(result)
        assert payload["status"] == "remembered"
        assert payload["target"] == "user.md"
        out = vault._written.get("content", "")
        assert "偏好简洁回复" in out
        assert "[来源: user]" in out
        assert "## Preferences" in out

    def test_empty_doc_gets_user_md_header(self):
        vault = self._make_user_vault("")
        pack = self._pack_with_user_vault(vault)
        asyncio.run(pack._do_user_remember(content="喜欢中文", category="preference"))
        out = vault._written.get("content", "")
        assert out.startswith("# 用户私有记忆（user.md）")

    def test_unsupported_without_user_vault(self):
        store = _make_store(vault=None)
        pack = MemoryToolPack(memory_store=store, wing="default")
        result = asyncio.run(pack._do_user_remember(content="x"))
        import json

        assert json.loads(result)["status"] == "unsupported"

    def test_user_remember_registered_only_with_user_vault(self):
        """user_remember 仅在绑定 user vault 时注册,避免死工具。"""
        vault = self._make_user_vault()
        store = _make_store(vault=None)
        with_pack = MemoryToolPack(memory_store=store, wing="default", user_vault=vault)
        asyncio.run(with_pack.preload_resource())
        names = {getattr(r, "name", "") for r in with_pack.sub_resources}
        assert "user_remember" in names

        without_pack = MemoryToolPack(memory_store=store, wing="default")
        asyncio.run(without_pack.preload_resource())
        names = {getattr(r, "name", "") for r in without_pack.sub_resources}
        assert "user_remember" not in names


class TestCrossSessionReadWrite:
    """真 LocalVaultFS 跨会话语义:写 → 重建 store 实例 → 读回。"""

    def test_vault_store_write_then_new_instance_read(self, tmp_path):
        from gyra.knowledge.types import new_space_id
        from gyra_ext.knowledge.vaultfs import LocalVaultFS
        from gyra_ext.storage.memory.knowledge_vault_store import (
            KnowledgeVaultMemoryConfig,
            KnowledgeVaultMemoryStore,
        )

        async def _scenario():
            root = tmp_path / "space"
            space_id = new_space_id()

            # 会话 1:写
            vault1 = LocalVaultFS(space_id=space_id, root=root)
            await vault1.initialize()
            store1 = KnowledgeVaultMemoryStore(
                config=KnowledgeVaultMemoryConfig(space_slug="memory-x"), vault=vault1
            )
            await store1.awrite_memory(
                content="跨会话记忆条目", wing="default", room="general"
            )
            await vault1.close()

            # 会话 2:新 vault/store 实例读
            vault2 = LocalVaultFS(space_id=space_id, root=root)
            await vault2.initialize()
            store2 = KnowledgeVaultMemoryStore(
                config=KnowledgeVaultMemoryConfig(space_slug="memory-x"), vault=vault2
            )
            entries = await store2.asearch_memory(query="跨会话记忆", top_k=5)
            await vault2.close()
            return entries

        entries = asyncio.run(_scenario())
        assert any("跨会话记忆条目" in e.content for e in entries)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
