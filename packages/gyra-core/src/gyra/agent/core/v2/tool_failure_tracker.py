"""工具连续失败跟踪器。

从 BAIZE react_master_agent.py:2517-2575 的 _tool_failure_counts 抽出。
无 agent 反向依赖。
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FailureRecord:
    """单次失败记录。"""
    tool_name: str
    error: str
    params: Optional[Dict[str, Any]] = None


class ToolFailureTracker:
    def __init__(self, max_failures: int = 5):
        """初始化失败跟踪器。

        Args:
            max_failures: 最大失败次数，默认5次（前3次提醒，5次终止）
        """
        self._failures: Dict[str, List[FailureRecord]] = {}
        self._max_failures = max_failures

    def record_failure(
        self, tool_name: str, error: str = "tool execution failed", params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """记录一次失败。返回是否达到阈值。

        Args:
            tool_name: 工具名称
            error: 错误信息
            params: 失败时的参数（可选）
        """
        if tool_name not in self._failures:
            self._failures[tool_name] = []

        self._failures[tool_name].append(
            FailureRecord(tool_name=tool_name, error=error, params=params)
        )
        return len(self._failures[tool_name]) >= self._max_failures

    def is_blocked(self, tool_name: str) -> bool:
        """检查工具是否被阻止。"""
        return len(self._failures.get(tool_name, [])) >= self._max_failures

    def get_failure_count(self, tool_name: str) -> int:
        """获取失败次数。"""
        return len(self._failures.get(tool_name, []))

    def get_last_failure(self, tool_name: str) -> Optional[FailureRecord]:
        """获取最近一次失败记录。"""
        records = self._failures.get(tool_name, [])
        return records[-1] if records else None

    def format_failure_message(self, tool_name: str, include_count: bool = True) -> str:
        """格式化失败提示信息，简洁展示工具、参数和错误。"""
        last_failure = self.get_last_failure(tool_name)
        if not last_failure:
            return f"工具 [{tool_name}] 执行失败"

        parts = [f"工具 [{tool_name}]"]
        if include_count:
            parts[0] += f" 连续失败 {self.get_failure_count(tool_name)} 次"

        # 添加参数信息
        if last_failure.params:
            params_display = []
            for k, v in last_failure.params.items():
                # 截断过长的值
                value_str = str(v)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                params_display.append(f"{k}={value_str}")
            if params_display:
                parts.append(f"参数: {', '.join(params_display)}")

        # 添加错误信息
        parts.append(f"错误: {last_failure.error}")

        return "\n".join(parts)

    def reset(self, tool_name: str) -> None:
        """重置工具失败计数。"""
        self._failures.pop(tool_name, None)
