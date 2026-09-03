"""RBAC 管理 Agent 工具 —— 把用户/角色/分组/授权的运维操作资产化为 Agent 工具。

定位:薄封装层。内部直接复用 ``PermissionDao`` / ``PermissionService`` /
``UserService`` / ``UserGroupService``(与 REST API 同一数据通路),不走 HTTP。

安全模型(fail-closed):
- 每个工具从 ``ToolContext`` 取提问者的 ``user_request``
  (由 V2 tool_context_factory 注入,见 gyra.agent.core.v2.tool_context_factory);
- 取不到 → 拒绝(不允许无身份执行管理操作);
- 有身份但没有 ``system.admin`` 权限(与 ``require_admin`` 同一判定,
  走 gyra_serve.permissions.has)→ 拒绝;
- 写操作统一记结构化日志(operator + 操作 + 关键参数),成功后清权限缓存。

Excel 批量注册场景:Agent 用既有文件读取能力解析表格后,把行数组传给
``rbac_batch_create_users``(默认 dry_run=true 先预览,确认后再执行)。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from gyra.agent.tools.base import ToolCategory, ToolRiskLevel, ToolSource
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.decorators import tool

from gyra_app.feature_plugins.permissions.dao import PermissionDao
from gyra_app.feature_plugins.permissions.service import PermissionService
from gyra_app.feature_plugins.user_groups.service import UserGroupService

logger = logging.getLogger(__name__)

_ADMIN_PERMISSION_KEY = "system.admin"

_dao = PermissionDao()
_svc = PermissionService()
_group_svc = UserGroupService()


# --------------------------------------------------------------------------- #
# 守卫与工具函数
# --------------------------------------------------------------------------- #
def _deny(reason: str) -> Dict[str, Any]:
    return {"success": False, "error": reason, "code": "PERMISSION_DENIED"}


def _get_user_request(context: Optional[ToolContext]):
    if context is None:
        return None
    return context.get_resource("user_request") or context.config.get("user_request")


def _require_admin(context: Optional[ToolContext]):
    """返回 (user_request, None) 或 (None, deny_result)。fail-closed。"""
    user_request = _get_user_request(context)
    if user_request is None:
        return None, _deny(
            "无法确认操作者身份(缺少用户上下文),拒绝执行 RBAC 管理操作"
        )
    from gyra_serve.permissions import has as has_permission

    if not has_permission(user_request, _ADMIN_PERMISSION_KEY):
        name = getattr(user_request, "user_name", None) or "unknown"
        return None, _deny(
            f"用户 {name} 没有系统管理权限({_ADMIN_PERMISSION_KEY}),拒绝执行"
        )
    return user_request, None


def _operator_name(user_request) -> str:
    return (
        getattr(user_request, "user_name", None)
        or getattr(user_request, "real_name", None)
        or "unknown"
    )


def _audit(op: str, operator: str, **params: Any) -> None:
    logger.info("RBAC-ADMIN op=%s operator=%s params=%s", op, operator, params)


def _get_user_service():
    from gyra_app.auth.user_service import UserService

    return UserService()


def _resolve_role_by_name(role_name: str) -> Optional[Dict[str, Any]]:
    return _dao.get_role_by_name(role_name.strip())


def _parse_permission_item(p: Any) -> Optional[Dict[str, Any]]:
    """把权限项规范化为 ``{resource_type, action, resource_id, effect}``。

    Agent/LLM 传参有歧义，可能为三种形态：
    - dict ``{"resource_type": "agent", "action": "admin"}``（约定格式）；
    - dict ``{"key": "agent.admin"}``（来自 ``rbac_list_permission_definitions`` 的 key）；
    - 直接字符串 ``"agent.admin"``（同上，LLM 常把 key 当字符串传）。

    统一经 ``parse_key`` 解析为存量存储格式 ``(resource_type, action)``，
    ``resource_id`` 缺省 ``*``、``effect`` 缺省 ``allow``。解析失败返回 None
    （由调用方跳过并记录原因），避免 ``'str' object has no attribute 'get'``。
    """
    if isinstance(p, dict):
        rt = p.get("resource_type")
        act = p.get("action")
        if not rt and p.get("key"):
            try:
                from gyra_serve.permissions import parse_key
                rt, act = parse_key(str(p["key"]))
            except (ValueError, TypeError):
                return None
        if not rt or not act:
            return None
        return {
            "resource_type": str(rt),
            "action": str(act),
            "resource_id": p.get("resource_id") or "*",
            "effect": p.get("effect") or "allow",
        }
    if isinstance(p, str) and p.strip():
        try:
            from gyra_serve.permissions import parse_key
            rt, act = parse_key(p.strip())
        except (ValueError, TypeError):
            return None
        return {
            "resource_type": rt,
            "action": act,
            "resource_id": "*",
            "effect": "allow",
        }
    return None


# --------------------------------------------------------------------------- #
# 读类工具(safe)
# --------------------------------------------------------------------------- #
@tool(
    "rbac_list_users",
    description="列出系统用户(分页+关键词搜索),附带每个用户的角色名列表",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_list_users(
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """列出系统用户。

    Args:
        keyword: 搜索关键词(匹配用户名/姓名/邮箱/ID),空为全部
        page: 页码,从 1 开始
        page_size: 每页条数,最大 100
    """
    _, err = _require_admin(context)
    if err:
        return err
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    users, total = _get_user_service().list_users(
        page=page, page_size=page_size, keyword=keyword
    )
    items = [
        {
            "id": u["id"],
            "name": u["name"],
            "fullname": u["fullname"],
            "email": u["email"],
            "is_active": u["is_active"],
            "roles": [r["name"] for r in _dao.get_user_roles(u["id"])],
            "gmt_create": u["gmt_create"],
        }
        for u in users
    ]
    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tool(
    "rbac_get_user_detail",
    description="查看用户详情:直接角色、用户组继承角色、聚合成效权限、实例级授权",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_get_user_detail(
    user_id: int, context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """查看单个用户的权限全貌。

    Args:
        user_id: 用户 ID(数字)
    """
    _, err = _require_admin(context)
    if err:
        return err
    user = _get_user_service().get_user(user_id)
    if not user:
        return {"success": False, "error": f"用户 {user_id} 不存在", "code": "NOT_FOUND"}
    perms = _svc.get_user_permissions(user_id)
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "fullname": user["fullname"],
            "email": user["email"],
            "is_active": user["is_active"],
        },
        "direct_roles": [r["name"] for r in _dao.get_user_roles(user_id)],
        "group_roles": [r["name"] for r in _dao.get_user_group_roles(user_id)],
        "all_roles": perms.role_names,
        "effective_permissions": perms.permissions_map,
        "grants": perms.grants,
    }


@tool(
    "rbac_list_roles",
    description="列出全部角色及其权限明细(资源类型/动作/范围)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_list_roles(context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """列出全部角色,每个角色附带权限明细。"""
    _, err = _require_admin(context)
    if err:
        return err
    roles = []
    for r in _dao.list_roles():
        perms = _dao.list_role_permissions(r["id"])
        roles.append(
            {
                **r,
                "permissions": [
                    {
                        "resource_type": p["resource_type"],
                        "resource_id": p["resource_id"],
                        "action": p["action"],
                        "effect": p["effect"],
                    }
                    for p in perms
                ],
            }
        )
    return {"success": True, "items": roles, "total": len(roles)}


@tool(
    "rbac_list_groups",
    description="列出全部用户组,附带成员数量和组绑定角色",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_list_groups(context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """列出全部用户组(含成员数、绑定角色)。"""
    _, err = _require_admin(context)
    if err:
        return err
    items = []
    for g in _group_svc.list_groups():
        items.append(
            {
                **g,
                "member_count": _group_svc.count_members(g["id"]),
                "roles": [
                    r["role_name"] for r in _dao.list_group_role_assignments(g["id"])
                ],
            }
        )
    return {"success": True, "items": items, "total": len(items)}


@tool(
    "rbac_get_group",
    description="查看用户组详情:成员列表与绑定角色",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_get_group(
    group_id: int, context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """查看用户组详情。

    Args:
        group_id: 用户组 ID
    """
    _, err = _require_admin(context)
    if err:
        return err
    group = _group_svc.get_group(group_id)
    if not group:
        return {"success": False, "error": f"用户组 {group_id} 不存在", "code": "NOT_FOUND"}
    return {
        "success": True,
        "group": group,
        "members": _group_svc.list_members(group_id),
        "roles": _dao.list_group_role_assignments(group_id),
    }


@tool(
    "rbac_list_permission_definitions",
    description="列出系统中所有已注册的权限定义(权限目录),含 key/名称/风险等级/是否可实例级授权",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_list_permission_definitions(
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """列出权限目录(代码注册的单一事实来源)。"""
    _, err = _require_admin(context)
    if err:
        return err
    from gyra_serve.permissions import PermissionRegistry

    items = [
        {
            "key": p.key,
            "name": p.name,
            "description": p.description,
            "scope_type": p.scope_type,
            "grantable": p.grantable,
            "risk_level": p.risk_level,
        }
        for p in PermissionRegistry.all()
    ]
    return {"success": True, "items": items, "total": len(items)}


@tool(
    "rbac_list_grants",
    description="列出资源实例级授权(resource_grant),可按用户或资源类型过滤",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.SAFE,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "read"],
)
def rbac_list_grants(
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """列出实例级授权。

    Args:
        user_id: 按用户过滤,空为全部
        resource_type: 按资源类型过滤(如 agent/database),空为全部
    """
    _, err = _require_admin(context)
    if err:
        return err
    grants = _dao.list_grants(user_id=user_id, resource_type=resource_type)
    return {"success": True, "items": grants, "total": len(grants)}


# --------------------------------------------------------------------------- #
# 写类工具(medium/high,ask_user 确认)
# --------------------------------------------------------------------------- #
def _create_user_with_roles(
    username: str,
    password: str,
    email: str,
    fullname: str,
    role_names: List[str],
) -> Dict[str, Any]:
    """创建用户并按角色名挂角色。未知角色名会报错且不静默跳过。"""
    username = (username or "").strip()
    if len(username) < 2:
        return {"success": False, "error": f"用户名 {username!r} 太短(至少 2 字符)"}
    if not password or len(password) < 6:
        return {"success": False, "error": f"用户 {username} 的密码至少 6 位"}

    role_ids, unknown = [], []
    for rn in role_names or []:
        role = _resolve_role_by_name(rn)
        if role:
            role_ids.append(role["id"])
        else:
            unknown.append(rn)
    if unknown:
        return {
            "success": False,
            "error": f"角色不存在: {unknown}(可用 rbac_list_roles 查看全部角色)",
        }

    user = _get_user_service().create_local_user(
        username=username,
        password=password,
        email=email or "",
        fullname=fullname or "",
        rbac_default_role="guest",
    )
    if not user:
        return {"success": False, "error": f"用户名 {username} 已存在"}

    for rid in role_ids:
        _dao.assign_role_to_user(user["id"], rid)
    _svc.invalidate_cache(user["id"])
    return {
        "success": True,
        "user_id": user["id"],
        "username": username,
        "assigned_roles": role_names or [],
    }


@tool(
    "rbac_create_user",
    description="创建本地用户(用户名/密码),可按角色名直接分配角色",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_create_user(
    username: str,
    password: str,
    email: str = "",
    fullname: str = "",
    role_names: Optional[List[str]] = None,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """创建本地用户。

    Args:
        username: 登录用户名(2-50 字符)
        password: 初始密码(至少 6 位)
        email: 邮箱,可空
        fullname: 姓名,可空
        role_names: 要分配的角色名列表(按名称,如 ["viewer"]),可空
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    result = _create_user_with_roles(
        username, password, email, fullname, role_names or []
    )
    _audit("rbac_create_user", _operator_name(user_request), username=username,
           role_names=role_names, ok=result["success"])
    return result


@tool(
    "rbac_batch_create_users",
    description="批量创建用户(如 Excel 导入场景)。默认 dry_run=true 只做逐行校验预览不写库;确认无误后传 dry_run=false 执行",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.HIGH,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write", "batch"],
    ask_user=True,
)
def rbac_batch_create_users(
    users: List[Dict[str, Any]],
    default_password: str = "",
    dry_run: bool = True,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """批量创建用户。

    Args:
        users: 用户行数组,每行 {"username": 必填, "password": 可空, "email": 可空,
               "fullname": 可空, "role_names": 可空列表}
        default_password: 行内未给密码时使用的统一初始密码
        dry_run: true=只预览不写库(默认);false=真正执行
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    if not users:
        return {"success": False, "error": "users 为空"}
    if len(users) > 500:
        return {"success": False, "error": "单次最多 500 行"}

    from gyra_app.auth.user_service import UserDao

    user_dao = UserDao()
    preview = []
    for i, row in enumerate(users):
        username = str(row.get("username") or "").strip()
        password = row.get("password") or default_password
        role_names = row.get("role_names") or []
        problems = []
        if len(username) < 2:
            problems.append("用户名缺失或太短")
        elif user_dao.get_by_username(username):
            problems.append("用户名已存在")
        if not password or len(password) < 6:
            problems.append("密码缺失或少于 6 位")
        unknown = [rn for rn in role_names if not _resolve_role_by_name(rn)]
        if unknown:
            problems.append(f"角色不存在: {unknown}")
        preview.append(
            {
                "row": i + 1,
                "username": username,
                "role_names": role_names,
                "ok": not problems,
                "problems": problems,
            }
        )

    ok_count = sum(1 for p in preview if p["ok"])
    summary = {"total": len(preview), "ok": ok_count, "failed": len(preview) - ok_count}
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "summary": summary,
            "preview": preview,
            "hint": "确认无误后用相同参数并 dry_run=false 执行",
        }

    results = []
    for row, p in zip(users, preview):
        if not p["ok"]:
            results.append({**p, "created": False})
            continue
        r = _create_user_with_roles(
            username=str(row.get("username") or "").strip(),
            password=row.get("password") or default_password,
            email=row.get("email") or "",
            fullname=row.get("fullname") or "",
            role_names=row.get("role_names") or [],
        )
        results.append({**p, "created": r["success"], "detail": r})
    created = sum(1 for r in results if r["created"])
    _audit("rbac_batch_create_users", _operator_name(user_request),
           total=len(users), created=created)
    return {
        "success": True,
        "dry_run": False,
        "summary": {**summary, "created": created},
        "results": results,
    }


@tool(
    "rbac_create_role",
    description="创建角色",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_create_role(
    name: str,
    description: str = "",
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """创建角色。

    Args:
        name: 角色名(唯一)
        description: 角色说明
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    if _resolve_role_by_name(name):
        return {"success": False, "error": f"角色 {name} 已存在"}
    role = _dao.create_role(name=name, description=description or None)
    _audit("rbac_create_role", _operator_name(user_request), name=name)
    return {"success": True, "role": role}


@tool(
    "rbac_update_role",
    description="更新角色名或说明(系统内置角色只读,不可改)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_update_role(
    role_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """更新角色。

    Args:
        role_id: 角色 ID
        name: 新角色名,可空(不改)
        description: 新说明,可空(不改)
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    role = _dao.get_role(role_id)
    if not role:
        return {"success": False, "error": f"角色 {role_id} 不存在", "code": "NOT_FOUND"}
    if role.get("is_system") == 1:
        return {"success": False, "error": "系统内置角色只读,不可修改"}
    updated = _dao.update_role(role_id, name=name, description=description)
    _svc.invalidate_cache()
    _audit("rbac_update_role", _operator_name(user_request), role_id=role_id)
    return {"success": True, "role": updated}


@tool(
    "rbac_delete_role",
    description="删除角色(级联清理角色权限/用户绑定/组绑定;系统内置角色不可删)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.HIGH,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write", "dangerous"],
    ask_user=True,
)
def rbac_delete_role(
    role_id: int, context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """删除角色。

    Args:
        role_id: 角色 ID
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    role = _dao.get_role(role_id)
    if not role:
        return {"success": False, "error": f"角色 {role_id} 不存在", "code": "NOT_FOUND"}
    if role.get("is_system") == 1:
        return {"success": False, "error": "系统内置角色不可删除"}
    _dao.delete_role(role_id)
    _svc.invalidate_cache()
    _audit("rbac_delete_role", _operator_name(user_request),
           role_id=role_id, role_name=role["name"])
    return {"success": True, "deleted_role": role["name"]}


@tool(
    "rbac_set_role_permissions",
    description="给角色添加或移除权限项(按 resource_type/action/resource_id)。先用 rbac_list_permission_definitions 查可用权限",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.HIGH,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_set_role_permissions(
    role_id: int,
    permissions: List[Dict[str, Any]],
    mode: str = "add",
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """批量增/删角色权限。

    Args:
        role_id: 角色 ID
        permissions: 权限项数组,每项 {"resource_type": 如 "agent", "action": 如 "chat",
                     "resource_id": 默认 "*", "effect": 默认 "allow"}
        mode: "add"=添加(幂等) 或 "remove"=移除
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    role = _dao.get_role(role_id)
    if not role:
        return {"success": False, "error": f"角色 {role_id} 不存在", "code": "NOT_FOUND"}
    if role.get("is_system") == 1:
        return {"success": False, "error": "系统内置角色只读,不可改权限"}
    if mode not in ("add", "remove"):
        return {"success": False, "error": "mode 必须是 add 或 remove"}
    if not permissions:
        return {"success": False, "error": "permissions 为空"}
    if not isinstance(permissions, list):
        return {"success": False, "error": "permissions 必须是数组"}

    applied, skipped = [], []
    for p in permissions:
        norm = _parse_permission_item(p)
        if norm is None:
            skipped.append({
                "item": p,
                "reason": "权限项格式非法(需 {resource_type, action} 或 'resource_type.action' 字符串)",
            })
            continue
        rt, act = norm["resource_type"], norm["action"]
        rid, effect = norm["resource_id"], norm["effect"]
        if mode == "add":
            _dao.add_role_permission(
                role_id=role_id,
                resource_type=rt,
                action=act,
                resource_id=rid,
                effect=effect,
            )
            applied.append({"resource_type": rt, "action": act, "resource_id": rid})
        else:
            matched = [
                ep for ep in _dao.list_role_permissions(role_id)
                if ep["resource_type"] == rt and ep["action"] == act
                and ep["resource_id"] == rid
            ]
            if not matched:
                skipped.append({"item": p, "reason": "权限项不存在"})
                continue
            for ep in matched:
                _dao.remove_role_permission(ep["id"])
            applied.append({"resource_type": rt, "action": act, "resource_id": rid})

    _svc.invalidate_cache()
    _audit("rbac_set_role_permissions", _operator_name(user_request),
           role_id=role_id, mode=mode, applied=len(applied))
    return {
        "success": True,
        "role": role["name"],
        "mode": mode,
        "applied": applied,
        "skipped": skipped,
    }


@tool(
    "rbac_assign_role",
    description="按角色名把角色分配给用户或用户组(二选一)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_assign_role(
    role_name: str,
    user_id: Optional[int] = None,
    group_id: Optional[int] = None,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """分配角色。

    Args:
        role_name: 角色名(按名称,用 rbac_list_roles 可查)
        user_id: 目标用户 ID(与 group_id 二选一)
        group_id: 目标用户组 ID(与 user_id 二选一)
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    if (user_id is None) == (group_id is None):
        return {"success": False, "error": "user_id 和 group_id 必须且只能给一个"}
    role = _resolve_role_by_name(role_name)
    if not role:
        return {"success": False, "error": f"角色 {role_name} 不存在"}

    if user_id is not None:
        if not _get_user_service().get_user(user_id):
            return {"success": False, "error": f"用户 {user_id} 不存在", "code": "NOT_FOUND"}
        _dao.assign_role_to_user(user_id, role["id"])
        _svc.invalidate_cache(user_id)
        target = {"user_id": user_id}
    else:
        if not _group_svc.get_group(group_id):
            return {"success": False, "error": f"用户组 {group_id} 不存在", "code": "NOT_FOUND"}
        _dao.assign_role_to_group(group_id, role["id"])
        _svc.invalidate_cache()
        target = {"group_id": group_id}

    _audit("rbac_assign_role", _operator_name(user_request),
           role_name=role_name, **target)
    return {"success": True, "role": role["name"], **target}


@tool(
    "rbac_remove_role",
    description="按角色名从用户或用户组移除角色(二选一)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_remove_role(
    role_name: str,
    user_id: Optional[int] = None,
    group_id: Optional[int] = None,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """移除角色。

    Args:
        role_name: 角色名
        user_id: 目标用户 ID(与 group_id 二选一)
        group_id: 目标用户组 ID(与 user_id 二选一)
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    if (user_id is None) == (group_id is None):
        return {"success": False, "error": "user_id 和 group_id 必须且只能给一个"}
    role = _resolve_role_by_name(role_name)
    if not role:
        return {"success": False, "error": f"角色 {role_name} 不存在"}

    if user_id is not None:
        removed = _dao.remove_user_role(user_id, role["id"])
        _svc.invalidate_cache(user_id)
        target = {"user_id": user_id}
    else:
        removed = _dao.remove_group_role(group_id, role["id"])
        _svc.invalidate_cache()
        target = {"group_id": group_id}
    if not removed:
        return {"success": False, "error": "该绑定不存在", **target}

    _audit("rbac_remove_role", _operator_name(user_request),
           role_name=role_name, **target)
    return {"success": True, "removed_role": role["name"], **target}


@tool(
    "rbac_create_group",
    description="创建用户组",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_create_group(
    name: str,
    description: str = "",
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """创建用户组。

    Args:
        name: 组名
        description: 组说明
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    group = _group_svc.create_group(name=name, description=description or None)
    _audit("rbac_create_group", _operator_name(user_request), name=name)
    return {"success": True, "group": group}


@tool(
    "rbac_add_group_members",
    description="把一批用户加入用户组(已在组内的自动跳过)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.MEDIUM,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_add_group_members(
    group_id: int,
    user_ids: List[int],
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """批量加组成员。

    Args:
        group_id: 用户组 ID
        user_ids: 用户 ID 数组
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    if not _group_svc.get_group(group_id):
        return {"success": False, "error": f"用户组 {group_id} 不存在", "code": "NOT_FOUND"}
    if not user_ids:
        return {"success": False, "error": "user_ids 为空"}
    svc = _get_user_service()
    missing = [uid for uid in user_ids if not svc.get_user(uid)]
    valid = [uid for uid in user_ids if uid not in missing]
    added, _ = _group_svc.add_members(group_id, valid)
    _audit("rbac_add_group_members", _operator_name(user_request),
           group_id=group_id, added=added)
    return {
        "success": True,
        "group_id": group_id,
        "added": added,
        "skipped_missing_users": missing,
    }


@tool(
    "rbac_grant_resource",
    description="给用户开某个具体资源的实例级授权(可带过期时间)。permission_key 必须来自 rbac_list_permission_definitions 且 grantable=true",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.HIGH,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_grant_resource(
    user_id: int,
    permission_key: str,
    resource_id: str,
    expires_at: Optional[str] = None,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """实例级授权。

    Args:
        user_id: 目标用户 ID
        permission_key: 协议权限 key,如 "agent.chat"(必须 grantable)
        resource_id: 资源实例 ID,如某个 agent 的 app_code
        expires_at: 过期时间(ISO 格式,如 2026-12-31T23:59:59),空为永久
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    from gyra_serve.permissions import PermissionRegistry, parse_key

    perm = PermissionRegistry.get(permission_key)
    if perm is None:
        return {"success": False, "error": f"未知权限 key: {permission_key}"}
    if not perm.grantable:
        return {"success": False, "error": f"权限 {permission_key} 不支持实例级授权"}
    if not _get_user_service().get_user(user_id):
        return {"success": False, "error": f"用户 {user_id} 不存在", "code": "NOT_FOUND"}

    expires = None
    if expires_at:
        from datetime import datetime

        try:
            expires = datetime.fromisoformat(expires_at)
        except ValueError:
            return {"success": False, "error": "expires_at 必须是 ISO 格式"}

    resource_type, _ = parse_key(permission_key)
    granter_id = None
    try:
        user_no = getattr(user_request, "user_no", None)
        granter_id = int(str(user_no).strip()) if user_no else None
    except (ValueError, TypeError):
        pass
    grant = _dao.create_grant(
        user_id=user_id,
        permission_key=permission_key,
        resource_type=resource_type,
        resource_id=resource_id,
        expires_at=expires,
        granted_by=granter_id,
    )
    _svc.invalidate_cache(user_id)
    _audit("rbac_grant_resource", _operator_name(user_request),
           user_id=user_id, permission_key=permission_key, resource_id=resource_id)
    return {"success": True, "grant": grant}


@tool(
    "rbac_revoke_resource",
    description="按授权 ID 回收实例级授权(用 rbac_list_grants 查 ID)",
    category=ToolCategory.BUILTIN,
    risk_level=ToolRiskLevel.HIGH,
    source=ToolSource.SYSTEM,
    tags=["rbac", "admin", "write"],
    ask_user=True,
)
def rbac_revoke_resource(
    grant_id: int, context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """回收实例级授权。

    Args:
        grant_id: 授权记录 ID
    """
    user_request, err = _require_admin(context)
    if err:
        return err
    target = next((g for g in _dao.list_grants() if g["id"] == grant_id), None)
    if not target:
        return {"success": False, "error": f"授权 {grant_id} 不存在", "code": "NOT_FOUND"}
    _dao.delete_grant(grant_id)
    _svc.invalidate_cache(target["user_id"])
    _audit("rbac_revoke_resource", _operator_name(user_request), grant_id=grant_id)
    return {"success": True, "revoked": target}
