"""
E2B Shell Client

基于 E2B Cloud SDandbox 的命令执行能力实现 ``ShellClient`` 接口。
E2B SDK 的命令执行是同步的，这里通过 ``asyncio.to_thread`` 包装为异步接口。
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from gyra.sandbox.client.shell.client import ShellClient, OMIT
from gyra.sandbox.client.shell.type.shell_command_result import ShellCommandResult
from gyra.sandbox.client.shell.type.shell_create_session_response import (
    ShellCreateSessionResponse,
)
from gyra.sandbox.client.shell.type.active_shell_sessions_result import (
    ActiveShellSessionsResult,
)
from gyra.sandbox.client.shell.type.shell_kill_result import ShellKillResult
from gyra.sandbox.client.shell.type.shell_wait_result import ShellWaitResult
from gyra.sandbox.client.shell.type.shell_write_result import ShellWriteResult

logger = logging.getLogger(__name__)


class E2BShellClient(ShellClient):
    """E2B 云端沙箱的 Shell 客户端。

    通过 E2B SDK 的 ``Sandbox.commands.run`` 执行命令，并返回统一的
    ``ShellCommandResult``。E2B 不提供持久 shell 会话，因此会话级方法
    （create_session / view / write_to_process 等）仅提供基础占位实现。
    """

    def __init__(
        self,
        sandbox_id: str,
        work_dir: str,
        sandbox: Any,  # E2B Sandbox 实例
        skill_dir: str = None,
        **kwargs,
    ):
        super().__init__(sandbox_id, work_dir, connection_config=None, **kwargs)
        self._sandbox = sandbox
        self._sandbox_id = sandbox_id
        self._logical_work_dir = work_dir or "/home/user"
        self._skill_dir = skill_dir

    def _resolve_cwd(self, work_dir: Any) -> str:
        """将逻辑 cwd 解析为 E2B 沙箱内的绝对路径。"""
        target = self._logical_work_dir
        if work_dir is not OMIT and work_dir is not None:
            target = work_dir
        if not target:
            return self._logical_work_dir
        return str(target).rstrip("/") or "/"

    async def exec_command(
        self,
        *,
        command: str,
        work_dir: Optional[str] = OMIT,
        async_mode: Optional[bool] = OMIT,
        timeout: Optional[float] = OMIT,
        terminal_id: Optional[str] = None,
        request_options: Optional[dict] = None,
    ) -> ShellCommandResult:
        """在 E2B 沙箱中同步执行命令并返回结果。"""
        cwd = self._resolve_cwd(work_dir)

        timeout_val = 60.0
        if timeout is not OMIT and timeout is not None:
            timeout_val = timeout

        logger.info("E2BShellClient exec: %s in %s", command, cwd)

        try:
            result = await asyncio.to_thread(
                self._sandbox.commands.run,
                cmd=command,
                timeout=int(timeout_val),
                workdir=cwd,
            )
            output = (result.stdout or "") + (result.stderr or "")
            exit_code = int(getattr(result, "exit_code", 0))
            status_val = "completed" if exit_code == 0 else "failed"
            return ShellCommandResult(
                session_id=self._sandbox_id,
                status=status_val,
                command=command,
                output=output,
                exit_code=exit_code,
                console=[],
            )
        except Exception as e:  # noqa: BLE001
            logger.error("E2B exec failed: %s", e)
            return ShellCommandResult(
                session_id=self._sandbox_id,
                status="failed",
                command=command,
                output=str(e),
                exit_code=-1,
                console=[],
            )

    async def view(self, *, terminal_id: Optional[str] = None, **kwargs) -> ShellCommandResult:
        """E2B 无持久会话，返回空结果。"""
        return ShellCommandResult(
            session_id=self._sandbox_id,
            status="completed",
            command=None,
            output="",
            exit_code=0,
            console=[],
        )

    async def create_session(
        self, *, exec_dir: Optional[str] = OMIT, request_options: Optional[dict] = None
    ) -> ShellCreateSessionResponse:
        """E2B 无持久 shell 会话，返回空响应。"""
        return ShellCreateSessionResponse(
            session_id=self._sandbox_id,
            working_dir=self._logical_work_dir,
        )

    async def wait_for_process(
        self, *, seconds: Optional[int] = OMIT, request_options: Optional[dict] = None
    ) -> ShellWaitResult:
        return ShellWaitResult(status="completed")

    async def write_to_process(
        self,
        *,
        input: str,
        press_enter: bool,
        request_options: Optional[dict] = None,
        terminal_id: Optional[str] = None,
    ) -> ShellWriteResult:
        """E2B 无持久交互进程，写入视为成功空操作。"""
        return ShellWriteResult(status="completed")

    async def kill_process(
        self, *, request_options: Optional[dict] = None
    ) -> ShellKillResult:
        return ShellKillResult(status="completed", returncode=0)

    async def get_terminal_url(self, *, request_options: Optional[dict] = None) -> str:
        return ""

    async def list_sessions(
        self, *, request_options: Optional[dict] = None
    ) -> ActiveShellSessionsResult:
        return ActiveShellSessionsResult(sessions={})

    async def cleanup_all_sessions(
        self, *, request_options: Optional[dict] = None
    ) -> Dict:
        return {}

    async def cleanup_session(
        self, *, request_options: Optional[dict] = None
    ) -> Dict:
        return {}