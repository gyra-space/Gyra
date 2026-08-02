"""向后兼容重导出——协议本体已迁移至 ``gyra.core.interface.resource.protocol``,
LegacyResourceAdapter 迁移至 ``gyra.agent.capabilities.legacy_adapter``。

本模块保留以兼容现有 ``from gyra.agent.shared.prompt_assembly.resource_protocol import X``
导入路径。新代码:
- 协议本体(ResourceProtocol/ConsumerRegistry/apply_consumption)→ gyra.core.interface.resource.protocol
- 桥接(LegacyResourceAdapter)→ gyra.agent.capabilities.legacy_adapter
"""

from gyra.core.interface.resource.protocol import (  # noqa: F401
    ConsumerRegistry,
    ResourceProtocol,
    apply_consumption,
)
from gyra.agent.capabilities.legacy_adapter import (  # noqa: F401
    LegacyResourceAdapter,
)