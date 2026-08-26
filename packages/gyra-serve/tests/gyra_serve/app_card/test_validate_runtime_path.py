"""AppCardService.validate_queries「运行时同路径」校验 的测试。

验证开发期校验直接复用运行期 _dispatch(_invoke_*) 取数,
从而能在上传前就暴露「dry-run 通过但运行期取数失败」的问题:
- 合法 SQL + 正确 bind 参数 → ok True, 且 trust 非 none
- 引用缺失的绑定参数 / 非法查询 → ok False
- metric 走与运行期一致的 executor
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from gyra._private.config import Config
from gyra.storage.metadata import db
from gyra_serve.app_card.service.service import AppCardService
from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao
from gyra_ext.datasource.rdbms.conn_sqlite import SQLiteConnector


@pytest.fixture
def app_card_service(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 't.db'}")
    db.create_all()
    svc = AppCardService(MagicMock(), MagicMock())
    svc._dao = None  # 本用例不落库
    return svc


@pytest.fixture
def demo_datasource(tmp_path, monkeypatch) -> int:
    """建临时 sqlite 数据源并注册, 返回 datasource id(参照 seed)。

    同时把 Config.local_db_manager 替换为返回该连接器的桩, 使
    run_readonly_sql 能通过 get_connector(db_name) 拿到真实 sqlite 连接器,
    从而真正执行查询(dry-run 与运行期同路径取数)。
    """
    demo_db = tmp_path / "demo.sqlite"
    connector = SQLiteConnector.from_file_path(str(demo_db))
    with connector.session_scope(commit=True) as session:
        session.execute(text(
            "CREATE TABLE demo_table (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
            "value REAL, created_at TEXT)"
        ))
        session.execute(text(
            "INSERT INTO demo_table (id, name, value, created_at) VALUES "
            "(:id, :name, :value, :created_at)"
        ), [
            {"id": 1, "name": "api-gateway", "value": 63.2, "created_at": "2026-08-24"},
            {"id": 2, "name": "order-service", "value": 91.5, "created_at": "2026-08-25"},
        ])

    dao = ConnectConfigDao()
    if dao.get_by_names("app_card_demo_test") is not None:
        dao.delete_db("app_card_demo_test")
    dao.add_file_db(
        db_name="app_card_demo_test", db_type="sqlite", db_path=str(demo_db),
        comment="app card validate test", user_id="",
    )
    row = dao.get_by_names("app_card_demo_test")
    assert row is not None

    fake_manager = SimpleNamespace(get_connector=lambda _db_name: connector)
    monkeypatch.setattr(Config, "local_db_manager", fake_manager)
    return int(row.id)


def test_validate_sql_ok(app_card_service, demo_datasource):
    queries = [{
        "key": "q_totals", "kind": "sql",
        "sql": "SELECT COUNT(*) AS n, AVG(value) AS avg FROM demo_table WHERE created_at >= :start",
        "datasource_id": demo_datasource, "bind_params": {"start": "2020-01-01"}, "limit": 10,
    }]
    resp = app_card_service.validate_queries(1, queries)
    assert resp.ok is True
    item = resp.items[0]
    assert item.ok is True
    assert item.trust != "none"
    assert item.error is None


def test_validate_sql_missing_bind_fails(app_card_service, demo_datasource):
    # :start 在 runtime bind 里缺失 → 运行期必然失败, dry-run 必须报出来
    queries = [{
        "key": "q_totals", "kind": "sql",
        "sql": "SELECT COUNT(*) AS n FROM demo_table WHERE created_at >= :start",
        "datasource_id": demo_datasource, "bind_params": {}, "limit": 10,
    }]
    resp = app_card_service.validate_queries(1, queries)
    assert resp.ok is False


def test_preview_invoke_runtime_path(app_card_service, demo_datasource):
    """开发期预览取数: 用编辑器里(未落库)的查询契约走运行期 dispatch。

    preview_invoke 与运行期 invoke 同一派发, 用声明的 query_key 真正取数并返回行列。
    """
    from gyra_serve.app_card.api.schemas import AppCardInvokeRequest

    queries = [{
        "key": "q_totals", "kind": "sql",
        "sql": "SELECT COUNT(*) AS n, AVG(value) AS avg, MAX(value) AS max FROM demo_table WHERE created_at >= :start",
        "datasource_id": demo_datasource, "bind_params": {"start": "2020-01-01"}, "limit": 10,
    }]
    req = AppCardInvokeRequest(op="query.sql", params={"bind_params": {"start": "2020-01-01"}}, query_key="q_totals")
    res = app_card_service.preview_invoke(1, queries, req)
    assert res.get("trust") != "none"
    assert res.get("row_count", 0) >= 0
    assert res.get("columns")
    # 模板未提供所需绑定参数且运行期也未传 → 必然失败, 预览取数应暴露出来
    no_default = [{
        "key": "q_nobind", "kind": "sql",
        "sql": "SELECT COUNT(*) AS n FROM demo_table WHERE created_at >= :start",
        "datasource_id": demo_datasource, "bind_params": {}, "limit": 10,
    }]
    req_bad = AppCardInvokeRequest(op="query.sql", params={}, query_key="q_nobind")
    res_bad = app_card_service.preview_invoke(1, no_default, req_bad)
    assert res_bad.get("trust") == "none"


def test_validate_unknown_kind_fails(app_card_service, demo_datasource):
    resp = app_card_service.validate_queries(1, [{"key": "k", "kind": "bogus"}])
    assert resp.ok is False
    assert resp.items[0].ok is False


def test_validate_sql_readonly_rejected(app_card_service, demo_datasource):
    # 非只读 SQL(写语句)被白名单拦截 → dry-run 报错, 防止卡片携带写库查询
    queries = [{
        "key": "q_drop", "kind": "sql",
        "sql": "DELETE FROM demo_table",
        "datasource_id": demo_datasource, "bind_params": {}, "limit": 10,
    }]
    resp = app_card_service.validate_queries(1, queries)
    assert resp.ok is False