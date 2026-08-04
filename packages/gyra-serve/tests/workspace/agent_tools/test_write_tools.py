import asyncio
import pytest
from unittest.mock import MagicMock

from gyra_serve.workspace.agent_tools._task_creator import create_task_from_tool


class TestCreateTaskFromTool:
    """Tests for _task_creator.create_task_from_tool."""

    def _build_system_app(self, mock_task, mock_playbook=None):
        """Build a mock system_app with task and playbook services."""
        mock_task_service = MagicMock()
        mock_task_service.create.return_value = mock_task

        mock_playbook_service = MagicMock()
        if mock_playbook is not None:
            mock_playbook_service.get_by_id.return_value = mock_playbook

        system_app = MagicMock()

        def get_component(name, cls):
            if name == "serve_task_service":
                return mock_task_service
            if name == "serve_playbook_service":
                return mock_playbook_service
            return None

        system_app.get_component = get_component
        return system_app

    @pytest.fixture(autouse=True)
    def _mock_asyncio_create_task(self, monkeypatch):
        """create_task_from_tool 在分离模式下会调 asyncio.create_task 启动 detached
        协程,测试无运行事件循环,monkeypatch 掉避免 RuntimeError。"""
        from gyra_serve.workspace.agent_tools import _task_creator

        async def _noop(*a, **kw):
            return None

        def fake_create_task(coro):
            return asyncio.ensure_future(coro)

        monkeypatch.setattr(_task_creator.asyncio, "create_task", fake_create_task)
        monkeypatch.setattr(_task_creator, "_summarize_title_detached", _noop)

    def test_creates_task_with_playbook(self):
        """When playbook_id is given, task title defaults to playbook name."""
        mock_task = MagicMock()
        mock_task.id = 42
        mock_task.title = "容量巡检"
        mock_task.status = "draft"
        mock_task.playbook_id = 7
        mock_task.triggered_by = "manual"

        mock_playbook = MagicMock()
        mock_playbook.name = "容量巡检"

        system_app = self._build_system_app(mock_task, mock_playbook)

        result = create_task_from_tool(
            system_app, workspace_id=1, user_id="100", playbook_id=7
        )
        assert result["task_id"] == 42
        assert result["title"] == "容量巡检"
        assert result["status"] == "draft"
        assert result["playbook_id"] == 7
        assert result["playbook_name"] == "容量巡检"
        assert result["triggered_by"] == "manual"

        mock_task_service = system_app.get_component("serve_task_service", MagicMock)
        request = mock_task_service.create.call_args.args[0]
        assert request.workspace_id == 1
        assert request.playbook_id == 7
        assert request.title == "容量巡检"
        assert request.type == "adhoc"
        assert request.triggered_by == "manual"
        assert request.created_by_user_id == 100

    def test_creates_task_with_custom_title(self):
        """When title is given, it overrides the playbook name."""
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "自定义标题"
        mock_task.status = "draft"
        mock_task.playbook_id = None
        mock_task.triggered_by = "manual"

        system_app = self._build_system_app(mock_task)

        result = create_task_from_tool(
            system_app,
            workspace_id=1,
            user_id="100",
            title="自定义标题",
            description="测试描述",
        )
        assert result["task_id"] == 1
        assert result["title"] == "自定义标题"

        mock_task_service = system_app.get_component("serve_task_service", MagicMock)
        request = mock_task_service.create.call_args.args[0]
        assert request.workspace_id == 1
        assert request.title == "自定义标题"
        assert request.description == "测试描述"
        assert request.type == "adhoc"
        assert request.triggered_by == "manual"
        assert request.created_by_user_id == 100

    def test_creates_task_without_playbook(self):
        """When no playbook_id, title defaults to '手动创建任务'."""
        mock_task = MagicMock()
        mock_task.id = 99
        mock_task.title = "手动创建任务"
        mock_task.status = "draft"
        mock_task.playbook_id = None
        mock_task.triggered_by = "manual"

        system_app = self._build_system_app(mock_task)

        result = create_task_from_tool(
            system_app, workspace_id=1, user_id="100"
        )
        assert result["task_id"] == 99
        assert result["title"] == "手动创建任务"
        assert result["playbook_id"] is None
        assert result["playbook_name"] is None

        mock_task_service = system_app.get_component("serve_task_service", MagicMock)
        request = mock_task_service.create.call_args.args[0]
        assert request.workspace_id == 1
        assert request.playbook_id is None
        assert request.title == "手动创建任务"
        assert request.description == ""
        assert request.type == "adhoc"
        assert request.triggered_by == "manual"
        assert request.created_by_user_id == 100

    def test_user_id_non_digit(self):
        """When user_id is not a digit, created_by_user_id is None."""
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "手动创建任务"
        mock_task.status = "draft"
        mock_task.playbook_id = None
        mock_task.triggered_by = "manual"

        system_app = self._build_system_app(mock_task)

        result = create_task_from_tool(
            system_app, workspace_id=1, user_id="system"
        )
        assert result["task_id"] == 1

        mock_task_service = system_app.get_component("serve_task_service", MagicMock)
        request = mock_task_service.create.call_args.args[0]
        assert request.created_by_user_id is None


class TestWriteToolsStartTask:
    """Tests for write_tools.build_write_tools start_task behavior."""

    def _build_system_app(self, mock_task):
        """Build a mock system_app with task and playbook services."""
        mock_task_service = MagicMock()
        mock_task_service.create.return_value = mock_task

        mock_playbook_service = MagicMock()

        system_app = MagicMock()

        def get_component(name, cls):
            if name == "serve_task_service":
                return mock_task_service
            if name == "serve_playbook_service":
                return mock_playbook_service
            return None

        system_app.get_component = get_component
        return system_app

    def test_start_task_emits_event(self):
        """start_task should call on_event with task_created.

        大厅模式(conv_uid 非空、task_id 为空)下 start_task 走内联模式:
        任务绑定到当前会话,status 为 running。
        """
        from gyra_serve.workspace.agent_tools.write_tools import build_write_tools

        mock_task = MagicMock()
        mock_task.id = 42
        mock_task.title = "测试任务"
        mock_task.status = "draft"
        mock_task.playbook_id = None
        mock_task.triggered_by = "manual"

        system_app = self._build_system_app(mock_task)

        events = []

        def on_event(event_type, payload):
            events.append((event_type, payload))

        tools = build_write_tools(
            system_app,
            workspace_id=1,
            user_id="100",
            conv_uid="conv-1",
            on_event=on_event,
        )

        start_task_tool = next(t for t in tools if t.name == "start_task")
        result = start_task_tool.execute()

        assert result["task_id"] == 42
        assert result["inline"] is True
        assert result["status"] == "running"
        assert len(events) == 1
        assert events[0][0] == "task_created"
        assert events[0][1]["task_id"] == 42
        assert events[0][1]["workspace_id"] == 1
        assert events[0][1]["title"] == "测试任务"
        assert events[0][1]["status"] == "running"
        assert events[0][1]["triggered_by"] == "manual"

    def test_start_task_without_event_callback(self):
        """start_task should work without on_event (no error)."""
        from gyra_serve.workspace.agent_tools.write_tools import build_write_tools

        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "任务"
        mock_task.status = "draft"
        mock_task.playbook_id = None
        mock_task.triggered_by = "manual"

        system_app = self._build_system_app(mock_task)

        tools = build_write_tools(
            system_app,
            workspace_id=1,
            user_id="100",
            conv_uid="conv-1",
            on_event=None,
        )

        start_task_tool = next(t for t in tools if t.name == "start_task")
        result = start_task_tool.execute()

        assert result["task_id"] == 1

    def test_start_task_task_mode_not_inline(self, monkeypatch):
        """任务模式(task_id 非空)下 start_task 不走内联模式,仍创建分离任务。"""
        from gyra_serve.workspace.agent_tools import _task_creator
        from gyra_serve.workspace.agent_tools.write_tools import build_write_tools

        mock_task = MagicMock()
        mock_task.id = 55
        mock_task.title = "子任务"
        mock_task.status = "draft"
        mock_task.playbook_id = None
        mock_task.triggered_by = "manual"

        system_app = self._build_system_app(mock_task)

        # 分离模式会调 asyncio.create_task(start detached run_task),
        # 测试无运行事件循环,monkeypatch 掉避免 RuntimeError。
        created_tasks = []

        def fake_create_task(coro):
            created_tasks.append(coro)
            t = asyncio.ensure_future(coro)
            return t

        async def _noop_title(*a, **kw):
            return None

        monkeypatch.setattr(_task_creator.asyncio, "create_task", fake_create_task)
        monkeypatch.setattr(_task_creator, "_summarize_title_detached", _noop_title)

        tools = build_write_tools(
            system_app,
            workspace_id=1,
            user_id="100",
            conv_uid="task-conv-1",
            task_id=10,  # 已在任务对话中
            on_event=None,
        )

        start_task_tool = next(t for t in tools if t.name == "start_task")
        result = start_task_tool.execute()

        assert result["task_id"] == 55
        assert result["inline"] is False
        assert result["status"] == "draft"  # 分离模式:status 来自 entity

    def test_non_start_task_tools_still_create_interventions(self):
        """close_task, publish_asset, etc. should still create interventions."""
        from gyra_serve.workspace.agent_tools.write_tools import build_write_tools

        mock_intervention = MagicMock()
        mock_intervention.id = 99

        mock_intervention_service = MagicMock()
        mock_intervention_service.create.return_value = mock_intervention

        system_app = MagicMock()

        def get_component(name, cls):
            if name == "serve_intervention_service":
                return mock_intervention_service
            return None

        system_app.get_component = get_component

        tools = build_write_tools(
            system_app,
            workspace_id=1,
            user_id="100",
            conv_uid="conv-1",
        )

        close_task_tool = next(t for t in tools if t.name == "close_task")
        result = close_task_tool.execute(task_id=5)
        assert result["intervention_id"] == 99
        assert result["status"] == "awaiting_human"
