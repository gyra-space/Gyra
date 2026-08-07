# 输入区 Dock 协议设计（Composer Dock Protocol）

| 字段 | 值 |
|---|---|
| 状态 | Draft |
| 创建日期 | 2026-08-07 |
| 作者 | Gyra Agent |
| 关联模块 | chat（SSE / 轮询）、gpts_memory、TodoStorage |
| 目标读者 | 架构 / 后端 / 前端 |

---

## 0. 文档定位

本文档定义 Gyra 对话页**输入框上方固定区域**（下文统一称 **Composer Dock / 输入区 Dock**）的渲染协议与机制。它取代当前"用围栏字符串拦截特定组件"的 hack 实现，把该区域升级为**可扩展的结构化 widget 容器**：SSE 实时通道与轮询回放通道共用同一数据结构，前端按 `type` 注册表渲染组件，组件自带交互契约。

阅读后应能回答：

1. 为什么现有 todo 展示方案是 hack，缺什么
2. `dock` 协议长什么样，SSE 与轮询如何同构
3. 后端如何生产 widget、如何从专用表回放
4. 前端如何用注册表渲染、如何做增量合并
5. 新增一个 widget 的最小路径是什么
6. 边界与降级策略

---

## 1. 背景与问题

### 1.1 需求来源

BAIZE 等 Agent 运行过程中用 `TodoWrite` 生成待办列表，需要固定在输入框上方展示，随状态实时更新、完成后折叠、清理或新开会话时消失。

### 1.2 现状链路（hack 实现）

```
TodoWrite 工具
  ├─ write_todos(DB 专用表)          ← 数据正确落库 ✅
  └─ build_todolist_fence()          ← 生成 ```d-todo-list\n{json}\n``` 围栏字符串
       └─ str 透传 SSE chunk          ← _deliver_push 对 str 直接 put_nowait
            └─ 前端 onMessage：
                 message.includes('```d-todo-list')  → regex 取 JSON → setTodoList
                 message.includes('```d-subagent-board') → setSubagentBoard
```

### 1.3 现状问题

| 问题 | 表现 |
|---|---|
| 拦截式 hack | 前端靠 `message.includes('```d-todo-list')` 特判；每新增一种组件就要加一段 `if`（`subagent_board` 已是第二处） |
| 轮询链路缺失 | `/api/v1/chat/query` 只返回 `vis_final / user_answer`，todo 只走 SSE。**重新打开运行中的会话，todo 面板为空** |
| 旁路线路 | 围栏是 `str` 透传，绕过 vis 转换器，与 `vis{...}` 信封结构不一致，是"三不管"地带 |

---

## 2. 设计目标

1. **结构化**：数据走统一信封，杜绝字符串围栏。
2. **可扩展**：新增组件走注册表，零特判、零改框架。
3. **双链路一致**：SSE chunk 与轮询 `/chat/query` 返回同一 `dock` 结构，前端只有一套合并逻辑。
4. **回放正确**：重开会话时从专用表恢复 widget（todo 不丢）。
5. **交互自治**：组件如何交互由组件自行定义，框架只负责"投递数据 + 回写结果"。

---

## 3. 核心概念

- **Composer Dock**：输入框上方固定渲染区域，是一个通用 widget 容器。
- **widget**：单个渲染单元，自描述（`id` + `type` + `payload`）。
- **dock 帧（frame）**：一次传输的 `{version, widgets[]}` 信封。
- **注册表（registry）**：前端 `type → React 组件` 的映射，DockPanel 据此渲染。

---

## 4. 协议定义

在现有 SSE chunk 信封、以及 `/chat/query` 响应里各加一个 `dock` 字段，**两边结构完全一致**。

### 4.1 SSE chunk（与现有 `vis` 平级）

```jsonc
data:{
  "vis": { "type": "...", "payload": {...} },   // 对话流渲染（不变）
  "dock": {                                       // 输入区 Dock（新增）
    "version": 1,
    "widgets": [
      {
        "id": "todo_list_b2x1k9",                 // 稳定 id，增量合并键
        "type": "todo_list",                      // 组件类型 → 注册表 key
        "kind": "replace",                        // replace | patch | remove
        "payload": {                              // 组件私有数据，组件自行定义
          "items": [{ "id": "t1", "title": "...", "status": "working" }],
          "current_index": 0
        }
      }
    ]
  }
}
```

### 4.2 轮询 `/api/v1/chat/query` 响应（新增 `dock` 字段）

```jsonc
{
  "conv_id": "...",
  "state": "RUNNING",
  "vis_final": "...",
  "user_answer": "...",
  "vis_render": "nex_vis_window",
  "dock": { "version": 1, "widgets": [ /* 结构与 SSE 相同 */ ] }
}
```

### 4.3 字段语义

| 字段 | 说明 |
|---|---|
| `version` | 协议版本，用于前向兼容 |
| `widgets[].id` | 稳定 id，前端按它做增量合并 |
| `widgets[].type` | 组件寻址符，`type → React 组件` |
| `widgets[].kind` | `replace` 整体覆盖 / `patch` 深合并 / `remove` 移除该 widget |
| `widgets[].payload` | 组件私有数据，schema 由对应组件定义 |

`kind:"remove"` 用于"清理 / 新开会话 widget 消失"——后端主动发一帧 remove。

---

## 5. 后端机制

### 5.1 生产端（替代围栏）

在 `gpts_memory.py` 新增统一入口，替代 `build_todolist_fence` 的字符串透传：

```python
async def push_dock_widget(self, conv_id: str, widget: dict):
    """把 dock widget 封装成统一帧推入 SSE 通道。"""
    cache = await self._get_cache(conv_id)
    if not cache:
        return
    frame = {"dock": {"version": 1, "widgets": [widget]}}
    cache.channel.put_nowait(orjson.dumps(frame).decode())
```

`TodoWrite._push_todolist_vis` 改为：把原 `vis_content` 作为 `payload`，`vis_tag()` 作为 `type`，构造 widget 后调 `push_dock_widget`。**不再产生任何字符串围栏。**

### 5.2 持久化

todo 已由 `write_todos` 落入专用表（`TodoStorage`），保持不变。Dock 协议不新增存储，只新增"轮询回放路径"。

### 5.3 轮询回放

`agent_chat.query_chat` 在返回 `vis_final` 的同时，从专用表读取领域数据并序列化为 widget：

```python
todos = await gpts_memory.read_todos(conv_id)          # 从专用表回放
widgets = [todo_storage_to_widget(todos)]              # 领域模型 → dock widget
return (
    await gpts_memory.vis_final(conv_id),
    await gpts_memory.user_answer(conv_id),
    current_vis_render, is_final, state,
    {"version": 1, "widgets": widgets},                # 第 6 个返回值：dock
)
```

`controller.query_chat`、`api_v1.chat_query` 透传该字段，前端 `ChatQueryResponse` 加 `dock` 即完成轮询闭环。**重开会话时 todo 可恢复。**

---

## 6. 前端机制

### 6.1 状态（统一替代散装 state）

`chat-session.tsx` 用单个 map 承载所有 dock widget，替代 `todoList` + `subagentBoard` 两个散装 state：

```ts
const [dockWidgets, setDockWidgets] = useState<Record<string, DockWidget>>({});
```

SSE `onMessage` 与轮询 `onPoll` **共用同一个** `applyDockFrame(frame)` 合并函数（按 `id` + `kind` 合并）。两条链路只有一个入口，不再有 `includes('```d-todo-list')` 特判。

### 6.2 注册表（扩展核心）

```tsx
// registry.ts
export const dockWidgetRegistry: Record<string, React.ComponentType<DockWidgetProps>> = {
  todo_list: VisTodoList,
  subagent_board: VisSubagentBoard,
  // 未来新增：pipeline、ticker、form …… 只需在此注册一行
};
```

### 6.3 DockPanel（通用渲染器）

遍历 `dockWidgets`，按 `type` 查注册表渲染对应组件；未知 `type` 静默忽略（前向兼容），不崩、不拦截。

### 6.4 交互契约

- **数据下发**：`DockWidgetProps = { widget }`，组件只读数据自行渲染。
- **交互回写**：组件自行调后端 API（如"勾选完成"→ `POST /api/v1/chat/dock/todo/toggle`），后端更新 `TodoStorage` 后，经同一条 `push_dock_widget` 回推 `kind:"patch"` 帧；前端 `applyDockFrame` 合并，组件收到新 `payload` 重渲染。

框架不感知 todo 语义，也不为交互写任何特判。

---

## 7. 扩展一个 widget 的最小路径

| 步骤 | 后端 | 前端 |
|---|---|---|
| 1. 定义类型 | 唯一 `type` 字符串 | — |
| 2. 定义 payload | 领域模型 → widget 序列化 | 定义 TS 类型 |
| 3. 生产 | 调 `push_dock_widget` | — |
| 4. 注册 | — | `dockWidgetRegistry[type] = <Component>` |
| 5. 渲染 | — | 组件自实现 UI + 交互 |

**无需改任何 if/switch、无需改 DockPanel、无需拦消息。** `subagent_board` 迁到同一条协议上，即可顺带解决与 todo 相同的"轮询丢失"问题。

---

## 8. 边界与降级

- **前向兼容**：`version` 字段 + 未知 `type` 忽略 → 老前端升级到新后端不崩。
- **删除语义**：清理/新会话时后端发 `kind:"remove"` 帧，前端从 `dockWidgets` 删除，满足"todo 消失"。
- **性能**：`dock` 仅在 widget 变化时才发帧；合并逻辑与现有 `vis` 增量合并平行，带宽可忽略。
- **回放一致性**：SSE 实时帧与轮询回放帧语义一致，前端合并幂等。

---

## 9. 迁移清单（实施阶段参考）

**后端**
- [ ] `gpts_memory.push_dock_widget()` 统一入口
- [ ] `TodoWrite._push_todolist_vis` 改为构造 widget（移除围栏）
- [ ] `agent_chat.query_chat` 增加 `dock` 返回（含 todo 回放）
- [ ] `controller.query_chat` / `api_v1.chat_query` 透传 `dock`

**前端**
- [ ] `ChatQueryResponse` 增加 `dock` 字段
- [ ] `applyDockFrame` 增量合并函数（SSE + 轮询共用）
- [ ] `dockWidgetRegistry` 注册表
- [ ] `DockPanel` 通用渲染器（替换 `basic-chat-content` / `task-chat-content` 里的硬编码 todo 面板）
- [ ] `chat-session.tsx` 用 `dockWidgets` 取代 `todoList` / `subagentBoard`
- [ ] `VisTodoList` 迁移为 dock widget（含交互回写）