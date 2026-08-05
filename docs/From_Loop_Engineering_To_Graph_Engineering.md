# 从 Loop Engineering 到 Graph Engineering：Gyra 的演进与规划

> 2026 年 6 月，OpenClaw 的 Peter Steinberger 用一句 "Stop prompting. Design the loop." 引爆了 Loop Engineering；同年 7 月，他又抛出 "我们还在谈 loop，还是已经转向 graph？"，Graph Engineering 随之走红。本文梳理这两次范式跃迁的来龙去脉，盘点 Gyra 当前三层 Loop + 五环数据飞轮的实际状态，并基于深度可行性分析，给出 Gyra 从 Loop 走向 Graph 的演进路线图与分阶段规划。

---

## 目录

1. [范式跃迁：从 Prompt 到 Loop，再到 Graph](#一范式跃迁从-prompt-到-loop-再到-graph)
2. [Gyra 的现状坐标：三层 Loop + 五环数据飞轮](#二gyra-的现状坐标三层-loop--五环数据飞轮)
3. [为什么需要图工程：当前 Loop 的边界](#三为什么需要图工程当前-loop-的边界)
4. [差距分析：从 Loop 到 Graph 要补什么](#四差距分析从-loop-到-graph-要补什么)
5. [可行性评估：复用与新建](#五可行性评估复用与新建)
6. [演进路线与分阶段规划](#六演进路线与分阶段规划)
7. [风险、权衡与三条红线](#七风险权衡与三条红线)
8. [结论](#八结论)

---

## 一、范式跃迁：从 Prompt 到 Loop，再到 Graph

AI 应用工程在过去几年里沿着"控制粒度不断上移"的路径演进。每一次跃迁都让 AI 从"一次性回答"更接近"可交付的真实业务参与"。

| 时代 | 核心范式 | 控制粒度 | 解决了什么 | 留下什么新问题 |
|---|---|---|---|---|
| **Prompt 时代** | 写更好的提示词 | 一句话 | 让 LLM 能"说话" | 无状态、无工具、无循环 |
| **Context 时代** | 提供更好的上下文 | 一段信息 | 让 LLM"更懂"输入 | 仍是单次推理 |
| **Harness 时代** | 搭建运行系统 | 一套系统 | 控制上下文、托管运行时 | 任务结束经验不沉淀 |
| **Loop Engineering** | 设计循环 | 一个闭环 | 让 AI 自主持续运转 | 多职责塞进单一循环，失败无法定点回退 |
| **Graph Engineering** | 编排图 | 一张节点图 | 多角色分工、并行、校验、人工关口 | 引入时延/成本/运维负担 |

**关键洞察**：Loop 和 Graph 不是"谁取代谁"的替代关系，而是**组织升级**关系。社区已经形成共识——

> **Loop 负责让一个角色把局部任务做完；Graph 负责让多个局部任务组成可交付的结果。一张 Graph 里，完全可以有 Loop。**

Graph Engineering 的三要素（源自 LangGraph 抽象）：

- **Node（节点）**：某一步具体做什么。可以是 LLM、确定性代码、API、规则，或一次人工审批。
- **Edge（边）**：当前节点完成后，下一步去哪个节点。表达路由、分支、回退、转人工的条件。
- **State（状态）**：任务当前处于什么状态、已拿到哪些信息——是结构化任务单，而非整段对话。

一句话概括 Graph Engineering 的本质：**把原本藏在 Prompt 和上下文里的职责、状态、路由、检查、退路，变成显式、可执行、可追踪的系统结构。重点不是"图"，是"显式"。**

---

## 二、Gyra 的现状坐标：三层 Loop + 五环数据飞轮

Gyra 当前已经落地的是**三层 Loop Engineering** 与**五环数据飞轮**，详见 [Three_Layer_Loop_And_Five_Ring_Flywheel.md](./Three_Layer_Loop_And_Five_Ring_Flywheel.md)。这里只做与本主题相关的现状盘点——**Gyra 离"图"其实并不遥远，图的运行时零件已经造好，缺的是"图"的编排骨架和声明语言**。

### 2.1 三层 Loop

| 层次 | 名称 | 循环本质 | Gyra 核心载体 |
|---|---|---|---|
| **L1** | LLM Loop | 思考 → 行动 → 验证 | `core/v2/run_loop.py` + `react_master_agent` |
| **L2** | Agent Loop | 记忆进化 + 沉淀反哺 | `LongTermMemoryManager` + `MemoryPromotionEngine` + `SedimentPipeline` |
| **L3** | 业务场景 Loop | 触发 → 执行 → 产出 → 交付 → 沉淀 → 演化 | `Workspace` + `Trigger` + `Playbook` + `Intervention` + `Asset` |

### 2.2 五环数据飞轮

由 `SharedEventBusComponent` 驱动同一条 `AssetEventBus`，五环（资产 → Agent → Trace → 演化 → 评测）通过 `TRACE_FINALIZED / SEDIMENT_RECEIVED / MATURITY_PROMOTED / EVOLUTION_PROPOSED` 等事件联动，构成"业务数据越跑飞轮越快"的自驱动闭环。

### 2.3 已埋下的"图"的种子

| 已有原语 | 位置 | 本质 | 离"图"还差什么 |
|---|---|---|---|
| 单 Agent 长程循环 | `run_loop.py` | Loop（思考→行动→验证→重试） | 这是"节点内部的干活"，不是节点 |
| 动态子 Agent | `subagent_runtime.py` `spawn` | 运行时按需 spawn（sync/async、限深度、独立 conv、transcript 重建） | spawn 是运行时动态产生，没有预定义的节点图 |
| Playbook 声明 | `playbook/runtime.py` | skills / context / gates / deliverables / distill | 是"约束声明"，不是"图声明" |
| 人工关口 | `Intervention` / 交付审批 / Execute 审批 | 任务级挂起 | 不是节点级退回 |
| 可观测 | `BufferedTraceCollector` | 事后轨迹（skill/gate 调用序） | 是观测，不是驱动执行的图引擎 |
| 多 Agent 团队 | `team_react_plan.py` | 规划 → 并行派活 → 汇总 | 已大段注释（legacy），且非显式图 |

**最关键的现状**：`playbook/runtime.py` 每个 Task 只 `app_chat_v3` 启动**一个** Agent 到同一会话，然后轮询到完成。也就是说——**L3 的"一次业务执行"目前就是"一个 Agent 在一个大 Loop 里自主跑完 + 末尾 gate 挂起 + 强制 distill"**。这正是社区指出的 Loop 固有问题的精确投影。

---

## 三、为什么需要图工程：当前 Loop 的边界

当 Agent 只负责回答时，出错只是体验问题；当 Agent 开始发邮件、改库存、调价格、操作客户数据时，出错就变成了流程、权限和责任问题。模型能力越强，它能做的动作越多，系统越需要清晰的结构。

社区总结出"该用 Graph 的信号"（五条，缺一不可）：

1. **路径会根据中间结果变化**——不同输入进入不同分支，可能返回前面的节点。
2. **有多个可独立完成的专业任务**——它们可以分工或并行，且有明确的输入输出。
3. **需要长时间运行**——跨分钟、小时甚至天，期间要暂停、恢复或等待外部信息。
4. **需要多道质量检查**——单点错误会向后放大，不适合只在最终结果上验收。
5. **涉及高风险动作**——影响用户、资金、客户关系、业务数据或对外承诺，必须有权限和人工关口。

对照 Gyra 的 L3 业务场景，这些信号大量存在：SRE 巡检（采集多源告警 → 事实校验 → 根因分析 → 人工确认修复）、数据月报（多源取数可并行 → 口径校验 → 生成报告 → 审批发布）等都是典型的"应上 Graph"场景。而 L1/L2 是纯 Loop 场景（单 Agent 长程任务），**用 Loop 最直接，不需要也不应该改**。

**选型判断顺序**（社区共识）：单次调用能解决 → 固定 Workflow → Loop → Graph。每向后走一步，系统获得更强的表达能力，也增加了时延、成本、调试和运维负担。**不要为了框架而框架。**

---

## 四、差距分析：从 Loop 到 Graph 要补什么

在当前工程上落地显式图工程，存在五个核心差距（Gap）：

### Gap 1：没有"图定义层"（Graph Schema）

社区图工程的起点是**预定义**的 Node / Edge / State。当前 Playbook 是**约束声明**（`gates` 是"遇到异常才人介入"的规则，不是"任务要经过哪几个节点"的拓扑）。

- 缺：`nodes: [{id, type, agent_ref, input, output_schema, accept}]`、`edges: [{from, to, condition}]`、`state_schema`。
- Playbook 的 `gates` 只能表达"单点挂起"，表达不了"失败退回上一节点"、"证据不足走补充采集分支"这类**边路由**。

### Gap 2：没有"图执行器"（Graph Executor）

当前只有两级执行：`run_loop`（单 agent 内部循环）和 `spawn`（动态子 agent）。缺一个**在节点间流转的引擎**：谁决定"当前节点完成 → 走哪条边 → 进入下个节点"，谁来**并行**多个独立节点、**join** 它们的产物、按条件**路由 / 回退**。

- 现在这些"流转"全部由 LLM 在 prompt 里自我决策，**不可追踪、不可定点恢复**。

### Gap 3：没有"结构化任务单"（Structured State）

社区强调 State 不是对话累积，而是结构化的（目标 / 阶段 / 已完成节点 / 证据列表 / 冲突项 / 审阅结果 / 重试次数 / 待人工项）。

- 当前状态 = 对话历史 + LongTermMemory + Trace 记录，**没有**一个"任务单"对象承载"任务进行到哪个节点、已产出什么、证据齐不齐、重试了几次"。没有它，就无法"暂停 → 恢复 → 追责 → 单点退回"。

### Gap 4：没有"节点级验收与回退"

社区主张**每个节点绑定验收标准**、失败**退回单个节点**。

- 当前只有：末尾校验 `deliverables` 完整性 + 评测环（事后反馈）。节点内部失败了，整个 Task 直接 `failed` 或归因到最终状态，**没有中间节点关卡、没有单点补偿**。

### Gap 5：人工关口是"任务级"而非"节点级"

- 当前 `intervention` 把整个任务挂起（`awaiting_human`），人解决后 Agent 继续。社区图工程是**把人工闸门插在具体节点之间**（如"发布"节点前必须人确认），人审完只继续后续节点，前面已完成的节点不重跑。前者是"全任务阀门"，后者是"节点级阀门"。

---

## 五、可行性评估：复用与新建

整体判断：**架构上完全可行，且成本可控**——Gyra 已经把"图"的运行时零件造好了，缺的是"图"的编排骨架和声明语言。按改造量分级：

| 能力 | 复用现有 | 需新建 | 改造量 |
|---|---|---|---|
| 节点宿主（一个节点 = 一个 agent 循环） | `run_loop.py` + `SubAgentRuntime.spawn` | 节点适配器（把 agent 包装成 node） | 小 |
| 节点内部干活 | L1/L2 Loop、Skill、工具、MCP | — | 0 |
| 节点间并行 / join | `run_async_tasks`（`team_react_plan` 已用） | join 语义封装 | 小 |
| 人工关口 | Intervention + 收件箱 | 节点级挂起语义（挂起"当前节点"而非"整个任务"） | 中 |
| 可观测 | `BufferedTraceCollector` | 节点级 trace（节点粒度 + 状态快照） | 中 |
| 状态持久化 | StateStore / EventStream | 结构化 State 模型（任务单 schema） | 中 |
| **图声明** | Playbook DSL | `graph` 段（nodes / edges / state） | **大（核心新建）** |
| **图执行器** | — | `GraphExecutor`（路由 / 回退 / 并行 / 挂起） | **大（核心新建）** |

**隐藏红利**：`run_step` 已天然支持 `AWAITING_USER / AWAITING_TOOL_PERMISSION / AWAITING_SUB_AGENT` 挂起态，`SubAgentRuntime` 已支持 async 后台 + transcript 重建（`reconstruct_handle_from_transcript`）——这些正是"图节点长时间运行、暂停、恢复"所需的**生命周期原语**，几乎可以平移。所以图执行器可以建立在现有 event / state 基础设施之上，而不是另起炉灶。

---

## 六、演进路线与分阶段规划

建议分 4 期推进，遵循"先用现有原语验证收益，再引入显式图"的原则，避免过早工程化。

### Phase 0 · 不引入"图"概念，先证明收益

把现有 `team_react_plan` 的"规划 → 并行子任务 → 汇总"能力收敛回可用（当前已注释），在一个 Playbook 里跑通"采集并行 + reporter 汇总"。**先用现有 Loop 原语拼出图的效果**，验证业务侧是否真的需要显式图，避免为框架而框架。

- 目标：验证"并行采集 + 汇总"在真实场景（如 SRE 巡检、数据月报）的收益。
- 交付：一个可用的多 Agent 并行示范 Playbook。

### Phase 1 · 给 Playbook 加 `graph` 声明段 + 轻量执行器

在 Playbook declaration 里新增**可选** `graph:` 段（不破坏现有 `skills/context/gates/deliverables/distill`，向后兼容）：

```yaml
graph:
  state: { phase, evidence: [], conflicts: [], retries: {}, pending_review: [] }
  nodes:
    - id: collect
      host: agent            # 复用 run_loop / spawn
      skills: [db_query, anomaly_detect]
      accept: { evidence: "min 3" }
    - id: verify
      host: code             # 确定性校验节点（复用现有规则）
      rules: [field_present, link_alive, date_in_range]
    - id: review
      host: human
  edges:
    - from: collect, to: verify
    - from: verify, to: collect, on: "evidence_conflict"   # 定点回退
    - from: verify, to: analyze, on: "ok"
    - from: analyze, to: review, on: "needs_human"
```

配套一个最小 `GraphExecutor`：读声明 → 按 edge 路由 → 每节点用 `run_step` / `spawn` 作为宿主 → 节点完成写回结构化 State → 满足 `accept` 才放行。**这一步把"一次执行 = 一个 agent loop"变成"一次执行 = 一条可追踪的节点链"。**

- 目标：打通"声明 → 执行 → 回退"的最小闭环。
- 交付：`GraphExecutor` + `graph` 声明段 + 一个真实 Playbook 改造。

### Phase 2 · 结构化 State + 节点级 gate + 定点回退

把 State 落成一张"任务单"表（阶段 / 证据 / 成果 / 重试数 / 待审项），替代"靠 trace 事后反推"。`gates` 升级为**挂在节点边界**上（`intervention` 从"挂起整个任务"改为"挂起当前节点，人处理后继续后续边"）。失败时按 `edges` 的 `on` 条件退回指定节点，已完成节点不重跑。

- 目标：可暂停、可恢复、可追责、可单点退回。
- 交付：结构化 State 模型 + 节点级挂起 + 定点回退。

### Phase 3 · 图粒度观测 + 评测 + 飞轮接入

`BufferedTraceCollector` 升级为**节点粒度** trace（节点 id / 状态 / 耗时 / 通过率 / 人工接管率），喂给评测环和演化环——这样"图"才能接入现有五环数据飞轮（Trace 环自然升级为"图轨迹"）。前端飞轮工作台可视化为真正的节点流程图。

- 目标：显式图的执行全程可观测、可量化、可反馈飞轮。
- 交付：节点粒度 Trace + 评测/演化接入 + 前端图可视化。

---

## 七、风险、权衡与三条红线

1. **别为了 Graph 而 Graph**。社区明确警告：`单调用 → Workflow → Loop → Graph` 逐级增加时延 / 成本 / 调试 / 运维负担。**L1/L2 是纯 Loop 场景，绝不改**。只有满足"多独立专业子任务 + 动态路由 + 需中途校验 + 高风险动作"的 L3 任务才值得。

2. **与现有"Agentic 哲学"的张力**。项目纪律是"声明式优于过程式、LLM 越强执行越好"。显式图本质是**把编排权从 LLM 收编到图结构**。解法是把 `graph` 做成**可选**：默认仍是"一个 Agent 自主编排"（保留 Agentic 红利），只有声明了 `graph` 的任务走显式图。**Graph 是"约束加强"，不是"替换 Agent"**——节点内部仍由 L1/L2 Loop + LLM 自由发挥。

3. **成本集中在两处**：`graph` 声明 DSL 的 schema 设计 + `GraphExecutor` 的路由 / 回退 / 挂起语义（这是真正的新代码）。其余都是"零件复用"。

4. **不要动五环飞轮**：图工程是**执行层**的升级，飞轮是**数据层**的反哺。两者正交——图让执行可追踪，飞轮让追踪的数据转起来。Phase 3 只是让 Trace 环"图粒化"，不改变五环结构。

**三条红线**（延续项目既有纪律）：
- **治理落工具面硬门禁，prompt 只做引导**：节点路由、权限、回退条件都落工具面/图结构，不靠 prompt 软约束。
- **AI 提议，人决策**：图演化、节点验收不通过时的处理、高阶动作审批，永远人把关。
- **Graph 可选，不破坏 Agentic 红利**：默认仍是单 Agent 自主编排，Graph 是约束加强而非替换。

---

## 八、结论

- **问题**：目前一次业务执行是"单 Agent 单 Loop"，把多职责塞进一个大上下文，失败无法定点回退、状态不可结构化追踪。
- **差距**：缺图声明层、图执行器、结构化 State、节点级验收 / 回退、节点级人工关口五样东西。
- **可行性**：**高**。运行时零件（`run_step` 挂起态、`SubAgentRuntime` async + transcript、Intervention、TraceCollector）都已存在，主要新建的是 `graph` 声明段 + `GraphExecutor`。
- **做法**：分 4 期，Phase 0 先用现有原语验证收益，Phase 1 加 `graph` 声明 + 轻量执行器（向后兼容、可选启用），Phase 2 结构化 State + 定点回退，Phase 3 图粒度观测接入五环飞轮。
- **核心原则**：**Graph 是 Loop 的组织升级，不是替代；可选启用，不破坏现有 Agentic 红利。**

> **Gyra：从"设计循环"到"编排图"，从"让 Agent 动起来"到"让 Agent 在真实业务里走对路"。**

---

## 参考文档

- [三层 Loop Engineering 与五环数据飞轮](./Three_Layer_Loop_And_Five_Ring_Flywheel.md)
- [场景空间产品设计](./SCENARIO_WORKSPACE_PRODUCT_DESIGN.md)
- [场景空间架构设计](./SCENARIO_WORKSPACE_DESIGN.md)
- [Playbook Runtime 剧本运行时](../packages/gyra-serve/src/gyra_serve/playbook/runtime.py)
- [SubAgentRuntime 子智能体运行时](../packages/gyra-core/src/gyra/agent/core/v2/subagent_runtime.py)
- [run_loop 运行循环](../packages/gyra-core/src/gyra/agent/core/v2/run_loop.py)

### 外部权威参考

- [LangGraph — Graph API Overview](https://langchain-ai.github.io/langgraph/)（State / Node / Edge 三要素）
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)（workflows vs agents、agent loop 本质）
- [Cobus Greyling — Loop Engineering（GitHub 开源项目）](https://github.com/cobusgreyling/loop-engineering)（Loop 六个原语、渐进自主）
- [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/)（"Build the loop. But build it like someone who intends to stay the engineer."）