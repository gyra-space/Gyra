"""用户自助 Agent 工具 —— 面向普通登录用户的"自己的账号"自助操作。

定位:薄封装层,复用 ``UserService``(与 REST API 同一数据通路),不走 HTTP。

安全模型(fail-closed,与 RBAC 管理工具区分):
- 每个工具从 ``ToolContext`` 取提问者的 ``user_request``;取不到 → 拒绝。
- **只操作自己的数据**:目标用户 id 一律取当前登录用户,不允许指定他人,
  从机制上杜绝越权(不依赖 prompt 约束)。
- **不需要 system.admin**:这些是普通用户的自助能力,只要已登录即可。
- 修改密码要求提供旧密码并校验通过,防止会话被借用时被改密。
- 写操作记结构化审计日志(不记录密码明文)。

与 ``permissions/agent_tools.py`` 的区别:那套是管理员对他人/全局的运维(需
system.admin);这套是普通用户对自己的自助(仅需登录)。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from gyra.agent.tools.base import ToolCategory, ToolRiskLevel, ToolSource
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.decorators import tool

logger = logging.getLogger(__name__)


def _deny(reason: str) -> Dict[str, Any]:
    return {"success": False, "error": reason, "code": "PERMISSION_DENIED"}


def _get_user_request(context: Optional[ToolContext]):
    if context is None:
        return None
    return context.get_resource("user_request") or context.config.get("user_request")


def _current_user_id(user_request) -> Optional[int]:
    """从 user_request 解析当前登录用户的数字 id(user_no / user_id)。"""
    for raw in (
        getattr(user_request, "user_no", None),
        getattr(user_request, "user_id", None),
    ):
        if raw is None or raw == "":
            continue
        try:
            return int(str(raw).strip())
        except (ValueError, TypeError):
            continue
    return None


def _require_self(context: Optional[ToolContext]):
    """返回 (user_request, user_id, None) 或 (None, None, deny_result)。fail-closed。"""
    user_request = _get_user_request(context)
    if user_request is None:
        return None, None, _deny(
            "无法确认操作者身份(缺少用户上下文),请先登录后再执行自助操作"
        )
    user_id = _current_user_id(user_request)
    if user_id is None:
        return None, None, _deny("无法解析当前用户 ID,拒绝执行")
    return user_request, user_id, None


def _operator_name(user_request) -> str:
    return (
        getattr(user_request, "user_name", None)
        or getattr(user_request, "real_name", None)
        or "unknown"
    )


def _audit(op: str, operator: str, **params: Any) -> None:
    # 不记录敏感参数(密码),只记录操作与对象。
    safe = {k: ("***" if "password" in k else v) for k, v in params.items()}
    logger.info("SELF-SERVICE op=%s operator=%s params=%s", op, operator, safe)


def _get_user_service():
    from gyra_app.auth.user_service import UserService

    return UserService()


# --------------------------------------------------------------------------- #
# 自助工具
# --------------------------------------------------------------------------- #
@tool(
    "self_get_profile",
    description=(
        "查看当前登录用户自己的账号资料(用户名、姓名、邮箱、角色、账号状态)。"
        "只返回本人信息,不暴露他人数据。"
    ),
    category=ToolCategory.BUILTIN,
    source=ToolSource.SYSTEM,
    risk_level=ToolRiskLevel.SAFE,
    tags=["self", "profile", "read"],
    ask_user=False,
)
def self_get_profile(context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """查看自己的账号资料。"""
    user_request, user_id, deny = _require_self(context)
    if deny:
        return deny
    user = _get_user_service().get_user(user_id)
    if not user:
        return {"success": False, "error": f"用户 {user_id} 不存在", "code": "NOT_FOUND"}
    user.pop("password_hash", None)
    return {"success": True, "profile": user}


@tool(
    "self_change_password",
    description=(
        "修改当前登录用户自己的登录密码。必须提供旧密码并校验通过才能修改,"
        "防止会话被借用时被改密。仅修改本人密码,不影响他人。"
    ),
    category=ToolCategory.BUILTIN,
    source=ToolSource.SYSTEM,
    risk_level=ToolRiskLevel.MEDIUM,
    tags=["self", "password", "write"],
    ask_user=True,
)
def self_change_password(
    old_password: str,
    new_password: str,
    context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """修改自己的密码(需校验旧密码)。

    Args:
        old_password: 当前使用的旧密码(用于校验身份)
        new_password: 要设置的新密码
    """
    user_request, user_id, deny = _require_self(context)
    if deny:
        return deny

    if not old_password or not new_password:
        return {"success": False, "error": "旧密码和新密码都不能为空", "code": "INVALID_PARAM"}
    if len(new_password) < 6:
        return {
            "success": False,
            "error": "新密码长度至少 6 位",
            "code": "INVALID_PARAM",
        }
    if old_password == new_password:
        return {
            "success": False,
            "error": "新密码不能与旧密码相同",
            "code": "INVALID_PARAM",
        }

    svc = _get_user_service()
    username = getattr(user_request, "user_name", None)
    if not username:
        return _deny("无法获取当前用户名,拒绝修改密码")

    # 用旧密码校验身份(verify_local_user 返回 None 表示校验失败)。
    verified = svc.verify_local_user(username, old_password)
    if not verified:
        _audit("self_change_password", _operator_name(user_request), result="old_password_mismatch")
        return {
            "success": False,
            "error": "旧密码不正确,未做任何修改",
            "code": "AUTH_FAILED",
        }

    updated = svc.update_user(user_id, password=new_password)
    if not updated:
        return {"success": False, "error": "密码更新失败,请稍后重试", "code": "UPDATE_FAILED"}

    updated.pop("password_hash", None)
    _audit("self_change_password", _operator_name(user_request), result="ok")
    return {
        "success": True,
        "message": "密码已修改成功,下次登录请使用新密码",
        "profile": updated,
    }
