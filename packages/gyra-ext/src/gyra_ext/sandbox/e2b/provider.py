"""
E2B Sandbox Provider

基于 E2B Cloud Sandbox (https://e2b.dev) 实现 ``SandboxBase`` 接口，注册为
``e2b`` provider。通过配置 ``sandbox.type = "e2b"`` 即可切换使用云端沙箱。

依赖：``e2b``（可选，``pip install gyra-ext[sandbox_e2b]``）。
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from gyra.sandbox.base import SandboxBase
from gyra.sandbox.client.sandbox.types import SandboxDetail

from gyra_ext.sandbox.e2b.config import E2BSandboxConfig
from gyra_ext.sandbox.e2b.shell_client import E2BShellClient
from gyra_ext.sandbox.e2b.file_client import E2BFileClient

logger = logging.getLogger(__name__)


class E2BSandbox(SandboxBase):
    """E2B 云端沙箱实现。

    使用 E2B SDK（``e2b``）创建云端沙箱，并通过 ``E2BShellClient`` /
    ``E2BFileClient`` 提供 Shell 与文件能力。
    """

    def __init__(
        self,
        config: Optional[E2BSandboxConfig] = None,
        **kwargs,
    ):
        self._config = config or E2BSandboxConfig()
        self._sandbox: Any = None  # E2B Sandbox 实例

        super().__init__(
            sandbox_id=kwargs.get("sandbox_id", ""),
            user_id=kwargs.get("user_id", "default"),
            agent=kwargs.get("agent", "default_agent"),
            conversation_id=kwargs.get("conversation_id"),
            sandbox_domain=kwargs.get("sandbox_domain"),
            sandbox_detail=kwargs.get("sandbox_detail"),
            work_dir=kwargs.get("work_dir", self._config.work_dir),
            enable_skill=kwargs.get("enable_skill", True),
            skill_dir=kwargs.get("skill_dir", self._config.skill_dir),
            connection_config=None,
        )

        self._created_at: Optional[float] = None
        self._timeout_at: Optional[float] = None
        self._is_running = False
        self._metadata: Dict[str, str] = kwargs.get("metadata", {})

        self._shell: Optional[E2BShellClient] = None
        self._file: Optional[E2BFileClient] = None

    @classmethod
    def provider(cls) -> str:
        """Provider identifier."""
        return "e2b"

    @classmethod
    async def create(
        cls,
        user_id: str,
        agent: str,
        template: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        allow_internet_access: bool = True,
        **kwargs,
    ) -> "E2BSandbox":
        """创建一个新的 E2B 云端沙箱。"""
        e2b = cls._import_sdk()

        config = E2BSandboxConfig.from_dict(kwargs.get("e2b_config", {}))

        # E2B 专用配置优先；仅当未配置时才回退到通用参数
        if not kwargs.get("e2b_config"):
            if template:
                config.template = template
            if timeout:
                config.timeout = timeout
        if metadata:
            config.metadata = dict(metadata)

        api_key = config.resolved_api_key()
        if not api_key:
            raise RuntimeError(
                "E2B API key 未配置：请设置配置项 e2b_config.api_key 或环境变量 E2B_API_KEY"
            )

        sandbox_id = f"e2b_{user_id}_{agent}_{int(time.time() * 1000)}"

        logger.info(
            "Creating E2B sandbox: template=%s timeout=%s user=%s agent=%s",
            config.template, config.timeout, user_id, agent,
        )

        # E2B 沙箱 timeout 单位为秒，上限 300
        live_timeout = min(int(config.timeout or 300), 300)

        sandbox = await asyncio.to_thread(
            e2b.Sandbox.create,
            template=config.template,
            api_key=api_key,
            timeout=live_timeout,
            metadata={
                **config.metadata,
                "user_id": str(user_id),
                "agent": str(agent),
            },
            env_vars=config.env_vars,
        )

        instance = cls(
            config=config,
            sandbox_id=getattr(sandbox, "sandbox_id", sandbox_id),
            user_id=user_id,
            agent=agent,
            work_dir=config.work_dir,
            skill_dir=config.skill_dir,
            metadata=config.metadata,
            **kwargs,
        )
        instance._sandbox = sandbox
        instance._is_running = True
        instance._created_at = time.time()

        await instance._init_clients()
        return instance

    @staticmethod
    def _import_sdk():
        """懒加载并校验 e2b SDK。"""
        try:
            import e2b
            return e2b
        except ImportError as exc:
            raise RuntimeError(
                "未安装 e2b SDK，请执行: pip install 'gyra-ext[sandbox_e2b]' "
                "（或 pip install e2b）"
            ) from exc

    async def _init_clients(self) -> None:
        """初始化 shell / file 客户端。"""
        if not self._sandbox:
            raise RuntimeError("E2B sandbox not initialized")

        self._shell = E2BShellClient(
            sandbox_id=self.sandbox_id,
            work_dir=self.work_dir,
            sandbox=self._sandbox,
            skill_dir=self.skill_dir,
        )
        self._file = E2BFileClient(
            sandbox_id=self.sandbox_id,
            work_dir=self.work_dir,
            sandbox=self._sandbox,
            skill_dir=self.skill_dir,
        )

    async def run_code(self, code: str, language: str = "python") -> str:
        """在 E2B 沙箱中运行 Python 代码。"""
        if not self._sandbox:
            raise RuntimeError("E2B sandbox not initialized")
        result = await asyncio.to_thread(self._sandbox.run_python, code)
        return (result.stdout or "") + (result.stderr or "")

    async def install_dependencies(self, dependencies: List[str]) -> bool:
        """在 E2B 沙箱中安装 Python 依赖。"""
        if not dependencies:
            return True
        cmd = "pip install " + " ".join(dependencies)
        result = await self._shell.exec_command(command=cmd)
        return result.exit_code == 0

    # ---- SandboxBase 接口 ----

    async def is_running(self, request_timeout: Optional[float] = None) -> bool:
        return self._is_running

    async def connect(self, timeout: Optional[int] = None, **opts) -> "E2BSandbox":
        """连接已有 E2B 沙箱（当前进程内已持有实例则直接返回）。"""
        if not self._sandbox:
            raise RuntimeError(f"E2B sandbox {self.sandbox_id} not found")
        self._is_running = True
        return self

    async def kill(self, template: Optional[str] = None) -> bool:
        """关闭 E2B 沙箱。"""
        if self._sandbox:
            try:
                await asyncio.to_thread(self._sandbox.kill)
            except Exception as exc:  # noqa: BLE001
                logger.warning("E2B kill failed: %s", exc)
            self._sandbox = None
        self._is_running = False
        return True

    async def close(self, template: Optional[str] = None) -> bool:
        return await self.kill(template)

    async def set_timeout(self, instance_id: str, timeout: int, **kwargs) -> None:
        """延长 E2B 沙箱存活时间。"""
        if self._sandbox:
            await asyncio.to_thread(
                self._sandbox.set_timeout, min(int(timeout), 300)
            )
        if self._created_at:
            self._timeout_at = self._created_at + int(timeout)

    async def get_info(self, **opts) -> Dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "provider": self.provider(),
            "user_id": self.user_id,
            "agent": self.agent,
            "conversation_id": self.conversation_id,
            "work_dir": self.work_dir,
            "skill_dir": self.skill_dir,
            "is_running": await self.is_running(),
            "created_at": self._created_at,
            "metadata": self._metadata,
            "config": {
                "template": self._config.template,
                "timeout": self._config.timeout,
            },
        }

    async def get_metrics(
        self, start: Optional[float] = None, end: Optional[float] = None, **opts
    ) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": time.time(),
                "memory": 0,
                "cpu": 0,
                "disk": 0,
            }
        ]

    # ---- SandboxBase 属性 ----

    @property
    def shell(self) -> Optional[E2BShellClient]:
        return self._shell

    @property
    def file(self) -> Optional[E2BFileClient]:
        return self._file

    @property
    def browser(self):
        """E2B 浏览器自动化暂未接入。"""
        return None

    @property
    def detail(self) -> Optional[SandboxDetail]:
        return None

    async def __aenter__(self) -> "E2BSandbox":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.kill()