"""AppCard serve module entry."""
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
        from .models.models import AppCardEntity, AppCardVersionEntity  # noqa: F401
        from .store.models import AppCardKvEntity, AppCardRecordEntity  # noqa: F401

        _ = [
            AppCardEntity.__tablename__,
            AppCardVersionEntity.__tablename__,
            AppCardRecordEntity.__tablename__,
            AppCardKvEntity.__tablename__,
        ]

    def before_start(self):
        from .models.models import AppCardEntity, AppCardVersionEntity  # noqa: F401
        from .store.models import AppCardKvEntity, AppCardRecordEntity  # noqa: F401

        init_db = self.create_or_get_db_manager()
        try:
            init_db.create_all()
        except Exception as e:
            logger.warning(f"Failed to create AppCard tables: {e}")
