"""Application Resources for the agent."""

import logging
import uuid
from typing import List, Optional

from gyra._private.config import Config
from gyra.agent import AgentMessage, ConversableAgent
from gyra.agent.core.agent import AgentContext
from gyra.agent.resource.app import AppInfo, AppResource
from gyra_serve.agent.agents.app_agent_manage import get_app_manager

logger = logging.getLogger(__name__)

CFG = Config()
class GptAppResource(AppResource):
    """AppResource resource class."""

    def __init__(self, name: str, app_code: str, **kwargs):
        """Initialize AppResource resource."""
        super().__init__(name, **kwargs)

        self._app_code = app_code
        self._app_name = kwargs.get("app_name")
        self._app_icon = kwargs.get("app_icon") or kwargs.get("icon")
        self._app_desc = kwargs.get("app_desc") or kwargs.get("app_describe")

    @property
    def app_code(self) -> str:
        """Return the app code."""
        return self._app_code

    @property
    def app_desc(self) -> str:
        """Return the app description."""
        return self._app_desc

    @property
    def app_name(self) -> str:
        """Return the app name."""
        return self._app_name

    @property
    def app_icon(self) -> str:
        """Return the app icon."""
        return self._app_icon

    # 多媒体 Agent 配置缓存：None 表示未解析，dict 为已解析的启用配置
    _multimedia_config_cache: Optional[dict] = None

    def get_multimedia_config(self) -> Optional[dict]:
        """返回该子 Agent app 的多媒体 Agent 配置（若启用），否则 None。

        供 core 层按 app_code 寻址时解析目标 app 自身的 ``ext_config.multimedia_agent``，
        从而动态构造绑定该 app 配置的独立 MultimediaAgent 实例（多实例互不覆盖）。
        """
        if self._multimedia_config_cache is not None:
            return self._multimedia_config_cache
        try:
            from gyra_serve.building.app.service.service import Service as AppService

            cfg = AppService.get_instance(CFG.SYSTEM_APP).get_multimedia_agent_config(
                self._app_code
            )
        except Exception:  # noqa: BLE001 - 解析失败按非多媒体处理
            cfg = None
        if cfg and cfg.get("enabled"):
            self._multimedia_config_cache = cfg
        else:
            self._multimedia_config_cache = None
        return self._multimedia_config_cache

    @classmethod
    def _get_app_list(cls, **kwargs) -> List[AppInfo]:
        from gyra_serve.agent.agents.app_agent_manage import get_app_manager

        # Only call this function when the system app is initialized
        apps = get_app_manager().get_gyras(query=kwargs.get("query"), user_code=kwargs.get("user_code"), sys_code=kwargs.get("sys_code"))
        app_list = []
        for app in apps:
            app_list.append(
                AppInfo(name=app.app_name, icon=app.icon, code=app.app_code, desc=app.app_describe)
            )
        return app_list

    async def _start_app(
        self,
        user_input: str,
        sender: ConversableAgent,
        conv_uid: Optional[str] = None,
        parent_depth: Optional[int] = None,
        extra_info: Optional[dict] = None,
    ) -> AgentMessage:
        """Start App By AppResource.

        Args:
            parent_depth: 父 agent 的 subagent_depth。传入时，子 agent 的
                AgentContext.extra["subagent_depth"] = parent_depth + 1。
                None 时不写入（保持默认 0）。
            extra_info: 父 agent 传来的附加元数据。其中的 ``media``（dict）会写入
                子 agent 收到的 ``AgentMessage.context``，供多媒体 Agent 读取生成参数
                （kind/model/size/resolution/duration 等）。
        """
        conv_uid = str(uuid.uuid4()) if conv_uid is None else conv_uid
        gpts_app = await get_app_manager().get_app(self._app_code)

        child_context: Optional[AgentContext] = None
        if parent_depth is not None:
            # 透传主对话上下文到子 agent：main_conv_id（授权通知主 agent 用，P1）
            # 和 workspace_id（沙箱共用用，P2）。嵌套时继承父的 main_conv_id，顶层用父 conv_id。
            child_extra: dict = {"subagent_depth": parent_depth + 1}
            parent_ctx = getattr(sender, "agent_context", None)
            if parent_ctx is not None:
                parent_extra = parent_ctx.extra or {}
                child_extra["main_conv_id"] = (
                    parent_extra.get("main_conv_id") or parent_ctx.conv_id
                )
                if "workspace_id" in parent_extra:
                    child_extra["workspace_id"] = parent_extra["workspace_id"]
            child_context = AgentContext(
                conv_id=conv_uid,
                conv_session_id=conv_uid,
                gpts_app_code=gpts_app.app_code,
                gpts_app_name=gpts_app.app_name,
                language=gpts_app.language,
                enable_vis_message=False,
                extra=child_extra,
            )

        app_agent = await get_app_manager().create_agent_by_app_code(
            gpts_app, conv_uid=conv_uid, context=child_context
        )

        # 沙箱实例继承：子 Agent 共享父 Agent 的 sandbox_manager（只共享客户端，
        # 不转移生命周期所有权——父会话清理时子任务通常已结束；场景空间共享
        # 沙箱常驻进程，天然安全）。子 Agent 的 AFS 交付与沙箱工具因此落到与
        # 主任务相同的工作目录，而不是各自为政或完全没有沙箱。
        try:
            parent_sandbox_mgr = getattr(sender, "sandbox_manager", None)
            if parent_sandbox_mgr is not None and getattr(
                app_agent, "sandbox_manager", None
            ) is None:
                app_agent.sandbox_manager = parent_sandbox_mgr
                logger.info(
                    f"[start_app] child agent inherits parent sandbox "
                    f"(parent={getattr(sender, 'name', '?')}, app={self._app_code})"
                )
        except Exception as e:  # noqa: BLE001 - 继承失败不影响子 agent 运行
            logger.warning(f"[start_app] inherit parent sandbox failed: {e}")

        agent_message = AgentMessage(
            content=user_input,
            current_goal=user_input,
            context={
                "conv_uid": conv_uid,
                **(extra_info or {}),
            },
            rounds=0,
        )
        reply_message: AgentMessage = await app_agent.generate_reply(
            received_message=agent_message, sender=sender
        )

        return reply_message
