"""Pytest entry for LocalVaultFS conformance (RFC 002 §6).

Runs the full conformance suite against LocalVaultFS in a tmp dir.
This is the baseline every other backend (DistributedVaultFS, future
third-party) must also pass.
"""

from __future__ import annotations

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
