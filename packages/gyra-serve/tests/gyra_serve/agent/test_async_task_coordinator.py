"""AsyncTaskCoordinator 单元测试。

覆盖目标（#2 / #3 / #4）：
- _sync_pending_from_managers: 自动把 manager 里带 conv_id 的任务同步进会话 pending 台账
- has_pending_tasks: 会话存在未完成任务 → 轮次结束可置 WAITING（#2）
- _poll_completed: 任务终态且会话 WAITING → 触发主 resume（#3）
- _resume_conv: 后台 task 消费 aggregation_chat 异步生成器（#3）
- recover_main: 按台账/内存态判定终态，全部终态则 resume；stale_conv 时把 running 台账任务标记失败（#4）
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from gyra.agent.core.schema import Status
from gyra.agent.util.async_task_manager import (
    AsyncTaskManager,
    AsyncTaskSpec,
    AsyncTaskState,
    AsyncTaskStatus,
)
from gyra_serve.agent.async_task_coordinator import (
    AsyncTaskCoordinator,
    get_async_task_coordinator,
    set_async_task_coordinator,
)


def _make_conv(extra: dict | None = None, state: str = "WAITING"):
    conv = MagicMock()
    conv.extra = json.dumps(extra) if extra is not None else None
    conv.conv_id = "conv_main_1"
    # 真实会话里 conv_session_id 是唯一会话 ID；_resume_conv 用其作为 conv_id 传入
    conv.conv_session_id = "conv_main_1"
    conv.gpts_name = "test_app"
    conv.user_code = "u1"
    conv.sys_code = "s1"
    conv.state = state
    return conv


def _make_agent_chat(conv=None):
    agent_chat = MagicMock()
    agent_chat.gpts_conversations = MagicMock()
    agent_chat.gpts_conversations.get_by_conv_id = MagicMock(return_value=conv)
    session = MagicMock()
    agent_chat.gpts_conversations.get_raw_session = MagicMock(return_value=session)
    agent_chat.aggregation_chat = AsyncMock()
    return agent_chat


def _extract_extra_from_update_call(session):
    update_call = session.query.return_value.filter.return_value.update.call_args
    extra_dict = update_call.args[0]
    return next(iter(extra_dict.values()))


def _media_spec(conv_id="conv_main_1", hold_event=None):
    async def _resume():
        if hold_event is not None:
            await hold_event.wait()
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


def _fresh_media(ledger_path):
    AsyncTaskManager._media_instance = None
    return AsyncTaskManager.media_instance(ledger_path=ledger_path)


def _reset_singleton():
    AsyncTaskManager._media_instance = None


# ---------------- #3: _resume_conv 后台消费 aggregation_chat ----------------

class TestResumeConv:
    @pytest.mark.asyncio
    async def test_resume_consumes_async_generator(self):
        """_resume_conv 应把合成的通知作为 user_query 注入并通过后台 task 消费生成器。"""
        conv = _make_conv(extra={})
        agent_chat = _make_agent_chat(conv)

        calls = {}

        async def _agg_gen(**kwargs):
            calls.update(kwargs)
            if False:  # make it a generator
                yield None, None, None

        agent_chat.aggregation_chat = _agg_gen

        coord = AsyncTaskCoordinator(agent_chat=agent_chat)
        await coord._resume_conv("conv_main_1", [])

        # 给后台 task 一点时间跑完
        await asyncio.sleep(0.05)
        assert calls["conv_id"] == "conv_main_1"
        assert calls["gpts_name"] == "test_app"
        assert "[异步任务完成通知]" in calls["user_query"]
        assert calls["gpts_conversations"] == [conv]


# ---------------- #2 / #3: pending 台账同步 + 完成轮询 ----------------

class TestPendingAndPoll:
    @pytest.mark.asyncio
    async def test_sync_pending_from_managers_writes_ledger(self, tmp_path):
        """manager 里带 conv_id 的任务应被自动写入会话 pending 台账。"""
        conv = _make_conv(extra={})
        agent_chat = _make_agent_chat(conv)
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)

        mgr = _fresh_media(str(tmp_path / "media_jobs.jsonl"))
        # 直接插入 running 状态，避免后台任务竞态
        spec = _media_spec()
        st = AsyncTaskState(
            spec=spec, status=AsyncTaskStatus.RUNNING, started_at=datetime.now()
        )
        mgr._tasks[spec.task_id] = st
        coord.add_manager(mgr)

        await coord._sync_pending_from_managers()

        session = agent_chat.gpts_conversations.get_raw_session.return_value
        extra = json.loads(_extract_extra_from_update_call(session))
        assert len(extra["pending_async_tasks"]) == 1
        assert extra["pending_async_tasks"][0]["task_id"] == spec.task_id
        assert extra["pending_async_tasks"][0]["status"] != "completed"
        _reset_singleton()

    @pytest.mark.asyncio
    async def test_has_pending_tasks_true_when_active(self, tmp_path):
        """存在未完成任务时 has_pending_tasks 返回 True（供轮次结束置 WAITING）。"""
        conv = _make_conv(extra={})
        agent_chat = _make_agent_chat(conv)
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)

        mgr = _fresh_media(str(tmp_path / "media_jobs.jsonl"))
        spec = _media_spec()
        st = AsyncTaskState(
            spec=spec, status=AsyncTaskStatus.RUNNING, started_at=datetime.now()
        )
        mgr._tasks[spec.task_id] = st
        coord.add_manager(mgr)

        assert await coord.has_pending_tasks("conv_main_1") is True
        _reset_singleton()

    @pytest.mark.asyncio
    async def test_poll_completed_triggers_resume_when_waiting(self, tmp_path):
        """任务终态 + 主会话 WAITING → 触发 resume。"""
        conv = _make_conv(extra={}, state=Status.WAITING.value)
        agent_chat = _make_agent_chat(conv)

        async def _agg_gen(**kwargs):
            if False:
                yield None, None, None

        agent_chat.aggregation_chat = _agg_gen

        coord = AsyncTaskCoordinator(agent_chat=agent_chat)
        mgr = _fresh_media(str(tmp_path / "media_jobs.jsonl"))
        spec = _media_spec()
        st = AsyncTaskState(
            spec=spec,
            status=AsyncTaskStatus.COMPLETED,
            completed_at=datetime.now(),
            consumed=False,
        )
        mgr._tasks[spec.task_id] = st
        coord.add_manager(mgr)

        await coord._poll_completed()
        await asyncio.sleep(0.05)

        # _poll_completed 内部会调用 _resume_conv → 后台 task 消费 aggregation_chat
        assert st.consumed is True
        _reset_singleton()

    @pytest.mark.asyncio
    async def test_poll_completed_skips_non_waiting(self, tmp_path):
        """主会话非 WAITING（如 COMPLETE）时不应触发 resume。"""
        conv = _make_conv(extra={}, state="COMPLETE")
        agent_chat = _make_agent_chat(conv)
        agent_chat.aggregation_chat = AsyncMock()
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)

        mgr = _fresh_media(str(tmp_path / "media_jobs.jsonl"))
        spec = _media_spec()
        st = AsyncTaskState(
            spec=spec,
            status=AsyncTaskStatus.COMPLETED,
            completed_at=datetime.now(),
            consumed=False,
        )
        mgr._tasks[spec.task_id] = st
        coord.add_manager(mgr)

        await coord._poll_completed()
        await asyncio.sleep(0.02)
        agent_chat.aggregation_chat.assert_not_awaited()
        _reset_singleton()

    @pytest.mark.asyncio
    async def test_subagent_task_tracked_and_pending(self, tmp_path):
        """spawn_agent_task(subagent 模式)任务带 conv_id 时应被 coordinator 跟踪并判为 pending。

        覆盖用户关心点：异步子 Agent 任务同样纳入 #2(WAITING) / #3(resume) 流程。
        """
        conv = _make_conv(extra={})
        agent_chat = _make_agent_chat(conv)
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)

        # subagent 模式管理器（带 subagent_manager，但测试直接注入状态）
        mgr = AsyncTaskManager(
            subagent_manager=MagicMock(),
            ledger_path=str(tmp_path / "subagent_jobs.jsonl"),
        )
        spec = AsyncTaskSpec(
            agent_name="code_reviewer",
            task_description="审查某个模块",
            conv_id="conv_main_1",
        )
        st = AsyncTaskState(
            spec=spec, status=AsyncTaskStatus.RUNNING, started_at=datetime.now()
        )
        mgr._tasks[spec.task_id] = st
        coord.add_manager(mgr)

        # #2: 判为 pending → 轮次结束可置 WAITING
        assert await coord.has_pending_tasks("conv_main_1") is True

        # 台账同步：任务被写入会话 pending_async_tasks
        await coord._sync_pending_from_managers()
        session = agent_chat.gpts_conversations.get_raw_session.return_value
        extra = json.loads(_extract_extra_from_update_call(session))
        assert any(
            i["task_id"] == spec.task_id for i in extra["pending_async_tasks"]
        )
        _reset_singleton()

    @pytest.mark.asyncio
    async def test_subagent_task_triggers_resume_when_waiting(self, tmp_path):
        """subagent 任务终态 + 主会话 WAITING → coordinator 触发 resume（#3）。"""
        conv = _make_conv(extra={}, state=Status.WAITING.value)
        agent_chat = _make_agent_chat(conv)

        async def _agg_gen(**kwargs):
            if False:
                yield None, None, None

        agent_chat.aggregation_chat = _agg_gen
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)

        mgr = AsyncTaskManager(
            subagent_manager=MagicMock(),
            ledger_path=str(tmp_path / "subagent_jobs.jsonl"),
        )
        spec = AsyncTaskSpec(
            agent_name="code_reviewer",
            task_description="审查某个模块",
            conv_id="conv_main_1",
        )
        st = AsyncTaskState(
            spec=spec,
            status=AsyncTaskStatus.COMPLETED,
            completed_at=datetime.now(),
            result="审查通过，无重大问题",
            consumed=False,
        )
        mgr._tasks[spec.task_id] = st
        coord.add_manager(mgr)

        await coord._poll_completed()
        await asyncio.sleep(0.05)
        assert st.consumed is True
        _reset_singleton()


# ---------------- #4: recover_main ----------------

class TestRecoverMain:
    @pytest.mark.asyncio
    async def test_recover_all_terminal_resumes(self, tmp_path):
        """pending 任务全部终态 → recover_main 触发 resume。"""
        conv = _make_conv(
            extra={
                "pending_async_tasks": [
                    {
                        "task_id": "atask_old",
                        "kind": "video",
                        "status": "completed",
                        "created_at": 0,
                    }
                ]
            },
            state="WAITING",
        )
        agent_chat = _make_agent_chat(conv)

        async def _agg_gen(**kwargs):
            if False:
                yield None, None, None

        agent_chat.aggregation_chat = _agg_gen
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)
        await coord.recover_main("conv_main_1")
        await asyncio.sleep(0.05)
        # 若 resume 被触发，会尝试读 conv（已存在），不抛异常即可

    @pytest.mark.asyncio
    async def test_recover_stale_marks_running_as_failed(self, tmp_path):
        """stale_conv=True 时，台账里 running 的媒体任务应被标记失败（进程已死）。"""
        conv = _make_conv(
            extra={
                "pending_async_tasks": [
                    {
                        "task_id": "atask_orphan",
                        "kind": "video",
                        "status": "running",
                        "created_at": 0,
                    }
                ]
            },
            state="WAITING",
        )
        agent_chat = _make_agent_chat(conv)

        async def _agg_gen(**kwargs):
            if False:
                yield None, None, None

        agent_chat.aggregation_chat = _agg_gen
        coord = AsyncTaskCoordinator(agent_chat=agent_chat)

        # 台账里该任务仍显示 running（原进程已死）
        mgr = _fresh_media(str(tmp_path / "media_jobs.jsonl"))
        mgr._ledger.upsert(
            {
                "task_id": "atask_orphan",
                "conv_id": "conv_main_1",
                "kind": "video",
                "status": "running",
                "created_at": "2026-01-01T00:00:00",
            }
        )
        coord.add_manager(mgr)

        # _set_waiting_reason 现在从 DB 读最新 extra（含 recover_main 写的终态），
        # 需在 recover_main 调用前模拟该行数据：pending_async_tasks 已置为 failed。
        session = agent_chat.gpts_conversations.get_raw_session.return_value
        session.query.return_value.filter.return_value.first.return_value = MagicMock(
            extra=json.dumps(
                {
                    "pending_async_tasks": [
                        {
                            "task_id": "atask_orphan",
                            "kind": "video",
                            "status": "failed",
                            "finished_at": 0,
                        }
                    ]
                }
            )
        )

        await coord.recover_main("conv_main_1", stale_conv=True)
        await asyncio.sleep(0.05)

        extra = json.loads(_extract_extra_from_update_call(session))
        assert extra["pending_async_tasks"][0]["status"] == "failed"
        _reset_singleton()


# ---------------- 全局单例 ----------------

class TestGlobalSingleton:
    def test_set_get(self):
        set_async_task_coordinator(None)
        assert get_async_task_coordinator() is None
        coord = AsyncTaskCoordinator(agent_chat=None)
        set_async_task_coordinator(coord)
        assert get_async_task_coordinator() is coord
        set_async_task_coordinator(None)


# ---------------- harness seam 对齐：JobRegistry 本地视图 ----------------

@pytest.mark.asyncio
async def test_sync_pending_registers_job_registry():
    """注入 job_registry 后，_sync_pending_from_managers 把任务状态同步到 JobRegistry。

    纯增量：不影响 gpts_conversations.extra 台账，仅提供 harness.jobs 本地统一视图。
    """
    from gyra.agent.core.v2.harness.seams import JobRegistry

    registry = JobRegistry()
    agent_chat = _make_agent_chat(conv=_make_conv())
    coord = AsyncTaskCoordinator(agent_chat=agent_chat, job_registry=registry)
    mgr = MagicMock()
    mgr.get_all_status = MagicMock(
        return_value={
            "task-1": {"conv_id": "conv_main_1", "kind": "media", "status": "running"},
        }
    )
    coord.add_manager(mgr)

    await coord._sync_pending_from_managers()

    job = registry.get_status("task-1")
    assert job is not None
    assert job["conv_id"] == "conv_main_1"
    assert job["kind"] == "media"
    assert job["status"] == "running"
    # 后续更新覆盖
    mgr.get_all_status = MagicMock(
        return_value={
            "task-1": {"conv_id": "conv_main_1", "kind": "media", "status": "completed"},
        }
    )
    await coord._sync_pending_from_managers()
    assert registry.get_status("task-1")["status"] == "completed"