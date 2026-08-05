"""LocalFileClient path containment security tests."""

import os
import pytest

from gyra_ext.sandbox.local.file_client import LocalFileClient


class MockRuntime:
    def __init__(self, base_dir):
        self.base_dir = base_dir


def _make_client(tmp_path, work_dir="/data/workspace", skill_dir=None, host_work_dir=None):
    session_dir = tmp_path / "sessions" / "s1"
    session_dir.mkdir(parents=True)
    runtime = MockRuntime(str(tmp_path / "sessions"))
    return LocalFileClient(
        sandbox_id="s1",
        work_dir=work_dir,
        runtime=runtime,
        skill_dir=skill_dir,
        host_work_dir=host_work_dir,
    )


@pytest.mark.asyncio
async def test_absolute_traversal_blocked(tmp_path):
    client = _make_client(tmp_path)
    with pytest.raises(PermissionError):
        await client.read("/../../../etc/passwd")


@pytest.mark.asyncio
async def test_relative_traversal_blocked(tmp_path):
    client = _make_client(tmp_path)
    with pytest.raises(PermissionError):
        await client.read("../../../etc/passwd")


@pytest.mark.asyncio
async def test_write_outside_blocked(tmp_path):
    client = _make_client(tmp_path)
    with pytest.raises(PermissionError):
        await client.write("/etc/evil.txt", "payload", overwrite=True)


@pytest.mark.asyncio
async def test_remove_outside_blocked(tmp_path):
    client = _make_client(tmp_path)
    with pytest.raises(PermissionError):
        await client.remove("/etc/passwd")


@pytest.mark.asyncio
async def test_workspace_path_maps_correctly_nested(tmp_path):
    client = _make_client(tmp_path, work_dir="/data/workspace")
    await client.write("/data/workspace/file.txt", "hello", overwrite=True)

    physical = client._get_physical_path("/data/workspace/file.txt")
    expected = os.path.abspath(
        os.path.join(client._session_root, "data/workspace/file.txt")
    )
    assert physical == expected
    assert physical.startswith(client._session_root)

    result = await client.read("/data/workspace/file.txt")
    assert result.content == "hello"


@pytest.mark.asyncio
async def test_workspace_path_maps_correctly_host(tmp_path):
    host_dir = tmp_path / "workspaces" / "42"
    host_dir.mkdir(parents=True)
    client = _make_client(
        tmp_path, work_dir="/data/workspace", host_work_dir=str(host_dir)
    )

    physical = client._get_physical_path("/data/workspace/file.txt")
    assert physical == os.path.abspath(str(host_dir / "file.txt"))

    await client.write("/data/workspace/file.txt", "hello", overwrite=True)
    result = await client.read("/data/workspace/file.txt")
    assert result.content == "hello"


@pytest.mark.asyncio
async def test_relative_path_resolves_to_work_dir(tmp_path):
    client = _make_client(tmp_path, work_dir="/data/workspace")
    await client.write("file.txt", "hello", overwrite=True)

    physical = client._get_physical_path("file.txt")
    assert physical == os.path.abspath(
        os.path.join(client._session_root, "data/workspace/file.txt")
    )

    result = await client.read("file.txt")
    assert result.content == "hello"


@pytest.mark.asyncio
async def test_mnt_whitelist_allowed(tmp_path):
    client = _make_client(tmp_path)
    # /mnt is in the host whitelist and should be returned as-is by _get_physical_path.
    physical = client._get_physical_path("/mnt")
    assert physical == "/mnt"
    physical = client._get_physical_path("/mnt/data/file.txt")
    assert physical == "/mnt/data/file.txt"


@pytest.mark.asyncio
async def test_skill_dir_whitelist_allowed(tmp_path):
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    client = _make_client(tmp_path, skill_dir=str(skill_dir))

    physical = client._get_physical_path(str(skill_dir / "skill.py"))
    assert physical == os.path.realpath(str(skill_dir / "skill.py"))


@pytest.mark.asyncio
async def test_symlink_escape_blocked(tmp_path):
    client = _make_client(tmp_path)
    session_root = client._session_root
    os.makedirs(session_root, exist_ok=True)

    secret = tmp_path / "secret.txt"
    secret.write_text("topsecret")
    link_path = os.path.join(session_root, "link_to_secret")
    os.symlink(str(secret), link_path)

    # The logical path points inside the session root, but the symlink target escapes.
    with pytest.raises(PermissionError):
        await client.read("/link_to_secret")


@pytest.mark.asyncio
async def test_logical_path_allowed_when_basedir_behind_symlink(tmp_path):
    """Regression: macOS /var -> /private/var.

    When the sandbox base_dir lives behind a symlink, the stored allowed roots
    keep the symlinked prefix (abspath) while the candidate path is resolved
    (realpath). Writing via the LOGICAL work_dir path must succeed instead of
    being falsely rejected as 'escapes sandbox allowed roots'.
    """
    real_root = tmp_path / "real"
    real_root.mkdir()
    link_root = tmp_path / "link"
    link_root.symlink_to(real_root, target_is_directory=True)

    sessions = link_root / "sessions"
    sessions.mkdir()
    (sessions / "s1").mkdir()
    runtime = MockRuntime(str(sessions))

    client = LocalFileClient(
        sandbox_id="s1",
        work_dir="/data/workspace",
        runtime=runtime,
    )
    assert os.path.realpath(client._session_root) != client._session_root

    await client.write("/data/workspace/file.txt", "hello", overwrite=True)
    result = await client.read("/data/workspace/file.txt")
    assert result.content == "hello"
