"""缓冲式轨迹采集器——执行过程中收集,批量写入,不阻塞 agent。

实现 TraceCollector 协议:
- record_skill/record_gate/record_skip 只写内存缓冲,执行零开销
- 缓冲超阈值(100 条)自动 flush 一次中间状态(增量 write)
- finalize 时 flush 最终轨迹并发布 TRACE_FINALIZED 事件,触发演化引擎分析
"""
import asyncio
import logging
import uuid
from typing import Optional

from gyra.distributed import (
    AssetEvent,
    AssetEventBus,
    AssetEventType,
    ExecutionTrace,
    GateTriggerRecord,
    SkillCallRecord,
    TraceCollector,
    TraceContext,
    TraceSink,
)

logger = logging.getLogger(__name__)


class BufferedTraceCollector(TraceCollector):
    """TraceCollector 实现——本地缓冲 + 批量发送。

    构造时接收 TraceContext(标识本次执行)与 TraceSink(落盘端)。
    可选接收 AssetEventBus, finalize 时发布 TRACE_FINALIZED 事件,
    供 TraceToEvolutionHandler 累积触发分析。
    """

    # 缓冲阈值: skill_calls + gates 累计超过此值则增量 flush 一次
    FLUSH_THRESHOLD = 100

    def __init__(
        self,
        context: TraceContext,
        sink: TraceSink,
        event_bus: Optional[AssetEventBus] = None,
    ):
        self._context = context
        self._sink = sink
        self._event_bus = event_bus
        self._trace = ExecutionTrace(
            trace_id=str(uuid.uuid4()),
            context=context,
        )
        self._lock = asyncio.Lock()
        self._finalized = False

    @property
    def trace_id(self) -> str:
        return self._trace.trace_id

    @property
    def trace(self) -> ExecutionTrace:
        return self._trace

    async def record_skill(self, record: SkillCallRecord) -> None:
        """记录 skill 调用——缓冲,超阈值自动增量 flush。"""
        async with self._lock:
            if self._finalized:
                return
            self._trace.skill_calls.append(record)
            if len(self._trace.skill_calls) >= self.FLUSH_THRESHOLD:
                await self._flush(final=False)

    async def record_gate(self, record: GateTriggerRecord) -> None:
        """记录 gate 触发(审批/教练)——缓冲。"""
        async with self._lock:
            if self._finalized:
                return
            self._trace.gates.append(record)
            if (
                len(self._trace.skill_calls) + len(self._trace.gates)
                >= self.FLUSH_THRESHOLD
            ):
                await self._flush(final=False)

    async def record_skip(self, step_name: str, reason: str) -> None:
        """记录步骤跳过——缓冲。"""
        async with self._lock:
            if self._finalized:
                return
            self._trace.skips.append((step_name, reason))

    async def finalize(self, status: str, failure_reason: str = "") -> str:
        """收尾: flush 最终轨迹,发布 TRACE_FINALIZED 事件,返回 trace_id。

        status: success/failed/partial/aborted
        """
        async with self._lock:
            if self._finalized:
                return self._trace.trace_id
            self._trace.status = status
            self._trace.failure_reason = failure_reason
            from datetime import datetime
            self._trace.finalized_at = datetime.now()
            await self._flush(final=True)
            self._finalized = True
            await self._publish_finalized()
            return self._trace.trace_id

    async def _flush(self, final: bool) -> None:
        """将当前缓冲轨迹写入 Sink——幂等(基于 trace_id)。"""
        idempotency_key = f"trace-{self._trace.trace_id}"
        try:
            await self._sink.write(
                self._trace, idempotency_key, final=final
            )
        except Exception as e:
            # 采集器失败不阻断 agent 主流程
            logger.warning(
                f"[trace-collector] flush failed trace={self._trace.trace_id} "
                f"final={final}: {e}"
            )

    async def _publish_finalized(self) -> None:
        """发布 TRACE_FINALIZED 事件——演化引擎据此触发分析。"""
        if self._event_bus is None:
            return
        try:
            event = AssetEvent(
                event_type=AssetEventType.TRACE_FINALIZED,
                asset_id=f"playbook:{self._context.playbook_id}",
                workspace_id=self._context.workspace_id,
                actor=self._context.agent_id or "system",
                payload={
                    "trace_id": self._trace.trace_id,
                    "playbook_id": self._context.playbook_id,
                    "playbook_version_id": self._context.playbook_version_id,
                    "task_id": self._context.task_id,
                    "status": self._trace.status,
                    "skill_call_count": len(self._trace.skill_calls),
                    "gate_count": len(self._trace.gates),
                    "skip_count": len(self._trace.skips),
                },
                idempotency_key=f"trace-finalized-{self._trace.trace_id}",
            )
            await self._event_bus.publish(
                event, partition_key=str(self._context.workspace_id)
            )
        except Exception as e:
            logger.warning(
                f"[trace-collector] publish TRACE_FINALIZED failed "
                f"trace={self._trace.trace_id}: {e}"
            )
