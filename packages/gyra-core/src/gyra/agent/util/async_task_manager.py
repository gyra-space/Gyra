"""
AsyncTaskManager - 通用异步任务管理器

统一承载两类「后台执行 + 完成后自动注入下一轮推理」的任务：
1. subagent 模式（原 AsyncTaskManager）：主 Agent 通过 Tool 启动后台子 Agent 任务，
   主 Agent 不被阻塞，完成后自动注入结果。
2. media 模式（原 MediaJobRegistry）：长耗时媒体生成（generate_image/video）提交后
   秒级返回 job_id，后台协程轮询外部 API（resume: poll+download）+ 存盘交付
   （deliver: 存 AFS + 建 artifact），完成后自动注入通知。

两种模式共享同一套生命周期：提交 -> 后台执行 -> 查询/等待 -> 取消 -> 完成通知注入。
可选 JSONL 台账持久化（``ledger_path``），供 serve 层跨进程查询 API 使用。

核心设计：
- 通过 ``spec.resume`` 判定模式：非空走 media 协程模式，否则走 subagent 委派模式。
- asyncio.Semaphore 控制并发
- asyncio.Future per task 实现 wait 和依赖
- asyncio.Event 实现 wait_any 通知
"""

from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import json
import logging
import os
import threading
import uuid

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# media 单例默认台账路径。可用环境变量 GYRA_MEDIA_JOB_LEDGER 覆盖，
# 需保证 serve(查询 API) 与 agent worker(提交/执行) 使用同一路径。
DEFAULT_LEDGER_PATH = os.getenv("GYRA_MEDIA_JOB_LEDGER", "data/media_jobs.jsonl")


def _resolve_ledger_path(explicit: Optional[str]) -> str:
    return explicit or os.environ.get("GYRA_MEDIA_JOB_LEDGER") or DEFAULT_LEDGER_PATH


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def normalize_task_text(text: str) -> str:
    """任务文本归一化（小写 + 压缩空白），供防重复提交的 dedup key 使用。"""
    return " ".join((text or "").split()).lower()


# ==================== 数据模型 ====================


class AsyncTaskStatus(str, Enum):
    """异步任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AsyncTaskSpec(BaseModel):
    """
    异步任务规格

    Attributes:
        task_id: 唯一任务 ID，自动生成
        agent_name: 目标子 Agent 名称（subagent 模式）
        task_description: 任务描述（subagent 模式传给子 Agent 的 prompt；media 模式作摘要）
        context: 上下文信息
        timeout: 超时秒数
        depend_on: 依赖的 task_id 列表（DAG 编排，subagent 模式）
        conv_id: 所属会话 ID（media 模式，用于通知按会话过滤）
        kind: 任务类别（media 模式："video" / "image"）
        model: 模型名（media 模式）
        poll_hint: 给 Agent 的预估耗时提示（media 模式，如 "~60-180s"）
        resume: media 模式的执行协程，无参，poll+download 后返回结果
        deliver: media 模式的交付协程，接收 resume 结果，存盘+建 artifact，返回 ToolResult
        delegate: subagent 模式的委派协程，无参，内部闭包已绑定 subagent_manager(+adapter)。
            统一实例下 subagent 任务不依赖 manager 的 ``subagent_manager``，而是把
            delegate 连同调用上下文一并塞进 spec，使单个进程级单例能同时跑两类任务。
    """
    task_id: str = Field(default_factory=lambda: f"atask_{uuid.uuid4().hex[:8]}")
    agent_name: str = ""
    task_description: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 600
    depend_on: List[str] = Field(default_factory=list)
    # media 模式扩展字段
    conv_id: str = ""
    kind: str = ""
    model: str = ""
    poll_hint: str = ""
    resume: Optional[Callable[[], Any]] = None
    deliver: Optional[Callable[[Any], Any]] = None
    # subagent 模式统一实例字段：已绑定 adapter 的委派协程
    delegate: Optional[Callable[[], Any]] = None


class TaskLedger:
    """异步任务持久化台账（JSONL）。

    每条行是一个任务的完整记录；同一 task_id 多次写入时以最后一次为准（读时
    按 task_id 去重）。写入采用 append，读时最后一条覆盖旧记录，避免频繁回写
    整个文件。用于跨进程查询与重启不丢。
    """

    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()

    @property
    def path(self) -> str:
        return self._path

    def upsert(self, record: Dict[str, Any]) -> None:
        """追加一条任务记录（同 task_id 以最后一次为准）。"""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self._path)), exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:  # noqa: BLE001 - 台账写失败不应阻断主流程
                logger.warning(f"[TaskLedger] write failed: {e}")

    def read_all(self) -> Dict[str, Dict[str, Any]]:
        """读取全部任务记录，同 task_id 以最后一次为准。"""
        records: Dict[str, Dict[str, Any]] = {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("task_id"):
                            records[rec["task_id"]] = rec
                    except Exception:  # noqa: BLE001 - 容忍脏行
                        continue
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[TaskLedger] read failed: {e}")
        return records


class AsyncTaskState(BaseModel):
    """
    异步任务运行状态 - AsyncTaskManager 内部维护

    Attributes:
        spec: 任务规格
        status: 当前状态
        created_at: 创建时间
        started_at: 开始执行时间
        completed_at: 完成时间
        result: 成功时的结果（subagent 为文本；media 为 deliver 返回的 ToolResult）
        error: 失败时的错误信息
        artifacts: 产出物字典
        consumed: 结果是否已被主 Agent 消费
    """
    spec: AsyncTaskSpec
    status: AsyncTaskStatus = AsyncTaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    consumed: bool = False

    class Config:
        arbitrary_types_allowed = True

    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.status in (
            AsyncTaskStatus.COMPLETED,
            AsyncTaskStatus.FAILED,
            AsyncTaskStatus.TIMEOUT,
            AsyncTaskStatus.CANCELLED,
        )

    def elapsed_seconds(self) -> float:
        """已用时间（秒）"""
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def result_text(self) -> str:
        """把 result 归一化为文本（兼容 str 与带 .output 的 ToolResult）。"""
        if self.result is None:
            return ""
        if isinstance(self.result, str):
            return self.result
        return getattr(self.result, "output", None) or ""

    def to_summary(self) -> Dict[str, Any]:
        """生成摘要字典"""
        return {
            "task_id": self.spec.task_id,
            "agent_name": self.spec.agent_name,
            "kind": self.spec.kind,
            "model": self.spec.model,
            "conv_id": self.spec.conv_id or "",
            "description": (self.spec.task_description or "")[:120],
            "status": self.status.value,
            "elapsed": round(self.elapsed_seconds(), 1),
            "result_preview": (self.result_text() or "")[:300] if self.result else None,
            "error": self.error,
        }

    def to_record(self) -> Dict[str, Any]:
        """生成持久化台账记录（供查询 API / 重启恢复）。

        从 ``result``（media 模式为 ToolResult）中提取交付物信息，使下游能拿到
        AFS 管理的预览/下载地址，而不是仅有模型返回的原始 OSS 地址。
        """
        artifact: Optional[Dict[str, Any]] = None
        result_preview: Optional[str] = None
        if self.result is not None:
            if isinstance(self.result, str):
                result_preview = self.result[:800]
            else:
                output = getattr(self.result, "output", None)
                if output:
                    result_preview = str(output)[:800]
                arts = getattr(self.result, "artifacts", None) or []
                if arts:
                    a = arts[0]
                    artifact = {
                        "name": getattr(a, "name", None),
                        "type": getattr(a, "type", None),
                        "url": getattr(a, "url", None),
                        "mime_type": getattr(a, "mime_type", None),
                    }
        # detail：请求侧（spec.context：provider task_id / prompt / 参数）
        # + 响应侧（provider 原始链接 / task_id / 分辨率等 media 元数据），
        # 供重启/中断后按 provider task_id 找回任务与下载地址。
        detail: Dict[str, Any] = dict(self.spec.context or {})
        result_meta = getattr(self.result, "metadata", None) or {}
        media_meta = result_meta.get("media") if isinstance(result_meta, dict) else None
        if not media_meta and artifact is not None:
            arts = getattr(self.result, "artifacts", None) or []
            media_meta = getattr(arts[0], "metadata", None) if arts else None
        if isinstance(media_meta, dict) and media_meta:
            detail["provider_response"] = {
                k: v
                for k, v in media_meta.items()
                if isinstance(v, (str, int, float, bool))
            }
        return {
            "task_id": self.spec.task_id,
            "conv_id": self.spec.conv_id or "",
            "kind": self.spec.kind,
            "model": self.spec.model,
            "description": (self.spec.task_description or "")[:200],
            "status": self.status.value,
            "created_at": _iso(self.created_at),
            "started_at": _iso(self.started_at),
            "completed_at": _iso(self.completed_at),
            "error": self.error,
            "result_preview": result_preview,
            "artifact": artifact,
            "detail": detail or None,
        }


# ==================== 核心管理器 ====================


class AsyncTaskManager:
    """
    通用异步任务管理器

    管理后台任务的完整生命周期：提交、执行、查询、等待、取消。支持两类任务：
    - subagent：委派子 Agent 执行（需 ``subagent_manager`` 暴露 ``async delegate``，
      或经 ``spec.delegate`` 传入已绑定上下文的委派协程）。
    - media：后台协程 ``resume`` + ``deliver``（长耗时媒体生成。

    统一实例：进程级单例 ``instance()`` 同时承载两类任务，media 工具与
    spawn_agent_task 都提交到同一实例，实现统一查看 / 统一持久化 / 统一恢复。

    Usage (subagent)::

        manager = AsyncTaskManager(
            subagent_manager=subagent_mgr,
            max_concurrent=5,
            parent_session_id="session_abc",
        )
        task_id = await manager.spawn(AsyncTaskSpec(
            agent_name="code_reviewer",
            task_description="Review the auth module",
        ))

    Usage (media)::

        mgr = AsyncTaskManager.media_instance()
        job_id = await mgr.spawn(AsyncTaskSpec(
            conv_id=conv_id, kind="video", model="happyhorse-1.1-t2v",
            task_description="...", resume=resume_fn, deliver=deliver_fn,
        ))

    持久化：默认不落盘；经 ``set_global_ledger`` 注入 LEDGER（如 serve 层的
    AsyncTaskDao）后，所有实例（含单例）统一写 DB，支撑分布式查询与恢复。
    ``ledger_path`` 显式传入时仍可用 JSONL 兜底（测试 / 无 DB 场景）。

    Args:
        subagent_manager: 子 Agent 委派器（media 模式可为 None）。
        max_concurrent: 最大并发任务数。
        parent_session_id: 父会话 ID。
        ledger_path: 可选 JSONL 台账路径，开启跨进程持久化与查询。
        on_task_complete / on_task_failed: 完成/失败回调。
    """

    _media_instance: Optional["AsyncTaskManager"] = None
    _global_ledger: Optional[Any] = None

    def __init__(
        self,
        subagent_manager: Any = None,
        max_concurrent: int = 5,
        parent_session_id: str = "",
        ledger_path: Optional[str] = None,
        on_task_complete: Optional[Callable[["AsyncTaskState"], Any]] = None,
        on_task_failed: Optional[Callable[["AsyncTaskState"], Any]] = None,
    ):
        self._subagent_manager = subagent_manager
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._parent_session_id = parent_session_id
        self._max_concurrent = max_concurrent

        # 任务存储
        self._tasks: Dict[str, AsyncTaskState] = {}
        self._futures: Dict[str, asyncio.Future] = {}
        self._bg_tasks: Dict[str, asyncio.Task] = {}

        # 持久化台账：显式 path > 全局注入 ledger（DB）> 无
        self._ledger = self._resolve_ledger(ledger_path)

        # 通知机制
        self._completion_event = asyncio.Event()

        # 回调
        self._on_complete = on_task_complete
        self._on_failed = on_task_failed

        # 统计
        self._total_spawned = 0
        self._total_completed = 0
        self._total_failed = 0

    @classmethod
    def set_global_ledger(cls, ledger: Any) -> None:
        """注入全局持久化 ledger（如 serve 层的 AsyncTaskDao）。

        注入后，所有新创建的实例（含 media 单例）都默认使用该 ledger 做持久化，
        实现跨实例 / 跨进程统一查询与恢复（分布式）。ledger 需暴露
        ``upsert(record)`` 与 ``read_all()`` 接口（与 AsyncTaskDao 对齐）。
        """
        cls._global_ledger = ledger

    @classmethod
    def _resolve_ledger(cls, ledger_path: Optional[str]) -> Any:
        """按优先级解析 ledger：显式 path > 全局注入（DB）> 无。"""
        if ledger_path is not None:
            return TaskLedger(_resolve_ledger_path(ledger_path))
        if cls._global_ledger is not None:
            return cls._global_ledger
        return None

    @classmethod
    def media_instance(cls, ledger_path: Optional[str] = None) -> "AsyncTaskManager":
        """获取进程级统一单例（media 与 subagent 任务共用）。

        供媒体生成工具、spawn_agent_task 与 serve 查询 API 共用。media 任务不委派
        子 Agent，故 subagent_manager 为 None；subagent 任务经 ``spec.delegate``
        打包委派协程提交到同一实例。

        持久化：显式 ``ledger_path`` > 全局注入 ledger（serve 启动时注入
        AsyncTaskDao，写 DB）> JSONL 兜底（无 DB 的纯 core / 测试场景）。
        """
        if ledger_path is None and cls._global_ledger is None:
            ledger_path = _resolve_ledger_path(None)
        if cls._media_instance is None:
            cls._media_instance = cls(
                subagent_manager=None,
                max_concurrent=5,
                ledger_path=ledger_path,
            )
        return cls._media_instance

    # ==================== 任务提交 ====================

    async def spawn(self, spec: AsyncTaskSpec) -> str:
        """
        提交异步任务，立即返回 task_id。

        任务在后台异步执行，不阻塞调用方。media 模式（spec.resume 非空）走协程
        执行；subagent 模式走委派执行。

        Args:
            spec: 任务规格

        Returns:
            task_id: 任务唯一标识

        Raises:
            ValueError: 如果 task_id 重复
        """
        if spec.task_id in self._tasks:
            raise ValueError(f"Task ID '{spec.task_id}' already exists")

        state = AsyncTaskState(spec=spec)
        self._tasks[spec.task_id] = state

        # 创建 Future 用于等待
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._futures[spec.task_id] = future

        # 验证依赖是否存在
        for dep_id in spec.depend_on:
            if dep_id not in self._tasks:
                logger.warning(
                    f"[AsyncTaskManager] Task {spec.task_id} depends on "
                    f"unknown task {dep_id}, will proceed anyway"
                )

        # 启动后台执行
        if spec.depend_on:
            bg_task = asyncio.create_task(
                self._wait_deps_then_run(state),
                name=f"async_task_{spec.task_id}",
            )
        else:
            bg_task = asyncio.create_task(
                self._run_task(state),
                name=f"async_task_{spec.task_id}",
            )
        self._bg_tasks[spec.task_id] = bg_task

        self._total_spawned += 1
        self._persist(state)

        logger.info(
            f"[AsyncTaskManager] Spawned task {spec.task_id}: "
            f"mode={'media' if spec.resume else 'subagent'}, "
            f"agent={spec.agent_name or spec.model}, "
            f"deps={spec.depend_on or 'none'}"
        )

        return spec.task_id

    # ==================== 外部任务镜像（SubAgent async 状态桥接） ====================

    async def register_external(self, spec: AsyncTaskSpec) -> str:
        """登记一个由外部驱动生命周期的任务（不启动任何执行体）。

        用于 SubAgent mode=async：执行体在 SubagentCoordinator（后台子会话），
        这里只镜像状态，使 check_tasks/wait_tasks 能用 sub_conv_id 查询与等待。
        spec.context 需标记 ``external=True``，AsyncTaskCoordinator 对这类任务
        只消费不触发 resume（resume 仍由外部驱动方负责）。

        幂等：task_id 已存在时直接返回原 id。
        """
        existing = self._tasks.get(spec.task_id)
        if existing is not None:
            return spec.task_id

        spec.context = {**(spec.context or {}), "external": True}
        state = AsyncTaskState(spec=spec)
        state.status = AsyncTaskStatus.RUNNING
        state.started_at = datetime.now()
        self._tasks[spec.task_id] = state

        loop = asyncio.get_running_loop()
        self._futures[spec.task_id] = loop.create_future()

        self._total_spawned += 1
        self._persist(state)
        logger.info(
            f"[AsyncTaskManager] Registered external task {spec.task_id}: "
            f"agent={spec.agent_name or spec.model}, conv={spec.conv_id}"
        )
        return spec.task_id

    def complete_external(
        self,
        task_id: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> bool:
        """把外部任务置为终态（由外部驱动方回调）。

        Returns:
            是否成功置终态；任务不存在或已是终态时返回 False。
        """
        state = self._tasks.get(task_id)
        if state is None or state.is_terminal():
            return False

        if error:
            state.status = AsyncTaskStatus.FAILED
            state.error = error
            self._total_failed += 1
        else:
            state.status = AsyncTaskStatus.COMPLETED
            state.result = result
            self._total_completed += 1
        state.completed_at = datetime.now()

        self._persist(state)
        self._resolve_future(task_id, state)
        logger.info(
            f"[AsyncTaskManager] External task {task_id} finished: "
            f"status={state.status.value}, elapsed={state.elapsed_seconds():.1f}s"
        )
        return True

    def merge_external_context(self, task_id: str, fields: Dict[str, Any]) -> bool:
        """向外部任务的 spec.context 合并字段并重新持久化。

        用于生成类任务在拿到 provider task_id / 原始下载地址后补充进台账
        （gpts_async_tasks.detail），保证昂贵请求的结果可按记录找回。
        """
        state = self._tasks.get(task_id)
        if state is None:
            return False
        state.spec.context = {**(state.spec.context or {}), **(fields or {})}
        self._persist(state)
        return True

    # ==================== 防重复提交查询 ====================

    def known_task_ids(self, task_ids: List[str]) -> List[str]:
        """返回 task_ids 中本管理器已知的部分（供工具层对未知 ID 显式报错）。"""
        return [tid for tid in task_ids if tid in self._tasks]

    def find_in_flight(
        self,
        *,
        conv_id: str = "",
        agent_name: str = "",
        kind: str = "",
        model: str = "",
        task_description: str = "",
    ) -> Optional["AsyncTaskState"]:
        """按 dedup key 查找内容相同的在途（非终态）任务。

        dedup key = (conv_id, agent_name, kind, model, 归一化 task_description)；
        提供的字段必须全部相等才算命中，task_description 为空时不参与匹配
        （此时必须至少提供 agent_name/kind/model 之一，避免误匹配）。
        仅进程内存态生效（跨进程查 ledger 代价高，暂不覆盖）。

        用于昂贵任务（图片/视频生成、子 Agent 委派）提交前去重：命中即复用，
        不重复提交、不重复扣费。
        """
        norm = normalize_task_text(task_description)
        if not norm and not (agent_name or kind or model):
            return None
        for state in self._tasks.values():
            if state.is_terminal():
                continue
            spec = state.spec
            if (spec.conv_id or "") != (conv_id or ""):
                continue
            if agent_name and (spec.agent_name or "") != agent_name:
                continue
            if kind and (spec.kind or "") != kind:
                continue
            if model and (spec.model or "") != model:
                continue
            if norm and normalize_task_text(spec.task_description) != norm:
                continue
            return state
        return None

    # ==================== 任务执行 ====================

    async def _wait_deps_then_run(self, state: AsyncTaskState) -> None:
        """等待依赖任务完成后再执行"""
        task_id = state.spec.task_id

        for dep_id in state.spec.depend_on:
            dep_future = self._futures.get(dep_id)
            if dep_future and not dep_future.done():
                logger.debug(
                    f"[AsyncTaskManager] Task {task_id} waiting for dependency {dep_id}"
                )
                try:
                    await asyncio.wait_for(
                        asyncio.shield(dep_future),
                        timeout=state.spec.timeout,
                    )
                except asyncio.TimeoutError:
                    state.status = AsyncTaskStatus.TIMEOUT
                    state.completed_at = datetime.now()
                    state.error = f"等待依赖任务 {dep_id} 超时"
                    self._resolve_future(task_id, state)
                    return
                except asyncio.CancelledError:
                    state.status = AsyncTaskStatus.CANCELLED
                    state.completed_at = datetime.now()
                    state.error = f"依赖任务 {dep_id} 被取消"
                    self._resolve_future(task_id, state)
                    return

            # 检查依赖是否成功
            dep_state = self._tasks.get(dep_id)
            if dep_state and dep_state.status != AsyncTaskStatus.COMPLETED:
                state.status = AsyncTaskStatus.FAILED
                state.completed_at = datetime.now()
                state.error = (
                    f"依赖任务 {dep_id} 未成功完成 "
                    f"(status={dep_state.status.value})"
                )
                self._resolve_future(task_id, state)
                return

        # 所有依赖完成，开始执行
        await self._run_task(state)

    async def _run_task(self, state: AsyncTaskState) -> None:
        """实际执行任务（受 semaphore 并发控制）"""
        task_id = state.spec.task_id

        # 如果任务已被取消
        if state.status == AsyncTaskStatus.CANCELLED:
            self._resolve_future(task_id, state)
            return

        async with self._semaphore:
            state.status = AsyncTaskStatus.RUNNING
            state.started_at = datetime.now()

            logger.info(
                f"[AsyncTaskManager] Running task {task_id}: "
                f"mode={'media' if state.spec.resume else 'subagent'}, "
                f"target={state.spec.agent_name or state.spec.model}"
            )

            try:
                if state.spec.resume is not None:
                    # media 模式：resume(poll+download) -> deliver(存盘+artifact)
                    result = await asyncio.wait_for(
                        state.spec.resume(), timeout=state.spec.timeout
                    )
                    state.result = await state.spec.deliver(result)
                    state.status = AsyncTaskStatus.COMPLETED
                    self._total_completed += 1
                else:
                    # subagent 模式：优先用 spec.delegate（统一实例，已绑定
                    # subagent_manager+adapter 的委派协程）；否则回退 subagent_manager。
                    if state.spec.delegate is not None:
                        result = await asyncio.wait_for(
                            state.spec.delegate(),
                            timeout=state.spec.timeout,
                        )
                    elif self._subagent_manager is not None:
                        result = await asyncio.wait_for(
                            self._subagent_manager.delegate(
                                subagent_name=state.spec.agent_name,
                                task=state.spec.task_description,
                                parent_session_id=self._parent_session_id,
                                context=state.spec.context,
                                sync=True,
                            ),
                            timeout=state.spec.timeout,
                        )
                    else:
                        raise RuntimeError(
                            f"subagent 任务缺少委派协程（spec.delegate 为空且 "
                            f"subagent_manager 未配置），无法委派给 "
                            f"'{state.spec.agent_name}'"
                        )
                    if getattr(result, "success", False):
                        state.status = AsyncTaskStatus.COMPLETED
                        state.result = getattr(result, "output", None)
                        state.artifacts = getattr(result, "artifacts", {}) or {}
                        self._total_completed += 1

                        if self._on_complete:
                            try:
                                await self._on_complete(state)
                            except Exception as e:
                                logger.warning(f"[AsyncTaskManager] on_complete callback failed: {e}")
                    else:
                        state.status = AsyncTaskStatus.FAILED
                        state.error = result.error or "子 Agent 执行失败"
                        self._total_failed += 1

                        if self._on_failed:
                            try:
                                await self._on_failed(state)
                            except Exception as e:
                                logger.warning(f"[AsyncTaskManager] on_failed callback failed: {e}")

            except asyncio.TimeoutError:
                state.status = AsyncTaskStatus.TIMEOUT
                state.error = f"执行超时（{state.spec.timeout}秒）"
                self._total_failed += 1
                logger.warning(f"[AsyncTaskManager] Task {task_id} timed out")

            except asyncio.CancelledError:
                state.status = AsyncTaskStatus.CANCELLED
                state.error = "任务被取消"
                logger.info(f"[AsyncTaskManager] Task {task_id} cancelled")

            except Exception as e:
                state.status = AsyncTaskStatus.FAILED
                state.error = str(e)
                self._total_failed += 1
                logger.error(f"[AsyncTaskManager] Task {task_id} failed: {e}")

            finally:
                state.completed_at = datetime.now()
                self._persist(state)
                self._resolve_future(task_id, state)

                logger.info(
                    f"[AsyncTaskManager] Task {task_id} finished: "
                    f"status={state.status.value}, "
                    f"elapsed={state.elapsed_seconds():.1f}s"
                )

    def _resolve_future(self, task_id: str, state: AsyncTaskState) -> None:
        """完成 Future 并触发通知"""
        future = self._futures.get(task_id)
        if future and not future.done():
            future.set_result(state)
        self._completion_event.set()

    def _persist(self, state: AsyncTaskState) -> None:
        """把任务当前状态写入持久化台账（若开启）。"""
        if not self._ledger:
            return
        try:
            self._ledger.upsert(state.to_record())
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[AsyncTaskManager] persist {state.spec.task_id} failed: {e}")

    # ==================== 状态查询 ====================

    def get_status(self, task_id: str) -> Optional[AsyncTaskState]:
        """获取指定任务状态"""
        return self._tasks.get(task_id)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务的摘要状态"""
        return {
            tid: state.to_summary()
            for tid, state in self._tasks.items()
        }

    def get_completed_results(
        self, consume: bool = True, conv_id: str = ""
    ) -> List[AsyncTaskState]:
        """
        获取已完成但未消费的任务结果。

        Args:
            consume: 是否标记为已消费（下次不再返回）
            conv_id: 非空时仅返回该会话的任务（media 模式按会话过滤）

        Returns:
            已完成的任务状态列表
        """
        results = []
        for state in self._tasks.values():
            if state.is_terminal() and not state.consumed:
                if conv_id and state.spec.conv_id and state.spec.conv_id != conv_id:
                    continue
                results.append(state)
                if consume:
                    state.consumed = True
        return results

    def has_pending_tasks(self) -> bool:
        """是否有未完成的任务"""
        return any(
            not state.is_terminal()
            for state in self._tasks.values()
        )

    def has_active_tasks_for_conv(self, conv_id: str) -> bool:
        """检查指定会话是否有未完成的（非终态）任务。

        供 AsyncTaskCoordinator 在轮次结束判定是否置 WAITING、以及恢复判定使用。
        """
        if not conv_id:
            return False
        return any(
            not state.is_terminal() and state.spec.conv_id == conv_id
            for state in self._tasks.values()
        )

    # ==================== 等待机制 ====================

    async def wait_any(self, timeout: float = 30) -> List[AsyncTaskState]:
        """
        等待任意任务完成，返回新完成的任务。

        如果已有未消费的完成结果，立即返回。
        否则阻塞直到有任务完成或超时。

        Args:
            timeout: 最大等待秒数

        Returns:
            新完成的任务状态列表
        """
        # 先检查是否有未消费结果
        existing = self.get_completed_results(consume=True)
        if existing:
            return existing

        # 等待新完成
        self._completion_event.clear()
        try:
            await asyncio.wait_for(self._completion_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self.get_completed_results(consume=True)

    async def wait_all(
        self,
        task_ids: List[str],
        timeout: float = 300,
    ) -> List[AsyncTaskState]:
        """
        等待指定任务全部完成。

        Args:
            task_ids: 需要等待的 task_id 列表
            timeout: 最大等待秒数

        Returns:
            指定任务的状态列表
        """
        futures = []
        for tid in task_ids:
            future = self._futures.get(tid)
            if future and not future.done():
                futures.append(future)

        if futures:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*[asyncio.shield(f) for f in futures], return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"[AsyncTaskManager] wait_all timed out after {timeout}s, "
                    f"some tasks may not be complete"
                )

        results = []
        for tid in task_ids:
            state = self._tasks.get(tid)
            if state:
                if not state.consumed:
                    state.consumed = True
                results.append(state)
        return results

    # ==================== 取消 ====================

    async def cancel(self, task_id: str) -> bool:
        """
        取消指定任务。

        Args:
            task_id: 要取消的任务 ID

        Returns:
            是否成功取消
        """
        state = self._tasks.get(task_id)
        if not state:
            return False

        if state.is_terminal():
            return False

        state.status = AsyncTaskStatus.CANCELLED
        state.completed_at = datetime.now()
        state.error = "任务被用户取消"

        # 取消后台协程
        bg_task = self._bg_tasks.get(task_id)
        if bg_task and not bg_task.done():
            bg_task.cancel()

        self._persist(state)
        self._resolve_future(task_id, state)

        logger.info(f"[AsyncTaskManager] Task {task_id} cancelled by user")
        return True

    # ==================== 持久化台账查询（跨进程 / 重启可见） ====================

    def list_jobs(
        self,
        conv_id: str = "",
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """从持久化台账查询任务记录（按创建时间倒序）。

        供 serve 层查询 API / 前端展示使用，不依赖进程内存态，因此重启后仍可见。
        """
        if not self._ledger:
            return []
        records = list(self._ledger.read_all().values())
        records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        out: List[Dict[str, Any]] = []
        for r in records:
            if conv_id and r.get("conv_id") and r["conv_id"] != conv_id:
                continue
            if status and r.get("status") != status:
                continue
            out.append(r)
            if len(out) >= limit:
                break
        return out

    def get_job(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从持久化台账查询单个任务记录。"""
        if not self._ledger:
            return None
        return self._ledger.read_all().get(task_id)

    # ==================== 格式化输出 ====================

    def format_status_table(self, task_ids: Optional[List[str]] = None) -> str:
        """
        格式化任务状态为 LLM 友好的文本。

        Args:
            task_ids: 指定任务 ID 列表，为空则显示全部

        Returns:
            格式化的状态文本
        """
        STATUS_ICONS = {
            AsyncTaskStatus.COMPLETED: "✓",
            AsyncTaskStatus.RUNNING: "⟳",
            AsyncTaskStatus.FAILED: "✗",
            AsyncTaskStatus.PENDING: "○",
            AsyncTaskStatus.TIMEOUT: "⏰",
            AsyncTaskStatus.CANCELLED: "⊘",
        }

        targets = task_ids or list(self._tasks.keys())
        if not targets:
            return "没有后台任务"

        lines = [f"共 {len(targets)} 个任务:\n"]
        for tid in targets:
            state = self._tasks.get(tid)
            if not state:
                lines.append(f"  [?] {tid}: 未找到")
                continue

            icon = STATUS_ICONS.get(state.status, "?")
            label = state.spec.agent_name or state.spec.model or "?"
            line = f"  [{icon}] {tid} ({label}): {state.status.value}"
            if state.started_at:
                line += f"  [{state.elapsed_seconds():.1f}s]"
            lines.append(line)

            desc = state.spec.task_description[:80]
            lines.append(f"      任务: {desc}")

            if state.result_text():
                preview = state.result_text()[:200].replace("\n", " ")
                lines.append(f"      结果: {preview}")
            if state.error:
                lines.append(f"      错误: {state.error}")

        return "\n".join(lines)

    def format_summary(self, conv_id: str = "") -> str:
        """格式化所有任务摘要（check_media_job 无 job_id 时用）。"""
        targets = [
            s
            for s in self._tasks.values()
            if not conv_id or not s.spec.conv_id or s.spec.conv_id == conv_id
        ]
        if not targets:
            return "没有媒体生成任务"
        icons = {
            AsyncTaskStatus.COMPLETED: "✓",
            AsyncTaskStatus.RUNNING: "⟳",
            AsyncTaskStatus.PENDING: "○",
            AsyncTaskStatus.FAILED: "✗",
            AsyncTaskStatus.TIMEOUT: "⏰",
            AsyncTaskStatus.CANCELLED: "⊘",
        }
        lines = [f"共 {len(targets)} 个媒体生成任务:\n"]
        for s in sorted(targets, key=lambda x: x.created_at):
            icon = icons.get(s.status, "?")
            label = s.spec.model or s.spec.agent_name or "?"
            lines.append(
                f"  [{icon}] {s.spec.task_id} ({s.spec.kind}/{label}): {s.status.value}"
            )
            if s.started_at:
                lines.append(f"      耗时: {s.elapsed_seconds():.1f}s")
            lines.append(f"      描述: {s.spec.task_description[:80]}")
            if s.error:
                lines.append(f"      错误: {s.error}")
        return "\n".join(lines)

    def format_results(self, states: List["AsyncTaskState"]) -> str:
        """格式化任务结果为详细文本"""
        if not states:
            return "没有任务结果"

        lines = []
        for state in states:
            lines.append(f"## Task: {state.spec.task_id}")
            label = state.spec.agent_name or state.spec.model or "?"
            lines.append(f"- 目标: {label}")
            lines.append(f"- 状态: {state.status.value}")
            lines.append(f"- 耗时: {state.elapsed_seconds():.1f}s")

            if state.result_text():
                lines.append(f"- 结果:\n{state.result_text()}")
            if state.error:
                lines.append(f"- 错误: {state.error}")
            if state.artifacts:
                lines.append(f"- 产出物: {list(state.artifacts.keys())}")
            lines.append("")

        return "\n".join(lines)

    def format_notifications(self, states: List["AsyncTaskState"]) -> str:
        """
        格式化完成通知，用于注入到 LLM 上下文。

        Args:
            states: 已完成的任务状态列表

        Returns:
            格式化的通知文本
        """
        if not states:
            return ""

        lines = ["[异步任务完成通知]\n以下后台任务已完成，请根据结果继续工作：\n"]
        for state in states:
            label = state.spec.agent_name or state.spec.model or "?"
            lines.append(f"### Task {state.spec.task_id} ({label})")
            lines.append(f"状态: {state.status.value}")
            text = state.result_text()
            if text:
                lines.append(f"结果:\n{text}")
            if state.error:
                lines.append(f"错误: {state.error}")
            lines.append("")

        return "\n".join(lines)

    # ==================== 统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_spawned": self._total_spawned,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "currently_running": sum(
                1 for s in self._tasks.values()
                if s.status == AsyncTaskStatus.RUNNING
            ),
            "currently_pending": sum(
                1 for s in self._tasks.values()
                if s.status == AsyncTaskStatus.PENDING
            ),
            "max_concurrent": self._max_concurrent,
            "media_singleton": self is AsyncTaskManager._media_instance,
        }


__all__ = [
    "AsyncTaskStatus",
    "AsyncTaskSpec",
    "AsyncTaskState",
    "AsyncTaskManager",
    "TaskLedger",
    "normalize_task_text",
]