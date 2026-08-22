"""V2Agent 工具步骤 -> 左面板规划空间（planning_window）桥接测试。

验证 _persist_v2_tool_call / _persist_v2_tool_result：
  - tool_call 消息携带 running 态 ActionOutput（vis 转换器 _act_out_2_plan
    据此刻画工具步骤条目）；
  - 每个工具步骤 upsert_task 挂 TASK 节点到 AGENT 根节点下（触发
    push(new_task_nodes) -> planning_window 渲染）；
  - tool_result 后 TASK 节点重推为 complete/failed 终态。
"""
import pytest

from gyra.agent.core.agent import AgentContext
from gyra.agent.core.memory.agent_memory import AgentMemory
from gyra.agent.core.schema import Status
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.expand.v2_agent import V2Agent


class _StubGptsMemory:
    """记录 append_message / append_work_entry / upsert_task 调用的桩。"""

    def __init__(self):
        self.appended_messages = []
        self.appended_entries = []
        self.task_nodes = []

    async def append_message(self, conv_id, message, **kwargs):
        self.appended_messages.append(message)

    async def append_work_entry(self, conv_id, entry, **kwargs):
        self.appended_entries.append(entry)

    async def upsert_task(self, conv_id, task):
        self.task_nodes.append((conv_id, task))


def _build_agent_with_stub():
    agent = V2Agent()
    agent.bind(
        AgentContext(
            conv_id="conv-plan",
            conv_session_id="sess-plan",
            gpts_app_code="app-plan",
            agent_app_code="app-plan",
            output_process_message=True,
            incremental=True,
        )
    )
    stub = _StubGptsMemory()
    agent.memory = AgentMemory(gpts_memory=stub)
    return agent, stub


def _tool_call_event(tool="Bash", args=None):
    return StepEvent(
        event_id="ev-1",
        step_id="step-1",
        conv_id="conv-plan",
        agent_id="app-plan",
        state=StepState.ACTING,
        event_type="tool_call",
        input={"tool": tool, "input": args or {"command": "ls"}},
        seq=1,
        timestamp=0.0,
    )


def _tool_result_event(content="done", success=True):
    return StepEvent(
        event_id="ev-2",
        step_id="step-1",
        conv_id="conv-plan",
        agent_id="app-plan",
        state=StepState.OBSERVING,
        event_type="tool_result",
        output={"content": content, "is_exe_success": success},
        seq=2,
        timestamp=1.0,
    )


@pytest.mark.asyncio
async def test_tool_call_pushes_running_action_and_task_node():
    agent, stub = _build_agent_with_stub()
    agent._v2_root_node_id = "user-msg-1"

    await agent._persist_v2_tool_call(_tool_call_event())

    assert len(stub.appended_messages) == 1
    msg = stub.appended_messages[0]
    # 消息携带 running 态 ActionOutput：planning_window 工具步骤的数据源
    assert msg.action_report and len(msg.action_report) == 1
    act = msg.action_report[0]
    assert act.name == "Bash"
    assert act.state == Status.RUNNING.value

    # TASK 节点挂到 AGENT 根节点下（与 V1 任务树结构一致）
    assert len(stub.task_nodes) == 1
    conv_id, node = stub.task_nodes[0]
    assert conv_id == "conv-plan"
    assert node.node_id == msg.message_id
    assert node.parent_id == "user-msg-1"
    assert node.content.task_type == "task"
    assert node.content.message_id == msg.message_id
    assert node.state == Status.RUNNING.value

    # pending 队列登记，供 tool_result 配对
    assert len(agent._v2_pending_tool_calls) == 1


@pytest.mark.asyncio
async def test_tool_result_reupserts_task_node_terminal_state():
    agent, stub = _build_agent_with_stub()
    agent._v2_root_node_id = "user-msg-1"
    await agent._persist_v2_tool_call(_tool_call_event())
    message_id = stub.appended_messages[0].message_id

    await agent._persist_v2_tool_result(_tool_result_event(success=True))

    # WorkEntry 已写回（右面板 / 刷新后 action_report 动态重建的数据源）
    assert len(stub.appended_entries) == 1
    entry = stub.appended_entries[0]
    assert entry.tool == "Bash"
    assert entry.message_id == message_id

    # TASK 节点重推为 complete 终态
    assert len(stub.task_nodes) == 2
    _, node = stub.task_nodes[1]
    assert node.state == Status.COMPLETE.value
    # pending 已消费
    assert agent._v2_pending_tool_calls == []


@pytest.mark.asyncio
async def test_tool_result_failed_state():
    agent, stub = _build_agent_with_stub()
    agent._v2_root_node_id = "user-msg-1"
    await agent._persist_v2_tool_call(_tool_call_event())

    await agent._persist_v2_tool_result(
        _tool_result_event(content="boom", success=False)
    )

    _, node = stub.task_nodes[1]
    assert node.state == Status.FAILED.value


@pytest.mark.asyncio
async def test_no_root_node_skips_task_upsert():
    """无根节点（如恢复流程缺 received_message）时静默跳过，不报错。"""
    agent, stub = _build_agent_with_stub()
    agent._v2_root_node_id = None

    await agent._persist_v2_tool_call(_tool_call_event())
    await agent._persist_v2_tool_result(_tool_result_event())

    # 消息与 WorkEntry 照常落，只有规划节点跳过
    assert len(stub.appended_messages) == 1
    assert len(stub.appended_entries) == 1
    assert stub.task_nodes == []
