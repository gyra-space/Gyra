import asyncio
import datetime
import json
import logging
import os
import time
import uuid
from concurrent.futures import Executor
from typing import List, Optional, cast

import pandas as pd
from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse

from gyra._private.config import Config

from gyra_app.feature_plugins.permissions.checker import require_permission
from gyra.component import ComponentType, SystemApp
from gyra.configs import TAG_KEY_KNOWLEDGE_CHAT_DOMAIN_TYPE
from gyra.core import ModelOutput, HumanMessage
from gyra.core.awel import BaseOperator, CommonLLMHttpRequestBody
from gyra.core.awel.dag.dag_manager import DAGManager
from gyra.core.awel.util.chat_util import safe_chat_stream_with_dag_task
from gyra.core.interface.file import FileStorageClient
from gyra.core.schema.api import (
    ChatCompletionResponseChoice,
    ChatMessage,
    UsageInfo,
    ChatCompletionResponse,
)
from gyra.util.data_util import first
from gyra.util.executor_utils import (
    DefaultExecutorFactory,
    ExecutorFactory,
)
from gyra.util.file_client import FileClient
from gyra.util.tracer import SpanType, root_tracer

# TODO: rewire to new knowledge module (Task #9)
try:
    from gyra_app.knowledge.request.request import KnowledgeSpaceRequest  # type: ignore
    from gyra_app.knowledge.service import KnowledgeService  # type: ignore
except ImportError:  # pragma: no cover - rag module removed
    KnowledgeSpaceRequest = None  # type: ignore[assignment]
    KnowledgeService = None  # type: ignore[assignment]

from gyra_app.openapi.api_view_model import (
    ChatCompletionResponseStreamChoice,
    ChatCompletionStreamResponse,
    ChatSceneVo,
    ConversationVo,
    DeltaMessage,
    MessageVo,
    Result,
    WorkMode,
)
from gyra_serve.agent.agents.controller import multi_agents
from gyra_serve.agent.db.gpts_app import UserRecentAppsDao
from gyra_serve.agent.team.base import TeamMode
from gyra_serve.core import blocking_func_to_async
from gyra_serve.datasource.manages.db_conn_info import DBConfig, DbTypeInfo
from gyra_serve.flow.service.service import Service as FlowService
from gyra_serve.utils.auth import UserRequest, get_user_from_headers

router = APIRouter()
CFG = Config()
logger = logging.getLogger(__name__)
# TODO: rewire to new knowledge module (Task #9)
knowledge_service = KnowledgeService() if KnowledgeService else None

model_semaphore = None
global_counter = 0

user_recent_app_dao = UserRecentAppsDao()


def _is_uuid_like(filename: str) -> bool:
    """Check if filename looks like a UUID (file_id)."""
    import re

    name_without_ext = filename.rsplit(".", 1)[0]
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(uuid_pattern.match(name_without_ext))


def _get_file_name_from_url_or_metadata(url_str: str, fs: FileStorageClient) -> str:
    """Get original file name from URL or metadata storage.

    When files are uploaded, they are stored with UUID as file_id, but original
    filename is saved in metadata. This function retrieves the original filename.
    """
    from urllib.parse import urlparse, unquote

    if url_str.startswith("gyra-fs://"):
        try:
            metadata = fs.storage_system.get_file_metadata_by_uri(url_str)
            if metadata and metadata.file_name:
                return metadata.file_name
        except Exception:
            pass

    parsed = urlparse(url_str)
    path_file_name = os.path.basename(unquote(parsed.path))

    if path_file_name and not _is_uuid_like(path_file_name):
        return path_file_name

    try:
        metadata = fs.storage_system.get_file_metadata_by_uri(url_str)
        if metadata and metadata.file_name:
            return metadata.file_name
    except Exception:
        pass

    return None


def __get_conv_user_message(conversations: dict):
    messages = conversations["messages"]
    for item in messages:
        if item["type"] == "human":
            return item["data"]["content"]
    return ""


def __new_conversation(team_mode, user_name: str, sys_code: str) -> ConversationVo:
    unique_id = uuid.uuid1()
    return ConversationVo(
        conv_uid=str(unique_id),
        team_mode=team_mode,
        user_name=user_name,
        sys_code=sys_code,
    )


def get_db_list(user_id: str = None):
    dbs = CFG.local_db_manager.get_db_list(user_id=user_id)
    db_params = []
    for item in dbs:
        params: dict = {}
        params.update({"param": item["db_name"]})
        params.update({"type": item["db_type"]})
        db_params.append(params)
    return db_params


def plugins_select_info():
    plugins_infos: dict = {}
    for plugin in CFG.plugins:
        plugins_infos.update(
            {f"【{plugin._name}】=>{plugin._description}": plugin._name}
        )
    return plugins_infos


def get_db_list_info(user_id: str = None):
    dbs = CFG.local_db_manager.get_db_list(user_id=user_id)
    params: dict = {}
    for item in dbs:
        comment = item["comment"]
        if comment is not None and len(comment) > 0:
            params.update({item["db_name"]: comment})
    return params


def knowledge_list_info():
    """return knowledge space list"""
    # TODO: rewire to new knowledge module (Task #9)
    if KnowledgeSpaceRequest is None or knowledge_service is None:
        return {}
    params: dict = {}
    request = KnowledgeSpaceRequest()
    spaces = knowledge_service.get_knowledge_space(request)
    for space in spaces:
        params.update({space.name: space.desc})
    return params


def knowledge_list(user_id: str = None):
    """return knowledge space list"""
    # TODO: rewire to new knowledge module (Task #9)
    if KnowledgeSpaceRequest is None or knowledge_service is None:
        return []
    request = KnowledgeSpaceRequest(user_id=user_id)
    spaces = knowledge_service.get_knowledge_space(request)
    space_list = []
    for space in spaces:
        params: dict = {}
        params.update({"param": space.name})
        params.update({"type": "space"})
        params.update({"space_id": space.id})
        space_list.append(params)
    return space_list


def get_fs() -> FileStorageClient:
    return FileStorageClient.get_instance(CFG.SYSTEM_APP)


def get_dag_manager() -> DAGManager:
    """Get the global default DAGManager"""
    return DAGManager.get_instance(CFG.SYSTEM_APP)


def get_chat_flow() -> FlowService:
    """Get Chat Flow Service."""
    return FlowService.get_instance(CFG.SYSTEM_APP)


def get_executor() -> Executor:
    """Get the global default executor"""
    return CFG.SYSTEM_APP.get_component(
        ComponentType.EXECUTOR_DEFAULT,
        ExecutorFactory,
        or_register_component=DefaultExecutorFactory,
    ).create()


@router.post("/v1/resource/params/list", response_model=Result[List[dict]])
async def resource_params_list(
    resource_type: str,
    user_token: UserRequest = Depends(get_user_from_headers),
):
    if resource_type == "database":
        result = get_db_list()
    elif resource_type == "knowledge":
        result = knowledge_list()
    elif resource_type == "tool":
        result = plugins_select_info()
    else:
        return Result.succ()
    return Result.succ(result)


@router.post("/v1/resource/file/upload")
async def file_upload(
    chat_mode: str,
    conv_uid: str,
    temperature: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
    sys_code: Optional[str] = None,
    model_name: Optional[str] = None,
    doc_files: List[UploadFile] = File(...),
    user_token: UserRequest = Depends(get_user_from_headers),
    fs: FileStorageClient = Depends(get_fs),
):
    logger.info(
        f"file_upload:{conv_uid}, files:{[file.filename for file in doc_files]}"
    )

    bucket = "gyra_app_file"
    file_params = []

    import mimetypes

    for doc_file in doc_files:
        file_name = doc_file.filename
        custom_metadata = {
            "user_name": user_token.user_id,
            "sys_code": sys_code,
            "conv_uid": conv_uid,
        }

        file_uri = await blocking_func_to_async(
            CFG.SYSTEM_APP,
            fs.save_file,
            bucket,
            file_name,
            doc_file.file,
            custom_metadata=custom_metadata,
        )

        doc_file.file.seek(0, 2)
        file_size = doc_file.file.tell()
        doc_file.file.seek(0)

        _, file_extension = os.path.splitext(file_name)
        mime_type, _ = mimetypes.guess_type(file_name)
        mime_type = mime_type or "application/octet-stream"

        metadata = fs.storage_system.get_file_metadata_by_uri(file_uri)
        file_id = metadata.file_id if metadata else ""

        file_param = {
            "is_oss": True,
            "file_path": file_uri,
            "file_name": file_name,
            "file_size": file_size,
            "file_extension": file_extension,
            "mime_type": mime_type,
            "file_id": file_id,
            "file_learning": False,
            "bucket": bucket,
            "preview_url": fs.get_public_url(file_uri),
        }
        file_params.append(file_param)

    result = file_params[0] if len(file_params) == 1 else file_params
    return Result.succ(result)


@router.post("/v1/resource/file/delete")
async def file_delete(
    conv_uid: str,
    file_key: str,
    user_name: Optional[str] = None,
    sys_code: Optional[str] = None,
    user_token: UserRequest = Depends(get_user_from_headers),
):
    logger.info(f"file_delete:{conv_uid},{file_key}")
    oss_file_client = FileClient()

    return Result.succ(
        await oss_file_client.delete_file(conv_uid=conv_uid, file_key=file_key)
    )


@router.post("/v1/resource/file/read")
async def file_read(
    conv_uid: str,
    file_key: str,
    user_name: Optional[str] = None,
    sys_code: Optional[str] = None,
    user_token: UserRequest = Depends(get_user_from_headers),
):
    logger.info(f"file_read:{conv_uid},{file_key}")
    file_client = FileClient()
    res = await file_client.read_file(conv_uid=conv_uid, file_key=file_key)
    df = pd.read_excel(res, index_col=False)
    return Result.succ(df.to_json(orient="records", date_format="iso", date_unit="s"))


async def get_hist_messages(conv_uid: str, user_name: str = None):
    from gyra_serve.conversation.service.service import Service as ConversationService

    instance: ConversationService = ConversationService.get_instance(CFG.SYSTEM_APP)
    return await instance.get_history_messages(
        {"conv_uid": conv_uid, "user_name": user_name}
    )


@router.post("/v1/chat/stop")
async def chat_stop(
    conv_session_id: str,
    user_token: UserRequest = Depends(get_user_from_headers),
):
    logger.info(f"chat_stop:{conv_session_id}")
    try:
        await multi_agents.stop_chat(
            conv_session_id, user_token.user_id if user_token else None
        )
    except Exception as e:
        logger.exception("停止对话异常！")
        return Result.failed(msg=f"停止对话失败！{str(e)}")


@router.get("/v1/chat/query")
async def chat_query(
    conv_id: str,
    vis_render: Optional[str] = Query(default=None, description="可视化协议名称"),
    user_token: UserRequest = Depends(get_user_from_headers),
):
    """查询会话状态和最终结论

    Args:
        conv_id: Agent会话ID (agent_conv_id)
        vis_render: 可视化协议名称
    """
    logger.info(f"chat_query: {conv_id}")
    from gyra_serve.permissions import can_read_conversation

    if not can_read_conversation(user_token, conv_id, allow_unknown_owner=True):
        return Result.failed(code="E0105", msg="无权访问该会话")
    try:
        result = await multi_agents.query_chat(conv_id=conv_id, vis_render=vis_render)
        if result is None:
            return Result.failed(code="E0103", msg=f"会话 {conv_id} 不存在")

        vis_final, user_answer, current_vis_render, is_final, state, dock = result
        return Result.succ(
            {
                "conv_id": conv_id,
                "state": state,
                "is_final": is_final,
                "vis_final": vis_final,
                "user_answer": user_answer,
                "vis_render": current_vis_render,
                "dock": dock,
            }
        )
    except Exception as e:
        logger.exception("查询会话异常!")
        return Result.failed(code="E0104", msg=f"查询会话失败: {str(e)}")


@router.get("/unified/vis/step_detail")
async def vis_step_detail(
    conv_id: str,
    step_id: str,
    user_token: UserRequest = Depends(get_user_from_headers),
):
    from gyra_serve.permissions import can_read_conversation

    if not can_read_conversation(user_token, conv_id, allow_unknown_owner=True):
        return Result.failed(code="E0105", msg="无权访问该会话")
    """按 step_id 查询单个执行步骤详情。

    vis_manus 布局左侧步骤点击时按需拉取(lazy_loading 模式),返回该步骤的
    active_step / outputs,前端 selectStep 据此切换右侧面板。
    直接返回 step_data(顶层 active_step / outputs),与前端 raw fetch 约定一致。
    """
    logger.info(f"vis_step_detail: conv_id={conv_id}, step_id={step_id}")
    try:
        result = await multi_agents.query_step_detail(conv_id=conv_id, step_uid=step_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"步骤 {step_id} 详情不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("查询步骤详情异常!")
        raise HTTPException(status_code=500, detail=f"查询步骤详情失败: {str(e)}")


def _assemble_scene_resources(ext_info, conv_uid: str):
    """预处理:有 workspace_id 时调场景资源装配器,返回待并入 dynamic_resources 的列表。

    纯函数,便于不起端点单测。仅在 ext_info 携带 workspace_id 时触发装配;
    否则返回 [](对话链路无场景空间资源,行为与未接入时完全一致)。

    注:此处刻意不直接 import gyra.component.CFG(Task 2 已确认该符号不可导入),
    改用文件顶部已建立的 `CFG = Config()`(来自 gyra._private.config.Config),
    与 gyra_serve/config/service/service.py:234 的 `Config().SYSTEM_APP` 同一事实来源。
    SceneResourceAssembler.assemble 内部已捕获一切异常并降级为 [],此处不再兜底。
    """
    ws_id = ext_info.get("workspace_id") if ext_info else None
    if not ws_id:
        return []
    from gyra_serve.workspace.scene_resource_assembler import (
        SceneResourceAssembler,
    )

    return SceneResourceAssembler.assemble(
        CFG.SYSTEM_APP,
        workspace_id=int(ws_id),
        task_id=ext_info.get("task_id"),
        conv_uid=conv_uid,
    )


def _extract_user_text(user_input) -> str:
    """从 user_input 抽取纯文本(支持 str / OpenAI 消息对象 / content blocks)。"""
    if not user_input:
        return ""
    if isinstance(user_input, str):
        return user_input
    # OpenAI 消息对象: {"role": "user", "content": "..."} 或 content blocks 列表
    content = user_input.get("content") if isinstance(user_input, dict) else None
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text", ""))
            elif isinstance(p, str):
                parts.append(p)
        return " ".join(parts)
    return ""


def _maybe_set_initial_title(
    conv_uid: str, workspace_id, task_id, user_input,
) -> Optional[str]:
    """A: 大厅会话(workspace_id 有 / task_id 无)首条消息写入初始标题。

    返回写入的 title(表示这是首条消息,B 应跟进),或 None(非大厅/已有标题/空输入)。
    """
    if not workspace_id or task_id is not None:
        return None
    text = _extract_user_text(user_input).strip()
    if not text:
        return None
    try:
        from gyra_serve.workspace.service.service import (
            WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
        )
        ws_service = CFG.SYSTEM_APP.get_component(
            WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
        )
        # 仅在 title 为空时写入;已有标题(手重命名/B 已生成)不覆盖
        before = ws_service.get_conversation_title(conv_uid)
        if (before or "").strip():
            return None
        return ws_service.set_initial_title_if_empty(conv_uid, text)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[conv_title] A set initial title failed: {e}")
        return None


async def _delayed_generate_llm_title(
    conv_uid: str, user_text: str, previous_title: str,
    max_attempts: int = 10, interval: float = 3.0,
) -> None:
    """B: 轮询等待首轮 AI 回复出现,再调 LLM 生成摘要标题覆盖 A 的初始标题。

    - ASYNC 模式下 Agent 在后台运行,首条 AI 回复延迟写入 chat_history;
      这里轻量轮询(最多 ~30s),拿到回复后生成标题,拿不到则保留 A 的初始标题。
    - 调用 WorkspaceService.generate_title_from_llm,内部仅在 title 仍等于
      previous_title 时覆盖,避免覆盖用户手动重命名。
    """
    from gyra.storage.chat_history.chat_history_db import ChatHistoryMessageDao
    from gyra_serve.workspace.service.service import (
        WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
    )
    try:
        ws_service = CFG.SYSTEM_APP.get_component(
            WORKSPACE_SERVICE_COMPONENT_NAME, WorkspaceService,
        )
    except Exception:  # noqa: BLE001
        return
    dao = ChatHistoryMessageDao()
    ai_reply = None
    for _ in range(max_attempts):
        await asyncio.sleep(interval)
        try:
            items = dao.get_messages_by_conv_uid(conv_uid)
        except Exception:  # noqa: BLE001
            items = None
        if items:
            # 优先取 "ai" 类型消息的文本;其次取 "view" 消息(VIS 内容)
            for item in reversed(items):
                detail = item.message_detail or {}
                msg_type = detail.get("type")
                if msg_type in ("ai", "assistant"):
                    content = detail.get("data", {}).get("content", "")
                    if content and isinstance(content, str):
                        ai_reply = content
                        break
            if not ai_reply:
                for item in reversed(items):
                    detail = item.message_detail or {}
                    if detail.get("type") == "view":
                        content = detail.get("data", {}).get("content", "")
                        if content and isinstance(content, str):
                            ai_reply = content
                            break
            if ai_reply:
                break
    if not ai_reply:
        return
    try:
        await ws_service.generate_title_from_llm(
            conv_uid=conv_uid,
            user_input=user_text,
            ai_reply=ai_reply,
            previous_title=previous_title,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[conv_title] B LLM title generation failed: {e}")


def _format_stream_error_frame(err: Exception) -> str:
    """流式响应中途异常的兜底错误帧:保证前端收到 vis error 事件而非连接裸断,
    已流式内容得以保留,末尾展示错误原因。"""

    error_content = json.dumps(
        {"vis": {"type": "error", "content": f"对话发生错误: {err}"}},
        ensure_ascii=False,
    )
    return f"data:{error_content}\n\n"


async def _stream_error_frames(err: Exception):
    """流式异常兜底帧序列：先发 vis error 帧,再补发 [DONE]。

    若只发 error 帧而不发 [DONE],前端会因未收到 [DONE] 而把连接关闭当成
    「服务端流提前中断」(onStreamDrop),覆盖掉具体错误文案,导致页面看不到真实报错。
    补发 [DONE] 后前端视为正常收尾(onDone),onError 里的具体错误得以保留。
    """
    yield _format_stream_error_frame(err)
    yield f"data:{json.dumps({'vis': '[DONE]'}, ensure_ascii=False)}\n\n"


def _derive_fallback_conv_uid(dialogue: "ConversationVo") -> str:
    """缺省 conv_uid 时派生跨轮稳定的会话 ID（修复多轮追问会话断裂）。

    根因：此前缺省时每次 ``uuid.uuid1().hex`` 生成新 ID，前端未传 conv_uid 的
    调用方（如 /chat 页面首次对话、纯 API 调用）每轮都是全新会话，V2/V1 事件
    日志与历史按不同 conv 隔离，追问丢失上下文。

    派生优先级（从请求已有稳定上下文提取，无状态请求间可复用）：
    1. ``ext_info.workspace_id + task_id`` → ``ws-{wsid}-task-{taskid}``
       （任务维度，同一任务下多轮稳定）；
    2. ``ext_info.workspace_id`` → ``ws-{wsid}-default``（空间维度，工作台多轮共享）；
    3. 否则 → ``uuid.uuid1().hex``（无 workspace 的一次性请求，保持原行为；
       多轮场景应由调用方持有会话 ID，前端已从 SSE metadata 帧回填）。
    """
    try:
        ext = dialogue.ext_info or {}
        ws_id = ext.get("workspace_id")
        task_id = ext.get("task_id")
        if ws_id is not None and task_id is not None:
            return f"ws-{ws_id}-task-{task_id}"
        if ws_id is not None:
            return f"ws-{ws_id}-default"
    except Exception:  # noqa: BLE001
        pass
    return uuid.uuid1().hex


@router.post("/v1/chat/completions")
async def chat_completions(
    background_tasks: BackgroundTasks,
    dialogue: ConversationVo = Body(),
    user_token: UserRequest = Depends(require_permission("agent", "chat")),
):
    logger.info(
        f"chat_completions:{dialogue.team_mode},{dialogue.select_param},"
        f"{dialogue.model_name}, work_mode={dialogue.work_mode}, timestamp={int(time.time() * 1000)}"
    )
    if not dialogue.conv_uid:
        dialogue.conv_uid = _derive_fallback_conv_uid(dialogue)

    # Adapt OpenAI messages format to user_input
    if not dialogue.user_input and dialogue.messages:
        try:
            last_message = next(
                (
                    msg
                    for msg in reversed(dialogue.messages)
                    if msg.get("role") == "user"
                ),
                None,
            )
            if last_message:
                dialogue.user_input = last_message.get("content", "")
                logger.info(
                    f"Extracted user_input from messages: {dialogue.user_input}"
                )
        except Exception as e:
            logger.warning(f"Failed to extract user_input from messages: {e}")

    dialogue.user_name = user_token.user_id if user_token else dialogue.user_name
    dialogue.ext_info.update(
        {
            "trace_id": first(
                root_tracer.get_context_trace_id(), default=uuid.uuid4().hex
            )
        }
    )
    dialogue.ext_info.update({"rpc_id": "0.1"})
    # 透传用户上下文到 agent_context.extra，供执行层 RBAC 权限检查使用
    dialogue.ext_info["user_request"] = user_token

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Transfer-Encoding": "chunked",
    }
    try:
        dialogue.ext_info.update({"model_name": dialogue.model_name})
        dialogue.ext_info.update({"incremental": dialogue.incremental})
        dialogue.ext_info.update({"temperature": dialogue.temperature})
        dialogue.ext_info.update({"max_new_tokens": dialogue.max_new_tokens})

        # 回合前路由:页面输入命中剧本 -> 预建会话内任务(注入 task_id)。
        # 之后装配器据 task_id 走 workbench(PlaybookResource + 物化能力注入当前对话),
        # 主 Agent 在当前对话同步执行,任务列表可见、交付进空间。其余发起(API/定时/
        # 订阅/显式异步)不经此路由,由 start_task/fire_trigger/cron 各自建任务后台执行。
        try:
            from gyra_serve.workspace.scene_router import route_scene_execution

            route_scene_execution(
                dialogue.ext_info,
                dialogue.user_input,
                dialogue.conv_uid,
                CFG.SYSTEM_APP,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[scene_router] pre-round routing failed: {e}")

        # 预处理:场景空间资源装配(agent 通用骨架不感知,此处为场景业务)
        scene_res = _assemble_scene_resources(dialogue.ext_info, dialogue.conv_uid)
        if scene_res:
            existing_dyn = dialogue.ext_info.get("dynamic_resources") or []
            existing_dyn.extend(scene_res)
            dialogue.ext_info["dynamic_resources"] = existing_dyn

        in_message = HumanMessage.parse_chat_completion_message(
            dialogue.user_input, ignore_unknown_media=True
        )

        # 方案 C - A: 大厅会话首条消息写入初始标题(用户输入截断);
        # B: 若 A 写入了标题,后台延迟调 LLM 生成摘要标题覆盖。
        _ws_id = dialogue.ext_info.get("workspace_id")
        _task_id = dialogue.ext_info.get("task_id")
        _initial_title = _maybe_set_initial_title(
            dialogue.conv_uid, _ws_id, _task_id, dialogue.user_input,
        )
        if _initial_title:
            _user_text = _extract_user_text(dialogue.user_input)
            asyncio.create_task(_delayed_generate_llm_title(
                conv_uid=dialogue.conv_uid,
                user_text=_user_text,
                previous_title=_initial_title,
            ))

        # 处理文件输入：提取文件引用并增强消息
        sandbox_file_refs = []
        if in_message.has_media:
            try:
                from gyra_serve.agent.file_io import (
                    process_chat_input_files,
                    build_enhanced_query_with_files,
                    SandboxFileRef,
                )

                # 获取 FileStorageClient 实例（用于从 gyra-fs metadata 还原原始文件名）
                fs = None
                try:
                    fs = FileStorageClient.get_instance(CFG.SYSTEM_APP, default_component=None)
                except Exception:
                    pass

                user_inputs = []
                if isinstance(in_message.content, list):
                    for media in in_message.content:
                        if hasattr(media, "type") and hasattr(media, "object"):
                            if media.type == "image" and media.object.format.startswith(
                                "url"
                            ):
                                url_str = str(media.object.data)
                                file_name = _get_file_name_from_url_or_metadata(
                                    url_str, fs
                                )
                                if not file_name:
                                    # 不伪造 .jpg 扩展名:无扩展名时下游守卫会按
                                    # "无法确认为图片" 判定,降级走沙箱,而非硬塞模型。
                                    file_name = f"image_{uuid.uuid4().hex[:8]}"

                                user_inputs.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": url_str,
                                            "file_name": file_name,
                                        },
                                    }
                                )
                            elif (
                                media.type == "file"
                                and media.object.format.startswith("url")
                            ):
                                url_str = str(media.object.data)
                                file_name = _get_file_name_from_url_or_metadata(
                                    url_str, fs
                                )
                                if not file_name:
                                    file_name = f"file_{uuid.uuid4().hex[:8]}"

                                user_inputs.append(
                                    {
                                        "type": "file_url",
                                        "file_url": {
                                            "url": url_str,
                                            "file_name": file_name,
                                        },
                                    }
                                )
                            elif (
                                media.type == "audio"
                                and media.object.format.startswith("url")
                            ):
                                url_str = str(media.object.data)
                                file_name = _get_file_name_from_url_or_metadata(
                                    url_str, fs
                                )
                                if not file_name:
                                    file_name = f"audio_{uuid.uuid4().hex[:8]}"

                                user_inputs.append(
                                    {
                                        "type": "audio_url",
                                        "audio_url": {
                                            "url": url_str,
                                            "file_name": file_name,
                                        },
                                    }
                                )
                            elif (
                                media.type == "video"
                                and media.object.format.startswith("url")
                            ):
                                url_str = str(media.object.data)
                                file_name = _get_file_name_from_url_or_metadata(
                                    url_str, fs
                                )
                                if not file_name:
                                    file_name = f"video_{uuid.uuid4().hex[:8]}"

                                user_inputs.append(
                                    {
                                        "type": "video_url",
                                        "video_url": {
                                            "url": url_str,
                                            "file_name": file_name,
                                        },
                                    }
                                )

                if user_inputs:
                    # 按当前 agent 模型能力 + 是否多媒体 agent 统一分流
                    try:
                        from gyra_serve.agent.file_io.file_type_config import (
                            is_multimedia_agent,
                            resolve_model_capabilities,
                        )

                        _caps = resolve_model_capabilities(dialogue.model_name)
                        _prefer_direct_media = is_multimedia_agent(
                            app_code=dialogue.app_code
                        )
                    except Exception:
                        _caps, _prefer_direct_media = [], False

                    result = await process_chat_input_files(
                        user_inputs=user_inputs,
                        sandbox=None,
                        conv_id=dialogue.conv_uid,
                        capabilities=_caps,
                        prefer_direct_media=_prefer_direct_media,
                    )
                    sandbox_file_refs = result.sandbox_file_refs
                    # 模型有能力直接消费的多媒体内容（image_url/audio/video）透传给
                    # agent_chat 合并进用户消息，实现"支持则直接消费"。
                    if result.multimodal_contents:
                        dialogue.ext_info["multimodal_contents"] = (
                            result.multimodal_contents
                        )
                    logger.info(
                        f"[v1/chat] Processed {len(sandbox_file_refs)} sandbox files, "
                        f"{len(result.multimodal_contents)} multimodal contents from user input"
                    )
                    # 打印 sandbox_file_refs 的详细信息
                    for i, ref in enumerate(sandbox_file_refs):
                        ref_dict = ref.to_dict() if hasattr(ref, "to_dict") else ref
                        logger.info(
                            f"[v1/chat] File {i}: file_name={ref_dict.get('file_name')}, "
                            f"url={ref_dict.get('url', '')[:80] if ref_dict.get('url') else 'None'}..."
                        )

                    # 注意：不在 API 层构建带路径的消息
                    # 文件路径将在 sandbox 创建后由 agent_chat.py 正确处理
                    # 只传递 sandbox_file_refs 到 ext_info

            except ImportError:
                logger.warning("[v1/chat] file_io module not available")
            except Exception as e:
                logger.warning(f"[v1/chat] Failed to process files: {e}")

        # 将 sandbox_file_refs 传递到 ext_info
        if sandbox_file_refs:
            dialogue.ext_info["sandbox_file_refs"] = [
                ref.to_dict() if hasattr(ref, "to_dict") else ref
                for ref in sandbox_file_refs
            ]

        work_mode = dialogue.work_mode or WorkMode.ASYNC

        if work_mode == WorkMode.QUICK:

            async def chat_wrapper():
                try:
                    async for chunk, agent_conv_id in multi_agents.quick_app_chat(
                        conv_session_id=dialogue.conv_uid,
                        user_query=in_message,
                        chat_in_params=dialogue.chat_in_params,
                        app_code=dialogue.app_code,
                        user_code=dialogue.user_name,
                        sys_code=dialogue.sys_code,
                        **dialogue.ext_info,
                    ):
                        yield chunk
                except Exception as e:
                    logger.exception("chat stream error(quick)!")
                    async for frame in _stream_error_frames(e):
                        yield frame
                    return

            return StreamingResponse(
                chat_wrapper(),
                headers=headers,
                media_type="text/event-stream",
            )
        elif work_mode == WorkMode.BACKGROUND:

            async def chat_wrapper():
                try:
                    async for chunk, agent_conv_id in multi_agents.app_chat_v2(
                        conv_uid=dialogue.conv_uid,
                        background_tasks=background_tasks,
                        gpts_name=dialogue.app_code,
                        specify_config_code=dialogue.app_config_code,
                        user_query=in_message,
                        user_code=dialogue.user_name,
                        sys_code=dialogue.sys_code,
                        chat_in_params=dialogue.chat_in_params,
                        **dialogue.ext_info,
                    ):
                        yield chunk
                except Exception as e:
                    logger.exception("chat stream error(background)!")
                    async for frame in _stream_error_frames(e):
                        yield frame
                    return

            return StreamingResponse(
                chat_wrapper(),
                headers=headers,
                media_type="text/event-stream",
            )
        elif work_mode == WorkMode.ASYNC:
            result = await multi_agents.app_chat_v3(
                conv_uid=dialogue.conv_uid,
                background_tasks=background_tasks,
                gpts_name=dialogue.app_code,
                specify_config_code=dialogue.app_config_code,
                user_query=in_message,
                user_code=dialogue.user_name,
                sys_code=dialogue.sys_code,
                chat_in_params=dialogue.chat_in_params,
                **dialogue.ext_info,
            )
            agent_conv_id = result[1] if result else None
            return Result.succ(data={"conv_id": agent_conv_id})
        else:

            async def chat_wrapper():
                try:
                    async for chunk, agent_conv_id in multi_agents.app_chat(
                        conv_uid=dialogue.conv_uid,
                        gpts_name=dialogue.app_code,
                        specify_config_code=dialogue.app_config_code,
                        user_query=in_message,
                        user_code=dialogue.user_name,
                        sys_code=dialogue.sys_code,
                        chat_in_params=dialogue.chat_in_params,
                        **dialogue.ext_info,
                    ):
                        yield chunk
                except Exception as e:
                    logger.exception("chat stream error(default)!")
                    async for frame in _stream_error_frames(e):
                        yield frame
                    return

            return StreamingResponse(
                chat_wrapper(),
                headers=headers,
                media_type="text/event-stream",
            )

    except Exception as e:
        logger.exception(f"Chat Exception!{dialogue}", e)

        async def error_text(err_msg):
            async for frame in _stream_error_frames(e):
                yield frame

        return StreamingResponse(
            error_text(str(e)),
            headers=headers,
            media_type="text/event-stream",
        )
    finally:
        if dialogue.user_name is not None and dialogue.app_code is not None:
            user_recent_app_dao.upsert(
                user_code=dialogue.user_name,
                sys_code=dialogue.sys_code,
                app_code=dialogue.app_code,
            )


@router.post("/v1/chat/topic/terminate")
async def terminate_topic(
    conv_id: str,
    round_index: int,
    user_token: UserRequest = Depends(get_user_from_headers),
):
    logger.info(f"terminate_topic:{conv_id},{round_index}")
    try:
        from gyra_serve.agent.agents.controller import multi_agents

        return Result.succ(await multi_agents.topic_terminate(conv_id))
    except Exception as e:
        logger.exception("Topic terminate error!")
        return Result.failed(code="E0102", msg=str(e))


@router.get("/v1/model/types")
async def model_types():
    """Return LLM model names configured in AppConfig.agent_llm.

    The old controller.get_all_instances() fallback has been removed; this
    endpoint now reads only from the agent.llm config (synced from
    AppConfig.agent_llm via /api/v1/config/* endpoints).
    """
    logger.info("/v1/model/types")
    try:
        types = set()

        # 数据库优先（分布式共享）：模型/LLM 配置以数据库为准，避免只读启动时加载的
        # 内存配置导致新增 provider 不生效。有记录时直接返回，否则回退到内存配置。
        try:
            from gyra_app.config_storage.agent_llm_db_storage import (
                load_agent_llm_model_names,
            )

            db_names = load_agent_llm_model_names()
            if db_names:
                return Result.succ(db_names)
        except Exception:
            pass

        system_app = SystemApp.get_instance()
        if system_app and system_app.config:
            # PRIORITY 1: app_config from configs dict (JSON config source).
            app_config = system_app.config.configs.get("app_config")
            agent_llm_conf = None

            if app_config:
                agent_llm_attr = getattr(app_config, "agent_llm", None)
                if agent_llm_attr:
                    agent_llm_dict = (
                        agent_llm_attr.model_dump(mode="json")
                        if hasattr(agent_llm_attr, "model_dump")
                        else dict(agent_llm_attr)
                    )
                    if "providers" in agent_llm_dict:
                        providers = agent_llm_dict.pop("providers")
                        if isinstance(providers, list):
                            converted = []
                            for p in providers:
                                if isinstance(p, dict):
                                    cp = dict(p)
                                    if "models" in cp:
                                        cp["model"] = cp.pop("models")
                                    converted.append(cp)
                            agent_llm_dict["provider"] = converted
                    agent_llm_conf = agent_llm_dict

            # PRIORITY 2: TOML "agent.llm" direct key.
            if not agent_llm_conf:
                agent_llm_conf = system_app.config.get("agent.llm")

            # PRIORITY 3: nested "agent" -> "llm".
            if not agent_llm_conf:
                agent_conf = system_app.config.get("agent")
                if isinstance(agent_conf, dict):
                    agent_llm_conf = agent_conf.get("llm")

            # PRIORITY 4: flattened keys.
            if not agent_llm_conf:
                flattened = system_app.config.get_all_by_prefix("agent.llm.")
                if flattened:
                    agent_llm_conf = {}
                    prefix_len = len("agent.llm.")
                    for k, v in flattened.items():
                        agent_llm_conf[k[prefix_len:]] = v

            # Parse models from Multi-Provider List Structure [[agent.llm.provider]]
            if agent_llm_conf and isinstance(agent_llm_conf.get("provider"), list):
                for p_conf in agent_llm_conf.get("provider"):
                    if isinstance(p_conf, dict) and "model" in p_conf:
                        p_models = p_conf.get("model")
                        if isinstance(p_models, list):
                            p_defaults = {
                                k: v for k, v in p_conf.items() if k not in ("model", "models")
                            }
                            for m in p_models:
                                if isinstance(m, dict) and "name" in m:
                                    # 排除媒体生成模型（图片/视频/音频），聊天只选文本/视觉 LLM
                                    try:
                                        from gyra.agent.util.llm.model_config_cache import (
                                            is_media_model_config,
                                        )

                                        merged = dict(p_defaults)
                                        merged.update(m)
                                        if is_media_model_config(merged):
                                            continue
                                    except Exception:
                                        pass
                                    types.add(m.get("name"))

        return Result.succ(list(types))

    except Exception as e:
        return Result.failed(code="E000X", msg=f"controller model types error {e}")


@router.get("/v1/test")
async def test():
    return "service status is UP"


async def flow_stream_generator(func, incremental: bool, model_name: str):
    stream_id = f"chatcmpl-{str(uuid.uuid1())}"
    previous_response = ""
    async for chunk in func:
        if chunk:
            msg = chunk.replace("\ufffd", "")
            if incremental:
                incremental_output = msg[len(previous_response) :]
                choice_data = ChatCompletionResponseStreamChoice(
                    index=0,
                    delta=DeltaMessage(role="assistant", content=incremental_output),
                )
                chunk = ChatCompletionStreamResponse(
                    id=stream_id, choices=[choice_data], model=model_name
                )
                _content = json.dumps(
                    chunk.dict(exclude_unset=True), ensure_ascii=False
                )
                yield f"data: {_content}\n\n"
            else:
                # TODO generate an openai-compatible streaming responses
                msg = msg.replace("\n", "\\n")
                yield f"data:{msg}\n\n"
            previous_response = msg
    if incremental:
        yield "data: [DONE]\n\n"


async def no_stream_generator(chat):
    with root_tracer.start_span("no_stream_generator"):
        msg = await chat.nostream_call()
        yield f"data: {msg}\n\n"


async def stream_generator(
    chat,
    incremental: bool,
    model_name: str,
    text_output: bool = True,
    openai_format: bool = False,
    conv_uid: str = None,
):
    """Generate streaming responses

    Our goal is to generate an openai-compatible streaming responses.
    Currently, the incremental response is compatible, and the full response will be
    transformed in the future.

    Args:
        chat (BaseChat): Chat instance.
        incremental (bool): Used to control whether the content is returned
            incrementally or in full each time.
        model_name (str): The model name

    Yields:
        _type_: streaming responses
    """
    span = root_tracer.start_span("stream_generator")
    msg = "[LLM_ERROR]: llm server has no output, maybe your prompt template is wrong."

    stream_id = conv_uid or f"chatcmpl-{str(uuid.uuid1())}"
    try:
        if incremental and not openai_format:
            raise ValueError("Incremental response must be openai-compatible format.")
        async for chunk in chat.stream_call(
            text_output=text_output, incremental=incremental
        ):
            if not chunk:
                await asyncio.sleep(0.02)
                continue

            if openai_format:
                # Must be ModelOutput
                output: ModelOutput = cast(ModelOutput, chunk)
                text = None
                think_text = None
                if output.has_text:
                    text = output.text
                if output.has_thinking:
                    think_text = output.thinking_text
                if incremental:
                    choice_data = ChatCompletionResponseStreamChoice(
                        index=0,
                        delta=DeltaMessage(
                            role="assistant", content=text, reasoning_content=think_text
                        ),
                    )
                    chunk = ChatCompletionStreamResponse(
                        id=stream_id, choices=[choice_data], model=model_name
                    )
                    _content = json.dumps(
                        chunk.dict(exclude_unset=True), ensure_ascii=False
                    )
                    yield f"data: {_content}\n\n"
                else:
                    choice_data = ChatCompletionResponseChoice(
                        index=0,
                        message=ChatMessage(
                            role="assistant",
                            content=output.text,
                            reasoning_content=output.thinking_text,
                        ),
                    )
                    if output.usage:
                        usage = UsageInfo(**output.usage)
                    else:
                        usage = UsageInfo()
                    _content = ChatCompletionResponse(
                        id=stream_id,
                        choices=[choice_data],
                        model=model_name,
                        usage=usage,
                    )
                    _content = json.dumps(
                        chunk.dict(exclude_unset=True), ensure_ascii=False
                    )
                    yield f"data: {_content}\n\n"
            else:
                msg = chunk.replace("\ufffd", "")
                msg = msg.replace("\n", "\\n")
                yield f"data:{msg}\n\n"
            await asyncio.sleep(0.02)
        if incremental:
            yield "data: [DONE]\n\n"
        span.end()
    except Exception as e:
        logger.exception("stream_generator error")
        yield f"data: [SERVER_ERROR]{str(e)}\n\n"
        if incremental:
            yield "data: [DONE]\n\n"


def message2Vo(message: dict, order, model_name) -> MessageVo:
    return MessageVo(
        role=message["type"],
        context=message["data"]["content"],
        order=order,
        model_name=model_name,
    )


from .config_api import router as config_router
from .tools_api import router as tools_router
from .auth_api import router as auth_router
from .users_api import router as users_router

router.include_router(config_router, prefix="/v1", tags=["Config"])
router.include_router(tools_router, prefix="/v1", tags=["Tools"])
router.include_router(auth_router, prefix="/v1", tags=["Auth"])
router.include_router(users_router, prefix="/v1", tags=["Users"])
