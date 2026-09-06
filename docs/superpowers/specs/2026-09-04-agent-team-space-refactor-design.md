# Agent Team 空间重构设计：从"剧本"到"专家团队"

* 日期：2026-09-04

* 状态：v5 修订（采纳评审意见：专家外挂资源独立成表——标准专家 agent + 空间外挂资源表，运行时组装注入；放弃 workspace\_resource config\_json 塞装备方案）

* v4：专家"身份全局 + 装备空间级"分层——同一法务专家在不同空间可挂不同 skill/MCP/知识库

* v3：专家为空间一等公民、空间内可直接交互与编辑维护；Leader 定位为"全能选手+调度者"

* v2：不建新 agent 表，复用 GptsApp 体系；"专员"改"专家"；补充剧本概念清理清单

* 关联文档：

  * `2026-06-30-agent-framework-evolution-design.md`（V2 框架子 Agent 统一模型）

  * `2026-07-07-scene-space-redesign-design.md`（场景空间三栏布局）

  * `2026-07-08-scene-agent-template-design.md`（scene-workspace-agent 模板）

* 关键代码：

  * `packages/gyra-serve/src/gyra_serve/playbook/`（剧本模型/runtime/finalize，待清理）

  * `packages/gyra-serve/src/gyra_serve/building/app/`（GptsApp 统一管理：gpts\_app + gpts\_app\_detail 表）

  * `packages/gyra-serve/src/gyra_serve/workspace/agent_tools/`（Leader 工具层）

  * `packages/gyra-serve/src/gyra_serve/workspace/materializer.py`（资源物化，已支持 app 引用）

***

## 1. 背景与问题

### 1.1 现状：剧本是一个"三合一"概念

Playbook declaration DSL 实际承载三类正交关注点：

| DSL 块                                                                           | 内容              | 本质归属                   |
| ------------------------------------------------------------------------------- | --------------- | ---------------------- |
| `text_content`（role\_definition/goal/workflow/behavior\_constraints/background） | 人设与执行指引         | **Agent 定义**           |
| `skills` + `context.resources`                                                  | 技能与数据源绑定        | **Agent 定义**           |
| `deliverables` + `distill`                                                      | 交付物类型/外发渠道/资产沉淀 | **工作合约（Contract）**     |
| `trigger_json`（表字段）                                                             | 定时/事件触发         | **冗余**（trigger 已是独立模块） |

### 1.2 三个结构性问题

1. **执行体缺位**：剧本不是独立 agent。`playbook/runtime.py::run_task` 用 `workspace.default_agent_app_code`（scene-workspace-agent）披剧本的"皮"执行——剧本没有自己的身份、会话与记忆。
2. **团队概念断头路**：`materialize_playbook_roles`（materializer.py:412）装配的角色团队只打日志，未传入执行链路。
3. **概念认知负担**：用户需要理解"剧本/场景 agent/roles/触发器"四个半生不熟的概念，而它们实为"Agent + 合约 + 触发"的错位拼装。

### 1.3 关键事实：系统早已支持 agent 统一定义

* **GptsApp 体系就是 agent 注册表**：`building/app` 模块维护 `gpts_app` + `gpts_app_detail` 表，已有 `dataops-agent`、`sre-agent`、`main`（orchestrator）、`scene-workspace-agent` 等定义（`gyra_app_define/*.json`），具备完整 CRUD/发布链路。

* **空间资源池与物化链路现成**：workspace\_resource 表（type: data\_source/knowledge\_space/environment/mcp/skill/llm\_model/ecp）是空间资源池；物化链路（`_materialize_declared_item` + `_load_pool_by_ref` 空间池对齐）可直接复用于专家外挂组装。

* **Task 模型已预留**：`assigned_agents_json`、`parent_task_id`、`triggered_by/trigger_ref`。

* **Leader 调度 prompt 已在位**：scene-workspace-agent 模板已有四路径执行决策表，分派对象从"剧本"换成"专家"即可。

**结论：专家身份不需要新的实体表（复用 GptsApp）；空间侧只需两张轻量关联表（成员名册 + 外挂明细）。专家 = GptsApp（身份）+ workspace\_expert（成员）+ workspace\_expert\_equipment（外挂）+ 合约（交付约定）。**

***

## 2. 目标 / 非目标

### 2.1 目标

1. 概念归一：场景空间 = 多 Agent 团队（1 Leader + N 专家），专家在 agent 模块（GptsApp）统一定义与维护。
2. 执行体分离：专家以自己的 GptsApp 身份执行任务，不再是 Leader 披皮。
3. Leader 调度：大厅 agent 升级为 Leader，持有 `dispatch_to_expert` 工具。
4. 剧本概念清退：playbook 相关工具、页面、prompt 语义全部清理或归位（见 §7 清理清单）。

### 2.2 非目标

* 不改动 V2 agent 框架内核（ConversableAgent/BAIZE）。

* 不改动 finalize 交付管线、trace 飞轮、intervention 介入机制。

* Phase 1/2 不做多专家并行编排（Phase 3）。

* 不改动 GptsApp 既有管理功能，只做能力扩展（空间绑定/合约关联）。

***

## 3. 核心概念模型

```
场景空间 Workspace = Agent Team（全员空间一等公民）
│
├── Leader Agent（scene-workspace-agent 演化，GptsApp）
│     双重角色：全能选手 + 调度者
│       - 全能选手（默认）：直接持有空间全部资源（skill/mcp/datasource/
│         knowledge_space），在自己的会话里完成问答、分析、写作等日常工作
│         ——资源通道已有：SceneResourceAssembler._assemble_lobby
│       - 调度者（按需）：遇到专业深度/长时运行/需定时交付的工作，派单给专家；
│         也可在自己干活途中就某个子环节派单（dispatch 是工具，不是角色边界）
│     工具：dispatch_to_expert / list_team_experts / get_expert_detail
│           + 现有 start_task / create_intervention / publish_asset 等
│
├── 专家 Expert × N（标准专家 agent + 空间外挂资源表，运行时组装）
│     【标准专家 · 全局 GptsApp】专家"是谁"，跨空间唯一
│       = system_prompt_template(人设+workflow+约束) + icon + llm_config
│       + resource_tool（标准装备/默认兜底）
│     【空间外挂 · 两张关联表】专家"在这个空间带什么外挂"
│       = workspace_expert（成员名册）+ workspace_expert_equipment（外挂明细）
│       同一个法务专家：在合同审查空间挂[合同模板库+文档比对skill]，
│       在合规审计空间挂[法规知识库+合规检查MCP] —— 身份不变，外挂随空间
│     运行时组装：标准装备 ∪ 空间外挂 → 物化注入专家会话（§5.2）
│     空间内直接入口（不经 Leader 转述）：
│       - @专家 / /专家名 派任务
│       - 团队卡片直接发起与专家的对话（workspace 级会话，非任务）
│       - 空间内直接创建/编辑专家（编辑器在空间内，不用跳 agent 管理页）
│     有身份/头像/独立会话，可被 @、可私聊、可查看"它在干嘛"
│
├── 交付合约 Contract × N（playbook 表演化，语义收窄）
│     deliverables：交付物类型 + 外发渠道
│     distill：资产沉淀规则（飞轮）
│     关联：target_app_code → 专家（一个专家可挂多个合约）
│
└── 触发器 Trigger × N（现有模块，改绑）
      target_app_code（替代 target_playbook_id）+ instruction
```

**用户心智**：空间有一个团队（活成员）——Leader 是坐镇的队长，自己能干活也会派活；专家各有专长，可直接对话、可直接派任务、可在空间内维护；合约保证交付，触发器负责唤醒。

### 3.1 概念关系

```
GptsApp(专家) 1 ──── n workspace_expert成员行 ──── n Workspace    （专家可进多个空间）
workspace_expert 1 ──── n workspace_expert_equipment外挂行         （每空间独立装备）
GptsApp(专家) 1 ──── n Contract                                   （专家可挂多个交付合约）
GptsApp(专家) 1 ──── n Trigger                                    （专家可被多个触发器唤醒）
Task         n ──── 1 专家(expert_app_code) + 0..1 合约(contract_id)
```

### 3.2 与现状的对应（迁移映射）

| 现状                              | 新模型                                                     | 迁移方式               |
| ------------------------------- | ------------------------------------------------------- | ------------------ |
| playbook.text\_content + skills | GptsApp（system\_prompt\_template + resource\_tool 标准装备） | 迁移脚本生成 app 定义      |
| playbook.context.resources      | workspace\_expert\_equipment 外挂行（按资源类型拆行）               | 迁移脚本生成外挂           |
| playbook.deliverables + distill | Contract（playbook 表收窄）                                  | 表保留，declaration 删块 |
| playbook.trigger\_json          | Trigger（现有模块）                                           | 字段迁移               |
| trigger.target\_playbook\_id    | trigger.target\_app\_code                               | 加列 + 回填            |
| scene-workspace-agent           | Leader（职责升级）                                            | prompt 模板 + 新工具    |
| roles 块（断头路）                    | Phase 3 编队模板输入                                          | 下线，迁移时告警           |

***

## 4. 数据模型

### 4.1 专家 = 标准 GptsApp（身份层，不动 app 体系结构）

专家**身份**落入 `gpts_app` / `gpts_app_detail` 现有结构：

| 剧本 declaration 块                                                                      | GptsApp 字段                                                  |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| text\_content.role\_definition / goal / workflow / behavior\_constraints / background | `system_prompt_template`（按 §5.3 模板渲染）                       |
| skills                                                                                | `resource_tool` → 语义改为**默认装备**（全局兜底；空间绑定行的装备清单优先，见 §4.2）    |
| name / icon / description                                                             | `app_name` / `icon` / `app_describe`                        |
| llm 配置                                                                                | `llm_config`                                                |
| 运行时                                                                                   | `agent = BAIZE`、`team_mode = auto_plan`（同 dataops-agent 模板） |

命名约定：`app_code = expert_{slug}`（全局唯一身份）；空间内绑定后在该空间可见。

> **身份与装备分离原则**：人设（专家是谁、怎么思考）全局唯一；技能/MCP/知识库（专家用什么干活）按空间绑定行配置。GptsApp.resource\_tool 仅作默认装备兜底，空间装备优先。

### 4.2 空间侧：两张轻量关联表（新）

**①** **`workspace_expert`（成员名册）**——专家 × 空间 的成员关系：

| 字段                           | 类型            | 说明                           |
| ---------------------------- | ------------- | ---------------------------- |
| id                           | int PK        | <br />                       |
| workspace\_id                | int           | uk(workspace\_id, app\_code) |
| app\_code                    | str(128)      | 专家身份（gpts\_app 引用）           |
| role\_hint                   | str(256) NULL | 空间内职责说明（prompt 补丁）           |
| default\_contract\_id        | int NULL      | 默认交付合约                       |
| is\_active                   | bool          | <br />                       |
| gmt\_created / gmt\_modified | datetime      | <br />                       |

**②** **`workspace_expert_equipment`（外挂资源明细）**——成员 × 资源 的外挂关系：

| 字段                           | 类型         | 说明                                            |
| ---------------------------- | ---------- | --------------------------------------------- |
| id                           | int PK     | <br />                                        |
| expert\_id                   | int, index | 引用 workspace\_expert.id                       |
| resource\_type               | str(32)    | skill / mcp / knowledge\_space / datasource   |
| resource\_ref                | str(255)   | 引用目标（技能名/MCP 名/空间资源 name）                     |
| config\_json                 | text NULL  | 外挂级参数（如知识库 top\_k）                            |
| is\_active                   | bool       | <br />                                        |
| gmt\_created / gmt\_modified | datetime   | uk(expert\_id, resource\_type, resource\_ref) |

**为什么独立成表而非塞 workspace\_resource.config\_json**（v4 方案否决）：

* "空间绑定了什么资源"（workspace\_resource）与"专家在这个空间装备了什么"是两个不同关系，混表正是本次重构要消除的概念粘连；

* 外挂明细成行后可索引/可校验/可级联：空间移除某资源时，能直接查出哪些专家装备了它并提示悬空；塞 JSON 则无法校验；

* 运行时组装逻辑直白：`WHERE workspace_id=? AND app_code=?` 取出外挂行物化注入。

**外挂语义**：外挂引用**本空间资源池**（workspace\_resource）中已绑定的资源——空间是注册/治理池，外挂是选配子集，不能凭空引入。空外挂 = 只用专家标准装备（GptsApp.resource\_tool）。

**归属**（`gpts_app` 加一列）：`owner_workspace_id int NULL, index`

* 空间内创建的专家 → `owner_workspace_id` = 当前空间（默认私有，语义上"空间的专家"）。

* 全局专家（agent 管理页创建）→ NULL。

* **空间内编辑规则**（身份/装备分区，编辑器入口在空间内）：

  * **装备区**（技能/MCP/知识库/数据源勾选）：空间级配置，**自由编辑、即时生效、绝不影响其他空间**——这是空间内维护的主要操作面。

  * **身份区**（人设/workflow/约束/模型）：写全局 GptsApp 定义。专家归属本空间时直接保存；全局专家或归属他空间时提示"该专家同时被 N 个空间绑定，身份修改全局生效"，确认放行（不阻断，只知情）。

* 全局 agent 管理页仍然是全量列表视图（可按 owner\_workspace\_id 过滤），但**不再是维护专家的主要入口**。

### 4.2.1 专家直接对话会话（非任务）

复用现有 `WorkspaceConversationLinkEntity`（workspace\_id + conv\_uid + task\_id nullable）：专家卡片发起对话 = 创建 conv\_uid 并落绑定行（task\_id=NULL, config 侧记 expert\_app\_code）。专家直接对话与任务会话隔离：前者是"咨询/协作"，后者是"执行合约"。

### 4.3 存量表变更（仅加列，不改名）

**`server_app_playbook`（语义收窄为 Contract）**：

* 加列 `target_app_code varchar(128) NULL, index`（关联专家）。

* declaration 中 `text_content/skills/context` 块迁出后删除，只留 `deliverables/distill`。

* API 层暴露为 `/contracts`；DB 表名不动。

**`trigger`** **表**：

* 加列 `target_app_code varchar(128) NULL, index`；`target_playbook_id` 改 nullable（过渡期双写，Phase 2 末下线）。

**`server_app_task`**：

* 加列 `expert_app_code varchar(128) NULL, index`（执行者）、`contract_id int NULL`（履行的合约，引用 playbook 表 id）。

* `playbook_id` 过渡期与 contract\_id 同值，Phase 3 后废弃。

### 4.4 迁移脚本

```python
# scripts/migrate_playbook_to_expert.py（幂等可重跑）
for each playbook:
    # 1. 生成专家 GptsApp（text_content → system_prompt_template；skills → resource_tool 标准装备）
    app_code = f"expert_{slugify(playbook.name)}"
    upsert_gpts_app(app_code, owner_workspace_id=playbook.workspace_id, ...)

    # 2. 生成空间成员行 + 外挂行（context.resources 按类型拆行）
    expert = upsert workspace_expert(workspace_id, app_code)
    for res in playbook.context.resources:
        upsert workspace_expert_equipment(expert_id=expert.id,
            resource_type=res.type, resource_ref=res.ref)

    # 3. playbook 收窄为合约
    playbook.declaration = {deliverables, distill}; playbook.target_app_code = app_code

    # 4. 触发器/任务回填
    trigger.target_app_code = app_code (where target_playbook_id = playbook.id)
    task.expert_app_code = app_code; task.contract_id = playbook.id (where task.playbook_id = ...)
```

***

## 5. 运行时架构

### 5.1 执行链路

```
用户消息 → Leader Agent（scene-workspace-agent 会话，已注入空间全量资源）
  │
  ├─ 路径1 Leader 直接执行（默认）：问答/分析/写作/一次性任务
  │     → Leader 用空间绑定的 skill/mcp/datasource 直接干活（现状通道不变）
  │     → 干活途中可就子环节 dispatch_to_expert（混合模式）
  │
  ├─ 路径2 显式派单：@专家名 / /专家名 xxx
  │     → dispatch_to_expert(app_code, description, contract_id?)
  │     → create task(expert_app_code, contract_id)
  │     → expert_runtime.run_task（见 5.2）
  │
  ├─ 路径3 自动分派：Leader 判断需要专业深度/长时运行/定时交付
  │     → 高置信度直接派单并告知；低置信度先给候选确认
  │
  ├─ 路径4 触发器唤醒：Trigger 到点
  │     → create task(expert_app_code=target_app_code, instruction)
  │     → expert_runtime.run_task
  │
  └─ 路径5 专家直接对话（非任务）：团队卡片 → 专家会话
        → 用户与专家直接交流（咨询/讨论/调试专家能力）
        → 对话中可升级："把这个做成任务" → 转路径2
```

**分派判断原则（写入 Leader prompt）**：自己能干且轻量的活直接干；需要专家人设深度、独立上下文、后台长时运行、或按合约定时交付的活派给专家。分派是 Leader 的工具而非职责边界。

### 5.2 `expert_runtime.run_task`（playbook/runtime.py 演化改名）

核心变化只有一处——**执行体从 workspace 默认 agent 换成专家本体**：

```python
# 旧
app_code = workspace.default_agent_app_code or "chat_normal"
# 新
app_code = task.expert_app_code or workspace.default_agent_app_code  # 无专家时回退 Leader（adhoc 任务）
```

保留不动：`_build_user_query`、轮询、`finalize_task`、trace 飞轮。

装配逻辑改造（`_assemble_workbench` 演进，现状是"有 playbook\_id 就注入剧本声明子集"）：

* **外挂组装注入**：读 task.expert\_app\_code → 查 workspace\_expert 成员行 → 查 workspace\_expert\_equipment 外挂行 → 经 `_materialize_declared_item` + 空间池对齐（`_load_pool_by_ref`）物化 → 与专家标准装备（GptsApp.resource\_tool）合并注入。无外挂行 = 仅标准装备。Leader 大厅会话不变（`_assemble_lobby` 全量空间资源）。

* **合约注入**：task.contract\_id 对应的 deliverables/distill 渲染进专家会话 system prompt 动态块（沿用 `_inject_workspace_context` 通道）。

* **role\_hint 注入**：成员行的空间职责说明作为 prompt 补丁注入专家会话（"你在本空间主要负责 …"）。

### 5.3 专家 system prompt 模板（迁移生成 + 新建向导共用）

```
你是 {app_name}，{role_definition}

## 目标
{goal}

## 工作流程
{workflow}                    ← 半确定性约束，企业场景可控性的关键

## 行为约束
{behavior_constraints}

## 交付合约（运行时按 task.contract 动态注入）
{deliverables 要求 + distill 规则}

## 背景
{background}
```

### 5.4 Leader 调度工具（agent\_tools 层改造）

| 工具                   | 参数                                                 | 行为                      |
| -------------------- | -------------------------------------------------- | ----------------------- |
| `dispatch_to_expert` | expert\_name/app\_code, description, contract\_id? | 创建并启动专家任务；返回 task\_id   |
| `list_team_experts`  | –                                                  | 列出空间绑定的专家（名称/描述/技能/活跃度） |
| `get_expert_detail`  | app\_code                                          | 专家人设/合约/近期任务            |

来源：改造现有 `build_playbook_tools`（playbook\_tools.py）与 read\_tools Layer 3（list\_playbooks/get\_playbook\_detail）——见 §7 清理清单。

Leader prompt 更新（scene-workspace-agent.json）——角色定位从"协作者"升级为"队长"：

* **身份块**：你是空间队长，既能亲自使用空间全部资源（技能/数据源/知识库/MCP）完成工作，也领导一支专家团队；分派是你的工具，不是你的边界。

* **执行决策表重排**：路径1 直接执行置顶为默认（现状即如此，保持）；派单路径强调触发条件（专业深度/长时/定时交付/用户点名）。

* 纪律泛化："派单优先复用团队已有专家；确无匹配时建议用户在空间内新建专家（提供引导）；一次性问题直接自己做"。

* 汇总职责：专家任务完成后 Leader 向用户报告结论（只传结论，不回传全文）。

***

## 6. API 与前端设计

### 6.1 API 演进

| 现有                                | 新增/变更                                                        | 说明                                                |
| --------------------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| `building/app` 的 GptsApp CRUD（已有） | 复用                                                           | 专家在此统一定义维护                                        |
| `POST/GET /playbooks`             | `POST/GET/PUT/DELETE /workspaces/{id}/experts`（成员/外挂管理 + 列表） | 本质是 workspace\_expert + equipment 两表管理 + app 摘要聚合 |
| –                                 | `GET /workspaces/{id}/team`                                  | 团队视图（Leader+专家+状态/近期任务）                           |
| –                                 | `POST /workspaces/{id}/experts/dispatch`                     | 显式派单                                              |
| `/playbooks`                      | 语义为 `/contracts`，旧 API 保留过渡                                  | 内部路由新模型                                           |
| `/triggers`                       | target\_playbook\_id → target\_app\_code                     | 触发器绑专家                                            |

### 6.2 前端（三栏信息架构不动，专家一等公民入口）

* **中间 dashboard**："快捷启动剧本"卡片 → **专家团队卡片**（头像/名字/人设/技能/运行中任务数），卡片三个动作：`对话`（直接进专家会话）、`派任务`（@专家）、`编辑`（空间内编辑器）。

* **专家编辑器（空间内，身份/装备两分区）**：

  * 身份区：人设五件套 + 模型（写 GptsApp；跨空间专家编辑前提示影响范围，§4.2 规则）；

  * 装备区：从**本空间资源池**勾选 skill/MCP/知识库/数据源（逐行写 workspace\_expert\_equipment，自由编辑不影响他空间）；装备区顶部一行提示"可选装备来自空间资源池，先到设置页绑定资源"；

  * 合约区：deliverables/distill 配置（写 contract）。

  * 保存编排四处写入（GptsApp / workspace\_expert 成员行 / equipment 外挂行 / contract）。

* **专家直接对话**：右栏 AgentWorkspace 支持切换对话对象（Leader / 各专家），或中间卡片"对话"入口把专家会话载入右栏；会话头部显示当前对话对象身份，可一键切回 Leader。

* **左栏任务流**：任务条目加"执行者"徽标（专家头像+名）。

* **空间设置**："剧本管理"页 → **"团队"页**（成员列表 + 新建/编辑入口 + 合约 + 触发器）。

* **术语**：UI 全面下线"剧本"，改"专家"；deliverables/distill 配置区称"交付合约"。

***

## 7. 剧本概念清理清单（回答"剧本相关工具/产品集成是不是也要清理"）

**是，需要系统性清理。** 全量触点如下：

### 7.1 后端清理

| 位置                                                  | 现状                                                                | 处置                                                                                    |
| --------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `workspace/agent_tools/playbook_tools.py`           | `build_playbook_tools` 整文件                                        | **重写**为 expert\_tools.py（dispatch/list/detail）                                        |
| `workspace/agent_tools/read_tools.py`               | Layer 3 "剧本能力"：list\_playbooks / get\_playbook\_detail            | **替换**为 list\_team\_experts / get\_expert\_detail / list\_contracts                   |
| `workspace/agent_tools/write_tools.py`              | create\_playbook / update\_playbook / delete\_playbook            | **删除**（专家定义归 agent 管理页，不经 Leader 工具）；保留 update\_trigger/delete\_trigger 并改绑 app\_code |
| `workspace/agent_tools/_task_creator.py`            | create\_task\_from\_tool 绑 playbook                               | **改造**为绑 expert\_app\_code + contract\_id                                             |
| `workspace/agent_tools/materialize_deliverables.py` | 合约交付物物化                                                           | **保留**，输入源从 playbook 改 contract（playbook 表）                                           |
| `workspace/agent_tools/context_builder.py`          | 注入 playbook 声明                                                    | **改造**为注入合约块 + 专家团队清单                                                                 |
| `workspace/materializer.py`                         | materialize\_playbook\_declaration / materialize\_playbook\_roles | declaration 物化**删除**（专家能力在 GptsApp 层）；roles 物化**删除**（Phase 3 重做）                      |
| `playbook/runtime.py`                               | run\_task 披皮执行                                                    | **改名迁移** expert\_runtime，执行体切 app\_code                                               |
| `playbook/finalize.py`                              | 交付管线                                                              | **保留**（参数 playbook→contract 语义改名）                                                     |
| `playbook/evolution/` + `playbook/trace/`           | 飞轮（trace 采集/进化分析）                                                 | **保留**，TraceContext.playbook\_id 维度改为 app\_code + contract\_id                        |
| `playbook/api/endpoints.py` + `service/`            | playbook CRUD                                                     | **收窄**为 contract CRUD（删 text\_content/skills/resources 字段）                            |
| `scene-workspace-agent.json` prompt                 | "剧本与触发纪律"章节                                                       | **重写**为"专家与触发纪律"                                                                      |

### 7.2 前端清理

| 位置                                                                                | 处置                                                                                                                                                        |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workspaces/detail/playbooks/` 整目录（client.tsx + detail + visual-editor 六 section） | **原地改造为空间内专家编辑器**（不跳 agent 管理页）：text-content/skills/resources/assets section → 专家定义区（保存写 GptsApp + 绑定）；deliverables/distill section → 合约配置区（保存写 contract） |
| `scene-space.tsx` 快捷启动剧本卡                                                         | 改为专家团队卡片                                                                                                                                                  |
| `scene-workspace-shell.tsx` listPlaybooks                                         | 改 list\_team\_experts                                                                                                                                     |
| `lobby.tsx` / `triggers-table.tsx` / `tasks/create` / `tasks/detail`              | 剧本引用全改专家/合约引用                                                                                                                                             |
| `parse-workspace-view.ts` + locales(zh/en)                                        | 术语替换                                                                                                                                                      |
| `web/src/client/api/playbook/`                                                    | 改 expert/contract API client                                                                                                                              |

### 7.3 路由与命令

* `/剧本名 xxx` 前缀路由 → `/专家名 xxx`（agent/agents/chat 命令路由）。

* `seed_builtin`（builtin\_examples.py 两个内置剧本）→ 迁移为内置**专家模板**（dataops-expert / sre-expert，gyra\_app\_define 新增 JSON）+ 内置合约模板。

### 7.4 保留不动的

* finalize 交付管线、trace/evolution 飞轮、intervention、delivery、artifact——这些是任务生命周期层，与"剧本"概念本就无关。

***

## 8. 任务规划

> Phase 1 纯重组零风险；Phase 2 核心改造；Phase 3 远期编排。每 Phase 独立可交付、可回滚。

### Phase 0 · 准备

| #   | 任务                                           | 产出                                      | 验收         |
| --- | -------------------------------------------- | --------------------------------------- | ---------- |
| 0.1 | 存量 playbook DSL 盘点（roles 块/非标准字段/app 类型资源引用） | 盘点报告                                    | 边界 case 清单 |
| 0.2 | 迁移脚本编写与预演                                    | `scripts/migrate_playbook_to_expert.py` | 测试库回放成功、幂等 |
| 0.3 | GptsApp 体系能力确认：版本管理/详情结构是否满足专家定义             | 确认结论（不足则列入 1.1）                         | –          |

### Phase 1 · 概念归位（数据与 API 重组，运行时不动）

| #   | 任务                                                                                                    | 涉及位置                                                       | 验收                           |
| --- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------- |
| 1.1 | gpts\_app 加列 owner\_workspace\_id；新建 workspace\_expert + workspace\_expert\_equipment 两表及 DAO/Service | building/app / workspace/expert/（新模块）                      | CRUD 单测通过                    |
| 1.2 | 专家外挂物化链路：外挂行 → AgentResource（复用 \_materialize\_declared\_item + 空间池对齐）；团队清单注入 Leader 上下文              | workspace/materializer.py / scene\_resource\_assembler.py  | 绑定专家+外挂后 Leader 可见团队；外挂可物化   |
| 1.3 | playbook/trigger/task 三表加列 + 迁移脚本上线（context.resources → 外挂行拆行）                                        | assets/schema/upgrades/                                    | 存量 100% 映射                   |
| 1.4 | 新 API：/experts 成员与外挂管理、/team、/contracts 视图；专家直接对话会话（WorkspaceConversationLink）                        | workspace/api/                                             | 旧 /playbooks 回归通过；专家会话可创建    |
| 1.5 | 前端：空间内专家编辑器（playbooks 目录原地改造）+ "团队"页 + 术语替换                                                           | web/src/app/workspaces/                                    | 空间内完成专家创建/编辑/合约配置；UI 无"剧本"字样 |
| 1.6 | 前端：dashboard 专家卡片（对话/派任务/编辑三动作）+ 任务"执行者"徽标                                                            | scene-space.tsx / scene-task-rail.tsx                      | 卡片三动作可用（对话走新会话，派单走旧 runtime） |
| 1.7 | Leader 空间资源挂载确认：\_assemble\_lobby 注入 skill/mcp/datasource 全链路验证 + prompt 队长定位升级                       | scene-workspace-agent.json / scene\_resource\_assembler.py | Leader 可直接用空间资源干活（不依赖派单）     |
| 1.8 | 内置剧本 → 内置专家模板迁移                                                                                       | gyra\_app\_define/ + builtin\_examples.py 下线               | seed 链路可用                    |

**出口标准**：用户看到"团队"并能空间内维护专家、直接与专家对话；Leader 确认可直接干活；底下任务执行仍走旧链路；数据已是新结构。

### Phase 2 · 执行体分离 + 剧本概念清退（核心）

| #   | 任务                                                                           | 涉及位置                                                | 验收                            |
| --- | ---------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------- |
| 2.1 | expert\_runtime.run\_task：执行体切 expert\_app\_code                             | playbook/runtime.py → agent/expert\_runtime.py      | 任务会话以专家身份执行                   |
| 2.2 | 外挂组装注入（标准装备 ∪ 空间外挂）+ 合约动态注入 + role\_hint 补丁                                  | scene\_resource\_assembler.py / context\_builder.py | 空间级装备生效；合约进 prompt            |
| 2.3 | Leader 工具改造：dispatch\_to\_expert / list\_team\_experts / get\_expert\_detail | agent\_tools/（playbook\_tools.py 重写等，按 §7.1）        | Leader 完成识别→分派→追踪闭环           |
| 2.4 | scene-workspace-agent prompt 升级 Leader 职责                                    | gyra\_app\_define/scene-workspace-agent.json        | 四路径改专家语义                      |
| 2.5 | 触发器改绑 target\_app\_code（双写→切换→旧列只读）                                          | trigger/ 模块                                         | 存量触发器正确唤醒专家                   |
| 2.6 | `/专家名` 前缀路由                                                                  | agent/agents/chat/ 命令路由                             | 直达专家                          |
| 2.7 | 剧本工具/页面/API 按 §7 清单清退（旧 /playbooks 仅保留 contract 只读视图）                        | 全清单                                                 | 代码库 playbook 概念仅剩 contract 语义 |
| 2.8 | trace/evolution 维度切换 app\_code + contract\_id                                | playbook/trace/ + evolution/                        | 飞轮指标不断档                       |

**出口标准**：专家是真实执行体；Leader 调度闭环；"剧本"从工具、页面、prompt 中消失。

### Phase 3 · 团队编排（远期，独立评审）

| #   | 任务                                                 | 说明                           |
| --- | -------------------------------------------------- | ---------------------------- |
| 3.1 | 多专家任务：parent\_task\_id + assigned\_agents\_json 启用 | Leader 分解→并行分派→汇总            |
| 3.2 | 专家间上下文协议（结论传递非全文）                                  | 依赖 V2 框架子 agent 统一模型         |
| 3.3 | roles 块以"编队模板"回归                                   | 一次派单拉起多专家                    |
| 3.4 | 专家成熟度/跨任务记忆积累                                      | 激活 AgentRoleService.maturity |

### 依赖关系

```
0.x → 1.1/1.2 → 1.3 → 1.4 → 1.5/1.6/1.7（可并行）
    → 2.1（依赖1.3） → 2.2（依赖2.1）；2.3/2.4 可与 2.1 并行 → 2.5/2.6 → 2.7/2.8
    → 3.x（依赖 V2 框架，独立排期）
```

***

## 9. 风险与缓解

| 风险             | 影响                   | 缓解                                                       |
| -------------- | -------------------- | -------------------------------------------------------- |
| 自动分派准确率低       | 派错专家比选错剧本更伤体验        | 高置信度才自动分派；@专家 显式直达兜底；分派前确认                               |
| Token 成本放大     | 专家独立会话 + Leader 汇总双轮 | Leader 只收结论；usage 模块监控                                   |
| 确定性稀释          | 专家自主发挥偏离 workflow    | workflow 写入专家 system prompt 作执行约束；合约层交付校验兜底；trace 飞轮监测   |
| 专家全局复用与空间定制的张力 | 空间内编辑影响多个空间          | owner\_workspace\_id 归属区分；编辑非本空间专家时提示影响范围（被 N 空间绑定）并确认放行 |
| 迁移数据破损         | 存量拆块出错               | 幂等脚本 + 预演 + 原字段保留一个版本周期                                  |
| 概念切换用户困惑       | 老用户找不到"剧本"           | UI 引导"'剧本'已升级为'专家团队'"                                    |

***

## 10. 整体验收标准

1. **空间内建专家**：在空间"团队"页直接创建"数据周报专家"（人设+技能+合约+每周一 9 点触发器），全程不离开空间；到点自动执行，任务列表显示执行者为该专家，交付物按合约外发。
2. **Leader 直接干活**：对 Leader 说"查一下本周订单量"，Leader 直接用空间数据源回答，不创建任务不派单；对 Leader 说"把上周核心指标整理成周报发邮件"，Leader 判断需合约交付，分派给数据周报专家并汇报结论。
3. **专家直接对话**：从团队卡片进入与专家的直接对话讨论分析思路，随后说"把这个做成每周任务"，无缝转为合约任务。
4. **外挂随空间**：全局创建"法务专家"，绑定进合同审查空间（外挂：合同模板库+文档比对 skill）与合规审计空间（外挂：法规知识库+合规检查 MCP）；同一专家在两空间执行任务，注入装备各自独立，互不影响。
5. 存量 playbook 全部迁移为"专家 + 绑定 + 合约"，旧任务详情/交付记录/触发器无回归。
6. 代码库与 UI 中 playbook/剧本 概念仅剩 contract 只读视图（过渡期）。

<br />
