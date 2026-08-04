"""Agent 成长模型事件处理器 —— 反哺飞轮。

监听三链事件,驱动 agent 评分变化:
- ASSET_ATTESTED    → 产出 agent 信用 attest_count +1
- ASSET_COACHED     → 产出 agent 惩罚 coach_count +1
- TRACE_FINALIZED   → 重算执行统计(执行量/成功率)
- EVOLUTION_APPLIED → 主导 agent 加分 evolution_count +1

所有处理器必须幂等(基于 event.idempotency_key 去重 + service 方法本身幂等)。
事件总线单机实现按消费组 ack 去重;生产环境切换 Kafka 时消费者自行幂等。
"""
from __future__ import annotations

import logging
from typing import Optional

from gyra.distributed import AssetEvent, AssetEventType, EventHandler

from .service import AgentMaturityService

logger = logging.getLogger(__name__)


def _resolve_agent_and_workspace(
    event: AssetEvent, *payload_keys: str
) -> tuple[Optional[str], Optional[int]]:
    """从事件 actor + payload 解析 agent_id 与 workspace_id。

    payload_keys: 候选 payload 字段(按优先级),取首个非空。
    """
    payload = event.payload or {}
    agent_id: Optional[str] = None
    for key in payload_keys:
        v = payload.get(key)
        if v:
            agent_id = str(v)
            break
    # 兜底: actor(但 system 兜底视为无 agent)
    if not agent_id and event.actor and event.actor != "system":
        agent_id = event.actor
    workspace_id = event.workspace_id
    if workspace_id is None or workspace_id == 0:
        ws = payload.get("workspace_id")
        if ws:
            try:
                workspace_id = int(ws)
            except (TypeError, ValueError):
                workspace_id = None
    return agent_id, workspace_id


class AssetAttestedToMaturityHandler(EventHandler):
    """监听 ASSET_ATTESTED → 给产出 agent 的 attest_count 信用 +1。

    消费组: agent_maturity_attest(同组负载均衡,避免重复加分)。
    """
    consumer_group = "agent_maturity_attest"

    def __init__(self, service: AgentMaturityService):
        self._service = service

    async def handle(self, event: AssetEvent) -> None:
        agent_id, workspace_id = _resolve_agent_and_workspace(
            event, "source_agent_id", "agent_id"
        )
        if not agent_id or not workspace_id:
            return
        try:
            self._service.increment_attest_count(
                agent_id=agent_id, workspace_id=workspace_id, delta=1
            )
        except Exception as e:  # noqa: BLE001 - 处理器失败不影响主流程
            logger.warning(
                f"[agent_maturity] attest credit failed agent={agent_id}: {e}"
            )


class AssetCoachedToMaturityHandler(EventHandler):
    """监听 ASSET_COACHED → 给产出 agent 的 coach_count 惩罚 +1。

    消费组: agent_maturity_coach。
    """
    consumer_group = "agent_maturity_coach"

    def __init__(self, service: AgentMaturityService):
        self._service = service

    async def handle(self, event: AssetEvent) -> None:
        agent_id, workspace_id = _resolve_agent_and_workspace(
            event, "source_agent_id", "agent_id"
        )
        if not agent_id or not workspace_id:
            return
        severity = (event.payload or {}).get("severity", "minor")
        try:
            self._service.apply_coach_penalty(
                agent_id=agent_id,
                workspace_id=workspace_id,
                severity=severity,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[agent_maturity] coach penalty failed agent={agent_id}: {e}"
            )


class TraceFinalizedToMaturityHandler(EventHandler):
    """监听 TRACE_FINALIZED → 重算执行统计(执行量/成功率/失败率)。

    消费组: agent_maturity_trace。
    """
    consumer_group = "agent_maturity_trace"

    def __init__(self, service: AgentMaturityService):
        self._service = service

    async def handle(self, event: AssetEvent) -> None:
        # TRACE_FINALIZED 的 actor 即执行 agent(collector._publish_finalized)
        agent_id, workspace_id = _resolve_agent_and_workspace(event)
        if not agent_id or not workspace_id:
            return
        try:
            self._service.on_trace_finalized(
                agent_id=agent_id, workspace_id=workspace_id
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[agent_maturity] trace recalc failed agent={agent_id}: {e}"
            )


class EvolutionAppliedToMaturityHandler(EventHandler):
    """监听 EVOLUTION_APPLIED → 给主导的 expert 加分 evolution_count +1。

    消费组: agent_maturity_evolution。

    payload 可能不含 agent_id(现有 engine 只发 reviewed_by),按
    proposed_by / reviewed_by / actor 顺序解析,system 视为无 agent。
    """
    consumer_group = "agent_maturity_evolution"

    def __init__(self, service: AgentMaturityService):
        self._service = service

    async def handle(self, event: AssetEvent) -> None:
        agent_id, workspace_id = _resolve_agent_and_workspace(
            event, "proposed_by", "agent_id", "reviewed_by"
        )
        if not agent_id or not workspace_id:
            return
        try:
            self._service.increment_evolution_count(
                agent_id=agent_id, workspace_id=workspace_id, delta=1
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[agent_maturity] evolution credit failed agent={agent_id}: {e}"
            )


# --------------------------------------------------------------------------- #
# 注册器
# --------------------------------------------------------------------------- #
def register_agent_maturity_handlers(service: AgentMaturityService) -> None:
    """订阅 4 个事件处理器到 service 的事件总线。

    在 AgentMaturityService.init_app 中调用(幂等: 仅注册一次)。
    """
    bus = service.event_bus
    bus.subscribe(
        AssetEventType.ASSET_ATTESTED,
        AssetAttestedToMaturityHandler(service),
        AssetAttestedToMaturityHandler.consumer_group,
    )
    bus.subscribe(
        AssetEventType.ASSET_COACHED,
        AssetCoachedToMaturityHandler(service),
        AssetCoachedToMaturityHandler.consumer_group,
    )
    bus.subscribe(
        AssetEventType.TRACE_FINALIZED,
        TraceFinalizedToMaturityHandler(service),
        TraceFinalizedToMaturityHandler.consumer_group,
    )
    bus.subscribe(
        AssetEventType.EVOLUTION_APPLIED,
        EvolutionAppliedToMaturityHandler(service),
        EvolutionAppliedToMaturityHandler.consumer_group,
    )


__all__ = [
    "AssetAttestedToMaturityHandler",
    "AssetCoachedToMaturityHandler",
    "TraceFinalizedToMaturityHandler",
    "EvolutionAppliedToMaturityHandler",
    "register_agent_maturity_handlers",
]
