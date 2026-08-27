"""AppCard 子应用数据空间 —— 记录(文档) + KV 存储模型。

使用**自身元数据库**(与 AppCardEntity 同源),与「外部数据源资源」(query.sql /
DBResource 管理的 datasource)完全解耦:外部库由用户配置的数据源管理,而子应用
自己的读写走这套表。

隔离键 = (workspace_id, app_card_id):每个子应用拥有独立的数据空间。
- 记录表(collection):问卷答卷 / 工单等「集合」数据,字段自定义(data_json),支持过滤/分页/聚合。
- KV 表:卡片级配置 / 草稿 / 用户进度等「点」数据,按 key 读写。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from gyra.storage.metadata import BaseDao, Model

APP_CARD_RECORD_TABLE_NAME = "app_card_record"
APP_CARD_KV_TABLE_NAME = "app_card_kv"


def _dump_json(v: Optional[Any]):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _load_json(v: Optional[Any]):
    if not v:
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return None


class AppCardRecordEntity(Model):
    __tablename__ = APP_CARD_RECORD_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    app_card_id = Column(Integer, nullable=False, index=True)
    collection = Column(String(64), nullable=False, default="records")
    record_id = Column(String(64), nullable=False)
    dedupe_key = Column(String(128), nullable=True)
    data_json = Column(Text, nullable=False, default="{}")
    created_by = Column(String(128), nullable=True)

    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index(
            "uk_app_card_record_rid",
            "workspace_id", "app_card_id", "collection", "record_id",
            unique=True,
        ),
        Index(
            "uk_app_card_record_dedupe",
            "workspace_id", "app_card_id", "collection", "dedupe_key",
            unique=True,
        ),
    )


class AppCardKvEntity(Model):
    __tablename__ = APP_CARD_KV_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    app_card_id = Column(Integer, nullable=False, index=True)
    key = Column(String(128), nullable=False)
    value_json = Column(Text, nullable=False, default="null")
    created_by = Column(String(128), nullable=True)

    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("uk_app_card_kv", "workspace_id", "app_card_id", "key", unique=True),
    )


class AppCardRecordDao(BaseDao[AppCardRecordEntity, Dict[str, Any], Dict[str, Any]]):
    """记录表 DAO:仅复用 BaseDao 的会话管理,查询/写入由业务层驱动(JSON 字段动态)。"""

    def from_request(self, request: Dict[str, Any]) -> AppCardRecordEntity:
        return AppCardRecordEntity(**request)

    def to_request(self, entity: AppCardRecordEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "workspace_id": entity.workspace_id,
            "app_card_id": entity.app_card_id,
            "collection": entity.collection,
            "record_id": entity.record_id,
            "dedupe_key": entity.dedupe_key,
            "data_json": entity.data_json,
            "created_by": entity.created_by,
            "gmt_created": str(entity.gmt_created) if entity.gmt_created else None,
            "gmt_modified": str(entity.gmt_modified) if entity.gmt_modified else None,
        }

    def to_response(self, entity: AppCardRecordEntity) -> Dict[str, Any]:
        return {
            "workspace_id": entity.workspace_id,
            "app_card_id": entity.app_card_id,
            "collection": entity.collection,
            "record_id": entity.record_id,
            "data": _load_json(entity.data_json) or {},
            "created_by": entity.created_by,
            "gmt_created": str(entity.gmt_created) if entity.gmt_created else None,
            "gmt_modified": str(entity.gmt_modified) if entity.gmt_modified else None,
        }


class AppCardKvDao(BaseDao[AppCardKvEntity, Dict[str, Any], Dict[str, Any]]):
    """KV 表 DAO。"""

    def from_request(self, request: Dict[str, Any]) -> AppCardKvEntity:
        return AppCardKvEntity(**request)

    def to_request(self, entity: AppCardKvEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "workspace_id": entity.workspace_id,
            "app_card_id": entity.app_card_id,
            "key": entity.key,
            "value_json": entity.value_json,
        }

    def to_response(self, entity: AppCardKvEntity) -> Dict[str, Any]:
        return {
            "key": entity.key,
            "value": _load_json(entity.value_json),
            "gmt_modified": str(entity.gmt_modified) if entity.gmt_modified else None,
        }
