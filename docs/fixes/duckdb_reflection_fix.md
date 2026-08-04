# DuckDB Reflection Fix for Excel/CSV Connectors

## 问题背景

当 Excel 文件作为数据库链接时，表学习过程会失败，原因是 DuckDB 1.2.x 不完全支持 PostgreSQL 的系统表（如 `pg_collation`）。

## 根本原因

1. **触发点**: `get_table_comment` 和 `get_foreign_keys` 方法使用 SQLAlchemy inspector，触发了 PostgreSQL 风格的查询
2. **影响**: 这些查询尝试访问 DuckDB 不支持的系统表，导致表学习失败
3. **范围**: `DuckDbNativeReflection` 类已有部分方法重写，但缺失了表学习过程中需要的其他方法

## 解决方案

在 `DuckDbNativeReflection` 类中添加了三个方法重写：

### 1. `get_foreign_keys(self, table_name: str) -> List[Dict]`
- **实现**: 返回空列表 `[]`
- **原因**: Excel/CSV 文件没有关系型约束
- **影响**: 避免 SQLAlchemy inspector 查询系统表

### 2. `get_table_comment(self, table_name: str) -> Dict`
- **实现**: 返回 `{"text": ""}`
- **原因**: Excel/CSV 文件没有表注释
- **影响**: 避免 SQLAlchemy inspector 查询 `pg_collation` 等系统表

### 3. `get_show_create_table(self, table_name: str) -> str`
- **实现**: 使用 DuckDB 原生的 `SHOW CREATE TABLE` 命令
- **原因**: 利用 DuckDB 原生功能，避免依赖 SQLAlchemy inspector
- **影响**: 使用 DuckDB 原生命令获取表结构

## 方法对比表

| 方法 | 实现 | 原因 |
|------|------|------|
| `get_foreign_keys` | 返回 `[]` | Excel/CSV 无外键 |
| `get_table_comment` | 返回 `{"text": ""}` | Excel/CSV 无表注释 |
| `get_show_create_table` | 使用 `SHOW CREATE TABLE` | DuckDB 原生命令 |

## 代码变更

### 文件: `packages/gyra-ext/src/gyra_ext/datasource/rdbms/conn_excel.py`

```python
class DuckDbNativeReflection:
    # ... 现有方法 ...

    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """File datasets carry no foreign keys.

        Excel/CSV files have no relational constraints, so return empty list.
        This avoids SQLAlchemy inspector queries that fail on DuckDB 1.2.x
        (e.g., pg_collation system table references).
        """
        return []

    def get_table_comment(self, table_name: str) -> Dict:
        """Get table comment for specified table.

        Excel/CSV files have no table comments, so return empty text.
        This avoids SQLAlchemy inspector queries that fail on DuckDB 1.2.x.
        """
        return {"text": ""}

    def get_show_create_table(self, table_name: str) -> str:
        """Get SHOW CREATE TABLE output using DuckDB-native command.

        DuckDB supports SHOW CREATE TABLE natively, avoiding SQLAlchemy
        inspector dependencies on PostgreSQL system tables.
        """
        with self.session_scope() as session:
            rows = session.execute(
                text(f'SHOW CREATE TABLE "{table_name}"')
            ).fetchall()
            return rows[0][1] if rows else ""
```

## 测试验证

创建了 `tests/test_duckdb_reflection_fix.py` 测试文件，包含：

1. **方法返回值测试**: 验证新增方法返回正确的值
2. **连接器继承测试**: 确认 ExcelConnector 和 CsvConnector 正确继承方法
3. **MRO 测试**: 验证方法解析顺序确保 DuckDbNativeReflection 优先

所有测试通过：

```bash
$ python -m pytest tests/test_duckdb_reflection_fix.py -v
...
test_duckdb_reflection_fix.py::TestDuckDbNativeReflection::test_get_foreign_keys_returns_empty_list PASSED
test_duckdb_reflection_fix.py::TestDuckDbNativeReflection::test_get_table_comment_returns_empty_dict PASSED
test_duckdb_reflection_fix.py::TestDuckDbNativeReflection::test_get_show_create_table_success PASSED
test_duckdb_reflection_fix.py::TestDuckDbNativeReflection::test_get_show_create_table_empty_result PASSED
test_duckdb_reflection_fix.py::TestDuckDbNativeReflection::test_quote_identifier PASSED
test_duckdb_reflection_fix.py::TestDuckDbNativeReflection::test_get_indexes_returns_empty_list PASSED
test_duckdb_reflection_fix.py::TestExcelCsvConnectors::test_excel_connector_has_reflection_methods PASSED
test_duckdb_reflection_fix.py::TestExcelCsvConnectors::test_csv_connector_has_reflection_methods PASSED
test_duckdb_reflection_fix.py::TestExcelCsvConnectors::test_mixin_order_correct PASSED
========================= 9 passed, 1 warning in 0.36s =========================
```

## 影响范围

- **受益连接器**: ExcelConnector, CsvConnector
- **修复场景**: Excel/CSV 文件上传后的表学习过程
- **兼容性**: 保持与现有代码的完全兼容，仅添加方法重写

## 相关链接

- 问题来源: DuckDB 1.2.x 与 SQLAlchemy inspector 的兼容性问题
- 解决思路: 使用 DuckDB 原生命令替代 SQLAlchemy inspector
- 参考: 类似问题在其他项目中的修复方案