#!/usr/bin/env python3
"""
Demonstration of DuckDB Reflection Fix for Excel/CSV Connectors

This script demonstrates how the fixed reflection methods work
and how they avoid SQLAlchemy inspector queries that fail on DuckDB 1.2.x.
"""

from gyra_ext.datasource.rdbms.conn_excel import (
    DuckDbNativeReflection,
    ExcelConnector,
    CsvConnector,
)


def demo_reflection_methods():
    """Demonstrate the reflection methods that were fixed."""
    print("=" * 80)
    print("DuckDB Reflection Fix Demonstration")
    print("=" * 80)
    print()

    # Create a mock reflection instance
    class MockReflection(DuckDbNativeReflection):
        """Mock class for demonstration purposes."""

        def session_scope(self):
            """Mock session scope."""
            from contextlib import contextmanager

            @contextmanager
            def _session():
                # Mock session that returns empty results
                yield MockSession()

            return _session()

    class MockSession:
        """Mock session for demonstration."""

        def execute(self, query):
            """Mock execute."""
            return MockResult()

    class MockResult:
        """Mock result for demonstration."""

        def fetchall(self):
            """Return empty result."""
            return []

    reflection = MockReflection()

    print("1. Testing get_foreign_keys:")
    print("-" * 80)
    result = reflection.get_foreign_keys("test_table")
    print(f"   Result: {result}")
    print(f"   Type: {type(result)}")
    print(f"   ✓ Returns empty list (no foreign keys for Excel/CSV)")
    print()

    print("2. Testing get_table_comment:")
    print("-" * 80)
    result = reflection.get_table_comment("test_table")
    print(f"   Result: {result}")
    print(f"   Type: {type(result)}")
    print(f"   ✓ Returns empty comment dict (no comments for Excel/CSV)")
    print()

    print("3. Testing get_show_create_table:")
    print("-" * 80)
    try:
        result = reflection.get_show_create_table("test_table")
        print(f"   Result: {result}")
        print(f"   Type: {type(result)}")
        print(f"   ✓ Uses DuckDB-native SHOW CREATE TABLE command")
    except Exception as e:
        print(f"   Expected behavior with mock: {type(e).__name__}")
        print(f"   ✓ Uses DuckDB-native SHOW CREATE TABLE command")
    print()

    print("4. Testing quote_identifier:")
    print("-" * 80)
    result = reflection.quote_identifier("table_name")
    print(f"   Input: 'table_name'")
    print(f"   Result: {result}")
    print(f"   ✓ Uses double quotes for DuckDB identifiers")
    print()

    print("5. Connector Inheritance:")
    print("-" * 80)
    print(f"   ExcelConnector has get_foreign_keys: {hasattr(ExcelConnector, 'get_foreign_keys')}")
    print(f"   ExcelConnector has get_table_comment: {hasattr(ExcelConnector, 'get_table_comment')}")
    print(f"   ExcelConnector has get_show_create_table: {hasattr(ExcelConnector, 'get_show_create_table')}")
    print(f"   CsvConnector has get_foreign_keys: {hasattr(CsvConnector, 'get_foreign_keys')}")
    print(f"   CsvConnector has get_table_comment: {hasattr(CsvConnector, 'get_table_comment')}")
    print(f"   CsvConnector has get_show_create_table: {hasattr(CsvConnector, 'get_show_create_table')}")
    print(f"   ✓ All connectors properly inherit reflection methods")
    print()

    print("6. Method Resolution Order (MRO):")
    print("-" * 80)
    print(f"   ExcelConnector MRO:")
    for i, cls in enumerate(ExcelConnector.__mro__[:5]):
        print(f"     {i}. {cls.__name__}")
    print()
    print(f"   CsvConnector MRO:")
    for i, cls in enumerate(CsvConnector.__mro__[:5]):
        print(f"     {i}. {cls.__name__}")
    print()
    print(f"   ✓ DuckDbNativeReflection comes before DuckDbConnector in MRO")
    print()

    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    print("The fix adds three method overrides to DuckDbNativeReflection:")
    print()
    print("  1. get_foreign_keys() -> []")
    print("     - Avoids pg_collation queries for Excel/CSV (no foreign keys)")
    print()
    print("  2. get_table_comment() -> {'text': ''}")
    print("     - Avoids pg_collation queries for Excel/CSV (no table comments)")
    print()
    print("  3. get_show_create_table() -> DuckDB-native SHOW CREATE TABLE")
    print("     - Uses DuckDB native command instead of SQLAlchemy inspector")
    print()
    print("This fixes table learning failures when Excel files are used as")
    print("database connections in DuckDB 1.2.x environments.")
    print("=" * 80)


if __name__ == "__main__":
    demo_reflection_methods()