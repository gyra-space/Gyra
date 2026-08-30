"""单元测试：CoordinatorOpsDelegate（V2 子任务 → V1 SubagentCoordinator 运维桥）。

覆盖目标（规格 §3.4）：
- try_register 新建: V2 handle/spec → coordinator.register_subagent 参数映射
  （main_conv_id=parent_conv_id、mode=ASYNC、params.source=v2_engine）
- try_register 去重命中: created=False + 已有在途任务 sub_conv_id/status 交还引擎
- coordinator 缺失/解析异常 → 静默降级 created=True（不断引擎执行）
- update_progress: 双键映射 + note→steps
- on_terminal 三分派:
  DONE → on_subagent_done(success=True)；空结果用占位文案
  CANCELLED → on_subagent_failed("任务已取消")（V1 无取消态）
  FAILED → on_subagent_failed(error)
- 全部方法在无 coordinator 时不抛错
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gyra.agent.core.subagent_handle import (
    SubAgentMode as V1SubAgentMode,
)
from gyra.agent.core.subagent_handle import (
    SubAgentStatus as V1SubAgentStatus,
)
from gyra.agent.core.v2.subagent_handle import (
    SubAgentHandle,
    SubAgentMode,
    SubAgentStatus,
)
from gyra.agent.core.v2.subagent_runtime import SubAgentSpawnSpec
from gyra_serve.agent.v2_ops_delegate import CoordinatorOpsDelegate


def _make_v2_handle(
    status: SubAgentStatus = SubAgentStatus.RUNNING,
    sub_conv_id: str = "conv_sub_1",
) -> SubAgentHandle:
    now = time.time()
    return SubAgentHandle(
        task_id="task_v2_1",
        parent_step_id="step_1",
        parent_conv_id="conv_main_1",
        sub_conv_id=sub_conv_id,
        agent_name="coder",
        mode=SubAgentMode.ASYNC,
        status=status,
        created_at=now,
        updated_at=now,
    )


def _make_spec() -> SubAgentSpawnSpec:
    return SubAgentSpawnSpec(
        agent_name="coder",
        task="实现登录接口",
        parent_step_id="step_1",
        parent_conv_id="conv_main_1",
        parent_agent_id="agent_main",
    )


def _make_coordinator(
    register_return=None,
) -> MagicMock:
    coord = MagicMock()
    coord.register_subagent = AsyncMock(return_value=register_return)
    coord.update_progress = AsyncMock(return_value=None)
    coord.on_subagent_done = AsyncMock(return_value=None)
    coord.on_subagent_failed = AsyncMock(return_value=None)
    return coord


# ---------------- try_register ----------------


class TestTryRegister:
    @pytest.mark.asyncio
    async def test_new_task_maps_v2_handle_to_coordinator(self):
        v1_handle = MagicMock(
            sub_conv_id="conv_sub_1", status=V1SubAgentStatus.RUNNING
        )
        coord = _make_coordinator(register_return=(v1_handle, True))
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle()

        reg = await delegate.try_register(handle, _make_spec())

        assert reg.created is True
        assert reg.task_id == "task_v2_1"
        assert reg.sub_conv_id == "conv_sub_1"
        assert reg.status is None

        kwargs = coord.register_subagent.await_args.kwargs
        assert kwargs["main_conv_id"] == "conv_main_1"
        assert kwargs["sub_conv_id"] == "conv_sub_1"
        assert kwargs["mode"] == V1SubAgentMode.ASYNC
        assert kwargs["agent_name"] == "coder"
        assert kwargs["task"] == "实现登录接口"
        assert kwargs["params"] == {
            "source": "v2_engine",
            "v2_task_id": "task_v2_1",
        }

    @pytest.mark.asyncio
    async def test_dedup_hit_returns_existing_task_identity(self):
        v1_handle = MagicMock(
            sub_conv_id="conv_existing", status=V1SubAgentStatus.RUNNING
        )
        coord = _make_coordinator(register_return=(v1_handle, False))
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(sub_conv_id="conv_sub_new")

        reg = await delegate.try_register(handle, _make_spec())

        assert reg.created is False
        # 引擎用已有在途任务的 sub_conv_id 短路本次 spawn
        assert reg.sub_conv_id == "conv_existing"
        assert reg.status == "running"

    @pytest.mark.asyncio
    async def test_degrades_when_coordinator_missing(self):
        delegate = CoordinatorOpsDelegate(coordinator=None)
        handle = _make_v2_handle()

        with patch(
            "gyra_serve.agent.subagent_coordinator.get_subagent_coordinator",
            return_value=None,
        ):
            reg = await delegate.try_register(handle, _make_spec())

        # 降级放行：引擎照常执行，只丢看板
        assert reg.created is True
        assert reg.sub_conv_id == "conv_sub_1"

    @pytest.mark.asyncio
    async def test_degrades_when_coordinator_resolve_raises(self):
        delegate = CoordinatorOpsDelegate(coordinator=None)
        handle = _make_v2_handle()

        with patch(
            "gyra_serve.agent.subagent_coordinator.get_subagent_coordinator",
            side_effect=RuntimeError("not ready"),
        ):
            reg = await delegate.try_register(handle, _make_spec())

        assert reg.created is True


# ---------------- update_progress ----------------


class TestUpdateProgress:
    @pytest.mark.asyncio
    async def test_maps_double_key_and_steps(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle()

        await delegate.update_progress(handle, 42, note="step2 done")

        kwargs = coord.update_progress.await_args.kwargs
        assert kwargs["main_conv_id"] == "conv_main_1"
        assert kwargs["sub_conv_id"] == "conv_sub_1"
        assert kwargs["progress"] == 42
        assert kwargs["steps"] == ["step2 done"]

    @pytest.mark.asyncio
    async def test_empty_note_omits_steps(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle()

        await delegate.update_progress(handle, 10)

        assert coord.update_progress.await_args.kwargs["steps"] is None


# ---------------- on_terminal ----------------


class TestOnTerminal:
    @pytest.mark.asyncio
    async def test_done_dispatches_to_on_subagent_done(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(status=SubAgentStatus.DONE)

        await delegate.on_terminal(handle, result_text="登录接口完成")

        coord.on_subagent_done.assert_awaited_once_with(
            "conv_main_1", "conv_sub_1", "登录接口完成", success=True
        )
        coord.on_subagent_failed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_done_empty_result_uses_placeholder(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(status=SubAgentStatus.DONE)

        await delegate.on_terminal(handle, result_text="")

        args = coord.on_subagent_done.await_args.args
        assert args[2] == "（子任务无文本输出）"

    @pytest.mark.asyncio
    async def test_cancelled_maps_to_failed_with_cancel_text(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(status=SubAgentStatus.CANCELLED)

        await delegate.on_terminal(handle, error="用户中止")

        coord.on_subagent_failed.assert_awaited_once_with(
            "conv_main_1", "conv_sub_1", "用户中止"
        )
        coord.on_subagent_done.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancelled_without_error_uses_default_text(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(status=SubAgentStatus.CANCELLED)

        await delegate.on_terminal(handle)

        args = coord.on_subagent_failed.await_args.args
        assert args[2] == "任务已取消"

    @pytest.mark.asyncio
    async def test_failed_dispatches_to_on_subagent_failed(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(status=SubAgentStatus.FAILED)

        await delegate.on_terminal(handle, error="boom")

        coord.on_subagent_failed.assert_awaited_once_with(
            "conv_main_1", "conv_sub_1", "boom"
        )
        coord.on_subagent_done.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_failed_without_error_uses_default_text(self):
        coord = _make_coordinator()
        delegate = CoordinatorOpsDelegate(coordinator=coord)
        handle = _make_v2_handle(status=SubAgentStatus.FAILED)

        await delegate.on_terminal(handle)

        args = coord.on_subagent_failed.await_args.args
        assert args[2] == "子任务失败"


# ---------------- 降级：无 coordinator 全静默 ----------------


class TestNoCoordinatorDegradation:
    @pytest.mark.asyncio
    async def test_all_methods_noop_without_coordinator(self):
        delegate = CoordinatorOpsDelegate(coordinator=None)
        handle = _make_v2_handle(status=SubAgentStatus.DONE)

        with patch(
            "gyra_serve.agent.subagent_coordinator.get_subagent_coordinator",
            return_value=None,
        ):
            reg = await delegate.try_register(handle, _make_spec())
            await delegate.update_progress(handle, 50, note="s1")
            await delegate.on_terminal(handle, result_text="ok")

        assert reg.created is True
        # 未抛错即通过（降级语义：只丢看板不断执行）
