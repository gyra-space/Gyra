"""预加载技能 helper 的单元测试（V1：collect -> XML -> system 注入块）。

覆盖：
  - SKILL.md 全文读取、YAML frontmatter 剥离、**不截断**；
  - 剧本 declaration.skills（ext_info.playbook_id 直接命中 / task_id 反查）;
  - chat_in_params sub_type='skill(gyra)' 手动选择合并 + 按引用去重；
  - <loaded_skills> 注入块格式与说明文案。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from gyra_serve.agent.preload_skills import (
    build_preloaded_skills_reminder,
    collect_preloaded_skill_xmls,
    load_skill_markdown,
    render_preloaded_skill_xml,
)

_SKILL_SVC = "serve_skill_service"
_PLAYBOOK_SVC = "serve_playbook_service"
_TASK_SVC = "serve_task_service"


# --------------------------------------------------------------------------- #
# Mocks
# --------------------------------------------------------------------------- #


class FakeSystemApp:
    """按组件名分发 service 的 SystemApp mock。"""

    def __init__(self, services: Dict[str, Any]):
        self._services = services

    def get_component(self, name, typ, default=None):
        return self._services.get(name, default)


class FakeSkillService:
    def __init__(self, dir_map: Dict[str, str]):
        self._dir_map = dir_map

    def get_skill_directory(self, skill_code: str) -> str:
        return self._dir_map.get(skill_code, os.path.join("/nonexist", skill_code))


class FakePlaybookService:
    def __init__(self, playbooks: Dict[int, Any]):
        self._playbooks = playbooks

    def get_by_id(self, pid):
        return self._playbooks.get(pid)


class FakeTaskService:
    def __init__(self, tasks: Dict[int, Any]):
        self._tasks = tasks

    def get_by_id(self, tid):
        return self._tasks.get(tid)


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class ChatInParam:
    def __init__(self, sub_type: str, param_value: str):
        self.param_type = "resource"
        self.sub_type = sub_type
        self.param_value = param_value


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _write_skill(tmp_path, code: str, name: str, body: str, description: str = "d"):
    d = tmp_path / code
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
    )
    return str(d)


def _make_app(tmp_path) -> FakeSystemApp:
    skill_dir = _write_skill(
        tmp_path,
        "test-skill",
        "测试技能",
        "# 指令正文\n\n完整内容 line2\n完整内容 line3",
    )
    playbook = _Obj(
        id=1,
        declaration={"skills": ["test-skill", "missing-skill"]},
    )
    task = _Obj(id=10, playbook_id=1)
    return FakeSystemApp(
        {
            _SKILL_SVC: FakeSkillService({"test-skill": skill_dir}),
            _PLAYBOOK_SVC: FakePlaybookService({1: playbook}),
            _TASK_SVC: FakeTaskService({10: task}),
        }
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_load_skill_markdown_strips_frontmatter(tmp_path):
    app = _make_app(tmp_path)
    loaded = load_skill_markdown(app, "test-skill")
    assert loaded is not None
    assert loaded["name"] == "测试技能"
    assert "完整内容 line2" in loaded["body"]
    assert "完整内容 line3" in loaded["body"]
    assert "---" not in loaded["body"]
    assert "description:" not in loaded["body"]


def test_load_skill_markdown_missing_returns_none(tmp_path):
    app = _make_app(tmp_path)
    assert load_skill_markdown(app, "missing-skill") is None


def test_render_preloaded_skill_xml_no_truncate():
    big_body = "x" * 200_000
    xml = render_preloaded_skill_xml("big", big_body)
    assert "big" in xml
    assert xml.count("x") == 200_000  # 不截断，SKILL.md 大小由 skill 作者控制


def test_collect_from_playbook_and_chat_params_dedup(tmp_path):
    app = _make_app(tmp_path)
    xmls = collect_preloaded_skill_xmls(
        app,
        {"playbook_id": 1},
        [ChatInParam("skill(gyra)", '{"name": "test-skill"}')],
    )
    assert len(xmls) == 1  # 剧本 + 手动选择同名 → 去重
    assert "<skill_content name=\"测试技能\">" in xmls[0]
    assert "完整内容 line3" in xmls[0]


def test_collect_from_task_id(tmp_path):
    """只有 task_id 时经 task 反查剧本 skills。"""
    app = _make_app(tmp_path)
    xmls = collect_preloaded_skill_xmls(app, {"task_id": 10}, None)
    assert len(xmls) == 1
    assert "完整内容 line2" in xmls[0]


def test_collect_chat_param_only(tmp_path):
    """无剧本，仅 /skill 命令 / 页面选择的技能。"""
    app = _make_app(tmp_path)
    xmls = collect_preloaded_skill_xmls(
        app, {}, [ChatInParam("skill(gyra)", '{"skill_code": "test-skill"}')]
    )
    assert len(xmls) == 1
    assert "完整内容 line2" in xmls[0]


def test_collect_no_source_returns_empty(tmp_path):
    app = _make_app(tmp_path)
    assert collect_preloaded_skill_xmls(app, {}, None) == []


def test_build_preloaded_skills_reminder_format(tmp_path):
    app = _make_app(tmp_path)
    xmls = collect_preloaded_skill_xmls(app, {"playbook_id": 1}, None)
    reminder = build_preloaded_skills_reminder(xmls)
    assert reminder.startswith("<loaded_skills>")
    assert "<skill_content" in reminder
    assert "已预加载到当前对话上下文" in reminder
    assert reminder.endswith("</loaded_skills>") is False  # 尾部是说明文案
    assert "skill 工具" in reminder
    assert build_preloaded_skills_reminder([]) == ""


def test_chat_flow_system_prompt_assembly(tmp_path):
    """链路级：模拟 aggregation_chat 的 system_prompt_parts 组装
    （workspace 摘要 + 预加载 + media），断言最终 ext_info["system_prompt"]。"""
    app = _make_app(tmp_path)
    xmls = collect_preloaded_skill_xmls(
        app,
        {"playbook_id": 1, "workspace_id": 7},
        [ChatInParam("skill(gyra)", '{"name": "test-skill"}')],
    )
    assert len(xmls) == 1

    # 模拟 agent_chat 1508-1551 的组装：ext_info.system_prompt(调用方) + workspace
    # 摘要(注入) + media note + 预加载块，最后 "\n\n".join 合并回 ext_info
    ext_info = {"system_prompt": "BASE_PROMPT_FROM_CALLER"}
    system_prompt_parts = [ext_info["system_prompt"]]
    system_prompt_parts.append("# 当前空间：测试空间 (id=7)")
    system_prompt_parts.append("[media note]")
    system_prompt_parts.append(build_preloaded_skills_reminder(xmls))
    ext_info["system_prompt"] = "\n\n".join(system_prompt_parts).strip()
    ext_info["preloaded_skills"] = xmls

    final = ext_info["system_prompt"]
    assert final.startswith("BASE_PROMPT_FROM_CALLER")
    assert "# 当前空间：测试空间 (id=7)" in final
    assert "<loaded_skills>" in final
    assert "完整内容 line3" in final  # SKILL.md 全文在 system prompt 中
    # V2 引擎走 user-role：清单经 ext_info["preloaded_skills"] set 给 V2Agent
    assert ext_info["preloaded_skills"] == xmls
