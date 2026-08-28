"""Feishu (Lark) wiki connector over the OpenAPI v2 endpoints.

Flow: ``tenant_access_token`` (cached, auto-refresh) → list wiki spaces →
recursively walk space nodes → fetch readable ``docx`` pages as plain text
via the raw_content API. Nodes of other types (sheet/bitable/mindnote/file,
and legacy ``doc``) are skipped with a warning — the raw_content endpoint
only serves the new docx format.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from . import ConnectorPage

logger = logging.getLogger(__name__)

_DEFAULT_DOMAIN = "https://open.feishu.cn"
_PAGE_SIZE = 50
_MAX_NODE_DEPTH = 10
_TIMEOUT = httpx.Timeout(30.0)

# obj_type values that raw_content can serve; legacy "doc" is not supported.
_READABLE_OBJ_TYPES = {"docx"}


class FeishuApiError(RuntimeError):
    """A Feishu OpenAPI call returned a non-zero business code."""


class FeishuWikiClient:
    """Async client implementing the WikiConnector protocol for Feishu wiki."""

    name = "feishu"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        domain: str = _DEFAULT_DOMAIN,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._domain = (domain or _DEFAULT_DOMAIN).rstrip("/")
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)
        self._token: Optional[str] = None
        self._token_expire_at: float = 0.0

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expire_at - 60:
            return self._token
        resp = await self._client.post(
            f"{self._domain}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
        )
        data = _unwrap(resp)
        self._token = data["tenant_access_token"]
        self._token_expire_at = time.time() + int(data.get("expire", 7200))
        return self._token

    async def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        token = await self._ensure_token()
        resp = await self._client.get(
            f"{self._domain}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params={k: v for k, v in (params or {}).items() if v},
        )
        return _unwrap(resp)

    # ------------------------------------------------------------------
    # WikiConnector protocol
    # ------------------------------------------------------------------

    async def list_spaces(self) -> List[Dict[str, Any]]:
        spaces: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        while True:
            data = await self._get(
                "/open-apis/wiki/v2/spaces",
                params={"page_size": _PAGE_SIZE, "page_token": page_token},
            )
            for item in data.get("items") or []:
                spaces.append(
                    {
                        "space_id": item.get("space_id", ""),
                        "name": item.get("name", ""),
                        "description": item.get("description", "") or "",
                    }
                )
            if not data.get("has_more") or not data.get("page_token"):
                break
            page_token = data["page_token"]
        return spaces

    async def list_pages(self, space_id: str) -> List[ConnectorPage]:
        """Flatten the space node tree into readable ConnectorPages."""
        pages: List[ConnectorPage] = []
        nodes = await self._walk_nodes(space_id)
        for node in nodes:
            obj_type = node.get("obj_type", "")
            title = node.get("title", "") or "untitled"
            if obj_type not in _READABLE_OBJ_TYPES:
                logger.info(
                    "feishu wiki node %s (%s) skipped: obj_type=%s not readable",
                    node.get("node_token"),
                    title,
                    obj_type or "unknown",
                )
                continue
            obj_token = node.get("obj_token", "")
            if not obj_token:
                continue
            content = await self.read_docx_raw(obj_token)
            if not content.strip():
                logger.info(
                    "feishu wiki node %s (%s) is empty, skipped", obj_token, title
                )
                continue
            pages.append(
                ConnectorPage(
                    title=title,
                    content=content,
                    source_ref=f"{space_id}/{node.get('node_token', '')}",
                    url=_wiki_url(self._domain, space_id, node.get("node_token", "")),
                    updated_at=_fmt_edit_time(node.get("obj_edit_time")),
                )
            )
        return pages

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Node tree walking
    # ------------------------------------------------------------------

    async def _walk_nodes(self, space_id: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        await self._walk_level(space_id, parent_token=None, depth=0, out=out)
        return out

    async def _walk_level(
        self,
        space_id: str,
        parent_token: Optional[str],
        depth: int,
        out: List[Dict[str, Any]],
    ) -> None:
        if depth > _MAX_NODE_DEPTH:
            logger.warning(
                "feishu wiki space %s: node tree deeper than %s levels, truncated",
                space_id,
                _MAX_NODE_DEPTH,
            )
            return
        page_token: Optional[str] = None
        level_nodes: List[Dict[str, Any]] = []
        while True:
            data = await self._get(
                f"/open-apis/wiki/v2/spaces/{space_id}/nodes",
                params={
                    "page_size": _PAGE_SIZE,
                    "page_token": page_token,
                    "parent_node_token": parent_token,
                },
            )
            level_nodes.extend(data.get("items") or [])
            if not data.get("has_more") or not data.get("page_token"):
                break
            page_token = data["page_token"]
        out.extend(level_nodes)
        for node in level_nodes:
            if node.get("has_child"):
                await self._walk_level(
                    space_id,
                    parent_token=node.get("node_token"),
                    depth=depth + 1,
                    out=out,
                )

    # ------------------------------------------------------------------
    # Document content
    # ------------------------------------------------------------------

    async def read_docx_raw(self, document_id: str) -> str:
        """Fetch a docx document's plain-text content via raw_content."""
        data = await self._get(
            f"/open-apis/docx/v1/documents/{document_id}/raw_content"
        )
        return data.get("content", "") or ""


def _unwrap(resp: httpx.Response) -> Dict[str, Any]:
    """Validate the Feishu envelope ``{code, msg, ...}`` and return it."""
    resp.raise_for_status()
    payload = resp.json()
    code = payload.get("code")
    if code not in (0, None):
        raise FeishuApiError(
            f"Feishu API error {code}: {payload.get('msg', 'unknown')}"
        )
    return payload


def _wiki_url(domain: str, space_id: str, node_token: str) -> str:
    if not node_token:
        return ""
    return f"{domain}/wiki/{node_token}"


def _fmt_edit_time(seconds: Any) -> Optional[str]:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(seconds)))
    except (TypeError, ValueError):
        return None
