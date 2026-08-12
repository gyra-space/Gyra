"""Register routers for enabled builtin feature plugins at process startup."""

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def register_enabled_feature_plugin_routers(app: FastAPI) -> None:
    """Conditionally mount plugin HTTP routes (requires restart after toggling plugins)."""
    # Try to load from database first
    try:
        from gyra_app.feature_plugins.system_config_dao import SystemConfigDao

        dao = SystemConfigDao()
        raw = dao.get_all_configs("feature_plugin")
        logger.info(f"Loaded feature plugins from database: {raw}")
    except Exception as e:
        logger.warning(f"Feature plugins: failed to load from database: {e}")
        raw = {}

    # Fall back to config file if database is empty
    if not raw:
        try:
            from gyra_core.config import ConfigManager, FeaturePluginEntry

            cfg = ConfigManager.get()
            raw_cfg = getattr(cfg, "feature_plugins", None) or {}
            raw = {
                k: v.model_dump(mode="json") if hasattr(v, "model_dump") else dict(v)
                for k, v in raw_cfg.items()
            }
        except Exception as e:
            logger.warning("Feature plugins: skip router registration (config unavailable): %s", e)
            return

    def _enabled(plugin_id: str) -> bool:
        entry = raw.get(plugin_id)
        if entry is None:
            return False
        if isinstance(entry, dict):
            return bool(entry.get("enabled"))
        return False

    # Check if access_control (unified permission system) is enabled.
    # The permission/user-group management routers are ALWAYS mounted so the
    # endpoints exist out of the box -- toggling the plugin in the UI no longer
    # requires a service restart for the routes to appear. The plugin flag only
    # gates RBAC *enforcement* (auth._is_permissions_enabled) and data seeding;
    # when the plugin is off, require_permission bypasses checks (open mode),
    # so these endpoints stay callable without login.
    access_control_enabled = _enabled("access_control")
    permissions_enabled = _enabled("permissions") or access_control_enabled

    from gyra_app.feature_plugins.user_groups.api import (
        router as user_groups_router,
    )
    from gyra_app.feature_plugins.permissions.api import (
        router as permissions_router,
    )

    app.include_router(user_groups_router, prefix="/api/v1")
    logger.info("Feature plugin mounted: user_groups at /api/v1/user-groups")

    app.include_router(permissions_router, prefix="/api/v1")
    logger.info("Feature plugin mounted: permissions at /api/v1/permissions")

    if permissions_enabled:
        from gyra_app.feature_plugins.permissions.seed import ensure_default_roles
        from gyra.storage.metadata.db_manager import db

        # Ensure permission tables exist before seeding data
        try:
            db.create_all()
        except Exception as e:
            logger.warning(f"Failed to create all tables: {e}")

        ensure_default_roles()

        # Migrate old conversation user_name from mock IDs to real usernames
        from gyra_app.feature_plugins.permissions.seed import migrate_conversation_user_names
        migrate_conversation_user_names()

    # Migrate workspaces owned by the mock user (owner_user_id=0) to admin,
    # so they remain visible/manageable after enabling auth. 幂等且廉价,
    # 每次启动兜底执行,覆盖「仅开启 OAuth 登录、未启用权限插件」的场景。
    from gyra_app.feature_plugins.permissions.seed import migrate_workspace_owners
    migrate_workspace_owners()
