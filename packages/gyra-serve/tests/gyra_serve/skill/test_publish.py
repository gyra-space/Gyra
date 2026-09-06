"""skill_publish 核心发布逻辑(publish_skill_from_dir)的单元测试。

覆盖:
  - 正常发布:SKILL.md 解析、skill_code 归一化、SkillRequest 字段、拷贝调用;
  - 同名 skill -> 原地 update(action="updated");
  - 目录不存在 / 无 SKILL.md / 服务未启动 的 fail 路径;
  - workspace_id -> skill_published 事件广播(event_bus)。
不落真实 DB:用 FakeSkillService 替身捕获 create/update 与拷贝调用。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from types import SimpleNamespace

import pytest

from gyra_serve.skill.publish import publish_skill_from_dir


SKILL_MD = """---
name: My Cool Skill
description: 测试技能
type: python
version: 1.0.0
---

# My Cool Skill
正文
"""


@dataclass
class FakeConfig:
    project_skill_dir: str = "/tmp/fake-project-skill"
    sandbox_skill_dir: Optional[str] = None

    def get_project_skill_dir(self) -> str:
        return self.project_skill_dir

    def get_sandbox_skill_dir(self):
        return self.sandbox_skill_dir


@dataclass
class FakeSkillService:
    """捕获 publish 调用面的 SkillService 替身。"""

    existing: Dict[str, Any] = field(default_factory=dict)
    config: FakeConfig = field(default_factory=FakeConfig)

    def __post_init__(self):
        self.created: List[Any] = []
        self.copied_to_project: List[tuple] = []
        self.copied_to_sandbox: List[tuple] = []

    # publish 内部调用的私有方法 —— 替身直接提供(递归语义对齐真实实现)
    def _find_skill_directory(self, base_dir: str):
        import os

        if os.path.exists(os.path.join(base_dir, "SKILL.md")):
            return base_dir
        for entry in os.scandir(base_dir):
            if entry.is_dir():
                found = self._find_skill_directory(entry.path)
                if found:
                    return found
        return None

    def _parse_skill_md(self, file_path: str) -> Dict[str, str]:
        # 与真实实现同构:返回 frontmatter 的扁平 dict
        import re

        text = open(file_path, encoding="utf-8").read()
        m = re.search(r"^---\s*\n(.*?)\n---\s*$", text, re.DOTALL | re.MULTILINE)
        if not m:
            return {}
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        return meta

    def _copy_skill_to_project(self, skill_path, skill_name, project_dir, skill_code):
        self.copied_to_project.append((skill_path, skill_name, project_dir, skill_code))

    def _copy_skill_to_sandbox(self, skill_path, skill_name, sandbox_dir, skill_code):
        self.copied_to_sandbox.append((skill_path, skill_name, sandbox_dir, skill_code))

    @property
    def dao(self):
        return self

    def get_one(self, query: Dict[str, Any]):
        return self.existing.get(query.get("skill_code"))

    def create(self, request):
        self.created.append(request)
        return request


class FakeSystemApp:
    def __init__(self, service: Any):
        self._service = service

    def get_component(self, name, typ, default=None):
        return self._service


def _make_skill_dir(tmp_path) -> str:
    d = tmp_path / "my-cool-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    return str(d)


def test_publish_creates_skill(tmp_path):
    svc = FakeSkillService()
    skill_dir = _make_skill_dir(tmp_path)

    result = publish_skill_from_dir(
        skill_dir, operator="alice", system_app=FakeSystemApp(svc)
    )

    assert result["success"] is True
    assert result["skill_code"] == "my-cool-skill"
    assert result["name"] == "My Cool Skill"
    assert result["action"] == "created"
    assert len(svc.created) == 1
    req = svc.created[0]
    assert req.skill_code == "my-cool-skill"
    assert req.description == "测试技能"
    assert req.path == "my-cool-skill"
    assert "My Cool Skill" in req.content
    # 拷贝到 project 目录(默认无 sandbox 目录)
    assert svc.copied_to_project[0][3] == "my-cool-skill"
    assert svc.copied_to_sandbox == []


def test_publish_existing_skill_updates_in_place(tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    svc = FakeSkillService(existing={"my-cool-skill": {"skill_code": "my-cool-skill"}})

    result = publish_skill_from_dir(skill_dir, system_app=FakeSystemApp(svc))

    assert result["success"] is True
    assert result["action"] == "updated"
    assert len(svc.created) == 1  # create 内部转 update


def test_publish_parent_dir_finds_skill(tmp_path):
    parent = tmp_path / "workspace"
    parent.mkdir()
    (parent / "my-cool-skill").mkdir()
    (parent / "my-cool-skill" / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    svc = FakeSkillService()

    result = publish_skill_from_dir(str(parent), system_app=FakeSystemApp(svc))

    assert result["success"] is True
    assert result["skill_code"] == "my-cool-skill"


def test_publish_dir_not_found(tmp_path):
    result = publish_skill_from_dir(
        str(tmp_path / "nope"), system_app=FakeSystemApp(FakeSkillService())
    )
    assert result["success"] is False
    assert result["code"] == "DIR_NOT_FOUND"


def test_publish_no_skill_md(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    result = publish_skill_from_dir(str(d), system_app=FakeSystemApp(FakeSkillService()))
    assert result["success"] is False
    assert result["code"] == "SKILL_MD_NOT_FOUND"


def test_publish_service_unavailable():
    result = publish_skill_from_dir(
        "/tmp", system_app=FakeSystemApp(None)
    )
    assert result["success"] is False
    assert result["code"] == "SERVICE_UNAVAILABLE"


def test_publish_warns_when_root_has_archives(tmp_path):
    d = _make_skill_dir(tmp_path)
    (tmp_path / "my-cool-skill" / "medical-quality-audit.zip").write_bytes(b"PK")
    svc = FakeSkillService()

    result = publish_skill_from_dir(str(d), system_app=FakeSystemApp(svc))

    assert result["success"] is True
    assert result["warnings"]
    assert "medical-quality-audit.zip" in result["warnings"][0]
    assert "独立子目录" in result["message"]


def test_publish_clean_dir_has_no_warnings(tmp_path):
    result = publish_skill_from_dir(
        _make_skill_dir(tmp_path), system_app=FakeSystemApp(FakeSkillService())
    )
    assert result["success"] is True
    assert "warnings" not in result


def test_publish_emits_workspace_event(tmp_path):
    from gyra_serve.workspace.event_bus import register_workspace_queue

    svc = FakeSkillService()
    skill_dir = _make_skill_dir(tmp_path)

    queue: asyncio.Queue = asyncio.Queue()
    register_workspace_queue(42, queue)
    try:
        result = publish_skill_from_dir(
            skill_dir, workspace_id=42, system_app=FakeSystemApp(svc)
        )
    finally:
        # unregister 不在 assert 前,避免污染其他用例
        from gyra_serve.workspace.event_bus import unregister_workspace_queue

        unregister_workspace_queue(42, queue)

    assert result["success"] is True
    event_type, payload = queue.get_nowait()
    assert event_type == "skill_published"
    assert payload["skill_code"] == "my-cool-skill"
    assert payload["workspace_id"] == 42
