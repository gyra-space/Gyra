"""知识空间默认模型初始化:_resolve_default_space_models + create_space 填充。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gyra_serve.knowledge.service.service import (
    Service,
    _resolve_default_space_models,
)

CACHE_PATH = "gyra.agent.util.llm.model_config_cache.ModelConfigCache"


def _patch_cache(monkeypatch, models, default_llm=None, multimodal=("vision-1",)):
    cache = MagicMock()
    cache.get_all_models.return_value = models
    cache.has_model.side_effect = lambda m: m in models
    cache.is_multimodal.side_effect = lambda m: m in multimodal
    monkeypatch.setattr(CACHE_PATH, cache)
    system_app = MagicMock()
    system_app.config.get.side_effect = (
        lambda key: default_llm if key == "agent.default_llm" else None
    )
    return cache, system_app


class TestResolveDefaultSpaceModels:
    def test_default_llm_and_multimodal(self, monkeypatch):
        _, system_app = _patch_cache(
            monkeypatch, ["text-1", "vision-1"], default_llm="text-1"
        )
        assert _resolve_default_space_models(system_app) == ("text-1", "vision-1")

    def test_fallback_first_model_when_default_unknown(self, monkeypatch):
        _, system_app = _patch_cache(
            monkeypatch, ["text-1", "vision-1"], default_llm="ghost"
        )
        assert _resolve_default_space_models(system_app) == ("text-1", "vision-1")

    def test_no_default_config_uses_first_model(self, monkeypatch):
        _, system_app = _patch_cache(monkeypatch, ["text-1"], default_llm=None)
        assert _resolve_default_space_models(system_app) == ("text-1", None)

    def test_none_system_app(self, monkeypatch):
        _patch_cache(monkeypatch, ["text-1", "vision-1"])
        assert _resolve_default_space_models(None) == ("text-1", "vision-1")

    def test_no_models_registered(self, monkeypatch):
        _patch_cache(monkeypatch, [])
        assert _resolve_default_space_models(MagicMock()) == (None, None)

    def test_failure_is_swallowed(self, monkeypatch):
        cache = MagicMock()
        cache.get_all_models.side_effect = RuntimeError("boom")
        monkeypatch.setattr(CACHE_PATH, cache)
        assert _resolve_default_space_models(MagicMock()) == (None, None)


def _make_service(slug: str = "sp1") -> Service:
    svc = Service.__new__(Service)
    svc._serve_config = MagicMock()
    svc._serve_config.default_backend = "local"
    svc._system_app = MagicMock()
    svc._system_app.config.get.return_value = None
    svc._spaces = {
        slug: SimpleNamespace(
            slug=slug,
            space_type="personal",
            default_agent_id=None,
            llm_model=None,
            multimodal_model=None,
            embedder_model=None,
            visibility="private",
            owner_id="",
            rerank_model=None,
            embed_verbats=False,
        )
    }
    vault = SimpleNamespace(root=f"/tmp/{slug}")
    svc.get_vault = AsyncMock(return_value=vault)
    svc.update_space_config = AsyncMock()
    return svc


class TestCreateSpaceFillsDefaults:
    @pytest.mark.asyncio
    async def test_fills_defaults_when_unset(self, monkeypatch):
        _patch_cache(monkeypatch, ["text-1", "vision-1"], default_llm="text-1")
        svc = _make_service("sp1")

        await svc.create_space("sp1")

        svc.update_space_config.assert_awaited_once_with(
            "sp1",
            default_agent_id=None,
            llm_model="text-1",
            multimodal_model="vision-1",
            embedder_model=None,
            rerank_model=None,
            embed_verbats=None,
        )

    @pytest.mark.asyncio
    async def test_explicit_llm_model_wins(self, monkeypatch):
        _patch_cache(monkeypatch, ["text-1", "vision-1"], default_llm="text-1")
        svc = _make_service("sp2")

        await svc.create_space("sp2", llm_model="explicit-llm")

        kwargs = svc.update_space_config.await_args.kwargs
        assert kwargs["llm_model"] == "explicit-llm"
        assert kwargs["multimodal_model"] == "vision-1"

    @pytest.mark.asyncio
    async def test_no_defaults_no_persist(self, monkeypatch):
        _patch_cache(monkeypatch, [])
        svc = _make_service("sp3")

        await svc.create_space("sp3")

        svc.update_space_config.assert_not_awaited()
