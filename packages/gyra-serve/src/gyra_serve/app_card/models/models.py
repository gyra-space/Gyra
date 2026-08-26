"""AppCard entities + DAO."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Index, desc

from gyra.storage.metadata import BaseDao, Model

from ..api.schemas import (
    AppCardCreateRequest, AppCardListFilter, AppCardResponse, AppCardUpdateRequest,
)
from ..config import SERVER_APP_TABLE_NAME

APP_CARD_TABLE_NAME = SERVER_APP_TABLE_NAME
APP_CARD_VERSION_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_version"


def _dump_json(v: Optional[Any]):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _load_json(v: Optional[str]):
    if not v:
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return None


class AppCardEntity(Model):
    __tablename__ = APP_CARD_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(String(1024), nullable=True)
    kind = Column(String(32), nullable=False, default="dashboard")
    status = Column(String(32), nullable=False, default="draft")
    code = Column(Text, nullable=False)
    config_json = Column(Text, nullable=True)
    queries_json = Column(Text, nullable=True)
    current_version = Column(Integer, nullable=False, default=1)
    source_task_id = Column(Integer, nullable=True, index=True)
    created_by = Column(String(128), nullable=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AppCardVersionEntity(Model):
    __tablename__ = APP_CARD_VERSION_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_card_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    code = Column(Text, nullable=False)
    config_json = Column(Text, nullable=True)
    queries_json = Column(Text, nullable=True)
    diff_summary = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)

    __table_args__ = (
        Index("uk_app_card_version", "app_card_id", "version", unique=True),
    )


class AppCardDao(BaseDao[AppCardEntity, AppCardCreateRequest, AppCardResponse]):
    def from_request(self, request) -> AppCardEntity:
        data = request.dict() if isinstance(request, AppCardCreateRequest) else dict(request)
        data.pop("id", None)
        data.pop("gmt_created", None)
        data.pop("gmt_modified", None)
        data.pop("current_version", None)
        data.pop("dry_run", None)
        config = data.pop("config", None)
        queries = data.pop("queries", None)
        entity = AppCardEntity(**data)
        entity.config_json = _dump_json(config)
        entity.queries_json = _dump_json(queries)
        return entity

    def to_request(self, entity: AppCardEntity) -> AppCardCreateRequest:
        return AppCardCreateRequest(
            workspace_id=entity.workspace_id,
            name=entity.name,
            description=entity.description,
            kind=entity.kind,
            code=entity.code,
            config=_load_json(entity.config_json) or {},
            queries=_load_json(entity.queries_json) or [],
            source_task_id=entity.source_task_id,
            created_by=entity.created_by,
        )

    def to_response(self, entity: AppCardEntity) -> AppCardResponse:
        return AppCardResponse(
            id=entity.id,
            workspace_id=entity.workspace_id,
            name=entity.name,
            description=entity.description,
            kind=entity.kind,
            status=entity.status,
            code=entity.code,
            config=_load_json(entity.config_json) or {},
            queries=_load_json(entity.queries_json) or [],
            current_version=entity.current_version,
            source_task_id=entity.source_task_id,
            created_by=entity.created_by,
            gmt_created=entity.gmt_created.isoformat() if entity.gmt_created else "",
            gmt_modified=entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        )

    def list_by_workspace(self, f: AppCardListFilter) -> List[AppCardResponse]:
        session = self.get_raw_session()
        try:
            entities = (
                session.query(AppCardEntity)
                .filter(
                    AppCardEntity.workspace_id == f.workspace_id,
                    AppCardEntity.status != "archived",
                )
                .order_by(desc(AppCardEntity.gmt_modified))
                .limit(f.limit)
                .all()
            )
            return [self.to_response(e) for e in entities]
        finally:
            session.close()
