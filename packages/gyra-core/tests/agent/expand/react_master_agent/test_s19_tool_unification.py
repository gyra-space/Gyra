"""RFC-005 S19 工具执行面与声明面同源验证。

验证 ToolAction.run 的工具句柄查找(经 agent.resolve_tool_entry)与 function_calling_params
(经 snapshot.all_tools)取自同一 snapshot,消除多 dict 两源不一致。
"""

from gyra.core.interface.resource.bundle import CacheScope, Contribution, Lifetime, Slot
from gyra.core.interface.resource.tool_entry import BUILTIN_EXECUTOR_ID, ToolEntry
from gyra.core.interface.resource.capability import Capability
from gyra.agent.capabilities.facade import ResourceFacade


class _FakeSandboxClient:
    provider = staticmethod(lambda: "local")
    skill_dir = "/s"


class _FakeAgent:
    """模拟 react_master_agent 的关键面:resolve_tool_entry + _last_snapshot。"""

    def __init__(self, snapshot):
        self._last_snapshot = snapshot

    def resolve_tool_entry(self, tool_name: str):
        snap = getattr(self, "_last_snapshot", None)
        if snap is None:
            return None
        from gyra.core.interface.resource.dispatcher import ToolDispatcher

        idx = ToolDispatcher.build_index(snap.all_tools())
        entry = idx.get(tool_name)
        if entry is None:
            return None
        tool = getattr(entry, "tool", None)
        if tool is None:
            tool = getattr(entry, "content", None)
        while (
            tool is not None
            and hasattr(tool, "tool_name")
            and hasattr(tool, "tool")
            and not hasattr(tool, "to_openai_tool")
        ):
            tool = tool.tool
        return tool


async def _make_snapshot_with_tools():
    from gyra.agent.resource import FunctionTool

    def _fn(**kw):
        return "ok"

    spawn = FunctionTool(name="spawn_agent_task", func=_fn, description="spawn")
    run_py = FunctionTool(name="run_python", func=_fn, description="run python")

    facade = ResourceFacade()
    return await facade.assemble(
        agent_id="canvas-agent", conv_id="c1",
        identity="id", control_block="ctl",
        builtin_tools={"spawn_agent_task": spawn, "run_python": run_py},
    )


# --------------------------------------------------------------------------- #
# resolve_tool_entry 与 function_calling_params 同源
# --------------------------------------------------------------------------- #
async def test_resolve_tool_entry_finds_builtin_tools():
    """执行面 resolve_tool_entry 能查到声明面 builtin tools。"""
    snap = await _make_snapshot_with_tools()
    agent = _FakeAgent(snap)
    assert agent.resolve_tool_entry("spawn_agent_task") is not None
    assert agent.resolve_tool_entry("run_python") is not None


async def test_resolve_and_declare_share_same_handle():
    """声明面(snapshot.all_tools)与执行面(resolve_tool_entry)返回同一句柄。"""
    snap = await _make_snapshot_with_tools()
    agent = _FakeAgent(snap)

    # 声明面:function_calling_params 会用 snapshot.all_tools() 转的句柄
    declared_handles = {}
    for entry in snap.all_tools():
        handle = getattr(entry, "tool", None) or getattr(entry, "content", None)
        name = getattr(entry, "tool_name", None) or getattr(handle, "name", None)
        declared_handles[name] = handle

    # 执行面:resolve_tool_entry 返回的句柄
    for name in ("spawn_agent_task", "run_python"):
        resolved = agent.resolve_tool_entry(name)
        assert resolved is declared_handles[name]  # 同一对象


async def test_resolve_unknown_returns_none():
    snap = await _make_snapshot_with_tools()
    agent = _FakeAgent(snap)
    assert agent.resolve_tool_entry("nonexistent_tool") is None


async def test_resolve_without_snapshot_returns_none():
    agent = _FakeAgent(None)
    assert agent.resolve_tool_entry("spawn_agent_task") is None


async def test_builtin_tools_marked_agent_builtin():
    """builtin 工具的 ToolEntry.executor_id==agent:builtin(派发器据此走 builtin 回调)。"""
    snap = await _make_snapshot_with_tools()
    for entry in snap.builtin_tools:
        assert entry.executor_id == BUILTIN_EXECUTOR_ID
        assert entry.capability_id == "agent:builtin"


# --------------------------------------------------------------------------- #
# capability 声明工具(memory 工具形态):Contribution(content=ToolEntry)
# --------------------------------------------------------------------------- #
class _FakeMcpLikeCapability(Capability):
    """模拟 MCPCapability.declare:TOOLS 槽产 Contribution(content=ToolEntry)。"""

    def __init__(self, tools):
        self._tools = tools

    @property
    def capability_id(self) -> str:
        return "mcp:memory_tools"

    def declare(self, config=None):
        return [
            Contribution(
                capability_id=self.capability_id,
                slot=Slot.TOOLS,
                content=ToolEntry(
                    tool_name=t.name,
                    tool=t,
                    capability_id=self.capability_id,
                    executor_id=BUILTIN_EXECUTOR_ID,
                    description=getattr(t, "description", "") or "",
                ),
                lifetime=Lifetime.CONFIG_STATIC,
                cache_scope=CacheScope.NONE,
                order=60,
            )
            for t in self._tools
        ]

    async def prepare(self) -> None:
        pass

    async def execute(self, call):
        raise NotImplementedError

    async def release(self, reason) -> None:
        pass


async def _make_snapshot_with_capability_tools():
    from gyra.agent.resource import FunctionTool
    from gyra.core.interface.resource.capability import CapabilityPack

    def _fn(**kw):
        return "ok"

    tools = [
        FunctionTool(name="memory_save", func=_fn, description="save"),
        FunctionTool(name="memory_remember", func=_fn, description="remember"),
    ]
    facade = ResourceFacade()
    return await facade.assemble(
        agent_id="canvas-agent",
        conv_id="c1",
        resource_root=CapabilityPack([_FakeMcpLikeCapability(tools)]),
        identity="id-cap",
        control_block="ctl-cap",
    ), tools


async def test_resolve_tool_entry_finds_capability_declared_tools():
    """capability 工具(Contribution(content=ToolEntry))执行面必须可查。

    回归:memory 工具经 MCPCapability.declare 后,LLM 声明面可见
    (function_calling_params 经 _tool_from_entry 解包),但执行面
    build_index 不识别该形态 → "Tool 'memory_save' not found in resources"。
    """
    from gyra.core.interface.resource.dispatcher import ToolDispatcher

    snap, tools = await _make_snapshot_with_capability_tools()
    idx = ToolDispatcher.build_index(snap.all_tools())
    assert "memory_save" in idx
    assert "memory_remember" in idx

    agent = _FakeAgent(snap)
    for tool in tools:
        resolved = agent.resolve_tool_entry(tool.name)
        assert resolved is tool


async def test_capability_declared_tool_declare_and_execute_same_handle():
    """声明面(function_calling_params 视角)与执行面取同一工具句柄。"""
    snap, tools = await _make_snapshot_with_capability_tools()
    agent = _FakeAgent(snap)
    for tool in tools:
        assert agent.resolve_tool_entry(tool.name) is tool
