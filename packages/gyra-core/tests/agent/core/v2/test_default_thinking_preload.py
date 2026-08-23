"""default_thinking_fn 预加载技能注入测试（V2：user-role <system-reminder>）。

覆盖：
  - preloaded_skills_provider 返回 XML 列表 → user-role <loaded_skills>
    reminder 注入，**不**进 system prompt（KV-cache 稳定前缀不被污染）；
  - provider 返回 None / 空 → 不注入；
  - provider 抛错 → thinking 不崩溃（降级跳过）；
  - 注入位置：在 user_prompt 之前。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from gyra.agent.core.v2.default_thinking import make_default_thinking_fn

_SKILL_XML = (
    '<skill_content name="测试技能">\n'
    "# 指令正文\n\n完整内容 line2\n完整内容 line3\n"
    "</skill_content>"
)


# --------------------------------------------------------------------------- #
# Helpers（对齐 test_default_thinking_catalog.py）
# --------------------------------------------------------------------------- #


async def _fake_llm_stream_empty(messages, model):
    _fake_llm_stream_empty.captured_messages = list(messages)
    yield {"token": "ok"}


def _build_thinking(*, preloaded_skills_provider=None):
    pipeline = MagicMock()
    pipeline.scrub_stream_delta = MagicMock(side_effect=lambda t: t)
    pipeline.consume_prefetch = AsyncMock(return_value=None)
    bundle = MagicMock()
    bundle.pipeline = pipeline
    bundle.manager = MagicMock()
    bundle.manager.retrieve_relevant_memories = AsyncMock(return_value=None)

    thinking_fn = make_default_thinking_fn(
        llm_stream_fn=_fake_llm_stream_empty,
        model_alias="test-model",
        memory_bundle=bundle,
        context_provider=lambda *a, **k: [
            {"role": "user", "content": "BASE_FROM_ENGINE"}
        ],
        system_prompt="SYSTEM_PROMPT_BASE",
        preloaded_skills_provider=preloaded_skills_provider,
    )
    return thinking_fn


async def _collect_messages(thinking_fn) -> List[Dict[str, Any]]:
    chunks = []
    async for c in thinking_fn(
        {
            "prompt": "USER_PROMPT",
            "conv_id": "c1",
            "session_id": "s1",
        }
    ):
        chunks.append(c)
    return _fake_llm_stream_empty.captured_messages


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


async def test_preloaded_skills_inject_user_role_reminder():
    """预加载技能 → user-role <loaded_skills> reminder 注入，不进 system。"""
    thinking_fn = _build_thinking(
        preloaded_skills_provider=lambda: [_SKILL_XML]
    )
    msgs = await _collect_messages(thinking_fn)

    preload_msgs = [
        m for m in msgs
        if m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and "<loaded_skills>" in m["content"]
    ]
    assert len(preload_msgs) == 1
    content = preload_msgs[0]["content"]
    assert content.startswith("<system-reminder>")
    assert "<skill_content name=\"测试技能\">" in content
    assert "完整内容 line2" in content
    assert "已预加载到当前对话上下文" in content
    # system prompt 不含预加载内容
    sys_msg = next(m for m in msgs if m.get("role") == "system")
    assert "<loaded_skills>" not in sys_msg["content"]
    assert "完整内容 line2" not in sys_msg["content"]
    # 在 user_prompt 之前
    prompt_idx = next(
        i for i, m in enumerate(msgs) if m.get("content") == "USER_PROMPT"
    )
    preload_idx = msgs.index(preload_msgs[0])
    assert preload_idx < prompt_idx


async def test_preloaded_skills_provider_none_no_inject():
    thinking_fn = _build_thinking(preloaded_skills_provider=lambda: None)
    msgs = await _collect_messages(thinking_fn)
    preload_msgs = [
        m for m in msgs
        if isinstance(m.get("content"), str) and "<loaded_skills>" in m["content"]
    ]
    assert preload_msgs == []


async def test_preloaded_skills_provider_empty_no_inject():
    thinking_fn = _build_thinking(preloaded_skills_provider=lambda: [])
    msgs = await _collect_messages(thinking_fn)
    preload_msgs = [
        m for m in msgs
        if isinstance(m.get("content"), str) and "<loaded_skills>" in m["content"]
    ]
    assert preload_msgs == []


async def test_preloaded_skills_provider_error_degrades_gracefully():
    def _boom():
        raise RuntimeError("provider exploded")

    thinking_fn = _build_thinking(preloaded_skills_provider=_boom)
    msgs = await _collect_messages(thinking_fn)
    # 不崩溃；有 system + user_prompt，无 loaded_skills
    roles = [m.get("role") for m in msgs]
    assert "system" in roles
    assert any(m.get("content") == "USER_PROMPT" for m in msgs)
    assert not any(
        isinstance(m.get("content"), str) and "<loaded_skills>" in m["content"]
        for m in msgs
    )


async def test_preloaded_skills_async_provider_supported():
    async def _async_provider():
        return [_SKILL_XML]

    thinking_fn = _build_thinking(preloaded_skills_provider=_async_provider)
    msgs = await _collect_messages(thinking_fn)
    assert any(
        m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and "<loaded_skills>" in m["content"]
        for m in msgs
    )
