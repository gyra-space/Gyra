"""V2 Runtime——Agent 框架内核.

六件套中的五件在 P1 落地：StepState/EventStream/StateStore/Recovery/PermissionGate。
SubAgent Runtime 在 P2 加。

参见设计文档：docs/superpowers/specs/2026-06-30-agent-framework-evolution-design.md
"""
from gyra.agent.core.hook.schema import BlockingPolicy, HookDecision
from gyra.agent.core.v2.agent_runtime import V2AgentRuntime
from gyra.agent.core.v2.ask_user_adapter import AskUserAdapter
from gyra.agent.core.v2.baize_subsystem_adapter import BAIZESubsystemAdapter
from gyra.agent.core.v2.compat_adapters import DoomLoopAdapter, TruncatorAdapter
from gyra.agent.core.v2.db_tool import DB_TOOL_NAME, DbTool
from gyra.agent.core.v2.default_acting import make_default_acting_fn
from gyra.agent.core.v2.default_thinking import make_default_thinking_fn
from gyra.agent.core.v2.event_projection import (
    ToolHistoryProjector,
    project_tool_history,
)
from gyra.agent.core.v2.event_stream import (
    DispatchResult,
    EventBatchConfig,
    EventStream,
    StepEventCallback,
)
from gyra.agent.core.v2.harness import (
    HarnessContext,
    JobRegistry,
    SkillSeam,
    SubagentSeam,
    VisBridge,
)
from gyra.agent.core.v2.hook_integration import (
    build_conversation_complete_context,
    build_post_tool_use_context,
    build_pre_tool_use_context,
    build_turn_complete_context,
)
from gyra.agent.core.v2.llm_stream_adapter import (
    make_gyra_llm_stream,
    make_gyra_llm_stream_fn,
)
from gyra.agent.core.v2.memory_hook_setup import register_memory_hooks
from gyra.agent.core.v2.permission_gate import (
    DecisionKind,
    DecisionResult,
    NoInteractionAdapterError,
    PermissionCheckResult,
    PermissionContext,
    PermissionDecision,
    PermissionGate,
    PermissionMiddleware,
    PermissionResult,
    ToolGuard,
)
from gyra.agent.core.v2.permission_mode import PermissionMode
from gyra.agent.core.v2.recovery import RecoveryCoordinatorV2
from gyra.agent.core.v2.retrying_thinking import retrying_thinking
from gyra.agent.core.v2.run_loop import run_loop, trigger_conversation_complete
from gyra.agent.core.v2.runtime import resume_step, run_step
from gyra.agent.core.v2.session_cache import SessionPermissionCache, hash_tool_input
from gyra.agent.core.v2.skills import (
    SKILL_TOOL_NAME,
    FilesystemSkillProvider,
    SkillCatalogConsumer,
    SkillDefinition,
    SkillInvocation,
    SkillLookupOptions,
    SkillProvider,
    SkillRegistry,
    SkillSummary,
    SkillTool,
    build_initial_reminder,
    build_replacement_reminder,
)
from gyra.agent.core.v2.spawn_subagent_tool import SpawnSubagentTool
from gyra.agent.core.v2.sse_adapter import stream_to_sse
from gyra.agent.core.v2.state_store import DbStateStore, StateStore, create_state_store
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import (
    VALID_TRANSITIONS,
    IllegalTransitionError,
    StepState,
    validate_transition,
)
from gyra.agent.core.v2.stream_converter import step_event_to_stream_event
from gyra.agent.core.v2.stream_event import EVENT_TYPES, StreamEvent
from gyra.agent.core.v2.subagent_handle import (
    SubAgentHandle,
    SubAgentMode,
    SubAgentStatus,
)
from gyra.agent.core.v2.subagent_interaction_gateway import SubAgentInteractionGateway
from gyra.agent.core.v2.subagent_ops_delegate import (
    SubAgentOpsDelegate,
    SubAgentRegistration,
)
from gyra.agent.core.v2.subagent_runtime import (
    SubAgentRuntime,
    SubAgentSpawnSpec,
)
from gyra.agent.core.v2.thinking_chunk import (
    AwaitUserChunk,
    ThinkingChunk,
    TokenChunk,
    ToolCallChunk,
    UsageChunk,
)
from gyra.agent.core.v2.tool_call_types import V2ToolCall, V2ToolResult
from gyra.agent.core.v2.tool_context_factory import ToolContextFactory
from gyra.agent.core.v2.tool_failure_tracker import ToolFailureTracker
from gyra.agent.core.v2.tool_resolver import ToolResolver
from gyra.agent.core.v2.unified_state_store import SqlAlchemyStateStore
from gyra.agent.core.v2.usage_metric import aggregate_usage, emit_usage_metric

__all__ = [
    "StepState",
    "VALID_TRANSITIONS",
    "validate_transition",
    "IllegalTransitionError",
    "StepEvent",
    "StateStore",
    "DbStateStore",
    "EventStream",
    "DispatchResult",
    "StepEventCallback",
    "EventBatchConfig",
    "RecoveryCoordinatorV2",
    "run_step",
    "resume_step",
    "PermissionMode",
    "PermissionGate",
    "PermissionResult",
    "PermissionDecision",
    "SessionPermissionCache",
    "hash_tool_input",
    "NoInteractionAdapterError",
    "SubAgentRuntime",
    "SubAgentSpawnSpec",
    "SubAgentOpsDelegate",
    "SubAgentRegistration",
    "SubAgentHandle",
    "SubAgentMode",
    "SubAgentStatus",
    "SubAgentInteractionGateway",
    "SpawnSubagentTool",
    "AskUserAdapter",
    "PermissionCheckResult",
    "ToolGuard",
    "PermissionMiddleware",
    "PermissionContext",
    "DecisionResult",
    "DecisionKind",
    "StreamEvent",
    "EVENT_TYPES",
    "step_event_to_stream_event",
    "stream_to_sse",
    "BAIZESubsystemAdapter",
    "emit_usage_metric",
    "aggregate_usage",
    "ThinkingChunk",
    "TokenChunk",
    "ToolCallChunk",
    "UsageChunk",
    "AwaitUserChunk",
    "BlockingPolicy",
    "HookDecision",
    "V2ToolCall",
    "V2ToolResult",
    "ToolFailureTracker",
    "retrying_thinking",
    "ToolResolver",
    "ToolContextFactory",
    "build_pre_tool_use_context",
    "build_post_tool_use_context",
    "build_turn_complete_context",
    "build_conversation_complete_context",
    "register_memory_hooks",
    "make_default_acting_fn",
    "make_default_thinking_fn",
    "make_gyra_llm_stream",
    "make_gyra_llm_stream_fn",
    "run_loop",
    "trigger_conversation_complete",
    "V2AgentRuntime",
    "DoomLoopAdapter",
    "TruncatorAdapter",
    "create_state_store",
    "SqlAlchemyStateStore",
    "project_tool_history",
    "ToolHistoryProjector",
    "HarnessContext",
    "SubagentSeam",
    "JobRegistry",
    "SkillSeam",
    "VisBridge",
    # V2 Skill 资源总线（对齐 DSH ctx.skills）
    "FilesystemSkillProvider",
    "SkillCatalogConsumer",
    "SkillDefinition",
    "SkillInvocation",
    "SkillLookupOptions",
    "SkillProvider",
    "SkillRegistry",
    "SkillSummary",
    "SkillTool",
    "SKILL_TOOL_NAME",
    "build_initial_reminder",
    "build_replacement_reminder",
    # V2 DB 入口（对齐 DSH tool-db：单 db({action}) 入口 + 按需 schema）
    "DbTool",
    "DB_TOOL_NAME",
]
