# 产物结构（App Card Payload Schema）

对应工作流「步骤 1：需求与结构」。**生成结果必须同时给出两块，缺一不可**：`code`（JS 渲染代码）+ `queries`（命名查询数据契约），并带完整 `meta` 签名。

## 完整示例（骨架）

```jsonc
{
  "name": "容量巡检核心看板",
  "kind": "dashboard",
  "meta": {
    "schema_name": "gyra_app_card",
    "schema_version": 1,
    "generated_by": "app-card-generator",
    "version": "1.0.0",
    "generated_at": "2026-08-26T00:00:00Z",
    "card_name": "容量巡检核心看板",
    "icon": "📊",
    "refresh_interval": 60
  },
  "config": {
    "tabs": [{ "key": "overview", "title": "总览" }, { "key": "detail", "title": "明细" }],
    "params": [
      { "key": "time_range", "label": "时间范围", "type": "daterange", "default_value": "LAST_7D" },
      { "key": "dimension", "label": "分组维度", "type": "select", "options": ["service","region"], "default_value": "service" }
    ],
    "default_params": { "time_range": "today" }
  },
  "queries": [
    { "key": "q_cpu", "kind": "metric", "metric_id": "m_cpu", "group_by": ["dim.service"], "time_range": {"range": "${time_range}"} },
    { "key": "q_trend", "kind": "sql", "sql": "SELECT day, AVG(cpu) cpu FROM metrics WHERE created_at >= :start GROUP BY day ORDER BY day",
      "datasource_id": 123, "bind_params": {"start": "2020-01-01"}, "limit": 120 }
  ],
  "code": "<见 docs/02_code_contract.md>"
}
```

## 字段说明

- `name`：非空字符串（卡片名）。
- `kind`：`dashboard` / `board` / `custom`。
- `meta`（**签名，检测与"一键导入"的可靠依据**，必含）：
  - `schema_name: "gyra_app_card"`、`schema_version`、`generated_by`、`generated_at`、`version`。
  - `version`：卡片**语义版本**，`x.y.z`（从 `1.0.0` 起增量）。
  - 可选：`card_name`、`icon`、`refresh_interval`。
- `config`：对象，含 `tabs` / `params` / `default_params` 等卡片结构与宿主参数。
- `queries`：数组，命名查询（见 `docs/05_queries.md`）。
- `code`：字符串，整段 JS 源码（见 `docs/02_code_contract.md`）。
- 可选顶层：`icon`、`permissions`。