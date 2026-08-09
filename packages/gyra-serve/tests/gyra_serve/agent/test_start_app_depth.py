"""Gap #178: start_app 深度传播测试。

验证 parent_depth 传入时，子 agent 的 AgentContext.extra["subagent_depth"] = parent_depth + 1。
Phase D:实现已从 GptAppResource._start_app 迁至 AppCapability.start_app。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gyra_serve.agent.capabilities.app import AppCapability


def _make_capability() -> AppCapability:
    return AppCapability(app_name="Sub", app_code="sub_app", description="")


@pytest.mark.asyncio
async def test_start_app_propagates_parent_depth_to_child_context():
    """parent_depth=2 → child AgentContext.extra["subagent_depth"] = 3。"""
    captured_contexts: list = []

    async def fake_create_agent_by_app_code(gpts_app, conv_uid=None, context=None, **kwargs):
        captured_contexts.append(context)
        mock_agent = MagicMock()
        mock_agent.generate_reply = AsyncMock(return_value=MagicMock(content="ok"))
        return mock_agent

    mock_gpts_app = MagicMock(app_code="sub_app", app_name="Sub", language="zh")

    with patch(
        "gyra_serve.agent.agents.app_agent_manage.get_app_manager"
    ) as mock_app_mgr:
        mock_app_mgr.return_value.get_app = AsyncMock(return_value=mock_gpts_app)
        mock_app_mgr.return_value.create_agent_by_app_code = fake_create_agent_by_app_code

        cap = _make_capability()
        await cap.start_app(
            user_input="hi",
            sender=MagicMock(),
            conv_uid="sub_conv_1",
            parent_depth=2,
        )

    assert len(captured_contexts) == 1
    ctx = captured_contexts[0]
    assert ctx is not None
    assert ctx.extra is not None
    assert ctx.extra.get("subagent_depth") == 3, (
        f"expected depth=3 (parent 2 + 1), got {ctx.extra.get('subagent_depth')}"
    )


@pytest.mark.asyncio
async def test_start_app_no_parent_depth_keeps_default():
    """parent_depth=None → 不写入 extra，保持默认。"""
    captured_contexts: list = []

    async def fake_create_agent_by_app_code(gpts_app, conv_uid=None, context=None, **kwargs):
        captured_contexts.append(context)
        mock_agent = MagicMock()
        mock_agent.generate_reply = AsyncMock(return_value=MagicMock(content="ok"))
        return mock_agent

    mock_gpts_app = MagicMock(app_code="sub_app", app_name="Sub", language="zh")

    with patch(
        "gyra_serve.agent.agents.app_agent_manage.get_app_manager"
    ) as mock_app_mgr:
        mock_app_mgr.return_value.get_app = AsyncMock(return_value=mock_gpts_app)
        mock_app_mgr.return_value.create_agent_by_app_code = fake_create_agent_by_app_code

        cap = _make_capability()
        await cap.start_app(
            user_input="hi",
            sender=MagicMock(),
            conv_uid="sub_conv_2",
            parent_depth=None,
        )

    assert len(captured_contexts) == 1
    ctx = captured_contexts[0]
    # parent_depth=None → child_context is None → create_agent_by_app_code 内部默认创建
    assert ctx is None


@pytest.mark.asyncio
async def test_start_app_child_inherits_parent_sandbox():
    """子 agent 共享父 agent 的 sandbox_manager（不新建、不覆盖已有的）。"""
    parent_sandbox_mgr = MagicMock()
    created_agents: list = []

    async def fake_create_agent_by_app_code(gpts_app, conv_uid=None, context=None, **kwargs):
        mock_agent = MagicMock()
        mock_agent.sandbox_manager = None
        mock_agent.generate_reply = AsyncMock(return_value=MagicMock(content="ok"))
        created_agents.append(mock_agent)
        return mock_agent

    mock_gpts_app = MagicMock(app_code="sub_app", app_name="Sub", language="zh")
    sender = MagicMock()
    sender.sandbox_manager = parent_sandbox_mgr

    with patch("gyra_serve.agent.agents.app_agent_manage.get_app_manager") as mock_app_mgr:
        mock_app_mgr.return_value.get_app = AsyncMock(return_value=mock_gpts_app)
        mock_app_mgr.return_value.create_agent_by_app_code = fake_create_agent_by_app_code

        cap = _make_capability()
        await cap.start_app(
            user_input="hi",
            sender=sender,
            conv_uid="sub_conv_3",
            parent_depth=0,
        )

    assert created_agents[0].sandbox_manager is parent_sandbox_mgr


@pytest.mark.asyncio
async def test_start_app_no_inherit_when_child_has_own_sandbox():
    """子 agent 已有自己的 sandbox_manager 时不覆盖。"""
    own_mgr = MagicMock()
    parent_mgr = MagicMock()
    created_agents: list = []

    async def fake_create_agent_by_app_code(gpts_app, conv_uid=None, context=None, **kwargs):
        mock_agent = MagicMock()
        mock_agent.sandbox_manager = own_mgr
        mock_agent.generate_reply = AsyncMock(return_value=MagicMock(content="ok"))
        created_agents.append(mock_agent)
        return mock_agent

    mock_gpts_app = MagicMock(app_code="sub_app", app_name="Sub", language="zh")
    sender = MagicMock()
    sender.sandbox_manager = parent_mgr

    with patch("gyra_serve.agent.agents.app_agent_manage.get_app_manager") as mock_app_mgr:
        mock_app_mgr.return_value.get_app = AsyncMock(return_value=mock_gpts_app)
        mock_app_mgr.return_value.create_agent_by_app_code = fake_create_agent_by_app_code

        cap = _make_capability()
        await cap.start_app(
            user_input="hi",
            sender=sender,
            conv_uid="sub_conv_4",
            parent_depth=0,
        )

    assert created_agents[0].sandbox_manager is own_mgr


@pytest.mark.asyncio
async def test_start_app_no_inherit_when_parent_has_no_sandbox():
    """父 agent 无 sandbox_manager 时子 agent 保持 None，不报错。"""
    created_agents: list = []

    async def fake_create_agent_by_app_code(gpts_app, conv_uid=None, context=None, **kwargs):
        mock_agent = MagicMock()
        mock_agent.sandbox_manager = None
        mock_agent.generate_reply = AsyncMock(return_value=MagicMock(content="ok"))
        created_agents.append(mock_agent)
        return mock_agent

    mock_gpts_app = MagicMock(app_code="sub_app", app_name="Sub", language="zh")
    sender = MagicMock()
    sender.sandbox_manager = None

    with patch("gyra_serve.agent.agents.app_agent_manage.get_app_manager") as mock_app_mgr:
        mock_app_mgr.return_value.get_app = AsyncMock(return_value=mock_gpts_app)
        mock_app_mgr.return_value.create_agent_by_app_code = fake_create_agent_by_app_code

        cap = _make_capability()
        await cap.start_app(
            user_input="hi",
            sender=sender,
            conv_uid="sub_conv_5",
            parent_depth=0,
        )

    assert created_agents[0].sandbox_manager is None
