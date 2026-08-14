"""Application Resources for the agent."""

import logging
from typing import List, Optional

from gyra._private.config import Config
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
