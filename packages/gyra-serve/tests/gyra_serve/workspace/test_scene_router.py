"""回合前路由测试:页面输入命中剧本 -> 预建会话内任务(execution_mode=in_session)。

覆盖 route_scene_execution:
- 显式 playbook_id / 隐式名称匹配 -> 预建 Task(triggered_by=page, conv=当前会话,
  context.execution_mode=in_session)并注入 ext_info.task_id;
- API/定时/订阅发起、已绑定任务会话、会话已有任务 -> 跳过;
- 未命中剧本 / 任何异常 -> 返回 None,保持原大厅对话行为。
"""
from unittest.mock import MagicMock

from gyra_serve.workspace.scene_router import route_scene_execution


def _make_app(conv_link=None, playbooks=None, playbook=None, task=None):
    app = MagicMock()
    ws_svc = MagicMock()
    ws_svc.get_conversation_workspace.return_value = conv_link
    pb_svc = MagicMock()
    pb_svc.list_playbooks.return_value = playbooks or []
    pb_svc.get_by_id.return_value = playbook
    task_svc = MagicMock()
    task_svc.create.return_value = task

    def _get(name, cls=None, default=None):
        return {
            "serve_workspace_service": ws_svc,
            "serve_playbook_service": pb_svc,
            "serve_task_service": task_svc,
        }.get(name, default)

    app.get_component.side_effect = _get
    return app


def _task(id_=101):
    return MagicMock(id=id_)


def _playbook(id_=5, name="容量巡检"):
    # MagicMock(name=...) 是特殊参数(设置 mock 名称而非 name 属性),须显式赋值
    pb = MagicMock(id=id_, is_active=True)
    pb.name = name
    return pb


def test_explicit_playbook_creates_in_session_task():
    app = _make_app(playbook=_playbook(), task=_task())
    ext = {"workspace_id": 1, "playbook_id": 5, "user_id": 9}

    result = route_scene_execution(ext, "跑一下容量巡检", "conv-1", app)

    assert result == {"task_id": 101, "playbook_id": 5, "playbook_name": "容量巡检"}
    assert ext["task_id"] == 101
    assert ext["initiator"] == "page"
    create_req = app.get_component("serve_task_service").create.call_args[0][0]
    assert create_req.workspace_id == 1
    assert create_req.playbook_id == 5
    assert create_req.triggered_by == "page"
    assert create_req.conv_session_id == "conv-1"  # 复用当前会话:同步执行
    assert create_req.context == {"execution_mode": "in_session"}
    assert create_req.status == "running"


def test_name_match_creates_task():
    pb = _playbook(id_=7, name="SRE 容量巡检")
    app = _make_app(playbooks=[pb], playbook=pb, task=_task(202))
    ext = {"workspace_id": 1}

    result = route_scene_execution(ext, "帮我跑一下 SRE 容量巡检", "c", app)

    assert result == {"task_id": 202, "playbook_id": 7, "playbook_name": "SRE 容量巡检"}
    assert ext["task_id"] == 202


def test_longest_name_match_wins():
    pb_short = _playbook(id_=1, name="巡检")
    pb_long = _playbook(id_=2, name="SRE 容量巡检")
    app = _make_app(playbooks=[pb_short, pb_long], playbook=pb_long, task=_task(303))

    route_scene_execution({"workspace_id": 1}, "执行 SRE 容量巡检", "c", app)

    create_req = app.get_component("serve_task_service").create.call_args[0][0]
    assert create_req.playbook_id == 2


def test_non_page_initiator_skipped():
    app = _make_app(playbook=_playbook(), task=_task())
    ext = {"workspace_id": 1, "initiator": "api", "playbook_id": 5}

    assert route_scene_execution(ext, "x", "c", app) is None
    assert "task_id" not in ext


def test_existing_task_id_skipped():
    app = _make_app(playbook=_playbook(), task=_task())
    ext = {"workspace_id": 1, "task_id": 3, "playbook_id": 5}

    assert route_scene_execution(ext, "x", "c", app) is None


def test_conversation_already_bound_skipped():
    app = _make_app(
        conv_link={"workspace_id": 1, "task_id": 9},
        playbook=_playbook(), task=_task(),
    )
    ext = {"workspace_id": 1, "playbook_id": 5}

    assert route_scene_execution(ext, "x", "c", app) is None
    assert "task_id" not in ext


def test_no_match_returns_none():
    app = _make_app(playbooks=[_playbook()], task=_task())

    assert route_scene_execution({"workspace_id": 1}, "随便聊聊", "c", app) is None


def test_inactive_playbook_skipped():
    pb = MagicMock(id=5, name="容量巡检", is_active=False)
    app = _make_app(playbook=pb, task=_task())

    assert route_scene_execution({"workspace_id": 1, "playbook_id": 5}, "x", "c", app) is None


def test_exception_graceful():
    app = MagicMock()
    app.get_component.side_effect = RuntimeError("boom")
    ext = {"workspace_id": 1}

    assert route_scene_execution(ext, "x", "c", app) is None
    assert "task_id" not in ext
