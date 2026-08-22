"""V2 上下文生命周期端到端测试（覆盖：攒批 + isolate + surface 标记 + spill + compaction + plan 模式）。

验证目标：把 V2 所有新增能力（ContextManager / TokenMeter / SpillManager /
Compactor / PlanManager / ProjectorRegistry / EventRegistry）跑通一个完整
turn，验证事件 → 投影 → 折叠 → 压缩 → 摘要的端到端流程。
"""
import os
import tempfile
import asyncio
from typing import Any, Dict, List, Optional

import pytest

from gyra.agent.core.v2.compaction import (
    Compactor,
    CompactionPolicy,
    HeuristicSummarizer,
)
from gyra.agent.core.v2.context_manager import (
    ContextManager,
    ContextManagerConfig,
)
from gyra.agent.core.v2.event_registry import (
    get_event_registry,
    register_event_type,
    reset_event_registry,
)
from gyra.agent.core.v2.event_stream import EventBatchConfig, EventStream
from gyra.agent.core.v2.harness.context import HarnessContext
from gyra.agent.core.v2.plan import PlanManager
from gyra.agent.core.v2.projector_registry import (
    ProjectorRegistry,
    get_projector_registry,
    reset_projector_registry,
)
from gyra.agent.core.v2.spill import FileSpillStore, SpillManager, SpillPolicy
from gyra.agent.core.v2.state_store import DbStateStore
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.token_meter import (
    PressureLevel,
    TokenMeter,
    TokenMeterConfig,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_path_dir(tmp_path):
    """测试用临时目录（spill 落盘用）。"""
    return str(tmp_path)


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


def _make_event(
    seq: int,
    event_type: str,
    *,
    state: StepState = StepState.THINKING,
    conv_id: str = "c1",
    agent_id: str = "a1",
    step_id: str = "s1",
    output: Optional[dict] = None,
    input_data: Optional[dict] = None,
    timestamp: Optional[float] = None,
) -> StepEvent:
    return StepEvent(
        event_id=f"e-{seq}",
        step_id=step_id,
        conv_id=conv_id,
        agent_id=agent_id,
        parent_step_id=None,
        state=state,
        event_type=event_type,
        input=input_data or {},
        output=output or {},
        seq=seq,
        timestamp=timestamp if timestamp is not None else float(seq),
    )


def _usage_event(seq: int, prompt: int, completion: int) -> StepEvent:
    total = prompt + completion
    return _make_event(
        seq,
        "usage_metric",
        state=StepState.THINKING,
        output={"this_call": {"prompt": prompt, "completion": completion, "total": total}},
    )


def _step_done(seq: int, step_id: str) -> StepEvent:
    return _make_event(seq, "step_done", state=StepState.DONE, step_id=step_id)


def _user_message(seq: int, text: str) -> StepEvent:
    return _make_event(
        seq, "user/message", state=StepState.THINKING, output={"text": text},
    )


def _assistant_message(seq: int, text: str) -> StepEvent:
    return _make_event(
        seq, "assistant/message", state=StepState.THINKING, output={"text": text},
    )


# =============================================================================
# 1. 不落库端到端：EventBatchConfig → EventStream → llm_token 只广播不落库
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_llm_token_not_persisted(tmp_store):
    """llm_token 只广播不落库；step_done 强事件照常落库。"""
    stream = EventStream(tmp_store, batch=EventBatchConfig())
    notified = []

    async def spy(ev):
        notified.append(ev.event_type)

    stream.subscribe(spy, mode="emit")

    # 10 个 llm_token 实时广播
    for i in range(1, 11):
        await stream.emit(_make_event(i, "llm_token"))
    assert len(notified) == 10  # 广播实时
    assert [e.event_type for e in await tmp_store.get_events("c1")] == []  # 不落库

    # 强事件照常落库
    await stream.emit(_make_event(11, "step_done", state=StepState.DONE))
    events = await tmp_store.get_events("c1")
    assert len(events) == 1
    assert events[0].event_type == "step_done"



# =============================================================================
# 2. Isolate 端到端：父 HarnessContext 隔离出子作用域，子修改不影响父
# =============================================================================


def test_e2e_harness_isolate_inheritance(tmp_store):
    """HarnessContext.isolate 父→子继承与覆盖。"""
    from gyra.agent.core.v2.harness.context import HarnessContext
    parent = HarnessContext(
        storage=tmp_store,
        events=EventStream(tmp_store, batch=False),
    )
    # 子作用域覆盖 approval，保留 storage
    child = parent.isolate("readonly_preset", approval=None)
    assert child is not parent
    # 父 approval 不被子覆盖
    assert child._isolate_label == "readonly_preset"
    # 父的 storage 与子的 storage 默认共享（不传 override）
    assert child.storage is parent.storage
    # 父 label 链追溯
    chain = child.get_isolation_chain()
    assert chain == ["readonly_preset"]


def test_e2e_harness_isolate_chain(tmp_store):
    """嵌套 isolate 形成 chain（父→子→孙）。"""
    from gyra.agent.core.v2.harness.context import HarnessContext
    parent = HarnessContext(
        storage=tmp_store,
        events=EventStream(tmp_store, batch=False),
    )
    child = parent.isolate("child", approval=None)
    grandchild = child.isolate("grandchild", tools=None)
    chain = grandchild.get_isolation_chain()
    assert chain == ["child", "grandchild"]


def test_e2e_harness_isolate_invalid_field(tmp_store):
    """isolate 拒绝非 HarnessContext 字段。"""
    from gyra.agent.core.v2.harness.context import HarnessContext
    h = HarnessContext(
        storage=tmp_store,
        events=EventStream(tmp_store, batch=False),
    )
    with pytest.raises(ValueError, match="override fields not in HarnessContext"):
        h.isolate("bad", nonexistent_field=None)


# =============================================================================
# 3. Surface 标记端到端：EventRegistry → ProjectorRegistry → 投影
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_surface_marking_projection(tmp_store):
    """surface 事件自动投影，internal 事件不投影。"""
    # 清空 registry，重新走默认注册
    reset_event_registry()
    reset_projector_registry()
    reg = get_event_registry()
    proj = get_projector_registry()

    # user/assistant 是 surface，llm_token/step_done 是 internal
    assert reg.is_surface("user/message") is True
    assert reg.is_surface("assistant/message") is True
    assert reg.is_surface("llm_token") is False
    assert reg.is_surface("step_done") is False

    # 写入混合事件（关闭攒批确保 emit 即落库）
    stream = EventStream(tmp_store, batch=False)
    for i in range(1, 5):
        await stream.emit(_user_message(i, f"user-{i}"))
        await stream.emit(_assistant_message(i + 10, f"asst-{i}"))
        await stream.emit(_make_event(i + 20, "llm_token", state=StepState.THINKING))
    await stream.emit(_make_event(100, "step_done", state=StepState.DONE))

    events = await tmp_store.get_events("c1")
    msgs = proj.project_events(events)
    # 投影只含 surface：4 user + 4 assistant = 8 条消息
    assert len(msgs) == 8
    roles = [m["role"] for m in msgs]
    assert roles.count("user") == 4
    assert roles.count("assistant") == 4
    # 没有 internal 事件
    assert all(m.get("role") in ("user", "assistant") for m in msgs)


def test_e2e_register_custom_event_with_projector():
    """业务插件可注册自定义 surface 事件 + projector。"""
    reset_event_registry()
    reset_projector_registry()
    reg = get_event_registry()

    def project_biz_fact(event: StepEvent) -> Optional[dict]:
        text = (event.output or {}).get("text")
        if not text:
            return None
        return {"role": "system", "content": f"[BIZ] {text}"}

    register_event_type(
        "biz/custom_fact",
        is_surface=True,
        category="biz",
        projector_fn=project_biz_fact,
    )
    assert reg.is_surface("biz/custom_fact") is True
    assert reg.get_projector("biz/custom_fact") is project_biz_fact


def test_e2e_model_visible_logged_invariant():
    """surface 事件必须配 projector_fn（model-visible = logged 强校验）。"""
    reset_event_registry()
    reg = get_event_registry()
    # 手动注册一个 surface 事件但不带 projector_fn
    reg.register("test/missing_proj", is_surface=True)
    # validate_logged_visibility 应该 raise
    with pytest.raises(RuntimeError, match="invariant violation"):
        reg.validate_logged_visibility("test/missing_proj")


# =============================================================================
# 4. Spill 端到端：超大 tool 结果 spill + locator 注入 + 取回
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_spill_large_tool_result(tmp_path_dir):
    """超大 tool 消息 → spill + locator 注入 + 摘要。"""
    sm = SpillManager(
        FileSpillStore(tmp_path_dir),
        SpillPolicy(max_inline_chars=200, max_summary_chars=100),
    )
    big_content = "x" * 1000
    msgs = [
        {"role": "user", "content": "帮我查一下"},
        {"role": "tool", "tool_call_id": "c1", "content": big_content},
        {"role": "assistant", "content": "好的"},
    ]
    out = sm.compact_tool_results(msgs)
    # user/assistant 不变
    assert out[0]["content"] == "帮我查一下"
    assert out[2]["content"] == "好的"
    # tool 消息被 spill
    assert "_spill_locator" in out[1]
    assert "spill://" in out[1]["content"]
    assert "1000" in out[1]["content"]  # size_bytes
    # locator 可取回原文
    full = sm.resolve_locator(out[1]["_spill_locator"])
    assert full == big_content.encode("utf-8")


@pytest.mark.asyncio
async def test_e2e_spill_within_context_manager(tmp_path_dir, tmp_store):
    """ContextManager.pre_step 集成 spill 流程。"""
    cm = ContextManager(
        store=tmp_store,
        event_stream=EventStream(tmp_store, batch=False),
        conv_id="c1",
        spill_manager=SpillManager(
            FileSpillStore(tmp_path_dir),
            SpillPolicy(max_inline_chars=100, max_summary_chars=50),
        ),
        config=ContextManagerConfig(enable_spill=True, enable_compaction=False),
    )
    big = "z" * 500
    msgs = [
        {"role": "tool", "tool_call_id": "c1", "content": big},
    ]
    out = await cm.pre_step(msgs)
    assert "_spill_locator" in out[0]
    assert "spill://" in out[0]["content"]


# =============================================================================
# 5. Compaction 端到端：压力触发 → 选范围 → 摘要 → replace_shadow 折叠
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_compaction_pressure_trigger(tmp_store):
    """压力达阈值 → 触发 compaction → emit summary 事件。"""
    # 1. 写入 usage 事件让 ratio 飙升
    for i in range(1, 6):
        await tmp_store.append_event(_usage_event(i, 200, 100))  # total 累计 1500

    # 2. 写入 user/assistant 历史消息（compactable）
    for i in range(10, 16):
        await tmp_store.append_event(_user_message(i, f"history-{i}"))

    # 3. 写入 step_done 划分 turn 边界
    await tmp_store.append_event(_step_done(100, "s-old"))
    await tmp_store.append_event(_step_done(101, "s-current"))

    # 4. 配置 compactor
    seq = [200]

    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        seq[0] += 1
        ev = StepEvent(
            event_id=f"c-{seq[0]}",
            step_id="s-current",
            conv_id="c1",
            agent_id="a1",
            state=state,
            event_type=et,
            input=input_data or {},
            output=output_data or {},
            seq=seq[0],
            timestamp=float(seq[0]),
        )
        await tmp_store.append_event(ev)
        return ev

    token_meter = TokenMeter(
        tmp_store, "c1", model=None,
        config=TokenMeterConfig(
            context_window=1000, warn_ratio=0.5, compact_ratio=0.8, evict_ratio=0.95,
        ),
    )
    compactor = Compactor(
        store=tmp_store,
        emit=emit,
        conv_id="c1",
        agent_id="a1",
        step_id="s-current",
        policy=CompactionPolicy(
            min_keep_recent_turns=1,  # 保留最近 1 个 turn
            enable_replace_shadow=True,
            force_compact_every_n_turns=0,
        ),
        token_meter=token_meter,
        llm_summarizer=HeuristicSummarizer(),
    )
    result = await compactor.maybe_run()
    assert result.triggered is True
    assert "pressure" in result.reason
    assert result.compacted_event_count >= 2

    # 5. 验证 compaction/summary 事件已写入
    events = await tmp_store.get_events("c1")
    summary_events = [e for e in events if e.event_type == "compaction/summary"]
    assert len(summary_events) == 1
    # 6. 投影验证：summary 替换了历史 user 消息
    msgs = get_projector_registry().project_events(events)
    # 至少有 1 条 Compaction 摘要
    comp_msgs = [m for m in msgs if m["content"].startswith("[Compaction 摘要]")]
    assert len(comp_msgs) == 1
    # user/message 被 replace_shadow 折叠（不重复）
    user_msgs = [m for m in msgs if m["role"] == "user"]
    assert len(user_msgs) == 0  # 全部被 summary 折叠


@pytest.mark.asyncio
async def test_e2e_compaction_force_trigger(tmp_store):
    """force_compact_every_n_turns 强制触发 compaction（不依赖 token 压力）。"""
    # 写入少量 usage（不触发压力）
    await tmp_store.append_event(_usage_event(1, 10, 5))
    # 写入历史消息
    for i in range(10, 14):
        await tmp_store.append_event(_user_message(i, f"q-{i}"))
    await tmp_store.append_event(_step_done(50, "s-old"))
    await tmp_store.append_event(_step_done(51, "s-current"))

    seq = [100]

    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        seq[0] += 1
        ev = StepEvent(
            event_id=f"c-{seq[0]}",
            step_id="s-current", conv_id="c1", agent_id="a1",
            state=state, event_type=et,
            input=input_data or {}, output=output_data or {},
            seq=seq[0], timestamp=float(seq[0]),
        )
        await tmp_store.append_event(ev)
        return ev

    token_meter = TokenMeter(tmp_store, "c1", model=None)
    compactor = Compactor(
        store=tmp_store, emit=emit, conv_id="c1", agent_id="a1", step_id="s-current",
        policy=CompactionPolicy(
            min_keep_recent_turns=1,
            force_compact_every_n_turns=1,  # 每 1 turn 强制压
        ),
        token_meter=token_meter,
        llm_summarizer=HeuristicSummarizer(),
    )
    # token 压力不达阈值，但 force=true
    result = await compactor.maybe_run()
    assert result.triggered is True
    assert "force" in result.reason or "turn" in result.reason


# =============================================================================
# 6. Plan 模式端到端：plan/start → plan/step → plan/finish 折叠
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_plan_mode_fold(tmp_store):
    """plan/* 事件触发 → 折叠为单条 plan/finish 消息。"""
    seq = [0]

    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        seq[0] += 1
        ev = StepEvent(
            event_id=f"p-{seq[0]}",
            step_id="s-plan", conv_id="c1", agent_id="a1",
            state=state, event_type=et,
            input=input_data or {}, output=output_data or {},
            seq=seq[0], timestamp=float(seq[0]),
        )
        await tmp_store.append_event(ev)
        return ev

    plan = PlanManager(emit=emit, step_id="s-plan")
    await plan.start("准备设计新功能")
    await plan.add_step("1. 收集用户需求")
    await plan.add_step("2. 设计 API")
    await plan.add_step("3. 编写实现代码")
    await plan.finish("准备进入执行阶段")

    events = await tmp_store.get_events("c1")
    types = [e.event_type for e in events]
    assert types == ["plan/start", "plan/step", "plan/step", "plan/step", "plan/finish"]

    # 投影：所有 plan/* 折叠为 1 条 system 消息（finish 用 replace_op）
    proj = get_projector_registry()
    msgs = proj.project_events(events)
    plan_msgs = [m for m in msgs if m.get("role") == "system" and "[Plan]" in m.get("content", "")]
    # 由于 finish 用了 _surface_op=replace，所有 plan/* 折叠为 1 条
    assert len(plan_msgs) == 1
    # 折叠后内容是 finish 的 final_text
    assert "准备进入执行阶段" in plan_msgs[0]["content"]


# =============================================================================
# 7. 集成：ContextManager.pre_step + post_step 完整 turn 流程
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_context_manager_full_turn(tmp_path_dir, tmp_store):
    """一个完整 turn：pre_step spill → thinking 累计 usage → post_step 触发 compaction。"""
    spill_mgr = SpillManager(
        FileSpillStore(tmp_path_dir),
        SpillPolicy(max_inline_chars=200, max_summary_chars=100),
    )
    cm = ContextManager(
        store=tmp_store,
        event_stream=EventStream(tmp_store, batch=False),
        model=None,
        conv_id="c1",
        spill_manager=spill_mgr,
        config=ContextManagerConfig(
            enable_spill=True,
            enable_compaction=True,
            token_meter=TokenMeterConfig(
                context_window=500,
                warn_ratio=0.5,
                compact_ratio=0.7,
                evict_ratio=0.9,
            ),
        ),
    )

    # Step 1: pre_step 处理超大 tool 消息
    big = "x" * 800
    msgs = [
        {"role": "user", "content": "查询数据库"},
        {"role": "tool", "tool_call_id": "c1", "content": big},
    ]
    processed = await cm.pre_step(msgs)
    assert "_spill_locator" in processed[1]

    # Step 2: 模拟 thinking 写入 usage 事件
    for i in range(1, 6):
        await tmp_store.append_event(_usage_event(i, 200, 100))  # ratio 1.5

    # Step 3: 写入历史消息
    for i in range(10, 14):
        await tmp_store.append_event(_user_message(i, f"history-q-{i}"))
    await tmp_store.append_event(_step_done(50, "s-old"))

    # Step 4: post_step 触发 compaction
    result = await cm.post_step(step_id="s-current", agent_id="a1", turn_count=1)
    assert result["snapshot"] is not None
    assert result["compaction"] is not None
    # 压力达 0.7 → compaction 触发
    assert result["compaction"]["triggered"] is True


# =============================================================================
# 8. 集成：替换 shadow 合并：plan + compaction 混合折叠
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_compaction_and_plan_combined(tmp_store):
    """compaction + plan 事件都通过 replace_shadow 折叠。"""
    seq = [0]

    async def emit(state, et, input_data=None, output_data=None, **kwargs):
        seq[0] += 1
        ev = StepEvent(
            event_id=f"x-{seq[0]}",
            step_id="s-current", conv_id="c1", agent_id="a1",
            state=state, event_type=et,
            input=input_data or {}, output=output_data or {},
            seq=seq[0], timestamp=float(seq[0]),
        )
        await tmp_store.append_event(ev)
        return ev

    # 1. plan 流程
    plan = PlanManager(emit=emit, step_id="s-current")
    await plan.start("初始化")
    await plan.add_step("step-A")
    await plan.finish("完成计划")

    # 先读出已落库的 plan 事件 id（用于 compaction 折叠）
    plan_events = await tmp_store.get_events("c1")
    plan_event_ids = [
        e.event_id for e in plan_events if e.event_type in ("plan/start", "plan/step", "plan/finish")
    ]

    # 2. compaction 摘要（手动 emit + compacted_event_ids 折叠 plan/*）
    await emit(
        StepState.OBSERVING, "compaction/summary",
        input_data={"compacted_count": len(plan_event_ids)},
        output_data={
            "summary": "本轮完成了计划设计与实现",
            "compacted_event_ids": plan_event_ids,
            "compacted_seq_range": [1, 5],
            "_surface_node_id": "compaction",
            "_surface_op": "replace",
        },
    )

    # 3. 普通 user/assistant 消息
    await emit(
        StepState.THINKING, "user/message",
        input_data={"text": "帮我写代码"},
        output_data={"text": "帮我写代码"},
    )
    await emit(
        StepState.THINKING, "assistant/message",
        input_data={"text": "好的，我来实现"},
        output_data={"text": "好的，我来实现"},
    )

    events = await tmp_store.get_events("c1")
    proj = get_projector_registry()
    msgs = proj.project_events(events)
    # plan/* 折叠为 1 条 + compaction summary 1 条 + user + assistant = 4 条
    plan_msgs = [m for m in msgs if m["content"].startswith("[Plan]")]
    summary_msgs = [m for m in msgs if m["content"].startswith("[Compaction")]
    user_msgs = [m for m in msgs if m["role"] == "user"]
    asst_msgs = [m for m in msgs if m["role"] == "assistant"]
    assert len(plan_msgs) == 0
    assert len(summary_msgs) == 1
    assert "计划" in summary_msgs[0]["content"]
    assert len(user_msgs) == 1
    assert len(asst_msgs) == 1
