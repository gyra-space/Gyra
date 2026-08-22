"""V2 thinking_fn yield 的 typed chunk 类型。"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from gyra.agent.core.v2.tool_call_types import V2ToolCall


@dataclass
class TokenChunk:
    """LLM 流式 token。usage 可选（最后一次 token 附带累计 usage）。

    channel 区分推理与正文两个通道：
      - "thinking"：模型推理/思考过程 token（前端渲染为思考块）；
      - "content"：最终正文 token（前端渲染为文本内容）。
    默认 "content"，兼容不产推理的模型与旧 dict 格式。
    """
    token: str
    usage: Optional[Dict[str, Any]] = None
    channel: str = "content"


@dataclass
class ToolCallChunk:
    """LLM emit 的工具调用（已拼接完整，非 delta）。"""
    tool_calls: List[V2ToolCall]


@dataclass
class UsageChunk:
    """独立的 usage 事件（部分 provider 在 stream 结束时单独发）。"""
    usage: Dict[str, Any]


@dataclass
class AwaitUserChunk:
    """LLM 请求用户输入（暂停 turn）。"""
    reason: str = ""


ThinkingChunk = Union[TokenChunk, ToolCallChunk, UsageChunk, AwaitUserChunk]
