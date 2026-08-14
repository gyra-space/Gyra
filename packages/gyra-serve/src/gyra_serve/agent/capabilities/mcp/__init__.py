"""MCP capability —— MCP 工具聚合自管目录(RFC-005 Step C / RFC-006 Stage 7)。

MCP 资源(ToolPack 子类)是工具聚合:declare 产工具列表 TOOLS。
config→MCPCapability 经 CapabilityFactoryRegistry(register_capability_to)构造。
注:facade 时序 declare 先于 prepare,MCP 工具列表来自 preload_resource I/O
(对象非 str,无法 DataRequirement 占位)。详见 capability.py。
"""

from .capability import MCPCapability  # noqa: F401

__all__ = ["MCPCapability"]


def register(registry) -> None:
    pass


def build_capability(value, system_app=None):
    """RFC-006 Stage 7:从 config 构造 MCPCapability(工具对象需 preload,config 暂产空)。"""
    return MCPCapability.from_config(value, system_app)


# RFC-006 Phase A:供 CapabilityFactoryRegistry 构造期 build_pack 用。
CAPABILITY_TYPE_KEY = "tool"


def register_capability_to(registry) -> None:
    registry.register(CAPABILITY_TYPE_KEY, build_capability)
    # Phase D:materializer/agent_chat/playbook 产出 "mcp(gyra)" 类型,
    # value 结构与 from_config 兼容,注册别名使旧路径退场后仍可构建。
    registry.register("mcp(gyra)", build_capability)
