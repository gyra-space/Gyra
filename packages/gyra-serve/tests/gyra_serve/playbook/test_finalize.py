"""公共任务收尾 finalize_task 测试(后台 run_task 与会话内 in_session 共用)。"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from gyra_serve.playbook.finalize import finalize_task


def _make_app():
    """构造 system_app:按组件名缓存并返回 MagicMock service(多次 get_component 同一实例)。"""
    app = MagicMock()
    services: dict = {}

    def _svc(name):
        m = MagicMock()
        if name == "serve_task_service":
            m.get_by_id.side_effect = lambda tid: _TASKS.get(tid)
            m.transition = MagicMock()
        elif name == "serve_playbook_service":
            m.get_by_id.side_effect = lambda pid: _PLAYBOOKS.get(pid)
        elif name == "serve_artifact_service":
            m.create.side_effect = lambda req: MagicMock(id=900)
        elif name == "serve_delivery_service":
            m.create.side_effect = lambda req: MagicMock(
                id=700, artifact_id=req.artifact_id
            )
        elif name == "serve_intervention_service":
            m.create.return_value = MagicMock(id=600)
        return m

    app.get_component.side_effect = lambda name, cls=None: services.setdefault(
        name, _svc(name)
    )
    return app


def _task(id_=1, status="running", playbook_id=5, workspace_id=1):
    t = MagicMock(id=id_, status=status, playbook_id=playbook_id, workspace_id=workspace_id)
    t.context = {"execution_mode": "in_session"}
    return t


def _playbook(id_=5):
    pb = MagicMock(id=id_, name="容量巡检")
    pb.declaration = {}
    return pb


_TASKS = {}
_PLAYBOOKS = {}


@pytest.fixture(autouse=True)
def _reset():
    _TASKS.clear()
    _PLAYBOOKS.clear()
    yield
    _TASKS.clear()
    _PLAYBOOKS.clear()


@pytest.mark.asyncio
async def test_finalize_delivered_with_artifacts_and_no_deliveries():
    _TASKS[1] = _task()
    _PLAYBOOKS[5] = _playbook()
    app = _make_app()

    with patch("gyra_serve.playbook.finalize._collect_deliverable_files",
               return_value=[{
                   "file_id": "f1", "file_name": "a.txt",
                   "download_url": "https://x/a.txt", "preview_url": None,
                   "oss_url": None,
               }]), \
         patch("gyra_serve.workspace.event_bus.emit_workspace_event"):
        result = await finalize_task(
            app, 1, agent_conv_id="a1", conv_id="c1",
            deliverable_content="最终答复", created_by_agent="scene-agent",
        )

    assert result["status"] == "delivered"
    assert result["artifact_ids"], "应物化交付文件 Artifact"
    # 无 deliverables 声明 -> 不建交付记录
    assert result["delivery_ids"] == []
    app.get_component("serve_task_service").transition.assert_called_once_with(1, "delivered")


@pytest.mark.asyncio
async def test_finalize_skips_non_running_task():
    _TASKS[1] = _task(status="closed")
    _PLAYBOOKS[5] = _playbook()
    app = _make_app()

    result = await finalize_task(app, 1, agent_conv_id="a1", conv_id="c1")

    assert result["status"] == "closed"
    app.get_component("serve_task_service").transition.assert_not_called()


@pytest.mark.asyncio
async def test_finalize_review_goes_awaiting_human():
    pb = _playbook()
    pb.declaration = {
        "deliverables": [
            {"type": "report", "delivery": [
                {"category": "notify", "channel": "in_app",
                 "require_intervention": "review"},
            ]},
        ],
    }
    _TASKS[1] = _task()
    _PLAYBOOKS[5] = pb
    app = _make_app()

    with patch("gyra_serve.playbook.finalize._collect_deliverable_files",
               return_value=[]), \
         patch("gyra_serve.workspace.event_bus.emit_workspace_event"):
        result = await finalize_task(
            app, 1, agent_conv_id="a1", conv_id="c1",
            deliverable_content="report",
        )

    assert result["status"] == "awaiting_human"
    assert len(result["delivery_ids"]) == 1
    app.get_component("serve_intervention_service").create.assert_called_once()
    app.get_component("serve_task_service").transition.assert_called_once_with(1, "awaiting_human")


@pytest.mark.asyncio
async def test_finalize_idempotent_after_delivered():
    _TASKS[1] = _task(status="delivered")
    _PLAYBOOKS[5] = _playbook()
    app = _make_app()

    result = await finalize_task(app, 1, agent_conv_id="a1", conv_id="c1")

    assert result["status"] == "delivered"
    app.get_component("serve_artifact_service").create.assert_not_called()
