"""skill_publish Agent 工具守卫单元测试。

覆盖:
- context 两种注入形态:V2(ToolContext)与 V1(context=agent 本体,
  身份从 agent_context.extra 取)——回归 ReActMasterAgent 无 get_resource 报错;
- fail-closed:无身份 / 无 skill.publish 权限一律拒绝;
- workspace_id 在两种形态下都能透传到 publish 核心层。
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gyra.agent.tools.context import ToolContext
from gyra_serve.utils.auth import UserRequest

from gyra_app.feature_plugins.skills import agent_tools


def _admin() -> UserRequest:
    return UserRequest(user_id="1", user_name="admin", role="admin")


def _no_perm_user() -> UserRequest:
    return UserRequest(
        user_id="2", user_name="bob", role="normal",
        permissions={}, roles=[], grants=[],
    )


def _v1_agent(user, workspace_id=None):
    """V1 形态的 context:即 agent 本身(react_master 路径)。"""
    return SimpleNamespace(
        agent_context=SimpleNamespace(
            extra={"user_request": user, "workspace_id": workspace_id}
        ),
        conv_id="c1",
    )


def _v2_ctx(user, workspace_id=None) -> ToolContext:
    ctx = ToolContext()
    if user is not None:
        ctx.set_resource("user_request", user)
    if workspace_id is not None:
        ctx.set_resource("workspace_id", workspace_id)
    return ctx


def _publish(**kwargs):
    captured = {}

    def fake_publish(skill_dir, operator="", workspace_id=None, system_app=None):
        captured.update(
            skill_dir=skill_dir, operator=operator, workspace_id=workspace_id
        )
        return {"success": True, "skill_code": "x"}

    with patch(
        "gyra_serve.skill.publish.publish_skill_from_dir", side_effect=fake_publish
    ):
        result = agent_tools.skill_publish("/tmp/skill", **kwargs)
    return result, captured


# --------------------------------------------------------------------------- #
# context 形态兼容
# --------------------------------------------------------------------------- #
def test_v1_agent_context_resolves_identity():
    """V1:context 是 ReActMasterAgent 本体,不应报 get_resource AttributeError。"""
    result, captured = _publish(context=_v1_agent(_admin(), workspace_id=7))
    assert result["success"] is True
    assert captured["operator"] == "admin"
    assert captured["workspace_id"] == 7


def test_v2_toolcontext_resolves_identity():
    result, captured = _publish(context=_v2_ctx(_admin(), workspace_id=9))
    assert result["success"] is True
    assert captured["operator"] == "admin"
    assert captured["workspace_id"] == 9


def test_v1_agent_without_extra_user_denied():
    agent = SimpleNamespace(agent_context=SimpleNamespace(extra={}), conv_id="c1")
    result = agent_tools.skill_publish("/tmp/skill", context=agent)
    assert result["success"] is False
    assert result["code"] == "PERMISSION_DENIED"


def test_none_context_denied():
    result = agent_tools.skill_publish("/tmp/skill", context=None)
    assert result["success"] is False
    assert result["code"] == "PERMISSION_DENIED"


# --------------------------------------------------------------------------- #
# 权限
# --------------------------------------------------------------------------- #
def test_user_without_publish_permission_denied():
    result, _ = _publish(context=_v1_agent(_no_perm_user()))
    assert result["success"] is False
    assert "skill.publish" in result["error"]
