"""V2 ask_user 交互恢复：checkpoint 查询/消费 与 会话复用决策 测试。"""
import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 与 test_agent_chat_playbook_command 相同：轻量 stub，避免引入完整 gyra_app
if "gyra_app.config" not in sys.modules:
    sys.modules["gyra_app"] = MagicMock()
    sys.modules["gyra_app.config"] = MagicMock()

from gyra.agent.core.schema import Status  # noqa: E402
from gyra.agent.core.v2.ask_user_adapter import AskUserAdapter  # noqa: E402
from gyra.agent.core.v2.state_store import DbStateStore  # noqa: E402
from gyra_serve.agent.agents.chat.agent_chat_simple import SimpleAgentChat  # noqa: E402


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = DbStateStore(path)
    yield s
    os.unlink(path)


@pytest.fixture
def chat():
    return SimpleAgentChat.__new__(SimpleAgentChat)


async def _seed_ask_user_checkpoint(store, conv_id: str) -> None:
    adapter = AskUserAdapter(state_store=store)
    await adapter.convert(
        {"message": "请确认是否继续？", "options": ["继续", "停止"]},
        step_id="step-1",
        conv_id=conv_id,
    )


def test_has_v2_ask_user_checkpoint_true(chat, store):
    """存在 ASK_USER_LEGACY checkpoint 时返回 True。"""
    asyncio.run(_seed_ask_user_checkpoint(store, "conv-session-1"))
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        assert asyncio.run(chat._has_v2_ask_user_checkpoint("conv-session-1"))


def test_has_v2_ask_user_checkpoint_false_when_absent(chat, store):
    """无 checkpoint（或空会话）时返回 False。"""
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        assert not asyncio.run(chat._has_v2_ask_user_checkpoint("conv-session-2"))


def test_consume_v2_ask_user_checkpoints(chat, store):
    """消费（删除）ask_user checkpoint，避免残留误判。"""
    asyncio.run(_seed_ask_user_checkpoint(store, "conv-session-3"))
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        asyncio.run(chat._consume_v2_ask_user_checkpoints("conv-session-3"))
    assert not asyncio.run(chat._has_v2_ask_user_checkpoint("conv-session-3"))


def _conv(conv_id: str, state: str):
    entity = MagicMock()
    entity.conv_id = conv_id
    entity.state = state
    return entity


def test_initialize_reuses_waiting_conversation(chat, store):
    """last_conversation 为 WAITING → 复用原会话并消费 checkpoint。"""
    asyncio.run(_seed_ask_user_checkpoint(store, "session-w"))
    chat.gpts_conversations = MagicMock()
    chat.gpts_conversations.get_by_session_id_asc = AsyncMock(
        return_value=[_conv("session-w_1", Status.WAITING.value)]
    )
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        agent_conv_id, _ = asyncio.run(
            chat._initialize_agent_conversation("session-w")
        )
    assert agent_conv_id == "session-w_1"
    # checkpoint 已被消费
    assert not asyncio.run(chat._has_v2_ask_user_checkpoint("session-w"))


def test_initialize_reuses_v2_ask_user_fallback(chat, store):
    """非 WAITING 但有 ask_user checkpoint → 复用原会话（防新建 _2 并发）。"""
    asyncio.run(_seed_ask_user_checkpoint(store, "session-f"))
    chat.gpts_conversations = MagicMock()
    chat.gpts_conversations.get_by_session_id_asc = AsyncMock(
        return_value=[_conv("session-f_1", Status.RUNNING.value)]
    )
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        agent_conv_id, _ = asyncio.run(
            chat._initialize_agent_conversation("session-f")
        )
    assert agent_conv_id == "session-f_1"
    assert not asyncio.run(chat._has_v2_ask_user_checkpoint("session-f"))


def test_initialize_creates_new_when_no_checkpoint(chat, store):
    """非 WAITING 且无 ask_user checkpoint → 新建 _N 会话（正常新消息）。"""
    chat.gpts_conversations = MagicMock()
    chat.gpts_conversations.get_by_session_id_asc = AsyncMock(
        return_value=[_conv("session-n_1", Status.COMPLETE.value)]
    )
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        agent_conv_id, _ = asyncio.run(
            chat._initialize_agent_conversation("session-n")
        )
    assert agent_conv_id == "session-n_2"


def test_initialize_first_conversation(chat, store):
    """无历史会话 → _1。"""
    chat.gpts_conversations = MagicMock()
    chat.gpts_conversations.get_by_session_id_asc = AsyncMock(return_value=[])
    with patch(
        "gyra.agent.core.v2.state_store.create_state_store", return_value=store
    ):
        agent_conv_id, _ = asyncio.run(
            chat._initialize_agent_conversation("session-0")
        )
    assert agent_conv_id == "session-0_1"
