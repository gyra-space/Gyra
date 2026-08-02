"""V2 acting_fn 用的 ToolCall/ToolResult 类型别名。

复用 gyra.agent 的统一类型，不重新设计。
"""
from gyra.agent.core.action.base import ToolCall as V2ToolCall
from gyra.agent.tools.result import ToolResult as V2ToolResult

__all__ = ["V2ToolCall", "V2ToolResult"]
