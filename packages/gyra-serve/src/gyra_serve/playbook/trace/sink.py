"""DB 轨迹写入端——将 ExecutionTrace 持久化到 PlaybookTraceEntity。

实现 TraceSink 协议: write/list_recent/list_by_workspace。
跨节点汇聚时,各 agent 进程通过此 Sink 写同一张表(trace_id 幂等)。
"""
import logging
from typing import List, Optional

from gyra.distributed import ExecutionTrace, TraceSink

from .models import PlaybookTraceDao

logger = logging.getLogger(__name__)


class DBTraceSink(TraceSink):
    """TraceSink 实现——写 DB,基于 trace_id 幂等。

    与 BufferedTraceCollector 配合: collector 在执行过程中缓冲,
    finalize 时调用 sink.write(trace, key, final=True) 落盘。
    """

    def __init__(self, dao: Optional[PlaybookTraceDao] = None):
        self._dao = dao or PlaybookTraceDao()

    @property
    def dao(self) -> PlaybookTraceDao:
        return self._dao

    async def write(
        self,
        trace: ExecutionTrace,
        idempotency_key: str,
        final: bool = False,
    ) -> None:
        """幂等写入轨迹——基于 trace_id 去重,支持增量 write(非 final)。"""
        try:
            self._dao.write(trace, idempotency_key, final=final)
        except Exception as e:
            # 轨迹写入失败不应阻断主流程,记录日志即可
            logger.warning(
                f"[db-trace-sink] write failed trace={trace.trace_id} "
                f"final={final}: {e}"
            )

    async def list_recent(
        self, playbook_id: int, limit: int = 20
    ) -> List[ExecutionTrace]:
        return self._dao.list_recent(playbook_id, limit)

    async def list_by_workspace(
        self, workspace_id: int, limit: int = 100
    ) -> List[ExecutionTrace]:
        return self._dao.list_by_workspace(workspace_id, limit)
