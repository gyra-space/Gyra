"""V2 兼容适配器：把 BAIZE 的 DoomLoopDetector / Truncator / Resource pack 适配到
default_acting.py 期望的接口。

default_acting.py 期望：
  doom_loop_detector.check(name, args) -> bool        (async)
  truncator.truncate(content, name, args) -> result   (async, with .truncated, .truncated_content)

BAIZE 实际接口：
  DoomLoopDetector.check_doom_loop(name, args) -> DoomLoopCheckResult  (sync)
  Truncator.truncate(content, name, ...) -> TruncationResult           (sync, .is_truncated, .content)
"""
from __future__ import annotations

from typing import Any, Optional


class DoomLoopAdapter:
    """适配 BAIZE DoomLoopDetector 到 V2 接口。

    V2 default_acting.py 调用 `await doom_loop_detector.check(name, args) -> bool`。
    BAIZE DoomLoopDetector 是同步 `check_doom_loop(name, args) -> DoomLoopCheckResult`。
    """

    def __init__(self, detector: Optional[Any]):
        self._detector = detector

    async def check(self, tool_name: str, args: dict) -> bool:
        if self._detector is None:
            return True  # 无检测器，放行
        try:
            result = self._detector.check_doom_loop(tool_name, args)
            # BAIZE DoomLoopCheckResult 真实字段为 is_doom_loop / action / message，
            # 不存在 should_block。此前误读 should_block 导致 getattr 恒为 False、
            # not False=True 永远放行，DoomLoop 只告警不阻断（工具层死循环）。
            # 这里以 is_doom_loop 为唯一判定依据：命中即阻断。
            if getattr(result, "is_doom_loop", False):
                return False
            return True
        except Exception:
            return True  # 检测异常不阻塞主流程


class TruncatorAdapter:
    """适配 BAIZE Truncator 到 V2 接口。

    V2 default_acting.py 调用 `await truncator.truncate(content, name, args)`
    期望返回带 `.truncated` (bool) 和 `.truncated_content` (str) 的对象。

    BAIZE Truncator.truncate 是同步，返回 TruncationResult（字段 `.is_truncated` /
    `.content`）。我们用 dataclass 桥接字段名。
    """

    def __init__(self, truncator: Optional[Any]):
        self._truncator = truncator

    async def truncate(self, content: str, tool_name: str, args: dict) -> Any:
        from dataclasses import dataclass

        @dataclass
        class _V2TruncResult:
            truncated: bool
            truncated_content: str

        if self._truncator is None or not content:
            return _V2TruncResult(truncated=False, truncated_content=content)
        try:
            result = self._truncator.truncate(content, tool_name)
            return _V2TruncResult(
                truncated=bool(getattr(result, "is_truncated", False)),
                truncated_content=getattr(result, "content", content),
            )
        except Exception:
            return _V2TruncResult(truncated=False, truncated_content=content)
