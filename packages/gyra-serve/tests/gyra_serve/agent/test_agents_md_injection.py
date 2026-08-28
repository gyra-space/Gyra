"""V1 AGENTS.md 注入 wrapper（agents_md_injection.py）单测。

不依赖 DB / KnowledgeService：vault 路在测试环境下自然降级跳过
（get_instance 返回 None / 抛异常 → debug 忽略），这本身就是降级
安全性的验证。
"""

import asyncio
import json
import os

import pytest

from gyra_serve.agent.agents.chat.agents_md_injection import (
    _coerce_ext_config,
    _resolve_memory_space_slug,
    build_agents_md_block,
)


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
    return asyncio.get_event_loop().run_until_complete(coro)


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
