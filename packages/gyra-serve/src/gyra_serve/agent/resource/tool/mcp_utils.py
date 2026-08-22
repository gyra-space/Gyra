import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime
from typing import Optional, Any, List
from urllib.parse import urlparse

import shortuuid
from cachetools import TTLCache
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

from gyra._private.config import Config
from gyra.util.async_executor_utils import safe_call_tool
from gyra.util.global_helper import truncate_text
from gyra.util.log_util import MCP_LOGGER as LOGGER
from gyra.util.tracer import root_tracer
from gyra_serve.agent.db.gpts_tool import GptsToolDao
from gyra_serve.agent.db.gpts_tool_messages import (
    GptsToolMessagesDao,
    GptsToolMessages,
)

logger = logging.getLogger(__name__)
# MCP tools/list 结果缓存：按 (mcp_name, server) 精确缓存，TTL 可调，避免每次会话
# 启动都访问远程 MCP server。工具列表变更时通过 invalidate_mcp_tool_cache 主动失效。
MCP_TOOL_CACHE_TTL = int(os.environ.get("GYRA_MCP_TOOL_CACHE_TTL", 600))
tool_cache = TTLCache(maxsize=200, ttl=MCP_TOOL_CACHE_TTL)
gpts_tool_messages_dao = GptsToolMessagesDao()
gpts_tool_dao = GptsToolDao()

CFG = Config()


def _tool_cache_key(mcp_name: str, server: str) -> tuple:
    """缓存 key：mcp 名 + server 地址，防止同名不同 server 串缓存。"""
    return mcp_name, server


def invalidate_mcp_tool_cache(mcp_name: str, server: str) -> None:
    """主动失效某个 MCP server 的工具列表缓存（等价 tools/list_changed）。"""
    key = _tool_cache_key(mcp_name, server)
    if key in tool_cache:
        tool_cache.pop(key, None)
        logger.info(f"mcp_server:{mcp_name}, invalidated tool list cache, server:{server}")


def _make_json_serializable(obj: Any) -> Any:
    """
    递归地将对象转换为 JSON 可序列化的格式

    Args:
        obj: 任意对象

    Returns:
        JSON 可序列化的对象
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    else:
        # 对于不可序列化的对象，返回其字符串表示
        # 这包括 AgentFileSystem, SandboxClient 等复杂对象
        return str(obj)


def _is_sse_url(url: str) -> bool:
    """根据 URL 路径判断是否为 SSE 端点。

    SSE 端点路径通常包含 `/sse`（如 `/mcp/sse`）；Streamable HTTP 端点
    则为根路径或 `/mcp`。据此在客户端层面自动选择传输类型。
    """
    try:
        path = urlparse(url).path.lower()
    except Exception:  # noqa: BLE001
        return False
    return path.endswith("/sse") or "/sse" in path


@asynccontextmanager
async def create_mcp_client(url: str, headers: Optional[dict] = None, timeout: Optional[int] = None):
    """按 URL 自动选择 MCP 传输方式，产出 (read, write, http_diagnostic) 三元组。

    - SSE（路径含 `/sse`）：使用 ``sse_client``。
    - Streamable HTTP（其余 HTTP(S) URL）：使用 ``streamable_http_client``，
      通过 ``httpx2.AsyncClient`` 透传 headers 与超时。

    ``http_diagnostic`` 记录 Streamable HTTP 调用过程中最近一次 4xx/5xx 响应的
    状态码与响应体片段。mcp SDK 对非 JSON-RPC 错误体只返回泛化的
    ``MCPError(-32603, 'Server returned an error response')``，原始 HTTP 信息
    会被丢弃；这里在传输层补采，便于调用方透出真实失败原因。
    """
    if _is_sse_url(url):
        async with sse_client(
            url=url, headers=headers, sse_read_timeout=timeout if timeout is not None else 300.0
        ) as (read, write):
            yield read, write, {}
        return
    # Streamable HTTP
    import httpx2
    from mcp.client.streamable_http import streamable_http_client

    http_diagnostic: dict = {}

    async def _record_error_response(response: Any):
        if getattr(response, "status_code", 0) >= 400:
            try:
                await response.aread()
                body = response.text
            except Exception:  # noqa: BLE001
                body = ""
            http_diagnostic["status"] = getattr(response, "status_code", None)
            http_diagnostic["reason"] = getattr(response, "reason_phrase", None)
            http_diagnostic["body"] = body[:2000]

    request_timeout = httpx2.Timeout(timeout if timeout is not None else 60.0)
    async with httpx2.AsyncClient(
        headers=headers,
        timeout=request_timeout,
        event_hooks={"response": [_record_error_response]},
    ) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write):
            yield read, write, http_diagnostic


def get_tool_input_schema(tool: Any) -> dict:
    """兼容新旧 mcp SDK 的 Tool 字段命名（input_schema / inputSchema）。

    新版 mcp_types 将 `Tool.inputSchema` 改名为 `Tool.input_schema`，
    这里做兼容取值，避免 AttributeError。
    """
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    if schema is None:
        raise ValueError(
            f"MCP tool {getattr(tool, 'name', '?')} 缺少 input schema 字段"
        )
    return schema


def switch_mcp_input_schema(input_schema: dict):
    args = {}
    try:
        properties = input_schema["properties"]
        required = input_schema.get("required", [])
        for k, v in properties.items():
            arg = {}

            title = v.get("title", None)
            description = v.get("description", None)
            items = v.get("items", None)
            items_str = str(items) if items else None
            any_of = v.get("anyOf", None)
            any_of_str = str(any_of) if any_of else None

            default = v.get("default", None)
            type = v.get("type", "string")

            arg["type"] = type
            if title:
                arg["title"] = title
            arg["description"] = description or items_str or any_of_str or str(v)
            arg["required"] = True if k in required else False
            if default:
                arg["default"] = default
            args[k] = arg
        return args
    except Exception as e:
        raise ValueError(f"MCP input_schema can't parase!{str(e)},{input_schema}")


async def get_mcp_tool_list(
    mcp_name: str,
    server: str,
    headers: Optional[dict] = None,
    allow_tools: Optional[List[str]] = None,
    server_ssl_verify: Optional[Any] = None,
    use_cache: bool = True,
    refresh_cache: bool = False,
    tool_id: Optional[str] = None,
    timeout: Optional[int] = None,
):
    trace_id = (
        root_tracer.get_current_span().trace_id
        if root_tracer.get_current_span().trace_id is not None
        else str(uuid.uuid4())
    )
    rpc_id = (
        root_tracer.get_context_rpc_id() + "." + shortuuid.ShortUUID().random(length=8)
    )
    cookie = root_tracer.get_context_cookie()

    if headers is None:
        headers = {}

    async def mcp_tool_list(server: str):
        try:
            cache_key = _tool_cache_key(mcp_name, server)
            cache_result = (
                None if not use_cache or refresh_cache else tool_cache.get(cache_key)
            )
            if cache_result and cache_result.tools and len(cache_result.tools) > 0:
                LOGGER.info(
                    f"mcp_server:{mcp_name}, hit tool list cache:{cache_result}"
                )
                result = cache_result
            else:
                start_time = int(datetime.now().timestamp() * 1000)
                (
                    headers["SOFA-TraceId"],
                    headers["SOFA-RpcId"],
                    headers["x-mcp-hash-key"],
                    headers["cookie"],
                ) = trace_id, rpc_id, str(uuid.uuid4()), cookie
                async with create_mcp_client(server, headers=headers) as (read, write, _http_diag):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        list_tools = await session.list_tools()
                        end_time = int(datetime.now().timestamp() * 1000)
                        LOGGER.info(
                            f"mcp_server:{mcp_name},sse:{server},header:{headers},list_tools:[{list_tools}],costMs:[{end_time - start_time}]"
                        )
                        if use_cache:
                            tool_cache[cache_key] = list_tools
                        result = deepcopy(list_tools)
            if allow_tools and len(allow_tools) > 0:
                tools = [tool for tool in result.tools if tool.name in allow_tools]
                result.tools = tools
            return result
        except Exception as e:
            LOGGER.exception(
                f"[DIGEST][tools/list]mcp_server=[{mcp_name}],sse=[{server}],success=[N],err_msg=[{str(e)}]"
            )
            raise e

    try:
        time_out = timeout if timeout else 60
        if CFG.debug_mode:
            logger.info("MCP Enter DebugMode, Use local mcp gateways!")
            server = f"http://localhost:{CFG.GYRA_WEBSERVER_PORT}/mcp/sse"
            time_out = 180
        return await safe_call_tool(
            mcp_tool_list,  # 可能是阻塞的函数
            server,
            time_out=time_out,
        )
    except asyncio.TimeoutError as e:
        raise ValueError(f"MCP服务{server}工具列表调用超时!")
    except Exception as e:
        raise ValueError(f"MCP服务{server}工具列表调用异常!", e)


async def call_mcp_tool(
    mcp_name: str,
    tool_name: str,
    server: str,
    headers: Optional[dict[str, str]] = None,
    server_ssl_verify: Optional[Any] = None,
    timeout: Optional[int] = None,
    tool_id: Optional[str] = None,
    **kwargs,
):
    logger.info(f"call_mcp_tool:{mcp_name},{tool_name},{server},{timeout}")
    trace_id = (
        root_tracer.get_current_span().trace_id
        if root_tracer.get_current_span().trace_id is not None
        else str(uuid.uuid4())
    )
    rpc_id = (
        root_tracer.get_context_rpc_id() + "." + shortuuid.ShortUUID().random(length=8)
    )
    cookie = root_tracer.get_context_cookie()

    if headers is None:
        headers = {}

    arguments = kwargs.get("arguments", kwargs)
    if isinstance(arguments, dict):
        arguments = {
            k: v
            for k, v in arguments.items()
            if k
            not in (
                "time_out",
                "timeout",
                "tool_id",
                "server_ssl_verify",
                "headers",
                "server",
                "tool_name",
                "mcp_name",
            )
        }

    if not tool_id:
        tool_id = str(uuid.uuid4())

    http_diagnostic: Optional[dict] = None

    async def call_tool(server: str, arguments: dict):
        nonlocal http_diagnostic
        # 将 arguments 转换为 JSON 可序列化的格式
        serializable_arguments = _make_json_serializable(arguments)

        gpts_tool_messages = GptsToolMessages(
            tool_id=tool_id,
            name=mcp_name,
            sub_name=tool_name,
            type="MCP",
            input=json.dumps(serializable_arguments, ensure_ascii=False),
            success=1,
            trace_id=trace_id,
        )

        try:
            start_time = int(datetime.now().timestamp() * 1000)
            (
                headers["SOFA-TraceId"],
                headers["SOFA-RpcId"],
                headers["x-mcp-hash-key"],
                headers["cookie"],
            ) = trace_id, rpc_id, str(uuid.uuid4()), cookie

            if CFG.debug_mode:
                logger.info("MCP Enter DebugMode, Use local mcp gateways!")
                mcp_server = f"http://localhost:{CFG.GYRA_WEBSERVER_PORT}/mcp/sse"
            else:
                mcp_server = server
            async with create_mcp_client(
                mcp_server, headers=headers, timeout=timeout
            ) as (read, write, http_diagnostic):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    # 使用序列化后的参数调用 MCP 工具
                    result = await session.call_tool(
                        tool_name, arguments=serializable_arguments
                    )
                    end_time = int(datetime.now().timestamp() * 1000)
                    LOGGER.info(
                        f"[DIGEST][tools/call]mcp_server=[{mcp_name}],sse=[{mcp_server}],success=[Y],err_msg=[],tool=[{tool_name}],costMs=[{end_time - start_time}],result_length=[{len(str(result.json()))}],headers=[{headers}],result:[{result.json()}]"
                    )
                    gpts_tool_messages.output = truncate_text(
                        json.dumps(result.model_dump(), ensure_ascii=False), 65535
                    )
                    return result
        except Exception as e:
            gpts_tool_messages.error = str(e)
            gpts_tool_messages.success = 0
            LOGGER.exception(
                f"[DIGEST][tools/call]mcp_server=[{mcp_name}],sse=[{server}],success=[N],err_msg=[{str(e)}],tool=[{tool_name}],costMs=[],result_length=[],headers=[{headers}]"
            )
            raise e
        finally:
            try:
                gpts_tool_messages_dao.create(gpts_tool_messages)
            except Exception as m:
                logger.info(
                    f"call_mcp_tool: save message error: {m}, trace_id:{trace_id}"
                )

    try:
        return await call_tool(server, arguments)
    except asyncio.TimeoutError as e:
        raise ValueError(f"MCP服务{mcp_name}工具调用超时!")
    except Exception as e:
        # 工具未找到/不存在：远端工具列表可能已变更，主动失效缓存，下次 list 重新拉取。
        if _is_tool_missing_error(e):
            invalidate_mcp_tool_cache(mcp_name, server)
        reason = _format_mcp_call_error(e, http_diagnostic)
        raise ValueError(f"MCP服务{mcp_name}:{tool_name}工具调用异常! 原因: {reason}", e) from e


def _is_tool_missing_error(err: Any) -> bool:
    """判断错误是否因工具不存在/未找到导致（tools/list_changed 的等价失效信号）。"""
    msg = str(err).lower()
    return any(kw in msg for kw in ("unknown tool", "tool not found", "not found", "method not found", "no tool named"))


def _unwrap_exception(err: BaseException) -> BaseException:
    """递归解包 ExceptionGroup，返回最内层首个异常（mcp SDK 内部用 TaskGroup 包装异常）。"""
    while isinstance(err, BaseExceptionGroup) and err.exceptions:
        err = err.exceptions[0]
    return err


def _format_mcp_call_error(e: BaseException, http_diagnostic: Optional[dict] = None) -> str:
    """把 MCP 调用异常解析为可读的失败原因，透出真实错误而非 SDK 的泛化消息。"""
    inner = _unwrap_exception(e)
    parts = []
    code = getattr(inner, "code", None)
    message = getattr(inner, "message", None)
    if code is not None or message is not None:
        # MCPError 等协议层异常
        detail = message or str(inner)
        parts.append(f"协议错误 code={code}, message={detail}")
        data = getattr(inner, "data", None)
        if data:
            parts.append(f"data={str(data)[:2000]}")
    else:
        parts.append(f"{type(inner).__name__}: {str(inner)}")
    if http_diagnostic:
        status = http_diagnostic.get("status")
        if status is not None:
            parts.append(f"HTTP {status} {http_diagnostic.get('reason', '')}".rstrip())
        body = http_diagnostic.get("body")
        if body:
            parts.append(f"响应体: {body[:2000]}")
    return "; ".join(parts)


def get_im_token(cookie: str):
    if not cookie or cookie == "":
        return None

    # 按分号分割所有键值对
    pairs = cookie.split(";")

    # 用于保存最后出现的 im_token
    im_token = None

    for pair in pairs:
        pair = pair.strip()
        if "=" in pair:
            key, value = pair.split("=", 1)
            if key == "IAM_TOKEN":
                im_token = value

    return im_token
