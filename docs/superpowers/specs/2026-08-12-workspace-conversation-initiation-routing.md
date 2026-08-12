# 场景空间对话发起方式 × 执行模式路由设计

| 字段 | 值 |
|---|---|
| 状态 | Draft(核心决策已拍板,见 §6) |
| 创建日期 | 2026-08-12 |
| 作者 | yhjun1026 + Claude |
| 关联文档 | `SCENARIO_WORKSPACE_PRODUCT_DESIGN.md`(上位文档)、`SCENARIO_WORKSPACE_CONVERSATION_AND_AGENT_TOOLS_DESIGN.md`(会话三层模型)、`SCENARIO_WORKSPACE_ASSET_MANAGEMENT.md`(资产/能力单向依赖) |

---

## 0. 本文档回答什么

空间里发起对话的方式有多种(页面输入 / API 调用 / 定时任务 / 订阅触发),它们应该怎么被处理?
核心诉求:

1. **页面输入**(正常对话)即使"命中剧本",也应在**当前对话里加载剧本同步运行**,完成目标;
2. **用剧本创建异步任务**(类似子 Agent)由后端独立完成;
3. **两种模式的任务都要在任务列表可见,结果都要在空间交付、参与飞轮循环**。

当前实现没有统一模型:页面输入只有"大厅自由分析(lobby)"和"预建任务后进入工作台(workbench)"两种,
前者不产任务记录,后者需要用户先建任务再进任务对话——没有"会话内同步跑剧本但仍是任务"的模式。

---

## 1. 核心思路:两个正交维度 + 统一任务记录

把"**怎么发起**"与"**怎么执行**"解耦:

| 维度 | 取值 | 落点 |
|---|---|---|
| 发起方式 `initiator` | `page` / `api` / `cron` / `webhook` / `alert` / `manual` | `Task.triggered_by`(字符串列,扩展枚举语义) |
| 执行模式 `execution_mode` | `in_session`(会话内同步)/ `background`(后台异步) | `Task.context_json["execution_mode"]`(P0 免迁移) |

**关键命题:页面输入命中剧本 = 会话内同步执行 + 但也是一条任务记录。**
任务记录是两种模式的统一视图:任务列表、交付、资产沉淀、飞轮循环都挂在这条记录上。

---

## 2. 路由矩阵

| 发起方式 | 命中剧本 | 执行模式 | 任务记录 | 机制 |
|---|---|---|---|---|
| 页面输入 | 否 | 会话内自由分析 | 无 | 现状 lobby(`task_id=None`) |
| 页面输入 | **是** | **会话内同步剧本执行** | 有(`triggered_by=page`) | **新增:回合前路由 + 会话内任务** |
| API 调用 | 是/否 | 后台异步 | 有(`triggered_by=api`) | `create_task` + `run_task` |
| 定时任务 cron | 是 | 后台异步 | 有(`triggered_by=cron`) | `trigger.fire` → task |
| 订阅触发 webhook/alert | 是 | 后台异步 | 有(`triggered_by=webhook/alert`) | `fire_trigger` → task |
| 对话内显式"后台跑" | 是 | 后台异步 | 有(`triggered_by=manual`) | `start_task` 工具(现状) |

---

## 3. 新增关键机制:回合前路由 + 会话内任务

### 3.1 回合前路由(pre-round router)

在 `chat/completions` 预处理层、`SceneResourceAssembler` 装配之前判定:

- **显式命中**:前端输入栏选择剧本,或 `ext_info.playbook_id` 显式透传 → 直接进"会话内剧本执行";
- **隐式命中**:自由文本提及空间剧本名 → 轻量名称匹配(起步,后续可升级 LLM 判定);
- **未命中** → 大厅自由分析(现状不变)。

路由只在 `workspace_id` 有、`task_id` 无、`initiator=page`(或未指定)时触发;
**已绑定任务的会话(workbench 对话)与 API/定时/订阅发起一律跳过**。

### 3.2 会话内任务(回合前预建,不在中途 promote)

1. 路由判定命中 → **回合开始前**创建 `Task(playbook_id, triggered_by=page, status=running, conv_session_id=当前会话, context.execution_mode=in_session)`;
2. 注入 `ext_info.task_id` → `SceneResourceAssembler` 走 workbench 装配
   (`PlaybookResource` + 物化 skills/resources 注入**当前对话**)→ 主 Agent 在当前对话同步执行;
3. 收尾(复用大厅交付物化 + 状态流转,见 §5):任务 `running→delivered`、
   本轮交付物化为 `Artifact(task_id)`、distill→Asset、delivery 记录、trace 事件发共享总线(飞轮)。

**关键取舍:回合前预建任务,不做对话中途 promote。**
这规避了历史教训——主 Agent 既建任务又自分析会导致重复工作、任务永久卡在 running。
自由分析路径保持轻量,不被任务化。

### 3.3 防重复命中

同一会话后续消息不得重复建任务:
- 路由先查会话绑定(`get_conversation_workspace(conv_uid)`)——已绑定 task 的会话直接跳过;
- 首条消息建任务后,会话即成为 workbench 会话,后续轮次 `task_id` 已有 → 路由天然跳过。

---

## 4. 后台异步(现状梳理 + 子 Agent 化)

现状已可用,统一口径:

- `start_task`(对话内显式)/ `fire_trigger`(订阅)/ cron(定时)/ `POST /tasks/{id}/start`(API)
  → 建 `Task(triggered_by 区分, context.execution_mode=background)`
  → 独立进程跑 `playbook_runtime.run_task`(app_chat_v3 非流式 + 轮询 + 收尾);
- **子 Agent 化**:剧本 `roles` 块装配职能角色团队(fetcher/analyzer/reporter);
  更深层子任务用 `spawn_agent_task`(gyra-core 已有 AsyncTaskCoordinator);
- **统一视图**:主任务 + 子任务进度都在任务列表;后台任务对话走 `task.conv_session_id`
  (任务专属会话),任务详情可回看执行轨迹与产出。

---

## 5. 统一收尾

两种执行模式收敛到同一套收尾动作:

| 动作 | in_session(对话内) | background(run_task) |
|---|---|---|
| 交付物化 Artifact(task_id,按 file 去重) | `playbook/finalize.py::finalize_task` | 同一函数 |
| 任务状态流转 `running→delivered/awaiting_human` | 同一函数 | 同一函数 |
| Delivery 记录/外发(notify 类) | 同一函数 | 同一函数 |
| review 介入检查 | 同一函数 | 同一函数 |
| workspace 事件(artifact_produced/delivery_sent/intervention_triggered) | 同一函数 | 同一函数 |
| distill→Asset | **未实现(runtime 亦未实现,独立后续项)** | 未实现 |
| trace 采集(skill/gate 级) | 无(靠 workspace 事件入飞轮) | run_task 内 BufferedTraceCollector |

**已落地**:新增 `playbook/finalize.py::finalize_task()` —— 后台 `run_task` 收尾与会话内
`aggregation_chat` finally 收尾共用同一实现,消除两套收尾(artifacts/delivery/介入/状态流转/事件)。
distill→Asset 为独立后续项(runtime 原实现也仅把 distill 渲染进 prompt,未真正沉淀资产)。

---

## 6. 落地清单(按依赖顺序)

1. **Task 口径**(✅ P0):`triggered_by` 扩展枚举(`page/api/cron/webhook/alert/manual`);
   `execution_mode` 存 `context_json`(免迁移,`TaskResponse.context` 已透出);
   `conv_session_id` 双用(in_session=当前会话,background=任务专属会话)。
2. **回合前路由**(✅ P0):`workspace/scene_router.py::route_scene_execution`,
   在 `chat_completions` 预处理层调用;显式 `playbook_id` 优先,名称匹配兜底;
   已绑定任务的会话 / 非 page 发起一律跳过。
3. **会话内收尾**(✅ P0→P1):`playbook/finalize.py::finalize_task` 公共收尾,
   `aggregation_chat` finally 与 `playbook_runtime.run_task` 共用。
4. **公共 finalize**(✅ P1):从 `playbook_runtime` 抽出(见 §5),两模式共用。
5. **前端**(✅ P1):输入栏剧本选择(原有)+ `scene-agent-send-data.ts` 透传
   `ext_info.playbook_id`(显式命中→后端预建会话内任务);任务列表实时状态
   (原 4s 轮询已存在)+ 会话开始即刷新;会话内任务卡片(原 `taskToCreatedStep`/
   `mergeTaskCards` 已有,任务入列表后自动呈现)。
6. **隐式命中**(~P1):剧本名匹配起步已落地;LLM 判定升级留作后续可选。
7. **distill→Asset**(待办):独立后续项,与本次路由无关。

---

## 7. 不做的事(防过度设计)

- 不做全局意图引擎;隐式命中先用剧本名匹配;
- 页面输入未命中剧本 → 无任务,保持自由分析轻量;
- 不做对话中途 promote(回合前预建);
- cron / API 不做成 in_session(无 UI 会话可言)。
