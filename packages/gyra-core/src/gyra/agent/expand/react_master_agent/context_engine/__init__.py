"""BAIZE 统一上下文管理引擎 (ContextEngine) -- 两段式压缩。

单一权威时间线 + 单一 join + 两段式压缩（压缩区 LLM 摘要 / 保留区逐字）+ 发送前硬不变量门禁。
取代历史上 hot/warm/cold 三层 + warm 剪枝 + 单条 cold handoff 的实现。

数据流::

    gpts_messages ─┐
                   ├─► TimelineAssembler ─► [load latest 摘要] ─► [触发压缩] ─► 渲染 ─► InvariantGuard ─► messages
    gpts_work_log ─┘   唯一 join+排序        CompressionService     两段式             发送前硬校验
                                              ├─ 压缩区: 9-section LLM 摘要 -> 一条 user 消息
                                              └─ 保留区: 逐字（tool_call+result 原子，大结果截断）
                                              ↕ gpts_cold_segments (压缩段持久化/增量链/恢复)

模块::

    text_utils     共享纯文本工具 (extract_text_content / build_user_content / token 估算)
    timeline       TimelineUnit / Timeline 数据模型
    assembler      TimelineAssembler (唯一真相源, message_id + tool_call_id join)
    compression    CompressionService + CompressionConfig + CompressionSegment (两段式 LLM 摘要)
    invariants     InvariantGuard (I1-I6 硬不变量)
    engine         ContextEngine (门面 build_messages)

注意事项::

- conv_id 模型：每轮新用户提问生成 `{session}_{N}`；但 ask_user / 工具授权回复在 WAITING
  状态下复用原 conv_id（见 gyra_serve agent_chat.py），故一个 conv_id 可含多条 user 消息。
  压缩边界按 (rounds, created_at) 全局时序确定，不依赖"一 conv 一 user"假设。
- 唯一压缩系统：ReActMasterAgent 路径上 ContextEngine 是唯一上下文压缩；compaction_pipeline
  的 Layer2(修剪)/Layer3(压缩) 已退役，仅保留 Layer1(工具输出截断) + Layer4(跨轮历史喂
  system_prompt) + 轮次状态。skill 是标准工具，内容经 tool 结果由 ContextEngine 原子渲染，
  无需特殊重注入。
- 配置：压缩参数支持环境变量覆盖，见 ReActMasterAgent._build_engine_config
  (GYRA_COMPRESS_THRESHOLD_RATIO / GYRA_COMPRESS_RETAIN_RATIO /
  GYRA_COMPRESS_MIN_INTERVAL_TURNS / GYRA_COMPRESS_RETAIN_TOOL_RESULT_MAX_LENGTH /
  GYRA_COMPRESS_MAX_SUMMARY_CHARS / GYRA_HISTORY_BUDGET_RATIO)。
- token 计数：tiktoken cl100k_base（gyra-core 核心依赖），全链路统一；
  count_tokens 不可用时兜底 chars//4。
"""

from .engine import (
    BuildOutput,
    CompressionPersistenceAdapter,
    ContextEngine,
    EngineConfig,
    EventEmitter,
    InMemoryCompressionPersistence,
    NoopEventEmitter,
)
from .invariants import GuardReport, InvariantGuard
from .compression import (
    COMPRESSION_PROMPT,
    SUMMARY_PREFIX,
    CompressionConfig,
    CompressionSegment,
    CompressionService,
    SummarizeFn,
    TokenCounter,
)
from .text_utils import (
    DEFAULT_CHARS_PER_TOKEN,
    build_user_content,
    estimate_message_tokens,
    estimate_tokens_text,
    extract_text_content,
)
from .timeline import (
    ResultStatus,
    Timeline,
    TimelineUnit,
    ToolCallBinding,
    UnitKind,
)
from .assembler import TimelineAssembler

__all__ = [
    "DEFAULT_CHARS_PER_TOKEN",
    "extract_text_content",
    "build_user_content",
    "estimate_tokens_text",
    "estimate_message_tokens",
    "UnitKind",
    "ResultStatus",
    "ToolCallBinding",
    "TimelineUnit",
    "Timeline",
    "TimelineAssembler",
    "CompressionConfig",
    "CompressionSegment",
    "CompressionService",
    "SummarizeFn",
    "TokenCounter",
    "SUMMARY_PREFIX",
    "COMPRESSION_PROMPT",
    "GuardReport",
    "InvariantGuard",
    "EngineConfig",
    "BuildOutput",
    "ContextEngine",
    "CompressionPersistenceAdapter",
    "EventEmitter",
    "NoopEventEmitter",
    "InMemoryCompressionPersistence",
]
