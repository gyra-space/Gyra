"""Tests for the built-in skill startup sync (skill/ -> skill module)."""

import asyncio
import io
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest
from unittest.mock import MagicMock

from gyra_serve.skill.api.schemas import SkillResponse
from gyra_serve.skill.config import ServeConfig
from gyra_serve.skill.service.service import Service

SKILL_MD = """---
name: {name}
description: {name} built-in skill
type: python
version: 1.0.0
---

# {name}
"""


def _response(skill_code: str) -> SkillResponse:
    now = "2026-01-01T00:00:00"
    return SkillResponse(
        skill_code=skill_code,
        name=skill_code,
        description="d",
        type="python",
        gmt_created=now,
        gmt_modified=now,
    )


@pytest.fixture
def tmp_dir():
    """Own temp dir: pytest's tmp_path hits an EEXIST mkdir in this sandbox."""
    path = Path(tempfile.mkdtemp(prefix="skill-builtin-test-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def service(tmp_dir):
    config = ServeConfig(
        project_skill_dir=str(tmp_dir / "project"),
        builtin_skill_dir=str(tmp_dir / "builtin"),
    )
    return Service(MagicMock(), config, dao=MagicMock())


def _write_skill_dir(root, name, extra_files=()):
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD.format(name=name), encoding="utf-8")
    for rel in extra_files:
        target = skill_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("content of " + rel, encoding="utf-8")
    return skill_dir


def _write_zip(root, name, arc_layout="nested"):
    """Write a zip whose SKILL.md declares `name` as the skill name."""
    payload = SKILL_MD.format(name=name).encode("utf-8")
    path = root / f"{name}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        prefix = f"{name}/" if arc_layout == "nested" else ""
        archive.writestr(f"{prefix}SKILL.md", payload)
    return path


def _names(payload: bytes):
    return zipfile.ZipFile(io.BytesIO(payload)).namelist()


def test_zip_only_is_packaged(service, tmp_dir):
    """A bare .zip is the normal built-in packaging and must be picked up."""
    builtin = tmp_dir / "builtin"
    builtin.mkdir()
    _write_zip(builtin, "alpha")

    archives = service._package_builtin_skills(str(builtin))

    assert [name for name, _ in archives] == ["alpha.zip"]
    assert "alpha/SKILL.md" in _names(archives[0][1])


def test_directory_wins_over_stale_sibling_zip(service, tmp_dir):
    """The git-tracked directory is fresher, so it must beat a sibling zip."""
    builtin = tmp_dir / "builtin"
    builtin.mkdir()
    _write_skill_dir(builtin, "alpha", extra_files=("docs/detail.md",))

    # Stale sibling zip. Deliberately not a valid archive so that reading it
    # would blow up instead of silently producing a wrong skill.
    (builtin / "alpha.zip").write_bytes(b"stale, not even a zip")

    archives = service._package_builtin_skills(str(builtin))

    assert [name for name, _ in archives] == ["alpha.zip"]
    payload = archives[0][1]
    # Built from the directory, proven by a file the stale zip never had.
    assert "alpha/docs/detail.md" in _names(payload)
    assert zipfile.ZipFile(io.BytesIO(payload)).testzip() is None


def test_directory_without_skill_md_is_skipped(service, tmp_dir):
    builtin = tmp_dir / "builtin"
    builtin.mkdir()
    (builtin / "beta").mkdir()
    (builtin / "beta" / "README.md").write_text("not a skill", encoding="utf-8")

    assert service._package_builtin_skills(str(builtin)) == []


def test_archive_layout_and_noise_exclusion(service, tmp_dir):
    """Single top-level folder (required by _find_skill_directory) and no junk."""
    builtin = tmp_dir / "builtin"
    builtin.mkdir()
    skill_dir = _write_skill_dir(builtin, "alpha", extra_files=("docs/detail.md",))
    (skill_dir / ".DS_Store").write_text("noise", encoding="utf-8")
    (skill_dir / "__pycache__").mkdir()
    (skill_dir / "__pycache__" / "x.pyc").write_text("noise", encoding="utf-8")

    payload = service._package_builtin_skills(str(builtin))[0][1]
    names = _names(payload)

    assert {n.split("/")[0] for n in names} == {"alpha"}
    assert "alpha/SKILL.md" in names
    assert not any(".DS_Store" in n or "__pycache__" in n for n in names)


def test_missing_dir_returns_empty(service, tmp_dir):
    assert asyncio.run(service.sync_from_builtin_dir(str(tmp_dir / "nope"))) == []


def test_sync_delegates_to_upload_from_zip(service, tmp_dir):
    """All recognition lives in upload_from_zip; sync only packages and hands off."""
    builtin = tmp_dir / "builtin"
    builtin.mkdir()
    _write_zip(builtin, "alpha")

    seen = []

    async def fake_upload(file):
        seen.append(file.filename)
        return _response("alpha")

    service.upload_from_zip = fake_upload

    result = asyncio.run(service.sync_from_builtin_dir(str(builtin)))

    assert seen == ["alpha.zip"]
    assert [r.skill_code for r in result] == ["alpha"]


def test_sync_continues_when_one_skill_fails(service, tmp_dir):
    """A broken package must not abort the rest of the seeding."""
    service._package_builtin_skills = lambda _dir: [("a.zip", b"a"), ("b.zip", b"b")]

    async def fake_upload(file):
        if file.filename == "a.zip":
            raise ValueError("boom")
        return _response("b")

    service.upload_from_zip = fake_upload

    result = asyncio.run(service.sync_from_builtin_dir(str(tmp_dir)))

    assert [r.skill_code for r in result] == ["b"]
