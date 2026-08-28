# 校验、落库与交付

对应工作流「步骤 5：校验与交付」。

## 1. 落库方式（默认：一键导入）

沙箱可能访问不到 Gyra Web 服务端口，因此**不要强求自行调用落库接口**。最终产物是一个 payload JSON 文件，交给开发者在**场景空间内一键导入**即可：

- 打开空间主页 → 「应用卡片」区块点「导入」，上传/粘贴该 JSON 落库；
- 或在该 JSON 对应的运行结果/交付文件预览里，点「导入为场景空间子应用」。

两种方式都等价于 `dry_run:false` 的正式创建（系统自动补 `workspace_id`、`name`、`permissions`），无需人工粘贴 `code`+`queries`+`config` 到管理界面。

**先 dry-run（能访问到服务时）**：`POST /api/v1/serve_app_card_service/app_cards/create`，`dry_run: true`，后端逐条校验查询（metric 走 preview / sql 走只读试跑）。逐条 `items[].ok` 为 true 才允许正式落库。

**校验失败**：metric 未 `confirmed` → 提示先在语义层确认；sql 被拒 → 改写为只读 + `bind_params` 后重新 dry-run。

## 2. 交付文件名（必须带版本+时间戳）

把最终 payload 写成 JSON 文件，**文件名必须携带版本号与时间戳**，格式（卡片名只取小写字母/数字/下划线 slug，`v` 后用 `meta.version`，时间用 UTC 的 `YYYYMMDDTHHMMSSZ`）：

```
app_card_<card_slug>_v<meta.version>_<YYYYMMDDTHHMMSSZ>.json
```

例：`app_card_capacity_dashboard_v1.0.0_20260826T103000Z.json`。**不要**使用不带版本/时间戳的通用名（如 `app_card_payload.json`）或相互覆盖文件名；同卡片每次交付都是新版本 → 新时间戳 → 新文件名。

- **版本**：从 `1.0.0` 起每次增量（修复 bug → patch `x.y.z+1`；新增 tab/查询/参数 → minor `x.(y+1).0`；重构/破坏性改动 → major `(x+1).0.0`）。
- **时间戳**：取 UTC 当前时刻 `datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")`（或 JS `new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')`）。
- **内容要求**：文件内容**务必用 `json.dumps` / `JSON.stringify` 序列化输出**（`code` 转义细则见 `docs/02_code_contract.md`）。务必带 `meta` 签名（`schema_name` + `schema_version` + `generated_by` + `version` + `generated_at`），并保证**文件名中的 `v<meta.version>` 与 `meta.version` 一致**、**文件名时间戳与 `meta.generated_at` 同一天**；再含 `name`、`code`、`config`、`queries`，可选 `icon`、`permissions`。

写完后明确告诉用户：去场景空间「应用卡片 → 导入」一键落库，或在该 JSON 的文件预览里点「导入为场景空间子应用」。

> 写 JSON 文件前，**先过下面「5. 自检清单」**；自检不通过，就不要交付。

## 3. 交付前逐个验证取数（必做）

交付前，**对每个 `metric` 和 `sql` 都用 hook 工具（`app_card_preview` / `db({action:"app_card_preview",...})`）执行一次取数**，逐条确认：

- `trust !== "none"`（不失败）；
- `rows` 有值（非空，样例数据符合预期）；
- 返回的列名（`columns` / `rows[0]` 的键）与 `code` 里访问的 `r.代数名` 完全一致；
- SQL 只读、前缀合法、`bind_params` 占位齐全；metric 已 `confirmed`。

**只要有一条查询取不到数据、报错或字段对不上，就修到通过再交付**。

> **交付门禁**：未逐条跑过 hook 工具验证的 payload，**禁止**进入 `validate.py`、**禁止**交付。只用 `execute_sql` 探数而未走 hook 工具逐条验证的，视为未验证。

## 4. 必做：最后一步运行校验脚本 `validate.py`

本技能目录（与 `SKILL.md` 同目录）内置 `validate.py`（可直接用 shell 执行）。**每次生成 payload 后，最后一步必须运行它，只有输出 `[OK]` 且退出码为 0 才能交付。** 不要跳过。

```bash
python validate.py app_card_capacity_dashboard_v1.0.0_20260826T103000Z.json
```

`validate.py` 会逐项校验：JSON 可解析、`meta.schema_name`/`schema_version`/`generated_by`/`version`/`generated_at` 签名、**交付文件名的版本+时间戳格式（`app_card_<slug>_v<version>_<ts>.json`）并与 `meta.version`/`meta.generated_at` 对齐**、`name`/`kind`/`code`/`config`/`queries` 必需字段、`code` 的括号配对与字符串闭合，以及每个 query 的 `metric_id`/`datasource_id`、只读 SQL 前缀与 `bind_params` 占位对齐。校验失败会列出具体问题（例如 `code` 引号未转义导致的非法 JSON、文件名缺版本时间戳），据其修复后重跑，直到输出 `[OK]`。

## 5. 交付前自检清单（逐条核对）

- [ ] 整份 JSON 能成功解析（`JSON.parse` / `json.loads`）。
- [ ] 再序列化回来，`meta.schema_name === "gyra_app_card"`、`schema_version`、`generated_by`、`version`、`generated_at` 齐全。
- [ ] **文件名带版本+时间戳**：形如 `app_card_<slug>_v<meta.version>_<YYYYMMDDTHHMMSSZ>.json`，且 `v` 后的版本与 `meta.version` 一致、文件名里的日期与 `meta.generated_at` 同一天（`validate.py` 会自动核对）。
- [ ] `name` 为非空字符串；`kind` ∈ `dashboard`/`board`/`custom`。
- [ ] `code` 存在且为非空字符串；`config` 为对象；`queries` 为数组。
- [ ] `code` 解析后是语法平衡的 JS（括号/花括号配对、字符串闭合），没有裸 `"` 破坏 JSON。
- [ ] **逐个验证取数（hook 工具）**：每个 `metric`/`sql` 都用 `app_card_preview` / `db` 执行过，`trust` 非 `none`、`rows` 有值、列名与 `code` 里 `r.字段` 完全一致。
- [ ] 每个 `query`：`key` 唯一；`metric` 必须带 `metric_id`；`sql` 必须 `SELECT/WITH/SHOW/DESC/DESCRIBE/EXPLAIN` 开头且带 `datasource_id`；所有动态值走 `bind_params`（`:name` 占位），禁止字符串拼 SQL。
- [ ] `code` 里对 op 结果的 `rows` 一律用**对象数组访问**（`rows.map(r => r.列名)`），**不要**用工具预览看到的下标写法（`rows[i][j]` / `r[0]`）；否则运行期（rows 是对象数组）会渲染不出数据。
- [ ] **分区块异步取数（基础规范）**：布局先渲染骨架；每个数据区块一个 `query_key` + 独立 `loadXxx()` + 独立 loading/empty/error 三态；各区块并行发出、各自渲染；**没有**用一个查询/一次调用拉全卡所有 SQL 后整体渲染。

## 6. 一键校验命令（生成后立刻跑）

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
node -e 'const fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(d.meta.schema_name!=="gyra_app_card")throw new Error("缺 schema_name");if(!d.code)throw new Error("code 为空");console.log("OK",d.name);' app_card_capacity_dashboard_v1.0.0_20260826T103000Z.json
```

> 校验失败就按下节「常见失败与修正」对症处理，直到通过再交付。只有自检通过的文件才能让「场景空间 → 应用卡片 → 导入」成功。

## 7. 常见失败与修正

- 指标没值 → 确认 `metric_id` 在本 workspace 已 `confirmed`，`time_range` 有数据。
- SQL 被拒 → SELECT 开头、去写操作、动态值改 `bind_params`。
- 卡片空白 → 检查 `code` 是否抛异常（渲染器会捕获并显示错误态），是否用了 `GyraAppCard.op` 取数。
- **首屏久白、或一慢全卡一起转圈/一起失败** → 违反了「布局先渲 + 分区块异步取数」基础规范：把布局骨架先渲染出来，每个数据区块拆成独立 `loadXxx()` + 独立三态，并行发出、各自渲染；不要用一个 `Promise.all` 等所有 SQL 齐了才整屏渲染。
- **明明取到数据但表格/卡片空白或全 `—`** → 多半是 `rows` 访问方式错了：运行期 `rows` 是对象数组，必须 `r.列名`；如果照搬了工具预览的下标写法（`r[0]` / `rows[i][j]`）就会取不到值。改用 `r.列名`，且字段名 = SQL 别名 / 指标输出列名。
- `trust==="none"` → 用 `error` 渲染错误态；核对 metric/sql 配置。
- 交互失效 → 检查 `code` 里的监听器是否绑定到已渲染的元素，以及 params 是否传对。