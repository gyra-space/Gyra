"""require_ecp 守卫单元测试:全局 ecp 域 + 场景空间投影。

背景:场景空间「语义资产」tab 打开 EcpConsole 即调治理端点,全局角色默认
不含 ecp.*,空间用户原先必 403。守卫规则(见 guard.py docstring):
1. 全局 ecp.<action> 通过 -> 放行;
2. workspace_id 为派生 ECP 空间(ecp_<code>)时投影空间域判定
   (read -> space.asset.view / manage -> space.asset.manage);
3. 其余 fail-closed 403。
"""

import asyncio

import pytest
from fastapi import HTTPException

from gyra_serve.ecp.api import guard


class _FakeRequest:
    def __init__(self, query=None, body=None, method="GET"):
        self.query_params = query or {}
        self._body = body
        self.method = method

    async def json(self):
        if isinstance(self._body, (dict, list)):
            return self._body
        raise ValueError("not json")


def _patch_auth(monkeypatch, has=True, has_scope=True, scene_ws_id=7):
    """mock has/has_scope/_lookup_workspace_id_by_code,并记录 has_scope 入参。"""
    calls = {"has": [], "has_scope": []}

    monkeypatch.setattr(guard, "has", lambda user, key: calls["has"].append(key) or has)

    def _fake_has_scope(user, key, workspace_id):
        calls["has_scope"].append((key, workspace_id))
        return has_scope

    monkeypatch.setattr(guard, "has_scope", _fake_has_scope)
    monkeypatch.setattr(
        "gyra_serve.workspace.rbac._lookup_workspace_id_by_code",
        lambda code: scene_ws_id,
    )
    return calls


class TestRequireEcp:
    def test_global_perm_passes(self, monkeypatch):
        _patch_auth(monkeypatch, has=True)
        user = object()
        out = asyncio.run(guard.require_ecp("read")(request=_FakeRequest(), user=user))
        assert out is user

    def test_projection_read_passes(self, monkeypatch):
        _patch_auth(monkeypatch, has=False, has_scope=True, scene_ws_id=7)
        req = _FakeRequest(query={"workspace_id": "ecp_ws_abc123"})
        user = object()
        out = asyncio.run(guard.require_ecp("read")(request=req, user=user))
        assert out is user

    def test_projection_read_maps_space_asset_view(self, monkeypatch):
        calls = _patch_auth(monkeypatch, has=False, has_scope=True)
        req = _FakeRequest(query={"workspace_id": "ecp_ws_abc123"})
        asyncio.run(guard.require_ecp("read")(request=req, user=object()))
        assert calls["has_scope"] == [("space.asset.view", 7)]

    def test_projection_manage_maps_space_asset_manage(self, monkeypatch):
        calls = _patch_auth(monkeypatch, has=False, has_scope=True)
        req = _FakeRequest(query={"workspace_id": "ecp_ws_abc123"})
        asyncio.run(guard.require_ecp("manage")(request=req, user=object()))
        assert calls["has_scope"] == [("space.asset.manage", 7)]

    def test_projection_manage_denied_without_scope(self, monkeypatch):
        _patch_auth(monkeypatch, has=False, has_scope=False)
        req = _FakeRequest(query={"workspace_id": "ecp_ws_abc123"})
        with pytest.raises(HTTPException) as exc:
            asyncio.run(guard.require_ecp("manage")(request=req, user=object()))
        assert exc.value.status_code == 403
        assert "ecp.manage" in exc.value.detail

    def test_body_workspace_id_projected(self, monkeypatch):
        _patch_auth(monkeypatch, has=False, has_scope=True)
        req = _FakeRequest(
            body={"sql": "select 1", "workspace_id": "ecp_ws_abc123"},
            method="POST",
        )
        out = asyncio.run(guard.require_ecp("manage")(request=req, user=object()))
        assert out is not None

    def test_no_workspace_falls_back_global_only(self, monkeypatch):
        calls = _patch_auth(monkeypatch, has=False, has_scope=True)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                guard.require_ecp("read")(request=_FakeRequest(), user=object())
            )
        assert exc.value.status_code == 403
        assert calls["has_scope"] == []

    def test_default_workspace_not_projected(self, monkeypatch):
        """全局 default 空间不走投影:反查 code 'default' 无场景空间语义。"""
        calls = _patch_auth(monkeypatch, has=False, has_scope=True)
        req = _FakeRequest(query={"workspace_id": "default"})
        with pytest.raises(HTTPException):
            asyncio.run(guard.require_ecp("read")(request=req, user=object()))
        assert calls["has_scope"] == []

    def test_unknown_workspace_code_403(self, monkeypatch):
        _patch_auth(monkeypatch, has=False, has_scope=True, scene_ws_id=None)
        req = _FakeRequest(query={"workspace_id": "ecp_ghost"})
        with pytest.raises(HTTPException) as exc:
            asyncio.run(guard.require_ecp("read")(request=req, user=object()))
        assert exc.value.status_code == 403
