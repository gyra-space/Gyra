"""向后兼容重导出——SandboxResource 已迁移至 ``gyra.agent.capabilities.sandbox``。

新代码请从 ``gyra.agent.capabilities.sandbox`` 导入。
"""

from gyra.agent.capabilities.sandbox.resource import (  # noqa: F401
    SANDBOX_DELEGATED_TOOLS,
    SandboxResource,
)