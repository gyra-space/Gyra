# Agent Team Space Refactor Implementation Plan

> 对应设计：[2026-09-04-agent-team-space-refactor-design.md](../specs/2026-09-04-agent-team-space-refactor-design.md)（v5）
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 场景空间从「剧本驱动」演进为「多 Agent 团队」：1 Leader（全能选手+调度者）+ N 专家（GptsApp 身份 + 空间外挂装备）+ 交付合约 + 触发器。

**Core Model:**

```
专家身份 = GptsApp（全局，persona/icon/llm_config/resource_tool 标准装备）
空间成员 = workspace_expert（workspace_id + app_code + role_hint + default_contract_id）
空间外挂 = workspace_expert_equipment（expert_id + resource_type + resource_ref，逐行）
运行时组装 = 标准装备 ∪ 空间外挂行 → 物化注入专家会话
合约 = playbook 表语义收窄（deliverables + distill + target_app_code）
```

**Tech Stack:** FastAPI + SQLAlchemy（gyra_serve）、Next.js 15 + React 18 + AntD 5（web/）、GptsApp/BAIZE 运行时。

## Global Constraints

- 不新建专家实体表：身份复用 GptsApp；空间侧仅加 `workspace_expert` / `workspace_expert_equipment` 两张轻量关联表。
- 外挂只能引用本空间资源池（workspace_resource）已绑定资源——空间=注册/治理池，外挂=选配子集。
- Phase 1 不动运行时执行链路（仍走 playbook runtime），所有改动向后兼容。
- 迁移脚本必须幂等可重跑，原字段保留一个版本周期再物理删除。
- 保留不动：finalize 交付管线、trace/evolution 飞轮、intervention、delivery、artifact。
- 术语纪律：新代码/UI 禁用「剧本/playbook」表述（contract 内部路由除外）；专家装备一律称「外挂」。

---

## Phase 0 · 准备（无代码变更）

### Task 0.1: 存量 playbook DSL 盘点

- [ ] **Step 1:** 扫描存量 playbook declaration_json，输出报告：
  - `roles` 块使用率（决定下线告警文案）
  - 非标准字段清单
  - `context.resources` 中 `type="app"` 引用清单（迁移目标不同）
- [ ] **Step 2:** 边界 case 清单评审确认

**产出：** 盘点报告（附迁移边界决策）

### Task 0.2: 迁移脚本预演

- [ ] **Step 1:** 编写 `scripts/migrate_playbook_to_expert.py`（伪代码见设计 §4.4），幂等（upsert by app_code / uk 约束）
- [ ] **Step 2:** 测试库回放，校验：GptsApp 生成、成员行+外挂行拆行、合约收窄、trigger/task 回填
- [ ] **Step 3:** 回滚预演（备份→恢复）

**产出：** 可上线迁移脚本

### Task 0.3: GptsApp 体系能力确认

- [ ] **Step 1:** 确认 `gpts_app_detail` 详情结构可承载 system_prompt_template 五件套渲染结果
- [ ] **Step 2:** 确认版本管理/发布链路是否满足专家定义演进；不足列入 Task 1.1 范围

---

## Phase 1 · 概念归位（数据与 API 重组，运行时不动）

### Task 1.1: 数据层 —— 两张关联表 + 归属列

**Files:**
- Create: `packages/gyra-serve/src/gyra_serve/workspace/expert/__init__.py`（新模块）
- Create: `packages/gyra-serve/src/gyra_serve/workspace/expert/models/entities.py`
- Create: `packages/gyra-serve/src/gyra_serve/workspace/expert/dao/expert_dao.py`
- Create: `packages/gyra-serve/src/gyra_serve/workspace/expert/service/expert_service.py`
- Create: `packages/gyra-serve/src/gyra_serve/assets/schema/upgrades/（DDL 升级文件，按现有惯例）`
- Modify: `packages/gyra-serve/src/gyra_serve/building/app/models/models.py`（gpts_app 加列）

- [ ] **Step 1:** 新增 `workspace_expert` 表：id / workspace_id / app_code / role_hint / default_contract_id / is_active / gmt_created / gmt_modified；uk(workspace_id, app_code)
- [ ] **Step 2:** 新增 `workspace_expert_equipment` 表：id / expert_id / resource_type / resource_ref / config_json / is_active / 审计字段；uk(expert_id, resource_type, resource_ref)
- [ ] **Step 3:** `gpts_app` 加列 `owner_workspace_id int NULL, index`
- [ ] **Step 4:** DAO + Service CRUD（含按 workspace 查团队、按 expert 查外挂）
- [ ] **Step 5:** 单元测试：CRUD、唯一约束、级联查询
- [ ] **Step 6:** Commit

**验收：** CRUD 单测通过；建表脚本幂等。

### Task 1.2: 外挂物化链路 + 团队清单注入

**Files:**
- Modify: `packages/gyra-serve/src/gyra_serve/workspace/materializer.py`
- Modify: `packages/gyra-serve/src/gyra_serve/workspace/scene_resource_assembler.py`

- [ ] **Step 1:** 新增 `assemble_expert_equipment(workspace_id, app_code) -> list[AgentResource]`：查外挂行 → `_materialize_declared_item` + `_load_pool_by_ref` 空间池对齐物化；无外挂返回空列表
- [ ] **Step 2:** 悬空校验：外挂引用不在空间池时记 warning 并跳过（不阻断执行）
- [ ] **Step 3:** `_assemble_lobby` 增加团队清单块（专家名/职责/合约摘要）注入 Leader 上下文
- [ ] **Step 4:** 单测：物化正确性、悬空处理、清单注入
- [ ] **Step 5:** Commit

**验收：** 绑定专家+外挂后，Leader 上下文可见团队清单；外挂可物化为 AgentResource。

### Task 1.3: 三表加列 + 迁移脚本上线

**Files:**
- Modify: playbook / trigger / task 实体与 DDL 升级文件
- Modify: `scripts/migrate_playbook_to_expert.py`（来自 0.2）

- [ ] **Step 1:** `playbook` 加列 `target_app_code str(128) NULL, index`
- [ ] **Step 2:** `trigger` 加列 `target_app_code str(128) NULL`
- [ ] **Step 3:** `task` 加列 `expert_app_code str(128) NULL, index` / `contract_id int NULL, index`
- [ ] **Step 4:** 上线迁移脚本；抽样人工核对（人设渲染、外挂拆行、trigger 回填）
- [ ] **Step 5:** Commit

**验收：** 存量 playbook 100% 映射为「专家 + 成员行 + 外挂行 + 合约」；旧字段保留。

### Task 1.4: 空间 API —— experts/team/contracts + 专家直接对话

**Files:**
- Create: `packages/gyra-serve/src/gyra_serve/workspace/api/expert_api.py`
- Modify: `packages/gyra-serve/src/gyra_serve/workspace/api/routers.py`（注册）

- [ ] **Step 1:** `POST/GET/PUT/DELETE /workspaces/{id}/experts`：成员+外挂管理（创建专家时编排写入 GptsApp + 成员行 + 外挂行）
- [ ] **Step 2:** `GET /workspaces/{id}/team`：团队视图（Leader + 各专家 + 运行中任务数）
- [ ] **Step 3:** `POST /workspaces/{id}/experts/dispatch`：显式派单（内部路由现有 task 创建）
- [ ] **Step 4:** `GET /workspaces/{id}/contracts`：合约只读视图（playbook 收窄后）
- [ ] **Step 5:** 专家直接对话会话：创建 conv 落 `WorkspaceConversationLinkEntity`（task_id=NULL，config 记 expert_app_code）
- [ ] **Step 6:** 旧 `/playbooks` API 保持可用（回归测试通过）
- [ ] **Step 7:** Commit

**验收：** 空间内一步创建专家（含外挂/合约）；专家会话可创建；旧 API 无回归。

### Task 1.5: 前端 —— 空间内专家编辑器 + 团队页 + 术语替换

**Files:**
- Modify: `web/src/app/workspaces/detail/playbooks/`（原地改造，后续重命名目录）
- Modify: `web/src/client/api/playbook/` → `web/src/client/api/expert/`

- [ ] **Step 1:** visual-editor 六 section 重排为三分区：**身份区**（人设五件套+模型，写 GptsApp；跨空间专家提示影响范围）/ **外挂区**（从本空间资源池勾选，逐行写 equipment；顶部提示"可选装备来自空间资源池"）/ **合约区**（deliverables/distill）
- [ ] **Step 2:** 「团队」页：成员列表 + 新建/编辑/解绑 + 合约 + 触发器入口
- [ ] **Step 3:** 全 UI 术语替换：剧本 → 专家；引导语「'剧本'已升级为'专家团队'」
- [ ] **Step 4:** Commit

**验收：** 空间内完成专家创建/编辑/外挂/合约配置；UI 无「剧本」字样。

### Task 1.6: 前端 —— 专家卡片三动作 + 任务执行者徽标

**Files:**
- Modify: `web/src/app/workspaces/detail/scene-space.tsx`（快捷启动剧本卡片 → 专家团队卡片）
- Modify: `web/src/app/workspaces/detail/scene-task-rail.tsx`
- Modify: `web/src/app/workspaces/detail/agent-workspace.tsx`（对话对象切换）

- [ ] **Step 1:** 专家卡片：头像/名字/role_hint/外挂摘要/运行中任务数；三动作 `对话`（创建专家会话载入右栏）/ `派任务`（@专家，走旧 runtime）/ `编辑`（空间内编辑器）
- [ ] **Step 2:** 右栏对话对象切换：Leader ↔ 专家；会话头显示当前对象身份；专家对话中「把这个做成任务」转派单
- [ ] **Step 3:** 任务条目加执行者徽标（专家头像+名）
- [ ] **Step 4:** Commit

**验收：** 卡片三动作可用；专家直接对话闭环。

### Task 1.7: Leader 空间资源挂载确认 + prompt 队长定位

**Files:**
- Modify: `packages/gyra-serve/src/gyra_serve/building/gyra_app_define/scene-workspace-agent.json`
- Modify: `packages/gyra-serve/src/gyra_serve/workspace/scene_resource_assembler.py`（如需）

- [ ] **Step 1:** 验证 `_assemble_lobby` 大厅链路注入 skill/mcp/datasource 全量空间资源（补缺漏）
- [ ] **Step 2:** prompt 身份块升级：「你是空间队长，既能亲自使用空间全部资源完成工作，也领导专家团队；分派是工具不是边界」；执行决策表路径1直接执行置顶
- [ ] **Step 3:** 端到端验证：Leader 直接回答需查数的问题（不建任务不派单）
- [ ] **Step 4:** Commit

**验收：** Leader 可直接用空间资源干活。

### Task 1.8: 内置剧本 → 内置专家模板迁移

**Files:**
- Create: `packages/gyra-serve/src/gyra_serve/building/gyra_app_define/dataops-expert.json` / `sre-expert.json`
- Modify: seed_builtin 链路（`builtin_examples.py` 改为模板数据，暂不删文件）

- [ ] **Step 1:** 两个内置剧本转 GptsApp JSON 模板（人设五件套 → system_prompt_template）
- [ ] **Step 2:** seed 流程：注册专家 + 写成员行 + 外挂行 + 内置合约模板
- [ ] **Step 3:** Commit

**验收：** 新空间 seed 出专家团队；模板可用。

**Phase 1 出口标准：** 用户看到「团队」并能空间内维护专家、直接与专家对话；Leader 可直接干活；任务执行仍走旧链路；数据已是新结构。

---

## Phase 2 · 执行体分离 + 剧本概念清退（核心）

### Task 2.1: expert_runtime —— 执行体切专家本体

**Files:**
- Modify: `packages/gyra-serve/src/gyra_serve/playbook/runtime.py` → 重命名 `packages/gyra-serve/src/gyra_serve/agent/expert_runtime.py`

- [ ] **Step 1:** `run_task` 执行体切换：`app_code = task.expert_app_code or workspace.default_agent_app_code`（过渡兼容）
- [ ] **Step 2:** 删除 `materialize_playbook_roles` 调用（断头路下线）
- [ ] **Step 3:** 任务会话归属：WorkspaceConversationLink 写执行体 app_code
- [ ] **Step 4:** 回归：finalize 交付管线/trace 飞轮不变
- [ ] **Step 5:** Commit

**验收：** 任务会话以专家身份执行（会话记录 app_code 为专家）。

### Task 2.2: 外挂组装注入 + 合约/role_hint 动态注入

**Files:**
- Modify: `scene_resource_assembler.py`（`_assemble_workbench` 改造）
- Modify: `context_builder.py`（如需）

- [ ] **Step 1:** workbench 装配：task.expert_app_code → 外挂行物化 ∪ 标准装备（resource_tool）→ 注入
- [ ] **Step 2:** 合约注入：task.contract_id → deliverables/distill 渲染进 system prompt 动态块（`_inject_workspace_context` 通道）
- [ ] **Step 3:** role_hint 注入：「你在本空间主要负责 …」prompt 补丁
- [ ] **Step 4:** 单测 + 端到端（法务专家双空间场景）
- [ ] **Step 5:** Commit

**验收：** 同一专家在两个空间执行任务，注入外挂各自独立；合约进入 prompt。

### Task 2.3: Leader 工具改造

**Files:**
- Modify: `packages/gyra-serve/src/gyra_serve/agent_tools/playbook_tools.py` → 重写为 `expert_tools.py`
- Modify: `packages/gyra-serve/src/gyra_serve/agent/service/tools/read_tools.py` / `write_tools.py`

- [ ] **Step 1:** 新工具 `list_team_experts`（团队+合约摘要）/ `get_expert_detail` / `dispatch_to_expert`（含幂等、await_user_input 模式复用 start_task）
- [ ] **Step 2:** read_tools Layer 3：list_playbooks/get_playbook_detail → list_team_experts/get_expert_detail；search_reusable_playbooks → search_reusable_experts
- [ ] **Step 3:** write_tools：create/update/delete_playbook **删除**（专家定义归空间编辑器/agent 管理页）
- [ ] **Step 4:** Commit

**验收：** Leader 完成「识别→分派→追踪」闭环。

### Task 2.4: Leader prompt 四路径改专家语义

**Files:**
- Modify: `gyra_app_define/scene-workspace-agent.json`

- [ ] **Step 1:** 「剧本与触发纪律」章节 → 「专家与触发纪律」：@专家直达；自动分派高置信度才执行否则给候选确认；无匹配专家时引导空间内新建
- [ ] **Step 2:** 汇总职责：专家任务完成后只回传结论向用户汇报
- [ ] **Step 3:** Commit

### Task 2.5: 触发器改绑

**Files:**
- Modify: `packages/gyra-serve/src/gyra_serve/trigger/`

- [ ] **Step 1:** 触发创建任务时 target_app_code 优先（双写过渡期），写入 task.expert_app_code
- [ ] **Step 2:** 存量触发器验证：到点正确唤醒专家
- [ ] **Step 3:** 旧 target_playbook_id 列转只读
- [ ] **Step 4:** Commit

### Task 2.6: `/专家名` 前缀路由

**Files:**
- Modify: agent/agents/chat/ 命令路由

- [ ] **Step 1:** `/剧本名 xxx` → `/专家名 xxx`：匹配空间成员行 → dispatch
- [ ] **Step 2:** Commit

### Task 2.7: 剧本概念全量清退（按设计 §7 清单）

**Files:**
- 后端：`playbook_tools.py`（已 2.3）、read/write_tools（已 2.3）、playbook API（收窄为 contract 只读）、`materializer.py`（materialize_playbook_declaration/roles 删除）、scene-workspace-agent.json（已 2.4）、`builtin_examples.py`（删除）、`merge_skill`（改绑 app_code）
- 前端：`workspaces/detail/playbooks/` 目录重命名 `experts/`；scene-space/scene-task-rail/lobby-home/triggers-table/tasks 页面换引用；`client/api/playbook/` 删

- [ ] **Step 1:** 后端清退（playbook 仅剩 contract 语义）
- [ ] **Step 2:** 前端清退（目录重命名 + 引用全换）
- [ ] **Step 3:** 全仓 grep `playbook` 残留审查（白名单：contract 内部路由、迁移脚本、旧字段注释）
- [ ] **Step 4:** Commit

### Task 2.8: trace/evolution 维度切换

**Files:**
- Modify: `packages/gyra-serve/src/gyra_serve/playbook/trace/` + `gyra/evolution/`

- [ ] **Step 1:** 埋点维度 playbook_id → app_code + contract_id（双写一个版本周期）
- [ ] **Step 2:** 飞轮指标看板验证不断档
- [ ] **Step 3:** Commit

**Phase 2 出口标准：** 专家是真实执行体；Leader 调度闭环；「剧本」从工具、页面、prompt 中消失（仅剩 contract 只读视图）。

---

## Phase 3 · 团队编排（远期，独立评审）

仅列方向，实施前独立设计评审：

- [ ] 多专家任务：parent_task_id + assigned_agents_json 启用（Leader 分解→并行分派→汇总）
- [ ] 专家间上下文协议（结论传递非全文），依赖 V2 框架子 agent 统一模型
- [ ] roles 块以「编队模板」回归（一次派单拉起多专家）
- [ ] 专家成熟度/跨任务记忆积累（激活 AgentRoleService.maturity）

---

## 依赖关系

```
0.1 → 0.2 → 0.3
    → 1.1 → 1.2 / 1.3 → 1.4 → 1.5 / 1.6 / 1.7（可并行）→ 1.8
    → 2.1（依赖 1.3）→ 2.2（依赖 2.1、1.2）；2.3 / 2.4 可与 2.1 并行
    → 2.5 / 2.6 → 2.7 → 2.8
    → 3.x（依赖 V2 框架，独立排期）
```

## 整体验收（对应设计 §10）

- [ ] 空间内建专家（人设+外挂+合约+触发器），全程不离开空间；到点自动执行、按合约外发
- [ ] Leader 直接干活（查数不建任务）；需合约交付时正确分派并汇报结论
- [ ] 专家直接对话 → 无缝转合约任务
- [ ] 法务专家双空间外挂隔离验证
- [ ] 存量迁移无回归；代码库 playbook 概念仅剩 contract 只读视图
