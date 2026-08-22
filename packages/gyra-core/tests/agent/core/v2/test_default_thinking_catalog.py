"""default_thinking_fn 接入 SkillCatalogConsumer / DbCatalogConsumer 的测试。

覆盖：
  - thinking_fn 拼 messages 时把 skill / db catalog reminder 作为 user-role
    ``<system-reminder>`` 注入；**不**进 system prompt；
  - catalog 空时不注入；
  - catalog_consumer 抛错时 thinking 不崩溃（降级跳过）；
  - 同一 digest 不会重复注入（首次 initial，后续 refresh 不变时 None）；
  - 注入位置：memory 之后、build_out 之前、user_prompt 之前。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from gyra.agent.core.v2.default_thinking import make_default_thinking_fn
from gyra.agent.core.v2.db_consumer import DbCatalogConsumer
from gyra.agent.core.v2.skills.catalog_consumer import SkillCatalogConsumer
from gyra.agent.core.v2.skills.registry import (
    LAYER_HOST,
    SkillRegistry,
)
from gyra.agent.core.v2.thinking_chunk import TokenChunk


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def _fake_llm_stream_empty(messages, model):
    """记录收到的 messages；只 yield 1 个 token chunk。"""
    _fake_llm_stream_empty.captured_messages = list(messages)
    yield {"token": "ok"}


def _build_thinking(
    *,
    catalog_consumer=None,
    db_catalog_consumer=None,
    memory_context: str = "",
):
    # Memory bundle mock
    pipeline = MagicMock()
    pipeline.scrub_stream_delta = MagicMock(side_effect=lambda t: t)
    pipeline.consume_prefetch = AsyncMock(return_value=memory_context)
    bundle = MagicMock()
    bundle.pipeline = pipeline
    bundle.manager = MagicMock()
    bundle.manager.retrieve_relevant_memories = AsyncMock(return_value=memory_context)

    thinking_fn = make_default_thinking_fn(
        llm_stream_fn=_fake_llm_stream_empty,
        model_alias="test-model",
        memory_bundle=bundle,
        context_provider=lambda *a, **k: [
            {"role": "user", "content": "BASE_FROM_ENGINE"}
        ],
        system_prompt="SYSTEM_PROMPT_BASE",
        catalog_consumer=catalog_consumer,
        db_catalog_consumer=db_catalog_consumer,
    )
    return thinking_fn


async def _collect_messages(thinking_fn) -> List[Dict[str, Any]]:
    chunks = []
    async for c in thinking_fn({
        "prompt": "USER_PROMPT",
        "conv_id": "c1",
        "session_id": "s1",
    }):
        chunks.append(c)
    return _fake_llm_stream_empty.captured_messages


# --------------------------------------------------------------------------- #
# Skill catalog reminder 注入
# --------------------------------------------------------------------------- #


async def test_skill_catalog_injects_user_role_reminder():
    """非空 catalog → 注入 user-role <system-reminder>（不进 system prompt）。"""
    reg = SkillRegistry()
    from gyra.agent.core.v2.skills.registry import (
        SkillInvocation, SkillProvider, SkillSummary, SkillLookupOptions,
    )

    class _P(SkillProvider):
        def __init__(self):
            super().__init__(name="h")
        async def list(self, options):
            return [SkillSummary(
                name="alpha", description="desc", invocation=SkillInvocation.BOTH,
                source="t", provider="h", path="p",
            )]
        async def get(self, name, options):
            return None

    reg.register_provider(LAYER_HOST, _P())
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    thinking_fn = _build_thinking(catalog_consumer=consumer)
    msgs = await _collect_messages(thinking_fn)
    # 至少 4 条：system / user(memory) / user(skill reminder) / user(extra) / user(prompt)
    # 我们关心 reminder 的位置与 role
    skill_msgs = [
        m for m in msgs
        if m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and "<available_skills>" in m["content"]
    ]
    assert len(skill_msgs) == 1
    # system prompt 不含 catalog
    sys_msg = next(m for m in msgs if m.get("role") == "system")
    assert "<available_skills>" not in sys_msg["content"]
    # skill reminder 在 user_prompt 之前
    prompt_idx = next(
        (i for i, m in enumerate(msgs) if m.get("content") == "USER_PROMPT"),
    )
    skill_idx = msgs.index(skill_msgs[0])
    assert skill_idx < prompt_idx


async def test_skill_catalog_empty_no_inject():
    """空 catalog → 不注入（避免污染 LLM 上下文）。"""
    reg = SkillRegistry()  # 全部空
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    thinking_fn = _build_thinking(catalog_consumer=consumer)
    msgs = await _collect_messages(thinking_fn)
    # 无 <available_skills>
    assert not any(
        isinstance(m.get("content"), str) and "<available_skills>" in m["content"]
        for m in msgs
    )


async def test_skill_catalog_unchanged_no_repeat_inject():
    """digest 不变 → 第二次 thinking 不重复注入。"""
    reg = SkillRegistry()
    from gyra.agent.core.v2.skills.registry import (
        SkillInvocation, SkillProvider, SkillSummary, SkillLookupOptions,
    )

    class _P(SkillProvider):
        def __init__(self):
            super().__init__(name="h")
        async def list(self, options):
            return [SkillSummary(
                name="alpha", description="desc", invocation=SkillInvocation.BOTH,
                source="t", provider="h", path="p",
            )]
        async def get(self, name, options):
            return None

    reg.register_provider(LAYER_HOST, _P())
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    thinking_fn = _build_thinking(catalog_consumer=consumer)
    # 第一次：注入
    msgs1 = await _collect_messages(thinking_fn)
    skill_msgs1 = [
        m for m in msgs1
        if isinstance(m.get("content"), str) and "<available_skills>" in m["content"]
    ]
    assert len(skill_msgs1) == 1
    # 第二次：digest 稳定 → 不注入
    msgs2 = await _collect_messages(thinking_fn)
    skill_msgs2 = [
        m for m in msgs2
        if isinstance(m.get("content"), str) and "<available_skills>" in m["content"]
    ]
    assert len(skill_msgs2) == 0


async def test_skill_catalog_consumer_failure_does_not_crash():
    """catalog_consumer 抛错 → thinking 不崩溃（降级跳过）。"""
    consumer = MagicMock()
    consumer._last_published_digest = None
    consumer.initial = AsyncMock(side_effect=RuntimeError("boom"))
    thinking_fn = _build_thinking(catalog_consumer=consumer)
    # 不应抛错
    msgs = await _collect_messages(thinking_fn)
    # 至少走到 LLM stream（chunks 非空）
    # messages 仍含 user_prompt
    assert any(m.get("content") == "USER_PROMPT" for m in msgs)


# --------------------------------------------------------------------------- #
# DB catalog reminder 注入
# --------------------------------------------------------------------------- #


async def test_db_catalog_injects_user_role_reminder():
    """非空 DB 列表 → 注入 <available_databases> reminder（user role）。"""
    items = [{
        "db_name": "alpha", "db_type": "mysql", "dialect": "mysql",
        "datasource_id": 1, "description": "main db",
    }]
    consumer = DbCatalogConsumer(provider=items)
    thinking_fn = _build_thinking(db_catalog_consumer=consumer)
    msgs = await _collect_messages(thinking_fn)
    db_msgs = [
        m for m in msgs
        if m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and "<available_databases>" in m["content"]
    ]
    assert len(db_msgs) == 1
    # system prompt 不含 DB catalog
    sys_msg = next(m for m in msgs if m.get("role") == "system")
    assert "<available_databases>" not in sys_msg["content"]
    # 位置：在 user_prompt 之前
    prompt_idx = next(
        (i for i, m in enumerate(msgs) if m.get("content") == "USER_PROMPT"),
    )
    db_idx = msgs.index(db_msgs[0])
    assert db_idx < prompt_idx


async def test_db_catalog_empty_no_inject():
    consumer = DbCatalogConsumer(provider=[])
    thinking_fn = _build_thinking(db_catalog_consumer=consumer)
    msgs = await _collect_messages(thinking_fn)
    assert not any(
        isinstance(m.get("content"), str) and "<available_databases>" in m["content"]
        for m in msgs
    )


async def test_db_catalog_consumer_failure_does_not_crash():
    consumer = MagicMock()
    consumer._last_published_digest = None
    consumer.initial = AsyncMock(side_effect=RuntimeError("boom"))
    thinking_fn = _build_thinking(db_catalog_consumer=consumer)
    msgs = await _collect_messages(thinking_fn)
    assert any(m.get("content") == "USER_PROMPT" for m in msgs)


# --------------------------------------------------------------------------- #
# 同时注入 skill + db catalog
# --------------------------------------------------------------------------- #


async def test_skill_and_db_catalog_inject_together():
    """skill + db catalog 同时存在 → 各自注入一条 reminder。"""
    # skill
    from gyra.agent.core.v2.skills.registry import (
        SkillInvocation, SkillProvider, SkillSummary,
    )

    class _P(SkillProvider):
        def __init__(self):
            super().__init__(name="h")
        async def list(self, options):
            return [SkillSummary(
                name="alpha", description="d", invocation=SkillInvocation.BOTH,
                source="t", provider="h", path="p",
            )]
        async def get(self, name, options):
            return None

    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _P())
    skill_consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    # db
    db_consumer = DbCatalogConsumer(provider=[{
        "db_name": "alpha", "db_type": "mysql", "dialect": "mysql",
        "datasource_id": 1, "description": "main",
    }])
    thinking_fn = _build_thinking(
        catalog_consumer=skill_consumer, db_catalog_consumer=db_consumer,
    )
    msgs = await _collect_messages(thinking_fn)
    skill_msgs = [
        m for m in msgs
        if isinstance(m.get("content"), str) and "<available_skills>" in m["content"]
    ]
    db_msgs = [
        m for m in msgs
        if isinstance(m.get("content"), str) and "<available_databases>" in m["content"]
    ]
    assert len(skill_msgs) == 1
    assert len(db_msgs) == 1


# --------------------------------------------------------------------------- #
# TODO 列表**不**进 system prompt（DSH 行为不变）
# --------------------------------------------------------------------------- #


async def test_todo_not_in_system_prompt():
    """TODO 列表**不**进 system prompt（避免污染 KV-cache）。"""
    thinking_fn = _build_thinking()
    msgs = await _collect_messages(thinking_fn)
    sys_msg = next(m for m in msgs if m.get("role") == "system")
    # system prompt 仅含 V1 静态内容；TODO 进度由 todowrite 工具参数 + 结果回显
    assert "TODO" not in sys_msg["content"]
    assert "<todo" not in sys_msg["content"].lower()


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
