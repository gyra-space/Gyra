import pytest
import tempfile
import os
from gyra.agent.core.v2.runtime import run_step
from gyra.agent.core.v2.state_store import DbStateStore


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = DbStateStore(path)
    yield s
    os.unlink(path)


async def test_llm_token_event_carries_usage_when_provided(store):
    """§10.7.2: llm_token.output.usage field — transparent passthrough from thinking_fn."""
    async def thinking(input_):
        yield {"token": "hello", "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105}}
        yield {"token": " world", "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}}

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, thinking):
        events.append(e)

    llm_tokens = [e for e in events if e.event_type == "llm_token"]
    assert len(llm_tokens) >= 2
    assert llm_tokens[0].output["token"] == "hello"
    assert llm_tokens[0].output["usage"]["total_tokens"] == 105
    assert llm_tokens[1].output["usage"]["total_tokens"] == 110


async def test_llm_token_without_usage_still_works(store):
    """Backwards compat: thinking_fn chunks without usage don't break."""
    async def thinking(input_):
        yield {"token": "no usage"}
        yield {"token": "", "tool_calls": []}

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, thinking):
        events.append(e)

    llm_tokens = [e for e in events if e.event_type == "llm_token"]
    assert len(llm_tokens) >= 1
    assert llm_tokens[0].output["token"] == "no usage"
    # usage key may be absent or None — no crash

async def test_typed_tool_call_chunk_does_not_crash_llm_token_emit(store):
    """Regression: ToolCallChunk/UsageChunk 不设置 channel，旧代码在 LLM 产出
    工具调用时抛 UnboundLocalError 杀死 run_loop。"""
    from gyra.agent.core.v2.thinking_chunk import ToolCallChunk, UsageChunk
    from gyra.agent.core.v2.tool_call_types import V2ToolCall

    async def thinking(input_):
        yield ToolCallChunk(tool_calls=[V2ToolCall(name="echo", args={"x": 1})])
        yield UsageChunk(usage={"total_tokens": 7})

    events = []
    async for e in run_step("agent-1", "conv-1", {"prompt": "hi"}, store, thinking):
        events.append(e)

    tool_calls = [e for e in events if e.event_type == "tool_call"]
    assert len(tool_calls) == 1
    # ToolCallChunk 路径的 llm_token 附带默认 channel，不再抛 UnboundLocalError
    tokens = [e for e in events if e.event_type == "llm_token"]
    assert all("channel" in e.output for e in tokens)
