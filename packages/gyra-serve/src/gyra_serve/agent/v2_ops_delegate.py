"""CoordinatorOpsDelegate — SubAgentOpsDelegate 的 gyra-serve 实现（V2→V1 运维桥）。

规格：docs/superpowers/specs/2026-08-29-v2-engine-v1-ops-merge-design.md §3.4

把 V2 SubAgentRuntime 的三个运维调用点映射到 V1 SubagentCoordinator，
使 V2 引擎的异步子任务复用 V1 运维底座（看板上板 / AsyncTaskManager 台账
镜像 / 终态回写 + 全部完成触发主会话 resume）：

    try_register    → coordinator.register_subagent（去重 + 上板 + 镜像一步到位）
    update_progress → coordinator.update_progress（d-subagent-board 进度条）
    on_terminal     → coordinator.on_subagent_done / on_subagent_failed
                      （DONE→done；CANCELLED→failed("任务已取消")，V1 无取消态）

依赖方向：gyra-serve → gyra-core（协议），反向无依赖。coordinator 经模块级
单例懒取（agent_chat build 时 set_subagent_coordinator 注入），delegate
构造不强依赖实例化顺序；coordinator 缺失（非 chat 场景）时全部调用静默
降级——try_register 返回 created=True 保证引擎照常执行，只丢看板不断执行。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from gyra.agent.core.subagent_handle import SubAgentMode as V1SubAgentMode
from gyra.agent.core.v2.subagent_handle import SubAgentStatus as V2SubAgentStatus
from gyra.agent.core.v2.subagent_ops_delegate import SubAgentRegistration

if TYPE_CHECKING:
    from gyra.agent.core.v2.subagent_handle import SubAgentHandle
    from gyra.agent.core.v2.subagent_runtime import SubAgentSpawnSpec
    from gyra_serve.agent.subagent_coordinator import SubagentCoordinator

logger = logging.getLogger(__name__)


class CoordinatorOpsDelegate:
    """V2 子任务 → V1 SubagentCoordinator 的运维委托适配器。

    每个 V2Agent 的 SubAgentRuntime 注入一个实例（engine-ready hook）；
    无状态，可安全共享。
    """

    def __init__(self, coordinator: Optional["SubagentCoordinator"] = None):
        # 显式传入优先（测试）；缺省运行时懒取模块级单例
        self._coordinator = coordinator

    def _resolve(self) -> Optional["SubagentCoordinator"]:
        if self._coordinator is not None:
            return self._coordinator
        try:
            from gyra_serve.agent.subagent_coordinator import (
                get_subagent_coordinator,
            )

            return get_subagent_coordinator()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[v2-ops-delegate] resolve coordinator failed: {e}")
            return None

    async def try_register(
        self, handle: "SubAgentHandle", spec: "SubAgentSpawnSpec"
    ) -> SubAgentRegistration:
        coord = self._resolve()
        if coord is None:
            return SubAgentRegistration(
                created=True,
                task_id=handle.task_id,
                sub_conv_id=handle.sub_conv_id,
            )
        v1_handle, created = await coord.register_subagent(
            main_conv_id=handle.parent_conv_id,
            sub_conv_id=handle.sub_conv_id,
            mode=V1SubAgentMode.ASYNC,
            agent_name=handle.agent_name,
            task=spec.task,
            params={
                "source": "v2_engine",
                "v2_task_id": handle.task_id,
            },
        )
        if created:
            return SubAgentRegistration(
                created=True,
                task_id=handle.task_id,
                sub_conv_id=handle.sub_conv_id,
            )
        # 去重命中：把已有在途任务的 sub_conv_id 交还引擎（LLM 经 V1
        # 台账 check_tasks/wait_tasks 用该 ID 复用），引擎短路本次 spawn
        return SubAgentRegistration(
            created=False,
            task_id=handle.task_id,
            sub_conv_id=v1_handle.sub_conv_id,
            status=v1_handle.status.value,
        )

    async def update_progress(
        self, handle: "SubAgentHandle", progress: int, note: str = ""
    ) -> None:
        coord = self._resolve()
        if coord is None:
            return
        await coord.update_progress(
            main_conv_id=handle.parent_conv_id,
            sub_conv_id=handle.sub_conv_id,
            progress=int(progress),
            steps=[note] if note else None,
        )

    async def on_terminal(
        self, handle: "SubAgentHandle", result_text: str = "", error: str = ""
    ) -> None:
        coord = self._resolve()
        if coord is None:
            return
        if handle.status is V2SubAgentStatus.DONE:
            await coord.on_subagent_done(
                handle.parent_conv_id,
                handle.sub_conv_id,
                result_text or "（子任务无文本输出）",
                success=True,
            )
        elif handle.status is V2SubAgentStatus.CANCELLED:
            # V1 SubAgentStatus 无 CANCELLED 态，按 FAILED 语义回写，
            # 文案传达取消事实（主 resume 判断不受影响）
            await coord.on_subagent_failed(
                handle.parent_conv_id,
                handle.sub_conv_id,
                error or "任务已取消",
            )
        else:
            await coord.on_subagent_failed(
                handle.parent_conv_id,
                handle.sub_conv_id,
                error or "子任务失败",
            )
