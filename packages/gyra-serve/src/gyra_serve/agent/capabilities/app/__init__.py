"""App(子 Agent)capability —— 自管目录(RFC-005 Step B / RFC-006 Stage 4)。

App 资源纯声明类:declare app 描述,无 I/O。
config→AppCapability 经 CapabilityFactoryRegistry(register_capability_to)构造。
"""

from .capability import AppCapability  # noqa: F401

__all__ = ["AppCapability"]


def register(registry) -> None:
    pass


def build_capability(value, system_app=None):
    """RFC-006:从 AgentResource.value dict 构造 AppCapability(无 I/O)。"""
    return AppCapability.from_config(value, system_app)


# RFC-006 Phase A:供 CapabilityFactoryRegistry 构造期 build_pack 用。
CAPABILITY_TYPE_KEY = "app"


def register_capability_to(registry) -> None:
    """注册 build_capability 到 CapabilityFactoryRegistry(构造期产 CapabilityPack)。"""
    registry.register(CAPABILITY_TYPE_KEY, build_capability)
