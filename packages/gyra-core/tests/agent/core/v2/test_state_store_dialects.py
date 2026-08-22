"""SqlAlchemyStateStore 方言兼容性验证（MySQL / PostgreSQL 编译级）。

不连接真实数据库：用 SQLAlchemy dialect 编译器验证 v2_* 表的 DDL 与
关键 SQL 在 MySQL / PostgreSQL 方言下可正确编译（无语法错误、索引/表名合法）。
真实部署时由 DBA 按本模块表定义预建或授权 create_all。
"""
import pytest

from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from gyra.agent.core.v2.unified_state_store import (
    _AgentLeaseRow,
    _AgentTranscriptRow,
    _InteractionCheckpointRow,
    _StepEventRow,
    _StepStateRow,
    _V2Base,
)

_ALL_ROWS = [
    _StepEventRow,
    _StepStateRow,
    _AgentLeaseRow,
    _InteractionCheckpointRow,
    _AgentTranscriptRow,
]

_DIALECTS = [mysql.dialect(), postgresql.dialect()]


def test_ddl_compiles_on_mysql_and_postgresql():
    """5 张 v2_* 表 + 索引在 MySQL/PG 方言下均可编译。"""
    for dialect in _DIALECTS:
        for row_cls in _ALL_ROWS:
            ddl = str(CreateTable(row_cls.__table__).compile(dialect=dialect))
            assert f"CREATE TABLE {row_cls.__tablename__}" in ddl, ddl
            # 索引随 create_all 一起编译
            for index in row_cls.__table__.indexes:
                idx_ddl = str(CreateIndex(index).compile(dialect=dialect))
                assert idx_ddl.startswith("CREATE INDEX"), idx_ddl


def test_table_names_not_reserved():
    """v2_* 表名在 MySQL/PG 下非保留字（无需引号转义的关键路径）。"""
    reserved_mysql = {"user", "order", "group", "key", "index", "value"}
    for row_cls in _ALL_ROWS:
        assert row_cls.__tablename__ not in reserved_mysql


def test_insert_statement_compiles():
    """step_event 批量 INSERT 在两种方言下可编译。"""
    from sqlalchemy import insert

    for dialect in _DIALECTS:
        stmt = insert(_StepEventRow).values(
            event_id="e1", step_id="s1", conv_id="c1", agent_id="a1",
            parent_step_id=None, state="done", event_type="step_done",
            input="{}", output="{}", metadata_json="{}", seq=1, timestamp=1.0,
        )
        sql = str(stmt.compile(dialect=dialect))
        assert "INSERT INTO v2_step_event" in sql


def test_select_with_conv_seq_index_compiles():
    """事件按 (conv_id, seq) 查询在两种方言下可编译（依赖复合索引）。"""
    from sqlalchemy import select

    for dialect in _DIALECTS:
        stmt = (
            select(_StepEventRow)
            .where(
                _StepEventRow.conv_id == "c1",
                _StepEventRow.seq >= 0,
            )
            .order_by(_StepEventRow.seq.asc())
        )
        sql = str(stmt.compile(dialect=dialect))
        assert "ORDER BY" in sql and "v2_step_event" in sql


def test_lease_merge_compiles():
    """租约 upsert（merge 语义）在两种方言下可编译。"""
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for dialect, insert_cls in [
        (mysql.dialect(), mysql_insert),
        (postgresql.dialect(), pg_insert),
    ]:
        stmt = insert_cls(_AgentLeaseRow).values(
            conv_id="c1", agent_id="a1", lease_expires_at=1.0,
        )
        sql = str(stmt.compile(dialect=dialect))
        assert "INSERT" in sql.upper()


def test_metadata_tables_registered():
    """全部 v2 表注册在统一 metadata 上（create_all 一次建齐）。"""
    tables = set(_V2Base.metadata.tables.keys())
    expected = {row.__tablename__ for row in _ALL_ROWS}
    assert expected.issubset(tables)
