"""CompressionPersistenceAdapter 的生产实现 -- 包装 gpts_cold_segments DAO。

放在 react_master_agent 层（而非 context_engine 内），因为它依赖 gyra_serve 的
DAO；context_engine 保持对存储无依赖、可纯测。DAO 不可用时静默降级
（load 返回 None / save no-op），由 ContextEngine 的内存兜底，绝不阻塞主流程。
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from .context_engine.compression import CompressionSegment

logger = logging.getLogger(__name__)


class DbCompressionPersistenceAdapter:
    """基于 gpts_cold_segments 表的压缩段持久化。"""

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None):
        self._executor = executor
        self._dao = None
        self._dao_init_failed = False

    def _get_dao(self):
        if self._dao is not None or self._dao_init_failed:
            return self._dao
        try:
            from gyra_serve.agent.db.gpts_cold_segment_db import GptsColdSegmentDao

            self._dao = GptsColdSegmentDao()
        except Exception as e:  # gyra_serve 不可用 -> 降级
            logger.warning(
                "[DbCompressionPersistence] DAO 不可用，压缩段降级为内存：%s", e
            )
            self._dao_init_failed = True
        return self._dao

    async def append_segment(
        self, session_id: str, conv_id: str, segment: CompressionSegment
    ) -> Optional[int]:
        dao = self._get_dao()
        if dao is None:
            return None
        try:
            if hasattr(dao, "append_segment_async"):
                return await dao.append_segment_async(
                    session_id=session_id,
                    conv_id=conv_id,
                    seq=segment.seq,
                    summary=segment.summary,
                    source_message_ids=segment.source_message_ids,
                    boundary_message_id=segment.boundary_message_id,
                    prev_segment_id=segment.prev_segment_id,
                    original_tokens=segment.original_tokens,
                    compressed_tokens=segment.compressed_tokens,
                    degraded=segment.degraded,
                )
            return await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: dao.append_segment(
                    session_id,
                    conv_id,
                    segment.seq,
                    segment.summary,
                    segment.source_message_ids,
                    segment.boundary_message_id,
                    segment.prev_segment_id,
                    segment.original_tokens,
                    segment.compressed_tokens,
                    segment.degraded,
                ),
            )
        except Exception as e:
            logger.warning("[DbCompressionPersistence] append 失败：%s", e)
            return None

    async def get_latest_by_session(self, session_id: str) -> Optional[dict]:
        dao = self._get_dao()
        if dao is None:
            return None
        try:
            if hasattr(dao, "get_latest_by_session_async"):
                return await dao.get_latest_by_session_async(session_id)
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, dao.get_latest_by_session, session_id
            )
        except Exception as e:
            logger.warning("[DbCompressionPersistence] get_latest 失败：%s", e)
            return None

    async def get_all_by_session(self, session_id: str) -> List[dict]:
        dao = self._get_dao()
        if dao is None:
            return []
        try:
            if hasattr(dao, "get_all_by_session_async"):
                return await dao.get_all_by_session_async(session_id)
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, dao.get_all_by_session, session_id
            )
        except Exception as e:
            logger.warning("[DbCompressionPersistence] get_all 失败：%s", e)
            return []
