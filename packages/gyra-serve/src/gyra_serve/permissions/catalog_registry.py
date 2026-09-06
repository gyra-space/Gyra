"""资源目录注册中心：管理各资源类型的 ResourceCatalogProvider。

各资源模块（datasource/agent/tool/...）在自身包内实现 CatalogProvider，
启动时由本模块统一注册，供 RBAC 配置界面的统一资源目录 API 调用。
"""

import logging
from typing import Dict, List, Optional

from .protocol import ResourceCatalogProvider

logger = logging.getLogger(__name__)


class ResourceCatalogRegistry:
    """资源目录注册表。"""

    _providers: Dict[str, ResourceCatalogProvider] = {}

    @classmethod
    def register(cls, provider: ResourceCatalogProvider) -> None:
        rtype = provider.resource_type()
        if rtype in cls._providers:
            existing = cls._providers[rtype]
            if existing is not provider:
                logger.warning(
                    "ResourceCatalogProvider conflict for %s: %s -> %s",
                    rtype,
                    type(existing).__name__,
                    type(provider).__name__,
                )
            return
        cls._providers[rtype] = provider
        logger.debug("ResourceCatalogProvider registered: %s", rtype)

    @classmethod
    def get(cls, resource_type: str) -> Optional[ResourceCatalogProvider]:
        return cls._providers.get(resource_type)

    @classmethod
    def list_types(cls) -> List[str]:
        return sorted(cls._providers.keys())

    @classmethod
    def has(cls, resource_type: str) -> bool:
        return resource_type in cls._providers


# --------------------------------------------------------------------------- #
# 内置 Provider 注册（启动时执行）
# --------------------------------------------------------------------------- #


def _register_builtin_providers() -> None:
    """注册内置资源目录 Provider。"""
    from gyra_serve.agent.catalog_provider import AgentCatalogProvider
    from gyra_serve.channel.catalog_provider import ChannelCatalogProvider
    from gyra_serve.cron.catalog_provider import CronCatalogProvider
    from gyra_serve.datasource.catalog_provider import DatabaseCatalogProvider
    from gyra_serve.ecp.catalog_provider import EcpCatalogProvider
    from gyra_serve.knowledge.catalog_provider import KnowledgeCatalogProvider
    from gyra_serve.model.catalog_provider import ModelCatalogProvider
    from gyra_serve.tool.catalog_provider import ToolCatalogProvider

    ResourceCatalogRegistry.register(AgentCatalogProvider())
    ResourceCatalogRegistry.register(ChannelCatalogProvider())
    ResourceCatalogRegistry.register(CronCatalogProvider())
    ResourceCatalogRegistry.register(DatabaseCatalogProvider())
    ResourceCatalogRegistry.register(EcpCatalogProvider())
    ResourceCatalogRegistry.register(KnowledgeCatalogProvider())
    ResourceCatalogRegistry.register(ModelCatalogProvider())
    ResourceCatalogRegistry.register(ToolCatalogProvider())

    logger.info(
        "ResourceCatalogRegistry initialized: %s",
        ResourceCatalogRegistry.list_types(),
    )


_register_builtin_providers()
