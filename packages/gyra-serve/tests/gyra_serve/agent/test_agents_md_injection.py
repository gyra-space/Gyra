"""V1 AGENTS.md 注入 wrapper（agents_md_injection.py）单测。

不依赖 DB / KnowledgeService：vault 路在测试环境下自然降级跳过
（get_instance 返回 None / 抛异常 → debug 忽略），这本身就是降级
安全性的验证。
"""

import asyncio
import json
import os

import pytest

from gyra_serve.agent.agents.chat import agents_md_injection
from gyra_serve.agent.agents.chat.agents_md_injection import (
    _coerce_ext_config,
    _resolve_memory_space_slug,
    build_agents_md_block,
    resolve_workspace_memory_space,
)
from gyra_serve.knowledge.service.service import Service as KnowledgeService


class FakeApp:
    def __init__(self, ext_config=None, resource_memory=None):
        self.ext_config = ext_config
        self.resource_memory = resource_memory


def _resource_memory(memory_id="memory-app1"):
    return [
        {
            "type": "memory",
            "name": "memory",
            "value": json.dumps(
                {
                    "memories": [{"memory_id": memory_id}],
                    "space_slug": memory_id,
                }
            ),
        }
    ]


# --------------------------- ext_config 防御 --------------------------- #


def test_coerce_ext_config_json_string():
    assert _coerce_ext_config('{"agents_md": {"path": "x.md"}}') == {
        "agents_md": {"path": "x.md"}
    }


def test_coerce_ext_config_bad_and_none():
    assert _coerce_ext_config("not-json") == {}
    assert _coerce_ext_config(None) == {}
    assert _coerce_ext_config(42) == {}


# --------------------------- slug 解析 --------------------------- #


def test_slug_from_resource_memory():
    app = FakeApp(resource_memory=_resource_memory())
    assert _resolve_memory_space_slug(app) == "memory-app1"


def test_slug_missing():
    assert _resolve_memory_space_slug(FakeApp()) is None
    assert _resolve_memory_space_slug(FakeApp(resource_memory=[{"value": "bad"}])) is None


# --------------------------- 三路收集 / 注入块 --------------------------- #


def _run(coro):
    return asyncio.run(coro)


def test_explicit_relative_path_via_workspace_root(tmp_path, monkeypatch):
    import gyra_serve.workspace.dataset_service as ds

    ws = tmp_path / "wsroot"
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# 显式规则\n\n用 uv 管理依赖\n", "utf-8")
    monkeypatch.setattr(ds, "workspace_sandbox_root", lambda wid: str(ws))

    app = FakeApp(
        ext_config={"agents_md": {"path": "AGENTS.md"}},
        resource_memory=_resource_memory(),
    )
    block = _run(build_agents_md_block(object(), app, {"workspace_id": 123}))
    assert block and "显式规则" in block
    assert "维护说明" in block


def test_project_dir_fallback(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# 项目规则\n\n用 Python 3.13\n", "utf-8")
    app = FakeApp(ext_config={"project_ecosystem": {"project_dir": str(tmp_path)}})
    block = _run(build_agents_md_block(object(), app, {}))
    assert block and "项目规则" in block


def test_empty_config_returns_none():
    assert _run(build_agents_md_block(object(), FakeApp(), {})) is None


def test_disabled_config_returns_none(tmp_path, monkeypatch):
    import gyra_serve.workspace.dataset_service as ds

    ws = tmp_path / "wsroot"
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# 规则\n", "utf-8")
    monkeypatch.setattr(ds, "workspace_sandbox_root", lambda wid: str(ws))
    app = FakeApp(ext_config={"agents_md": {"enabled": False, "path": "AGENTS.md"}})
    assert _run(build_agents_md_block(object(), app, {"workspace_id": 1})) is None


# --------------------------- workspace 记忆空间 --------------------------- #


class _FakeWS:
    def __init__(self, workspace_code):
        self.workspace_code = workspace_code


class _FakeWorkspaceService:
    _by_id = {}

    def __init__(self, system_app=None, config=None):
        pass

    def get_by_id(self, ws_id):
        return self._by_id.get(ws_id)


class _FakeKS:
    def __init__(self):
        self.created = []

    async def get_or_create_workspace_space(self, workspace_code):
        self.created.append(workspace_code)
        return object()

    @staticmethod
    def workspace_space_slug(workspace_code):
        return KnowledgeService.workspace_space_slug(workspace_code)


@pytest.fixture(autouse=True)
def _clear_ws_slug_cache():
    agents_md_injection._WORKSPACE_SLUG_CACHE.clear()
    yield
    agents_md_injection._WORKSPACE_SLUG_CACHE.clear()


def _patch_workspace_env(monkeypatch, fake_ks, ws_by_id=None):
    _FakeWorkspaceService._by_id = ws_by_id or {}
    import gyra_serve.workspace.config as ws_cfg_mod
    import gyra_serve.workspace.service.service as ws_svc_mod

    monkeypatch.setattr(ws_svc_mod, "WorkspaceService", _FakeWorkspaceService)
    monkeypatch.setattr(ws_cfg_mod, "ServeConfig", lambda: object())
    monkeypatch.setattr(
        KnowledgeService, "get_instance", classmethod(lambda cls, app: fake_ks)
    )


def test_workspace_space_slug_cleaning():
    assert KnowledgeService.workspace_space_slug("ws-abc") == "memory-ws-ws-abc"
    assert KnowledgeService.workspace_space_slug("ws abc/1") == "memory-ws-ws_abc_1"
    assert KnowledgeService.workspace_space_slug("") == "memory-ws-unknown"


def test_resolve_workspace_memory_space_creates_and_caches(monkeypatch):
    fake_ks = _FakeKS()
    _patch_workspace_env(monkeypatch, fake_ks, ws_by_id={7: _FakeWS("ws-seven")})

    slug = _run(resolve_workspace_memory_space(object(), 7))
    assert slug == "memory-ws-ws-seven"
    assert fake_ks.created == ["ws-seven"]

    # 第二次走缓存：不再触发建空间
    slug2 = _run(resolve_workspace_memory_space(object(), 7))
    assert slug2 == slug
    assert fake_ks.created == ["ws-seven"]


def test_resolve_workspace_memory_space_fallback_code(monkeypatch):
    """workspace 查不到 / 查询失败时回退 ws-{id}，仍建空间。"""
    fake_ks = _FakeKS()
    _patch_workspace_env(monkeypatch, fake_ks, ws_by_id={})  # 查不到

    slug = _run(resolve_workspace_memory_space(object(), 42))
    assert slug == "memory-ws-ws-42"
    assert fake_ks.created == ["ws-42"]


def test_resolve_workspace_memory_space_degrades_on_error(monkeypatch):
    import gyra_serve.workspace.service.service as ws_svc_mod

    def _boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(ws_svc_mod, "WorkspaceService", _boom)
    slug = _run(resolve_workspace_memory_space(object(), 9))
    assert slug is None


# --------------------------- 四路收集（含 workspace 路） --------------------------- #


def test_collect_sections_includes_workspace_memory(tmp_path, monkeypatch):
    """workspace 路命中时,空间级 AGENTS.md 进入注入块,优先于 app 记忆空间。"""
    from gyra_serve.agent.agents.chat.agents_md_injection import (
        collect_agents_md_sections,
    )

    async def _fake_resolve(system_app, workspace_id):
        return "memory-ws-1"

    async def _fake_load(system_app, slug):
        return "# 空间记忆\n\n本空间用 PostgreSQL 16\n"

    monkeypatch.setattr(agents_md_injection, "resolve_workspace_memory_space", _fake_resolve)
    monkeypatch.setattr(agents_md_injection, "_load_vault_agents_md", _fake_load)

    app = FakeApp(resource_memory=_resource_memory())  # app 级路自然降级(无 DB)
    sections = _run(collect_agents_md_sections(object(), app, {"workspace_id": 1}))
    sources = [s for s, _ in sections]
    assert "workspace-memory" in sources
    joined = "\n".join(c for _, c in sections)
    assert "本空间用 PostgreSQL 16" in joined


def test_collect_sections_no_workspace_id_skips_workspace_path(monkeypatch):
    from gyra_serve.agent.agents.chat.agents_md_injection import (
        collect_agents_md_sections,
    )

    called = []

    async def _fake_resolve(system_app, workspace_id):
        called.append(workspace_id)
        return None

    monkeypatch.setattr(agents_md_injection, "resolve_workspace_memory_space", _fake_resolve)
    app = FakeApp()
    _run(collect_agents_md_sections(object(), app, {}))
    assert called == []
