"""SubAgentRuntime — spec §8 SubAgent Runtime entry point.

Single entry: spawn(spec) -> SubAgentHandle.
- SYNC mode: await sub-agent's run_step, return handle with result
- ASYNC mode: schedule run_step in background, persist transcript, return immediately
- Depth limiting: reject spawn if depth+1 > max_depth
- Independent context: each spawn creates a new sub_conv_id

P2 wraps the existing AsyncTaskManager for ASYNC mode (lifecycle, cancel,
wait). SYNC mode just awaits run_step directly.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from gyra._private.pydantic import BaseModel, ConfigDict
from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.harness.seams import SubagentSeam
from gyra.agent.core.v2.permission_gate import PermissionGate
from gyra.agent.core.v2.permission_mode import PermissionMode
from gyra.agent.core.v2.run_loop import run_loop
from gyra.agent.core.v2.subagent_handle import (
    SubAgentHandle,
    SubAgentMode,
    SubAgentStatus,
)
from gyra.agent.core.v2.subagent_interaction_gateway import SubAgentInteractionGateway

if TYPE_CHECKING:
    from gyra.agent.core.v2.state_store import StateStore
    from gyra.agent.core.v2.subagent_ops_delegate import SubAgentOpsDelegate
    from gyra.agent.util.async_task_manager import AsyncTaskManager

logger = logging.getLogger(__name__)


class SubAgentSpawnSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    agent_name: str
    task: str
    run_in_background: bool = False
    context: Dict[str, Any] = {}
    parent_step_id: str
    parent_conv_id: str
    parent_agent_id: str
    depth: int = 0
    thinking_fn: Optional[Any] = None
    acting_fn: Optional[Any] = None
    interaction_gateway: Optional[Any] = None
    ruleset: Optional[Any] = None
    shared_conv: bool = False  # v2 新增：True=共享父 conv_id（AgentStart 语义）
    # 生产接线（V2Agent → SubAgentRuntime）：子 agent 独立上下文
    session_id: Optional[str] = None  # 子会话 ID（缺省 = sub_conv_id）
    system_prompt: Optional[str] = None  # 子 agent 系统指令（透传进 run_step input_）
    user_id: Optional[str] = None  # 触发用户标识


class SubAgentRuntime(SubagentSeam):
    """V2 引擎内子 Agent 运行时（实现 :class:`SubagentSeam`）。

    Single entry: spawn(spec) -> SubAgentHandle.
    - SYNC mode: await sub-agent's run_step, return handle with result
    - ASYNC mode: schedule run_step in background, persist transcript,
      return immediately
    - Depth limiting: reject spawn if depth+1 > max_depth
    - Independent context: each spawn creates a new sub_conv_id

    P2 wraps the existing AsyncTaskManager for ASYNC mode (lifecycle, cancel,
    wait). SYNC mode just awaits run_step directly.

    生产接线：``default_thinking_fn`` / ``default_acting_fn`` 由装配层（V2Agent）
    传入，spawn spec 未显式携带 fn 时使用默认实现——子 agent 因此可复用主引擎
    的 ContextEngine / 工具解析，而无需工具参数透传 callable。
    """

    def __init__(
        self,
        state_store: "StateStore",
        max_depth: int = 5,
        async_task_manager: Optional["AsyncTaskManager"] = None,
        default_thinking_fn: Optional[Any] = None,
        default_acting_fn: Optional[Any] = None,
        default_user_id: Optional[str] = None,
        job_registry: Optional[Any] = None,
        ops_delegate: Optional["SubAgentOpsDelegate"] = None,
    ):
        self._store = state_store
        self._max_depth = max_depth
        self._async_mgr = async_task_manager
        self._default_thinking_fn = default_thinking_fn
        self._default_acting_fn = default_acting_fn
        self._default_user_id = default_user_id
        # harness.jobs 本地视图：spawn/终态同步（引擎与产品层统一查询）
        self._job_registry = job_registry
        # 运维委托（gyra-serve CoordinatorOpsDelegate）：看板上板/台账镜像/
        # 终态回写。None 时引擎行为与未桥接前一致（纯增量，零回归）。
        self.ops_delegate = ops_delegate
        self._handles: Dict[str, SubAgentHandle] = {}
        self._async_tasks: Dict[str, asyncio.Task] = {}
        # 已回调 on_terminal 的 task_id（防 finally 与 cancel 兜底重复上报）
        self._terminal_notified: Set[str] = set()

    def _sync_job(self, task_id: str, status: str, **meta: Any) -> None:
        """把子任务状态同步到 harness.jobs（注册或更新）。"""
        if self._job_registry is None:
            return
        try:
            if self._job_registry.get_status(task_id) is None:
                handle = self._handles.get(task_id)
                self._job_registry.register(
                    task_id,
                    conv_id=(
                        handle.parent_conv_id
                        if handle is not None
                        else None
                    ),
                    kind="subagent",
                    status=status,
                    **meta,
                )
            else:
                self._job_registry.update_status(task_id, status, **meta)
        except Exception:  # noqa: BLE001
            pass  # job 同步失败不影响子 agent 主流程

    async def spawn(self, spec: SubAgentSpawnSpec) -> SubAgentHandle:
        if spec.depth + 1 > self._max_depth:
            raise ValueError(
                f"spawn depth limit exceeded: depth={spec.depth}, "
                f"max_depth={self._max_depth}"
            )

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        if spec.shared_conv:
            sub_conv_id = spec.parent_conv_id  # 共享父 conv
        else:
            sub_conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        now = time.time()
        mode = SubAgentMode.ASYNC if spec.run_in_background else SubAgentMode.SYNC
        handle = SubAgentHandle(
            task_id=task_id,
            parent_step_id=spec.parent_step_id,
            parent_conv_id=spec.parent_conv_id,
            sub_conv_id=sub_conv_id,
            agent_name=spec.agent_name,
            mode=mode,
            status=SubAgentStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        if mode is SubAgentMode.SYNC:
            await self._run_subagent(handle, spec)
        else:
            # ASYNC: 先经运维委托登记（上板 + 台账镜像 + 去重），再调度执行体
            reg = await self._try_register(handle, spec)
            if reg is not None and not reg.created:
                # 去重命中：复用在途任务，短路本次 spawn（不建执行体、不镜像
                # job——V1 台账已有镜像）。改写 sub_conv_id 为已有任务 ID，
                # LLM 经 check_tasks/wait_tasks 用该 ID 查询/等待。
                logger.info(
                    f"[SubAgentRuntime] dedup: reuse in-flight subagent "
                    f"{reg.sub_conv_id} for spawn {task_id} "
                    f"(agent={spec.agent_name})"
                )
                handle.sub_conv_id = reg.sub_conv_id
                handle.transcript_id = None
                handle.status = SubAgentStatus.RUNNING
                handle.updated_at = time.time()
                return handle
            # ASYNC: schedule in background, persist transcript
            transcript_id = f"t-{uuid.uuid4().hex[:8]}"
            handle.transcript_id = transcript_id
            handle.status = SubAgentStatus.RUNNING
            self._handles[task_id] = handle
            # 异步任务注册到 harness.jobs（终态由 _run_subagent_async 更新）
            self._sync_job(
                task_id, "running",
                agent_name=spec.agent_name, sub_conv_id=sub_conv_id,
            )
            self._async_tasks[task_id] = asyncio.create_task(
                self._run_subagent_async(handle, spec, transcript_id)
            )

        return handle

    async def _try_register(
        self, handle: SubAgentHandle, spec: SubAgentSpawnSpec
    ):
        """经运维委托登记 ASYNC 子任务；委托缺失/异常时返回 None 不阻断。"""
        if self.ops_delegate is None:
            return None
        try:
            return await self.ops_delegate.try_register(handle, spec)
        except Exception as e:  # noqa: BLE001 - 委托故障不阻断引擎主流程
            logger.warning(
                f"[SubAgentRuntime] ops try_register failed for "
                f"{handle.task_id}: {e}"
            )
            return None

    async def _make_permission_gate(
        self, handle: SubAgentHandle, spec: SubAgentSpawnSpec
    ):
        """Build a PermissionGate wired to the parent's gateway (if any)."""
        if spec.interaction_gateway is None:
            return None
        sub_gateway = SubAgentInteractionGateway(
            parent_gateway=spec.interaction_gateway,
            sync=not spec.run_in_background,
        )
        return PermissionGate(
            state_store=self._store,
            event_stream=EventStream(self._store),
            interaction_adapter=sub_gateway,
            mode=PermissionMode.DEFAULT,
            ruleset=spec.ruleset,
            step_id=None,  # bound by run_step
            conv_id=handle.sub_conv_id,
            agent_id=f"subagent-{handle.task_id}",
        )

    def _resolve_sub_fns(self, spec: SubAgentSpawnSpec):
        """子 agent 的 thinking/acting fn：spec 显式优先，缺省回退装配层默认。"""
        thinking_fn = spec.thinking_fn or self._default_thinking_fn
        acting_fn = spec.acting_fn or self._default_acting_fn
        return thinking_fn, acting_fn

    def _build_sub_input(
        self, spec: SubAgentSpawnSpec, sub_conv_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """构造子 agent run_step 输入：独立 session_id / system_prompt / conv_id。

        thinking_fn 由 input_ 字段驱动（default_thinking 从 input_ 读
        conv_id/session_id/system_prompt/agent_id），因此子 agent 可复用主引擎
        同一闭包，并各自投影自己的事件日志（V2 单源）。
        """
        session_id = spec.session_id or sub_conv_id
        input_ = {
            "prompt": spec.task,
            "conv_id": sub_conv_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "user_id": spec.user_id or self._default_user_id,
            "system_prompt": spec.system_prompt,
            "is_subagent": True,
            "subagent_depth": spec.depth + 1,
        }
        input_.update(spec.context or {})
        return input_

    async def _emit_sub_dialog_message(
        self, handle: "SubAgentHandle", role: str, content: str
    ) -> None:
        """子 agent 的对话消息写入子 conv 事件日志（V2 单源事实）。"""
        if not content:
            return
        try:
            from gyra.agent.core.v2.event_stream import EventStream
            from gyra.agent.core.v2.step_event import StepEvent
            from gyra.agent.core.v2.step_state import StepState

            stream = EventStream(self._store)
            existing = await self._store.get_events(handle.sub_conv_id)
            seq = max((e.seq for e in existing), default=-1) + 1
            ev = StepEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                step_id=f"dialog-{uuid.uuid4().hex[:6]}",
                conv_id=handle.sub_conv_id,
                agent_id=f"subagent-{handle.task_id}",
                parent_step_id=None,
                state=StepState.DONE,
                event_type=f"{role}/message",
                input={},
                output={"text": content},
                seq=seq,
                timestamp=time.time(),
            )
            await stream.emit(ev)
        except Exception:  # noqa: BLE001
            pass

    async def _run_subagent(
        self, handle: SubAgentHandle, spec: SubAgentSpawnSpec
    ) -> None:
        """Sync mode: run sub-agent to completion before returning.

        子 agent 用 ``run_loop``（多轮循环，非单步 run_step）驱动，收集
        content 通道最终答案写入 handle.result——主 agent 才能拿到子结论。
        """
        handle.status = SubAgentStatus.RUNNING
        self._handles[handle.task_id] = handle
        thinking_fn, acting_fn = self._resolve_sub_fns(spec)
        if thinking_fn is None:
            handle.error = "sub-agent thinking_fn unavailable (not wired by assembler)"
            handle.status = SubAgentStatus.FAILED
            return
        input_ = self._build_sub_input(
            spec, handle.sub_conv_id, f"subagent-{handle.task_id}"
        )
        # V2 单源：子任务消息写入子 conv 事件日志
        await self._emit_sub_dialog_message(handle, "user", spec.task)
        permission_gate = await self._make_permission_gate(handle, spec)
        try:
            result = {"events": []}
            answer_parts: list = []
            async for event in run_loop(
                agent_id=f"subagent-{handle.task_id}",
                conv_id=handle.sub_conv_id,
                input_=input_,
                state_store=self._store,
                thinking_fn=thinking_fn,
                acting_fn=acting_fn,
                parent_step_id=handle.parent_step_id,
                permission_gate=permission_gate,
                max_steps=max(self._max_depth * 4, 10),
            ):
                event.metadata["is_subagent"] = True
                event.metadata["subagent_depth"] = spec.depth + 1
                await self._store.update_event_metadata(
                    event.event_id, event.metadata,
                )
                result["events"].append({
                    "seq": event.seq,
                    "state": event.state.value,
                    "event_type": event.event_type,
                })
                if event.event_type == "llm_token":
                    token = (event.output or {}).get("token", "")
                    channel = (event.output or {}).get("channel", "content")
                    if token and channel != "thinking":
                        answer_parts.append(token)
            handle.result = {
                "status": "done",
                "answer": "".join(answer_parts),
                "events_count": len(result["events"]),
            }
            handle.status = SubAgentStatus.DONE
            await self._emit_sub_dialog_message(
                handle, "assistant", "".join(answer_parts)
            )
        except Exception as e:
            handle.error = str(e)
            handle.status = SubAgentStatus.FAILED
        handle.updated_at = time.time()
        self._sync_job(
            handle.task_id,
            "completed" if handle.status is SubAgentStatus.DONE else "failed",
            agent_name=handle.agent_name,
        )

    async def _run_subagent_async(
        self, handle: SubAgentHandle, spec: SubAgentSpawnSpec, transcript_id: str,
    ) -> None:
        """Async mode: run in background, update transcript periodically."""
        thinking_fn, acting_fn = self._resolve_sub_fns(spec)
        if thinking_fn is None:
            handle.error = "sub-agent thinking_fn unavailable (not wired by assembler)"
            handle.status = SubAgentStatus.FAILED
            await self._store.save_transcript(
                transcript_id=transcript_id,
                task_id=handle.task_id,
                sub_conv_id=handle.sub_conv_id,
                parent_step_id=handle.parent_step_id,
                parent_conv_id=handle.parent_conv_id,
                agent_name=handle.agent_name,
                status="failed",
                latest_event_seq=0,
                payload={"error": handle.error},
            )
            await self._notify_terminal(handle)
            return
        input_ = self._build_sub_input(
            spec, handle.sub_conv_id, f"subagent-{handle.task_id}"
        )
        # V2 单源：子任务消息写入子 conv 事件日志
        await self._emit_sub_dialog_message(handle, "user", spec.task)
        permission_gate = await self._make_permission_gate(handle, spec)
        try:
            latest_seq = 0
            answer_parts: list = []
            max_steps = max(self._max_depth * 4, 10)
            seen_steps: Set[str] = set()
            async for event in run_loop(
                agent_id=f"subagent-{handle.task_id}",
                conv_id=handle.sub_conv_id,
                input_=input_,
                state_store=self._store,
                thinking_fn=thinking_fn,
                acting_fn=acting_fn,
                parent_step_id=handle.parent_step_id,
                permission_gate=permission_gate,
                max_steps=max_steps,
            ):
                event.metadata["is_subagent"] = True
                event.metadata["subagent_depth"] = spec.depth + 1
                await self._store.update_event_metadata(
                    event.event_id, event.metadata,
                )
                latest_seq = max(latest_seq, event.seq)
                if event.event_type == "llm_token":
                    token = (event.output or {}).get("token", "")
                    channel = (event.output or {}).get("channel", "content")
                    if token and channel != "thinking":
                        answer_parts.append(token)
                elif event.step_id and event.step_id not in seen_steps:
                    # 步级进度上报（step 粒度天然节流，避免 token 流打爆看板）
                    seen_steps.add(event.step_id)
                    await self._report_progress(
                        handle, len(seen_steps), max_steps, event.event_type
                    )
                # Persist transcript snapshot every few events
                await self._store.save_transcript(
                    transcript_id=transcript_id,
                    task_id=handle.task_id,
                    sub_conv_id=handle.sub_conv_id,
                    parent_step_id=handle.parent_step_id,
                    parent_conv_id=handle.parent_conv_id,
                    agent_name=handle.agent_name,
                    status="running",
                    latest_event_seq=latest_seq,
                    payload={"last_event_state": event.state.value},
                )
            handle.result = {
                "status": "done",
                "answer": "".join(answer_parts),
                "latest_seq": latest_seq,
            }
            handle.status = SubAgentStatus.DONE
            await self._emit_sub_dialog_message(
                handle, "assistant", "".join(answer_parts)
            )
            await self._store.save_transcript(
                transcript_id=transcript_id,
                task_id=handle.task_id,
                sub_conv_id=handle.sub_conv_id,
                parent_step_id=handle.parent_step_id,
                parent_conv_id=handle.parent_conv_id,
                agent_name=handle.agent_name,
                status="done",
                latest_event_seq=latest_seq,
                payload={"result": handle.result},
            )
        except asyncio.CancelledError:
            handle.status = SubAgentStatus.CANCELLED
            await self._store.save_transcript(
                transcript_id=transcript_id,
                task_id=handle.task_id,
                sub_conv_id=handle.sub_conv_id,
                parent_step_id=handle.parent_step_id,
                parent_conv_id=handle.parent_conv_id,
                agent_name=handle.agent_name,
                status="cancelled",
                latest_event_seq=0,
                payload={"error": "cancelled"},
            )
            raise
        except Exception as e:
            handle.error = str(e)
            handle.status = SubAgentStatus.FAILED
            await self._store.save_transcript(
                transcript_id=transcript_id,
                task_id=handle.task_id,
                sub_conv_id=handle.sub_conv_id,
                parent_step_id=handle.parent_step_id,
                parent_conv_id=handle.parent_conv_id,
                agent_name=handle.agent_name,
                status="failed",
                latest_event_seq=0,
                payload={"error": str(e)},
            )
        finally:
            handle.updated_at = time.time()
            # 终态同步到 harness.jobs（completed/failed/cancelled）
            self._sync_job(
                handle.task_id,
                (
                    "completed"
                    if handle.status is SubAgentStatus.DONE
                    else (
                        "cancelled"
                        if handle.status is SubAgentStatus.CANCELLED
                        else "failed"
                    )
                ),
                agent_name=handle.agent_name,
            )
            # 终态回写运维委托（看板终态 + 台账 complete + 全完成触发主 resume）
            await self._notify_terminal(handle)

    async def _notify_terminal(self, handle: SubAgentHandle) -> None:
        """终态回写运维委托（幂等）：委托按 handle.status 分派产品语义。

        先记账后回调去重（finally 与未来 cancel 兜底不重复上报）；
        ``except Exception`` 不吞 CancelledError（BaseException）。
        """
        if self.ops_delegate is None or handle.task_id in self._terminal_notified:
            return
        self._terminal_notified.add(handle.task_id)
        result_text = ""
        if isinstance(handle.result, dict):
            result_text = str(handle.result.get("answer") or "")
        elif isinstance(handle.result, str):
            result_text = handle.result
        try:
            await self.ops_delegate.on_terminal(
                handle,
                result_text=result_text,
                error=handle.error or "",
            )
        except Exception as e:  # noqa: BLE001 - 委托故障不影响子任务终态
            logger.warning(
                f"[SubAgentRuntime] ops on_terminal failed for "
                f"{handle.task_id}: {e}"
            )

    async def _report_progress(
        self, handle: SubAgentHandle, steps_done: int, max_steps: int,
        note: str,
    ) -> None:
        """按步数折算进度上报运维委托（0-100，封顶 95 留终态给 DONE）。"""
        if self.ops_delegate is None:
            return
        progress = min(95, max(1, steps_done * 100 // max(max_steps, 1)))
        try:
            await self.ops_delegate.update_progress(handle, progress, note)
        except Exception as e:  # noqa: BLE001 - 委托故障不影响执行主流程
            logger.debug(
                f"[SubAgentRuntime] ops update_progress failed for "
                f"{handle.task_id}: {e}"
            )

    async def wait(
        self, handle: SubAgentHandle, timeout: Optional[float] = None
    ) -> SubAgentHandle:
        if handle.mode is SubAgentMode.SYNC:
            return handle  # sync already done
        task = self._async_tasks.get(handle.task_id)
        if task is None:
            return handle
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self._handles.get(handle.task_id, handle)

    async def reconstruct_handle_from_transcript(
        self, task_id: str
    ) -> Optional[SubAgentHandle]:
        """Reconstruct a SubAgentHandle from the persisted async transcript."""
        transcript = await self._store.get_transcript_by_task_id(task_id)
        if transcript is None:
            return None
        return SubAgentHandle(
            task_id=transcript["task_id"],
            parent_step_id=transcript["parent_step_id"],
            parent_conv_id=transcript["parent_conv_id"],
            sub_conv_id=transcript["sub_conv_id"],
            agent_name=transcript["agent_name"],
            mode=SubAgentMode.ASYNC,
            status=SubAgentStatus(transcript["status"]),
            result=transcript["payload"].get("result"),
            error=transcript["payload"].get("error"),
            created_at=transcript["updated_at"],
            updated_at=transcript["updated_at"],
            transcript_id=transcript["transcript_id"],
        )

    async def get_status(self, task_id: str) -> Optional[SubAgentHandle]:
        if task_id in self._handles:
            return self._handles[task_id]
        return await self.reconstruct_handle_from_transcript(task_id)

    async def cancel(self, task_id: str) -> bool:
        task = self._async_tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        # If the task was cancelled before it started, the coroutine body never
        # ran and didn't get a chance to update the handle status.
        handle = self._handles.get(task_id)
        if handle is not None and not handle.is_done():
            handle.status = SubAgentStatus.CANCELLED
            handle.updated_at = time.time()
        return True

    async def resume(self, task_id: str) -> Optional[SubAgentHandle]:
        """Re-attach to an async sub-agent. Returns current handle."""
        return await self.get_status(task_id)
