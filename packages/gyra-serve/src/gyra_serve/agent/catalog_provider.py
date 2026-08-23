"""Agent 资源目录 Provider：向 RBAC 提供 Agent 可选列表。"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class AgentCatalogProvider(ResourceCatalogProvider):
    """Agent 资源目录。"""

    def resource_type(self) -> str:
        return "agent"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_core.config import ConfigManager

            cfg = ConfigManager.get()
            agents = cfg.agents or {}

            items = []
            for name, agent in agents.items():
                if keyword and keyword.lower() not in name.lower():
                    continue
                desc = getattr(agent, "description", "") or ""
                items.append(
                    ResourceCatalogItem(
                        id=name,
                        name=name,
                        description=desc[:100] if desc else None,
                        metadata={
                            "max_steps": getattr(agent, "max_steps", None),
                            "tools": getattr(agent, "tools", None),
                        },
                    )
                )
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.warning(f"[AgentCatalogProvider] list agents failed: {e}")
            return []
