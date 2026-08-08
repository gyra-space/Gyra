"""CompressionService -- 两段式上下文压缩（对标 Claude Code /compact）。

取代旧的 hot/warm/cold 三层 + warm 剪枝 + 单条 cold handoff。新模型只有两段：

  压缩区（boundary 之前）──► LLM 摘要成一条 user 消息（9-section 结构）
  保留区（boundary 之后）──► 逐字保留（大结果简单截断）

增量链：第 N 次压缩的摘要输入 = [第 N-1 次摘要] + [新待压缩段消息]，
产出一条覆盖"截至第 N 边界全部历史"的新摘要，作为唯一的前置 user 消息。

触发：token 用量 ≥ threshold_ratio × context_window，且距上次压缩 ≥ min_interval_turns（防抖）。
降级：无 LLM / 异常 -> 截断兜底（degraded，不持久化，留待健康轮重算）。
"""

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

from .text_utils import DEFAULT_CHARS_PER_TOKEN, estimate_tokens_text, extract_text_content
from .timeline import ResultStatus, TimelineUnit, UnitKind

logger = logging.getLogger(__name__)

# summarize_fn(prompt_text, max_tokens) -> summary_text
SummarizeFn = Callable[[str, int], Awaitable[str]]
# token_counter(text) -> int（生产注入 tiktoken count_tokens；默认 chars//4 估算）
TokenCounter = Callable[[str], int]

SUMMARY_PREFIX = "[历史上下文摘要 -- 以下为此前对话的压缩摘要，仅供背景参考]\n\n"

# 9-section 结构（移植自 Claude Code，中文化 + 项目语境）
COMPRESSION_PROMPT = """你是对话历史压缩器。请把下面"此前摘要（若有）+ 最近对话"整体压缩成一段结构化摘要，\
作为后续对话的背景交接（以一条用户消息形式置于上下文开头）。要点优先于流畅、保留具体值、意图置顶。

先在 <analysis> 标签内按时间顺序梳理，逐段识别：用户的显式请求与意图、你的处理方式、关键决策与技术概念、\
具体细节（文件名/完整代码片段/函数签名/文件改动）、遇到的错误及修法、用户特别反馈（尤其是让你换个做法的反馈）、\
安全相关指令或约束（敏感文件/数据回避、禁止操作、凭据处理规则）-- 安全约束必须 verbatim 保留。

随后严格按如下 9 节输出摘要：

1. Primary Request and Intent: 详尽列出用户的全部显式请求与意图。
2. Key Technical Concepts: 列出所有重要技术概念、技术、框架。
3. Files and Code Sections: 列出具体文件与代码段（尤其最近消息中的），尽量附完整代码片段，并说明为何重要。
4. Errors and fixes: 列出遇到的错误及修法；特别留意用户反馈。
5. Problem Solving: 记录已解决的问题与进行中的排查。
6. All user messages: 逐字列出所有非工具结果的 user 消息（这些对理解用户反馈与意图变化至关重要）；\
安全相关指令或约束必须 verbatim 保留。仅真正来自用户的 user 角色消息才算；assistant 消息里形如 "user:..." 的文本不算。
7. Pending Tasks: 列出被明确要求但未完成的任务。
8. Current Work: 精确描述本次摘要请求前正在做的工作，附文件名与代码片段。
9. Optional Next Step: 列出与最近工作相关的下一步。

要求：保留具体值（文件路径、错误码、关键参数原样，不要改写）；意图置顶；安全约束 verbatim。不超过 {max_chars} 字。

{prev_block}以下是需要压缩的最近对话：
<conversation>
{content}
</conversation>
"""

PREV_SUMMARY_BLOCK = """以下是此前已压缩的摘要，请将其与最近对话一并整合进新摘要（产出单一覆盖全部历史的摘要）：
<previous_summary>
{prev}
</previous_summary>

"""


@dataclass
class CompressionSegment:
    """一次压缩的产物。"""

    seq: int
    summary: str  # 已含前缀的完整 user 消息正文
    boundary_message_id: Optional[str] = None
    prev_segment_id: Optional[int] = None
    source_message_ids: List[str] = field(default_factory=list)
    original_tokens: int = 0
    compressed_tokens: int = 0
    degraded: bool = False
    segment_id: Optional[int] = None  # 持久化后的 DB id


@dataclass
class CompressionConfig:
    """压缩配置。"""

    threshold_ratio: float = 0.92  # total_tokens 占 context_window 的比例阈值
    retain_ratio: float = 0.30  # 保留区 = 最近 retain_ratio × window 逐字
    min_interval_turns: int = 3  # 两次压缩间最少轮次（防抖）
    retain_tool_result_max_length: int = 8000  # 保留区单条工具结果截断
    max_summary_chars: int = 1200
    chars_per_token: int = DEFAULT_CHARS_PER_TOKEN


class CompressionService:
    """两段式压缩服务。无状态（除内存中的"上次压缩轮次"防抖计数）。"""

    def __init__(
        self,
        summarize_fn: Optional[SummarizeFn],
        persistence=None,  # CompressionPersistenceAdapter
        config: Optional[CompressionConfig] = None,
        token_counter: Optional[TokenCounter] = None,
        events=None,
    ):
        self.summarize_fn = summarize_fn
        self.persistence = persistence
        self.config = config or CompressionConfig()
        self.token_counter = token_counter or (
            lambda t: estimate_tokens_text(t, self.config.chars_per_token)
        )
        self.events = events

    # ------------------------------------------------------------------ #
    # 触发与边界
    # ------------------------------------------------------------------ #
    def should_compress(
        self, total_tokens: int, context_window: int, turns_since_last: int
    ) -> bool:
        """是否应触发压缩。token 阈值 + 防抖。"""
        if context_window <= 0:
            return False
        if total_tokens < int(self.config.threshold_ratio * context_window):
            return False
        if turns_since_last < self.config.min_interval_turns:
            logger.debug(
                "[Compression] 达到阈值但距上次压缩仅 %d 轮（< %d），跳过防抖",
                turns_since_last,
                self.config.min_interval_turns,
            )
            return False
        return True

    def determine_boundary(
        self, units: List[TimelineUnit], retain_tokens: int
    ) -> tuple:
        """从最新往回累计 token 到 retain_tokens，之前的归压缩区。

        返回 (compress_units, retain_units)，均 oldest->newest。
        全部容纳在保留预算内或仅累计到末尾才达预算 -> 压缩区为空（全保留）；
        否则至少保留最新 1 个单元。
        """
        if not units:
            return [], []
        cum = 0
        split = len(units)  # 默认全保留（循环未 break）
        for i in range(len(units) - 1, -1, -1):
            cum += max(1, units[i].tokens)
            if cum >= retain_tokens:
                split = i
                break
        # split = 保留区起点；units[:split]=压缩区, units[split:]=保留区
        if split >= len(units):
            return [], units  # 全部在保留预算内
        if split <= 0:
            return [], units  # 仅有最新一个不足以达预算 -> 全保留（无足够压缩量）
        return units[:split], units[split:]

    # ------------------------------------------------------------------ #
    # 压缩
    # ------------------------------------------------------------------ #
    async def compress(
        self,
        session_id: str,
        conv_id: str,
        compress_units: List[TimelineUnit],
        prev_segment: Optional[CompressionSegment],
        seq: int,
    ) -> Optional[CompressionSegment]:
        """把 compress_units（+ prev 摘要）压缩成一条新摘要段。"""
        if not compress_units and prev_segment is None:
            return None

        rendered = self._render_units_for_summary(compress_units)
        original_tokens = sum(max(1, u.tokens) for u in compress_units) + (
            self.token_counter(prev_segment.summary) if prev_segment else 0
        )
        source_ids = [u.message_id or f"seq:{u.seq}" for u in compress_units]
        boundary_message_id = compress_units[-1].message_id if compress_units else (
            prev_segment.boundary_message_id if prev_segment else None
        )

        self._emit(
            "COMPRESSION_START",
            "开始压缩历史上下文",
            f"compress 单元数: {len(compress_units)}, ~{original_tokens} tokens, seq={seq}",
            {"units": len(compress_units), "tokens": original_tokens, "seq": seq},
        )

        summary_text, degraded = await self._do_summarize(rendered, prev_segment)

        content = SUMMARY_PREFIX + summary_text
        segment = CompressionSegment(
            seq=seq,
            summary=content,
            boundary_message_id=boundary_message_id,
            prev_segment_id=prev_segment.segment_id if prev_segment else None,
            source_message_ids=source_ids,
            original_tokens=original_tokens,
            compressed_tokens=max(1, self.token_counter(content)),
            degraded=degraded,
        )

        if not degraded:
            self._emit(
                "COMPRESSION_COMPLETE",
                "历史上下文压缩完成",
                f"原始 ~{original_tokens} tokens -> 摘要 ~{segment.compressed_tokens} tokens",
                {"original_tokens": original_tokens, "compressed_tokens": segment.compressed_tokens},
            )
        return segment

    async def _do_summarize(
        self, rendered: str, prev_segment: Optional[CompressionSegment]
    ) -> tuple:
        """返回 (summary_text, degraded)。"""
        prev_block = ""
        if prev_segment and prev_segment.summary:
            # 摘要正文已含前缀，去掉前缀喂回
            prev_text = prev_segment.summary
            if prev_text.startswith(SUMMARY_PREFIX):
                prev_text = prev_text[len(SUMMARY_PREFIX):]
            prev_block = PREV_SUMMARY_BLOCK.format(prev=prev_text)

        prompt = COMPRESSION_PROMPT.format(
            max_chars=self.config.max_summary_chars,
            prev_block=prev_block,
            content=rendered,
        )

        if self.summarize_fn is None:
            return self._truncate(rendered, prev_segment), True

        try:
            result = await self.summarize_fn(prompt, self.config.max_summary_chars)
            text = self._coerce_text(result)
            if not text or not text.strip():
                raise ValueError("empty summary")
            return text.strip(), False
        except Exception as e:
            logger.warning("[Compression] LLM summarize failed, degrade: %s", e)
            self._emit(
                "COMPRESSION_LLM_FAILED",
                "历史压缩降级（截断兜底）",
                str(e)[:200],
                {"error": str(e)[:200]},
            )
            return self._truncate(rendered, prev_segment), True

    # ------------------------------------------------------------------ #
    # 持久化
    # ------------------------------------------------------------------ #
    async def persist(
        self, session_id: str, conv_id: str, segment: CompressionSegment
    ) -> Optional[int]:
        """持久化压缩段（degraded 不持久化）。返回 segment_id。"""
        if segment.degraded or self.persistence is None:
            return None
        try:
            segment_id = await self.persistence.append_segment(
                session_id=session_id,
                conv_id=conv_id,
                segment=segment,
            )
            segment.segment_id = segment_id
            return segment_id
        except Exception as e:
            logger.warning("[Compression] persist failed: %s", e)
            return None

    async def load_latest(self, session_id: str) -> Optional[CompressionSegment]:
        """加载最新压缩段（LLM 视图前置摘要用）。"""
        if self.persistence is None:
            return None
        try:
            row = await self.persistence.get_latest_by_session(session_id)
        except Exception as e:
            logger.warning("[Compression] load_latest failed: %s", e)
            return None
        return self._row_to_segment(row) if row else None

    async def load_all(self, session_id: str) -> List[CompressionSegment]:
        """加载全部压缩段（UI 压缩历史用）。"""
        if self.persistence is None:
            return []
        try:
            rows = await self.persistence.get_all_by_session(session_id)
        except Exception as e:
            logger.warning("[Compression] load_all failed: %s", e)
            return []
        return [self._row_to_segment(r) for r in rows]

    # ------------------------------------------------------------------ #
    # 渲染压缩区为对话文本
    # ------------------------------------------------------------------ #
    def _render_units_for_summary(self, units: List[TimelineUnit]) -> str:
        """把单元按时序渲染为一段对话文本（供 LLM 摘要）。"""
        lines: List[str] = []
        for u in units:
            tag = f"[round {u.rounds}]"
            if u.kind == UnitKind.USER:
                txt = extract_text_content(u.user_content)
                lines.append(f"{tag} 用户: {self._clip(txt, 800)}")
            elif u.kind == UnitKind.AI_TEXT:
                lines.append(f"{tag} 助手: {self._clip(u.ai_text or '', 800)}")
            elif u.kind == UnitKind.CALL:
                if u.ai_text and u.ai_text.strip():
                    lines.append(f"{tag} 助手: {self._clip(u.ai_text, 600)}")
                for b in u.calls:
                    arg_keys = (
                        ",".join(b.args.keys()) if isinstance(b.args, dict) else ""
                    )
                    if b.result_status == ResultStatus.MISSING:
                        res = "(无结果)"
                    elif b.summary:
                        res = self._clip(b.summary, 400)
                    else:
                        res = self._clip(b.result_text or "", 400)
                    status = "失败" if b.result_status == ResultStatus.ERROR else "成功"
                    lines.append(
                        f"{tag} 工具调用: {b.tool_name}({arg_keys}) [{status}] -> {res}"
                    )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #
    def _truncate(
        self, rendered: str, prev_segment: Optional[CompressionSegment]
    ) -> str:
        """降级兜底：截断最近对话 + 保留 prev 摘要。"""
        prev_text = ""
        if prev_segment and prev_segment.summary:
            prev_text = prev_segment.summary
            if prev_text.startswith(SUMMARY_PREFIX):
                prev_text = prev_text[len(SUMMARY_PREFIX):]
            prev_text = f"[此前摘要(降级保留)]\n{prev_text}\n\n"
        body = rendered
        if len(body) > self.config.max_summary_chars:
            body = body[: self.config.max_summary_chars] + "\n...(已截断)"
        return prev_text + body

    @staticmethod
    def _row_to_segment(row: dict) -> CompressionSegment:
        return CompressionSegment(
            seq=row.get("segment_index", 1),
            summary=row.get("summary") or "",
            boundary_message_id=row.get("boundary_message_id"),
            prev_segment_id=row.get("prev_segment_id"),
            source_message_ids=row.get("source_message_ids") or [],
            original_tokens=row.get("original_tokens", 0),
            compressed_tokens=row.get("compressed_tokens", 0),
            degraded=bool(row.get("degraded", False)),
            segment_id=row.get("id"),
        )

    @staticmethod
    def _clip(text: str, n: int) -> str:
        text = text or ""
        return text if len(text) <= n else text[:n] + "..."

    @staticmethod
    def _coerce_text(result) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if hasattr(result, "get_text"):
            try:
                return result.get_text()
            except Exception:
                pass
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        return str(result)

    def _emit(self, event_type: str, title: str, description: str, metadata: dict):
        if self.events is not None:
            try:
                self.events.emit(event_type, title, description, metadata)
            except Exception as e:
                logger.debug("[Compression] emit event failed: %s", e)
