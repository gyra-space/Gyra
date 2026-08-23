"""Knowledge 资源目录 Provider：向 RBAC 提供知识空间可选列表。"""

import asyncio
import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class KnowledgeCatalogProvider(ResourceCatalogProvider):
    """Knowledge 资源目录。"""

    def resource_type(self) -> str:
        return "knowledge"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_serve.knowledge.service.service import Service as KnowledgeService
            from gyra.component import SystemApp
            from gyra_serve.knowledge.config import ServeConfig

            # 构造最小化 Service 实例（仅用于 list_spaces）
            config = ServeConfig()
            app = SystemApp()
            service = KnowledgeService(app, config)

            # list_spaces 是 async 方法，需要同步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                spaces = loop.run_until_complete(service.list_spaces())
            finally:
                loop.close()

            items = []
            for space in spaces:
                slug = space.get("slug", "")
                if not slug:
                    continue
                if keyword and keyword.lower() not in slug.lower():
                    continue
                items.append(
                    ResourceCatalogItem(
                        id=slug,
                        name=slug,
                        description=space.get("space_type", ""),
                        metadata={
                            "backend": space.get("backend"),
                            "space_type": space.get("space_type"),
                            "default_agent_id": space.get("default_agent_id"),
                        },
                    )
                )
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.warning(f"[KnowledgeCatalogProvider] list spaces failed: {e}")
            return []
