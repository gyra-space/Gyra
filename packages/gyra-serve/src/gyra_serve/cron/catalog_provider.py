"""Cron 资源目录 Provider：向 RBAC 提供定时任务可选列表。"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class CronCatalogProvider(ResourceCatalogProvider):
    """Cron 资源目录。"""

    def resource_type(self) -> str:
        return "cron"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_serve.cron.models.models import CronJobEntity, ServeDao

            dao = ServeDao(None)
            with dao.session(commit=False) as session:
                q = session.query(CronJobEntity).filter(CronJobEntity.enabled == 1)
                if keyword:
                    q = q.filter(CronJobEntity.name.contains(keyword))
                entities = q.limit(limit).all()

                items = []
                for e in entities:
                    session.expunge(e)
                    items.append(
                        ResourceCatalogItem(
                            id=e.id,
                            name=e.name or e.id,
                            description=e.description or "",
                            metadata={
                                "schedule_kind": e.schedule_kind,
                                "payload_kind": e.payload_kind,
                            },
                        )
                    )
                return items
        except Exception as e:
            logger.warning(f"[CronCatalogProvider] list jobs failed: {e}")
            return []
