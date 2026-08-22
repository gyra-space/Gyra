"""SqlAlchemyStateStore 测试——V2 事件溯源接入系统数据库（跟随动态切换）。"""
import pytest

from gyra.storage.metadata.db_manager import DatabaseManager
from gyra.agent.core.v2 import SqlAlchemyStateStore, create_state_store
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra.agent.core.v2.event_projection import project_tool_history


@pytest.fixture
def db_manager(tmp_path):
    """新建系统数据库管理器（文件 sqlite），模拟 serve 层 init_db。

    用文件库而非 in-memory：in-memory sqlite 每连接独立，跨连接看不到表。
    """
    mgr = DatabaseManager()
    mgr.init_db(f"sqlite:///{tmp_path / 'system.db'}")
    return mgr


@pytest.fixture
def store(db_manager):
    return SqlAlchemyStateStore(db_manager)


def _mk_event(seq, state, event_type, input_=None, output=None, step_id="s1"):
    return StepEvent(
        event_id=f"evt-{seq}",
        step_id=step_id,
        conv_id="c1",
        agent_id="a1",
        parent_step_id=None,
        state=state,
        event_type=event_type,
        input=input_ or {},
        output=output or {},
        seq=seq,
        timestamp=seq,
    )


async def test_append_and_read_events(store):
    """事件 append-only 写入与按序读取。"""
    await store.append_event(_mk_event(1, StepState.INIT, "step_init"))
    await store.append_event(_mk_event(2, StepState.DONE, "step_done"))
    events = await store.get_events("c1")
    assert len(events) == 2
    assert events[0].seq == 1
    assert events[1].seq == 2
    # since_seq 过滤
    later = await store.get_events("c1", since_seq=2)
    assert len(later) == 1 and later[0].seq == 2


async def test_step_state_crud(store):
    """step_state 写入/读取/覆盖。"""
    await store.set_step_state("s1", "c1", StepState.THINKING, {"k": "v"})
    state, snapshot = await store.get_step_state("s1")
    assert state is StepState.THINKING
    assert snapshot == {"k": "v"}
    # 覆盖
    await store.set_step_state("s1", "c1", StepState.DONE, {"k": "v2"})
    state2, _ = await store.get_step_state("s1")
    assert state2 is StepState.DONE


async def test_lease_mechanism(store):
    """分布式租约：多实例抢同会话处理权（fail-closed）。"""
    assert await store.acquire_lease("c1", "agent-a", ttl_seconds=60) is True
    # 其他实例抢不到
    assert await store.acquire_lease("c1", "agent-b", ttl_seconds=60) is False
    # 原实例续租
    assert await store.acquire_lease("c1", "agent-a", ttl_seconds=60) is True
    # 过期后可被抢
    await store.release_lease("c1")
    assert await store.acquire_lease("c1", "agent-b", ttl_seconds=60) is True


async def test_interaction_checkpoint(store):
    """审批/交互检查点 CRUD。"""
    await store.save_interaction_checkpoint(
        "req-1", "s1", "c1", {"tool_name": "bash", "tool_input": {"cmd": "ls"}}
    )
    got = await store.get_interaction_checkpoint("req-1")
    assert got["request_payload"]["tool_name"] == "bash"
    await store.delete_interaction_checkpoint("req-1")
    assert await store.get_interaction_checkpoint("req-1") is None


async def test_transcript_crud(store):
    """异步子 Agent transcript 生命周期。"""
    await store.save_transcript(
        transcript_id="t1", task_id="task-1", sub_conv_id="sub1",
        parent_step_id="s1", parent_conv_id="c1", agent_name="sub",
        status="running", latest_event_seq=5, payload={"k": "v"},
    )
    got = await store.get_transcript("t1")
    assert got["status"] == "running"
    assert got["payload"] == {"k": "v"}
    assert await store.get_transcript_by_task_id("task-1") == got
    assert len(await store.list_transcripts_for_parent("c1")) == 1
    # 更新（merge）
    await store.save_transcript(
        transcript_id="t1", task_id="task-1", sub_conv_id="sub1",
        parent_step_id="s1", parent_conv_id="c1", agent_name="sub",
        status="done", latest_event_seq=8, payload={"r": 1},
    )
    assert (await store.get_transcript("t1"))["status"] == "done"
    await store.delete_transcript("t1")
    assert await store.get_transcript("t1") is None


async def test_update_event_metadata(store):
    """事件 metadata 更新（子 agent 标注等）。"""
    await store.append_event(_mk_event(1, StepState.THINKING, "llm_token"))
    await store.update_event_metadata("evt-1", {"is_subagent": True})
    events = await store.get_events("c1")
    assert events[0].metadata == {"is_subagent": True}


async def test_projection_on_unified_store(store):
    """事件日志投影在统一后端上工作（事实源与后端解耦）。"""
    await store.append_event(
        _mk_event(1, StepState.ACTING, "tool_call",
                  input_={"tool": "bash", "input": {"cmd": "ls"}})
    )
    await store.append_event(
        _mk_event(2, StepState.OBSERVING, "tool_result",
                  output={"is_exe_success": True, "content": "ok", "tool_name": "bash"})
    )
    msgs = await project_tool_history(store, "c1")
    assert len(msgs) == 2
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "bash"
    assert msgs[1]["content"] == "ok"


def test_create_state_store_uses_system_db(db_manager):
    """create_state_store 显式 db_manager → SqlAlchemyStateStore（跟随系统 DB）。"""
    store = create_state_store(agent_id="a1", db_manager=db_manager)
    assert isinstance(store, SqlAlchemyStateStore)


def test_create_state_store_explicit_db_path(tmp_path):
    """create_state_store 显式 db_path → 本地 SQLite（测试隔离）。"""
    from gyra.agent.core.v2.state_store import DbStateStore
    store = create_state_store(agent_id="a1", db_path=str(tmp_path / "x.db"))
    assert isinstance(store, DbStateStore)


def test_create_state_store_explicit_data_dir(tmp_path):
    """create_state_store 显式 data_dir → 隔离 SQLite（测试/沙箱）。"""
    from gyra.agent.core.v2.state_store import DbStateStore
    store = create_state_store(agent_id="a1", conv_id="c1", data_dir=str(tmp_path))
    assert isinstance(store, DbStateStore)
