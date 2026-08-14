import asyncio
import json
import logging
import os
import traceback
import uuid
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Type, Union

import httpx
import orjson
from fastapi import BackgroundTasks

from gyra import BaseComponent
from gyra._private.config import Config
from gyra.agent import (
    AgentMemory,
    ConversableAgent,
    get_agent_manager,
    AgentContext,
    UserProxyAgent,
    LLMStrategyType,
    GptsMemory,
    LLMConfig,
    ActionOutput,
    Agent,
    AgentMessage,
    ProfileConfig,
    ShortTermMemory,
)
from gyra.agent.core.agent_alias import AgentAliasManager, resolve_agent_name
from gyra.agent.core.memory.gpts import GptsMessage
from gyra.agent.core.plan.react.team_react_plan import AutoTeamContext
from gyra.agent.core.sandbox_manager import SandboxManager
from gyra.agent.core.step_state_guard import validate_session_transition
from gyra.agent.core.schema import Status
from gyra.agent.resource import get_resource_manager, ResourceManager
from gyra.agent.resource.agent_skills import AgentSkillResource
from gyra.agent.resource.base import FILE_RESOURCES, AgentResource
from gyra.agent.util.ext_config import ExtConfigHolder
from gyra_serve.agent.resource.tool.memory_tool import MemoryToolPack
from gyra.component import ComponentType, SystemApp
from gyra.sandbox import AutoSandbox
from gyra_app.config import SandboxConfigParameters
from gyra_serve.agent.resource import GyraSkillResource
from gyra_serve.schedule.local_scheduler import LocalScheduler
from gyra.core.interface.scheduler import Scheduler
from gyra.core import HumanMessage, StorageConversation
from gyra.core.interface.file import FileStorageClient
from gyra.util.data_util import first
from gyra.util.date_utils import current_ms
from gyra.util.executor_utils import ExecutorFactory, execute_no_wait
from gyra.util.json_utils import serialize
from gyra.util.log_util import CHAT_LOGGER
from gyra.util.logger import digest
from gyra.util.tracer.tracer_impl import root_tracer, trace
from gyra.vis import VisProtocolConverter
from gyra.vis.vis_manage import get_vis_manager
from gyra_serve.core import blocking_func_to_async
from gyra_serve.agent.agents.gyras_memory import (
    MetaGyrasPlansMemory,
    MetaGyrasMessageMemory,
    MetaAgentSystemMessageMemory,
    MetaGyrasWorkLogStorage,
    MetaGyrasKanbanStorage,
    MetaGyrasTodoStorage,
    MetaGyrasFileMetadataStorage,
)
from gyra_serve.agent.db import (
    GptsConversationsEntity,
    GptsConversationsDao,
    GptsMessagesDao,
)
from gyra_serve.agent.db.gpts_tool import GptsToolDao
from gyra_serve.agent.team.base import TeamMode
from gyra_serve.building.app.api.schema_app import GptsApp
from gyra_serve.building.app.api.schemas import ServerResponse
from gyra_serve.building.app.service.service import Service as AppService
from gyra_serve.building.config.api.schemas import ChatInParamValue, AppParamType
from gyra_serve.conversation.serve import Serve as ConversationServe
from gyra_serve.workspace.agent_tools.context_builder import (
    build_workspace_context,
    render_workspace_context_summary,
)
from gyra_serve.workspace.agent_prompts import render_scene_dynamic_context
from gyra_serve.workspace.context_builder import (
    build_workspace_context as _legacy_build_workspace_context,
)

logger = logging.getLogger(__name__)

# Mapping from legacy client-side resource type names to their
# ResourceManager-registered aliases.  Old clients may send
# sub_type='database' but DatasourceResource is registered as 'datasource'.
_RESOURCE_TYPE_ALIASES: Dict[str, str] = {
    "database": "datasource",
}

CFG = Config()


def _get_web_config(app_config: Any) -> Any:
    """获取 web 配置，兼容两种 config 结构。

    - ApplicationConfig (gyra_app): ``app_config.service.web``
    - AppConfig (gyra_core): ``app_config.web``
    """
    if app_config is None:
        return None
    service = getattr(app_config, "service", None)
    if service is not None:
        return getattr(service, "web", None)
    return getattr(app_config, "web", None)


def get_app_service() -> AppService:
    return AppService.get_instance(CFG.SYSTEM_APP)


def _serialize_extra_for_db(extra: Dict[str, Any]) -> str:
    """Serialize ext_info for persistence, excluding non-serializable agents.

    extra_agents contains pre-built ConversableAgent instances which cannot be
    JSON-serialized and are rebuilt on each chat request, so they are omitted.
    Pydantic models (e.g. AgentResource) and dataclasses are converted to dicts.
    """
    from dataclasses import asdict, is_dataclass

    from gyra._private.pydantic import BaseModel, model_to_dict

    def _default(obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return model_to_dict(obj)
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        return serialize(obj)

    return orjson.dumps(
        {k: v for k, v in extra.items() if k != "extra_agents"},
        default=_default,
    ).decode()


def _merge_scene_dynamic_context(gpt_app: GptsApp, ext_info: Dict[str, Any]) -> None:
    """Append runtime workspace context to a custom app system prompt template.

    For apps with a custom system_prompt_template (e.g. scene-workspace-agent),
    append the runtime workspace context so the identity layer is complete.
    """
    system_prompt = ext_info.get("system_prompt")
    if system_prompt and gpt_app.system_prompt_template:
        gpt_app.system_prompt_template = (
            f"{gpt_app.system_prompt_template}\n\n{system_prompt}"
        )


def _inject_workspace_context(
    *,
    system_app,
    workspace_id: Optional[int],
    user_id: Optional[str],
    conv_uid: Optional[str],
    task_id: Optional[int],
    focus_artifact_id: Optional[int] = None,
    system_prompt: List[str],
    extra_agents: List,
    ext_info: Optional[Dict[str, Any]] = None,
    llm_config: Optional[LLMConfig] = None,
    event_queue: Optional[asyncio.Queue] = None,
    app_code: Optional[str] = None,
) -> None:
    """把 workspace 上下文摘要注入对话 system_prompt，并合并物化资源到 ext_info。

    保留旧的 workspace_context dict + 物化资源注入，保证下游 context_loaded
    事件和动态资源消费继续工作。场景工具/剧本资源走资源协议正道，在 chat
    端点装配阶段注入；此处不再构造 toolkit agent，extra_agents 保持为空。
    """
    if not workspace_id:
        return
    mode = "workbench" if task_id else "lobby"
    try:
        if ext_info is not None:
            ws_ctx_legacy = _legacy_build_workspace_context(
                system_app,
                int(workspace_id),
                task_id=int(task_id) if task_id else None,
            )
            ext_info["workspace_context"] = ws_ctx_legacy
            materialized = ws_ctx_legacy.get("materialized") or {}
            existing_dyn = ext_info.get("dynamic_resources") or []
            existing_dyn.extend(materialized.get("dynamic_resources") or [])
            ext_info["dynamic_resources"] = existing_dyn

            existing_extra = ext_info.get("extra_agents")
            if existing_extra is None:
                existing_extra = []
                ext_info["extra_agents"] = existing_extra
            existing_extra.extend(materialized.get("extra_agents") or [])

        ctx = build_workspace_context(
            system_app=system_app,
            workspace_id=int(workspace_id),
            user_id=user_id,
            task_id=int(task_id) if task_id else None,
            focus_artifact_id=focus_artifact_id,
            mode=mode,
        )
        summary = render_workspace_context_summary(ctx, mode=mode)
        if summary:
            system_prompt.append(summary)

        if app_code == "scene-workspace-agent":
            scene_dynamic = render_scene_dynamic_context(ctx, mode=mode)
            if scene_dynamic:
                system_prompt.append(scene_dynamic)

        # NOTE: Scene tools/resources now flow via the resource-protocol path
        # (WorkspaceSceneResource TOOLS slot + factories) assembled pre-chat in
        # the chat_completions endpoint. The old toolkit-injection segment that
        # built a WorkspaceControlAgent with a None agent_context and appended
        # it to extra_agents (causing the agent_to_resource crash) has been
        # removed. extra_agents must stay empty so the main-agent-build
        # else-branch handles SINGLE_AGENT.
    except Exception:
        logger.warning("workspace context injection failed", exc_info=True)


# workspace 流式事件白名单
WORKSPACE_EVENT_TYPES = frozenset(
    {
        "task_created",
        "context_loaded",
        "intervention_triggered",
        "artifact_produced",
        "delivery_sent",
        "asset_referenced",
        "inbox_created",
        "inbox_resolved",
    }
)


def format_workspace_event(event_type: str, payload: dict) -> str:
    """格式化 workspace 结构化事件为 SSE chunk。

    与现有 vis.type=metadata/interrupt/error 同协议，前端 use-chat.ts 白名单 fast-return。

    未知事件类型记录 warning 并返回空串，避免破坏 SSE 流。
    """
    if event_type not in WORKSPACE_EVENT_TYPES:
        logger.warning(
            f"unsupported workspace event type: {event_type}, skipping"
        )
        return ""
    body = orjson.dumps({"vis": {"type": event_type, "payload": payload}})
    return f"data:{body.decode()}\n\n"


def _format_vis_msg(msg: str):
    content = json.dumps({"vis": msg}, default=serialize, ensure_ascii=False)
    return f"data:{content} \n"


def _serialize_stream_chunk(chunk: Any) -> str:
    """把通道里读到的 chunk 序列化成 SSE data 帧。

    - dock 帧（dict 且含 "dock" 键）：已是顶层 `{"dock": ...}` 信封，按原样输出，
      不再包一层 `{"vis": ...}`（Composer Dock 协议）。
    - 其余 chunk：包成 `{"vis": ...}` 信封（对话流渲染，保持原逻辑）。
    """
    if isinstance(chunk, dict) and "dock" in chunk:
        return orjson.dumps(chunk).decode("utf-8")
    return orjson.dumps({"vis": chunk}).decode("utf-8")


async def _register_memory_curator_cron(system_app: Any, space_slug: str) -> None:
    """幂等注册 idle memory curator cron job（每天凌晨 3 点）。

    job_id 固定为 `memory-curator-{space_slug}`，重复调用时若 job 已存在则跳过。
    cron job 触发时派发 MemoryCurateAgent，message 为 `curate:{space_slug}`，
    agent 在 _run_memory_task 里识别该前缀走 curate_space 全量整理路径。

    注意：`cron.get_job` / `cron.add_job` 都是 async def，必须 await；早年缺 await
    会让 `get_job` 返回未启动的 coroutine（非 None），命中幂等早退分支，导致定时
    任务永不注册、且无任何日志（既不成功也不报错）。
    """
    try:
        from gyra_serve.cron.config import SERVE_SERVICE_COMPONENT_NAME
        from gyra_serve.cron.service.service import Service as CronService
        from gyra.cron.types import (
            CronJobCreate,
            CronPayload,
            CronSchedule,
            PayloadKind,
            ScheduleKind,
            SessionMode,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[AgentChat] cron modules unavailable, skip curator cron: {e}"
        )
        return

    try:
        cron = system_app.get_component(SERVE_SERVICE_COMPONENT_NAME, CronService)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[AgentChat] cron service unavailable for slug={space_slug}: {e}"
        )
        return

    job_id = f"memory-curator-{space_slug}"
    try:
        existing = await cron.get_job(job_id)
        if existing is not None:
            return
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[AgentChat] curator cron get_job failed for {job_id}, "
            f"will attempt add: {e}"
        )

    await cron.add_job(
        CronJobCreate(
            id=job_id,
            name=f"Memory Curator for {space_slug}",
            description="Daily idle curator: L1 umbrella merge + classification + backup",
            enabled=True,
            schedule=CronSchedule(
                kind=ScheduleKind.CRON, expr="0 3 * * *", tz="Asia/Shanghai"
            ),
            payload=CronPayload(
                kind=PayloadKind.AGENT_TURN,
                message=f"curate:{space_slug}",
                agent_id="MemoryCurateAgent",
                session_mode=SessionMode.ISOLATED,
                timeout_seconds=1800,
            ),
        )
    )
    logger.info(
        f"[AgentChat] registered memory curator cron job_id={job_id} (0 3 * * *)"
    )


async def _build_conversation(
    conv_id: str,
    select_param: Union[str, Dict[str, Any]],
    model_name: str,
    summary: str,
    app_code: str,
    conv_serve: ConversationServe,
    user_name: Optional[str] = "",
    sys_code: Optional[str] = "",
) -> StorageConversation:
    return await StorageConversation(
        conv_uid=conv_id,
        chat_mode="chat_agent",
        user_name=user_name,
        sys_code=sys_code,
        model_name=model_name,
        summary=summary,
        param_type="gyras",
        param_value=select_param,
        app_code=app_code,
        conv_storage=conv_serve.conv_storage,
        message_storage=conv_serve.message_storage,
        async_load=True,
    ).async_load()


# 使用类型别名简化复杂类型注解
AgentContextType = Union[str, AutoTeamContext]


def _sandbox_key(
    workspace_id: Optional[Any],
    conv_id: Optional[str],
    staff_no: Optional[str],
) -> str:
    """构造沙箱 cache key：workspace_id 优先（同 workspace 主子 agent 共用沙箱，P2），
    无 workspace_id 时回退 conv_id（普通会话独占沙箱）。

    workspace 维度的沙箱用 ``ws:`` 前缀 key，_cleanup_sandbox_manager 仍用 conv 维度
    key（无 workspace_id），故 workspace 会话 cleanup 找不到 -> 共享沙箱常驻至进程退出，
    避免误杀仍在运行的子 agent。
    """
    sn = staff_no or "default"
    if workspace_id:
        return f"ws:{workspace_id}:{sn}"
    return f"{conv_id}_{sn}"


class GlobalSandboxManagerCache:
    """全局沙箱管理器缓存，用于同一会话内共享 sandbox_manager"""

    _repository: Dict[str, SandboxManager] = {}
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def get_lock(cls) -> asyncio.Lock:
        """获取锁，延迟初始化"""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    def get(cls, key: str) -> Optional[SandboxManager]:
        """获取沙箱管理器"""
        return cls._repository.get(key)

    @classmethod
    async def get_or_create(
        cls, key: str, creator: Callable[[], Awaitable[SandboxManager]]
    ) -> SandboxManager:
        """获取或创建沙箱管理器"""
        async with cls.get_lock():
            if key in cls._repository:
                return cls._repository[key]
            sandbox_manager = await creator()
            cls._repository[key] = sandbox_manager
            logger.info(
                f"[Sandbox]创建新sandbox，key={key}, 当前运行中沙箱数量={len(cls._repository)}"
            )
            return sandbox_manager

    @classmethod
    def remove(cls, key: str):
        """移除沙箱管理器"""
        cls._repository.pop(key, None)
        logger.info(
            f"[Sandbox]移除sandbox，key={key}, 当前运行中沙箱数量={len(cls._repository)}"
        )

    @classmethod
    async def cleanup_and_remove(cls, key: str):
        """清理并移除沙箱管理器，包括 kill 沙箱客户端"""
        sandbox_manager = cls._repository.pop(key, None)
        if sandbox_manager and sandbox_manager.client:
            try:
                await sandbox_manager.client.kill()
                logger.info(
                    f"[Sandbox]清理sandbox_manager并kill，key={key}, 杀死后运行中沙箱数量={len(cls._repository)}"
                )
            except Exception as e:
                logger.exception(
                    f"[Sandbox]清理sandbox_manager失败，key={key}, error={str(e)}"
                )


def _resolve_forwardable_url(
    file_url: str,
    file_storage_client=None,
) -> str:
    """把文件引用解析成 provider 可直接消费的公共 http(s) URL。

    多媒体生成 provider 只接受公共服务的文件协议/地址（http/https），不认
    内部协议（gyra-fs://）或沙箱本地路径。规则：
    - http(s) → 原样返回
    - 其它（gyra-fs:// 等内部协议）→ 经 FileStorageClient 生成公开 URL
    - 无法解析 → 返回原值（保留信息，由上层决定是否可转发）
    """
    if not file_url:
        return ""
    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url
    if file_storage_client is not None:
        try:
            public = file_storage_client.get_public_url(file_url)
            if public:
                return public
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[AgentChat] Failed to resolve public URL for {file_url}: {e}"
            )
    return file_url


async def _materialize_sandbox_file_refs(
    system_app: SystemApp,
    sandbox_client,
    sandbox_file_refs: List[Dict[str, Any]],
) -> List[str]:
    """将上传文件引用中的文件实际写入沙箱，并返回用于提示的引用列表.

    支持 gyra-fs:// 协议（通过 FileStorageClient 直接读取）以及 http(s) URL。
    文件提示同时注入 provider 可消费的公共 URL，供主 agent 转发给多媒体子 agent。
    """
    work_dir = sandbox_client.work_dir
    uploads_dir = f"{work_dir}/uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    updated_refs: List[str] = []

    file_storage_client = None
    try:
        file_storage_client = FileStorageClient.get_instance(
            system_app,
            default_component=None,
        )
    except Exception as e:
        logger.warning(f"[AgentChat] Failed to get FileStorageClient: {e}")

    for idx, ref in enumerate(sandbox_file_refs, 1):
        if not isinstance(ref, dict):
            logger.warning(f"[AgentChat] Invalid sandbox_file_ref type: {type(ref)}")
            continue

        file_name = ref.get("file_name", "")
        file_url = ref.get("url", "") or ""
        logger.info(
            f"[AgentChat] Processing ref: file_name={file_name}, "
            f"url={file_url[:100] if file_url else 'None/Empty'}, "
            f"has_url={bool(file_url)}, "
            f"is_http={file_url.startswith('http://') or file_url.startswith('https://') if file_url else False}"
        )
        if not file_name:
            logger.warning("[AgentChat] sandbox_file_ref missing file_name")
            continue

        new_path = f"{uploads_dir}/{file_name}"
        ref["sandbox_path"] = new_path
        # 解析 provider 可直接消费的公共 http(s) URL，供主 agent 转发给多媒体
        # 子 agent 作首帧/参考图（provider 只认公共协议/地址，不认 gyra-fs://）。
        public_url = _resolve_forwardable_url(file_url, file_storage_client)
        ref["public_url"] = public_url
        forward_url = public_url or file_url
        ref_info = f"{idx}. `{new_path}`"
        if forward_url:
            ref_info += f" (URL: {forward_url})"
        updated_refs.append(ref_info)
        logger.info(f"[AgentChat] Updated sandbox_path: {new_path}")

        if not file_url:
            logger.warning(
                f"[AgentChat] No URL to download file, file_name={file_name}"
            )
            continue

        try:
            content = None

            if file_url.startswith("gyra-fs://"):
                if file_storage_client:
                    logger.info(
                        f"[AgentChat] Downloading gyra-fs:// file to sandbox: {new_path}"
                    )
                    await blocking_func_to_async(
                        system_app,
                        file_storage_client.download_file,
                        file_url,
                        dest_path=new_path,
                    )
                    logger.info(f"[AgentChat] Wrote gyra-fs file to sandbox: {new_path}")
                else:
                    logger.warning(
                        "[AgentChat] FileStorageClient not available for gyra-fs:// URL"
                    )
            elif file_url.startswith("http://") or file_url.startswith("https://"):
                logger.info(f"[AgentChat] Downloading file from: {file_url}")
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.get(file_url)
                    if response.status_code == 200:
                        content = response.content
                        os.makedirs(uploads_dir, exist_ok=True)
                        with open(new_path, "wb") as f:
                            f.write(content)
                        logger.info(
                            f"[AgentChat] Wrote HTTP file to sandbox: {new_path}, "
                            f"size={len(content)}"
                        )
                    else:
                        logger.warning(
                            f"[AgentChat] Failed to download file: HTTP {response.status_code}"
                        )
            else:
                logger.warning(f"[AgentChat] Invalid URL format: {file_url[:50]}")
        except Exception as e:
            logger.error(
                f"[AgentChat] Failed to write file to sandbox: {e}",
                exc_info=True,
            )

    return updated_refs


class AgentChat(BaseComponent, ABC):
    name = ComponentType.AGENT_CHAT

    def __init__(
        self,
        system_app: SystemApp,
        gpts_memory: Optional[GptsMemory] = None,
        llm_provider: Optional[Any] = None,
    ):
        self.gpts_conversations = GptsConversationsDao()
        self.gpts_messages_dao = GptsMessagesDao()

        # 初始化数据库存储后端
        file_metadata_db_storage = MetaGyrasFileMetadataStorage()
        work_log_db_storage = MetaGyrasWorkLogStorage()
        kanban_db_storage = MetaGyrasKanbanStorage()
        todo_db_storage = MetaGyrasTodoStorage()

        self.memory = gpts_memory or GptsMemory(
            plans_memory=MetaGyrasPlansMemory(),
            message_memory=MetaGyrasMessageMemory(),
            message_system_memory=MetaAgentSystemMessageMemory(),
            file_metadata_db_storage=file_metadata_db_storage,
            work_log_db_storage=work_log_db_storage,
            kanban_db_storage=kanban_db_storage,
            todo_db_storage=todo_db_storage,
        )

        self.llm_provider = llm_provider
        self.agent_memory_map = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

        # 设置 system_app 属性
        super().__init__(system_app)
        self.system_app = system_app
        self.agent_manage = get_agent_manager(system_app)

        # Register GptsMemory to system_app for file_dispatch.py to access (全局单例，只注册一次)
        # Note: GptsMemory is not a BaseComponent, so we manually add it to components dict
        # without calling lifecycle methods
        try:
            from gyra.component import ComponentType

            # 检查是否已经注册，避免重复注册
            name = ComponentType.GPTS_MEMORY.value if isinstance(ComponentType.GPTS_MEMORY, ComponentType) else ComponentType.GPTS_MEMORY
            if name not in self.system_app.components:
                # Manually add to components dict without calling init_app or lifecycle methods
                self.system_app.components[name] = self.memory
                logger.info("[AgentChat] Registered GptsMemory to system_app")
            else:
                logger.debug("[AgentChat] GptsMemory already registered, skipping")
        except Exception as e:
            logger.warning(f"[AgentChat] Failed to register GptsMemory: {e}")

        # 注册全局 SubagentCoordinator 单例，供 SubAgent 工具 async 模式访问
        try:
            from gyra_serve.agent.subagent_coordinator import (
                SubagentCoordinator,
                set_subagent_coordinator,
            )
            set_subagent_coordinator(SubagentCoordinator(agent_chat=self))
            logger.info("[AgentChat] global SubagentCoordinator registered")
        except Exception as coord_err:
            logger.warning(
                f"[AgentChat] failed to register SubagentCoordinator: {coord_err}"
            )

        # 注册全局 AsyncTaskCoordinator 单例：监听 media / spawn_agent_task 后台异步任务，
        # 完成后自动恢复主会话 loop；并把 media 进程级单例纳入轮询。
        try:
            from gyra_serve.agent.async_task_coordinator import (
                AsyncTaskCoordinator,
                set_async_task_coordinator,
            )
            self.async_task_coord = AsyncTaskCoordinator(agent_chat=self)
            set_async_task_coordinator(self.async_task_coord)
            from gyra.agent.util.async_task_manager import AsyncTaskManager

            # 注入 DB 持久化 ledger（AsyncTaskDao），替代 JSONL 台账。
            # 使 media 单例与 subagent 任务统一写 gpts_async_tasks 表，
            # 支撑分布式查询 / 跨进程恢复。
            try:
                from gyra_serve.agent.db.async_task_db import AsyncTaskDao

                AsyncTaskManager.set_global_ledger(AsyncTaskDao())
            except Exception as ledger_err:
                logger.warning(
                    f"[AgentChat] failed to inject DB ledger for async tasks: {ledger_err}"
                )

            self.async_task_coord.add_manager(AsyncTaskManager.media_instance())
            self.async_task_coord.start_watch()
            logger.info("[AgentChat] global AsyncTaskCoordinator registered")
        except Exception as async_err:
            logger.warning(
                f"[AgentChat] failed to register AsyncTaskCoordinator: {async_err}"
            )

    def init_app(self, system_app: SystemApp):
        self.system_app = system_app
        # 注册全局模型配置缓存
        self._register_model_configs()

    def _register_model_configs(self):
        """注册全局模型配置到缓存"""
        from gyra.agent.util.llm.model_config_cache import (
            ModelConfigCache,
            parse_provider_configs,
        )

        global_agent_conf = self.system_app.config.get("agent.llm")
        if not global_agent_conf:
            agent_conf = self.system_app.config.get("agent")
            if isinstance(agent_conf, dict):
                global_agent_conf = agent_conf.get("llm")

        if global_agent_conf:
            model_configs = parse_provider_configs(global_agent_conf)
            if model_configs:
                ModelConfigCache.register_configs(model_configs)
                logger.info(f"Registered {len(model_configs)} models to global cache")

    async def _get_or_create_sandbox_manager(
        self, context: AgentContext, app: GptsApp, need_sandbox: bool
    ) -> Optional[SandboxManager]:
        """获取或创建沙箱管理器，同一会话内共享

        Args:
            context: Agent 上下文
            app: 应用配置
            need_sandbox: 是否需要沙箱

        Returns:
            SandboxManager 实例或 None
        """
        # 检查是否需要沙箱
        # 处理 team_context 可能是字典或对象的情况
        use_sandbox_flag = False
        if app.team_context:
            if hasattr(app.team_context, "use_sandbox"):
                use_sandbox_flag = app.team_context.use_sandbox
            elif isinstance(app.team_context, dict):
                use_sandbox_flag = app.team_context.get("use_sandbox", False)

        # 检查系统级 sandbox 配置
        # 当系统配置了 sandbox type 时，即使应用级 use_sandbox_flag 为 False，
        # 也应该创建 sandbox_manager，确保 sandbox 配置能正确注入到 system prompt
        app_config = self.system_app.config.configs.get("app_config")
        sandbox_config: Optional[SandboxConfigParameters] = (
            app_config.sandbox if app_config else None
        )
        system_sandbox_enabled = bool(sandbox_config and sandbox_config.type)

        # Safely access context.extra (may be None for non-chat contexts like ECP)
        extra_dict = context.extra or {}
        dynamic_resources = extra_dict.get("dynamic_resources", [])

        if not (
            (need_sandbox and (use_sandbox_flag or system_sandbox_enabled))
            or await self._have_agent_skill(app, dynamic_resources)
        ):
            logger.debug(
                f"[Sandbox] Skip sandbox creation: need_sandbox={need_sandbox}, "
                f"use_sandbox_flag={use_sandbox_flag}, system_sandbox_enabled={system_sandbox_enabled}, "
                f"has_agent_skill={await self._have_agent_skill(app, dynamic_resources)}"
            )
            return None

        logger.info(
            f"[Sandbox] Creating sandbox_manager: need_sandbox={need_sandbox}, "
            f"use_sandbox_flag={use_sandbox_flag}, system_sandbox_enabled={system_sandbox_enabled}"
        )

        # 检查缓存中是否已有该会话的 sandbox_manager
        sandbox_key = _sandbox_key(
            (context.extra or {}).get("workspace_id"), context.conv_id, context.staff_no
        )
        cached_manager = GlobalSandboxManagerCache.get(sandbox_key)
        if cached_manager:
            return cached_manager

        # 缓存中没有，需要创建新的
        async def _create_sandbox_manager() -> SandboxManager:
            app_config = self.system_app.config.configs.get("app_config")
            sandbox_config: Optional[SandboxConfigParameters] = app_config.sandbox

            file_storage_client = None
            try:
                from gyra.core.interface.file import FileStorageClient

                file_storage_client = FileStorageClient.get_instance(self.system_app)
                if file_storage_client:
                    logger.info(
                        f"[AgentChat] FileStorageClient retrieved for sandbox creation"
                    )
            except Exception as e:
                logger.warning(f"[AgentChat] Failed to get FileStorageClient: {e}")

            # 场景空间:沙箱工作目录指向空间家目录(pilot/data/workspaces/<id>,
            # 与数据集目录同源),大厅/任务共享且跨会话持久;非场景对话保持原行为
            work_dir = sandbox_config.work_dir
            host_work_dir = None
            workspace_id = (context.extra or {}).get("workspace_id")

            # 工程目录生态(Claude Code / Cursor 兼容):agent 编辑里配置了
            # ext_config.project_ecosystem.project_dir 时,沙箱工作目录直接指向
            # 该宿主机工程目录(本地沙箱,与场景空间 home 同语义),优先级最高
            project_dir = None
            try:
                eco_cfg = (getattr(app, "ext_config", None) or {}).get(
                    "project_ecosystem"
                ) or {}
                project_dir = (eco_cfg.get("project_dir") or "").strip()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Sandbox] resolve project_dir failed: {e}")
                project_dir = None

            if project_dir and os.path.isdir(project_dir):
                host_work_dir = os.path.abspath(project_dir)
                work_dir = host_work_dir
                logger.info(
                    f"[Sandbox] project ecosystem dir {project_dir} set as sandbox "
                    f"work_dir (Claude Code / Cursor 兼容)"
                )
            elif workspace_id:
                try:
                    from gyra_serve.workspace.dataset_service import (
                        workspace_sandbox_root,
                    )

                    host_work_dir = workspace_sandbox_root(int(workspace_id))
                    work_dir = host_work_dir
                    logger.info(
                        f"[Sandbox] scene workspace {workspace_id} sandbox dir: "
                        f"{host_work_dir}"
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"[Sandbox] resolve workspace sandbox root failed, "
                        f"fallback to default work_dir: {e}"
                    )
                    host_work_dir = None

            # E2B 云端沙箱配置透传（type="e2b" 时生效）
            e2b_config = {
                "api_key": sandbox_config.e2b_api_key,
                "template": sandbox_config.e2b_template,
                "timeout": sandbox_config.e2b_timeout,
                "work_dir": sandbox_config.e2b_work_dir,
                "skill_dir": sandbox_config.e2b_skill_dir,
            }
            e2b_config = {k: v for k, v in e2b_config.items() if v is not None}

            sandbox_client = await AutoSandbox.create(
                user_id=context.staff_no or sandbox_config.user_id,
                agent=sandbox_config.agent_name,
                type=sandbox_config.type,
                template=sandbox_config.template_id,
                work_dir=work_dir,
                host_work_dir=host_work_dir,
                skill_dir=sandbox_config.skill_dir,
                file_storage_client=file_storage_client,
                oss_ak=sandbox_config.oss_ak,
                oss_sk=sandbox_config.oss_sk,
                oss_endpoint=sandbox_config.oss_endpoint,
                oss_bucket_name=sandbox_config.oss_bucket_name,
                e2b_config=e2b_config,
            )
            sandbox_manager = SandboxManager(sandbox_client=sandbox_client)
            # 后台启动和初始化沙箱服务
            sandbox_task = asyncio.create_task(sandbox_manager.acquire())
            sandbox_manager.set_init_task(sandbox_task)
            return sandbox_manager

        return await GlobalSandboxManagerCache.get_or_create(
            sandbox_key, _create_sandbox_manager
        )

    async def _cleanup_sandbox_manager(
        self, conv_id: str, staff_no: Optional[str] = None
    ):
        """清理会话的沙箱管理器

        Args:
            conv_id: 会话ID
            staff_no: 用户ID
        """
        if staff_no:
            # P2: workspace 维度的共享沙箱用 ws: 前缀 key 创建，此处 conv 维度 key 找不到，
            # 共享沙箱常驻至进程退出（避免误杀仍在运行的子 agent）；普通会话独占沙箱正常 cleanup。
            sandbox_key = _sandbox_key(None, conv_id, staff_no)
            await GlobalSandboxManagerCache.cleanup_and_remove(sandbox_key)

    def _register_multimedia_agents(self, gpt_app: Any) -> None:
        """把多媒体 Agent 模板注册进 AgentManager（协议层统一，类似 ReActMaster）。

        - 注册 ``role=MULTIMEDIA`` 使 ``app.agent="MULTIMEDIA"`` 可持久化，并作为
          一等公民主 Agent 模板使用（无需独立的 MultimediaAgentRegistry 旁路）。
        - 同时把当前 app 的 ``ext_config.multimedia_agent`` 绑定到模板实例，供
          spawn_agent_task 委派时按当前 app 配置解析（同一模板服务不同 app）。
        """
        try:
            from gyra.agent.multimedia import MultimediaAgent

            # 模板身份：实例的 role。类级访问 pydantic Field（MultimediaAgent.profile）
            # 会抛 AttributeError（非 ValueError），导致注册被外层吞掉、模板从未登记。
            role = MultimediaAgent().role

            # 已在代理管理器注册则跳过重复注册
            try:
                self.agent_manage.get_by_name(role)
            except ValueError:
                self.agent_manage.register_agent(MultimediaAgent)
                logger.info(f"[multimedia-agent] registered template (role={role})")

            inst = self.agent_manage.get_agent(role)
            if inst is not None:
                inst.ext_config = getattr(gpt_app, "ext_config", None) or {}
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[multimedia-agent] register failed: {e}")

    def after_start(self):
        # LLM client is resolved per-request by AIWrapper + ProviderRegistry
        # reading from agent.llm config; no shared llm_provider is needed.
        # P3: 启动时扫未完成的 RUNNING 会话（含 pending_subagents），恢复主 agent。
        # best-effort：若无事件循环则跳过，下次启动再恢复。
        try:
            from gyra_serve.agent.recovery_daemon import RecoveryDaemon
            asyncio.create_task(RecoveryDaemon(self).scan_and_recover())
        except RuntimeError:
            logger.warning("[AgentChat] no running event loop, skip recovery scan")
        except Exception as e:
            logger.warning(f"[AgentChat] recovery scan launch failed: {e}")

        # #4: 启动时恢复 WAITING 会话未完成的异步任务（media / spawn_agent_task），
        # 按台账/内存态判定终态，全部终态则触发主 resume 恢复 loop。
        try:
            from gyra_serve.agent.async_task_coordinator import (
                get_async_task_coordinator,
            )
            async_coord = get_async_task_coordinator()
            if async_coord is not None:
                asyncio.create_task(async_coord.recover_all())
        except RuntimeError:
            logger.warning(
                "[AgentChat] no running event loop, skip async task recovery"
            )
        except Exception as e:
            logger.warning(f"[AgentChat] async task recovery launch failed: {e}")

        # chunk 调试文件保留期清理(无任何接口消费,长期累积;启动扫一次+每日周期)
        try:
            from gyra_serve.agent.chunk_file_cleaner import ChunkFileCleaner

            asyncio.create_task(ChunkFileCleaner().run_forever())
        except RuntimeError:
            logger.warning("[AgentChat] no running event loop, skip chunk cleaner")
        except Exception as e:
            logger.warning(f"[AgentChat] chunk cleaner launch failed: {e}")

    async def save_conversation(
        self,
        conv_session_id: str,
        agent_conv_id: str,
        current_message: StorageConversation,
        final_message: Optional[str] = None,
        err_msg: Optional[str] = None,
        chat_call_back: Optional[Callable[..., Optional[Any]]] = None,
        first_chunk_ms: Optional[int] = None,
    ):
        """最终对话保存（按格式收集最终内容，回调，并销毁缓存空间）

        Args:
            conv_session_id:会话id
            agent_conv_id:对话id
            err_msg:错误信息（如果是对话中断，包含中断信息）
        """
        logger.info(f"Agent chat end, save conversation {agent_conv_id}!")
        try:
            # 检查对话状态，如果是 RUNNING 则根据 err_msg 更新
            try:
                conv_entity = self.gpts_conversations.get_by_conv_id(agent_conv_id)
                if conv_entity and conv_entity.state == Status.RUNNING.value:
                    if err_msg:
                        if "中断" in err_msg or "interrupt" in err_msg.lower():
                            new_state = Status.INTERRUPTED.value
                            validate_session_transition(Status.RUNNING, Status.INTERRUPTED)
                        else:
                            new_state = Status.FAILED.value
                            validate_session_transition(Status.RUNNING, Status.FAILED)
                        self.gpts_conversations.update(agent_conv_id, new_state)
                        logger.info(
                            f"Updated conversation {agent_conv_id} state to {new_state}"
                        )
            except Exception as state_error:
                logger.error(f"Failed to update conversation state: {state_error}")

            """统一保存对话结果的逻辑"""
            if not final_message:
                try:
                    final_message = await self.memory.vis_final(agent_conv_id)
                    logger.info(f"[save_conversation] vis_final 返回内容长度: {len(final_message) if final_message else 0}, 内容前200字符: {final_message[:200] if final_message else 'None'}")
                except Exception as e:
                    logger.exception(f"获取{agent_conv_id}最终消息异常: {str(e)}")
                    final_message = str(e)

            # 把终态视图(is_running=False)推到流式 channel,确保 chunk 文件以"非运行中"
            # 收尾,否则页面刷新后右面板永久卡"思考中"(流式增量最后一条 is_running=True)。
            try:
                await self.memory.push_final_view(agent_conv_id)
            except Exception as e:  # noqa: BLE001 - 终态推送失败不影响保存
                logger.warning(f"[save_conversation] push_final_view failed for {agent_conv_id}: {e}")

            final_report = None
            if callable(chat_call_back):
                try:
                    final_report = await self.memory.user_answer(agent_conv_id)
                except Exception as e:
                    logger.exception(f"获取{conv_session_id}最终报告异常: {str(e)}")

                post_action_reports: list[dict] = []
                try:
                    messages = await self.memory.get_messages(agent_conv_id)
                    post_action_reports = [
                        post_action_report
                        for message in messages
                        if (
                            post_action_report := _get_post_action_report(
                                message.context
                            )
                        )
                    ]
                except Exception as e:
                    logger.exception(
                        f"获取{conv_session_id}post_action_reports: {str(e)}"
                    )

                await chat_call_back(
                    conv_session_id,
                    agent_conv_id,
                    final_message,
                    final_report,
                    err_msg,
                    first_chunk_ms,
                    post_action_reports=post_action_reports,
                )

            # Deliver to channel if configured (handles cron job message delivery)
            if not err_msg:
                content = final_report  # 只看final_report 不看final_message
                content = content.lstrip() if content else None
                if content:
                    await self._deliver_to_channel_if_configured(
                        conv_session_id, content
                    )

            # logger.info(f"获取{conv_session_id}最终消息: {final_message}, 异常信息:{err_msg}")
            if not final_message:
                final_message = ""
            if err_msg:
                current_message.add_view_message(final_message)
            else:
                current_message.add_view_message(final_message)
            current_message.end_current_round()
            current_message.save_to_storage()

        finally:
            await self.memory.clear(agent_conv_id)

    async def _deliver_to_channel_if_configured(
        self,
        conv_session_id: str,
        content: str,
    ) -> bool:
        """Deliver message to channel if configured in conversation extra.

        This method handles automatic message delivery to channels (e.g., DingTalk)
        when the conversation was initiated from a channel or when a cron job
        needs to deliver results to a channel.

        The channel info is stored in the conversation's extra field when
        the conversation is created from a channel message.

        Args:
            conv_session_id: The conversation session ID.
            content: The message content to deliver.

        Returns:
            True if delivered successfully, False otherwise.
        """
        if not conv_session_id:
            return False

        try:
            # Get channel info from conversation extra
            conversations = await self.gpts_conversations.get_by_session_id_asc(
                conv_session_id
            )

            if not conversations:
                logger.debug(f"No conversations found for session {conv_session_id}")
                return False

            # Get the most recent conversation to extract channel info
            first_conv = conversations[-1]
            if not first_conv.extra:
                logger.debug(f"No extra field in conversation {first_conv.conv_id}")
                return False

            # Parse extra field
            extra = orjson.loads(first_conv.extra)
            channel_info = extra.get("channel")

            if not channel_info:
                logger.debug(f"No channel info in conversation {first_conv.conv_id}")
                return False

            channel_id = channel_info.get("channel_id")
            receiver_id = channel_info.get("receiver_id")
            is_group = channel_info.get("is_group", False)

            if not channel_id or not receiver_id:
                logger.warning(
                    f"Incomplete channel info: channel_id={channel_id}, receiver_id={receiver_id}"
                )
                return False

            # Get the channel handler from registry
            from gyra.channel.registry import ChannelHandlerRegistry

            registry = ChannelHandlerRegistry.get_instance()
            handler = registry.get_handler(channel_id)

            if not handler:
                logger.warning(f"No active handler for channel {channel_id}")
                return False

            # Send the message
            result = await handler.send_message(
                receiver_id=receiver_id,
                content=content,
                content_type="text",
                is_group=is_group,
            )

            if result.success:
                logger.info(f"Delivered message to channel {channel_id}")
                return True
            else:
                logger.error(f"Failed to deliver: {result.error}")
                return False

        except Exception as e:
            logger.error(f"Error delivering to channel: {e}")
            return False

    @trace("agent.initialize_conversation", requires=["app_code", "conv_session_id"])
    async def _initialize_conversation(
        self,
        conv_session_id: str,
        app_code: str,
        user_query: Union[str, HumanMessage],
        user_code: Optional[str] = None,
    ) -> StorageConversation:
        """初始化会话"""
        conv_serve = ConversationServe.get_instance(CFG.SYSTEM_APP)
        current_message = await _build_conversation(
            conv_id=conv_session_id,
            select_param="",
            summary="",
            model_name="",
            app_code=app_code,
            conv_serve=conv_serve,
            user_name=user_code,
        )
        execute_no_wait(current_message.save_to_storage)
        # current_message.save_to_storage()
        current_message.start_new_round()
        current_message.add_user_message(
            user_query if isinstance(user_query, str) else user_query.content
        )
        return current_message

    @trace(
        "agent.initialize_agent_conversation", requires=["app_code", "conv_session_id"]
    )
    async def _initialize_agent_conversation(self, conv_session_id: str, **ext_info):
        gpts_conversations: List[
            GptsConversationsEntity
        ] = await self.gpts_conversations.get_by_session_id_asc(conv_session_id)

        logger.info(
            f"gpts_conversations count:{conv_session_id}, "
            f"{len(gpts_conversations) if gpts_conversations else 0}"
        )
        last_conversation = gpts_conversations[-1] if gpts_conversations else None
        if last_conversation and Status.WAITING.value == last_conversation.state:
            agent_conv_id = last_conversation.conv_id
            logger.info("收到用户动作授权, 恢复会话: " + agent_conv_id)
        else:
            gpt_chat_order = (
                "1" if not gpts_conversations else str(len(gpts_conversations) + 1)
            )
            agent_conv_id = conv_session_id + "_" + gpt_chat_order
        # 三层嵌套 trace:L1 会话两个 id 的映射(chunk 文件名/SSE 用 agent_conv_id,
        # 会话台账用 conv_session_id),便于 grep 串联主会话 -> 子会话 -> 轮询任务
        logger.info(
            f"[agent-conv] session={conv_session_id} -> agent_conv={agent_conv_id}"
        )
        return agent_conv_id, gpts_conversations

    @abstractmethod
    async def chat(
        self,
        conv_uid: str,
        gpts_name: str,
        user_query: Union[str, HumanMessage],
        background_tasks: Optional[BackgroundTasks] = None,
        specify_config_code: Optional[str] = None,
        user_code: Optional[str] = None,
        sys_code: Optional[str] = None,
        stream: Optional[bool] = True,
        chat_call_back: Optional[Any] = None,
        chat_in_params: Optional[List[ChatInParamValue]] = None,
        **ext_info,
    ):
        """会话入口接口,根据需要分开实现. 对外服务
        Args:

        """
        raise NotImplementedError

    @staticmethod
    def _extract_playbook_command(chat_in_params):
        """从 chat_in_params 抽取 playbook_command,返回 {playbook_id, playbook_name} 或 None。"""
        if not chat_in_params:
            return None
        for p in chat_in_params:
            if getattr(p, "param_type", None) == "playbook_command":
                try:
                    return json.loads(p.param_value)
                except (TypeError, ValueError, AttributeError):
                    return None
        return None

    @staticmethod
    def _extract_model(chat_in_params):
        """从 chat_in_params 抽取 model 参数,返回 model 名字符串或 None。"""
        if not chat_in_params:
            return None
        for p in chat_in_params:
            if getattr(p, "param_type", None) == "model":
                return getattr(p, "param_value", None)
        return None

    @staticmethod
    def _resolve_app_model_name(gpt_app: Any) -> Optional[str]:
        """安全地从 app 解析当前模型名（用于文件分流的能力判断）。

        ``gpts_app.llm_config`` 是 ``LLMResource``，没有 ``.model`` 字段，直接访问会
        抛 AttributeError。这里按优先级安全取值：
        1. ``llm_config.agent_llm_config`` 字典里的 ``model``；
        2. 多媒体 agent 的 ``ext_config.multimedia_agent`` 默认图片/视频模型；
        3. 兜底返回 None（此时靠 ``prefer_direct_media`` 决定分流）。
        """
        if gpt_app is None:
            return None
        try:
            llm_cfg = getattr(gpt_app, "llm_config", None)
            if llm_cfg is not None:
                agent_llm = (
                    llm_cfg.agent_llm_config
                    if hasattr(llm_cfg, "agent_llm_config")
                    else None
                )
                if isinstance(agent_llm, dict) and agent_llm.get("model"):
                    return agent_llm.get("model")
                if isinstance(agent_llm, str):
                    try:
                        import json as _json

                        agent_llm = _json.loads(agent_llm)
                        if isinstance(agent_llm, dict) and agent_llm.get("model"):
                            return agent_llm.get("model")
                    except Exception:  # noqa: BLE001
                        pass
        except Exception:  # noqa: BLE001
            pass

        # 多媒体 agent：解析其默认生成模型
        try:
            ext_cfg = getattr(gpt_app, "ext_config", None)
            if isinstance(ext_cfg, str):
                import json as _json

                ext_cfg = _json.loads(ext_cfg)
            if isinstance(ext_cfg, dict):
                mm = ext_cfg.get("multimedia_agent") or {}
                if isinstance(mm, dict):
                    return (
                        mm.get("default_video_model")
                        or mm.get("default_image_model")
                        or None
                    )
        except Exception:  # noqa: BLE001
            pass

        return None

    @staticmethod
    def _resolve_vis_render(ext_info, gpt_app):
        """场景 Agent(workspace_id)默认 scene_agent_workspace,否则走 app layout / gpt_vis_all。"""
        if ext_info.get("workspace_id"):
            return "scene_agent_workspace"
        if gpt_app and gpt_app.layout and gpt_app.layout.chat_layout:
            return gpt_app.layout.chat_layout.name
        return "gpt_vis_all"

    async def aggregation_chat(
        self,
        conv_id: str,
        agent_conv_id: str,
        gpts_name: str,
        user_query: Union[str, HumanMessage],
        user_code: str = None,
        sys_code: str = None,
        stream: Optional[bool] = True,
        gpts_conversations: Optional[List[GptsConversationsEntity]] = None,
        specify_config_code: Optional[str] = None,
        chat_in_params: Optional[List[ChatInParamValue]] = None,
        **ext_info,
    ):
        """具体agent(app)对话入口，构建对话记忆和对话目标等通用的Agent对话逻辑(需要外层基于会话封装一般不直接)

        Args:
            conv_id: 会话id
            agent_conv_id：当前对话id
            gpts_name：要对话的智能体(应用/agent/工作流等)
        """
        # logger.info(
        #     f"agent_chat conv_id:{conv_id}, agent_conv_id:{agent_conv_id},gpts_name:{gpts_name},user_query:"
        #     f"{user_query}"
        # )
        root_tracer.set_current_agent_id(gpts_name)  # 将当前agent app_code写入trace存储
        digest(
            CHAT_LOGGER,
            "CHAT_ENTRY",
            conv_id=conv_id,
            app_code=gpts_name,
            user_code=user_code,
        )
        start_ts = root_tracer.get_context_entrance_ms() or current_ms()
        succeed = False
        first_chunk_time = None
        if isinstance(user_query, str):
            user_query: HumanMessage = HumanMessage.parse_chat_completion_message(
                user_query, ignore_unknown_media=True
            )

        root_tracer.set_context_conv_id(agent_conv_id)
        message_round = 0
        history_message_count = 0
        is_retry_chat = False
        last_speaker_name = None
        history_messages = None

        ########################################################
        app_config = self.system_app.config.configs.get("app_config")
        web_config = _get_web_config(app_config)

        app_service = get_app_service()
        gpt_app: GptsApp = await app_service.app_detail(
            gpts_name, specify_config_code, building_mode=False
        )
        await self.dynamic_resource_adapter(gpt_app, ext_info)
        if not gpt_app:
            raise ValueError(f"Not found app {gpts_name}!")
        # 注册多媒体 Agent（从应用 ext_config.multimedia_agent 读取模板配置）
        self._register_multimedia_agents(gpt_app)

        # Workspace context + 物化资源注入
        system_prompt_parts = []
        if ext_info.get("system_prompt"):
            system_prompt_parts.append(ext_info["system_prompt"])
        workspace_event_queue: asyncio.Queue = asyncio.Queue()
        # 注册到 workspace 事件总线,scene 写工具/run_task 产生的事件经此 drain 进 SSE
        _ws_id_for_bus = ext_info.get("workspace_id")
        if _ws_id_for_bus:
            from gyra_serve.workspace.event_bus import register_workspace_queue

            register_workspace_queue(int(_ws_id_for_bus), workspace_event_queue)
        _inject_workspace_context(
            system_app=self.system_app,
            workspace_id=ext_info.get("workspace_id"),
            user_id=user_code,
            conv_uid=conv_id,
            task_id=ext_info.get("task_id"),
            focus_artifact_id=ext_info.get("focus_artifact_id"),
            system_prompt=system_prompt_parts,
            extra_agents=ext_info.setdefault("extra_agents", []),
            ext_info=ext_info,
            llm_config=LLMConfig(llm_client=self.llm_provider),
            event_queue=workspace_event_queue,
            app_code=gpt_app.app_code,
        )
        if system_prompt_parts:
            ext_info["system_prompt"] = "\n\n".join(system_prompt_parts).strip()

        _merge_scene_dynamic_context(gpt_app, ext_info)

        # 剧本命令模式:chat_in_params 含 playbook_command 时直接创建任务,跳过 LLM 回合
        playbook_command = self._extract_playbook_command(chat_in_params)
        if playbook_command and ext_info.get("workspace_id"):
            from gyra_serve.workspace.agent_tools._task_creator import (
                create_task_from_tool,
            )

            # user_query 此时已解析为 HumanMessage,取其文本内容作为标题(否则回退 playbook_name)
            _user_text = ""
            _content = getattr(user_query, "content", None)
            if isinstance(_content, str):
                _user_text = _content
            elif isinstance(_content, list):
                _user_text = " ".join(
                    p.get("text", "")
                    for p in _content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            # 选了剧本必须有任务目标:剧本只指定资源/能力,目标由用户输入。
            if not _user_text.strip():
                yield (
                    None,
                    _format_vis_msg(
                        "选择剧本后请输入本次任务目标(剧本只指定资源与能力,目标由你定义)。"
                    ),
                    agent_conv_id,
                )
                yield None, _format_vis_msg("[DONE]"), agent_conv_id
                return
            _model_name = self._extract_model(chat_in_params)
            result = create_task_from_tool(
                system_app=self.system_app,
                workspace_id=int(ext_info["workspace_id"]),
                user_id=user_code,
                playbook_id=playbook_command.get("playbook_id"),
                title=_user_text,
                description=None,
                model_name=_model_name,
            )
            # 发 task_created workspace event 后直接结束流(与 aggregation_chat 其余
            # yield 一致的 (task, sse_chunk, agent_conv_id) 三元组形态)
            yield (
                None,
                format_workspace_event(
                    "task_created",
                    {
                        "task_id": result["task_id"],
                        "title": result["title"],
                        "status": result["status"],
                        "playbook_id": result["playbook_id"],
                        "playbook_name": result["playbook_name"],
                        "triggered_by": result["triggered_by"],
                        "workspace_id": int(ext_info["workspace_id"]),
                    },
                ),
                agent_conv_id,
            )
            yield None, _format_vis_msg("[DONE]"), agent_conv_id
            return

        # init gpts  memory
        vis_render = ext_info.get("vis_render", None)
        # 如果接口指定使用接口传递，没有指定使用当前应用的布局配置
        if not vis_render:
            vis_render = self._resolve_vis_render(ext_info, gpt_app)

        vis_converter_mng = get_vis_manager()
        vis_protocol = vis_converter_mng.get_by_name(vis_render)(
            gyra_url=web_config.web_url
        )
        ext_info["incremental"] = vis_protocol.incremental

        #########################################################

        with root_tracer.start_span("agent.conversation.state_check"):
            # 检查最后一个对话记录是否完成，如果是等待状态，则要继续进行当前对话
            if gpts_conversations:
                last_gpts_conversation: GptsConversationsEntity = gpts_conversations[-1]
                logger.info(
                    f"last conversation status:{last_gpts_conversation.__dict__}"
                )
                if last_gpts_conversation.state == Status.WAITING.value:
                    is_retry_chat = True
                    agent_conv_id = last_gpts_conversation.conv_id

                    # 读取持久化的等待原因（extra["waiting_reason"]），供 _inner_chat
                    # 传给 initiate_chat → base_agent._update_recovering：
                    # 只有"工具授权"才重放，其余（追问/异步任务/子agent）走 LLM 处理新输入。
                    try:
                        _extra = json.loads(last_gpts_conversation.extra) if isinstance(
                            last_gpts_conversation.extra, str
                        ) else (last_gpts_conversation.extra or {})
                    except (json.JSONDecodeError, TypeError):
                        _extra = {}
                    ext_info["waiting_reason"] = (
                        _extra.get("waiting_reason") if isinstance(_extra, dict) else None
                    )

                    gpts_messages: List[
                        GptsMessage
                    ] = await self.gpts_messages_dao.get_by_conv_id(agent_conv_id)  # type:ignore

                    last_message = gpts_messages[-1]
                    message_round = last_message.rounds + 1
                    last_speaker_name = last_message.sender_name

        await self.memory.init(
            agent_conv_id,
            app_code=gpts_name,
            history_messages=history_messages,
            start_round=history_message_count,
            vis_converter=vis_protocol,
        )

        historical_dialogues: List[GptsMessage] = []
        if is_retry_chat:
            # 恢复起来的会话，需要加载历史消息到记忆中
            await self.memory.load_persistent_memory(agent_conv_id)

        if not is_retry_chat:
            # Create a new gpts conversation record

            ## When creating a new gpts conversation record, determine whether to
            # include the history of previous topics according to the application
            # definition.
            if gpt_app.keep_start_rounds > 0 or gpt_app.keep_end_rounds > 0:
                if gpts_conversations and len(gpts_conversations) > 0:
                    rely_conversations = []
                    if gpt_app.keep_start_rounds + gpt_app.keep_end_rounds < len(
                        gpts_conversations
                    ):
                        if gpt_app.keep_start_rounds > 0:
                            front = gpts_conversations[: gpt_app.keep_start_rounds]
                            rely_conversations.extend(front)
                        if gpt_app.keep_end_rounds > 0:
                            back = gpts_conversations[-gpt_app.keep_end_rounds :]
                            rely_conversations.extend(back)
                    else:
                        rely_conversations = gpts_conversations
                    for gpts_conversation in rely_conversations:
                        temps: List[GptsMessage] = await self.memory.get_messages(
                            gpts_conversation.conv_id
                        )
                        if temps and len(temps) > 1:
                            historical_dialogues.append(temps[0])
                            historical_dialogues.append(temps[-1])

            user_goal = json.dumps(user_query.to_dict(), ensure_ascii=False)
            user_goal = user_goal[: min(len(user_goal), 6500)] if user_goal else ""
            workspace_id = ext_info.get("workspace_id")
            task_id = ext_info.get("task_id")
            await self.gpts_conversations.a_add(
                GptsConversationsEntity(
                    conv_id=agent_conv_id,
                    conv_session_id=conv_id,
                    user_goal=user_goal,
                    gpts_name=gpts_name,
                    team_mode=gpt_app.team_mode,
                    state=Status.RUNNING.value,
                    max_auto_reply_round=0,
                    auto_reply_count=0,
                    user_code=user_code,
                    sys_code=sys_code,
                    workspace_id=int(workspace_id) if workspace_id else None,
                    task_id=int(task_id) if task_id else None,
                    vis_render=vis_render,
                    extra=_serialize_extra_for_db(ext_info),
                )
            )

        # init agent memory
        agent_memory = self.get_or_build_gyra_memory(
            conv_id, gpt_app.app_code, user_code, gpt_app.team_context
        )
        file_handle = None
        task = None
        try:
            task = asyncio.create_task(
                self._inner_chat(
                    user_query=user_query,
                    conv_session_id=conv_id,
                    conv_uid=agent_conv_id,
                    gpts_app=gpt_app,
                    agent_memory=agent_memory,
                    is_retry_chat=is_retry_chat,
                    last_speaker_name=last_speaker_name,
                    init_message_rounds=message_round,
                    historical_dialogues=historical_dialogues,
                    user_code=user_code,
                    sys_code=sys_code,
                    stream=stream,
                    chat_in_params=chat_in_params,
                    **ext_info,
                )
            )
            # 注册任务以便可以通过 stop_chat 取消
            self.register_running_task(conv_id, task)
            ## TEST FILE WRITE
            WRITE_TO_FILE = True
            if WRITE_TO_FILE:
                from gyra.configs.model_config import DATA_DIR
                import os

                chat_chunk_file_path = os.path.join(DATA_DIR, "chat_chunk_file")
                os.makedirs(chat_chunk_file_path, exist_ok=True)
                filename = os.path.join(
                    chat_chunk_file_path, f"_chat_file_{agent_conv_id}.jsonl"
                )
                file_handle = open(filename, "w", encoding="utf-8")
            if stream == True:
                stream_complete = False

                # Check if task failed immediately
                await asyncio.sleep(0.1)  # Give task a moment to start
                if task.done() and task.exception():
                    exc = task.exception()
                    logger.error(f"Task failed immediately: {exc}")
                    raise exc

                # workspace context 注入后，yield context_loaded 事件给前端
                if ext_info.get("workspace_id"):
                    ws_ctx = ext_info.get("workspace_context") or {}
                    resources = ws_ctx.get("resources") or []
                    yield task, format_workspace_event(
                        "context_loaded",
                        {
                            "workspace_id": int(ext_info["workspace_id"]),
                            "resources": [
                                {"type": r.get("type"), "name": r.get("name")}
                                for r in resources
                            ],
                            "materialized_count": len(
                                (ws_ctx.get("materialized") or {}).get("dynamic_resources") or []
                            ),
                        },
                    ), agent_conv_id

                # 首先发送 session metadata，包含 conv_session_id 和 conv_uid
                metadata_content = orjson.dumps(
                    {
                        "vis": {
                            "type": "metadata",
                            "conv_session_id": conv_id,
                            "conv_uid": agent_conv_id,
                        }
                    }
                ).decode("utf-8")
                yield task, f"data:{metadata_content}\n\n", agent_conv_id

                # SSE heartbeat: if the agent is still running but no output has
                # been produced for 30 seconds, send an SSE comment every 10 seconds
                # to keep the TCP connection alive. SSE comments are ignored by the
                # browser's EventSource parser.
                HEARTBEAT_INTERVAL_MS = 30 * 1000
                HEARTBEAT_TIMEOUT_S = 10

                chat_iter = self._chat_messages(agent_conv_id, task)
                last_chunk_time = current_ms()

                # 用 asyncio.wait 而非 wait_for 包装 __anext__:
                # wait_for 超时会 cancel 协程,向 _chat_messages 异步生成器注入
                # CancelledError(属 BaseException,_chat_messages 的 except Exception
                # 抓不住),生成器被关闭 -> 下次 __anext__ 直接 StopAsyncIteration
                # -> 提前 yield [DONE],但后台 agent task 仍在跑(表现为:前端不渲染
                # 内容,过一会突然完成,后端 agent 还在继续)。
                # asyncio.wait 超时不 cancel pending task,生成器保持挂起继续等
                # queue.get(),agent 思考/工具执行数分钟也不会中断。
                next_chunk = asyncio.ensure_future(chat_iter.__anext__())

                while True:
                    # Drain workspace events before waiting for the next chunk (and
                    # on every heartbeat cycle) so they are not delayed.
                    while not workspace_event_queue.empty():
                        event_type, payload = workspace_event_queue.get_nowait()
                        formatted = format_workspace_event(event_type, payload)
                        if formatted:
                            yield task, formatted, agent_conv_id

                    done, _ = await asyncio.wait(
                        {next_chunk}, timeout=HEARTBEAT_TIMEOUT_S
                    )
                    if next_chunk not in done:
                        # 超时:next_chunk 仍在等 queue.get(),不 cancel。检查是否
                        # 到了 heartbeat 间隔,发 SSE 注释保活 TCP 连接。
                        now = current_ms()
                        if (
                            task
                            and not task.done()
                            and now - last_chunk_time >= HEARTBEAT_INTERVAL_MS
                        ):
                            yield task, ": heartbeat\n\n", agent_conv_id
                            last_chunk_time = now
                        continue

                    try:
                        chunk = next_chunk.result()
                    except StopAsyncIteration:
                        break

                    last_chunk_time = current_ms()
                    if chunk and len(chunk) > 0:
                        try:
                            content = _serialize_stream_chunk(chunk)
                            if WRITE_TO_FILE:
                                file_handle.write(content)
                                file_handle.write("\n")
                            resp = f"data:{content}\n\n"
                            first_chunk_time = first_chunk_time or current_ms()
                            yield task, resp, agent_conv_id
                        except Exception as e:
                            logger.exception(
                                f"get messages {gpts_name} Exception!" + str(e)
                            )
                            yield task, f"data: {str(e)}\n\n", agent_conv_id
                    stream_complete = True
                    next_chunk = asyncio.ensure_future(chat_iter.__anext__())

                # Wait for task to finish if it hasn't already
                if not task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(task), timeout=2.0
                        )
                    except (asyncio.TimeoutError, Exception):
                        pass

                if task.done() and task.exception():
                    if not stream_complete:
                        logger.exception(f"agent chat exception!{conv_id}")
                        raise task.exception()
                    else:
                        # Error was already pushed to queue and yielded,
                        # just log and send DONE
                        logger.warning(
                            f"Task had exception but messages were streamed: {task.exception()}"
                        )
                # Drain any remaining workspace events before yielding [DONE]
                while not workspace_event_queue.empty():
                    event_type, payload = workspace_event_queue.get_nowait()
                    formatted = format_workspace_event(event_type, payload)
                    if formatted:
                        yield task, formatted, agent_conv_id
                yield task, _format_vis_msg("[DONE]"), agent_conv_id
            else:
                logger.info("非流式消息输出!")
                last_chunk = None, None, None
                async for chunk in self._chat_messages(agent_conv_id, task):
                    if chunk and len(chunk) > 0:
                        if not first_chunk_time:
                            yield task, "", agent_conv_id
                        try:
                            content = _serialize_stream_chunk(chunk)
                            if WRITE_TO_FILE:
                                file_handle.write(content)
                                file_handle.write("\n")
                            resp = f"data:{content}\n\n"
                            first_chunk_time = first_chunk_time or current_ms()
                            last_chunk = task, resp, agent_conv_id
                        except Exception as e:
                            logger.exception(
                                f"get messages {gpts_name} Exception!" + str(e)
                            )
                            yield task, f"data: {str(e)}\n\n", agent_conv_id
                yield last_chunk
            succeed = True
        except asyncio.CancelledError:
            logger.info(f"Chat interrupted by user for conv_id: {conv_id}")
            # 推送中断消息
            interrupt_content = orjson.dumps(
                {
                    "vis": {
                        "type": "interrupt",
                        "content": "对话已被用户中断",
                    }
                }
            ).decode("utf-8")
            yield task, f"data:{interrupt_content}\n\n", agent_conv_id
            yield task, _format_vis_msg("[DONE]"), agent_conv_id
            # 保存中断状态
            succeed = False
            raise
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            logger.error(f"Agent chat have error! {str(e)}\n{error_trace}")

            try:
                if task and not task.done():
                    task.cancel()
            except Exception:
                pass

            error_content = orjson.dumps(
                {
                    "vis": {
                        "type": "error",
                        "content": f"对话发生错误: {str(e)}",
                    }
                }
            ).decode("utf-8")
            yield task, f"data:{error_content}\n\n", agent_conv_id
            yield task, _format_vis_msg("[DONE]"), agent_conv_id
        finally:
            # 大厅直接对话(task_id 为空)收尾:把本轮明确交付(deliverable)的文件
            # 物化为空间交付产物(Artifact)。任务模式(task_id 非空)由 playbook
            # runtime 收尾物化,此处跳过避免重复。
            try:
                if _ws_id_for_bus and not ext_info.get("task_id"):
                    from gyra_serve.workspace.agent_tools.materialize_deliverables import (
                        materialize_direct_conversation_deliverables,
                    )

                    await materialize_direct_conversation_deliverables(
                        system_app=self.system_app,
                        workspace_id=int(_ws_id_for_bus),
                        conv_id=conv_id,
                        agent_conv_id=agent_conv_id,
                        created_by_agent=gpt_app.app_code,
                    )
            except Exception as e:
                logger.warning(
                    f"[workspace] materialize lobby deliverables failed: {e}"
                )
            # 大厅内联任务收尾:内联任务绑定到当前会话(conv_session_id == conv_id),
            # 由主 agent 在当前对话中直接执行,没有分离的 playbook runtime 收尾。
            # 会话结束后把仍 running 的内联任务流转到终态,否则任务永久卡在 running。
            try:
                if _ws_id_for_bus and not ext_info.get("task_id"):
                    from gyra_serve.workspace.agent_tools._task_creator import (
                        finalize_inline_tasks,
                    )

                    # 会话行按 {base}_{round} 存储 conv_id,get_by_conv_id 精确匹配
                    # base 会落空;改按 conv_session_id(与任务 conv_session_id 一致)取
                    # 该会话全部轮次,以最新一轮的 state 作为收尾判定依据。
                    _convs = await self.gpts_conversations.get_by_session_id_asc(
                        conv_id
                    )
                    await finalize_inline_tasks(
                        system_app=self.system_app,
                        workspace_id=int(_ws_id_for_bus),
                        conv_id=conv_id,
                        conv_state=_convs[-1].state if _convs else None,
                    )
            except Exception as e:
                logger.warning(
                    f"[workspace] finalize inline tasks failed: {e}"
                )
            # 会话内剧本任务收尾(execution_mode=in_session):与后台任务共享公共收尾
            # finalize_task —— 物化产出(Artifact)、创建交付记录(Delivery)、介入检查、
            # 状态流转,结果统一进空间交付与飞轮事件。后台任务由 run_task 内部调用
            # 同一函数;此处仅处理会话内任务,避免重复收尾。
            try:
                _in_session_task_id = ext_info.get("task_id")
                if _ws_id_for_bus and _in_session_task_id:
                    from gyra_serve.task.service.service import (
                        TASK_SERVICE_COMPONENT_NAME, TaskService,
                    )
                    _task_service = self.system_app.get_component(
                        TASK_SERVICE_COMPONENT_NAME, TaskService,
                    )
                    _in_task = _task_service.get_by_id(int(_in_session_task_id))
                    if _in_task and (
                        _in_task.context or {}
                    ).get("execution_mode") == "in_session":
                        from gyra_serve.playbook.finalize import finalize_task
                        await finalize_task(
                            self.system_app,
                            int(_in_session_task_id),
                            agent_conv_id=agent_conv_id,
                            conv_id=conv_id,
                            created_by_agent=gpt_app.app_code,
                        )
            except Exception as e:
                logger.warning(
                    f"[workspace] finalize in-session task failed: {e}"
                )
            if _ws_id_for_bus:
                from gyra_serve.workspace.event_bus import (
                    unregister_workspace_queue,
                )

                unregister_workspace_queue(
                    int(_ws_id_for_bus), workspace_event_queue
                )
            digest(
                CHAT_LOGGER,
                "CHAT_DONE",
                conv_id=conv_id,
                app_code=gpts_name,
                user_code=user_code,
                succeed=succeed,
                cost_ms=current_ms() - start_ts,
                first_chunk_time=(first_chunk_time - start_ts)
                if first_chunk_time
                else 0,
            )
            # 取消注册任务:仅当 agent task 已结束时注销。
            # 断流时(SSE 关闭)agent 仍在后台运行,保留注册项,以便:
            # 1) stop_chat 仍可按 conv_id 找到并取消 task(真正终止);
            # 2) 后台 finalize(simple chat)在 agent 跑完后兜底注销。
            if task is not None and task.done():
                self.unregister_running_task(conv_id)
            # 确保文件句柄关闭
            if file_handle:
                file_handle.close()

    async def _save_message_to_db(self, msg):
        """保存消息到数据库.

        Args:
            msg: GptsMessage 消息对象
        """
        try:
            self.gpts_messages_dao.update_message(msg)
        except Exception as e:
            logger.error(f"Failed to save message {msg.message_id}: {e}")

    def get_or_build_agent_memory(self, conv_id: str, gyras_name: str) -> AgentMemory:
        session_memory = ShortTermMemory(buffer_size=10)
        agent_memory = AgentMemory(session_memory, gpts_memory=self.memory)
        return agent_memory

    async def _save_message_to_db(self, msg):
        """保存消息到数据库.

        Args:
            msg: GptsMessage 消息对象
        """
        try:
            self.gpts_messages_dao.update_message(msg)
            logger.debug(f"Saved message {msg.message_id} to database")
        except Exception as e:
            logger.error(f"Failed to save message {msg.message_id}: {e}")

    @trace("agent.get_or_build_memory", requires=["conv_id", "agent_id"])
    def get_or_build_gyra_memory(
        self,
        conv_id: str,
        agent_id: str,
        user_id: str,
        team_context: Optional[AgentContextType] = None,
    ) -> AgentMemory:
        """Get or build a Gyra memory instance for the given conversation ID.

        Args:
            conv_id:(str) conversation ID
            agent_id:(str) app_code
        """
        session_memory = ShortTermMemory(buffer_size=20)
        agent_memory = AgentMemory(
            memory=session_memory,
            gpts_memory=self.memory,
        )
        return agent_memory

    async def build_agent_by_app_code(
        self,
        app_code: str,
        context: AgentContext,
        agent_memory: AgentMemory = None,
        **kwargs,
    ) -> ConversableAgent:
        app_service = get_app_service()
        gpts_app: ServerResponse = await app_service.app_detail(
            app_code, building_mode=False
        )
        agent_memory = agent_memory or self.get_or_build_agent_memory(
            context.conv_id, gpts_app.app_name
        )
        resource_manager: ResourceManager = get_resource_manager()
        logger.info(
            f"[AgentChat] get_resource_manager() called, "
            f"_SYSTEM_APP is None: {get_resource_manager.__module__}, "
            f"rm_id={id(resource_manager)}, "
            f"type_to_resources_keys={list(resource_manager._type_to_resources.keys())}"
        )

        # Create scheduler for the agent
        cache = await self.memory.cache(context.conv_id)
        scheduler: Scheduler = LocalScheduler(cache=cache)

        return await self._build_agent_by_gpts(
            context=context,
            agent_memory=agent_memory,
            rm=resource_manager,
            app=gpts_app,
            scheduler=scheduler,
            **kwargs,
        )

    async def _have_agent_skill(
        self, app: GptsApp, dynamic_resources: Optional[List[AgentResource]] = None
    ):
        """检查应用是否包含 AgentSkill 资源"""
        if app.resource_tool and any(
            item.type in [AgentSkillResource.type(), GyraSkillResource.type()]
            for item in app.resource_tool
        ):
            return True
        if app.all_resources and any(
            item.type in [AgentSkillResource.type(), GyraSkillResource.type()]
            for item in app.all_resources
        ):
            return True
        if dynamic_resources and any(
            item.type in [AgentSkillResource.type(), GyraSkillResource.type()]
            for item in dynamic_resources
        ):
            return True
        return False

    async def _build_capability_pack(self, real_all_resources) -> Any:
        """统一构建 CapabilityPack（新标准资源协议）。

        所有 team_mode（SINGLE_AGENT/NATIVE_APP/AUTO_PLAN 等）统一走此入口，
        把 workspace_scene/ecp/datasource 等能力类资源从 AgentResource 列表构建为
        CapabilityPack，供主代理绑定承载。无 factory 的边角类资源留在旧 depend_resource
        路径。构建失败仅告警，不阻断主流程。
        """
        cap_pack = None
        try:
            from gyra.agent.capabilities.registry_factory import (
                get_default_factory_registry,
            )
            cap_pack = get_default_factory_registry().build_pack(
                real_all_resources, self.system_app
            )
            if cap_pack and cap_pack.sub_resources:
                logger.info(
                    f"[AgentChat] CapabilityPack built: "
                    f"{len(cap_pack.sub_resources)} caps "
                    f"({[getattr(c, 'capability_id', '?') for c in cap_pack.sub_resources]})"
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[AgentChat] build CapabilityPack failed: {e}")
        return cap_pack

    @trace("agent.build_agent_by_gpts")
    async def _build_agent_by_gpts(
        self,
        context: AgentContext,
        agent_memory: AgentMemory,
        rm: ResourceManager,
        app: GptsApp,
        scheduler: Optional[Scheduler],
        need_sandbox: bool = False,
        **kwargs,
    ) -> ConversableAgent:
        """Build a dialogue target agent through gpts configuration"""
        from datetime import datetime

        logger.info(
            f"_build_agent_by_gpts:{app.app_code},{app.app_name}, start:{datetime.now()}"
        )
        try:
            ## 检测动态资源 - prefer context.extra, fall back to kwargs
            extra_dict = context.extra or {}
            real_all_resources = extra_dict.get("dynamic_resources", []) or kwargs.get("dynamic_resources", [])

            # 使用全局缓存获取或创建 sandbox_manager，避免并行创建重复的沙箱
            sandbox_manager = await self._get_or_create_sandbox_manager(
                context, app, need_sandbox
            )

            # 初始化场景文件到沙箱（如果应用绑定了场景）
            # 注意：每个Agent有独立的场景文件目录，避免多Agent共享沙箱时的冲突
            if sandbox_manager and app.scenes and len(app.scenes) > 0:
                try:
                    from gyra.agent.core.sandbox.scene_initializer import (
                        initialize_scenes_for_agent,
                    )

                    scene_init_result = await initialize_scenes_for_agent(
                        app_code=app.app_code,
                        agent_name=app.app_name or app.app_code or "default_agent",
                        scenes=app.scenes,
                        sandbox_manager=sandbox_manager,
                    )
                    if scene_init_result.get("success"):
                        logger.info(
                            f"[AgentChat] Scene files initialized for {app.app_code}: "
                            f"{len(scene_init_result.get('files', []))} files "
                            f"in {scene_init_result.get('scenes_dir', 'unknown')}"
                        )
                    else:
                        logger.warning(
                            f"[AgentChat] Failed to initialize scene files for {app.app_code}: "
                            f"{scene_init_result.get('message')}"
                        )
                except Exception as scene_init_error:
                    logger.warning(
                        f"[AgentChat] Error initializing scene files for {app.app_code}: "
                        f"{scene_init_error}"
                    )
                    # 场景初始化失败不影响主流程

            # 统一治理：子 Agent 不再在此预构建/hire。子 Agent 一律以 AppResource
            # （type=app）注入 capability_pack/resource_map，派发时经 _resolve_app_code
            # 命中后由 GptAppResource._start_app 按需构建。app.details 与 workspace
            # 物化器（原 extra_agents）均已并入 AppResource 注入路径。
            team_mode = TeamMode(app.team_mode)
            ## 模型服务
            # LLM client is resolved by AIWrapper via ProviderRegistry at
            # call time (reading agent.llm config). llm_client is left None.
            # 多媒体 Agent 可无 llm_config（使用媒体生成模型），此处安全回退空配置。
            _app_llm = getattr(app, "llm_config", None)
            _llm_strategy = (
                getattr(_app_llm, "llm_strategy", None)
                if _app_llm is not None
                else None
            )
            _llm_config_kwargs = (
                {}
                if _llm_strategy is None
                else {"llm_strategy": LLMStrategyType(_llm_strategy)}
            )
            llm_config = LLMConfig(
                llm_client=self.llm_provider,
                **_llm_config_kwargs,
                strategy_context=(
                    getattr(_app_llm, "llm_strategy_value", None)
                    if _app_llm is not None
                    else None
                ),
                llm_param=getattr(_app_llm, "llm_param", None),
                mist_keys=getattr(_app_llm, "mist_keys", None),
            )

            real_all_resources.extend(app.all_resources)
            real_all_resources = await self.add_duplicate_allow_tools(
                real_all_resources
            )

            if team_mode == TeamMode.SINGLE_AGENT or TeamMode.NATIVE_APP == team_mode:
                # 统一治理：主代理恒由 app.agent 构建，并承载全部能力包
                # （workspace_scene/ecp 等资产）。子代理不再预构建/hire，资产加载与
                # 子代理无关，主代理独立承载全部资产。
                # 解析Agent别名（历史数据兼容）
                resolved_agent_type = resolve_agent_name(app.agent)
                if resolved_agent_type != app.agent:
                    logger.info(
                        f"[AgentChat] Resolved agent alias: {app.agent} -> {resolved_agent_type}"
                    )
                cls: Type[ConversableAgent] = self.agent_manage.get_by_name(
                    resolved_agent_type
                )

                ## 处理agent资源内容
                logger.info(
                    f"[AgentChat] real_all_resources before build: "
                    f"{[(r.type, r.name) for r in real_all_resources]}"
                )

                agent_context = deepcopy(context)
                agent_context.agent_app_code = app.app_code

                cap_pack = await self._build_capability_pack(real_all_resources)

                recipient = (
                    await cls()
                    .bind(agent_context)
                    .bind(agent_memory)
                    .bind(llm_config)
                    .bind(sandbox_manager)
                    .bind(cap_pack)
                    # .bind(prompt_template)
                    .bind(app.context_config)
                    .bind(ExtConfigHolder(ext_config=app.ext_config))
                    .bind(scheduler)
                    .build()
                )

                # 统一治理：不再 hire 预构建子 Agent 到主 Team（子 Agent 按需经
                # AppResource/_dispatch_to_app 构建），避免把主代理/子代理提前实例化。

                ## 处理Agent实例的基本信息
                temp_profile = recipient.profile.copy()
                temp_profile.desc = app.app_describe
                temp_profile.name = app.app_name
                temp_profile.avatar = app.icon
                if app.system_prompt_template is not None:
                    temp_profile.system_prompt_template = app.system_prompt_template
                if app.user_prompt_template:
                    temp_profile.user_prompt_template = app.user_prompt_template

                # 如果应用有场景，读取场景内容并注入到Agent的System Prompt
                if app.scenes and len(app.scenes) > 0 and sandbox_manager:
                    try:
                        scene_content = await self._load_and_inject_scenes(
                            agent_name=app.app_name or app.app_code or "default_agent",
                            scenes=app.scenes,
                            sandbox_manager=sandbox_manager,
                            agent_profile=temp_profile,
                        )
                        if scene_content:
                            logger.info(
                                f"[AgentChat] 场景内容已注入Agent: "
                                f"{len(scene_content)} 字符"
                            )
                    except Exception as e:
                        logger.warning(f"[AgentChat] 场景内容注入失败: {e}")
                        # 场景注入失败不影响主流程

                recipient.bind(temp_profile)

                # ========== Memory Integration Bundle Creation (V1 Agent) ==========
                # Parse resource_memory and create MemoryIntegrationBundle for V1 agents
                # Check both app.resource_memory (explicit field) and app.all_resources (merged list)
                memory_resources = []

                # Debug: Check what resources are available
                logger.info(
                    f"[AgentChat] Memory integration check for {app.app_code}: "
                    f"resource_memory={bool(app.resource_memory) if hasattr(app, 'resource_memory') else 'N/A'}, "
                    f"all_resources={len(app.all_resources) if hasattr(app, 'all_resources') and app.all_resources else 0}"
                )

                # Check explicit resource_memory field
                if hasattr(app, "resource_memory") and app.resource_memory and len(app.resource_memory) > 0:
                    memory_resources.extend(app.resource_memory)
                    logger.info(f"[AgentChat] Found {len(app.resource_memory)} items in resource_memory")

                # Also check all_resources for memory-type resources
                if hasattr(app, "all_resources") and app.all_resources:
                    for res in app.all_resources:
                        res_type = getattr(res, "type", "") or ""
                        logger.debug(f"[AgentChat] Checking resource type: {res_type}")
                        if res_type.lower() == "memory" or res_type == "MemoryResource":
                            # Avoid duplicates
                            if res not in memory_resources:
                                memory_resources.append(res)
                                logger.info(f"[AgentChat] Found memory resource in all_resources: type={res_type}")

                logger.info(f"[AgentChat] Total memory_resources found: {len(memory_resources)}")

                if memory_resources:
                    try:
                        from gyra.agent.core.memory.longterm_manager import (
                            LongTermMemoryConfig,
                        )
                        from gyra.storage.memory import LLMMemoryProcessor

                        # Parse from first memory resource item
                        memory_resource = memory_resources[0]
                        memory_value = getattr(memory_resource, "value", None)
                        logger.info(
                            f"[AgentChat] Parsing memory resource: "
                            f"value type={type(memory_value).__name__ if memory_value else 'None'}, "
                            f"value={memory_value[:200] if memory_value and isinstance(memory_value, str) else memory_value}"
                        )
                        memory_config = LongTermMemoryConfig.from_resource_value(memory_value)

                        config_memories = memory_config.memories if memory_config else None
                        logger.info(
                            f"[AgentChat] Memory config parsed: "
                            f"config={bool(memory_config)}, memories={len(config_memories) if config_memories else 0}"
                        )

                        if memory_config and memory_config.memories:
                            # Honour MemoryParameters long-term memory switches.
                            # If both use and collection are disabled, skip the
                            # whole memory bundle so we do not inject memories
                            # into the prompt or run background hooks.
                            if (
                                not memory_config.enable_long_term_use
                                and not memory_config.enable_collect_long_term
                            ):
                                logger.info(
                                    f"[AgentChat] Memory resource present but both "
                                    f"enable_long_term_use and enable_collect_long_term "
                                    f"are disabled for {app.app_code}; skipping bundle."
                                )
                                return recipient

                            # Memory store factory: prefer knowledge-vault
                            # (each agent gets its own llm-wiki Space as the
                            # 4-tier hermes memory sink). Fall back to
                            # SimpleSQLite if the Space is unavailable
                            # (migration period / missing knowledge service).
                            memory_bundle = None
                            try:
                                from gyra_ext.storage.memory.knowledge_vault_store import (
                                    KnowledgeVaultMemoryConfig,
                                    KnowledgeVaultMemoryStore,
                                )
                                from gyra.agent.core.memory.longterm_manager import (
                                    LongTermMemoryManager,
                                    MemoryIntegrationBundle,
                                    MemorySpaceStrategy,
                                )
                                from gyra_serve.knowledge.service.service import (
                                    Service as KnowledgeService,
                                )

                                memory_stores = {}
                                strategies = {}
                                ks = None
                                try:
                                    ks = KnowledgeService.get_instance(self.system_app)
                                except Exception as ks_e:
                                    logger.warning(
                                        f"[AgentChat] KnowledgeService unavailable: {ks_e}"
                                    )

                                for mem_item in memory_config.memories:
                                    mem_id = mem_item.get("memory_id")
                                    if not mem_id:
                                        continue

                                    store = None
                                    space_slug = (
                                        mem_item.get("space_slug")
                                        or (mem_id.startswith("memory-") and mem_id)
                                        or None
                                    )
                                    store_type = mem_item.get("store_type")

                                    # Try knowledge-vault path first when we
                                    # have a slug OR the memory_id looks like
                                    # a slug (migration: old apps without
                                    # explicit store_type but slug-shaped id).
                                    if ks is not None and space_slug and (
                                        store_type == "knowledge_vault"
                                        or mem_id.startswith("memory-")
                                    ):
                                        try:
                                            vault = await ks.get_vault(space_slug)
                                            kv_cfg = KnowledgeVaultMemoryConfig(
                                                space_slug=space_slug,
                                                enable_kg=memory_config.enable_kg,
                                            )
                                            store = KnowledgeVaultMemoryStore(
                                                config=kv_cfg,
                                                vault=vault,
                                                system_app=self.system_app,
                                            )
                                            logger.info(
                                                f"[AgentChat] Created KnowledgeVaultMemoryStore for slug={space_slug}"
                                            )
                                            # 注册 idle curator cron job（幂等：
                                            # job_id 固定，重复注册时 get_job 命中即跳过）
                                            try:
                                                await _register_memory_curator_cron(
                                                    self.system_app, space_slug
                                                )
                                            except Exception as cron_e:
                                                logger.warning(
                                                    f"[AgentChat] register memory curator "
                                                    f"cron for slug={space_slug} failed: {cron_e}"
                                                )
                                        except Exception as kv_e:
                                            logger.warning(
                                                f"[AgentChat] KnowledgeVault store creation failed "
                                                f"for slug={space_slug}: {kv_e}; falling back to SimpleSQLite"
                                            )
                                            store = None

                                    if store is None:
                                        from gyra_ext.storage.memory.simple_sqlite_store import (
                                            SimpleSQLiteMemoryConfig,
                                            SimpleSQLiteMemoryStore,
                                        )
                                        fallback_cfg = SimpleSQLiteMemoryConfig(
                                            enable_kg=memory_config.enable_kg,
                                        )
                                        store = SimpleSQLiteMemoryStore(
                                            config=fallback_cfg,
                                            index_name=mem_id,
                                        )
                                        logger.info(
                                            f"[AgentChat] Created SimpleSQLite store for {mem_id}"
                                        )

                                    memory_stores[mem_id] = store
                                    strategies[mem_id] = MemorySpaceStrategy(
                                        space_id=mem_id,
                                        auto_extraction=memory_config.auto_memory,
                                        kg_extraction=memory_config.enable_kg,
                                    )

                                if memory_stores:
                                    from gyra.storage.memory.recall_tracker import RecallTracker
                                    from gyra.storage.memory.promotion import MemoryPromotionEngine
                                    from gyra.storage.memory.hybrid_search import HybridSearchEngine
                                    from gyra.storage.memory.lifecycle import DefaultLifecycleHooks
                                    from gyra.storage.memory.snapshot import FrozenSnapshotManager

                                    # 为每个 space 建 LLMMemoryProcessor。
                                    # 优先用 self.llm_provider（chat 自己的 working LLM
                                    # client）；生产路径下它是 None（controller.py
                                    # 用 SimpleAgentChat(self.system_app) 实例化时不
                                    # 注入），此时从 ModelConfigCache 取第一个可用
                                    # 模型，构造 AIWrapper 让它跑一遍 _init_provider
                                    # 的 secrets/env/placeholder 解析，再取其 _provider。
                                    # LLMProvider ABC 与 LLMClient 在 generate(req) /
                                    # models() 上签名一致，可鸭子类型喂给
                                    # LLMMemoryProcessor。
                                    processors = {}
                                    llm_client = self.llm_provider
                                    if llm_client is None:
                                        try:
                                            from gyra.agent.util.llm.llm_client import (
                                                AIWrapper,
                                            )
                                            from gyra.agent.util.llm.model_config_cache import (
                                                ModelConfigCache,
                                            )
                                            from gyra.agent.core.llm_config import (
                                                AgentLLMConfig,
                                            )

                                            all_models = (
                                                ModelConfigCache.get_all_models()
                                            )
                                            if all_models:
                                                model_name = all_models[0]
                                                cfg_dict = (
                                                    ModelConfigCache.get_config(
                                                        model_name
                                                    )
                                                    or {}
                                                )
                                                temp_llm_config = (
                                                    AgentLLMConfig.from_dict(
                                                        cfg_dict
                                                    )
                                                )
                                                wrapper = AIWrapper(
                                                    llm_config=temp_llm_config
                                                )
                                                llm_client = wrapper._provider
                                                if llm_client is not None:
                                                    logger.info(
                                                        f"[AgentChat] Built LLMProvider "
                                                        f"(provider={temp_llm_config.provider}, "
                                                        f"model={temp_llm_config.model}) "
                                                        f"via AIWrapper for memory processor"
                                                    )
                                                else:
                                                    logger.warning(
                                                        "[AgentChat] AIWrapper resolved no "
                                                        "provider; tier2/tier3 LLM "
                                                        "extraction will be skipped"
                                                    )
                                            else:
                                                logger.warning(
                                                    "[AgentChat] ModelConfigCache empty; "
                                                    "tier2/tier3 LLM extraction will be skipped"
                                                )
                                        except Exception as e:
                                            logger.warning(
                                                f"[AgentChat] Failed to build LLMProvider "
                                                f"via AIWrapper: {e}"
                                            )
                                            llm_client = None

                                    if llm_client is not None:
                                        for mem_id in memory_stores.keys():
                                            try:
                                                processors[mem_id] = (
                                                    LLMMemoryProcessor(
                                                        llm_client=llm_client
                                                    )
                                                )
                                            except Exception as proc_e:
                                                logger.warning(
                                                    f"[AgentChat] LLMMemoryProcessor "
                                                    f"creation failed for {mem_id}: {proc_e}"
                                                )
                                        logger.info(
                                            f"[AgentChat] Built {len(processors)} "
                                            f"LLMMemoryProcessor(s) for memory spaces"
                                        )
                                    else:
                                        logger.warning(
                                            "[AgentChat] no llm_provider and no "
                                            "ModelConfigCache fallback; tier2/tier3 "
                                            "LLM extraction will be skipped"
                                        )

                                    # 持久化召回统计（SQLite，跟随 gyra
                                    # 本地存储惯例 data/memory/），重启后
                                    # promotion 不再冷启动。
                                    recall_tracker = RecallTracker(
                                        db_path=os.path.join(
                                            os.getcwd(),
                                            "data",
                                            "memory",
                                            "recall_tracker.db",
                                        )
                                    )
                                    promotion_engine = MemoryPromotionEngine(
                                        recall_tracker=recall_tracker,
                                    )
                                    lifecycle_hooks = DefaultLifecycleHooks(
                                        memory_store=next(
                                            iter(memory_stores.values()), None
                                        )
                                    )
                                    snapshot_manager = FrozenSnapshotManager()
                                    hybrid_search = HybridSearchEngine()
                                    # 把全部组件注入 manager —— curate_session 通过
                                    # getattr(self, "_promotion_engine", None) 等读取，
                                    # 不注入则 tier3 promotion/snapshot 全是 None 而变成 0ms no-op。
                                    manager = LongTermMemoryManager(
                                        config=memory_config,
                                        memory_stores=memory_stores,
                                        processors=processors,
                                        strategies=strategies,
                                        recall_tracker=recall_tracker,
                                        hybrid_search_engine=hybrid_search,
                                        lifecycle_hooks=lifecycle_hooks,
                                        snapshot_manager=snapshot_manager,
                                        promotion_engine=promotion_engine,
                                    )
                                    memory_bundle = MemoryIntegrationBundle(
                                        config=memory_config,
                                        manager=manager,
                                        processors=processors,
                                        strategies=strategies,
                                        recall_tracker=recall_tracker,
                                        hybrid_search=hybrid_search,
                                        lifecycle_hooks=lifecycle_hooks,
                                        snapshot_manager=snapshot_manager,
                                        promotion_engine=promotion_engine,
                                    )
                                    logger.info(
                                        f"[AgentChat] Memory bundle created with {len(memory_stores)} stores"
                                    )
                            except Exception as bundle_e:
                                logger.warning(f"[AgentChat] Memory bundle creation failed: {bundle_e}")

                            if memory_bundle:
                                # Inject bundle to agent via private attribute
                                recipient._memory_bundle = memory_bundle
                                # Register the bundle with the conversation's
                                # HookManager so the memory dispatcher can
                                # find it, and so the default memory hooks
                                # (tier 1/2/3) get appended — either now
                                # (if HookManager already exists) or
                                # deferred to init_hook_manager.
                                try:
                                    conv_id = recipient.agent_context.conv_id
                                    recipient.memory.gpts_memory.register_memory_bundle(
                                        conv_id, memory_bundle
                                    )
                                except Exception as hook_e:
                                    logger.warning(
                                        f"[AgentChat] Memory hook registration failed: {hook_e}"
                                    )

                                # Inject memory tools so the agent can actively
                                # search/save memories and query/edit the KG.
                                try:
                                    if memory_bundle.manager.has_stores():
                                        memory_tool_pack = MemoryToolPack(
                                            memory_stores=memory_bundle.manager.memory_stores,
                                            wing=memory_config.wing
                                            if memory_config
                                            else "default",
                                        )
                                        await memory_tool_pack.preload_resource()

                                        # Phase D:记忆工具包包装为 MCPCapability
                                        # (工具已 preload,纯 declare 投影),
                                        # 挂进 capability_pack 供 facade 渲染。
                                        from gyra.core.interface.resource.capability import (
                                            CapabilityPack,
                                        )
                                        from gyra_serve.agent.capabilities.mcp import (
                                            MCPCapability,
                                        )

                                        memory_cap = MCPCapability.from_tools(
                                            list(memory_tool_pack.sub_resources),
                                            name="memory_tools",
                                        )
                                        if recipient.capability_pack is None:
                                            recipient.capability_pack = CapabilityPack(
                                                [memory_cap]
                                            )
                                        else:
                                            recipient.capability_pack.add(memory_cap)
                                        logger.info(
                                            f"[AgentChat] Memory tools injected for "
                                            f"{app.app_code}: "
                                            f"{len(memory_bundle.manager.memory_stores)} stores"
                                        )
                                except Exception as tool_e:
                                    logger.warning(
                                        f"[AgentChat] Memory tool injection failed: {tool_e}"
                                    )

                                logger.info(
                                    f"[AgentChat] Memory bundle created for {app.app_code}: "
                                    f"{len(memory_bundle.manager.memory_stores)} stores"
                                )
                    except Exception as e:
                        logger.warning(f"[AgentChat] Failed to create memory bundle: {e}")

                return recipient
            elif TeamMode.AUTO_PLAN == team_mode:
                agent_manager = get_agent_manager()
                auto_team_ctx = app.team_context
                # team_context 可能是 dict（sync_app_detail 序列化后）或 AutoTeamContext 对象
                teamleader = (
                    auto_team_ctx.get("teamleader")
                    if isinstance(auto_team_ctx, dict)
                    else getattr(auto_team_ctx, "teamleader", None)
                )

                manager_cls: Type[ConversableAgent] = agent_manager.get_by_name(
                    teamleader
                )
                manager = manager_cls()

                # 统一治理：与 SINGLE_AGENT/NATIVE_APP 一致，主代理也承载全部能力包
                # （workspace_scene/ecp 等资产）。AUTO_PLAN 主代理此前只 bind 旧资源
                # depend_resource（对 workspace_scene/ecp 均失败），导致场景空间资产
                # 无法注入系统提示词；此处统一补上 CapabilityPack 绑定，确保资产可感知。
                cap_pack = await self._build_capability_pack(real_all_resources)
                if cap_pack is not None:
                    manager.bind(cap_pack)

                agent_context = deepcopy(context)
                agent_context.agent_app_code = app.app_code

                manager = (
                    await manager.bind(agent_context)
                    .bind(llm_config)
                    .bind(agent_memory)
                    .bind(app.context_config)
                    .bind(sandbox_manager)
                    .bind(ExtConfigHolder(ext_config=app.ext_config))
                    .bind(scheduler)
                    .build()
                )

                ## 处理Agent实例的基本信息
                temp_profile = manager.profile.copy()
                temp_profile.desc = app.app_describe
                temp_profile.name = app.app_name
                temp_profile.avatar = app.icon
                if app.system_prompt_template is not None:
                    temp_profile.system_prompt_template = app.system_prompt_template
                if app.user_prompt_template:
                    temp_profile.user_prompt_template = app.user_prompt_template
                manager.bind(temp_profile)

                # 统一治理：不再 hire 预构建子 Agent（子 Agent 按需经
                # AppResource/_dispatch_to_app 构建）。
                logger.info(
                    f"_build_agent_by_gpts return:{manager.profile.name},{manager.profile.desc},{id(manager)}"
                )

                return manager
            else:
                raise ValueError(f"Unknown Agent Team Mode!{team_mode}")

        finally:
            logger.info(
                f"_build_agent_by_gpts:{app.app_code},{app.app_name}, end:{datetime.now()}"
            )

    async def _load_and_inject_scenes(
        self,
        agent_name: str,
        scenes: List[str],
        sandbox_manager: SandboxManager,
        agent_profile: Any,
    ) -> str:
        """
        从沙箱加载场景内容并注入到Agent的System Prompt

        Args:
            agent_name: Agent名称
            scenes: 场景ID列表
            sandbox_manager: 沙箱管理器
            agent_profile: Agent配置对象

        Returns:
            注入的场景内容
        """
        from gyra.agent.core.sandbox.scene_initializer import get_scene_initializer

        initializer = get_scene_initializer(sandbox_manager)
        scene_contents = []

        # 读取每个场景文件
        for scene_id in scenes:
            try:
                content = await initializer.read_scene_file(agent_name, scene_id)
                if content:
                    # 解析YAML Front Matter，提取有效内容
                    parts = content.split("---\n")
                    if len(parts) >= 3:
                        # 有Front Matter，提取body部分
                        body = "---\n".join(parts[2:])
                        scene_contents.append(f"## 场景: {scene_id}\n\n{body}")
                    else:
                        # 没有Front Matter，使用全部内容
                        scene_contents.append(f"## 场景: {scene_id}\n\n{content}")

                    logger.debug(f"[AgentChat] 加载场景内容: {scene_id}")
            except Exception as e:
                logger.warning(f"[AgentChat] 加载场景 {scene_id} 失败: {e}")

        if not scene_contents:
            return ""

        # 构建场景提示词
        scene_separator = "\n\n---\n\n"
        scene_prompt = f"""# 场景定义

你是根据以下场景定义来协助用户的智能助手。请严格遵循场景定义中的角色设定、工作流程和工具使用规范。

{scene_separator.join(scene_contents)}

---

"""

        # 注入到Agent的System Prompt
        original_prompt = agent_profile.system_prompt_template or ""
        agent_profile.system_prompt_template = scene_prompt + original_prompt

        return scene_prompt

    async def add_duplicate_allow_tools(self, resources: List[AgentResource]):
        if not resources:
            return []
        gpts_tool_dao = GptsToolDao()
        for resource in resources:
            if resource.type not in [AgentSkillResource.type()]:
                continue
            value = json.loads(resource.value)
            tool_id = value.get("tool_id")
            if not tool_id:
                continue
            gpt_tool = gpts_tool_dao.get_tool_by_tool_id(tool_id)
            if not gpt_tool:
                continue
            config = json.loads(gpt_tool.config)
            release, debug = config.get("release", None), config.get("debug", None)
            if release:
                allow_tools = release.get("metadata", {}).get("allowed-tools")
            elif debug:
                allow_tools = debug.get("metadata", {}).get("allowed-tools")
            else:
                continue
            if allow_tools:
                skill_allow_tools = await self._get_skill_allow_tools_resources(
                    allow_tools
                )
                resources.extend(skill_allow_tools)
        seen_combinations = set()
        unique_resources = []
        for resource in resources:
            key = resource.unique_id
            if not key:
                unique_resources.append(resource)
                continue
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_resources.append(resource)
        return unique_resources

    @staticmethod
    def _preserve_scene_resources(
        scene_resources: List[AgentResource],
        rebuilt_resources: Optional[List[AgentResource]],
    ) -> List[AgentResource]:
        """保留场景装配器预注入的资源,不被 chat_in_params 重建覆盖。

        chat_in_params_to_resource 从空重建且只读 extraTools,不携带已有
        ``ext_info["dynamic_resources"]``(场景资源 workspace_scene/ecp 由 api_v1
        _assemble_scene_resources / playbook runtime 预注入)。直接用重建结果覆盖
        会丢掉场景 ECP 能力。契约:preserved/extended, never overwritten(见
        playbook/runtime.py)。场景资源置前;最终去重由下游 add_duplicate_allow_tools/
        build_pack 处理。
        """
        if not scene_resources:
            return rebuilt_resources or []
        return list(scene_resources) + (rebuilt_resources or [])

    def _extract_default_datasources(
        self, gpts_app: GptsApp
    ) -> List[AgentResource]:
        """Extract default bound datasource resources from app's resource_tool.

        These are databases bound in the app editing page (not dynamically
        added via chat_in_params). We extract them here so they go through the
        same dynamic_resources path as chat_in_params resources, ensuring
        proper prompt injection and tool registration.
        """
        results = []
        if not gpts_app.resource_tool:
            return results
        for tool_resource in gpts_app.resource_tool:
            if tool_resource.type == "datasource":
                results.append(tool_resource)
        if results:
            logger.info(
                f"[AgentChat] Extracted {len(results)} default datasource "
                f"resources from app config resource_tool"
            )
        return results

    async def chat_in_params_to_resource(
        self,
        chat_in_params: Optional[List[ChatInParamValue]],
        ext_info: Optional[dict] = None,
    ) -> Optional[List[AgentResource]]:
        dynamic_resources = []
        if chat_in_params:
            for chat_in_param in chat_in_params:
                if chat_in_param.param_type == "resource":
                    sub_type = chat_in_param.sub_type
                    param_value = chat_in_param.param_value
                    # Map legacy type names (e.g. 'database') to ResourceManager aliases
                    sub_type = _RESOURCE_TYPE_ALIASES.get(sub_type, sub_type)

                    if sub_type == "mcp(gyra)":
                        try:
                            if isinstance(param_value, str):
                                value_data = json.loads(param_value)
                            else:
                                value_data = param_value

                            mcp_code = (
                                value_data.get("mcp_code")
                                if isinstance(value_data, dict)
                                else value_data
                            )
                            mcp_name = (
                                value_data.get("name")
                                if isinstance(value_data, dict)
                                else None
                            )

                            if mcp_code:
                                from gyra_serve.agent.resource.tool.mcp_collect import (
                                    get_mcp_info,
                                )

                                mcp_info = get_mcp_info(mcp_code)
                                if mcp_info:
                                    mcp_value = {
                                        "name": mcp_name or mcp_info.name or mcp_code,
                                        "mcp_code": mcp_code,
                                        "mcp_servers": mcp_info.sse_url or "",
                                        "headers": mcp_info.sse_headers or {},
                                        "source": mcp_info.type or "faas",
                                        "timeout": 120,
                                    }
                                    mcp_resource = AgentResource.from_dict(
                                        {
                                            "type": "mcp(gyra)",
                                            "name": mcp_name or f"MCP[{mcp_code}]",
                                            "value": json.dumps(
                                                mcp_value, ensure_ascii=False
                                            ),
                                        }
                                    )
                                    dynamic_resources.append(mcp_resource)
                                    logger.info(
                                        f"Added MCP resource from chat_in_params: {mcp_code}"
                                    )
                                else:
                                    logger.warning(
                                        f"MCP info not found for code: {mcp_code}"
                                    )
                        except Exception as e:
                            logger.warning(f"Failed to process MCP resource: {e}")
                    else:
                        # Skip FILE_RESOURCES (common_file, text_file, excel_file, image_file)
                        # These are handled separately in _dispatch_uploaded_files
                        if sub_type not in FILE_RESOURCES:
                            dynamic_resources.append(
                                AgentResource.from_dict(
                                    {
                                        "type": sub_type,
                                        "name": f"用户选择了[{sub_type}]资源",
                                        "value": param_value,
                                    }
                                )
                            )
                        else:
                            logger.info(
                                f"Skipping file resource type {sub_type} in chat_in_params_to_resource, "
                                f"will be handled in _dispatch_uploaded_files"
                            )

                    if chat_in_param.sub_type == GyraSkillResource.type():
                        skill_param_value = chat_in_param.param_value
                        if isinstance(skill_param_value, str):
                            skill_config = json.loads(skill_param_value)
                        else:
                            skill_config = skill_param_value
                        config_str = skill_config.get("config")
                        if config_str:
                            metadata = (
                                json.loads(config_str)
                                .get("release", {})
                                .get("metadata", {})
                            )
                        else:
                            metadata = {}
                        allow_tools = metadata.get("allowed-tools")
                        allow_tools_resources = (
                            await self._get_skill_allow_tools_resources(allow_tools)
                        )
                        if allow_tools_resources:
                            dynamic_resources.extend(allow_tools_resources)
        if ext_info:
            ext_resources = await self._get_resource_from_ext_info(ext_info)
            dynamic_resources.extend(ext_resources)
        return dynamic_resources

    async def _get_skill_allow_tools_resources(
        self, allow_tools: Optional[Union[str, List[str]]]
    ):
        """根据 Skill 资源的 allow tools 参数获取对应的 Tool 资源列表"""
        try:
            if allow_tools is None:
                return []
            if isinstance(allow_tools, str):
                allow_tools = [
                    tool.strip() for tool in allow_tools.split(",") if tool.strip()
                ]
            all_tool_names = []
            mcp_with_allow_tools = {}
            for tool_name in allow_tools:
                if tool_name.startswith("mcp."):
                    split_list = tool_name.split(".")
                    mcp_name = split_list[1] if len(split_list) > 1 else None
                    mcp_allow_tool = split_list[2] if len(split_list) > 2 else None
                    if mcp_allow_tool:
                        if mcp_name in mcp_with_allow_tools:
                            mcp_with_allow_tools[mcp_name].append(mcp_allow_tool)
                        else:
                            mcp_with_allow_tools[mcp_name] = [mcp_allow_tool]
                    all_tool_names.append(mcp_name)
                else:
                    all_tool_names.append(tool_name)

            tool_resources = []
            gpts_tool_dao = GptsToolDao()
            if all_tool_names:
                tools = await gpts_tool_dao.get_tools_by_names(all_tool_names)
                for tool in tools:
                    try:
                        tool_config = (
                            json.loads(tool.config)
                            if isinstance(tool.config, str)
                            else tool.config
                        )
                        value = {
                            "name": tool.tool_name,
                            "tool_id": tool.tool_id,
                            "description": tool_config.get("description", ""),
                        }
                        match tool.type:
                            case "MCP":
                                resource_type = "tool(mcp(sse))"
                                value["headers"] = tool_config.get("headers", {})
                                value["source"] = tool_config.get("source", "faas")
                                value["timeout"] = tool_config.get("timeout", 120)
                                value["mcp_servers"] = tool_config.get("url", "")
                                if tool.tool_name in mcp_with_allow_tools:
                                    value["allow_tools"] = mcp_with_allow_tools[
                                        tool.tool_name
                                    ]
                            case "HTTP" | "TR" | "LOCAL":
                                resource_type = f"tool({tool.type.lower()})"
                            case "SKILL":
                                resource_type = "agent_skill"
                                value["config"] = tool.config
                            case _:
                                logger.warning(f"Unknown tool type: {tool.type}")
                                continue
                        tool_resource = AgentResource.from_dict(
                            {
                                "type": resource_type,
                                "name": tool.tool_name,
                                "value": json.dumps(value, ensure_ascii=False),
                                "is_dynamic": True,
                                "context": None,
                            }
                        )
                        tool_resources.append(tool_resource)
                        logger.info(
                            f"Added tool resource from allow_tools [{resource_type}]: {tool.tool_name}"
                        )
                    except Exception as e:
                        logger.error(f"Skill Failed to load tool {tool.tool_name}: {e}")
            return tool_resources
        except Exception as e:
            logger.error(
                f"Failed to load allow_tools for skill {self.name}: {e}", exc_info=True
            )

    async def _get_resource_from_ext_info(self, ext_info: Optional[dict]):
        """Solve front chat in params."""
        dynamic_resources = []
        if not ext_info or "extraTools" not in ext_info:
            return dynamic_resources

        extra_tools = ext_info.get("extraTools")
        if not extra_tools or not isinstance(extra_tools, list):
            return dynamic_resources

        for tool in extra_tools:
            try:
                name, tool_id, id, type = (
                    tool.get("toolName"),
                    tool.get("toolId"),
                    tool.get("id", None),
                    tool.get("type"),
                )
                protocol, description, config = (
                    tool.get("protocol"),
                    tool.get("description"),
                    tool.get("config"),
                )
                value = {
                    "name": name,
                    "tool_id": tool_id,
                    "description": description,
                    "nex_tool_id": id,
                }
                if type == "LOCAL":
                    resource_type = "tool(local)"
                elif type == "API":
                    if protocol == "HTTP":
                        resource_type = "tool(http)"
                    elif protocol == "TR":
                        resource_type = "tool(tr)"
                    else:
                        resource_type = "tool(http)"
                elif type == "MCP":
                    resource_type = "tool(mcp(sse))"
                    if config:
                        config = json.loads(config)
                        value["headers"] = config.get("headers", {})
                        value["source"] = config.get("source", "faas")
                        value["timeout"] = config.get("timeout", 120)
                        value["mcp_servers"] = config.get("url", "")
                elif type == "SKILL":
                    resource_type = "agent_skill"
                    if config:
                        value["config"] = config
                        metadata = (
                            json.loads(config).get("release", {}).get("metadata", {})
                        )
                        allow_tools = metadata.get("allowed-tools")
                        if allow_tools:
                            allow_tool_resources = (
                                await self._get_skill_allow_tools_resources(allow_tools)
                            )
                            dynamic_resources.extend(allow_tool_resources)
                else:
                    logger.warning(f"Unknown tool type: {type}")
                    continue
                agent_resource = AgentResource(
                    type=resource_type,
                    name=name,
                    value=json.dumps(value, ensure_ascii=False),
                    unique_id=tool_id,
                    is_dynamic=True,
                )
                dynamic_resources.append(agent_resource)
                logger.info(f"Added dynamic tool resource: {name}")
            except Exception as e:
                logger.exception(f"Failed to load tool: {e}")
                continue

        seen_combinations = set()
        unique_resources = []
        for resource in dynamic_resources:
            key = (resource.name, resource.type)
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_resources.append(resource)
        return unique_resources

    def chat_in_params_to_context(
        self, chat_in_params: Optional[List[ChatInParamValue]], gpts_app: GptsApp
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """处理对话输出参数"""
        context = {}
        ## 输入层参数转Agent上下文参数
        ### 1.资源类型统一变成对话上下文参数
        ### 2.其他类型统一变成环境上下文参数
        llm_context = {}
        env_context = {}
        if chat_in_params:
            for param in chat_in_params:
                if AppParamType.Resource.value == param.param_type:
                    if param.sub_type not in FILE_RESOURCES:
                        # Map legacy type names (e.g. 'database') to ResourceManager aliases
                        mapped_sub_type = _RESOURCE_TYPE_ALIASES.get(param.sub_type, param.sub_type)
                        try:
                            if isinstance(param.param_value, str):
                                value_obj = json.loads(param.param_value)
                                if isinstance(value_obj, list):
                                    r_value = value_obj[0]
                                else:
                                    r_value = value_obj
                            else:
                                r_value = param.param_value
                            logger.info("加载用户指定的资源")
                            chat_in_resource = AgentResource.from_dict(
                                {
                                    "type": mapped_sub_type,
                                    "name": f"对话选择[{mapped_sub_type}]资源",
                                    "value": r_value,
                                }
                            )
                            if not gpts_app.all_resources:
                                gpts_app.all_resources = []
                            gpts_app.all_resources.append(chat_in_resource)
                            llm_context[mapped_sub_type] = chat_in_resource
                        except Exception as e:
                            logger.warning(f"选择资源无法转换！{chat_in_params}", e)
                    else:
                        llm_context[param.sub_type] = param.param_value
                else:
                    llm_context[param.param_type] = param.param_value
                    if param.param_type == AppParamType.Model.value:
                        logger.info("用户指定了模型，优先使用")
                        # 多媒体 Agent 无 llm_config（使用媒体生成模型），跳过 LLM 模型覆盖
                        if gpts_app.llm_config is not None:
                            gpts_app.llm_config.llm_strategy_value = [
                                param.param_value
                            ]

                    elif param.param_type == AppParamType.Temperature.value:
                        temperature = param.param_value
                        logger.info("用户指定了模型Temperature，优先使用")

                    elif param.param_type == AppParamType.MaxNewTokens.value:
                        max_tokens = param.param_value
                        logger.info("用户指定了模型MaxTokens，优先使用")

                    elif param.param_type == AppParamType.TopP.value:
                        logger.info("用户指定了模型TopP，优先使用")

                    elif param.param_type == AppParamType.ReasoningEffort.value:
                        logger.info("用户指定了模型思考深度(reasoning_effort)，优先使用")
        return llm_context, env_context

    async def _dispatch_uploaded_files(
        self,
        chat_in_params: Optional[List[ChatInParamValue]],
        conv_id: str,
        user_query: HumanMessage,
        staff_no: Optional[str] = None,
        model_name: Optional[str] = None,
        prefer_direct_media: bool = False,
    ) -> Optional[HumanMessage]:
        """处理上传的文件，根据类型分流.

        - 图片/音频/视频文件 → 直接给多模态模型消费
        - 其他文件 → 加入AgentFileSystem并同步写入沙箱

        Args:
            chat_in_params: 对话输入参数
            conv_id: 会话ID
            user_query: 用户消息
            staff_no: 用户工号 (用于获取 sandbox)
            model_name: 当前 agent 所用模型名（按模型能力决定是否直接消费）
            prefer_direct_media: 是否为多媒体 agent（媒体文件直接消费）

        Returns:
            更新后的用户消息（如果需要），如果无需更新则返回None
        """
        if not chat_in_params:
            return None

        file_resources = []
        for param in chat_in_params:
            if param.param_type == "resource":
                # Map legacy type aliases for consistent comparison
                mapped_sub_type = _RESOURCE_TYPE_ALIASES.get(param.sub_type, param.sub_type)
                # Only process file-type resources (images, text, excel, common files).
                # Non-file resources (datasource, knowledge, skill, mcp) are handled
                # by chat_in_params_to_resource / chat_in_params_to_context.
                if mapped_sub_type not in FILE_RESOURCES:
                    logger.debug(
                        f"[FileDispatch] Skipping non-file resource type: sub_type={param.sub_type} (mapped: {mapped_sub_type})"
                    )
                    continue
                try:
                    logger.debug(
                        f"[FileDispatch] Processing param: sub_type={param.sub_type}, param_value type={type(param.param_value)}"
                    )

                    if isinstance(param.param_value, str):
                        value_data = json.loads(param.param_value)
                    else:
                        value_data = param.param_value

                    logger.debug(
                        f"[FileDispatch] Parsed value_data type={type(value_data)}, content={value_data}"
                    )

                    if isinstance(value_data, list):
                        file_resources.extend(value_data)
                    elif isinstance(value_data, dict):
                        file_resources.append(value_data)
                except Exception as e:
                    logger.warning(f"Failed to parse file resource: {e}")

        logger.info(
            f"[FileDispatch] Total file_resources count: {len(file_resources)}, content: {file_resources}"
        )

        if not file_resources:
            return None

        sandbox_client = None
        # 使用与 _get_or_create_sandbox_manager 相同的 key 格式（此函数无 workspace_id，回退 conv 维度）
        sandbox_key = _sandbox_key(None, conv_id, staff_no)
        sandbox_manager = GlobalSandboxManagerCache.get(sandbox_key)
        if sandbox_manager and sandbox_manager.client:
            sandbox_client = sandbox_manager.client

        from gyra_serve.agent.utils.file_dispatch import (
            process_uploaded_files,
            FileDispatchType,
        )
        from gyra.core.interface.media import MediaContent
        from gyra.core.interface.file import FileStorageClient

        # 获取 FileStorageClient 实例
        file_storage_client = None
        try:
            file_storage_client = FileStorageClient.get_instance(
                self.system_app, default_component=None
            )
        except Exception as e:
            logger.debug(f"FileStorageClient not available: {e}")

        media_contents, file_infos = await process_uploaded_files(
            file_resources=file_resources,
            conv_id=conv_id,
            sandbox_client=sandbox_client,
            system_app=self.system_app,
            file_storage_client=file_storage_client,
            model_name=model_name,
            prefer_direct_media=prefer_direct_media,
        )

        if not media_contents:
            return None

        existing_content = []
        if isinstance(user_query.content, str) and user_query.content:
            existing_content.append(MediaContent.build_text(user_query.content))
        elif isinstance(user_query.content, list):
            existing_content = user_query.content

        new_content = media_contents + existing_content

        multimodal_files = [
            f for f in file_infos if f.dispatch_type == FileDispatchType.MULTIMODAL
        ]
        sandbox_files = [
            f for f in file_infos if f.dispatch_type == FileDispatchType.SANDBOX
        ]

        if multimodal_files:
            logger.info(
                f"[FileDispatch] Processed {len(multimodal_files)} multimodal files"
            )
        if sandbox_files:
            logger.info(f"[FileDispatch] Processed {len(sandbox_files)} sandbox files")

        return HumanMessage(content=new_content)

    def _set_waiting_reason(self, conv_uid: str, waiting_reason: Optional[str]) -> None:
        """在 gpts_conversations.extra 持久化等待原因。

        WAITING 时写入具体原因（await_user_question / await_tool_authorization /
        await_async_tasks / await_subagents），供 resume 时（aggregation_chat → 
        initiate_chat → base_agent._update_recovering）决策是否重放；
        置 None 时清空该字段，避免终态会话残留旧等待原因。
        """
        try:
            conv = self.gpts_conversations.get_by_conv_id(conv_uid)
            if not conv:
                return
            try:
                extra = json.loads(conv.extra) if isinstance(conv.extra, str) else (conv.extra or {})
            except (json.JSONDecodeError, TypeError):
                extra = {}
            if not isinstance(extra, dict):
                extra = {}
            if waiting_reason is None:
                extra.pop("waiting_reason", None)
            else:
                extra["waiting_reason"] = waiting_reason
            session = self.gpts_conversations.get_raw_session()
            session.query(GptsConversationsEntity).filter(
                GptsConversationsEntity.conv_id == conv_uid
            ).update(
                {GptsConversationsEntity.extra: json.dumps(extra, ensure_ascii=False)},
                synchronize_session="fetch",
            )
            session.commit()
            session.close()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[AgentChat] set_waiting_reason failed for {conv_uid}: {e}")

    async def _inner_chat(
        self,
        user_code: str,
        user_query: HumanMessage,
        conv_session_id: str,
        conv_uid: str,
        gpts_app: GptsApp,
        agent_memory: AgentMemory,
        is_retry_chat: bool = False,
        last_speaker_name: str = None,
        init_message_rounds: int = 0,
        historical_dialogues: Optional[List[GptsMessage]] = None,
        rely_messages: Optional[List[GptsMessage]] = None,
        stream: Optional[bool] = True,
        chat_in_params: Optional[List[ChatInParamValue]] = None,
        **ext_info,
    ):
        ### init chat param
        ## 检查应用是否配置完整
        if not gpts_app.agent:
            raise ValueError("当前应用还没配置Agent模版无法开启对话!")
        if not gpts_app.llm_config:
            # 多媒体 Agent 使用媒体生成模型，不依赖 LLM 配置，可跳过该校验
            try:
                from gyra_serve.agent.file_io.file_type_config import (
                    is_multimedia_agent,
                )

                _skip_llm = is_multimedia_agent(gpt_app=gpts_app)
            except Exception:  # noqa: BLE001
                _skip_llm = False
            if not _skip_llm:
                raise ValueError("当前应用还没配置模型无法开始对话!")
        recipient: Optional[ConversableAgent] = None
        gpts_status = Status.COMPLETE.value
        staff_no = ext_info.get("staff_no") or gpts_app.user_code or "gyra"

        # PR 4: 心跳 — 会话入口处 touch 一次，标识本进程在跑
        # Tier 3.2: 同时 acquire_lease，多进程部署下确保会话所有权
        try:
            from gyra.agent.core.heartbeat_hook import touch_heartbeat
            from gyra_serve.agent.heartbeat import acquire_lease
            touch_heartbeat(conv_uid)
            acquired = await acquire_lease(conv_uid)
            if not acquired:
                logger.warning(
                    f"[agent_chat] _inner_chat conv={conv_uid}: lease held by another worker, "
                    f"proceeding anyway (may indicate concurrent dispatch)"
                )
        except Exception:
            pass

        try:
            if isinstance(user_query.content, List):
                from gyra_serve.multimodal.service.service import MultimodalService
                from gyra.core.interface.media import MediaContent, MediaContentType

                multimodal_service = MultimodalService.get_instance(self.system_app)

                if multimodal_service:
                    new_content = MediaContent.replace_url(
                        user_query.content, multimodal_service.replace_uri
                    )
                    user_query.content = new_content

                    matched_model = multimodal_service.match_model_for_content(
                        user_query.content
                    )
                    if matched_model:
                        ext_info["multimodal_matched_model"] = matched_model
                        logger.info(f"[Multimodal] Auto matched model: {matched_model}")
                else:
                    from gyra_serve.file.serve import Serve as FileServe

                    file_serve = FileServe.get_instance(self.system_app)
                    new_content = MediaContent.replace_url(
                        user_query.content, file_serve.replace_uri
                    )
                    user_query.content = new_content

            if not self.agent_manage:
                self.agent_manage = get_agent_manager()

            from gyra.agent.core.types import ENV_CONTEXT_KEY
            from gyra.agent.core.types import LLM_CONTEXT_KEY

            ## 处理对话输入参数
            ### 环境参数穿透当前会话不落表，llm参数作为消息的扩展参数随消息落表，agent控制是否向下传递
            llm_context, env_context = self.chat_in_params_to_context(
                chat_in_params, gpts_app
            )
            ### 获取Agent对话资源
            # 先保留场景装配器预注入的资源(workspace_scene/ecp 等,见 api_v1
            # _assemble_scene_resources / playbook runtime)。chat_in_params_to_resource
            # 从空重建且只读 extraTools,不携带已有 dynamic_resources;若直接覆盖会丢掉
            # 场景 ECP 能力(契约:preserved/extended, never overwritten,见 runtime.py)。
            scene_resources = ext_info.get("dynamic_resources") or []
            dynamic_resources = await self.chat_in_params_to_resource(
                chat_in_params, ext_info
            )
            dynamic_resources = self._preserve_scene_resources(
                scene_resources, dynamic_resources
            )

            ### 提取应用配置中默认绑定的数据库资源，走和动态资源相同的加载路径
            default_db_resources = self._extract_default_datasources(gpts_app)
            if default_db_resources:
                if not dynamic_resources:
                    dynamic_resources = []
                dynamic_resources.extend(default_db_resources)
                # 从 all_resources 中移除已提取的 datasource，避免重复实例化
                if gpts_app.all_resources:
                    gpts_app.all_resources = [
                        r
                        for r in gpts_app.all_resources
                        if r.type != "datasource"
                    ]

            if dynamic_resources:
                ext_info["dynamic_resources"] = dynamic_resources

            if ext_info.get(ENV_CONTEXT_KEY):
                env_context.update(ext_info.get(ENV_CONTEXT_KEY))
            context: AgentContext = AgentContext(
                user_id=user_code,
                # user_name 缺失会让 memory hook 的 verbat metadata.author 为
                # None（hook_dispatcher.memory_write_turn_function 读
                # event.user_name）。user_code 是当前唯一可靠的 user 标识，
                # 同时填到 user_name 让 raw 记忆文件能归属到用户。
                user_name=user_code,
                staff_no=staff_no,
                conv_id=conv_uid,
                conv_session_id=conv_session_id,
                trace_id=first(
                    ext_info.get("trace_id", None),
                    root_tracer.get_context_trace_id(),
                    uuid.uuid4().hex,
                ),
                rpc_id=ext_info.get("rpc_id", "0.1"),
                gpts_app_code=gpts_app.app_code,
                gpts_app_name=gpts_app.app_name,
                language=gpts_app.language,
                incremental=ext_info.get("incremental", False),
                env_context=env_context,
                stream=stream,
                extra=ext_info,
                mist_keys=getattr(gpts_app.llm_config, "mist_keys", None),
                # 对话输入参数覆盖模型推理参数(未指定时回退空间/全局配置,见 llm_client)
                temperature=llm_context.get("temperature"),
                max_new_tokens=llm_context.get("max_new_tokens"),
                top_p=llm_context.get("top_p"),
                reasoning_effort=llm_context.get("reasoning_effort"),
            )

            cache = await self.memory.cache(conv_uid)

            # PR 8: 注册 usage 实时回调，把累计用量推送到 SSE channel（Agent 空间上下文用量环形图）
            try:
                from gyra.agent.core.usage_metric import (
                    get_context_window,
                    register_usage_callback,
                )

                def _push_usage_metric_sse(usage):
                    try:
                        # 优先使用快照显式携带的 context_window；否则按模型名估算
                        context_window = usage.by_model.get("__context_window__")
                        if not context_window:
                            context_window = get_context_window(usage.last_model_name)
                        context_window = int(context_window or 0)
                        ratio = (
                            usage.total_tokens / context_window
                            if context_window > 0
                            else 0.0
                        )
                        # 明细分类（分层/工具占比等），由 emit_context_usage 写入
                        detail = usage.by_model.get("__context_detail__") or {}
                        cache.channel.put_nowait(
                            {
                                "type": "usage_metric",
                                "payload": {
                                    "total": usage.total_tokens,
                                    "prompt": usage.total_prompt_tokens,
                                    "completion": usage.total_completion_tokens,
                                    "context_window": context_window,
                                    "ratio": ratio,
                                    "system": detail.get("system") or 0,
                                    "history": detail.get("history") or 0,
                                    "user_msg": detail.get("user_msg") or 0,
                                    "tools": detail.get("tools") or 0,
                                    "layers": detail.get("layers")
                                    or {"compressed": 0, "retained": 0},
                                },
                            }
                        )
                    except Exception as cb_err:  # noqa: BLE001
                        logger.debug(f"[usage] sse push skipped: {cb_err}")

                register_usage_callback(conv_uid, _push_usage_metric_sse)
            except Exception as reg_err:  # noqa: BLE001
                logger.debug(f"[usage] callback registration skipped: {reg_err}")

            scheduler: Scheduler = LocalScheduler(cache=cache)

            rm = get_resource_manager()
            recipient = await self._build_agent_by_gpts(
                context,
                agent_memory,
                rm,
                gpts_app,
                scheduler=scheduler,
                need_sandbox=True,
                **ext_info,
            )

            # 工具执行授权配置：从 ext_info 或 app ext_config 读取 authorization_config
            # (dict)，挂到 agent。ToolAction 据此按 mode/tool_overrides/白黑名单决定
            # ASK(弹授权卡片WAITING)/DENY(拒绝)/ALLOW(放行)。无配置则保持既有自动流程。
            # 注意：不导入 gyra.core.authorization（该实验包 __init__ 有破损导入），
            # 直接透传 dict，由 ToolAction 解析。
            try:
                _auth_cfg_dict = ext_info.get("authorization_config")
                if not _auth_cfg_dict and gpts_app:
                    _ec = getattr(gpts_app, "ext_config", None)
                    if isinstance(_ec, str):
                        try:
                            import json as _json

                            _ec = _json.loads(_ec)
                        except Exception:
                            _ec = None
                    if isinstance(_ec, dict):
                        _auth_cfg_dict = _ec.get("authorization_config")
                if (
                    _auth_cfg_dict
                    and isinstance(_auth_cfg_dict, dict)
                    and recipient is not None
                ):
                    setattr(recipient, "authorization_config", _auth_cfg_dict)
            except Exception:
                pass

            # 处理文件上传
            # 优先使用 sandbox_file_refs（从 api_v1.py 传递过来）
            # 如果 sandbox_file_refs 为空，才处理 chat_in_params
            sandbox_file_refs = ext_info.get("sandbox_file_refs", [])
            logger.info(
                f"[AgentChat] sandbox_file_refs from ext_info: {len(sandbox_file_refs)} items"
            )

            if sandbox_file_refs:
                # 处理 sandbox_file_refs（从 api_v1.py 传递过来）
                sandbox_key = _sandbox_key(ext_info.get("workspace_id"), conv_uid, staff_no)
                sandbox_manager = GlobalSandboxManagerCache.get(sandbox_key)
                logger.info(
                    f"[AgentChat] sandbox_manager for key {sandbox_key}: {sandbox_manager is not None}"
                )
                if sandbox_manager and sandbox_manager.client:
                    sandbox_client = sandbox_manager.client
                    updated_refs = await _materialize_sandbox_file_refs(
                        system_app=self.system_app,
                        sandbox_client=sandbox_client,
                        sandbox_file_refs=sandbox_file_refs,
                    )

                    ext_info["sandbox_file_refs"] = sandbox_file_refs

                    # 获取用户消息的文本内容
                    user_text = ""
                    if isinstance(user_query.content, str):
                        user_text = user_query.content
                    elif isinstance(user_query.content, list):
                        # 多模态消息，提取文本部分
                        for item in user_query.content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                # 字典格式
                                user_text = item.get("object", {}).get("data", "")
                                break
                            elif hasattr(item, "type") and item.type == "text":
                                # MediaContent 对象格式
                                try:
                                    user_text = item.get_text()
                                except Exception:
                                    user_text = (
                                        str(item.object.data)
                                        if hasattr(item, "object")
                                        else ""
                                    )
                                break

                    # 如果用户消息中没有文件提示，添加正确的文件提示
                    if updated_refs and user_text:
                        if "User uploaded files" not in user_text:
                            new_file_info = (
                                f"\n\n---\n\n📎 **User uploaded files**:\n"
                                + "\n".join(updated_refs)
                            )
                            user_query = HumanMessage(content=user_text + new_file_info)
                            logger.info(
                                f"[AgentChat] Added file info to user message with correct paths"
                            )
                else:
                    logger.warning(
                        f"[AgentChat] sandbox_manager not available for key: {sandbox_key}"
                    )
            elif chat_in_params:
                # 如果没有 sandbox_file_refs，才处理 chat_in_params
                logger.info("[AgentChat] Processing files from chat_in_params")
                # 按当前 agent 模型能力 + 是否多媒体 agent 统一分流（路径 B）
                try:
                    from gyra_serve.agent.file_io.file_type_config import (
                        is_multimedia_agent,
                    )

                    _prefer_direct = is_multimedia_agent(gpt_app=gpts_app)
                except Exception:
                    _prefer_direct = False
                file_dispatch_result = await self._dispatch_uploaded_files(
                    chat_in_params=chat_in_params,
                    conv_id=conv_uid,
                    user_query=user_query,
                    staff_no=staff_no,
                    model_name=ext_info.get("model_name")
                    or self._resolve_app_model_name(gpts_app),
                    prefer_direct_media=_prefer_direct,
                )
                if file_dispatch_result:
                    user_query = file_dispatch_result

            # 合并从 api_v1 透传的多模态内容（模型有能力直接消费的 image/audio/video）。
            # 当存在 sandbox_file_refs 时，上面的沙箱分支会把 user_query 重建为
            # "纯文本+文件提示"，从而丢掉原本可直接进模型消费的媒体；这里补回，
            # 并按 URL 去重，避免与原始 in_message 中已有的媒体重复。
            _multimodal_contents = ext_info.get("multimodal_contents") or []
            if _multimodal_contents and isinstance(user_query, HumanMessage):
                try:
                    from gyra.core.interface.media import MediaContent as _MC

                    _parsed = _MC.parse_chat_completion_message(
                        {"content": _multimodal_contents}
                    )
                    _existing = set()
                    if isinstance(user_query.content, list):
                        for _mc in user_query.content:
                            if (
                                isinstance(_mc, _MC)
                                and _mc.type in ("image", "audio", "video")
                            ):
                                _existing.add(str(_mc.object.data))
                    _new_items = [
                        _m for _m in _parsed if str(_m.object.data) not in _existing
                    ]
                    if isinstance(user_query.content, list):
                        user_query.content = list(user_query.content) + _new_items
                    elif user_query.content:
                        user_query.content = [_MC.build_text(user_query.content)] + _new_items
                    else:
                        user_query.content = _new_items
                    if _new_items:
                        logger.info(
                            f"[AgentChat] Merged {len(_new_items)} direct-consume "
                            f"multimodal contents into user message"
                        )
                except Exception as e:
                    logger.warning(
                        f"[AgentChat] Failed to merge multimodal_contents: {e}"
                    )

            if is_retry_chat:
                # retry chat
                validate_session_transition(Status.WAITING, Status.RUNNING)
                self.gpts_conversations.update(conv_uid, Status.RUNNING.value)

            user_proxy: UserProxyAgent = (
                await UserProxyAgent().bind(context).bind(agent_memory).build()
            )
            user_code = ext_info.get("user_code", None)
            if user_code:
                app_config = self.system_app.config.configs.get("app_config")
                web_config = _get_web_config(app_config)
                user_proxy.profile.avatar = (
                    f"{web_config.web_url}/user/avatar?loginName={user_code}"
                )
            await user_proxy.initiate_chat(
                recipient=recipient,
                message=user_query,
                is_retry_chat=is_retry_chat,
                last_speaker_name=last_speaker_name,
                message_rounds=init_message_rounds,
                historical_dialogues=user_proxy.convert_to_agent_message(
                    historical_dialogues
                ),
                rely_messages=rely_messages,
                approval_message_id=ext_info.get("approval_message_id"),
                waiting_reason=ext_info.get("waiting_reason"),
                **llm_context,
            )

            if await scheduler.running():
                await scheduler.schedule()

            # Check if the user has received a question.
            waiting_reason = None
            if user_proxy.have_ask_user():
                gpts_status = Status.WAITING.value
                # 区分"工具授权"（BEFORE/AFTER_ACTION，resume 时需重放以复用缓存工具
                # 结果）与"用户追问"（CONCLUSION_INCOMPLETE / ask_user 交互工具，resume
                # 时走 follow-up 由 LLM 处理用户新回答）。
                from gyra.agent.core.action.base import AskUserType
                from gyra.agent.core.schema import WaitingReason as WR
                _ask_type = getattr(user_proxy, "ask_type", None)
                if _ask_type in (
                    AskUserType.BEFORE_ACTION.value,
                    AskUserType.AFTER_ACTION.value,
                ):
                    waiting_reason = WR.TOOL_AUTHORIZATION.value
                else:
                    waiting_reason = WR.USER_QUESTION.value

            # PR 2: 有 pending 子 agent 时，主会话也 WAITING（等子 agent 完成后 coordinator 触发 resume）
            if gpts_status != Status.WAITING.value:
                try:
                    from gyra_serve.agent.subagent_coordinator import (
                        get_subagent_coordinator,
                    )
                    coordinator = get_subagent_coordinator()
                    if coordinator is not None:
                        handles = await coordinator._read_pending(conv_uid)
                        if handles and any(not h.is_terminal() for h in handles):
                            gpts_status = Status.WAITING.value
                            from gyra.agent.core.schema import WaitingReason as WR
                            waiting_reason = WR.SUBAGENTS.value
                except Exception as sub_err:
                    logger.debug(
                        f"[AgentChat] pending_subagents check skipped: {sub_err}"
                    )

            # 异步任务（media 生成 / spawn_agent_task wait=false）存在未完成任务时，
            # 主会话也置 WAITING，等 AsyncTaskCoordinator 完成后触发 resume 恢复 loop。
            if gpts_status != Status.WAITING.value:
                try:
                    from gyra_serve.agent.async_task_coordinator import (
                        get_async_task_coordinator,
                    )
                    async_coord = get_async_task_coordinator()
                    if async_coord is not None and await async_coord.has_pending_tasks(
                        conv_uid
                    ):
                        logger.info(
                            f"[AgentChat] conv={conv_uid} has pending async tasks, "
                            f"setting WAITING"
                        )
                        gpts_status = Status.WAITING.value
                        from gyra.agent.core.schema import WaitingReason as WR
                        waiting_reason = WR.ASYNC_TASKS.value
                except Exception as async_err:
                    logger.debug(
                        f"[AgentChat] pending_async_tasks check skipped: {async_err}"
                    )

            validate_session_transition(Status.RUNNING, Status(gpts_status))
            self.gpts_conversations.update(conv_uid, gpts_status)
            # 持久化等待原因：WAITING 时写入具体原因供 resume 决策；非 WAITING（COMPLETE
            # 等终态）时清空，避免残留旧等待原因误导后续恢复。
            self._set_waiting_reason(conv_uid, waiting_reason if gpts_status == Status.WAITING.value else None)
        except asyncio.CancelledError:
            logger.info(f"Chat cancelled by user for conv_uid: {conv_uid}")
            gpts_status = Status.INTERRUPTED.value
            validate_session_transition(Status.RUNNING, Status.INTERRUPTED)
            self.gpts_conversations.update(conv_uid, gpts_status)

            # 推送中断消息到消息队列
            try:
                interrupt_msg = {
                    "type": "interrupt",
                    "content": "对话已被用户中断",
                }
                await self.memory.push_message(
                    conv_id=conv_uid,
                    stream_msg=interrupt_msg,
                )
            except Exception as push_error:
                logger.error(f"Failed to push interrupt message: {push_error}")

            # 确保消息被写入数据库
            try:
                messages = await self.memory.get_messages(conv_uid)
                for msg in messages:
                    await self._save_message_to_db(msg)
                logger.info(
                    f"Saved {len(messages)} messages for interrupted conversation {conv_uid}"
                )
            except Exception as save_error:
                logger.error(f"Failed to save messages on interrupt: {save_error}")

            raise
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            logger.error(
                f"chat abnormal termination！{conv_uid}, error: {str(e)}\n{error_trace}"
            )
            gpts_status = Status.FAILED.value
            validate_session_transition(Status.RUNNING, Status.FAILED)
            self.gpts_conversations.update(conv_uid, gpts_status)

            error_pushed = False
            try:
                error_msg = {
                    "type": "error",
                    "content": f"[ERROR]对话发生错误: {str(e)}[/ERROR]",
                    "error_detail": error_trace,
                }
                await self.memory.push_message(
                    conv_id=conv_uid,
                    stream_msg=error_msg,
                )
                error_pushed = True
            except Exception as push_error:
                logger.error(f"Failed to push error message via vis converter: {push_error}")

            # Fallback: push error directly to queue bypassing vis converter
            if not error_pushed:
                try:
                    cache = await self.memory._get_cache(conv_uid)
                    if cache:
                        error_view = json.dumps(
                            {"type": "error", "content": f"对话发生错误: {str(e)}"},
                            ensure_ascii=False,
                        )
                        cache.channel.put_nowait(error_view)
                        logger.info(f"Pushed error directly to queue for {conv_uid}")
                except Exception as direct_push_error:
                    logger.error(f"Failed to push error directly to queue: {direct_push_error}")

            raise ValueError(f"The conversation is abnormal! {str(e)}")
        finally:
            logger.info(f"inner chat final!{conv_uid}")
            try:
                await self.memory.complete(conv_uid)
            except Exception as complete_error:
                logger.error(f"Failed to complete memory: {complete_error}")
            # PR 8: 会话结束 log usage 聚合，并清理 usage 回调
            try:
                from gyra.agent.core.usage_metric import (
                    clear_in_memory_usage,
                    format_usage_log,
                    get_in_memory_usage,
                    unregister_usage_callback,
                )

                unregister_usage_callback(conv_uid)
                usage = get_in_memory_usage(conv_uid)
                if usage is not None and usage.total_llm_calls > 0:
                    logger.info(format_usage_log(usage))
                clear_in_memory_usage(conv_uid)
            except Exception as usage_err:  # noqa: BLE001
                logger.debug(f"[usage] final log skipped: {usage_err}")
            # Tier 3.2: 释放 lease（会话正常结束），让其他 worker 可立即接管
            # WAITING 状态不释放（等子 agent / 用户输入期间仍由本 worker 持有）
            try:
                from gyra_serve.agent.heartbeat import release_lease
                from gyra.agent.core.schema import Status as _Status
                if gpts_status not in (
                    _Status.WAITING.value, _Status.RETRYING.value
                ):
                    await release_lease(conv_uid)
            except Exception as lease_err:  # noqa: BLE001
                logger.debug(f"[lease] release skipped: {lease_err}")
            await self._cleanup_sandbox_manager(conv_uid, staff_no)
        return conv_uid

    async def _chat_messages(self, conv_id: str, task: Optional[asyncio.Task] = None):
        """Yield chat messages from the queue with task monitoring.

        If a task is provided and it fails during iteration, the error will be raised.
        Also handles timeout cases to prevent infinite waiting.
        Items are yielded BEFORE checking task status so that error messages
        pushed to the queue are properly forwarded to the consumer.
        """
        if not (iterator := await self.memory.queue_iterator(conv_id)):
            return

        try:
            async for item in iterator:
                # Yield the item first, so error messages from the queue
                # are forwarded even when the task has already failed
                yield item
                await asyncio.sleep(0)
                # Then check task status - if failed, raise on next iteration
                if task and task.done():
                    exc = task.exception()
                    if exc:
                        import traceback

                        logger.error(
                            f"Background task failed: {exc}\n"
                            f"{traceback.format_exception(type(exc), exc, exc.__traceback__)}"
                        )
                        raise exc
        except Exception as e:
            import traceback

            logger.error(
                f"Chat message iteration failed: {e}\n{traceback.format_exc()}"
            )
            raise

    async def stop_chat(self, conv_session_id: str, user_id: Optional[str] = None):
        """停止对话.

        Args:
            conv_session_id:会话id(当前会话的conversation_session_id)
            user_id:用户ID，用于清理沙箱
        """
        logger.info(f"stop_chat conv_session_id:{conv_session_id}")

        if not conv_session_id or not conv_session_id.strip():
            logger.warning(f"conv_session_id is empty, skip stop_chat")
            return

        # 取消执行任务
        task_key = conv_session_id
        if task_key in self._running_tasks:
            task = self._running_tasks.pop(task_key)
            if task and not task.done():
                task.cancel()
                logger.info(f"Cancelled execution task for session {conv_session_id}")

        convs = await self.gpts_conversations.get_by_session_id_asc(conv_session_id)
        if convs:
            conv_id = convs[-1].conv_id
            await self.memory.stop(conv_id=conv_id)
            # 清理该会话的沙箱
            await self._cleanup_sandbox_manager(conv_id, user_id)
        else:
            logger.warning(f"未找到会话[{conv_session_id}], may already stopped")
            return

    async def stop_chat_with_conv_id(self, conv_id: str, user_id: Optional[str] = None):
        """停止对话.

        Args:
            conv_id: 对话id(当前对话的agent_conv_id 非conversation_session_id)
            user_id: 用户ID，用于清理沙箱
        """
        logger.info(f"stop_chat conv_id:{conv_id}")

        # 取消执行任务
        if conv_id in self._running_tasks:
            task = self._running_tasks.pop(conv_id)
            if task and not task.done():
                task.cancel()
                logger.info(f"Cancelled execution task for conv_id {conv_id}")

        await self.memory.stop(conv_id=conv_id)
        # 清理该会话的沙箱
        await self._cleanup_sandbox_manager(conv_id, user_id)

    def register_running_task(self, session_id: str, task: asyncio.Task):
        """注册正在运行的执行任务.

        Args:
            session_id: 会话ID
            task: asyncio.Task 实例
        """
        self._running_tasks[session_id] = task
        logger.info(f"Registered running task for session {session_id}")

    def unregister_running_task(self, session_id: str):
        """取消注册执行任务.

        Args:
            session_id: 会话ID
        """
        if session_id in self._running_tasks:
            del self._running_tasks[session_id]
            logger.info(f"Unregistered running task for session {session_id}")

    async def retry_chat(self, conv_id: str):
        """重试对话, 对于运行中且最终消息超过5分钟的 可以基于已有对话记录继续运行

        Args:
            conv_id: 对话id(当前对话的agent_conv_id 非conversation_session_id)
        """
        pass

    async def query_chat(self, conv_id: str, vis_render: Optional[str] = None):
        """查询对话

        Args:
            conv_id: 对话id(当前对话的agent_conv_id 非conversation_session_id)
            vis_render: 可视化协议名称（决定返回数据的格式）
        """
        gpts_memory = GptsMemory(
            plans_memory=MetaGyrasPlansMemory(),
            message_memory=MetaGyrasMessageMemory(),
            todo_db_storage=MetaGyrasTodoStorage(),
            # 重算 vis_final 需要交付/任务文件列表，回源 DB 文件元数据
            file_metadata_db_storage=MetaGyrasFileMetadataStorage(),
        )
        try:
            gpts_conversation: GptsConversationsEntity = (
                self.gpts_conversations.get_by_conv_id(conv_id)
            )
            if not gpts_conversation:
                # 兼容前端传入 conversation_session_id（非 agent conv_id）的场景：
                # 历史会话轮询用的是 URL 上的 conv_uid（即 session_id），
                # 此处按 session 取最新一轮 agent 会话
                session_convs = await self.gpts_conversations.get_by_session_id_asc(
                    conv_id
                )
                if session_convs:
                    gpts_conversation = session_convs[-1]
            if not gpts_conversation:
                return None
            conv_id = gpts_conversation.conv_id
            is_final = False
            if gpts_conversation.state in [Status.COMPLETE.value, Status.FAILED.value]:
                is_final = True
            logger.info(
                f"query_chat gpts_conversation vis render:{vis_render},{gpts_conversation.vis_render}"
            )
            current_vis_render = (
                vis_render or gpts_conversation.vis_render or "nex_vis_window"
            )

            app_config = self.system_app.config.configs.get("app_config")
            web_config = _get_web_config(app_config)
            vis_manager = get_vis_manager()
            vis_convert: VisProtocolConverter = vis_manager.get_by_name(
                current_vis_render
            )(gyra_url=web_config.web_url)

            ## 重新初始化对话memory数据
            await gpts_memory.init(conv_id=conv_id, vis_converter=vis_convert)
            await gpts_memory.load_persistent_memory(conv_id)
            ## 构建Agent应用实例并挂载到memory，获取对应头像等信息
            # context: AgentContext = AgentContext(
            #     conv_id=conv_id,
            #     conv_session_id=gpts_conversation.conv_session_id,
            #     trace_id=uuid.uuid4().hex,
            #     rpc_id="",
            #     gpts_app_code=gpts_conversation.gpts_name,
            # )
            # try:
            #     await self.build_agent_by_app_code(gpts_conversation.gpts_name, context)
            # except Exception as e:
            #     logger.warning(f"查询会话时，恢复agent对象异常！{str(e)}")

            # 返回对应协议的最终消息内容
            # 6th 返回值：dock 帧（Composer Dock 协议），从专用表回放 todo 等
            # 输入区 widget，重开会话时可恢复 todo 面板。
            dock = await self._build_dock_frame(gpts_memory, conv_id)
            return (
                await gpts_memory.vis_final(conv_id),
                await gpts_memory.user_answer(conv_id),
                current_vis_render,
                is_final,
                gpts_conversation.state,
                dock,
            )
        finally:
            await gpts_memory.clear(conv_id)

    async def _build_dock_frame(self, gpts_memory: GptsMemory, conv_id: str) -> dict:
        """从领域存储回放输入区 Dock widget，组装成统一 dock 帧。

        目前回放 todo_list 与 subagent_board；后续新增 widget 在此追加即可。
        无任何 widget 时返回空帧 `{"version": 1, "widgets": []}`。
        """
        widgets: List[dict] = []
        try:
            from gyra.agent.tools.builtin.todo.todo_reminder import build_todo_widget

            todos = await gpts_memory.read_todos(conv_id)
            if todos:
                widgets.append(build_todo_widget(todos, conv_id))
        except Exception as e:
            logger.warning(f"[dock] build todo widget failed: {e}")

        try:
            from gyra_serve.agent.subagent_coordinator import (
                build_subagent_board_widget,
                get_subagent_coordinator,
            )

            coordinator = get_subagent_coordinator()
            if coordinator is not None:
                items = await coordinator.list_subagent_items(conv_id)
                if items:
                    widgets.append(build_subagent_board_widget(items, conv_id))
                else:
                    # pending 已清空（子任务全部完成/resume 后）：回退到持久化的
                    # 终态看板，保证恢复/刷新后对话页仍能看到子任务完成情况
                    terminal_items = await coordinator.list_persistent_board(conv_id)
                    if terminal_items:
                        widgets.append(
                            build_subagent_board_widget(terminal_items, conv_id)
                        )
        except Exception as e:
            logger.warning(f"[dock] build subagent_board widget failed: {e}")

        # 异步任务看板（spawn_agent_task / media wait=false 后台任务）：
        # 与 SubagentCoordinator 的子任务看板同构，数据源为 pending_async_tasks。
        # 复用 build_subagent_board_widget 渲染，保证刷新/恢复后主对话页可见。
        try:
            from gyra_serve.agent.async_task_coordinator import (
                get_async_task_coordinator,
            )
            from gyra_serve.agent.subagent_coordinator import (
                build_subagent_board_widget,
            )

            async_coord = get_async_task_coordinator()
            if async_coord is not None:
                async_items = await async_coord.list_board_items(conv_id)
                if async_items:
                    widgets.append(
                        build_subagent_board_widget(async_items, conv_id)
                    )
        except Exception as e:
            logger.warning(f"[dock] build async task board widget failed: {e}")

        return {"version": 1, "widgets": widgets}

    async def query_step_detail(
        self, conv_id: str, step_uid: str,
    ) -> Optional[dict]:
        """按 step uid 查询单个执行步骤的 VIS 渲染数据。

        conv_id 入参实为 conv_session_id(前端 URL 的 conv_uid);消息持久化于
        {conv_session_id}_{round},故按 session_id 解析会话并全量加载消息重放匹配。
        """
        try:
            # conv_id 入参为 conv_session_id,按 session_id 解析(消息存于 {base}_{round})
            conversations = await self.gpts_conversations.get_by_session_id_asc(conv_id)
            if not conversations:
                return None
            gpts_conversation = conversations[-1]  # 最新一轮
            agent_conv_id = gpts_conversation.conv_id  # {conv_session_id}_{round}

            current_vis_render = gpts_conversation.vis_render or "nex_vis_window"
            app_config = self.system_app.config.configs.get("app_config")
            web_config = _get_web_config(app_config)
            vis_manager = get_vis_manager()
            vis_convert = vis_manager.get_by_name(current_vis_render)(
                gyra_url=web_config.web_url
            )

            # 优先用转换器的 get_step_detail:按 step_id(或 action_id)重放消息精确匹配,
            # 正确处理并行多工具调用(render_step_detail 只取消息内最后一个 action)。
            # 全量加载该会话所有轮次消息(按 conv_session_id)。
            if hasattr(vis_convert, "get_step_detail"):
                all_messages = self.gpts_messages_dao.get_by_conv_session_id(conv_id)
                if all_messages:
                    detail = vis_convert.get_step_detail(messages=all_messages, step_id=step_uid)
                    if detail:
                        return detail

            # Fallback:按 tool_call_id(=action_id)定位消息,再 render_step_detail
            gpts_memory = GptsMemory(
                plans_memory=MetaGyrasPlansMemory(),
                message_memory=MetaGyrasMessageMemory(),
                work_log_db_storage=MetaGyrasWorkLogStorage(),
            )
            try:
                await gpts_memory.init(conv_id=agent_conv_id, vis_converter=vis_convert)
                await gpts_memory.load_persistent_memory(agent_conv_id)
                cache = await gpts_memory._get_cache(agent_conv_id)
                if not cache:
                    return None

                target_entry = None
                for entry in cache.work_logs:
                    if entry.tool_call_id == step_uid:
                        target_entry = entry
                        break

                if not target_entry or not target_entry.message_id:
                    return None

                target_msg = cache.messages.get(target_entry.message_id)
                if not target_msg:
                    return None

                entries = cache.work_entries_by_message.get(target_msg.message_id, [])
                if entries and hasattr(target_msg, "is_new_format") and target_msg.is_new_format:
                    target_msg.set_work_entries(entries)

                if hasattr(vis_convert, "render_step_detail"):
                    rd = await vis_convert.render_step_detail(
                        gpt_msg=target_msg,
                        step_uid=step_uid,
                    )
                    if rd and rd.get("step_data"):
                        return rd["step_data"]

                action_name = target_entry.tool or ""
                observation = getattr(target_entry, "output", None) or ""
                return {
                    "active_step": {
                        "id": step_uid,
                        "type": action_name or "tool",
                        "title": action_name or "Step",
                        "status": "completed" if target_entry.success else "error",
                        "action": action_name,
                        "action_input": getattr(target_entry, "args", None),
                    },
                    "outputs": [{"output_type": "text", "content": observation}]
                    if observation
                    else [],
                }
            finally:
                await gpts_memory.clear(agent_conv_id)
        except Exception:
            logger.exception(f"query_step_detail error: conv_id={conv_id}, step_uid={step_uid}")
            return None

    async def dynamic_resource_adapter(
        self, gpt_app: GptsApp, ext_info: Optional[dict] = None
    ) -> None:
        """Dynamic resource adapter."""
        pass


def _get_post_action_report(context: str | dict) -> Optional[dict]:
    if not context:
        return None

    try:
        if isinstance(context, str):
            context = json.loads(context)
        return context.get("post_action_report", None)
    except Exception as e:
        return None
