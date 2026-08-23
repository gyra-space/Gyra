"""Channel 资源目录 Provider：向 RBAC 提供渠道可选列表。"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class ChannelCatalogProvider(ResourceCatalogProvider):
    """Channel 资源目录。"""

    def resource_type(self) -> str:
        return "channel"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_serve.channel.models.models import ChannelDao, ChannelEntity

            dao = ChannelDao(None)
            with dao.session(commit=False) as session:
                q = session.query(ChannelEntity).filter(ChannelEntity.enabled == 1)
                if keyword:
                    q = q.filter(ChannelEntity.name.contains(keyword))
                entities = q.limit(limit).all()

                items = []
                for e in entities:
                    session.expunge(e)
                    items.append(
                        ResourceCatalogItem(
                            id=e.id,
                            name=e.name or e.id,
                            description=e.channel_type,
                            metadata={
                                "channel_type": e.channel_type,
                                "status": e.status,
                            },
                        )
                    )
                return items
        except Exception as e:
            logger.warning(f"[ChannelCatalogProvider] list channels failed: {e}")
            return []
