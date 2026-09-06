"""场景管理写工具测试:触发 + 介入审批工具。"""
from unittest.mock import MagicMock, patch


def test_build_scene_write_tools_includes_trigger_and_intervention_tools():
    """build_scene_write_tools 产出含 update_trigger/delete_trigger/
    fire_trigger/resolve_intervention/abort_intervention + 原有 start_task/close_task 等。
    专家派单不走专用工具:协作走标准 SubAgent,任务化派单走 start_task(app_code)。"""
    from gyra_serve.workspace.agent_tools.write_tools import build_scene_write_tools
    tools = build_scene_write_tools(
        system_app=MagicMock(), workspace_id=1, user_id="u1",
        conv_uid="c1", task_id=None,
    )
    names = {t.name for t in tools}
    for must in ("start_task", "close_task",
                 "resolve_intervention", "abort_intervention",
                 "update_trigger", "delete_trigger", "fire_trigger",
                 "publish_asset", "create_delivery", "update_workspace"):
        assert must in names, f"missing tool {must}; got {names}"
    assert "dispatch_to_expert" not in names

