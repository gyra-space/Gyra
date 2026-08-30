# ECP 模块功能设计（业务层高阶 llm-wiki）

版本：v1.0（2026-07-28）
上位文档：`docs/ECP.md`（协议设计）、`docs/ECP-implementation-design.md`（技术落地）

---

## 1. 产品定位

**ECP 是面向业务层的高阶 llm-wiki。** DB / API / 知识库是原子技术资产——
它们各自已经是（或即将是）技术维度的 llm-wiki 管理单元；ECP 站在它们之上，
面向业务问题（"这个数字是什么口径、能不能信、从哪来"）。

对应关系：

| llm-wiki 知识空间（技术层） | ECP 语义资产（业务层） |
|---|---|
| 原始材料 = 文档文件 | 原始材料 = **技术资产引用**（DB 连接/API/raw 文件） |
| wiki 页 = 文档知识 | 硬语义 = **业务口径**（entity/metric/relation/dimension），软知识 = 业务词条 |
| graph = 页面关联 | graph = **数字→口径→绑定→物理字段的血缘** |
| lint = 结构健康 | lint = **语义健康**（口径漂移/矛盾/未命中聚类） |
| 信任 = drift 检测/信任分 | 信任 = **确认门槛 + 版本冻结 + ✅/⚠️ 标记** |

一句话：**知识空间管"文档里说了什么"，ECP 管"业务数字是什么意思、能不能信"。**

两条铁律贯穿全部功能设计：
- 数字只能来自硬语义层，叙述可以引用软知识层
- 一切能力资产化：口径、别名、维度值、join 路径、解析缓存全部走
  proposed → confirmed → versioned

## 2. 信息架构

页面 `/ecp`，顶部固定：**workspace 切换 + 北极星状态条**
（✅ confirmed 对象数 / 🟡 待确认数 / 解析缓存命中率 / 本周兜底触发率），
下方 8 个视图 tab。与知识空间的 raw/wiki/graph/lint/settings 分层同构：

```
┌────────────────────────────────────────────────────────────────┐
│ workspace: [default ▾]   ✅ 42  🟡 7待确认  缓存命中 68%  ⚠️↓  │
├────────────────────────────────────────────────────────────────┤
│ 总览 │ 收件箱 │ 资产层 │ 硬语义 │ 软知识 │ 血缘图 │ 巡检 │ 设置 │
└────────────────────────────────────────────────────────────────┘
```

### 2.1 总览（Overview）

ECP 的"资产固化程度仪表盘"——回答"我们的业务语义资产积累到什么程度了"。

| 区块 | 内容 | 数据来源 |
|---|---|---|
| 资产厚度 | 四类对象 confirmed/proposed 计数（堆叠条） | `GET /objects`（已有✅） |
| 北极星 | ⚠️→✅ 转化率趋势（按周） | op_log 聚合（🔧 P2） |
| 待办 | 待确认 Top 5（按影响面）、漂移告警数、未命中聚类数 | inbox / lint（部分✅） |
| 资产健康 | 各资产 ref 的就绪/漂移状态点阵 | `GET /assets`（✅）+ lint |

### 2.2 收件箱（Inbox）— 确认动线核心

确认人的默认工作界面（P0 已有基础版，需增强）：

- 提案卡片：类型徽章 + name/aliases + **自然语言口径解释** + **证据引文**
  （文档原文 quote，P3 文档双路后充实）+ binding 目标 + 置信度
- 操作：✅ 确认 / ❌ 否决 / ✏️ 改后确认（编辑 payload 后以新版本确认，
  API 已支持✅，UI 待做🔧）/ 维度值提案的逐行值映射编辑（🔧 P2）
- 首日规则视图：只显示影响最大的 3-5 个口径问题（🔧 P2，"全部"可展开）
- 排序：影响面（被引用次数，P2 边表后精确；当前按来源+时间近似✅）

### 2.3 资产层（Assets）— 原始资产管理

管理"ECP 关注哪些技术资产"（`ecp_asset_ref` 注册表，后端✅）：

| 资产类型 | 登记方式 | 状态展示 | 操作 |
|---|---|---|---|
| DB 数据源 | 选已有 datasource（下拉来自 datasource 模块） | 就绪检查（schema 学习状态/表数）、漂移告警、最近检查时间 | 生成提案、查看引用它的语义对象 |
| 知识空间 | 选已有 space slug | ingest 状态、文档数 | 设为证据来源、打开空间 |
| 文档（单文件） | 上传到 ECP space（走 knowledge 管线） | ingest 状态 | 查看解析出的 wiki/evidence |
| API | 表单登记（url/method/schema）（P3） | 连通性测试 | 生成提案（P3） |

每行资产展开：基本信息 + readiness 检查项（逐项 ✅/❌）+ 关联统计
（该资产产出/支撑了多少个语义对象）。

### 2.4 硬语义层（Semantics）— 企业的 Wikidata

四类对象 × 状态二维浏览（P0 基础版✅，增强点）：

- 左栏：类型分组树（entity/metric/relation/dimension，各带 confirmed/proposed 计数）
- 主栏：对象列表（搜索、状态过滤）
- 详情 drawer（✅已有基础，增强）：payload 结构化展示（不再是裸 JSON——
  entity 显示字段表、metric 显示口径卡、dimension 显示值映射表、relation 显示路径）、
  版本历史 + 相邻版本 diff（🔧）、evidence 引文、血缘（被哪些报告/指标引用，
  P2 边表后）、局部图（一跳邻域，P2）
- confirmed ✅ / proposed 🟡 标识贯穿全部视图——**目录页本身就是资产固化程度的可视化**

### 2.5 软知识层（Wiki）— 企业的 Wikipedia

ECP 专用 knowledge space（`ecp-<workspace>`，后端 get-or-create✅）的分层展示，
直接复用知识空间视图体系：

- wiki 树 + 词条阅读（复用 knowledge-vault API；词条 frontmatter `ref` 字段
  双向跳转：词条 → 硬对象详情，硬对象 → 相关词条）
- raw 文件列表（作为证据来源的原始文档）
- 入口也可以从知识空间侧进入：ECP space 在 `/knowledge-vault` 列表中天然可见，
  两边是同一数据的两个视角（业务视角 / 文档视角）

### 2.6 血缘图（Graph）

- **全局图**：节点按类型着色（entity 蓝/metric 绿/dimension 紫/relation 橙），
  按状态区分（confirmed 实线/proposed 虚线或浅色）；数据源/API/文档资产
  作为物理层节点挂在 binding/provenance 边的末端（`GET /ecp/graph` ✅基础版，
  前端渲染🔧；首期也可用 Obsidian 打开软层顶替——但硬层图只有这里能看到）
- **对象局部图**：详情 drawer 内的一跳邻域（P2）
- 这张图 = "从老板看到的数字到数据库字段"的全链路血缘，也是续费谈判时的
  资产证明（ECP 文档原话）

### 2.7 巡检（Lint）

| 区块 | 内容 | 分期 |
|---|---|---|
| 硬层巡检 | 绑定漂移/语义矛盾/陈旧确认/孤儿对象/未命中聚类/缓存健康（ecp/lint.py，cron 每日） | P3 |
| 软层巡检 | knowledge doc_lint 7 项（含新增的 index_drift）对 ECP space 跑 | P1 可提前（API 已有✅） |
| 未命中聚类 | op_log 中兜底问题聚类 → 一键生成提案 | P3 |
| 巡检历史 | log.md + op_log 的 lint 记录时间线 | P3 |

### 2.8 设置（Settings）

- 确认人名单管理（API✅，UI🔧）
- domain_hint / 领域背景配置（workspace 级，注入提案）
- op_log 查看器（操作审计时间线，API✅）
- ECP space 入口与 schema.md 查看（P3 定制）

## 3. 关键用户旅程

**冷启动（首日 < 1 小时）**：
登记 DB 资产 → 就绪检查全绿 → 「生成提案」（批处理管线）→ 收件箱确认
3-5 个核心口径 → 对话里问"上周销售额" → ✅ 带血缘的数字

**文档进资产**：
登记/上传行业文档（《财务核算办法》）→ ingest 完成 → 重新生成提案
（已确认目录回注，只增量）→ 确认卡片上直接看到文档引文 → 确认成本骤降

**修正回写**：
报告里数字标 ⚠️ → 对话里说"要剔税" → 系统定位 mtr.net_sales →
新版本 proposed + 影响分析（"影响周报 3 处"）→ 确认 → 回执"已修正，
本次及以后所有报告生效" → 换个说法"营收"再问 → 反问确认 → 别名回填 →
第三次问零摩擦命中

**漂移治理（每周）**：
Lint 发现 tb_so_01 加了列/改了类型 → 收件箱出现"绑定漂移"更新提案 →
确认人看一眼 diff → 确认 → 语义资产跟上物理层

## 4. 分期功能映射

| 视图 | P0（已交付） | P1 | P2 | P3 |
|---|---|---|---|---|
| 收件箱 | 列表+确认/否决+详情 | — | 改后确认 UI、维度值编辑、首日规则 | evidence 充实 |
| 资产层 | — | **注册表+readiness+登记 UI+生成提案** | 资产关联统计 | API 资产 |
| 硬语义 | 浏览+详情+版本历史 | — | 结构化 payload 展示、版本 diff、局部图 | — |
| 软知识 | — | **ECP space 供给+wiki 树只读视图** | ref 双向跳转 | 文档双路 ingest |
| 血缘图 | — | **全局图（对象+边）** | 局部图、物理层节点 | — |
| 巡检 | （软层 lint 修复✅） | 软层 lint 展示 | — | 硬层 6 项+聚类+历史 |
| 总览 | — | 简化版（计数+待办） | 北极星趋势 | 完整版 |
| 设置 | — | 确认人+op_log UI | domain 配置 | schema 查看 |
| 工具面/查询 | — | **6 工具+executor 门禁+目录注入+提案 Agent** | ⚠️内联确认卡片 | — |

**当前迭代（本次落地）= 资产层 + 软知识 space + 血缘图基础 + 设置 UI +
工具面（任务 8/9 继续）**，让 /ecp 从"一个表格"变成"分层业务语义工作台"。

---

## 5. 提案内容升级（v1.1，2026-08-29 已落地）

**问题**：提案确认人（业务人）看不懂提案——库只有数字 ID、字段血缘是裸字符串、
来源是自由文本（`discovery:ds1`/`gate:rule5`）、MISS 学习来的提案看不到原始 SQL、
详情页是 payload JSON dump。

**目标（验收口径）**：打开任意提案，业务人能回答三个问题——
① 这数字从哪来（库/表/字段+口径）；② 用起来生成什么 SQL（不点试跑也能看到组装效果）；
③ 它是怎么被提出来的（来源徽章；MISS 学习来的直接展示原始 SQL）。

**三层结构**：

```
L0 存储层   payload(不动,契约照旧) + provenance 列(来源快照,写入时落库)
L1 派生层   service/proposal_view.py(读时计算,不落库——血缘与 SQL 是
            payload 的函数,落库必腐化)
L2 展示层   前端结构化区块(干掉 JSON dump)
```

**provenance（写入时快照）**：`ecp_semantic_object.provenance` JSON 列
（迁移照 usage serve try/except ALTER 先例；MySQL/PG gyra.sql 同步）。
`{origin, actor, origin_sql[], miss_ref, note, derived_from}`；
origin 枚举在 `config.py`（discovery/miss_learn/manual_sql/rule5_gate/edit/
agent/import/legacy，含中文标签与历史 source 前缀映射 `origin_from_source`）。
老数据 provenance 为空 → 视图降级显示 source 原文。
确认/编辑派生新版本经 `carry_provenance` 携带原来源（origin 不被编辑覆盖，
derived_from 记录派生链）。

**ProposalViewVO（读时派生）**：`build_proposal_view(vo, objects, ds_name_resolver, level)`
- `summary`：一句话业务口径（后端按类型契约生成，取代前端 summarizePayload 散逻辑）
- `origin`：kind + 中文 label + origin_sql 快照 + miss_ref 活链
- `lineage`：datasource_id→数据源中文名、表、**字段级血缘**
  （expression/extra_filters 经 sqlglot 解析出列，对照 entity.fields 标注
  meaning/role/usage；`declared=false` = 引用了未声明列 = 口径疑点，前端红色高亮）+
  引用对象链（带 ✅/🟡 状态）
- `sql_preview`：**静态 SQL 组装效果**（与 executor 同一 `_assemble_sql`
  确定性组装，不执行；近 7 天示例时间窗；参与组装对象清单；不完整提案降级
  warnings 不报错）。试跑真数据仍走 `/debug` 端点

**写入统一（3 合 1）**：`Service.propose()` 是唯一提案写入口
（API/Agent 工具×2/批量管线/执行门禁全部汇聚）；`gate_level="executable"`
时过可执行级契约门禁（`ContractViolation` 携带问题列表，工具回传
contract_gaps）；entity 兜底（Oracle owner 补全 + 时间列 role=time）
从 ecp_tools 并入 Service，三条路径质量拉齐。
原三份 propose_semantic 实现收敛为薄壳；Agent 工具路径新增
`miss_ref`/`origin_sql` 参数——MISS 学习提案必须回传聚类键与原始 SQL
（auto_learn cron 指令与提案 Agent prompt 已同步），miss→提案断链修复
（反向 `miss_learn.proposal_ids` 已有，正向 provenance.miss_ref 补齐）。

**Service 拆分**：1947 行上帝类 → 门面（提案生命周期/契约 admin/读模型/确认人）
+ 无状态协作者（miss.py 飞轮 / graph.py 全景图 / alignment_ops.py 对齐运营 /
assets.py 资产 / workspace.py 空间配置 / transfer.py 导入导出 /
knowledge_bridge.py 软层只读桥梁——顺带消除 slug 聚合×3、knowledge
Service 获取样板×5 两处重复）。

**API 增量**：
- `GET /objects/{id}/versions/{v}/view` → ProposalViewVO（详情页数据源）
- `GET /inbox`、`GET /objects` 加 `include_view`（默认开，brief 级视图）
- `GET /contracts` → 各类型 payload 契约（前端表单单一事实来源，
  消除 prompt/contracts.py/前端表单/前端模板四处重复中的前端两份；
  PayloadEditor 接入为后续项）
- `SemanticObjectVO` 加 `provenance` + `view` 字段；导出/导入透传 provenance

**前端三展示面**：
- 收件箱卡片：一句话口径 + 来源徽章（中文+着色）+ 血缘 chips（库名·表）
- 详情 Drawer 五区块：基本信息（来源徽章）/ 业务定义（分类型结构化：
  metric 口径卡、dimension 值映射表、relation 路径卡、文档类定义卡）/
  数据血缘（库·表·字段表，未声明列红色标注）/ SQL 生成效果（静态预览+
  参与对象+scenario 说明；场景确认页另有试跑面板）/ 来源与证据
  （MISS 学习：原始 SQL 代码块 + miss 轨迹指引）/ 版本历史。**JSON dump 已删除**
- 场景空间确认页复用同一 ObjectDetailContent（自动继承）；移动端同步升级
