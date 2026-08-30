"""Agent 资源目录 Provider：向 RBAC 提供 Agent 可选列表。

数据源为 gpts_app 应用表（用户实际看到/对话的应用）,app_code 即
``require_permission("agent", ..., resource_id=app_code)`` 判定时用的资源 ID。
"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class AgentCatalogProvider(ResourceCatalogProvider):
    """Agent 资源目录（gpts_app 应用）。"""

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
            from gyra.storage.metadata.db_manager import db
            from gyra_serve.building.app.models.models import ServeEntity

            items = []
            with db.session(commit=False) as s:
                q = s.query(ServeEntity).order_by(ServeEntity.id.desc())
                if keyword:
                    like = f"%{keyword}%"
                    q = q.filter(
                        (ServeEntity.app_name.like(like))
                        | (ServeEntity.app_code.like(like))
                    )
                for r in q.limit(limit).all():
                    if not r.app_code:
                        continue
                    items.append(
                        ResourceCatalogItem(
                            id=r.app_code,
                            name=r.app_name or r.app_code,
                            description=(r.app_describe or "")[:100] or None,
                            metadata={
                                "published": r.published,
                                "team_mode": r.team_mode,
                            },
                        )
                    )
            return items
        except Exception as e:
            logger.warning(f"[AgentCatalogProvider] list apps failed: {e}")
            return []
