"""Model 资源目录 Provider：向 RBAC 提供模型可选列表。"""

import logging
from typing import List, Optional

from gyra_serve.permissions.protocol import ResourceCatalogItem, ResourceCatalogProvider

logger = logging.getLogger(__name__)


class ModelCatalogProvider(ResourceCatalogProvider):
    """Model 资源目录。"""

    def resource_type(self) -> str:
        return "model"

    def supports_hierarchy(self) -> bool:
        return False

    def list_items(
        self,
        parent_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ResourceCatalogItem]:
        try:
            from gyra_app.config_storage.agent_llm_db_storage import load_agent_llm_dict

            agent_llm = load_agent_llm_dict()
            if not agent_llm:
                return []

            items = []
            providers = agent_llm.get("provider") or []
            if not isinstance(providers, list):
                return []

            for p_conf in providers:
                if not isinstance(p_conf, dict):
                    continue
                provider_name = p_conf.get("provider", "unknown")
                models = p_conf.get("model") or []
                if not isinstance(models, list):
                    continue

                for m_conf in models:
                    if not isinstance(m_conf, dict):
                        continue
                    model_name = m_conf.get("name") or m_conf.get("model")
                    if not model_name:
                        continue
                    if keyword and keyword.lower() not in model_name.lower():
                        continue
                    items.append(
                        ResourceCatalogItem(
                            id=model_name,
                            name=model_name,
                            description=f"{provider_name} | {m_conf.get('model_type', 'llm')}",
                            metadata={
                                "provider": provider_name,
                                "model_type": m_conf.get("model_type", "llm"),
                            },
                        )
                    )
                    if len(items) >= limit:
                        return items
            return items
        except Exception as e:
            logger.warning(f"[ModelCatalogProvider] list models failed: {e}")
            return []
