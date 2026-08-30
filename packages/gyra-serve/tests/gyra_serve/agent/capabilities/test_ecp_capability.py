"""ECPCapability 托管 db 资产的 schema 工具降级连带注入回归测试。

背景:ECP 模块绑定(托管)数据库后,数据查询必须统一走 ECP 工具
(execute_metric_query / execute_raw_sql),但只读 schema 工具
(get_table_spec / list_tables / search_tables)必须保持可用——
供 execute_raw_sql 兜底与提案理解物理表。工具面纪律:
- 托管 db 时:连带注入只读 schema 三件套;绝不注入 execute_sql
  (直连由 asset_gate 在 execute_sql 内硬门禁拦截)
- 未托管 db 时:不注入 schema 工具(无素材,不制造噪音)
"""

import asyncio
from unittest.mock import MagicMock

from gyra.core.interface.resource.bundle import Slot

from gyra_serve.agent.capabilities.ecp.capability import (
    ECPCapability,
    _load_db_schema_tools,
)

SCHEMA_TOOL_NAMES = {"get_table_spec", "list_tables", "search_tables"}


def _patch_prepare_io(monkeypatch, managed_ds_ids):
    """mock prepare 的两路 I/O:目录文本 + 托管资产清单(独立降级,需分别 mock)。"""
    catalog = MagicMock()
    catalog.build_catalog_text.return_value = "【目录摘要】"
    monkeypatch.setattr(
        "gyra_serve.ecp.service.catalog.build_catalog_text",
        catalog.build_catalog_text,
    )
    gate = MagicMock()
    gate.build_managed_assets_text.return_value = "【ECP 托管资产】"
    gate.managed_db_datasource_ids.return_value = managed_ds_ids
    monkeypatch.setattr(
        "gyra_serve.ecp.service.asset_gate.build_managed_assets_text",
        gate.build_managed_assets_text,
    )
    monkeypatch.setattr(
        "gyra_serve.ecp.service.asset_gate.managed_db_datasource_ids",
        gate.managed_db_datasource_ids,
    )


def _declared_tools(cap: ECPCapability):
    """declare() 的 TOOLS 槽工具名集合。"""
    return {
        c.content.name
        for c in cap.declare()
        if getattr(c, "slot", None) == Slot.TOOLS
        and getattr(c.content, "name", None)
    }


def _declared_system_texts(cap: ECPCapability):
    return [
        c.content
        for c in cap.declare()
        if getattr(c, "slot", None) == Slot.SYSTEM
    ]


def test_load_db_schema_tools_read_only_only():
    """连带注入的必须恰好是只读 schema 三件套,绝不包含 execute_sql。"""
    tools = {t.name for t in _load_db_schema_tools()}
    assert SCHEMA_TOOL_NAMES <= tools
    assert "execute_sql" not in tools


def test_declare_injects_schema_tools_when_db_managed(monkeypatch):
    """ECP 托管 db 时:schema 只读工具保持可用 + ECP 工具在场 + 直连不在场。"""
    _patch_prepare_io(monkeypatch, managed_ds_ids={"1"})
    cap = ECPCapability(workspace_id="default")
    asyncio.run(cap.prepare())

    names = _declared_tools(cap)
    assert SCHEMA_TOOL_NAMES <= names, "托管 db 后只读 schema 工具必须仍可注入"
    assert "execute_sql" not in names, "ECP capability 不得连带注入直连 execute_sql"
    assert "execute_metric_query" in names
    assert "execute_raw_sql" in names

    system_texts = _declared_system_texts(cap)
    assert any("ECP 托管资产" in (t or "") for t in system_texts)


def test_declare_no_schema_tools_without_managed_db(monkeypatch):
    """ECP 未托管任何 db 时:不注入 schema 工具(不制造噪音),ECP 工具照常。"""
    _patch_prepare_io(monkeypatch, managed_ds_ids=set())
    cap = ECPCapability(workspace_id="default")
    asyncio.run(cap.prepare())

    names = _declared_tools(cap)
    assert not (SCHEMA_TOOL_NAMES & names)
    assert "execute_sql" not in names
    assert "execute_metric_query" in names
