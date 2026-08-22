"""default_thinking_fn 工厂。

流程：
1. Memory 注入（consume_prefetch 或 sync retrieve_relevant_memories；另加载
   首轮静态记忆索引并入 system 前缀，后续由 memory_search 工具读增量）
2. ContextEngine.build_messages
3. 拼最终 LLM messages（前缀 = system + skill/db catalog + history 投影；
   动态参考 = 动态 memory + 运行提醒插在 history 之后；最后一条 user
   = 用户最新输入）
4. LLM stream（带 retrying_thinking MAX_ATTEMPTS）
5. StreamingContextScrubber 清洗 token
6. yield TokenChunk / ToolCallChunk / UsageChunk

前缀缓存（KV-cache）设计：
- 前缀保持稳定：system（身份 + 环境 + 静态记忆索引）+ catalog + 历史投影；
- 每轮变化块（动态 memory、运行提醒）统一插在 history 之后、用户最新输入之前，
  ——让"最后一条 user"始终是当前输入，且不扰动前缀；
- TODO 列表不进 system（由 todowrite 工具自见），避免污染静态前缀。
"""
import logging
from typing import Any, AsyncGenerator, Callable, Optional

from gyra.agent.core.v2.thinking_chunk import (
    ThinkingChunk, TokenChunk, ToolCallChunk, UsageChunk,
)
from gyra.agent.core.v2.tool_call_types import V2ToolCall
from gyra.agent.core.v2.retrying_thinking import retrying_thinking

logger = logging.getLogger(__name__)


STATIC_ROOMS = ["profile", "preference"]


def make_default_thinking_fn(
    *,
    llm_stream_fn: Callable,  # async generator: (messages, model) -> chunks of {"token", "usage", "tool_calls"}
    model_alias: str,
    memory_bundle: Optional[Any] = None,
    max_attempts: int = 3,
    model_fallback: Optional[Callable[[str], str]] = None,
    system_prompt: Optional[str] = None,
    context_provider: Optional[Callable] = None,  # async/sync: () -> List[dict]（事件日志全量投影，V2 单源）
    catalog_consumer: Optional[Any] = None,  # SkillCatalogConsumer 实例（对齐 DSH tool-skill）
    db_catalog_consumer: Optional[Any] = None,  # DbCatalogConsumer 实例（对齐 DSH tool-db）
    context_manager: Optional[Any] = None,  # ContextManager 实例（pre_step spill 超大工具结果）
    operational_reminders_provider: Optional[Callable] = None,  # async/sync: () -> Optional[str]
) -> Callable:
    """构造 ThinkingFn（V2 单源：LLM 上下文完全来自事件日志投影）。

    llm_stream_fn: async generator factory，输入 (messages, model)，yield dict chunk：
        {"token": str, "usage": Optional[dict], "tool_calls": Optional[List[dict]]}

    context_provider: 事件日志全量投影器（async/sync → List[dict]），输出
        user/assistant/tool 消息与 compaction 摘要——V2 的 LLM 上下文**唯一**事实源。
        替代旧版从 gpts_messages 构建的 ContextEngine 输入，保证用户/助手/工具
        消息全部来自 V2 事件日志（不再依赖 V1 会话表）。

    memory_bundle / catalog_consumer / db_catalog_consumer / context_manager /
    operational_reminders_provider：系统注入（memory 上下文、skill/db 目录
    reminder、spill、异步任务通知等），不受单源化影响。

    TODO 列表**不**在此注入（对齐 DSH tool-todo：由 todowrite 工具参数自见）。
    """

    async def thinking_fn(input_: dict) -> AsyncGenerator[ThinkingChunk, None]:
        user_prompt = input_["prompt"]
        conv_id = input_["conv_id"]
        session_id = input_["session_id"]
        sys_prompt = input_.get("system_prompt", system_prompt)

        # 运行时操作上下文（异步任务完成通知 / 用户补充输入）。对齐 V1
        # ``_operational_parts``，但**不再**拼进 system prompt 尾部——那会扰动
        # KV-cache 静态前缀。改为收集后 append 到消息列表**末尾**（尾部动态块，
        # 每轮新增，前缀保持稳定）。TODO 列表**不**在此注入（由 todowrite 自见）。
        operational_tail: List[str] = []
        if operational_reminders_provider is not None:
            try:
                _op = await _maybe_await(operational_reminders_provider())
                if _op:
                    operational_tail.append(str(_op))
            except Exception:
                logger.exception(
                    "[default_thinking] operational reminders provider failed, skipping"
                )

        # 首轮静态记忆索引（KV-cache 稳定前缀）：从 read pipeline 取冻结块
        # （STATIC_ROOMS profile/preference + L1 memory 索引切片），并入 system。
        # 冻结一次后整场会话不变；具体回忆内容由 LLM 经 memory_search 工具在
        # 后续轮次按需读取增量，不再每轮全量检索塞进消息体。
        static_block = await _load_static_memory_index(memory_bundle)

        # 1. Memory 注入（dynamic）
        memory_context = ""
        if memory_bundle is not None:
            pipeline = getattr(memory_bundle, "pipeline", None)
            if pipeline is not None:
                # consumer key：同 conv 多 agent 各自消费一次（prefetch
                # cache 按消费方 key 去重），miss 时同步 fallback。
                # timeout=0.5：入口预取与 tier0 轮末预热通常已就绪或即将就绪，
                # 最多等 0.5s 换掉一次完整同步检索；超时仍走同步 fallback。
                consumer = input_.get("agent_id") or "default_thinking"
                result = await pipeline.consume_prefetch(timeout=0.5, consumer=consumer)
                if result is None:
                    result = await memory_bundle.manager.retrieve_relevant_memories(
                        query=user_prompt, exclude_rooms=STATIC_ROOMS,
                    )
                memory_context = _build_memory_context_block(result)

        # 2. 事件日志全量投影（V2 单源：user/assistant/tool 消息 + compaction 摘要）
        projected: List[dict] = []
        if context_provider is not None:
            try:
                # conv_id/agent_id 从 input_ 取：主 agent 与子 agent 各自投影自己的
                # 事件日志（子 agent 复用同一 thinking_fn，input_ 字段驱动会话绑定）
                projected = await _maybe_await(
                    context_provider(
                        input_.get("conv_id") or conv_id,
                        input_.get("agent_id"),
                    )
                )
                projected = list(projected or [])
            except Exception:
                logger.exception(
                    "[default_thinking] context_provider failed, skipping"
                )

        # 3. 拼最终 LLM messages
        #    前缀稳定：system（身份 + 环境 + 静态记忆索引）+ catalog + 历史投影
        #    尾缀动态：当前输入 + 动态记忆 + 运行提醒（append 在末尾）
        llm_messages = []
        if static_block:
            # 静态记忆索引并入 system，整场会话冻结（KV-cache 稳定前缀）
            sys_prompt = (sys_prompt or "") + "\n\n" + static_block
        if sys_prompt:
            llm_messages.append({"role": "system", "content": sys_prompt})
        # skill catalog reminder（对齐 DSH tool-skill）：
        #   - 不进 system prompt（避免 KV-cache 污染），作为 user-role
        #     <system-reminder> 注入；
        #   - 首次或 digest 变化才发（consumer 内部自管）；
        #   - 注入位置 = memory_context 之后、历史投影之前（与 memory
        #     块同级），保证模型能先看到工具能力再读历史。
        if catalog_consumer is not None:
            try:
                if getattr(catalog_consumer, "_last_published_digest", None) is None:
                    catalog_msg = await _maybe_await(catalog_consumer.initial())
                else:
                    catalog_msg = await _maybe_await(catalog_consumer.refresh())
                if catalog_msg:
                    llm_messages.append(catalog_msg)
            except Exception:
                logger.exception("[default_thinking] skill catalog consumer failed, skipping")
        # 可用 DB 列表 reminder（对齐 DSH tool-db）——与 catalog_consumer 同位
        # 注入：首次 / DB 列表 digest 变化才发，避免拼 schema 进 system prompt。
        if db_catalog_consumer is not None:
            try:
                if getattr(db_catalog_consumer, "_last_published_digest", None) is None:
                    db_msg = await _maybe_await(db_catalog_consumer.initial())
                else:
                    db_msg = await _maybe_await(db_catalog_consumer.refresh())
                if db_msg:
                    llm_messages.append(db_msg)
            except Exception:
                logger.exception("[default_thinking] db catalog consumer failed, skipping")
        # 事件日志投影注入（V2 单源上下文：历史 user/assistant + 工具事实 + 摘要）。
        # 去重：V2Agent 已在 run_loop 前 emit 当前 user/message，投影最后一条
        # user 若等于当前 user_prompt，则移除（由下面统一追加，避免重复）。
        if projected and projected[-1].get("role") == "user" \
                and str(projected[-1].get("content", "")) == user_prompt:
            projected = projected[:-1]
        llm_messages.extend(projected)
        # 历史投影设为"每轮动态参考上下文"的插入边界：动态记忆（<memory-context>）
        # 与运行提醒统一插在历史投影**之后**、当前用户输入**之前**——作为参考背景
        # 供模型结合最新指令读取；同时保证"用户最新输入"始终是消息列表最后一条
        # user，避免动态块抢占"最新指令"位（前缀仍稳定，只有 input 前这一段每轮变）。
        for _ref in ([memory_context] if memory_context else []) + operational_tail:
            llm_messages.append({"role": "user", "content": _ref})

        # NOTE: TODO 列表**不**在此注入。对齐 DSH tool-todo 设计：
        #   - system prompt 是 KV-cache 友好的静态前缀，TODO 进度是每轮都会变
        #     的会话事实，不能污染 system prompt（否则 prefix 缓存全失效）；
        #   - 模型通过自己上一轮 todowrite tool_call 的参数（每次 send ENTIRE
        #     list）+ 工具结果回显（`{todos, counts}`）自然看到当前状态；
        #   - 事件溯源：`todo/write` 事件流（is_surface=False）作为 UI / 回放
        #     的单一事实源，由 `gyra.agent.core.v2.todo_projection` 投影。
        # 最后一条 human 消息覆写为 user_prompt（多模态时 content 为数组：
        # 文本 + 图片/音频/视频/文件段，供支持多模态的模型消费）
        media_items = input_.get("media_items") or []
        if media_items:
            content: Any = [{"type": "text", "text": user_prompt}]
            content.extend(list(media_items))
        else:
            content = user_prompt
        llm_messages.append({"role": "user", "content": content})

        # 3.5 ContextManager.pre_step：spill 超大工具结果（避免压爆 LLM 上下文）
        if context_manager is not None:
            try:
                llm_messages = await context_manager.pre_step(llm_messages)
            except Exception:
                logger.exception(
                    "[default_thinking] context pre_step failed, skipping"
                )

        # 4 + 5. LLM stream + retry + scrub
        scrubber = getattr(getattr(memory_bundle, "pipeline", None), "scrub_stream_delta", None) if memory_bundle else None

        async def _stream():
            async for chunk in llm_stream_fn(llm_messages, model_alias):
                yield chunk

        async for chunk in retrying_thinking(
            _stream, max_attempts=max_attempts, model_fallback=model_fallback,
            initial_model=model_alias,
        ):
            token = chunk.get("token")
            usage = chunk.get("usage")
            tool_calls_raw = chunk.get("tool_calls")
            channel = chunk.get("channel", "content")

            if token:
                # <memory-context> fence scrubber 只作用于 content 通道；
                # thinking（推理）文本不参与 memory fence，也不应消费 scrubber
                # 状态（避免 fence 跨越 thinking/content 边界误伤正文）。
                if channel == "content" and scrubber is not None:
                    token = scrubber(token)
                yield TokenChunk(token=token, usage=usage, channel=channel)
            if tool_calls_raw:
                tcs = [V2ToolCall(name=tc["tool"], args=tc.get("input", {})) for tc in tool_calls_raw]
                yield ToolCallChunk(tool_calls=tcs)
            elif usage:
                yield UsageChunk(usage=usage)

    return thinking_fn


async def _maybe_await(value):
    import inspect
    if inspect.isawaitable(value):
        return await value
    return value


def _build_memory_context_block(raw: str) -> str:
    """等价 BAIZE memory/read_pipeline.build_memory_context_block。"""
    if not raw:
        return ""
    return f"<memory-context>\n{raw}\n</memory-context>"


async def _load_static_memory_index(memory_bundle) -> Optional[str]:
    """首轮静态记忆索引：从 read pipeline 加载冻结块并入 system 前缀。

    - 冻结一次后整场会话不变（profile/preference + L1 memory 索引切片）；
    - 具体回忆内容由 LLM 经 memory_search 工具后续按需读取增量；
    - 无 memory_bundle / 无 pipeline / 加载失败时返回 None（静默跳过）。
    """
    if memory_bundle is None:
        return None
    pipeline = getattr(memory_bundle, "pipeline", None)
    if pipeline is None:
        return None
    try:
        # MagicMock 兼容：static_loaded 若不是真 bool 或 static_block 非 str，跳过
        loaded = getattr(pipeline, "static_loaded", False)
        if not isinstance(loaded, bool) or not loaded:
            loader = getattr(pipeline, "load_static_block", None)
            if callable(loader):
                await loader(memory_bundle)
        block = getattr(pipeline, "static_block", None)
        return block if isinstance(block, str) and block else None
    except Exception:  # noqa: BLE001
        logger.exception("[default_thinking] static memory index load skipped")
        return None
