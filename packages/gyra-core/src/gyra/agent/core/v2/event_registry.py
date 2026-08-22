"""事件词表注册表（对齐 DSH ``SessionEventMap`` + ``SurfaceEventType``）。

V2 事件溯源契约：**model-visible = logged**——任何进入 LLM 上下文的消息
都必须有对应的事件类型可投影回日志。

**Surface 事件** = 会影响 LLM 上下文的事实事件（assistant message / tool
result / user message / system message 等）。**非 surface 事件** = 仅影响
渲染/观测/审计的内部事件（llm_token / step_done / vis_update / interaction
request 等）。

词表可注册（merge-extensible 的 Python 近似）：
  - 默认注册 DSH-style 核心事件（user / assistant / tool / step / token 等）；
  - 业务插件可注册自定义事件类型并标记 surface=True/False；
  - 投影器（ProjectorRegistry）按事件类型→LLM 消息格式投影。

用法::

    from gyra.agent.core.v2.event_registry import (
        EventRegistry, register_event_type, get_event_registry,
    )

    # 业务插件注册新事件
    register_event_type(
        "my_business/fact",
        is_surface=True,
        projector_fn=lambda event: {"role": "user", "content": event.output.get("text", "")},
    )

    # 查询事件是否 surface
    reg = get_event_registry()
    assert reg.is_surface("user/message")
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set

# 投影器函数签名：接收 StepEvent，返回 LLM 消息 dict（or list of dicts）
ProjectorFn = Callable[[Any], Any]


# 内置核心事件分类（DSH-aligned + 我们的 V2 既有事件）
#
# - surface=True  : 影响 LLM 上下文的事实事件（投影回消息）
# - surface=False : 仅渲染/审计的内部事件
#
_DEFAULT_EVENT_TYPES: Dict[str, Dict[str, Any]] = {
    # --- surface=True：模型可见事实 ---
    "user/message": {
        "is_surface": True,
        "description": "User turn input（用户输入）",
        "category": "user",
    },
    "assistant/message": {
        "is_surface": True,
        "description": "Assistant turn final（助手最终回复，不含 token 流）",
        "category": "assistant",
    },
    "assistant/chunk": {
        "is_surface": False,  # streaming token 单独累积为 message；非独立 surface
        "description": "Assistant streaming token chunk（流式分片）",
        "category": "assistant",
    },
    "tool/result": {
        "is_surface": True,
        "description": "Tool execution result（工具结果）",
        "category": "tool",
    },
    "compaction/summary": {
        "is_surface": True,
        "description": "Compaction 摘要（替换/折叠历史后注入模型）",
        "category": "compaction",
    },
    # --- surface=False：内部/渲染/审计 ---
    "llm_token": {
        "is_surface": False,
        "description": "LLM streaming token（高频渲染事件，不进入 LLM 上下文）",
        "category": "render",
    },
    "step_init": {
        "is_surface": False,
        "description": "Step 初始化事件",
        "category": "step",
    },
    "step_done": {
        "is_surface": False,
        "description": "Step 终止事件",
        "category": "step",
    },
    "step_aborted": {
        "is_surface": False,
        "description": "Step 被 waterfall 中间件中止",
        "category": "step",
    },
    "thinking_started": {
        "is_surface": False,
        "description": "Thinking 阶段开始（waterfall 接缝）",
        "category": "step",
    },
    "request_header": {
        "is_surface": False,
        "description": "LLM 请求 header 快照（model/prompt 摘要/会话标识）",
        "category": "audit",
    },
    "tool_call": {
        "is_surface": False,  # 与 tool/result 配对后再入模型
        "description": "Tool invocation declaration（待执行）",
        "category": "tool",
    },
    "tool_pre_execute": {
        "is_surface": False,
        "description": "Tool pre-execute waterfall 事件",
        "category": "tool",
    },
    "tool_executed": {
        "is_surface": False,
        "description": "Tool execution 元事件（成功/失败/错误码）",
        "category": "tool",
    },
    "observing_done": {
        "is_surface": False,
        "description": "OBSERVING 阶段收尾",
        "category": "step",
    },
    "subagent_spawn": {
        "is_surface": False,
        "description": "Subagent spawn 事件",
        "category": "subagent",
    },
    "interaction_request": {
        "is_surface": False,  # 由 ask_user 折叠为 user/message 后入模型
        "description": "Awaiting user input / tool permission / subagent",
        "category": "interaction",
    },
    "usage_metric": {
        "is_surface": False,
        "description": "Token usage 观测（per-call + cumulative + ratio）",
        "category": "metric",
    },
    "compaction/start": {
        "is_surface": False,
        "description": "Compaction 触发事件",
        "category": "compaction",
    },
    "compaction/end": {
        "is_surface": False,
        "description": "Compaction 完成事件",
        "category": "compaction",
    },
    "spill/store": {
        "is_surface": False,
        "description": "Spill seam：大对象落盘 + locator 注入",
        "category": "spill",
    },
    "plan/start": {
        "is_surface": True,
        "description": "Plan mode 启动",
        "category": "plan",
    },
    "plan/step": {
        "is_surface": True,
        "description": "Plan 步骤（折叠入 plan 状态）",
        "category": "plan",
    },
    "plan/finish": {
        "is_surface": True,
        "description": "Plan 完成（折叠入 plan 状态）",
        "category": "plan",
    },
    # --- todo 事件 ---
    # 对齐 DSH tool-todo：todo 列表**不**进入 LLM 上下文。
    # LLM 通过自己上一轮 tool_call 参数（每次 send ENTIRE list）+ 工具结果
    # 回显（`{todos, counts}`）自然看到当前状态。
    # 事件流只服务 UI（dock widget 渲染）+ 回放（replay last-write-wins），
    # 因此 is_surface=False，不参与 ProjectorRegistry 的 LLM 投影。
    "todo/write": {
        "is_surface": False,
        "description": "Todo list 全量替换事件（last-write-wins，UI + 回放）",
        "category": "todo",
    },
}


class EventTypeInfo:
    """事件类型元信息。"""

    __slots__ = ("name", "is_surface", "description", "category", "projector_fn")

    def __init__(
        self,
        name: str,
        *,
        is_surface: bool,
        description: str = "",
        category: str = "custom",
        projector_fn: Optional[ProjectorFn] = None,
    ):
        self.name = name
        self.is_surface = is_surface
        self.description = description
        self.category = category
        self.projector_fn = projector_fn

    def __repr__(self) -> str:
        surface = "surface" if self.is_surface else "internal"
        return f"<EventTypeInfo {self.name!r} {surface} cat={self.category!r}>"


class EventRegistry:
    """事件词表注册表（单例）。"""

    def __init__(self) -> None:
        self._types: Dict[str, EventTypeInfo] = {}
        # 加载默认事件词表
        for name, info in _DEFAULT_EVENT_TYPES.items():
            self._types[name] = EventTypeInfo(
                name=name,
                is_surface=info["is_surface"],
                description=info.get("description", ""),
                category=info.get("category", "custom"),
            )

    def register(
        self,
        name: str,
        *,
        is_surface: bool,
        description: str = "",
        category: str = "custom",
        projector_fn: Optional[ProjectorFn] = None,
    ) -> EventTypeInfo:
        """注册新事件类型（业务插件扩展点）。"""
        if not name or not isinstance(name, str):
            raise ValueError("event type name must be a non-empty string")
        if name in self._types and self._types[name].projector_fn is None and projector_fn is not None:
            # 允许用 projector_fn 二次注册已有事件（增强投影器）
            info = self._types[name]
            info.projector_fn = projector_fn
            return info
        info = EventTypeInfo(
            name=name,
            is_surface=is_surface,
            description=description,
            category=category,
            projector_fn=projector_fn,
        )
        self._types[name] = info
        return info

    def get(self, name: str) -> Optional[EventTypeInfo]:
        return self._types.get(name)

    def is_surface(self, name: str) -> bool:
        """未注册事件默认 surface=False（保守：避免误把内部事件当消息）。"""
        info = self._types.get(name)
        return info.is_surface if info else False

    def surface_types(self) -> List[str]:
        return [n for n, i in self._types.items() if i.is_surface]

    def internal_types(self) -> List[str]:
        return [n for n, i in self._types.items() if not i.is_surface]

    def all_types(self) -> List[str]:
        return list(self._types.keys())

    def set_projector(self, name: str, fn: ProjectorFn) -> None:
        info = self._types.get(name)
        if info is None:
            raise KeyError(f"event type not registered: {name}")
        info.projector_fn = fn

    def get_projector(self, name: str) -> Optional[ProjectorFn]:
        info = self._types.get(name)
        return info.projector_fn if info else None

    def validate_logged_visibility(self, name: str) -> None:
        """运行时断言：surface 事件必须可投影（model-visible = logged）。"""
        info = self._types.get(name)
        if info is None:
            return  # 未注册事件不强制约束
        if info.is_surface and info.projector_fn is None:
            raise RuntimeError(
                f"invariant violation: surface event '{name}' has no projector_fn "
                f"(model-visible = logged requires every surface event to project)"
            )


# 全局单例
_REGISTRY: Optional[EventRegistry] = None
# 初始化钩子：每次新建 EventRegistry 时调用（用于业务模块在 registry 重置后重新挂载 projector）
_INIT_HOOKS: List[Callable[[EventRegistry], None]] = []


def register_post_init_hook(fn: Callable[[EventRegistry], None]) -> None:
    """注册初始化钩子：每次 ``get_event_registry`` 新建实例后调用。

    用于解决业务模块（如 plan.py / spill.py）依赖模块导入期副作用的脆弱性——
    测试中如果调用了 ``reset_event_registry``，原副作用丢失。
    通过本接口注册钩子，保证 reset 后 projector_fn 也能被重新挂载。

    用法::

        def _ensure_plan(reg: EventRegistry) -> None:
            if reg.get("plan/start") is not None and reg.get("plan/start").projector_fn is None:
                reg.set_projector("plan/start", project_plan_start)

        register_post_init_hook(_ensure_plan)
    """
    _INIT_HOOKS.append(fn)


def get_event_registry() -> EventRegistry:
    """获取全局事件词表单例。

    新建实例时自动调用所有 post_init_hook（保证业务 projector 在 reset 后
    也能被重新挂载）。
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = EventRegistry()
        for fn in _INIT_HOOKS:
            try:
                fn(_REGISTRY)
            except Exception:  # noqa: BLE001
                # 钩子失败不阻断 registry 创建（业务可后续手动注册）
                pass
    return _REGISTRY


def register_event_type(
    name: str,
    *,
    is_surface: bool,
    description: str = "",
    category: str = "custom",
    projector_fn: Optional[ProjectorFn] = None,
) -> EventTypeInfo:
    """便捷注册接口（业务插件入口）。"""
    return get_event_registry().register(
        name,
        is_surface=is_surface,
        description=description,
        category=category,
        projector_fn=projector_fn,
    )


def reset_event_registry() -> None:
    """重置事件词表（仅测试用）。"""
    global _REGISTRY
    _REGISTRY = None
