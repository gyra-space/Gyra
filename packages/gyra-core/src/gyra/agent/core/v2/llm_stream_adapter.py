"""gyra_llm stream 适配器。

把 gyra_llm 的 OpenAI 格式 delta stream 转成 default_thinking_fn 期望的 chunk：
  {"token": str} / {"tool_calls": [{"tool": str, "input": dict}]} / {"usage": dict}
"""
import json
import logging
from typing import Any, AsyncGenerator, Callable

logger = logging.getLogger(__name__)


def make_gyra_llm_stream(gyra_stream_fn: Callable) -> Callable:
    """包装 gyra_llm stream。

    Args:
        gyra_stream_fn: async generator factory，输入 (model, messages)，
            yield OpenAI 格式 chunk:
            {"choices": [{"delta": {"content": ...}, "finish_reason": ...,
                          "message": {"tool_calls": [...]}}],
             "usage": {...}}

    Returns:
        async generator factory，输入 (messages, model)，
        yield {"token": str} / {"tool_calls": [...]} / {"usage": dict}
    """

    async def adapted_stream(messages, model) -> AsyncGenerator[dict, None]:
        async for raw in gyra_stream_fn(model, messages):
            choices = raw.get("choices", [])
            usage = raw.get("usage")

            for choice in choices:
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason")

                content = delta.get("content")
                if content:
                    yield {"token": content, "usage": usage}

                if finish_reason == "tool_calls":
                    message = choice.get("message", {})
                    raw_tool_calls = message.get("tool_calls", [])
                    tcs = []
                    for tc in raw_tool_calls:
                        fn = tc.get("function", {})
                        name = fn.get("name")
                        args_str = fn.get("arguments", "{}")
                        try:
                            args = json.loads(args_str) if args_str else {}
                        except json.JSONDecodeError:
                            args = {"_raw": args_str}
                        if name:
                            tcs.append({"tool": name, "input": args})
                    if tcs:
                        yield {"tool_calls": tcs, "usage": usage}

                if usage and not content and finish_reason != "tool_calls":
                    yield {"usage": usage}

    return adapted_stream


def make_gyra_llm_stream_fn(
    ai_wrapper,
    model_alias: str,
    get_function_calling_context: Callable = None,
):
    """构造 default_thinking_fn 需要的 llm_stream_fn（dict chunk 格式）。

    包装 AIWrapper.create(stream_out=True) → yield {"token", "usage", "tool_calls"}.
    BAIZE 路径同样通过 AIWrapper 解析 LLM provider（self.llm_provider 在生产为 None）。

    get_function_calling_context: 可选异步回调，返回 function_calling_context
    （含 "tools" 声明，如 V1 function_calling_params 产物）。缺省时 LLM 请求不携带
    工具声明，模型将认为无可调用工具（表现为"无文件权限"等误判）。
    """
    async def _stream(messages, model):
        create_kwargs = {
            "messages": messages,
            "llm_model": model or model_alias,
            "stream_out": True,
        }
        if get_function_calling_context is not None:
            try:
                fcc = await get_function_calling_context()
                if fcc and fcc.get("tools"):
                    create_kwargs["function_calling_context"] = fcc
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[llm_stream_adapter] fcc fetch failed: {e}")
        # 流式 tool_calls 逐帧增量累积，只在流结束帧产出完整参数，
        # 避免把中间帧（arguments 未闭合）当成最终调用导致工具执行报错。
        last_tool_calls: Optional[list] = None
        # AIWrapper.create 流式输出 content/thinking_content 是"累积全量"，
        # 逐帧取增量 token，避免 _v2_final_answer += 全量导致文本重复。
        prev_full_text = ""
        async for model_output in ai_wrapper.create(**create_kwargs):
            chunk = {}
            # AgentLLMOut has .content and .thinking_content, not .text
            text = getattr(model_output, "content", None) or ""
            thinking = getattr(model_output, "thinking_content", None) or ""
            # Combine thinking and content for full text
            full_text = (thinking + text) if thinking and text else (thinking or text)
            if full_text:
                if full_text.startswith(prev_full_text) and prev_full_text:
                    delta = full_text[len(prev_full_text):]
                else:
                    delta = full_text  # 前缀不匹配（异常/新段）退化为全量
                prev_full_text = full_text
                if delta:
                    chunk["token"] = delta
            usage = None
            if getattr(model_output, "metrics", None):
                usage_dict = {}
                metrics = model_output.metrics
                if hasattr(metrics, "prompt_tokens") and metrics.prompt_tokens:
                    usage_dict["prompt_tokens"] = metrics.prompt_tokens
                if hasattr(metrics, "completion_tokens") and metrics.completion_tokens:
                    usage_dict["completion_tokens"] = metrics.completion_tokens
                if hasattr(metrics, "total_tokens") and metrics.total_tokens:
                    usage_dict["total_tokens"] = metrics.total_tokens
                if usage_dict:
                    chunk["usage"] = usage_dict
                    usage = usage_dict
            tool_calls = getattr(model_output, "tool_calls", None)
            if tool_calls:
                if isinstance(tool_calls, str):
                    try:
                        tool_calls = json.loads(tool_calls)
                    except Exception:
                        tool_calls = None
                if isinstance(tool_calls, list):
                    normalized = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            fn = tc.get("function") or {}
                            normalized.append({
                                "tool": fn.get("name") or tc.get("name") or tc.get("tool"),
                                "input": _parse_args(fn.get("arguments") or tc.get("input") or tc.get("args") or {}),
                            })
                        else:
                            normalized.append({"tool": str(tc), "input": {}})
                    # 只保留参数解析成功的调用：流式中间帧 arguments 未闭合时
                    # _parse_args 会落到 {"_raw": ...}，必须跳过，避免误当最终调用
                    complete = [n for n in normalized if "_raw" not in (n.get("input") or {})]
                    if complete:
                        # 覆盖为最新累积全量（后续帧含完整 arguments）
                        last_tool_calls = complete
            if chunk:
                yield chunk
        # 流结束后兜底：完整 tool_calls 只产出一次（兼容无 finish/usage 信号的单帧输出）
        if last_tool_calls:
            yield {"tool_calls": last_tool_calls}

    return _stream


def _parse_args(args):
    """tool_call arguments may be JSON string or dict."""
    if isinstance(args, str):
        try:
            return json.loads(args)
        except Exception:
            return {"_raw": args}
    return args or {}
