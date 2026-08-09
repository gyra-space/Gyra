"""
通用多媒体 Agent 模板（协议层统一：继承 ``ConversableAgent``）

一个「只使用多媒体生成模型」的 Agent：不跑 LLM 推理循环，而是重写``thinking``
把「任务描述 + 固定配置」确定性映射到媒体生成 provider 调用。它继承标准
``ConversableAgent``，因此：
- 是**一等公民主 Agent 模板**：注册进 ``AgentManager``（role=MULTIMEDIA），
  可作为 ``app.agent`` 持久化取值，并出现在模板列表中（类似 BAIZE/ReActMaster）。
- 同时保留标准 agent 接口（``run`` / ``generate_image`` / ``generate_video``），
  可被场景空间 / 其它主 Agent 通过 agent 交互或异步子任务（spawn_agent_task）调用。
- 统一走协议层：身份、注册、bind、memory、事件、交付均复用 ``ConversableAgent``，
  无需独立的 ``MultimediaAgentRegistry`` 旁路。

设计要点：
- 继承 ``ConversableAgent``，重写关键流程 ``thinking``（确定性生成，绕过 LLM）
- 自管模型选择：request.model › config.default_*_model › 系统默认 › 首个可用
- 自管结果轮询下载：异步模式经 AsyncTaskManager 后台 resume(poll+download)
- 预设风格/场景 prompt：config.style_prompt / scene_prompt / negative_prompt
- 配置来源：``ext_config.multimedia_agent``（app 配置）或构造时显式传入
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from gyra._private.pydantic import Field
from gyra.agent import AgentMessage, ProfileConfig
from gyra.agent.core.base_agent import ConversableAgent
from gyra.agent.util.llm.llm_client import AgentLLMOut

from .config import MultimediaAgentConfig
from .executor import KIND_IMAGE, KIND_VIDEO, MultimediaExecutor, MultimediaRequest

logger = logging.getLogger(__name__)


class _LocalDirSandboxAdapter:
    """本地目录沙箱适配器：把 AFS 的沙箱拷贝落到本地工作区目录。

    子 Agent（如 SubAgent 后台派发的多媒体 Agent）通常没有自己的沙箱，
    AFS 的 sandbox 拷贝分支会被跳过，生成文件只进 FileStorage、不进用户
    可见的工作区目录。本地沙箱部署下，用本适配器指向系统配置的同一
    work_dir，仅实现 AFS 用到的最小接口（work_dir + file.write）。
    """

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.file = self._FileOps()

    class _FileOps:
        async def write(self, path: str, data: bytes) -> None:
            from pathlib import Path

            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(data, str):
                data = data.encode("utf-8")
            await asyncio.to_thread(p.write_bytes, data)


class MultimediaAgent(ConversableAgent):
    """通用多媒体 Agent 模板（一等公民 ConversableAgent）。

    Args:
        config: 固定配置（MultimediaAgentConfig 或 dict）。
        afs: 默认 AFS 实例（单次调用可覆盖）。
        conv_id: 默认所属会话 ID。
    """

    # 主 Agent 模板身份：role 即注册键（app.agent = "MULTIMEDIA"）
    profile: ProfileConfig = Field(
        default_factory=lambda: ProfileConfig(
            name="MULTIMEDIA",
            role="MULTIMEDIA",
            goal="只使用多媒体生成模型，把任务描述确定性映射为图片/视频生成调用。",
            desc="只使用多媒体生成模型的通用 Agent 模板，可被主 Agent 通过异步子任务（spawn_agent_task）调用",
            aliases=["multimedia_agent", "多媒体Agent"],
        )
    )

    def __init__(
        self,
        config: Optional[MultimediaAgentConfig | Dict[str, Any]] = None,
        afs: Any = None,
        conv_id: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        if isinstance(config, dict):
            config = MultimediaAgentConfig.from_dict(config)
        self._config = config or self._resolve_config()
        self._executor = MultimediaExecutor(
            config=self._config, afs=afs, conv_id=conv_id
        )
        # 结构化失败标记:thinking 失败分支置位,correctness_check 消费(置
        # reply_message.success=False),替代消费端对"多媒体生成失败"前缀的字符串匹配
        self._gen_failure: Optional[str] = None

    # ---- 身份 ----

    @property
    def name(self) -> str:
        """Agent 名称（供 spawn_agent_task / 寻址）。"""
        return self._config.name

    @property
    def description(self) -> str:
        return self._config.description

    @property
    def config(self) -> MultimediaAgentConfig:
        return self._config

    def bind_app_config(
        self, app_ext_config: Optional[Dict[str, Any]] = None
    ) -> "MultimediaAgent":
        """绑定应用级多媒体配置（多实例各自独立、互不污染）。

        把该 app 的 ``ext_config`` 绑定到实例，并按其中 ``multimedia_agent`` 重新解析
        配置与执行器。未传 / 非 dict / 解析失败时保持现状（默认配置）。这样同一
        MULTIMEDIA 模板下不同 app 实例各自携带自己的名称、默认模型、风格 prompt。
        """
        if isinstance(app_ext_config, dict):
            self.ext_config = app_ext_config
            try:
                self._config = self._resolve_config()
                self._executor.config = self._config
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[multimedia-agent] bind_app_config resolve failed: {e}")
        return self

    @property
    def executor(self) -> MultimediaExecutor:
        return self._executor

    def info(self) -> Dict[str, Any]:
        """Agent 元信息（供注册 / 展示）。"""
        return {
            "name": self.name,
            "description": self.description,
            "capability_image": self._config.capability_image,
            "capability_video": self._config.capability_video,
            "default_image_model": self._config.default_image_model,
            "default_video_model": self._config.default_video_model,
            "async_default": self._config.async_default,
        }

    # ---- 协议层重写：把 LLM 推理替换为确定性媒体生成 ----

    def _resolve_config(self) -> MultimediaAgentConfig:
        """从绑定的 ``ext_config.multimedia_agent`` 解析配置（运行时读取 app 配置）。"""
        try:
            raw = (getattr(self, "ext_config", None) or {}).get("multimedia_agent")
            if raw:
                return MultimediaAgentConfig.from_dict(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[multimedia-agent] ext_config resolve failed: {e}")
        return MultimediaAgentConfig()

    async def _ensure_agent_file_system(self) -> Optional[Any]:
        """确保 AgentFileSystem 已初始化（懒加载）。

        多媒体 Agent 作为主 Agent / 场景 Agent 运行时，继承的协议层不会自动创建
        AFS。这里按 ``conv_id`` 懒加载 AFS，并把 ``metadata_storage`` 指向
        ``gpts_memory``，使生成的文件作为交付物落盘后可被 gpts_memory.list_files
        检索，从而在 vis_manus 右面板「交付文件」中展示并支持打开。
        """
        if getattr(self, "_agent_file_system", None) is not None:
            return self._agent_file_system

        try:
            if not self.agent_context:
                return None
            from gyra.agent.core.file_system.agent_file_system import AgentFileSystem

            conv_id = self.agent_context.conv_id or "default"
            session_id = self.agent_context.conv_session_id or conv_id

            # 尝试获取 FileStorageClient（网络/分布式存储后端）
            file_storage_client = None
            try:
                from gyra.core.interface.file import FileStorageClient
                from gyra._private.config import Config

                system_app = Config().SYSTEM_APP
                if system_app:
                    file_storage_client = FileStorageClient.get_instance(system_app)
            except Exception:  # noqa: BLE001 - FileStorageClient 不可用
                pass

            # sandbox 客户端（可选）；子 Agent（SubAgent 后台派发）通常没有自己的
            # 沙箱，回退到系统配置的本地工作区目录，让交付文件落到与主 Agent
            # 相同的「沙箱文件目录」（仅本地沙箱部署生效）
            sandbox = None
            if getattr(self, "sandbox_manager", None) and self.sandbox_manager.client:
                sandbox = self.sandbox_manager.client
            if sandbox is None:
                sandbox = self._local_workspace_sandbox_fallback()

            self._agent_file_system = AgentFileSystem(
                conv_id=conv_id,
                session_id=session_id,
                metadata_storage=(
                    self.memory.gpts_memory if getattr(self, "memory", None) else None
                ),
                file_storage_client=file_storage_client,
                sandbox=sandbox,
            )
            await self._agent_file_system.sync_workspace()

            # 注入到 executor，供同步/异步交付路径复用
            self._executor.afs = self._agent_file_system
            self._executor.conv_id = conv_id
            # 子会话 context.extra 携带主会话 ID：透传给 executor，使媒体轮询任务
            # 记录 main_conv_id（轮询任务仍按 sub_conv 隔离不触发主 resume），
            # 主会话可据此查到子 Agent 生成的产物 artifact。
            main_conv_id = (getattr(self.agent_context, "extra", None) or {}).get(
                "main_conv_id", ""
            )
            if main_conv_id:
                self._executor.main_conv_id = main_conv_id
            logger.info(
                f"[multimedia-agent] AFS initialized for conv_id={conv_id}"
            )
            return self._agent_file_system
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[multimedia-agent] AFS init failed: {e}", exc_info=True
            )
            return None

    def _local_workspace_sandbox_fallback(self) -> Optional[Any]:
        """无沙箱客户端时的本地工作区兜底（仅本地沙箱部署）。

        读系统沙箱配置（与 agent_chat 创建 sandbox_manager 同一来源）：
        type 为本地（None/""/"local"）且 work_dir 存在时，返回指向该目录的
        适配器，使 AFS 沙箱拷贝分支把交付文件写进用户可见的工作区。
        子 Agent 上下文携带 workspace_id（场景空间）时优先用空间家目录。
        """
        try:
            # 场景空间：子 Agent 经 _start_app 继承的 workspace_id → 空间家目录
            ws_id = None
            try:
                ws_id = (self.agent_context.extra or {}).get("workspace_id")
            except Exception:  # noqa: BLE001
                ws_id = None
            if ws_id:
                try:
                    from gyra_serve.workspace.dataset_service import (
                        workspace_sandbox_root,
                    )

                    ws_root = workspace_sandbox_root(int(ws_id))
                    if os.path.isdir(ws_root):
                        return _LocalDirSandboxAdapter(ws_root)
                except Exception:  # noqa: BLE001 - 回退到默认 work_dir
                    pass

            from gyra._private.config import Config

            system_app = Config().SYSTEM_APP
            if not system_app:
                return None
            app_config = system_app.config.configs.get("app_config")
            sandbox_config = getattr(app_config, "sandbox", None) if app_config else None
            if sandbox_config is None:
                return None
            s_type = getattr(sandbox_config, "type", None)
            work_dir = getattr(sandbox_config, "work_dir", None)
            if s_type not in (None, "", "local") or not work_dir:
                return None
            if not os.path.isdir(work_dir):
                return None
            logger.info(
                f"[multimedia-agent] no sandbox client; "
                f"fallback to local workspace dir: {work_dir}"
            )
            return _LocalDirSandboxAdapter(work_dir)
        except Exception as e:  # noqa: BLE001 - 兜底失败不影响主流程
            logger.debug(f"[multimedia-agent] local workspace fallback skip: {e}")
            return None

    async def thinking(  # type: ignore[override]
        self,
        messages: List[AgentMessage],
        reply_message_id: str,
        sender: Optional[Any] = None,
        prompt: Optional[str] = None,
        received_message: Optional[AgentMessage] = None,
        reply_message: Optional[AgentMessage] = None,
        **kwargs,
    ) -> Optional[AgentLLMOut]:
        """重写：不再调用 LLM，而是执行一次确定性媒体生成。

        从 ``received_message`` 提取任务描述，经 ``MultimediaExecutor`` 生成图片/视频，
        把结果输出文本作为回复 content 返回。生成前确保 AFS 已初始化，文件会作为
        交付物落盘并在右面板展示。
        """
        task = ""
        if received_message is not None:
            task = (received_message.content or "").strip()
        elif messages:
            task = (messages[-1].content or "").strip()

        # 父 Agent 通过 SubAgent 的 media 参数透传的多媒体生成参数（kind/model/size/
        # resolution/duration/aspect_ratio 等），未传字段回退到 Agent 配置默认值
        media_params: Dict[str, Any] = {}
        if received_message is not None and getattr(received_message, "context", None):
            ctx = received_message.context or {}
            _media = ctx.get("media") or {}
            if isinstance(_media, dict):
                media_params = dict(_media)

        # 主 Agent 运行时读取 app 的多媒体配置（若已绑定）
        if getattr(self, "ext_config", None) is not None:
            self._config = self._resolve_config()
            self._executor.config = self._config

        # 确保 AFS 已初始化，使生成文件作为交付物落盘
        afs = await self._ensure_agent_file_system()

        params = dict(media_params)
        params["wait"] = True
        params["afs"] = afs
        request = self._build_request(task, params)
        result = await self._executor.run(request)

        if result is None:
            self._gen_failure = "无返回结果"
            return AgentLLMOut(
                llm_name=self._config.default_image_model or "multimedia",
                content="多媒体生成失败：无返回结果。",
                thinking_content="",
                tool_calls=None,
            )
        if not getattr(result, "success", False):
            error = getattr(result, "error", None) or "多媒体生成失败"
            self._gen_failure = str(error)
            return AgentLLMOut(
                llm_name=self._config.default_image_model or "multimedia",
                content=f"多媒体生成失败：{error}",
                thinking_content="",
                tool_calls=None,
            )
        self._gen_failure = None
        return AgentLLMOut(
            llm_name=self._config.default_image_model or "multimedia",
            content=str(getattr(result, "output", "") or "已生成。"),
            thinking_content="",
            tool_calls=None,
            extra={"artifacts": getattr(result, "artifacts", None)},
        )

    async def correctness_check(
        self, message: AgentMessage, **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """把媒体生成失败反映到 reply_message.success(结构化失败标记)。

        thinking 的失败分支置 ``_gen_failure``;这里消费它返回 False,使
        ``generate_reply`` 把 ``reply_message.success`` 置 False。消费端
        (``_result_from_answer`` / ``on_subagent_done``)据此判失败,不再依赖
        "多媒体生成失败" content 前缀匹配(前缀仍保留,供展示与旧路径兜底)。

        安全:本 Agent 无 tool calls(act_outs 为空),verify 失败后
        generate_reply 直接 break,不会重试导致重复生成/重复扣费。
        """
        if self._gen_failure:
            reason = self._gen_failure
            self._gen_failure = None
            return False, reason
        return True, None

    # ---- 标准接口 ----

    # ---- 标准接口 ----

    async def run(self, task: str, **params: Any) -> Any:
        """标准 agent 入口：执行一次多媒体生成任务。

        返回 ToolResult（SUCCESS/PENDING/FAILED）。``params`` 透传给
        MultimediaRequest，支持 kind / model / description / wait / afs / conv_id /
        reference_images / image_url / image_url_last / params 等字段。
        其中 ``params`` 为 dict 时并入 provider 参数覆盖。

        Examples::

            await agent.run("一只在星空下弹吉他的猫", style="cyberpunk")
            await agent.run("日落海浪慢镜头", kind="video", wait=False)
        """
        request = self._build_request(task, params)
        return await self.executor.run(request)

    async def generate_image(self, prompt: str, **params: Any) -> Any:
        """生成图片（kind=image 的便捷入口）。"""
        params.setdefault("kind", KIND_IMAGE)
        return await self.run(prompt, **params)

    async def generate_video(self, prompt: str, **params: Any) -> Any:
        """生成视频（kind=video 的便捷入口）。"""
        params.setdefault("kind", KIND_VIDEO)
        return await self.run(prompt, **params)

    # ---- 异步子任务（agent 协作范式） ----

    def to_async_delegate(self, afs: Any = None, conv_id: str = "") -> Any:
        """构造可交给 spawn_agent_task / AsyncTaskManager 的委派协程。

        返回一个无参 async callable：被调用时把任务描述解析为一次多媒体生成
        （kind 优先从 ``task`` 里的 kind= 标记或默认判断），执行并返回 ToolResult。
        这样多媒体 agent 可作为异步子 agent 被主 agent 委派。

        Args:
            afs: 本次可用的 AFS 实例（后台执行时上下文可能已失效，需外部注入）。
            conv_id: 所属会话 ID（用于异步通知过滤）。
        """
        # 与 ``thinking`` 保持一致的配置解析：委派时若已绑定 app 的 ext_config，
        # 按当前应用的多媒体模板配置（重新）解析，使同一模板实例可服务不同 app。
        if getattr(self, "ext_config", None) is not None:
            self._config = self._resolve_config()
            self._executor.config = self._config

        async def _delegate(
            subagent_name: str = "",
            task: str = "",
            context: Optional[Dict[str, Any]] = None,
        ):
            # 未注入 AFS 时懒加载，确保后台交付文件也正确落盘
            bound_afs = afs if afs is not None else self.executor.afs
            if bound_afs is None:
                bound_afs = await self._ensure_agent_file_system()
            bound_conv = conv_id or self.executor.conv_id
            ctx = context or {}
            kind = ctx.get("kind") or ctx.get("media_kind") or ""
            model = ctx.get("model") or ""
            params = ctx.get("params") or {}
            # 参考图 / 首帧 / 尾帧（图片输入，图生图/图生视频/首尾帧生视频）
            reference_images = ctx.get("reference_images") or []
            image_url = ctx.get("image_url") or ""
            image_url_last = ctx.get("image_url_last") or ""
            # 允许把参考图等平铺在 context 顶层（无 params 键时）
            if not reference_images and ctx.get("images"):
                reference_images = ctx.get("images")
            if not image_url and ctx.get("image"):
                image_url = ctx.get("image")
            # task 里可能带 kind= 标记，如 "生成视频: ..."
            if not kind and "kind=" in task:
                for seg in task.split():
                    if seg.startswith("kind="):
                        kind = seg.split("=", 1)[1].strip("\"'")
            request = self._build_request(
                task,
                {
                    "kind": kind,
                    "model": model,
                    "params": params,
                    "reference_images": reference_images,
                    "image_url": image_url,
                    "image_url_last": image_url_last,
                    "wait": False,
                    "afs": bound_afs,
                    "conv_id": bound_conv,
                },
            )
            return await self.executor.run(request)

        return _delegate

    # ---- 内部 ----

    def _build_request(self, task: str, params: Dict[str, Any]) -> MultimediaRequest:
        """把 run / delegate 的参数字典归一化为 MultimediaRequest。"""
        raw = dict(params or {})

        # 允许把 provider 参数直接平铺在顶层（无 params 键时）
        provider_params = raw.pop("params", None) or {}
        if not isinstance(provider_params, dict):
            provider_params = {}

        # 顶层直接的 provider 参数（除保留字段外）并入 provider_params
        reserved = {
            "kind",
            "model",
            "description",
            "wait",
            "afs",
            "conv_id",
            "reference_images",
            "image_url",
            "image_url_last",
            "prompt",
        }
        for k, v in list(raw.items()):
            if k not in reserved:
                provider_params[k] = provider_params.get(k, v)

        return MultimediaRequest(
            prompt=task,
            kind=raw.get("kind") or self.config.capability or KIND_IMAGE,
            model=raw.get("model") or "",
            params=provider_params,
            description=raw.get("description") or "",
            wait=raw.get("wait"),
            afs=raw.get("afs"),
            conv_id=raw.get("conv_id") or self.executor.conv_id,
            reference_images=raw.get("reference_images") or [],
            image_url=raw.get("image_url") or "",
            image_url_last=raw.get("image_url_last") or "",
        )


__all__ = [
    "MultimediaAgent",
]
