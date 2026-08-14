"""Memory capability —— 记忆能力自管目录(RFC-005 Step D / RFC-006 Stage 5)。

记忆资源是配置载体 + Consumer(检索回注)。declare 空,consume 提供接口。
config→MemoryCapability 经 CapabilityFactoryRegistry(register_capability_to)构造。
注:记忆真检索走 _memory_bundle 独立路径,本轮只统一对象模型,不接 consume/execute
生产路径(留待后续)。
"""

from .capability import MemoryCapability  # noqa: F401

__all__ = ["MemoryCapability"]


def register(registry) -> None:
    pass


def build_capability(value, system_app=None):
    """RFC-006:从 config dict 构造 MemoryCapability(无 I/O)。"""
    return MemoryCapability.from_config(value, system_app)


# RFC-006 Phase A:供 CapabilityFactoryRegistry 构造期 build_pack 用。
CAPABILITY_TYPE_KEY = "memory"


def register_capability_to(registry) -> None:
    registry.register(CAPABILITY_TYPE_KEY, build_capability)
