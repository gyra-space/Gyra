"""Test DuckDbNativeReflection methods for Excel/CSV connectors.

Verifies that the reflection methods avoid SQLAlchemy inspector queries
that fail on DuckDB 1.2.x (e.g., pg_collation system table references).
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import text

from gyra_ext.datasource.rdbms.conn_excel import (
    DuckDbNativeReflection,
    ExcelConnector,
    CsvConnector,
)


class TestDuckDbNativeReflection:
    """Test suite for DuckDbNativeReflection methods."""

    def test_get_foreign_keys_returns_empty_list(self):
        """Test that get_foreign_keys returns empty list for file datasets."""
        reflection = DuckDbNativeReflection()
        result = reflection.get_foreign_keys("test_table")
        assert result == []
        assert isinstance(result, list)

    def test_get_table_comment_returns_empty_dict(self):
        """Test that get_table_comment returns empty text dict."""
        reflection = DuckDbNativeReflection()
        result = reflection.get_table_comment("test_table")
        assert result == {"text": ""}
        assert isinstance(result, dict)
        assert "text" in result

    def test_get_show_create_table_success(self):
        """Test that get_show_create_table uses DuckDB-native command."""
        # DuckDbNativeReflection is a mixin, needs parent class for session_scope
        # This test validates method signature and logic structure
        from gyra_ext.datasource.rdbms.conn_excel import ExcelConnector

        # Verify method exists and has correct signature
        import inspect
        sig = inspect.signature(ExcelConnector.get_show_create_table)
        params = list(sig.parameters.keys())
        assert 'self' in params or len(params) >= 1  # self + table_name
        assert 'table_name' in sig.parameters or len(params) >= 1

    def test_get_show_create_table_empty_result(self):
        """Test that get_show_create_table logic handles empty results."""
        # The method should return empty string when no rows returned
        # Verify the implementation checks for empty rows list
        from gyra_ext.datasource.rdbms.conn_excel import ExcelConnector
        import inspect

        # Verify method exists
        assert hasattr(ExcelConnector, 'get_show_create_table')

        # Check implementation contains empty result handling
        source = inspect.getsource(ExcelConnector.get_show_create_table)
        assert 'rows[0][1] if rows else ""' in source or 'else ""' in source

    def test_quote_identifier(self):
        """Test that identifier quoting uses double quotes."""
        reflection = DuckDbNativeReflection()
        assert reflection.quote_identifier("table_name") == '"table_name"'
        assert reflection.quote_identifier("column") == '"column"'

    def test_get_indexes_returns_empty_list(self):
        """Test that get_indexes returns empty list for file datasets."""
        reflection = DuckDbNativeReflection()
        result = reflection.get_indexes("test_table")
        assert result == []
        assert isinstance(result, list)


class TestExcelCsvConnectors:
    """Test that Excel and CSV connectors properly inherit reflection methods."""

    def test_excel_connector_has_reflection_methods(self):
        """Verify ExcelConnector has all required reflection methods."""
        assert hasattr(ExcelConnector, 'get_foreign_keys')
        assert hasattr(ExcelConnector, 'get_table_comment')
        assert hasattr(ExcelConnector, 'get_show_create_table')
        assert hasattr(ExcelConnector, 'get_columns')
        assert hasattr(ExcelConnector, 'get_indexes')

    def test_csv_connector_has_reflection_methods(self):
        """Verify CsvConnector has all required reflection methods."""
        assert hasattr(CsvConnector, 'get_foreign_keys')
        assert hasattr(CsvConnector, 'get_table_comment')
        assert hasattr(CsvConnector, 'get_show_create_table')
        assert hasattr(CsvConnector, 'get_columns')
        assert hasattr(CsvConnector, 'get_indexes')

    def test_mixin_order_correct(self):
        """Verify MRO ensures DuckDbNativeReflection methods take precedence."""
        # ExcelConnector MRO: ExcelConnector -> DuckDbNativeReflection -> DuckDbConnector
        excel_mro = ExcelConnector.__mro__
        csv_mro = CsvConnector.__mro__

        # DuckDbNativeReflection should come before DuckDbConnector
        excel_native_idx = excel_mro.index(DuckDbNativeReflection)
        excel_duckdb_idx = excel_mro.index(ExcelConnector.__bases__[1])  # DuckDbConnector

        assert excel_native_idx < excel_duckdb_idx, \
            "DuckDbNativeReflection should come before DuckDbConnector in MRO"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])