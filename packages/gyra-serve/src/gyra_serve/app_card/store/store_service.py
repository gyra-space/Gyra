"""AppCard 子应用数据空间服务 —— 自身元数据库上的统一读写。

与「外部数据源资源」(query.sql / DBResource)彻底解耦:子应用自己的问卷答卷、
工单等数据存于此,而非用户配置的 datasource。

写入门控策略(首版):
- 低风险直接写:store.insert / store.update / kv.put / kv.del(带字段校验 + 去重)
- 高风险进介入:store.delete(删除记录 → human-in-loop 审批通道,复用 intervention)

隔离:所有读写按 (workspace_id, app_card_id) 定位,每个子应用天然独立数据空间。
字段完全由应用自定义(data_json),可选 data_space 契约做轻量校验。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from gyra.component import SystemApp

from .models import (
    AppCardKvDao,
    AppCardKvEntity,
    AppCardRecordDao,
    AppCardRecordEntity,
    _dump_json,
    _load_json,
)

# 默认分页/上限
_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200
_MAX_RECORD_BYTES = 200 * 1024

# 高风险 op:需要人工介入审批
_HIGH_RISK_OPS = {"store.delete"}


def _default_entity() -> Dict[str, Any]:
    return {}


class AppCardStoreService:
    """子应用数据空间读写服务。"""

    def __init__(self, system_app: SystemApp):
        self._system_app = system_app
        self._record_dao = AppCardRecordDao()
        self._kv_dao = AppCardKvDao()

    # ---------------------------------------------------------------- 校验
    @staticmethod
    def _match_type(value: Any, ftype: Optional[str]) -> bool:
        if ftype in (None, "", "any"):
            return True
        if ftype == "string":
            return isinstance(value, str)
        if ftype == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if ftype == "boolean":
            return isinstance(value, bool)
        if ftype == "array":
            return isinstance(value, list)
        if ftype == "object":
            return isinstance(value, dict)
        return True

    def _validate_record(
        self, data_space: Optional[Dict[str, Any]], record: Dict[str, Any]
    ) -> Optional[str]:
        fields = (data_space or {}).get("fields") or {}
        if not fields:
            return None
        errors: List[str] = []
        for fname, spec in fields.items():
            spec = spec or {}
            required = bool(spec.get("required", False))
            present = fname in record and record[fname] not in (None, "")
            if not present:
                if required:
                    errors.append(f"缺少必填字段 {fname}")
                continue
            ftype = spec.get("type")
            if ftype and not self._match_type(record[fname], ftype):
                errors.append(f"字段 {fname} 类型应为 {ftype}")
        return "\n".join(errors) if errors else None

    @staticmethod
    def _match_filters(data: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        for k, v in (filters or {}).items():
            if isinstance(v, list):
                if data.get(k) not in v:
                    return False
            elif data.get(k) != v:
                return False
        return True

    @staticmethod
    def _ensure_record_size(params: Dict[str, Any]) -> Optional[str]:
        raw = params.get("record")
        if raw is None:
            return None
        try:
            import json as _json

            size = len(_json.dumps(raw, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:  # noqa: BLE001
            return "record 序列化失败"
        if size > _MAX_RECORD_BYTES:
            return "record 过大"
        return None

    # ---------------------------------------------------------------- 记录集合
    def insert_record(
        self,
        app_card_id: int,
        workspace_id: int,
        params: Dict[str, Any],
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        collection = params.get("collection") or "records"
        record = params.get("record") or {}
        if not isinstance(record, dict):
            return {"trust": "none", "error": "record 需为对象"}
        size_err = self._ensure_record_size(params)
        if size_err:
            return {"trust": "none", "error": size_err}
        data_space = (config or {}).get("data_space") or {}
        err = self._validate_record(data_space, record)
        if err:
            return {"trust": "none", "error": err}

        record_id = params.get("record_id") or uuid.uuid4().hex
        dedupe_key = params.get("dedupe_key")
        session = self._record_dao.get_raw_session()
        try:
            if dedupe_key:
                existing = (
                    session.query(AppCardRecordEntity)
                    .filter(
                        AppCardRecordEntity.workspace_id == workspace_id,
                        AppCardRecordEntity.app_card_id == app_card_id,
                        AppCardRecordEntity.collection == collection,
                        AppCardRecordEntity.dedupe_key == str(dedupe_key),
                    )
                    .first()
                )
                if existing is not None:
                    return {"trust": "confirmed", **self._record_dao.to_response(existing)}
            entity = AppCardRecordEntity(
                workspace_id=workspace_id,
                app_card_id=app_card_id,
                collection=collection,
                record_id=record_id,
                dedupe_key=str(dedupe_key) if dedupe_key else None,
                data_json=_dump_json(record),
                created_by=params.get("created_by"),
            )
            session.add(entity)
            session.flush()
            resp = self._record_dao.to_response(entity)
            session.commit()
            return {"trust": "confirmed", **resp}
        except Exception as e:  # noqa: BLE001
            session.rollback()
            return {"trust": "none", "error": str(e)}
        finally:
            session.close()

    def query_records(
        self,
        app_card_id: int,
        workspace_id: int,
        params: Dict[str, Any],
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        collection = params.get("collection") or "records"
        filters = params.get("filters") or {}
        page = max(1, int(params.get("page", 1) or 1))
        page_size = int(params.get("page_size", params.get("limit", _DEFAULT_PAGE_SIZE)) or _DEFAULT_PAGE_SIZE)
        page_size = min(max(1, page_size), _MAX_PAGE_SIZE)
        order_field = params.get("order_field") or "gmt_created"
        order_dir = str(params.get("order_dir") or "desc").lower()

        session = self._record_dao.get_raw_session()
        try:
            entities = (
                session.query(AppCardRecordEntity)
                .filter(
                    AppCardRecordEntity.workspace_id == workspace_id,
                    AppCardRecordEntity.app_card_id == app_card_id,
                    AppCardRecordEntity.collection == collection,
                )
                .all()
            )
            rows = [self._record_dao.to_response(e) for e in entities]
        finally:
            session.close()

        rows = [r for r in rows if self._match_filters(r.get("data") or {}, filters)]
        self._sort_rows(rows, order_field, order_dir)

        total = len(rows)
        offset = (page - 1) * page_size
        page_rows = rows[offset : offset + page_size]
        # rows 展开为「record_id + 自定义字段」的扁平对象,便于子应用直接渲染
        flat = [
            {**{"record_id": r["record_id"], "gmt_created": r["gmt_created"]}, **(r.get("data") or {})}
            for r in page_rows
        ]
        columns = self._infer_columns(flat)
        return {
            "trust": "confirmed",
            "columns": columns,
            "rows": flat,
            "row_count": len(flat),
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def update_record(
        self,
        app_card_id: int,
        workspace_id: int,
        params: Dict[str, Any],
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        collection = params.get("collection") or "records"
        record_id = params.get("record_id")
        patch = params.get("patch") or {}
        if not record_id or not isinstance(patch, dict):
            return {"trust": "none", "error": "需要 record_id + patch"}
        data_space = (config or {}).get("data_space") or {}
        err = self._validate_record(data_space, patch)
        if err:
            return {"trust": "none", "error": err}

        session = self._record_dao.get_raw_session()
        try:
            entity = (
                session.query(AppCardRecordEntity)
                .filter(
                    AppCardRecordEntity.workspace_id == workspace_id,
                    AppCardRecordEntity.app_card_id == app_card_id,
                    AppCardRecordEntity.collection == collection,
                    AppCardRecordEntity.record_id == record_id,
                )
                .first()
            )
            if entity is None:
                return {"trust": "none", "error": f"记录 {record_id} 不存在"}
            data = _load_json(entity.data_json) or {}
            data.update(patch)
            entity.data_json = _dump_json(data)
            session.flush()
            resp = self._record_dao.to_response(entity)
            session.commit()
            return {"trust": "confirmed", **resp}
        except Exception as e:  # noqa: BLE001
            session.rollback()
            return {"trust": "none", "error": str(e)}
        finally:
            session.close()

    def delete_record(
        self,
        app_card_id: int,
        workspace_id: int,
        params: Dict[str, Any],
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        collection = params.get("collection") or "records"
        record_id = params.get("record_id")
        if not record_id:
            return {"trust": "none", "error": "需要 record_id"}

        intervention = self._get_intervention_service()
        if intervention is None:
            return {
                "trust": "none",
                "error": "删除记录需人工审批(介入服务不可用)",
                "awaiting_human": True,
                "risk": "high",
            }
        try:
            from gyra_serve.intervention.api.schemas import InterventionRequest

            request = InterventionRequest(
                workspace_id=workspace_id,
                requested_by="app_card",
                question={
                    "tool": "store.delete",
                    "args": {"collection": collection, "record_id": record_id},
                },
            )
            entity = intervention.create(request=request)
            return {
                "trust": "inferred",
                "status": "awaiting_human",
                "intervention_id": getattr(entity, "id", None),
                "risk": "high",
                "note": "删除已转人工介入审批,审批通过后执行",
            }
        except Exception as e:  # noqa: BLE001
            return {"trust": "none", "error": f"介入创建失败: {e}", "awaiting_human": True, "risk": "high"}

    # ---------------------------------------------------------------- KV
    def kv_get(
        self, app_card_id: int, workspace_id: int, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        key = params.get("key")
        if not key:
            return {"trust": "none", "error": "缺少 key"}
        session = self._kv_dao.get_raw_session()
        try:
            entity = (
                session.query(AppCardKvEntity)
                .filter(
                    AppCardKvEntity.workspace_id == workspace_id,
                    AppCardKvEntity.app_card_id == app_card_id,
                    AppCardKvEntity.key == str(key),
                )
                .first()
            )
            if entity is None:
                return {"trust": "none", "error": f"key {key} 不存在"}
            return {"trust": "confirmed", **self._kv_dao.to_response(entity)}
        finally:
            session.close()

    def kv_put(
        self, app_card_id: int, workspace_id: int, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        key = params.get("key")
        value = params.get("value")
        if key is None:
            return {"trust": "none", "error": "缺少 key"}
        session = self._kv_dao.get_raw_session()
        try:
            entity = (
                session.query(AppCardKvEntity)
                .filter(
                    AppCardKvEntity.workspace_id == workspace_id,
                    AppCardKvEntity.app_card_id == app_card_id,
                    AppCardKvEntity.key == str(key),
                )
                .first()
            )
            if entity is None:
                entity = AppCardKvEntity(
                    workspace_id=workspace_id,
                    app_card_id=app_card_id,
                    key=str(key),
                    value_json=_dump_json(value),
                    created_by=params.get("created_by"),
                )
                session.add(entity)
            else:
                entity.value_json = _dump_json(value)
            session.flush()
            resp = self._kv_dao.to_response(entity)
            session.commit()
            return {"trust": "confirmed", **resp}
        except Exception as e:  # noqa: BLE001
            session.rollback()
            return {"trust": "none", "error": str(e)}
        finally:
            session.close()

    def kv_del(
        self, app_card_id: int, workspace_id: int, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        key = params.get("key")
        if key is None:
            return {"trust": "none", "error": "缺少 key"}
        session = self._kv_dao.get_raw_session()
        try:
            entity = (
                session.query(AppCardKvEntity)
                .filter(
                    AppCardKvEntity.workspace_id == workspace_id,
                    AppCardKvEntity.app_card_id == app_card_id,
                    AppCardKvEntity.key == str(key),
                )
                .first()
            )
            if entity is None:
                return {"trust": "confirmed", "key": str(key), "deleted": False}
            session.delete(entity)
            session.commit()
            return {"trust": "confirmed", "key": str(key), "deleted": True}
        except Exception as e:  # noqa: BLE001
            session.rollback()
            return {"trust": "none", "error": str(e)}
        finally:
            session.close()

    # ---------------------------------------------------------------- 辅助
    @staticmethod
    def _sort_rows(rows: List[Dict[str, Any]], order_field: str, order_dir: str) -> None:
        def _key(r: Dict[str, Any]) -> Any:
            if order_field in ("gmt_created", "gmt_modified"):
                return r.get(order_field) or ""
            return (r.get("data") or {}).get(order_field)

        reverse = order_dir == "desc"
        rows.sort(key=_key, reverse=reverse)

    @staticmethod
    def _infer_columns(rows: List[Dict[str, Any]], cap: int = 100) -> List[str]:
        cols: List[str] = []
        for r in rows[:cap]:
            for k in r.keys():
                if k not in cols:
                    cols.append(k)
        return cols

    def _get_intervention_service(self):
        if self._system_app is None:
            return None
        try:
            from gyra_serve.intervention.service.service import (
                INTERVENTION_SERVICE_COMPONENT_NAME,
                InterventionService,
            )

            return self._system_app.get_component(
                INTERVENTION_SERVICE_COMPONENT_NAME, InterventionService
            )
        except Exception:  # noqa: BLE001
            return None
