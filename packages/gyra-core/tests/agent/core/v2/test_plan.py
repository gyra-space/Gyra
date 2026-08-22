"""Plan mode seam 测试。"""
import os
import tempfile
import pytest

from gyra.agent.core.v2.event_registry import get_event_registry
from gyra.agent.core.v2.plan import PlanManager, PlanState
from gyra.agent.core.v2.projector_registry import get_projector_registry
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


@pytest.fixture
def tmp_store():
    """临时文件 SQLite（in-memory DB 在多连接下表不存在，文件 DB 更可靠）。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    s = DbStateStore(path)
    yield s
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_plan_lifecycle(tmp_store):
    """plan.start → add_step → finish 正常流转。"""
    seq = 0

    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        nonlocal seq
        seq += 1
        ev = StepEvent(
            event_id=f"p-{seq}",
            step_id="s-plan", conv_id="c1", agent_id="a1",
            state=state, event_type=et,
            input=input_data or {}, output=output_data or {},
            seq=seq, timestamp=float(seq),
        )
        await tmp_store.append_event(ev)
        return ev

    plan = PlanManager(emit=emit, step_id="s-plan")
    assert not plan.active

    await plan.start("设计新功能")
    assert plan.active
    assert plan.state.started_at is not None

    await plan.add_step("1. 收集需求")
    await plan.add_step("2. 实现")
    assert len(plan.state.steps) == 2

    await plan.finish("准备进入执行阶段")
    assert not plan.active
    assert plan.state.final_text is not None
    # state 已记录 step 数（独立于 final_text）
    assert len(plan.state.steps) == 2

    events = await tmp_store.get_events("c1")
    types = [e.event_type for e in events]
    assert "plan/start" in types
    assert "plan/step" in types
    assert types.count("plan/step") == 2
    assert "plan/finish" in types


@pytest.mark.asyncio
async def test_plan_add_step_requires_start(tmp_store):
    """未 start 时 add_step 报错。"""
    async def emit(state, et, **kwargs):
        return StepEvent(
            event_id="x", step_id="s", conv_id="c", agent_id="a",
            state=state, event_type=et, seq=1, timestamp=0.0,
        )

    plan = PlanManager(emit=emit)
    with pytest.raises(RuntimeError, match="add_step called before start"):
        await plan.add_step("1.")


@pytest.mark.asyncio
async def test_plan_events_projected_to_system(tmp_store):
    """plan/* 事件投影为 system 消息（折叠）。"""
    seq = 0

    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        nonlocal seq
        seq += 1
        ev = StepEvent(
            event_id=f"p-{seq}",
            step_id="s-plan", conv_id="c1", agent_id="a1",
            state=state, event_type=et,
            input=input_data or {}, output=output_data or {},
            seq=seq, timestamp=float(seq),
        )
        await tmp_store.append_event(ev)
        return ev

    plan = PlanManager(emit=emit)
    await plan.start("design")
    await plan.add_step("step1")
    await plan.finish("done")

    events = await tmp_store.get_events("c1")
    proj = get_projector_registry()
    msgs = proj.project_events(events)
    # 至少有 1 条 plan 折叠的 system 消息
    plan_msgs = [m for m in msgs if "[Plan]" in m.get("content", "")]
    assert len(plan_msgs) >= 1


def test_plan_state_to_dict():
    state = PlanState()
    d = state.to_dict()
    assert d["active"] is False
    assert d["step_count"] == 0
    assert d["final_text"] is None


def test_plan_events_registered_in_registry():
    """plan/* 事件已注册到 EventRegistry。"""
    reg = get_event_registry()
    assert reg.is_surface("plan/start") is True
    assert reg.is_surface("plan/step") is True
    assert reg.is_surface("plan/finish") is True
    assert reg.get_projector("plan/start") is not None
    assert reg.get_projector("plan/step") is not None
    assert reg.get_projector("plan/finish") is not None


@pytest.mark.asyncio
async def test_plan_format_plan(tmp_store):
    """format_plan 输出包含 step 列表。"""
    seq = 0

    async def emit(state, et, **kwargs):
        nonlocal seq
        seq += 1
        ev = StepEvent(
            event_id=f"p-{seq}",
            step_id="s", conv_id="c", agent_id="a",
            state=state, event_type=et, seq=seq, timestamp=float(seq),
        )
        await tmp_store.append_event(ev)
        return ev

    plan = PlanManager(emit=emit)
    await plan.start("init")
    await plan.add_step("需求分析")
    await plan.add_step("实现")
    text = plan.format_plan()
    assert "1. 需求分析" in text
    assert "2. 实现" in text
