"""playbook_command 入口与 scene_agent_workspace render_name 测试。"""
import sys
from unittest.mock import MagicMock

import pytest

# The task package __init__ eagerly imports endpoints -> runtime -> agent
# controller, which requires gyra_app.config. Provide a lightweight stub so
# unit tests can import chat modules without the full gyra_app package
# installed.
if "gyra_app.config" not in sys.modules:
    sys.modules["gyra_app"] = MagicMock()
    sys.modules["gyra_app.config"] = MagicMock()

from gyra_serve.agent.agents.chat.agent_chat import AgentChat
from gyra_serve.agent.agents.chat.agent_chat_simple import SimpleAgentChat
from gyra_serve.building.config.api.schemas import ChatInParamValue


def _make_param(ptype, value, sub_type=None):
    return ChatInParamValue(param_type=ptype, param_value=value, sub_type=sub_type)


def test_extract_playbook_command_returns_playbook_id_and_name():
    """chat_in_params 含 playbook_command 时能被正确抽取。"""
    chat = SimpleAgentChat.__new__(SimpleAgentChat)
    params = [
        _make_param("resource", "[]", "common_file"),
        _make_param(
            "playbook_command",
            '{"playbook_id": 7, "playbook_name": "营收分析"}',
            "playbook",
        ),
    ]
    cmd = chat._extract_playbook_command(params)  # type: ignore[attr-defined]
    assert cmd == {"playbook_id": 7, "playbook_name": "营收分析"}


def test_extract_playbook_command_returns_none_when_absent():
    chat = SimpleAgentChat.__new__(SimpleAgentChat)
    assert chat._extract_playbook_command(None) is None  # type: ignore[attr-defined]
    assert chat._extract_playbook_command([_make_param("resource", "[]")]) is None  # type: ignore[attr-defined]


def test_resolve_vis_render_prefers_scene_for_workspace():
    """有 workspace_id 时 render_name 解析为 scene_agent_workspace。"""
    chat = SimpleAgentChat.__new__(SimpleAgentChat)
    assert chat._resolve_vis_render(ext_info={"workspace_id": 1}, gpt_app=None) == "scene_agent_workspace"  # type: ignore[attr-defined]
    # 无 workspace_id 且无 app layout 时回退 gpt_vis_all
    assert chat._resolve_vis_render(ext_info={}, gpt_app=None) == "gpt_vis_all"  # type: ignore[attr-defined]


def test_resolve_vis_render_defaults_v2_agent_to_vis_manus():
    """v2 引擎应用未配置布局时默认 vis_manus(gpt_vis_all 不支持增量合并与步骤渲染)。"""
    chat = SimpleAgentChat.__new__(SimpleAgentChat)

    def _app(agent_version=None, team_context=None):
        app = MagicMock()
        app.layout = None
        app.agent_version = agent_version
        app.team_context = team_context
        return app

    assert chat._resolve_vis_render(ext_info={}, gpt_app=_app(agent_version="v2")) == "vis_manus"  # type: ignore[attr-defined]
    assert (
        chat._resolve_vis_render(ext_info={}, gpt_app=_app(team_context={"agent_version": "v2"}))  # type: ignore[attr-defined]
        == "vis_manus"
    )
    # v1 应用仍走 gpt_vis_all
    assert chat._resolve_vis_render(ext_info={}, gpt_app=_app(agent_version="v1")) == "gpt_vis_all"  # type: ignore[attr-defined]


def test_extract_model_returns_model_name():
    """chat_in_params 含 model 参数时能抽到 param_value。"""
    chat = SimpleAgentChat.__new__(SimpleAgentChat)
    params = [
        _make_param("resource", "[]", "common_file"),
        _make_param("model", "test-provider/test-model"),
    ]
    assert chat._extract_model(params) == "test-provider/test-model"  # type: ignore[attr-defined]


def test_extract_model_returns_none_when_absent():
    chat = SimpleAgentChat.__new__(SimpleAgentChat)
    assert chat._extract_model(None) is None  # type: ignore[attr-defined]
    assert chat._extract_model([_make_param("resource", "[]")]) is None  # type: ignore[attr-defined]


def test_inject_workspace_context_no_longer_appends_extra_agents():
    """移除 toolkit 注入后,_inject_workspace_context 不再往 extra_agents append。"""
    from gyra_serve.agent.agents.chat.agent_chat import _inject_workspace_context
    from unittest.mock import MagicMock, patch
    extra_agents = []
    ext_info = {"workspace_id": 1}
    with patch("gyra_serve.agent.agents.chat.agent_chat._legacy_build_workspace_context") as mleg, \
         patch("gyra_serve.agent.agents.chat.agent_chat.build_workspace_context") as mbwc, \
         patch("gyra_serve.agent.agents.chat.agent_chat.render_workspace_context_summary") as msum, \
         patch("gyra_serve.agent.agents.chat.agent_chat.render_scene_dynamic_context") as mscene:
        mleg.return_value = {"materialized": {"dynamic_resources": [], "extra_agents": []}}
        mbwc.return_value = MagicMock(playbook_resource=None)
        msum.return_value = ""; mscene.return_value = ""
        _inject_workspace_context(
            system_app=MagicMock(), workspace_id=1, user_id="u1",
            conv_uid="c1", task_id=None, system_prompt=[],
            extra_agents=extra_agents, ext_info=ext_info, llm_config=None,
            event_queue=None, app_code="scene-workspace-agent",
        )
    assert extra_agents == []