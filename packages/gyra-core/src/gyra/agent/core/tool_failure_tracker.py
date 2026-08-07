"""PR 7: ToolFailureTracker — 工具失败追踪 + 熔断 + cooldown。

V1 已有 ReActMasterAgent._check_and_record_tool_failure（计数 + 阈值 + 永久熔断）。
本模块补两个 V1 缺的能力：
1. cooldown — 熔断 N 秒后自动解除（V1 是永久熔断，需手动 reset）
2. record_success — 工具成功时自动清空失败计数（V1 是手动 reset）

设计为独立工具类，每个会话 / agent 一个实例。不依赖 ReActMasterAgent，
未来可替换 V1 的内联计数逻辑，或独立用于其他 agent 类型。
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FailureRecord:
    """单次失败记录。"""
    tool_name: str
    error: str
    timestamp: float  # time.monotonic()，用于 cooldown 计算
    wall_time: float = 0.0  # time.time()，用于日志展示
    params: Optional[Dict[str, Any]] = None  # 记录失败时的参数


@dataclass
class ToolFailureTracker:
    """工具失败追踪：连续失败 N 次后熔断，熔断后 cooldown 秒自动解除。

    每个会话独立。线程不安全（agent loop 单线程，OK）。

    Usage:
        tracker = ToolFailureTracker(conv_id="conv1")
        if tracker.is_disabled("execute_sql"):
            return error  # 熔断中，跳过执行
        try:
            result = run_tool(...)
            tracker.record_success("execute_sql")
        except Exception as e:
            tracker.record_failure("execute_sql", str(e))
    """
    conv_id: str
    max_consecutive_failures: int = 5
    cooldown_seconds: int = 300  # 5 分钟
    _failures: Dict[str, List[FailureRecord]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _disabled_until: Dict[str, float] = field(default_factory=dict)

    def record_failure(
        self, tool_name: str, error: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录一次失败。若达到阈值，设置 cooldown 截止时间。"""
        if not tool_name:
            return
        now_mono = time.monotonic()
        now_wall = time.time()
        self._failures[tool_name].append(
            FailureRecord(
                tool_name=tool_name,
                error=error,
                timestamp=now_mono,
                wall_time=now_wall,
                params=params,
            )
        )
        failure_count = len(self._failures[tool_name])

        # 构建日志信息
        params_str = ""
        if params:
            # 只显示关键参数，避免日志过长
            key_params = {
                k: str(v)[:50] + "..." if len(str(v)) > 50 else v
                for k, v in params.items()
                if k in ["url", "query", "path", "id", "name", "sql", "code"]
            }
            if key_params:
                params_str = f" params={key_params}"

        logger.warning(
            f"[failure-tracker] conv={self.conv_id} tool={tool_name} "
            f"failed ({failure_count}/{self.max_consecutive_failures}): {error}{params_str}"
        )
        if failure_count >= self.max_consecutive_failures:
            self._disabled_until[tool_name] = now_mono + self.cooldown_seconds
            logger.error(
                f"[failure-tracker] conv={self.conv_id} tool={tool_name} "
                f"circuit-broken for {self.cooldown_seconds}s "
                f"(consecutive failures={failure_count})"
            )

    def record_success(self, tool_name: str) -> None:
        """记录一次成功。清空失败计数 + 移除熔断。"""
        if not tool_name:
            return
        if tool_name in self._failures:
            self._failures.pop(tool_name, None)
        if tool_name in self._disabled_until:
            self._disabled_until.pop(tool_name, None)
            logger.info(
                f"[failure-tracker] conv={self.conv_id} tool={tool_name} "
                f"recovered after success, block lifted"
            )

    def is_disabled(self, tool_name: str) -> bool:
        """检查工具是否在 cooldown 期内。

        cooldown 已过期时自动清理状态（lazy expiry）。
        """
        if not tool_name:
            return False
        until = self._disabled_until.get(tool_name)
        if until is None:
            return False
        if time.monotonic() >= until:
            # cooldown 过期，lazy 清理
            self._disabled_until.pop(tool_name, None)
            self._failures.pop(tool_name, None)
            logger.info(
                f"[failure-tracker] conv={self.conv_id} tool={tool_name} "
                f"cooldown expired, block lifted"
            )
            return False
        return True

    def get_disabled_tools(self) -> List[str]:
        """返回当前所有被熔断的工具（已过期的会被 lazy 清理）。"""
        return [t for t in list(self._disabled_until.keys()) if self.is_disabled(t)]

    def get_failure_count(self, tool_name: str) -> int:
        """返回工具的当前连续失败次数。"""
        return len(self._failures.get(tool_name, []))

    def get_last_failure(self, tool_name: str) -> Optional[FailureRecord]:
        """返回工具的最近一次失败记录（无则 None）。"""
        records = self._failures.get(tool_name, [])
        return records[-1] if records else None

    def format_failure_message(self, tool_name: str, include_count: bool = True) -> str:
        """格式化失败提示信息，简洁展示工具、参数和错误。

        Args:
            tool_name: 工具名称
            include_count: 是否包含失败次数（终止时显示，提醒时可省略）
        """
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

    def reset(self, tool_name: Optional[str] = None) -> None:
        """手动重置。tool_name=None 重置所有。"""
        if tool_name is None:
            self._failures.clear()
            self._disabled_until.clear()
        else:
            self._failures.pop(tool_name, None)
            self._disabled_until.pop(tool_name, None)

    def snapshot(self) -> Dict[str, Any]:
        """返回可序列化快照（用于日志 / 调试）。"""
        return {
            "conv_id": self.conv_id,
            "max_consecutive_failures": self.max_consecutive_failures,
            "cooldown_seconds": self.cooldown_seconds,
            "failure_counts": {
                t: len(rs) for t, rs in self._failures.items()
            },
            "disabled_tools": [
                {
                    "tool": t,
                    "disabled_until_remaining_s": max(
                        0, self._disabled_until[t] - time.monotonic()
                    ),
                }
                for t in self._disabled_until
            ],
        }
