"""Tests for the agent overall memory document (AGENTS.md) maintenance.

Covers the four capabilities of the AGENTS.md high-value memory design:
1. `LongTermMemoryManager.maintain_agents_md` writes AGENTS.md from
   high-value items (LLM-screened or stable-fact fallback)
2. Deterministic fallback merge preserves user-authored content and
   routes facts into the right sections
3. Hard capacity limit: `_trim_agents_md_fallback` evicts lowest-value
   auto entries while always keeping `[来源: user]` lines
4. Auto Dream: `_dream_agents_md` periodically consolidates / trims
   the document, never dropping user-tagged entries
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from gyra.agent.core.memory.longterm_manager import (
    LongTermMemoryManager,
    LongTermMemoryConfig,
    _dream_agents_md,
    _facts_to_items,
    _merge_agents_md_fallback,
    _trim_agents_md_fallback,
)


def _fake_entry(content: str, room: str = "general") -> Any:
    e = MagicMock()
    e.content = content
    e.room = room
    return e


def _make_store(facts_by_room=None, agents_md="") -> Any:
    """Build a fake knowledge-vault store with alist_by_room + vault."""
    facts_by_room = facts_by_room or {}

    store = MagicMock()

    async def _alist(room, wing):
        return [_fake_entry(c, room) for c in facts_by_room.get(room, [])]
    store.alist_by_room = _alist

    vault = MagicMock()

    async def _read_agents_md():
        return agents_md
    vault.read_agents_md = _read_agents_md
    written: dict = {}

    async def _write_agents_md(content):
        written["content"] = content
    vault.write_agents_md = _write_agents_md
    vault._written = written
    vault.doc_list = AsyncMock(return_value=[])
    store.vault = vault
    return store


def _make_manager(store, processors=None) -> LongTermMemoryManager:
    cfg = LongTermMemoryConfig(
        memories=[{"memory_id": "s1", "memory_name": "space1"}],
        wing="default",
    )
    mgr = LongTermMemoryManager(
        config=cfg,
        memory_stores={"s1": store},
        processors=processors or {},
    )
    return mgr


def _make_processor(call_llm: Any) -> Any:
    """Build a processor mock exposing an async `_call_llm`."""
    processor = MagicMock()
    processor._call_llm = AsyncMock(side_effect=call_llm)
    return processor


class TestMaintainAgentsMd:
    def test_merges_profile_and_preference_facts(self):
        store = _make_store(
            facts_by_room={
                "profile": ["我是工程师团队助手"],
                "preference": ["用户偏好简洁中文回答"],
            },
            agents_md="# 测试 Agent 整体记忆（AGENTS.md）\n\n"
                      "## Identity\n<身份画像>\n\n"
                      "## Preferences\n<稳定偏好>\n\n"
                      "## Decisions\n\n## Conventions\n\n## Recent Updates\n",
        )
        mgr = _make_manager(store)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(mgr.maintain_agents_md("s1", store))
        assert result is True
        out = store.vault._written.get("content", "")
        assert "工程师团队助手" in out
        assert "简洁中文回答" in out

    def test_preserves_user_handwritten_content(self):
        store = _make_store(
            facts_by_room={"preference": ["用户偏好 dark mode"]},
            agents_md="# 测试 Agent 整体记忆（AGENTS.md）\n\n"
                      "## Identity\n我是用户手写的身份。\n\n"
                      "## Preferences\n用户偏好明亮主题。\n\n"
                      "## Decisions\n\n## Conventions\n\n## Recent Updates\n",
        )
        mgr = _make_manager(store)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(mgr.maintain_agents_md("s1", store))
        assert result is True
        out = store.vault._written.get("content", "")
        # 用户手写内容保留
        assert "用户手写的身份" in out
        assert "明亮主题" in out
        # 新事实合并
        assert "dark mode" in out

    def test_no_facts_skips_write(self):
        store = _make_store(facts_by_room={}, agents_md="# X\n\n## Identity\n测试\n")
        mgr = _make_manager(store)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(mgr.maintain_agents_md("s1", store))
        assert result is False
        assert store.vault._written.get("content") is None

    def test_llm_screens_history_when_processor_and_history_present(self):
        """With a processor + history, maintain uses LLM-screened items,
        not the static rooms fallback."""
        async def _call_llm(prompt):
            assert "对话" in prompt  # screening prompt
            return ('{"items": [{"category": "lesson", '
                    '"content": "字符串强转损坏二进制文件"}]}')
        processor = _make_processor(_call_llm)
        store = _make_store(
            facts_by_room={"preference": ["用户偏好 dark mode"]},
            agents_md="# X\n\n## Identity\n\n## Lessons\n\n## Preferences\n\n## Recent Updates\n",
        )
        mgr = _make_manager(store, processors={"s1": processor})
        loop = asyncio.get_event_loop()
        history = [{"role": "user", "content": "踩坑：二进制文件被损坏了"}]
        result = loop.run_until_complete(
            mgr.maintain_agents_md("s1", store, conversation_history=history)
        )
        assert result is True
        out = store.vault._written.get("content", "")
        # LLM 筛出的是 lesson 条目，不是静态 preference
        assert "字符串强转损坏二进制文件" in out
        assert "dark mode" not in out


class TestMergeFallback:
    def test_routes_facts_to_sections(self):
        existing = "# X\n\n## Identity\n\n## Preferences\n\n## Decisions\n\n## Conventions\n\n## Recent Updates\n"
        items = [
            {"category": "profile", "content": "我是工程师团队助手"},
            {"category": "preference", "content": "用户偏好简洁中文回答"},
            {"category": "memory", "content": "决策：采用事件驱动架构"},
        ]
        out = _merge_agents_md_fallback(existing, items)
        assert "工程师团队助手" in out
        assert "简洁中文回答" in out
        assert "事件驱动架构" in out

    def test_preserves_existing_content(self):
        existing = (
            "# X\n\n## Identity\n我是手写身份。\n\n"
            "## Preferences\n\n## Decisions\n\n## Conventions\n\n## Recent Updates\n"
        )
        items = [{"category": "preference", "content": "用户偏好 dark mode"}]
        out = _merge_agents_md_fallback(existing, items)
        assert "我是手写身份。" in out
        assert "dark mode" in out

    def test_dedupes_repeated_facts(self):
        existing = "# X\n\n## Identity\n\n## Preferences\n用户偏好简洁。\n\n## Decisions\n\n## Conventions\n\n## Recent Updates\n"
        items = [{"category": "preference", "content": "用户偏好简洁。"}]
        out = _merge_agents_md_fallback(existing, items)
        # 同一事实只出现一次
        assert out.count("用户偏好简洁。") == 1

    def test_routes_lesson_event_data_to_new_sections(self):
        existing = "# X\n\n## Identity\n\n## Preferences\n\n## Decisions\n\n## Conventions\n\n## Recent Updates\n"
        items = [
            {"category": "lesson", "content": "不用 str() 转 bytes"},
            {"category": "event", "content": "2026-08-01 上线 v2"},
            {"category": "data", "content": "AFS 路径 /data/afs"},
        ]
        out = _merge_agents_md_fallback(existing, items)
        assert "不用 str() 转 bytes" in out
        assert "2026-08-01 上线 v2" in out
        assert "AFS 路径 /data/afs" in out
        # 归入正确 section
        lessons = out.split("## Lessons", 1)[1].split("##", 1)[0]
        assert "不用 str() 转 bytes" in lessons


class TestScreenHighValueItems:
    def test_parses_llm_json_items(self):
        async def _call_llm(prompt):
            return ('```json\n{"items": ['
                    '{"category": "lesson", "content": "字符串强转损坏二进制"}, '
                    '{"category": "decision", "content": "统一走共享事件总线"}, '
                    '{"category": "data", "content": "AFS 路径 /data/afs"}]}\n```')
        processor = _make_processor(_call_llm)
        store = _make_store()
        mgr = _make_manager(store, processors={"s1": processor})
        loop = asyncio.get_event_loop()
        history = [
            {"role": "user", "content": "踩坑：字符串强转损坏二进制"},
            {"role": "assistant", "content": "建议统一走共享事件总线"},
        ]
        items = loop.run_until_complete(
            mgr._screen_high_value_items(processor, history)
        )
        assert len(items) == 3
        cats = {i["category"] for i in items}
        assert cats == {"lesson", "decision", "data"}

    def test_invalid_category_defaults_to_decision(self):
        async def _call_llm(prompt):
            return '{"items": [{"category": "weird", "content": "随便一条"}]}'
        processor = _make_processor(_call_llm)
        store = _make_store()
        mgr = _make_manager(store, processors={"s1": processor})
        loop = asyncio.get_event_loop()
        items = loop.run_until_complete(
            mgr._screen_high_value_items(processor, [{"role": "user", "content": "hi"}])
        )
        assert items == [{"category": "decision", "content": "随便一条"}]

    def test_empty_transcript_returns_empty(self):
        processor = _make_processor(lambda prompt: "unused")
        store = _make_store()
        mgr = _make_manager(store, processors={"s1": processor})
        loop = asyncio.get_event_loop()
        items = loop.run_until_complete(
            mgr._screen_high_value_items(processor, [{"role": "user", "content": "  "}])
        )
        assert items == []

    def test_llm_failure_returns_empty(self):
        async def _call_llm(prompt):
            raise RuntimeError("llm down")
        processor = _make_processor(_call_llm)
        store = _make_store()
        mgr = _make_manager(store, processors={"s1": processor})
        loop = asyncio.get_event_loop()
        items = loop.run_until_complete(
            mgr._screen_high_value_items(processor, [{"role": "user", "content": "hi"}])
        )
        assert items == []


class TestTrimAgentsMdFallback:
    def test_short_content_unchanged(self):
        content = "# X\n\n## Identity\nhi\n"
        assert _trim_agents_md_fallback(content, 100) == content

    def test_keeps_user_tagged_lines_under_pressure(self):
        content = (
            "# X\n\n## Identity\n身份行 [来源: user]\n\n## Lessons\n"
            + "".join(f"- 自动条目 {i}\n" for i in range(30))
            + "- 用户易错点 [来源: user]\n"
        )
        out = _trim_agents_md_fallback(content, 60)
        assert len(out) <= 60
        # 用户标记条目永不淘汰
        assert "[来源: user]" in out
        assert "用户易错点" in out

    def test_over_limit_returns_trimmed(self):
        content = "# X\n\n## Identity\n" + "- x" * 200 + "\n"
        out = _trim_agents_md_fallback(content, 100)
        assert len(out) <= 100
        assert out.strip()


class TestDreamAgentsMd:
    def test_empty_content_returns_none(self):
        loop = asyncio.get_event_loop()
        assert loop.run_until_complete(_dream_agents_md("", None, 4000)) is None

    def test_within_limit_no_llm_returns_content(self):
        content = "# X\n\n## Identity\nhi\n"
        loop = asyncio.get_event_loop()
        out = loop.run_until_complete(_dream_agents_md(content, None, 4000))
        assert out == content.strip()

    def test_over_limit_no_llm_trims_preserving_user(self):
        content = (
            "# X\n\n## Lessons\n"
            + "".join(f"- 自动 {i}\n" for i in range(60))
            + "- 用户易错点 [来源: user]\n"
        )
        loop = asyncio.get_event_loop()
        out = loop.run_until_complete(_dream_agents_md(content, None, 120))
        assert len(out) <= 120
        assert "[来源: user]" in out

    def test_with_llm_uses_processor(self):
        content = "# X\n\n## Lessons\n- 自动条目\n- 用户易错点 [来源: user]\n"
        dreamed = "# Dreamed\n\n## Lessons\n- 用户易错点 [来源: user]"
        loop = asyncio.get_event_loop()
        with patch(
            "gyra.storage.memory.llm_processor.LLMMemoryProcessor"
        ) as MockProcessor:
            proc = MagicMock()
            proc._call_llm = AsyncMock(return_value=dreamed)
            MockProcessor.return_value = proc
            out = loop.run_until_complete(
                _dream_agents_md(content, MagicMock(), 4000)
            )
        assert out == dreamed
        proc._call_llm.assert_awaited_once()


class TestFactsToItems:
    def test_parses_room_bullets(self):
        items = _facts_to_items(
            "- [profile] 我是工程师\n- [preference] 用户偏好简洁\n"
            "- [memory] 决策：事件驱动\n- 无标签行\n"
        )
        assert items[0] == {"category": "profile", "content": "我是工程师"}
        assert items[1] == {"category": "preference", "content": "用户偏好简洁"}
        assert items[2] == {"category": "memory", "content": "决策：事件驱动"}
        # 无标签行归为 decision
        assert items[3] == {"category": "decision", "content": "无标签行"}

    def test_empty_returns_empty_list(self):
        assert _facts_to_items("") == []
        assert _facts_to_items("   \n  \n") == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
