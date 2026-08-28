"""Pytest entry for LocalVaultFS conformance (RFC 002 §6).

Runs the full conformance suite against LocalVaultFS in a tmp dir.
This is the baseline every other backend (DistributedVaultFS, future
third-party) must also pass.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import pytest_asyncio

from gyra_ext.knowledge.vaultfs import LocalVaultFS
from gyra_ext.knowledge.vaultfs.conformance import run_conformance


@pytest_asyncio.fixture
async def vault(tmp_path: Path):
    from gyra.knowledge.types import new_space_id

    root = tmp_path / "test_space"
    v = LocalVaultFS(space_id=new_space_id(), root=root)
    await v.initialize()
    yield v
    await v.close()


@pytest.mark.asyncio
async def test_local_vaultfs_conformance(vault):
    """LocalVaultFS must pass the full conformance suite."""
    await run_conformance(vault)


@pytest.mark.asyncio
async def test_local_vaultfs_backend_type(vault):
    assert vault.backend_type == "local"


@pytest.mark.asyncio
async def test_local_vaultfs_creates_directory_structure(vault):
    """initialize() must create raw/, wiki/, .ks/ dirs."""
    root = vault.root
    assert (root / "raw" / "sources").is_dir()
    assert (root / "raw" / "convos").is_dir()
    assert (root / "raw" / "clips").is_dir()
    assert (root / "wiki").is_dir()
    assert (root / ".ks").is_dir()
    assert (root / ".ks" / "index.db").is_file()


@pytest.mark.asyncio
async def test_local_vaultfs_seeds_agents_md(vault):
    """initialize() must seed AGENTS.md at the space root."""
    root = vault.root
    assert (root / "AGENTS.md").is_file()
    content = await vault.read_agents_md()
    assert "AGENTS" in content or "Agent" in content


@pytest.mark.asyncio
async def test_local_vaultfs_agents_md_roundtrip(vault):
    """read_agents_md / write_agents_md round-trip preserves content."""
    await vault.write_agents_md("# My Agent\n\n## Identity\n我是测试 Agent\n")
    assert await vault.read_agents_md() == "# My Agent\n\n## Identity\n我是测试 Agent\n"


@pytest.mark.asyncio
async def test_local_vaultfs_agents_md_is_protected(vault):
    """doc_delete must refuse to delete AGENTS.md (protected file)."""
    await vault.write_agents_md("# My Agent\n\n## Identity\n测试\n")
    with pytest.raises(PermissionError):
        await vault.doc_delete("AGENTS.md")


# ---------------------------------------------------------------------------
# Asset storage (embedded images from extractors)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_vaultfs_asset_roundtrip(vault):
    """asset_write returns a vault-relative ref; asset_read restores the bytes."""
    data = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 8
    ref = await vault.asset_write("team offsite.png", data)

    match = re.fullmatch(r"assets/([0-9a-f]{16})-(\S+)", ref)
    assert match is not None
    assert match.group(2) == "team_offsite.png"

    got = await vault.asset_read(ref)
    assert got == data


@pytest.mark.asyncio
async def test_local_vaultfs_asset_write_is_deduped(vault):
    """Same bytes twice → same content-addressed ref, file written once."""
    data = b"same-bytes" * 128
    ref1 = await vault.asset_write("a.png", data)
    ref2 = await vault.asset_write("a.png", data)
    assert ref1 == ref2
    files = list((vault.root / "assets").iterdir())
    assert len(files) == 1


@pytest.mark.asyncio
async def test_local_vaultfs_asset_read_missing_returns_empty(vault):
    assert await vault.asset_read("assets/deadbeef00112233-nope.png") == b""
    assert await vault.asset_read("") == b""


@pytest.mark.asyncio
async def test_local_vaultfs_asset_read_blocks_traversal(vault, tmp_path: Path):
    """Refs escaping the vault root must never resolve outside it."""
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"top secret")
    for evil in ("../secret.txt", "../../secret.txt", "assets/../../secret.txt"):
        assert await vault.asset_read(evil) == b""
