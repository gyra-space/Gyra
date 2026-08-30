"""ECP 资产迁移:语义资产的导出 / 导入(可携带 JSON 快照)。

语义资产是一份可携带的 JSON 快照;跨系统迁移时只需把 payload 里的
binding.datasource_id 换成目标系统的 datasource_id,其余(对象 id/
版本链/状态/口径)原样保留,即可"点了就能用"。

TransferOps 是无状态协作者,经 svc 门面访问 DAO。
"""

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..api.schemas import AssetRefVO, SemanticObjectVO
from ..config import OBJECT_TYPES, STATUS_PROPOSED

logger = logging.getLogger(__name__)


class TransferOps:
    """导入导出协作者(无状态;经 svc 门面访问 DAO)。"""

    def __init__(self, svc: Any):
        self._svc = svc

    # ------------------------------------------------------------- helpers
    @staticmethod
    def object_to_export_dict(vo: SemanticObjectVO) -> Dict[str, Any]:
        return {
            "id": vo.id,
            "version": vo.version,
            "workspace_id": vo.workspace_id,
            "obj_type": vo.obj_type,
            "status": vo.status,
            "name": vo.name,
            "payload": dict(vo.payload or {}),
            "confidence": vo.confidence,
            "evidence": vo.evidence,
            "created_by": vo.created_by,
            "created_at": vo.created_at,
            "confirmed_by": vo.confirmed_by,
            "confirmed_at": vo.confirmed_at,
            "source": vo.source,
            "provenance": (dict(vo.provenance) if getattr(vo, "provenance", None) else None),
            "supersedes": vo.supersedes,
        }

    @staticmethod
    def asset_to_export_dict(vo: AssetRefVO) -> Dict[str, Any]:
        return {
            "id": vo.id,
            "workspace_id": vo.workspace_id,
            "kind": vo.kind,
            "ref_id": vo.ref_id,
            "ref_meta": dict(vo.ref_meta or {}),
            "status": vo.status,
            "last_checked_at": vo.last_checked_at,
        }

    @staticmethod
    def _coerce_datasource_id(value: Any) -> Any:
        """Coerce a datasource mapping value to int when possible.

        DB executor resolves connections by ``datasource_id`` (int column); a
        stray string "99" from the import UI would still usually coerce, but we
        normalise here so the imported payload is strictly well-typed.
        """
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _collect_datasource_refs(
        objects: List[Dict[str, Any]], assets: List[Dict[str, Any]]
    ) -> Dict[str, dict]:
        """Collect the DB datasource ids referenced by an export snapshot.

        Returns ``{str(datasource_id): {datasource_id, tables?, db_name?, db_type?}}``
        so the import UI can offer an old→new mapping per datasource.
        """
        refs: Dict[str, dict] = {}
        for o in objects:
            payload = o.get("payload") or {}
            if o.get("obj_type") == "entity":
                binding = payload.get("binding") or {}
                if binding.get("kind", "db") != "db":
                    continue
                ds = binding.get("datasource_id")
                if ds is None:
                    continue
                info = refs.setdefault(
                    str(ds), {"datasource_id": str(ds), "tables": []}
                )
                table = binding.get("table")
                if table and table not in info["tables"]:
                    info["tables"].append(table)
        for a in assets:
            if a.get("kind") != "db":
                continue
            ds = a.get("ref_id")
            info = refs.setdefault(
                str(ds), {"datasource_id": str(ds), "tables": []}
            )
            meta = a.get("ref_meta") or {}
            if meta.get("db_name"):
                info["db_name"] = meta["db_name"]
            if meta.get("db_type"):
                info["db_type"] = meta["db_type"]
        return refs

    # ------------------------------------------------------------- export
    def export_workspace(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Dump a workspace's semantic assets to a portable JSON snapshot."""
        svc = self._svc
        ws = svc._ws(workspace_id)
        object_dicts = [
            self.object_to_export_dict(o)
            for o in svc._object_dao.list_all_versions(ws)
        ]
        asset_dicts = [self.asset_to_export_dict(a) for a in svc._asset_dao.list(ws)]
        refs = self._collect_datasource_refs(object_dicts, asset_dicts)
        svc._oplog_dao.append("export", ws, {"objects": len(object_dicts),
                                             "assets": len(asset_dicts)})
        return {
            "format_version": 1,
            "exported_at": datetime.now().isoformat(),
            "source_workspace_id": ws,
            "datasource_refs": list(refs.values()),
            "objects": object_dicts,
            "assets": asset_dicts,
        }

    # ------------------------------------------------------------- import
    def import_workspace(
        self,
        data: Dict[str, Any],
        workspace_id: Optional[str] = None,
        datasource_map: Optional[Dict[str, Any]] = None,
        user_id: str = "system",
    ) -> Dict[str, Any]:
        """Merge an exported snapshot into a workspace (default: the target).

        ``datasource_map`` maps ``str(old_datasource_id) -> new_datasource_id``;
        every ``entity.binding.datasource_id`` and ``db`` asset ref is rewritten
        through it so the imported assets bind to the target system's DBs and can
        be used directly.
        """
        svc = self._svc
        ws = svc._ws(workspace_id)
        map_ = datasource_map or {}
        objects = data.get("objects") or []
        assets = data.get("assets") or []
        imported, skipped, errors = 0, 0, []

        for o in objects:
            obj_type = o.get("obj_type")
            try:
                if obj_type not in OBJECT_TYPES:
                    raise ValueError(f"未知对象类型 {obj_type}")
                payload = copy.deepcopy(o.get("payload") or {})
                if obj_type == "entity":
                    binding = payload.get("binding") or {}
                    ds = binding.get("datasource_id")
                    if ds is not None:
                        binding["datasource_id"] = self._coerce_datasource_id(
                            map_.get(str(ds), ds)
                        )
                    if binding:
                        payload["binding"] = binding
                vo = svc._object_dao.import_object(
                    object_id=o.get("id") or "",
                    version=int(o.get("version") or 1),
                    obj_type=obj_type,
                    workspace_id=ws,
                    status=o.get("status", STATUS_PROPOSED),
                    name=o.get("name"),
                    payload=payload,
                    confidence=o.get("confidence"),
                    evidence=o.get("evidence"),
                    created_by=o.get("created_by") or "import",
                    created_at=o.get("created_at"),
                    confirmed_by=o.get("confirmed_by"),
                    confirmed_at=o.get("confirmed_at"),
                    source=o.get("source"),
                    provenance=o.get("provenance"),
                    supersedes=o.get("supersedes"),
                )
                if vo:
                    imported += 1
                    svc._refresh_edges(vo, ws)
                else:
                    skipped += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"{o.get('id')}: {e}")

        assets_imported = 0
        for a in assets:
            try:
                kind = a.get("kind")
                if kind == "db":
                    old = a.get("ref_id")
                    new = map_.get(str(old), old)
                    svc._asset_dao.register(
                        "db", str(new), ws, ref_meta=a.get("ref_meta") or {}
                    )
                elif kind in ("document", "space", "api"):
                    svc._asset_dao.register(
                        kind,
                        a.get("ref_id") or "",
                        ws,
                        ref_meta=a.get("ref_meta") or {},
                    )
                else:
                    continue
                assets_imported += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"asset:{a.get('kind')}:{a.get('ref_id')}: {e}")

        svc._oplog_dao.append(
            "import", ws,
            {"imported": imported, "skipped": skipped,
             "assets_imported": assets_imported, "errors": errors[:20],
             "by": user_id},
        )
        return {
            "workspace_id": ws,
            "imported": imported,
            "skipped": skipped,
            "assets_imported": assets_imported,
            "errors": errors,
        }
