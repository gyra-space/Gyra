"""Tests for the Feishu wiki connector (fully offline via httpx.MockTransport)."""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

import gyra_ext.knowledge.connectors.feishu_wiki as feishu_wiki_mod
from gyra_ext.knowledge.connectors.feishu_wiki import (
    FeishuApiError,
    FeishuWikiClient,
)

DOMAIN = "https://feishu.test"

TokenRoute = "/open-apis/auth/v3/tenant_access_token/internal"


def _install_mock_transport(monkeypatch, handler: Callable[[httpx.Request], httpx.Response]):
    """Inject a MockTransport into every AsyncClient the connector creates."""
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(feishu_wiki_mod.httpx, "AsyncClient", factory)


def _token_ok(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"code": 0, "tenant_access_token": "tk-1", "expire": 7200},
    )


def _items(items: list, has_more: bool = False, page_token: str | None = None) -> httpx.Response:
    body: dict = {"code": 0, "items": items, "has_more": has_more}
    if page_token:
        body["page_token"] = page_token
    return httpx.Response(200, json=body)


@pytest.mark.asyncio
async def test_list_spaces_sends_token_and_maps_fields(monkeypatch):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == TokenRoute:
            assert json.loads(request.content) == {
                "app_id": "cli_a",
                "app_secret": "s3cret",
            }
            return _token_ok(request)
        assert request.url.path == "/open-apis/wiki/v2/spaces"
        assert request.headers["Authorization"] == "Bearer tk-1"
        return _items(
            [
                {"space_id": "sp1", "name": "产品空间", "description": "doc hub"},
                {"space_id": "sp2", "name": "研发空间"},
            ]
        )

    _install_mock_transport(monkeypatch, handler)
    client = FeishuWikiClient(app_id="cli_a", app_secret="s3cret", domain=DOMAIN)
    try:
        spaces = await client.list_spaces()
    finally:
        await client.aclose()

    assert [s["space_id"] for s in spaces] == ["sp1", "sp2"]
    assert spaces[0]["name"] == "产品空间"
    assert spaces[0]["description"] == "doc hub"
    assert spaces[1]["description"] == ""
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_list_spaces_follows_pagination(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TokenRoute:
            return _token_ok(request)
        assert request.url.path == "/open-apis/wiki/v2/spaces"
        page_token = request.url.params.get("page_token")
        if not page_token:
            return _items(
                [{"space_id": "a", "name": "A"}], has_more=True, page_token="t1"
            )
        assert page_token == "t1"
        return _items([{"space_id": "b", "name": "B"}])

    _install_mock_transport(monkeypatch, handler)
    client = FeishuWikiClient(app_id="app", app_secret="sec", domain=DOMAIN)
    try:
        spaces = await client.list_spaces()
    finally:
        await client.aclose()

    assert [s["space_id"] for s in spaces] == ["a", "b"]


@pytest.mark.asyncio
async def test_list_pages_walks_tree_reads_docx_and_skips_rest(monkeypatch):
    seen_paths: list[str] = []

    def node(token: str, obj_token: str, obj_type: str, title: str, has_child: bool):
        return {
            "node_token": token,
            "obj_token": obj_token,
            "obj_type": obj_type,
            "title": title,
            "has_child": has_child,
            "obj_edit_time": 1700000000,
        }

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == TokenRoute:
            return _token_ok(request)
        if request.url.path == "/open-apis/wiki/v2/spaces/sp1/nodes":
            parent = request.url.params.get("parent_node_token")
            page_token = request.url.params.get("page_token")
            if not parent:
                # multi-page root level: page 1 has a child node, page 2 a sheet
                if not page_token:
                    return _items(
                        [
                            node("n1", "doc1", "docx", "首页", True),
                            node("n2", "doc2", "docx", "空文档", False),
                        ],
                        has_more=True,
                        page_token="t1",
                    )
                return _items([node("n3", "sheet1", "sheet", "表格", False)])
            assert parent == "n1"
            return _items([node("n4", "doc4", "docx", "子页", False)])
        if request.url.path == "/open-apis/docx/v1/documents/doc1/raw_content":
            return httpx.Response(200, json={"code": 0, "content": "第一页正文"})
        if request.url.path == "/open-apis/docx/v1/documents/doc2/raw_content":
            return httpx.Response(200, json={"code": 0, "content": "   "})
        if request.url.path == "/open-apis/docx/v1/documents/doc4/raw_content":
            return httpx.Response(200, json={"code": 0, "content": "子页正文"})
        return httpx.Response(404, json={"code": 99991661, "msg": "not found"})

    _install_mock_transport(monkeypatch, handler)
    client = FeishuWikiClient(app_id="app", app_secret="sec", domain=DOMAIN)
    try:
        pages = await client.list_pages("sp1")
    finally:
        await client.aclose()

    titles = [p.title for p in pages]
    assert titles == ["首页", "子页"]

    first = pages[0]
    assert first.content == "第一页正文"
    assert first.source_ref == "sp1/n1"
    assert first.url == f"{DOMAIN}/wiki/n1"
    assert first.updated_at == "2023-11-14T22:13:20"

    # token requested exactly once across the whole walk
    token_calls = [p for p in seen_paths if p == TokenRoute]
    assert len(token_calls) == 1


@pytest.mark.asyncio
async def test_nonzero_business_code_raises_feishu_api_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TokenRoute:
            return _token_ok(request)
        return httpx.Response(
            200, json={"code": 99991672, "msg": "wiki space not found"}
        )

    _install_mock_transport(monkeypatch, handler)
    client = FeishuWikiClient(app_id="app", app_secret="sec", domain=DOMAIN)
    try:
        with pytest.raises(FeishuApiError, match="99991672"):
            await client.list_spaces()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_token_refreshes_after_expiry(monkeypatch):
    tokens = iter(["tk-1", "tk-2"])
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TokenRoute:
            calls.append("token")
            return httpx.Response(
                200,
                json={"code": 0, "tenant_access_token": next(tokens), "expire": 30},
            )
        return _items([{"space_id": "a", "name": "A"}])

    _install_mock_transport(monkeypatch, handler)
    client = FeishuWikiClient(app_id="app", app_secret="sec", domain=DOMAIN)
    try:
        await client.list_spaces()
        assert client._token == "tk-1"
        # expire=30 < 60s safety margin → next call must re-authenticate
        await client.list_spaces()
        assert client._token == "tk-2"
    finally:
        await client.aclose()

    assert len(calls) == 2
