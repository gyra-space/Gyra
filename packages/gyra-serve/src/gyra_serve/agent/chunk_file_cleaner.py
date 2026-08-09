"""chunk 文件保留期清理守护。

`aggregation_chat` 流式期间把 vis chunk 追加到
``pilot/data/chat_chunk_file/_chat_file_{agent_conv_id}.jsonl``（纯调试 dump：
``query_chat`` 刷新恢复全走 DB，无任何后端接口读取这些文件，仅前端
ChunkReplay 调试页手动上传使用）。长期运行下文件无限累积，这里做保留期清理：
启动时扫一次 + 每日周期扫，删除 mtime 早于 ``RETENTION_DAYS`` 的文件。

best-effort：任何失败只记日志，不影响服务。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

RETENTION_DAYS = 7
SWEEP_INTERVAL_SECONDS = 24 * 3600


class ChunkFileCleaner:
    """按 mtime 清理过期 chunk 文件。

    Usage:
        cleaner = ChunkFileCleaner()
        asyncio.create_task(cleaner.run_forever())
    """

    def __init__(self, chunk_dir: Optional[str] = None):
        if chunk_dir is None:
            from gyra.configs.model_config import DATA_DIR

            chunk_dir = os.path.join(DATA_DIR, "chat_chunk_file")
        self._chunk_dir = chunk_dir

    def sweep_once(self) -> int:
        """删除一轮过期 chunk 文件，返回删除数。"""
        if not os.path.isdir(self._chunk_dir):
            return 0
        cutoff = time.time() - RETENTION_DAYS * 86400
        removed = 0
        for name in os.listdir(self._chunk_dir):
            if not (name.startswith("_chat_file_") and name.endswith(".jsonl")):
                continue
            path = os.path.join(self._chunk_dir, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    removed += 1
            except OSError as e:
                logger.debug(f"[chunk-cleaner] remove {path} failed: {e}")
        if removed:
            logger.info(
                f"[chunk-cleaner] removed {removed} expired chunk files "
                f"(>{RETENTION_DAYS}d) from {self._chunk_dir}"
            )
        return removed

    async def run_forever(self) -> None:
        """启动时先扫一次，之后每日周期扫。宽 except 保活。"""
        while True:
            try:
                self.sweep_once()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[chunk-cleaner] sweep failed: {e}")
            await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
