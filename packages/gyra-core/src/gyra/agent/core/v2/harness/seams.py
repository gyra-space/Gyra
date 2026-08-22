"""Harness 能力缝（seam）——对齐 DeepSeek Harness 的能力缝设计。

每个 harness 能力 = 服务定义（ABC）+ 可替换 Provider 实现 + Consumer。
V2 引擎（run_loop / run_step / V2AgentRuntime）只消费 seam 接口，不依赖
具体实现，因此换 provider 即换行为（如本地子 Agent → 分布式子 Agent）。
"""
from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class SubagentSeam(abc.ABC):
    """子 Agent 统一 seam：V2 引擎内 spawn 子 agent 的唯一入口。

    Provider 示例：
      - ``SubAgentRuntime``（core/v2/subagent_runtime.py）：单进程内 run_step
        驱动（SYNC 阻塞等待 / ASYNC 后台 + transcript 持久化）；
      - ``DistributedSubagentBackend``（未来）：RPC 队列派发到其他机器。

    产品层 serve 的 SubagentCoordinator / AsyncTaskCoordinator 跟踪的是
    V1 主链路的 pending 子任务（gpts_conversations.extra），不在本 seam 内；
    引擎侧（V2）统一走本接口，避免 V2 与 serve 各自维护一套子 Agent 生命周期。
    """

    @abc.abstractmethod
    async def spawn(self, spec: Any):  # -> SubAgentHandle
        """按 spec 派生一个子 Agent，返回 handle。"""

    @abc.abstractmethod
    async def wait(
        self, handle: Any, timeout: Optional[float] = None
    ):  # -> SubAgentHandle
        """等待子 Agent 到达终态。"""

    @abc.abstractmethod
    async def get_status(self, task_id: str):  # -> Optional[SubAgentHandle]
        """按 task_id 查询子 Agent 当前状态（含从持久化 transcript 重建）。"""

    @abc.abstractmethod
    async def cancel(self, task_id: str) -> bool:
        """取消后台子 Agent；成功返回 True。"""

    @abc.abstractmethod
    async def resume(self, task_id: str):  # -> Optional[SubAgentHandle]
        """重新挂接到异步子 Agent，返回当前 handle。"""


class JobRegistry:
    """异步任务统一注册/查询（对齐 dsh ``ctx.jobs``）。

    把 AsyncTaskCoordinator 的"跟踪 + 完成监听"语义收敛为进程内接口：
    引擎侧只依赖本接口，不感知 media / subagent 等具体任务类型。
    产品层现有 AsyncTaskManager / AsyncTaskCoordinator 可适配进本注册表，
    作为跨进程分布式 backend 的本地投影。
    """

    _TERMINAL = frozenset({"completed", "failed", "timeout", "cancelled"})

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        task_id: str,
        *,
        conv_id: Optional[str] = None,
        kind: str = "async",
        **meta: Any,
    ) -> None:
        """注册一个异步任务。"""
        self._jobs[task_id] = {
            "task_id": task_id,
            "conv_id": conv_id,
            "kind": kind,
            "status": "pending",
            **meta,
        }

    def update_status(self, task_id: str, status: str, **meta: Any) -> None:
        """更新任务状态（completed/failed/timeout/cancelled 为终态）。"""
        if task_id in self._jobs:
            self._jobs[task_id].update({"status": status, **meta})

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询单任务状态；未注册返回 None。"""
        return self._jobs.get(task_id)

    def list_for_conv(self, conv_id: str) -> List[Dict[str, Any]]:
        """列出某会话下注册的全部任务。"""
        return [
            job for job in self._jobs.values() if job.get("conv_id") == conv_id
        ]

    def wait_all(
        self,
        conv_id: str,
        terminal: Optional[frozenset] = None,
    ) -> List[Dict[str, Any]]:
        """返回某会话下已到达终态的任务快照（完成监听轮询用）。"""
        terminal = terminal or self._TERMINAL
        return [
            job for job in self.list_for_conv(conv_id)
            if job.get("status") in terminal
        ]

    def clear(self) -> None:
        """清空全部记录（进程回收用）。"""
        self._jobs.clear()


# --------------------------------------------------------------------------- #
# Skill seam（对齐 DSH ``ctx.skills``）
# --------------------------------------------------------------------------- #

class SkillSeam(abc.ABC):
    """Skill 资源总线（对齐 DSH ``ctx.skills``）。

    V2 引擎默认消费本接口；具体实现（进程内 :class:`SkillRegistry`、
    未来跨进程后端）作为 provider 注入。

    设计要点：
      - list() / get() 接口与 DSH SkillProvider 一致（list 走 summary，
        get 加载完整 body）；
      - catalog_digest() 返回 SHA-256 前缀，供 consumer 判断"目录是否
        变化"——DSH 强调 *digest 变化才注入完整替换*；
      - subscribe() 接收 catalog invalidate 通知（push 通道）。
    """

    @abc.abstractmethod
    async def list(
        self,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> List[Any]:  # List[SkillSummary]
        """返回 invocation-neutral skill 摘要（按 name 排序）。"""

    @abc.abstractmethod
    async def get(
        self,
        name: str,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> Any:  # Optional[SkillDefinition]
        """按 name 加载完整 skill 定义；不存在返回 None。"""

    @abc.abstractmethod
    async def catalog_digest(
        self,
        layer_chain: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> str:
        """对当前目录算 digest；consumer 据此判断是否需要重新发布。"""

    @abc.abstractmethod
    def subscribe(self, callback: Any) -> Any:  # -> disposer
        """订阅 catalog 变化通知；返回 disposer。"""
