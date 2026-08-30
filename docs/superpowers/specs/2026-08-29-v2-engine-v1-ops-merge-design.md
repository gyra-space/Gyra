# V2 引擎 × V1 运维底座合并设计：单一异步子Agent体系 + 统一看板渲染

* 日期：2026-08-29

* 状态：已批准实施；**P-M1 已落地**（2026-08-29，协议签名以本文 §3.2 实施版为准）

* 作者：yhjun1026 + TRAE

* 前置设计：`docs/superpowers/specs/2026-07-02-v2-agent-framework-successor-design.md`（参考，已关闭）、`docs/superpowers/specs/2026-07-03-v2-agent-independent-evolution-design.md`（双轨并存）

* 关联文档：`docs/ASYNC_SUBAGENT_ARCHITECTURE.md`（异步子Agent总览）、`docs/superpowers/plans/2026-07-01-agent-v2-runtime-p2.md`（P2 SubAgent Runtime）

* 关联代码：

  * V1 运维底座：`packages/gyra-core/src/gyra/agent/util/async_task_manager.py`、`packages/gyra-serve/src/gyra_serve/agent/subagent_coordinator.py`、`packages/gyra-serve/src/gyra_serve/agent/async_task_coordinator.py`、`packages/gyra-serve/src/gyra_serve/agent/recovery_daemon.py`

  * V2 执行引擎：`packages/gyra-core/src/gyra/agent/core/v2/subagent_runtime.py`、`packages/gyra-core/src/gyra/agent/core/v2/spawn_subagent_tool.py`、`packages/gyra-core/src/gyra/agent/core/v2/runtime.py`

  * 渲染：`packages/gyra-ext/src/gyra_ext/vis/common/tags/gyra_subagent_board.py`、`web/src/components/chat/chat-content-components/VisComponents/VisSubagentBoard/index.tsx`、`packages/gyra-core/src/gyra/agent/core/v2/sse_adapter.py`

***

## 1. 背景与现状

### 1.1 两套机制并存的由来（决策史）

| 时间             | 决策                                                                | 证据                                                         |
| -------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- |
| 2026-06-30     | V2 内核立项（P0-P4：状态机 → PermissionGate → SubAgent Runtime → 事件流 → 清理） | `docs/superpowers/plans/2026-06-30-agent-v2-runtime-p0.md` |
| 2026-07-02     | "V2 框架继任 BAIZE"完整迁移设计（5-6 周）                                      | 继任设计 spec                                                  |
| **2026-07-03** | **推翻迁移，关闭 V2 生产入口**，结论："V2 优势可在 V1 (BAIZE) 上纯加法实现"                | 继任设计头部警告（L3-L7）                                            |
| 同日             | 新增"独立演进"spec 复活 V2：双轨并存，互不干扰                                      | 独立演进 spec                                                  |

反复的根本原因（继任设计审计对比表，L48-63）：**两边各有胜场，谁也吃不掉谁**——

* **V2 赢在引擎层**：StepState 状态机、事件溯源 replay、run\_step 级崩溃恢复、PermissionGate、子 Agent transcript 重建

* **V1 赢在运维层**：多轮 loop、上下文两段式压缩、记忆、工具系统、retry/doom-loop 防护，以及一整套**异步子任务运维体系**

当前真实生产形态：`/api/v2/chat` 端点是 mock；V2Agent（role=PIXIU）是 `ReActMasterAgent` 子类"换引擎不换车"，走 agent\_chat 常规构建链，其 V2 部分只贡献 `spawn_subagent` 一个工具，**且仍在消费 V1 AsyncTaskManager 的后台任务通知**（`v2_agent.py` L497 `_collect_background_notifications`）。

### 1.2 能力矩阵：V1 运维底座 vs V2 执行引擎

| #  | 能力                | V1（AsyncTaskManager + serve 三件套）                                                                    | V2（SubAgentRuntime）                                        |
| -- | ----------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 1  | 异步执行              | `asyncio.create_task` + `Semaphore` 限流                                                              | `asyncio.create_task`（无限流）                                 |
| 2  | DAG 依赖            | `depend_on`（Future 等待，`_wait_deps_then_run` L688）                                                   | ❌ 无                                                        |
| 3  | 台账持久化             | `gpts_async_tasks` DB + JSONL，重启重建（`_materialize_from_record`）                                      | 仅 state\_store transcript 快照，不进业务 DB                       |
| 4  | 在途/已完成去重          | `find_in_flight` / `find_completed_equivalent` / coordinator `normalize_task_text` 归一化去重（防昂贵任务重复扣费） | ❌ 无                                                        |
| 5  | 跨进程恢复             | `RecoveryDaemon`：启动扫描 + 心跳/lease 判活 + 原子抢占                                                          | ❌ 无（`reconstruct_handle_from_transcript` 只能事后查状态）          |
| 6  | 真 resume          | 走 `aggregation_chat(is_retry=True)` 全链路                                                             | ❌ `resume()` 只是 `return await self.get_status()`（L489-491） |
| 7  | 完成通知 → 主会话 resume | `AsyncTaskCoordinator` watch\_loop + `SubagentCoordinator.on_subagent_done`                         | ❌ 无（V2 任务不触发主会话唤醒）                                         |
| 8  | **看板渲染**          | `d-subagent-board` → push\_dock → `VisSubagentBoard`，含持久化回放                                         | ❌ **完全不可见**（见 1.3）                                         |
| 9  | 产物聚合/交付           | `collect_artifacts_for_main_conv` + `_deliver_child_artifacts_to_main`（落主会话文件面板）                    | ❌ 无                                                        |
| 10 | 授权围栏              | `emit_authorization_needed` + 看板待授权高亮                                                               | 有 PermissionGate（引擎层），但无产品化围栏推送                            |
| —  | 引擎能力              | —                                                                                                   | ✅ 状态机/事件溯源/深度限制/交互网关/transcript（V1 无）                      |

结论：**V2 执行强、运维全缺；V1 运维全、无子 Agent 引擎语义**（V1 子 Agent 是"再起一个完整会话"，没有 run\_step 级状态机与权限门）。

### 1.3 渲染覆盖现状（核心结论：只有 V1 覆盖，V2 完全不可见）

用户诉求：**异步子 Agent 任务并行必须有专门设计的渲染组件，V1 / V2 主引擎都要覆盖**。

现状核实（file:line 均已验证）：

| 渲染链路环节        | V1 (BAIZE)                                                                                                                             | V2 (PIXIU)                                                                                |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 看板数据结构        | ✅ `gyra_subagent_board.py` vis tag `d-subagent-board`（SubagentItem：sub\_conv\_id/agent\_name/task/status/mode/authorization/artifacts） | ❌ 无对应产出                                                                                   |
| 上板触发          | ✅ `SubagentCoordinator.register_subagent` → `_emit_board_event`（subagent\_coordinator.py L161）→ `push_dock_widget`                     | ❌ `SubAgentRuntime.spawn` 无任何上板调用                                                         |
| SSE 传输        | ✅ gpts\_memory channel → chunk 文件 → SSE                                                                                                | ❌ `sse_adapter.py` L69-72 **显式抑制** **`sub_agent_start`** **等事件**                          |
| 终态/进度刷新       | ✅ `on_subagent_done` / `update_progress`（L477）→ 板重推                                                                                    | ❌ 仅同步到 `job_registry`（**只读查询视图**，`agent_chat.py` L2394-2425 注释明确"纯增量，不影响 serve 台账"，不驱动渲染） |
| 持久化回放（刷新可见）   | ✅ `persist_board` → extra\["subagent\_board"] → `query_chat` 回放                                                                        | ❌ 无                                                                                       |
| 卡片点击 → 子会话实时流 | ✅ 子会话 = 常规会话，query\_chat 直接回放                                                                                                          | ⚠️ 子会话事件在 state\_store（V2 事件日志），现有会话回放端点不识别                                               |

**结论：当前不满足"V1/V2 都覆盖"。V1 渲染体系完整且成熟；V2 async 子任务在产品界面零呈现——用户看不到任务存在、看不到进度、看不到结果，主会话也不会被唤醒。**

### 1.4 关键发现：缝合点已预留，合并成本低于预期

1. `SubAgentRuntime.__init__` 已有 `async_task_manager` 参数（L75），但 `_async_mgr` 全文件仅 L83 赋值一次、**从未被使用**——桥接意图早已存在，只差接线。
2. `SubagentCoordinator` 已具备完整的"登记即渲染"路径：`register_subagent` 一次调用完成 **去重（L133-144）→ 上板（L161）→ 台账镜像（L167 →** **`_mirror_register`）**；终态 `on_subagent_done`/`on_subagent_failed` 完成 板更新 → `_mirror_complete` → 产物聚合交付 → 主会话 resume。
3. `AsyncTaskManager.register_external`（L484）+ `complete_external`（L516）外部任务镜像模式现成（幂等、持久化）。
4. V2 引擎装配的注入通道现成：`agent_chat.py` 已用 `set_v2_engine_ready_hook` 模式把 JobRegistry 关联进 coordinator（L2399-2425），同一机制可注入运维委托。

⚠️ 注意两个约束（决定方案选型）：

* `register_external` 的任务带 `external=True` 标记，AsyncTaskCoordinator 对其**只消费、不触发 resume**（docstring L489-491 明确）——所以**不能只做台账镜像**，resume 必须由 SubagentCoordinator 终态链驱动。

* `SubagentCoordinator` 在 gyra-serve，`SubAgentRuntime` 在 gyra-core——**core 不能反向依赖 serve**，必须用协议接口解耦。

***

## 2. 目标与设计原则

### 2.1 设计原则

1. **执行与运维分离**：V2 引擎只管"怎么跑"（run\_loop/状态机/权限门/transcript）；V1 底座只管"跑的账"（去重/台账/恢复/看板/resume）。
2. **渲染协议单一化**：前端只有**一个**子任务看板组件（`VisSubagentBoard`），V1/V2 主引擎产出的异步子任务都汇入同一 vis 协议 `d-subagent-board`；前端无破坏性 API 变更，增量严格限制在 3.5.3 有意增量清单内（可选字段/可选交互，向后兼容）。
3. **依赖单向**：gyra-core 定义委托协议（Protocol），gyra-serve 提供 SubagentCoordinator 实现；core 不 import serve。
4. **纯增量、可降级**：委托缺位（纯 core 单测、无 serve 环境）时 V2 行为与现状完全一致；桥接失败只打日志不阻断执行。

### 2.2 目标

1. V2 `spawn_subagent(run_in_background=true)` 的子任务：可去重、进台账、看板可见、进度可刷新、完成后自动唤醒主会话、进程重启可恢复。
2. **不管主会话跑在 V1（BAIZE）还是 V2（PIXIU）引擎，异步子任务的渲染入口、卡片协议、交互行为完全一致**。
3. LLM 工具面长期收敛为单一 `spawn_subagent`（阶段四，可选）。

### 2.3 成功标准

| 维度       | 标准                                                                                                 |
| -------- | -------------------------------------------------------------------------------------------------- |
| **渲染统一** | V2Agent 发起 async spawn 后，主会话看板出现卡片（与 V1 卡片同构），终态/进度/产物自动刷新；前端无破坏性 API 变更（增量仅限 3.5.3 有意增量清单，全部向后兼容） |
| **运维对齐** | V2 async 任务可被 `check_tasks`/`wait_tasks` 查询等待；同内容重复提交被去重；主会话 WAITING 时收到完成通知并 resume               |
| **恢复**   | 进程重启后，RUNNING 的 V2 async 任务经 RecoveryDaemon 判活走恢复链；`resume` 能从 transcript latest\_seq 续跑           |
| **零回归**  | V1 SubAgent action / spawn\_agent\_task / media 路径行为不变；V2 无委托时行为不变                                 |

***

## 3. 总体架构

### 3.1 合并后的数据流

```
┌────────────────────────────────────────────────────────────────────────┐
│ 主会话（V1 BAIZE 引擎 或 V2 PIXIU 引擎）                                │
└──────────┬─────────────────────────────────────────────────────────────┘
           │ LLM 工具调用（async 委派）
           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ SubAgentRuntime.spawn(ASYNC)          [V2 执行引擎]                     │
│  1. 深度检查 / 生成 task_id + sub_conv_id / 构建 handle                  │
│  2. ops_delegate.try_register(handle, spec)  ──────────┐（新增，协议）  │
│     ├─ created=False → 去重命中：直接返回已有 handle     │               │
│     └─ created=True  → 登记 + 上板 + 台账镜像（serve）   │               │
│  3. asyncio.create_task(_run_subagent_async)           │               │
│  4. run_loop 事件周期回调 ops_delegate.update_progress  │               │
│  5. 终态（finally）回调 ops_delegate.on_terminal ───────┤               │
└────────────────────────────────────────────────────────┼───────────────┘
                                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│ SubagentCoordinator（V1 运维底座，serve 层实现委托协议）                  │
│  register_subagent：去重(normalize_task_text) → _emit_board_event 上板  │
│                     → _mirror_register（AsyncTaskManager 台账）          │
│  on_subagent_done / on_subagent_failed：                                │
│      板终态 → _mirror_complete → _collect_child_artifacts 产物聚合      │
│      → _deliver_child_artifacts_to_main 交付面板 → 主会话 resume        │
│  persist_board：看板持久化（刷新回放）                                   │
└──────────┬──────────────────────────────────┬──────────────────────────┘
           ▼                                  ▼
┌──────────────────────────┐    ┌─────────────────────────────────────┐
│ AsyncTaskManager 台账     │    │ 前端渲染（唯一组件，V1/V2 共用）      │
│ gpts_async_tasks / 去重   │    │  d-subagent-board (vis tag)          │
│ check_tasks/wait_tasks    │    │   → push_dock_widget → SSE          │
│ AsyncTaskCoordinator 轮询 │    │   → VisSubagentBoard 卡片看板        │
│ RecoveryDaemon 恢复       │    │  （无破坏性改动；增量见 3.5.3）      │
└──────────────────────────┘    └─────────────────────────────────────┘
```

### 3.2 核心新增：`SubAgentOpsDelegate` 协议（gyra-core）

位置：`packages/gyra-core/src/gyra/agent/core/v2/subagent_ops_delegate.py`（新增）

```python
@dataclass(frozen=True)
class SubAgentRegistration:
    """try_register 结果。created=False（去重命中）时 sub_conv_id 必须携带
    已有在途任务的 ID，引擎据此改写 handle 并短路本次 spawn。"""
    created: bool
    task_id: str
    sub_conv_id: str
    status: Optional[str] = None  # 去重命中时为 V1 在途任务状态值（如 "running"）


class SubAgentOpsDelegate(Protocol):
    """V2 子任务运维委托：由 serve 层实现，桥接 V1 运维底座。

    不变量：
    1. 实现方必须吞掉自身异常（记日志），不得向引擎抛出；
       引擎侧另有一层 try/except 兜底（降级为照常执行，只丢看板）。
    2. coordinator 缺位（纯 core / 非 chat 场景）时 try_register
       返回 created=True 放行，引擎行为与无 delegate 时一致。
    """

    async def try_register(self, handle, spec) -> SubAgentRegistration:
        """登记子任务：去重检查 + 看板登记 + 台账镜像（一次到位）。
        created=False 表示去重命中（已有在途同内容任务），引擎放弃本次
        spawn，改写 handle.sub_conv_id 为已有任务 ID 返回给 LLM 复用。"""

    async def update_progress(self, handle, progress: int, note: str = "") -> None:
        """进度同步（看板进度条）。以 handle 为入参：适配器定位 V1
        update_progress 需要 main_conv_id + sub_conv_id 双键，单 task_id 不够。
        节流在引擎侧完成（step 粒度去重），实现方无需再节流。"""

    async def on_terminal(self, handle, result_text: str = "", error: str = "") -> None:
        """终态回调：板终态 → 台账回写 → 产物聚合交付 → 主会话 resume。
        引擎侧经 _terminal_notified 集合保证幂等（早退分支与 finally
        双路径只回调一次）。"""
```

要点（实施版，P-M1 已按此落地）：

* `try_register` 内部复用 `SubagentCoordinator.register_subagent`（去重 + 上板 + 镜像一次到位），`main_conv_id=handle.parent_conv_id`、`sub_conv_id=handle.sub_conv_id`、`task=spec.task`、`params={"source": "v2_engine", "v2_task_id": handle.task_id}`（source 标记供后续按引擎分流/排障）。

* **去重短路语义**：`created=False` 时引擎将 `handle.sub_conv_id` 改写为已有在途任务 ID、`transcript_id=None`，**不创建 asyncio task、不镜像 job**，直接返回 handle——LLM 侧表现为拿到原任务 ID，经 V1 台账 `check_tasks`/`wait_tasks` 复用，天然防重复扣费。

* 进度节流（引擎侧，step 粒度）：run\_loop 按 `event.step_id` 去重（`seen_steps` 集合，排除 `llm_token` 等高频事件），`progress = min(95, steps_done * 100 // max_steps)`——封顶 95，终态 100 留给 DONE 回调，避免"进度 100 但终态未达"的窗口。

* `on_terminal` 按 `handle.status` 分派：`DONE → on_subagent_done(result_text or "（子任务无文本输出）", success=True)`；`FAILED → on_subagent_failed(error or "子任务失败")`；`CANCELLED → on_subagent_failed(error or "任务已取消")`（保持 V1 终态二元模型，取消事实由 error 文案承载；若后续看板需要独立取消态，再扩 SubAgentStatus）。

* 终态幂等（引擎侧）：`_terminal_notified: Set[task_id]` 先记账后回调，覆盖 thinking\_fn 早退与 finally 两条路径；实现方异常同样被吞（记 warning 不阻断）。

* 状态映射：V2 `SubAgentStatus.PENDING/RUNNING → V1 RUNNING`，其余一一对应；注意 **V1 枚举无 CANCELLED**（仅 PENDING/RUNNING/DONE/FAILED），取消态映射为 FAILED + 文案。

* 命名冲突说明（实施期核实修正）：两个同名 `SubAgentHandle` **均在 gyra-core 层**——V2 版 `gyra/agent/core/v2/subagent_handle.py`（pydantic，含 CANCELLED）；V1 版 `gyra/agent/core/subagent_handle.py`（dataclass，无 CANCELLED）。委托协议以 V2 handle 为入参，serve 适配器负责字段转换；后续可择机统一（P-M4）。

### 3.3 引擎侧改造（SubAgentRuntime）

改动点（`subagent_runtime.py`，全部为增量，P-M1 已落地）：

1. `__init__` 增加 `ops_delegate: Optional[SubAgentOpsDelegate] = None` 与 `self._terminal_notified: Set[str]`（与既有 `_async_mgr` 参数并列；`_async_mgr` 参数保留但标记 deprecated，未来由 delegate 吸收其职责）。
2. `spawn()` ASYNC 分支：创建 handle 后、`asyncio.create_task` 之前调用 `_try_register(handle, spec)`（内部委托 `ops_delegate.try_register`，异常容错）；`created=False` 时执行去重短路——改写 `handle.sub_conv_id` 为已有在途任务 ID、`transcript_id=None`、状态置 RUNNING，**不建 asyncio task、不镜像 job**，直接返回（见 §3.2 要点）。
3. `_run_subagent_async()`：

   * run\_loop 消费循环中按 **step 粒度**上报：`event.step_id` 进入 `seen_steps` 集合去重（排除 `llm_token` 高频事件），每见新 step 调 `_report_progress`（`progress = min(95, len(seen_steps) * 100 // max(max_steps, 1))`，`note=event.event_type`）；`max_steps = max(self._max_depth * 4, 10)`。

   * `finally` 块（既有 `_sync_job` 终态同步处）追加 `await self._notify_terminal(handle)`（result 从 handle.result 提取 answer，error 从 handle.error 取）；`thinking_fn` 为空的**早退 FAILED 分支同样回调**，保证任何退出路径终态必达（不变量 2）。
4. SYNC 模式**不接 delegate**：同步委派在主会话上下文内联执行，上板无意义（V1 sync 同理）。
5. `resume()` 升级（阶段三）：从 `reconstruct_handle_from_transcript` 拿 `latest_seq`，从该序号续放 run\_loop 事件流；terminal 后同样回调 `on_terminal`。

### 3.4 serve 侧适配器（CoordinatorOpsDelegate）

位置：`packages/gyra-serve/src/gyra_serve/agent/v2_ops_delegate.py`（新增）

* 薄适配器，全部逻辑委托给既有 `SubagentCoordinator` 方法，不自研状态管理（实施版见 `v2_ops_delegate.py`，P-M1 已落地）。coordinator 解析策略：构造显式传入优先（测试），缺省运行时经 `get_subagent_coordinator()` 模块级单例**懒取**（规避 agent\_chat 构建顺序），解析失败静默返回 None → 全部方法降级。

* 注入路径（实施版；engine-ready hook 为**单值**，delegate 绑定必须与 JobRegistry 绑定合并进同一 hook 函数）：

```python
# agent_chat.py engine-ready hook 内（同步函数，幂等）
def _bind_v2_ops_delegate(agent) -> None:
    rt = agent.v2_subagent_runtime       # V2Agent 新增只读视图 property
    if rt is not None and getattr(rt, "ops_delegate", None) is None:
        from gyra_serve.agent.v2_ops_delegate import CoordinatorOpsDelegate
        rt.ops_delegate = CoordinatorOpsDelegate()   # coordinator 懒取
```

* 配套改动：`V2Agent.v2_subagent_runtime` property（`self._v2_harness.subagents` 的安全读取视图，harness 未装配时返回 None）；`_bind_v2_job_registry` 与 hook 立即绑定段（历史会话场景）均调用 `_bind_v2_ops_delegate`，以 `ops_delegate is None` 判重保证幂等。

### 3.5 渲染组件统一设计：SubagentBoard 是唯一的异步子任务渲染组件

针对"异步子 Agent 任务并行要有**专门设计的组件**渲染，V1 / V2 主引擎**都要覆盖**"的诉求，现状结论（1.3 已逐环节核实）：

* **V1（BAIZE）：已满足。** `VisSubagentBoard` + `d-subagent-board` vis 协议就是为此专门设计的组件——登记即上板、进度可刷、终态折叠、刷新回放、点击进子会话、待授权高亮。

* **V2（PIXIU）：完全不满足。** 三重缺失：无上板调用、SSE 事件被抑制、job\_registry 只读不渲染。

* **本方案的选择：不另起炉灶新造第二个前端组件**，而是把 V2 任务经委托协议汇入这套已产品化的组件，使其成为**两个引擎共用的唯一渲染组件**（协议单一化，见 2.1 原则 2）。理由：V1 组件已覆盖看板全部产品能力，新造组件意味着卡片协议/传输/持久化/回放/交互全部重做且长期维护两套；汇入方案的前端改动被压缩到 3.5.3 的明确增量清单内，且全部向后兼容。

#### 3.5.1 双引擎汇入架构

```
   V1 主会话（BAIZE）                        V2 主会话（PIXIU）
   SubAgent action（async 模式）              spawn_subagent（run_in_background=true）
        │                                         │
        ▼                                         ▼
┌───────────────────────┐    ops_delegate    ┌───────────────────────┐
│ SubagentCoordinator   │◄───────────────────│ SubAgentRuntime       │
│（serve 层，实现委托）  │  try_register      │（core 层，执行引擎）  │
│ register_subagent：   │  update_progress   │                       │
│   去重→上板→台账镜像  │  on_terminal       │                       │
│ 终态：板→产物→resume  │                    │                       │
└───────────┬───────────┘                    └───────────────────────┘
            │ _emit_board_event
            ▼
   d-subagent-board（vis 协议，唯一渲染出口）
            │ push_dock_widget → chunk 文件 → SSE
            ▼
┌─────────────────────────────────────────────────────────┐
│ VisSubagentBoard（前端唯一组件，V1/V2 任务同池渲染）    │
│ 卡片网格 / 进度条 / 产物缩略图 / 终态折叠             │
│ 点击开子会话 / 待授权高亮 / 刷新持久化回放            │
└─────────────────────────────────────────────────────────┘
```

要点：V1 入口零改动；V2 不产生第二套渲染协议——`sub_agent_start` 的 SSE 抑制（`sse_adapter.py` L69-72）**维持不变**，渲染只走 dock 推送这一条路（与 V1 一致），避免前端为 raw 事件新增解析器、出现两套卡片逻辑。

#### 3.5.2 卡片数据契约（SubagentItem）与不变量

数据契约由 vis tag `gyra_subagent_board.py` 定义，两个引擎产出**同一结构**（既有字段以该文件 schema 为准，下图为契约示意）：

```
SubagentItem {
  sub_conv_id    string   子会话 ID（卡片点击打开子会话的键，V2 生成规则不变）
  agent_name     string   子 Agent 显示名
  task           string   任务摘要
  status         string   pending | running | done | failed | awaiting_authorization
  mode           string   sync | async
  authorization  object?  待授权信息（emit_authorization_needed 高亮用）
  artifacts      array    产物缩略图（子会话聚合产物）
  progress       number?  0-100【P-M1 新增可选字段，由 update_progress 喂入】
  shared         bool?    会话内任务标记【P-M2 新增，shared_conv=true 时为 true】
  task_ref       string?  台账任务 ID 引用【P-M2 新增，取消按钮依赖，经 params 透传】
  engine         string?  "v1" | "v2" 引擎徽标【P-M4 新增可选字段】
}
```

两条引擎都必须满足的**不变量**：

1. **上板即登记**：任何 async 子任务启动前必须先出现卡片。V1 由 `register_subagent` 保证；V2 由 `try_register` → 同一函数保证。
2. **终态必达**：卡片必须到达 done/failed 并折叠。V1 走 `on_subagent_done/failed`；V2 走 `finally → on_terminal →` 同一终态链，子任务崩溃也由异常路径兜底，不允许出现永久 running 的孤儿卡。
3. **状态映射唯一**：V2 `PENDING/RUNNING → running`；`DONE → done`；`FAILED → failed`；`CANCELLED → failed`（error="cancelled"，文案承载"已取消"）；与 3.2 `on_terminal` 分派规则一一对应。V2 PermissionGate 的授权事件若要产品化围栏（能力矩阵 #10），复用 `emit_authorization_needed → awaiting_authorization`，列为后续增强，不阻塞本期。
4. **回放同源**：卡片经 `persist_board` 持久化，刷新后 V1/V2 卡片同池回放，顺序与终态一致。

#### 3.5.3 组件既有能力与有意增量清单

**既有能力（已实现，零改动）**：卡片网格与状态着色、进度条、产物缩略图、终态自动折叠、点击卡片打开子会话、待授权高亮、`persist_board` 刷新回放。

**有意增量（全部向后兼容——新字段可选、旧前端忽略；新增交互仅在对应字段存在时渲染）**：

| 增量          | 内容                                                                           | 阶段   | 前端改动                |
| ----------- | ---------------------------------------------------------------------------- | ---- | ------------------- |
| progress 喂数 | `update_progress` → 卡片进度条实时刷新（协议新增可选字段 progress）                             | P-M1 | 无（进度条 UI 已存在，接字段即亮） |
| 取消按钮        | RUNNING 卡片提供取消 → `AsyncTaskManager.cancel`（V2 镜像任务同链路生效）                     | P-M2 | 新增按钮 + 确认交互         |
| shared 标记   | `shared_conv=true` 的任务显示"会话内"，点击不另开标签                                        | P-M2 | 新增标记样式              |
| 子会话回放分流     | 点击 V2 卡片打开子会话：查询端点按来源分流（gpts\_messages vs state\_store），**前端无改动**（路由在 serve） | P-M2 | 无                   |
| 引擎徽标        | 卡片角标 v1/v2（可选字段 engine）                                                      | P-M4 | 新增角标样式              |

当前唯一的产品化缺口是**子会话详情回放分流**：V2 子会话事件在 state\_store（`conv-{id}` 事件日志），V1 子会话在 `gpts_messages`，卡片点击打开子会话时查询端点需能按来源路由（V2 会话回放是独立演进 spec 已规划的能力，本期仅要求端点路由可区分，不阻塞）。

#### 3.5.4 渲染验收口径

同一页面、同一组件、同一协议下逐项对齐：

1. BAIZE 主会话与 PIXIU 主会话各发起一个 async 子任务 → 两张卡片结构、字段、样式一致（引擎徽标上线前无引擎可辨差异）。
2. 状态流转逐项一致：登记即出现（pending/running）→ 进度刷新 → done/failed 折叠。
3. 同内容重复提交：两引擎下都只保留一张卡片（跨引擎去重生效）。
4. 刷新页面：V1/V2 卡片同池回放，终态与顺序一致。
5. 点击卡片：均可打开子会话并看到实时/回放内容（V2 依赖 P-M2 分流完成）。

***

## 4. 分阶段实施

### 阶段一（P-M1）：委托协议 + 桥接接线【核心，先行】

| 项  | 内容                                                                                                                                                                                                                                                                                                                                            |
| -- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 新增 | `gyra-core/.../v2/subagent_ops_delegate.py`（Protocol）；`gyra-serve/.../agent/v2_ops_delegate.py`（CoordinatorOpsDelegate）                                                                                                                                                                                                                       |
| 修改 | `subagent_runtime.py`：`__init__` 加 `ops_delegate`；`spawn` ASYNC 分支接 `try_register`（去重短路）；`_run_subagent_async` finally 接 `on_terminal`；run\_loop 循环接 `update_progress`                                                                                                                                                                        |
| 修改 | `agent_chat.py`：engine-ready hook 中追加 delegate 绑定（与 JobRegistry 绑定同址）                                                                                                                                                                                                                                                                         |
| 测试 | 新增 `packages/gyra-core/tests/agent/core/v2/test_subagent_ops_delegate.py`（8 例：无 delegate 回归 / 正常链路 / 去重短路 / try\_register 异常容错 / on\_terminal 异常容错 / 早退 FAILED / 进度区间 / 幂等）；新增 `packages/gyra-serve/tests/gyra_serve/agent/test_v2_ops_delegate.py`（11 例：字段映射 / 去重命中 / 双降级 / update\_progress 映射 / on\_terminal 三分派与占位文案 / 无 coordinator 全静默） |

完成后即获得：去重（#4）、台账（#3）、check\_tasks/wait\_tasks 可查（#2）、**看板渲染（#8）**、完成 resume（#7）、产物交付（#9）——能力矩阵 8 项缺口一次补掉 6 项。

**P-M1 落地清单（2026-08-29，全部实施）**：

* 新增：`gyra-core/.../v2/subagent_ops_delegate.py`（SubAgentRegistration + SubAgentOpsDelegate 协议，§3.2 实施版）

* 新增：`gyra-serve/.../agent/v2_ops_delegate.py`（CoordinatorOpsDelegate：try\_register 三参数映射 + update\_progress 双键 + on\_terminal 三分派）

* 修改：`gyra-core/.../v2/subagent_runtime.py`（\_\_init\_\_ + \_try\_register + 去重短路 + seen\_steps 进度 + \_notify\_terminal 幂等 + 早退分支回调）

* 修改：`gyra-core/.../v2/\_\_init\_\_.py`（导出协议两个符号）；`gyra-core/.../expand/v2\_agent/v2\_agent.py`（v2\_subagent\_runtime property）

* 修改：`gyra-serve/.../chat/agent\_chat.py`（engine-ready hook 内 \_bind\_v2\_ops\_delegate，幂等，覆盖 hook 路径与历史会话立即绑定路径）

* 已知边界（留待后续阶段）：V2 子会话正文不写 gpts\_messages → 看板点击下钻暂空白（P-M2 分流解决）；CANCELLED 风暴下 finally-await 上报可能丢失（无 cancel 工具暴露，暂无触发面）；SYNC 模式不桥接（设计使然）。

### 阶段二（P-M2）：渲染验收 + 子会话回放分流

* e2e：V2Agent（PIXIU）async spawn → 主会话看板出卡 → 进度刷新 → 终态折叠 → 点击卡片打开子会话（V2 事件源）。

* 会话查询端点按会话来源（V1 gpts\_messages / V2 state\_store）分流。

* 看板持久化回放验证（刷新后 V2 卡片仍在）。

* 前端增量落地（3.5.3）：取消按钮、shared 标记。

### 阶段三（P-M3）：恢复与 resume 对齐

* `SubAgentRuntime.resume()`：transcript `latest_seq` 续跑；终态回调 `on_terminal`。

* RecoveryDaemon 覆盖验证：V2 任务经 `_mirror_register` 进台账后，主会话 RUNNING 扫描时 `pending_subagents` 已包含 V2 任务 → 走 coordinator 恢复链（理论上阶段一即自动生效，本阶段补 e2e 断言）。

* V2 任务补 `Semaphore` 并发上限（复用 `AsyncTaskManager.max_concurrent` 语义，委托 `try_register` 返回前检查，超限进入 PENDING 上板排队）。

### 阶段四（P-M4，长期可选）：工具面收敛

* 单一 LLM 工具 `spawn_subagent`：SYNC → SubAgentRuntime 内联；ASYNC → SubAgentRuntime + delegate。`spawn_agent_task` 保留给 media 任务（产物聚合链路依赖 kind=media，不在本期合并范围）。`SubAgent` action async 分支标记 deprecated。

* 两个 `SubAgentHandle` 模型统一（共享 schema 或显式改名消除歧义）。

* 引擎徽标（3.5.3，可选字段 engine）。

***

## 5. 风险与边界

| 风险                                            | 应对                                                                                                        |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| delegate 异常拖垮子任务执行                            | 协议约束实现方吞异常；引擎侧再兜一层 try/except + 日志（与 `_sync_job` 的 `except: pass` 风格一致）                                   |
| 去重误伤（V2 任务与 V1 任务同内容）                         | `register_subagent` 去重 key 含 agent\_name + 归一化 task + 非终态，语义即"同一件事别做两遍"，跨引擎去重是特性非缺陷                       |
| `shared_conv=true`（共享父 conv）无独立 sub\_conv\_id | 上板但 `params` 标记 `shared=true`，前端点击不另开标签（3.5.3 增量）；台账仍记 task\_id                                           |
| V2 子会话媒体产物                                    | 子 Agent 内部经 V1 工具生成的产物挂在轮询任务台账，`_collect_child_artifacts` 按 sub\_conv\_id 聚合即可命中——V2 子会话只要沿用 V1 工具体系即自动兼容 |
| 台账/看板双写一致性                                    | 单一写入口（coordinator），镜像写在同调用内完成；镜像失败降级为"照跑 + 日志"，看板次日起以台账 `_materialize_from_record` 兜底回放                   |
| BAIZE 主链路回归                                   | V1 三个入口（SubAgent action / spawn\_agent\_task / media）零改动；delegate 仅挂载在 V2 engine 的 runtime 上              |

***

## 6. 验收清单

* [ ] V2Agent `spawn_subagent(run_in_background=true)` → 主会话看板出现卡片（与 V1 卡片同构），终态自动折叠

* [ ] 同内容重复 spawn → 复用 task\_id，看板不出现第二张卡（防重复扣费）

* [ ] `check_tasks(task_ids=[sub_conv_id])` / `wait_tasks` 对 V2 任务可查可等

* [ ] V2 任务完成后，WAITING 主会话被唤醒并收到结果通知（经 coordinator 终态链，非 AsyncTaskCoordinator external 分支）

* [ ] 子会话进度在看板可见（update\_progress）

* [ ] kill 进程重启 → RecoveryDaemon 判活 → 主会话恢复 + V2 任务按台账状态处理；`resume` 从 latest\_seq 续跑

* [ ] 子会话产物（图片/视频）出现在主会话交付面板与看板缩略图

* [ ] 刷新页面 → V2 卡片经持久化回放恢复

* [ ] BAIZE 主链路（SubAgent action / spawn\_agent\_task / media）回归测试通过

* [ ] 前端 `VisSubagentBoard` 无破坏性 API 变更：diff 仅限 3.5.3 有意增量清单（progress 可选字段、取消按钮、shared 标记、引擎徽标），且均为向后兼容增量

* [ ] 3.5.4 渲染验收口径逐项通过（BAIZE 与 PIXIU 双引擎同页对齐）

***

## 7. 测试计划

| 层级        | 文件                                                               | 用例                                                                                                                                                                             |
| --------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 单测（core）  | `tests/agent/core/v2/test_subagent_ops_delegate.py`（新增，P-M1 已落地） | 无 delegate 现状不变；try\_register 去重短路（不建 task / 不镜像 job）；早退分支终态回调；try\_register/on\_terminal 异常容错；update\_progress step 粒度区间（1-95）；\_notify\_terminal 幂等                          |
| 单测（serve） | `tests/gyra_serve/agent/test_v2_ops_delegate.py`（新增，P-M1 已落地）    | 字段映射（V2 handle → register\_subagent 参数，含 params.source=v2\_engine）；去重命中交还已有 sub\_conv\_id；coordinator 缺失/解析异常双降级；update\_progress 双键+steps 映射；终态分派 done/failed/cancelled 及占位文案 |
| 集成（serve） | `tests/gyra_serve/agent/test_async_task_coordinator.py`          | V2 镜像任务不触发 external resume 分支（仍由 coordinator 驱动）                                                                                                                               |
| e2e       | `scripts/v2_demo.py` 扩展 / 满配 agent e2e                           | spawn async → 看板事件序列（登记→进度→终态）→ resume 通知 → 台账记录断言；双引擎渲染对齐（3.5.4）                                                                                                              |

***

## 8. 备选方案（已否决，记录原因）

| 方案                                                | 否决原因                                                                                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| A：仅 `register_external` 台账镜像（不经 coordinator）      | `external=True` 任务被 AsyncTaskCoordinator 设计为"只消费不 resume"（L489-491）；且看板渲染入口在 coordinator 的 `_emit_board_event`，纯镜像**不解决渲染**，与本次核心诉求（统一渲染）不符 |
| B：sse\_adapter 放开 `sub_agent_start`，前端新增 V2 事件解析器 | 违反渲染协议单一化：出现第二套子任务渲染链路，卡片协议/回放/持久化全部重做，前端有破坏性 API 变更                                                                                        |
| B'：为 V2 新造一个独立前端看板组件                              | 与 B 同源问题：卡片协议/传输/持久化/回放/交互全量重做且长期维护两套组件；V1 组件已覆盖全部产品能力，汇入成本远低于新造（见 3.5 选型理由）                                                                |
| C：大爆炸迁移（V2 吸收 V1 全部运维，废弃 V1）                      | P3.5 迁移已因 react\_master\_agent.py 与 V1 方法深度纠缠被标记 "Not yet scheduled"；成本高、回归面大，与"执行/运维分离"的自然边界相悖                                             |

<br />
