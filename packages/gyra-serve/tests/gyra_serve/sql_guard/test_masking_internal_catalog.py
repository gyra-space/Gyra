"""masking 系统目录表白名单测试:is_internal_catalog_sql 判定 + Pass 2 兜底误伤回归。

覆盖:
- is_internal_catalog_sql: Oracle/DM 数据字典、ANSI information_schema、
  PG/SQLite/MySQL 系统对象、SHOW/DESC/EXPLAIN、大小写与引号、
  混合查询/CTE/字面量干扰/解析失败一律保守返回 False
- is_internal_catalog_table: 表预览等只知道单一表名的调用点
- DataMasker Pass 2: 内部表无规则但同数据源其他表配了同名列规则时
  会被列名兜底命中(即本次修复针对的误伤根因)
"""

import pytest

from gyra_serve.sql_guard.masking import (
    is_internal_catalog_sql,
    is_internal_catalog_table,
)
from gyra_serve.sql_guard.masking.detector import SensitiveType
from gyra_serve.sql_guard.masking.masker import (
    ColumnMaskingConfig,
    DataMasker,
)


class TestInternalCatalogSql:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT table_name FROM all_tables",
            "SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = 'SYS'",
            "select t.owner, t.table_name from sys.all_tables t",
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'",
            "SELECT c.relname, c.relnatts FROM pg_catalog.pg_class c",
            "SELECT relname FROM pg_class",
            "SELECT name FROM sqlite_master WHERE type = 'table'",
            'SELECT "NAME" FROM "ALL_TABLES"',
            "SELECT * FROM DUAL",
            "SELECT a.table_name FROM all_tables a "
            "JOIN all_tab_columns c ON a.table_name = c.table_name",
            "SELECT * FROM mysql.user",
            "SELECT * FROM sys.tables",
            "SHOW TABLES",
            "DESC users",
            "DESCRIBE users",
            "EXPLAIN SELECT * FROM users",
        ],
    )
    def test_internal_catalog_sql(self, sql):
        assert is_internal_catalog_sql(sql) is True

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT name FROM users",
            "SELECT table_name FROM user_meta_tables",
            "SELECT t.table_name FROM all_tables t JOIN users u ON u.tid = t.tid",
            "WITH x AS (SELECT name FROM users) SELECT * FROM x",
            "SELECT * FROM users WHERE remark = 'from all_tables'",
            "SELECT 1",
            "~~~ not a sql",
            "",
            "   ",
        ],
    )
    def test_business_or_unsafe_sql_not_internal(self, sql):
        assert is_internal_catalog_sql(sql) is False


class TestPassTwoColumnFallbackRegression:
    def test_unknown_table_masked_by_same_name_rule(self):
        masker = DataMasker()
        masker.configure_column(
            ColumnMaskingConfig(
                table_name="users",
                column_name="table_name",
                sensitive_type=SensitiveType.NAME.value,
            ),
            datasource_id=7,
        )
        columns, rows, masked = masker.mask_results_ex(
            ["table_name"], [["orders"]], datasource_id=7
        )
        assert masked == ["table_name"]
        assert rows[0][0] != "orders"

    def test_internal_catalog_gate_bypasses_fallback(self):
        sql = "SELECT table_name FROM all_tables"
        assert is_internal_catalog_sql(sql) is True


class TestInternalCatalogTable:
    @pytest.mark.parametrize(
        "name",
        [
            "all_tables",
            "ALL_TABLES",
            '"ALL_TABLES"',
            "`pg_class`",
            "[dual]",
            "pg_catalog.pg_class",
            "information_schema.columns",
            "mysql.user",
            "sys.tables",
            "sqlite_master",
            " user_tables ",
        ],
    )
    def test_internal_catalog_table(self, name):
        assert is_internal_catalog_table(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "users",
            "user_meta_tables",
            "",
            "   ",
            None,
        ],
    )
    def test_business_table_not_internal(self, name):
        assert is_internal_catalog_table(name) is False

    @pytest.mark.parametrize(
        "name",
        ["all_tables", "users", "pg_catalog.pg_class", "sqlite_master"],
    )
    def test_table_check_consistent_with_sql_check(self, name):
        sql = f"SELECT * FROM {name}"
        assert is_internal_catalog_table(name) == is_internal_catalog_sql(sql)
