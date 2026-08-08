"""
异步任务 Tools - LLM 可调用的异步任务管理工具

提供 4 个 Tool 让主 Agent 在 ReAct 循环中管理后台子 Agent 任务：
1. spawn_agent_task - 启动后台 Agent 任务
2. check_tasks - 查看任务状态
3. wait_tasks - 等待任务完成
4. cancel_task - 取消任务

@see docs/ASYNC_TASK_SYSTEM.md
"""

from typing import Any, Dict, Optional
import logging

from ...base import ToolBase, ToolCategory, ToolRiskLevel, ToolSource
from ...metadata import ToolMetadata
from ...result import ToolResult
from ...context import ToolContext

logger = logging.getLogger(__name__)


# ==================== Tool Prompts ====================


_SPAWN_PROMPT = """启动一个后台 Agent 任务。任务会在后台异步执行，你可以继续处理其他工作，稍后用 check_tasks 或 wait_tasks 获取结果。

使用场景：
- 需要多个独立子任务并行执行时
- 某个任务耗时较长，不想阻塞当前工作时
- 需要不同专业 Agent 分别处理不同子目标时

注意：
- 提交后立即返回 task_id，不会等待任务完成
- 默认 wait_for_result=true（阻塞等待）：提交后本轮立即结束，任务完成后自动恢复继续，无需轮询
- 仅当结果与后续工作完全无关时传 wait_for_result=false（后台执行，结果经异步通知注入）
- 可以一次提交多个任务实现并行执行
- 通过 depend_on 参数可以设置任务依赖关系
- 相同内容的任务会被去重：若已有相同任务在途，会直接返回在途 task_id，不会重复执行（图片/视频生成按次计费，切勿换个说法重复提交）"""

_CHECK_PROMPT = """查看后台任务的当前状态，不阻塞。

可以查看所有任务或指定任务的状态、进度、结果预览等信息。"""

_WAIT_PROMPT = """等待后台任务完成并获取完整结果。

两种模式：
- 指定 task_ids: 等待这些任务全部完成后返回结果
- 不指定 task_ids: 等待任意一个任务完成后返回结果

适用于需要子任务结果才能继续的场景。"""

_CANCEL_PROMPT = """取消一个正在执行或等待中的后台任务。"""


# ==================== Tool 1: spawn_agent_task ====================


class SpawnAgentTaskTool(ToolBase):
    """启动后台 Agent 异步任务"""

    def __init__(self, async_task_manager: Optional[Any] = None):
        self._manager = async_task_manager
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="spawn_agent_task",
            display_name="Spawn Agent Task",
            description=_SPAWN_PROMPT,
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.MEDIUM,
            source=ToolSource.SYSTEM,
            requires_permission=False,
            timeout=30,
            tags=["agent", "async", "task", "parallel", "background"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "目标子 Agent 的名称，必须为系统中已注册的 Agent。",
                },
                "task": {
                    "type": "string",
                    "description": "需要完成的任务描述。请提供清晰、具体的任务说明。",
                },
                "context": {
                    "type": "object",
                    "description": "传递给子 Agent 的额外上下文信息（可选）。",
                    "default": {},
                },
                "timeout": {
                    "type": "integer",
                    "description": "任务超时秒数（可选，默认 300 秒）。",
                    "default": 300,
                    "minimum": 10,
                    "maximum": 3600,
                },
                "depend_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "依赖的 task_id 列表。这些任务完成后才会开始执行当前任务（可选）。",
                    "default": [],
                },
                "wait_for_result": {
                    "type": "boolean",
                    "description": (
                        "是否需要等待该任务的结果才能继续（默认 true）。"
                        "true=阻塞等待：提交后本轮立即结束，任务完成后自动恢复继续；"
                        "false=后台执行：你继续处理其他工作，结果经异步通知注入上下文。"
                        "仅当任务结果与后续工作完全无关时才用 false。"
                    ),
                    "default": True,
                },
            },
            "required": ["agent_name", "task"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        agent_name = args.get("agent_name", "")
        task = args.get("task", "")

        if not agent_name:
            return ToolResult.fail(
                error="agent_name 不能为空",
                tool_name=self.name,
            )
        if not task:
            return ToolResult.fail(
                error="task 描述不能为空",
                tool_name=self.name,
            )

        # 获取 AsyncTaskManager（统一单例优先；无注入时回退 context 资源）
        manager = self._manager
        if not manager and context:
            manager = (
                context.get_resource("async_task_manager")
                if hasattr(context, "get_resource")
                else None
            )
        if not manager:
            from ....util.async_task_manager import AsyncTaskManager

            manager = AsyncTaskManager.media_instance()

        if not manager:
            return ToolResult.fail(
                error="异步任务管理器不可用。当前环境未启用异步任务功能。",
                tool_name=self.name,
            )

        try:
            from ....util.async_task_manager import AsyncTaskSpec

            # 阻塞等待（默认）：提交后本轮 loop 立即结束、会话 WAITING，任务完成
            # 后由 coordinator resume 恢复；False = fire-and-forget 后台执行
            wait_for_result = bool(args.get("wait_for_result", True))

            conv_id = ""
            if context is not None:
                conv_id = getattr(context, "conversation_id", "") or ""
                if not conv_id:
                    # v1 框架下 tool_action 约定 context 即 agent 本身，
                    # 从 agent.agent_context 取 conv_id；缺失会导致
                    # AsyncTaskCoordinator 无法按会话跟踪该任务（台账卡 running）
                    agent_ctx = getattr(context, "agent_context", None)
                    conv_id = getattr(agent_ctx, "conv_id", "") or ""

            # 统一单例下 subagent 任务需经 delegate 委派；若 context 提供
            # subagent_delegate_factory，则用其构造委派协程（否则回退 manager 内置
            # subagent_manager，兼容非统一实例）。
            delegate = None
            if context is not None:
                factory = None
                try:
                    factory = (
                        context.get_resource("subagent_delegate_factory")
                        if hasattr(context, "get_resource")
                        else None
                    )
                except Exception:  # noqa: BLE001
                    factory = None
                if callable(factory):
                    delegate = lambda: factory(  # noqa: E731
                        subagent_name=agent_name,
                        task=task,
                        conv_id=conv_id,
                        context=args.get("context", {}),
                    )

            spec = AsyncTaskSpec(
                agent_name=agent_name,
                task_description=task,
                context=args.get("context", {}),
                timeout=args.get("timeout", 300),
                depend_on=args.get("depend_on", []),
                conv_id=conv_id,
                delegate=delegate,
            )

            # 防重复提交：同会话已有同 agent 同内容的在途任务时直接复用，
            # 不新建（图片/视频生成按次计费，重复提交 = 重复扣费）
            in_flight = manager.find_in_flight(
                conv_id=conv_id,
                agent_name=agent_name,
                task_description=task,
            )
            if in_flight is not None:
                existing_id = in_flight.spec.task_id
                return ToolResult.ok(
                    output=(
                        f"相同任务已在后台执行中，已复用、未重复提交。\n"
                        f"- Task ID: {existing_id}\n"
                        f"- Agent: {agent_name}\n"
                        f"- 状态: {in_flight.status.value}\n\n"
                        f"请勿再次提交相同任务。"
                        + (
                            "本轮将结束等待，任务完成后会自动恢复继续。"
                            if wait_for_result
                            else "结果完成后会经异步通知注入上下文。"
                        )
                    ),
                    tool_name=self.name,
                    metadata={
                        "task_id": existing_id,
                        "agent_name": agent_name,
                        "reused": True,
                        "wait_async": wait_for_result,
                        "async_task": {
                            "task_id": existing_id,
                            "kind": "subagent",
                            "model": agent_name,
                            "conv_id": conv_id,
                        },
                    },
                )

            task_id = await manager.spawn(spec)

            deps_info = ""
            if spec.depend_on:
                deps_info = f"\n依赖: {', '.join(spec.depend_on)}（等待依赖完成后自动开始）"

            wait_note = (
                "\n本轮将在此结束并等待任务完成，完成后会自动恢复继续（无需轮询）。"
                if wait_for_result
                else "\n你可以继续其他工作，结果完成后会经异步通知注入上下文。"
            )
            output = (
                f"任务已提交到后台执行。\n"
                f"- Task ID: {task_id}\n"
                f"- Agent: {agent_name}\n"
                f"- 描述: {task[:100]}\n"
                f"- 超时: {spec.timeout}s"
                f"{deps_info}\n\n"
                f"你可以继续其他工作，稍后用 check_tasks 查看状态或 wait_tasks 获取结果。"
                f"{wait_note}"
            )

            return ToolResult.ok(
                output=output,
                tool_name=self.name,
                metadata={
                    "task_id": task_id,
                    "agent_name": agent_name,
                    "wait_async": wait_for_result,
                    # 供 ToolAction 在工具执行处登记 pending 异步任务
                    "async_task": {
                        "task_id": task_id,
                        "kind": "subagent",
                        "model": agent_name,
                        "conv_id": conv_id,
                    },
                },
            )

        except Exception as e:
            logger.error(f"[SpawnAgentTaskTool] 提交任务失败: {e}")
            return ToolResult.fail(error=str(e), tool_name=self.name)


# ==================== Tool 2: check_tasks ====================


class CheckTasksTool(ToolBase):
    """查看后台任务状态"""

    def __init__(self, async_task_manager: Optional[Any] = None):
        self._manager = async_task_manager
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="check_tasks",
            display_name="Check Tasks",
            description=_CHECK_PROMPT,
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.SAFE,
            source=ToolSource.SYSTEM,
            requires_permission=False,
            timeout=10,
            tags=["agent", "async", "task", "status"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要查询的 task_id 列表。为空则查询所有任务。",
                    "default": [],
                },
            },
            "required": [],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        manager = self._manager
        if not manager and context:
            manager = (
                context.get_resource("async_task_manager")
                if hasattr(context, "get_resource")
                else None
            )
        if not manager:
            # 与 spawn_agent_task 一致回退进程级统一单例：
            # 任务提交到该单例，查询/等待/取消必须查同一实例
            from ....util.async_task_manager import AsyncTaskManager

            manager = AsyncTaskManager.media_instance()

        if not manager:
            return ToolResult.fail(
                error="异步任务管理器不可用",
                tool_name=self.name,
            )

        try:
            task_ids = args.get("task_ids", []) or None
            output = manager.format_status_table(task_ids)
            if "未找到" in output:
                output += (
                    "\n\n提示：标记「未找到」的 ID 请核对拼写；SubAgent 异步返回的 "
                    "sub_conv_id 与 spawn_agent_task 返回的 atask_* 均可直接查询。"
                    "任务查询不到不代表丢失，请勿因此重复提交生成任务。"
                )
            return ToolResult.ok(output=output, tool_name=self.name)

        except Exception as e:
            logger.error(f"[CheckTasksTool] 查询失败: {e}")
            return ToolResult.fail(error=str(e), tool_name=self.name)


# ==================== Tool 3: wait_tasks ====================


class WaitTasksTool(ToolBase):
    """等待后台任务完成"""

    def __init__(self, async_task_manager: Optional[Any] = None):
        self._manager = async_task_manager
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="wait_tasks",
            display_name="Wait Tasks",
            description=_WAIT_PROMPT,
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.LOW,
            source=ToolSource.SYSTEM,
            requires_permission=False,
            timeout=600,
            tags=["agent", "async", "task", "wait", "blocking"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "等待的 task_id 列表。为空则等待任意一个任务完成。",
                    "default": [],
                },
                "timeout": {
                    "type": "integer",
                    "description": "最大等待秒数（默认 60）。",
                    "default": 60,
                    "minimum": 5,
                    "maximum": 600,
                },
            },
            "required": [],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        manager = self._manager
        if not manager and context:
            manager = (
                context.get_resource("async_task_manager")
                if hasattr(context, "get_resource")
                else None
            )
        if not manager:
            # 与 spawn_agent_task 一致回退进程级统一单例：
            # 任务提交到该单例，查询/等待/取消必须查同一实例
            from ....util.async_task_manager import AsyncTaskManager

            manager = AsyncTaskManager.media_instance()

        if not manager:
            return ToolResult.fail(
                error="异步任务管理器不可用",
                tool_name=self.name,
            )

        try:
            task_ids = args.get("task_ids", [])
            timeout = args.get("timeout", 60)

            # 对未知 task_id 显式报错，避免误导性的"等待超时"让 LLM 误判任务
            # 丢失而重复提交。SubAgent 异步返回的 sub_conv_id 与 spawn_agent_task
            # 返回的 atask_* ID 均可直接用于本工具。
            if task_ids:
                known = set(manager.known_task_ids(task_ids))
                unknown = [tid for tid in task_ids if tid not in known]
                if unknown and not known:
                    return ToolResult.fail(
                        error=(
                            f"任务 ID 不存在: {unknown}。请核对 ID（SubAgent 异步返回的 "
                            f"sub_conv_id、spawn_agent_task 返回的 atask_* 均可直接查询）；"
                            f"不要因查询不到就重复提交生成任务。"
                        ),
                        tool_name=self.name,
                    )
                if unknown:
                    logger.warning(
                        f"[WaitTasksTool] unknown task_ids ignored: {unknown}"
                    )
                    task_ids = [tid for tid in task_ids if tid in known]

            if task_ids:
                results = await manager.wait_all(task_ids, timeout=timeout)
            else:
                results = await manager.wait_any(timeout=timeout)

            if not results:
                return ToolResult.ok(
                    output="等待超时，暂无任务完成。你可以继续其他工作后再检查。",
                    tool_name=self.name,
                )

            output = manager.format_results(results)
            return ToolResult.ok(
                output=output,
                tool_name=self.name,
                metadata={
                    "completed_task_ids": [s.spec.task_id for s in results],
                    "total_results": len(results),
                },
            )

        except Exception as e:
            logger.error(f"[WaitTasksTool] 等待失败: {e}")
            return ToolResult.fail(error=str(e), tool_name=self.name)


# ==================== Tool 4: cancel_task ====================


class CancelTaskTool(ToolBase):
    """取消后台任务"""

    def __init__(self, async_task_manager: Optional[Any] = None):
        self._manager = async_task_manager
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="cancel_task",
            display_name="Cancel Task",
            description=_CANCEL_PROMPT,
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.LOW,
            source=ToolSource.SYSTEM,
            requires_permission=False,
            timeout=10,
            tags=["agent", "async", "task", "cancel"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "要取消的任务 ID。",
                },
            },
            "required": ["task_id"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        task_id = args.get("task_id", "")
        if not task_id:
            return ToolResult.fail(
                error="task_id 不能为空",
                tool_name=self.name,
            )

        manager = self._manager
        if not manager and context:
            manager = (
                context.get_resource("async_task_manager")
                if hasattr(context, "get_resource")
                else None
            )
        if not manager:
            # 与 spawn_agent_task 一致回退进程级统一单例：
            # 任务提交到该单例，查询/等待/取消必须查同一实例
            from ....util.async_task_manager import AsyncTaskManager

            manager = AsyncTaskManager.media_instance()

        if not manager:
            return ToolResult.fail(
                error="异步任务管理器不可用",
                tool_name=self.name,
            )

        try:
            success = await manager.cancel(task_id)
            if success:
                return ToolResult.ok(
                    output=f"任务 {task_id} 已取消。",
                    tool_name=self.name,
                )
            else:
                return ToolResult.ok(
                    output=f"无法取消任务 {task_id}（任务可能已完成或不存在）。",
                    tool_name=self.name,
                )

        except Exception as e:
            logger.error(f"[CancelTaskTool] 取消失败: {e}")
            return ToolResult.fail(error=str(e), tool_name=self.name)


__all__ = [
    "SpawnAgentTaskTool",
    "CheckTasksTool",
    "WaitTasksTool",
    "CancelTaskTool",
]
