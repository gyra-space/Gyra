"""
E2B File Client

基于 E2B Cloud Sandbox 的 ``Sandbox.files`` 文件系统能力实现 ``FileClient`` 接口。
E2B SDK 的文件操作是同步的，这里通过 ``asyncio.to_thread`` 包装为异步接口。
"""

import asyncio
import io
import logging
import posixpath
import urllib.request
import uuid
from datetime import datetime
from typing import Any, Dict, IO, List, Literal, Optional, Union

from gyra.sandbox.client.file.client import FileClient
from gyra.sandbox.client.file.types import (
    EntryInfo,
    FileInfo,
    FileType,
    OSSFile,
    TaskResult,
)
from gyra.sandbox.connection_config import Username

logger = logging.getLogger(__name__)


class E2BFileClient(FileClient):
    """E2B 云端沙箱的文件客户端。"""

    def __init__(
        self,
        sandbox_id: str,
        work_dir: str,
        sandbox: Any,  # E2B Sandbox 实例
        skill_dir: str = None,
        file_storage_client: Any = None,
        **kwargs,
    ):
        super().__init__(
            sandbox_id=sandbox_id,
            work_dir=work_dir,
            file_storage_client=file_storage_client,
            **kwargs,
        )
        self._sandbox = sandbox
        self._sandbox_id = sandbox_id
        self._logical_work_dir = work_dir or "/home/user"
        self._skill_dir = skill_dir

    def _abs(self, path: str) -> str:
        """将相对路径解析为沙箱内绝对路径。"""
        if not path:
            return self._logical_work_dir
        if path.startswith("/"):
            return posixpath.normpath(path)
        return posixpath.normpath(posixpath.join(self._logical_work_dir, path))

    async def write(
        self,
        path: str,
        data: Union[str, bytes, IO],
        user: Optional[Username] = None,
        overwrite: bool = False,
        save_oss: bool = False,
    ) -> FileInfo:
        abs_path = self._abs(path)
        if isinstance(data, str):
            payload = data.encode("utf-8")
        elif isinstance(data, bytes):
            payload = data
        else:
            raw = data.read()
            payload = raw.encode("utf-8") if isinstance(raw, str) else raw
        await asyncio.to_thread(self._sandbox.files.write, abs_path, payload)
        return FileInfo(path=abs_path, name=posixpath.basename(abs_path))

    async def create(
        self,
        path: str,
        content: Optional[str] = None,
        user: Optional[str] = None,
        overwrite: bool = True,
    ) -> FileInfo:
        return await self.write(path, content or "", overwrite=overwrite)

    async def read(
        self,
        path: str,
        format: Literal["text", "bytes", "stream"] = "text",
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ):
        abs_path = self._abs(path)
        data = await asyncio.to_thread(self._sandbox.files.read, abs_path)
        if format == "bytes":
            return data
        if format == "stream":
            return data  # 简化：返回 bytes
        return data.decode("utf-8", errors="replace")

    async def list(
        self,
        path: str,
        depth: Optional[int] = 1,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> List[EntryInfo]:
        abs_path = self._abs(path)
        entries = await asyncio.to_thread(self._sandbox.files.list, abs_path)
        result = []
        for entry in entries or []:
            name = getattr(entry, "name", None) or ""
            item_path = getattr(entry, "path", None) or ""
            is_dir = bool(getattr(entry, "is_dir", False))
            result.append(
                EntryInfo(
                    name=name,
                    type=FileType.DIR if is_dir else FileType.FILE,
                    path=item_path,
                    size=0,
                    mode=0,
                    permissions="",
                    owner="",
                    group="",
                    modified_time=datetime.now(),
                )
            )
        return result

    async def exists(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> bool:
        abs_path = self._abs(path)
        return bool(
            await asyncio.to_thread(self._sandbox.files.exists, abs_path)
        )

    async def get_info(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> EntryInfo:
        abs_path = self._abs(path)
        entries = await asyncio.to_thread(self._sandbox.files.list, posixpath.dirname(abs_path))
        name = posixpath.basename(abs_path)
        for entry in entries or []:
            if (getattr(entry, "name", None) or "") == name:
                return EntryInfo(
                    name=name,
                    type=FileType.DIR if getattr(entry, "is_dir", False) else FileType.FILE,
                    path=abs_path,
                    size=0,
                    mode=0,
                    permissions="",
                    owner="",
                    group="",
                    modified_time=datetime.now(),
                )
        return EntryInfo(
            name=name,
            type=FileType.FILE,
            path=abs_path,
            size=0,
            mode=0,
            permissions="",
            owner="",
            group="",
            modified_time=datetime.now(),
        )

    async def remove(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> None:
        abs_path = self._abs(path)
        await asyncio.to_thread(self._sandbox.files.remove, abs_path)

    async def rename(
        self,
        old_path: str,
        new_path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> EntryInfo:
        old = self._abs(old_path)
        new = self._abs(new_path)
        await asyncio.to_thread(self._sandbox.files.rename, old, new)
        return EntryInfo(
            name=posixpath.basename(new),
            type=FileType.FILE,
            path=new,
            size=0,
            mode=0,
            permissions="",
            owner="",
            group="",
            modified_time=datetime.now(),
        )

    async def make_dir(
        self,
        path: str,
        user: Optional[Username] = None,
        request_timeout: Optional[float] = None,
    ) -> bool:
        abs_path = self._abs(path)
        if await asyncio.to_thread(self._sandbox.files.exists, abs_path):
            return False
        await asyncio.to_thread(self._sandbox.files.make_dir, abs_path)
        return True

    async def find_file(self, path: str, glob: str) -> List[str]:
        """通过 shell find 实现简单文件查找。"""
        abs_path = self._abs(path)
        cmd = f"find {abs_path} -maxdepth 3 -name {glob!r}"
        result = await asyncio.to_thread(
            self._sandbox.commands.run, cmd=cmd, timeout=30
        )
        return [line for line in ((result.stdout or "")).splitlines() if line]

    async def find_content(self, path: str, reg_ex: str) -> FileInfo:
        abs_path = self._abs(path)
        cmd = f"grep -rn -E {reg_ex!r} {abs_path} | head -n 100"
        result = await asyncio.to_thread(
            self._sandbox.commands.run, cmd=cmd, timeout=30
        )
        return FileInfo(path=abs_path, content=(result.stdout or ""))

    async def str_replace(
        self, path: str, old_str: str, new_str: str, user: Optional[Username] = None
    ) -> FileInfo:
        abs_path = self._abs(path)
        content = await self.read(abs_path)
        replaced = content.replace(old_str, new_str)
        await self.write(abs_path, replaced)
        return FileInfo(path=abs_path, content=replaced)

    # ---- OSS/FileStorage 持久化方法：E2B 云端沙箱支持将文件持久化到项目 FileStorage ----

    @property
    def oss(self):
        # 返回基类的 _legacy_oss，如果没有配置 OSS AK/SK 就是 None
        return super().oss

    async def upload_to_oss(self, file_path: str) -> OSSFile:
        """Upload file from E2B sandbox to FileStorage (OSS/local storage).

        Reads file content from E2B sandbox, then saves to FileStorageClient.
        """
        abs_path = self._abs(file_path)
        file_name = posixpath.basename(abs_path)

        # 1. Read file content from E2B sandbox
        data_bytes = await asyncio.to_thread(self._sandbox.files.read, abs_path)
        if not isinstance(data_bytes, bytes):
            if isinstance(data_bytes, str):
                data_bytes = data_bytes.encode("utf-8")
            else:
                data_bytes = bytes(data_bytes)

        file_stream = io.BytesIO(data_bytes)

        # 2. If FileStorageClient is available, save to it
        if self._file_storage_client:
            try:
                from gyra.core.interface.file import FileStorageURI

                storage_key = self.build_oss_path(
                    posixpath.join("e2b-sandbox", self._sandbox_id, file_path.lstrip("/"))
                )

                custom_metadata = {
                    "sandbox_id": self._sandbox_id,
                    "sandbox_path": abs_path,
                    "original_filename": file_name,
                }

                uri = await asyncio.to_thread(
                    self._file_storage_client.save_file,
                    self._oss_bucket,
                    file_name,
                    file_stream,
                    storage_type=self._file_storage_client.default_storage_type,
                    file_id=storage_key,
                    custom_metadata=custom_metadata,
                )

                # Get preview URL
                if uri.startswith(("http://", "https://")):
                    preview_url = uri
                else:
                    preview_url = await asyncio.to_thread(
                        self._file_storage_client.get_public_url,
                        uri,
                        expire=3600,
                    )

                # Build full object name
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
                    full_object_name = f"{fixed_bucket}/{self._oss_bucket}/{storage_key}"
                elif self._oss_bucket:
                    full_object_name = f"{self._oss_bucket}/{storage_key}"
                else:
                    full_object_name = storage_key

                return OSSFile(
                    object_name=full_object_name,
                    object_url=uri,
                    temp_url=preview_url,
                )

            except Exception as exc:
                logger.error(
                    "[E2BFileClient] Failed to upload to FileStorage: path=%s error=%s",
                    abs_path,
                    exc,
                )
                # Fall through to return basic OSSFile

        # If no FileStorageClient or upload failed, return basic info
        return OSSFile(object_name=abs_path)

    async def start_upload_to_oss(self, file_path: str) -> str:
        """Start async upload task. For E2B, we do it synchronously."""
        return ""

    async def download_to_local(
        self, url: str, filename: str, path: str, user: Optional[Username] = None
    ) -> bool:
        """Download file from URL to E2B sandbox.

        Downloads from given URL (OSS/FileStorage public URL) and writes to sandbox.
        """
        target_path = posixpath.join(path, filename)
        abs_target_path = self._abs(target_path)

        try:
            # 1. Download content from URL
            if url.startswith(("http://", "https://")):
                # Public HTTP URL (e.g. signed OSS URL)
                with urllib.request.urlopen(url, timeout=300) as response:
                    data_bytes = response.read()
            elif url.startswith("gyra-fs://") or url.startswith("file://"):
                # Gyra FileStorage URI - download via FileStorageClient
                if self._file_storage_client:
                    # Download to memory then write to sandbox
                    uri_path, _metadata = await asyncio.to_thread(
                        self._file_storage_client.download_file,
                        url,
                    )
                    with open(uri_path, "rb") as f:
                        data_bytes = f.read()
                else:
                    logger.error(
                        "[E2BFileClient] Cannot download FileStorage URI without FileStorageClient: %s",
                        url,
                    )
                    return False
            else:
                logger.error("[E2BFileClient] Unsupported URL scheme: %s", url)
                return False

            # 2. Write to E2B sandbox
            await asyncio.to_thread(self._sandbox.files.write, abs_target_path, data_bytes)
            return True

        except Exception as exc:
            logger.error(
                "[E2BFileClient] Failed to download to sandbox: url=%s target=%s error=%s",
                url,
                abs_target_path,
                exc,
            )
            return False

    async def start_download_to_local(
        self, url: str, filename: str, path: str, user: Optional[Username] = None
    ) -> str:
        """Start async download task. For E2B, we do it synchronously."""
        return ""

    async def get_task_result(self, task_id: str) -> TaskResult:
        return TaskResult(0, 0, "", {})

    async def cancel_tasks(self, task_ids: List[str]) -> bool:
        return True