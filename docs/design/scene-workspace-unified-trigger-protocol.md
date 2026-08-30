# 场景空间统一输入协议设计

> 范围：场景空间（scene workspace）对话输入框及场景内所有输入点
> 版本：v1.1（决策已定，待排期）
> 状态：7 项决策已拍板（§9）｜P0 已实现 T1–T9（见 §8.3）｜T10 真实链路待验（需起服务）｜3 项仍未决（§9 表二）

---

## 0. 结论先行

**目标**：把 `/` `@` `#` 从三个零散功能，升级为**一套输入协议（Trigger Protocol）**——同一套触发规则、同一个浮层组件、同一份数据协议，让场景空间里所有输入点行为完全一致。

**三个入口的语义分工（整个设计的地基）**：

| Trigger | 语义 | 回答的问题 | 选中后形态 | 生命周期 | 现状 |
|---|---|---|---|---|---|
| `/` | 能力编排 | 用什么做 | chip（技能/MCP 可多选，剧本单选） | 单轮（模式类命令除外） | **80% 已实现** |
| `@` | 身份切换 | 谁来做 | 接管态 banner（单选） | **会话级**，直至显式退出 | **0%** |
| `#` | 对象引用 | 对什么做 | 内联引用（多选） | 单轮 | **0%** |

**已拍板的三个设计判断**：

1. **`@` 是「身份切换」不是「委托」**。单轮委托已有 `SubAgent` 工具覆盖（模型自主调用），`@` 要解决的恰恰是"我不想经过主 Agent 转派，我要直接跟它聊"。→ **会话级 sticky，共享会话历史**。
2. **后端改动极小**。主 Agent 由 `agent_chat.py:1546` 一处 `app_detail(gpts_name)` 决定，`@` 只需在此前加一个 extractor 覆写。数据源（`/resources/list`、`artifacts/list`、`assets/list`）全部已就绪。
3. **`#` 的最大障碍是 textarea 不支持内联 chip**。→ **P0 先复用现有附件区，P1 再升级输入框**，但数据结构从 P0 起就按内联引用设计。

**两个调研中新发现的关键事实**（显著降低了实现成本）：

- **任务指令框也是 `TextArea`**（`tasks/create/client.tsx:375-385`），且触发器创建页已重定向到该页（`triggers/create/client.tsx:7-25`）。所以"剧本任务 / 触发器接 `#`"与"对话输入框接 `#`"是**同一种控件**，只需按上下文启用不同的 trigger 集合——"全局一致"因此落到代码复用层面，而非仅视觉对齐。
- **命令注册表可零建表实现**：`workspace_resource` 表加 `type='command'` 即可——CRUD、`/resources/list`、配置 UI 全部现成；且物化器对未知 type 是 **skip 而非报错**（`materializer.py:483-488`），而命令本就不需要物化给 Agent。代价从"新表 + CRUD + 迁移"降到"后端 2 行白名单"。

**改动落点**：前端 + `gyra-serve`（V1）单点，`gyra-core`（V2）零改动。

---

## 1. 现状盘点

### 1.1 前端

| 项 | 位置 | 现状 |
|---|---|---|
| 对话页路由 | `app/workspaces/detail/page.tsx` | 薄壳，逻辑在 `client.tsx` → `scene-workspace-shell.tsx` |
| 输入框 | `app/workspaces/detail/agent-workspace-input.tsx` | antd `Input.TextArea`（`:935`），非富文本 |
| 唯一 trigger 检测 | `agent-workspace-input.tsx:645-652` | **只认 `/`，且只在行首**：`v.startsWith('/') && !playbookCommand` |
| `/` 菜单 | `components/chat/input/slash-menu.tsx` | 已覆盖 playbook/skill/mcp/command 四类，键盘导航完善（`:218-243`） |
| `+` 鼠标入口 | `components/chat/input/plus-menu.tsx` | 与 `/` 共享数据，面板含 7 类 |
| 附件卡片 | `agent-workspace-input.tsx:793-800` | 60×60 卡片，位于输入框上方 |
| chip 组件 | `plus-menu.tsx:566-600` `SelectionChip` | 5 档主题色，支持 icon/prefix/移除 |
| payload 组装 | `app/workspaces/detail/scene-agent-send-data.ts` | 纯函数，有单测 |
| 请求发送 | `hooks/use-chat.ts:81` | `const params = { ...data, app_code }`，`app_code` 在 hook 初始化时固定 |

**关键缺口**：`activeTrigger` 概念不存在，`selectedSubAgent` / `resourceRefs` 状态不存在。

### 1.2 后端

| 项 | 位置 | 现状 |
|---|---|---|
| 子 Agent 配置 | `workspace_resource` 表，`type='app'`，`physical_ref=app_code` | 已有，前端配置 UI 在 `assets/capability-tab.tsx:106` |
| 子 Agent 列表接口 | `POST /api/v1/serve_workspace_service/resources/list {workspace_id, type:"app"}` | **已就绪**，前端 `listResources` 已封装 |
| 主 Agent 决定点 | `agent/agents/chat/agent_chat.py:1546` `app_detail(gpts_name)` | 单点，唯一决定因素 |
| 已有子 Agent 委托 | `gyra-core/.../actions/agent_action.py:348` `SubAgent` Action | 独立 conv，模型自主调用 |
| `chat_in_params` 消费 | `agent_chat.py` 共 6 处 | 见表 7.2 |
| 交付产物 | `POST /serve_artifact_service/artifacts/list` | 已就绪，前端 `listArtifacts` |
| 空间资产 | `POST /serve_workspace_asset_service/assets/list` | 已就绪，前端 `listAssets` |
| 命令注册表 | —— | **不存在**，3 条命令前端硬编码（`agent-workspace-input.tsx:679-684`） |

### 1.3 差距矩阵

| 能力 | 前端 | 后端 | 数据接口 | 缺口性质 |
|---|---|---|---|---|
| `/` 技能 | ✅ | ✅ `skill(gyra)` 分支 | ✅ `getSkillList` | 仅触发位置限制 |
| `/` MCP | ✅ | ✅ `mcp(gyra)` 分支 | ✅ `getMCPList` | 仅触发位置限制 |
| `/` 剧本 | ✅ | ✅ `playbook_command` 分支 | ✅ `listPlaybooks` | 仅触发位置限制 |
| `/` 命令 | ✅ | 部分（plan/compact 有落点，clear 纯前端） | ❌ 无注册表 | 需新建命令源 |
| `@` 子 Agent | ❌ | ❌ 无 extractor | ✅ `resources/list` | **全链路待建** |
| `#` 资源文件 | ❌ | 部分（`common_file` 通道可用） | ✅ `artifacts/list`、`assets/list` | **前端全建 + 后端判类型** |

---

## 2. 核心设计：Trigger 协议

### 2.1 触发规则（三个 trigger 共用）

**现状问题**（`agent-workspace-input.tsx:651`）：

```ts
setShowPlaybook(v.startsWith('/') && !playbookCommand);
```

只在行首触发，与 Slack / Notion / Linear 的通用习惯不符——用户在句子中间写"帮我看下 @ 这个"时不应失效。

**新规则**：

```
激活条件（同时满足）：
  1. 光标前紧邻字符 c ∈ {'/', '@', '#'}
  2. c 位于文本开头，或其前一个字符是空白（含中文全角空格）
  3. c 与光标之间无空白字符（处于"过滤词"状态）

关闭条件（任一满足）：
  1. 输入空白字符
  2. trigger 字符被删除
  3. 光标移出该 token 范围
  4. Esc
  5. 完成选中
```

**伪代码**（替换 `handleChange`）：

```ts
const TRIGGERS = ['/', '@', '#'] as const;
type Trigger = typeof TRIGGERS[number];

interface TriggerState {
  char: Trigger;
  start: number;   // trigger 字符在文本中的下标
  query: string;   // 过滤词
}

function detectTrigger(text: string, caret: number): TriggerState | null {
  if (caret <= 0) return null;
  const before = text.slice(0, caret);
  const idx = before.lastIndexOf(...TRIGGERS.map(t => before.lastIndexOf(t)).filter(i => i >= 0));
  // 取最后一个 trigger 位置
  const char = text[idx] as Trigger;
  if (!TRIGGERS.includes(char)) return null;
  if (idx > 0 && !/\s|　/.test(text[idx - 1])) return null;   // 前置必须是空白或开头
  const query = before.slice(idx + 1);
  if (/\s|　/.test(query)) return null;                        // 过滤词里不能有空白
  return { char, start: idx, query };
}
```

> ⚠️ 输入法保护：`handleKeyDown`（`:633`）已有 `isComposing` 判断，改造时必须保留，否则中文输入选词会被菜单截获。

### 2.2 与 `+` 按钮的关系

`+` 是**鼠标入口**，`/` `@` `#` 是**键盘入口**，两者共享同一套菜单组件与数据源，只是唤起方式不同：

| | 唤起方式 | 定位锚点 | 是否需要 trigger 字符 |
|---|---|---|---|
| `+` | 点击按钮 | 按钮 | 否，选中后不写入文本 |
| `/` `@` `#` | 键入字符 | 光标位置 | 是，选中后清掉 trigger token |

**统一原则**：`PlusMenu` 与三个 trigger 菜单共用 `TriggerMenu` 组件的 items 构建逻辑，保证"鼠标能点的和键盘能打的完全一致"。

### 2.3 生命周期对比

这是三个入口最容易做混的地方，必须明确：

| | 生效范围 | 状态存放 | 清空时机 |
|---|---|---|---|
| `/` 技能 | 本轮 | `selectedSkills[]` | 发送后清空 |
| `/` MCP | 本轮 | `selectedMcps[]` | 发送后清空 |
| `/` 剧本 | 本轮 | `playbookCommand` | 发送后清空 |
| `/` 命令·模式类（plan/compact） | **下一轮**（sticky） | `planMode` / `compactMode` | 发送后清空 |
| `/` 命令·即时类（clear） | 立即执行 | 不进输入框 | —— |
| `@` 子 Agent | **会话级**（sticky） | `activeSubAgent` | 用户显式退出或 @ 另一个 |
| `#` 资源 | 本轮 | `resourceRefs[]` | 发送后清空 |

---

## 3. `/` 能力编排菜单

### 3.1 现有结构（直接复用）

`slash-menu.tsx:132-188` 已构建的分组：

```
addFile     文件      → 上传（前端）
playbook    剧本      → chip → chat_in_param(playbook_command)
skill       技能      → chip → chat_in_param(resource, skill(gyra))
mcp         MCP 服务  → chip → chat_in_param(resource, mcp(gyra))
command     命令      → 前端硬编码 3 条，不随消息发送
```

### 3.2 变更点

| # | 变更 | 说明 |
|---|---|---|
| 1 | 触发位置：行首 → 任意位置 | 见 §2.1，与 `@` `#` 统一 |
| 2 | 清词逻辑：`text.replace(/^\/\S*\s*/, '')` → 按 token 区间删除 | 现状硬编码行首正则（3 处：`:659` `:694` `:711`），必须改为按 `start` 下标删除 |
| 3 | 命令组 UI 分组标题明确为「会话命令」 | 与"能力挂载"语义区隔 |

### 3.3 命令组的定位重塑（建议）

现状问题：「压缩上下文 / 清理会话 / 规划模式」与「技能 / MCP / 剧本」不是一类东西——前者是**会话行为**，后者是**能力挂载**，混在一组里语义不清。

**建议**：保留在 `/` 菜单（用户心智一致），但 UI 上明确分组，并按行为分两类：

| 类型 | 命令 | 选中后行为 |
|---|---|---|
| 即时执行型 | 清理会话 | 立即执行，不进输入框 |
| 模式开关型 | 规划模式、压缩上下文 | 变成 chip，sticky 到下一轮发送 |

### 3.4 命令注册表（本期实现，零建表）

**决策**：命令本期即后端可配，但**不新建表**——复用 `workspace_resource`，`type='command'`。

**为什么可行**：

- CRUD 全现成：`POST /resources/add|remove|update|list`（`workspace/api/endpoints.py:269-322`）
- 配置 UI 全现成：`assets/capability-tab.tsx:106` 是 `{ key: 'app', title: '子智能体', items: ... }` 的数组，加一项即可获得完整的增删改查
- 物化器对未知 type 是 **skip + warning**，不报错（`materializer.py:483-488`）——命令本就不需要物化成 `AgentResource` 给 Agent，跳过正是期望行为

**唯一后端改动**（仅为消除日志噪音，非必需）：

```python
# materializer.py，_MATERIALIZE_DISPATCH 附近
_NON_AGENT_RESOURCE_TYPES = {"command"}   # 仅前端消费，不物化给 Agent

# materialize_resources 循环内，skip 分支前插入
if rtype in _NON_AGENT_RESOURCE_TYPES:
    continue
```

**存储形态**：

| 列 | 存什么 |
|---|---|
| `type` | `'command'` |
| `name` | 展示名，如"压缩上下文" |
| `physical_ref` | 命令标识，如 `'compact'` |
| `config_json` | `{"kind":"toggle","description":"...","payload":{"force_compress":true}}` |
| `is_active` | 是否在该空间启用 |

**接口形态**：

```ts
interface SceneCommand {
  resource_id: number;
  command: string;                  // physical_ref
  name: string;                     // 展示名
  description: string;
  kind: 'immediate' | 'toggle';
  scope: 'session' | 'workspace';
  payload?: Record<string, unknown>;  // toggle 类携带的 ext_info 键，如 { force_compress: true }
}
```

**内置命令种子**：3 条现有命令（压缩上下文 / 清理会话 / 规划模式）作为系统内置，空间可追加自定义命令。菜单展示顺序：内置在前，空间自定义在后。

---

## 4. `@` 子 Agent 接管

### 4.1 语义澄清（最关键的设计决策）

**必须先与已有的「子 Agent 委托」划清界限**：

| | 已有的「子 Agent 委托」 | 新增的「`@` 接管」 |
|---|---|---|
| 发起者 | 主 Agent（LLM 自主决策） | **用户**（显式 @ 选择） |
| 触发 | 模型调用 `SubAgent` 工具 | 输入框键入 `@` |
| 会话 | **独立 conv**（`capability.py:196` 新建 uuid） | **共享当前 conv** |
| 结果流向 | 返回摘要给主 Agent，主 Agent 继续 | **直接输出给用户，主 Agent 让位** |
| 代码位置 | `gyra-core/.../agent_action.py:348` | 新增：`agent_chat.py` 覆写 |
| 是否已有 | ✅ 生产在用 | ❌ 待建 |

**结论：`@` = 会话级身份切换，不是单轮委托。**

理由：单轮委托已被 `SubAgent` 工具完整覆盖，再做一个是功能重复。`@` 要解决的正是"跳过主 Agent 转派，直接和它对话"——如果只生效一轮，用户每句话都得重新 @，体验上不成立。

### 4.2 交互形态

```
┌────────────────────────────────────────────────┐
│ ⬡ 当前由【数据分析专家】接管 · 退出             │  ← 接管 banner，常驻
├────────────────────────────────────────────────┤
│                                                │
│ 帮我看下这份报表 @                              │
│                                                │
└────────────────────────────────────────────────┘
```

- 选中子 Agent 后，输入框**上方**出现接管 banner，而非输入框内 chip
- banner 常驻直到：点击「退出」/ `@` 选择另一个 / 切换会话
- 退出后恢复空间默认 Agent（`ws.default_agent_app_code`）
- 接管态下继续 @ 其他子 Agent = 直接换人，不叠加

### 4.3 后端实现（最小改动路径）

**唯一改动点**：`agent_chat.py:1546` 之前覆写 `gpts_name`。

```python
# 现状 agent_chat.py:1541-1549
app_service = get_app_service()
gpt_app: GptsApp = await app_service.app_detail(
    gpts_name, specify_config_code, building_mode=False
)
```

**新增 extractor**（紧邻 `:1409` `_extract_model` 放置，与 `:1396` `_extract_playbook_command` 同构）：

```python
@staticmethod
def _extract_subagent(chat_in_params) -> Optional[Dict[str, Any]]:
    """从 chat_in_params 抽取 @ 接管指定的子 Agent。"""
    if not chat_in_params:
        return None
    for p in chat_in_params:
        if getattr(p, "param_type", None) == "subagent":
            try:
                return json.loads(p.param_value)
            except (TypeError, ValueError, AttributeError):
                return None
    return None
```

**覆写位置**（`aggregation_chat` 内，`app_detail` 之前）：

```python
subagent = self._extract_subagent(chat_in_params)
if subagent and subagent.get("app_code"):
    gpts_name = subagent["app_code"]          # 主 Agent 让位
    ext_info["active_agent"] = {
        "app_code": subagent["app_code"],
        "app_name": subagent.get("app_name", ""),
        "main_app_code": origin_gpts_name,    # 保留原始主 Agent 供审计/UI
    }
    ext_info["subagent_depth"] = 1            # 复用深度守卫，防止自我递归
```

**为什么这样改就够了**：下游 `_inner_chat`（`:3591`）→ `_build_agent_by_gpts`（`:3797`）→ `AgentContext.gpts_app_code`（`:3729`）全部读 `gpts_app`，没有别处硬编码主 Agent，一处覆写整条链路自动跟随。

**V1/V2 通吃**：`V2Agent`（PIXIU）也是从 `_build_agent_by_gpts` 构建出来的（`v2_agent.py:92` 继承 `ReActMasterAgent`），所以 V2 链路同样受益，**gyra-core 零改动**。

**必须同步处理的 3 个副作用**：

| # | 风险 | 处理 |
|---|---|---|
| 1 | `gpts_conversations.gpts_name` 落表变成子 Agent，用量/回放归属偏移 | `ext_info` 存 `main_app_code`（`_serialize_extra_for_db` 已自动序列化整个 ext_info，无需额外代码） |
| 2 | 接管后自我递归（子 Agent 的 capability_pack 里仍有自己） | 设 `subagent_depth=1`，复用 `agent_action.py:198-202` 的深度守卫 |
| 3 | `chat_in_params_to_context`（`:3345`）的 else 兜底会把 `subagent` 塞进 `llm_context` | 无害（后续只取 4 个已知键），但建议显式 `continue` 跳过，避免污染 |

### 4.4 前端实现

**不走 `app_code` 覆盖，走 `chat_in_params`**。理由：

- `use-chat.ts:81` 的 `app_code` 是 hook 初始化参数、依赖数组固定（`:222`），改成 per-message 会牵动缓存与请求构造
- 保持 `app_code` 为主 Agent，会话列表 / 归属 / 用量统计不混乱
- 后端覆写已能达到效果，前端只需多传一个 param

**改动清单**：

| 文件 | 改动 |
|---|---|
| `app/workspaces/detail/agent-workspace-types.ts` | 新增 `SubAgentRef` 接口 |
| `app/workspaces/detail/agent-workspace-input.tsx` | 新增 `activeSubAgent` 状态、接管 banner、`@` 分支 |
| `app/workspaces/detail/scene-agent-send-data.ts` | payload 增 `subAgent` 字段 → `chat_in_params` |
| `components/chat/input/slash-menu.tsx` | 抽出 `TriggerMenu`，新增 `MentionMenu` 变体 |

**数据源**：`listResources({ workspace_id, type: 'app' })`，返回 `WorkspaceResourceResponse`，关键字段：

```ts
interface SubAgentRef {
  resource_id: number;
  name: string;            // 展示名
  physical_ref: string;    // app_code ← 传给后端
  config?: { app_name?: string; app_desc?: string };
}
```

### 4.5 边界情况

| 场景 | 处理 |
|---|---|
| 空间未绑定任何子 Agent | 菜单显示空态："当前空间暂无可用子 Agent"+ 跳转配置页按钮 |
| 子 Agent 的 app 已被删除/停用 | 列表过滤 `is_active=false`，发送前校验，失效则降级为主 Agent 并提示 |
| 接管态下发送含 `/` 剧本 | 允许。剧本在建任务 + 子 Agent 执行，二者正交 |
| 接管态下刷新页面 | banner 状态丢失（未持久化）。P0 接受；P1 可从会话 `extra.active_agent` 恢复 |
| 接管态下子 Agent 又派发子 Agent | `subagent_depth` 守卫生效，超过阈值报错 |
| 运维模式 | 与简洁模式行为一致，同一组件 |

---

## 5. `#` 资源引用

### 5.1 数据源（三层，全部已就绪）

| 层 | 存储 | 接口 | 前端封装 | 说明 |
|---|---|---|---|---|
| 交付产物 | `server_app_artifact` | `POST /api/v1/serve_artifact_service/artifacts/list` | `listArtifacts` | 会话/任务产出的文件 |
| 空间资产 | `server_app_workspace_asset` | `POST /api/v1/serve_workspace_asset_service/assets/list` | `listAssets` | 带 maturity 沉淀的资产 |
| 已上传文件 | 会话内 | —— | 现有 `resources[]` | 本轮刚上传的 |

**菜单分组建议**：

```
# 菜单
├─ 检索框（输入文件名过滤）
├─ 交付产物    workspace 内 artifact
├─ 空间资产    workspace 内 asset（按 maturity 排序）
└─ 任务链接    workspace 内 task（见 §5.3）
```

### 5.2 引用形态：最大的技术取舍

**约束**：输入框是 antd `TextArea`（`agent-workspace-input.tsx:935`），**无法渲染内联 chip**。

| 方案 | 描述 | 成本 | 体验 | 风险 |
|---|---|---|---|---|
| **A 附件区复用** | 选中 → 加入输入框上方 resources 卡片区 | 低 | 中：引用与文本分离，长文本下对应关系丢失 | 无 |
| **B contenteditable** | 输入框改富文本，真内联 chip | 高 | 高 | IME 组词、粘贴、光标、选区、历史栈 |
| **C 文本 token + 装饰层** | 文本存 `#文件名`，overlay 高亮 | 中 | 中 | 文本测量、换行/滚动同步 |

**推荐：P0 走 A，P1 演进到 B。且 P0 起数据结构就按 B 设计。**

关键：P0 的引用对象就带 `start`/`end` offset，只是 P0 阶段恒为文本末尾。这样 P1 换渲染层时数据协议不用改。

```ts
interface ResourceRef {
  id: string;
  kind: 'artifact' | 'asset' | 'file' | 'task';
  label: string;
  ref_id?: number;        // artifact_id / asset_id / task_id
  content_ref?: string;   // 文件路径，供后端注入
  start: number;          // 在纯文本中的起始 offset（P0 恒为末尾）
  end: number;
}
```

### 5.3 后端注入路径

| kind | 建议 `sub_type` | 后端处理 | 说明 |
|---|---|---|---|
| `file`（本轮上传） | `common_file`（现状） | `_dispatch_uploaded_files`（`:3429`）落沙箱 | 无需改动 |
| `artifact` | `artifact`（新增） | 在 `chat_in_params_to_resource`（`:3067`）转 `AgentResource` | 已落盘，不重复上传 |
| `asset` | `asset`（新增） | 同上 | 同上 |
| `task` | `task_link`（新增） | 进 `ext_info.focus_task_id` | 任务链接，非文件 |

**⚠️ 关键陷阱**：`agent_chat.py:3387` 的 else 兜底会把未知 `param_type` 静默塞进 `llm_context`，而构造 `AgentContext` 时（`:3713-3742`）只取 `temperature/max_new_tokens/top_p/reasoning_effort` 四个键，**其余全部丢弃**。

> 也就是说：**只加前端字段不改后端 = 参数静默丢失，且无任何报错**。这是最容易踩的坑，必须在验收清单里显式验证。

### 5.4 剧本任务的 `#` 复用（跨场景一致性）

用户诉求："剧本任务也使用 `#` 唤起菜单进行选择链接"。

这不是"聊天框里多加一种资源"，而是**把 `#` 抽成一个跨场景的资源选择器**。建议抽 `ResourcePicker`：

```ts
interface ResourcePickerProps {
  workspaceId: number;
  kinds: Array<'artifact' | 'asset' | 'task' | 'file'>;  // 允许的类别
  multiple?: boolean;
  value?: ResourceRef[];
  onChange?: (refs: ResourceRef[]) => void;
  /** trigger 模式：由 # 唤起，选中后写入文本；picker 模式：表单字段，不写文本 */
  mode: 'trigger' | 'picker';
  anchorEl?: HTMLElement | null;   // trigger 模式的定位锚点
}
```

**关键实现洞察**：所有宿主都是 `TextArea`，因此抽一个 **`TriggerTextArea`**——同一套 `detectTrigger` + `TriggerMenu`，靠 `triggers` prop 决定启用哪些字符：

```tsx
<TriggerTextArea
  triggers={['/', '@', '#']}   // 对话输入框：三个全开
  ...
/>

<TriggerTextArea
  triggers={['#']}             // 任务指令框：只开 #
  ...
/>
```

任务指令框不启用 `/` 和 `@` 是有语义依据的：**剧本已经定了"用什么做"，任务已经定了"谁来做"**，指令里只剩"对什么做"。

**宿主清单**：

| # | 宿主 | 位置 | 模式 | 启用的 trigger |
|---|---|---|---|---|
| 1 | 对话输入框 | `agent-workspace-input.tsx:935` | `trigger` | `/` `@` `#` |
| 2 | 任务指令框 | `tasks/create/client.tsx:375-385` | `trigger` | `#` |
| 3 | 触发器配置 | 同上（`triggers/create` 已重定向到该页） | `trigger` | `#` |

> 原计划的 `picker` 模式（表单字段点击唤起）可以不做——既然宿主本身就是文本框，统一走 `trigger` 模式即可，少一套实现。若后续出现非文本框的绑定位（如表格行内选择），再补 `picker` 模式。

这样"全局一致"才成立：**同一套代码、同一个面板、同一份数据、同一套视觉**，只是启用范围不同。

---

## 6. 组件架构：TriggerMenu 抽象

从 `SlashMenu`（`slash-menu.tsx`）抽出通用能力，三个 trigger 共用：

```
TriggerMenu（通用浮层）                    复用 slash-menu.tsx 现有实现
├─ props
│   ├─ groups: MenuGroup[]                 ← :132-188 分组构建
│   ├─ query: string                       ← :191 matches() 过滤
│   ├─ loading / empty                     ← 各数据源不同
│   └─ onSelect(sel)                       ← 各 trigger 行为不同
├─ useImperativeHandle: handleKey(e) => boolean   ← :218-243 键盘导航，直接复用
└─ antd Popover trigger={[]} placement="topLeft"  ← :304-315

三个实例：
  SlashMenu   → 技能 / MCP / 剧本 / 命令
  MentionMenu → 子 Agent 列表
  HashMenu    → 交付产物 / 空间资产 / 任务
```

**三个菜单的差异点**（抽象时必须参数化）：

| | SlashMenu | MentionMenu | HashMenu |
|---|---|---|---|
| 选择模式 | 混合（技能/MCP 多选，剧本/命令单选） | 单选 | 多选 |
| 选中后清 trigger token | 是 | 是 | 是 |
| 产物进输入框文本 | 否（变 chip） | 否（变 banner） | 是（P1 内联）/ 否（P0 附件区） |
| 空态文案 | 无匹配项 | 暂无子 Agent + 配置入口 | 暂无资源 |
| 数据源加载时机 | 页面加载即拉（现状） | 首次 `@` 时拉 | 首次 `#` 时拉 |

---

## 7. 数据协议变更

### 7.1 `chat_in_params` 新增项

| `param_type` | `sub_type` | `param_value` | 后端处理 | 状态 |
|---|---|---|---|---|
| `subagent` | `app` | `{"app_code":"...","app_name":"..."}` | 新增：覆写 `gpts_name` | 新增 |
| `resource` | `artifact` | `{"artifact_id":1,"title":"...","content_ref":"..."}` | 新增：转 `AgentResource` | 新增 |
| `resource` | `asset` | `{"asset_id":1,"name":"...","content_ref":"..."}` | 新增：转 `AgentResource` | 新增 |
| `resource` | `common_file` | 现状文件数组 | `_dispatch_uploaded_files` 落沙箱 | 复用 |

### 7.2 `chat_in_params` 的 6 个既有消费点（改动前必查）

| # | 位置 | 作用 | 命中条件 |
|---|---|---|---|
| 1 | `agent_chat.py:1396` `_extract_playbook_command` | 抽剧本命令 | `playbook_command` |
| 2 | `agent_chat.py:1409` `_extract_model` | 抽模型名 | `model` |
| 3 | `agent_chat.py:1590-1597` | media 拼进 system prompt | `media` |
| 4 | `agent_chat.py:3067` `chat_in_params_to_resource` | 转 `AgentResource` | `resource` |
| 5 | `agent_chat.py:3345` `chat_in_params_to_context` | 兜底进 `llm_context` | **else 分支（静默丢弃）** |
| 6 | `agent_chat.py:3429` `_dispatch_uploaded_files` | 文件落沙箱 | `resource` + `sub_type ∈ FILE_RESOURCES` |

### 7.3 `ext_info` 新增项

```ts
ext_info: {
  active_agent: {              // @ 接管态，供 UI 与审计
    app_code: string;
    app_name: string;
    main_app_code: string;     // 原始主 Agent，用于用量归属与"退出接管"
  },
  refs: ResourceRef[],         // # 内联引用（P1 启用）
}
```

> `ext_info` 会被 `_serialize_extra_for_db` 整体序列化进 `gpts_conversations.extra`，**前端刷新后可从会话恢复接管态**（P1 能力）。

---

## 8. 落地计划

### 8.1 任务依赖与并行批次

```
批次 A（地基，串行）
  T1 detectTrigger 纯函数 + 单测
  T2 TriggerMenu 抽象 + TriggerTextArea
        │
批次 B（三入口前端，可并行）        批次 C（后端，可并行）
  T3  / 改造接入                      T5  @ 后端覆写
  T4  @ 接管前端                      T6  命令注册表（零建表）
  T7  # 资源引用前端                  T8  # artifact/asset 分支
        │                                   │
批次 D（联调与复用）
  T9  任务指令框接入（复用 T1/T2/T7）
  T10 端到端验收
```

---

### 批次 A — 地基

#### T1 `detectTrigger` 纯函数

| 项 | 内容 |
|---|---|
| 目标 | 把 trigger 检测从"行首硬编码"升级为通用规则，并做成可单测的纯函数 |
| 改动 | 新增 `web/src/app/workspaces/detail/trigger-detect.ts` |
| 要点 | 规则见 §2.1；返回 `{ char, start, query } \| null`；必须处理中文全角空格 |
| 验收 | 单测覆盖：行首 / 词中 / 前置非空白不触发 / 过滤词含空白不触发 / 多个 trigger 取最后一个 / 空文本 / 光标在 0 |
| 风险 | **低**。纯函数，无 DOM 依赖，可 node 环境直接跑 |

#### T2 `TriggerMenu` 抽象 + `TriggerTextArea`

| 项 | 内容 |
|---|---|
| 目标 | 从 `slash-menu.tsx` 抽出通用浮层，三个 trigger 共用 |
| 改动 | 改 `components/chat/input/slash-menu.tsx`；新增 `components/chat/input/trigger-menu.tsx`、`trigger-textarea.tsx` |
| 要点 | 复用现有实现：分组构建（`:132-188`）、过滤（`:191`）、`handleKey` 键盘导航（`:218-243`）、Popover 受控（`:304-315`）；差异点参数化（见 §6 表格） |
| 验收 | `SlashMenu` 改由 `TriggerMenu` 实现后，现有行为零回归（既有单测全绿）；方向键/Enter/Esc 与既有逻辑一致 |
| 风险 | **中**。`slash-menu.tsx` 无单测保护，重构需先补一组快照测试再动 |

---

### 批次 B — 三入口前端（T2 后可并行）

#### T3 `/` 改造接入

| 项 | 内容 |
|---|---|
| 目标 | `/` 从行首触发改为任意位置，接入统一协议 |
| 改动 | `agent-workspace-input.tsx:645-652`（检测）、`:659` `:694` `:711`（清词正则） |
| 要点 | 删除 3 处 `text.replace(/^\/\S*\s*/, '')`，改为按 `trigger.start` 下标删除 |
| 验收 | 句中键入 `/` 能唤起；选中后只删掉 `/xxx` token，不误删前文 |
| 风险 | **低**，但 3 处正则散落，需全量搜索确认无遗漏 |

#### T4 `@` 接管前端

| 项 | 内容 |
|---|---|
| 目标 | `@` 菜单 + 接管态 banner + 状态持久化于会话 |
| 改动 | `agent-workspace-input.tsx`（`activeSubAgent` 状态、banner UI）、`agent-workspace-types.ts`（`SubAgentRef`）、`scene-agent-send-data.ts`（payload） |
| 要点 | 数据源 `listResources({ workspace_id, type: 'app' })`；banner 常驻输入框上方；退出恢复 `ws.default_agent_app_code`；空态引导到配置页 |
| 验收 | 接管态下连续多轮均带 `subagent` param；退出后 param 消失；未绑定子 Agent 时显示空态引导 |
| 风险 | **低**。注意 banner 与现有 chip 区（plan/compact）的视觉层级不要打架 |

#### T7 `#` 资源引用前端

| 项 | 内容 |
|---|---|
| 目标 | `#` 菜单 + 选中进附件区 + 数据结构预留内联 |
| 改动 | `agent-workspace-input.tsx`（`resourceRefs` 状态）、`agent-workspace-types.ts`（`ResourceRef`）、`scene-agent-send-data.ts`（payload） |
| 要点 | 数据源 `listArtifacts` / `listAssets`；`ResourceRef` 带 `start`/`end` offset（**P0 恒为文本末尾**）；菜单分组：交付产物 / 空间资产 / 已上传 |
| 验收 | 选中后附件区出现对应卡片；payload 中 `sub_type` 正确；`start`/`end` 字段存在 |
| 风险 | **低** |

---

### 批次 C — 后端（可并行）

#### T5 `@` 后端覆写

| 项 | 内容 |
|---|---|
| 目标 | `chat_in_params.subagent` → 覆写主 Agent |
| 改动 | `agent_chat.py` 新增 `_extract_subagent()`（紧邻 `:1409`）；`aggregation_chat` 内 `:1546` 前覆写 |
| 要点 | 同构于 `:1396` `_extract_playbook_command`；覆写同时写 `ext_info.active_agent.{app_code, app_name, main_app_code}` 与 `ext_info.subagent_depth=1` |
| 验收 | 日志确认 `gpts_name` 已替换；`gpts_conversations.extra` 中 `active_agent` 完整；深度守卫生效 |
| 风险 | **中高**。这是唯一触碰主循环的地方，必须回归现有对话链路（含 V2/PIXIU） |

#### T6 命令注册表（零建表）

| 项 | 内容 |
|---|---|
| 目标 | 命令从前端硬编码改为空间可配 |
| 改动 | 后端：`materializer.py` 加 2 行白名单（见 §3.4）。前端：`assets/capability-tab.tsx:106` 加 `{ key: 'command', ... }`；`agent-workspace-input.tsx:679-684` 数据源改为接口拉取 + 内置种子合并 |
| 要点 | 3 条现有命令作为内置种子，空间自定义追加在后；`config_json` 存 `kind`/`payload` |
| 验收 | 配置页能增删改命令；`/` 菜单显示 内置 + 自定义；新增命令无需发版 |
| 风险 | **低**。零建表零迁移 |

#### T8 `#` artifact / asset 后端分支

| 项 | 内容 |
|---|---|
| 目标 | 已落盘的 artifact/asset 不重复上传，直接转 `AgentResource` |
| 改动 | `agent_chat.py:3067` `chat_in_params_to_resource` 增 `artifact` / `asset` 分支 |
| 要点 | 两者均不属 `FILE_RESOURCES`，不会被 `:3429` `_dispatch_uploaded_files` 重复落沙箱；需在 `:3345` `chat_in_params_to_context` 显式 `continue`，避免被 `:3387` else 兜底静默吞掉 |
| 验收 | Agent 能在沙箱读到 artifact 内容；日志确认无重复上传 |
| 风险 | **中**。⚠️ 见 §7.2 的静默丢弃陷阱，必须做反例验证 |

---

### 批次 D — 联调与复用

#### T9 任务指令框接入

| 项 | 内容 |
|---|---|
| 目标 | `#` 在剧本任务 / 触发器配置页同样可用 |
| 改动 | `tasks/create/client.tsx:375-385` 的 `TextArea` → `<TriggerTextArea triggers={['#']} />` |
| 要点 | 提交任务时，指令文本中的 `#引用` 需解析成任务绑定的资源（而非 `chat_in_params`） |
| 验收 | 任务指令框键入 `#` 能唤起同一面板；选中的资源随任务提交并可在任务详情看到 |
| 风险 | **中**。任务提交链路与对话链路不同，需确认后端任务接口如何接收资源引用（**待补：任务侧资源绑定的现有协议**） |

#### T10 端到端验收清单

1. 在文本**任意位置**键入 `/` `@` `#` 均能唤起对应菜单
2. `@` 选中子 Agent 后，后端日志确认 `gpts_name` 已替换为子 Agent `app_code`
3. `@` 接管态下**连续多轮**对话，响应均来自子 Agent，且共享前文上下文
4. 接管态下点击「退出」，下一轮恢复空间默认 Agent
5. `#` 选中 artifact 后，Agent 能在沙箱中读到该文件内容
6. **反例验证**：新增 `param_type` 未被 `agent_chat.py:3387` 静默吞掉（临时加日志或断言）
7. 中文输入法组词时按方向键 / 回车**不被菜单截获**（`isComposing` 保护）
8. `/` 选中后只删除 `/xxx` token，前文完整保留
9. 任务指令框 `#` 与对话输入框 `#` 面板、数据、视觉完全一致
10. 既有单测全绿：`__tests__/agent-workspace-input.test.tsx`、`scene-agent-send-data` 单测、`parse-workspace-view.test.ts`
11. V2（PIXIU）链路回归：覆写对 `app.agent='PIXIU'` 的应用同样生效
12. 空间未绑定子 Agent / 无交付资源时，菜单显示空态引导而非空白

---

### 8.2 后续演进

**P1 — 输入框内联化**

- `TextArea` → `contenteditable`，支持真内联 chip（引用、技能、剧本、接管态）
- 接管态从会话 `extra.active_agent` 恢复（刷新不丢，P0 阶段刷新会丢）
- 验收：输入法、粘贴图片、光标定位、撤销栈回归测试

**P2 — 命令作用域扩展**

- 命令从空间级扩展到工作区级 / 全局级，支持跨空间复用
- 若出现非文本框的绑定位（如表格行内选择），补 `ResourcePicker` 的 `picker` 模式

---

### 8.3 实现状态（2026-08-30 晚）

| 任务 | 状态 | 产出 |
|---|---|---|
| T1 detectTrigger | ✅ | `components/chat/input/trigger-detect.ts`，16 项单测 |
| T2 TriggerMenu 抽象 | ✅ | `trigger-menu.tsx`（18）、`scene-trigger-menu.tsx`（13）；`slash-menu.tsx` 改为基于通用层，**24 项既有测试零回归** |
| T3 `/` 改造 | ✅ | 行首正则 → 按 token 区间删除；句中前置空白可唤起，前置非空白（路径/网址）仍不误触发 |
| T4 `@` 接管前端 | ✅ | 接管 banner（会话级 sticky，可退出）+ `subagent` chat_in_param |
| T7 `#` 引用前端 | ✅ | 引用 chip + `artifact`/`asset` chat_in_param；数据结构带 start/end，为内联化预留 |
| T5 `@` 后端覆写 | ✅ | `agent_chat.py` 新增 `_extract_subagent()` + `gpts_name` 覆写 |
| T6 命令注册表 | ✅ | 后端白名单（`materializer.py`）+ 配置 UI（`capability-tab.tsx` 新建命令表单）+ 输入框「内置种子 + 空间自定义」合并 + toggle chip / `commandPayload` 通道 |
| T8 `#` artifact/asset | ✅ | `chat_in_params_to_resource` 分支 + `subagent` 跳过 context 兜底 |
| T9 任务指令框 | ✅ | `trigger-textarea.tsx` 接入 `tasks/create`，引用随表单提交（指令文本 + `resource_refs` 双写） |
| T10 端到端验收 | ⏳ | 单测层已覆盖（组件 53 项 + 输入框 28 项）；**真实链路需起服务验证** |

**T10 未验部分**（需要真实环境，非代码问题）：

1. 后端日志确认 `gpts_name` 被替换为子 Agent `app_code`
2. `@` 接管态连续多轮共享前文上下文
3. V2（PIXIU）链路回归：覆写对 `app.agent='PIXIU'` 的应用同样生效
4. Agent 能在沙箱读到 `#` 引用的 artifact 内容
5. **反例验证**：新增 `param_type` 未被 `agent_chat.py` 的 else 兜底静默吞掉

**自定义命令的执行语义**（T6 实现时定稿）：自定义命令统一按 **toggle** 处理——选中成
chip、可取消，发送时 `config_json.payload` 合并进 `ext_info`。内置 3 条保留各自硬编码
行为（clear 即时执行、plan/compact 模式开关）。immediate 类自定义命令需要通用即时执行
通道，P2 再做；管理员若手配 `kind:'immediate'`，前端会按 toggle 降级处理。

---

## 9. 决策记录

| # | 问题 | 决策 | 依据 |
|---|---|---|---|
| 1 | `@` 会话级 sticky 还是单轮？ | **会话级 sticky** | 单轮已有 `SubAgent` 工具覆盖，重复建设无价值 |
| 2 | `@` 接管是否共享会话历史？ | **共享 conv** | 接管 = 换人接手同一会话，上下文应连续 |
| 3 | `#` P0 走附件区还是直接做内联？ | **P0 附件区，P1 内联** | 先跑通链路再升级渲染层；数据结构 P0 起即按内联设计 |
| 4 | artifact / asset 是否落沙箱？ | **不落，新增 `sub_type` 转 `AgentResource`** | 文件已落盘，重复上传浪费 |
| 5 | 命令组是否本期后端可配？ | **是，本期实现（零建表）** | 见 §3.4；复用 `workspace_resource` 使代价降到"后端 2 行" |
| 6 | 触发器配置是否也要接 `#`？ | **要** | 触发器创建页已重定向到任务创建页，与剧本任务共用指令框 |
| 7 | 接管态下子 Agent 能否再派发？ | **可以，靠深度守卫兜底** | 保留能力，`subagent_depth=1` 防自我递归 |

> 第 5 条系按"需要"理解为「本期即后端可配」。若原意为保持前端硬编码，T6 可整块移出 P0，不影响其余任务。

**仍未决 / 需在开发中补齐**：

| # | 问题 | 影响 | 建议处理 |
|---|---|---|---|
| a | 任务侧资源绑定的现有协议是什么？`#引用` 如何随任务提交传给后端？ | T9 阻塞点 | T9 开工前先查任务创建接口的 payload 结构 |
| b | 接管态刷新后丢失（P0 不持久化） | 体验瑕疵 | P0 接受；P1 从会话 `extra.active_agent` 恢复 |
| c | 接管态下 UI 是否需要区分"子 Agent 回复"与"主 Agent 回复" | 视觉设计 | 建议 P1 随 ExecutionCapsule 重构一并考虑 |

---

## 附录：关键文件速查

| 用途 | 路径 | 关键行 |
|---|---|---|
| 输入框组件 | `web/src/app/workspaces/detail/agent-workspace-input.tsx` | 432, 645, 679, 935 |
| `/` 菜单（可复用模板） | `web/src/components/chat/input/slash-menu.tsx` | 132, 191, 218, 304 |
| payload 组装 | `web/src/app/workspaces/detail/scene-agent-send-data.ts` | 104-190 |
| 请求发送 | `web/src/hooks/use-chat.ts` | 68, 81, 222 |
| **V1 对话主循环** | `packages/gyra-serve/src/gyra_serve/agent/agents/chat/agent_chat.py` | 1493, 1546, 3067, 3345, 3387 |
| 子 Agent 能力 | `packages/gyra-serve/src/gyra_serve/agent/capabilities/app/capability.py` | 174-250 |
| 子 Agent 工具（V1） | `packages/gyra-core/src/gyra/agent/expand/actions/agent_action.py` | 198, 348 |
| 资源物化 | `packages/gyra-serve/src/gyra_serve/workspace/materializer.py` | 114, 194, 448 |
| resources/list | `packages/gyra-serve/src/gyra_serve/workspace/api/endpoints.py` | 269-280 |
| Artifact 模型 | `packages/gyra-serve/src/gyra_serve/artifact/models/models.py` | 40-60 |
| Asset 模型 | `packages/gyra-serve/src/gyra_serve/workspace_asset/models/models.py` | 46-74 |
| 子 Agent 配置 UI | `web/src/app/workspaces/detail/assets/capability-tab.tsx` | 106, 149-161 |
