"""app_card_preview 开发期取数工具注册测试。

该工具作为数据库资源自带取数工具,经 ``@tool`` 装饰器自动注册进 tool_registry,
由 ``base_agent._inject_database_tools`` 随 DBResource 一起注入 agent TOOLS 槽。
"""
from gyra.agent.tools.base import ToolCategory
from gyra.agent.tools.registry import tool_registry


def _ensure_registered():
    import gyra_serve.app_card.agent_tools  # noqa: F401  触发 @tool 注册


def test_app_card_preview_registered():
    _ensure_registered()
    tool = tool_registry.get("app_card_preview")
    assert tool is not None
    assert tool.name == "app_card_preview"
    assert tool.metadata.category == ToolCategory.DATABASE
    assert "app_card_preview" in tool_registry.list_names()
