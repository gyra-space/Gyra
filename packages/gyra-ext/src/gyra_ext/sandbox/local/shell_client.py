"""
Local Shell Client Implementation
"""

from typing import Optional, Dict, cast, Any
import os
import logging
import asyncio
import shlex
import subprocess
import time
from gyra.sandbox.client.shell.client import ShellClient
from gyra.sandbox.client.shell.type.shell_command_result import ShellCommandResult

logger = logging.getLogger(__name__)

OMIT = cast(Any, ...)


class LocalShellClient(ShellClient):
    """本地 Shell 客户端实现"""

    def __init__(
        self,
        sandbox_id: str,
        work_dir: str,
        runtime,
        skill_dir: str = None,
        host_work_dir: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(sandbox_id, work_dir, connection_config=None, **kwargs)
        self._runtime = runtime
        self._sandbox_id = sandbox_id
        self._logical_work_dir = work_dir or "/home/ubuntu"
        self._skill_dir = skill_dir
        self._host_work_dir = host_work_dir

        # Physical roots that define the sandbox boundary.
        self._session_root = os.path.abspath(
            os.path.join(self._runtime.base_dir, self._sandbox_id)
        )
        if host_work_dir:
            self._work_dir_physical = os.path.abspath(host_work_dir)
        else:
            logical_rel = self._logical_work_dir.lstrip("/")
            self._work_dir_physical = os.path.abspath(
                os.path.join(self._session_root, logical_rel)
            )

        self._allowed_roots = [self._session_root, self._work_dir_physical]
        if skill_dir:
            self._allowed_roots.append(os.path.realpath(skill_dir))
        self._allowed_roots.append("/mnt")

    def _resolve_cwd(self, work_dir: Any) -> str:
        """Resolve a logical cwd to a physical path inside the sandbox."""
        target_cwd = self._work_dir_physical
        if work_dir is not OMIT and work_dir is not None:
            target_cwd = work_dir

        if not target_cwd:
            return self._work_dir_physical

        # The physical work directory itself is always valid.
        real_target = os.path.realpath(target_cwd)
        if real_target == os.path.realpath(self._work_dir_physical):
            return real_target

        # Whitelisted host paths: /mnt and skill_dir are accessed directly.
        if os.path.isabs(target_cwd):
            for allowed in ("/mnt", self._skill_dir):
                if allowed and (
                    target_cwd == allowed or target_cwd.startswith(f"{allowed}/")
                ):
                    return os.path.realpath(target_cwd)

            # Map logical work_dir prefix (e.g. /data/workspace) to physical work_dir.
            if target_cwd.startswith(self._logical_work_dir):
                relative = target_cwd[len(self._logical_work_dir) :].lstrip("/")
                physical = os.path.abspath(
                    os.path.join(self._work_dir_physical, relative)
                )
                return self._ensure_inside_allowed(physical)

            # Any other absolute path is considered an escape attempt.
            raise PermissionError(
                f"Absolute cwd {target_cwd} is outside the sandbox work directory"
            )

        # Relative paths resolve against the physical work directory.
        physical = os.path.abspath(os.path.join(self._work_dir_physical, target_cwd))
        return self._ensure_inside_allowed(physical)

    def _ensure_inside_allowed(self, physical_path: str) -> str:
        """Verify that *physical_path* stays within an allowed root.

        Roots are stored with os.path.abspath (symlinks unresolved), while
        *physical_path* is compared via os.path.realpath (symlinks resolved).
        When the sandbox temp dir lives behind a symlink (e.g. macOS
        /var -> /private/var), both sides must be resolved consistently or
        every legitimate workspace path is falsely rejected as an escape.
        """
        real = os.path.realpath(physical_path)
        for root in self._allowed_roots:
            if not root:
                continue
            root_real = os.path.realpath(root)
            if real == root_real or real.startswith(os.path.join(root_real, "")):
                return real
        raise PermissionError(
            f"Working directory {physical_path} escapes sandbox allowed roots"
        )

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
        """执行 Shell 命令"""

        try:
            cwd = self._resolve_cwd(work_dir)
        except PermissionError as exc:
            logger.warning(f"LocalShellClient rejected cwd: {exc}")
            return ShellCommandResult(
                session_id=self._sandbox_id,
                status="failed",
                command=command,
                output=str(exc),
                exit_code=1,
                console=[],
            )

        try:
            from gyra.sandbox.sandbox_utils import validate_shell_command

            validate_shell_command(
                command, cwd, allowed_roots=self._allowed_roots
            )
        except (ValueError, PermissionError) as exc:
            logger.warning(f"LocalShellClient rejected command: {exc}")
            return ShellCommandResult(
                session_id=self._sandbox_id,
                status="failed",
                command=command,
                output=str(exc),
                exit_code=1,
                console=[],
            )

        # Ensure dir exists, otherwise subprocess fails
        if not os.path.exists(cwd):
            try:
                os.makedirs(cwd, exist_ok=True)
            except Exception:
                cwd = self._work_dir_physical

        timeout_val = 60.0
        if timeout is not OMIT and timeout is not None:
            timeout_val = timeout

        logger.info(f"LocalShellClient exec: {command} in {cwd}")

        try:
            # 安全性提示：LocalShellClient 依赖代码层校验；真正的 OS 级隔离需由
            # LocalSandboxRuntime 的 sandbox-exec / chroot 提供。当前实现已做路径
            # 与命令策略校验，后续可再叠加 sandbox-exec 包装。

            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_val
                )
                exit_code = process.returncode
                output = stdout.decode() if stdout else ""
                error = stderr.decode() if stderr else ""

                # 构造符合 ShellCommandResult 预期的结果
                status_val = (
                    "completed" if exit_code == 0 else "failed"
                )  # 注意 BashCommandStatus 类型

                return ShellCommandResult(
                    session_id=self._sandbox_id,
                    status=status_val,
                    command=command,
                    output=output + error,
                    exit_code=exit_code,
                    console=[],  # console record mock
                )

            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Command timed out: {command}")

        except Exception as e:
            logger.error(f"Local exec failed: {e}")
            raise
