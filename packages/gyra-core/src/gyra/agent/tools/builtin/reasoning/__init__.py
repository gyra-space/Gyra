"""
推理工具模块 - SleepTool

SleepTool 是 Agent Loop 的休眠工具，允许 LLM 在需要等待的场景下
让当前 Agent Loop 暂停指定时间。核心实现为 `await asyncio.sleep(duration)`，
因此是真正的异步等待，不会阻塞进程的事件循环。

时长限制：1 秒到 10 分钟 (600 秒)。
"""

from typing import Any, Dict, Optional

import asyncio
import logging

from ...base import ToolBase, ToolCategory, ToolRiskLevel, ToolSource, ToolEnvironment
from ...metadata import ToolMetadata
from ...result import ToolResult
from ...context import ToolContext

logger = logging.getLogger(__name__)

# 时长上下限（秒）
SLEEP_MIN_SECONDS = 1
SLEEP_MAX_SECONDS = 600  # 10 分钟


class SleepTool(ToolBase):
    """
    Agent Loop 休眠工具 - 让当前 Agent Loop 等待一段时间

    使用场景：
    - 等待异步任务完成后继续
    - 等待外部服务就绪
    - 避免高频轮询/限流自控
    - 在需要时间间隔的流程中插入等待

    该工具通过 `await asyncio.sleep()` 实现，休眠期间不阻塞进程事件循环，
    其它协程仍可正常调度。
    """

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sleep",
            display_name="Sleep",
            description=(
                "Pause the current agent loop and wait for a specified duration, "
                "then resume execution. The wait is non-blocking (async) so the "
                "process event loop keeps running.\n\n"
                "Use this tool when you need to:\n"
                "- Wait for an async task / external service to finish before continuing\n"
                "- Insert a delay between steps (e.g. rate-limit self-control)\n"
                "- Wait for a resource or service to become ready\n\n"
                "Duration must be between 1 and 600 seconds (1 second to 10 minutes).\n"
                "Note: while sleeping, the agent performs no other action."
            ),
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.SAFE,
            source=ToolSource.SYSTEM,
            requires_permission=False,
            tags=["sleep", "wait", "delay", "loop-control", "async"],
            timeout=660,
            environment=ToolEnvironment.LOCAL,
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "duration": {
                    "type": "integer",
                    "description": (
                        "Sleep duration in seconds. Range: 1 to 600 "
                        "(1 second to 10 minutes)."
                    ),
                    "minimum": SLEEP_MIN_SECONDS,
                    "maximum": SLEEP_MAX_SECONDS,
                },
                "reason": {
                    "type": "string",
                    "description": "Optional reason for the sleep, for traceability.",
                },
            },
            "required": ["duration"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        duration = args.get("duration")
        reason = args.get("reason", "")

        # 参数校验
        if not isinstance(duration, int):
            try:
                duration = int(duration)
            except (TypeError, ValueError):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"duration 必须是整数秒，实际为: {duration!r}",
                    tool_name=self.name,
                )

        if duration < SLEEP_MIN_SECONDS:
            return ToolResult(
                success=False,
                output="",
                error=f"休眠时长不能小于 {SLEEP_MIN_SECONDS} 秒，实际为: {duration}",
                tool_name=self.name,
            )

        if duration > SLEEP_MAX_SECONDS:
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"休眠时长不能超过 {SLEEP_MAX_SECONDS} 秒 "
                    f"({SLEEP_MAX_SECONDS // 60} 分钟)，实际为: {duration}"
                ),
                tool_name=self.name,
            )

        reason_text = f"，原因：{reason}" if reason else ""
        logger.info(f"[SleepTool] 开始休眠 {duration} 秒{reason_text}")

        try:
            # 非阻塞异步等待：不阻塞进程事件循环
            await asyncio.sleep(duration)
            logger.info(f"[SleepTool] 休眠完成，已休眠 {duration} 秒")
            return ToolResult(
                success=True,
                output=f"已完成休眠 {duration} 秒{reason_text}",
                tool_name=self.name,
                metadata={"duration": duration, "reason": reason},
            )
        except asyncio.CancelledError:
            logger.warning(f"[SleepTool] 休眠被中断（已休眠部分时间）")
            return ToolResult(
                success=False,
                output="",
                error="休眠被中断（已休眠部分时间）",
                tool_name=self.name,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"[SleepTool] 休眠失败: {e}")
            return ToolResult(
                success=False, output="", error=f"休眠失败: {str(e)}", tool_name=self.name
            )


def register_reasoning_tools(registry) -> None:
    """注册推理/循环控制工具"""
    registry.register(SleepTool())
    logger.info("[ReasoningTools] 已注册 1 个工具: sleep")