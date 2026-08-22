"""PermissionGate — 工具调用前的水fall决策中间件链 + 单调守卫。

Spec §9.3. 决策中间件（waterfall）按 order 升序执行，每一级返回
``DecisionResult`` 或 None（无意见、委托下游）；不调 ``next_()`` 即短路——
监听器"不调 next() 即拥有决策"。中间件可读写共享的 ``PermissionContext``。

内置决策顺序（原 5 级链，行为兼容）：
  1. PermissionMode short-circuit (bypass/auto/plan)
  2. session cache (allow_session)
  3. permission_ruleset (static rules: ALLOW/DENY/ASK)
  4. Tool.check_permissions hook (opt-in via `tool` kwarg)
  5. 单调守卫链（ToolGuard：只允许拒绝，不允许放行——fail-closed）
  6. ask → emit AWAITING_TOOL_PERMISSION event + persist checkpoint +
     delegate to InteractionAdapter.request_tool_permission

check() 是 async generator：ask 时 yield AWAITING_TOOL_PERMISSION 事件；
调用方读完生成器后读 gate.last_result 获得最终决策。
"""
from __future__ import annotations
import inspect
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Awaitable, Callable, List, Optional, TYPE_CHECKING
from gyra._private.pydantic import BaseModel, ConfigDict
from gyra.agent.core.v2.permission_mode import PermissionMode
from gyra.agent.core.v2.session_cache import SessionPermissionCache, hash_tool_input
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState
from gyra_core.permission.ruleset import PermissionRuleset, PermissionAction

if TYPE_CHECKING:
    from gyra.agent.core.v2.state_store import StateStore
    from gyra.agent.core.v2.event_stream import EventStream
    from gyra.agent.core.interaction_adapter import InteractionAdapter


# Tools that have side effects (write/delete/execute). In P1 we use a simple
# heuristic: tools whose name matches these patterns are side-effecting.
# P2+ can replace this with Tool.metadata.risk_level.
_SIDE_EFFECT_PATTERNS = ("rm", "write", "delete", "execute", "bash", "shell",
                         "mv", "cp", "mkdir", "rmdir", "chmod", "chown")


def _is_side_effecting(tool_name: str) -> bool:
    lower = tool_name.lower()
    return any(p in lower for p in _SIDE_EFFECT_PATTERNS)


def _decision_allows(decision: Any) -> bool:
    """把 serial 订阅者返回的决策归一化为是否放行（fail-closed）。

    支持的形态：
      - ``True``；
      - 字符串：``allow`` / ``allow_once`` / ``allow_session``（大小写不敏感）；
      - dict：``{"action": ...}`` 或 ``{"decision": ...}`` 同上；
      - 枚举：``value`` / ``name`` 同上。
    其余一律视为拒绝。
    """
    if decision is True:
        return True
    if isinstance(decision, str):
        return decision.lower() in ("allow", "allow_once", "allow_session")
    if isinstance(decision, dict):
        val = decision.get("action", decision.get("decision"))
        if isinstance(val, str):
            return val.lower() in ("allow", "allow_once", "allow_session")
    name = getattr(decision, "value", None) or getattr(decision, "name", None)
    if isinstance(name, str):
        return name.lower() in ("allow", "allow_once", "allow_session")
    return False


class NoInteractionAdapterError(RuntimeError):
    """Raised when PermissionGate reaches the ASK path but no adapter is configured."""


class PermissionDecision:
    ALLOW = "allow"
    DENY = "deny"
    AWAITING = "awaiting"


class PermissionResult(BaseModel):
    model_config = ConfigDict(use_enum_values=False, arbitrary_types_allowed=True)
    decision: str  # PermissionDecision.*
    reason: str = ""
    request_id: Optional[str] = None


class PermissionCheckResult(BaseModel):
    model_config = ConfigDict(use_enum_values=False, arbitrary_types_allowed=True)
    decision: str  # "allow" / "deny" / "ask"
    reason: str = ""


class DecisionKind(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class DecisionResult:
    """waterfall 决策中间件的 typed decision。

    kind=ASK 时由 PermissionGate 负责 emit + checkpoint + adapter 委托；
    ALLOW/DENY 短路后续中间件。
    """
    kind: DecisionKind
    reason: str = ""


@dataclass
class PermissionContext:
    """中间件共享上下文：读写、贯穿整条决策链。

    参数不可改写：工具调用参数（tool_name/tool_input/input_hash）在链中固定，
    历史、审计、UI、执行必须一致。
    """
    tool_name: str
    tool_input: dict
    input_hash: str
    agent_id: Optional[str] = None
    conv_id: Optional[str] = None
    step_id: Optional[str] = None
    extra: dict = field(default_factory=dict)


NextFn = Callable[[], Awaitable[Optional[DecisionResult]]]


class PermissionMiddleware(ABC):
    """决策中间件基类。

    子类实现 ``run(ctx, next_)``：
      - 返回 DecisionResult → 短路（ALLOW/DENY）或转入 ASK；
      - 调用 ``await next_()`` 委托下游；不调 next() 即拥有决策。
    ``order`` 越小越先执行（内置中间件 order 见 PermissionGate._default_middlewares）。
    """

    order: int = 100

    @abstractmethod
    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]: ...


class ToolGuard(ABC):
    """单调守卫：只允许返回 denial（None = 放行，str = 拒绝原因）。

    没有 allow 结果——监听器顺序不可能把一次拒绝翻回允许，权限系统天然
    fail-closed。守卫注册顺序无影响：任一守卫拒绝即拒绝。
    """

    @abstractmethod
    async def check(self, ctx: PermissionContext) -> Optional[str]:
        """返回 denial reason（非 None 即拒绝），或 None 放行。"""


class _GuardMiddleware(PermissionMiddleware):
    """把 ToolGuard 列表包装成决策中间件。

    order=35：在 tool hook 与 ruleset 应用之前执行——单调守卫是 fail-closed
    的最后防线，任何 allow 决策（无论来自 ruleset 还是 tool）都无法绕过守卫。
    """

    order: int = 35

    def __init__(self, guards: List[ToolGuard]):
        self._guards = guards

    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]:
        for guard in self._guards:
            reason = await guard.check(ctx)
            if reason:
                return DecisionResult(kind=DecisionKind.DENY, reason=f"guard: {reason}")
        return await next_()


class _ModeMiddleware(PermissionMiddleware):
    """Level 1: PermissionMode short-circuit (bypass/auto/plan)。"""

    order: int = 10

    def __init__(self, mode: PermissionMode):
        self._mode = mode

    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]:
        if self._mode is PermissionMode.BYPASS:
            return DecisionResult(kind=DecisionKind.ALLOW, reason="bypass mode")
        if self._mode is PermissionMode.AUTO:
            return DecisionResult(kind=DecisionKind.ALLOW, reason="auto mode")
        if self._mode is PermissionMode.PLAN and _is_side_effecting(ctx.tool_name):
            return DecisionResult(
                kind=DecisionKind.DENY,
                reason="plan mode denies side-effecting tool",
            )
        return await next_()


class _SessionCacheMiddleware(PermissionMiddleware):
    """Level 2: session cache (allow_session)。"""

    order: int = 20

    def __init__(self, cache: SessionPermissionCache):
        self._cache = cache

    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]:
        if self._cache.is_allowed(ctx.tool_name, ctx.input_hash):
            return DecisionResult(kind=DecisionKind.ALLOW, reason="session cache")
        return await next_()


class _RulesetMiddleware(PermissionMiddleware):
    """Level 3: permission_ruleset (static rules)。

    只计算 ruleset 决策并写入 ctx.extra，不短路——ruleset 决策在
    tool hook / guard 之后应用（与旧 check() 顺序一致：tool 可覆盖 ruleset）。
    """

    order: int = 30

    def __init__(self, ruleset: Optional[PermissionRuleset]):
        self._ruleset = ruleset

    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]:
        action = PermissionAction.ALLOW
        if self._ruleset is not None:
            action = self._ruleset.check(ctx.tool_name, context={})
        ctx.extra["ruleset_action"] = action
        return await next_()


class _RulesetApplyMiddleware(PermissionMiddleware):
    """Level 3b: 应用 ruleset 决策（在 tool hook / guard 表态之后）。

    ALLOW → ALLOW；DENY → DENY；ASK → 转入 ask 阶段。
    """

    order: int = 50

    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]:
        action = ctx.extra.get("ruleset_action", PermissionAction.ALLOW)
        if action is PermissionAction.ALLOW:
            return DecisionResult(kind=DecisionKind.ALLOW, reason="ruleset allow")
        if action is PermissionAction.DENY:
            return DecisionResult(kind=DecisionKind.DENY, reason="ruleset deny")
        # ASK → 转入 ask 阶段（Level 5；守卫已在前序执行过，不会被绕过）
        return DecisionResult(kind=DecisionKind.ASK, reason="ruleset ask")


class _ToolHookMiddleware(PermissionMiddleware):
    """Level 4: Tool.check_permissions hook (opt-in via `tool` kwarg)。"""

    order: int = 40

    def __init__(self, tool: Optional[Any], gate: "PermissionGate"):
        self._tool = tool
        self._gate = gate

    async def run(self, ctx: PermissionContext, next_: NextFn) -> Optional[DecisionResult]:
        if self._tool is None:
            return await next_()
        try:
            tool_result = await self._tool.check_permissions(ctx.tool_input, context={
                "agent_id": ctx.agent_id,
                "conv_id": ctx.conv_id,
                "step_id": ctx.step_id,
            })
        except NotImplementedError:
            return await next_()
        if tool_result is not None:
            decision = getattr(tool_result, "decision", None)
            reason = getattr(tool_result, "reason", "")
            if decision == "allow":
                return DecisionResult(kind=DecisionKind.ALLOW, reason=f"tool check_permissions: {reason}")
            if decision == "deny":
                return DecisionResult(kind=DecisionKind.DENY, reason=f"tool check_permissions: {reason}")
            # decision == "ask" → 委托 ask 阶段（本中间件无意见，继续）
        return await next_()


class PermissionGate:
    """工具调用前的水fall决策中间件链。check() 是 async generator。

    通过 ``register_middleware`` / ``register_guard`` 可插拔第三方策略：
      - 决策中间件：可改决策、短路、委托下游；
      - 单调守卫：只能拒绝（fail-closed），顺序无关。
    """

    def __init__(
        self,
        state_store: "StateStore",
        event_stream: "EventStream",
        interaction_adapter: Optional["InteractionAdapter"] = None,
        session_cache: Optional[SessionPermissionCache] = None,
        ruleset: Optional[PermissionRuleset] = None,
        mode: PermissionMode = PermissionMode.DEFAULT,
        step_id: Optional[str] = None,
        conv_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool: Optional[Any] = None,
    ):
        self._store = state_store
        self._stream = event_stream
        self._adapter = interaction_adapter
        self._cache = session_cache or SessionPermissionCache()
        self._ruleset = ruleset
        self._mode = mode
        self._step_id = step_id
        self._conv_id = conv_id
        self._agent_id = agent_id
        self._tool = tool
        self._guards: List[ToolGuard] = []
        self._middlewares: List[PermissionMiddleware] = []
        self.last_result: PermissionResult = PermissionResult(
            decision=PermissionDecision.DENY, reason="not checked"
        )

    # ------------------------------------------------------------------
    # 扩展点
    # ------------------------------------------------------------------

    def register_guard(self, guard: ToolGuard) -> None:
        """注册单调守卫：只允许拒绝，不允许放行。fail-closed。"""
        if not isinstance(guard, ToolGuard):
            raise TypeError(f"guard must be ToolGuard, got {type(guard).__name__}")
        self._guards.append(guard)

    def register_middleware(self, middleware: PermissionMiddleware) -> None:
        """注册自定义决策中间件（waterfall 语义）。"""
        if not isinstance(middleware, PermissionMiddleware):
            raise TypeError(
                f"middleware must be PermissionMiddleware, got {type(middleware).__name__}"
            )
        self._middlewares.append(middleware)

    def _default_middlewares(self) -> List[PermissionMiddleware]:
        return [
            _ModeMiddleware(self._mode),
            _SessionCacheMiddleware(self._cache),
            _RulesetMiddleware(self._ruleset),
            _GuardMiddleware(self._guards),
            _ToolHookMiddleware(self._tool, self),
            _RulesetApplyMiddleware(),
        ]

    def _ordered_middlewares(self) -> List[PermissionMiddleware]:
        all_mws = self._default_middlewares() + self._middlewares
        return sorted(all_mws, key=lambda m: m.order)

    # ------------------------------------------------------------------
    # check() — async generator，兼容原有调用契约
    # ------------------------------------------------------------------

    async def check(
        self,
        tool_call: dict,
        emit: Optional[Callable] = None,
    ) -> AsyncGenerator[StepEvent, None]:
        """运行 waterfall 决策链。

        Yields AWAITING_TOOL_PERMISSION events when asking.
        Sets self.last_result. Caller reads last_result after generator exhausts.

        Args:
            tool_call: {"tool": str, "input": dict}
            emit: optional runtime emit callable
                (state, event_type, input_data, output_data) -> StepEvent.
                When provided, the gate uses it to construct+persist the
                AWAITING_TOOL_PERMISSION event (correct seq assigned by runtime).
                When None, the gate constructs the event itself with seq=0
                (unit-test mode; not safe for production replay ordering).
        """
        tool_name = tool_call.get("tool", "")
        tool_input = tool_call.get("input", {}) or {}
        input_hash = hash_tool_input(tool_input)
        ctx = PermissionContext(
            tool_name=tool_name,
            tool_input=tool_input,
            input_hash=input_hash,
            agent_id=self._agent_id,
            conv_id=self._conv_id,
            step_id=self._step_id,
        )

        middlewares = self._ordered_middlewares()

        async def run_chain(index: int) -> Optional[DecisionResult]:
            if index >= len(middlewares):
                return None
            mw = middlewares[index]
            return await mw.run(ctx, lambda: run_chain(index + 1))

        decision = await run_chain(0)

        # 无任何中间件表态 → 默认放行（安全默认：无规则则 ALLOW）
        if decision is None:
            decision = DecisionResult(kind=DecisionKind.ALLOW, reason="default allow")

        if decision.kind is DecisionKind.ALLOW:
            self.last_result = PermissionResult(
                decision=PermissionDecision.ALLOW, reason=decision.reason
            )
            return

        if decision.kind is DecisionKind.DENY:
            self.last_result = PermissionResult(
                decision=PermissionDecision.DENY, reason=decision.reason
            )
            return

        # ASK → serial 决策检查点 → 无裁决时 delegate 给 InteractionAdapter
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        request_payload = {
            "request_id": request_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "step_id": self._step_id,
            "conv_id": self._conv_id,
        }
        await self._store.save_interaction_checkpoint(
            request_id, self._step_id, self._conv_id, request_payload
        )

        # serial 决策检查点（对齐 DSH 审批检查点）：订阅者返回非 None/False
        # 即裁决完成，无需 adapter / 用户介入，也不阻塞等待。
        if emit is not None:
            # Runtime path: 用 runtime 的 emit 保证 seq 正确分配；
            # 支持 mode 的 emit 走 serial 决策检查点，旧式 emit（无 mode）退化为广播。
            dr = await self._emit_serial_event(
                emit, StepState.AWAITING_TOOL_PERMISSION,
                "interaction_request", request_payload,
            )
        else:
            # Unit-test path: construct event directly with seq=0 placeholder
            event = StepEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                step_id=self._step_id,
                conv_id=self._conv_id,
                agent_id=self._agent_id,
                parent_step_id=None,
                state=StepState.AWAITING_TOOL_PERMISSION,
                event_type="interaction_request",
                input=request_payload,
                output={},
                seq=0,
                timestamp=time.time(),
            )
            dr = await self._stream.emit_serial(event)
        yield dr.event
        if dr.decision is not None:
            await self._apply_serial_decision(
                request_id, tool_name, input_hash, dr.decision
            )
            return

        # 无订阅者裁决 → 必须委托 InteractionAdapter 询问用户
        if self._adapter is None:
            # fail-closed：无 adapter 且无订阅者裁决时拒绝执行——既避免高危工具
            # 在无审批通道下被放行（安全事故），也避免抛异常导致整轮 turn 崩溃。
            self._cache.deny(tool_name, input_hash)
            self.last_result = PermissionResult(
                decision=PermissionDecision.DENY,
                reason=(
                    "no interaction adapter configured; "
                    "permission request denied (fail-closed)"
                ),
                request_id=request_id,
            )
            return

        # Delegate to InteractionAdapter (blocks until user responds)
        response = await self._adapter.request_tool_permission(
            tool_name=tool_name, tool_args=tool_input,
        )
        # P1 I-1 fix: read response.choice (the field on InteractionResponse),
        # NOT response.action. Map: allow_once/allow_session → ALLOW; else DENY.
        choice = getattr(response, "choice", None)
        # Clean up checkpoint on denial; runtime cleans up on allow.
        if choice not in ("allow_once", "allow_session"):
            await self._store.delete_interaction_checkpoint(request_id)
            self._cache.deny(tool_name, input_hash)
            self.last_result = PermissionResult(
                decision=PermissionDecision.DENY,
                reason=f"user choice: {choice!r}",
                request_id=request_id,
            )
            return
        if choice == "allow_session":
            self._cache.allow_session(tool_name, input_hash)
        # allow_once: no cache update; checkpoint deletion deferred to runtime
        self.last_result = PermissionResult(
            decision=PermissionDecision.ALLOW,
            reason=f"user choice: {choice}",
            request_id=request_id,
        )

    @staticmethod
    async def _emit_serial_event(
        emit: Callable,
        state: StepState,
        event_type: str,
        input_data: dict,
    ) -> "DispatchResult":
        """调用 runtime emit，兼容新旧两种签名。

        - 新 emit（支持 ``mode`` kwarg，如 runtime._make_emit）：以 serial 模式分发，
          返回 DispatchResult（含决策）；
        - 旧 emit（无 mode 参数）：直接广播，返回 StepEvent，包成无决策的 DispatchResult。
        """
        from gyra.agent.core.v2.event_stream import DispatchResult

        try:
            supports_mode = "mode" in inspect.signature(emit).parameters
        except (TypeError, ValueError):
            supports_mode = False
        if supports_mode:
            return await emit(
                state, event_type, input_data=input_data, mode="serial"
            )
        event = await emit(state, event_type, input_data=input_data)
        return DispatchResult(event=event)

    async def _apply_serial_decision(
        self,
        request_id: str,
        tool_name: str,
        input_hash: str,
        decision: Any,
    ) -> None:
        """应用 serial 订阅者的裁决结果（不阻塞等待 InteractionAdapter）。

        ALLOW → 清理 checkpoint + 可选 session cache；DENY → 清理 checkpoint + 记录拒绝。
        """
        if _decision_allows(decision):
            await self._store.delete_interaction_checkpoint(request_id)
            if isinstance(decision, str) and decision.lower() == "allow_session":
                self._cache.allow_session(tool_name, input_hash)
            self.last_result = PermissionResult(
                decision=PermissionDecision.ALLOW,
                reason=f"serial subscriber decision: {decision!r}",
            )
            return
        await self._store.delete_interaction_checkpoint(request_id)
        self._cache.deny(tool_name, input_hash)
        self.last_result = PermissionResult(
            decision=PermissionDecision.DENY,
            reason=f"serial subscriber decision: {decision!r}",
        )
