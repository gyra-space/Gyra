"""ECP DB 结果出口统一脱敏回归测试。

验证接入脱敏后数据返回正确:
- ``_mask_dict_rows``(execute_metric_query / preview 共用)对 dict 行按列索引脱敏,
  键与顺序保持、非敏感列原样。
- ``execute_raw_sql`` 执行结果进入脱敏入口,返回的是脱敏后的展示数据。
"""
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# 部分模块间接 import openai，mock 掉避免环境依赖
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()

from gyra_serve.ecp.service.executor import _mask_dict_rows  # noqa: E402


def _fake_mask(ds_id, columns, rows, *, table_name=None, session_id=None, **kwargs):
    """假脱敏:对第 2 列(id.name)加 MASKED_ 前缀,其余列原样。"""
    cols = list(columns)
    masked_rows = [list(r) for r in rows]
    for r in masked_rows:
        if len(r) > 1 and r[1] is not None:
            r[1] = f"MASKED_{r[1]}"
    return cols, masked_rows, [cols[1]]


@pytest.fixture
def patch_mask(monkeypatch):
    import gyra_serve.sql_guard.masking as masking_mod

    monkeypatch.setattr(masking_mod, "mask_run_result", _fake_mask)


class TestMaskDictRows:
    def test_masks_sensitive_col_and_keeps_dict_shape(self, patch_mask):
        columns = ["id", "name", "email"]
        rows = [
            {"id": 1, "name": "张伟", "email": "z@x.com"},
            {"id": 2, "name": "李丽", "email": "l@x.com"},
        ]
        out, masked = _mask_dict_rows(7, columns, rows)

        assert masked == ["name"]  # 仅 id 下标 1 这一列被脱敏
        assert list(out[0].keys()) == columns  # 键与顺序不丢
        assert out[0] == {"id": 1, "name": "MASKED_张伟", "email": "z@x.com"}
        assert out[1]["name"] == "MASKED_李丽"
        # 非敏感列与行数保持一致
        assert out[1]["id"] == 2 and out[1]["email"] == "l@x.com"
        assert len(out) == len(rows)

    def test_empty_rows_returns_unchanged(self):
        columns = ["id", "name"]
        out, masked = _mask_dict_rows(7, columns, [])
        assert out == [] and masked == []

    def test_missing_columns_returns_unchanged(self):
        rows = [{"id": 1, "name": "x"}]
        out, masked = _mask_dict_rows(7, [], rows)
        assert out == rows and masked == []

    def test_mask_failure_falls_back_to_original(self, monkeypatch):
        import gyra_serve.sql_guard.masking as masking_mod

        def _boom(*a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(masking_mod, "mask_run_result", _boom)
        rows = [{"id": 1, "name": "张伟"}]
        out, masked = _mask_dict_rows(7, ["id", "name"], rows)
        assert out == rows and masked == []  # 脱敏失败永不破坏查询


class TestMaskDictRowsInternalCatalogGate:
    """系统目录白名单门控:内部表跳过脱敏,混合查询仍保守脱敏。"""

    def test_internal_catalog_sql_skips_masking(self, patch_mask):
        columns = ["id", "table_name"]
        rows = [{"id": 1, "table_name": "USERS"}]
        out, masked = _mask_dict_rows(
            7, columns, rows, sql="SELECT table_name FROM all_tables"
        )
        assert out == rows and masked == []

    def test_internal_catalog_table_name_skips_masking(self, patch_mask):
        columns = ["id", "table_name"]
        rows = [{"id": 1, "table_name": "USERS"}]
        out, masked = _mask_dict_rows(
            7, columns, rows, table_name="pg_catalog.pg_class"
        )
        assert out == rows and masked == []

    def test_business_sql_still_masked(self, patch_mask):
        columns = ["id", "name"]
        rows = [{"id": 1, "name": "张伟"}]
        out, masked = _mask_dict_rows(7, columns, rows, sql="SELECT name FROM users")
        assert masked == ["name"]
        assert out[0]["name"] == "MASKED_张伟"

    def test_mixed_query_still_masked(self, patch_mask):
        columns = ["table_name", "name"]
        rows = [{"table_name": "A", "name": "张伟"}]
        out, masked = _mask_dict_rows(
            7,
            columns,
            rows,
            sql="SELECT t.table_name, u.name FROM all_tables t "
            "JOIN users u ON u.tid = t.tid",
        )
        assert masked == ["name"]
        assert out[0]["name"] == "MASKED_张伟"


class TestExecuteRawSqlMasking:
    @pytest.mark.asyncio
    async def test_result_is_masked(self, monkeypatch):
        from gyra_serve.ecp.tools import ecp_tools
        from gyra_serve.datasource.manages.connect_config_db import (
            ConnectConfigDao,
        )

        monkeypatch.setattr(ecp_tools.OpLogDao, "append", lambda *a, **k: None)
        monkeypatch.setattr(
            ecp_tools.Vis, "sync_display", lambda self, **k: str(k)
        )

        import gyra_serve.sql_guard.masking as masking_mod

        monkeypatch.setattr(masking_mod, "mask_run_result", _fake_mask)

        fake_connector = MagicMock()
        fake_connector.db_type = "sqlite"
        fake_connector.dialect = "sqlite"
        fake_connector.run.return_value = [
            ["id", "name"],
            [1, "张伟"],
            [2, "李丽"],
        ]
        # 安全层执行路径走 query_ex(超时 + max_rows 截断)
        fake_connector.query_ex.return_value = (
            ["id", "name"],
            [[1, "张伟"], [2, "李丽"]],
        )
        monkeypatch.setattr(
            ConnectConfigDao, "get_one",
            lambda *a, **k: SimpleNamespace(db_name="test_db"),
        )
        from gyra._private.config import Config

        manager = SimpleNamespace(get_connector=lambda _: fake_connector)
        monkeypatch.setattr(Config, "local_db_manager", manager)

        from gyra_serve.ecp.service import auto_learn

        monkeypatch.setattr(
            auto_learn, "ensure_auto_learn_cron", AsyncMock(return_value=None)
        )

        out = await ecp_tools.execute_raw_sql(
            datasource_id=1, sql="SELECT id, name FROM t", reasoning="r"
        )
        # 返回的展示数据中,名称已脱敏,明文不存在
        assert "MASKED_张伟" in out
        assert "MASKED_李丽" in out
        assert "张伟" not in out.replace("MASKED_张伟", "")
        assert "李丽" not in out.replace("MASKED_李丽", "")