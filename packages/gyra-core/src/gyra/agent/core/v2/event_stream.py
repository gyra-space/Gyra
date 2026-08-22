"""EventStream--AsyncGenerator + 持久化 + 订阅（emit / waterfall / serial 三分法）。

对齐 DeepSeek Harness（dsh）事件分发三模式：

- emit（广播）：所有订阅者按注册顺序收到事件，不收集返回值；
  订阅者异常只记录日志，不影响主事件流与其他订阅者。
- waterfall（瀑布式 / 环绕中间件）：订阅者签名为 ``(event, next)``，
  必须 ``await next()`` 才能把事件传递给下一个；可通过 ``await next(new_event)``
  改写事件；不调 next() 直接返回即中止整条链。中间件异常只记录日志并透传（fail-open）。
- serial（串行终态检查点）：订阅者签名为 ``(event) -> Optional[decision]``，
  第一个非 None/False 的返回值胜出并停止后续订阅者；只能观察裁决，不能改写事件。

持久化语义（durability-before-visibility）：
- emit / serial：先持久化再通知订阅者；
- waterfall：先让中间件链改写 / 裁决，再持久化最终事件--事件溯源只记录最终事实。

订阅分流（观察 vs 干预）：
- ``emit`` 订阅者（默认）是纯观察者：三种 dispatch 的事件都会在持久化后通知到，
  只观察不改写；
- ``waterfall`` / ``serial`` 订阅者是干预者：只参与对应模式的 dispatch，
  可改写 / 中止（waterfall）或裁决（serial）。

高频渲染事件（默认 ``llm_token``）例外：只广播、不落库（见
:class:`EventBatchConfig`）。
"""
from __future__ import annotations
import dataclasses
import inspect
import logging
from typing import (
    Any, AsyncGenerator, Awaitable, Callable, Iterable, List, Literal, Optional, Tuple, Union,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.state_store import StateStore

logger = logging.getLogger(__name__)

# 分发模式（DSH 三分法）
DispatchMode = Literal["emit", "waterfall", "serial"]


@dataclasses.dataclass
class EventBatchConfig:
    """高频渲染事件配置（默认 ``llm_token``）。

    这些事件**只广播订阅者，不落库**：事件投影 / 恢复 / 用量统计 / compaction
    均不读 DB 中的 token 级事件，逐 token 落库只会让事件日志随回复长度线性膨胀、
    拖慢下一轮全量读。前端流式渲染走订阅者（VisBridge），刷新后重建走
    gpts_messages / work_entries，均不依赖 DB 里的 token 事件。

    其余事件（step_init / tool_call / tool_result / step_done /
    interaction_request）始终立即持久化--step 边界与关键事实保持
    durability-before-visibility，崩溃恢复点不受影响。

    llm_token 不落库只会产生 seq 空洞，seq 由 max(seq)+1 续号，
    ``ORDER BY seq`` 语义不受影响。
    """

    batch_event_types: Optional[frozenset] = None  # None -> 默认高频类型

    # 默认不落库类型：流式 token 渲染事件（高频、无恢复语义）
    DEFAULT_BATCH_TYPES = frozenset({"llm_token"})

    def effective_types(self) -> frozenset:
        if self.batch_event_types is not None:
            return self.batch_event_types
        return self.DEFAULT_BATCH_TYPES

# emit 订阅回调：接收持久化后的 StepEvent
StepEventCallback = Callable[[StepEvent], Union[None, Awaitable[None]]]
# waterfall 订阅回调：必须 await next() 传递；next(new_event) 改写事件；不调 next 即中止
WaterfallCallback = Callable[
    [StepEvent, Callable[..., Awaitable[StepEvent]]],
    Union[None, StepEvent, Awaitable[None], Awaitable[StepEvent]],
]
# serial 订阅回调：返回首个非 None/False 的决策值则胜出
SerialCallback = Callable[[StepEvent], Union[Any, Awaitable[Any]]]


@dataclasses.dataclass
class DispatchResult:
    """三分法分发结果。

    - ``event``：waterfall 链改写后的最终事件（emit/serial 模式下即原事件）；
    - ``aborted``：waterfall 链被中间件中止（未调 next()）；
    - ``decision``：serial 模式下首个非 None/False 的决策值。
    """

    event: StepEvent
    aborted: bool = False
    decision: Any = None


class EventStream:
    """事件流：持久化 + 重放 + 订阅（emit / waterfall / serial 三分法）。"""

    def __init__(
        self,
        state_store: StateStore,
        batch: Optional[EventBatchConfig] = None,
    ):
        """构造事件流。

        ``batch``：None 表示默认开启（llm_token 只广播不落库）。
        显式传 ``False`` 可关闭（所有事件都落库）。
        """
        self._store = state_store
        # (event_types 过滤集, 回调, 模式)；event_types=None 表示订阅全部事件
        self._subscribers: List[Tuple[Optional[frozenset], Callable, str]] = []
        # 高频渲染事件配置：None=未设置->默认开启（生产路径）；False->显式关闭
        if batch is False:
            self._batch: Optional[EventBatchConfig] = None
        elif batch is None:
            self._batch = EventBatchConfig()  # 默认开启
        else:
            self._batch = batch

    def subscribe(
        self,
        callback: Callable,
        event_types: Optional[Iterable[str]] = None,
        mode: str = "emit",
    ) -> Callable[[], None]:
        """订阅 StepEvent，返回 unsubscribe()。

        - ``event_types``：None 订阅全部事件；否则只通知匹配的事件类型。
        - ``mode``：
          - ``"emit"``：广播。回调签名 ``callback(event)``，异常不影响主流程。
          - ``"waterfall"``：中间件链。回调签名 ``callback(event, next)``，
            必须 ``await next()`` 传递；``await next(new_event)`` 改写事件；
            不调 next() 即中止链。异常只记日志并透传（fail-open）。
          - ``"serial"``：终态检查点。回调签名 ``callback(event) -> Optional[decision]``，
            第一个非 None/False 返回值胜出并停止后续订阅者；异常只记日志并继续。
        """
        if mode not in ("emit", "waterfall", "serial"):
            raise ValueError(f"unknown dispatch mode: {mode!r}")
        entry = (frozenset(event_types) if event_types else None, callback, mode)
        self._subscribers.append(entry)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(entry)
            except ValueError:
                pass

        return unsubscribe

    # ------------------------------------------------------------------
    # 三种分发入口
    # ------------------------------------------------------------------

    async def emit(self, event: StepEvent) -> StepEvent:
        """广播（emit 模式）。先持久化再通知 emit 观察者，返回原事件。

        高频渲染事件（默认 ``llm_token``，见 :class:`EventBatchConfig`）
        例外：只广播不落库。
        """
        if self._batch is not None and event.event_type in self._batch.effective_types():
            await self._notify(event)
            return event
        await self._persist(event)
        await self._notify(event)
        return event

    async def emit_waterfall(self, event: StepEvent) -> DispatchResult:
        """瀑布式中间件链。链结束后持久化最终事件并通知观察者，返回 DispatchResult。"""
        result = await self._run_waterfall(event)
        await self._persist(result.event)
        await self._notify(result.event)
        return result

    async def emit_serial(self, event: StepEvent) -> DispatchResult:
        """串行终态检查点。先持久化、通知观察者，再收集首个非 None/False 决策。"""
        await self._persist(event)
        await self._notify(event)
        decision = await self._run_serial(event)
        return DispatchResult(event=event, decision=decision)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    async def _persist(self, event: StepEvent) -> None:
        """持久化事件 + 状态（每个事件先落库再对外可见）。"""
        await self._store.append_event(event)
        await self._store.set_step_state(
            event.step_id, event.conv_id, event.state, event.input
        )

    def _matching(self, event: StepEvent, mode: str) -> List[Callable]:
        return [
            callback
            for event_types, callback, cb_mode in self._subscribers
            if cb_mode == mode
            and (event_types is None or event.event_type in event_types)
        ]

    async def _notify(self, event: StepEvent) -> None:
        """emit 观察者通知：全部事件（emit/waterfall/serial）在持久化后回调，异常只记日志。"""
        for callback in self._matching(event, "emit"):
            try:
                result = callback(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: BLE001
                logger.warning(
                    "EventStream subscriber %r failed on event %s",
                    callback, event.event_type, exc_info=True,
                )

    async def _run_waterfall(self, event: StepEvent) -> DispatchResult:
        """waterfall 链：中间件依次 (event, next) 调用。

        - ``await next()``：传递当前事件给下游；
        - ``await next(new_event)``：以 new_event 改写后传给下游；
        - 不调 next() 直接返回：中止整条链（aborted=True）；
        - 回调返回非 None 的 StepEvent：作为本层的后置改写；
        - 回调异常：记录日志并透传当前事件（fail-open），不阻断下游。
        """
        matched = self._matching(event, "waterfall")
        if not matched:
            return DispatchResult(event=event)

        aborted = False

        async def run(index: int, current: StepEvent) -> StepEvent:
            if index >= len(matched):
                return current
            callback = matched[index]
            called_next = False
            chain_result: dict = {"event": None}

            async def next_fn(new_event: Optional[StepEvent] = None) -> StepEvent:
                nonlocal called_next
                called_next = True
                nxt = new_event if new_event is not None else current
                chain_result["event"] = await run(index + 1, nxt)
                return chain_result["event"]

            try:
                result = callback(current, next_fn)
                if inspect.isawaitable(result):
                    result = await result
            except Exception:  # noqa: BLE001
                logger.warning(
                    "waterfall subscriber %r failed on event %s",
                    callback, event.event_type, exc_info=True,
                )
                # fail-open：跳过异常中间件，继续下游链
                return await run(index + 1, current)

            if not called_next:
                nonlocal aborted
                aborted = True
                return current  # 未调 next()：中止链，事件保持当前值

            # 回调返回值优先（后置改写）；否则用下游链的结果
            if result is not None and isinstance(result, StepEvent):
                return result
            return chain_result["event"] if chain_result["event"] is not None else current

        final_event = await run(0, event)
        return DispatchResult(event=final_event, aborted=aborted)

    async def _run_serial(self, event: StepEvent) -> Any:
        """serial 检查点：首个非 None/False 返回值胜出并停止；异常只记日志并继续。"""
        for callback in self._matching(event, "serial"):
            try:
                result = callback(event)
                if inspect.isawaitable(result):
                    result = await result
            except Exception:  # noqa: BLE001
                logger.warning(
                    "serial subscriber %r failed on event %s",
                    callback, event.event_type, exc_info=True,
                )
                continue
            if result is None or result is False:
                continue
            return result
        return None

    async def replay(
        self, conv_id: str, since_seq: int = 0
    ) -> AsyncGenerator[StepEvent, None]:
        """从 StateStore 重放历史事件。用于进程重启后续接。"""
        events = await self._store.get_events(conv_id, since_seq=since_seq)
        for event in events:
            yield event
