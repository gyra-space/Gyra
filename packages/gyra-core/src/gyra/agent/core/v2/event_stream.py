"""EventStream——AsyncGenerator + 持久化 + 订阅。

每个 yield 前先持久化到 StateStore（durability before visibility）。
进程崩溃后通过 replay() 从 StateStore 重放历史事件。

P0 插件化扩展点：subscribe() 允许外部插件按 event_type 订阅 StepEvent。
订阅者在事件持久化之后被同步通知（对插件同样保证 durability-before-visibility），
按注册顺序依次回调；订阅者异常只记录日志，不影响主事件流。
"""
from __future__ import annotations
import inspect
import logging
from typing import (
    AsyncGenerator, Awaitable, Callable, Iterable, List, Optional, Tuple, Union,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.state_store import StateStore

logger = logging.getLogger(__name__)

# 订阅回调：同步或异步均可，接收持久化后的 StepEvent
StepEventCallback = Callable[[StepEvent], Union[None, Awaitable[None]]]


class EventStream:
    """事件流：持久化 + 重放 + 订阅。不直接 yield，由 run_step 的 async generator 驱动。"""

    def __init__(self, state_store: StateStore):
        self._store = state_store
        # (event_types 过滤集, 回调)；event_types=None 表示订阅全部事件
        self._subscribers: List[Tuple[Optional[frozenset], StepEventCallback]] = []

    def subscribe(
        self,
        callback: StepEventCallback,
        event_types: Optional[Iterable[str]] = None,
    ) -> Callable[[], None]:
        """订阅 StepEvent，返回 unsubscribe()。

        - event_types=None：订阅全部事件类型；否则只通知匹配的事件。
        - callback 可为同步函数或协程函数；按注册顺序、在事件持久化后依次回调。
        - 回调异常被捕获并记录日志，不会中断主事件流。
        """
        entry = (frozenset(event_types) if event_types else None, callback)
        self._subscribers.append(entry)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(entry)
            except ValueError:
                pass

        return unsubscribe

    async def emit(self, event: StepEvent) -> StepEvent:
        """持久化事件、通知订阅者后返回同一对象，供调用方 yield。"""
        await self._store.append_event(event)
        await self._store.set_step_state(
            event.step_id, event.conv_id, event.state, event.input
        )
        await self._notify(event)
        return event

    async def _notify(self, event: StepEvent) -> None:
        for event_types, callback in list(self._subscribers):
            if event_types is not None and event.event_type not in event_types:
                continue
            try:
                result = callback(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: BLE001
                logger.warning(
                    "EventStream subscriber %r failed on event %s",
                    callback, event.event_type, exc_info=True,
                )

    async def replay(
        self, conv_id: str, since_seq: int = 0
    ) -> AsyncGenerator[StepEvent, None]:
        """从 StateStore 重放历史事件。用于进程重启后续接。"""
        events = await self._store.get_events(conv_id, since_seq=since_seq)
        for event in events:
            yield event
