# Queries 数据契约

对应工作流「步骤 3：定义查询」。《SKILL.md》规定只读 SQL + `bind_params` 与命名查询约束，本文档给出每类查询的字段说明与防注入细则。

`queries` 是命名查询，是「生成期 dry-run → 运行期冻结取数」的载体：

| kind | 字段 | 说明 |
|---|---|---|
| `metric` | `metric_id`（必填）、`group_by`、`filters`、`time_range` | 走 ECP 语义层，构造级防注入，需指标 `confirmed` |
| `sql` | `sql`（必填，只读）、`datasource_id`（必填）、`bind_params`、`limit` | 走只读 SQL + 绑定参数；用 `:name` 占位，`bind_params` 提供值 |

**防注入**：`sql` 只允许 `SELECT/WITH/SHOW/DESC/DESCRIBE/EXPLAIN` 开头；所有动态值（时间、维度）必须走 `bind_params` 绑定，**禁止**字符串拼进 SQL。

**切 tab / 选时间**：优先由卡片自身维护 UI 状态（`activeTab`、`timeRange`），变化后重新调 `GyraAppCard.op` 取数即可；`config.params` + `GyraAppCard.params()/onParamChange` 用于需要宿主统一管理参数的情形。