import asyncio
import logging
from typing import Union, Optional, Any, List, AsyncGenerator, Tuple, Coroutine

from fastapi import BackgroundTasks

from gyra.core import HumanMessage
from gyra.util.date_utils import current_ms
from gyra.util.tracer import root_tracer
from gyra_serve.agent.agents.chat.agent_chat import AgentChat, _format_vis_msg
from gyra_serve.building.config.api.schemas import ChatInParamValue

logger = logging.getLogger(__name__)


class SimpleAgentChat(AgentChat):
    # 持有后台 finalize task 的强引用,避免运行中被 GC
    # (SSE 断流后等 agent 跑完再保存最终结果的异步任务)
    _background_finalizers: set = set()

    async def chat(
        self,
        conv_uid: str,
        gpts_name: str,
        user_query: Union[str, HumanMessage],
        background_tasks: Optional[BackgroundTasks] = None,
        specify_config_code: Optional[str] = None,
        user_code: Optional[str] = None,
        sys_code: Optional[str] = None,
        stream: bool = True,
        chat_call_back: Optional[Any] = None,
        chat_in_params: Optional[List[ChatInParamValue]] = None,
        **ext_info: Any,
    ) -> Union[AsyncGenerator[str, None], Tuple[str, str]]:
        """简单对话入口(构建会话、发起Agent对话、处理连接中断、保存对话历史)

        Args:
            conv_uid: 会话ID
            gpts_name: 要对话的智能体名称
            user_query: 用户消息，支持多模态
            background_tasks: FastAPI后台任务
            specify_config_code: 指定配置代码
            user_code: 用户代码
            sys_code: 系统代码
            stream: 是否使用流式响应
            chat_call_back: 对话回调函数
            chat_in_params: 对话输入参数
            **ext_info: 扩展信息

        Yields:
            str: 对话响应内容

        Raises:
            asyncio.CancelledError: 客户端断开连接
            Exception: 其他异常
        """
        logger.info(
            f"Simple agent chat initiated - GPT: {gpts_name}, Query: {user_query}, Session: {conv_uid}"
        )

        current_message = None
        agent_conv_id = None
        agent_task: Optional[Coroutine] = None
        error_info: Optional[str] = None
        start_ms = root_tracer.get_context_entrance_ms() or current_ms()
        ttft = None
        first_chunk_ms = None
        span = root_tracer.start_span(
            "agent_chat",
            metadata={
                "chat_type": "simple",
                "app_code": gpts_name,
                "ttft": None,
                "succeed": False,
            },
        )
        try:
            # 初始化对话
            current_message = await self._initialize_conversation(
                conv_session_id=conv_uid,
                app_code=gpts_name,
                user_query=user_query,
                user_code=user_code,
            )

            (
                agent_conv_id,
                gpts_conversations,
            ) = await self._initialize_agent_conversation(
                conv_session_id=conv_uid, app_code=gpts_name, **ext_info
            )
            span.metadata["conv_id"] = agent_conv_id

            # 处理对话流
            async for task, chunk, conv_id in self.aggregation_chat(
                conv_id=conv_uid,
                agent_conv_id=agent_conv_id,
                gpts_name=gpts_name,
                user_query=user_query,
                user_code=user_code,
                sys_code=sys_code,
                chat_in_params=chat_in_params,
                specify_config_code=specify_config_code,
                gpts_conversations=gpts_conversations,
                stream=stream,
                **ext_info,
            ):
                agent_task = task
                first_chunk_ms = (
                    current_ms() if first_chunk_ms is None else first_chunk_ms
                )
                if ttft is None:
                    ttft = current_ms() - start_ms
                    span.metadata["ttft"] = ttft
                    root_tracer.start_span("agent.ttft", metadata={"ttft": ttft}).end()
                yield chunk, agent_conv_id
            span.metadata["succeed"] = True
        except asyncio.CancelledError:
            # SSE/请求被取消:不 cancel agent_task,让它后台继续运行,
            # 由 finally 的后台 finalize 在 agent 跑完后保存最终结果。
            # 真正终止只走 stop_chat 接口(cancel _running_tasks 中的 task)。
            logger.warning(
                f"Chat stream cancelled for session {conv_uid}, "
                f"agent continues in background"
            )
            error_info = "对话已被用户中断"
            yield _format_vis_msg("对话已被用户中断"), agent_conv_id

        except Exception as e:
            error_msg = f"Chat with {gpts_name} failed (Conversation ID: {agent_conv_id}) - {str(e)}"
            logger.exception(error_msg)
            error_info = str(e)
            # 不 cancel agent_task:异常由后台 finalize 兜底保存
            yield _format_vis_msg(error_info), agent_conv_id

        finally:
            # SSE 断开 ≠ agent 终止:agent 是独立 asyncio.Task(_inner_chat),
            # 客户端断流时仍在后台运行。按 agent_task 是否结束分流:
            # - 未结束(客户端断流): 不立即 save(避免用中间态覆盖 final 视图)、
            #   不清 cache、不 unregister;启动后台 finalize 等 agent 跑完后
            #   写完整 final 消息,前端重开页面可读取或轮询恢复。
            # - 已结束(正常完成/异常/stop_chat 取消): 直接 save。
            # 仅 stop_chat 接口会 cancel agent_task(真正终止)。
            if agent_task is not None and not agent_task.done():
                logger.info(
                    f"SSE disconnected, agent continues in background "
                    f"(conv_id={conv_uid}); finalize will persist final view "
                    f"after agent done"
                )
                finalize_task = asyncio.create_task(
                    self._finalize_in_background(
                        agent_task=agent_task,
                        conv_session_id=conv_uid,
                        agent_conv_id=agent_conv_id,
                        current_message=current_message,
                        chat_call_back=chat_call_back,
                        first_chunk_ms=first_chunk_ms,
                    )
                )
                # 持有强引用,避免后台 task 在运行中被 GC
                self._background_finalizers.add(finalize_task)
                finalize_task.add_done_callback(self._background_finalizers.discard)
            else:
                logger.info(f"Saving conversation history for session {conv_uid}")
                try:
                    await self.save_conversation(
                        conv_session_id=conv_uid,
                        agent_conv_id=agent_conv_id,
                        current_message=current_message,
                        err_msg=error_info,
                        chat_call_back=chat_call_back,
                        first_chunk_ms=first_chunk_ms,
                    )
                except Exception as e:
                    logger.exception(f"Failed to save conversation: {e}")
            span.end()

    async def _finalize_in_background(
        self,
        agent_task: asyncio.Task,
        conv_session_id: str,
        agent_conv_id: str,
        current_message: Any,
        chat_call_back: Optional[Any] = None,
        first_chunk_ms: Optional[int] = None,
    ) -> None:
        """SSE 断流后,后台等待 agent 跑完再保存最终对话。

        客户端断开 SSE 时 agent(_inner_chat) 仍为独立 task 在后台运行。
        本方法等其结束后生成完整 vis_final 落盘 + 销毁 cache + 注销
        running task,使前端重新打开对话可读取完整结果;若 agent 运行中
        则前端降级为轮询。仅 stop_chat 接口会 cancel agent_task(主动终止),
        此时按中断态保存。
        """
        err_msg: Optional[str] = None
        try:
            await agent_task
        except asyncio.CancelledError:
            err_msg = "对话已被用户中断"
            logger.info(
                f"Background finalize: agent cancelled by stop_chat "
                f"(conv_id={agent_conv_id})"
            )
        except Exception as e:
            err_msg = str(e)
            logger.exception(
                f"Background finalize: agent failed (conv_id={agent_conv_id}): {e}"
            )
        try:
            logger.info(
                f"Background finalize: saving conversation for {agent_conv_id}"
            )
            await self.save_conversation(
                conv_session_id=conv_session_id,
                agent_conv_id=agent_conv_id,
                current_message=current_message,
                err_msg=err_msg,
                chat_call_back=chat_call_back,
                first_chunk_ms=first_chunk_ms,
            )
        except Exception as e:
            logger.exception(
                f"Background finalize: failed to save conversation "
                f"(conv_id={agent_conv_id}): {e}"
            )
        finally:
            # 兜底注销 running task(aggregation_chat finally 在断流时不注销)
            try:
                self.unregister_running_task(conv_session_id)
            except Exception:
                pass
