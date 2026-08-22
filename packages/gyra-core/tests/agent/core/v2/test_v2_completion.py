"""V2 缺失补全回归测试。

覆盖：
1. run_step 在 thinking 收尾 emit usage_metric StepEvent（TokenMeter 事实源）
2. default_thinking 的 operational_reminders_provider 注入 + context_manager pre_step
3. SubAgentRuntime 生产接线（default thinking/acting fn + session/system_prompt 透传）
"""
import os
import tempfile

import pytest

from gyra.agent.core.v2.runtime import run_step
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.subagent_runtime import SubAgentRuntime, SubAgentSpawnSpec


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = DbStateStore(path)
    yield s
    os.unlink(path)


# --------------------------------------------------------------------------- #
# 1. usage_metric StepEvent（TokenMeter 事实源）
# --------------------------------------------------------------------------- #

async def test_run_step_emits_usage_metric_event(store):
    """thinking 带 usage 时，run_step 收尾 emit 一次 usage_metric 事件。"""
    async def thinking(input_):
        # 流式多帧携带同一最终 metrics（模拟 AIWrapper 累积输出）
        yield {"token": "a", "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105}}
        yield {"token": "b", "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105}}

    events = []
    async for e in run_step(
        "agent-1", "conv-1", {"prompt": "hi"}, store, thinking,
        request_meta={"model": "test-model"},
    ):
        events.append(e)

    usage_events = [e for e in events if e.event_type == "usage_metric"]
    assert len(usage_events) == 1, "每 LLM 调用恰好 emit 一次 usage_metric"
    out = usage_events[0].output
    assert out["this_call"] == {"prompt": 100, "completion": 5, "total": 105, "cached": 0}
    assert out["model"] == "test-model"
    assert out["cumulative"]["total"] == 105


async def test_run_step_no_usage_no_usage_metric(store):
    """thinking 不带 usage 时不 emit usage_metric（不破坏旧行为）。"""
    async def thinking(input_):
        yield {"token": "no usage"}

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, thinking):
        events.append(e)

    assert not [e for e in events if e.event_type == "usage_metric"]


async def test_run_step_usage_metric_is_persisted_and_aggregated(store):
    """usage_metric 事件落库，TokenMeter.snapshot 可重算累计。"""
    from gyra.agent.core.v2.token_meter import TokenMeter

    async def thinking(input_):
        yield {"token": "a", "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}}

    async for _e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, thinking):
        pass

    meter = TokenMeter(store, "conv-1", model="test-model")
    snap = await meter.snapshot()
    assert snap.total == 12
    assert snap.prompt == 10
    assert snap.completion == 2


# --------------------------------------------------------------------------- #
# 2. default_thinking：operational reminders + context_manager.pre_step
# --------------------------------------------------------------------------- #

async def test_default_thinking_injects_operational_reminders():
    from gyra.agent.core.v2.default_thinking import make_default_thinking_fn

    captured = {}

    async def llm_stream(messages, model):
        captured["messages"] = messages
        yield {"token": "done"}

    class _FakeManager:
        async def retrieve_relevant_memories(self, query, **kw):
            return ""

    class _FakePipeline:
        async def consume_prefetch(self, **kw):
            return None
        def scrub_stream_delta(self, token):
            return token

    class _FakeMemoryBundle:
        pipeline = _FakePipeline()
        manager = _FakeManager()

    async def _reminders():
        return "[异步任务完成通知]\nmedia done"

    fn = make_default_thinking_fn(
        llm_stream_fn=llm_stream,
        model_alias="m",
        memory_bundle=_FakeMemoryBundle(),
        context_provider=lambda *a, **k: [{"role": "assistant", "content": "prev"}],
        operational_reminders_provider=_reminders,
    )

    async for _chunk in fn({"prompt": "hi", "conv_id": "c", "session_id": "s"}):
        pass

    msgs = captured["messages"]
    # 运行提醒是每轮动态参考块，不入 system；作为独立 user 消息插在动态参考位
    # （AST 默认无 system 模板，故这里无 system 消息）。
    assert not [m for m in msgs if m.get("role") == "system"]
    # 关键：用户最新输入是消息列表**最后一条** user，动态参考（提醒）在其前 → 让
    # 模型聚焦当前指令，且前缀维持稳定。
    assert msgs[-1] == {"role": "user", "content": "hi"}
    assert msgs[-2] == {"role": "user", "content": "[异步任务完成通知]\nmedia done"}


async def test_default_thinking_applies_context_manager_pre_step():
    from gyra.agent.core.v2.default_thinking import make_default_thinking_fn

    captured = {}
    pre_calls = []

    class _FakeCM:
        async def pre_step(self, messages):
            pre_calls.append(len(messages))
            return [{"role": "user", "content": "spilled"}]  # 模拟 spill 后消息

    async def llm_stream(messages, model):
        captured["messages"] = messages
        yield {"token": "x"}

    class _FakeManager:
        async def retrieve_relevant_memories(self, query, **kw):
            return ""

    class _FakePipeline:
        async def consume_prefetch(self, **kw):
            return None

    class _FakeMemoryBundle:
        pipeline = _FakePipeline()
        manager = _FakeManager()

    fn = make_default_thinking_fn(
        llm_stream_fn=llm_stream,
        model_alias="m",
        memory_bundle=_FakeMemoryBundle(),
        context_provider=lambda *a, **k: [{"role": "assistant", "content": "p"}],
        context_manager=_FakeCM(),
    )

    async for _chunk in fn({"prompt": "hi", "conv_id": "c", "session_id": "s"}):
        pass

    assert pre_calls, "context_manager.pre_step 应在 LLM 调用前执行"
    # LLM 实际收到的是 spill 后的消息
    assert captured["messages"] == [{"role": "user", "content": "spilled"}]


# --------------------------------------------------------------------------- #
# 3. SubAgentRuntime 生产接线（default fn + session/system_prompt 透传）
# --------------------------------------------------------------------------- #

async def test_subagent_runtime_uses_default_fns_and_input_fields(store):
    """spawn spec 未携带 fn 时回退装配层 default，input_ 携带子会话字段。"""
    seen = {}

    async def sub_thinking(input_):
        seen["input_"] = dict(input_)
        yield {"token": "sub answer"}

    async def sub_acting(tool_call, ctx):
        from gyra.agent.core.v2.tool_call_types import V2ToolResult
        return V2ToolResult(success=True, output="ok", tool_name="echo")

    runtime = SubAgentRuntime(
        state_store=store,
        default_thinking_fn=sub_thinking,
        default_acting_fn=sub_acting,
        default_user_id="u-1",
    )
    spec = SubAgentSpawnSpec(
        agent_name="BAIZE",
        task="do it",
        parent_step_id="step-1",
        parent_conv_id="conv-parent",
        parent_agent_id="agent-1",
        system_prompt="sub system",
    )
    handle = await runtime.spawn(spec)

    assert handle.status.value == "done"
    assert seen["input_"]["is_subagent"] is True
    # 子 agent 独立会话绑定：session_id = sub_conv_id，conv_id = sub_conv_id
    assert seen["input_"]["session_id"] == handle.sub_conv_id
    assert seen["input_"]["conv_id"] == handle.sub_conv_id
    assert seen["input_"]["system_prompt"] == "sub system"
    assert seen["input_"]["user_id"] == "u-1"


async def test_subagent_runtime_spec_fns_take_precedence(store):
    """显式 spec fn 优先于 default fn。"""
    async def default_thinking(input_):
        yield {"token": "default"}

    async def spec_thinking(input_):
        yield {"token": "spec"}

    runtime = SubAgentRuntime(state_store=store, default_thinking_fn=default_thinking)
    spec = SubAgentSpawnSpec(
        agent_name="X",
        task="t",
        parent_step_id="s",
        parent_conv_id="c",
        parent_agent_id="a",
        thinking_fn=spec_thinking,
    )
    handle = await runtime.spawn(spec)
    assert handle.status.value == "done"
    assert handle.result["events_count"] >= 1


# --------------------------------------------------------------------------- #
# 4. run_loop 层子 agent 端到端（生产路径：LLM 发 spawn_subagent → 子 agent 执行）
# --------------------------------------------------------------------------- #

async def test_run_loop_subagent_e2e_no_turn_interrupt(store):
    """P0 回归：run_loop 遇 AWAITING_SUB_AGENT 不再中断 turn。

    主 agent LLM 第一轮发 spawn_subagent tool_call，子 agent 执行并返回答案；
    run_loop 必须完整消费（子 agent 真实执行 + tool_result 回传），
    而不是在 subagent_spawn 事件处提前 return 导致 spawn 永不执行。
    """
    from gyra.agent.core.v2.run_loop import run_loop
    from gyra.agent.core.v2.thinking_chunk import ToolCallChunk, TokenChunk
    from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult

    sub_seen = {}

    async def sub_thinking(input_):
        sub_seen["input"] = dict(input_)
        # 子 agent 直接产出答案（无需工具）
        yield {"token": "391"}

    async def sub_acting(tool_call, ctx):
        return V2ToolResult(success=True, output="ok", tool_name="echo")

    sub_runtime = SubAgentRuntime(
        state_store=store,
        default_thinking_fn=sub_thinking,
        default_acting_fn=sub_acting,
    )

    # 主 agent thinking：第一轮发 spawn_subagent，第二轮产出最终结论
    round_no = {"n": 0}

    async def main_thinking(input_):
        round_no["n"] += 1
        if round_no["n"] == 1:
            yield ToolCallChunk(tool_calls=[V2ToolCall(
                name="spawn_subagent",
                args={"agent_name": "BAIZE", "task": "compute 17*23", "run_in_background": False},
            )])
        else:
            yield {"token": "sub result: 391"}

    async def main_acting(tool_call, ctx):
        return V2ToolResult(success=True, output="handled", tool_name=tool_call.name)

    events = []
    async for ev in run_loop(
        agent_id="main-1",
        conv_id="conv-main",
        input_={"prompt": "spawn subagent", "conv_id": "conv-main", "session_id": "conv-main"},
        state_store=store,
        thinking_fn=main_thinking,
        acting_fn=main_acting,
        subagent_runtime=sub_runtime,
        max_steps=10,
    ):
        events.append(ev)

    types = [e.event_type for e in events]
    assert "subagent_spawn" in types, f"应产出 subagent_spawn, got {types}"
    assert "tool_result" in types
    # 子 agent 真实执行：input_ 携带独立子会话绑定
    assert sub_seen["input"]["is_subagent"] is True
    assert sub_seen["input"]["session_id"] != "conv-main"
    # 子 agent 答案已收集（handle.result.answer）
    sub_result = next(
        e.output for e in events
        if e.event_type == "tool_result" and (e.output or {}).get("task_id")
    )
    assert sub_result.get("result", {}).get("answer") == "391"
    # run_loop 完整收尾：主 agent 第二轮产出最终 token
    assert "llm_token" in types and "step_done" in types


# --------------------------------------------------------------------------- #
# 5. 图片多模态：媒体提取 + thinking 多模态 user 消息
# --------------------------------------------------------------------------- #

async def test_v2agent_extract_media_items():
    """媒体段（图片/音频/视频/文件）转 OpenAI 多模态 content items。"""
    from gyra.agent.expand.v2_agent.v2_agent import V2Agent

    content = [
        {"type": "text", "object": {"data": "看这张图"}},
        {"type": "file", "object": {
            "data": "data:image/png;base64,AAA", "name": "a.png", "extension": "png",
        }},
        {"type": "file", "object": {
            "data": "data:audio/mp3;base64,BBB", "name": "s.mp3", "extension": "mp3",
        }},
    ]
    items = V2Agent._extract_media_items(content)
    types = [i["type"] for i in items]
    assert "image_url" in types, f"图片应转 image_url, got {types}"
    assert "audio_url" in types, f"音频应转 audio_url, got {types}"
    img = next(i for i in items if i["type"] == "image_url")
    assert img["image_url"]["url"].startswith("data:image")
    # 文本项被跳过（由 _extract_text_from_content 处理）
    assert all(i["type"] != "text" for i in items)


async def test_default_thinking_multimodal_user_message():
    """default_thinking 带 media_items 时 user 消息 content 为数组。"""
    from gyra.agent.core.v2.default_thinking import make_default_thinking_fn

    captured = {}

    async def llm_stream(messages, model):
        captured["messages"] = messages
        yield {"token": "x"}

    class _FakeManager:
        async def retrieve_relevant_memories(self, query, **kw):
            return ""

    class _FakePipeline:
        async def consume_prefetch(self, **kw):
            return None

    class _FakeMemoryBundle:
        pipeline = _FakePipeline()
        manager = _FakeManager()

    fn = make_default_thinking_fn(
        llm_stream_fn=llm_stream,
        model_alias="m",
        memory_bundle=_FakeMemoryBundle(),
        context_provider=lambda *a, **k: [],
    )
    async for _c in fn({
        "prompt": "描述图片",
        "conv_id": "c",
        "session_id": "s",
        "media_items": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}}],
    }):
        pass

    user = captured["messages"][-1]
    assert user["role"] == "user"
    assert isinstance(user["content"], list)
    assert user["content"][0] == {"type": "text", "text": "描述图片"}
    assert user["content"][1]["type"] == "image_url"


# --------------------------------------------------------------------------- #
# 6. ContextManager emit_fn：compaction/summary 事件持久化
# --------------------------------------------------------------------------- #

async def test_v2runtime_cm_emit_persists_events(store):
    """V2AgentRuntime 注入 emit_fn 后，ContextManager 事件真实落库。"""
    from gyra.agent.core.v2.agent_runtime import V2AgentRuntime
    from gyra.agent.core.v2.context_manager import ContextManager
    from gyra.agent.core.v2.event_stream import EventStream

    async def thinking(input_):
        yield {"token": "hi"}

    async def acting(tool_call, ctx):
        from gyra.agent.core.v2.tool_call_types import V2ToolResult
        return V2ToolResult(success=True, output="ok", tool_name="x")

    runtime = V2AgentRuntime(
        agent_id="a", conv_id="c1",
        state_store=store, thinking_fn=thinking, acting_fn=acting,
        event_stream=EventStream(store),
    )
    assert runtime._context_manager is not None
    # _cm_emit 写 compaction/audit 事件
    ev = await runtime._cm_emit("observing", "compaction/summary",
                                input_data={"compaction": True},
                                output_data={"summary": "s", "compacted_event_ids": []})
    assert ev.event_type == "compaction/summary"
    assert ev.seq >= 0  # 空 store 从 0 起，与会话 seq 单调对齐
    # 事件已持久化，可从 store 读回（TokenMeter/Projector 事实源）
    events = await store.get_events("c1")
    assert any(e.event_type == "compaction/summary" for e in events)
    # 连续两次 emit seq 单调递增
    ev2 = await runtime._cm_emit("observing", "compaction/end", output_data={})
    assert ev2.seq > ev.seq


# --------------------------------------------------------------------------- #
# 7. 工具历史投影量级控制（多轮追问不丢近期工具事实）
# --------------------------------------------------------------------------- #

async def test_trim_tool_history_keeps_recent_and_pairs():
    """工具历史投影按预算截断：保留最近调用、成对完整。"""
    from gyra.agent.expand.v2_agent.v2_agent import V2Agent

    class FakeSelf:
        async def get_agent_llm_context_length(self):
            return 4000  # 预算 = max(600, 2000) = 2000 token

    # 50 个工具调用（100 条消息），工具结果带较长输出，远超预算
    msgs = []
    for i in range(50):
        msgs.append({"role": "assistant", "content": "",
                     "tool_calls": [{"id": f"c{i}", "type": "function",
                                     "function": {"name": "Bash", "arguments": f'{{"cmd": "cmd {i}"}}'}}]})
        msgs.append({"role": "tool", "tool_call_id": f"c{i}",
                     "content": f"结果{i} " + "x" * 300})

    out = await V2Agent._trim_tool_history(FakeSelf(), msgs)
    assert len(out) < len(msgs), "应截断"
    # 最近的调用保留
    ids = [m.get("tool_call_id") for m in out if m.get("role") == "tool"]
    assert "c49" in ids, "最近一次工具调用必须保留（多轮追问可答）"
    assert max(int(x[1:]) for x in ids) == 49
    # 成对完整：assistant(tool_calls) 与 tool 结果交替且开头是 assistant
    roles = [m["role"] for m in out]
    assert roles[0] == "assistant" and roles[-1] == "tool"
    for i in range(0, len(roles), 2):
        assert roles[i] == "assistant" and roles[i + 1] == "tool", (
            f"截断必须成对, index={i}: {roles}"
        )


async def test_trim_tool_history_no_truncation_when_small():
    """工具历史未超预算时不截断（近期轮次完整）。"""
    from gyra.agent.expand.v2_agent.v2_agent import V2Agent

    class FakeSelf:
        async def get_agent_llm_context_length(self):
            return 128000

    msgs = []
    for i in range(3):
        msgs.append({"role": "assistant", "content": "",
                     "tool_calls": [{"id": f"c{i}", "type": "function",
                                     "function": {"name": "Bash", "arguments": "{}"}}]})
        msgs.append({"role": "tool", "tool_call_id": f"c{i}", "content": f"结果{i}"})
    out = await V2Agent._trim_tool_history(FakeSelf(), msgs)
    assert len(out) == len(msgs), "小历史不应截断"
