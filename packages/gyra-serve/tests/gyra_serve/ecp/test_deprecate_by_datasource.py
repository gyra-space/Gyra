"""SemanticObjectDao.deprecate_by_datasource 单元测试。

删数据库时的 ECP 级联失效:
- entity 通过 payload.binding.datasource_id 直接绑定到 datasource(锚点)
- metric/dimension 通过 payload.entity、relation 通过 from/to 指向锚点实体,
  间接绑定到同一 datasource
- 只有 proposed / confirmed 版本被标记 deprecated(rejected/superseded 不动)。
"""

import pytest

from gyra.storage.metadata import db
from gyra_serve.ecp.models.models import (
    EcpSemanticObjectEntity,
    SemanticObjectDao,
)


def _obj(oid, obj_type, version, status, payload):
    return EcpSemanticObjectEntity(
        id=oid,
        version=version,
        workspace_id="default",
        obj_type=obj_type,
        status=status,
        payload=payload,
    )


@pytest.fixture
def dao(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(f"sqlite:///{db_path}")
    db.create_all()
    yield SemanticObjectDao()


def _insert(dao, rows):
    session = dao.get_raw_session()
    session.add_all(rows)
    session.commit()
    session.close()


def _statuses(dao, oid, ws="default"):
    return {
        (v.version, v.status)
        for v in dao.version_history(oid, ws)
    }


def test_deprecates_direct_and_transitive(dao):
    rows = [
        # 绑定到 datasource 3 的锚点实体
        _obj("ent.order", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t1", "datasource_id": 3}}),
        # 直接引用该实体的 metric / dimension / relation
        _obj("mtr.sales", "metric", 1, "confirmed",
             {"entity": "ent.order", "expression": "SUM(F1)"}),
        _obj("dim.status", "dimension", 1, "proposed",
             {"entity": "ent.order", "column": "status"}),
        _obj("rel.o2s", "relation", 1, "confirmed",
             {"from": "ent.order", "to": "ent.store"}),
        # 另一个锚点实体(also ds 3)被 relation 另一端引用 —— 也应失效
        _obj("ent.store", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t2", "datasource_id": 3}}),
        # 不相关对象:绑定到 datasource 5,不应受影响
        _obj("ent.order2", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t9", "datasource_id": 5}}),
        _obj("mtr.other", "metric", 1, "confirmed",
             {"entity": "ent.order2", "expression": "SUM(F2)"}),
        # 已 rejected / superseded 的对象即使绑定到 ds 3 也不该被改
        _obj("ent.dead", "entity", 1, "rejected",
             {"binding": {"kind": "db", "table": "t3", "datasource_id": 3}}),
        _obj("ent.sup", "entity", 1, "superseded",
             {"binding": {"kind": "db", "table": "t4", "datasource_id": 3}}),
    ]
    _insert(dao, rows)

    changed = dao.deprecate_by_datasource(3)

    assert changed >= 5
    # 直接 + 间接绑定 ds3 的对象全部 deprecated
    for oid in ("ent.order", "ent.store", "mtr.sales", "dim.status", "rel.o2s"):
        assert {s for _, s in _statuses(dao, oid)} == {"deprecated"}, oid
    # 无关对象保持原状
    assert {s for _, s in _statuses(dao, "ent.order2")} == {"confirmed"}
    assert {s for _, s in _statuses(dao, "mtr.other")} == {"confirmed"}
    # rejected / superseded 不改动
    assert {s for _, s in _statuses(dao, "ent.dead")} == {"rejected"}
    assert {s for _, s in _statuses(dao, "ent.sup")} == {"superseded"}


def test_matches_int_or_str_datasource_id(dao):
    rows = [
        _obj("ent.a", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t1", "datasource_id": "3"}}),
        _obj("ent.b", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t2", "datasource_id": 3}}),
        _obj("ent.c", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t3", "datasource_id": 30}}),
    ]
    _insert(dao, rows)

    changed = dao.deprecate_by_datasource("3")

    assert changed == 2
    assert {s for _, s in _statuses(dao, "ent.a")} == {"deprecated"}
    assert {s for _, s in _statuses(dao, "ent.b")} == {"deprecated"}
    assert {s for _, s in _statuses(dao, "ent.c")} == {"confirmed"}


def test_no_match_returns_zero(dao):
    rows = [
        _obj("ent.a", "entity", 1, "confirmed",
             {"binding": {"kind": "db", "table": "t1", "datasource_id": 8}}),
    ]
    _insert(dao, rows)

    assert dao.deprecate_by_datasource(999) == 0
    assert {s for _, s in _statuses(dao, "ent.a")} == {"confirmed"}


def test_flat_legacy_datasource_id_matches(dao):
    """旧形态扁平 datasource_id(无 binding)也应命中。"""
    rows = [
        _obj("ent.legacy", "entity", 1, "confirmed", {"datasource_id": 7}),
    ]
    _insert(dao, rows)

    assert dao.deprecate_by_datasource(7) == 1
    assert {s for _, s in _statuses(dao, "ent.legacy")} == {"deprecated"}
