import os
import shutil
import asyncio
import aiofiles
import logging
import posixpath
import tempfile
import uuid
from typing import Optional, List, Union, IO, Literal
from datetime import datetime
from pathlib import Path

from gyra.sandbox.client.file.client import FileClient
from gyra.sandbox.client.file.types import (
    EntryInfo,
    FileInfo,
    FileType,
    OSSFile,
    TaskResult,
)

try:
    from gyra.connection_config import Username
except ImportError:
    from gyra.sandbox.connection_config import Username

logger = logging.getLogger(__name__)


class LocalFileClient(FileClient):
    """
    Local implementation of FileClient.
    Operates directly on the local filesystem within the sandbox directory.
    """

    def __init__(
        self,
        sandbox_id: str,
        work_dir: str,
        runtime,
        skill_dir: str = None,
        file_storage_client=None,
        host_work_dir: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            sandbox_id,
            work_dir,
            connection_config=None,
            file_storage_client=file_storage_client,
            **kwargs,
        )
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

    def _get_physical_path(self, path: str) -> str:
        """Resolve logical path to physical path in local sandbox.

        Raises:
            PermissionError: if the resolved path escapes the allowed sandbox roots.
        """
        if not path:
            path = "."

        if os.path.isabs(path):
            # Whitelisted host paths: /mnt and skill_dir are accessed directly.
            for allowed in ("/mnt", self._skill_dir):
                if allowed and (path == allowed or path.startswith(f"{allowed}/")):
                    return os.path.realpath(path)

            # Map logical work_dir prefix (e.g. /data/workspace) to physical work_dir.
            if path.startswith(self._logical_work_dir):
                relative = path[len(self._logical_work_dir) :].lstrip("/")
                physical = os.path.abspath(
                    os.path.join(self._work_dir_physical, relative)
                )
                return self._ensure_inside_allowed(physical)

            # Any other absolute path is considered an escape attempt.
            raise PermissionError(
                f"Absolute path {path} is outside the sandbox work directory"
            )

        # Relative paths resolve against the physical work directory.
        physical = os.path.abspath(os.path.join(self._work_dir_physical, path))
        return self._ensure_inside_allowed(physical)

    def _ensure_inside_allowed(self, physical_path: str) -> str:
        """Verify that *physical_path* stays within an allowed root.

        Uses realpath to follow symlinks safely. Roots are stored with
        os.path.abspath (symlinks unresolved), so each root must also be
        realpath-resolved before comparison; otherwise a sandbox temp dir that
        lives behind a symlink (e.g. macOS /var -> /private/var) causes every
        legitimate workspace path to be falsely rejected as an escape.
        Raises PermissionError on escape.
        """
        real = os.path.realpath(physical_path)
        for root in self._allowed_roots:
            if not root:
                continue
            root_real = os.path.realpath(root)
            if real == root_real or real.startswith(os.path.join(root_real, "")):
                return real
        raise PermissionError(
            f"Path {physical_path} escapes sandbox allowed roots"
        )

    async def read(
        self,
        path: str,
        format: Literal["text", "bytes", "stream"] = "text",
        user=None,
        request_timeout: Optional[float] = None,
    ):
        from gyra.sandbox.client.file.types import FileInfo

        physical_path = self._get_physical_path(path)
        logger.info(f"LocalFileClient read: {path} -> {physical_path}")

        if not os.path.exists(physical_path):
            raise FileNotFoundError(f"File not found: {path}")

        if format == "text":
            async with aiofiles.open(physical_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
        else:
            async with aiofiles.open(physical_path, mode="rb") as f:
                content = await f.read()

        return FileInfo(
            path=path,
            content=content,
            name=os.path.basename(path),
        )

    async def write(
        self,
        path: str,
        data: Union[str, bytes, IO],
        user: Optional[Username] = None,
        overwrite: bool = False,
        save_oss: bool = False,
    ) -> FileInfo:
        physical_path = self._get_physical_path(path)
        logger.info(f"LocalFileClient write: {path} -> {physical_path}")

        if os.path.exists(physical_path) and not overwrite:
            raise FileExistsError(f"File exists: {path}")

        # Ensure parent dirs exist
        os.makedirs(os.path.dirname(physical_path), exist_ok=True)

        mode = "w" if isinstance(data, str) else "wb"
        encoding = "utf-8" if isinstance(data, str) else None

        async with aiofiles.open(physical_path, mode=mode, encoding=encoding) as f:
            await f.write(data)

        return FileInfo(
            path=path, name=os.path.basename(path), last_modify=datetime.now()
        )

    async def list(
        self,
        path: str,
        depth: Optional[int] = 1,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> List[EntryInfo]:
        physical_path = self._get_physical_path(path)
        logger.info(f"LocalFileClient list: {path} -> {physical_path}")

        entries = []
        if not os.path.exists(physical_path):
            return entries

        # Only support depth=1 for now
        with os.scandir(physical_path) as it:
            for entry in it:
                stat = entry.stat()
                entries.append(
                    EntryInfo(
                        name=entry.name,
                        path=os.path.join(path, entry.name),
                        type=FileType.DIR if entry.is_dir() else FileType.FILE,
                        size=stat.st_size,
                        mode=stat.st_mode,
                        permissions=oct(stat.st_mode)[-3:],
                        owner=str(stat.st_uid),
                        group=str(stat.st_gid),
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                    )
                )
        return entries

    async def exists(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> bool:
        physical_path = self._get_physical_path(path)
        return os.path.exists(physical_path)

    async def make_dir(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> bool:
        physical_path = self._get_physical_path(path)
        if os.path.exists(physical_path):
            return False
        os.makedirs(physical_path, exist_ok=True)
        return True

    async def remove(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> None:
        physical_path = self._get_physical_path(path)
        if os.path.isdir(physical_path):
            shutil.rmtree(physical_path)
        else:
            os.remove(physical_path)

    async def get_info(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> EntryInfo:
        physical_path = self._get_physical_path(path)
        stat = os.stat(physical_path)
        return EntryInfo(
            name=os.path.basename(path),
            path=path,
            type=FileType.DIR if os.path.isdir(physical_path) else FileType.FILE,
            size=stat.st_size,
            mode=stat.st_mode,
            permissions=oct(stat.st_mode)[-3:],
            owner=str(stat.st_uid),
            group=str(stat.st_gid),
            modified_time=datetime.fromtimestamp(stat.st_mtime),
        )

    async def create(
        self,
        path: str,
        content: Optional[str] = None,
        user: Optional[Username] = None,
        overwrite: bool = True,
    ) -> FileInfo:
        physical_path = self._get_physical_path(path)
        logger.info(f"LocalFileClient create: {path} -> {physical_path}")

        if os.path.exists(physical_path) and not overwrite:
            raise FileExistsError(f"File exists: {path}")

        os.makedirs(os.path.dirname(physical_path), exist_ok=True)

        if content is not None:
            async with aiofiles.open(physical_path, mode="w", encoding="utf-8") as f:
                await f.write(content)

        return FileInfo(
            path=path,
            name=os.path.basename(path),
            last_modify=datetime.now(),
        )

    async def rename(
        self,
        old_path: str,
        new_path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> EntryInfo:
        old_physical = self._get_physical_path(old_path)
        new_physical = self._get_physical_path(new_path)
        logger.info(f"LocalFileClient rename: {old_path} -> {new_path}")

        os.makedirs(os.path.dirname(new_physical), exist_ok=True)
        shutil.move(old_physical, new_physical)

        return await self.get_info(new_path, user, request_timeout)

    async def find_file(self, path: str, glob: str) -> List[str]:
        import fnmatch

        physical_path = self._get_physical_path(path)
        matches = []
        for root, dirs, files in os.walk(physical_path):
            for filename in fnmatch.filter(files, glob):
                matches.append(os.path.join(root, filename))
        return matches

    async def find_content(self, path: str, reg_ex: str) -> FileInfo:
        import re

        physical_path = self._get_physical_path(path)
        if not os.path.exists(physical_path):
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(physical_path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        matches = re.findall(reg_ex, content)
        return FileInfo(
            path=path,
            content="\n".join(str(m) for m in matches),
            name=os.path.basename(path),
        )

    async def str_replace(
        self,
        path: str,
        old_str: str,
        new_str: str,
        user: Optional[Username] = None,
    ) -> FileInfo:
        physical_path = self._get_physical_path(path)
        if not os.path.exists(physical_path):
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(physical_path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        new_content = content.replace(old_str, new_str)

        async with aiofiles.open(physical_path, mode="w", encoding="utf-8") as f:
            await f.write(new_content)

        return FileInfo(
            path=path,
            name=os.path.basename(path),
            last_modify=datetime.now(),
        )

    async def upload_to_oss(
        self,
        file_path: str,
    ) -> OSSFile:
        physical_path = self._get_physical_path(file_path)
        if not os.path.exists(physical_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)

        if self._file_storage_client:
            try:
                import asyncio
                from gyra.core.interface.file import FileStorageURI

                bucket = self._oss_bucket
                oss_path = self.build_oss_path(
                    f"local_sandbox/{self._sandbox_id}/{file_name}"
                )

                with open(physical_path, "rb") as f:
                    uri = await asyncio.to_thread(
                        self._file_storage_client.save_file,
                        bucket,
                        file_name,
                        f,
                        storage_type=self._file_storage_client.default_storage_type,
                        file_id=oss_path,
                        public_url=True,
                    )

                if uri.startswith(("http://", "https://")):
                    preview_url = uri
                else:
                    preview_url = await asyncio.to_thread(
                        self._file_storage_client.get_public_url,
                        uri,
                        expire=3600,
                    )

                fixed_bucket = None
                try:
                    storage_system = self._file_storage_client.storage_system
                    storage_backends = getattr(storage_system, "storage_backends", {})
                    backend = storage_backends.get(
                        self._file_storage_client.default_storage_type
                    )
                    if backend:
                        fixed_bucket = getattr(backend, "fixed_bucket", None)
                except Exception:
                    pass

                if fixed_bucket:
                    full_object_name = f"{fixed_bucket}/{bucket}/{oss_path}"
                elif bucket:
                    full_object_name = f"{bucket}/{oss_path}"
                else:
                    full_object_name = oss_path

                return OSSFile(
                    object_name=full_object_name,
                    object_url=preview_url,
                    temp_url=preview_url,
                    status="completed",
                )
            except Exception as e:
                logger.error(
                    f"Failed to upload via FileStorageClient: {e}. "
                    f"File: {file_path}. Falling back to legacy OSS or local:// URL."
                )

        if self.oss and self.oss.bucket_name:
            try:
                oss_path = self.build_oss_path(
                    f"local_sandbox/{self._sandbox_id}/{file_name}"
                )
                self.oss.upload_file(physical_path, oss_path)
                temp_url = self.oss.generate_presigned_url(oss_path, download=True)
                return OSSFile(
                    object_name=oss_path,
                    object_url=temp_url,
                    temp_url=temp_url,
                    status="completed",
                )
            except Exception as e:
                logger.warning(f"Failed to upload to OSS: {e}")

        logger.error(
            f"All storage backends failed for file: {file_path}. "
            f"Returning local:// URL as last resort. "
            f"This URL is not accessible from frontend. "
            f"Please check FileStorageClient and storage configuration."
        )
        return OSSFile(
            object_name=file_name,
            object_url=f"local://{file_path}",
            temp_url=f"local://{file_path}",
            status="local_only",
        )

    async def download_to_local(
        self,
        url: str,
        filename: str,
        path: str,
        user: Optional[Username] = None,
    ) -> bool:
        import aiohttp

        physical_path = self._get_physical_path(path)
        os.makedirs(physical_path, exist_ok=True)
        target_file = os.path.join(physical_path, filename)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(target_file, mode="wb") as f:
                            await f.write(await response.read())
                        return True
                    else:
                        logger.error(f"Failed to download: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False

    async def start_upload_to_oss(self, file_path: str) -> str:
        result = await self.upload_to_oss(file_path)
        return str(uuid.uuid4())

    async def start_download_to_local(
        self,
        url: str,
        filename: str,
        path: str,
        user: Optional[Username] = None,
    ) -> str:
        return str(uuid.uuid4())

    async def get_task_result(self, task_id: str) -> TaskResult:
        return TaskResult(
            start=0,
            end=100,
            status="completed",
            detail={"message": "Local sandbox tasks complete immediately"},
        )

    async def cancel_tasks(self, task_ids: List[str]) -> bool:
        return True
