"""共享事件总线组件 —— 让飞轮各模块(资产成熟度/Agent成长/Trace/演化/评测)
通过同一条 AssetEventBus 联动,避免各服务各自构造 LocalEventBus 造成事件孤岛。

装配方式:
    SystemApp 启动时,在任何飞轮服务 register 之前,先 register 本组件:

        from gyra.distributed import SharedEventBusComponent
        system_app.register(SharedEventBusComponent)

    随后各飞轮服务在 ``init_app`` 中通过 ``get_shared_event_bus(system_app)``
    获取同一条 bus;若组件未注册(例如单元测试场景),则降级为新建 LocalEventBus,
    保证向后兼容。

生产环境可替换为 Redis/Kafka 后端的 AssetEventBus 实现,协议不变。
"""
from __future__ import annotations

import logging
from typing import Optional

from gyra.component import BaseComponent, SystemApp

from .local import LocalEventBus
from .protocols import AssetEventBus

logger = logging.getLogger(__name__)

SHARED_EVENT_BUS_COMPONENT_NAME = "gyra_shared_event_bus"


class SharedEventBusComponent(BaseComponent):
    """共享事件总线组件 —— 全进程单例 AssetEventBus。

    所有飞轮服务(AssetMaturity / AgentMaturity / TraceCollector /
    PlaybookEvolutionEngine / EvaluationToMaturityHandler)应通过
    ``get_shared_event_bus`` 获取同一实例,确保事件 publish/subscribe 走同一条 bus。
    """

    name = SHARED_EVENT_BUS_COMPONENT_NAME

    def __init__(self, system_app: Optional[SystemApp] = None, bus: Optional[AssetEventBus] = None):
        # 先占位,init_app 中正式构造,便于 SystemApp.register 标准流程
        self._bus: Optional[AssetEventBus] = bus
        super().__init__(system_app)

    def init_app(self, system_app: SystemApp) -> None:
        if self._bus is None:
            self._bus = LocalEventBus()
        logger.info(
            f"[shared-bus] SharedEventBusComponent initialized: {type(self._bus).__name__}"
        )

    @property
    def bus(self) -> AssetEventBus:
        if self._bus is None:
            self._bus = LocalEventBus()
        return self._bus


def get_shared_event_bus(system_app: Optional[SystemApp]) -> AssetEventBus:
    """从 SystemApp 获取共享事件总线;未注册则降级为新建 LocalEventBus。

    向后兼容: 单元测试或未装配 SharedEventBusComponent 的场景下,
    返回一个独立的 LocalEventBus(不报错,但事件不跨服务联动)。
    """
    if system_app is None:
        return LocalEventBus()
    try:
        component = system_app.get_component(
            SHARED_EVENT_BUS_COMPONENT_NAME,
            SharedEventBusComponent,
            default_component=None,
        )
        if component is not None:
            return component.bus
    except Exception as e:  # noqa: BLE001 - 装配缺失不应阻断主流程
        logger.warning(
            f"[shared-bus] get SharedEventBusComponent failed, fallback to "
            f"LocalEventBus: {e}"
        )
    return LocalEventBus()


__all__ = [
    "SHARED_EVENT_BUS_COMPONENT_NAME",
    "SharedEventBusComponent",
    "get_shared_event_bus",
]
