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
from .evolution.api import init_endpoints as evolution_init_endpoints
from .evolution.api import router as evolution_router

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
        self._system_app.app.include_router(
            evolution_router, prefix=self._api_prefix, tags=self._api_tags
        )
        self._config = self._config or ServeConfig.from_app_config(
            system_app.config, SERVE_CONFIG_KEY_PREFIX
        )
        init_endpoints(self._system_app, self._config)
        # 飞轮体系: 初始化演化引擎 API(引擎/提议存储/轨迹 DAO 单例)
        evolution_init_endpoints(self._system_app, self._config)
        self._app_has_initiated = True

    def on_init(self):
        from .models.models import PlaybookEntity, PlaybookVersionEntity  # noqa: F401
        from .trace.models import (  # noqa: F401
            PlaybookEvolutionProposalEntity, PlaybookTraceEntity,
        )
        _ = [
            PlaybookEntity.__tablename__,
            PlaybookVersionEntity.__tablename__,
            PlaybookTraceEntity.__tablename__,
            PlaybookEvolutionProposalEntity.__tablename__,
        ]

    def before_start(self):
        from .models.models import PlaybookEntity, PlaybookVersionEntity  # noqa: F401
        from .trace.models import (  # noqa: F401
            PlaybookEvolutionProposalEntity, PlaybookTraceEntity,
        )
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
        except Exception as e:
            logger.warning(f"Failed to create Playbook tables: {e}")
