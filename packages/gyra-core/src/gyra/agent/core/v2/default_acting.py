"""default_acting_fn 工厂。

流程：resolve → doom → failure_tracker → pre_tool_use hook → execute → post_tool_use hook → truncate

等价 BAIZE tool_action.py:278-680 的 ToolAction.run，但用原生 V2ToolCall/V2ToolResult/ToolContext。
"""
from typing import Any, Optional

from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.core.v2.tool_failure_tracker import ToolFailureTracker
from gyra.agent.core.v2.tool_resolver import ToolResolver
from gyra.agent.core.v2.tool_context_factory import ToolContextFactory
from gyra.agent.core.v2.hook_integration import (
    build_pre_tool_use_context,
    build_post_tool_use_context,
)
from gyra.agent.core.hook.schema import BlockingPolicy
from gyra.agent.tools.context import ToolContext


def make_default_acting_fn(
    *,
    tool_resolver: ToolResolver,
    doom_loop_detector: Any,
    failure_tracker: ToolFailureTracker,
    truncator: Any,
    tool_context_factory: ToolContextFactory,
    hook_manager: Optional[Any] = None,
):
    async def acting_fn(tool_call: V2ToolCall, ctx: ToolContext) -> V2ToolResult:
        tool_name = tool_call.name
        tool_input = tool_call.args

        # 1. DoomLoop 检测
        allowed = await doom_loop_detector.check(tool_name, tool_input)
        if not allowed:
            return V2ToolResult.fail(error="doom loop detected, blocked", tool_name=tool_name)

        # 2. 失败跟踪
        if failure_tracker.is_blocked(tool_name):
            return V2ToolResult.fail(
                error=failure_tracker.format_failure_message(tool_name, include_count=True),
                tool_name=tool_name
            )

        # 3. 解析工具
        tool = tool_resolver.resolve(tool_name)
        if tool is None:
            return V2ToolResult.fail(error=f"工具 {tool_name} 未注册", tool_name=tool_name)

        # 4. 适配 BAIZE 工具（C4 fix: BAIZE tools return str, V2 expects V2ToolResult）
        from gyra.agent.core.v2.unified_tool_adapter import UnifiedToolAdapter
        tool = UnifiedToolAdapter(tool)

        # 5. pre_tool_use hook（blocking）
        if hook_manager is not None:
            decision = await hook_manager.trigger_blocking(
                "pre_tool_use",
                build_pre_tool_use_context(tool_call, ctx),
            )
            action = getattr(decision, "action", BlockingPolicy.CONTINUE)
            if action == BlockingPolicy.DENY:
                reason = getattr(decision, "reason", "no reason")
                return V2ToolResult.fail(error=f"hook denied: {reason}", tool_name=tool_name)
            if action == BlockingPolicy.ABORT:
                return V2ToolResult.fail(error="hook aborted", tool_name=tool_name)
            if action == BlockingPolicy.MODIFY:
                modified = getattr(decision, "modified_input", None)
                if modified is not None:
                    tool_input = modified

        # 6. 执行
        try:
            result: V2ToolResult = await tool.execute(tool_input, context=ctx)
        except Exception as e:
            failure_tracker.record_failure(
                tool_name, error=str(e), params=tool_input
            )
            if hook_manager is not None:
                await hook_manager.trigger(
                    "post_tool_use",
                    build_post_tool_use_context(tool_call, ctx, None, error=str(e)),
                )
            return V2ToolResult.fail(error=f"执行异常: {e}", tool_name=tool_name)

        if not result.success:
            failure_tracker.record_failure(
                tool_name, error=str(result.error) if result.error else "execution failed", params=tool_input
            )
        else:
            failure_tracker.reset(tool_name)

        # 7. post_tool_use hook（fire-and-forget）
        if hook_manager is not None:
            await hook_manager.trigger(
                "post_tool_use",
                build_post_tool_use_context(tool_call, ctx, result),
            )

        # 8. 截断（L1）
        # 排除已自行管理输出大小的工具（与 V1 tool_action.py 对齐）：
        # skill/Skill 工具输出可能很大但需完整保留；read/read_file/view 等
        # 已自行分页管理，避免循环截断。
        output_content = str(result.output) if result.output is not None else ""
        if tool_name not in ("read", "read_file", "view", "Skill", "skill", "execute_sql", "get_table_spec"):
            trunc_result = await truncator.truncate(output_content, tool_name, tool_input)
            if getattr(trunc_result, "truncated", False):
                # 覆写 output 为截断后内容（含 dattach tag）
                result.output = trunc_result.truncated_content

        return result

    return acting_fn
