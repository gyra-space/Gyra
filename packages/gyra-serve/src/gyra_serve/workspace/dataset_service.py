"""Workspace-owned dataset service.

Manages self-owned data assets of a scene workspace: uploaded Excel/CSV
files are materialized as per-dataset DuckDB files inside the workspace
sandbox directory, registered as `connect_config` records
(db_type=excel/csv, owner_workspace_id set) and auto-bound to the
workspace via `workspace_resource`. This makes them first-class
datasources: schema learning (table_spec/db_spec) and structured
proposals work on them unchanged.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from gyra_serve.datasource.manages.connect_config_db import ConnectConfigDao
from gyra_serve.datasource.service.file_dataset import (
    db_type_for_file,
    materialize_file_to_duckdb,
    sanitize_asset_name,
)

from .api.schemas import WorkspaceResourceRequest
from .models.models import WorkspaceResourceDao

logger = logging.getLogger(__name__)

# Sandbox root for workspace-owned assets; relative to the server working
# directory (matches the `pilot/data` convention).
DEFAULT_SANDBOX_ROOT = "pilot/data/workspaces"

SANDBOX_SUBDIRS = ("files", "db", "runtime")

# 会话级工作目录:位于公共层之下,目录名固定为 sessions/<conv_uid>。
SESSION_DIR_NAME = "sessions"
SESSION_SUBDIRS = ("files", "runtime")

# 空间级共享目录:会话通过 promote 提升到此处的资产,跨会话可见。
SHARED_DIR_NAME = "shared"

__all__ = [
    "WorkspaceDatasetService",
    "sanitize_asset_name",
    "DEFAULT_SANDBOX_ROOT",
    "SANDBOX_SUBDIRS",
    "SESSION_DIR_NAME",
    "SESSION_SUBDIRS",
    "SHARED_DIR_NAME",
    "workspace_sandbox_root",
    "session_sandbox_root",
    "workspace_shared_dir",
]


def workspace_sandbox_root(workspace_id: int) -> str:
    """场景空间沙箱根目录(绝对路径,含 files/db/runtime 子目录)。

    这是**公共层**,同时也是沙箱的访问边界(allowed root):
    大厅/任务模式共享此持久目录,agent 可直接读写 files/ 中的上传数据集。
    沙箱侧要求绝对路径(macOS sandbox-exec profile 只放行绝对路径)。

    注意:此函数只负责公共层。agent 的当前工作目录(cwd)请使用
    :func:`session_sandbox_root`,后者位于本目录下,因此权限与隔离
    边界仍由本层决定——沙箱实例数、cleanup 规则均不受影响。
    """
    root = os.environ.get("GYRA_WORKSPACE_SANDBOX_ROOT", DEFAULT_SANDBOX_ROOT)
    root = os.path.abspath(os.path.join(root, str(workspace_id)))
    for sub in SANDBOX_SUBDIRS:
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    return root


def session_sandbox_root(workspace_id: int, conv_session_id: str) -> str:
    """会话级沙箱工作目录(绝对路径)。

    只把 agent 的**当前工作目录(cwd)**下移到
    ``<公共层>/sessions/<conv_session_id>/``,公共层本身不变:

    - 沙箱实例仍按 workspace 复用(见 ``agent_chat._sandbox_key``),
      实例数量、资源占用、``_cleanup_sandbox_manager`` 规则全部不变;
    - 会话目录都在公共层之下,而 ``allowed_roots`` 覆盖公共层,
      所以主子 agent(同一实例、不同 cwd)与跨会话之间物理上互相可达,
      绝对路径仍能访问空间级公共资产,无需软链。

    Args:
        workspace_id: 场景空间 ID。
        conv_session_id: **会话标识**,必须是 ``AgentContext.conv_session_id``。

            切勿传 ``AgentContext.conv_id`` —— 它是
            ``{conv_session_id}_{round}``,每提一次问就变(带 ``_1``/``_2``
            轮次后缀),用它建目录会导致同一会话的每一轮各占一个目录,
            上一轮写的文件下一轮就读不到。

    Returns:
        会话目录绝对路径,已创建 files/runtime 子目录。
    """
    root = workspace_sandbox_root(workspace_id)
    # 顺带确保公共层的 shared/ 存在,agent 随时可以把文件 promote 上去。
    workspace_shared_dir(workspace_id)
    safe = sanitize_asset_name(str(conv_session_id), fallback="default")
    session_root = os.path.join(root, SESSION_DIR_NAME, safe)
    for sub in SESSION_SUBDIRS:
        os.makedirs(os.path.join(session_root, sub), exist_ok=True)
    return session_root


def workspace_shared_dir(workspace_id: int) -> str:
    """空间级共享目录(绝对路径):会话 promote 出来的公共资产存放于此。

    位于公共层之下,因此对所有会话可见(通过 ``../shared/`` 或绝对路径)。
    """
    shared = os.path.join(workspace_sandbox_root(workspace_id), SHARED_DIR_NAME)
    os.makedirs(shared, exist_ok=True)
    return shared


class WorkspaceDatasetService:
    """Import and list workspace-owned Excel/CSV datasets."""

    def __init__(self, system_app=None, sandbox_root: Optional[str] = None):
        self._system_app = system_app
        self._sandbox_root = sandbox_root or os.environ.get(
            "GYRA_WORKSPACE_SANDBOX_ROOT", DEFAULT_SANDBOX_ROOT
        )
        self._dao = ConnectConfigDao()
        self._resource_dao = WorkspaceResourceDao()

    # ---------------- sandbox ----------------

    def sandbox_dir(self, workspace_id: int) -> str:
        """Return the workspace sandbox dir, creating files/db/runtime."""
        root = os.path.join(self._sandbox_root, str(workspace_id))
        for sub in SANDBOX_SUBDIRS:
            os.makedirs(os.path.join(root, sub), exist_ok=True)
        return root

    # ---------------- import ----------------

    def import_dataset(
        self,
        workspace_id: int,
        file_name: str,
        file_content: bytes,
        display_name: Optional[str] = None,
        user_id: Optional[str] = None,
        trigger_learning: bool = True,
    ) -> Dict[str, Any]:
        """Import an uploaded Excel/CSV file as a workspace-owned dataset.

        Steps: save original -> materialize into per-dataset DuckDB file ->
        upsert connect_config -> ensure workspace_resource binding ->
        best-effort schema learning.

        Returns:
            Dict with datasource_id, db_name, db_type, tables, learning.
        """
        ext = os.path.splitext(file_name)[1].lower()
        db_type = db_type_for_file(file_name)
        if db_type is None:
            raise ValueError(f"Unsupported file type '{ext}', expected Excel/CSV")

        asset_name = sanitize_asset_name(os.path.splitext(os.path.basename(file_name))[0])
        display_name = display_name or asset_name
        db_name = f"ws{workspace_id}_{asset_name}"

        root = self.sandbox_dir(workspace_id)
        original_path = os.path.join(root, "files", f"{asset_name}{ext}")
        with open(original_path, "wb") as f:
            f.write(file_content)

        duckdb_path = os.path.abspath(os.path.join(root, "db", f"{asset_name}.duckdb"))
        tables = materialize_file_to_duckdb(file_content, ext, duckdb_path)

        datasource_id = self._upsert_connect_config(
            db_name=db_name,
            db_type=db_type,
            db_path=duckdb_path,
            workspace_id=workspace_id,
            comment=display_name,
            user_id=user_id,
        )
        self._ensure_resource_binding(workspace_id, datasource_id, display_name)

        learning = self._trigger_learning(datasource_id, db_name, tables, trigger_learning)

        return {
            "datasource_id": datasource_id,
            "db_name": db_name,
            "db_type": db_type,
            "display_name": display_name,
            "tables": tables,
            "duckdb_path": duckdb_path,
            "original_path": original_path,
            "learning": learning,
        }

    def _upsert_connect_config(
        self,
        db_name: str,
        db_type: str,
        db_path: str,
        workspace_id: int,
        comment: str,
        user_id: Optional[str],
    ) -> int:
        existing = self._dao.get_by_names(db_name)
        if existing is not None:
            if existing.owner_workspace_id != workspace_id:
                raise ValueError(
                    f"Dataset name conflict: '{db_name}' is owned by another "
                    f"workspace ({existing.owner_workspace_id})"
                )
            # Re-import of the same dataset: tables already replaced in the
            # backing file, reuse the existing connect_config record.
            return existing.id
        entity = self._dao.add_workspace_file_db(
            db_name=db_name,
            db_type=db_type,
            db_path=db_path,
            owner_workspace_id=workspace_id,
            comment=comment,
            user_id=user_id,
        )
        return entity.id

    def _ensure_resource_binding(
        self, workspace_id: int, datasource_id: int, display_name: str
    ) -> None:
        physical_ref = str(datasource_id)
        for entity in self._resource_dao.list_by_workspace(workspace_id, "data_source"):
            if entity.physical_ref == physical_ref:
                return
        self._resource_dao.create(
            WorkspaceResourceRequest(
                workspace_id=workspace_id,
                type="data_source",
                name=display_name,
                category="scenario_specific",
                physical_ref=physical_ref,
                access_mode="read",
            )
        )

    def _trigger_learning(
        self,
        datasource_id: int,
        db_name: str,
        tables: List[str],
        trigger_learning: bool,
    ) -> Dict[str, Any]:
        """Best-effort schema learning; failures never break the import."""
        if not trigger_learning:
            return {"status": "skipped"}
        if self._system_app is None:
            return {"status": "skipped", "reason": "no system_app"}
        try:
            from gyra.component import ComponentType

            from gyra_serve.datasource.manages.connector_manager import (
                ConnectorManager,
            )
            from gyra_serve.datasource.service.learning_service import (
                SchemaLearningService,
            )

            connector_manager = self._system_app.get_component(
                ComponentType.CONNECTOR_MANAGER, ConnectorManager
            )
            learning_service = SchemaLearningService(connector_manager, self._system_app)
            for table in tables:
                learning_service.learn_single_table(datasource_id, db_name, table)
            return {"status": "completed", "tables": tables}
        except Exception as e:
            logger.warning(f"[Dataset] schema learning failed for {db_name}: {e}")
            return {"status": "failed", "error": str(e)}

    # ---------------- list ----------------

    def list_datasets(self, workspace_id: int) -> List[Dict[str, Any]]:
        """List workspace-owned datasets."""
        return [
            {
                "datasource_id": e.id,
                "db_name": e.db_name,
                "db_type": e.db_type,
                "display_name": e.comment,
                "db_path": e.db_path,
                "gmt_created": e.gmt_created.isoformat() if e.gmt_created else None,
                "gmt_modified": e.gmt_modified.isoformat() if e.gmt_modified else None,
            }
            for e in self._dao.list_by_workspace(workspace_id)
        ]
