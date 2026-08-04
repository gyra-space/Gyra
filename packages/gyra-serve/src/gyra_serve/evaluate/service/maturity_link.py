"""评测与Agent成长联动 —— P1任务8。

职责:
- 评测完成后,将分数写入AgentMaturityModel
- 评测结果影响agent晋升评分
- 低分评测触发coach负样本

联动方式:
- 评测服务发布EVALUATION_COMPLETED事件
- EvaluationToMaturityHandler消费,更新agent评分
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    EventHandler,
    LocalEventBus,
)

logger = logging.getLogger(__name__)


# 扩展事件类型: 评测完成（复用AssetEvent结构,asset_id=agent_id）
EVALUATION_COMPLETED_EVENT = "evaluation_completed"


class EvaluationToMaturityHandler(EventHandler):
    """监听评测完成事件,更新agent成长评分

    幂等: 基于event.idempotency_key
    联动:
    - 评测分数 → AgentMaturityService评分维度
    - 低分评测 → 触发coach负样本
    """

    consumer_group = "evaluation-to-maturity"

    def __init__(self, system_app):
        self._system_app = system_app

    async def handle(self, event: AssetEvent) -> None:
        agent_id = event.payload.get("agent_id")
        if not agent_id:
            return

        workspace_id = event.workspace_id
        score = event.payload.get("score", 0.0)
        evaluation_type = event.payload.get("evaluation_type", "general")

        try:
            from gyra_serve.workspace.agent_maturity.service import (
                AgentMaturityService,
            )
            maturity_service: AgentMaturityService = self._system_app.get_component(
                "serve_agent_maturity_service", AgentMaturityService
            )

            # 更新评测评分维度
            maturity_service.set_score_field(
                agent_id=agent_id,
                workspace_id=workspace_id,
                field="evaluation_score",
                value=score,
            )

            # 低分触发coach负样本
            if score < 0.4:
                maturity_service.apply_coach_penalty(
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    severity="major",
                )
                logger.info(
                    f"[eval-maturity] agent {agent_id} low score {score}, "
                    f"applied coach penalty"
                )
            else:
                logger.info(
                    f"[eval-maturity] agent {agent_id} score {score} recorded"
                )

        except Exception as e:
            logger.warning(
                f"[eval-maturity] failed to update maturity for agent {agent_id}: {e}"
            )


def publish_evaluation_completed(
    event_bus: AssetEventBus,
    agent_id: str,
    workspace_id: int,
    score: float,
    evaluation_type: str = "general",
    evaluator: str = "system",
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """发布评测完成事件（供评测服务调用）

    评测服务在run_evaluation完成后调用此函数,触发成长联动。
    """
    import asyncio
    event = AssetEvent(
        event_type=AssetEventType.ASSET_REVIEWED,  # 复用REVIEWED类型
        asset_id=f"agent:{agent_id}",
        workspace_id=workspace_id,
        actor=evaluator,
        payload={
            "agent_id": agent_id,
            "score": score,
            "evaluation_type": evaluation_type,
            "details": details or {},
            "event_subtype": EVALUATION_COMPLETED_EVENT,
        },
        idempotency_key=f"eval-{agent_id}-{evaluation_type}-{workspace_id}",
    )
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                event_bus.publish(event, partition_key=str(workspace_id))
            )
        else:
            loop.run_until_complete(
                event_bus.publish(event, partition_key=str(workspace_id))
            )
    except RuntimeError:
        # 无事件循环,创建新的
        asyncio.run(event_bus.publish(event, partition_key=str(workspace_id)))

    return event.event_id
