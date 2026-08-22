"""ProjectorRegistry——事件→LLM 消息投影器注册表。

替代 V2 ``event_projection._project_events`` 中的硬编码 if/elif 分支：
每种 surface 事件可注册独立 projector_fn，由 ProjectorRegistry 统一调度。

投影规则（与 DSH ``deriveMessages`` 一致）：
  1. 沿 ``seq`` 顺序遍历 StepEvent 日志；
  2. surface=True 事件 → 通过 projector_fn 派生 LLM 消息；
  3. surface=False 事件 → 跳过（仅影响渲染/审计，不入模型上下文）；
  4. tool_call (ACTING) / tool_result (OBSERVING) 配对后输出 assistant+tool 对；
  5. 配对失败的未完成 tool_call 默认跳过（``include_unfinished=True`` 时输出）。

**事件合并**（对齐 DSH replace shadow）：
  - 同一 surface_node_id 多个 surface 事件，按 surface_op 折叠
    （``append`` 串联文本 / ``replace`` 取最后一个 / ``prepend`` 反向串联）。
  - projector_fn 返回的 ``_surface_node_id`` / ``_surface_op`` 字段
    由本模块识别并执行合并。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Set

from gyra.agent.core.v2.event_registry import (
    EventRegistry,
    ProjectorFn,
    get_event_registry,
)
from gyra.agent.core.v2.step_event import StepEvent
from gyra.agent.core.v2.step_state import StepState


# ---------- 工具函数 ----------

def _dump_args(args: Any) -> str:
    try:
        return json.dumps(args or {}, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return "{}"


# ---------- 内置投影器 ----------

def project_assistant_tool_call(call_id: str, name: str, args: Any) -> dict:
    """``tool_call`` (ACTING) → assistant 消息（声明 tool_calls）。"""
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


def _tool_result_content(output: dict) -> str:
    """从 tool_result output 提取可读内容（content > 子 agent 答案 > error）。"""
    if output.get("content"):
        return str(output["content"])
    sub_answer = (output.get("result") or {}).get("answer")
    if sub_answer:
        return str(sub_answer)
    return str(output.get("error") or "[空结果]")


def project_tool_result(call_id: str, output: dict) -> dict:
    """``tool_result`` (OBSERVING) → tool 消息。"""
    content = _tool_result_content(output)
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": content or "[空结果]",
    }


def project_user_message(event: StepEvent) -> Optional[dict]:
    """``user/message`` → user 消息。"""
    text = (event.output or {}).get("text") or (event.input or {}).get("text")
    if text is None:
        return None
    return {"role": "user", "content": text}


def project_assistant_message(event: StepEvent) -> Optional[dict]:
    """``assistant/message`` → assistant 消息。"""
    text = (event.output or {}).get("text")
    if text is None:
        return None
    return {"role": "assistant", "content": text}


def project_compaction_summary(event: StepEvent) -> Optional[dict]:
    """``compaction/summary`` → system 消息（注入压缩历史摘要）。

    自动从 ``event.output._surface_node_id`` / ``_surface_op`` 提取 replace
    shadow 元信息——业务侧 emit 时声明 ``_surface_node_id="compaction"`` +
    ``_surface_op="replace"``，本投影器自动折叠被压缩的 user/assistant/tool 段。
    """
    text = (event.output or {}).get("summary")
    if not text:
        return None
    msg: Dict[str, Any] = {
        "role": "system",
        "content": f"[Compaction 摘要]\n{text}",
    }
    # 透传 replace_shadow 元信息
    out = event.output or {}
    if "_surface_node_id" in out:
        msg["_surface_node_id"] = out["_surface_node_id"]
    if "_surface_op" in out:
        msg["_surface_op"] = out["_surface_op"]
    return msg


def project_plan_step(event: StepEvent) -> Optional[dict]:
    """``plan/step`` → system 消息（plan 模式步骤状态）。

    自动从 ``event.output._surface_node_id`` / ``_surface_op`` 提取 replace
    shadow 元信息——业务侧只需在 emit 时声明 ``_surface_node_id="plan"`` +
    ``_surface_op="replace"``，本投影器自动折叠所有 plan/* 事件为单条消息。
    """
    text = (event.output or {}).get("text")
    if not text:
        return None
    msg: Dict[str, Any] = {
        "role": "system",
        "content": f"[Plan] {text}",
    }
    # 透传 replace_shadow 元信息（业务在 emit 时声明）
    out = event.output or {}
    if "_surface_node_id" in out:
        msg["_surface_node_id"] = out["_surface_node_id"]
    if "_surface_op" in out:
        msg["_surface_op"] = out["_surface_op"]
    return msg


# ---------- ProjectorRegistry ----------

class ProjectorRegistry:
    """投影器注册表（事件类型 → projector_fn）。"""

    def __init__(self, event_registry: Optional[EventRegistry] = None) -> None:
        self._event_registry = event_registry or get_event_registry()
        self._projectors: Dict[str, ProjectorFn] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """注册内置投影器，并把绑定写入 EventRegistry 让 model-visible 断言通过。"""
        defaults: Dict[str, ProjectorFn] = {
            "user/message": project_user_message,
            "assistant/message": project_assistant_message,
            "tool/result": self._project_tool_result_event,
            "compaction/summary": project_compaction_summary,
            "plan/start": project_plan_step,
            "plan/step": project_plan_step,
            "plan/finish": project_plan_step,
        }
        for name, fn in defaults.items():
            self.register(name, fn)

    def register(self, event_type: str, fn: ProjectorFn) -> None:
        """注册投影器（覆盖默认）。"""
        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type must be a non-empty string")
        self._projectors[event_type] = fn
        # 同步到 EventRegistry 以满足 surface → projector_fn 强校验
        info = self._event_registry.get(event_type)
        if info is not None:
            info.projector_fn = fn
        else:
            # 未在 EventRegistry 注册的事件类型：自动注册（默认 surface=True）
            self._event_registry.register(
                event_type, is_surface=True, projector_fn=fn,
            )

    def unregister(self, event_type: str) -> None:
        self._projectors.pop(event_type, None)

    def get(self, event_type: str) -> Optional[ProjectorFn]:
        return self._projectors.get(event_type)

    # ------------------------------------------------------------------
    # 投影主入口
    # ------------------------------------------------------------------

    def project_events(
        self,
        events: List[StepEvent],
        *,
        include_unfinished: bool = False,
    ) -> List[dict]:
        """从事件日志投影出 LLM 上下文消息列表（surface 事件）。"""
        msgs: List[dict] = []
        pending_calls: List[tuple] = []  # (call_id, name, args)
        # replace-shadow 合并：surface_node_id → list of messages
        replace_shadow: Dict[str, List[dict]] = {}
        # compaction/summary 折叠范围：summary_event_id → set of compacted event_ids
        compaction_ranges: Dict[str, set] = {}

        # 1. 先扫描所有 compaction/summary 事件，登记被压范围
        for ev in events:
            if ev.event_type == "compaction/summary":
                out = ev.output or {}
                compacted_ids = set(out.get("compacted_event_ids") or [])
                if compacted_ids:
                    compaction_ranges[ev.event_id] = compacted_ids
                # 同时也支持 seq range（旧 API 兼容）：仅覆盖**该 summary 之前**的事件
                seq_range = out.get("compacted_seq_range")
                if seq_range and len(seq_range) == 2:
                    lo, hi = seq_range
                    for e2 in events:
                        # 关键：summary 事件本身及之后的事件都不在压范围内
                        # （summary 是 replace 后的最终态，自身不应被压）
                        if e2.seq >= ev.seq:
                            continue
                        if lo <= e2.seq <= hi:
                            compaction_ranges.setdefault(ev.event_id, set()).add(e2.event_id)

        # 2. 投影事件，命中 compact range 的事件折叠入 summary shadow
        for ev in events:
            et = ev.event_type

            # tool_call 与 tool_result 配对（保留原 tool_history 语义）
            if et == "tool_call" and ev.state is StepState.ACTING:
                inp = ev.input or {}
                name = inp.get("tool", "")
                if not name:
                    continue
                call_id = f"call_{ev.step_id}_{ev.seq}"
                pending_calls.append((call_id, name, inp.get("input", {})))
                continue

            if et == "tool_result" and ev.state is StepState.OBSERVING:
                if not pending_calls:
                    continue
                call_id, name, args = pending_calls.pop(0)
                msgs.append(project_assistant_tool_call(call_id, name, args))
                msgs.append(project_tool_result(call_id, ev.output or {}))
                continue

            # surface 标记的事件走 projector_fn
            if not self._event_registry.is_surface(et):
                continue

            # 跳过被 compaction 折叠的源事件（被压段不再独立入消息流）
            is_compacted_source = False
            for summary_id, compacted_ids in compaction_ranges.items():
                if ev.event_id in compacted_ids:
                    is_compacted_source = True
                    break
            if is_compacted_source:
                continue

            projector = self._projectors.get(et)
            if projector is None:
                # 未注册投影器：严格模式 raise（model-visible = logged 强校验）
                self._event_registry.validate_logged_visibility(et)
                continue

            try:
                result = projector(ev)
            except Exception:  # noqa: BLE001
                continue
            if result is None:
                continue
            # 投影器可返回 dict 或 list[dict]（多消息）
            items = result if isinstance(result, list) else [result]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # replace shadow 合并
                shadow_id = item.pop("_surface_node_id", None)
                shadow_op = item.pop("_surface_op", "append")
                if shadow_id:
                    replace_shadow.setdefault(shadow_id, [])
                    if shadow_op == "replace":
                        replace_shadow[shadow_id] = [item]
                    elif shadow_op == "prepend":
                        replace_shadow[shadow_id].insert(0, item)
                    else:  # append
                        replace_shadow[shadow_id].append(item)
                else:
                    msgs.append(item)

        # flush replace shadow 到消息流
        for shadow_id, items in replace_shadow.items():
            msgs.extend(items)

        if include_unfinished:
            for call_id, name, args in pending_calls:
                msgs.append(project_assistant_tool_call(call_id, name, args))

        return msgs

    async def project_from_store(
        self,
        store: Any,
        conv_id: str,
        *,
        include_unfinished: bool = False,
    ) -> List[dict]:
        """异步从 StateStore 加载事件并投影（顶层便利方法）。"""
        events = await store.get_events(conv_id)
        return self.project_events(events, include_unfinished=include_unfinished)

    # ------------------------------------------------------------------
    # 内部：tool_result_event 投影（直接读事件 output）
    # ------------------------------------------------------------------

    def _project_tool_result_event(self, event: StepEvent) -> Optional[dict]:
        # 注意：tool/result 事件（surface）由 tool_call/tool_result 配对处理
        # 后产生 assistant+tool 消息对，单个 tool/result 事件本身较少独立出现。
        # 如未来有 standalone tool/result 事件（例如 compacted/replayed 注入）
        # 可在此处理。
        out = event.output or {}
        content = str(out.get("content") or out.get("error") or "[空结果]")
        call_id = out.get("tool_call_id") or f"call_{event.step_id}_{event.seq}"
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "content": content,
        }


# 全局单例
_PROJECTOR_REGISTRY: Optional[ProjectorRegistry] = None


def get_projector_registry() -> ProjectorRegistry:
    global _PROJECTOR_REGISTRY
    if _PROJECTOR_REGISTRY is None:
        _PROJECTOR_REGISTRY = ProjectorRegistry()
    return _PROJECTOR_REGISTRY


def reset_projector_registry() -> None:
    """重置投影器注册表（仅测试用）。"""
    global _PROJECTOR_REGISTRY
    _PROJECTOR_REGISTRY = None


# 兼容旧 API：保留 project_tool_history / ToolHistoryProjector 入口
# （内部委托给 ProjectorRegistry，保持向后兼容）

async def project_tool_history(
    store: Any,
    conv_id: str,
    *,
    include_unfinished: bool = False,
) -> List[dict]:
    """向后兼容的旧 API：仅投影 tool_calls + tool 结果消息对。"""
    events = await store.get_events(conv_id)
    msgs: List[dict] = []
    pending: List[tuple] = []
    for ev in events:
        if ev.event_type == "tool_call" and ev.state is StepState.ACTING:
            inp = ev.input or {}
            name = inp.get("tool", "")
            if not name:
                continue
            call_id = f"call_{ev.step_id}_{ev.seq}"
            pending.append((call_id, name, inp.get("input", {})))
        elif ev.event_type == "tool_result" and ev.state is StepState.OBSERVING:
            if not pending:
                continue
            call_id, name, args = pending.pop(0)
            out = ev.output or {}
            content = _tool_result_content(out)
            msgs.append(project_assistant_tool_call(call_id, name, args))
            msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": content or "[空结果]",
                }
            )
    if include_unfinished:
        for call_id, name, args in pending:
            msgs.append(project_assistant_tool_call(call_id, name, args))
    return msgs


class ToolHistoryProjector:
    """向后兼容的旧 API：带缓存的 tool_history 投影器。"""

    def __init__(self, store: Any) -> None:
        self._store = store
        self._cache: Dict[str, tuple] = {}

    async def get(self, conv_id: str) -> List[dict]:
        events = await self._store.get_events(conv_id)
        seen_seq, cached = self._cache.get(conv_id, (0, []))
        fresh = [e for e in events if e.seq > seen_seq]
        if fresh:
            # 旧版只投影 tool 历史；为保证正确性直接全量重投影
            cached = await project_tool_history(self._store, conv_id)
            self._cache[conv_id] = (events[-1].seq if events else seen_seq, cached)
        return cached
