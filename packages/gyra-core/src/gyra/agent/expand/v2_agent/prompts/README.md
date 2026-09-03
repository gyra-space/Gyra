# V2Agent(PIXIU) Prompt 模板

本目录是 **PIXIU(V2 引擎)专用的独立静态模板目录**，与 BAIZE(V1) 的
`react_master_agent/prompts/` 完全分离，互不覆盖。

## 为什么独立

`PromptRegistry` 进程级单例的 `set_agent_prompts_dir` 会清空并重载全量模板，
V1/V2 同进程混跑时共用单例会互相污染模板。因此 `V2Agent._get_prompt_assembler`
持有 standalone Registry 实例（进程内缓存一份，`_V2_PROMPT_REGISTRY`），
加载本目录，与 BAIZE 的 agent 级目录彻底隔离。

## 目录结构

```
prompts/
├── identity/          # 身份层：PIXIU = V2 事件溯源引擎（run_loop 状态机）
├── workflow/          # 工作流层：v2.md（步数预算 / KV-cache 静态前缀 / 挂起态）
├── exceptions/        # 异常层：4.3 引擎保护与挂起态
├── delivery/          # 交付层：content/thinking 双通道纪律
└── README.md
```

模板选择名：identity=`default(_en)`、workflow=`v2(_en)`、exceptions/delivery=`main(_en)`
（`PromptAssemblyConfig(workflow_version="v2")`）。

## 与 BAIZE 模板的分工

| | BAIZE（react_master_agent/prompts/） | PIXIU（本目录） |
|---|---|---|
| 引擎叙事 | ReAct 循环 + 四大保护机制 | 事件溯源状态机 + 动作经济性 |
| 上下文约束 | 会话压缩 / 输出截断 / 熔断 | 步数预算 / 工具历史预算 / 挂起态恢复 |
| 缓存模型 | system prompt 可追加运行时内容 | **KV-cache 静态前缀**，动态内容走 `<system-reminder>` |

两目录共享的行为面（行为基调、技能优先、独占/并行工具规则、记忆运用、
双交付）保持语义一致，仅引擎机制描述不同。

## 静态前缀红线

本引擎的 system prompt 是会话级 KV-cache 静态前缀。**任何每轮变化的内容
（技能目录、DB 目录、长期记忆、任务通知）不得写入本目录的模板**——
它们由引擎以 user-role `<system-reminder>` 注入在历史投影之后、最新输入之前。
