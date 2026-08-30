"""ecp_tools 单元测试:get_verbat 全文读取工具(sheet 分块 + offset/limit 分页)。

设计:get_verbat 走「检索定位 → 按 id 读全文」两步(explore_docs 只给片段,
无法拿到 Excel 的完整行/表)。用 monkeypatch 把 DataAccess(AssetRefDao /
Config.SYSTEM_APP 知识服务 / vault)替换成内存替身,专注验证:
- _sheet_headers / _extract_sheet_block:Excel 分块解析
- get_verbat:按 id 定位、显式 space、sheet 精读、offset/limit 分页、
  跨空间定位、错误分支(无托管空间/verbat 不存在/sheet 不存在)
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gyra.knowledge.types import ExtractMode
from gyra_serve.ecp.tools import ecp_tools as tools


def _ref(ref_id: str, status: str = "active"):
    """AssetRefVO 替身(与 test_asset_gate 一致)。"""
    return SimpleNamespace(ref_id=ref_id, status=status)


def _verbat(vid: str, content: str, source_file: str = "book.xlsx"):
    """Verbat 替身(get_verbat 只读这几个字段)。"""
    return SimpleNamespace(
        id=vid,
        content=content,
        source_file=source_file,
        extract_mode=ExtractMode.UPLOAD,
        deprecated=False,
        filed_at=None,
    )


class _FakeVault:
    def __init__(self, verbats: dict):
        self._verbats = verbats

    async def verbat_get(self, vid: str):
        return self._verbats.get(vid)


class _FakeKS:
    def __init__(self, spaces: dict):
        self._spaces = spaces  # slug -> _FakeVault

    async def get_vault(self, slug: str):
        return self._spaces[slug]


class _FakeSystemApp:
    def __init__(self, ks):
        self._ks = ks

    def get_component(self, name, cls):
        return self._ks


def _patch_backend(monkeypatch, refs_by_ws: dict, spaces: dict):
    """替换 AssetRefDao 与 Config.SYSTEM_APP 知识服务为内存替身。

    get_verbat 在函数体内 import,故直接 patch 底层模块属性即可生效。
    """
    dao = MagicMock()
    dao.list.side_effect = lambda ws, kind=None: refs_by_ws.get(ws, [])
    monkeypatch.setattr("gyra_serve.ecp.models.models.AssetRefDao", lambda: dao)
    ks = _FakeKS(spaces)
    app = _FakeSystemApp(ks)
    monkeypatch.setattr(
        "gyra._private.config.Config",
        lambda: SimpleNamespace(SYSTEM_APP=app),
    )
    return dao


SHEETS_CONTENT = (
    "## Sheet: Sheet1 (3 rows)\n"
    "| 门店 | 销售额 |\n"
    "|---|---|\n"
    "| A | 100 |\n"
    "| B | 200 |\n"
    "\n"
    "## Sheet: 汇总 (2 rows)\n"
    "| 指标 | 数值 |\n"
    "|---|---|\n"
    "| 总销售额 | 300 |\n"
)


class TestSheetHelpers:
    def test_sheet_headers_parses_names(self):
        assert tools._sheet_headers(SHEETS_CONTENT) == ["Sheet1", "汇总"]

    def test_sheet_headers_empty(self):
        assert tools._sheet_headers("没有分块标题\n普通文本") == []

    def test_extract_sheet_block_first(self):
        block = tools._extract_sheet_block(SHEETS_CONTENT, "Sheet1")
        assert block is not None
        assert block.startswith("## Sheet: Sheet1")
        assert "| A | 100 |" in block
        assert "汇总" not in block

    def test_extract_sheet_block_last_to_end(self):
        block = tools._extract_sheet_block(SHEETS_CONTENT, "汇总")
        assert block is not None
        assert block.startswith("## Sheet: 汇总")
        assert "| 总销售额 | 300 |" in block

    def test_extract_sheet_block_missing(self):
        assert tools._extract_sheet_block(SHEETS_CONTENT, "Nope") is None


class TestGetVerbat:
    @pytest.mark.asyncio
    async def test_full_content(self, monkeypatch):
        v = _verbat("v1", SHEETS_CONTENT)
        _patch_backend(
            monkeypatch,
            {"default": [_ref("s1")]},
            {"s1": _FakeVault({"v1": v})},
        )
        body = json.loads(await tools.get_verbat("v1"))
        assert body["verbat_id"] == "v1"
        assert body["space"] == "s1"
        assert body["source_file"] == "book.xlsx"
        assert body["total_len"] == len(SHEETS_CONTENT)
        assert body["returned_len"] == len(SHEETS_CONTENT)
        assert body["truncated"] is False
        assert body["content"] == SHEETS_CONTENT
        assert body["sheets"] == ["Sheet1", "汇总"]
        assert body["trust"] == "inferred"
        assert "全文" in body["note"]

    @pytest.mark.asyncio
    async def test_sheet_block(self, monkeypatch):
        v = _verbat("v1", SHEETS_CONTENT)
        _patch_backend(
            monkeypatch,
            {"default": [_ref("s1")]},
            {"s1": _FakeVault({"v1": v})},
        )
        body = json.loads(await tools.get_verbat("v1", sheet="汇总"))
        assert body["content"].startswith("## Sheet: 汇总")
        assert "| A | 100 |" not in body["content"]
        assert "| 总销售额 | 300 |" in body["content"]
        assert "sheet '汇总'" in body["note"]

    @pytest.mark.asyncio
    async def test_pagination(self, monkeypatch):
        content = "abcdefghijklmnopqrstuvwxyz"  # 26 chars
        v = _verbat("v1", content)
        _patch_backend(
            monkeypatch,
            {"default": [_ref("s1")]},
            {"s1": _FakeVault({"v1": v})},
        )
        body = json.loads(await tools.get_verbat("v1", offset=10, limit=5))
        assert body["content"] == "klmno"
        assert body["returned_len"] == 5
        assert body["truncated"] is True
        assert "已截断" in body["note"]

    @pytest.mark.asyncio
    async def test_explicit_space_skips_dao(self, monkeypatch):
        v = _verbat("v1", "explicit space content")
        _patch_backend(
            monkeypatch,
            {"default": []},  # 走显式 space 时不查 AssetRefDao
            {"s1": _FakeVault({"v1": v})},
        )
        body = json.loads(await tools.get_verbat("v1", space="s1"))
        assert body["space"] == "s1"
        assert body["content"] == "explicit space content"

    @pytest.mark.asyncio
    async def test_locates_across_spaces(self, monkeypatch):
        v = _verbat("v1", "content in s2")
        _patch_backend(
            monkeypatch,
            {"default": [_ref("s1"), _ref("s2")]},
            {"s1": _FakeVault({}), "s2": _FakeVault({"v1": v})},
        )
        body = json.loads(await tools.get_verbat("v1"))
        assert body["space"] == "s2"
        assert body["content"] == "content in s2"

    @pytest.mark.asyncio
    async def test_no_managed_spaces(self, monkeypatch):
        _patch_backend(monkeypatch, {"default": []}, {})
        body = json.loads(await tools.get_verbat("v1"))
        assert "error" in body
        assert "无托管知识空间" in body["error"]
        assert body["trust"] == "none"

    @pytest.mark.asyncio
    async def test_verbat_not_found(self, monkeypatch):
        _patch_backend(
            monkeypatch,
            {"default": [_ref("s1")]},
            {"s1": _FakeVault({})},
        )
        body = json.loads(await tools.get_verbat("nope"))
        assert "error" in body
        assert "未找到 verbat" in body["error"]
        assert body["trust"] == "none"

    @pytest.mark.asyncio
    async def test_sheet_not_found(self, monkeypatch):
        v = _verbat("v1", SHEETS_CONTENT)
        _patch_backend(
            monkeypatch,
            {"default": [_ref("s1")]},
            {"s1": _FakeVault({"v1": v})},
        )
        body = json.loads(await tools.get_verbat("v1", sheet="Nope"))
        assert "error" in body
        assert "未找到 sheet" in body["error"]
        assert body["available_sheets"] == ["Sheet1", "汇总"]
        assert body["trust"] == "none"
