"""资产迁移(导出/导入)单元测试。

覆盖核心行为:
- export_workspace:构建可携带 JSON 快照 + 收集 datasource 引用
- import_workspace:按 datasource_map 重绑 entity.binding.datasource_id,
  并把 db 资产引用登记到目标 datasource_id(合并导入,幂等)。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from gyra_serve.ecp.service.service import Service


def _vo(**kw):
    """构建语义对象 VO(SimpleNamespace 即可,导出里访问属性)。"""
    defaults = dict(
        id="ent.order",
        version=1,
        workspace_id="default",
        obj_type="entity",
        status="confirmed",
        name="销售订单",
        payload={
            "name": "销售订单",
            "aliases": ["订单"],
            "binding": {
                "kind": "db",
                "table": "tb_so_01",
                "datasource_id": 1,
                "pk": "F001",
            },
        },
        confidence=1.0,
        evidence=None,
        created_by="u1",
        created_at="2026-01-01T00:00:00",
        confirmed_by="u1",
        confirmed_at="2026-01-02T00:00:00",
        source=None,
        supersedes=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _asset_vo(**kw):
    defaults = dict(
        id=1,
        workspace_id="default",
        kind="db",
        ref_id="1",
        ref_meta={"db_name": "erp", "db_type": "mysql"},
        status="active",
        last_checked_at=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _service(monkeypatch, objects=None, assets=None):
    svc = Service.__new__(Service)
    svc._object_dao = MagicMock()
    svc._asset_dao = MagicMock()
    svc._oplog_dao = MagicMock()
    svc._edge_dao = MagicMock()
    svc._ws_config_dao = MagicMock()
    svc._system_app = MagicMock()
    svc._object_dao.list_all_versions.return_value = objects or []
    svc._asset_dao.list.return_value = assets or []
    monkeypatch.setattr(svc, "_refresh_edges", lambda vo, ws: None)
    return svc


class TestExport:
    def test_builds_snapshot_and_collects_ds_refs(self, monkeypatch):
        svc = _service(monkeypatch, objects=[_vo()], assets=[_asset_vo()])
        out = svc.export_workspace("default")

        assert out["format_version"] == 1
        assert out["source_workspace_id"] == "default"
        assert out["objects"][0]["payload"]["binding"]["datasource_id"] == 1
        # datasource ref 收集:来自 entity binding + db 资产
        ds_refs = {r["datasource_id"]: r for r in out["datasource_refs"]}
        assert "1" in ds_refs
        assert "tb_so_01" in ds_refs["1"]["tables"]
        assert ds_refs["1"]["db_name"] == "erp"
        # 导出事件写 op_log
        assert svc._oplog_dao.append.call_args.args[0] == "export"
        assert svc._oplog_dao.append.call_args.args[1] == "default"

    def test_no_objects_returns_empty_snapshot(self, monkeypatch):
        svc = _service(monkeypatch, objects=[], assets=[])
        out = svc.export_workspace("default")
        assert out["objects"] == []
        assert out["assets"] == []
        assert out["datasource_refs"] == []


class TestImport:
    def test_remaps_datasource_and_registers_asset(self, monkeypatch):
        svc = _service(monkeypatch)
        snapshot = {
            "objects": [
                {
                    "id": "ent.order",
                    "version": 1,
                    "workspace_id": "default",
                    "obj_type": "entity",
                    "status": "confirmed",
                    "name": "销售订单",
                    "payload": {
                        "binding": {
                            "kind": "db",
                            "table": "tb_so_01",
                            "datasource_id": 1,
                        }
                    },
                }
            ],
            "assets": [
                {
                    "id": 1,
                    "workspace_id": "default",
                    "kind": "db",
                    "ref_id": "1",
                    "ref_meta": {"db_name": "erp", "db_type": "mysql"},
                    "status": "active",
                }
            ],
        }
        captured = {}

        def fake_import_object(**kw):
            captured.update(kw)
            return SimpleNamespace(
                id=kw["object_id"],
                version=kw["version"],
                status=kw["status"],
                obj_type=kw["obj_type"],
            )

        svc._object_dao.import_object.side_effect = fake_import_object
        svc._asset_dao.register.return_value = SimpleNamespace(id=1)

        result = svc.import_workspace(snapshot, "default", datasource_map={"1": 99})

        assert result["imported"] == 1
        assert result["skipped"] == 0
        assert result["assets_imported"] == 1
        # entity.binding.datasource_id 已被重绑为 99
        assert captured["payload"]["binding"]["datasource_id"] == 99
        # db 资产引用以 99 重新登记
        args = svc._asset_dao.register.call_args.args
        assert args[0] == "db"
        assert args[1] == "99"
        assert args[2] == "default"

    def test_skips_existing_object(self, monkeypatch):
        svc = _service(monkeypatch)
        snapshot = {
            "objects": [
                {
                    "id": "ent.order",
                    "version": 1,
                    "workspace_id": "default",
                    "obj_type": "entity",
                    "status": "confirmed",
                    "payload": {"binding": {"kind": "db", "datasource_id": 1}},
                }
            ],
            "assets": [],
        }
        svc._object_dao.import_object.return_value = None  # 已存在 -> skip
        result = svc.import_workspace(snapshot, "default")
        assert result["imported"] == 0
        assert result["skipped"] == 1

    def test_unknown_type_goes_to_errors(self, monkeypatch):
        svc = _service(monkeypatch)
        snapshot = {
            "objects": [{"id": "x.1", "version": 1, "obj_type": "wat", "payload": {}}],
            "assets": [],
        }
        result = svc.import_workspace(snapshot, "default")
        assert result["imported"] == 0
        assert any("未知对象类型" in e for e in result["errors"])
