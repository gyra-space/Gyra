"""RBAC-backed PermissionProvider for SQL Guard.

将 gyra_serve.permissions 的 RBAC 判定接入 SQL Guard 的表/列级权限检查。
资源 ID 编码规则:
    database:{ds_id}           → 数据源级(全部表)
    database:{ds_id}.{table}   → 表级
    database:{ds_id}.{table}.{column} → 列级(预留)
"""

import logging
from typing import List, Optional

from gyra_serve.sql_guard.models import SQLType
from gyra_serve.sql_guard.rules.permission_rules import PermissionProvider

logger = logging.getLogger(__name__)

# SQL 操作 → 权限动作映射
_OP_TO_ACTION = {
    SQLType.SELECT.value: "read",
    SQLType.SHOW.value: "read",
    SQLType.DESCRIBE.value: "read",
    SQLType.EXPLAIN.value: "read",
    SQLType.WITH.value: "read",
    SQLType.INSERT.value: "manage",
    SQLType.UPDATE.value: "manage",
    SQLType.DELETE.value: "manage",
    SQLType.DDL.value: "manage",
    SQLType.DCL.value: "manage",
    SQLType.UNKNOWN.value: "read",
}


class RbacPermissionProvider(PermissionProvider):
    """基于 gyra RBAC 的表/列级权限 Provider。

    判定逻辑完全复用 gyra_serve.permissions.check.has():
      1. 管理员短路(superadmin/admin)
      2. 角色权限: 精确 resource_id → 通配回退
      3. 资源实例级 grant(resource_grant 表)
      4. 未命中 → 拒绝
    """

    def __init__(self, user=None):
        """构造 Provider。

        Args:
            user: gyra_serve.utils.auth.UserRequest 实例。
                  为 None 时 provider 进入"无用户"模式, 所有检查放行
                  (兼容开发模式/未认证场景)。
        """
        self._user = user
        self._enabled = user is not None and user.permissions is not None
        if not self._enabled:
            logger.debug(
                "[RbacPermissionProvider] no user or permissions disabled, "
                "all checks will pass"
            )

    # ------------------------------------------------------------------ #
    # PermissionProvider 接口实现
    # ------------------------------------------------------------------ #

    def check_table_access(
        self,
        user_id: str,
        datasource_id: int,
        table_name: str,
        operation: str,
    ) -> bool:
        if not self._enabled:
            return True

        action = _OP_TO_ACTION.get(operation, "read")

        # deny 优先于逐级 allow:先查表级/数据源级的显式 deny——
        # 否则"通配 allow + 单表 deny"会在回退到上级 allow 时放行
        ds = str(datasource_id)
        for deny_key in (f"database:{ds}.{table_name}", f"database:{ds}"):
            if self._is_denied(deny_key, action):
                logger.info(
                    f"[RbacPermissionProvider] denied by {deny_key}: user={user_id}"
                )
                return False

        # 逐级回退: ds_id.table → ds_id → *
        for rid in self._candidate_resource_ids(datasource_id, table_name):
            if self._has(f"database.{action}", resource_id=rid):
                return True

        # admin 动作覆盖(拥有 database.admin 即所有表可读写)
        if self._has("database.admin"):
            return True

        logger.info(
            f"[RbacPermissionProvider] denied: user={user_id} "
            f"ds={datasource_id} table={table_name} op={operation}"
        )
        return False

    def check_column_access(
        self,
        user_id: str,
        datasource_id: int,
        table_name: str,
        column_names: List[str],
    ) -> List[str]:
        """列级权限检查:返回被 deny 的列名列表。

        列维度只做"否决"(敏感列场景):角色权限 effect=deny 且
        resource_id = "{ds_id}.{table}.{column}" 时该列被拦截;
        无任何 deny 记录则全部放行(表级放行由 check_table_access 保证)。

        判定直接读 deny_map——不能用 has():列级没有 allow 语义,
        has() 对无显式授权的列一律 False,会把所有列都误判为拒绝。
        """
        if not self._enabled:
            return []

        deny_map = getattr(self._user, "deny_permissions", None) or {}
        denied: List[str] = []
        for col in column_names:
            rid = f"database:{datasource_id}.{table_name}.{col}"
            actions = deny_map.get(rid, [])
            if "read" in actions or "manage" in actions or "admin" in actions:
                denied.append(col)

        if denied:
            logger.info(
                f"[RbacPermissionProvider] denied columns {denied}: user={user_id} "
                f"ds={datasource_id} table={table_name}"
            )
        return denied

    def get_allowed_tables(
        self,
        user_id: str,
        datasource_id: int,
    ) -> Optional[List[str]]:
        """返回用户可访问的表白名单。

        None = 无限制; [] = 无任何权限; [...] = 白名单。
        此接口用于 SQL 重写(如自动加 WHERE 过滤),当前实现返回 None,
        实际拦截在 check_table_access 中完成。
        """
        return None

    def get_row_filter(
        self,
        user_id: str,
        datasource_id: int,
        table_name: str,
    ) -> Optional[str]:
        """行级过滤条件(预留)。

        当前 RBAC 未定义行级权限,返回 None。
        """
        return None

    # ------------------------------------------------------------------ #
    # 内部: RBAC 判定
    # ------------------------------------------------------------------ #

    def _has(self, permission_key: str, resource_id: Optional[str] = None) -> bool:
        """调用统一权限判定入口。"""
        try:
            from gyra_serve.permissions.check import has

            return has(self._user, permission_key, resource_id=resource_id)
        except Exception as e:
            # fail-open: 权限服务异常时不阻断 SQL 执行
            # (与 _db_tools_impl.py 中 ECP gate 的 fail-open 策略一致)
            logger.warning(f"[RbacPermissionProvider] has() failed, allow: {e}")
            return True

    def _is_denied(self, scoped_key: str, action: str) -> bool:
        """查 deny_map 中指定 scoped key 是否 deny 该动作(含 admin 覆盖)。"""
        deny_map = getattr(self._user, "deny_permissions", None) or {}
        actions = deny_map.get(scoped_key, [])
        return action in actions or "admin" in actions

    @staticmethod
    def _candidate_resource_ids(datasource_id: int, table_name: str) -> List[str]:
        """生成逐级回退的 resource_id 候选列表。"""
        ds = str(datasource_id)
        return [
            f"{ds}.{table_name}",  # 表级
            ds,                     # 数据源级
            "*",                    # 全局通配
        ]
