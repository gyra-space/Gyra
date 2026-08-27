"""Phase D 黄金对照:register_variables 四个资源变量的 v2 输出格式。

v1 格式(从 resource_map 渲染,见 git 历史):
- available_agents:    - <agent><code>{code}</code><name>{name}</name><description>{desc}</description>\n</agent>\n
- available_knowledges: - <knowledge><id>{id}</id><name>{name}</name><description>{desc}</description></knowledge>\n
- available_skills:    - <skill><name>..</name><description>..</description><path>..</path><branch>..</branch><load_command>skill(name="..")</load_command>\n</skill>\n
- other_resources(DB): v1 为 schema I/O 文本;v2 为 DBCapability 基本信息(无 I/O),
  包装格式 - <database><name>..</name><prompt>..</prompt>\n</database>\n 保持一致。

用裸实例(object.__new__)避开重依赖构造,只设 register_variables 注册期需要的字段。
"""
import os

from gyra.agent.expand.react_master_agent.react_master_agent import ReActMasterAgent
from gyra.configs.model_config import DATA_DIR


class _FakePack:
    def __init__(self, caps=()):
        self._caps = list(caps)

    def get_all(self, prefix):
        return [
            c
            for c in self._caps
            if getattr(c, "capability_id", "").startswith(prefix)
        ]

    def get(self, prefix):
        caps = self.get_all(prefix)
        return caps[0] if caps else None


class _FakeAppCap:
    capability_id = "app"

    def __init__(self, app_code, app_name, app_desc):
        self.app_code = app_code
        self.app_name = app_name
        self.app_desc = app_desc


class _FakeKnowledgeCap:
    capability_id = "knowledge"

    def __init__(self, spaces):
        self._spaces = spaces


class _FakeSkillCap:
    capability_id = "skill"

    def __init__(self, skills):
        self._skills = skills


class _FakeDBCap:
    capability_id = "db:7"

    def __init__(self, db_name):
        self.db_name = db_name

    def _build_basic_info(self):
        return f"<database>\n  <name>{self.db_name}</name>\n</database>"


def _bare_agent(capability_pack=None):
    from types import SimpleNamespace

    agent = object.__new__(ReActMasterAgent)
    # current_profile 是 property,读私有属性 _inited_profile(存 __pydantic_private__);
    # _vm(VariableManager)同样是私有属性。裸实例直接预置两者。
    from gyra.agent.core.variable import VariableManager

    object.__setattr__(
        agent,
        "__pydantic_private__",
        {
            "_inited_profile": SimpleNamespace(get_role=lambda: "test-role"),
            "_vm": VariableManager(),
        },
    )
    agent.__dict__["capability_pack"] = capability_pack
    agent.__dict__["sandbox_manager"] = None
    agent.__dict__["agent_context"] = None
    agent.register_variables()
    return agent


async def test_available_agents_format_parity():
    agent = _bare_agent(
        _FakePack([_FakeAppCap("db-agent", "DB 诊断", "数据库诊断助手")])
    )
    out = await agent._vm.get_value("available_agents", instance=agent)
    assert out == (
        "- <agent><code>db-agent</code><name>DB 诊断</name>"
        "<description>数据库诊断助手</description>\n</agent>\n"
    )


async def test_available_knowledges_format_parity():
    agent = _bare_agent(
        _FakePack(
            [_FakeKnowledgeCap([{"knowledge_id": "k1", "name": "wiki", "desc": "内部wiki"}])]
        )
    )
    out = await agent._vm.get_value("available_knowledges", instance=agent)
    assert out == (
        "- <knowledge><id>k1</id><name>wiki</name>"
        "<description>内部wiki</description></knowledge>\n"
    )


async def test_available_skills_format_parity():
    agent = _bare_agent(
        _FakePack(
            [
                _FakeSkillCap(
                    [
                        {
                            "name": "data-viz",
                            "description": "图表技能",
                            "path": "",
                            "branch": "master",
                            "skill_code": "sc-1",
                        }
                    ]
                )
            ]
        )
    )
    out = await agent._vm.get_value("available_skills", instance=agent)
    expected_path = os.path.join(DATA_DIR, "skill", "sc-1")
    assert out == (
        f'- <skill><name>data-viz</name><description>图表技能</description>'
        f'<path>{expected_path}</path><branch>master</branch>'
        f'<load_command>skill(name="sc-1")</load_command>\n</skill>\n'
    )


async def test_available_skills_debug_branch_override():
    agent = _bare_agent(
        _FakePack(
            [
                _FakeSkillCap(
                    [
                        {
                            "name": "s1",
                            "description": "d",
                            "path": "",
                            "branch": "master",
                            "skill_code": "sc-9",
                            "debug_info": {"is_debug": True, "branch": "feat-x"},
                        }
                    ]
                )
            ]
        )
    )
    out = await agent._vm.get_value("available_skills", instance=agent)
    assert "<branch>feat-x</branch>" in out


async def test_other_resources_db_wrapper_format():
    agent = _bare_agent(_FakePack([_FakeDBCap("sales_db")]))
    out = await agent._vm.get_value("other_resources", instance=agent)
    assert out.startswith("- <database><name>sales_db</name><prompt>")
    assert out.endswith("</prompt>\n</database>\n")
    assert "sales_db" in out


async def test_empty_capability_pack_renders_empty():
    agent = _bare_agent(_FakePack([]))
    assert await agent._vm.get_value("available_agents", instance=agent) == ""
    assert await agent._vm.get_value("available_knowledges", instance=agent) == ""
    assert await agent._vm.get_value("other_resources", instance=agent) == ""


async def test_none_capability_pack_renders_empty():
    agent = _bare_agent(None)
    assert await agent._vm.get_value("available_agents", instance=agent) == ""
