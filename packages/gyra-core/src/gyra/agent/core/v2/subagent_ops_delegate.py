"""SubAgentOpsDelegate — V2 子 Agent 运维委托协议（引擎 → 产品层单向注入）。

规格：docs/superpowers/specs/2026-08-29-v2-engine-v1-ops-merge-design.md §3.2

背景：V2 SubAgentRuntime 只管执行（run_loop 驱动），不感知产品层运维——
看板上板 / AsyncTaskManager 台账镜像 / 终态回写 / 全部完成触发主会话 resume，
这些由 gyra-serve 的 SubagentCoordinator 承载。gyra-core 不能反向依赖
gyra-serve，因此以 Protocol + 运行时注入（duck typing）解耦：

    SubAgentRuntime.spawn / progress / 终态 ──▶ SubAgentOpsDelegate（协议）
                                                      ▲
    CoordinatorOpsDelegate（gyra-serve 实现）─────────┘ 复用 V1 运维底座

不变量：
1. delegate 为 None 时引擎行为与改造前完全一致（纯增量，零回归）。
2. delegate 方法抛异常只记日志，不得中断子 Agent 执行主流程。
3. try_register 去重命中（created=False）时 spawn 短路——不创建新执行体，
   复用在途任务（昂贵任务防重复扣费，对齐 V1 register_subagent 语义）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from gyra.agent.core.v2.subagent_handle import SubAgentHandle
    from gyra.agent.core.v2.subagent_runtime import SubAgentSpawnSpec


@dataclass(frozen=True)
class SubAgentRegistration:
    """try_register 的注册结果。

    created: True=新注册（引擎继续创建执行体）；False=去重命中（引擎短路复用）。
    task_id: 引擎侧任务 ID（短路时为本次 spawn 生成的 task_id，仅作回显）。
    sub_conv_id: 生效子会话 ID——短路时为**已有任务**的 sub_conv_id，
        LLM 经它在 V1 台账（check_tasks/wait_tasks）复用在途任务。
    status: 短路时已有任务的状态文本（新建时为 None）。
    """

    created: bool
    task_id: str
    sub_conv_id: str
    status: Optional[str] = None


class SubAgentOpsDelegate(Protocol):
    """V2 子 Agent 运维委托协议（gyra-serve 侧实现，引擎侧可选依赖）。

    三个调用点全部位于 SubAgentRuntime：spawn ASYNC 分支（try_register）、
    run_loop 步进（update_progress）、_run_subagent_async 终态（on_terminal）。
    """

    async def try_register(
        self, handle: "SubAgentHandle", spec: "SubAgentSpawnSpec"
    ) -> SubAgentRegistration:
        """ASYNC spawn 前登记：上板 + 台账镜像 + 去重。

        返回 created=False 表示命中在途同任务，引擎应短路本次 spawn。
        """
        ...

    async def update_progress(
        self, handle: "SubAgentHandle", progress: int, note: str = ""
    ) -> None:
        """执行中进度上报（步级节流由引擎侧负责），progress ∈ [0, 100]。"""
        ...

    async def on_terminal(
        self, handle: "SubAgentHandle", result_text: str = "", error: str = ""
    ) -> None:
        """终态回写：按 handle.status 分派 DONE/FAILED/CANCELLED 的产品语义。"""
        ...
