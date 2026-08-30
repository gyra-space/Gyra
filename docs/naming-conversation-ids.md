# 会话标识命名规范（conversation / turn）

> 目标：让「会话」和「轮次」这两个维度在前后端有**唯一**的说法，
> 新代码不再需要靠 `rsplit("_")` 猜前端传的是哪种。

## 一、术语表（定稿）

| 维度 | 后端（Python） | 前端（TS） | DB 列 | 格式 | 语义 |
|---|---|---|---|---|---|
| **会话** | `conv_session_id` | `conversationId` | `conv_session_id`（列名即标准名） | 纯 uuid | 一场对话，跨轮次不变 |
| **轮次** | `conv_turn_id`（读别名） | `turnId` | `conv_id`（Deprecated） | `{会话 uuid}_{n}` | 一次提问，每提一次问 +1 |
| 空间 | `workspace_id` | `workspaceId` | — | int | 场景空间 |

示例：

```
会话  conv_session_id  b63fbb0e-38d8-11f1-8578-b5920cfbee2e
轮次  conv_turn_id     b63fbb0e-38d8-11f1-8578-b5920cfbee2e_2
```

层级：`workspace_id` ⊃ 会话 ⊃ 轮次。

> 为什么会话直接用 `conv_session_id`：它本来就是 DB 列名与 `AgentContext`
> 字段名，零迁移成本；而 `conv_id` 是历史混淆的根源（名字看不出是轮次），
> 用 `conv_turn_id` 别名过渡，未来 DB 迁移时把列翻个面即可。

## 二、废弃与别名

| 旧名 | 状态 | 替代 |
|---|---|---|
| `conv_id`（后端字段/DB 列） | Deprecated | `conv_turn_id` |
| `conversation_id` / `turn_id`（阶段 0 临时别名） | **已移除** | 上表的定稿名 |
| `conv_uid`（旧 API 参数） | 保留（API 契约） | 语义两义，入口处归一化 |
| `convIdBase()`（前端函数） | 已改名 | `toConversationId()` |

`AgentContext.conv_turn_id` 与 3 个核心 Entity（`GptsMessagesEntity` /
`GptsConversationsEntity` / `GptsFileMetadataEntity`）的 `conv_turn_id`
均为只读 `@property`，DDL 不变；SQLAlchemy 查询构造（`Entity.conv_id == x`）
仍需用列对象，别名仅用于读实例属性。

## 三、归一化工具（第 6 处重复已收敛到 1 + 1）

历史上「剥离 `_N` 后缀」的判断有 **6 处各写各的**（后端 5 + 前端 1），已收敛：

```python
# 后端
from gyra_serve.conversation.ids import to_conversation_id, is_turn_id, split_turn_id
to_conversation_id("..._2")   # -> "..."，幂等
```

```ts
// 前端（types/context-metrics.ts，原 convIdBase）
import { toConversationId } from '@/types/context-metrics';
toConversationId('..._2');    // -> '...'，幂等
```

## 四、前端状态（阶段 1，已完成）

- ✅ `convUid`/`ConvUid` → `conversationId`/`ConversationId`
  （20 个文件批量替换，API 参数 key `conv_uid` 未动）
- ✅ `convIdBase` → `toConversationId`（它是后端归一化函数的前端版）
- ✅ 存量 `convId` → `conversationId`（23 个文件）。逐文件追踪数据源后确认：
  除 `MemoryView.tsx` 外，所有 `convId` 的值都来自会话 id
  （URL `conv_uid` 参数、API 返回的 `conv_uid`/`conv_session_id` 字段、
  `chatId` 等），其中 `/v1/chat/query` 的 `conv_id` 参数后端注释即为
  「Agent会话ID」。对外契约保持不变：URL/事件 payload 的 `conv_id=` 字面量、
  API 响应字段均未改动。
- ⚠️ 唯一保留：`MemoryView.tsx` 的 `convId` —— 值取自 verbat 元数据的
  `conv_id` 字段，写入侧语义未能确认（可能轮次），改动前需先追 verbat 写入链路。
- ✅ `usage/page.tsx` 补了 `toConversationId()` 归一化：URL 上 `conv_id` 可能是
  轮次 id，归一化后入状态，与后端 usage API 的行为对齐，变量名才名副其实。

## 五、常见坑

**把轮次 id 当会话维度用**是最容易犯且后果最严重的错误。
例如按它创建工作目录，会导致同一会话每提一次问建一个新目录，
上一轮写的文件下一轮读不到，目录还会爆炸式增长。

判断方法：如果这个值会被持久化、跨轮次累积、或作为聚合 key，
就必须是会话 id（`conv_session_id` / `conversationId`）。
