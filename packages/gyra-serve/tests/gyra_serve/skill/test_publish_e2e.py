"""skill_publish 集成测试:真实 Service/DAO/sqlite,端到端验证发布链路。

覆盖:
  - 首次发布 -> server_app_skill 落库 + project_skill_dir 落盘;
  - 重复发布同名技能 -> 原地 update(不新建行),内容与文件同步更新;
  - sandbox_skill_dir 配置时同步拷贝到沙箱目录。
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from gyra.storage.metadata import db
from gyra_serve.skill.publish import publish_skill_from_dir


SKILL_MD_V1 = """---
name: e2e-publish-demo
description: v1 描述
type: python
---

# e2e-publish-demo
v1 body
"""

SKILL_MD_V2 = """---
name: e2e-publish-demo
description: v2 描述(更新)
type: python
---

# e2e-publish-demo
v2 body
"""


@pytest.fixture
def env(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 'skill_e2e.db'}")
    db.create_all()

    from gyra_serve.skill.config import ServeConfig
    from gyra_serve.skill.models.models import SkillDao
    from gyra_serve.skill.service.service import Service

    project_dir = tmp_path / "skills"
    sandbox_dir = tmp_path / "sandbox_skills"
    sandbox_dir.mkdir()  # _copy_skill_to_sandbox 要求目标目录已存在(生产由沙箱 provisioning 创建)
    config = ServeConfig(
        project_skill_dir=str(project_dir),
        sandbox_skill_dir=str(sandbox_dir),
    )
    svc = Service(SimpleNamespace(), config)
    svc._dao = SkillDao(config)
    svc._system_app = SimpleNamespace()

    system_app = SimpleNamespace()
    system_app.get_component = lambda name, typ, default=None: svc
    return SimpleNamespace(
        service=svc,
        system_app=system_app,
        project_dir=project_dir,
        sandbox_dir=sandbox_dir,
    )


def _make_skill_dir(tmp_path, name: str, text: str) -> str:
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    return str(d)


def test_publish_end_to_end_create_then_update(tmp_path, env):
    # 首次发布
    src1 = _make_skill_dir(tmp_path, "demo-v1", SKILL_MD_V1)
    r1 = publish_skill_from_dir(src1, operator="tester", system_app=env.system_app)

    assert r1["success"] is True
    assert r1["action"] == "created"
    assert r1["skill_code"] == "e2e-publish-demo"

    # DB 落库
    row = env.service.dao.get_one({"skill_code": "e2e-publish-demo"})
    assert row is not None
    assert row.name == "e2e-publish-demo"
    assert row.description == "v1 描述"
    assert "v1 body" in row.content

    # project 目录落盘 + sandbox 目录同步
    assert (env.project_dir / "e2e-publish-demo" / "SKILL.md").exists()
    assert (env.sandbox_dir / "e2e-publish-demo" / "SKILL.md").exists()

    # 修改后重发同名技能 -> 原地 update
    src2 = _make_skill_dir(tmp_path, "demo-v2", SKILL_MD_V2)
    r2 = publish_skill_from_dir(src2, operator="tester", system_app=env.system_app)

    assert r2["success"] is True
    assert r2["action"] == "updated"

    row2 = env.service.dao.get_one({"skill_code": "e2e-publish-demo"})
    assert row2.description == "v2 描述(更新)"
    assert "v2 body" in row2.content
    # 拷贝覆盖后,project 目录内容也更新
    published = (
        env.project_dir / "e2e-publish-demo" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "v2 body" in published
