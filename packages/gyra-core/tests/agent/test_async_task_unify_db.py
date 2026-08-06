"""统一实例 + DB ledger 注入的验证测试。

覆盖本轮补齐点：
1. set_global_ledger：注入全局 ledger（如 AsyncTaskDao）后，media 单例统一用它持久化，
   支撑分布式；显式 ledger_path 仍优先（JSONL 兜底）。
2. 统一单例跑 subagent 任务：spec.delegate 打包委派协程，进程级单例无需 subagent_manager
   也能执行 subagent 任务，实现 media / subagent 统一调度。
"""
import asyncio
import pytest

from gyra.agent.util.async_task_manager import (
    AsyncTaskManager,
    AsyncTaskSpec,
    AsyncTaskStatus,
)


class _FakeLedger:
    """鸭子类型 ledger：与 AsyncTaskDao 对齐的 upsert(record) / read_all()。"""

    def __init__(self):
        self.records = {}

    def upsert(self, record):
        self.records[record["task_id"]] = dict(record)

    def read_all(self):
        return dict(self.records)


def _reset_singleton():
    AsyncTaskManager._media_instance = None
    AsyncTaskManager._global_ledger = None


def _media_spec(conv_id="conv-1"):
    async def _resume():
        return None

    async def _deliver(_result):
        return None

    return AsyncTaskSpec(
        conv_id=conv_id,
        kind="video",
        model="happyhorse-1.1-t2v",
        task_description="测试视频",
        resume=_resume,
        deliver=_deliver,
    )


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _reset_singleton()


@pytest.mark.asyncio
async def test_global_ledger_is_used_by_media_instance():
    """注入全局 ledger 后，media 单例的持久化落到注入的 ledger（DB 语义）。"""
    fake = _FakeLedger()
    AsyncTaskManager.set_global_ledger(fake)

    mgr = AsyncTaskManager.media_instance()
    assert mgr._ledger is fake

    task_id = await mgr.spawn(_media_spec())
    assert task_id in fake.records
    assert fake.records[task_id]["conv_id"] == "conv-1"

    # list/get 从注入 ledger 查询
    assert mgr.get_job(task_id)["task_id"] == task_id
    assert [j["task_id"] for j in mgr.list_jobs(conv_id="conv-1")] == [task_id]


def test_explicit_ledger_path_beats_global(tmp_path):
    """显式 ledger_path 优先于全局注入（测试 / 无 DB 兜底用 JSONL）。"""
    fake = _FakeLedger()
    AsyncTaskManager.set_global_ledger(fake)

    path = str(tmp_path / "fallback.jsonl")
    mgr = AsyncTaskManager(ledger_path=path)
    # 显式 path 时用 TaskLedger（JSONL），而非全局注入的 DB ledger
    assert mgr._ledger is not None
    assert mgr._ledger is not fake
    assert mgr._ledger.path == path


async def _run_to_terminal(mgr, spec, timeout=3.0):
    task_id = await mgr.spawn(spec)
    async def _wait():
        while True:
            st = mgr.get_status(task_id)
            if st is not None and st.is_terminal():
                return st
            await asyncio.sleep(0.01)
    return await asyncio.wait_for(_wait(), timeout)


@pytest.mark.asyncio
async def test_singleton_runs_subagent_via_delegate():
    """统一单例经 spec.delegate 执行 subagent 任务（无需 subagent_manager）。"""
    mgr = AsyncTaskManager.media_instance()

    async def _delegate():
        return type(
            "SubagentResult",
            (),
            {
                "success": True,
                "output": "审查某个模块",
                "error": None,
                "artifacts": {},
            },
        )()

    spec = AsyncTaskSpec(
        agent_name="code_reviewer",
        task_description="审查某个模块",
        conv_id="conv-1",
        delegate=_delegate,
    )

    st = await _run_to_terminal(mgr, spec)
    assert st.status == AsyncTaskStatus.COMPLETED
    assert st.result == "审查某个模块"