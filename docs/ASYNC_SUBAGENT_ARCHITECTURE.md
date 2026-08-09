# 异步子 Agent 任务机制 & 推送渲染交互 — 架构文档

> 适用版本:2026-08 修复后。本文梳理「子 Agent 异步任务机制」「多媒体子 Agent 流程」「多层嵌套隔离与整体恢复」「推送渲染交互机制」四条主线,供排查与持续开发参考。所有结论标注 `file:line`,可直接定位。

---

## 0. 总览

```
┌─────────────────────────────────────────────────────────────────────┐
│  主会话 conv (main_conv_id)  — Canvas Agent / BAIZE (glm-5)         │
│    react_master_agent 循环                                          │
│      │ spawn_agent_task(mode=async) / SubAgent action               │
│      ▼                                                               │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ AsyncTaskManager (media_instance 单例)                │           │
│  │   _tasks{task_id: AsyncTaskState}                     │           │
│  │   _run_task -> spec.delegate() / subagent_manager     │           │
│  └──────────────┬───────────────────────────────────────┘           │
│                 │ Path A: delegate=to_async_delegate -> executor.run │
│                 │ Path B: _delegate_via_app -> _start_app(子会话)    │
│                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ 子 Agent 会话 (sub_conv_id)  — MultimediaAgent 等     │           │
│  │   enable_vis_message=False (vis 不流向主会话)         │           │
│  │   executor.run(wait=False) -> _run_async              │           │
│  │     │ register_external(轮询任务, conv_id=sub_conv)   │           │
│  │     ▼                                                 │           │
│  │  ┌────────────────────────────────────────┐           │           │
│  │  │ 轮询任务 (atask_xxx, external=True)     │           │           │
│  │  │   submit -> poll -> download -> deliver │           │           │
│  │  │   artifact {url,...} (图片/视频)        │           │           │
│  │  └────────────────────────────────────────┘           │           │
│  └──────────────┬───────────────────────────────────────┘           │
│                 │ 完成                                               │
│                 ▼                                                    │
│  AsyncTaskCoordinator._poll_completed (跳过 external)                │
│  SubagentCoordinator.on_subagent_done -> _trigger_main_resume        │
│      │ 合成「异步任务完成通知」(+ 产物 artifact)                      │
│      ▼                                                               │
│  aggregation_chat(is_retry_chat=True) -> 主会话 resume               │
└─────────────────────────────────────────────────────────────────────┘
```

**核心设计原则**
- **隔离**:轮询任务 `external=True` + `conv_id=sub_conv`,绝不触发主会话 resume;只有子 Agent 完成才回复主会话。
- **产物不随 vis 流**:子 Agent `enable_vis_message=False`,其内部推理步骤不进主会话 vis;产物(图片/视频)经 `main_conv_id` 聚合后通过通知/board 注入主会话。
- **统一台账**:所有异步任务落 `gpts_async_tasks` 表,跨进程/重启可恢复。

---

## 1. 子 Agent 异步任务机制

### 1.1 两条 spawn 路径(易混淆,务必区分)

| | Path A: delegate 直跑 | Path B: 子会话 react 循环 |
|---|---|---|
| 入口 | `spawn_agent_task` 工具,delegate factory 命中 | factory 返回 None 回退;或 `SubAgent` action(`agent_action.py:720`) |
| 执行体 | `MultimediaAgent.to_async_delegate._delegate` -> `executor.run`(`multimedia/agent.py:434`) | `react_master_agent._delegate_via_app` -> `GptAppResource._start_app`(`react_master_agent.py:543`) |
| 子会话 | 无(在父上下文直接跑) | 有,新建 `sub_conv_id`(`app.py:120`) |
| react 循环 | 无,单次媒体生成 | 有,可多步推理(如生成多张图) |
| 完成回调 | `AsyncTaskCoordinator` resume | `SubagentCoordinator.on_subagent_done` (action) 或 `AsyncTaskCoordinator` (spawn 回退) |
| message_id | — | `_start_app` 传 `message_id=conv_uid`(`app.py:151`,曾缺失导致 task_id=None) |

**关键**:运行时观测到的视频/图像子 Agent 实际走 **Path B**(日志有 `[start_app]` + `MULTIMEDIA StepStart/StepEnd`)。delegate factory 静默回退(`tool_context_factory.py:150`)是回退到 Path B 的根因,已改为记 warning。

### 1.2 AsyncTaskManager(任务生命周期)

`packages/gyra-core/src/gyra/agent/util/async_task_manager.py`

- **任务规格** `AsyncTaskSpec`(:66):`task_id`(自动 `atask_xxx`,:87)、`conv_id`、`kind`、`delegate`/`resume`+`deliver`、`context`。
- **状态** `AsyncTaskState`(:152):`status`(PENDING/RUNNING/COMPLETED/FAILED/TIMEOUT/CANCELLED)、`result`、`error`、`artifacts`、`consumed`。
- **spawn**(:444):`asyncio.create_task(self._run_task(state))`。
- **_run_task**(:709):subagent 分支 `await spec.delegate()`(:741)或回退 `subagent_manager.delegate(sync=True)`(:746);media 分支 `resume`+`deliver`。**success 判定**:`getattr(result,"success",False)`(:762)决定 COMPLETED/FAILED。
- **register_external**(:464):登记外部驱动任务(轮询任务/子 Agent 镜像),标 `external=True`(:478),只镜像状态不执行,加入 `_tasks`(:482)。
- **complete_external**(:495):回写终态 result/error。
- **get_completed_results**(:842):`consume=True` 标记已消费;按 `conv_id` 过滤。
- **持久化**:`_persist`(:803) -> `to_record`(:219) -> `AsyncTaskDao.upsert` 落 `gpts_async_tasks` 表。

### 1.3 任务状态语义(修复后)

- **目标失败标 FAILED**:`_delegate_via_app`/`delegate` 原本无条件 `success=True`(失败也标 completed)。修复:`_result_from_answer`(`react_master_agent.py`)检测"多媒体生成失败"前缀 -> `success=False` -> `_run_task` 标 FAILED。
- `to_record` 的 `artifact` 字段:仅当 `state.result` 是 ToolResult(非字符串)时从 `result.artifacts` 提取。轮询任务满足(media 路径 deliver 返回 ToolResult);subagent 镜像任务 result 是文本,artifact 为 None(产物靠聚合,见 §3)。

---

## 2. 多媒体子 Agent 异步任务流程

`packages/gyra-core/src/gyra/agent/multimedia/`

### 2.1 执行链路

```
MultimediaAgent.thinking/generate_reply (react 循环)
  -> MultimediaExecutor.run (executor.py:90)
     -> _resolve_model (自管模型:显式 › default › 系统默认 › 首个可用, :319)
     -> _resolve_media_model -> (protocol, api_key, base_url)
     -> MediaGenProviderRegistry.create_provider_by_protocol
     -> wait=False ? _run_async : 同步 generate + _deliver
        │
        ├─ _run_async (:608): AsyncTaskSpec(resume=_resume, deliver=_deliver) -> mgr.spawn
        │    context 含 provider/provider_task_id/prompt/main_conv_id
        └─ _register_media_mirror (:440): register_external(轮询任务镜像, conv_id=sub_conv)
             _complete_media_mirror 回写终态
```

### 2.2 模型解析(易踩坑)

- 视频模型来自 `ext_config.multimedia_agent.video_models` / `default_video_model`(`executor.py:_resolve_model:319`),**与 `llm_config.llm_strategy_value` 是两套独立配置**。
- `llm_strategy_value` 是 Agent 的**推理 LLM**(`base_agent` 用),曾被误配成视频模型(如 `happyhorse-1.1-t2v`),但不影响视频生成模型。
- 报错里的 `happyhorse` 是 **provider 实现名**(`happyhorse_video_provider.py`,dashscope_multimedia 协议),不是模型名。实际提交模型见日志 `[HappyHorseVideoProvider] Submitting ... model=xxx`。

### 2.3 产物 artifact(图片可见性的核心)

- 轮询任务 `deliver` 后,`state.result` = ToolResult(含 `artifacts`),`to_record` 提取 `artifact {name,type,url,mime_type}` 落 DB。
- **但轮询任务 `conv_id=sub_conv`**,主会话按 conv_id 查不到 -> 页面看不到图片。
- **修复后的聚合链路**(见 §3.3):`main_conv_id` 透传 -> `collect_artifacts_for_main_conv` -> 通知/board 注入。

---

## 3. 多层嵌套与隔离(主 -> 子 Agent -> 轮询任务)

### 3.1 三层结构与 conv_id 归属

| 层 | 任务 | conv_id | external | 触发主 resume? |
|---|---|---|---|---|
| L1 主会话 | Canvas Agent | main | — | — |
| L2 子 Agent | spawn atask / SubAgent handle | main(镜像) | True | 子 Agent 终态时(`on_subagent_done`) |
| L3 轮询任务 | media mirror atask | **sub_conv** | True | **否**(被 AsyncTaskCoordinator 跳过) |

### 3.2 隔离机制(恢复不泄漏)

- **轮询任务**:`register_external` 标 `external=True`,`conv_id=sub_conv`。`AsyncTaskCoordinator._poll_completed`(**`async_task_coordinator.py:127`**)显式跳过 external 任务 -> **轮询任务完成不触发主 resume**。
- **子 Agent 镜像**:`SubagentCoordinator._mirror_register`(`subagent_coordinator.py:170`)用 `task_id=sub_conv_id`、`conv_id=main_conv_id` 注册为 external。`on_subagent_done`(:232)-> 仅当 `all(h.is_terminal())`(:249)才 `_trigger_main_resume`。
- **去重**:`AsyncTaskCoordinator` 与 `react_master_agent._collect_background_notifications` 共用 `consumed` 标记,互斥不重复注入。
- **`main_conv_id` 透传**(修复):`_start_app` 设 `child_extra["main_conv_id"]`(`app.py:115`);`MultimediaAgent` 从 `agent_context.extra["main_conv_id"]` 注入 `executor.main_conv_id`(`agent.py:213`);轮询任务 context 记录 `main_conv_id`。使主会话能查到子 Agent 产物,且**不破坏隔离**(轮询任务仍 external、仍 sub_conv)。

### 3.3 产物聚合(两条路径都覆盖)

**spawn 路径(Path B 回退)**:
```
AsyncTaskCoordinator._build_notification (async_task_coordinator.py:384)
  -> main_conv_ids = {st.spec.conv_id}  # 主会话 id
  -> AsyncTaskManager.collect_artifacts_for_main_conv(main_conv_id)
       扫 _tasks, context.main_conv_id 匹配, to_record().artifact 去重
  -> 通知文本追加 "### 生成产物" + markdown 图片链接 ![name](url)
```

**SubAgent action 路径**:
```
SubagentCoordinator.on_subagent_done (subagent_coordinator.py:232)
  -> _collect_child_artifacts(sub_conv_id)
       AsyncTaskDao.list(conv_id=sub_conv) 收集 artifact
  -> h.artifacts = [...]
  -> list_subagent_items / terminal_items 含 artifacts
  -> build_subagent_board_widget -> push_dock_widget 到主会话
```

### 3.4 task_id 透传(修复)

- `_start_app` 构造 `AgentMessage` 必传 `message_id=conv_uid`(`app.py:151`、`capabilities/app/capability.py:261`)。
- 否则 `task_id_by_received_message`(`base_agent.py:3070`)返回 None,`push_context_event` 在 `if not task_id: return`(:3101)丢弃子 Agent 所有上下文事件(StepStart/StepEnd 等),执行轨迹无法入库/恢复。

---

## 4. 整体恢复机制

### 4.1 正常完成 -> 主 resume

```
子 Agent / 轮询任务完成
  │
  ├─ AsyncTaskCoordinator._watch_loop (1s 轮询, async_task_coordinator.py:65)
  │    _poll_completed (:110) 发现 completed 未消费 + 主会话 WAITING
  │    -> _resume_conv (:285)
  │       _build_notification (含产物 artifact)
  │       _safe_set_waiting -> aggregation_chat(is_retry_chat=True)
  │
  └─ SubagentCoordinator.on_subagent_done (action 路径)
       全部子 Agent 终态 -> _trigger_main_resume (:464)
         合成"子 agent 全部完成"通知 -> aggregation_chat
```

`aggregation_chat`(`agent_chat.py:1437`)检测 `state==WAITING` -> `is_retry_chat=True` -> `_inner_chat` `WAITING->RUNNING`(:3625)。**通知文本作为新 user_query 重新激活主 Agent**。

### 4.2 重启恢复(RecoveryDaemon)

`packages/gyra-serve/src/gyra_serve/agent/recovery_daemon.py`

- 启动时扫所有 RUNNING 会话,按心跳判断真死:`is_stale` -> 标 RETRYING + `acquire_lease` 抢占。
- **有 pending_subagents** -> `SubagentCoordinator.recover_main`(`subagent_coordinator.py:631`):
  - RUNNING 子 Agent 检查 lease:过期 -> 标 FAILED + 重建 transcript;未过期(在另一进程跑)-> 注册监听等完成。
  - 全部终态 -> `_trigger_main_resume`;否则等待。**不会提前 resume 主**。
- **无 pending_subagents** -> `_trigger_main_retry`(直接 `aggregation_chat(is_retry_chat=True)`)。

### 4.3 resume 循环防护(修复)

`react_master_agent` 的 BlankAction 兜底(`react_master_agent.py:3010`):async-resume 轮次 LLM 返回纯文本(无工具调用)时,取消 terminate 强制续推(防止主对话"看不到继续输出")。**修复**:仅当内容 <50 字符(占位文本)才强制;实质最终答案(长文本)直接 terminate,避免重复输出最终答案(曾 1668/1669/1670 重复 3 次)。

---

## 5. 推送渲染交互机制

### 5.1 vis 流式推送链路

```
Agent 循环 (react_master_agent)
  -> gpts_memory._push_stream_message (gpts_memory.py:1485)
     -> vis_messages (converter 增量转换) -> cache.channel.put_nowait(vis_view)
        vis_view = JSON{planning_window, running_window, meta_window}
  │
  ▼
agent_chat 流式循环 (agent_chat.py:1600+)
  chat_iter 消费 cache.channel
  -> _serialize_stream_chunk -> file_handle.write(content+"\n")  # 写 chunk 文件
  -> yield (task, resp, agent_conv_id)                           # SSE
  │
  ▼
v2_chat_endpoint (v2_chat_endpoint.py:41 event_stream)
  -> yield f"data:{json}\n\n"  -> 前端 EventSource
  │
  ▼
前端渲染 (vis_manus)
  planning_window: d-planning-space / d-system-events / d-agent-plan / d-subagent-board
  running_window: manus-right-panel
  dock: DockPanel(subagent_board / todo)
```

**chunk 文件**:`pilot/data/chat_chunk_file/_chat_file_{conv_id}_{n}.jsonl`(`agent_chat.py:1566`),每行一条 vis 记录。流式期间持续追加。

### 5.2 vis 组件(planning_window 内的 fenced block)

| 组件 | 内容 | 构建 |
|---|---|---|
| `d-planning-space` | 规划/思考空间 | `gyra_vis_window3_converter` |
| `d-system-events` | `is_running`/`current_action`/`recent_events` | `_system_events_vis_build`(:2354) |
| `d-agent-plan` | Agent 计划/异步任务通知 | converter |
| `d-subagent-board` | 子任务看板(状态/产物) | `build_subagent_board_widget`(`subagent_coordinator.py:667`) |
| `manus-right-panel` | 右面板执行步骤/输出 | `_build_right_panel_data`(`gyra_vis_manus_converter.py:817`) |

### 5.3 终态收尾(修复)

- 流式期间 `d-system-events` 的 `is_running=True`(依赖 `agent_complete` 事件,但该事件实际从不产生)。
- `_final_system_events_vis`(`gyra_vis_window3_converter.py:2331`)在 `final_view` 中强制 `is_running=False` 覆盖。
- **但 `vis_final` 只 return 终态视图给 DB/query_chat,不进 channel** -> chunk 文件最后一条卡 `is_running=True`,页面刷新后右面板卡"思考中"。
- **修复**:`gpts_memory.push_final_view`(`gpts_memory.py:1063`)在 `save_conversation`(`agent_chat.py:963`)时把终态视图推到 channel,确保 chunk 流以 `is_running=False` 收尾。

### 5.4 chunk 膨胀治理(修复)

- 根因:`manus-right-panel` 用 `UpdateType.ALL` 全量重发;`active_step.detail`(整段通知/脚本,数百 KB)每条增量都带。曾导致单对话 chunk 文件 159MB。
- **修复**:`_build_steps_from_messages_stateless`(`gyra_vis_manus_converter.py:1044`)lazy 模式(流式 `is_working=True`)截断 `active_step.detail`(>200 字符)和 `outputs.content`(>2000 字符);`steps_map` 已在 lazy 模式省略 outputs。前端按需经 `/vis/step_detail` 拉取完整内容。

### 5.5 Dock Widget(子任务看板)

```
SubagentCoordinator._emit_board_event (subagent_coordinator.py:352)
  -> list_subagent_items (含 artifacts)
  -> build_subagent_board_widget (type="subagent_board", kind="replace")
  -> gpts_memory.push_dock_widget (conv_id=main)
  -> 持久化 extra["subagent_board"] (persist_board, :298)
  -> 前端 DockPanel 渲染 (VisSubagentBoard)
```

刷新恢复:`query_chat` -> `_build_dock_frame`(`agent_chat.py:4023`)从 `extra["subagent_board"]` 回放 dock 帧。

### 5.6 刷新恢复(query_chat)

`agent_chat.py:3952 query_chat` 返回 6 元组:
```
(vis_final, user_answer, current_vis_render, is_final, state, dock)
```
- `vis_final`:`gpts_memory.vis_final` -> `final_view`(含 `is_running=False` + 交付文件)。
- `dock`:`_build_dock_frame` 回放 subagent_board/todo。
- 前端据此 + chunk 文件重建对话状态。

### 5.7 lazy 按需加载

- 流式/final_view 的 `manus-right-panel` 在 lazy 模式下 `steps_map` 只含元信息(无 outputs),`lazy_loading=True`。
- 前端点击步骤 -> `/vis/step_detail?conv_id=&step_id=` -> `query_step_detail` -> `vis_convert.get_step_detail` 精确匹配。
- **陷阱**:step_id(`step_{msg_id前8}_{计数}`)≠ action_id(`tool_call_id`),接口需优先按 step_id 解析(见 [[vis-manus-linkage-architecture]])。

---

## 6. 关键文件索引

| 关注点 | 文件:位置 |
|---|---|
| spawn_agent_task 工具 | `gyra-core/.../tools/builtin/async_task/async_task_tools.py:124` |
| delegate factory | `gyra-core/.../core/v2/tool_context_factory.py:107` |
| AsyncTaskManager | `gyra-core/.../util/async_task_manager.py` |
| _run_task / success 判定 | `async_task_manager.py:709,762` |
| register_external / external 跳过 | `async_task_manager.py:464`;`async_task_coordinator.py:127` |
| collect_artifacts_for_main_conv | `async_task_manager.py:864` |
| MultimediaAgent delegate | `gyra-core/.../multimedia/agent.py:375` |
| MultimediaExecutor _run_async / mirror | `gyra-core/.../multimedia/executor.py:608,440` |
| _start_app / message_id / main_conv_id | `gyra-serve/.../resource/app.py:115,151` |
| SubagentCoordinator | `gyra-serve/.../agent/subagent_coordinator.py` |
| on_subagent_done / _trigger_main_resume | `subagent_coordinator.py:232,464` |
| AsyncTaskCoordinator resume | `gyra-serve/.../agent/async_task_coordinator.py:285,384` |
| RecoveryDaemon | `gyra-serve/.../agent/recovery_daemon.py` |
| react_master BlankAction 兜底 | `gyra-core/.../react_master_agent.py:3010` |
| _result_from_answer(失败判定) | `react_master_agent.py:457` |
| vis_final / push_final_view | `gyra-core/.../memory/gpts/gpts_memory.py:1023,1063` |
| chunk 文件写入 / SSE | `gyra-serve/.../agents/chat/agent_chat.py:1566,1600`;`v2_chat_endpoint.py:41` |
| query_chat / _build_dock_frame | `agent_chat.py:3952,4023` |
| manus-right-panel / lazy 截断 | `gyra-ext/.../vis/gyra/gyra_vis_manus_converter.py:817,1044,1114` |
| 系统事件 is_running | `gyra-ext/.../vis/gyra/gyra_vis_window3_converter.py:2354` |
| 前端 VisSubagentBoard | `web/src/.../VisComponents/VisSubagentBoard/index.tsx` |
| 前端 DockPanel | `web/src/components/chat/dock/` |

---

## 7. 排查指南

### 7.1 常见症状 -> 定位

| 症状 | 看哪 | 可能原因 |
|---|---|---|
| 页面只看到"图片生成成功"文本,看不到图 | `gpts_async_tasks.artifact`(轮询任务,conv=sub_conv) | main_conv_id 未透传/聚合;查 `executor.main_conv_id`、`collect_artifacts_for_main_conv` 日志 |
| 失败任务显示"完成" | `gpts_async_tasks.status` | `_result_from_answer` 未检测到失败前缀;查子 Agent 回复是否以"多媒体生成失败"开头 |
| 子 Agent 执行轨迹丢失 | 日志 `push_context_event task_id为空` | `_start_app` 未传 `message_id` |
| 页面刷新后卡"思考中" | chunk 文件最后一条 `is_running` | `push_final_view` 未推到 channel;查 `save_conversation` 是否调用 |
| final answer 重复输出多次 | 日志 `async-resume round returned BlankAction; forcing continuation` | BlankAction 兜底对长文本也强制续推 |
| chunk 文件异常大 | `running_window` 单条大小 | `manus-right-panel` 未走 lazy 截断 |
| 轮询任务触发主 resume(泄漏) | 日志 `[async-task-coordinator] triggering main resume` 时机 | 轮询任务未标 external 或 conv_id 误挂主 conv |
| 视频报错"happyhorse request failed" | `[HappyHorseVideoProvider] Submitting ... model=xxx` | happyhorse 是 provider 名;查实际 model + API key 权限(403) |

### 7.2 关键日志关键字

- `[AsyncTaskManager] Spawned/Running/Registered external/Task ... finished` — 任务生命周期
- `[async-task-coordinator] triggering main resume` — 主会话恢复触发
- `[subagent-coordinator] subagent ... done/failed for main` — 子 Agent 终态
- `[subagent_delegate_factory] build delegate ... failed, fallback` — delegate 回退到 Path B(可观测)
- `[multimedia-executor] registered sync media record / submit failed` — 媒体任务
- `[HappyHorseVideoProvider] Submitting ... model=xxx` — 实际提交的模型
- `push_context_event task_id为空` — task_id 透传问题(修复后不应出现)
- `[push_final_view]` — 终态视图推送
- `[ReActMasterAgent] async-resume round returned BlankAction; forcing continuation` — resume 循环

### 7.3 DB 查询速查

```sql
-- 某会话的所有异步任务(含产物)
SELECT task_id, conv_id, kind, model, status, error,
       substr(result_preview,1,80), artifact
FROM gpts_async_tasks WHERE conv_id LIKE 'conv_id%' ORDER BY gmt_create;

-- 子会话(sub_conv)的轮询任务产物(主会话查不到时下钻)
SELECT task_id, artifact FROM gpts_async_tasks WHERE conv_id = 'sub_conv_id';

-- 会话 pending_subagents / subagent_board
SELECT json_extract(extra,'$.pending_subagents'), json_extract(extra,'$.subagent_board')
FROM gpts_conversations WHERE conv_id = 'conv_id';
```

### 7.4 修复记录(2026-08-09)

1. artifact 聚合(main_conv_id 透传 + collect + 通知/board 注入)
2. subagent_board 渲染图片产物(前端)
3. `_start_app` 传 message_id(消除 task_id=None)
4. delegate factory 静默回退改 warning + 隔离机制验证
5. `_result_from_answer` 失败标 failed
6. BlankAction 兜底仅对占位文本强制续推
7. `push_final_view` 推终态视图到 channel(修 vis 卡 running)
8. manus-right-panel lazy 截断 detail/outputs(修 chunk 膨胀)

---

## 8. 后续改进方向(建议)

- **Path A/B 统一**:delegate factory 命中率低导致频繁回退 Path B(重路径)。可让多媒体子 Agent 在「单次生成」场景显式走 Path A(轻量、status 直接来自 ToolResult),「多步推理」才走 Path B。
- **artifact 持久化健壮性**:`collect_artifacts_for_main_conv` 当前只扫内存 `_tasks`,重启后依赖 DB。可加 `AsyncTaskDao` 按 `detail.main_conv_id` 的扫描兜底(需 detail JSON 解析或加列)。
- **status 语义统一**:subagent react 循环的失败判定靠"多媒体生成失败"前缀(脆弱)。可让 MultimediaAgent 在失败时于 `AgentMessage` 设结构化失败标记,delegate 读取而非字符串匹配。
- **chunk 文件清理**:长期运行下 chunk 文件累积,建议加轮转/清理策略。
- **端到端可观测**:为三层嵌套加一条 trace(主 conv -> sub_conv -> 轮询 task_id),便于排查"产物去哪了"。
