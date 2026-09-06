"""AppCapability —— 子 Agent 自管理资源能力(RFC-006 Stage 4 + Phase D)。

App 是首个落地的自管理 Capability,用于验证 config→Capability→declare→prepare 全链。
特性:
- **无构造 I/O**:GptAppResource.__init__ 只存属性;AppCapability.prepare no-op。
- **declare 纯函数**:渲染 app 描述进 SYSTEM(复用 _APP_TEMPLATE_ZH / _render_app_desc)。
- **execute 不接管**:agent_start(子 agent 调度)是多轮对话而非单工具调用,
  形状对不上 Capability.execute —— 保持 AgentAction 走 sender.send(recipient) 团队
  派发。故 AppCapability.execute 抛 NotImplementedError(agent_start 不经 Route B)。
- **Phase D 收编 start_app**:子 agent 启动逻辑从 GptAppResource._start_app 移植为
  start_app/async_execute,供 AgentAction 与 cron ToolContext 注入使用(替代 v1
  AppResource 实例)。

AppCapability 直接渲染 app 描述进 SYSTEM(旧 wrapper 桩路径已删)。
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from gyra.core.interface.resource.bundle import (
    CacheScope,
    Contribution,
    Lifetime,
    Slot,
)
from gyra.core.interface.resource.capability import Capability
from gyra.core.interface.resource.executor import (
    ExecutorCall,
    ExecutorStatus,
    ReleaseReason,
)

logger = logging.getLogger(__name__)

_APP_TEMPLATE_ZH = (
    "{{app_name}}：{% if app_code %}(app_code: {{app_code}}){% endif %}"
    "调用此资源与应用 {{app_name}} 进行交互。"
    "应用 {{app_name}} 有什么用？{{description}}"
)


def _render_app_desc(app_name: str, app_code: str, description: str) -> str:
    from gyra.util.template_utils import render

    return render(
        _APP_TEMPLATE_ZH,
        {"app_name": app_name, "app_code": app_code, "description": description},
    )


class AppCapability(Capability):
    """子 Agent 自管理能力:持有 app 元数据,declare 渲染描述。

    capability_id="app";executor_id="app:{app_code}"(多 app 唯一,避免 provider key
    冲突)。execute 不接管 agent_start(保持 AgentAction)。
    """

    capability_id = "app"

    def __init__(
        self,
        app_name: Optional[str] = None,
        app_code: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self._app_name = app_name or ""
        self._app_code = app_code or ""
        self._description = description or ""
        self._status = ExecutorStatus.UNINITIALIZED

    @classmethod
    def from_config(cls, value: dict, system_app: Any = None) -> "AppCapability":
        """从 AgentResource.value dict 构造(无 I/O)。

        value 形如 {"app_code":..., "app_name":..., "app_desc":...}。
        """
        value = value or {}
        return cls(
            app_name=value.get("app_name") or value.get("name") or "",
            app_code=value.get("app_code") or "",
            description=value.get("app_desc") or value.get("description") or "",
        )

    @property
    def executor_id(self) -> str:
        # 与 capability_id 解耦:多 app 唯一,避免 executor_provider key 冲突。
        return f"app:{self._app_code}" if self._app_code else "app"

    # ----------------------------- 输入投影(纯) -------------------------- #
    def declare(self, config: Any = None) -> List[Contribution]:
        """渲染 app 描述进 SYSTEM。无 I/O。

        agent_start 工具不在此贡献(由 react_master 系统注入路径提供,builtin executor)。
        """
        if not self._app_name:
            return []
        try:
            text = _render_app_desc(
                self._app_name, self._app_code, self._description
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[app-capability] render app desc failed: {e}")
            text = f"{self._app_name}: {self._description}"
        return [
            Contribution(
                capability_id=self.capability_id,
                slot=Slot.SYSTEM,
                content=text,
                lifetime=Lifetime.CONFIG_STATIC,
                cache_scope=CacheScope.USER,
                order=30,
            )
        ]

    def requires(self, config: Any = None) -> List[str]:
        # app 无 live 实例 / 不依赖共享 executor(不调 execute)。
        return []

    # ----------------------------- 生命周期(无 I/O) ----------------------- #
    async def prepare(self) -> None:
        self._status = ExecutorStatus.READY

    async def execute(self, call: ExecutorCall) -> Any:
        # agent_start 保持 AgentAction 团队派发,不经 Capability.execute。
        raise NotImplementedError(
            "AppCapability.execute 不接管 agent_start —— 保持 AgentAction 路由"
        )

    async def release(self, reason: ReleaseReason) -> None:
        self._status = ExecutorStatus.RELEASED

    # ----------------------------- Phase D: 子 Agent 启动 ---------------- #
    @property
    def app_code(self) -> str:
        return self._app_code

    @property
    def app_name(self) -> str:
        return self._app_name

    @property
    def app_desc(self) -> str:
        return self._description

    # 多媒体 Agent 配置缓存:None 表示未解析,dict 为已解析的启用配置
    _multimedia_config_cache: Optional[dict] = None

    def get_multimedia_config(self) -> Optional[dict]:
        """返回该子 Agent app 的多媒体 Agent 配置(若启用),否则 None。

        供 core 层按 app_code 寻址时解析目标 app 自身的 ``ext_config.multimedia_agent``,
        从而动态构造绑定该 app 配置的独立 MultimediaAgent 实例(多实例互不覆盖)。
        移植自 GptAppResource.get_multimedia_config。
        """
        if self._multimedia_config_cache is not None:
            return self._multimedia_config_cache
        try:
            from gyra._private.config import Config
            from gyra_serve.building.app.service.service import Service as AppService

            cfg = AppService.get_instance(Config().SYSTEM_APP).get_multimedia_agent_config(
                self._app_code
            )
        except Exception:  # noqa: BLE001 - 解析失败按非多媒体处理
            cfg = None
        if cfg and cfg.get("enabled"):
            self._multimedia_config_cache = cfg
        else:
            self._multimedia_config_cache = None
        return self._multimedia_config_cache

    async def start_app(
        self,
        user_input: str,
        sender: Any = None,
        conv_uid: Optional[str] = None,
        parent_depth: Optional[int] = None,
        extra_info: Optional[dict] = None,
    ) -> Any:
        """启动子 Agent app(移植自 GptAppResource._start_app)。

        sender 容忍为 None(cron ToolContext 注入路径无父 agent 实例):
        此时不做上下文透传与沙箱继承。
        """
        import uuid

        from gyra.agent import AgentMessage
        from gyra.agent.core.agent import AgentContext
        from gyra_serve.agent.agents.app_agent_manage import get_app_manager

        conv_uid = str(uuid.uuid4()) if conv_uid is None else conv_uid
        gpts_app = await get_app_manager().get_app(self._app_code)

        child_context: Optional[AgentContext] = None
        if parent_depth is not None:
            child_extra: dict = {"subagent_depth": parent_depth + 1}
            parent_ctx = getattr(sender, "agent_context", None)
            if parent_ctx is not None:
                parent_extra = parent_ctx.extra or {}
                child_extra["main_conv_id"] = (
                    parent_extra.get("main_conv_id") or parent_ctx.conv_id
                )
                if "workspace_id" in parent_extra:
                    child_extra["workspace_id"] = parent_extra["workspace_id"]
                # 透传操作者身份 user_request：RBAC / 技能发布等 fail-closed 工具
                # 依赖它断言管理员身份，缺失会让子会话报"无权限"。
                if "user_request" in parent_extra:
                    child_extra["user_request"] = parent_extra["user_request"]
            child_context = AgentContext(
                conv_id=conv_uid,
                conv_session_id=conv_uid,
                gpts_app_code=gpts_app.app_code,
                gpts_app_name=gpts_app.app_name,
                # agent_app_code 是当前子 Agent 的应用 ID：V2 引擎构造 StepEvent/
                # ToolContext/PermissionGate 时严格要求非空字符串，缺省 None 会在
                # 子会话发射事件时报 "agent_id Input should be a valid string"。
                agent_app_code=gpts_app.app_code,
                # 透传父 Agent 的身份/权限字段：子 Agent 沿用发起者的用户身份，
                # 避免子会话因 user_id/staff_no 缺失被判“无权限”。
                user_id=getattr(parent_ctx, "user_id", None),
                user_name=getattr(parent_ctx, "user_name", None),
                staff_no=getattr(parent_ctx, "staff_no", None),
                language=gpts_app.language,
                enable_vis_message=False,
                extra=child_extra,
            )

        app_agent = await get_app_manager().create_agent_by_app_code(
            gpts_app, conv_uid=conv_uid, context=child_context
        )

        # 沙箱实例继承:子 Agent 共享父 Agent 的 sandbox_manager(只共享客户端,
        # 不转移生命周期所有权)。
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
            # message_id 必传(同 GptAppResource._start_app):缺省 None 会导致子 Agent
            # 上下文事件在 push_context_event 被 `if not task_id: return` 丢弃。
            message_id=conv_uid,
            context={
                "conv_uid": conv_uid,
                **(extra_info or {}),
            },
            rounds=0,
        )
        return await app_agent.generate_reply(
            received_message=agent_message, sender=sender
        )

    async def async_execute(self, user_input: str = "", parent_agent: Any = None, **kwargs) -> Any:
        """兼容 v1 AppResource.async_execute 调用形状(ToolContext 注入路径用)。"""
        return await self.start_app(user_input=user_input, sender=parent_agent)