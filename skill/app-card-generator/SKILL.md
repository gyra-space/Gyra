---
name: app-card-generator
description: |
  生成 app-card（应用卡片/常驻子应用）主技能。当用户要求"生成/设计一个应用卡片、
  子应用、多tab多指标看板、仪表盘卡片、空间主页常驻的可交互看板"，或要把一组
  指标/数据包装成一个能放进空间主页、切 tab/选时间后实时取数的可交互子应用时，
  必须使用本技能。即使没有说"卡片"两个字，只要是"做一个能交互的看板/面板/子应用"
  就用本技能。
type: python
category: frontend
version: 1.2.0
---

# App Card 生成技能

目标：产出一个「应用卡片」——一段自包含的 JS 渲染代码 + 一份命名查询数据契约，最终
通过 `POST /api/v1/serve_app_card_service/app_cards/create` 落库，在空间主页常驻渲染。
**生成一次、冻结为版本；运行期由引擎执行冻结的命名查询取数，绝不重新调用 agent。**

---

## 一、产物结构

生成结果必须同时给出两块，缺一不可：

```jsonc
{
  "name": "容量巡检核心看板",
  "kind": "dashboard",
  "meta": {
    "schema_name": "gyra_app_card",
    "schema_version": 1,
    "generated_by": "app-card-generator",
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
  "code": "<见 Code 契约>"
}
```

---

## 二、Code 契约（最重要）

`code` 是一段**JS 片段**，会在沙箱 iframe 的 `<body>` 里被包成 `(function(){ ... })()` 执行。
它自己往 `document.getElementById('root')` 里渲染界面。取数只能通过全局 `window.GyraAppCard`：

| 方法 | 用途 |
|---|---|
| `GyraAppCard.op(op, params, queryKey)` | 通用能力调用。`op ∈ query.metric / query.sql / assets.get / preview.*`；`params` 传入参数、`queryKey` 引用 `queries` 里已声明的命名查询。返回 `Promise`。 |
| `GyraAppCard.assets(params)` | 等同 `op('assets.get', params)`，读空间资产 |
| `GyraAppCard.params()` | 宿主注入的初始参数（即 `config.default_params`，只读快照） |
| `GyraAppCard.getParam(k)` | 读某个初始参数 |
| `GyraAppCard.onParamChange(fn)` | 宿主切换参数（切 tab/选时间范围）时回调 `fn(newParams)` |

**op 返回结构**（务必判断 `trust`）：
```jsonc
{ "trust": "inferred" | "preview" | "none",
  "error": null | "错误信息",
  "columns": ["col1","col2"],
  "rows": [ {"col1": v, "col2": v} ],
  "row_count": 0 }
```
- `trust === "none"` 表示失败（此时 `error` 有值）→ 渲染错误态，不要当正常数据。
- `rows` 是数组，每项是「列名 → 值」的对象。渲染时用 `rows.map(r => r.xxx)`。

**铁律**
- 只能通过 `GyraAppCard.op` / `~.assets` 取数；**不要**自己 `fetch` 业务接口、不要写裸 SQL 走数据源、不要碰 `window.parent`/`cookie`/`localStorage`。
- 数据请求尽量用 `query_key` 引用 `queries` 里已声明的命名查询；`query.metric` 必须传 `metric_id`。
- 代码必须**纯前端 + SDK 取数**，自包含、无外部后端依赖。
- **DOM 写入必须先判空（硬性要求）**：对 `document.getElementById(id)` 的结果赋值（`textContent`/`innerHTML`/`value`/`style`）或绑定事件前，必须确认元素存在，否则元素不匹配时会抛
  `Cannot set properties of null (setting 'textContent')` 把整屏弄崩。推荐直接复用模板里的辅助函数：
  - `el(id)` 取元素（可能为 null）
  - `setH(id, html)` / `take(id, fn)` 存在时才内部写入 / 执行
  - 对单点赋值用 `var e=el(id); if(e) e.textContent = v;`
  生成代码时**绝不写裸的 `document.getElementById('x').textContent = ...`**。

**`code` 字段在 JSON 里必须转义（最容易整份报废的坑）**

最终产物是 JSON，`code` 的值是**一个 JSON 字符串**，里面装着整段 JS 源码。JS 源码里常出现的双引号（尤其是 HTML 属性 `class="x"`、`id="y"`、`style="..."`）一旦是裸的，`JSON.parse` 会在这一行直接失败，整份 payload 变成非法 JSON，导入报「不是有效的 App Card payload」。因此：

- JS 里的每个 `"` 必须写成 `\"`：如 `class="sk"` → `class=\"sk\"`、`id="overviewBox"` → `id=\"overviewBox\"`。
- JS 里的每个 `\` 写成 `\\`。
- 代码里的换行/回车/制表符分别转义为 `\n`/`\r`/`\t`；建议把 JS 整体压成一行，用 `+` 拼接字符串（同「四、复杂范例」）。
- 唯一的例外：`code` 字段值本身两端的定界引号。

> **怎么产出最稳**：不要手拼 JSON 字符串。先用代码构造对象（Python 里 `dict` / JS 里 `object`），然后统一序列化——Python 用 `json.dumps(payload, ensure_ascii=False, indent=2)`，JS 用 `JSON.stringify(payload, null, 2)`。序列化器会自动把 `code` 里所有双引号、反斜杠、换行转义到位，从根上避免裸引号。

---

## 三、视觉与独立风格（重点：你可以做任何样式）

沙箱 **只限制「数据来源」**，完全不限制「视觉表现」。你有完整的设计自由度：

- **布局**：`display:grid` / `flex` 任意组合；支持响应式（`@media`）。
- **主题**：浅色/深色/渐变/玻璃拟态均可，自定义背景、卡片、阴影、圆角。允许整页深色主题。
- **字体**：系统字体栈或 web-safe 字体；中文建议 `-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif`。
- **图表**：优先**自包含**——用内联 SVG（折线/面积/柱状/环形）或 `<canvas>` 手绘；也可用 `<script src="https://...CDN...">` 引入图表库（如 ECharts），但要有**降级兜底**（CDN 加载失败时不白屏）。
- **状态**：至少覆盖 loading / empty / error 三态（骨架屏、空数据提示、错误信息+重试）。
- **动效**：CSS transition / keyframes，克制即可。
- **视觉基准**：配色统一（主色+中性色）、间距成体系、圆角/阴影一致，标题层级清晰（大标题/小节/正文字号分明）。

> 只写 "好看、复杂、独立风格" 即可；不要因为它是"卡片"就做得简陋。参考：给真实产品做仪表盘首页的水准。

---

## 四、复杂范例（可直接模仿）

多 tab + 深色主题 + 指标卡 + 内联 SVG 趋势图 + 时间范围交互 + 三态。`queries` 提供 `q_totals`（总指标）、`q_trend`（趋势）、`q_metrics`（明细）。

```js
document.head.insertAdjacentHTML('beforeend',
 '<style>body{background:#0f172a;color:#e5e7eb;font-family:-apple-system,"PingFang SC",sans-serif;margin:0}'+
 '.ac{padding:14px}.bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}'+
 '.title{font-size:16px;font-weight:700;letter-spacing:.2px}.sub{font-size:11px;color:#94a3b8}'+
 '.pills{display:flex;gap:6px}.pill{background:#1e293b;color:#cbd5e1;border:1px solid #334155;border-radius:999px;padding:4px 10px;font-size:12px;cursor:pointer}'+
 '.pill.on{background:#2563eb;color:#fff;border-color:#2563eb}'+
 '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:12px}'+
 '.k{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:12px}.k .t{font-size:11px;color:#94a3b8}.k .v{font-size:24px;font-weight:700;margin-top:4px}'+
 '.chart{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:12px}.chart .h{font-size:12px;color:#94a3b8;margin-bottom:8px}'+
 '.svg{width:100%;height:180px}.tbl{width:100%;border-collapse:collapse;background:#1e293b;border-radius:12px;overflow:hidden}'+
 '.tbl th,.tbl td{padding:8px 10px;font-size:12px;border-bottom:1px solid #334155;text-align:left}'+
 '.tbl th{color:#94a3b8;background:#0b1220}.st{color:#94a3b8;font-size:12px}.st b{color:#e5e7eb}</style>');

var root = el('root');
root.innerHTML =
 '<div class="ac">'+
  '<div class="bar"><div><div class="title">容量巡检核心看板</div><div class="sub">Agent 生成的常驻子应用</div></div><div class="pills" id="pills"></div></div>'+
  '<div class="grid" id="cards"></div>'+
  '<div class="chart"><div class="h">CPU 使用率趋势</div><svg class="svg" id="svg" preserveAspectRatio="none"></svg><div class="st" id="note"></div></div>'+
  '<div class="tbl" id="tbl" style="margin-top:12px"></div>'+
 '</div>';

var state = { start: '2020-01-01' };
var pills = [['2020-01-01','显示全部'],['2026-08-26','今天'],['2026-08-01','近 7 天']];
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function fmt(n){ return n==null?'—':Number(n).toFixed(2); }
/* —— DOM 安全辅助: 任何 getElementById 的写入都必须判空, 否则元素不存在时
 * 会抛 "Cannot set properties of null (setting 'textContent')" 把整屏弄崩。 — */
function el(id){ return document.getElementById(id); }
function take(id, fn){ var e=el(id); if(e) fn(e); }       // 元素存在才操作
function setH(id, html){ take(id, function(e){ e.innerHTML=html; }); }

function renderPills(){
  setH('pills', pills.map(function(p){
    return '<button class="pill'+(p[0]===state.start?' on':'')+'" data-s="'+p[0]+'">'+p[1]+'</button>';
  }).join(''));
}
function draw(rows){
  var svg=el('svg'), W=680, H=180, pad=22, w=W-pad*2, h=H-pad*2;
  var nums=(rows||[]).map(function(r){return Number(r.cpu)||0;});
  var max=Math.max.apply(null,nums.concat([1]));
  var pts=(rows||[]).map(function(r,i){
    return [pad+(i*(w/Math.max(1,(rows.length-1)))), pad+h-((Number(r.cpu)||0)/max)*h];
  });
  var line=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');
  var area=line+' L'+(pts.length?pts[pts.length-1][0].toFixed(1):pad)+','+(pad+h)+' L'+(pts.length?pts[0][0].toFixed(1):pad)+','+(pad+h)+' Z';
  var g='';
  for(var i=0;i<=4;i++){ var y=pad+h-(h*i/4); g+='<line x1="'+pad+'" y1="'+y+'" x2="'+(W-pad)+'" y2="'+y+'" stroke="#334155" stroke-width="1"/>'; }
  if(svg){ svg.innerHTML = g +
    (pts.length? '<path d="'+area+'" fill="rgba(37,99,235,0.18)"/>' : '') +
    (pts.length? '<path d="'+line+'" fill="none" stroke="#3b82f6" stroke-width="2.5"/>' : '') +
    pts.map(function(p){return '<circle cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="3" fill="#3b82f6"/>';}).join('');
  }
  setH('note', '峰值: <b>'+fmt(max)+'</b> · '+(rows||[]).length+' 个点');
}
function load(){
  var p = { bind_params: { start: state.start } };
  Promise.all([
    GyraAppCard.op('query.sql', p, 'q_totals'),
    GyraAppCard.op('query.sql', p, 'q_trend'),
    GyraAppCard.op('query.sql', p, 'q_metrics')
  ]).then(function(res){
    var total=(res[0]&&res[0].rows&&res[0].rows[0])||{};
    setH('cards',
      '<div class="k"><div class="t">记录数</div><div class="v">'+fmt(total.n)+'</div></div>'+
      '<div class="k"><div class="t">平均值</div><div class="v">'+fmt(total.avg)+'</div></div>'+
      '<div class="k"><div class="t">最大值</div><div class="v">'+fmt(total.max)+'</div></div>');
    draw(res[1]&&res[1].rows);
    var rows=(res[2]&&res[2].rows)||[];
    setH('tbl',
      '<table style="width:100%"><thead><tr><th>服务</th><th>指标值</th><th>日期</th></tr></thead><tbody>'+
      rows.map(function(r){return '<tr><td>'+esc(r.service)+'</td><td>'+fmt(r.cpu)+'</td><td>'+esc(r.day)+'</td></tr>';}).join('')+
      '</tbody></table>');
  }).catch(function(e){
    setH('cards','<div class="st">取数失败: '+esc(e.message)+'</div>');
  });
}
take('pills', function(e){ e.addEventListener('click', function(ev){
  var b=ev.target.closest('button'); if(!b) return;
  state.start=b.getAttribute('data-s'); renderPills(); load();
}); });
renderPills(); load();
```

> 上面代码可直接作为模板。把它替换成任何更复杂的布局、主题、图表都可。

---

## 五、Queries 数据契约

`queries` 是命名查询，是「生成期 dry-run → 运行期冻结取数」的载体：

| kind | 字段 | 说明 |
|---|---|---|
| `metric` | `metric_id`（必填）、`group_by`、`filters`、`time_range` | 走 ECP 语义层，构造级防注入，需指标 `confirmed` |
| `sql` | `sql`（必填，只读）、`datasource_id`（必填）、`bind_params`、`limit` | 走只读 SQL + 绑定参数；用 `:name` 占位，`bind_params` 提供值 |

**防注入**：`sql` 只允许 `SELECT/WITH/SHOW/DESC/DESCRIBE/EXPLAIN` 开头；所有动态值（时间、维度）必须走 `bind_params` 绑定，**禁止**字符串拼进 SQL。

**切 tab / 选时间**：优先由卡片自身维护 UI 状态（`activeTab`、`timeRange`），变化后重新调 `GyraAppCard.op` 取数即可；`config.params` + `GyraAppCard.params()/onParamChange` 用于需要宿主统一管理参数的情形。

---

## 六、生成后校验与落库

> **默认落库方式(一键导入)**：沙箱可能访问不到 Gyra Web 服务端口，因此不要强求自行调用落库接口。最终产物是一个 payload JSON 文件，交给开发者在**场景空间内一键导入**即可：
> - 打开空间主页 → 「应用卡片」区块点「导入」，上传/粘贴该 JSON 落库；
> - 或在该 JSON 对应的运行结果/交付文件预览里，点「导入为场景空间子应用」。
> 两种方式都等价于 `dry_run:false` 的正式创建（系统自动补 `workspace_id`、`name`、`permissions`），无需人工粘贴 `code`+`queries`+`config` 到管理界面。

1. **先 dry-run（能访问到服务时）**：`POST /api/v1/serve_app_card_service/app_cards/create`，`dry_run: true`，后端逐条校验查询（metric 走 preview / sql 走只读试跑）。逐条 `items[].ok` 为 true 才允许正式落库。
2. **交付文件**：把最终 payload 写成 JSON 文件（如 `app_card_payload.json`）——**务必用 `json.dumps` / `JSON.stringify` 序列化输出**（见「二、`code` 字段…」与「七、交付前自检」），并在写入后跑一遍自检命令确认可解析。务必在顶层带 **`meta` 签名**（`schema_name: "gyra_app_card"` + `schema_version` + `generated_by` + `generated_at`，可选 `card_name`/`icon`/`refresh_interval`），这是检测与"一键导入"的可靠依据；再含 `name`、`code`、`config`、`queries`，可选 `icon`、`permissions`。写完后明确告诉用户：去场景空间「应用卡片 → 导入」一键落库，或在该 JSON 的文件预览里点「导入为场景空间子应用」
3. **校验失败**：metric 未 confirmed → 提示先在语义层确认；sql 被拒 → 改写为只读 + `bind_params` 后重新 dry-run。
4. **可选字段**：`icon`（emoji/图标）、`permissions`（可访问角色数组，如 `["member"]`）。

> 写 JSON 文件前，**先过「七、交付前自检」**；自检不通过，就不要交付。

---

## 七、交付前自检（JSON 合法性，必做）

**最终交付物必须是一份能被 `JSON.parse` / `json.loads` 正常解析的合法 JSON**，这是硬性要求，不满足就重写，不要交付。

### 0. 必做：最后一步运行随技能分发的校验脚本 `validate.py`

本技能目录（与 `SKILL.md` 同目录）内置了校验脚本 `validate.py`（可直接用 shell 执行）。**每次生成 payload 后，最后一步必须运行它，只有输出 `[OK]` 且退出码为 0 才能交付。** 不要跳过。

```bash
python validate.py app_card_payload.json
```

`validate.py` 会逐项校验：JSON 可解析、`meta.schema_name`/`schema_version`/`generated_by`/`generated_at` 签名、`name`/`kind`/`code`/`config`/`queries` 必需字段、`code` 的括号配对与字符串闭合，以及每个 query 的 `metric_id`/`datasource_id`、只读 SQL 前缀与 `bind_params` 占位对齐。校验失败会列出具体问题（例如 `code` 引号未转义导致的非法 JSON），据其修复后重跑，直到输出 `[OK]`。

### 1. 用序列化器产出，禁止手拼 JSON 字符串

`code` 是「整段 JS 源码塞进 JSON 字符串」，最容易漏转义 `"` 导致整份文件报废。一律按下述方式产出，**禁止** f-string / 模板串手拼 JSON：

- Python：先构造 `dict`，再 `json.dumps(payload, ensure_ascii=False, indent=2)`。
- JS：先构造对象，再 `JSON.stringify(payload, null, 2)`。

### 2. code 转义：正确 vs 错误

错误（`code` 里 HTML 属性双引号是裸的 → 解析失败）：
```json
{"code":"root.innerHTML='<div class="sk">x</div>'"}
```
正确（每个 `"` 都转义为 `\"`，JSON 才能解析）：
```json
{"code":"root.innerHTML='<div class=\"sk\">x</div>'" }
```

### 3. 交付前自检清单（逐条核对）

- [ ] 整份 JSON 能成功解析（`JSON.parse` / `json.loads`）。
- [ ] 再序列化回来，`meta.schema_name === "gyra_app_card"`、`schema_version`、`generated_by`、`generated_at` 齐全。
- [ ] `name` 为非空字符串；`kind` ∈ `dashboard`/`board`/`custom`。
- [ ] `code` 存在且为非空字符串；`config` 为对象；`queries` 为数组。
- [ ] `code` 解析后是语法平衡的 JS（括号/花括号配对、字符串闭合），没有裸 `"` 破坏 JSON。
- [ ] 每个 `query`：`key` 唯一；`metric` 必须带 `metric_id`；`sql` 必须 `SELECT/WITH/SHOW/DESC/DESCRIBE/EXPLAIN` 开头且带 `datasource_id`；所有动态值走 `bind_params`（`:name` 占位），禁止字符串拼 SQL。

### 4. 一键校验命令（生成后立刻跑）

Python：
```bash
python - <<'PY'
import json, sys
s = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
d = json.loads(s)                       # 非法 JSON 会在此抛错并给出行列
assert d["meta"]["schema_name"] == "gyra_app_card", "缺少 schema_name 签名"
assert isinstance(d.get("code"), str) and d["code"].strip(), "code 缺失或为空"
assert isinstance(d.get("config"), dict), "config 应为对象"
assert isinstance(d.get("queries"), list), "queries 应为数组"
for q in d.get("queries", []):
    if q.get("kind") == "sql":
        assert q.get("datasource_id") is not None, f"{q.get('key')} 缺 datasource_id"
        assert q.get("sql", "").lstrip().upper().split()[0] in ("SELECT","WITH","SHOW","DESC","DESCRIBE","EXPLAIN"), f"{q.get('key')} 非法 SQL 开头"
    if q.get("kind") == "metric":
        assert q.get("metric_id"), f"{q.get('key')} 缺 metric_id"
print("OK, name =", d.get("name"))
PY
```

Node：
```bash
node -e 'const fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(d.meta.schema_name!=="gyra_app_card")throw new Error("缺 schema_name");if(!d.code)throw new Error("code 为空");console.log("OK",d.name);' app_card_payload.json
```

> 校验失败就按「八、常见失败与修正」对症处理，直到通过再交付。只有自检通过的文件才能让「场景空间 → 应用卡片 → 导入」成功。

---

## 八、常见失败与修正

- 指标没值 → 确认 `metric_id` 在本 workspace 已 `confirmed`，`time_range` 有数据。
- SQL 被拒 → SELECT 开头、去写操作、动态值改 `bind_params`。
- 卡片空白 → 检查 `code` 是否抛异常（渲染器会捕获并显示错误态），是否用了 `GyraAppCard.op` 取数。
- `trust==="none"` → 用 `error` 渲染错误态；核对 metric/sql 配置。
- 交互失效 → 检查 `code` 里的监听器是否绑定到已渲染的元素，以及 params 是否传对。
