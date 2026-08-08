"""Workspace / WorkspaceMember / WorkspaceResource entities + DAOs."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    desc,
    func,
    or_,
)

from gyra.storage.metadata import BaseDao, Model
from gyra.util import PaginationResult

from ..api.schemas import (
    WorkspaceListFilter,
    WorkspaceMemberRequest,
    WorkspaceMemberResponse,
    WorkspaceRequest,
    WorkspaceResourceListRequest,
    WorkspaceResourceRequest,
    WorkspaceResourceResponse,
    WorkspaceResponse,
)
from ..config import SERVER_APP_TABLE_NAME

WORKSPACE_TABLE_NAME = SERVER_APP_TABLE_NAME
WORKSPACE_MEMBER_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_member"
WORKSPACE_RESOURCE_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_resource"
WORKSPACE_CONV_LINK_TABLE_NAME = f"{SERVER_APP_TABLE_NAME}_conv_link"


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


class WorkspaceEntity(Model):
    __tablename__ = WORKSPACE_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_code = Column(String(64), nullable=False, unique=True, comment="unique workspace code")
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(32), nullable=False, default="scenario", comment="scenario / team")
    scenario_type = Column(String(64), nullable=True, comment="sre / data_ops / ...")
    # 场景空间模式:task_execution/decision_discussion/knowledge_curation/
    # continuous_monitoring。NULL 视为默认 task_execution(兼容历史数据)。
    scene_mode = Column(
        String(32),
        nullable=True,
        default="task_execution",
        comment="task_execution/decision_discussion/knowledge_curation/continuous_monitoring",
    )
    owner_user_id = Column(Integer, nullable=False)
    default_agent_app_code = Column(String(255), nullable=True)
    settings_json = Column(Text, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    # 软删除/释放标记:释放后空间从列表隐藏,保留底层记录便于恢复。
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WorkspaceMemberEntity(Model):
    __tablename__ = WORKSPACE_MEMBER_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(32), nullable=False, default="contributor")
    # 用户级主空间标记(每个用户在最多一个空间为 True)。区别于历史
    # workspace.settings.is_home(空间级,跨用户共享),此处按用户隔离,
    # 使"我的默认空间"真正属于个人。
    is_home = Column(Boolean, nullable=False, default=False, index=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uk_workspace_member"),
    )


class WorkspaceResourceEntity(Model):
    __tablename__ = WORKSPACE_RESOURCE_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    type = Column(String(32), nullable=False, comment="data_source/knowledge_space/environment/mcp/skill/llm_model/ecp")
    name = Column(String(128), nullable=False)
    category = Column(String(16), nullable=False, default="scenario_bound")
    physical_ref = Column(String(255), nullable=True)
    config_json = Column(Text, nullable=True)
    access_mode = Column(String(16), nullable=False, default="read")
    is_active = Column(Boolean, nullable=False, default=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("workspace_id", "type", "name", name="uk_workspace_resource"),
    )


class WorkspaceConversationLinkEntity(Model):
    """Links chat_history.conv_uid to a workspace (and optionally a Task).
    Avoids modifying the canonical chat_history table.
    """

    __tablename__ = WORKSPACE_CONV_LINK_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    conv_uid = Column(String(255), nullable=False, unique=True, index=True)
    task_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    is_current = Column(Boolean, nullable=False, default=False, index=True)
    title = Column(String(255), nullable=True)

    gmt_created = Column(DateTime, name="gmt_create", default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WorkspaceConversationLinkDao(
    BaseDao[
        WorkspaceConversationLinkEntity,
        Dict[str, Any],
        Dict[str, Any],
    ]
):
    """DAO for WorkspaceConversationLink — uses raw session for simplicity."""

    def from_request(self, request):
        raise NotImplementedError

    def to_request(self, entity):
        raise NotImplementedError

    def to_response(self, entity):
        return {
            "id": entity.id,
            "workspace_id": entity.workspace_id,
            "conv_uid": entity.conv_uid,
            "task_id": entity.task_id,
            "user_id": entity.user_id,
            "title": entity.title,
            "is_current": entity.is_current,
            "gmt_created": entity.gmt_created.isoformat() if entity.gmt_created else "",
            "gmt_modified": entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        }

    def link(
        self,
        workspace_id: int,
        conv_uid: str,
        task_id: Optional[int] = None,
        user_id: Optional[int] = None,
        title: Optional[str] = None,
        set_current: bool = False,
    ) -> WorkspaceConversationLinkEntity:
        session = self.get_raw_session()
        try:
            existing = (
                session.query(WorkspaceConversationLinkEntity)
                .filter(WorkspaceConversationLinkEntity.conv_uid == conv_uid)
                .first()
            )
            if existing:
                existing.workspace_id = workspace_id
                if task_id is not None:
                    existing.task_id = task_id
                if user_id is not None:
                    existing.user_id = user_id
                if title is not None:
                    existing.title = title
                session.commit()
                if set_current:
                    self._set_current_internal(workspace_id, user_id, conv_uid)
                # commit 后属性已 expire,session 关闭前 refresh,
                # 否则调用方 to_response 读属性会抛 DetachedInstanceError
                session.refresh(existing)
                return existing
            row = WorkspaceConversationLinkEntity(
                workspace_id=workspace_id,
                conv_uid=conv_uid,
                task_id=task_id,
                user_id=user_id,
                title=title,
                is_current=False,
            )
            session.add(row)
            session.commit()
            if set_current:
                self._set_current_internal(workspace_id, user_id, conv_uid)
            elif user_id is not None and self.get_current(workspace_id, user_id) is None:
                self._set_current_internal(workspace_id, user_id, conv_uid)
            # 同 existing 分支:关闭前 refresh,避免 DetachedInstanceError
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _user_scope_filter(self, user_id: Optional[int]):
        """用户可见域,与 get_current 对称:无主 link(user_id IS NULL)对所有用户可见。

        set_current 与 get_current 必须共用同一域,否则会出现"设了 current 却查不到"
        的不对称:set 用 user_id == X 严格匹配会漏掉无主 link(NULL != X),而 get 又
        把无主 link 视为可见 -> 永远查不到 is_current=True -> "Failed to set current"。
        """
        if user_id is None:
            return WorkspaceConversationLinkEntity.user_id.is_(None)
        return or_(
            WorkspaceConversationLinkEntity.user_id == user_id,
            WorkspaceConversationLinkEntity.user_id.is_(None),
        )

    def _set_current_internal(
        self,
        workspace_id: int,
        user_id: Optional[int],
        conv_uid: str,
    ) -> None:
        scope = self._user_scope_filter(user_id)
        session = self.get_raw_session()
        try:
            session.query(WorkspaceConversationLinkEntity).filter(
                WorkspaceConversationLinkEntity.workspace_id == workspace_id,
                scope,
                WorkspaceConversationLinkEntity.conv_uid != conv_uid,
            ).update(
                {WorkspaceConversationLinkEntity.is_current: False},
                synchronize_session=False,
            )
            session.query(WorkspaceConversationLinkEntity).filter(
                WorkspaceConversationLinkEntity.workspace_id == workspace_id,
                scope,
                WorkspaceConversationLinkEntity.conv_uid == conv_uid,
            ).update(
                {WorkspaceConversationLinkEntity.is_current: True},
                synchronize_session=False,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_current(
        self,
        workspace_id: int,
        user_id: Optional[int],
        conv_uid: str,
    ) -> None:
        """Public wrapper to set the current conversation for a workspace/user."""
        self._set_current_internal(workspace_id, user_id, conv_uid)

    def get_current(
        self, workspace_id: int, user_id: Optional[int]
    ) -> Optional[WorkspaceConversationLinkEntity]:
        session = self.get_raw_session()
        try:
            q = session.query(WorkspaceConversationLinkEntity).filter(
                WorkspaceConversationLinkEntity.workspace_id == workspace_id,
                WorkspaceConversationLinkEntity.is_current.is_(True),
                self._user_scope_filter(user_id),
            )
            return q.order_by(
                WorkspaceConversationLinkEntity.gmt_modified.desc()
            ).first()
        finally:
            session.close()

    def rename(
        self, conv_uid: str, title: str
    ) -> Optional[WorkspaceConversationLinkEntity]:
        session = self.get_raw_session()
        try:
            entity = (
                session.query(WorkspaceConversationLinkEntity)
                .filter(WorkspaceConversationLinkEntity.conv_uid == conv_uid)
                .first()
            )
            if entity is None:
                return None
            entity.title = title
            session.commit()
            # commit 后属性过期,关闭前 refresh 防 DetachedInstanceError
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_conv(self, conv_uid: str) -> Optional[WorkspaceConversationLinkEntity]:
        session = self.get_raw_session()
        try:
            return (
                session.query(WorkspaceConversationLinkEntity)
                .filter(WorkspaceConversationLinkEntity.conv_uid == conv_uid)
                .first()
            )
        finally:
            session.close()

    def list_by_workspace(
        self, workspace_id: int, user_id: Optional[int] = None, limit: int = 100
    ) -> List[WorkspaceConversationLinkEntity]:
        session = self.get_raw_session()
        try:
            query = session.query(WorkspaceConversationLinkEntity).filter(
                WorkspaceConversationLinkEntity.workspace_id == workspace_id
            )
            if user_id is not None:
                # 与 get_current 一致:无主 link(user_id=None)对所有用户可见
                from sqlalchemy import or_

                query = query.filter(
                    or_(
                        WorkspaceConversationLinkEntity.user_id == user_id,
                        WorkspaceConversationLinkEntity.user_id.is_(None),
                    )
                )
            return (
                query.order_by(WorkspaceConversationLinkEntity.gmt_modified.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()


# ----------------------------- DAOs -----------------------------
class WorkspaceDao(BaseDao[WorkspaceEntity, WorkspaceRequest, WorkspaceResponse]):
    def from_request(self, request: Union[WorkspaceRequest, Dict[str, Any]]) -> WorkspaceEntity:
        data = request.dict() if isinstance(request, WorkspaceRequest) else dict(request)
        data.pop("gmt_created", None)
        data.pop("gmt_modified", None)
        data.pop("member_count", None)
        settings = data.pop("settings", None) or {}
        entity = WorkspaceEntity(**data)
        entity.settings_json = _dump_json(settings)
        if not entity.workspace_code:
            import uuid as _uuid
            entity.workspace_code = f"ws_{_uuid.uuid4().hex[:12]}"
        return entity

    def to_request(self, entity: WorkspaceEntity) -> WorkspaceRequest:
        return WorkspaceRequest(
            workspace_code=entity.workspace_code,
            name=entity.name,
            description=entity.description,
            type=entity.type,
            scenario_type=entity.scenario_type,
            scene_mode=entity.scene_mode,
            owner_user_id=entity.owner_user_id,
            default_agent_app_code=entity.default_agent_app_code,
            settings=_load_json(entity.settings_json),
            is_archived=entity.is_archived,
            is_deleted=entity.is_deleted,
        )

    def to_response(self, entity: WorkspaceEntity, member_count: int = 0) -> WorkspaceResponse:
        return WorkspaceResponse(
            id=entity.id,
            workspace_code=entity.workspace_code,
            name=entity.name,
            description=entity.description,
            type=entity.type,
            scenario_type=entity.scenario_type,
            scene_mode=entity.scene_mode or "task_execution",
            owner_user_id=entity.owner_user_id,
            default_agent_app_code=entity.default_agent_app_code,
            settings=_load_json(entity.settings_json),
            is_archived=entity.is_archived,
            is_deleted=entity.is_deleted,
            member_count=member_count,
            gmt_created=entity.gmt_created.isoformat() if entity.gmt_created else "",
            gmt_modified=entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        )

    def filter_list(
        self, filter_request: WorkspaceListFilter
    ) -> List[WorkspaceResponse]:
        """List workspaces. If user_id is provided, only workspaces where the user is a member."""
        session = self.get_raw_session()
        try:
            query = session.query(WorkspaceEntity)
            # 已释放(软删除)的空间一律不可见。
            query = query.filter(WorkspaceEntity.is_deleted == False)
            if not filter_request.include_archived:
                query = query.filter(WorkspaceEntity.is_archived == False)
            if filter_request.scenario_type:
                query = query.filter(WorkspaceEntity.scenario_type == filter_request.scenario_type)
            if filter_request.user_id is not None:
                member_subq = (
                    session.query(WorkspaceMemberEntity.workspace_id)
                    .filter(WorkspaceMemberEntity.user_id == filter_request.user_id)
                    .subquery()
                )
                query = query.filter(or_(
                    WorkspaceEntity.id.in_(member_subq),
                    WorkspaceEntity.owner_user_id == filter_request.user_id,
                ))
            entities = query.order_by(desc(WorkspaceEntity.gmt_modified)).all()
            return self._with_member_counts(session, entities)
        finally:
            session.close()

    def _with_member_counts(
        self, session, entities: List[WorkspaceEntity]
    ) -> List[WorkspaceResponse]:
        """为列表聚合各空间成员数,避免对每个 workspace 触发 N+1 查询。"""
        workspace_ids = [e.id for e in entities]
        count_map: Dict[int, int] = {}
        if workspace_ids:
            subq = (
                session.query(
                    WorkspaceMemberEntity.workspace_id.label("wid"),
                    func.count(WorkspaceMemberEntity.id).label("cnt"),
                )
                .filter(WorkspaceMemberEntity.workspace_id.in_(workspace_ids))
                .group_by(WorkspaceMemberEntity.workspace_id)
                .subquery()
            )
            rows = session.query(subq.c.wid, subq.c.cnt).all()
            count_map = {wid: cnt for wid, cnt in rows}
        return [
            self.to_response(e, member_count=count_map.get(e.id, 0))
            for e in entities
        ]


class WorkspaceMemberDao(BaseDao[WorkspaceMemberEntity, WorkspaceMemberRequest, WorkspaceMemberResponse]):
    def from_request(self, request: Union[WorkspaceMemberRequest, Dict[str, Any]]) -> WorkspaceMemberEntity:
        data = request.dict() if isinstance(request, WorkspaceMemberRequest) else dict(request)
        data.pop("gmt_created", None)
        data.pop("gmt_modified", None)
        data.pop("user_name", None)
        return WorkspaceMemberEntity(**data)

    def to_request(self, entity: WorkspaceMemberEntity) -> WorkspaceMemberRequest:
        return WorkspaceMemberRequest(
            workspace_id=entity.workspace_id,
            user_id=entity.user_id,
            role=entity.role,
        )

    def to_response(self, entity: WorkspaceMemberEntity, user_name: Optional[str] = None) -> WorkspaceMemberResponse:
        return WorkspaceMemberResponse(
            id=entity.id,
            workspace_id=entity.workspace_id,
            user_id=entity.user_id,
            user_name=user_name,
            role=entity.role,
            gmt_created=entity.gmt_created.isoformat() if entity.gmt_created else "",
            gmt_modified=entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        )

    def list_by_workspace(self, workspace_id: int) -> List[WorkspaceMemberEntity]:
        session = self.get_raw_session()
        try:
            return (
                session.query(WorkspaceMemberEntity)
                .filter(WorkspaceMemberEntity.workspace_id == workspace_id)
                .all()
            )
        finally:
            session.close()

    def list_by_workspace_with_user_info(self, workspace_id: int) -> List[Tuple[WorkspaceMemberEntity, Optional[str]]]:
        """List members with user names by joining user table.

        Returns:
            List of (member_entity, user_name) tuples
        """
        from gyra_app.auth.user_service import UserEntity

        session = self.get_raw_session()
        try:
            results = (
                session.query(WorkspaceMemberEntity, UserEntity.name)
                .outerjoin(UserEntity, WorkspaceMemberEntity.user_id == UserEntity.id)
                .filter(WorkspaceMemberEntity.workspace_id == workspace_id)
                .all()
            )
            return results
        finally:
            session.close()

    def count_by_workspace(self, workspace_id: int) -> int:
        session = self.get_raw_session()
        try:
            return (
                session.query(WorkspaceMemberEntity)
                .filter(WorkspaceMemberEntity.workspace_id == workspace_id)
                .count()
            )
        finally:
            session.close()

    def get_role(self, workspace_id: int, user_id: int) -> Optional[str]:
        session = self.get_raw_session()
        try:
            row = (
                session.query(WorkspaceMemberEntity)
                .filter(
                    and_(
                        WorkspaceMemberEntity.workspace_id == workspace_id,
                        WorkspaceMemberEntity.user_id == user_id,
                    )
                )
                .first()
            )
            return row.role if row else None
        finally:
            session.close()

    # ---------------- 用户级主空间(home) ----------------
    def clear_home(self, user_id: int) -> None:
        """清除该用户在所有空间的主空间标记(最多一个为 True)。"""
        session = self.get_raw_session()
        try:
            session.query(WorkspaceMemberEntity).filter(
                WorkspaceMemberEntity.user_id == user_id,
                WorkspaceMemberEntity.is_home.is_(True),
            ).update(
                {WorkspaceMemberEntity.is_home: False},
                synchronize_session=False,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_home(self, workspace_id: int, user_id: int) -> bool:
        """把某空间设为该用户的主空间;返回是否成功(False=用户非该空间成员)。"""
        self.clear_home(user_id)
        session = self.get_raw_session()
        try:
            row = (
                session.query(WorkspaceMemberEntity)
                .filter(
                    and_(
                        WorkspaceMemberEntity.workspace_id == workspace_id,
                        WorkspaceMemberEntity.user_id == user_id,
                    )
                )
                .first()
            )
            if row is None:
                return False
            row.is_home = True
            row.gmt_modified = datetime.now()
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_home_workspace_id(self, user_id: int) -> Optional[int]:
        """返回该用户主空间的 workspace_id;未设置返回 None。"""
        session = self.get_raw_session()
        try:
            row = (
                session.query(WorkspaceMemberEntity)
                .filter(
                    WorkspaceMemberEntity.user_id == user_id,
                    WorkspaceMemberEntity.is_home.is_(True),
                )
                .first()
            )
            return row.workspace_id if row else None
        finally:
            session.close()


class WorkspaceResourceDao(BaseDao[WorkspaceResourceEntity, WorkspaceResourceRequest, WorkspaceResourceResponse]):
    def from_request(self, request: Union[WorkspaceResourceRequest, Dict[str, Any]]) -> WorkspaceResourceEntity:
        data = request.dict() if isinstance(request, WorkspaceResourceRequest) else dict(request)
        data.pop("gmt_created", None)
        data.pop("gmt_modified", None)
        config = data.pop("config", None) or {}
        entity = WorkspaceResourceEntity(**data)
        entity.config_json = _dump_json(config)
        return entity

    def to_request(self, entity: WorkspaceResourceEntity) -> WorkspaceResourceRequest:
        return WorkspaceResourceRequest(
            workspace_id=entity.workspace_id,
            type=entity.type,
            name=entity.name,
            category=entity.category,
            physical_ref=entity.physical_ref,
            config=_load_json(entity.config_json),
            access_mode=entity.access_mode,
            is_active=entity.is_active,
        )

    def to_response(self, entity: WorkspaceResourceEntity) -> WorkspaceResourceResponse:
        return WorkspaceResourceResponse(
            id=entity.id,
            workspace_id=entity.workspace_id,
            type=entity.type,
            name=entity.name,
            category=entity.category,
            physical_ref=entity.physical_ref,
            config=_load_json(entity.config_json),
            access_mode=entity.access_mode,
            is_active=entity.is_active,
            gmt_created=entity.gmt_created.isoformat() if entity.gmt_created else "",
            gmt_modified=entity.gmt_modified.isoformat() if entity.gmt_modified else "",
        )

    def list_by_workspace(
        self, workspace_id: int, type_filter: Optional[str] = None
    ) -> List[WorkspaceResourceEntity]:
        session = self.get_raw_session()
        try:
            query = session.query(WorkspaceResourceEntity).filter(
                WorkspaceResourceEntity.workspace_id == workspace_id
            )
            if type_filter:
                query = query.filter(WorkspaceResourceEntity.type == type_filter)
            return query.order_by(desc(WorkspaceResourceEntity.gmt_modified)).all()
        finally:
            session.close()
