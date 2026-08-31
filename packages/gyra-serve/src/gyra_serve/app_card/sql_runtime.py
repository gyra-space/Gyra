"""应用卡片 SQL 运行时防护: 有界并发排队 + 结果缓存 + 统一参数读取.

集中解决应用卡片取数把服务拖死的问题:
- 专用 ThreadPoolExecutor, 与全局 to_thread 池隔离, 池内只跑纯同步 SQL 执行,
  choke point 放在 async 调用层, 避免池内任务再等内层槽位造成嵌套饿死;
- Semaphore(并发数+排队数) 限制任务总量, 排队等待超时抛 AppCardBusyError 快速失败;
- TTL+LRU 结果缓存, 短时间重复打开卡片直接命中缓存, 不再重复打数据库.
"""

import asyncio
import functools
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class QueryRuntimeSettings:
    """取数防护参数, 默认值与 ServeConfig 保持一致, 可被 configure() 覆盖."""

    query_timeout_seconds: int = 60
    query_max_workers: int = 8
    query_max_queue: int = 8
    query_queue_wait_seconds: float = 5.0
    max_result_rows: int = 100000
    result_cache_ttl_seconds: float = 30.0
    result_cache_max_entries: int = 256


_settings = QueryRuntimeSettings()
_pool: Optional[ThreadPoolExecutor] = None
_slots: Optional[asyncio.Semaphore] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_result_cache: Optional["TtlLruCache"] = None
_pool_lock = threading.Lock()


class AppCardBusyError(RuntimeError):
    """查询排队已满, 由调用方捕获后转为友好提示(快速失败, 不拖垮服务)."""


def is_timeout_error(e: BaseException) -> bool:
    """识别各数据库的超时报错文案(MySQL 3024 的文案不含 timeout 字样)."""
    msg = str(e).lower()
    return any(
        kw in msg
        for kw in (
            "timeout",
            "timed out",
            "max_execution_time",
            "execution time exceeded",
        )
    )


def _int_cfg(config: Any, name: str, default: int) -> int:
    try:
        value = getattr(config, name, default)
        return default if value is None else int(value)
    except (TypeError, ValueError):
        return default


def _float_cfg(config: Any, name: str, default: float) -> float:
    try:
        value = getattr(config, name, default)
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def configure(config: Any) -> None:
    """Serve.init_app 时把 ServeConfig 的取数防护参数同步到运行时."""
    global _settings, _pool, _slots, _loop, _result_cache
    with _pool_lock:
        _settings = QueryRuntimeSettings(
            query_timeout_seconds=max(0, _int_cfg(config, "query_timeout_seconds", 60)),
            query_max_workers=max(1, _int_cfg(config, "query_max_workers", 8)),
            query_max_queue=max(0, _int_cfg(config, "query_max_queue", 8)),
            query_queue_wait_seconds=max(
                0.0, _float_cfg(config, "query_queue_wait_seconds", 5.0)
            ),
            max_result_rows=max(1, _int_cfg(config, "max_result_rows", 100000)),
            result_cache_ttl_seconds=max(
                0.0, _float_cfg(config, "result_cache_ttl_seconds", 30.0)
            ),
            result_cache_max_entries=max(
                1, _int_cfg(config, "result_cache_max_entries", 256)
            ),
        )
        _pool = None
        _slots = None
        _loop = None
        _result_cache = None


def get_query_settings() -> QueryRuntimeSettings:
    return _settings


class TtlLruCache:
    """线程安全的 TTL + LRU 缓存; ttl<=0 表示禁用(由 get_result_cache 返回 None)."""

    def __init__(self, ttl_seconds: float, max_entries: int):
        self._ttl = float(ttl_seconds)
        self._max = int(max_entries)
        self._data: "OrderedDict[Any, Any]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def put(self, key: Any, value: Any) -> None:
        now = time.monotonic()
        with self._lock:
            self._data[key] = (now + self._ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)


def get_result_cache() -> Optional[TtlLruCache]:
    """获取结果缓存单例; ttl<=0 时返回 None 表示缓存关闭."""
    global _result_cache
    settings = get_query_settings()
    if settings.result_cache_ttl_seconds <= 0:
        return None
    with _pool_lock:
        if _result_cache is None:
            _result_cache = TtlLruCache(
                settings.result_cache_ttl_seconds,
                settings.result_cache_max_entries,
            )
        return _result_cache


def _get_pool() -> tuple:
    """懒创建专用线程池与并发信号量; 事件循环更换时重建信号量."""
    global _pool, _slots, _loop
    settings = get_query_settings()
    running_loop = asyncio.get_running_loop()
    with _pool_lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(
                max_workers=settings.query_max_workers,
                thread_name_prefix="appcard-sql",
            )
        if _slots is None or _loop is not running_loop:
            _slots = asyncio.Semaphore(
                settings.query_max_workers + settings.query_max_queue
            )
            _loop = running_loop
        return _pool, _slots


async def run_bounded(fn: Callable, /, *args: Any, **kwargs: Any) -> Any:
    """在有界专用线程池中执行同步函数; 排队满且等待超时则快速失败.

    注意: 只能把纯同步、不再二次入池的函数交给它, 否则会嵌套占线程导致饿死.
    """
    executor, slots = _get_pool()
    settings = get_query_settings()
    if settings.query_queue_wait_seconds <= 0:
        if slots.locked():
            raise AppCardBusyError(
                f"数据查询并发已满(运行 {settings.query_max_workers}), 请稍后重试"
            )
        await slots.acquire()
    else:
        try:
            await asyncio.wait_for(
                slots.acquire(), timeout=settings.query_queue_wait_seconds
            )
        except asyncio.TimeoutError:
            raise AppCardBusyError(
                f"数据查询排队已满(运行 {settings.query_max_workers}"
                f" + 排队 {settings.query_max_queue}), 请稍后重试"
            ) from None
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            executor, functools.partial(fn, *args, **kwargs)
        )
    finally:
        slots.release()


async def run_bounded_disconnect_aware(
    http_request: Any, fn: Callable, /, *args: Any, **kwargs: Any
) -> Any:
    """run_bounded 的客户端断连感知版本.

    轮询 http_request.is_disconnected(): 客户端关闭页面/断网后, 协程侧
    立即释放信号量槽位并返回, 不再干等池内同步 SQL 跑完才把槽位让出来,
    避免狂刷页面时槽位被"孤儿请求"长期占用(池内 SQL 本身仍在跑,
    由语句级超时/行数熔断兜底, 无法从外部强杀线程)。
    """
    query_task = asyncio.ensure_future(run_bounded(fn, *args, **kwargs))

    async def _watch_disconnect() -> None:
        while not query_task.done():
            try:
                if await http_request.is_disconnected():
                    return
            except Exception:  # noqa: BLE001
                return
            await asyncio.sleep(0.5)

    watcher = asyncio.ensure_future(_watch_disconnect())
    try:
        done, _ = await asyncio.wait(
            {query_task, watcher}, return_when=asyncio.FIRST_COMPLETED
        )
        if query_task in done:
            return query_task.result()
        # 客户端已断开:取消等待(槽位随 run_bounded 的 finally 释放),
        # 池内 SQL 由超时/熔断兜底终止。
        query_task.cancel()
        raise AppCardBusyError("客户端已断开连接, 查询已放弃")
    finally:
        watcher.cancel()
        try:
            await watcher
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
