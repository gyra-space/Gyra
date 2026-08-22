# V2 事件溯源表 schema 治理指南

> 适用：V2 Runtime 事件溯源 / 状态机引擎（packages/gyra-core/.../v2/）。
> 文档版本：v1（2026-08-18）
> 维护：V2 Engine 团队

---

## 1. 背景

V2 引擎的事件溯源（event sourcing）持久化跟随**系统业务数据库**动态切换：
- SQLite（单机开发）
- MySQL / PostgreSQL / OceanBase（生产分布式）

V2 事件溯源在系统库中创建 5 张表，统一以 **`v2_` 前缀**标识，区别于业务表。
DBA 治理、V2 表迁移、备份/清理等场景必须能识别并仅作用于 V2 命名空间。

## 2. 表清单

| 表名 | 用途 | 索引 |
|---|---|---|
| `v2_step_event` | append-only StepEvent 日志（事实源） | `idx_v2_step_event_conv_seq(conv_id, seq)` |
| `v2_step_state` | Step 状态快照（崩溃恢复） | `idx_v2_step_state_conv(conv_id)` |
| `v2_agent_lease` | 跨实例租约（多 agent 防抢） | `idx_v2_lease_expires(lease_expires_at)` |
| `v2_interaction_checkpoint` | 用户交互检查点（ask_user / permission） | `idx_v2_checkpoint_conv(conv_id)` |
| `v2_agent_transcript` | 子 Agent 持久 ledger | `idx_v2_transcript_parent(parent_conv_id)`、`idx_v2_transcript_task(task_id)` |

> 表定义代码：[/Users/yanghongjun/code/Gyra/packages/gyra-core/src/gyra/agent/core/v2/unified_state_store.py](file:///Users/yanghongjun/code/Gyra/packages/gyra-core/src/gyra/agent/core/v2/unified_state_store.py)
> 兜底 SQLite schema：[/Users/yanghongjun/code/Gyra/packages/gyra-core/src/gyra/agent/core/v2/state_store.py](file:///Users/yanghongjun/code/Gyra/packages/gyra-core/src/gyra/agent/core/v2/state_store.py#L95-L151)

## 3. 推荐治理方案（按优先级）

### 方案 A（强烈推荐）—— 独立 schema（PostgreSQL/MySQL）

生产库在 SQLAlchemy URL 中指定独立 schema：

```ini
# config.toml
[service.web.database]
url = "postgresql://user:pwd@host/gyra?options=-csearch_path%3Dgyra_main%2Cgyra_v2"
```

V2 表由 `SqlAlchemyStateStore` 用 `Base = declarative_base()` 独立 base，
`metadata.create_all(engine)` 幂等建表到 `gyra_v2` schema（业务表在 `gyra_main`）。

**好处**：
- 物理隔离，DBA 可独立 backup/restore/cleanup；
- 跨 schema 授权灵活（V2 schema 可独立 read-only 备份账号）；
- 业务表与 V2 表可独立优化（V2 step_event 高写入，buffer pool 可独立配置）。

### 方案 B —— 独立 DB 用户（更严格的隔离）

V2 schema 单独授权给 `gyra_v2_writer` 账号，业务 app 用 `gyra_app_writer`：
- 业务账号无 DDL 权限（不可 `CREATE` / `DROP` V2 表）；
- V2 账号可独立 rotate key；
- 审计/合规上明确 V2 写入来源。

### 方案 C —— 同一 schema + 前缀识别（最低成本）

如果短期无法独立 schema，至少保证：
1. **统一前缀 `v2_`**：所有 V2 表强制 `v2_` 前缀，索引同样（`idx_v2_*`）；
2. **DBA 治理脚本过滤**：`pg_dump --table='v2_*'` / `mysqldump gyra v2_step_event v2_step_state ...`；
3. **监控面板分组**：V2 表的写入 QPS / 容量独立监控，避免业务表告警被淹没。

## 4. 迁移与升级

### 4.1 新增 V2 表

1. 在 `unified_state_store._SQLALCHEMY_SCHEMA` 字典中加新表（`metadata.create_all` 幂等）；
2. 更新本清单第 2 节；
3. 通知 DBA review schema 设计（主键、索引、JSON 字段、文本长度）。

### 4.2 列变更（add / modify）

**append-only 表**（`v2_step_event`）：**禁止 DROP COLUMN / RENAME COLUMN**——
事件日志投影逻辑会按列名读取，破坏列结构会回放历史事件失败。

允许：
- ADD COLUMN（nullable 或带默认值，对历史事件透明）；
- ADD INDEX（DBA 独立执行）。

禁止：
- 改 JSON 字段语义（如 `metadata` 新增必填子字段）——历史事件可能没有；
- 改 PK 列类型（事件 ID 是 sha256/UUID 派生，类型变更会导致 lookup 失败）。

### 4.3 表废弃

**永远不要 DROP**——事件溯源的本质是 log 不可变；废弃表用 RENAME TO `v2_xxx_archived_<date>`，DBA 单独 backup 后再清。

## 5. 备份与清理

### 5.1 备份

```bash
# PostgreSQL
pg_dump -h host -U backup_user -t 'v2_*' -Fc gyra > v2_$(date +%Y%m%d).dump

# MySQL
mysqldump -u backup_user -p --tables v2_step_event v2_step_state \
  v2_agent_lease v2_interaction_checkpoint v2_agent_transcript gyra > v2.sql
```

### 5.2 TTL 清理（按业务）

`v2_step_event` 增长最快（每 LLM token 一条）。建议：
- 生产环境保留 30 天（事件 + 派生消息）；
- `v2_agent_lease`：永久保留（量级极小）；
- `v2_interaction_checkpoint`：24h TTL（交互等待过久自动 expire）；
- `v2_agent_transcript`：随父 conv 生命周期，父 conv 删除时 cascade 清理。

清理脚本（PostgreSQL 示例）：

```sql
-- 每晚 cron
DELETE FROM v2_step_event WHERE timestamp < now() - interval '30 days';
DELETE FROM v2_interaction_checkpoint WHERE created_at < now() - interval '24 hours';
VACUUM ANALYZE v2_step_event;
```

## 6. 监控告警

关键指标（V2 表独立监控，避免与业务表混在一起）：

| 指标 | 阈值 | 行动 |
|---|---|---|
| `v2_step_event` 写 QPS | > 5000/s | 检查是否有 agent 死循环 / 滥用 |
| `v2_step_event` 表大小 | > 100GB | 触发 TTL 清理 |
| `v2_agent_lease` 活跃数 | > 1000 | 检查 agent 是否堆积 / 死锁 |
| `v2_agent_lease` 过期未释放率 | > 5% | 检查 `release_lease` 调用完整性 |
| `v2_interaction_checkpoint` 陈旧率 | > 10% | 检查 ask_user 收尾路径 |

## 7. 数据安全

- **事件日志 append-only**：禁止 UPDATE / DELETE `v2_step_event`（除 TTL 清理）；
- **租约**：`acquire_lease` 用 SQL `INSERT OR REPLACE`（SQLite）/ `merge`（MySQL PG）幂等；
- **schema 变更窗口**：建议低峰期执行（事件写入峰值时 DDL 可能阻塞）；
- **审计**：所有 V2 表的写操作应被 APM 采集（与业务表同账号即可）。

## 8. 故障排查

| 症状 | 排查 |
|---|---|
| 事件丢失 | 检查 `v2_step_event` 的 `event_id` 唯一性 / `seq` 连续性 |
| Lease 抢不到 | `SELECT * FROM v2_agent_lease WHERE lease_expires_at > now()` 看持锁 agent |
| 投影结果异常 | 查 `v2_step_event` 是否存在 `event_type` 不在 EventRegistry 注册的事件 |
| Compaction 未触发 | 查 `v2_step_event` 中 `compaction/summary` 与 `compaction/end` 配对 |

## 9. 命名约定

- 表名：`v2_<domain>_<purpose>`（snake_case）
- 列名：`snake_case`，禁止驼峰
- 索引：`idx_v2_<table>_<cols>` 或 `uk_v2_<table>_<unique_cols>`
- JSON 字段：默认 `Text` 存（兼容方言），内部 `json.loads` 解析
- 时间戳：REAL（SQLite）/ DOUBLE（PRECISION MySQL/PG），epoch 秒

## 10. 联系

V2 引擎问题、schema 变更申请请联系 V2 Engine 团队。
