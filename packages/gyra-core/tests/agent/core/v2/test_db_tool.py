"""DbTool 测试——DSH tool-db 风格 ``db({action, ...})`` 工具。

覆盖：
  - action 校验：空 / 非法 action；
  - 各 action 必填字段校验；
  - V1 dispatch 调用（用 mock 替换 ``gyra_serve.agent.capabilities.db.tools._db_tools_impl``）；
  - 返回 ``ToolResult.ok`` 且 metadata 含 action / db_name；
  - V1 dispatch 失败时返回明确错误。
"""
from __future__ import annotations

import asyncio
import sys
import types
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gyra.agent.core.v2.db_tool import DB_TOOL_NAME, DbTool
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.result import ToolResult


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _install_mock_v1_db_tools(monkeypatch) -> Dict[str, AsyncMock]:
    """Patch gyra_serve.agent.capabilities.db.tools._db_tools_impl with mocks."""
    pkg = types.ModuleType("gyra_serve")
    pkg2 = types.ModuleType("gyra_serve.agent")
    pkg3 = types.ModuleType("gyra_serve.agent.capabilities")
    pkg4 = types.ModuleType("gyra_serve.agent.capabilities.db")
    pkg5 = types.ModuleType("gyra_serve.agent.capabilities.db.tools")
    impl = types.ModuleType(
        "gyra_serve.agent.capabilities.db.tools._db_tools_impl",
    )
    mocks = {
        "get_table_spec": AsyncMock(return_value="DESCRIBED"),
        "execute_sql": AsyncMock(return_value="EXECUTED"),
        "list_tables": AsyncMock(return_value="TABLES"),
        "search_tables": AsyncMock(return_value="SEARCHED"),
    }
    impl.get_table_spec = mocks["get_table_spec"]
    impl.execute_sql = mocks["execute_sql"]
    impl.list_tables = mocks["list_tables"]
    impl.search_tables = mocks["search_tables"]
    for m in (pkg, pkg2, pkg3, pkg4, pkg5, impl):
        monkeypatch.setitem(sys.modules, m.__name__, m)
    return mocks


# --------------------------------------------------------------------------- #
# Tool metadata
# --------------------------------------------------------------------------- #


def test_db_tool_metadata():
    tool = DbTool()
    md = tool.metadata
    assert md.name == DB_TOOL_NAME
    assert DB_TOOL_NAME == "db"
    assert "Database" in md.display_name
    assert md.category is not None
    assert md.requires_permission is True  # SQL 执行需要审批


def test_db_tool_parameters_required_fields():
    tool = DbTool()
    params = tool.parameters
    # action 必填
    assert "action" in params["required"]
    # 5 个合法 action
    assert set(params["properties"]["action"]["enum"]) == {
        "list_tables", "describe_tables", "search", "execute_sql",
        "app_card_preview",
    }


# --------------------------------------------------------------------------- #
# 校验
# --------------------------------------------------------------------------- #


async def test_db_tool_rejects_empty_action(monkeypatch):
    _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({"action": ""}))
    assert result.success is False
    assert "action is required" in (result.error or "")


async def test_db_tool_rejects_unknown_action(monkeypatch):
    _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({"action": "drop_table"}))
    assert result.success is False
    assert "Unknown action" in (result.error or "")


async def test_db_tool_list_tables_requires_db_name(monkeypatch):
    _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({"action": "list_tables"}))
    assert result.success is False
    assert "db_name is required" in (result.error or "")


async def test_db_tool_search_requires_db_name(monkeypatch):
    """search 必填 db_name；缺 question 时 fallback 到 db_name（保持向后兼容）。

    DSH-style：缺核心字段即失败；兼容缺口仅 ``question``（用 db_name 兜底）。"""
    _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    # 缺 db_name → 失败
    r1 = await _await(tool.execute({"action": "search", "question": "x"}))
    assert r1.success is False
    assert "db_name" in (r1.error or "")
    # 缺 question → fallback 到 db_name，仍能成功 dispatch
    r2 = await _await(tool.execute({"action": "search", "db_name": "x"}))
    assert r2.success is True


async def test_db_tool_execute_sql_requires_db_name_and_sql(monkeypatch):
    _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    r1 = await _await(tool.execute({"action": "execute_sql"}))
    assert r1.success is False
    r2 = await _await(tool.execute({"action": "execute_sql", "db_name": "x"}))
    assert r2.success is False


# --------------------------------------------------------------------------- #
# 成功 dispatch
# --------------------------------------------------------------------------- #


async def test_db_tool_list_tables_dispatches(monkeypatch):
    mocks = _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({
        "action": "list_tables", "db_name": "alpha", "page": 2, "page_size": 25,
    }))
    assert result.success is True
    assert result.output == "TABLES"
    assert mocks["list_tables"].called
    # kwargs 正确转发
    call = mocks["list_tables"].call_args
    assert call.kwargs["db_name"] == "alpha"
    assert call.kwargs["page"] == 2
    assert call.kwargs["page_size"] == 25
    assert result.metadata["action"] == "list_tables"
    assert result.metadata["db_name"] == "alpha"


async def test_db_tool_describe_tables_dispatches(monkeypatch):
    mocks = _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({
        "action": "describe_tables", "db_name": "alpha", "table_names": "t1,t2",
    }))
    assert result.success is True
    assert result.output == "DESCRIBED"
    assert mocks["get_table_spec"].called
    call = mocks["get_table_spec"].call_args
    assert call.kwargs["db_name"] == "alpha"
    assert call.kwargs["table_names"] == "t1,t2"


async def test_db_tool_search_dispatches(monkeypatch):
    mocks = _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({
        "action": "search", "db_name": "alpha", "question": "users table",
    }))
    assert result.success is True
    assert result.output == "SEARCHED"
    assert mocks["search_tables"].called
    call = mocks["search_tables"].call_args
    assert call.kwargs["db_name"] == "alpha"
    assert call.kwargs["question"] == "users table"


async def test_db_tool_execute_sql_dispatches(monkeypatch):
    mocks = _install_mock_v1_db_tools(monkeypatch)
    tool = DbTool()
    result = await _await(tool.execute({
        "action": "execute_sql",
        "db_name": "alpha",
        "sql": "SELECT 1",
        "page": 1,
        "page_size": 50,
    }))
    assert result.success is True
    assert result.output == "EXECUTED"
    call = mocks["execute_sql"].call_args
    assert call.kwargs["db_name"] == "alpha"
    assert call.kwargs["sql"] == "SELECT 1"
    assert call.kwargs["page"] == 1
    assert call.kwargs["page_size"] == 50


# --------------------------------------------------------------------------- #
# V1 dispatch 失败
# --------------------------------------------------------------------------- #


async def test_db_tool_v1_dispatch_exception_returns_fail(monkeypatch):
    mocks = _install_mock_v1_db_tools(monkeypatch)
    mocks["execute_sql"].side_effect = RuntimeError("db down")
    tool = DbTool()
    result = await _await(tool.execute({
        "action": "execute_sql", "db_name": "alpha", "sql": "SELECT 1",
    }))
    assert result.success is False
    assert "db down" in (result.error or "")


async def test_db_tool_v1_module_missing_returns_clear_error(monkeypatch):
    """gyra_serve 未装 / impl 不存在时返回明确错误（不抛异常）。"""
    # 注入一个 meta_path finder，拦截 _db_tools_impl 让 import 抛 ImportError。
    class _BoomFinder:
        def find_spec(self, name, path=None, target=None):
            if name == "gyra_serve.agent.capabilities.db.tools._db_tools_impl":
                raise ImportError("simulated: gyra_serve not installed")
            return None

    boom = _BoomFinder()
    monkeypatch.setattr(sys, "meta_path", [boom] + list(sys.meta_path))
    # 也要把已加载的模块从 sys.modules 删掉
    monkeypatch.delitem(
        sys.modules,
        "gyra_serve.agent.capabilities.db.tools._db_tools_impl",
        raising=False,
    )

    tool = DbTool()
    result = await _await(tool.execute({
        "action": "execute_sql", "db_name": "alpha", "sql": "SELECT 1",
    }))
    assert result.success is False
    assert "DB tools unavailable" in (result.error or "")


# --------------------------------------------------------------------------- #
# context 透传
# --------------------------------------------------------------------------- #


async def test_db_tool_passes_context_to_v1(monkeypatch):
    """``context`` 透传给 V1 函数（v1_kwargs 形参）。"""
    mocks = _install_mock_v1_db_tools(monkeypatch)
    fake_ctx = MagicMock(spec=ToolContext)
    fake_ctx.agent = "AGENT_REF"
    tool = DbTool()
    result = await _await(tool.execute(
        {"action": "execute_sql", "db_name": "x", "sql": "SELECT 1"},
        context=fake_ctx,
    ))
    assert result.success is True
    call = mocks["execute_sql"].call_args
    # context 形参已透传
    assert call.kwargs.get("context") is fake_ctx
    # agent 也透传
    assert call.kwargs.get("agent") == "AGENT_REF"


# --------------------------------------------------------------------------- #
# 与 V1 不冲突
# --------------------------------------------------------------------------- #


def test_v1_db_tools_still_exist():
    """V1 ``execute_sql`` / ``list_tables`` / ``get_table_spec`` / ``search_tables`` 仍存在。

    DSH 改造**不**替换 V1 工具；V2 DbTool 作为额外注册项并存。
    """
    pytest.importorskip("gyra_serve", reason="V1 DB tools live in gyra-serve")
    from gyra_serve.agent.capabilities.db.tools._db_tools_impl import (  # noqa: F401
        execute_sql,
        get_table_spec,
        list_tables,
        search_tables,
    )
    assert callable(execute_sql)
    assert callable(get_table_spec)
    assert callable(list_tables)
    assert callable(search_tables)


def test_db_tool_name_is_distinct():
    """V2 db 工具名与 V1 工具名不冲突。"""
    assert DB_TOOL_NAME == "db"
    assert DB_TOOL_NAME not in {
        "execute_sql", "list_tables", "get_table_spec", "search_tables",
    }


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


async def _await(awaitable):
    return await asyncio.wait_for(awaitable, timeout=5.0)
