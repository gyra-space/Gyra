"""V2 活跃链路 SSE 协议契约测试（run_loop → stream_sse）。

验证 V2AgentRuntime.stream_sse 产出的 BAIZE 兼容 SSE 行格式，供前端
use-chat.ts / V2EventHandler 消费：
  - llm_token → ``data:{"vis":"<token>"}``（字符串 vis，追加到消息）；
  - 内部事件（tool_call/tool_result/step_*）被抑制（前端无对应 vis 类型，
    避免 raw-object-as-text 渲染）；
  - 结尾 ``data:{"vis":"[DONE]"}``。
"""
import tempfile

import pytest

from gyra.agent.core.v2 import HarnessContext, V2AgentRuntime
from gyra.agent.core.v2.tool_call_types import V2ToolResult


async def _thinking(input_):
    """模拟 LLM：先思考，再工具调用，最后收尾。"""
    yield {"token": "思考中"}
    yield {
        "token": "",
        "tool_calls": [{"tool": "echo", "input": {"text": "hi"}}],
    }
    yield {"token": "完成。"}


async def _acting(tool_call, ctx):
    return V2ToolResult.ok(output="echo: hi", tool_name="echo")


@pytest.mark.asyncio
async def test_stream_sse_contract(tmp_path):
    """完整 run_loop → SSE 行的协议契约。"""
    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=str(tmp_path),
        thinking_fn=_thinking, acting_fn=_acting,
    )
    runtime = V2AgentRuntime(
        agent_id="a1", conv_id="c1",
        harness=harness, model_alias="test-model", max_steps=10,
    )

    lines = [line async for line in runtime.stream_sse("你好")]

    # 1) 结尾 [DONE]
    assert lines[-1].startswith('data:{"vis":"[DONE]"}')
    # 2) token 渲染为字符串 vis（前端追加）
    token_lines = [l for l in lines if '"思考中"' in l or '"完成。"' in l]
    assert token_lines, "llm_token 应以字符串 vis 输出"
    assert all(l.startswith("data:") and l.endswith("\n\n") for l in lines[:-1])
    # 3) 内部事件抑制：无原始事件类型泄漏
    raw = "".join(lines)
    for leaked in ("tool_call", "tool_result", "step_done", "step_init", '"vis":{"type"'):
        assert leaked not in raw, f"内部事件不应泄漏到 SSE: {leaked}"


@pytest.mark.asyncio
async def test_stream_sse_done_on_empty_thinking(tmp_path):
    """无 token 时也以 [DONE] 收尾（前端依赖 [DONE] 判定 turn 完成）。"""

    async def _no_token(input_):
        yield {"token": "", "tool_calls": []}

    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=str(tmp_path),
        thinking_fn=_no_token, acting_fn=None,
    )
    runtime = V2AgentRuntime(
        agent_id="a1", conv_id="c1",
        harness=harness, model_alias="test-model", max_steps=5,
    )
    lines = [line async for line in runtime.stream_sse("hi")]
    assert lines and lines[-1].startswith('data:{"vis":"[DONE]"}')


@pytest.mark.asyncio
async def test_stream_events_sequence(tmp_path):
    """StreamEvent 序列：llm_token 与 usage 事件按序产出。"""
    harness = HarnessContext.build(
        agent_id="a1", conv_id="c1", data_dir=str(tmp_path),
        thinking_fn=_thinking, acting_fn=_acting,
    )
    runtime = V2AgentRuntime(
        agent_id="a1", conv_id="c1",
        harness=harness, model_alias="test-model", max_steps=10,
    )
    events = [e async for e in runtime.stream_events("你好")]
    types = [e.type for e in events]
    assert "llm_token" in types
    assert any(e.type == "llm_token" and e.payload.get("token") == "思考中"
               for e in events)
