"""ECP 默认提案 Agent 绑定:工作空间未配置时自动绑定内置 ecp-proposal-agent。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gyra_serve.ecp.config import DEFAULT_PROPOSAL_AGENT_APP_CODE
from gyra_serve.ecp.service.service import Service


def _make_service(ws_config_dao=None) -> Service:
    svc = Service.__new__(Service)
    svc._ws_config_dao = ws_config_dao if ws_config_dao is not None else MagicMock()
    return svc


class TestEnsureDefaultProposalAgent:
    def test_binds_default_when_unset(self):
        dao = MagicMock()
        dao.get.return_value = SimpleNamespace(proposal_agent_id=None)
        svc = _make_service(dao)

        svc._ensure_default_proposal_agent("ws1")

        dao.upsert.assert_called_once_with("ws1", DEFAULT_PROPOSAL_AGENT_APP_CODE)

    def test_keeps_existing_binding(self):
        dao = MagicMock()
        dao.get.return_value = SimpleNamespace(proposal_agent_id="user-app")
        svc = _make_service(dao)

        svc._ensure_default_proposal_agent("ws1")

        dao.upsert.assert_not_called()

    def test_failure_is_silent(self):
        dao = MagicMock()
        dao.get.side_effect = RuntimeError("db down")
        svc = _make_service(dao)

        svc._ensure_default_proposal_agent("ws1")

        dao.upsert.assert_not_called()


class TestGetOrCreateSpaceSeedsDefaultAgent:
    @pytest.mark.asyncio
    async def test_get_or_create_space_invokes_binding(self):
        svc = Service.__new__(Service)
        ks = MagicMock()
        ks.get_space_config = AsyncMock(return_value={"slug": "ecp-ws9"})
        svc._system_app = MagicMock()
        svc._system_app.get_component.return_value = ks
        svc._asset_dao = MagicMock()
        svc._oplog_dao = MagicMock()

        with patch.object(
            Service, "_ensure_default_proposal_agent", autospec=True
        ) as ensure:
            vo = await svc.get_or_create_space("ws9")

        assert vo.created is False
        ensure.assert_called_once_with(svc, "ws9")
        svc._asset_dao.register.assert_called_once()
