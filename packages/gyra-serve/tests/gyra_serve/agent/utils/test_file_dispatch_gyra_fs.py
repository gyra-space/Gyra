"""Tests for dispatch_file_to_sandbox with gyra-fs:// URIs."""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if "gyra_app.config" not in sys.modules:
    sys.modules["gyra_app"] = MagicMock()
    sys.modules["gyra_app.config"] = MagicMock()

from gyra_serve.agent.utils.file_dispatch import dispatch_file_to_sandbox


@pytest.mark.asyncio
async def test_dispatch_gyra_fs_without_public_url_returns_none():
    """gyra-fs:// URI 无法生成公开 URL 时，应优雅跳过(返回 None)，不崩溃。"""
    fake_file_storage_client = MagicMock()
    fake_file_storage_client.get_public_url = MagicMock(return_value=None)

    sandbox_client = MagicMock()
    sandbox_client.work_dir = "/tmp/sandbox"
    sandbox_client.file = MagicMock()
    sandbox_client.file.create = AsyncMock(return_value=None)

    result = await dispatch_file_to_sandbox(
        file_path="gyra-fs://local/gyra_app_file/abc-123",
        file_name="doc.md",
        sandbox_client=sandbox_client,
        file_storage_client=fake_file_storage_client,
    )

    assert result is None
    fake_file_storage_client.get_public_url.assert_called_once_with(
        "gyra-fs://local/gyra_app_file/abc-123"
    )
    sandbox_client.file.create.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_gyra_fs_uses_public_url_when_available():
    """gyra-fs:// URI 能生成公开 HTTP URL 时，应通过 httpx 下载。"""
    fake_response = MagicMock()
    fake_response.content = b"# Public content"

    fake_file_storage_client = MagicMock()
    fake_file_storage_client.get_public_url = MagicMock(
        return_value="http://example.com/public.md"
    )

    sandbox_client = MagicMock()
    sandbox_client.work_dir = "/tmp/sandbox"
    sandbox_client.file = MagicMock()
    sandbox_client.file.create = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient") as mock_client:
        fake_client = MagicMock()
        fake_client.get = AsyncMock(return_value=fake_response)
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = fake_client

        result = await dispatch_file_to_sandbox(
            file_path="gyra-fs://local/gyra_app_file/abc-123",
            file_name="public.md",
            sandbox_client=sandbox_client,
            file_storage_client=fake_file_storage_client,
        )

    assert result == "/tmp/sandbox/uploads/public.md"
    sandbox_client.file.create.assert_called_once_with(
        "/tmp/sandbox/uploads/public.md", "# Public content", overwrite=True
    )
