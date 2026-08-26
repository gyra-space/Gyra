"""AppCardService.create 名称幂等唯一 的测试。

同 workspace 下同名重复上传应执行幂等更新而非新建:
- 第二次 create 返回同一 id, 不产生重复记录
- code/config/queries 更新为新值, current_version +1 且新增版本快照
- 不同 workspace 的同名卡片互不干扰
- 已归档(archived)的同名卡片不参与去重, 可重新创建
"""
from unittest.mock import MagicMock

import pytest

from gyra.storage.metadata import db
from gyra_serve.app_card.api.schemas import AppCardCreateRequest, AppCardListFilter
from gyra_serve.app_card.models.models import AppCardDao, AppCardEntity, AppCardVersionEntity
from gyra_serve.app_card.service.service import AppCardService


@pytest.fixture
def app_card_service(tmp_path):
    db.init_db(f"sqlite:///{tmp_path / 't.db'}")
    db.create_all()
    svc = AppCardService(MagicMock(), MagicMock())
    svc._dao = AppCardDao()
    return svc


def _req(workspace_id, name, code, **kw):
    return AppCardCreateRequest(
        workspace_id=workspace_id,
        name=name,
        code=code,
        description=kw.get("description"),
        kind=kw.get("kind", "dashboard"),
        config=kw.get("config", {}),
        queries=kw.get("queries", []),
        source_task_id=kw.get("source_task_id"),
        created_by=kw.get("created_by", "tester"),
    )


def _count_cards(workspace_id):
    return len(AppCardDao().list_by_workspace(AppCardListFilter(workspace_id=workspace_id, limit=100)))


def _version_count():
    session = AppCardDao().get_raw_session()
    try:
        return session.query(AppCardVersionEntity).count()
    finally:
        session.close()


def test_same_name_recreate_updates_in_place(app_card_service):
    first = app_card_service.create(_req(1, "销售看板", "<div>v1</div>", description="版本一"))
    second = app_card_service.create(_req(1, "销售看板", "<div>v2</div>", description="版本二"))

    assert first.id == second.id          # 同名不新建, 返回同一卡片
    assert _count_cards(1) == 1           # 无重复记录
    assert second.current_version == 2
    assert second.code == "<div>v2</div>"
    assert second.description == "版本二"


def test_same_name_in_different_workspaces_both_created(app_card_service):
    a = app_card_service.create(_req(1, "销售看板", "<div>A</div>"))
    b = app_card_service.create(_req(2, "销售看板", "<div>B</div>"))

    assert a.id != b.id
    assert _count_cards(1) == 1
    assert _count_cards(2) == 1


def test_recreate_adds_version_snapshot(app_card_service):
    app_card_service.create(_req(1, "看板", "<div>v1</div>"))
    app_card_service.create(_req(1, "看板", "<div>v2</div>"))
    app_card_service.create(_req(1, "看板", "<div>v3</div>"))

    assert _version_count() == 3  # 每次上传一个版本快照, 不会因重复上传翻倍
    assert _count_cards(1) == 1


def test_archived_same_name_can_be_recreated(app_card_service):
    card = app_card_service.create(_req(1, "旧卡片", "<div>old</div>"))

    session = AppCardDao().get_raw_session()
    try:
        e = session.query(AppCardEntity).filter(AppCardEntity.id == card.id).first()
        e.status = "archived"
        session.commit()
    finally:
        session.close()

    new_card = app_card_service.create(_req(1, "旧卡片", "<div>new</div>"))
    assert new_card.id != card.id
    assert _count_cards(1) == 1  # 归档的不参与去重, 仅剩新的 1 条非归档
