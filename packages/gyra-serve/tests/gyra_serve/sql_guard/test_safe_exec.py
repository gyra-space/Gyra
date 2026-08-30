"""safe_exec 执行安全层测试:LIMIT 注入/封顶(方言门控)+ 超时/流式截断执行。

覆盖:
- apply_select_limit: LIMIT 系方言注入与封顶、oracle/mssql 不注入、
  非 SELECT 不动、limit<=0 不干预、WITH(CTE)按 SELECT 处理
- run_select_with_limits: query_ex 哨兵截断、无 query_ex 回退 run、空结果
- execute_sql 集成: 超限结果截断并标注、超时返回优化建议、写操作不走安全层
"""

import json
import re
import sys
from unittest.mock import MagicMock

import pytest

# 部分模块间接 import openai，mock 掉避免环境依赖
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()

from gyra.agent.tools.context import ToolContext
from gyra_serve.agent.capabilities.db.tools import _db_tools_impl
from gyra_serve.sql_guard.safe_exec import (
    apply_select_limit,
    run_select_with_limits,
    timeout_error_message,
)


# --------------------------- apply_select_limit ---------------------------


class TestApplySelectLimit:
    def test_mysql_injects_limit_when_missing(self):
        sql = apply_select_limit("SELECT id FROM t", "mysql", 2000)
        assert sql == "SELECT id FROM t LIMIT 2000"

    def test_mysql_strips_trailing_semicolon(self):
        sql = apply_select_limit("SELECT id FROM t;", "mysql", 2000)
        assert sql == "SELECT id FROM t LIMIT 2000"

    def test_caps_excessive_limit(self):
        sql = apply_select_limit("SELECT id FROM t LIMIT 50000", "mysql", 2000)
        assert "LIMIT 2000" in sql
        assert "50000" not in sql

    def test_keeps_smaller_limit(self):
        sql = apply_select_limit("SELECT id FROM t LIMIT 100", "mysql", 2000)
        assert sql == "SELECT id FROM t LIMIT 100"

    def test_postgres_and_sqlite_supported(self):
        assert apply_select_limit("SELECT 1", "postgresql", 2000).endswith("LIMIT 2000")
        assert apply_select_limit("SELECT 1", "sqlite", 2000).endswith("LIMIT 2000")

    def test_oracle_not_rewritten(self):
        sql = "SELECT id FROM t"
        assert apply_select_limit(sql, "oracle", 2000) == sql

    def test_mssql_not_rewritten(self):
        sql = "SELECT id FROM t"
        assert apply_select_limit(sql, "mssql", 2000) == sql

    def test_non_select_untouched(self):
        sql = "UPDATE t SET a = 1 WHERE id = 1"
        assert apply_select_limit(sql, "mysql", 2000) == sql
        show = "SHOW TABLES"
        assert apply_select_limit(show, "mysql", 2000) == show

    def test_with_cte_gets_limit(self):
        sql = apply_select_limit(
            "WITH x AS (SELECT 1 AS a) SELECT a FROM x", "mysql", 2000
        )
        assert sql.endswith("LIMIT 2000")

    def test_limit_le_zero_disables(self):
        sql = "SELECT id FROM t"
        assert apply_select_limit(sql, "mysql", 0) == sql
        assert apply_select_limit(sql, "mysql", -1) == sql


# ------------------------- run_select_with_limits -------------------------


def _make_query_ex_connector(rows_count: int, dialect: str = "sqlite") -> MagicMock:
    """忠实模拟 query_ex:尊重 max_rows 截断。"""
    connector = MagicMock()
    connector.db_type = dialect
    connector.dialect = dialect

    def _query_ex(sql, fetch="all", timeout=None, params=None, max_rows=None):
        rows = [[i, f"name_{i}"] for i in range(1, rows_count + 1)]
        if max_rows is not None:
            rows = rows[:max_rows]
        return (["id", "name"], rows)

    connector.query_ex.side_effect = _query_ex
    return connector


class TestRunSelectWithLimits:
    def test_returns_run_shape(self):
        connector = _make_query_ex_connector(5)
        result, truncated = run_select_with_limits(
            connector, "SELECT 1", timeout=30, max_rows=2000
        )
        assert result[0] == ("id", "name")
        assert len(result) == 6  # 表头 + 5 行
        assert truncated is False

    def test_sentinel_detects_truncation(self):
        connector = _make_query_ex_connector(3000)
        result, truncated = run_select_with_limits(
            connector, "SELECT 1", timeout=30, max_rows=2000
        )
        # 哨兵多取一行被识别并裁掉,最终恰好 2000 行
        assert len(result) == 2001  # 表头 + 2000 行
        assert truncated is True

    def test_max_rows_le_zero_unlimited(self):
        connector = _make_query_ex_connector(3000)
        result, truncated = run_select_with_limits(
            connector, "SELECT 1", timeout=30, max_rows=0
        )
        assert len(result) == 3001
        assert truncated is False

    def test_timeout_le_zero_passes_none(self):
        connector = _make_query_ex_connector(5)
        run_select_with_limits(connector, "SELECT 1", timeout=0, max_rows=10)
        assert connector.query_ex.call_args.kwargs["timeout"] is None

    def test_fallback_to_run_without_query_ex(self):
        connector = MagicMock(spec=["run"])  # 无 query_ex 属性
        connector.run.return_value = [["a"], [1]]
        result, truncated = run_select_with_limits(
            connector, "SELECT 1", timeout=30, max_rows=10
        )
        assert result == [["a"], [1]]
        assert truncated is False
        connector.run.assert_called_once_with("SELECT 1")

    def test_empty_result(self):
        connector = MagicMock()
        connector.query_ex.return_value = ([], None)
        result, truncated = run_select_with_limits(
            connector, "SELECT 1", timeout=30, max_rows=10
        )
        assert result == []
        assert truncated is False

    def test_timeout_propagates(self):
        connector = MagicMock()
        connector.query_ex.side_effect = TimeoutError("Query exceeded timeout")
        with pytest.raises(TimeoutError):
            run_select_with_limits(connector, "SELECT 1", timeout=30, max_rows=10)


# --------------------------- execute_sql 集成 ---------------------------


def _parse_sql_query_vis(text: str) -> dict:
    m = re.search(r"```d-sql-query\s*\n(.*?)\n```", text, re.DOTALL)
    assert m, f"d-sql-query VIS not found in output:\n{text}"
    return json.loads(m.group(1))


def _make_context(connector: MagicMock, ds_id: int = 42) -> ToolContext:
    db_resource = MagicMock()
    db_resource._connector = connector
    db_resource._datasource_id = ds_id
    ctx = ToolContext()
    ctx.set_resource("db_resource", db_resource)
    return ctx


@pytest.fixture
def passthrough_masking(monkeypatch):
    """mask_run_result 透传，避免脱敏规则查库引入不确定性。"""

    def _passthrough(ds_id, columns, all_rows, session_id=None):
        return columns, all_rows, []

    import gyra_serve.sql_guard.masking as masking_mod

    monkeypatch.setattr(masking_mod, "mask_run_result", _passthrough)


class TestExecuteSqlSafety:
    @pytest.mark.asyncio
    async def test_interactive_truncation_annotated(self, passthrough_masking):
        """超过 SQL_MAX_ROWS(默认 2000)的结果被截断并标注。"""
        connector = _make_query_ex_connector(3000)
        ctx = _make_context(connector)
        out = await _db_tools_impl.execute_sql(
            db_name="test_db", sql="SELECT id, name FROM t", context=ctx
        )
        data = _parse_sql_query_vis(out)
        assert data["total_rows"] == 2000
        assert "result_truncation_note" in data
        assert "2000" in data["result_truncation_note"]

    @pytest.mark.asyncio
    async def test_limit_injected_into_sql(self, passthrough_masking):
        """无 LIMIT 的查询在 LIMIT 系方言上被注入 LIMIT 2000。"""
        connector = _make_query_ex_connector(10)
        ctx = _make_context(connector)
        await _db_tools_impl.execute_sql(
            db_name="test_db", sql="SELECT id FROM t", context=ctx
        )
        executed_sql = connector.query_ex.call_args.args[0]
        assert executed_sql.endswith("LIMIT 2000")

    @pytest.mark.asyncio
    async def test_timeout_returns_guidance(self, passthrough_masking):
        connector = _make_query_ex_connector(10)
        connector.query_ex.side_effect = TimeoutError("Query exceeded timeout")
        ctx = _make_context(connector)
        out = await _db_tools_impl.execute_sql(
            db_name="test_db", sql="SELECT id FROM t", context=ctx
        )
        assert "SQL 执行错误" in out
        assert "被终止" in out
        assert "时间过滤" in out

    @pytest.mark.asyncio
    async def test_write_keeps_legacy_path(self, passthrough_masking, monkeypatch):
        """写操作(NATIVE_SQL_CAN_RUN_WRITE=true)不走安全层,仍用 connector.run。"""
        from gyra._private.config import Config

        # Config 是 Singleton,属性在实例上,patch 类属性会被实例属性遮蔽
        monkeypatch.setattr(Config(), "NATIVE_SQL_CAN_RUN_WRITE", True)
        connector = _make_query_ex_connector(0)
        connector.run.return_value = [["id"], [1]]
        ctx = _make_context(connector)
        await _db_tools_impl.execute_sql(
            db_name="test_db",
            sql="UPDATE t SET name = 'x' WHERE id = 1",
            context=ctx,
        )
        connector.run.assert_called_once()
        connector.query_ex.assert_not_called()


def test_timeout_error_message_content():
    msg = timeout_error_message(30, 2000)
    assert "30s" in msg
    assert "2000" in msg
    assert "1 年" in msg
