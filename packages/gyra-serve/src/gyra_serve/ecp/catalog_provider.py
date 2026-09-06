"""ECP 资源目录 Provider：向 RBAC 提供语义对象可选列表。"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class EcpCatalogProvider(ResourceCatalogProvider):
    """ECP 资源目录（语义对象，跨空间去重取最新版本）。"""

    def resource_type(self) -> str:
        return "ecp"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_serve.ecp.models.models import EcpSemanticObjectEntity
            from gyra.storage.metadata.db_manager import db

            with db.session(commit=False) as session:
                q = session.query(EcpSemanticObjectEntity).filter(
                    EcpSemanticObjectEntity.status == "confirmed"
                )
                if keyword:
                    q = q.filter(EcpSemanticObjectEntity.name.contains(keyword))
                rows = (
                    q.order_by(
                        EcpSemanticObjectEntity.id.asc(),
                        EcpSemanticObjectEntity.version.desc(),
                    )
                    .limit(limit * 4)
                    .all()
                )

                # 按 id 去重取最新版本（order_by 保证每个 id 首次出现即最新）
                items: List[ResourceCatalogItem] = []
                seen = set()
                for e in rows:
                    if e.id in seen:
                        continue
                    seen.add(e.id)
                    items.append(
                        ResourceCatalogItem(
                            id=e.id,
                            name=e.name or e.id,
                            description=e.obj_type,
                            metadata={
                                "workspace_id": e.workspace_id,
                                "obj_type": e.obj_type,
                            },
                        )
                    )
                    if len(items) >= limit:
                        break
                return items
        except Exception as e:
            logger.warning(f"[EcpCatalogProvider] list semantic objects failed: {e}")
            return []
