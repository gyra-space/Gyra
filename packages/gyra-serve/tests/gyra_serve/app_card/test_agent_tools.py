"""app_card_preview 开发期取数工具注册测试。

该工具作为数据库资源自带取数工具,经 ``@tool`` 装饰器自动注册进 tool_registry,
由 ``base_agent._inject_database_tools`` 随 DBResource 一起注入 agent TOOLS 槽。
"""
import asyncio
import json

from gyra.agent.tools.base import ToolCategory
from gyra.agent.tools.registry import tool_registry


def _ensure_registered():
    import gyra_serve.app_card.agent_tools  # noqa: F401  触发 @tool 注册


def test_app_card_preview_registered():
    _ensure_registered()
    tool = tool_registry.get("app_card_preview")
    assert tool is not None
    assert tool.name == "app_card_preview"
    assert tool.metadata.category == ToolCategory.DATABASE
    assert "app_card_preview" in tool_registry.list_names()


def _run_preview(op, params):
    from gyra_serve.app_card.agent_tools import app_card_preview

    raw = asyncio.run(app_card_preview(op=op, params=params))
    return json.loads(raw)


def test_store_preview_dry_run_valid():
    _ensure_registered()
    res = _run_preview("store.preview", {
        "collection": "responses",
        "record": {"name": "张三", "score": 88},
        "data_space": {"fields": {"name": {"type": "string", "required": True}}},
    })
    assert res["trust"] == "preview"
    assert res["valid"] is True
    assert res["collection"] == "responses"
    assert "name" in res["fields"]


def test_store_preview_dry_run_invalid_required():
    _ensure_registered()
    res = _run_preview("store.preview", {
        "record": {"score": 88},
        "data_space": {"fields": {"name": {"type": "string", "required": True}}},
    })
    assert res["trust"] == "none"
    assert res["valid"] is False
    assert "name" in res["error"]


def test_store_preview_dry_run_type_mismatch():
    _ensure_registered()
    res = _run_preview("store.preview", {
        "record": {"score": "not-a-number"},
        "data_space": {"fields": {"score": {"type": "number"}}},
    })
    assert res["trust"] == "none"
    assert res["valid"] is False


def test_kv_preview_dry_run():
    _ensure_registered()
    ok = _run_preview("kv.preview", {"key": "draft", "value": {"step": 2}})
    assert ok["trust"] == "preview"
    assert ok["valid"] is True

    bad = _run_preview("kv.preview", {"value": 1})
    assert bad["trust"] == "none"
    assert bad["valid"] is False
