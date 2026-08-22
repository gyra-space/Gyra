"""DbCatalogConsumer 测试——DSH tool-db 风格 digest 变化才注入。

覆盖：
  - 渲染：``<available_databases>`` XML 含 db_name / type / dialect / datasource_id；
  - XML 转义 + 截断 description；
  - provider = list / 可调用 / async callable 三种形态；
  - ``initial()``：非空 → 发 reminder；空 → None；
  - ``refresh()``：digest 不变返回 None；变化时发 replacement；同一变化只发一次；
  - generation 跟踪（provider 可选 ``generation`` 属性）；
  - ``reset()`` 清状态。
"""
from __future__ import annotations

import asyncio
import pytest

from gyra.agent.core.v2.db_consumer import (
    DEFAULT_DESCRIPTION_MAX,
    DbCatalogConsumer,
    build_initial_reminder,
    build_replacement_reminder,
    render_available_databases_xml,
)


def _db(name: str, **kw) -> dict:
    base = {
        "db_name": name, "db_type": "mysql", "dialect": "mysql",
        "datasource_id": hash(name) & 0xFFFF,
        "description": f"Database {name}",
    }
    base.update(kw)
    return base


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #


def test_render_xml_basic_fields():
    items = [_db("alpha"), _db("beta", db_type="postgres", dialect="postgresql")]
    xml = render_available_databases_xml(items)
    assert "<available_databases>" in xml
    assert "<db_name>alpha</db_name>" in xml
    assert "<db_name>beta</db_name>" in xml
    assert "<db_type>mysql</db_type>" in xml
    assert "<dialect>postgresql</dialect>" in xml
    assert "<datasource_id>" in xml


def test_render_xml_escapes_special_chars():
    items = [_db("a&b", description='<"weird">')]
    xml = render_available_databases_xml(items)
    assert "a&amp;b" in xml
    assert "&lt;&quot;weird&quot;&gt;" in xml


def test_render_xml_truncates_long_description():
    items = [_db("a", description="x" * 500)]
    xml = render_available_databases_xml(items, description_max=200)
    # 截断后带省略号
    assert "…" in xml
    # 截断后 description 长度 ≤ 200
    desc_start = xml.find("<description>") + len("<description>")
    desc_end = xml.find("</description>")
    assert desc_end - desc_start <= 200


def test_render_xml_skips_empty_name():
    items = [
        _db("valid"),
        {"db_name": "", "db_type": "x", "dialect": "x"},
    ]
    xml = render_available_databases_xml(items)
    assert xml.count("<database>") == 1
    assert "<db_name>valid</db_name>" in xml


def test_render_xml_empty_returns_empty_string():
    assert render_available_databases_xml([]) == ""
    assert render_available_databases_xml([{"db_name": ""}]) == ""


def test_render_xml_handles_missing_datasource_id():
    items = [_db("a", datasource_id=None)]
    xml = render_available_databases_xml(items)
    assert "<datasource_id></datasource_id>" in xml


def test_build_initial_reminder_none_when_empty():
    """空 DB 列表不污染 LLM 上下文。"""
    assert build_initial_reminder([]) is None


def test_build_initial_reminder_has_system_reminder_tag():
    msg = build_initial_reminder([_db("alpha")])
    assert msg is not None
    assert msg["role"] == "user"
    assert "<system-reminder>" in msg["content"]
    assert "</system-reminder>" in msg["content"]
    # 提到 db 工具
    assert "db(" in msg["content"]


def test_build_replacement_reminder_always_returns():
    """digest 变化时即使空也发。"""
    msg = build_replacement_reminder([])
    assert msg["role"] == "user"


# --------------------------------------------------------------------------- #
# Provider 形态
# --------------------------------------------------------------------------- #


async def test_provider_as_list():
    items = [_db("a"), _db("b")]
    consumer = DbCatalogConsumer(provider=items)
    summaries = await _await(consumer._list())
    assert len(summaries) == 2


async def test_provider_as_callable():
    items = [_db("a")]
    consumer = DbCatalogConsumer(provider=lambda: items)
    out = await _await(consumer._list())
    assert out == items


async def test_provider_as_async_callable():
    async def _prov():
        return [_db("a"), _db("b")]
    consumer = DbCatalogConsumer(provider=_prov)
    out = await _await(consumer._list())
    assert len(out) == 2


async def test_provider_none_returns_empty():
    consumer = DbCatalogConsumer(provider=None)
    assert await _await(consumer._list()) == []


# --------------------------------------------------------------------------- #
# Consumer 行为
# --------------------------------------------------------------------------- #


class _MutableProvider:
    """可观察 + 可变 provider——test 期间 mutate state。"""

    def __init__(self, initial: list):
        self._items = list(initial)
        self.generation = 0

    def __call__(self):
        return list(self._items)

    def add(self, db: dict) -> None:
        self._items.append(db)
        self.generation += 1

    def remove(self, db_name: str) -> None:
        self._items = [it for it in self._items if it.get("db_name") != db_name]
        self.generation += 1

    def mutate(self, db_name: str, **kw) -> None:
        for it in self._items:
            if it.get("db_name") == db_name:
                it.update(kw)
        self.generation += 1


async def test_initial_emits_reminder_when_non_empty():
    prov = _MutableProvider([_db("a"), _db("b")])
    consumer = DbCatalogConsumer(provider=prov)
    msg = await _await(consumer.initial())
    assert msg is not None
    assert msg["role"] == "user"
    assert "<db_name>a</db_name>" in msg["content"]
    assert "<db_name>b</db_name>" in msg["content"]


async def test_initial_returns_none_when_empty():
    consumer = DbCatalogConsumer(provider=[])
    msg = await _await(consumer.initial())
    assert msg is None


async def test_refresh_no_change_returns_none():
    prov = _MutableProvider([_db("a")])
    consumer = DbCatalogConsumer(provider=prov)
    await _await(consumer.initial())
    assert await _await(consumer.refresh()) is None
    # 多次 refresh 仍 None
    assert await _await(consumer.refresh()) is None


async def test_refresh_fires_once_on_digest_change():
    prov = _MutableProvider([_db("a")])
    consumer = DbCatalogConsumer(provider=prov)
    await _await(consumer.initial())
    # 第一次 refresh（未变）→ None
    assert await _await(consumer.refresh()) is None
    # provider 增 DB
    prov.add(_db("b"))
    # digest 变了 → 发 replacement
    msg = await _await(consumer.refresh())
    assert msg is not None
    assert "<db_name>a</db_name>" in msg["content"]
    assert "<db_name>b</db_name>" in msg["content"]
    # 立即再 refresh：digest 稳定 → None
    assert await _await(consumer.refresh()) is None
    assert await _await(consumer.refresh()) is None


async def test_refresh_fires_on_description_change():
    prov = _MutableProvider([_db("a", description="old")])
    consumer = DbCatalogConsumer(provider=prov)
    await _await(consumer.initial())
    # description 变化 → digest 变
    prov.mutate("a", description="new description text")
    msg = await _await(consumer.refresh())
    assert msg is not None


async def test_refresh_emits_empty_replacement_on_removal():
    """DB 全部删除 → digest 变 → 发空替换。"""
    prov = _MutableProvider([_db("a")])
    consumer = DbCatalogConsumer(provider=prov)
    await _await(consumer.initial())
    prov.remove("a")
    msg = await _await(consumer.refresh())
    assert msg is not None
    assert msg["role"] == "user"
    # 渲染时无 ``<database>`` 行
    assert "<database>" not in msg["content"]


async def test_refresh_falls_back_to_initial_when_never_published():
    """未发布过时 refresh 降级为 initial。"""
    consumer = DbCatalogConsumer(provider=[_db("a")])
    msg = await _await(consumer.refresh())
    assert msg is not None
    assert "<db_name>a</db_name>" in msg["content"]


async def test_reset_clears_state():
    prov = _MutableProvider([_db("a")])
    consumer = DbCatalogConsumer(provider=prov)
    await _await(consumer.initial())
    consumer.reset()
    assert consumer._last_published_digest is None
    assert consumer._last_published_generation == -1


async def test_refresh_after_reset_emits_initial():
    """reset 后 refresh 必发 initial。"""
    prov = _MutableProvider([_db("a")])
    consumer = DbCatalogConsumer(provider=prov)
    await _await(consumer.initial())
    consumer.reset()
    msg = await _await(consumer.refresh())
    assert msg is not None
    assert "<db_name>a</db_name>" in msg["content"]


# --------------------------------------------------------------------------- #
# 兼容 DBCapability 视图（agent 持 capability_pack 的 get_all("db")）
# --------------------------------------------------------------------------- #


async def test_provider_capability_pack_view():
    """模拟 agent.capability_pack.get_all('db') 视图。"""
    class _Cap:
        def __init__(self, name, **kw):
            self.db_name = name
            self._db_type = kw.get("type", "mysql")
            self._dialect = kw.get("dialect", "mysql")
            self._datasource_id = kw.get("ds_id", 1)
            self._description = kw.get("description", "")

    class _Pack:
        def __init__(self, caps):
            self._caps = caps

        def get_all(self, kind):
            if kind == "db":
                return self._caps
            return []

    pack = _Pack([_Cap("alpha"), _Cap("beta", type="postgres", dialect="postgresql", ds_id=2)])

    def _prov():
        return [
            {
                "db_name": c.db_name,
                "db_type": c._db_type,
                "dialect": c._dialect,
                "datasource_id": c._datasource_id,
                "description": c._description,
            }
            for c in pack.get_all("db")
        ]

    consumer = DbCatalogConsumer(provider=_prov)
    msg = await _await(consumer.initial())
    assert msg is not None
    assert "<db_name>alpha</db_name>" in msg["content"]
    assert "<db_name>beta</db_name>" in msg["content"]
    assert "<dialect>postgresql</dialect>" in msg["content"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
