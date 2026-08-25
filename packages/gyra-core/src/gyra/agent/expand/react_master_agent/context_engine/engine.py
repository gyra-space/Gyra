"""ContextEngine -- 两段式上下文引擎（门面/编排）。

build_messages 串起：assemble -> [load latest 摘要] -> [触发压缩] -> render -> guard.repair。

两段式（对标 Claude Code /compact）：
  压缩区（最新 boundary 之前）-- 一条 user 摘要消息（CompressionService 产出，9-section）
  保留区（boundary 之后）    -- 逐字保留（tool_call+result 原子，大结果截断）

引擎不持 agent 引用、不碰 GptsMemory。三个注入协作者保证可纯测：
  - CompressionPersistenceAdapter: 压缩段持久化（append_segment / get_latest_by_session / get_all_by_session）
  - SummarizeFn: 一次性 LLM 摘要 callable
  - TokenCounter: token 计数（生产 tiktoken，默认 chars//4 估算）
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from .assembler import TimelineAssembler
from .compression import (
    CompressionConfig,
    CompressionSegment,
    CompressionService,
    SUMMARY_PREFIX,
    SummarizeFn,
    TokenCounter,
)
from .invariants import GuardReport, InvariantGuard
from .text_utils import DEFAULT_CHARS_PER_TOKEN, estimate_messages_tokens
from .timeline import ResultStatus, TimelineUnit, ToolCallBinding, UnitKind

logger = logging.getLogger(__name__)

ROLE_AI = "ai"
ROLE_HUMAN = "human"
ROLE_TOOL = "tool"

_SUPERSEDED_PLACEHOLDER = "[写入内容已被后续读取/写入覆盖，此处省略具体内容]"


# ---------------------------------------------------------------------- #
# 注入接口
# ---------------------------------------------------------------------- #
class CompressionPersistenceAdapter(Protocol):
    async def append_segment(
        self, session_id: str, conv_id: str, segment: CompressionSegment
    ) -> Optional[int]:
        ...

    async def get_latest_by_session(
        self, session_id: str
    ) -> Optional[dict]:
        ...

    async def get_all_by_session(self, session_id: str) -> List[dict]:
        ...


class EventEmitter(Protocol):
    def emit(
        self,
        event_type: str,
        title: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...


class NoopEventEmitter:
    def emit(self, event_type, title, description="", metadata=None) -> None:
        return None


class InMemoryCompressionPersistence:
    """内存版压缩段持久化（降级/测试用）。无跨进程恢复能力。"""

    def __init__(self):
        self._segments: List[dict] = []

    async def append_segment(self, session_id, conv_id, segment):
        seq = segment.seq
        row = {
            "id": len(self._segments) + 1,
            "session_id": session_id,
            "conv_id": conv_id,
            "segment_index": seq,
            "boundary_message_id": segment.boundary_message_id,
            "prev_segment_id": segment.prev_segment_id,
            "summary": segment.summary,
            "source_message_ids": list(segment.source_message_ids),
            "original_tokens": segment.original_tokens,
            "compressed_tokens": segment.compressed_tokens,
            "degraded": segment.degraded,
        }
        self._segments.append(row)
        segment.segment_id = row["id"]
        return row["id"]

    async def get_latest_by_session(self, session_id):
        rows = [r for r in self._segments if r["session_id"] == session_id]
        if not rows:
            return None
        return max(rows, key=lambda r: r["segment_index"])

    async def get_all_by_session(self, session_id):
        return sorted(
            [r for r in self._segments if r["session_id"] == session_id],
            key=lambda r: r["segment_index"],
        )


# ---------------------------------------------------------------------- #
# 配置 / 输出
# ---------------------------------------------------------------------- #
@dataclass
class EngineConfig:
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    history_budget_ratio: float = 0.85  # context_window × 此比例 = 可用历史预算
    enable_invariant_repair: bool = True
    chars_per_token: int = DEFAULT_CHARS_PER_TOKEN
    # 是否在保留区渲染工具调用（assistant tool_calls + tool 结果）。
    # V1 路径默认 True（ContextEngine 是工具事实唯一来源）；
    # V2 路径设为 False——工具事实由事件日志投影（ProjectorRegistry）单源提供，
    # 避免同一工具调用经「ContextEngine 渲染」与「工具历史投影」双重进入 LLM 上下文。
    render_tool_calls: bool = True


@dataclass
class BuildOutput:
    messages: List[Dict[str, Any]] = field(default_factory=list)  # 不含 system
    total_tokens: int = 0
    compression_segment: Optional[CompressionSegment] = None  # 本次触发产出的段（若有）
    latest_segment: Optional[CompressionSegment] = None  # 当前生效的最新段
    # 两段式历史分区 token（供环形图）：compressed=摘要, retained=保留区逐字
    history_breakdown: Dict[str, int] = field(
        default_factory=lambda: {"compressed": 0, "retained": 0}
    )
    guard_report: Optional[GuardReport] = None

    def get_cache_cleanup_hints(self) -> Dict[str, List[str]]:
        return {}


# ---------------------------------------------------------------------- #
# 引擎
# ---------------------------------------------------------------------- #
class ContextEngine:
    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        compression_persistence: Optional[CompressionPersistenceAdapter] = None,
        summarize_fn: Optional[SummarizeFn] = None,
        token_counter: Optional[TokenCounter] = None,
        events: Optional[EventEmitter] = None,
    ):
        self.config = config or EngineConfig()
        self.events = events or NoopEventEmitter()
        self.compression_persistence = (
            compression_persistence or InMemoryCompressionPersistence()
        )
        # 全链路统一 token 计数器：生产注入 tiktoken count_tokens，默认 chars//4
        self._token_counter = token_counter or (
            lambda t: max(1, len(t) // self.config.chars_per_token)
        )
        self.assembler = TimelineAssembler(
            self.config.chars_per_token, token_counter=self._token_counter
        )
        self.compression = CompressionService(
            summarize_fn=summarize_fn,
            persistence=self.compression_persistence,
            config=self.config.compression,
            token_counter=self._token_counter,
            events=self.events,
        )
        self.guard = InvariantGuard()
        # 防抖：记录上次压缩时的会话累计消息数（粗略的"轮次"代理）
        self._last_compress_msg_count: Dict[str, int] = {}

    async def build_messages(
        self,
        messages: List[Any],
        work_logs_by_conv: Dict[str, List[Any]],
        current_conv_id: str,
        session_id: str,
        context_window: int,
        subagent_goal_id: Optional[str] = None,
        current_user_content: Optional[str] = None,
        # 主动触发压缩:本轮推理前强制走历史摘要压缩(跳过阈值/防抖判断),
        # 由前端 /压缩上下文 会话命令经 ext_info.force_compress 透传至此
        force_compress: bool = False,
    ) -> BuildOutput:
        history_window = int(context_window * self.config.history_budget_ratio)

        # 1) 装配全局有序时间线
        timeline = self.assembler.assemble(
            messages=messages,
            work_logs_by_conv=work_logs_by_conv,
            current_conv_id=current_conv_id,
            session_id=session_id,
            subagent_goal_id=subagent_goal_id,
        )
        units = timeline.units  # oldest -> newest
        if not units:
            return BuildOutput()

        # 2) 加载最新压缩段 -> 切出当前保留区（boundary 之后）
        latest = await self.compression.load_latest(session_id)
        retained_units, compressed_msg_ids = self._split_by_boundary(units, latest)

        # 3) 触发判断：摘要 tokens + 保留区 tokens ≥ 阈值
        summary_tokens = (
            self.compression.token_counter(latest.summary) if latest else 0
        )
        retained_tokens = sum(max(1, u.tokens) for u in retained_units)
        total_tokens = summary_tokens + retained_tokens
        turns_since = self._turns_since_last(session_id, len(units))

        new_segment: Optional[CompressionSegment] = None
        # force_compress(主动指令) 跳过阈值/防抖,直接在当轮推理前对保留区做摘要压缩;
        # 与被动触发走同一套 determine_boundary/compress/persist 历史摘要逻辑
        if force_compress or self.compression.should_compress(total_tokens, history_window, turns_since):
            # 3a) 在当前保留区内确定新边界 -> 新压缩区 + 新保留区
            retain_budget = int(history_window * self.config.compression.retain_ratio)
            new_compress, new_retained = self.compression.determine_boundary(
                retained_units, retain_budget
            )
            if new_compress:
                seq = (latest.seq + 1) if latest else 1
                new_segment = await self.compression.compress(
                    session_id=session_id,
                    conv_id=current_conv_id,
                    compress_units=new_compress,
                    prev_segment=latest,
                    seq=seq,
                )
                if new_segment is not None:
                    await self.compression.persist(session_id, current_conv_id, new_segment)
                    self._last_compress_msg_count[session_id] = len(units)
                    latest = new_segment
                    retained_units = new_retained
                    compressed_msg_ids = compressed_msg_ids | {
                        (u.message_id or f"seq:{u.seq}") for u in new_compress
                    }

        # 4) 渲染：[摘要 user 消息] + [保留区逐字]
        out_messages: List[Dict[str, Any]] = []
        if latest and latest.summary:
            out_messages.append({"role": ROLE_HUMAN, "content": latest.summary})
        out_messages.extend(self._render_units(retained_units))

        # 4.5) 保证当前 user 指令存在（防 DB 读回竞态：append_message fire-and-forget
        #      写 DB、get_session_messages 读 DB，当前轮 user 可能尚未落库）。
        #      若输出中无此指令则追加到末尾；已存在（含 ReAct retry 中位于中段）则不动。
        if current_user_content and current_user_content.strip():
            _cur = current_user_content.strip()
            _present = False
            for _m in out_messages:
                if _m.get("role") not in (ROLE_HUMAN, "user"):
                    continue
                _c = _m.get("content", "")
                _t = (
                    _c
                    if isinstance(_c, str)
                    else " ".join(
                        p.get("text", "")
                        for p in _c
                        if isinstance(p, dict) and p.get("type") == "text"
                    )
                )
                if _t.strip() == _cur:
                    _present = True
                    break
            if not _present:
                out_messages.append({"role": ROLE_HUMAN, "content": current_user_content})

        # 5) 发送前不变量门禁
        if self.config.enable_invariant_repair:
            out_messages, report = self.guard.repair(out_messages)
        else:
            report = self.guard.check(out_messages)

        total_out = estimate_messages_tokens(out_messages, self.config.chars_per_token)
        compressed_tokens = (
            self._token_counter(latest.summary) if latest and latest.summary else 0
        )
        # 历史保留区 token（排除当前用户消息=最后一个 USER 单元），与环形图
        # history 语义一致：history ≈ compressed + retained
        display_units = list(retained_units)
        for i in range(len(display_units) - 1, -1, -1):
            if display_units[i].kind == UnitKind.USER:
                display_units.pop(i)
                break
        retained_tokens = sum(max(1, u.tokens) for u in display_units)
        return BuildOutput(
            messages=out_messages,
            total_tokens=total_out,
            compression_segment=new_segment,
            latest_segment=latest,
            history_breakdown={
                "compressed": compressed_tokens,
                "retained": retained_tokens,
            },
            guard_report=report,
        )

    # ------------------------------------------------------------------ #
    # 切分
    # ------------------------------------------------------------------ #
    def _split_by_boundary(
        self, units: List[TimelineUnit], latest: Optional[CompressionSegment]
    ) -> tuple:
        """按最新段的 boundary_message_id 切：boundary 及之前=已压缩（不渲染），
        之后=保留区（逐字）。无段则全部保留。

        返回 (retained_units, compressed_message_ids)。
        """
        if not latest or not latest.boundary_message_id:
            return units, set()
        boundary = latest.boundary_message_id
        retained: List[TimelineUnit] = []
        compressed_ids = set()
        passed = False
        for u in units:
            uid = u.message_id or f"seq:{u.seq}"
            if not passed:
                compressed_ids.add(uid)
                if uid == boundary:
                    passed = True
                continue
            retained.append(u)
        # 若 boundary 未命中（异常），保守全部保留
        if not passed:
            return units, set()
        return retained, compressed_ids

    def _turns_since_last(self, session_id: str, current_msg_count: int) -> int:
        last = self._last_compress_msg_count.get(session_id)
        if last is None:
            return self.config.compression.min_interval_turns  # 未压缩过 -> 允许触发
        return max(0, current_msg_count - last)

    # ------------------------------------------------------------------ #
    # 渲染
    # ------------------------------------------------------------------ #
    def _render_units(self, units: List[TimelineUnit]) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        limit = self.config.compression.retain_tool_result_max_length
        for u in units:
            if u.kind == UnitKind.USER:
                if u.user_content:
                    messages.append({"role": ROLE_HUMAN, "content": u.user_content})
            elif u.kind == UnitKind.AI_TEXT:
                if u.ai_text and u.ai_text.strip():
                    msg = {"role": ROLE_AI, "content": u.ai_text}
                    self._attach_reasoning_content(msg, u.ai_thinking)
                    messages.append(msg)
            elif u.kind == UnitKind.CALL:
                # render_tool_calls=False（V2）：工具事实由事件日志投影单源提供，
                # 这里只保留调用前后的旁白（ai_text），不重复渲染 tool_calls/tool 结果。
                if not self.config.render_tool_calls:
                    if u.ai_text and u.ai_text.strip():
                        msg = {"role": ROLE_AI, "content": u.ai_text}
                        self._attach_reasoning_content(msg, u.ai_thinking)
                        messages.append(msg)
                    continue
                messages.extend(self._render_call_unit(u, limit))
        return messages

    @staticmethod
    def _attach_reasoning_content(msg: Dict[str, Any], thinking: Optional[str]):
        """DeepSeek 思考模式要求历史 assistant 消息必须原样回传 reasoning_content，
        否则追问会报 'The reasoning_content in the thinking mode must be passed back to the API'。
        仅在确实存在思维链时附加，避免影响其它模型。"""
        if thinking and str(thinking).strip():
            msg["reasoning_content"] = thinking

    def _render_call_unit(
        self, u: TimelineUnit, limit: int
    ) -> List[Dict[str, Any]]:
        renderable = u.renderable_calls()
        if not renderable:
            if u.ai_text and u.ai_text.strip():
                msg = {"role": ROLE_AI, "content": u.ai_text}
                self._attach_reasoning_content(msg, u.ai_thinking)
                return [msg]
            return []

        out: List[Dict[str, Any]] = []
        tool_calls = [
            {
                "id": b.tool_call_id,
                "type": "function",
                "function": {
                    "name": b.tool_name,
                    "arguments": self._args_to_str(b.args),
                },
            }
            for b in renderable
        ]
        ai_msg = {"role": ROLE_AI, "content": u.ai_text or "", "tool_calls": tool_calls}
        self._attach_reasoning_content(ai_msg, u.ai_thinking)
        out.append(ai_msg)
        for b in renderable:
            out.append(
                {
                    "role": ROLE_TOOL,
                    "tool_call_id": b.tool_call_id,
                    "content": self._render_result(b, limit),
                }
            )
        return out

    def _render_result(self, b: ToolCallBinding, limit: int) -> str:
        if b.superseded_content:
            return _SUPERSEDED_PLACEHOLDER
        text = b.result_text or ""
        if b.result_status == ResultStatus.ERROR and not text:
            text = "[工具执行失败]"
        if len(text) > limit:
            suffix = (
                f"\n...(过长已截断，完整结果见归档 {b.full_result_archive})"
                if b.full_result_archive
                else "\n...(过长已截断)"
            )
            text = text[:limit] + suffix
        return text or "[空结果]"

    @staticmethod
    def _args_to_str(args: Any) -> str:
        if isinstance(args, str):
            return args
        try:
            import json

            return json.dumps(args, ensure_ascii=False, default=str)
        except Exception:
            return str(args)
