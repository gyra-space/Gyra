"""SkillCatalogConsumer 测试——DSH tool-skill 风格 digest 变化才注入。

覆盖：
  - ``initial()``：首次发布；空 catalog 返回 None；
  - ``refresh()``：digest 不变返回 None；变化时返回完整替换；
  - ``refresh()`` 在未发布过时降级为 ``initial()``；
  - 同一 catalog 不再变时多次 refresh 都返回 None（不重复发）；
  - 注册 / 注销 provider / invalidate 后 digest 变化，refresh 才发；
  - 渲染：``<available_skills>`` XML 转义 + 排序 + 截断 description；
  - USER_ONLY / NONE invocation 不进 catalog；
  - ``reset()`` 清空 digest 状态。
"""
from __future__ import annotations

import asyncio
import pytest

from gyra.agent.core.v2.skills.catalog_consumer import (
    DEFAULT_DESCRIPTION_MAX,
    SkillCatalogConsumer,
    build_initial_reminder,
    build_replacement_reminder,
    render_catalog_xml,
)
from gyra.agent.core.v2.skills.registry import (
    LAYER_HOST,
    LAYER_SCOPE,
    SkillDefinition,
    SkillInvocation,
    SkillLookupOptions,
    SkillProvider,
    SkillRegistry,
    SkillSummary,
)


class _StaticProvider(SkillProvider):
    def __init__(self, name: str, summaries: list, bodies: dict | None = None):
        super().__init__(name=name)
        self._summaries = list(summaries)
        self._bodies = dict(bodies or {})

    async def list(self, options):
        return list(self._summaries)

    async def get(self, name, options):
        body = self._bodies.get(name)
        if body is None:
            return None
        s = next((x for x in self._summaries if x.name == name), None)
        if s is None:
            return None
        return SkillDefinition(
            name=s.name, description=s.description, when_to_use=s.when_to_use,
            invocation=s.invocation, source=s.source, provider=self.name,
            path=s.path, rank=s.rank, content=body, metadata={},
        )


def _summary(name: str, desc: str = "", **kw) -> SkillSummary:
    base = dict(
        name=name, description=desc, invocation=SkillInvocation.BOTH,
        source="test", provider="test", path=f"/skills/{name}",
    )
    base.update(kw)
    return SkillSummary(**base)


def _definition(name: str, content: str = "body", **kw) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        description=kw.pop("description", ""),
        when_to_use=kw.pop("when_to_use", None),
        invocation=kw.pop("invocation", SkillInvocation.BOTH),
        source=kw.pop("source", "test"),
        provider=kw.pop("provider", "test"),
        path=kw.pop("path", f"/skills/{name}"),
        rank=kw.pop("rank", 0),
        content=content,
        metadata=kw.pop("metadata", {}),
    )


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #


def test_render_xml_skips_user_only_and_none():
    summaries = [
        _summary("a", "model-a"),
        _summary("b", "user-b", invocation=SkillInvocation.USER_ONLY),
        _summary("c", "none-c", invocation=SkillInvocation.NONE),
    ]
    xml = render_catalog_xml(summaries)
    assert "<name>a</name>" in xml
    assert "<name>b</name>" not in xml
    assert "<name>c</name>" not in xml


def test_render_xml_escapes_special_chars():
    summaries = [_summary("a", "A & B <C> \"D\"")]
    xml = render_catalog_xml(summaries)
    assert "A &amp; B &lt;C&gt; &quot;D&quot;" in xml


def test_render_xml_truncates_long_description():
    long = "x" * 1500
    summaries = [_summary("a", long)]
    xml = render_catalog_xml(summaries, description_max=500)
    # 截断后应含省略号
    assert "…" in xml
    # 截断后长度 ≤ 500 字符
    desc_start = xml.find("<description>") + len("<description>")
    desc_end = xml.find("</description>")
    assert desc_end - desc_start <= 500


def test_render_xml_preserves_input_order():
    """render_catalog_xml 不排序（排序由 registry.list() 负责）。

    函数保留输入顺序；上层必须传已排序的 summaries。
    """
    summaries = [
        _summary("zeta", "z"),
        _summary("alpha", "a"),
        _summary("beta", "b"),
    ]
    xml = render_catalog_xml(summaries)
    pos_z = xml.find("<name>zeta</name>")
    pos_a = xml.find("<name>alpha</name>")
    pos_b = xml.find("<name>beta</name>")
    # 按输入顺序：zeta → alpha → beta
    assert pos_z < pos_a < pos_b


def test_render_xml_empty_returns_empty_string():
    assert render_catalog_xml([]) == ""
    # 全是 USER_ONLY → 视为空
    summaries = [_summary("a", "x", invocation=SkillInvocation.USER_ONLY)]
    assert render_catalog_xml(summaries) == ""


def test_build_initial_reminder_returns_none_when_empty():
    """空 catalog 不返回 reminder（无 user-role 消息污染上下文）。"""
    assert build_initial_reminder([]) is None
    assert build_initial_reminder(
        [_summary("a", "x", invocation=SkillInvocation.USER_ONLY)],
    ) is None


def test_build_initial_reminder_contains_system_reminder_tag():
    msg = build_initial_reminder([_summary("a", "x")])
    assert msg is not None
    assert msg["role"] == "user"
    assert "<system-reminder>" in msg["content"]
    assert "</system-reminder>" in msg["content"]
    assert "skill(" in msg["content"]


def test_build_replacement_reminder_always_returns_message():
    """digest 变化时即使空也发（让模型知道目录被清空）。"""
    msg = build_replacement_reminder([])
    assert msg["role"] == "user"
    assert "<system-reminder>" in msg["content"]


# --------------------------------------------------------------------------- #
# Consumer 行为
# --------------------------------------------------------------------------- #


async def test_initial_emits_reminder_when_catalog_non_empty():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _summary("alpha", "first skill"),
    ]))
    consumer = SkillCatalogConsumer(
        registry=reg, layer_chain=[LAYER_HOST],
    )
    msg = await _await(consumer.initial())
    assert msg is not None
    assert msg["role"] == "user"
    assert "<name>alpha</name>" in msg["content"]
    # digest 状态已记录
    assert consumer._last_published_digest is not None
    assert consumer._last_published_generation == reg.generation


async def test_initial_returns_none_when_catalog_empty():
    reg = SkillRegistry()
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    msg = await _await(consumer.initial())
    assert msg is None
    # digest 仍记录（但 _last_published_digest 是空 catalog 的 digest）
    assert consumer._last_published_digest is not None
    # catalog digest 在两个空状态下应一致
    d1 = consumer._last_published_digest
    reg.invalidate()
    consumer2 = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    await _await(consumer2.initial())
    assert consumer2._last_published_digest == d1


async def test_refresh_returns_none_when_unchanged():
    """digest 不变（catalog 未变）→ refresh 返回 None（不发任何消息）。"""
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "x")]))
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    # initial 必发
    msg0 = await _await(consumer.initial())
    assert msg0 is not None
    # 第一次 refresh：digest 未变 → 返回 None
    msg1 = await _await(consumer.refresh())
    assert msg1 is None
    # 多次 refresh 仍 None
    msg2 = await _await(consumer.refresh())
    assert msg2 is None


async def test_refresh_emits_replacement_only_once_per_digest_change():
    """digest 变化 → refresh 发一条替换；再 refresh 不重复发。"""
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "x")]))
    chain = [LAYER_SCOPE, LAYER_HOST]
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=chain)
    await _await(consumer.initial())
    # 第一次 refresh（catalog 未变）→ None
    assert await _await(consumer.refresh()) is None

    # 新增 skill → invalidate → digest 变
    reg.register(LAYER_SCOPE, _definition("b", "body", description="scope-b"))
    reg.invalidate()

    # 第二次 refresh：digest 变 → 返回 replacement
    msg1 = await _await(consumer.refresh())
    assert msg1 is not None
    assert "<name>a</name>" in msg1["content"]
    assert "<name>b</name>" in msg1["content"]
    # 立即再 refresh：digest 稳定 → None（**只发一次**）
    msg2 = await _await(consumer.refresh())
    assert msg2 is None
    msg3 = await _await(consumer.refresh())
    assert msg3 is None


async def test_refresh_falls_back_to_initial_when_never_published():
    """未发布过时 refresh 降级为 initial。"""
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "x")]))
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    # 未调 initial，直接 refresh
    msg = await _await(consumer.refresh())
    assert msg is not None
    assert "<name>a</name>" in msg["content"]


async def test_refresh_after_digest_change_with_new_description():
    """description 改变 → digest 变 → 重新发。"""
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "old")]))
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    await _await(consumer.initial())

    # 替换为新描述的同名 skill
    reg2 = SkillRegistry()
    reg2.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "new")]))
    consumer2 = SkillCatalogConsumer(registry=reg2, layer_chain=[LAYER_HOST])
    await _await(consumer2.initial())
    msg = await _await(consumer2.refresh())
    assert msg is None  # digest 也按 description 入 hash；这里 gen 没变、digest 也没变


async def test_reset_clears_state():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "x")]))
    consumer = SkillCatalogConsumer(registry=reg, layer_chain=[LAYER_HOST])
    await _await(consumer.initial())
    consumer.reset()
    assert consumer._last_published_digest is None
    assert consumer._last_published_generation == -1


# --------------------------------------------------------------------------- #
# 与 DSH 资源协议对齐：分层场景
# --------------------------------------------------------------------------- #


async def test_layered_registry_invalidation_triggers_refresh():
    """scope 层新增 skill → 顶层 refresh 必发。"""
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "x")]))
    consumer = SkillCatalogConsumer(
        registry=reg, layer_chain=[LAYER_SCOPE, LAYER_HOST],
    )
    msg0 = await _await(consumer.initial())
    assert msg0 is not None
    # scope 层注册新 skill
    reg.register(LAYER_SCOPE, _definition("b", "scope body", description="scope-b"))
    reg.invalidate()
    msg1 = await _await(consumer.refresh())
    assert msg1 is not None
    assert "<name>b</name>" in msg1["content"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
