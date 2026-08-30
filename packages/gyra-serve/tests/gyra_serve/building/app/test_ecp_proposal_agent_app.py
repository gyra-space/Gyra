"""ecp-proposal-agent.json 内置应用定义校验 + 与 config 常量一致性。"""

import json
import os
import sys
from unittest.mock import MagicMock

if "gyra_app.config" not in sys.modules:
    sys.modules["gyra_app"] = MagicMock()
    sys.modules["gyra_app.config"] = MagicMock()

from gyra_serve.building.app.api.schemas import ServeRequest
from gyra_serve.ecp.config import DEFAULT_PROPOSAL_AGENT_APP_CODE


def _load_json():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(
        current_dir,
        "../../../../src/gyra_serve/building/app/service/gyra_app_define/"
        "ecp-proposal-agent.json",
    )
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_ecp_proposal_agent_json_parses_via_serve_request():
    """ecp-proposal-agent.json 可通过 ServeRequest.from_dict 解析。"""
    items = _load_json()
    assert len(items) == 1
    item = items[0]
    request = ServeRequest.from_dict(item)
    assert request.app_code == DEFAULT_PROPOSAL_AGENT_APP_CODE
    assert request.app_code == "ecp-proposal-agent"
    assert request.agent == "EcpProposalAgent"
    assert request.team_mode == "single_agent"
    assert request.published is True


def test_ecp_proposal_agent_json_relies_on_class_profile():
    """无 GptsApp 级 system_prompt_template(提示词由 EcpProposalAgent 类内置)。"""
    item = _load_json()[0]
    assert item.get("system_prompt_template") is None
