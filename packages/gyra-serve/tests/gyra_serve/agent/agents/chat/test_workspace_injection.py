"""Tests for workspace materialized resource injection in aggregation_chat."""
import sys
from unittest.mock import MagicMock, patch

import pytest

# The task package __init__ eagerly imports endpoints -> runtime -> agent
# controller, which requires gyra_app.config. Provide a lightweight stub so
# unit tests can import chat modules without the full gyra_app package
# installed.
if "gyra_app.config" not in sys.modules:
    sys.modules["gyra_app"] = MagicMock()
    sys.modules["gyra_app.config"] = MagicMock()

from gyra_serve.agent.agents.chat.agent_chat import (
    _ensure_lobby_conv_link,
    _inject_workspace_context,
)


class _ConcreteAgentChat:
    system_app = MagicMock()


def _make_fake_ctx(materialized=None):
    return {
        "workspace_id": 1,
        "workspace": MagicMock(),
        "members": [],
        "resources": [],
        "materialized": materialized or {},
        "current_task": None,
        "recent_tasks": [],
        "recent_assets": [],
        "task_artifacts": [],
        "task_interventions": [],
    }


@pytest.mark.asyncio
async def test_workspace_materialized_resources_injected_to_ext_info():
    """workspace_id 存在时，物化的 dynamic_resources 合并到 ext_info。"""
    agent_chat = _ConcreteAgentChat()
    ext_info = {"workspace_id": 1, "task_id": None}

    fake_resource = MagicMock()
    fake_resource.type = "mcp(gyra)"
    fake_ctx = _make_fake_ctx(
        materialized={
            "dynamic_resources": [fake_resource],
            "extra_agents": [{"app_code": "analyzer"}],
        }
    )

    with patch(
        "gyra_serve.agent.agents.chat.agent_chat._legacy_build_workspace_context",
        return_value=fake_ctx,
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.build_workspace_context",
        return_value=fake_ctx,
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.render_workspace_context_summary",
        return_value="summary",
    ):
        _inject_workspace_context(
            system_app=agent_chat.system_app,
            workspace_id=ext_info.get("workspace_id"),
            user_id=None,
            conv_uid="conv-1",
            task_id=ext_info.get("task_id"),
            system_prompt=[],
            extra_agents=ext_info.setdefault("extra_agents", []),
            ext_info=ext_info,
        )

    assert "dynamic_resources" in ext_info
    assert len(ext_info["dynamic_resources"]) == 1
    assert ext_info["dynamic_resources"][0] == fake_resource
    assert "extra_agents" in ext_info
    assert ext_info["extra_agents"] == [{"app_code": "analyzer"}]
    assert "workspace_context" in ext_info


@pytest.mark.asyncio
async def test_workspace_injection_no_workspace_id_noop():
    """无 workspace_id 时 ext_info 不被改动。"""
    ext_info = {}
    _inject_workspace_context(
        system_app=MagicMock(),
        workspace_id=None,
        user_id=None,
        conv_uid="conv-1",
        task_id=None,
        system_prompt=[],
        extra_agents=[],
        ext_info=ext_info,
    )
    assert "dynamic_resources" not in ext_info
    assert "extra_agents" not in ext_info
    assert "workspace_context" not in ext_info


@pytest.mark.asyncio
async def test_workspace_materialized_resources_merged_with_existing():
    """已有 dynamic_resources / extra_agents 时，物化资源追加而非覆盖。"""
    existing_resource = MagicMock()
    existing_resource.type = "existing"
    materialized_resource = MagicMock()
    materialized_resource.type = "materialized"

    ext_info = {
        "workspace_id": 1,
        "task_id": None,
        "dynamic_resources": [existing_resource],
        "extra_agents": [{"app_code": "existing"}],
    }

    fake_ctx = _make_fake_ctx(
        materialized={
            "dynamic_resources": [materialized_resource],
            "extra_agents": [{"app_code": "materialized"}],
        }
    )

    with patch(
        "gyra_serve.agent.agents.chat.agent_chat._legacy_build_workspace_context",
        return_value=fake_ctx,
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.build_workspace_context",
        return_value=fake_ctx,
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.render_workspace_context_summary",
        return_value="summary",
    ):
        _inject_workspace_context(
            system_app=MagicMock(),
            workspace_id=ext_info.get("workspace_id"),
            user_id=None,
            conv_uid="conv-1",
            task_id=ext_info.get("task_id"),
            system_prompt=[],
            extra_agents=ext_info["extra_agents"],
            ext_info=ext_info,
        )

    assert len(ext_info["dynamic_resources"]) == 2
    assert ext_info["dynamic_resources"][0] == existing_resource
    assert ext_info["dynamic_resources"][1] == materialized_resource

    assert len(ext_info["extra_agents"]) == 2
    assert ext_info["extra_agents"][0] == {"app_code": "existing"}
    assert ext_info["extra_agents"][1] == {"app_code": "materialized"}


@pytest.mark.asyncio
async def test_inject_workspace_context_never_appends_toolkit_agent():
    """回归：移除 toolkit 注入后 extra_agents 不再被追加 WorkspaceControlAgent。

    场景工具走资源协议正道（WorkspaceSceneResource TOOLS slot）在 chat 端点
    预装配阶段注入；_inject_workspace_context 只负责摘要/物化资源，不再构造
    toolkit agent，避免 agent_context=None 导致 agent_to_resource 崩溃。
    """
    ext_info = {"workspace_id": 1, "task_id": None, "extra_agents": []}
    extra_agents = ext_info["extra_agents"]

    fake_agent = MagicMock(name="WorkspaceControlAgent")
    fake_ctx = _make_fake_ctx()

    with patch(
        "gyra_serve.agent.agents.chat.agent_chat._legacy_build_workspace_context",
        return_value=fake_ctx,
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.build_workspace_context",
        return_value=fake_ctx,
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.render_workspace_context_summary",
        return_value="summary",
    ), patch(
        "gyra_serve.agent.agents.chat.agent_chat.render_scene_dynamic_context",
        return_value="",
    ):
        _inject_workspace_context(
            system_app=MagicMock(),
            workspace_id=ext_info.get("workspace_id"),
            user_id=None,
            conv_uid="conv-1",
            task_id=ext_info.get("task_id"),
            system_prompt=[],
            extra_agents=extra_agents,
            ext_info=ext_info,
        )

    # extra_agents remains empty — no toolkit agent appended.
    assert ext_info["extra_agents"] == []
    assert extra_agents == []
    assert fake_agent not in ext_info["extra_agents"]


def test_ensure_lobby_conv_link_links_workspace_conv():
    """大厅直接对话(task_id 为空)兜底:确保会话进入空间任务列表。"""
    system_app = MagicMock()
    ws_svc = MagicMock()
    system_app.get_component.return_value = ws_svc

    _ensure_lobby_conv_link(
        system_app, workspace_id=1, conv_id="conv-1", user_code="42", task_id=None
    )

    ws_svc.link_conversation.assert_called_once_with(
        workspace_id=1, conv_uid="conv-1", user_id=42
    )


def test_ensure_lobby_conv_link_skips_task_conversation():
    """任务对话(task_id 非空)跳过兜底,避免覆盖任务创建时建立的关联。"""
    system_app = MagicMock()
    ws_svc = MagicMock()
    system_app.get_component.return_value = ws_svc

    _ensure_lobby_conv_link(
        system_app, workspace_id=1, conv_id="conv-1", user_code="42", task_id=7
    )

    ws_svc.link_conversation.assert_not_called()


def test_ensure_lobby_conv_link_noop_without_workspace():
    """无 workspace_id 时不执行任何 link。"""
    system_app = MagicMock()
    _ensure_lobby_conv_link(system_app, workspace_id=None, conv_id="conv-1", user_code="42", task_id=None)
    system_app.get_component.assert_not_called()


def test_ensure_lobby_conv_link_swallows_link_error():
    """link 失败只记日志,不阻断对话。"""
    system_app = MagicMock()
    system_app.get_component.return_value = MagicMock()
    system_app.get_component.return_value.link_conversation.side_effect = RuntimeError("db down")

    _ensure_lobby_conv_link(
        system_app, workspace_id=1, conv_id="conv-1", user_code="42", task_id=None
    )  # should not raise


def test_ensure_lobby_conv_link_non_numeric_user_code():
    """user_code 非数字时 user_id 落 None(无主 link,对所有用户可见)。"""
    system_app = MagicMock()
    ws_svc = MagicMock()
    system_app.get_component.return_value = ws_svc

    _ensure_lobby_conv_link(
        system_app, workspace_id=1, conv_id="conv-1", user_code="abc", task_id=None
    )

    ws_svc.link_conversation.assert_called_once_with(
        workspace_id=1, conv_uid="conv-1", user_id=None
    )
