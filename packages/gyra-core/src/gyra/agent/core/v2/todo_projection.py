"""Todo 状态投影——从 V2 事件日志读取最新 todo 列表（DSH todos projection 等价物）。

对齐 DSH tool-todo 设计：
  - **Source of truth** = `todo/write` 事件日志（last-write-wins on replay）。
  - **UI 消费** = 通过本 projector 的 ``project_current(state_store, conv_id)``
    取最新 todo 列表。
  - **LLM 消费** = 不通过这里。LLM 通过自己上一轮 tool_call 参数 + 工具结果
    回显自然看到当前 todo 状态（避免 system prompt 频繁变化影响 KV-cache）。

设计选择：
  - 不在 ProjectorRegistry 里挂 todo/write 的 projector（事件 surface=False，
    EventRegistry.validate_logged_visibility 也不会拦它），保持 DSH 的
    "todo 状态不进入 LLM 上下文" 不变量；
  - 本模块提供**显式** API 给 UI / 回放 / 对话重水合等场景，避免误用污染 LLM 通道。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def project_current_todo(
    state_store: Any,
    conv_id: str,
) -> Optional[List[Dict[str, Any]]]:
    """从 V2 事件日志读取最新 todo 列表（last-write-wins）。

    Args:
        state_store: V2 StateStore（实现 ``get_events(conv_id)`` 异步方法）。
        conv_id: 会话 ID。

    Returns:
        最新一次 ``todo/write`` 事件的 ``todos`` payload；
        没有 todo 写入时返回 ``None``（区别于"空列表"——空列表也是合法状态）。
    """
    try:
        events = await state_store.get_events(conv_id)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"project_current_todo get_events failed: {e}")
        return None
    if not events:
        return None

    # 沿 seq 顺序扫描，最后一次 todo/write 即为最新（last-write-wins）
    latest: Optional[List[Dict[str, Any]]] = None
    for ev in events:
        if ev.event_type == "todo/write":
            payload = ev.output or {}
            todos = payload.get("todos")
            if isinstance(todos, list):
                latest = todos
    return latest
