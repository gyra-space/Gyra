"""Seed data initialization for built-in roles and default admin user."""

import logging

from sqlalchemy import or_, text as sa_text

from .dao import PermissionDao

logger = logging.getLogger(__name__)


def _keys_to_tuples(permission_keys: list[str]) -> list[tuple[str, str]]:
    """协议权限 key 列表 -> 存量 (resource_type, action) 元组列表"""
    from gyra_serve.permissions.protocol import parse_key

    return [parse_key(k) for k in permission_keys]

# Default permission definitions that can be assigned to roles
SEED_PERMISSION_DEFINITIONS = [
    # Agent permissions
    {"name": "agent_read_all", "description": "可读取所有智能体", "resource_type": "agent", "resource_id": "*", "action": "read"},
    {"name": "agent_chat_all", "description": "可与所有智能体对话", "resource_type": "agent", "resource_id": "*", "action": "chat"},
    {"name": "agent_write_all", "description": "可管理所有智能体配置", "resource_type": "agent", "resource_id": "*", "action": "write"},
    {"name": "agent_admin_all", "description": "可完全管理所有智能体", "resource_type": "agent", "resource_id": "*", "action": "admin"},
    # Tool permissions
    {"name": "tool_read_all", "description": "可读取所有工具", "resource_type": "tool", "resource_id": "*", "action": "read"},
    {"name": "tool_execute_all", "description": "可执行所有工具", "resource_type": "tool", "resource_id": "*", "action": "execute"},
    {"name": "tool_manage_all", "description": "可管理所有工具", "resource_type": "tool", "resource_id": "*", "action": "manage"},
    # Knowledge permissions
    {"name": "knowledge_read_all", "description": "可读取所有知识库", "resource_type": "knowledge", "resource_id": "*", "action": "read"},
    {"name": "knowledge_query_all", "description": "可检索所有知识库", "resource_type": "knowledge", "resource_id": "*", "action": "query"},
    {"name": "knowledge_write_all", "description": "可管理所有知识库", "resource_type": "knowledge", "resource_id": "*", "action": "write"},
    # Model permissions
    {"name": "model_read_all", "description": "可读取所有模型", "resource_type": "model", "resource_id": "*", "action": "read"},
    {"name": "model_chat_all", "description": "可使用所有模型对话", "resource_type": "model", "resource_id": "*", "action": "chat"},
    {"name": "model_manage_all", "description": "可管理所有模型", "resource_type": "model", "resource_id": "*", "action": "manage"},
    # System permissions
    {"name": "system_admin", "description": "系统管理员权限", "resource_type": "system", "resource_id": "*", "action": "admin"},
    # Cron permissions
    {"name": "cron_read_all", "description": "可查看所有定时任务", "resource_type": "cron", "resource_id": "*", "action": "read"},
    {"name": "cron_manage_all", "description": "可管理所有定时任务", "resource_type": "cron", "resource_id": "*", "action": "manage"},
    # Channel permissions
    {"name": "channel_read_all", "description": "可查看所有渠道", "resource_type": "channel", "resource_id": "*", "action": "read"},
    {"name": "channel_manage_all", "description": "可管理所有渠道", "resource_type": "channel", "resource_id": "*", "action": "manage"},
    # Database permissions
    {"name": "database_read_all", "description": "可查看所有数据库", "resource_type": "database", "resource_id": "*", "action": "read"},
    {"name": "database_manage_all", "description": "可管理所有数据库", "resource_type": "database", "resource_id": "*", "action": "manage"},
]

SEED_ROLES = [
    {
        "name": "superadmin",
        "description": "超级管理员（判定时全量绕过，不可删除）",
        "is_system": 1,
        "scope_type": "global",
        "permissions": [],
    },
    {
        "name": "guest",
        "description": "访客（仅可查看模型和监控，不能查看智能体/工具/知识库）",
        "is_system": 1,
        "permissions": [
            ("model", "read"),
            ("model", "chat"),
        ],
    },
    {
        "name": "normal_user",
        "description": "普通用户（可查看和使用智能体对话，可打开分享链接）",
        "is_system": 1,
        "permissions": [
            ("agent", "read"),
            ("agent", "chat"),
            ("model", "read"),
            ("model", "chat"),
        ],
    },
    {
        "name": "viewer",
        "description": "只读访问所有资源（可查看界面和详情，但不能对话/执行/编辑）",
        "is_system": 1,
        "permissions": [
            ("agent", "read"),
            ("tool", "read"),
            ("knowledge", "read"),
            ("model", "read"),
        ],
    },
    {
        "name": "operator",
        "description": "操作员（可查看、对话、执行工具、检索知识库，但不能编辑配置）",
        "is_system": 1,
        "permissions": [
            ("agent", "read"),
            ("agent", "chat"),
            ("tool", "read"),
            ("tool", "execute"),
            ("knowledge", "read"),
            ("knowledge", "query"),
            ("model", "read"),
            ("model", "chat"),
        ],
    },
    {
        "name": "developer",
        "description": "开发者（可新增/编辑/删除智能体，使用对话，管理Skills/MCP/数据库/模型/定时任务/渠道）",
        "is_system": 1,
        "permissions": [
            ("agent", "read"),
            ("agent", "chat"),
            ("agent", "write"),
            ("tool", "read"),
            ("tool", "execute"),
            ("tool", "manage"),
            ("knowledge", "read"),
            ("knowledge", "query"),
            ("model", "read"),
            ("model", "chat"),
            ("model", "manage"),
            ("database", "read"),
            ("database", "manage"),
            ("cron", "read"),
            ("cron", "manage"),
            ("channel", "read"),
            ("channel", "manage"),
        ],
    },
    {
        "name": "editor",
        "description": "编辑者（可查看、使用、编辑所有资源配置）",
        "is_system": 1,
        "permissions": [
            ("agent", "read"),
            ("agent", "chat"),
            ("agent", "write"),
            ("tool", "read"),
            ("tool", "execute"),
            ("tool", "manage"),
            ("knowledge", "read"),
            ("knowledge", "query"),
            ("knowledge", "write"),
            ("model", "read"),
            ("model", "chat"),
            ("model", "manage"),
        ],
    },
    {
        "name": "admin",
        "description": "完全管理权限",
        "is_system": 1,
        "permissions": [
            ("agent", "read"),
            ("agent", "chat"),
            ("agent", "write"),
            ("agent", "admin"),
            ("tool", "read"),
            ("tool", "execute"),
            ("tool", "manage"),
            ("tool", "admin"),
            ("knowledge", "read"),
            ("knowledge", "query"),
            ("knowledge", "write"),
            ("knowledge", "admin"),
            ("model", "read"),
            ("model", "chat"),
            ("model", "manage"),
            ("model", "admin"),
            ("database", "read"),
            ("database", "manage"),
            ("cron", "read"),
            ("cron", "manage"),
            ("channel", "read"),
            ("channel", "manage"),
            ("system", "read"),
            ("system", "write"),
            ("system", "admin"),
        ],
    },
]

# ===== 内置空间角色（scope_type=space，绑定具体空间后生效） =====
from gyra_serve.permissions.modules.space import (  # noqa: E402
    SPACE_ALL,
    SPACE_MEMBER_KEYS,
    SPACE_VIEWER_KEYS,
)

SEED_SPACE_ROLES = [
    {
        "name": "space.admin",
        "description": "空间管理（空间内全部权限）",
        "is_system": 1,
        "scope_type": "space",
        "permissions": _keys_to_tuples(SPACE_ALL),
    },
    {
        "name": "space.member",
        "description": "空间使用（对话/任务/看产出，资产能力剧本只读）",
        "is_system": 1,
        "scope_type": "space",
        "permissions": _keys_to_tuples(SPACE_MEMBER_KEYS),
    },
    {
        "name": "space.viewer",
        "description": "空间查看（只读，不能发起对话/任务）",
        "is_system": 1,
        "scope_type": "space",
        "permissions": _keys_to_tuples(SPACE_VIEWER_KEYS),
    },
]


def _ensure_system_role_permissions(
    dao: PermissionDao, role_id: int, expected_permissions: list[tuple[str, str]]
) -> None:
    """Ensure built-in system role has all expected wildcard permissions."""
    current = dao.list_role_permissions(role_id)
    current_keys = {
        (p.get("resource_type"), p.get("action"), p.get("resource_id", "*"))
        for p in current
    }

    for resource_type, action in expected_permissions:
        key = (resource_type, action, "*")
        if key in current_keys:
            continue
        try:
            dao.add_role_permission(
                role_id=role_id,
                resource_type=resource_type,
                action=action,
                resource_id="*",
            )
            logger.info(
                "Added missing permission %s:%s(*) to system role id=%s",
                resource_type,
                action,
                role_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to add missing permission %s:%s to role id=%s: %s",
                resource_type,
                action,
                role_id,
                e,
            )


def ensure_default_roles() -> None:
    """Idempotent: 创建内置角色（如果不存在）并创建默认 admin 用户。"""
    dao = PermissionDao()

    # 1. 创建默认角色
    admin_role_id = None
    for role_def in SEED_ROLES + SEED_SPACE_ROLES:
        existing = dao.get_role_by_name(role_def["name"])
        if existing:
            logger.debug(f"Seed role already exists: {role_def['name']}")
            # Align existing system role permissions with current seed definition.
            _ensure_system_role_permissions(
                dao,
                existing["id"],
                role_def["permissions"],
            )
            if role_def["name"] == "admin":
                admin_role_id = existing["id"]
            continue
        try:
            role = dao.create_role(
                name=role_def["name"],
                description=role_def["description"],
                is_system=role_def["is_system"],
                scope_type=role_def.get("scope_type", "global"),
            )
            for resource_type, action in role_def["permissions"]:
                dao.add_role_permission(
                    role_id=role["id"],
                    resource_type=resource_type,
                    action=action,
                )
            logger.info(f"Seed role created: {role_def['name']}")
            if role_def["name"] == "admin":
                admin_role_id = role["id"]
        except Exception as e:
            logger.exception(f"Failed to create seed role {role_def['name']}: {e}")

    # 2. 创建默认 admin 用户并分配角色
    if admin_role_id:
        try:
            import os
            import bcrypt
            from gyra_app.auth.user_service import UserEntity
            from gyra.storage.metadata.db_manager import db
            from datetime import datetime

            default_password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")
            password_hash = bcrypt.hashpw(
                default_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            with db.session(commit=True) as s:
                # 检查是否已存在 admin 用户（通过 oauth_id 或 name）
                existing_admin = s.query(UserEntity).filter(
                    or_(
                        UserEntity.oauth_id == "admin",
                        UserEntity.name == "admin",
                    )
                ).first()

                if existing_admin:
                    logger.debug(f"Admin user already exists: {existing_admin.name}")
                    admin_user_id = existing_admin.id

                    # Upgrade path: ensure oauth_provider, oauth_id, password_hash
                    needs_update = False
                    if existing_admin.oauth_provider != "local":
                        existing_admin.oauth_provider = "local"
                        needs_update = True
                        logger.info("Updated admin user oauth_provider to 'local'")
                    if not existing_admin.oauth_id:
                        existing_admin.oauth_id = "admin"
                        needs_update = True
                    try:
                        if not existing_admin.password_hash:
                            existing_admin.password_hash = password_hash
                            needs_update = True
                            logger.info("Set default password for existing admin user")
                    except Exception:
                        # password_hash column might not exist yet
                        logger.warning(
                            "password_hash column may not exist, will attempt ALTER TABLE"
                        )
                        try:
                            from sqlalchemy import text as sa_text
                            s.execute(sa_text(
                                "ALTER TABLE user ADD COLUMN password_hash VARCHAR(255)"
                            ))
                            s.commit()
                            logger.info("Added password_hash column to user table")
                            existing_admin.password_hash = password_hash
                            needs_update = True
                        except Exception as col_err:
                            logger.debug(f"ALTER TABLE (may already exist): {col_err}")

                    if needs_update:
                        s.merge(existing_admin)
                        s.commit()

                    # 检查是否已分配 admin 角色
                    user_roles = dao.get_user_roles(admin_user_id)
                    has_admin_role = any(r.get("id") == admin_role_id for r in user_roles)
                    if not has_admin_role:
                        dao.assign_role_to_user(admin_user_id, admin_role_id)
                        logger.info("Assigned admin role to existing admin user")
                else:
                    # 创建新的 admin 用户
                    user = UserEntity(
                        name="admin",
                        fullname="System Administrator",
                        oauth_provider="local",
                        oauth_id="admin",
                        email="admin@gyra.local",
                        password_hash=password_hash,
                        role="admin",
                        is_active=1,
                        gmt_create=datetime.utcnow(),
                        gmt_modify=datetime.utcnow(),
                    )
                    s.add(user)
                    s.flush()  # 获取 ID
                    admin_user_id = user.id
                    s.commit()

                    # 分配 admin 角色
                    dao.assign_role_to_user(admin_user_id, admin_role_id)
                    logger.info(f"Created default admin user (ID={admin_user_id}) and assigned admin role")
                    logger.info("=" * 60)
                    logger.info("DEFAULT ADMIN USER CREATED:")
                    logger.info("  Username: admin")
                    logger.info("  Password: %s", default_password)
                    logger.info("  Provider: local (username/password login)")
                    logger.info(f"  User ID: {admin_user_id}")
                    logger.info("  !! Change the default password in production !!")
                    logger.info("=" * 60)
        except Exception as e:
            logger.error(f"Failed to create/assign admin user: {e}", exc_info=True)

    # 3. 创建默认权限定义
    _ensure_default_permission_definitions(dao)


def _ensure_default_permission_definitions(dao: PermissionDao) -> None:
    """Idempotent: 创建默认权限定义（如果不存在）。"""
    for perm_def in SEED_PERMISSION_DEFINITIONS:
        # Check if already exists by name
        existing = None
        try:
            all_defs = dao.list_permission_definitions()
            existing = next((d for d in all_defs if d["name"] == perm_def["name"]), None)
        except Exception:
            pass

        if existing:
            logger.debug(f"Seed permission definition already exists: {perm_def['name']}")
            continue

        try:
            dao.create_permission_definition(
                name=perm_def["name"],
                description=perm_def["description"],
                resource_type=perm_def["resource_type"],
                resource_id=perm_def["resource_id"],
                action=perm_def["action"],
                effect="allow",
            )
            logger.info(f"Seed permission definition created: {perm_def['name']}")
        except Exception as e:
            logger.warning(f"Failed to create seed permission definition {perm_def['name']}: {e}")


# Track whether migration has run in this process
_migration_done = False
_workspace_migration_done = False
_ecp_confirmer_migration_done = False


def _dialect_name(s) -> str:
    """当前会话绑定的数据库方言名（sqlite/mysql/postgresql...），小写。"""
    return (s.get_bind().dialect.name or "").lower()


def _table_columns(s, table: str) -> set:
    """跨方言：列出表现有列名（SQLite/MySQL/PostgreSQL 通用）。"""
    from sqlalchemy import inspect as _inspect

    inspector = _inspect(s.get_bind())
    try:
        return {c["name"] for c in inspector.get_columns(table)}
    except Exception:  # noqa: BLE001
        return set()


def _ensure_user_role_scope_index(s) -> bool:
    """确保 user_role 唯一索引覆盖 scope_id（MySQL/PostgreSQL）。

    存量库的 uk_user_role 可能是旧结构 (user_id, role_id)，不含 scope_id，
    会阻止空间级绑定。重建为 (user_id, role_id, scope_id) 以对齐新模型。
    返回 True 表示索引被重建/创建；无需改动或失败返回 False。
    """
    from sqlalchemy import inspect as _inspect

    inspector = _inspect(s.get_bind())
    try:
        indexes = {
            i.get("name"): list(i.get("column_names") or [])
            for i in inspector.get_indexes("user_role")
        }
    except Exception as e:  # noqa: BLE001
        logger.debug("schema upgrade: inspect user_role indexes failed: %s", e)
        return False

    target = {"user_id", "role_id", "scope_id"}
    current = indexes.get("uk_user_role")
    if current and set(current) == target:
        return False

    try:
        if current:
            # MySQL 的 DROP INDEX 语法为 DROP INDEX name ON table
            s.execute(sa_text("DROP INDEX uk_user_role ON user_role"))
            s.commit()
        s.execute(
            sa_text(
                "CREATE UNIQUE INDEX uk_user_role "
                "ON user_role (user_id, role_id, scope_id)"
            )
        )
        s.commit()
        logger.info("Schema upgraded: user_role unique index covers scope_id")
        return True
    except Exception as e:  # noqa: BLE001
        s.rollback()
        logger.debug("schema upgrade user_role index skipped (may exist): %s", e)
        return False


def _rebuild_user_role_with_scope(s) -> bool:
    """检测 user_role 缺 scope_id 列并补齐（幂等，跨方言）。

    - SQLite：无法直接改唯一约束，重建表换唯一约束（IFNULL 兜底空 scope_id）。
    - MySQL/PostgreSQL：ALTER ADD COLUMN + 重建唯一索引覆盖 scope_id。

    返回 True 表示本函数对 schema 做了改动；无需改动时返回 False。
    """
    cols = _table_columns(s, "user_role")
    if not cols:
        return False  # 表还不存在，create_all 会按新结构建

    if _dialect_name(s) != "sqlite":
        changed = False
        if "scope_id" not in cols:
            try:
                s.execute(sa_text("ALTER TABLE user_role ADD COLUMN scope_id INTEGER"))
                s.commit()
                logger.info("Schema upgraded: user_role.scope_id added")
                changed = True
            except Exception as e:  # noqa: BLE001
                s.rollback()
                logger.debug(
                    "schema upgrade user_role.scope_id skipped (may exist): %s", e
                )
        if _ensure_user_role_scope_index(s):
            changed = True
        return changed

    if "scope_id" in cols:
        return False
    s.execute(sa_text(
        """
        CREATE TABLE user_role_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            scope_id INTEGER,
            gmt_create DATETIME
        )
        """
    ))
    s.execute(sa_text(
        """
        INSERT INTO user_role_new (id, user_id, role_id, scope_id, gmt_create)
        SELECT id, user_id, role_id, NULL, gmt_create FROM user_role
        """
    ))
    s.execute(sa_text("DROP TABLE user_role"))
    s.execute(sa_text("ALTER TABLE user_role_new RENAME TO user_role"))
    s.execute(sa_text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uk_user_role "
        "ON user_role (user_id, role_id, IFNULL(scope_id, -1))"
    ))
    s.execute(sa_text(
        "CREATE INDEX IF NOT EXISTS ix_user_role_user_id ON user_role (user_id)"
    ))
    s.commit()
    logger.info("Schema upgraded: user_role rebuilt with scope_id column")
    return True


def ensure_schema_upgrades() -> None:
    """幂等：为存量库补齐新列/新约束（db.create_all 不会 ALTER 已有表）。

    - role.scope_type
    - permission_definition.scope_type / grantable
    - user_role.scope_id（SQLite 重建表换唯一约束；MySQL/PG ALTER 加列+重建索引）
    """
    from gyra.storage.metadata.db_manager import db

    with db.session(commit=False) as s:
        _rebuild_user_role_with_scope(s)

    # grantable 的默认值按方言出字面量:PG 的 BOOLEAN 列不能 DEFAULT 0(非法),
    # SQLite/MySQL 接受 0
    dialect = getattr(getattr(db, "engine", None), "dialect", None)
    dialect_name = getattr(dialect, "name", "") or ""
    grantable_default = "false" if "postgres" in dialect_name else "0"

    stmts = [
        "ALTER TABLE role ADD COLUMN scope_type VARCHAR(16) NOT NULL DEFAULT 'global'",
        "ALTER TABLE permission_definition ADD COLUMN scope_type VARCHAR(16) NOT NULL DEFAULT 'global'",
        f"ALTER TABLE permission_definition ADD COLUMN grantable BOOLEAN NOT NULL DEFAULT {grantable_default}",
    ]
    with db.session(commit=False) as s:
        for stmt in stmts:
            try:
                s.execute(sa_text(stmt))
                s.commit()
                logger.info("Schema upgraded: %s", stmt)
            except Exception as e:  # noqa: BLE001
                s.rollback()
                logger.debug("Schema upgrade skipped (may exist): %s", e)


_SPACE_ROLE_NAMES = {
    "owner": "space.admin",
    "contributor": "space.member",
    "viewer": "space.viewer",
}


def migrate_space_role_bindings() -> None:
    """幂等迁移：workspace_member.role -> user_role 空间级绑定。

    老成员表的三值角色映射为内置空间角色（user_role.scope_id=workspace_id），
    使空间域判定走统一协议；workspace_member 保留（成员名单/is_home 等）。
    每次启动兜底执行，覆盖运行期新增但未双写的成员记录。
    """
    try:
        from gyra.storage.metadata.db_manager import db
        from gyra_serve.workspace.models.models import WorkspaceMemberEntity
        from .models import UserRoleEntity
    except Exception as e:
        logger.debug("migrate_space_role_bindings: workspace models unavailable: %s", e)
        return

    dao = PermissionDao()
    role_ids = {}
    for role_name in ("space.admin", "space.member", "space.viewer"):
        row = dao.get_role_by_name(role_name)
        if row:
            role_ids[role_name] = row["id"]
    if not role_ids:
        return

    created = 0
    try:
        with db.session(commit=False) as s:
            members = s.query(WorkspaceMemberEntity).all()
            for m in members:
                role_name = _SPACE_ROLE_NAMES.get((m.role or "").strip())
                if not role_name or role_name not in role_ids:
                    continue
                uid = m.user_id
                if uid is None:
                    continue
                try:
                    uid = int(uid)
                except (TypeError, ValueError):
                    continue
                exists = (
                    s.query(UserRoleEntity)
                    .filter(
                        UserRoleEntity.user_id == uid,
                        UserRoleEntity.role_id == role_ids[role_name],
                        UserRoleEntity.scope_id == m.workspace_id,
                    )
                    .first()
                )
                if exists:
                    continue
                s.add(
                    UserRoleEntity(
                        user_id=uid,
                        role_id=role_ids[role_name],
                        scope_id=m.workspace_id,
                    )
                )
                created += 1
            if created:
                s.commit()
                logger.info(
                    "migrate_space_role_bindings: created %d scoped bindings", created
                )
    except Exception as e:  # noqa: BLE001
        logger.warning("migrate_space_role_bindings failed: %s", e)


def sync_permission_definitions() -> None:
    """把代码注册的权限协议（PermissionRegistry）同步到 permission_definition 表。

    幂等 upsert（以 name=permission key 为准）；代码中已删除的 key 不删库行
    （避免误删管理员自定义引用），仅日志提示。
    """
    from gyra_serve.permissions import PermissionRegistry, parse_key

    dao = PermissionDao()
    existing = {d["name"]: d for d in dao.list_permission_definitions()}

    created = updated = 0
    for perm in PermissionRegistry.all():
        resource_type, action = parse_key(perm.key)
        description = f"{perm.name}｜{perm.description}" if perm.description else perm.name
        row = existing.get(perm.key)
        if row is None:
            dao.create_permission_definition(
                name=perm.key,
                resource_type=resource_type,
                action=action,
                resource_id="*",
                effect="allow",
                description=description,
                scope_type=perm.scope_type,
                grantable=perm.grantable,
            )
            created += 1
        elif (
            row.get("scope_type") != perm.scope_type
            or bool(row.get("grantable")) != perm.grantable
            or row.get("description") != description
        ):
            dao.update_permission_definition(
                definition_id=row["id"],
                description=description,
                scope_type=perm.scope_type,
                grantable=perm.grantable,
            )
            updated += 1

    logger.info(
        "Permission registry synced: %d keys (%d created, %d updated)",
        len(PermissionRegistry.keys()), created, updated,
    )

    # 失效定义清理:不在注册表、且无任何角色 permission-defs 引用的存量行
    # (如旧版蛇形命名 agent_admin_all 的重复定义)置 is_active=0。
    # 不物理删除,保留历史痕迹;有引用的行不动。
    from gyra.storage.metadata.db_manager import db

    from .models import RolePermissionDefEntity

    registered_names = set(PermissionRegistry.keys())
    referenced_def_ids = set()
    with db.session(commit=False) as s:
        for (def_id,) in s.query(RolePermissionDefEntity.permission_def_id).distinct():
            referenced_def_ids.add(def_id)
    deactivated = 0
    for row in dao.list_permission_definitions(is_active=True):
        if row["name"] in registered_names or row["id"] in referenced_def_ids:
            continue
        dao.update_permission_definition(definition_id=row["id"], is_active=False)
        deactivated += 1
    if deactivated:
        logger.info("Deactivated %d stale permission definitions", deactivated)


def migrate_ecp_confirmers() -> None:
    """One-time migration: sync ECP 提案确认人名单与空间成员一致。

    历史问题:建空间时仅 owner 写入确认白名单,其他成员在待办里能看到提案
    却无法确认;旧 mock 用户(owner_user_id=0)还会留下 user_id="0" 的陈旧
    确认人记录,导致名单非空却无任何真实用户命中 —— 所有用户都失去提案
    确认权限。本迁移(幂等,每次启动兜底执行):
    - 把每个场景空间的全体成员补入其派生 ECP 空间的确认人名单(成员默认可确认);
    - 清除陈旧 "0" 确认人记录(open bootstrap 场景保持为空)。
    """
    global _ecp_confirmer_migration_done
    if _ecp_confirmer_migration_done:
        return
    _ecp_confirmer_migration_done = True

    try:
        from gyra.storage.metadata.db_manager import db
        from gyra_serve.ecp.models.models import EcpConfirmerEntity
        from gyra_serve.workspace.ecp_derive import derived_ecp_workspace_id
        from gyra_serve.workspace.models.models import (
            WorkspaceEntity,
            WorkspaceMemberEntity,
        )

        with db.session(commit=False) as s:
            workspaces = s.query(WorkspaceEntity).all()
            member_rows = s.query(WorkspaceMemberEntity).all()
            members_by_ws: dict = {}
            for m in member_rows:
                members_by_ws.setdefault(m.workspace_id, []).append(m.user_id)
            changed = 0
            for w in workspaces:
                if not w.workspace_code:
                    continue
                ecp_ws = derived_ecp_workspace_id(w.workspace_code)
                # 1. 清除陈旧 mock 确认人记录
                removed = (
                    s.query(EcpConfirmerEntity)
                    .filter(
                        EcpConfirmerEntity.workspace_id == ecp_ws,
                        EcpConfirmerEntity.user_id == "0",
                    )
                    .delete(synchronize_session=False)
                )
                changed += removed
                # 2. 全体成员补入名单(幂等;owner 也是成员,天然在名单内)
                member_ids = members_by_ws.get(w.id, [])
                if w.owner_user_id is not None and w.owner_user_id not in member_ids:
                    member_ids = list(member_ids) + [w.owner_user_id]
                if not member_ids:
                    continue
                existing = {
                    r.user_id
                    for r in s.query(EcpConfirmerEntity)
                    .filter(EcpConfirmerEntity.workspace_id == ecp_ws)
                    .all()
                }
                for uid in member_ids:
                    uid_str = str(uid)
                    if uid_str != "0" and uid_str not in existing:
                        s.add(
                            EcpConfirmerEntity(
                                workspace_id=ecp_ws, user_id=uid_str, scope=None
                            )
                        )
                        changed += 1
            if changed:
                s.commit()
                logger.info(
                    "migrate_ecp_confirmers: fixed %d confirmer entries",
                    changed,
                )
            else:
                logger.debug("migrate_ecp_confirmers: nothing to fix")

    except Exception as e:
        logger.warning(f"migrate_ecp_confirmers: migration failed: {e}")


def migrate_workspace_owners() -> None:
    """One-time migration: mock 用户(owner_user_id=0)创建的空间迁移给 admin。

    登录未开启时,前端用 mock 用户身份(user_no="0")建空间,owner 记录为 0。
    开启系统登录后 admin 是真实 DB 用户,而 workspace 列表按成员过滤,
    导致这些空间在 admin 名下不可见。本迁移把这些空间的 owner 和成员记录
    一并转移给第一个 admin 用户,使其成为正式 owner(配合列表 admin 绕过)。
    """
    global _workspace_migration_done
    if _workspace_migration_done:
        return
    _workspace_migration_done = True

    try:
        from gyra_app.auth.user_service import UserEntity
        from gyra.storage.metadata.db_manager import db
        from gyra_serve.workspace.models.models import (
            WorkspaceEntity,
            WorkspaceMemberEntity,
        )

        with db.session(commit=False) as s:
            # 找到第一个 admin 用户作为空间归属目标
            admin_user = (
                s.query(UserEntity)
                .filter(UserEntity.name == "admin")
                .first()
            )
            if not admin_user:
                logger.debug("migrate_workspace_owners: no admin user found, skip")
                return
            admin_id = admin_user.id

            migrated_ws = 0
            migrated_members = 0

            # 1. mock 用户(owner_user_id=0)拥有的空间 -> owner 改给 admin
            mock_ws = (
                s.query(WorkspaceEntity)
                .filter(WorkspaceEntity.owner_user_id == 0)
                .all()
            )
            mock_ws_ids = [w.id for w in mock_ws]
            for w in mock_ws:
                w.owner_user_id = admin_id
                migrated_ws += 1

            # 2. 这些空间里 user_id=0 的成员记录 -> 改给 admin(避免 owner 无成员记录)
            if mock_ws_ids:
                mock_members = (
                    s.query(WorkspaceMemberEntity)
                    .filter(
                        WorkspaceMemberEntity.workspace_id.in_(mock_ws_ids),
                        WorkspaceMemberEntity.user_id == 0,
                    )
                    .all()
                )
                for m in mock_members:
                    existing = (
                        s.query(WorkspaceMemberEntity)
                        .filter(
                            WorkspaceMemberEntity.workspace_id == m.workspace_id,
                            WorkspaceMemberEntity.user_id == admin_id,
                        )
                        .first()
                    )
                    if existing:
                        # admin 已是成员:owner 记录保留,删掉 mock 冗余成员行
                        if m.role == "owner" and existing.role not in ("owner", "admin"):
                            existing.role = "owner"
                        s.delete(m)
                    else:
                        m.user_id = admin_id
                    migrated_members += 1

            if migrated_ws or migrated_members:
                s.commit()
                logger.info(
                    "migrate_workspace_owners: migrated %d workspaces and "
                    "%d member records from mock user(0) to admin user id=%s",
                    migrated_ws, migrated_members, admin_id,
                )
            else:
                logger.debug("migrate_workspace_owners: no workspaces owned by mock user")

    except Exception as e:
        logger.warning(f"migrate_workspace_owners: migration failed: {e}")


def migrate_conversation_user_names() -> None:
    """One-time migration: update conversation user_name from old mock IDs (e.g. '001')
    to the actual username so conversations remain visible after enabling auth.

    When auth was OFF, all conversations were stored with user_name='001' (the mock
    admin ID). After enabling auth, user_id becomes the username (e.g. 'admin'), so
    old conversations become invisible. This migration rewrites those old records.
    """
    global _migration_done
    if _migration_done:
        return
    _migration_done = True

    try:
        from gyra_app.auth.user_service import UserEntity
        from gyra.storage.metadata.db_manager import db

        with db.session(commit=False) as s:
            # Find the first admin user to map old conversations to
            admin_user = (
                s.query(UserEntity)
                .filter(UserEntity.name == "admin")
                .first()
            )
            if not admin_user:
                logger.debug("migrate_conversation_user_names: no admin user found, skip")
                return

            admin_name = admin_user.name  # "admin"

            # Build mapping of old mock user IDs to the admin username
            old_mock_ids = ["001"]
            updated_total = 0

            # 1. Migrate chat_history table (V1)
            try:
                from gyra.storage.chat_history.chat_history_db import ChatHistoryEntity

                for old_id in old_mock_ids:
                    count = (
                        s.query(ChatHistoryEntity)
                        .filter(ChatHistoryEntity.user_name == old_id)
                        .update({ChatHistoryEntity.user_name: admin_name},
                                synchronize_session="fetch")
                    )
                    if count:
                        logger.info(
                            "migrate_conversation_user_names: updated %d chat_history "
                            "rows from user_name='%s' to '%s'",
                            count, old_id, admin_name,
                        )
                        updated_total += count
            except Exception as e:
                logger.warning("migrate_conversation_user_names: chat_history migration failed: %s", e)

            # 2. Migrate gpts_conversations table (V2)
            try:
                from gyra_serve.agent.db.gpts_conversations_db import GptsConversationsEntity

                for old_id in old_mock_ids:
                    count = (
                        s.query(GptsConversationsEntity)
                        .filter(GptsConversationsEntity.user_code == old_id)
                        .update({GptsConversationsEntity.user_code: admin_name},
                                synchronize_session="fetch")
                    )
                    if count:
                        logger.info(
                            "migrate_conversation_user_names: updated %d gpts_conversations "
                            "rows from user_code='%s' to '%s'",
                            count, old_id, admin_name,
                        )
                        updated_total += count
            except Exception as e:
                logger.warning("migrate_conversation_user_names: gpts_conversations migration failed: %s", e)

            if updated_total:
                s.commit()
                logger.info(
                    "migrate_conversation_user_names: total %d rows migrated", updated_total
                )
            else:
                logger.debug("migrate_conversation_user_names: no rows need migration")

    except Exception as e:
        logger.warning("migrate_conversation_user_names: migration failed: %s", e)
