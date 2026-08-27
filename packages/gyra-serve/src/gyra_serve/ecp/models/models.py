"""ECP database entities and DAOs.

Five tables (docs/ECP.md 3.1 + v1.2 edge table):

- gyra_serve_ecp_semantic_object  : hard semantic objects, versioned, with
  status state machine (proposed/confirmed/rejected/deprecated/superseded)
- gyra_serve_ecp_resolution_cache : normalized question -> frozen tool-call
  params (the cache is an asset too)
- gyra_serve_ecp_semantic_edge    : materialized projection of edges from
  object payloads / soft-layer refs; never edited by hand
- gyra_serve_ecp_confirmer        : confirmer allow-list per workspace
- gyra_serve_ecp_op_log           : append-only operation log (lint feedstock)
"""

import logging
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    desc,
    func,
)

from gyra.storage.metadata import BaseDao, Model

from ..api.schemas import (
    AssetRefVO,
    CatalogEntryVO,
    ConfirmerVO,
    MissLearnVO,
    OpLogVO,
    SemanticObjectListVO,
    SemanticObjectVO,
    WorkspaceConfigVO,
)
from ..config import (
    DEFAULT_WORKSPACE_ID,
    STATUS_CONFIRMED,
    STATUS_PROPOSED,
    STATUS_SUPERSEDED,
    TABLE_ASSET_REF,
    TABLE_CONFIRMER,
    TABLE_MISS_LEARN,
    TABLE_OP_LOG,
    TABLE_RESOLUTION_CACHE,
    TABLE_SEMANTIC_EDGE,
    TABLE_SEMANTIC_OBJECT,
    TABLE_WORKSPACE_CONFIG,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- entities
class EcpSemanticObjectEntity(Model):
    """One version of a semantic object. Versions are immutable."""

    __tablename__ = TABLE_SEMANTIC_OBJECT

    id = Column(String(128), primary_key=True)
    version = Column(Integer, primary_key=True)
    workspace_id = Column(String(128), nullable=False, default=DEFAULT_WORKSPACE_ID)
    obj_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default=STATUS_PROPOSED)
    name = Column(String(256), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)
    created_by = Column(String(64), nullable=False, default="llm")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    confirmed_by = Column(String(64), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    source = Column(String(256), nullable=True)
    supersedes = Column(Integer, nullable=True)
    gmt_create = Column(DateTime, default=datetime.now, nullable=False)
    gmt_modify = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    __table_args__ = (
        Index("idx_ecp_obj_ws_status", "workspace_id", "status"),
        Index("idx_ecp_obj_type_status", "obj_type", "status"),
    )


class EcpResolutionCacheEntity(Model):
    """Normalized question -> frozen execute_metric_query call params."""

    __tablename__ = TABLE_RESOLUTION_CACHE

    question_norm = Column(String(512), primary_key=True)
    workspace_id = Column(String(128), primary_key=True, default=DEFAULT_WORKSPACE_ID)
    resolution = Column(JSON, nullable=False, default=dict)
    validated_by = Column(String(128), nullable=True)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    gmt_modify = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


class EcpSemanticEdgeEntity(Model):
    """Materialized edge projection; recomputed from payloads, never hand-edited."""

    __tablename__ = TABLE_SEMANTIC_EDGE

    src = Column(String(128), primary_key=True)
    edge_type = Column(String(64), primary_key=True)
    dst = Column(String(128), primary_key=True)
    workspace_id = Column(String(128), primary_key=True, default=DEFAULT_WORKSPACE_ID)
    src_version = Column(Integer, nullable=True)
    status = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (Index("idx_ecp_edge_dst", "workspace_id", "dst"),)


class EcpConfirmerEntity(Model):
    """Confirmer allow-list. Empty list for a workspace means open bootstrap."""

    __tablename__ = TABLE_CONFIRMER

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(128), nullable=False, default=DEFAULT_WORKSPACE_ID)
    user_id = Column(String(128), nullable=False)
    scope = Column(String(128), nullable=True)
    gmt_create = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", "scope", name="uk_ecp_confirmer"),
    )


class EcpOpLogEntity(Model):
    """Append-only operation log."""

    __tablename__ = TABLE_OP_LOG

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(128), nullable=False, default=DEFAULT_WORKSPACE_ID)
    ts = Column(DateTime, default=datetime.now, nullable=False)
    op = Column(String(64), nullable=False)
    detail = Column(JSON, nullable=True)

    __table_args__ = (Index("idx_ecp_oplog_ws_ts", "workspace_id", "ts"),)


class EcpAssetRefEntity(Model):
    """Registry of original-asset references (ECP owns references, not assets).

    kind=db        -> ref_id = datasource_id (holder: datasource module)
    kind=document  -> ref_id = '{space_slug}:{verbat_id}' (holder: knowledge)
    kind=space     -> ref_id = space_slug (holder: knowledge)
    kind=api       -> ref_id = api_resource_id (holder: ecp itself, P3)
    """

    __tablename__ = TABLE_ASSET_REF

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(128), nullable=False, default=DEFAULT_WORKSPACE_ID)
    kind = Column(String(32), nullable=False)
    ref_id = Column(String(256), nullable=False)
    ref_meta = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    last_checked_at = Column(DateTime, nullable=True)
    gmt_create = Column(DateTime, default=datetime.now, nullable=False)
    gmt_modify = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "kind", "ref_id", name="uk_ecp_asset_ref"),
    )


class EcpMissLearnEntity(Model):
    """Record that a miss cluster has been learned (a proposal was generated).

    The ``pattern`` is the normalized cluster key from ``cluster_fallbacks``; the
    unique identity is ``(workspace_id, kind, datasource_id, pattern)``. Once a
    cluster is recorded here, ``get_miss_report``/``miss_report`` exclude it so the
    daily miss-learning cron does not re-surface already-covered concepts
    (flywheel's learned marker). Dedup is enforced in the DAO (datasource_id is
    NULL-able for doc clusters, so a DB unique index would not coalesce NULLs).
    """

    __tablename__ = TABLE_MISS_LEARN

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(128), nullable=False, default=DEFAULT_WORKSPACE_ID)
    kind = Column(String(32), nullable=False)
    datasource_id = Column(Integer, nullable=True)
    pattern = Column(String(512), nullable=False)
    example = Column(String(1024), nullable=True)
    proposal_ids = Column(JSON, nullable=True)
    trigger = Column(String(32), nullable=False, default="agent")
    learned_at = Column(DateTime, default=datetime.now, nullable=False)
    gmt_create = Column(DateTime, default=datetime.now, nullable=False)
    gmt_modify = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    __table_args__ = (Index("idx_ecp_miss_learn_ws", "workspace_id"),)


class EcpWorkspaceConfigEntity(Model):
    """Per-workspace ECP settings.

    The proposal agent is a STANDARD agent from the agent store with ECP
    tools bound — ECP deliberately does not duplicate the agent platform's
    model/prompt configuration. Execution = send the agent a task message;
    output structure is enforced by the propose_semantic tool schema.
    """

    __tablename__ = TABLE_WORKSPACE_CONFIG

    workspace_id = Column(String(128), primary_key=True, default=DEFAULT_WORKSPACE_ID)
    proposal_agent_id = Column(String(256), nullable=True)
    gmt_create = Column(DateTime, default=datetime.now, nullable=False)
    gmt_modify = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


# ------------------------------------------------------------------------ helpers
def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse an ISO datetime string (or pass a datetime through) for import."""
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def to_object_vo(e: EcpSemanticObjectEntity) -> SemanticObjectVO:
    return SemanticObjectVO(
        id=e.id,
        version=e.version,
        workspace_id=e.workspace_id,
        obj_type=e.obj_type,
        status=e.status,
        name=e.name,
        payload=e.payload or {},
        confidence=e.confidence,
        evidence=e.evidence,
        created_by=e.created_by,
        created_at=_iso(e.created_at),
        confirmed_by=e.confirmed_by,
        confirmed_at=_iso(e.confirmed_at),
        source=e.source,
        supersedes=e.supersedes,
    )


# ---------------------------------------------------------------------------- DAOs
class SemanticObjectDao(BaseDao[EcpSemanticObjectEntity, Any, Any]):
    """DAO for semantic objects, enforcing version immutability."""

    # ------------------------------------------------------------------ write
    def create_proposal(
        self,
        object_id: str,
        obj_type: str,
        payload: Dict[str, Any],
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        confidence: Optional[float] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        created_by: str = "llm",
        source: Optional[str] = None,
    ) -> SemanticObjectVO:
        """Create a new proposed version. LLM writes are always proposed.

        入库前经 contracts.normalize_payload 机械归一(扁平形态→契约形态),
        所有写入点(service/tools/executor auto-propose)在此统一自愈。
        """
        from ..service.contracts import normalize_payload

        payload = normalize_payload(obj_type, payload)
        with self.session() as session:
            # 硬去重:该对象已有 confirmed 版本且其 payload(归一后)与新提案完全相同
            # -> 跳过建 proposed,直接返回已确认 VO。避免对已确认的相同概念因重新生产/
            # miss 学习反复再确认(新 proposed 版本会盖住旧 confirmed 的统计/目录)。
            existing_confirmed = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                    EcpSemanticObjectEntity.status == STATUS_CONFIRMED,
                )
                .order_by(desc(EcpSemanticObjectEntity.version))
                .first()
            )
            if existing_confirmed and (existing_confirmed.payload or {}) == payload:
                return to_object_vo(existing_confirmed)
            max_ver = (
                session.query(func.max(EcpSemanticObjectEntity.version))
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .scalar()
            )
            entity = EcpSemanticObjectEntity(
                id=object_id,
                version=(max_ver or 0) + 1,
                workspace_id=workspace_id,
                obj_type=obj_type,
                status=STATUS_PROPOSED,
                name=payload.get("name"),
                payload=payload,
                confidence=confidence,
                evidence=evidence,
                created_by=created_by,
                source=source,
            )
            session.add(entity)
            session.flush()
            session.refresh(entity)
            return to_object_vo(entity)

    def create_confirmed_version(
        self,
        object_id: str,
        obj_type: str,
        payload: Dict[str, Any],
        workspace_id: str,
        user_id: str,
        supersedes: Optional[int] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        source: Optional[str] = None,
    ) -> SemanticObjectVO:
        """Create an already-confirmed new version (edit-then-confirm path).

        The previously confirmed version of the same id is superseded.
        """
        with self.session() as session:
            self._supersede_confirmed(session, object_id, workspace_id)
            max_ver = (
                session.query(func.max(EcpSemanticObjectEntity.version))
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .scalar()
            )
            entity = EcpSemanticObjectEntity(
                id=object_id,
                version=(max_ver or 0) + 1,
                workspace_id=workspace_id,
                obj_type=obj_type,
                status=STATUS_CONFIRMED,
                name=payload.get("name"),
                payload=payload,
                confidence=1.0,
                evidence=evidence,
                created_by=user_id,
                confirmed_by=user_id,
                confirmed_at=datetime.now(),
                source=source,
                supersedes=supersedes,
            )
            session.add(entity)
            session.flush()
            session.refresh(entity)
            return to_object_vo(entity)

    @staticmethod
    def _supersede_confirmed(session, object_id: str, workspace_id: str) -> List[int]:
        """Mark all confirmed versions of an object as superseded. Returns versions."""
        rows = (
            session.query(EcpSemanticObjectEntity)
            .filter(
                EcpSemanticObjectEntity.id == object_id,
                EcpSemanticObjectEntity.workspace_id == workspace_id,
                EcpSemanticObjectEntity.status == STATUS_CONFIRMED,
            )
            .all()
        )
        superseded = []
        for row in rows:
            row.status = STATUS_SUPERSEDED
            superseded.append(row.version)
        return superseded

    def confirm_version(
        self, object_id: str, version: int, workspace_id: str, user_id: str
    ) -> Optional[SemanticObjectVO]:
        """Confirm a proposed version; other confirmed versions are superseded."""
        with self.session() as session:
            entity = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.version == version,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if not entity or entity.status != STATUS_PROPOSED:
                return None
            superseded = self._supersede_confirmed(session, object_id, workspace_id)
            entity.status = STATUS_CONFIRMED
            entity.confidence = 1.0
            entity.confirmed_by = user_id
            entity.confirmed_at = datetime.now()
            if superseded:
                entity.supersedes = max(superseded)
            session.flush()
            session.refresh(entity)
            return to_object_vo(entity)

    def update_status(
        self, object_id: str, version: int, workspace_id: str, status: str
    ) -> Optional[SemanticObjectVO]:
        with self.session() as session:
            entity = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.version == version,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if not entity:
                return None
            entity.status = status
            session.flush()
            session.refresh(entity)
            return to_object_vo(entity)

    # ------------------------------------------------------------------ reads
    def get_version(
        self, object_id: str, version: int, workspace_id: str
    ) -> Optional[SemanticObjectVO]:
        with self.session(commit=False) as session:
            entity = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.version == version,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .first()
            )
            return to_object_vo(entity) if entity else None

    def get_confirmed(
        self, object_id: str, workspace_id: str
    ) -> Optional[SemanticObjectVO]:
        with self.session(commit=False) as session:
            entity = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                    EcpSemanticObjectEntity.status == STATUS_CONFIRMED,
                )
                .order_by(desc(EcpSemanticObjectEntity.version))
                .first()
            )
            return to_object_vo(entity) if entity else None

    def version_history(
        self, object_id: str, workspace_id: str
    ) -> List[SemanticObjectVO]:
        with self.session(commit=False) as session:
            rows = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .order_by(desc(EcpSemanticObjectEntity.version))
                .all()
            )
            return [to_object_vo(r) for r in rows]

    def _latest_version_subquery(self, session, workspace_id: str):
        return (
            session.query(
                EcpSemanticObjectEntity.id.label("id"),
                func.max(EcpSemanticObjectEntity.version).label("max_version"),
            )
            .filter(EcpSemanticObjectEntity.workspace_id == workspace_id)
            .group_by(EcpSemanticObjectEntity.id)
            .subquery()
        )

    def _latest_confirmed_version_subquery(self, session, workspace_id: str):
        """每个对象最新 confirmed 版本(即"存在 confirmed 版本的对象"集合)。

        与 _latest_version_subquery 区别:只在 status=confirmed 行里取 max(version)。
        用于 confirmed 列表/计数/目录:某对象有 confirmed v1 + proposed v2 时,仍按
        v1(confirmed)计入已确认(与执行用 get_confirmed 同口径),不被 v2 盖掉、不误显为"没确认"。
        """
        return (
            session.query(
                EcpSemanticObjectEntity.id.label("id"),
                func.max(EcpSemanticObjectEntity.version).label("max_version"),
            )
            .filter(
                EcpSemanticObjectEntity.workspace_id == workspace_id,
                EcpSemanticObjectEntity.status == STATUS_CONFIRMED,
            )
            .group_by(EcpSemanticObjectEntity.id)
            .subquery()
        )

    def list_latest(
        self,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        obj_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SemanticObjectListVO:
        """List the latest version of each object with filters."""
        with self.session(commit=False) as session:
            # confirmed 用"存在 confirmed 版本"口径(每对象最新 confirmed),与执行
            # (get_confirmed)一致;避免 confirmed v1 + proposed v2 时被 v2 盖掉误显为未确认。
            if status == STATUS_CONFIRMED:
                sub = self._latest_confirmed_version_subquery(session, workspace_id)
            else:
                sub = self._latest_version_subquery(session, workspace_id)
            query = session.query(EcpSemanticObjectEntity).join(
                sub,
                (EcpSemanticObjectEntity.id == sub.c.id)
                & (EcpSemanticObjectEntity.version == sub.c.max_version),
            )
            if obj_type:
                query = query.filter(EcpSemanticObjectEntity.obj_type == obj_type)
            if status:
                query = query.filter(EcpSemanticObjectEntity.status == status)
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(
                    (EcpSemanticObjectEntity.name.like(like))
                    | (EcpSemanticObjectEntity.id.like(like))
                )
            total = query.count()
            rows = (
                query.order_by(desc(EcpSemanticObjectEntity.gmt_modify))
                .offset(max(0, (page - 1)) * page_size)
                .limit(page_size)
                .all()
            )
        return SemanticObjectListVO(
            items=[to_object_vo(r) for r in rows],
            total_count=total,
            page=page,
            page_size=page_size,
        )

    def list_catalog(
        self, workspace_id: str = DEFAULT_WORKSPACE_ID, keyword: Optional[str] = None
    ) -> List[CatalogEntryVO]:
        """Confirmed latest versions as one-line catalog entries.

        Catalogs are small by design (a few hundred objects), so keyword
        filtering over name/id/aliases is done in Python for portability
        across SQLite/MySQL JSON semantics.
        """
        with self.session(commit=False) as session:
            sub = self._latest_confirmed_version_subquery(session, workspace_id)
            rows = (
                session.query(EcpSemanticObjectEntity)
                .join(
                    sub,
                    (EcpSemanticObjectEntity.id == sub.c.id)
                    & (EcpSemanticObjectEntity.version == sub.c.max_version),
                )
                .order_by(EcpSemanticObjectEntity.id)
                .all()
            )
        entries = []
        for r in rows:
            payload = r.payload or {}
            aliases = payload.get("aliases") or []
            if keyword:
                kw = keyword.lower()
                haystack = " ".join(
                    [r.id, r.name or "", *aliases, payload.get("description") or ""]
                ).lower()
                if kw not in haystack:
                    continue
            entries.append(
                CatalogEntryVO(
                    id=r.id,
                    obj_type=r.obj_type,
                    name=r.name,
                    aliases=aliases,
                    one_line=payload.get("description") or payload.get("one_line"),
                    grain=payload.get("grain"),
                )
            )
        return entries

    def list_all_versions(
        self, workspace_id: str = DEFAULT_WORKSPACE_ID
    ) -> List[SemanticObjectVO]:
        """All historic versions of every object of a workspace (export source).

        Unlike ``list_latest`` (one row per id), this returns the full version
        history so an export faithfully preserves the version chain and the
        ``supersedes`` links that make the asset layer reproducible.
        """
        with self.session(commit=False) as session:
            rows = (
                session.query(EcpSemanticObjectEntity)
                .filter(EcpSemanticObjectEntity.workspace_id == workspace_id)
                .order_by(EcpSemanticObjectEntity.id, EcpSemanticObjectEntity.version)
                .all()
            )
        return [to_object_vo(r) for r in rows]

    def import_object(
        self,
        object_id: str,
        version: int,
        obj_type: str,
        workspace_id: str,
        status: str = STATUS_PROPOSED,
        name: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        created_by: str = "import",
        created_at: Optional[Any] = None,
        confirmed_by: Optional[str] = None,
        confirmed_at: Optional[Any] = None,
        source: Optional[str] = None,
        supersedes: Optional[int] = None,
    ) -> Optional[SemanticObjectVO]:
        """Restore one semantic object row from an export (merge import).

        Merge semantics:
        - An existing ``(id, version, workspace_id)`` row is skipped (None),
          so re-importing a snapshot is idempotent.
        - Importing a ``confirmed`` row supersedes any existing confirmed
          version of the same id (follows write rule 3).
        - Row status / version / supersedes are taken verbatim from the source
          so the imported asset layer behaves exactly like the original.
        """
        with self.session() as session:
            exists = (
                session.query(EcpSemanticObjectEntity)
                .filter(
                    EcpSemanticObjectEntity.id == object_id,
                    EcpSemanticObjectEntity.version == version,
                    EcpSemanticObjectEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if exists:
                return None
            if status == STATUS_CONFIRMED:
                self._supersede_confirmed(session, object_id, workspace_id)
            entity = EcpSemanticObjectEntity(
                id=object_id,
                version=version,
                workspace_id=workspace_id,
                obj_type=obj_type,
                status=status,
                name=name,
                payload=payload or {},
                confidence=confidence,
                evidence=evidence,
                created_by=created_by,
                created_at=_parse_dt(created_at) or datetime.now(),
                confirmed_by=confirmed_by,
                confirmed_at=_parse_dt(confirmed_at),
                source=source,
                supersedes=supersedes,
            )
            session.add(entity)
            session.flush()
            session.refresh(entity)
            return to_object_vo(entity)


class ResolutionCacheDao(BaseDao[EcpResolutionCacheEntity, Any, Any]):
    """DAO for the resolution cache (normalized question -> tool-call params)."""

    def get(
        self, question_norm: str, workspace_id: str
    ) -> Optional[EcpResolutionCacheEntity]:
        with self.session(commit=False) as session:
            return (
                session.query(EcpResolutionCacheEntity)
                .filter(
                    EcpResolutionCacheEntity.question_norm == question_norm,
                    EcpResolutionCacheEntity.workspace_id == workspace_id,
                )
                .first()
            )

    def put(
        self,
        question_norm: str,
        workspace_id: str,
        resolution: Dict[str, Any],
        validated_by: Optional[str] = None,
    ) -> None:
        with self.session() as session:
            entity = (
                session.query(EcpResolutionCacheEntity)
                .filter(
                    EcpResolutionCacheEntity.question_norm == question_norm,
                    EcpResolutionCacheEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity:
                entity.resolution = resolution
                entity.validated_by = validated_by
            else:
                session.add(
                    EcpResolutionCacheEntity(
                        question_norm=question_norm,
                        workspace_id=workspace_id,
                        resolution=resolution,
                        validated_by=validated_by,
                    )
                )

    def record_hit(self, question_norm: str, workspace_id: str) -> None:
        with self.session() as session:
            entity = (
                session.query(EcpResolutionCacheEntity)
                .filter(
                    EcpResolutionCacheEntity.question_norm == question_norm,
                    EcpResolutionCacheEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if entity:
                entity.hit_count = (entity.hit_count or 0) + 1

    def invalidate_referencing(self, object_id: str, workspace_id: str) -> int:
        """Drop cache entries whose resolution references the given object id."""
        with self.session() as session:
            count = (
                session.query(EcpResolutionCacheEntity)
                .filter(
                    EcpResolutionCacheEntity.workspace_id == workspace_id,
                    EcpResolutionCacheEntity.resolution.cast(String).like(
                        f'%"{object_id}"%'
                    ),
                )
                .delete(synchronize_session=False)
            )
        return int(count)


class SemanticEdgeDao(BaseDao[EcpSemanticEdgeEntity, Any, Any]):
    """DAO for the materialized edge projection."""

    def replace_out_edges(
        self,
        src: str,
        workspace_id: str,
        src_version: Optional[int],
        edges: List[Dict[str, Any]],
    ) -> None:
        """Recompute all out-edges of a node (called on object write/version)."""
        with self.session() as session:
            session.query(EcpSemanticEdgeEntity).filter(
                EcpSemanticEdgeEntity.src == src,
                EcpSemanticEdgeEntity.workspace_id == workspace_id,
            ).delete(synchronize_session=False)
            for e in edges:
                session.add(
                    EcpSemanticEdgeEntity(
                        src=src,
                        edge_type=e["edge_type"],
                        dst=e["dst"],
                        workspace_id=workspace_id,
                        src_version=src_version,
                        status=e.get("status"),
                    )
                )

    def neighbors(
        self, node: str, workspace_id: str, edge_type: Optional[str] = None
    ) -> List[EcpSemanticEdgeEntity]:
        with self.session(commit=False) as session:
            query = session.query(EcpSemanticEdgeEntity).filter(
                EcpSemanticEdgeEntity.workspace_id == workspace_id,
                (EcpSemanticEdgeEntity.src == node)
                | (EcpSemanticEdgeEntity.dst == node),
            )
            if edge_type:
                query = query.filter(EcpSemanticEdgeEntity.edge_type == edge_type)
            return query.all()


class ConfirmerDao(BaseDao[EcpConfirmerEntity, Any, Any]):
    """DAO for the confirmer allow-list."""

    def list(self, workspace_id: str) -> List[ConfirmerVO]:
        with self.session(commit=False) as session:
            rows = (
                session.query(EcpConfirmerEntity)
                .filter(EcpConfirmerEntity.workspace_id == workspace_id)
                .order_by(EcpConfirmerEntity.id)
                .all()
            )
        return [
            ConfirmerVO(
                id=r.id, workspace_id=r.workspace_id, user_id=r.user_id, scope=r.scope
            )
            for r in rows
        ]

    def add(self, workspace_id: str, user_id: str, scope: Optional[str] = None) -> None:
        with self.session() as session:
            exists = (
                session.query(EcpConfirmerEntity)
                .filter(
                    EcpConfirmerEntity.workspace_id == workspace_id,
                    EcpConfirmerEntity.user_id == user_id,
                    EcpConfirmerEntity.scope == scope,
                )
                .first()
            )
            if not exists:
                session.add(
                    EcpConfirmerEntity(
                        workspace_id=workspace_id, user_id=user_id, scope=scope
                    )
                )

    def remove(self, confirmer_id: int) -> bool:
        with self.session() as session:
            count = (
                session.query(EcpConfirmerEntity)
                .filter(EcpConfirmerEntity.id == confirmer_id)
                .delete(synchronize_session=False)
            )
        return count > 0

    def remove_by_user(self, workspace_id: str, user_id: str) -> int:
        """按 user 移除确认人(成员移除时同步回收确认权限)。"""
        with self.session() as session:
            count = (
                session.query(EcpConfirmerEntity)
                .filter(
                    EcpConfirmerEntity.workspace_id == workspace_id,
                    EcpConfirmerEntity.user_id == user_id,
                )
                .delete(synchronize_session=False)
            )
        return count

    def is_confirmer(self, workspace_id: str, user_id: str) -> bool:
        """Bootstrap rule: an empty allow-list means anyone may confirm."""
        with self.session(commit=False) as session:
            rows = (
                session.query(EcpConfirmerEntity)
                .filter(EcpConfirmerEntity.workspace_id == workspace_id)
                .all()
            )
        if not rows:
            return True
        return any(r.user_id == user_id for r in rows)


class OpLogDao(BaseDao[EcpOpLogEntity, Any, Any]):
    """DAO for the append-only op log."""

    def append(
        self, op: str, workspace_id: str, detail: Optional[Dict[str, Any]] = None
    ) -> None:
        with self.session() as session:
            session.add(
                EcpOpLogEntity(workspace_id=workspace_id, op=op, detail=detail or {})
            )

    def list(
        self,
        workspace_id: str,
        op: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[OpLogVO]:
        with self.session(commit=False) as session:
            query = session.query(EcpOpLogEntity).filter(
                EcpOpLogEntity.workspace_id == workspace_id
            )
            if op:
                query = query.filter(EcpOpLogEntity.op == op)
            rows = (
                query.order_by(desc(EcpOpLogEntity.ts))
                .offset(max(0, (page - 1)) * page_size)
                .limit(page_size)
                .all()
            )
        return [
            OpLogVO(
                id=r.id,
                workspace_id=r.workspace_id,
                ts=_iso(r.ts),
                op=r.op,
                detail=r.detail,
            )
            for r in rows
        ]


class MissLearnDao(BaseDao[EcpMissLearnEntity, Any, Any]):
    """DAO for miss-cluster learned markers (append-idempotent)."""

    def mark_learned(
        self,
        workspace_id: str,
        kind: str,
        pattern: str,
        datasource_id: Optional[int] = None,
        example: Optional[str] = None,
        proposal_ids: Optional[List[str]] = None,
        trigger: str = "agent",
    ) -> MissLearnVO:
        """Idempotently record that a miss cluster was learned.

        Unique identity is ``(workspace_id, kind, datasource_id, pattern)``;
        on collision we refresh the existing row (update proposal_ids/example/
        learned_at/trigger) rather than insert a duplicate. ``pattern`` is the
        normalized cluster key so future fallback records of the same query
        still map to the same learned marker.
        """
        pattern = (pattern or "")[:512]
        example = (example or "")[:1024] if example else None
        with self.session() as session:
            entity = (
                session.query(EcpMissLearnEntity)
                .filter(
                    EcpMissLearnEntity.workspace_id == workspace_id,
                    EcpMissLearnEntity.kind == kind,
                    EcpMissLearnEntity.datasource_id == datasource_id,
                    EcpMissLearnEntity.pattern == pattern,
                )
                .first()
            )
            if entity:
                entity.learned_at = datetime.now()
                entity.trigger = trigger
                entity.example = example or entity.example
                if proposal_ids:
                    entity.proposal_ids = proposal_ids
                session.flush()
                session.refresh(entity)
            else:
                entity = EcpMissLearnEntity(
                    workspace_id=workspace_id,
                    kind=kind,
                    datasource_id=datasource_id,
                    pattern=pattern,
                    example=example,
                    proposal_ids=proposal_ids or [],
                    trigger=trigger,
                )
                session.add(entity)
                session.flush()
                session.refresh(entity)
            return _to_miss_learn_vo(entity)

    def list(
        self, workspace_id: str, kind: Optional[str] = None
    ) -> List[MissLearnVO]:
        with self.session(commit=False) as session:
            query = session.query(EcpMissLearnEntity).filter(
                EcpMissLearnEntity.workspace_id == workspace_id
            )
            if kind:
                query = query.filter(EcpMissLearnEntity.kind == kind)
            rows = query.order_by(desc(EcpMissLearnEntity.learned_at)).all()
        return [_to_miss_learn_vo(r) for r in rows]

    def learned_keys(self, workspace_id: str) -> set:
        """Return ``{(kind, datasource_id, pattern)}`` already learned.

        Used to filter clusters out of ``get_miss_report``/``miss_report`` so the
        daily cron stops re-proposing already-covered concepts.
        """
        with self.session(commit=False) as session:
            rows = (
                session.query(
                    EcpMissLearnEntity.kind,
                    EcpMissLearnEntity.datasource_id,
                    EcpMissLearnEntity.pattern,
                )
                .filter(EcpMissLearnEntity.workspace_id == workspace_id)
                .all()
            )
        return {(r.kind, r.datasource_id, r.pattern) for r in rows}

    def clear(
        self,
        workspace_id: str,
        kind: Optional[str] = None,
        pattern: Optional[str] = None,
        datasource_id: Optional[int] = None,
    ) -> int:
        """Remove learned markers so the clusters can be re-surfaced. Returns count.

        ``datasource_id`` 是聚类唯一键的一部分: None 精确匹配 doc 聚类
        (datasource_id IS NULL),避免误删同 pattern 其他数据源的标记。
        """
        with self.session() as session:
            query = session.query(EcpMissLearnEntity).filter(
                EcpMissLearnEntity.workspace_id == workspace_id
            )
            if kind:
                query = query.filter(EcpMissLearnEntity.kind == kind)
            if pattern:
                query = query.filter(EcpMissLearnEntity.pattern == pattern)
            query = query.filter(EcpMissLearnEntity.datasource_id == datasource_id)
            rows = query.all()
            for r in rows:
                session.delete(r)
            return len(rows)

    def get(
        self,
        workspace_id: str,
        kind: str,
        pattern: str,
        datasource_id: Optional[int] = None,
    ) -> Optional[MissLearnVO]:
        """Exact lookup of a learned marker by cluster key (detail views)."""
        with self.session(commit=False) as session:
            entity = (
                session.query(EcpMissLearnEntity)
                .filter(
                    EcpMissLearnEntity.workspace_id == workspace_id,
                    EcpMissLearnEntity.kind == kind,
                    EcpMissLearnEntity.pattern == pattern,
                    EcpMissLearnEntity.datasource_id == datasource_id,
                )
                .first()
            )
        return _to_miss_learn_vo(entity) if entity else None


class AssetRefDao(BaseDao[EcpAssetRefEntity, Any, Any]):
    """DAO for the original-asset reference registry."""

    def register(
        self,
        kind: str,
        ref_id: str,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        ref_meta: Optional[Dict[str, Any]] = None,
    ) -> AssetRefVO:
        """Idempotent registration."""
        with self.session() as session:
            entity = (
                session.query(EcpAssetRefEntity)
                .filter(
                    EcpAssetRefEntity.workspace_id == workspace_id,
                    EcpAssetRefEntity.kind == kind,
                    EcpAssetRefEntity.ref_id == ref_id,
                )
                .first()
            )
            if entity:
                if ref_meta:
                    entity.ref_meta = ref_meta
                session.flush()
                session.refresh(entity)
            else:
                entity = EcpAssetRefEntity(
                    workspace_id=workspace_id,
                    kind=kind,
                    ref_id=ref_id,
                    ref_meta=ref_meta or {},
                )
                session.add(entity)
                session.flush()
                session.refresh(entity)
            return _to_asset_ref_vo(entity)

    def list(
        self, workspace_id: str, kind: Optional[str] = None
    ) -> List[AssetRefVO]:
        with self.session(commit=False) as session:
            query = session.query(EcpAssetRefEntity).filter(
                EcpAssetRefEntity.workspace_id == workspace_id
            )
            if kind:
                query = query.filter(EcpAssetRefEntity.kind == kind)
            rows = query.order_by(EcpAssetRefEntity.id).all()
            return [_to_asset_ref_vo(r) for r in rows]

    def get_by_ref(
        self, kind: str, ref_id: str, workspace_id: str
    ) -> Optional[AssetRefVO]:
        """Look up an asset reference by (kind, ref_id) within a workspace."""
        with self.session(commit=False) as session:
            entity = (
                session.query(EcpAssetRefEntity)
                .filter(
                    EcpAssetRefEntity.workspace_id == workspace_id,
                    EcpAssetRefEntity.kind == kind,
                    EcpAssetRefEntity.ref_id == ref_id,
                )
                .first()
            )
            return _to_asset_ref_vo(entity) if entity else None

    def touch_checked(self, ref_pk: int) -> None:
        with self.session() as session:
            entity = (
                session.query(EcpAssetRefEntity)
                .filter(EcpAssetRefEntity.id == ref_pk)
                .first()
            )
            if entity:
                entity.last_checked_at = datetime.now()

    def delete(self, ref_pk: int) -> bool:
        """Delete an asset reference by its primary key.

        ECP owns only the reference, so deletion here does NOT touch the
        original asset (DB / space / document) — it just unregisters it
        from the workspace. Returns True if a row was removed.
        """
        with self.session() as session:
            count = (
                session.query(EcpAssetRefEntity)
                .filter(EcpAssetRefEntity.id == ref_pk)
                .delete(synchronize_session=False)
            )
        return count > 0

    def delete_in_workspace(
        self, ref_pk: int, workspace_id: str
    ) -> Optional[EcpAssetRefEntity]:
        """Delete an asset reference scoped to a workspace.

        Returns the removed entity (kind + ref_id for op-log) if a row was
        removed, None otherwise. Scoping by workspace prevents one workspace
        from dropping another workspace's ref by guessing its primary key.
        """
        with self.session() as session:
            entity = (
                session.query(EcpAssetRefEntity)
                .filter(
                    EcpAssetRefEntity.id == ref_pk,
                    EcpAssetRefEntity.workspace_id == workspace_id,
                )
                .first()
            )
            if not entity:
                return None
            kind, ref_id = entity.kind, entity.ref_id
            session.delete(entity)
            return SimpleNamespace(kind=kind, ref_id=ref_id)

    def delete_by_ref(
        self,
        kind: str,
        ref_id: str,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> int:
        """Delete all asset references matching (workspace_id, kind, ref_id).

        Used by the cascade hooks when an original asset (DB / space) is
        deleted in its owning module — ECP must drop the dangling reference
        so it doesn't keep showing up in the asset list. Returns the number
        of rows removed.
        """
        with self.session() as session:
            count = (
                session.query(EcpAssetRefEntity)
                .filter(
                    EcpAssetRefEntity.workspace_id == workspace_id,
                    EcpAssetRefEntity.kind == kind,
                    EcpAssetRefEntity.ref_id == ref_id,
                )
                .delete(synchronize_session=False)
            )
        return int(count)

    def delete_by_ref_all_workspaces(self, kind: str, ref_id: str) -> int:
        """Delete all asset references matching (kind, ref_id) across ALL workspaces.

        Used by the cascade hooks when an original asset (DB / space) is
        deleted in its owning module — the owning module doesn't know which
        ECP workspaces referenced it, so we sweep all of them to avoid
        dangling refs. Returns the number of rows removed.
        """
        with self.session() as session:
            count = (
                session.query(EcpAssetRefEntity)
                .filter(
                    EcpAssetRefEntity.kind == kind,
                    EcpAssetRefEntity.ref_id == ref_id,
                )
                .delete(synchronize_session=False)
            )
        return int(count)


def _to_asset_ref_vo(e: EcpAssetRefEntity) -> AssetRefVO:
    return AssetRefVO(
        id=e.id,
        workspace_id=e.workspace_id,
        kind=e.kind,
        ref_id=e.ref_id,
        ref_meta=e.ref_meta or {},
        status=e.status,
        last_checked_at=_iso(e.last_checked_at),
    )


def _to_miss_learn_vo(e: EcpMissLearnEntity) -> MissLearnVO:
    return MissLearnVO(
        id=e.id,
        workspace_id=e.workspace_id,
        kind=e.kind,
        datasource_id=e.datasource_id,
        pattern=e.pattern,
        example=e.example,
        proposal_ids=e.proposal_ids or [],
        trigger=e.trigger,
        learned_at=_iso(e.learned_at),
    )


class WorkspaceConfigDao(BaseDao[EcpWorkspaceConfigEntity, Any, Any]):
    """DAO for per-workspace ECP settings."""

    def get(self, workspace_id: str) -> WorkspaceConfigVO:
        with self.session(commit=False) as session:
            entity = (
                session.query(EcpWorkspaceConfigEntity)
                .filter(EcpWorkspaceConfigEntity.workspace_id == workspace_id)
                .first()
            )
            if entity:
                return WorkspaceConfigVO(
                    workspace_id=entity.workspace_id,
                    proposal_agent_id=entity.proposal_agent_id,
                )
        return WorkspaceConfigVO(workspace_id=workspace_id)

    def upsert(
        self,
        workspace_id: str,
        proposal_agent_id: Optional[str] = None,
    ) -> WorkspaceConfigVO:
        with self.session() as session:
            entity = (
                session.query(EcpWorkspaceConfigEntity)
                .filter(EcpWorkspaceConfigEntity.workspace_id == workspace_id)
                .first()
            )
            if not entity:
                entity = EcpWorkspaceConfigEntity(workspace_id=workspace_id)
                session.add(entity)
            entity.proposal_agent_id = proposal_agent_id or None
            session.flush()
            session.refresh(entity)
            return WorkspaceConfigVO(
                workspace_id=entity.workspace_id,
                proposal_agent_id=entity.proposal_agent_id,
            )
