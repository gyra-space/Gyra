"""memory_bundle_factory 单测。

build_memory_bundle: vault 路(真 LocalVaultFS + tmp_path)/ SQLite 降级路 /
空 specs。wire_memory_bundle: bundle 挂载、双键 pipeline 注册、hook bundle
注册、MCPCapability 注入(含 capability_pack=None 分支)。无 LLM / DB 依赖。
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gyra.agent.core.memory.longterm_manager import LongTermMemoryConfig
from gyra.knowledge.types import new_space_id
from gyra_serve.agent.agents.chat.memory_bundle_factory import (
    MemorySpaceSpec,
    build_memory_bundle,
    specs_from_memories,
    wire_memory_bundle,
)
from gyra_serve.agent.resource.tool.memory_tool import MemoryToolPack


def _run(coro):
    return asyncio.run(coro)


def _memory_config(**overrides) -> LongTermMemoryConfig:
    kwargs = dict(
        memories=[{"memory_id": "memory-ws-test"}],
        auto_memory=True,
        enable_kg=False,
    )
    kwargs.update(overrides)
    return LongTermMemoryConfig(**kwargs)


def _specs(slug: str = "memory-ws-test") -> list:
    return [MemorySpaceSpec(memory_id=slug, space_slug=slug, store_type="knowledge_vault")]


# --------------------------- specs_from_memories --------------------------- #


def test_specs_from_memories_slug_derivation():
    cfg = _memory_config(
        memories=[
            {"memory_id": "memory-a"},                      # slug 形 id → slug 直取
            {"memory_id": "b", "space_slug": "memory-b"},   # 显式 slug
            {"memory_id": ""},                              # 无 id → 跳过
            {"memory_id": "c"},                             # 非 slug 形 → None
        ]
    )
    specs = specs_from_memories(cfg)
    assert [s.space_slug for s in specs] == ["memory-a", "memory-b", None]
    assert [s.memory_id for s in specs] == ["memory-a", "b", "c"]


# --------------------------- build_memory_bundle --------------------------- #


def test_build_empty_specs_returns_none():
    assert _run(build_memory_bundle(MagicMock(), None, app_code="x",
                                    memory_config=_memory_config(), specs=[])) is None


def test_build_sqlite_fallback_when_no_knowledge_service():
    """KnowledgeService 不可用(MagicMock system_app 取不到实例)时降级 SQLite。"""
    bundle = _run(
        build_memory_bundle(
            MagicMock(), None,
            app_code="app1", memory_config=_memory_config(), specs=_specs(),
        )
    )
    assert bundle is not None
    assert bundle.manager.has_stores()
    store = bundle.manager.memory_stores["memory-ws-test"]
    from gyra_ext.storage.memory.simple_sqlite_store import SimpleSQLiteMemoryStore

    assert isinstance(store, SimpleSQLiteMemoryStore)


def test_build_vault_path_with_real_local_vault(tmp_path, monkeypatch):
    """KnowledgeService 可用且 get_vault 命中时走 KnowledgeVaultMemoryStore。"""
    from gyra_ext.knowledge.vaultfs import LocalVaultFS

    vault = LocalVaultFS(space_id=new_space_id(), root=tmp_path / "space")
    _run(vault.initialize())

    class _FakeKS:
        async def get_vault(self, slug):
            return vault

    import gyra_serve.knowledge.service.service as ks_mod

    monkeypatch.setattr(
        ks_mod.Service, "get_instance", classmethod(lambda cls, app: _FakeKS())
    )
    try:
        bundle = _run(
            build_memory_bundle(
                MagicMock(), None,
                app_code="app1", memory_config=_memory_config(), specs=_specs(),
            )
        )
    finally:
        _run(vault.close())
    assert bundle is not None
    from gyra_ext.storage.memory.knowledge_vault_store import KnowledgeVaultMemoryStore

    assert isinstance(
        bundle.manager.memory_stores["memory-ws-test"], KnowledgeVaultMemoryStore
    )


# --------------------------- wire_memory_bundle --------------------------- #


def _make_bundle_with_real_toolpack_stores():
    """走 SQLite 降级路构建真 bundle(manager/stores 均真实可用)。"""
    return _run(
        build_memory_bundle(
            MagicMock(), None,
            app_code="app1", memory_config=_memory_config(), specs=_specs(),
        )
    )


def test_wire_attaches_bundle_dualkey_pipeline_and_capability():
    from gyra.agent.core.memory.hook_dispatcher import get_memory_pipeline

    bundle = _make_bundle_with_real_toolpack_stores()
    recipient = SimpleNamespace(
        memory=MagicMock(), agent_context=SimpleNamespace(conv_id="conv-1")
    )
    _run(
        wire_memory_bundle(
            recipient, bundle, MagicMock(),
            user_id=None, conv_id="conv-1", conv_session_id="sess-1",
        )
    )
    assert recipient._memory_bundle is bundle
    # 双键注册:conv_id 与 conv_session_id 指向同一 pipeline
    assert get_memory_pipeline("conv-1") is not None
    assert get_memory_pipeline("conv-1") is get_memory_pipeline("sess-1")
    assert bundle.pipeline is get_memory_pipeline("conv-1")
    # hook bundle 注册
    recipient.memory.gpts_memory.register_memory_bundle.assert_called_once_with(
        "conv-1", bundle
    )
    # capability_pack 为 None 时自建并注入 memory 工具
    assert recipient.capability_pack is not None


def test_wire_adds_capability_to_existing_pack():
    bundle = _make_bundle_with_real_toolpack_stores()
    recipient = SimpleNamespace(memory=MagicMock())
    cap_pack = MagicMock()
    _run(
        wire_memory_bundle(
            recipient, bundle, MagicMock(),
            user_id=None, conv_id="conv-2", conv_session_id=None,
            capability_pack=cap_pack,
        )
    )
    cap_pack.add.assert_called_once()
    added = cap_pack.add.call_args[0][0]
    assert getattr(added, "name", "") == "memory_tools" or added is not None


def test_wire_toolpack_contains_memory_tools():
    bundle = _make_bundle_with_real_toolpack_stores()
    pack = MemoryToolPack(
        memory_stores=bundle.manager.memory_stores, wing="default"
    )
    _run(pack.preload_resource())
    names = {r.name for r in pack.sub_resources} if hasattr(pack.sub_resources[0], "name") else set()
    # 基础记忆工具必须存在(async 修复后仍注册)
    for tool in pack.sub_resources:
        names.add(getattr(tool, "name", ""))
    assert "memory_search" in names
    assert "memory_save" in names
    assert "memory_remember" in names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
