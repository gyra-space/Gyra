"""MediaJobRegistry - 异步媒体生成任务管理器。

把 generate_video 等长耗时媒体生成从「单次工具调用阻塞轮询(≤600s)」改成
「提交后秒级返回 job_id -> 后台轮询 -> 完成后通知注入下一轮推理」,镜像现有
``AsyncTaskManager`` 的后台任务 + 自动注入模式。

与 AsyncTaskManager 的区别:媒体生成不是「委派子 Agent」,而是 ``resume`` 协程
(poll+download -> MediaGenResult) + ``deliver`` 协程(存 AFS + 建 artifact ->
ToolResult)。故 spec 直接持有这两个 callable,在后台协程里依次 await。

进程级单例(与同包 ``MediaGenProviderRegistry`` 一致),job 按 ``conversation_id``
标记,通知按会话过滤。内存态:进程重启丢失(与 AsyncTaskManager 一致)。
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MediaJobStatus(str, Enum):
    """异步媒体生成任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class MediaJobSpec:
    """异步媒体生成任务规格。

    Attributes:
        conv_id: 所属会话 ID(用于通知按会话过滤)。
        kind: "video" / "image"。
        model: 模型名。
        description: 任务描述(摘要展示用)。
        resume: 无参协程,poll+download 后返回 MediaGenResult。
        deliver: 接收 MediaGenResult,存盘+建 artifact,返回 ToolResult。
        timeout: resume 最大耗时秒数。
        poll_hint: 给 Agent 的预估耗时提示,如 "~120s"。
    """

    conv_id: str
    kind: str
    model: str
    description: str
    resume: Callable[[], Awaitable[Any]]
    deliver: Callable[[Any], Awaitable[Any]]
    timeout: int = 600
    poll_hint: str = ""


@dataclass
class MediaJobState:
    """异步媒体生成任务运行状态。"""

    job_id: str
    spec: MediaJobSpec
    status: MediaJobStatus = MediaJobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tool_result: Any = None  # deliver 返回的 ToolResult(含 artifact / preview_url)
    error: Optional[str] = None
    consumed: bool = False

    def is_terminal(self) -> bool:
        return self.status in (
            MediaJobStatus.COMPLETED,
            MediaJobStatus.FAILED,
            MediaJobStatus.TIMEOUT,
            MediaJobStatus.CANCELLED,
        )

    def elapsed_seconds(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def to_summary(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.spec.kind,
            "model": self.spec.model,
            "description": self.spec.description[:120],
            "status": self.status.value,
            "elapsed": round(self.elapsed_seconds(), 1),
            "error": self.error,
        }


class MediaJobRegistry:
    """异步媒体生成任务管理器(进程级单例)。

    Usage::

        mgr = MediaJobRegistry.instance()
        job_id = mgr.submit(MediaJobSpec(
            conv_id=conv_id, kind="video", model=model,
            description=desc, resume=resume_fn, deliver=deliver_fn,
        ))
        # 下一轮推理前(react_master_agent.thinking)自动 collect + 注入通知;
        # 也可由 Agent 主动调用 check_media_job 查询。
    """

    _instance: Optional["MediaJobRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._jobs: Dict[str, MediaJobState] = {}
        self._bg_tasks: Dict[str, asyncio.Task] = {}
        self._max_jobs = 200
        self._initialized = True

    @classmethod
    def instance(cls) -> "MediaJobRegistry":
        """获取单例。"""
        return cls()

    # ── 提交 ────────────────────────────────────────────────────

    def submit(self, spec: MediaJobSpec) -> str:
        """提交一个媒体生成任务,立即返回 job_id。

        resume+deliver 在后台 asyncio.Task 里执行,不阻塞调用方。提交阶段的同步
        错误(如 403)由调用方在调用 provider.submit_video 时已捕获;这里只承接
        已经提交成功、拿到 task_id 的任务。
        """
        job_id = f"mjob_{uuid.uuid4().hex[:10]}"
        state = MediaJobState(job_id=job_id, spec=spec)
        self._jobs[job_id] = state
        self._maybe_gc()
        bg = asyncio.create_task(self._run_job(state), name=f"media_job_{job_id}")
        self._bg_tasks[job_id] = bg
        logger.info(
            f"[MediaJobRegistry] submitted {job_id}: kind={spec.kind} "
            f"model={spec.model}"
        )
        return job_id

    async def _run_job(self, state: MediaJobState) -> None:
        """后台执行:resume(poll+download) -> deliver(存盘+artifact)。"""
        state.status = MediaJobStatus.RUNNING
        state.started_at = datetime.now()
        try:
            result = await asyncio.wait_for(
                state.spec.resume(), timeout=state.spec.timeout
            )
            state.tool_result = await state.spec.deliver(result)
            state.status = MediaJobStatus.COMPLETED
        except asyncio.TimeoutError:
            state.status = MediaJobStatus.TIMEOUT
            state.error = f"生成超时({state.spec.timeout}s)"
        except asyncio.CancelledError:
            state.status = MediaJobStatus.CANCELLED
            state.error = "任务被取消"
            raise
        except Exception as e:
            state.status = MediaJobStatus.FAILED
            state.error = str(e)
            logger.error(
                f"[MediaJobRegistry] job {state.job_id} failed: {e}", exc_info=True
            )
        finally:
            state.completed_at = datetime.now()
            logger.info(
                f"[MediaJobRegistry] job {state.job_id} finished: "
                f"{state.status.value} ({state.elapsed_seconds():.1f}s)"
            )

    # ── 查询 ────────────────────────────────────────────────────

    def get_status(self, job_id: str) -> Optional[MediaJobState]:
        return self._jobs.get(job_id)

    def get_completed(
        self, conv_id: str = "", consume: bool = True
    ) -> List[MediaJobState]:
        """返回已终态且未消费的任务。

        按 conv_id 过滤(conv_id 为空或任务无 conv_id 时不限)。``consume=True``
        标记为已消费(下次不再返回),供自动注入去重。
        """
        out: List[MediaJobState] = []
        for state in self._jobs.values():
            if not state.is_terminal() or state.consumed:
                continue
            if conv_id and state.spec.conv_id and state.spec.conv_id != conv_id:
                continue
            if consume:
                state.consumed = True
            out.append(state)
        return out

    def has_pending(self, conv_id: str = "") -> bool:
        for s in self._jobs.values():
            if s.is_terminal():
                continue
            if conv_id and s.spec.conv_id and s.spec.conv_id != conv_id:
                continue
            return True
        return False

    async def cancel(self, job_id: str) -> bool:
        state = self._jobs.get(job_id)
        if not state or state.is_terminal():
            return False
        state.status = MediaJobStatus.CANCELLED
        state.completed_at = datetime.now()
        state.error = "用户取消"
        bg = self._bg_tasks.get(job_id)
        if bg and not bg.done():
            bg.cancel()
        return True

    # ── 格式化(注入 LLM 上下文) ────────────────────────────────

    def format_notifications(self, states: List[MediaJobState]) -> str:
        """格式化完成通知,用于注入下一轮推理上下文。"""
        if not states:
            return ""
        lines = ["[媒体生成完成通知]\n以下后台媒体生成任务已完成,请根据结果继续工作:\n"]
        for s in states:
            lines.append(f"### {s.spec.kind} {s.job_id} ({s.spec.model})")
            lines.append(f"状态: {s.status.value}  耗时: {s.elapsed_seconds():.1f}s")
            if s.status == MediaJobStatus.COMPLETED and s.tool_result is not None:
                output = getattr(s.tool_result, "output", None)
                if output:
                    lines.append(f"结果:\n{output}")
            if s.error:
                lines.append(f"错误: {s.error}")
            lines.append("")
        return "\n".join(lines)

    def format_summary(self, conv_id: str = "") -> str:
        """格式化所有任务摘要(check_media_job 无 job_id 时用)。"""
        targets = [
            s
            for s in self._jobs.values()
            if not conv_id or not s.spec.conv_id or s.spec.conv_id == conv_id
        ]
        if not targets:
            return "没有媒体生成任务"
        icons = {
            MediaJobStatus.COMPLETED: "✓",
            MediaJobStatus.RUNNING: "⟳",
            MediaJobStatus.PENDING: "○",
            MediaJobStatus.FAILED: "✗",
            MediaJobStatus.TIMEOUT: "⏰",
            MediaJobStatus.CANCELLED: "⊘",
        }
        lines = [f"共 {len(targets)} 个媒体生成任务:\n"]
        for s in sorted(targets, key=lambda x: x.created_at):
            icon = icons.get(s.status, "?")
            lines.append(
                f"  [{icon}] {s.job_id} ({s.spec.kind}/{s.spec.model}): {s.status.value}"
            )
            if s.started_at:
                lines.append(f"      耗时: {s.elapsed_seconds():.1f}s")
            lines.append(f"      描述: {s.spec.description[:80]}")
            if s.error:
                lines.append(f"      错误: {s.error}")
        return "\n".join(lines)

    # ── 维护 ────────────────────────────────────────────────────

    def _maybe_gc(self) -> None:
        """超过上限时丢弃最早已消费的终态任务,防内存泄漏。"""
        if len(self._jobs) < self._max_jobs:
            return
        consumed_terminal = [
            jid for jid, s in self._jobs.items() if s.consumed and s.is_terminal()
        ]
        for jid in consumed_terminal[: max(1, len(consumed_terminal) // 2)]:
            self._jobs.pop(jid, None)
            self._bg_tasks.pop(jid, None)


__all__ = [
    "MediaJobStatus",
    "MediaJobSpec",
    "MediaJobState",
    "MediaJobRegistry",
]
