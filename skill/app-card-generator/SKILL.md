***

name: app-card-generator
description: |
生成 app-card（应用卡片/常驻子应用）主技能。当用户要求"生成/设计一个应用卡片、
子应用、多tab多指标看板、仪表盘卡片、空间主页常驻的可交互看板"，或要把一组
指标/数据包装成一个能放进空间主页、切 tab/选时间后实时取数的可交互子应用时，
必须使用本技能。即使没有说"卡片"两个字，只要是"做一个能交互的看板/面板/子应用"
就用本技能。
type: python
category: frontend
version: 1.3.0
--------------

# App Card 生成技能（骨架版）

目标：产出一个「应用卡片」——一段自包含 JS 渲染代码 + 一份命名查询数据契约。通过
`POST /api/v1/serve_app_card_service/app_cards/create` 落库后，在空间主页常驻渲染。
**生成一次、冻结为版本；运行期由引擎执行冻结的命名查询取数，绝不重新调用 agent。**

本 `SKILL.md` 只承载**工作流主干 + 全局硬约束**；细节的字段、代码写法、完整范例、校验
命令等都在 `docs/` 下的分环节文档里——**做到哪个环节，就读取哪份文档，按需加载**，
不提前通读全部 docs。

***

## 一、工作流主干（依次推进，按需加载对应文档）

| 步骤      | 做的事                                                                                                | 按需加载文档                                                                        | 关键出口                         |
| ------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------- |
| 1 需求与结构 | 澄清卡片名/用途/布局/tab/参数 → 定下 `name`、`kind`、`meta`、`config` 框架                                           | `docs/01_payload_schema.md`                                                   | `meta` 签名齐全的结构骨架             |
| 2 探索数据  | **先用 hook 工具取数再开发**：对计划中的每个查询执行一次取数，拿到字段/列名与样例值，确认 metric 已 `confirmed`                            | `docs/02_code_contract.md`                                                    | 依真实数据确定的字段/列名清单              |
| 3 定义查询  | 为每个数据区块写命名查询 `queries[]`（metric / 只读 sql + `bind_params`）                                          | `docs/05_queries.md`                                                          | 防注入、字段匹配的 queries            |
| 4 编写代码  | 按「布局先渲 + 分区块异步取数」写 `code`；套视觉主题；可参考完整范例                                                            | `docs/02_code_contract.md` + `docs/03_style_vision.md` + `docs/04_example.md` | 自包含、三态齐全的 JS code            |
| 5 校验与交付 | **逐个指标/SQL 用 hook 工具执行验证**取数有值、字段名与 code 一致；落库/导出 payload，**文件名带版本+时间戳**，跑 `validate.py` 必须 `[OK]` | `docs/06_delivery.md`                                                         | 一份「取数已逐个验证 + 合法 + 通过自检」的交付文件 |

> 执行规则：**前一个环节的产出确认后，才进入下一个环节**；进入某环节前才读对应文档。
> 中间报错先用 `docs/06_delivery.md` 的「常见失败与修正」对症处理。

***

## 二、全局硬约束（任何时候都守，SKILL.md 即总纲）

**产物**

* 产出物 = 一份**合法 JSON** payload；缺一块即不交付：`meta` 签名 + `name` + `code` + `config` + `queries`。

* **必须用序列化器产出**（Python `json.dumps` / JS `JSON.stringify`），禁止 f-string/模板串手拼 JSON。

* 交付文件名必须带**版本 + 时间戳**：`app_card_<slug>_v<meta.version>_<YYYYMMDDTHHMMSSZ>.json`，且与 `meta.version`/`meta.generated_at` 对齐。

**取数**

* 只能通过 `GyraAppCard.op` / `~.assets` 取数；禁止 `fetch` 业务接口、裸 SQL、`window.parent`/`cookie`/`localStorage`。

* **开发前先取数（硬门禁）**：动手写 code 前，先对每个计划查询用 hook 工具（`app_card_preview` / `db({action:"app_card_preview"})`）执行一次取数，确认字段名与样例值。**未取得真实样例数据前，禁止开始写** **`code`**；**禁止**把 `execute_sql` 的二维数组 rows 当字段依据（运行期是对象数组，照它写必渲染错）。

* **交付前逐个验证（硬门禁）**：每个 `metric` 和 `sql` 都必须用 hook 工具执行一次，确认 `trust !== "none"`、`rows` 有值、字段名与 `code` 中访问一致；任一查询取不到数据或字段不匹配，就修到通过再交付。**未逐条跑过 hook 工具验证的 payload，禁止交付**。

* **hook 工具在开发对话已注入**：在场景空间开发对话里，`app_card_preview` 已作为 ECP 场景工具注入（`workspace_id` 已由宿主闭包绑定，**无需**传）。直接调 `app_card_preview(op="query.sql", params={"sql":"...", "datasource_id": <id>, "bind_params":{...}})` 或 V2 的 `db({action:"app_card_preview", op="query.sql", ...})`；`datasource_id` 从 `get_table_spec`/语义目录/托管资产清单获取。

* **分区块异步取数（基础规范）**：布局先渲染骨架；每区块一个 `query_key` + 独立 `loadXxx()` + 独立三态；并行发出、各自渲染；**禁止**一个查询/一次调用拉全卡 SQL 后整体渲染。

* `sql` 只读 + `bind_params`（`:name` 占位），禁止字符串拼 SQL。

**健壮性**

* `code` 里对 op 结果 `rows` 一律**对象数组访问**（`r.列名`），不用工具预览的下标写法。

* DOM 写入必须先判空（用 `el(id)` / `setH(id, html)` / `take(id, fn)`），禁止裸 `getElementById(...).textContent = ...`。

* `code` 在 JSON 里必须正确转义（`"`→`\"`、`\`→`\\`、换行→`\n`）。

**交付守门（两道门禁，缺一不交付）**

* **门禁 ①（hook 工具逐条验证）**：每个 `metric`/`sql` 都用 hook 工具（`app_card_preview` / `db({action:"app_card_preview"})`）执行过一次，确认 `trust !== "none"`、`rows` 有值、列名与 `code` 一致；**未逐条验证的 payload 禁止进入下一道门禁**，只用 `execute_sql` 探数视为未验证。

* **门禁 ②（validate.py）**：最后一步**必须运行**随技能分发的 `validate.py`，输出 `[OK]` 且退出码为 0 才能交付；失败就修复后重跑，**不自检不交付**。

***

## 三、文档索引（按需读取）

* `docs/01_payload_schema.md` — 产物结构与 meta 签名（步骤 1）

* `docs/02_code_contract.md` — Code 契约：SDK 方法、op 返回结构、工具 vs 运行期 rows 差异、分区块异步取数与转义写法（步骤 2 / 4）

* `docs/03_style_vision.md` — 视觉与独立风格自由度（步骤 4）

* `docs/04_example.md` — 完整复杂范例，可直接模仿（步骤 4）

* `docs/05_queries.md` — Queries 数据契约与防注入（步骤 3）

* `docs/06_delivery.md` — 校验脚本、落库、交付文件名、自检清单/命令、常见失败与修正（步骤 5）

