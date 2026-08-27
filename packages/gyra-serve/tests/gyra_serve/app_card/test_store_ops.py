"""AppCard store 数据空间 + op 注册表单测。"""
import types
from unittest.mock import MagicMock

import pytest

from gyra.storage.metadata import db

from gyra_serve.app_card.store.models import (  # noqa: F401  注册表
    AppCardKvEntity, AppCardRecordEntity,
)
from gyra_serve.app_card.store.store_service import AppCardStoreService
from gyra_serve.app_card.api.schemas import AppCardInvokeRequest
from gyra_serve.app_card.ops import resolve_app_card_op
from gyra_serve.app_card.service.service import AppCardService


@pytest.fixture
def store(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 'store.db'}")
    db.create_all()
    return AppCardStoreService(None)


def test_insert_and_query_records(store):
    r = store.insert_record(1, 1, {"record": {"name": "张三", "score": 88}}, None)
    assert r["trust"] == "confirmed"
    assert r["record_id"]
    assert r["data"]["name"] == "张三"

    q = store.query_records(1, 1, {}, None)
    assert q["trust"] == "confirmed"
    assert q["row_count"] == 1
    assert q["rows"][0]["name"] == "张三"


def test_query_filters_and_pagination(store):
    store.insert_record(1, 1, {"record": {"status": "open"}}, None)
    store.insert_record(1, 1, {"record": {"status": "closed"}}, None)
    store.insert_record(1, 1, {"record": {"status": "open"}}, None)

    res = store.query_records(1, 1, {"filters": {"status": "open"}}, None)
    assert res["total"] == 2
    assert res["row_count"] == 2

    page = store.query_records(1, 1, {"filters": {"status": "open"}, "page": 1, "page_size": 1}, None)
    assert page["total"] == 2
    assert page["row_count"] == 1


def test_dedupe_key_idempotent(store):
    a = store.insert_record(1, 1, {"record": {"name": "x"}, "dedupe_key": "uuid-abc"}, None)
    b = store.insert_record(1, 1, {"record": {"name": "x"}, "dedupe_key": "uuid-abc"}, None)
    assert a["record_id"] == b["record_id"]


def test_data_space_validation(store):
    config = {"data_space": {"fields": {"name": {"type": "string", "required": True}}}}
    r = store.insert_record(1, 1, {"record": {"score": 1}}, config)
    assert r["trust"] == "none"
    assert "name" in r["error"]

    ok = store.insert_record(1, 1, {"record": {"name": "ok"}}, config)
    assert ok["trust"] == "confirmed"


def test_update_record(store):
    rid = store.insert_record(1, 1, {"record": {"status": "open"}}, None)["record_id"]
    upd = store.update_record(1, 1, {"record_id": rid, "patch": {"status": "closed"}}, None)
    assert upd["data"]["status"] == "closed"


def test_delete_record_requires_human(store):
    # 未接入 intervention 时应返回 awaiting_human 提示, 而不是直接删除
    store.insert_record(1, 1, {"record": {"status": "open"}}, None)
    d = store.delete_record(1, 1, {"record_id": "whatever"}, None)
    assert d.get("awaiting_human") is True
    assert d.get("trust") == "none"


def test_kv_roundtrip(store):
    put = store.kv_put(1, 1, {"key": "draft", "value": {"step": 2}})
    assert put["trust"] == "confirmed"
    got = store.kv_get(1, 1, {"key": "draft"})
    assert got["value"]["step"] == 2
    store.kv_put(1, 1, {"key": "draft", "value": {"step": 3}})
    assert store.kv_get(1, 1, {"key": "draft"})["value"]["step"] == 3
    assert store.kv_del(1, 1, {"key": "draft"})["deleted"] is True
    assert store.kv_get(1, 1, {"key": "draft"})["trust"] == "none"


def test_isolation_by_app_card(store):
    # 不同 app_card_id 数据隔离
    store.insert_record(1, 1, {"record": {"name": "a"}}, None)
    store.insert_record(2, 1, {"record": {"name": "b"}}, None)
    assert store.query_records(1, 1, {}, None)["row_count"] == 1
    assert store.query_records(2, 1, {}, None)["row_count"] == 1


def test_unknown_op_via_dispatch(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 't2.db'}")
    db.create_all()
    svc = AppCardService(MagicMock(), MagicMock())
    svc._store_service = AppCardStoreService(None)
    entity = types.SimpleNamespace(id=1, config={})
    res = svc._dispatch(entity, 1, [], AppCardInvokeRequest(op="unknown.thing"))
    assert res["trust"] == "none"
    assert "不支持的能力" in res["error"]


def test_store_op_via_dispatch(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 't3.db'}")
    db.create_all()
    svc = AppCardService(MagicMock(), MagicMock())
    svc._store_service = AppCardStoreService(None)
    entity = types.SimpleNamespace(id=7, config={"data_space": {"fields": {"email": {"required": True}}}})
    res = svc._dispatch(
        entity, 1, [], AppCardInvokeRequest(op="store.insert",
        params={"record": {"email": "a@b.com"}})
    )
    assert res["trust"] == "confirmed"
    assert res["app_card_id"] == 7

    q = svc._dispatch(entity, 1, [], AppCardInvokeRequest(op="store.query", params={}))
    assert q["row_count"] == 1


def test_registry_resolves_builtin_and_store_ops():
    for op in ("query.sql", "query.metric", "assets.get", "store.insert", "kv.put"):
        assert resolve_app_card_op(op) is not None
    assert resolve_app_card_op("knowledge.search") is None
