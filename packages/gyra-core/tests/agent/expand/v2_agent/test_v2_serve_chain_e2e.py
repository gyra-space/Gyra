"""V2Agent serve 装配语义端到端测试。

覆盖服务链路级的关键装配点（不依赖真实 LLM/DB/HTTP 服务）：
  1. 生产注册：AgentManager.register_agent + get_by_name('V2') 命中 V2Agent
     （对应 serve 层 _build_agent_by_gpts 的 resolve_agent_name -> get_by_name 路径）；
  2. V1 外层循环：thinking -> act -> verify 完整序列（V1 generate_reply 的核心）,
     内部由 V2 run_loop 驱动多步工具循环；
  3. 事件投影事实源：LLM 第二轮收到的 messages 含事件日志投影的
     assistant tool_calls + tool 结果（model-visible = logged）；
  4. BAIZE vis 桥接：gpts_memory.push_message 被调用（流式渲染）；
  5. 会话持久化：工具调用消息写回 gpts_memory（WorkEntry + tool_calls）；
  6. 跨实例恢复：同一 v2_state_dir 重建 Agent 后仍能从事件日志投影出历史
     （真实持久化验证）。
"""
import tempfile
from unittest.mock import MagicMock

import pytest

from gyra.agent.core.agent import AgentContext
from gyra.agent.core.memory.agent_memory import AgentMemory
from gyra.agent.core.memory.gpts.gpts_memory import GptsMemory
from gyra.agent.core.v2 import StepEvent
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
    """模拟 AIWrapper.create(stream_out=True)。

    记录每次请求的 messages，供断言事件投影是否进入模型上下文。
    """

    def __init__(self, rounds=None):
        self._rounds = list(rounds or [])
        self._n = 0
        self.call_count = 0
        self.received_messages = []  # 每次 create 收到的 messages

    async def create(self, messages=None, llm_model=None, stream_out=False, **kwargs):
        self.received_messages.append(list(messages or []))
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


class _V2AgentForTest(V2Agent):
    """测试子类：绕过 ModelConfigCache，固定返回测试模型别名。"""

    async def select_llm_model(self, excluded_models=None):
        return "test-model", None


class _UserMsg:
    def __init__(self, content):
        self.content = content
        self.observation = ""


def _build_agent(state_dir, llm_rounds=None, tools=None):
    agent = _V2AgentForTest(v2_state_dir=state_dir)
    agent.bind(
        AgentContext(
            conv_id="conv-serve-e2e",
            conv_session_id="sess-serve-e2e",
            gpts_app_code="app-serve-e2e",
            agent_app_code="app-serve-e2e",
            output_process_message=True,
            incremental=True,
        )
    )
    agent.memory = AgentMemory(gpts_memory=GptsMemory())
    agent.llm_client = MockLLMClient(llm_rounds)
    agent.llm_config = type("Cfg", (), {"strategy_context": None})()
    agent.available_system_tools = tools or {"echo": EchoTool()}
    return agent


def _default_rounds():
    """第 1 轮工具调用（echo hello），第 2 轮最终答案。"""
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


# =============================================================================
# 1. 生产注册路径
# =============================================================================


def test_agent_manager_registers_v2_agent():
    """AgentManager 注册 V2Agent（对外主名 PIXIU/貔貅），get_by_name 命中（serve 装配路径）。"""
    from gyra.agent.core.agent_manage import AgentManager

    manager = AgentManager(system_app=MagicMock())
    profile = manager.register_agent(V2Agent)
    assert profile == "PIXIU"
    cls = manager.get_by_name("PIXIU")
    assert cls is V2Agent
    # 别名也命中（resolve_agent_name 兼容，历史 app.agent=V2 可无缝迁移）
    resolved = manager.get_by_name("V2")
    assert resolved is V2Agent
    resolved_alias2 = manager.get_by_name("V2Agent")
    assert resolved_alias2 is V2Agent


# =============================================================================
# 2. V1 外层循环（thinking -> act -> verify）+ 事件投影 + vis + 会话持久化
# =============================================================================


@pytest.mark.asyncio
async def test_v2_serve_chain_full_loop():
    """V1 外层循环驱动 V2 内核：工具执行 → 投影进模型 → 最终答案 → vis → 会话。"""
    state_dir = tempfile.mkdtemp(prefix="v2-serve-chain-")
    agent = _build_agent(state_dir, llm_rounds=_default_rounds())

    gm = agent.memory.gpts_memory
    pushed = []
    real_push = gm.push_message

    async def spy_push(*args, **kwargs):
        sm = kwargs.get("stream_msg")
        if isinstance(sm, dict):
            pushed.append(sm)
        return await real_push(*args, **kwargs)

    gm.push_message = spy_push
    received_msg = _UserMsg("帮我调用 echo hello")

    # ---- V1 外层循环：thinking（内部 V2 run_loop 完成多步）→ act → verify ----
    llm_out = await agent.thinking(
        messages=[],
        reply_message_id="reply-1",
        received_message=received_msg,
    )
    outputs = await agent.act(received_msg, sender=agent)
    passed, reason = await agent.verify(received_msg, sender=agent)

    # 1) 最终答案与收尾
    assert "最终答案：完成。" in (llm_out.content or "")
    assert passed is True
    assert any(o.terminate for o in outputs)

    # 2) 事件日志持久化到真实 StateStore（非 tempdir）
    store = agent._v2_state_store
    events = await store.get_events("sess-serve-e2e")
    assert len(events) > 0
    assert events[-1].state is StepState.DONE
    tool_calls = [e for e in events if e.event_type == "tool_call"]
    tool_results = [e for e in events if e.event_type == "tool_result"]
    assert len(tool_calls) == 1 and len(tool_results) == 1

    # 3) 事件投影进入模型上下文（LLM 第二轮看到工具执行事实，model-visible=logged）
    assert agent.llm_client.call_count == 2
    second_messages = agent.llm_client.received_messages[1]
    roles = [m.get("role") for m in second_messages]
    assert "assistant" in roles and "tool" in roles
    tool_msg = next(m for m in second_messages if m.get("role") == "tool")
    assert "echo: hello" in tool_msg["content"]
    # 投影的 assistant tool_calls 与 tool 消息 tool_call_id 一致
    asst_msg = next(
        m for m in second_messages
        if m.get("role") == "assistant" and m.get("tool_calls")
    )
    assert asst_msg["tool_calls"][0]["function"]["name"] == "echo"
    assert asst_msg["tool_calls"][0]["id"] == tool_msg["tool_call_id"]

    # 4) BAIZE vis 桥接：流式推送发生
    assert pushed, "V2 run_loop 的 llm_token 应桥回 BAIZE vis"

    # 5) 会话持久化：工具调用消息 + WorkEntry 写回 gpts_memory
    work_log = await gm.get_work_log("conv-serve-e2e")
    assert work_log, "工具执行结果应写回 WorkEntry"
    assert any(
        getattr(w, "tool", "") == "echo" for w in work_log
    ), "WorkEntry 应记录 echo 工具"


# =============================================================================
# 3. 跨实例恢复（真实持久化）
# =============================================================================


@pytest.mark.asyncio
async def test_v2_serve_chain_cross_instance_recovery():
    """同一 state_dir 重建 Agent：事件日志跨实例可投影（真实持久化）。"""
    state_dir = tempfile.mkdtemp(prefix="v2-serve-chain-")

    # 实例 A：跑一轮工具
    agent_a = _build_agent(state_dir, llm_rounds=_default_rounds())
    await agent_a.thinking(
        messages=[],
        reply_message_id="reply-1",
        received_message=_UserMsg("帮我调用 echo hello"),
    )

    # 实例 B：同 state_dir 重建（模拟重启/另一进程）
    agent_b = _build_agent(state_dir, llm_rounds=[])

    # 投影仍能读全事件（含对话消息 + 工具历史）——懒创建 store 从真实持久目录恢复
    store_b = agent_b._ensure_v2_state_store()
    events = await store_b.get_events("sess-serve-e2e")
    assert len(events) > 0
    # V2 单源：完整上下文（user/assistant/tool + 结果）跨实例可从事件日志重建
    projected = await agent_b._v2_build_full_context()
    roles = [m.get("role") for m in projected]
    assert "user" in roles and "assistant" in roles and "tool" in roles
    assert any("echo: hello" in str(m.get("content", "")) for m in projected)


# =============================================================================
# 4. 权限拦截（serve 规则集复用）
# =============================================================================


@pytest.mark.asyncio
async def test_v2_serve_chain_ruleset_deny():
    """serve 规则集复用：DENY 工具被拦（fail-closed），不执行。"""
    from gyra_core.permission.ruleset import (
        PermissionAction,
        PermissionRule,
        PermissionRuleset,
    )

    state_dir = tempfile.mkdtemp(prefix="v2-serve-chain-")
    agent = _build_agent(
        state_dir,
        llm_rounds=[
            [
                AgentLLMOut(
                    llm_name="test-model",
                    content="调用工具",
                    tool_calls=[_tool_call("echo", '{"text":"x"}')],
                )
            ],
            [AgentLLMOut(llm_name="test-model", content="结束")],
        ],
    )
    agent.permission_ruleset = PermissionRuleset(
        rules={
            "echo": PermissionRule(tool_pattern="echo", action=PermissionAction.DENY)
        },
        default_action=PermissionAction.ALLOW,
    )

    await agent.thinking(
        messages=[],
        reply_message_id="reply-1",
        received_message=_UserMsg("调用 echo"),
    )

    events = await agent._v2_state_store.get_events("sess-serve-e2e")
    echo_calls = [
        e for e in events
        if e.event_type == "tool_call" and e.input.get("tool") == "echo"
    ]
    assert len(echo_calls) == 1
    # DENY 的工具不产生 tool_result（未执行）
    assert not [e for e in events if e.event_type == "tool_result"]
