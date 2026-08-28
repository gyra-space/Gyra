# Code 契约（写 code 的一切）

对应工作流「步骤 2 / 4：探索数据、编写代码」。这是最重要的一份文档。

## 1. code 是什么

`code` 是一段 **JS 片段**，会在沙箱 iframe 的 `<body>` 里被包成 `(function(){ ... })()` 执行。
它自己往 `document.getElementById('root')` 里渲染界面。取数只能通过全局 `window.GyraAppCard`：

| 方法                                     | 用途                                                                                                                            |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `GyraAppCard.op(op, params, queryKey)` | 通用能力调用。`op ∈ query.metric / query.sql / assets.get / preview.*`；`params` 传入参数、`queryKey` 引用 `queries` 里已声明的命名查询。返回 `Promise`。 |
| `GyraAppCard.assets(params)`           | 等同 `op('assets.get', params)`，读空间资产                                                                                           |
| `GyraAppCard.params()`                 | 宿主注入的初始参数（即 `config.default_params`，只读快照）                                                                                     |
| `GyraAppCard.getParam(k)`              | 读某个初始参数                                                                                                                       |
| `GyraAppCard.onParamChange(fn)`        | 宿主切换参数（切 tab/选时间范围）时回调 `fn(newParams)`                                                                                        |

## 2. op 返回结构（务必判断 `trust`）

```jsonc
{ "trust": "inferred" | "preview" | "none",
  "error": null | "错误信息",
  "columns": ["col1","col2"],
  "rows": [ {"col1": v, "col2": v} ],
  "row_count": 0 }
```

* `trust === "none"` 表示失败（此时 `error` 有值）→ 渲染错误态，不要当正常数据。

* `rows` 是数组，每项是「列名 → 值」的对象。渲染时用 `rows.map(r => r.xxx)`。

## 3. ⚠️ 工具预览与运行期数据格式不一样（最容易"渲染不对"的坑）

你在**生成期**用**自己的工具**（`execute_sql` / `execute_raw_sql` / `execute_metric_query`）探索数据时，返回的是 **VIS 组件**（`d-sql-query` / `d-ecp-metric`）。它为了给前端表格组件渲染，会把 `rows` **统一归一成二维数组**：

```jsonc
{ "columns": ["service","cpu","day"],
  "rows": [ ["api-gateway", 63.2, "2026-08-24"], ... ],   // ← 二维数组（list of lists）
  "total_rows": 3 }
```

而**运行期** **`GyraAppCard.op(...)`** **返回的** **`rows`** **是对象数组**：

```jsonc
{ "columns": ["service","cpu","day"],
  "rows": [ { "service":"api-gateway", "cpu":63.2, "day":"2026-08-24" }, ... ],
  "row_count": 3 }
```

**两者结构不同**：工具侧靠 `columns` 表头 + 按下标 `rows[i][j]` 取值；运行期直接用 `r.列名`。所以：

* 写卡片 `code` 时**一律按运行期格式**（`rows.map(r => r.列名)`）来写，**绝不照搬工具里的下标写法** `rows[i][j]` / `row[i]`。

* 工具里 SQL 结果没有 `row_count`，用的是 `total_rows`；运行期才是 `row_count`。工具错误提示是 `error`/`warning`（字符串），运行期是 `error`/`warnings`（数组）——判断失败一律以 `trust === "none"` 为准。

**如何拿到"与运行期完全一致"的数据（三种做法，优先第一种）**

> **这个入口就是「hook 工具」**：`app_card_preview`（或 V2 的 `db({action:"app_card_preview",...})`）与运行期走同一条取数路径，agent 通过它拿到的就是 app card 里 `GyraAppCard.op` 同款的数据。所以**开发前用它取数定字段、交付前用它逐条验证每个 metric/sql**——既能拿到真实样例做开发，也能在交付前确认每个查询有值、字段对得上。

1. **首选：内置工具** **`app_card_preview`**（作为数据库工具随库自动注入）。它与 `execute_sql`/`get_table_spec` 一样，绑定了数据库资源的 agent 天然可用，**无需额外绑定资源**。直接执行 `query.sql` / `query.metric`，与运行期同一条派发路径，返回**对象数组 rows** + `row_count` + **`elapsed_ms`（性能基线）**：

```text
app_card_preview(op="query.sql", query_key="q_trend",
                 params={"bind_params": {"start": "2020-01-01"}},
                 queries=[/* 你的查询契约 */], workspace_id=<id>)
# 返回:  {"columns": [...], "rows": [{"col": v, ...}], "row_count": n,
#         "trust": "inferred|verified|none", "elapsed_ms": 12, ...}
```

* 也直接支持 `op="sql.explain"` 拿到查询计划，用 `elapsed_ms` / `row_count` / plan 评估与调优（如加索引、限制 `limit`）。

* 用它而非 `execute_sql`（后者 rows 是二维数组，容易写错渲染逻辑）。

* **V2 引擎**下通过统一 `db` 工具调用：`db({ action:"app_card_preview", op:"query.sql", query_key:"q_trend", params:{bind_params:{start:"2020-01-01"}}, queries:[/* 你的查询契约 */], workspace_id:<id> })`，返回同样结构。

> **硬性规则**：字段名依据**只能**来自 hook 工具（或 preview 接口）返回的对象数组。❌ **反例（禁止）**：只用 `execute_sql` 探数就直接写 `rows.map(r => r.xxx)` 渲染逻辑、跳过 hook 工具的字段确认与逐条验证——`execute_sql` 的 rows 是二维数组（`rows[i][j]`），与运行期对象数组结构不同，照它猜字段名必渲染错。开发前未用 hook 工具取到真实样例数据，**不得**开始写 `code`。

1. **也推荐：走预览取数（与运行期同一条派发路径）**。调 `POST /api/v1/serve_app_card_service/app_cards/preview/invoke`：

```jsonc
{ "workspace_id": 1,
  "op": "query.sql", "query_key": "q_trend",
  "params": { "bind_params": { "start": "2020-01-01" } },
  "queries": [ /* 你的 queries 契约（未落库也可） */ ] }
```

它直接复用运行期的 `_invoke_sql` / `_invoke_metric`，返回的 `rows` 就是对象数组，`row_count`/`warnings` 等字段也与真实运行一致。**预览结果可直接作为写渲染逻辑与核对字段名的依据**。

1. **兜底：对自己工具的结果手动归一**。把工具的 `columns` 与二维数组 `rows` 合并成对象数组再对照：

```js
// 将工具返回（columns + 二维数组 rows）归一为运行期对象数组
function toRows(res){
  var cols = (res||{}).columns || [], arr = (res||{}).rows || [];
  return arr.map(function(row){
    var o = {}; cols.forEach(function(c, j){ o[c] = row[j]; });
    return o;
  });
}
// 用法：var rows = toRows(MY_TOOL_RESULT);  // 之后即可 rows[0].service
```

> 归一/预览得到的字段名 = SQL 别名 / 指标输出列名（如 `SELECT ... AS cpu` → `r.cpu`）。写 `code` 时直接用这些列名。

**性能调优提示**：卡片取数都以 `query_key` 走命名查询，配置 `limit` 控制返回行数；若 `app_card_preview` 的 `elapsed_ms` 偏大，优先加大筛选（`bind_params`/`time_range`）、加 `limit`，必要时用 `sql.explain` 看是否缺索引。

## 4. 布局先渲、分区块异步取数（基础规范）

不要「一个接口一次拉走几十个 SQL」再整屏渲染——那样首屏空白等待长、一个查询挂了整屏全废、后期也难维护。**必须**分区块、按需、各自异步加载：

1. **布局先渲染**：进卡片先画出完整骨架（分区容器 + 每个区的 loading 占位/骨架屏），不等任何数据。静态标题、tab、筛选器、空容器立即可见。
2. **每块一个查询，各自独立**：指标卡、趋势图、明细表…每个数据区块对应一个 `query_key`，用一个 `loadXxx()` 单独调 `GyraAppCard.op('query.sql', params, 'q_xxx')`（或 `query.metric`）。区块间互不阻塞。
3. **并行发出、先到先渲染**：各区块的请求**同时发出**（可并行），但**各自用独立的** **`.then`** **渲染自己**，数据到一个区就渲染一个区（渐进填充），**不要**用一个大的 `Promise.all` 等所有结果齐了才一次性整屏渲染。个别慢/失败的区块不影响其他区块。
4. **三态落在区块级**：每个区独立维护 loading / empty / error（`trust==="none"`）三态，有自己的骨架、空态文案与"重试"。一个区报错只降级该区，不拖垮全卡。
5. **依赖才串行**：仅当区块 A 的数据是区块 B 的入参时才 `A.then(loadB)`；无依赖就并行。

标准写法示例（每块独立 load + 独立三态）：

```js
function loadCards(p){   // 指标卡区
  GyraAppCard.op('query.sql', p, 'q_totals').then(function(res){
    var t=(res&&res.rows&&res.rows[0])||{};
    document.getElementById('cards').innerHTML = renderCards(t);
  }).catch(function(e){
    document.getElementById('cards').innerHTML = '<div class="st">加载失败: '+esc(e.message)+'</div>';
  });
}
function loadTrend(p){   // 趋势图区
  GyraAppCard.op('query.sql', p, 'q_trend').then(function(res){
    draw(res&&res.rows);
  }).catch(function(e){ /* 只降级本区 */ });
}
function load(){
  var p = { bind_params: { start: state.start } };
  loadCards(p); loadTrend(p);   // 同时发出, 先到先渲
}
```

❌ 反例（禁止）：`Promise.all([op(...), op(...), op(...)]).then(render 整屏)` —— 三个查询都回来才渲染，最慢的查询决定首屏时间，任何一个失败整屏全废。

> 什么时候仍可"合并一条 SQL"：同一区块内部、完全同源同筛选的指标可写一条 SQL 一起取（如指标卡 n/avg/max 一行返回），但**跨区块**仍走各自查询 + 各自异步渲染。

## 5. DOM 写入必须先判空（硬性要求）

对 `document.getElementById(id)` 的结果赋值（`textContent`/`innerHTML`/`value`/`style`）或绑定事件前，必须确认元素存在，否则元素不匹配时会抛
`Cannot set properties of null (setting 'textContent')` 把整屏弄崩。推荐直接复用模板里的辅助函数：

* `el(id)` 取元素（可能为 null）

* `setH(id, html)` / `take(id, fn)` 存在时才内部写入 / 执行

* 对单点赋值用 `var e=el(id); if(e) e.textContent = v;`

生成代码时**绝不写裸的** **`document.getElementById('x').textContent = ...`**。

## 6. code 字段在 JSON 里必须转义（最容易整份报废的坑）

最终产物是 JSON，`code` 的值是**一个 JSON 字符串**，里面装着整段 JS 源码。JS 源码里常出现的双引号（尤其是 HTML 属性 `class="x"`、`id="y"`、`style="..."`）一旦是裸的，`JSON.parse` 会在这一行直接失败，整份 payload 变成非法 JSON，导入报「不是有效的 App Card payload」。因此：

* JS 里的每个 `"` 必须写成 `\"`：如 `class="sk"` → `class=\"sk\"`、`id="overviewBox"` → `id=\"overviewBox\"`。

* JS 里的每个 `\` 写成 `\\`。

* 代码里的换行/回车/制表符分别转义为 `\n`/`\r`/`\t`；建议把 JS 整体压成一行，用 `+` 拼接字符串（同 `docs/04_example.md`）。

* 唯一的例外：`code` 字段值本身两端的定界引号。

> **怎么产出最稳**：不要手拼 JSON 字符串。先用代码构造对象（Python 里 `dict` / JS 里 `object`），然后统一序列化——Python 用 `json.dumps(payload, ensure_ascii=False, indent=2)`，JS 用 `JSON.stringify(payload, null, 2)`。序列化器会自动把 `code` 里所有双引号、反斜杠、换行转义到位，从根上避免裸引号。

