import logging
from typing import List, Optional, Union

from sqlalchemy import URL

from gyra.component import SystemApp
from gyra.storage.metadata import DatabaseManager, Model, UnifiedDBManagerFactory, db
from gyra_serve.core import BaseServe

from .api.endpoints import init_endpoints, router
from .config import (
    APP_NAME, SERVE_APP_NAME, SERVE_APP_NAME_HUMP,
    SERVE_CONFIG_KEY_PREFIX, ServeConfig,
)

logger = logging.getLogger(__name__)


class Serve(BaseServe):
    name = SERVE_APP_NAME

    def __init__(
        self, system_app: SystemApp, config: Optional[ServeConfig] = None,
        api_prefix: Optional[str] = f"/api/v1/serve_{APP_NAME}_service",
        api_tags: Optional[List[str]] = None,
        db_url_or_db: Union[str, URL, DatabaseManager] = None,
        try_create_tables: Optional[bool] = False,
    ):
        if api_tags is None:
            api_tags = [SERVE_APP_NAME_HUMP]
        super().__init__(system_app, api_prefix, api_tags, db_url_or_db, try_create_tables)
        self._config = config

    def init_app(self, system_app: SystemApp):
        if self._app_has_initiated:
            return
        self._system_app = system_app
        self._system_app.app.include_router(router, prefix=self._api_prefix, tags=self._api_tags)
        self._config = self._config or ServeConfig.from_app_config(
            system_app.config, SERVE_CONFIG_KEY_PREFIX
        )
        init_endpoints(self._system_app, self._config)
        self._app_has_initiated = True

    def on_init(self):
        from .models.models import ArtifactEntity, ArtifactVersionEntity  # noqa: F401
        _ = [ArtifactEntity.__tablename__, ArtifactVersionEntity.__tablename__]

    def _ensure_column_conv_id(self, init_db) -> None:
        """存量 server_app_artifact 表补 conv_id 列（幂等，失败只告警）。

        用于大厅会话级交付(task_id=0)按归属会话彻底隔离;新表由 create_all 直接建出,
        旧表需 ALTER 补齐。
        """
        from sqlalchemy import inspect as sa_inspect, text

        from .config import SERVER_APP_TABLE_NAME

        try:
            engine = init_db.engine
            existing = {
                c["name"]
                for c in sa_inspect(engine).get_columns(SERVER_APP_TABLE_NAME)
            }
            if "conv_id" in existing:
                return
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"ALTER TABLE {SERVER_APP_TABLE_NAME} "
                        "ADD COLUMN conv_id VARCHAR(255) NULL"
                    )
                )
            logger.info("artifact table: added column conv_id")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"ensure conv_id column failed: {e}")

    def before_start(self):
        from .models.models import ArtifactEntity, ArtifactVersionEntity  # noqa: F401
        db_manager_factory = self._system_app.get_component(
            "unified_metadata_db_manager_factory",
            UnifiedDBManagerFactory, default_component=None,
        )
        if db_manager_factory is not None and db_manager_factory.create():
            init_db = db_manager_factory.create()
        else:
            init_db = db if not self._db_url_or_db else self._db_url_or_db
            init_db = DatabaseManager.build_from(init_db, base=Model)
        try:
            init_db.create_all()
            # 存量表加列：create_all 不会 ALTER 已存在的表
            self._ensure_column_conv_id(init_db)
        except Exception as e:
            logger.warning(f"Failed to create Artifact tables: {e}")
