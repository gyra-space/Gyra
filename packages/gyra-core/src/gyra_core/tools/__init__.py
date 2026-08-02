"""
Gyra Core Tools - 兼容层重定向

此模块已迁移到统一工具框架 `gyra.agent.tools`。

旧的导入路径:
    from gyra_core.tools import ToolBase, ReadTool, ...

新的导入路径 (推荐):
    from gyra.agent.tools import ToolBase, tool_registry, ...
    from gyra.agent.tools.builtin import ReadTool, WriteTool, ...

此文件仅作为向后兼容层存在，新代码请使用统一框架。
"""

import warnings

warnings.warn(
    "gyra_core.tools 已迁移到 gyra.agent.tools，此兼容层将在未来版本移除",
    DeprecationWarning,
    stacklevel=2,
)

# 从统一框架重新导出核心类
from gyra.agent.tools.base import (
    ToolBase,
    ToolCategory,
    ToolRiskLevel as ToolRisk,
    ToolSource,
)

from gyra.agent.tools.metadata import ToolMetadata
from gyra.agent.tools.result import ToolResult
from gyra.agent.tools.registry import (
    ToolRegistry,
    tool_registry,
    register_builtin_tools,
)

# 从内置工具模块导入具体工具
from gyra.agent.tools.builtin.file_system.read import ReadTool
from gyra.agent.tools.builtin.file_system.write import WriteTool
from gyra.agent.tools.builtin.file_system.edit import EditTool
from gyra.agent.tools.builtin.file_system.glob import GlobTool
from gyra.agent.tools.builtin.file_system.grep import GrepTool
from gyra.agent.tools.builtin.shell.bash import BashTool
from gyra.agent.tools.builtin.network import WebFetchTool, WebSearchTool

# 保留 composition 功能（特有的高级功能）
from .composition import (
    BatchExecutor,
    BatchResult,
    TaskExecutor,
    TaskResult,
    WorkflowBuilder,
    batch,
    spawn,
    workflow,
)

__all__ = [
    "ToolBase",
    "ToolMetadata",
    "ToolResult",
    "ToolCategory",
    "ToolRisk",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "GlobTool",
    "GrepTool",
    "BashTool",
    "WebFetchTool",
    "WebSearchTool",
    "BatchExecutor",
    "BatchResult",
    "TaskExecutor",
    "TaskResult",
    "WorkflowBuilder",
    "batch",
    "spawn",
    "workflow",
    "ToolRegistry",
    "tool_registry",
    "register_builtin_tools",
]
