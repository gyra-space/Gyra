"""事件日志投影（对齐 DeepSeek Harness 的 ``deriveMessages``）。

V2 事实源 = StateStore 里的 StepEvent（append-only 日志）；LLM 上下文中的
工具执行历史由本模块**从日志投影派生**，替代 V2Agent 手写双写
（``_v2_tool_rounds`` 手工拼接 + 回读 gpts_memory），消除 DB 读回竞态与
手工状态维护——模型看到的事实永远与事件日志一致（model-visible = logged）。

投影规则：
  - 按 ``seq`` 顺序遍历某 conv 的全部 StepEvent；
  - ``ACTING / tool_call`` 入队（记录工具名与参数）；
  - ``OBSERVING / tool_result`` 与最早未配对的 tool_call 配对，输出
    ``assistant``（tool_calls 声明）+ ``tool``（执行结果）消息对；
  - 未配对的 tool_call（当前 step 正在 thinking，尚未出结果）**跳过**，
    避免把未完成调用注入模型上下文。
"""
from __future__ import annotations

import json
from typing import List, Optional

from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


def _dump_args(args) -> str:
    try:
        return json.dumps(args or {}, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return "{}"


async def project_tool_history(
    store,
    conv_id: str,
    *,
    include_unfinished: bool = False,
) -> List[dict]:
    """从事件日志投影某会话的工具执行历史（LLM 消息格式）。

    Args:
        store: StateStore（含 async ``get_events(conv_id)``）。
        conv_id: 会话 ID。
        include_unfinished: 是否包含尚未配对的 tool_call（默认 False）。

    Returns:
        List[dict]：``assistant``（tool_calls）+ ``tool``（结果）消息对列表；
        无历史时返回空列表。
    """
    events = await store.get_events(conv_id)
    return _project_events(events, include_unfinished=include_unfinished)


def _project_events(
    events: List[StepEvent],
    *,
    include_unfinished: bool = False,
) -> List[dict]:
    msgs: List[dict] = []
    pending: List[tuple] = []  # (tool_call_id, tool_name, args)

    for ev in events:
        if ev.event_type == "tool_call" and ev.state is StepState.ACTING:
            inp = ev.input or {}
            name = inp.get("tool", "")
            args = inp.get("input", {})
            if not name:
                continue
            # 确定性 tool_call_id：由 (step_id, seq) 派生，日志可重放
            call_id = f"call_{ev.step_id}_{ev.seq}"
            pending.append((call_id, name, args))
        elif ev.event_type == "tool_result" and ev.state is StepState.OBSERVING:
            if not pending:
                continue
            call_id, name, args = pending.pop(0)
            out = ev.output or {}
            # 支持子 agent 结果（handle.result.answer）作为 tool 消息内容
            content = str(
                out.get("content")
                or (out.get("result") or {}).get("answer")
                or out.get("error")
                or "[空结果]"
            )
            success = bool(out.get("is_exe_success", True))
            msgs.append(_assistant_tool_call_msg(call_id, name, args))
            msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": content or "[空结果]",
                }
            )
        # 其余事件（llm_token / step_done / interaction_request 等）不影响投影

    if include_unfinished:
        for call_id, name, args in pending:
            msgs.append(_assistant_tool_call_msg(call_id, name, args))
    return msgs


def _assistant_tool_call_msg(call_id: str, name: str, args) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": _dump_args(args)},
            }
        ],
    }


class ToolHistoryProjector:
    """带按会话缓存的投影器（多次 thinking 调用避免重复全量扫描）。

    引擎每轮 thinking 前调用 :meth:`get` 获取最新工具历史；事件日志是
    append-only，缓存按 ``(conv_id, 已见 max_seq)`` 增量更新。
    """

    def __init__(self, store):
        self._store = store
        # conv_id -> (projected_msgs, consumed_seq)
        self._cache: dict = {}

    async def get(self, conv_id: str) -> List[dict]:
        """返回截至当前日志的最新工具历史（增量投影）。"""
        events = await self._store.get_events(conv_id)
        seen_seq, cached = self._cache.get(conv_id, (0, []))
        fresh = [e for e in events if e.seq > seen_seq]
        # 增量投影只处理新增事件；缓存保留已配对的完整消息
        if fresh:
            new_msgs = _project_events(fresh)
            # 若增量起点是从 pending 中断处开始，配对可能跨批次丢失；
            # 为保证正确性，小规模直接全量重投影（历史事件量级可控）。
            cached = _project_events(events)
            self._cache[conv_id] = (events[-1].seq if events else seen_seq, cached)
        return cached
