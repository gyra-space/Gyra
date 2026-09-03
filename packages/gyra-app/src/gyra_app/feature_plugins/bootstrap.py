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

    def _permission_setting(key: str, default):
        """从 permissions/access_control 插件的 settings 里读取配置（无则用默认）。"""
        for plugin_id in ("permissions", "access_control"):
            entry = raw.get(plugin_id)
            if not isinstance(entry, dict):
                continue
            settings = entry.get("settings")
            if isinstance(settings, dict) and key in settings:
                return settings.get(key, default)
        return default

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

    # 注册 RBAC 管理 Agent 工具(@tool auto_register 进全局工具 registry)。
    # 工具本身 fail-closed(继承提问者身份校验 system.admin),注册不依赖插件开关。
    try:
        from gyra_app.feature_plugins.permissions import (
            agent_tools as _rbac_agent_tools,  # noqa: F401
        )

        logger.info("RBAC admin agent tools registered")
    except Exception as e:
        logger.warning(f"RBAC admin agent tools registration failed: {e}")

    # 注册技能发布 Agent 工具(@tool auto_register 进全局工具 registry)。
    # 工具本身 fail-closed(校验 skill.publish 权限),注册不依赖插件开关。
    try:
        from gyra_app.feature_plugins.skills import (
            agent_tools as _skill_agent_tools,  # noqa: F401
        )

        logger.info("Skill publish agent tools registered")
    except Exception as e:
        logger.warning(f"Skill publish agent tools registration failed: {e}")

    if permissions_enabled:
        from gyra_app.feature_plugins.permissions.seed import (
            ensure_default_roles,
            ensure_schema_upgrades,
            sync_permission_definitions,
        )
        from gyra.storage.metadata.db_manager import db

        # Ensure permission tables exist before seeding data
        try:
            db.create_all()
        except Exception as e:
            logger.warning(f"Failed to create all tables: {e}")

        # 存量库补齐新列（role / user_role / permission_definition 的新增列）。
        # 可由 feature_plugins.<permissions|access_control>.settings.auto_schema_upgrade
        # 关闭（默认开启）；表结构交由外部 DDL 管理时设为 false。
        if _permission_setting("auto_schema_upgrade", True):
            ensure_schema_upgrades()
        # 先 seed 角色/旧版定义,再同步协议定义——sync 末尾会把旧版蛇形
        # 命名定义置为失效,顺序反了会当晚重建、次日才收敛。
        ensure_default_roles()
        # 代码注册的权限协议 -> permission_definition 表（幂等 upsert + 失效清理）
        sync_permission_definitions()

        # workspace_member.role -> user_role 空间级绑定（幂等，兜底双写遗漏）
        from gyra_app.feature_plugins.permissions.seed import (
            migrate_space_role_bindings,
        )
        migrate_space_role_bindings()

        # Migrate old conversation user_name from mock IDs to real usernames
        from gyra_app.feature_plugins.permissions.seed import migrate_conversation_user_names
        migrate_conversation_user_names()

    # Migrate workspaces owned by the mock user (owner_user_id=0) to admin,
    # so they remain visible/manageable after enabling auth. 幂等且廉价,
    # 每次启动兜底执行,覆盖「仅开启 OAuth 登录、未启用权限插件」的场景。
    from gyra_app.feature_plugins.permissions.seed import migrate_workspace_owners
    migrate_workspace_owners()

    # Fix ECP 提案确认白名单:清除 mock 用户留下的陈旧确认人记录并确保
    # owner 在名单内,避免「名单非空却无真实用户命中、所有人失去确认权限」。
    from gyra_app.feature_plugins.permissions.seed import migrate_ecp_confirmers
    migrate_ecp_confirmers()
