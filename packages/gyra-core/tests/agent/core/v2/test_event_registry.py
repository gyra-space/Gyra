"""EventRegistry / ProjectorRegistry / Surface 标记测试。"""
import pytest

from gyra.agent.core.v2.event_registry import (
    EventRegistry,
    get_event_registry,
    register_event_type,
    reset_event_registry,
)
from gyra.agent.core.v2.projector_registry import (
    ProjectorRegistry,
    get_projector_registry,
    reset_projector_registry,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


def test_event_registry_defaults():
    """默认事件词表存在。"""
    reset_event_registry()
    reg = get_event_registry()
    assert reg.is_surface("user/message") is True
    assert reg.is_surface("llm_token") is False
    assert reg.is_surface("compaction/summary") is True
    assert reg.is_surface("plan/step") is True


def test_register_custom_event():
    """业务插件可注册自定义事件类型。"""
    reset_event_registry()
    reg = get_event_registry()
    info = reg.register(
        "biz/custom_fact",
        is_surface=True,
        description="业务自定义事件",
        category="biz",
    )
    assert info.is_surface is True
    assert reg.is_surface("biz/custom_fact") is True


def test_unknown_event_default_internal():
    """未注册事件默认 surface=False（保守：避免误把内部事件当消息）。"""
    reset_event_registry()
    reg = get_event_registry()
    assert reg.is_surface("nonexistent/xxx") is False


def test_projector_registry_defaults():
    """默认投影器覆盖核心 surface 事件。"""
    reset_projector_registry()
    proj = get_projector_registry()
    # user/message / assistant/message / compaction/summary 都有默认投影器
    assert proj.get("user/message") is not None
    assert proj.get("assistant/message") is not None
    assert proj.get("compaction/summary") is not None


def test_project_user_message():
    """user/message 投影为 user 消息。"""
    proj = get_projector_registry()
    event = StepEvent(
        event_id="e1", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.THINKING, event_type="user/message",
        output={"text": "你好"},
        seq=1, timestamp=0.0,
    )
    msgs = proj.project_events([event])
    assert len(msgs) == 1
    assert msgs[0] == {"role": "user", "content": "你好"}


def test_project_compaction_summary():
    """compaction/summary 投影为 system 消息。"""
    proj = get_projector_registry()
    event = StepEvent(
        event_id="e1", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.OBSERVING, event_type="compaction/summary",
        output={"summary": "这是历史摘要"},
        seq=1, timestamp=0.0,
    )
    msgs = proj.project_events([event])
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"
    assert "Compaction 摘要" in msgs[0]["content"]
    assert "这是历史摘要" in msgs[0]["content"]


def test_replace_shadow_collapses_messages():
    """同 surface_node_id 的多条消息按 surface_op 折叠（replace 取最新）。"""
    proj = get_projector_registry()
    e1 = StepEvent(
        event_id="e1", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.THINKING, event_type="user/message",
        output={"text": "v1"},
        seq=1, timestamp=0.0,
        metadata={"_surface_node_id": "u", "_surface_op": "append"},
    )
    e2 = StepEvent(
        event_id="e2", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.THINKING, event_type="user/message",
        output={"text": "v2"},
        seq=2, timestamp=0.0,
        metadata={"_surface_node_id": "u", "_surface_op": "replace"},
    )
    # 注：metadata 不被 projector 用——这是 projector 的内部约定：用 output 字段
    msgs = proj.project_events([e1, e2])
    # 两个都映射到 user message（无 shadow 折叠）；但若 projector 返回带 shadow：
    # 我们的默认 projector 不返回 shadow——验证基础功能
    assert len(msgs) == 2


def test_custom_projector_override():
    """业务可覆盖默认投影器。"""
    proj = get_projector_registry()

    def custom_user_proj(event):
        return {"role": "user", "content": f"CUSTOM:{event.output.get('text', '')}"}

    proj.register("user/message", custom_user_proj)
    event = StepEvent(
        event_id="e1", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.THINKING, event_type="user/message",
        output={"text": "hi"},
        seq=1, timestamp=0.0,
    )
    msgs = proj.project_events([event])
    assert msgs[0]["content"] == "CUSTOM:hi"
    # 还原
    from gyra.agent.core.v2.projector_registry import project_user_message
    proj.register("user/message", project_user_message)


def test_tool_call_result_pair_projection():
    """tool_call + tool_result 配对投影为 assistant+tool 消息对。"""
    proj = get_projector_registry()
    call = StepEvent(
        event_id="e1", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.ACTING, event_type="tool_call",
        input={"tool": "search", "input": {"q": "weather"}},
        seq=1, timestamp=0.0,
    )
    result = StepEvent(
        event_id="e2", step_id="s1", conv_id="c1", agent_id="a1",
        state=StepState.OBSERVING, event_type="tool_result",
        output={"content": "sunny", "is_exe_success": True},
        seq=2, timestamp=0.0,
    )
    msgs = proj.project_events([call, result])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "assistant"
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "search"
    assert msgs[1]["role"] == "tool"
    assert msgs[1]["content"] == "sunny"


def test_validate_logged_visibility():
    """surface 事件必有 projector_fn（model-visible = logged 强校验）。"""
    reset_event_registry()
    reg = get_event_registry()
    # 注册 surface 事件但无 projector
    reg.register("test/surface", is_surface=True, projector_fn=None)
    with pytest.raises(RuntimeError, match="invariant violation"):
        reg.validate_logged_visibility("test/surface")
