"""AppCardService.delete 的验证测试。

确认删除链路真实生效:
- 开发者本人删除成功后, 该 workspace 列表不再包含该卡片
- 非开发者的删除被权限拒绝(PermissionError)
"""
from unittest.mock import MagicMock

import pytest

from gyra.storage.metadata import db
from gyra_serve.app_card.api.schemas import AppCardCreateRequest, AppCardListFilter
from gyra_serve.app_card.models.models import AppCardDao
from gyra_serve.app_card.service.service import AppCardService
from gyra_serve.utils.auth import UserRequest


@pytest.fixture
def app_card_service(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 't.db'}")
    db.create_all()
    svc = AppCardService(MagicMock(), MagicMock())
    svc._dao = AppCardDao()
    return svc


def _req(workspace_id, name, code):
    return AppCardCreateRequest(
        workspace_id=workspace_id,
        name=name,
        code=code,
        created_by="tester",
    )


def _user(name="tester", role="normal"):
    return UserRequest(user_id="0001", user_no=name, user_name=name, role=role)


def test_delete_removes_card_from_workspace(app_card_service):
    card = app_card_service.create(_req(1, "销售看板", "<div>v1</div>"))

    ok = app_card_service.delete(card.id, 1, _user("tester"))
    assert ok is True
    listed = app_card_service.list_by_workspace(AppCardListFilter(workspace_id=1, limit=100), _user("tester"))
    assert len(listed) == 0


def test_delete_rejects_non_developer(app_card_service):
    card = app_card_service.create(_req(1, "销售看板", "<div>v1</div>"))

    with pytest.raises(PermissionError):
        app_card_service.delete(card.id, 1, _user("stranger"))


def test_delete_returns_false_for_missing_card(app_card_service):
    assert app_card_service.delete(9999, 1, _user("tester")) is False
