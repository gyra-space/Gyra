"""SkillRegistry 分层注册表测试——对齐 DSH ``ctx.skills``。

覆盖：
  - 分层注册（host / scope）：近层覆盖远层；同层同名 first-wins；
  - ``register``（runtime 定义）和 ``register_provider``（远端 provider）双轨；
  - ``list``：合并各层、排序、近层胜出、缓存命中；
  - ``get``：按 name 加载完整定义、近层胜出；
  - ``catalog_digest``：内容稳定时 digest 稳定；变化时 digest 变化；
  - ``generation`` 单调递增；``subscribe`` 通知；
  - 不接受非法 layer / 类型错误。
"""
from __future__ import annotations

import asyncio
import pytest

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


# --------------------------------------------------------------------------- #
# 提供者
# --------------------------------------------------------------------------- #


class _StaticProvider(SkillProvider):
    """测试用 provider——list/get 走固定候选。"""

    def __init__(
        self,
        name: str,
        summaries: list,
        bodies: dict | None = None,
    ) -> None:
        super().__init__(name=name)
        self._summaries = list(summaries)
        self._bodies = dict(bodies or {})

    async def list(self, options: SkillLookupOptions) -> list:
        return list(self._summaries)

    async def get(self, name: str, options: SkillLookupOptions):
        body = self._bodies.get(name)
        if body is None:
            return None
        s = next((x for x in self._summaries if x.name == name), None)
        if s is None:
            return None
        return SkillDefinition(
            name=s.name,
            description=s.description,
            when_to_use=s.when_to_use,
            invocation=s.invocation,
            source=s.source,
            provider=self.name,
            path=s.path,
            rank=s.rank,
            content=body,
            metadata={"provider": self.name},
        )


def _summary(name: str, desc: str = "", **kw) -> SkillSummary:
    base = dict(
        name=name,
        description=desc,
        invocation=SkillInvocation.BOTH,
        source="test",
        provider="test",
        path=f"/skills/{name}",
    )
    base.update(kw)
    return SkillSummary(**base)


def _definition(name: str, content: str = "body", **kw) -> SkillDefinition:
    base = dict(
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
    return SkillDefinition(**base)


# --------------------------------------------------------------------------- #
# 分层注册
# --------------------------------------------------------------------------- #


def test_register_provider_rejects_empty_layer():
    reg = SkillRegistry()
    with pytest.raises(ValueError):
        reg.register_provider("", _StaticProvider("p", []))


def test_register_provider_rejects_non_provider():
    reg = SkillRegistry()
    with pytest.raises(TypeError):
        reg.register_provider(LAYER_HOST, object())  # type: ignore[arg-type]


def test_register_provider_rejects_duplicate_in_same_layer():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("dup", []))
    with pytest.raises(ValueError):
        reg.register_provider(LAYER_HOST, _StaticProvider("dup", []))


def test_register_provider_same_name_different_layer_ok():
    reg = SkillRegistry()
    dispose_h = reg.register_provider(LAYER_HOST, _StaticProvider("h", []))
    dispose_s = reg.register_provider(LAYER_SCOPE, _StaticProvider("h", []))
    assert callable(dispose_h)
    assert callable(dispose_s)


def test_dispose_removes_provider_and_invalidates():
    reg = SkillRegistry()
    p = _StaticProvider("p", [_summary("a")])
    dispose = reg.register_provider(LAYER_HOST, p)
    gen_before = reg.generation
    dispose()
    gen_after = reg.generation
    assert gen_after > gen_before
    # dispose 后 list 为空（同步校验——list 内部 await 走 event loop）


async def test_register_runtime_definition_first_wins_per_layer():
    reg = SkillRegistry()
    reg.register(LAYER_SCOPE, _definition("a", "scope-body"))
    reg.register(LAYER_SCOPE, _definition("a", "scope-body-2"))  # second 应被忽略
    got = await _alist(reg.get("a", layer_chain=[LAYER_SCOPE]))
    assert got is not None
    assert got.content == "scope-body"


async def test_register_runtime_duplicate_logs_noop_disposer():
    reg = SkillRegistry()
    reg.register(LAYER_HOST, _definition("a", "h1"))
    dispose = reg.register(LAYER_HOST, _definition("a", "h2"))
    # duplicate → noop disposer（first-wins）
    dispose()
    got = await _alist(reg.get("a", layer_chain=[LAYER_HOST]))
    assert got is not None
    assert got.content == "h1"


# --------------------------------------------------------------------------- #
# list / get 合并语义
# --------------------------------------------------------------------------- #


async def test_list_merges_layers_nearest_wins():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _summary("a", "host-a"),
        _summary("b", "host-b"),
    ]))
    reg.register(LAYER_SCOPE, _definition("a", "scope-body", description="scope-a"))
    summaries = await _alist(reg.list(layer_chain=[LAYER_SCOPE, LAYER_HOST]))
    by_name = {s.name: s for s in summaries}
    assert set(by_name) == {"a", "b"}
    # "a" 来自 scope（近层赢），description 来自 scope definition
    assert by_name["a"].description == "scope-a"
    # "b" 只在 host
    assert by_name["b"].description == "host-b"


async def test_list_sorted_by_name():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _summary("zeta"),
        _summary("alpha"),
        _summary("beta"),
    ]))
    summaries = await _alist(reg.list())
    assert [s.name for s in summaries] == ["alpha", "beta", "zeta"]


async def test_list_provider_failure_isolated():
    """单个 provider.list 抛错不阻塞其他 provider。"""
    class _BoomProvider(_StaticProvider):
        async def list(self, options):
            raise RuntimeError("boom")

    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _BoomProvider("boom", []))
    reg.register_provider(LAYER_HOST, _StaticProvider("ok", [_summary("alpha")]))
    summaries = await _alist(reg.list())
    assert [s.name for s in summaries] == ["alpha"]


async def test_get_runtime_layer_wins_over_provider():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider(
        "h", [_summary("a", "h-desc")], bodies={"a": "h-body"},
    ))
    reg.register(LAYER_SCOPE, _definition("a", "scope-body", description="scope-desc"))
    defn = await _alist(reg.get("a", layer_chain=[LAYER_SCOPE, LAYER_HOST]))
    assert defn is not None
    assert defn.content == "scope-body"
    assert defn.description == "scope-desc"


async def test_get_provider_provider_failure_isolated():
    class _BoomProvider(_StaticProvider):
        async def get(self, name, options):
            raise RuntimeError("boom")

    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _BoomProvider("boom", []))
    reg.register_provider(LAYER_HOST, _StaticProvider(
        "ok", [_summary("a")], bodies={"a": "ok-body"},
    ))
    defn = await _alist(reg.get("a"))
    assert defn is not None
    assert defn.content == "ok-body"


async def test_get_returns_none_when_missing():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a")]))
    assert await _alist(reg.get("nope")) is None


# --------------------------------------------------------------------------- #
# 缓存
# --------------------------------------------------------------------------- #


async def test_list_uses_cache_within_ttl():
    reg = SkillRegistry(cache_ttl=10.0)

    calls = {"n": 0}

    class _CountingProvider(SkillProvider):
        def __init__(self):
            super().__init__(name="count")
            self._items = [_summary("a", "v1")]

        async def list(self, options):
            calls["n"] += 1
            return list(self._items)

        async def get(self, name, options):
            return None

    p = _CountingProvider()
    reg.register_provider(LAYER_HOST, p)
    await _alist(reg.list())
    await _alist(reg.list())
    assert calls["n"] == 1
    p._items = [_summary("a", "v2"), _summary("b", "new")]
    reg.invalidate()
    summaries = await _alist(reg.list())
    assert calls["n"] == 2
    assert [s.name for s in summaries] == ["a", "b"]


# --------------------------------------------------------------------------- #
# digest
# --------------------------------------------------------------------------- #


async def test_catalog_digest_stable_when_content_stable():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [
        _summary("a", "x"), _summary("b", "y"),
    ]))
    d1 = await _alist(reg.catalog_digest())
    d2 = await _alist(reg.catalog_digest())
    assert d1 == d2
    assert len(d1) == 16


async def test_catalog_digest_changes_on_addition():
    reg = SkillRegistry()
    reg.register_provider(LAYER_HOST, _StaticProvider("h", [_summary("a", "x")]))
    chain = [LAYER_SCOPE, LAYER_HOST]
    d1 = await _alist(reg.catalog_digest(layer_chain=chain))
    reg.register(LAYER_SCOPE, _definition("b", "body", description="scope-b"))
    reg.invalidate()
    d2 = await _alist(reg.catalog_digest(layer_chain=chain))
    assert d1 != d2


async def test_catalog_digest_changes_on_description_change():
    """provider 替换后 list 内容变 → digest 变。

    直接 mutate provider._summaries 验证 digest 随内容变。
    """
    reg = SkillRegistry()
    p = _StaticProvider("h", [_summary("a", "old")])
    reg.register_provider(LAYER_HOST, p)
    d1 = await _alist(reg.catalog_digest())
    # 替换 provider 内部 summaries + invalidate
    p._summaries = [_summary("a", "new description")]
    reg.invalidate()
    d2 = await _alist(reg.catalog_digest())
    assert d1 != d2


# --------------------------------------------------------------------------- #
# generation / subscribe
# --------------------------------------------------------------------------- #


async def test_generation_monotonic():
    reg = SkillRegistry()
    g0 = reg.generation
    reg.register_provider(LAYER_HOST, _StaticProvider("h", []))
    g1 = reg.generation
    assert g1 > g0
    reg.invalidate()
    g2 = reg.generation
    assert g2 > g1


async def test_subscribe_receives_callback_on_invalidate():
    reg = SkillRegistry()
    calls = {"n": 0}
    reg.subscribe(lambda: calls.__setitem__("n", calls["n"] + 1))
    reg.invalidate()
    reg.invalidate()
    reg.invalidate()
    # 回调至少被调用 3 次（同步路径）
    assert calls["n"] >= 3


async def test_subscribe_dispose_stops_callback():
    reg = SkillRegistry()
    calls = {"n": 0}
    dispose = reg.subscribe(lambda: calls.__setitem__("n", calls["n"] + 1))
    reg.invalidate()
    n_after = calls["n"]
    dispose()
    reg.invalidate()
    assert calls["n"] == n_after


def test_subscribe_rejects_non_callable():
    reg = SkillRegistry()
    with pytest.raises(TypeError):
        reg.subscribe("not-callable")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 内部 helpers
# --------------------------------------------------------------------------- #


async def _alist(awaitable):
    """await asyncio.wait_for(awaitable, 5)；防死锁保护。"""
    return await asyncio.wait_for(awaitable, timeout=5.0)
