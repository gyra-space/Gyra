"""AsyncTaskManager 外部任务镜像 + 防重复提交 单元测试。

覆盖：
- register_external / complete_external 状态流转（不启动执行体）
- find_in_flight dedup key 匹配（conv_id/agent/kind/model/归一化任务描述）
- known_task_ids
- WaitTasksTool 对未知 task_id 显式报错（不再返回误导性"等待超时"）
- SpawnAgentTaskTool 重复提交去重 + wait_async metadata（阻塞等待默认模式）
"""
from __future__ import annotations

import pytest

from gyra.agent.util.async_task_manager import (
    AsyncTaskManager,
    AsyncTaskSpec,
    AsyncTaskStatus,
    normalize_task_text,
)


@pytest.fixture
def manager():
    return AsyncTaskManager(ledger_path=None)


# ---------------- normalize_task_text ----------------

class TestNormalizeTaskText:
    def test_case_and_whitespace_normalized(self):
        assert normalize_task_text("  生成  Gyra 架构图 ") == "生成 gyra 架构图"

    def test_empty(self):
        assert normalize_task_text("") == ""
        assert normalize_task_text(None) == ""


# ---------------- register_external / complete_external ----------------

class TestExternalTasks:
    @pytest.mark.asyncio
    async def test_register_external_creates_running_task(self, manager):
        tid = await manager.register_external(
            AsyncTaskSpec(
                task_id="sub_conv_1",
                agent_name="图像生成助手",
                task_description="生成图片",
                conv_id="conv_1",
                kind="subagent",
                context={"source": "subagent_coordinator"},
            )
        )
        assert tid == "sub_conv_1"
        state = manager.get_status("sub_conv_1")
        assert state is not None
        assert state.status == AsyncTaskStatus.RUNNING
        assert state.spec.context["external"] is True
        assert state.spec.context["source"] == "subagent_coordinator"

    @pytest.mark.asyncio
    async def test_register_external_idempotent(self, manager):
        spec = AsyncTaskSpec(task_id="sub_conv_1", conv_id="conv_1")
        await manager.register_external(spec)
        # 重复登记不报错，返回原 id
        tid = await manager.register_external(spec)
        assert tid == "sub_conv_1"
        assert len(manager._tasks) == 1

    @pytest.mark.asyncio
    async def test_complete_external_success(self, manager):
        await manager.register_external(
            AsyncTaskSpec(task_id="sub_conv_1", conv_id="conv_1")
        )
        ok = manager.complete_external("sub_conv_1", result="done-result")
        assert ok is True
        state = manager.get_status("sub_conv_1")
        assert state.status == AsyncTaskStatus.COMPLETED
        assert state.result == "done-result"
        # 重复置终态无效
        assert manager.complete_external("sub_conv_1", result="x") is False

    @pytest.mark.asyncio
    async def test_complete_external_failure(self, manager):
        await manager.register_external(
            AsyncTaskSpec(task_id="sub_conv_1", conv_id="conv_1")
        )
        ok = manager.complete_external("sub_conv_1", error="boom")
        assert ok is True
        state = manager.get_status("sub_conv_1")
        assert state.status == AsyncTaskStatus.FAILED
        assert state.error == "boom"

    @pytest.mark.asyncio
    async def test_complete_external_unknown_returns_false(self, manager):
        assert manager.complete_external("nope", result="x") is False

    @pytest.mark.asyncio
    async def test_wait_all_on_external_task(self, manager):
        """wait_tasks 可以等待外部任务（sub_conv_id）完成——ID 错配修复的核心。"""
        await manager.register_external(
            AsyncTaskSpec(task_id="sub_conv_1", conv_id="conv_1")
        )

        async def _complete_later():
            import asyncio

            await asyncio.sleep(0.05)
            manager.complete_external("sub_conv_1", result="ok")

        import asyncio

        asyncio.create_task(_complete_later())
        results = await manager.wait_all(["sub_conv_1"], timeout=5)
        assert len(results) == 1
        assert results[0].status == AsyncTaskStatus.COMPLETED
        assert results[0].result == "ok"


# ---------------- known_task_ids ----------------

class TestKnownTaskIds:
    @pytest.mark.asyncio
    async def test_known_task_ids_filters(self, manager):
        await manager.register_external(AsyncTaskSpec(task_id="t1"))
        assert manager.known_task_ids(["t1", "t2", "t3"]) == ["t1"]
        assert manager.known_task_ids([]) == []


# ---------------- find_in_flight ----------------

class TestFindInFlight:
    @pytest.mark.asyncio
    async def test_match_by_agent_and_description(self, manager):
        await manager.register_external(
            AsyncTaskSpec(
                task_id="t1",
                agent_name="图像生成助手",
                task_description="生成 Gyra 架构图",
                conv_id="conv_1",
            )
        )
        hit = manager.find_in_flight(
            conv_id="conv_1",
            agent_name="图像生成助手",
            task_description=" 生成 gyra 架构图 ",  # 大小写/空白归一化后相同
        )
        assert hit is not None
        assert hit.spec.task_id == "t1"

    @pytest.mark.asyncio
    async def test_no_match_different_conv(self, manager):
        await manager.register_external(
            AsyncTaskSpec(
                task_id="t1",
                agent_name="a",
                task_description="task",
                conv_id="conv_1",
            )
        )
        assert (
            manager.find_in_flight(
                conv_id="conv_2", agent_name="a", task_description="task"
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_no_match_different_description(self, manager):
        await manager.register_external(
            AsyncTaskSpec(
                task_id="t1",
                agent_name="a",
                task_description="生成图片",
                conv_id="conv_1",
            )
        )
        assert (
            manager.find_in_flight(
                conv_id="conv_1", agent_name="a", task_description="生成视频"
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_terminal_task_not_matched(self, manager):
        await manager.register_external(
            AsyncTaskSpec(
                task_id="t1",
                agent_name="a",
                task_description="task",
                conv_id="conv_1",
            )
        )
        manager.complete_external("t1", result="done")
        assert (
            manager.find_in_flight(
                conv_id="conv_1", agent_name="a", task_description="task"
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_match_by_kind_and_model(self, manager):
        await manager.register_external(
            AsyncTaskSpec(
                task_id="media_1",
                kind="video",
                model="wan2.7",
                task_description="AI 生成内容: 海浪",
                conv_id="conv_1",
            )
        )
        hit = manager.find_in_flight(
            conv_id="conv_1", kind="video", model="wan2.7",
            task_description="AI 生成内容: 海浪",
        )
        assert hit is not None
        # kind 不同则不命中
        assert (
            manager.find_in_flight(
                conv_id="conv_1", kind="image", model="wan2.7",
                task_description="AI 生成内容: 海浪",
            )
            is None
        )

    def test_no_criteria_returns_none(self, manager):
        assert manager.find_in_flight(conv_id="conv_1") is None


# ---------------- WaitTasksTool 未知 ID ----------------

class TestWaitTasksToolUnknownIds:
    @pytest.mark.asyncio
    async def test_all_unknown_fails_explicitly(self, manager):
        from gyra.agent.tools.builtin.async_task.async_task_tools import (
            WaitTasksTool,
        )

        tool = WaitTasksTool(async_task_manager=manager)
        result = await tool.execute(
            {"task_ids": ["ghost_1", "ghost_2"], "timeout": 1}, context=None
        )
        assert not result.success
        assert "不存在" in (result.error or "")

    @pytest.mark.asyncio
    async def test_partial_unknown_waits_known(self, manager):
        from gyra.agent.tools.builtin.async_task.async_task_tools import (
            WaitTasksTool,
        )

        await manager.register_external(
            AsyncTaskSpec(task_id="t1", conv_id="c1")
        )
        manager.complete_external("t1", result="ok")

        tool = WaitTasksTool(async_task_manager=manager)
        result = await tool.execute(
            {"task_ids": ["t1", "ghost"], "timeout": 1}, context=None
        )
        assert result.success
        assert "t1" in (result.output or "")


# ---------------- SpawnAgentTaskTool 去重 + wait_async ----------------

class TestSpawnAgentTaskToolDedup:
    @pytest.mark.asyncio
    async def test_duplicate_spawn_reuses_in_flight(self, manager):
        from gyra.agent.tools.builtin.async_task.async_task_tools import (
            SpawnAgentTaskTool,
        )

        await manager.register_external(
            AsyncTaskSpec(
                task_id="t_existing",
                agent_name="图像生成助手",
                task_description="生成图片",
                conv_id="",  # 工具无 context 时 conv_id 为空
            )
        )

        tool = SpawnAgentTaskTool(async_task_manager=manager)
        result = await tool.execute(
            {"agent_name": "图像生成助手", "task": "生成图片"}, context=None
        )
        assert result.success
        assert result.metadata["reused"] is True
        assert result.metadata["task_id"] == "t_existing"
        # 阻塞等待默认开启
        assert result.metadata["wait_async"] is True
        assert "未重复提交" in (result.output or "")

    @pytest.mark.asyncio
    async def test_new_spawn_carries_wait_async_metadata(self, manager):
        from gyra.agent.tools.builtin.async_task.async_task_tools import (
            SpawnAgentTaskTool,
        )

        tool = SpawnAgentTaskTool(async_task_manager=manager)
        result = await tool.execute(
            {"agent_name": "some_agent", "task": "新任务", "wait_for_result": True},
            context=None,
        )
        assert result.success
        assert result.metadata["wait_async"] is True
        assert result.metadata["async_task"]["task_id"] == result.metadata["task_id"]

    @pytest.mark.asyncio
    async def test_fire_and_forget_disables_wait_async(self, manager):
        from gyra.agent.tools.builtin.async_task.async_task_tools import (
            SpawnAgentTaskTool,
        )

        tool = SpawnAgentTaskTool(async_task_manager=manager)
        result = await tool.execute(
            {"agent_name": "some_agent", "task": "新任务", "wait_for_result": False},
            context=None,
        )
        assert result.success
        assert result.metadata["wait_async"] is False
