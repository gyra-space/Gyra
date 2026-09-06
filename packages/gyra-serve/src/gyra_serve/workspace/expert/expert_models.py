"""WorkspaceExpert / WorkspaceExpertEquipment entities + DAOs.

专家外挂资源仅可引用本空间资源池（workspace_resource）已绑定的资源：
空间 = 注册/治理池，外挂 = 选配子集，不能凭空引入。
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    desc,
)

from gyra.storage.metadata import BaseDao, Model

from ..config import SERVER_APP_TABLE_NAME

WORKSPACE_EXPERT_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_expert"
WORKSPACE_EXPERT_EQUIPMENT_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_expert_equipment"

# 外挂资源类型白名单：与 workspace_resource.type / _MATERIALIZE_DISPATCH 对齐
# （datasource 是 data_source 的别名，见 materializer._MATERIALIZE_DISPATCH）。
EXPERT_EQUIPMENT_RESOURCE_TYPES = (
    "data_source",
    "datasource",
    "knowledge_space",
    "mcp",
    "skill",
    "agent_skill",
)

logger = logging.getLogger(__name__)


def _dump_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: Any) -> Any:
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


class WorkspaceExpertEntity(Model):
    """专家成员名册：专家（GptsApp）× 空间 的成员关系。"""

    __tablename__ = WORKSPACE_EXPERT_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    app_code = Column(String(128), nullable=False, comment="专家身份（gpts_app.app_code）")
    role_hint = Column(String(256), nullable=True, comment="空间内职责说明（prompt 补丁）")
    icon = Column(String(512), nullable=True, comment="空间级头像覆盖（空则回落 GptsApp.icon）")
    default_contract_id = Column(Integer, nullable=True, comment="默认交付合约 id")
    is_active = Column(Boolean, nullable=False, default=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("workspace_id", "app_code", name="uk_workspace_expert"),
    )


class WorkspaceExpertEquipmentEntity(Model):
    """专家外挂资源明细：成员 × 空间资源池 的外挂关系（逐行）。"""

    __tablename__ = WORKSPACE_EXPERT_EQUIPMENT_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    expert_id = Column(Integer, nullable=False, index=True, comment="workspace_expert.id")
    resource_type = Column(
        String(32), nullable=False,
        comment="data_source/knowledge_space/mcp/skill（与 workspace_resource.type 对齐）",
    )
    resource_ref = Column(String(255), nullable=False, comment="引用目标（空间资源 name/physical_ref）")
    config_json = Column(Text, nullable=True, comment="外挂级参数（如知识库 top_k）")
    is_active = Column(Boolean, nullable=False, default=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint(
            "expert_id", "resource_type", "resource_ref",
            name="uk_workspace_expert_equipment",
        ),
    )


class WorkspaceExpertDao(BaseDao[WorkspaceExpertEntity, Dict[str, Any], Dict[str, Any]]):
    # Columns added in expert schema v2. Idempotent ALTER for upgrades from v1
    # (CREATE TABLE IF NOT EXISTS won't add columns to an existing table).
    _V2_COLUMNS = [
        ("icon", "VARCHAR(512)"),
    ]

    def __init__(self, db_manager=None) -> None:
        super().__init__(db_manager)
        self._migrate_v2()

    def _migrate_v2(self) -> None:
        """Add v2 columns to workspace_expert if missing (idempotent)."""
        try:
            from sqlalchemy import inspect as sa_inspect
            from sqlalchemy import text

            with self.session(commit=False) as session:
                insp = sa_inspect(session.bind)
                if WorkspaceExpertEntity.__tablename__ not in insp.get_table_names():
                    return  # table doesn't exist yet; CREATE will handle it
                existing = {
                    c["name"] for c in insp.get_columns(WorkspaceExpertEntity.__tablename__)
                }
                for col, col_type in self._V2_COLUMNS:
                    if col in existing:
                        continue
                    session.execute(
                        text(
                            f"ALTER TABLE {WorkspaceExpertEntity.__tablename__} "
                            f"ADD COLUMN {col} {col_type}"
                        )
                    )
                session.commit()
        except Exception as e:
            logger.debug("workspace expert v2 migration skipped: %s", e)

    def from_request(self, request: Union[Dict[str, Any]]) -> WorkspaceExpertEntity:
        data = dict(request)
        data.pop("id", None)
        data.pop("gmt_created", None)
        data.pop("gmt_modified", None)
        return WorkspaceExpertEntity(**data)

    def to_request(self, entity: WorkspaceExpertEntity) -> Dict[str, Any]:
        return {
            "workspace_id": entity.workspace_id,
            "app_code": entity.app_code,
            "role_hint": entity.role_hint,
            "icon": entity.icon,
            "default_contract_id": entity.default_contract_id,
            "is_active": entity.is_active,
        }

    def to_response(self, entity: WorkspaceExpertEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "workspace_id": entity.workspace_id,
            "app_code": entity.app_code,
            "role_hint": entity.role_hint,
            "icon": entity.icon,
            "default_contract_id": entity.default_contract_id,
            "is_active": bool(entity.is_active),
            "gmt_created": entity.gmt_created.isoformat() if entity.gmt_created else "",
            "gmt_modified": entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        }

    def upsert(self, workspace_id: int, app_code: str, **fields) -> WorkspaceExpertEntity:
        """幂等：按 uk(workspace_id, app_code) 存在则更新、否则创建。"""
        session = self.get_raw_session()
        try:
            if "icon" in fields:
                # '' 归一化为 NULL：空值即未覆盖，回落 GptsApp.icon
                fields["icon"] = fields["icon"] or None
            row = (
                session.query(WorkspaceExpertEntity)
                .filter(
                    WorkspaceExpertEntity.workspace_id == workspace_id,
                    WorkspaceExpertEntity.app_code == app_code,
                )
                .first()
            )
            if row is None:
                row = WorkspaceExpertEntity(workspace_id=workspace_id, app_code=app_code, **fields)
                session.add(row)
            else:
                for k, v in fields.items():
                    setattr(row, k, v)
                row.gmt_modified = datetime.now()
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_app_code(
        self, workspace_id: int, app_code: str
    ) -> Optional[WorkspaceExpertEntity]:
        session = self.get_raw_session()
        try:
            return (
                session.query(WorkspaceExpertEntity)
                .filter(
                    WorkspaceExpertEntity.workspace_id == workspace_id,
                    WorkspaceExpertEntity.app_code == app_code,
                )
                .first()
            )
        finally:
            session.close()

    def list_by_workspace(
        self, workspace_id: int, active_only: bool = True
    ) -> List[WorkspaceExpertEntity]:
        session = self.get_raw_session()
        try:
            query = session.query(WorkspaceExpertEntity).filter(
                WorkspaceExpertEntity.workspace_id == workspace_id
            )
            if active_only:
                query = query.filter(WorkspaceExpertEntity.is_active.is_(True))
            return query.order_by(desc(WorkspaceExpertEntity.gmt_modified)).all()
        finally:
            session.close()


class WorkspaceExpertEquipmentDao(
    BaseDao[WorkspaceExpertEquipmentEntity, Dict[str, Any], Dict[str, Any]]
):
    def from_request(self, request: Union[Dict[str, Any]]) -> WorkspaceExpertEquipmentEntity:
        data = dict(request)
        data.pop("id", None)
        data.pop("gmt_created", None)
        data.pop("gmt_modified", None)
        config = data.pop("config", None)
        entity = WorkspaceExpertEquipmentEntity(**data)
        entity.config_json = _dump_json(config)
        return entity

    def to_request(self, entity: WorkspaceExpertEquipmentEntity) -> Dict[str, Any]:
        return {
            "expert_id": entity.expert_id,
            "resource_type": entity.resource_type,
            "resource_ref": entity.resource_ref,
            "config": _load_json(entity.config_json),
            "is_active": entity.is_active,
        }

    def to_response(self, entity: WorkspaceExpertEquipmentEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "expert_id": entity.expert_id,
            "resource_type": entity.resource_type,
            "resource_ref": entity.resource_ref,
            "config": _load_json(entity.config_json),
            "is_active": bool(entity.is_active),
            "gmt_created": entity.gmt_created.isoformat() if entity.gmt_created else "",
            "gmt_modified": entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        }

    def upsert(
        self, expert_id: int, resource_type: str, resource_ref: str, **fields
    ) -> WorkspaceExpertEquipmentEntity:
        """幂等：按 uk(expert_id, resource_type, resource_ref) 存在则更新、否则创建。"""
        session = self.get_raw_session()
        try:
            row = (
                session.query(WorkspaceExpertEquipmentEntity)
                .filter(
                    WorkspaceExpertEquipmentEntity.expert_id == expert_id,
                    WorkspaceExpertEquipmentEntity.resource_type == resource_type,
                    WorkspaceExpertEquipmentEntity.resource_ref == resource_ref,
                )
                .first()
            )
            if row is None:
                row = WorkspaceExpertEquipmentEntity(
                    expert_id=expert_id,
                    resource_type=resource_type,
                    resource_ref=resource_ref,
                    **fields,
                )
                session.add(row)
            else:
                for k, v in fields.items():
                    setattr(row, k, v)
                row.gmt_modified = datetime.now()
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_by_expert(
        self, expert_id: int, active_only: bool = True
    ) -> List[WorkspaceExpertEquipmentEntity]:
        session = self.get_raw_session()
        try:
            query = session.query(WorkspaceExpertEquipmentEntity).filter(
                WorkspaceExpertEquipmentEntity.expert_id == expert_id
            )
            if active_only:
                query = query.filter(WorkspaceExpertEquipmentEntity.is_active.is_(True))
            return query.order_by(WorkspaceExpertEquipmentEntity.id).all()
        finally:
            session.close()

    def delete_by_expert(self, expert_id: int) -> int:
        session = self.get_raw_session()
        try:
            count = (
                session.query(WorkspaceExpertEquipmentEntity)
                .filter(WorkspaceExpertEquipmentEntity.expert_id == expert_id)
                .delete(synchronize_session=False)
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_by_resource_ref(
        self, resource_type: str, resource_ref: str
    ) -> int:
        """按资源类型+引用删除外挂行(知识空间删除时级联清理,避免悬空引用)。"""
        session = self.get_raw_session()
        try:
            count = (
                session.query(WorkspaceExpertEquipmentEntity)
                .filter(
                    WorkspaceExpertEquipmentEntity.resource_type == resource_type,
                    WorkspaceExpertEquipmentEntity.resource_ref == resource_ref,
                )
                .delete(synchronize_session=False)
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
