# 场景空间统一设计(Scenario Workspace Unification)

> 分支:`feat/workspace-unification`
> 状态:设计文档(阶段 0 产物),用作团队认知对齐与后续 5 个实现阶段的纲领。
> 一句话主张:**把「对话」和「剧本」从两个并列产品单元,统一成「执行(Run)」的两种配置,共用同一个飞轮闭环。**

---

## 1. 背景与问题诊断

### 1.1 现状:两套理念在三层并存

场景空间当前由两套不同来源的设计理念合流而成,「两套」嵌在三个层面,互相纠缠:

| 层 | 理念 A | 理念 B | 缝在哪 |
|---|---|---|---|
| 设计叙事 | 产品-空间叙事(6 份 SCENARIO_WORKSPACE_*):「把产品单元从对话升级为**环境**」,九实体 + 三大机制(协作/进化/交付) | 工程-循环/图叙事(Three_Layer_Loop + From_Loop_To_Graph):「三层 Loop + 五环飞轮」,场景空间=L3 Loop 载体 | 词汇不通:产品层从不说「飞轮/图工程」,工程层从不提「九实体」。增长机制对不齐--「进化」(三大机制)与「飞轮」(五环)映射不干净 |
| 执行范式 | 编排驱动(骨架):trigger→task→playbook→runtime→artifact→delivery→intervention→trace→evolution,声明式、有交付/人环/飞轮 | 对话驱动(肌肉):agent/conversation/subagent/skill/mcp,即时、LLM 自主、异步子 agent | 非平行而是嵌套(runtime 调 app_chat_v3),但自由对话不进飞轮 trace,反馈闭环断 |
| 历史遗留 | 新 workspace(场景空间=工作单元,在跑) | 旧 scene(SceneProfile=Agent 配置附件,标 DEPRECATED 未删) | 半统一债:`/api/scenes` 返回内存假数据、`/scene` 孤儿页、`tab-scenes` 残留、三种 scene 含义打架 |

**关键背景**:scene→workspace 的「并存不删」是设计讨论中明确的决策(§7.9:「我希望并存,因为现有模块是场景空间的基础原子能力」)。复用原子能力是对的,但「不删旧的」+「两套叙事没对齐」攒下了债。

### 1.2 四个没填平的缝

| 缝 | 描述 | 根因? |
|---|---|---|
| **缝 1** | 自由对话不进飞轮 trace。被 playbook 调用的 agent 挂 TraceCollector→产 ExecutionTrace→喂演化/成熟度;自由对话只有 `gyra.util.tracer`(可观测性),不产飞轮 trace。同一 agent 经剧本跑就长大、自由聊就不长大 | **是,根因** |
| **缝 2** | 剧本把「声明」和「后置钩子」绑死。后置处理(artifact/delivery/intervention/distill)硬编码在 `run_task`,独属剧本;adhoc 任务跑完啥也没有 | 直觉命中 |
| **缝 3** | UI 硬拼。对话只在工作台 Tab,切走就消失;剧本页只能管不能跑;「跑个周报」三条路;左栏混排大厅会话和剧本任务;导览卡自己并列「随便问问」和「跑一个剧本」 | 用户最直接感受 |
| **缝 4** | 历史债 + 命名复用。旧 scene 包没删干净;`TaskService.spawn`(建子任务记录不跑)与 `spawn_agent_task`(起子 agent 立即跑)同名不同义;`flow`(AWEL DAG)与 `playbook`(策略声明)两套声明式执行无调用关系并存 | 收尾 |

`From_Loop_To_Graph` 文档自己诊断过现状:「`playbook/runtime.py` 每个 Task 只启动一个 Agent 在一个大 Loop 里自主跑完 + 末尾 gate + 强制 distill,这正是 Loop 固有问题的精确投影」--与「剧本越来越像子 agent」的直觉是同一句话。

---

## 2. 统一设计理念

### 2.1 中心思想

> **场景空间 = 一个持续运转的业务场景,由四要素构成:资产(用什么)→ 触发(何时做)→ 执行(怎么做)→ 沉淀(越用越厚)。对话和剧本都是「执行」的形态,共用同一个飞轮。**

这套话术同时吃掉两套叙事:「四要素」对应产品层九实体(精简归并),「执行统一 + 飞轮唯一」对应工程层三层 Loop + 五环飞轮。一套词,不再两套。

### 2.2 四要素模型

| 要素 | 回答 | 对应概念 |
|---|---|---|
| **资产 Asset** | 用什么 | ECP(事实)/workspace_asset(经验)/playbook(能力)/knowledge(索引) |
| **触发 Trigger** | 何时做 | timer/webhook/alert/manual,触发源是字段不是类型 |
| **执行 Run** | 怎么做 | 对话(即时 Run)+ 剧本(可复用 Run),统一容器复用 `server_app_task` |
| **沉淀 Flywheel** | 越用越厚 | trace→演化、记忆→沉淀、成熟度→复用,所有 Run 都进 |

### 2.3 执行统一(核心)

「执行」从被对话和剧本瓜分的状态解放出来,成为一等公民:

- **对话 Chat** = 执行的一种形态:即时 Run,无剧本,默认轻量钩子
- **剧本 Playbook** = 可复用的策略声明(skills/resources/gates/roles)+ 一组默认钩子
- **任务 Task** = Run 的容器(底层复用 `server_app_task`,已有 `type=adhoc`);有剧本的 Run 多了声明约束

剧本退化成「可复用的执行预设」,对话退化成「即时的执行」,两者不再是两条路,而是同一条路的两种用法。

### 2.4 飞轮唯一

所有 Run 都进同一个飞轮闭环(填缝 1):trace→演化(剧本改进提议)、记忆→沉淀(经验资产)、成熟度→复用(agent 成长)。不再有「经剧本跑就长大、自由聊就不长大」的割裂。

### 2.5 钩子独立(填缝 2)

后置处理(artifact/delivery/intervention/distill)从 `run_task` 硬编码提成独立 Hook,任何 Run 可挂。剧本声明「默认钩子」,adhoc Run 可选挂。「跑完发飞书」「跑完挂 review」不再需要建完整剧本。

---

## 3. 两套叙事对齐

| 产品层旧词 | 工程层旧词 | 统一词 |
|---|---|---|
| 进化(三大机制之一) | 飞轮(五环) | **飞轮**(用工程层词,有协议实现) |
| 协作 + 交付(三大机制) | (无对应) | 归入「执行 + 钩子」:协作=执行+人环,交付=artifact+delivery |
| (无对应) | Trace 环 + 评测环 | 归入飞轮的「反馈」环节 |
| 九实体 | (无对应) | 精简为四要素 + Run + 钩子 + 资产 |
| 环境隐喻 | L3 Loop 载体 | **场景空间 = 持续运转的业务场景**(两个隐喻是一回事,统一表述) |

---

## 4. 概念重新定位

| 概念 | 现状 | 重新定位 | 改动量 |
|---|---|---|---|
| 执行 Run(产品语言) | 不存在,被 task 和 chat 瓜分 | 统一抽象:所有 agent 执行都是一次 Run,底层复用 `server_app_task` | 小:对话也建 adhoc task |
| 对话 Chat | 和剧本并列的两条路之一 | 执行的一种形态:即时 Run | 概念归位 |
| 剧本 Playbook | 声明 DSL + 后置回调链(绑死) | 回归纯策略声明,带一组默认钩子 | 拆:钩子逻辑提出 |
| 任务 Task | 顶层工作单元 | Run 的容器,有剧本的 Run 多声明约束 | 概念澄清 |
| 钩子 Hook | 藏在 runtime | 独立一等公民,任何 Run 可挂 | 中:配置从 declaration 提到 Run |
| 飞轮 Flywheel | 工程层词,与「进化」并列 | 唯一增长机制,所有 Run 都进 | 统一 trace 注入点 |
| ECP | 事实资产,UI 错位 | 不变,UI 归位资产层 | UI |
| 资产 Asset | 四类 | 不变 | 无 |
| flow(AWEL DAG) | 与 playbook 并存 | 图工程载体:playbook 默认 Agentic,声明 graph 的 Run 走显式图 | 叙事,不 merged |

---

## 5. flow vs playbook 关系

执行有两种模型,不是两个产品:

- **Loop 型(默认)**:playbook,agent 自主编排,保留 Agentic 红利
- **Graph 型(可选)**:flow(AWEL DAG),显式编排图,声明 graph 的 Run 走此路

这是 `From_Loop_To_Graph`「graph 可选、组织升级非替代」的落地。未来一个 Run 可「loop 跑前半段 + graph 跑关键审批段 + loop 跑收尾」,因为共享同一 Run 容器和飞轮。本次不合并,仅明确关系。

---

## 6. 六阶段路线图

| 阶段 | 内容 | 验证 | 依赖 |
|---|---|---|---|
| 0 统一叙事 | 本文档 | 术语统一 | 无 |
| 1 统一 trace(根因) | TraceCollector 上移到执行入口,对话进飞轮 | 自由对话后 trace 表有记录、成熟度/资产有变化 | 无(支持 task_id=None) |
| 2 钩子独立 | 后置处理提成 Hook,剧本拆声明 | adhoc Run 能挂 delivery,剧本 Run 行为不变 | 与 3 协同 |
| 3 对话进 task 容器 | 对话建 adhoc task,进 Run 体系 | 对话在执行列表可见,能挂 trace/hook | 1、2 |
| 4 UI 重组 | 以执行为中心,顶栏重组,左栏统一 Run | 跑周报一条路径,切 Tab 对话不消失 | 3 |
| 5 清债+改名 | 删 scene 旧包/孤儿页,spawn 改名 | 旧路由 404,无残留引用 | 随时可做 |
| 6 未来(不做) | flow 融合、多 agent 协作、飞轮质量门禁 | - | - |

推荐顺序:0 → 1 → 2 → 3 → 4 → 5。阶段 1 是根因必须先做;2/3 可协同;4 依赖 3;5 随时。

---

## 7. 不做(边界)

- 不造新 Run 表:复用 `server_app_task`
- 不合并 flow 和 playbook:仅叙事明确关系
- 不重构飞轮协议层:`asset_protocols.py` 六协议四资产不动
- 不碰 RBAC 两套分离:全局管 resource / 场景空间管 3 角色,保持
- 不强推图工程:graph 可选,默认 Agentic

---

## 附:关键代码位置(实现时定位)

- 编排枢纽:`packages/gyra-serve/src/gyra_serve/playbook/runtime.py`(`run_task`,trace 初始化 L109-123,后置物化 L263-417)
- 执行入口:`packages/gyra-serve/src/gyra_serve/agent/agents/controller.py`(`multi_agents.app_chat_v3`)
- 资源装配:`packages/gyra-serve/src/gyra_serve/workspace/scene_resource_assembler.py`(lobby/workbench 分支)
- 飞轮协议:`packages/gyra-core/src/gyra/distributed/asset_protocols.py`
- trace 采集:`packages/gyra-serve/src/gyra_serve/playbook/trace/`
- 前端工作台:`web/src/app/workspaces/detail/client.tsx`(顶栏)、`scene-workspace-shell.tsx`(三栏)、`scene-task-rail.tsx`(左栏)
- 旧 scene 残留:`packages/gyra-serve/src/gyra_serve/scene/`、`web/src/app/scene/`、`web/src/app/application/app/components/tab-scenes.tsx`
