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

import logging
from typing import Any, Dict, List, Optional, Tuple

from gyra._private.pydantic import Field
from gyra.agent import AgentMessage, ProfileConfig
from gyra.agent.core.base_agent import ConversableAgent
from gyra.agent.util.llm.llm_client import AgentLLMOut

from .config import MultimediaAgentConfig
from .executor import KIND_IMAGE, KIND_VIDEO, MultimediaExecutor, MultimediaRequest

logger = logging.getLogger(__name__)


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
        把结果输出文本作为回复 content 返回。
        """
        task = ""
        if received_message is not None:
            task = (received_message.content or "").strip()
        elif messages:
            task = (messages[-1].content or "").strip()

        # 主 Agent 运行时读取 app 的多媒体配置（若已绑定）
        if getattr(self, "ext_config", None) is not None:
            self._config = self._resolve_config()
            self._executor.config = self._config

        request = self._build_request(task, {"wait": True})
        result = await self._executor.run(request)

        if result is None:
            return AgentLLMOut(
                llm_name=self._config.default_image_model or "multimedia",
                content="多媒体生成失败：无返回结果。",
                thinking_content="",
                tool_calls=None,
            )
        if not getattr(result, "success", False):
            error = getattr(result, "error", None) or "多媒体生成失败"
            return AgentLLMOut(
                llm_name=self._config.default_image_model or "multimedia",
                content=f"多媒体生成失败：{error}",
                thinking_content="",
                tool_calls=None,
            )
        return AgentLLMOut(
            llm_name=self._config.default_image_model or "multimedia",
            content=str(getattr(result, "output", "") or "已生成。"),
            thinking_content="",
            tool_calls=None,
            extra={"artifacts": getattr(result, "artifacts", None)},
        )

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

        bound_afs = afs if afs is not None else self.executor.afs
        bound_conv = conv_id or self.executor.conv_id

        async def _delegate(
            subagent_name: str = "",
            task: str = "",
            context: Optional[Dict[str, Any]] = None,
        ):
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
            kind=raw.get("kind") or KIND_IMAGE,
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
