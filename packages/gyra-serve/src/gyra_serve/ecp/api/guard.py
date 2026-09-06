"""ECP API 权限守卫：全局 ecp 域 + 场景空间投影。

背景：场景空间「语义资产」tab 内嵌 EcpConsole，打开即调 /graph、/op-log、
/admin/* 等治理端点；这些端点若只挂全局域 ``require("ecp.read")``，而内置
全局角色默认不含 ``ecp.*``（admin 靠 legacy 角色直通），空间主/成员打开必 403。

授权规则（``require_ecp(action)``，fail-closed）：
1. 全局 ``ecp.<action>`` 通过（``has``）→ 放行：全局治理员语义不变，
   插件关闭（开发模式）/ legacy admin 直通也在这层生效；
2. 请求携带的 workspace_id 是派生 ECP 空间（``ecp_<workspace_code>``）时，
   反查场景空间后按空间域判定（``has_scope``）：
   - read   -> ``space.asset.view``（space.member/viewer/admin 均有，可浏览）
   - manage -> ``space.asset.manage``（仅 space.admin，可治理）
3. 其余（无 workspace_id / 全局 default 空间 / 反查不到空间）不投影，
   仅规则 1，维持原全局语义。

workspace_id 解析覆盖 query 与 JSON body（Starlette 缓存 ``_body``，不影响
后续端点的 Pydantic 解析），与 ECP 端点的入参方式（GET Query / POST body /
POST querystring）对齐。
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request

from gyra_serve.permissions.check import has, has_scope
from gyra_serve.utils.auth import UserRequest, get_user_from_headers

# 派生 ECP workspace_id 前缀（约定见 workspace/ecp_derive.py）
_ECP_WORKSPACE_PREFIX = "ecp_"

# 空间域投影：ecp.<action> -> space.*（空间角色矩阵见 permissions/modules/space.py）
_SPACE_PROJECTION = {
    "read": "space.asset.view",
    "manage": "space.asset.manage",
}


async def _request_workspace_id(request: Request) -> Optional[str]:
    """从 query / JSON body 提取 workspace_id（与 ECP 端点入参方式对齐）。"""
    wid = request.query_params.get("workspace_id")
    if wid:
        return wid
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return None
        if isinstance(body, dict):
            wid = body.get("workspace_id")
            if isinstance(wid, str) and wid:
                return wid
    return None


def _scene_workspace_id(ecp_workspace_id: str) -> Optional[int]:
    """派生 ECP 空间 id（ecp_<code>）反查场景空间数字 id；其余返回 None。"""
    if not ecp_workspace_id.startswith(_ECP_WORKSPACE_PREFIX):
        return None
    code = ecp_workspace_id[len(_ECP_WORKSPACE_PREFIX) :]
    if not code:
        return None
    try:
        from gyra_serve.workspace.rbac import _lookup_workspace_id_by_code

        return _lookup_workspace_id_by_code(code)
    except Exception:  # noqa: BLE001
        return None


def require_ecp(action: str):
    """FastAPI 依赖工厂：ecp.<action> 判定（含场景空间投影，见模块 docstring）。"""
    permission_key = f"ecp.{action}"

    async def dependency(
        request: Request,
        user: UserRequest = Depends(get_user_from_headers),
    ) -> UserRequest:
        if has(user, permission_key):
            return user
        projection = _SPACE_PROJECTION.get(action)
        if projection:
            ecp_ws = await _request_workspace_id(request)
            scene_ws_id = _scene_workspace_id(ecp_ws) if ecp_ws else None
            if scene_ws_id is not None and has_scope(user, projection, scene_ws_id):
                return user
        raise HTTPException(
            status_code=403, detail=f"Permission denied: {permission_key}"
        )

    return dependency
