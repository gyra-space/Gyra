import asyncio
import logging
from typing import List, Optional, Union

from sqlalchemy import URL

from gyra.component import SystemApp
from gyra.storage.metadata import DatabaseManager, Model, UnifiedDBManagerFactory, db
from gyra_serve.core import BaseServe

from .api.endpoints import init_endpoints, router
from .config import (
    APP_NAME,
    SERVE_APP_NAME,
    SERVE_APP_NAME_HUMP,
    SERVE_CONFIG_KEY_PREFIX,
    ServeConfig,
)

logger = logging.getLogger(__name__)


class Serve(BaseServe):
    """Serve component for Skill management

    Examples:

        Register the serve component to the system app

        .. code-block:: python

            from fastapi import FastAPI
            from gyra import SystemApp
            from gyra_serve.skill.serve import Serve

            app = FastAPI()
            system_app = SystemApp(app)
            system_app.register(Serve, api_prefix="/api/v1/serve_skill_service")
            system_app.on_init()
            system_app.before_start()

            skill_service = system_app.get_component(Serve.name, Serve)
    """

    name = SERVE_APP_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: Optional[ServeConfig] = None,
        api_prefix: Optional[str] = f"/api/v1/serve_{APP_NAME}_service",
        api_tags: Optional[List[str]] = None,
        db_url_or_db: Union[str, URL, DatabaseManager] = None,
        try_create_tables: Optional[bool] = False,
    ):
        if api_tags is None:
            api_tags = [SERVE_APP_NAME_HUMP]
        super().__init__(
            system_app, api_prefix, api_tags, db_url_or_db, try_create_tables
        )
        self._config = config
        # Strong reference to the fire-and-forget startup sync task.
        self._builtin_sync_task: Optional[asyncio.Task] = None

    def init_app(self, system_app: SystemApp):
        if self._app_has_initiated:
            return
        self._system_app = system_app
        self._system_app.app.include_router(
            router, prefix=self._api_prefix, tags=self._api_tags
        )
        self._config = self._config or ServeConfig.from_app_config(
            system_app.config, SERVE_CONFIG_KEY_PREFIX
        )
        init_endpoints(self._system_app, self._config)
        self._app_has_initiated = True

    def on_init(self):
        """Called before the start of the application.

        You can do some initialization here.
        """
        # import models to ensure they are registered with SQLAlchemy
        from .models.models import SkillEntity  # noqa: F401
        from .models.skill_sync_task_db import SkillSyncTaskEntity  # noqa: F401
        _ = list(map(lambda x: None, [
            SkillEntity.__tablename__,
            SkillSyncTaskEntity.__tablename__,
        ]))

    def before_start(self):
        """Called before the start of the application.

        You can do some initialization here.
        """
        # Import models to ensure they are registered
        from .models.models import SkillEntity  # noqa: F401
        from .models.skill_sync_task_db import SkillSyncTaskEntity  # noqa: F401

        # Force create tables for SQLite mode
        db_manager_factory: UnifiedDBManagerFactory = self._system_app.get_component(
            "unified_metadata_db_manager_factory",
            UnifiedDBManagerFactory,
            default_component=None,
        )
        if db_manager_factory is not None and db_manager_factory.create():
            init_db = db_manager_factory.create()
        else:
            init_db = db if not self._db_url_or_db else self._db_url_or_db
            from gyra.storage.metadata import DatabaseManager
            init_db = DatabaseManager.build_from(init_db, base=Model)

        try:
            init_db.create_all()
        except Exception as e:
            logger.warning(f"Failed to create Skill tables: {e}")

    async def async_after_start(self):
        """Called after the application has started.

        Run the one-time, idempotent skill normalization migration to repair
        legacy hash-suffixed skill_code/directories, then seed the built-in
        skills shipped under the source tree (fire-and-forget).
        """
        await self._normalize_existing_skills()
        self._schedule_builtin_skill_sync()

    def _schedule_builtin_skill_sync(self):
        """Seed built-in skills in the background without blocking startup.

        Normalization must finish first because it can rename skill_code values
        that the built-in sync would otherwise match against.
        """
        from .service.service import Service

        try:
            service: Service = self._system_app.get_component(Service.name, Service)
            if not service:
                logger.info("Skill service not available, skipping built-in skill sync")
                return
            if not service.config.enable_builtin_skill_sync:
                logger.info("Built-in skill sync disabled by config, skipping")
                return

            task = asyncio.create_task(self._run_builtin_skill_sync(service))
            # Keep a strong reference: a bare create_task can be garbage
            # collected mid-flight, silently dropping the sync.
            self._builtin_sync_task = task
            task.add_done_callback(self._on_builtin_sync_done)
        except Exception as e:
            logger.warning(
                f"Failed to schedule built-in skill sync: {e}", exc_info=True
            )

    async def _run_builtin_skill_sync(self, service) -> None:
        """Background body of the built-in skill sync."""
        try:
            skills = await service.sync_from_builtin_dir()
            logger.info(
                f"Built-in skill sync uploaded/updated {len(skills)} skill(s)"
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Built-in skill sync failed: {e}", exc_info=True)

    def _on_builtin_sync_done(self, task: asyncio.Task) -> None:
        """Surface exceptions from the background sync task."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.warning(f"Built-in skill sync task raised: {exc}")

    async def _normalize_existing_skills(self):
        """Run the one-time, idempotent skill normalization migration."""
        from .service.service import Service

        try:
            service: Service = self._system_app.get_component(Service.name, Service)
            if not service:
                logger.info("Skill service not available, skipping normalization")
                return
            result = service.normalize_existing_skills()
            logger.info(f"Skill normalization result: {result}")
        except Exception as e:
            logger.warning(f"Failed to normalize existing skills: {e}", exc_info=True)