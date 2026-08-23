"""Tool 资源目录 Provider：向 RBAC 提供工具可选列表。"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class ToolCatalogProvider(ResourceCatalogProvider):
    """Tool 资源目录。"""

    def resource_type(self) -> str:
        return "tool"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_core.tools import tool_registry, register_builtin_tools

            register_builtin_tools()
            tools = tool_registry.list_all()

            items = []
            for tool in tools:
                meta = tool.metadata
                name = meta.name
                if keyword and keyword.lower() not in name.lower():
                    continue
                desc = meta.description or ""
                items.append(
                    ResourceCatalogItem(
                        id=name,
                        name=name,
                        description=desc[:100] if desc else None,
                        metadata={
                            "category": getattr(meta, "category", None),
                            "risk_level": getattr(meta, "risk_level", None),
                            "requires_permission": getattr(meta, "requires_permission", False),
                        },
                    )
                )
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.warning(f"[ToolCatalogProvider] list tools failed: {e}")
            return []
