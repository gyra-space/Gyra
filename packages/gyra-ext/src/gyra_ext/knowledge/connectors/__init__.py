"""External wiki/doc connectors that feed remote pages into the ingest pipeline.

A connector turns a remote source (Feishu wiki today, more later) into a flat
list of :class:`ConnectorPage`. The ingest orchestrator then treats each page
like any other verbatim source: L0 verbatim → L1 wiki → L2 graph edges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ConnectorPage:
    """One page pulled from an external wiki/doc source.

    ``content`` is plain text (markup already stripped by the connector).
    ``source_ref`` identifies the page in the remote system so re-syncs can
    be traced; ``url`` is the human-facing link stored as provenance.
    """

    title: str
    content: str
    source_ref: str
    url: Optional[str] = None
    updated_at: Optional[str] = None


@runtime_checkable
class WikiConnector(Protocol):
    """Minimal interface the ingest orchestrator expects from a connector."""

    name: str

    async def list_spaces(self) -> List[Dict[str, Any]]:
        """Return selectable spaces: ``[{space_id, name, description}]``."""
        ...

    async def list_pages(self, space_id: str) -> List[ConnectorPage]:
        """Return all readable pages of a space, flattened."""
        ...

    async def aclose(self) -> None:
        """Release underlying HTTP resources."""
        ...


__all__ = [
    "ConnectorPage",
    "WikiConnector",
    "FeishuWikiClient",
]


def __getattr__(name: str):  # lazy heavy import (httpx) until actually used
    if name == "FeishuWikiClient":
        from .feishu_wiki import FeishuWikiClient

        return FeishuWikiClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
