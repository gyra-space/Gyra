"""
E2B Cloud Sandbox Provider

E2B (https://e2b.dev) 云端沙箱接入。注册为 ``e2b`` provider：
配置 ``sandbox.type = "e2b"`` 即可切换使用云端沙箱。

依赖：``e2b``（可选，``pip install gyra-ext[sandbox_e2b]``）。
"""

from gyra_ext.sandbox.e2b.config import E2BSandboxConfig
from gyra_ext.sandbox.e2b.provider import E2BSandbox
from gyra_ext.sandbox.e2b.shell_client import E2BShellClient
from gyra_ext.sandbox.e2b.file_client import E2BFileClient

__all__ = [
    "E2BSandbox",
    "E2BSandboxConfig",
    "E2BShellClient",
    "E2BFileClient",
]