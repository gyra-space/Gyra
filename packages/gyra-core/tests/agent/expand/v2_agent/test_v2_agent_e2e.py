"""V2Agent 模板端到端测试：换引擎不换车。

验证"标准主 agent（V2 引擎）"在 serve bind 链等价环境下：
  - V2Agent.thinking() 内部由 V2 run_loop（run_step 状态机）驱动，而非 V1 ReAct 循环
  - 工具经 acting_fn 真实执行（echo 工具命中）
  - 最终答案组装为 V1 协议 AgentLLMOut（外层 generate_reply 直接可用）
  - BAIZE vis 桥接：gpts_memory.push_message 被调用（流式 temp_message 渲染）
  - 模板注册：role="V2" + 自动扫描注册（gyra.agent.expand）可被 get_by_name 解析

不依赖真实 LLM 服务：mock AIWrapper.create(stream_out=True) 产 OpenAI 格式流，
第一轮带工具调用、第二轮返回最终答案。
"""
import asyncio
import tempfile
from contextlib import asynccontextmanager

import pytest

from gyra.agent.core.agent import AgentContext
from gyra.agent.core.memory.agent_memory import AgentMemory
from gyra.agent.core.memory.gpts.gpts_memory import GptsMemory
from gyra.agent.core.v2 import DbStateStore, StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.expand.v2_agent import V2Agent
from gyra.agent.util.llm.llm_client import AgentLLMOut


class EchoTool:
    """V2 原生工具：返回 V2ToolResult。"""

    name = "echo"

    async def execute(self, args, context=None):
        from gyra.agent.core.v2.tool_call_types import V2ToolResult

        return V2ToolResult.ok(
            output=f"echo: {args.get('text', '')}", tool_name="echo"
        )


class MockLLMClient:
    """模拟 AIWrapper.create(stream_out=True) 的 OpenAI 格式流。

    rounds: 每轮一次 LLM 请求（一个 step），每轮 yield 若干 AgentLLMOut chunk。
    默认第 1 轮带工具调用，第 2 轮返回最终答案。
    """

    def __init__(self, rounds=None):
        self._rounds = list(rounds or [])
        self._n = 0
        self.call_count = 0

    async def create(self, messages=None, llm_model=None, stream_out=False, **kwargs):
        if self._n >= len(self._rounds):
            return
        outputs = self._rounds[self._n]
        self._n += 1
        self.call_count += 1
        for out in outputs:
            yield out


def _tool_call(name, arguments):
    return {
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def _default_rounds():
    return [
        [
            AgentLLMOut(
                llm_name="test-model",
                content="我先调用工具。",
                tool_calls=[_tool_call("echo", '{"text":"hello"}')],
            )
        ],
        [AgentLLMOut(llm_name="test-model", content="最终答案：完成。")],
    ]


def _build_agent(llm_rounds=None, tools=None):
    """按 serve bind 链等价方式装配 V2Agent（不依赖真实 LLM / serve 层）。

    每个 agent 注入独立的 v2_state_dir（tempdir），保证测试间事件日志隔离。
    """
    agent = _V2AgentForTest(
        v2_state_dir=tempfile.mkdtemp(prefix="v2-e2e-state-")
    )
    agent.bind(
        AgentContext(
            conv_id="conv-e2e",
            conv_session_id="sess-e2e",
            gpts_app_code="app-e2e",
            agent_app_code="app-e2e",
            output_process_message=True,
            incremental=True,
        )
    )
    agent.memory = AgentMemory(gpts_memory=GptsMemory())
    agent.llm_client = MockLLMClient(llm_rounds or _default_rounds())
    agent.llm_config = type("Cfg", (), {"strategy_context": None})()
    agent.available_system_tools = tools or {"echo": EchoTool()}

    return agent


class _V2AgentForTest(V2Agent):
    """测试子类：绕过 ModelConfigCache，固定返回测试模型别名。"""

    async def select_llm_model(self, excluded_models=None):
        return "test-model", None


class _UserMsg:
    """最小 received_message 桩（thinking/listen_thinking_stream 只读 content/observation）。"""

    def __init__(self, content):
        self.content = content
        self.observation = ""



@asynccontextmanager
async def _record_pushes(gm, conv_id):
    """spy gpts_memory.push_message，记录 BAIZE vis 推送的 stream_msg 内容。"""
    real_push = gm.push_message
    recorded: list[dict] = []

    async def spy(*args, **kwargs):
        sm = kwargs.get("stream_msg")
        if isinstance(sm, dict):
            recorded.append(sm)
        return await real_push(*args, **kwargs)

    gm.push_message = spy
    try:
        await asyncio.sleep(0)  # 让 80ms 攒批 flush timer 有机会触发前先让出
        yield recorded
    finally:
        gm.push_message = real_push


@pytest.mark.asyncio
async def test_v2_agent_full_run_and_render():
    """完整运行：run_loop 驱动 + 工具执行 + 最终答案 + BAIZE vis 推送。"""
    agent = _build_agent()

    async with _record_pushes(agent.memory.gpts_memory, "conv-e2e") as pushes:
        result = await agent.thinking(
            messages=[],
            reply_message_id="reply-1",
            received_message=_UserMsg("请帮我跑个流程"),
        )

    # 1) 最终答案（V1 协议输出）
    assert result is not None
    assert "最终答案" in (result.content or "")
    # 中间 step 的旁白不拼进最终答案（只保留最后一个 step 的正文），
    # 避免最终消息 content 出现多段旁白重复
    assert "我先调用工具" not in agent._v2_final_answer
    assert "最终答案" in agent._v2_final_answer

    # 2) 引擎确为 V2 run_loop：状态机事件落盘（durability-before-visibility）
    store: DbStateStore = agent._v2_state_store
    events: list[StepEvent] = await store.get_events("sess-e2e")
    states = [e.state for e in events]
    assert StepState.INIT in states and StepState.DONE in states
    tool_calls = [e for e in events if e.event_type == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0].input.get("tool") == "echo"
    tool_results = [e for e in events if e.event_type == "tool_result"]
    assert any("echo: hello" in e.output.get("content", "") for e in tool_results)

    # 3) BAIZE vis 桥接：gpts_memory.push_message 已推送 temp_message
    assert pushes, "listen_thinking_stream 未推送任何 vis 帧"
    rendered = " ".join(
        (str(p.get("content", "")) + str(p.get("thinking", ""))) for p in pushes
    )
    assert "最终答案" in rendered
    # 中间旁白虽不进入最终答案，但流式推送过程可见
    assert "我先调用工具" in rendered


@pytest.mark.asyncio
async def test_v2_agent_no_tool_round_single_step():
    """无工具调用时一轮即收尾（DONE），最终答案不丢。"""
    agent = _build_agent(llm_rounds=[[AgentLLMOut(llm_name="m", content="直接回答")]])
    result = await agent.thinking(
        messages=[],
        reply_message_id="reply-1",
        received_message=_UserMsg("你好"),
    )
    assert "直接回答" in (result.content or "")

    store: DbStateStore = agent._v2_state_store
    events = await store.get_events("sess-e2e")
    tool_calls = [e for e in events if e.event_type == "tool_call"]
    assert len(tool_calls) == 0


@pytest.mark.asyncio
async def test_v2_agent_tool_denied_by_ruleset():
    """PermissionGate 复用现有规则集：DENY 工具被拦（fail-closed），不执行。"""
    from gyra_core.permission.ruleset import (
        PermissionAction,
        PermissionRule,
        PermissionRuleset,
    )

    agent = _build_agent(tools={"echo": EchoTool()})
    agent.permission_ruleset = PermissionRuleset(
        rules={
            "echo": PermissionRule(
                tool_pattern="echo", action=PermissionAction.DENY
            )
        },
        default_action=PermissionAction.ALLOW,
    )
    result = await agent.thinking(
        messages=[],
        reply_message_id="reply-1",
        received_message=_UserMsg("调用 echo"),
    )

    store: DbStateStore = agent._v2_state_store
    events = await store.get_events("sess-e2e")
    echo_call = [
        e
        for e in events
        if e.event_type == "tool_call" and e.input.get("tool") == "echo"
    ]
    assert len(echo_call) == 1
    assert echo_call[0].output.get("denied") is True
    # 工具未真正执行：无 tool_result 含 echo 输出
    assert not any(
        "echo: hello" in e.output.get("content", "")
        for e in events
        if e.event_type == "tool_result"
    )
    # 即使被拒，最终答案仍正常收尾
    assert result is not None and (result.content or "")


@pytest.mark.asyncio
async def test_v2_agent_registered_and_resolvable():
    """模板注册：role="BIXIU"，gyra.agent.expand 自动扫描可解析（serve 启动路径）。"""
    from gyra.agent.core.agent_manage import get_agent_manager, scan_agents
    from gyra.agent.expand.v2_agent import V2Agent as V2AgentCls

    assert V2AgentCls().role == "BIXIU"

    scanned = scan_agents("gyra.agent.expand")
    assert any(v is V2AgentCls for v in scanned.values())

    # get_by_name 解析（serve _build_agent_by_gpts 的 resolve_agent_name 路径）
    manager = get_agent_manager()
    if "BIXIU" not in (manager.all_agents() or {}):
        manager.after_start()  # 模拟 serve 启动后的自动扫描注册
    agent_cls = manager.get_by_name("BIXIU")
    assert agent_cls is V2AgentCls
    # 别名 "V2"/"V2Agent" 兼容历史存量配置
    assert manager.get_by_name("V2") is V2AgentCls
    assert manager.get_by_name("V2Agent") is V2AgentCls


@pytest.mark.asyncio
async def test_v2_agent_subscribe_step_event():
    """subscribe_step_event（P0 插件化扩展点）：引擎装配前订阅即可收到完整事件。"""
    agent = _build_agent()

    all_seen: list[StepEvent] = []
    executed_seen: list[StepEvent] = []
    # 引擎尚未装配（懒创建），订阅应先挂载到共享 EventStream
    agent.subscribe_step_event(all_seen.append)
    agent.subscribe_step_event(executed_seen.append, event_types=["tool_executed"])

    await agent.thinking(
        messages=[],
        reply_message_id="reply-1",
        received_message=_UserMsg("请帮我跑个流程"),
    )

    # 全量订阅：覆盖 run_loop 各阶段（含 P0 新发射点）
    all_types = [e.event_type for e in all_seen]
    assert "thinking_started" in all_types
    assert "tool_executed" in all_types
    assert "observing_done" in all_types
    assert "step_done" in all_types

    # 过滤订阅：只收到 echo 的 tool_executed，且事件已持久化（durability-before-visibility）
    assert len(executed_seen) == 1
    assert executed_seen[0].input.get("tool") == "echo"
    assert executed_seen[0].output.get("success") is True
    store: DbStateStore = agent._v2_state_store
    persisted_ids = [e.event_id for e in await store.get_events("sess-e2e")]
    assert executed_seen[0].event_id in persisted_ids
