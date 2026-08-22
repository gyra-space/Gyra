"""HarnessContext —— V2 引擎统一服务总线（对齐 DeepSeek Harness 的 ctx）。

本次 harness 收敛改造的核心：把散落在 run_loop / run_step / V2AgentRuntime
参数里的 harness 能力（storage / events / tools / approval / subagents / jobs /
hooks / thinking / acting）收拢为一个可注入、可替换的上下文对象。

设计原则：
  1. **单一入口**：run_loop / run_step 只消费一个 ``HarnessContext``，
     不再透传 10+ 散参数；缺省能力按需从 harness 解包。
  2. **能力缝**：每个能力是可选的 seam 字段，装配时注入不同 provider 即替换行为。
  3. **真实持久化**：``storage`` 默认由 :func:`create_state_store` 创建，
     落 ``{DATA_DIR}/v2_state``（非 tempdir），事件溯源日志跨进程可恢复。
  4. **向后兼容**：run_loop / run_step 保留旧关键字参数，显式参数优先于
     harness 解包；现有测试与调用方无需改动。
"""
from __future__ import annotations

import dataclasses
from typing import Any, Callable, Optional

from gyra.agent.core.v2.event_stream import EventStream
from gyra.agent.core.v2.state_store import StateStore, create_state_store
from gyra.agent.core.v2.tool_resolver import ToolResolver

from gyra.agent.core.v2.harness.seams import JobRegistry, SubagentSeam


@dataclasses.dataclass
class HarnessContext:
    """V2 引擎的统一服务总线。

    字段语义（对齐 DSH ctx 总线）：
      - ``storage``：事件溯源持久化（StepEvent append-only 日志）；
      - ``events``：共享事件流（emit / waterfall / serial 三分法分发）；
      - ``tools``：统一工具入口（system / sandbox / registry / resource 聚合）；
      - ``approval``：工具审批（PermissionGate，含 serial 决策检查点）；
      - ``subagents``：子 Agent seam（可换 provider）；
      - ``jobs``：异步任务注册/查询（可换 backend）；
      - ``hooks``：HookManager（turn_complete / conversation_complete 等）；
      - ``skills``：Skill seam（对齐 DSH ``ctx.skills``；默认实现
        :class:`SkillRegistry`，支持 host+per-scope 分层注册 / digest
        变化通知 / consumer 按需注入 catalog reminder）；
      - ``thinking_fn`` / ``acting_fn``：本轮 turn 的功能函数（装配层生成）。
    """

    storage: StateStore
    events: EventStream
    tools: Optional[ToolResolver] = None
    approval: Any = None  # PermissionGate
    subagents: Optional[SubagentSeam] = None
    jobs: Optional[JobRegistry] = None
    hooks: Optional[Any] = None
    skills: Optional[Any] = None  # SkillSeam（默认实现 SkillRegistry）
    thinking_fn: Optional[Callable] = None
    acting_fn: Optional[Callable] = None

    # ------------------------------------------------------------------
    # 装配辅助
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        agent_id: Optional[str] = None,
        conv_id: Optional[str] = None,
        data_dir: Optional[str] = None,
        db_path: Optional[str] = None,
        state_store: Optional[StateStore] = None,
        event_stream: Optional[EventStream] = None,
        tool_resolver: Optional[ToolResolver] = None,
        approval: Any = None,
        subagents: Optional[SubagentSeam] = None,
        jobs: Optional[JobRegistry] = None,
        hooks: Optional[Any] = None,
        skills: Optional[Any] = None,
        thinking_fn: Optional[Callable] = None,
        acting_fn: Optional[Callable] = None,
        event_batch: Any = None,
    ) -> "HarnessContext":
        """便捷装配：默认创建真实持久化 StateStore + 共享 EventStream。

        独立场景（测试 / 演示 / 无需 V1 agent 装配时）用本方法；
        V2Agent 生产装配走 ``_ensure_v2_engine`` 手动组装（复用 V1 依赖）。

        ``event_batch``：EventStream 高频渲染事件配置（None=默认开启：llm_token 只广播不落库）。
        ``skills``：SkillSeam 实例（默认 None；调用方按需挂载
        :class:`SkillRegistry` 或跨进程后端）。
        """
        if state_store is None:
            state_store = create_state_store(
                agent_id=agent_id,
                conv_id=conv_id,
                data_dir=data_dir,
                db_path=db_path,
            )
        if event_stream is None:
            # 默认开启攒批（None 表示沿用 EventStream 默认）；显式 False 关闭
            batch_arg = event_batch if event_batch is not None else None
            event_stream = EventStream(state_store, batch=batch_arg)
        if skills is None:
            # 默认装一个进程内 SkillRegistry（host 层空启动）
            try:
                from gyra.agent.core.v2.skills import SkillRegistry
                skills = SkillRegistry()
            except Exception:  # noqa: BLE001
                skills = None
        return cls(
            storage=state_store,
            events=event_stream,
            tools=tool_resolver,
            approval=approval,
            subagents=subagents,
            jobs=jobs or JobRegistry(),
            hooks=hooks,
            skills=skills,
            thinking_fn=thinking_fn,
            acting_fn=acting_fn,
        )

    # ------------------------------------------------------------------
    # 能力快捷访问
    # ------------------------------------------------------------------

    @property
    def state_store(self) -> StateStore:
        """别名：storage（旧代码 state_store 命名兼容）。"""
        return self.storage

    @property
    def event_stream(self) -> EventStream:
        """别名：events（旧代码 event_stream 命名兼容）。"""
        return self.events

    @property
    def permission_gate(self) -> Any:
        """别名：approval（旧代码 permission_gate 命名兼容）。"""
        return self.approval

    @property
    def subagent_runtime(self) -> Optional[SubagentSeam]:
        """别名：subagents（旧代码 subagent_runtime 命名兼容）。"""
        return self.subagents

    @property
    def hook_manager(self) -> Optional[Any]:
        """别名：hooks（旧代码 hook_manager 命名兼容）。"""
        return self.hooks

    # ------------------------------------------------------------------
    # 嵌套作用域（对齐 DSH ctx.isolate + ctx.intercept）
    # ------------------------------------------------------------------

    def isolate(self, label: str, **overrides: Any) -> "HarnessContext":
        """创建子作用域（嵌套 HarnessContext），按字段名覆盖父字段。

        用法::

            # 在某 agent preset 中剥离 approval（只读不执行工具）
            sub_harness = parent.isolate(
                "readonly_preset", approval=None, subagents=None,
            )

        语义对齐 DSH ``ctx.isolate(name)``：
          - 子作用域继承父所有字段，未指定 override 时保持原值；
          - 子作用域是**独立 dataclass 实例**，修改子不影响父；
          - 适合 agent preset 内部"差异化能力集"场景（如只读子 agent 关闭 approval）。

        注意：``storage`` / ``events`` 默认**共享**（不改写）；如需隔离 store
        需显式 override（如 ``storage=sub_store``）。
        """
        if not label or not isinstance(label, str):
            raise ValueError("isolate label must be a non-empty string")
        # 仅接受 HarnessContext 已声明字段
        valid_fields = {f.name for f in dataclasses.fields(self)}
        illegal = set(overrides) - valid_fields
        if illegal:
            raise ValueError(
                f"isolate() override fields not in HarnessContext: {illegal}"
            )
        # 浅拷贝字段（避免 dataclasses.asdict 递归深拷贝导致 storage 失去身份）
        field_values = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}
        field_values.update({k: v for k, v in overrides.items() if k in valid_fields})
        new = self.__class__(**field_values)
        new._isolate_label = label
        new._isolate_parent = self
        return new

    def with_override(self, **overrides: Any) -> "HarnessContext":
        """与 ``isolate`` 同语义但 label 自动生成（``override-{int}``），便利方法。"""
        import time as _t
        return self.isolate(f"override-{int(_t.time() * 1000)}", **overrides)

    def get_isolation_chain(self) -> list:
        """返回从根到当前实例的 isolate label 链（调试用）。"""
        chain = []
        cur = self
        while cur is not None:
            label = getattr(cur, "_isolate_label", None)
            if label:
                chain.append(label)
            cur = getattr(cur, "_isolate_parent", None)
        return list(reversed(chain))


# 添加 _isolate_label / _isolate_parent 字段（不在 dataclass 字段表中，避免 asdict 报错）
_HarnessContext_orig_init = HarnessContext.__init__


def _patched_init(self, *args, **kwargs):
    _HarnessContext_orig_init(self, *args, **kwargs)
    self._isolate_label: Optional[str] = None
    self._isolate_parent: Optional["HarnessContext"] = None


HarnessContext.__init__ = _patched_init  # type: ignore[assignment]
