"""Tests for TaskDao.list_by_filter own_and_public_only visibility (simple mode).

简单页面模式可见性规则:
- 自己提交的对话任务(triggered_by=page/manual 且 created_by=本人)可见;
- 空间公共任务(订阅/触发源产生的 timer/webhook/alert 等任务)可见;
- 别人的对话任务不可见。
"""
import pytest

from gyra.storage.metadata import db
from gyra_serve.task.api.schemas import TaskListFilter, TaskRequest
from gyra_serve.task.config import ServeConfig
from gyra_serve.task.models.models import TaskDao
from gyra_serve.task.service.service import TaskService


@pytest.fixture
def service(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(f"sqlite:///{db_path}")
    db.create_all()
    return TaskService(None, ServeConfig(), TaskDao())


ME = 101
OTHER = 202


def _create(service, *, triggered_by="manual", created_by=None, title="t"):
    return service.create(TaskRequest(
        workspace_id=1,
        title=title,
        triggered_by=triggered_by,
        created_by_user_id=created_by,
    ))


def _list(**kwargs):
    return TaskDao().list_by_filter(TaskListFilter(workspace_id=1, limit=100, **kwargs))


def test_hides_others_dialog_tasks(service):
    mine_page = _create(service, triggered_by="page", created_by=ME, title="mine page")
    mine_manual = _create(service, triggered_by="manual", created_by=ME, title="mine manual")
    other_page = _create(service, triggered_by="page", created_by=OTHER, title="other page")
    other_manual = _create(service, triggered_by="manual", created_by=OTHER, title="other manual")

    ids = {t.id for t in _list(own_and_public_only=True, user_id=ME)}
    assert mine_page.id in ids
    assert mine_manual.id in ids
    assert other_page.id not in ids
    assert other_manual.id not in ids


def test_shows_public_trigger_tasks(service):
    timer = _create(service, triggered_by="timer", title="timer")
    webhook = _create(service, triggered_by="webhook", title="webhook")
    alert = _create(service, triggered_by="alert", title="alert")

    ids = {t.id for t in _list(own_and_public_only=True, user_id=ME)}
    assert {timer.id, webhook.id, alert.id} <= ids


def test_without_user_id_keeps_public_only(service):
    timer = _create(service, triggered_by="timer", title="timer")
    mine_page = _create(service, triggered_by="page", created_by=ME, title="mine page")

    ids = {t.id for t in _list(own_and_public_only=True)}
    assert timer.id in ids
    assert mine_page.id not in ids


def test_default_filter_returns_all(service):
    other_page = _create(service, triggered_by="page", created_by=OTHER, title="other page")
    timer = _create(service, triggered_by="timer", title="timer")

    ids = {t.id for t in _list()}
    assert {other_page.id, timer.id} <= ids
