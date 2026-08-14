"""RFC-005 Step C / RFC-006 Stage 7: mcp capability(工具聚合)迁移测试。

MCP/ToolPack 子类:declare 产工具列表 TOOLS(每个工具一个 ToolEntry)。
"""

from types import SimpleNamespace

from gyra.core.interface.resource.bundle import Slot
from gyra.core.interface.resource.tool_entry import BUILTIN_EXECUTOR_ID


def _make_tool(name="mcp_tool_1", description="an MCP tool"):
    return SimpleNamespace(name=name, description=description)


# =========================================================================== #
# RFC-006 Stage 7: MCPCapability 自管理(对象模型统一)
# =========================================================================== #
def test_mcp_capability_from_tools_declares_tools():
    """from_tools 注入已就绪工具 → declare 产 ToolEntry(Route A builtin)。"""
    from gyra_serve.agent.capabilities.mcp import MCPCapability

    tools = [_make_tool("s1"), _make_tool("s2")]
    cap = MCPCapability.from_tools(tools, name="demo")
    contribs = cap.declare()
    assert len(contribs) == 2
    names = {c.content.tool_name for c in contribs}
    assert names == {"s1", "s2"}
    for c in contribs:
        assert c.slot == Slot.TOOLS
        assert c.capability_id == "mcp:demo"
        assert c.content.executor_id == BUILTIN_EXECUTOR_ID


def test_mcp_capability_empty_when_no_tools():
    from gyra_serve.agent.capabilities.mcp import MCPCapability

    assert MCPCapability(mcp_name="x").declare() == []


# =========================================================================== #
# RFC-006 Stage 8: MCPCapability prepare 自管 preload(连 server + 重建工具)
# =========================================================================== #
async def test_mcp_capability_prepare_loads_tools_from_server(monkeypatch):
    """prepare 调 get_mcp_tool_list，逐工具用 FunctionTool 重建，declare 出 ToolEntry。"""
    from gyra_serve.agent.capabilities.mcp import MCPCapability
    fake_tool = SimpleNamespace(name="mcp_sum", description="sum", inputSchema={"properties": {"a": {"type": "number", "description": "x"}}, "required": ["a"]})
    fake_result = SimpleNamespace(tools=[fake_tool])

    async def _fake_get(mcp_name, server, **kw):
        return fake_result

    monkeypatch.setattr(
        "gyra_serve.agent.capabilities.mcp.capability.get_mcp_tool_list", _fake_get, raising=False
    )
    # mcp_utils 在 prepare 内 import,monkeypatch 顶层 import 名需 patch 真模块
    import gyra_serve.agent.capabilities.mcp.capability as mcp_mod, sys
    # prepare 内 from ...mcp_utils import get_mcp_tool_list —— 用 sys.modules 兜底
    real_utils = sys.modules.get("gyra_serve.agent.resource.tool.mcp_utils")
    import gyra_serve.agent.resource.tool.mcp_utils as utils
    monkeypatch.setattr(utils, "get_mcp_tool_list", _fake_get)

    cap = MCPCapability(
        mcp_name="demo", mcp_servers="http://x/sse", headers={}, tool_id="t1", timeout=10
    )
    await cap.prepare()
    assert cap.capability_id == "mcp:demo"
    contribs = cap.declare()
    assert len(contribs) == 1
    assert contribs[0].content.tool_name == "mcp_sum"
    assert contribs[0].content.executor_id == BUILTIN_EXECUTOR_ID


async def test_mcp_capability_prepare_no_servers_ready():
    from gyra_serve.agent.capabilities.mcp import MCPCapability
    cap = MCPCapability(mcp_name="x", mcp_servers=None)
    await cap.prepare()
    assert cap._status.value == "ready"
    assert cap.declare() == []


async def test_mcp_capability_prepare_degrades_on_failure(monkeypatch):
    """get_mcp_tool_list 抛异常 → 降级(空工具列表,不崩,ready)。"""
    from gyra_serve.agent.capabilities.mcp import MCPCapability
    import gyra_serve.agent.resource.tool.mcp_utils as utils

    async def _boom(*a, **kw):
        raise RuntimeError("server down")

    monkeypatch.setattr(utils, "get_mcp_tool_list", _boom)
    cap = MCPCapability(mcp_name="demo", mcp_servers="http://x/sse")
    await cap.prepare()
    assert cap._status.value == "ready"
    assert cap.declare() == []


# =========================================================================== #
# RFC-006 Phase C: facade.assemble 读 agent.capability_pack(MCP 走纯新协议)
# =========================================================================== #
async def test_facade_assemble_reads_capability_pack_for_mcp(monkeypatch):
    """agent.capability_pack 含 MCPCapability(已 preload 工具)→ facade.assemble
    从 capability_pack 读,declare 出 MCP 工具 ToolEntry(走纯新协议,不翻旧 ToolPack)。"""
    from gyra.agent.capabilities import ResourceFacade
    from gyra.agent.capabilities.facade import _CapabilityDeclareAdapter
    from gyra_serve.agent.capabilities.mcp import MCPCapability
    from gyra.agent.resource import FunctionTool
    from gyra.core.interface.resource.capability import CapabilityPack

    # 造一个已 prepare 的 MCPCapability(自带工具,免 server)
    def _fn(**k):
        return "ok"
    _fn.__doc__ = "d"
    cap = MCPCapability(mcp_name="demo", mcp_servers="http://x/sse")
    cap._tools = [FunctionTool(name="mcp_loaded", func=_fn, description="d")]
    from gyra.core.interface.resource.executor import ExecutorStatus
    cap._status = ExecutorStatus.READY

    pack = CapabilityPack([cap])

    class _FakeAgent:
        capability_pack = pack
        resource = None

    facade = ResourceFacade()
    snap = await facade.assemble(
        agent_id="a1", conv_id="c1", agent=_FakeAgent(),
        identity="id", control_block="ctl",
    )
    # MCP 工具进 snapshot tools
    tool_names = {getattr(c.content, "tool_name", None) for c in snap.tools}
    assert "mcp_loaded" in tool_names


def test_mcp_gyra_alias_registered():
    """Phase D:"mcp(gyra)" 类型(materializer 产出)注册别名,走 MCPCapability。"""
    from gyra.agent.capabilities.registry_factory import CapabilityFactoryRegistry
    from gyra_serve.agent.capabilities.mcp import register_capability_to

    registry = CapabilityFactoryRegistry()
    register_capability_to(registry)
    assert registry.has("tool")
    assert registry.has("mcp(gyra)")
    # mcp(gyra) value 形状(materializer 产出)可直接构建
    cap = registry.get("mcp(gyra)")(
        {
            "mcp_code": "mc-1",
            "name": "my-mcp",
            "mcp_servers": "http://sse.example.com",
            "headers": {"k": "v"},
            "source": "sse",
        }
    )
    assert cap._mcp_name == "my-mcp"
    assert cap._mcp_servers == "http://sse.example.com"
    assert cap._headers == {"k": "v"}
