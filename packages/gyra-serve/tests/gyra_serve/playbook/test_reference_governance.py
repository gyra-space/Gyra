"""引用完整性治理:剧本 = 空间池子集(空间=注册/治理池,剧本=选配/编排子集)。

覆盖 PlaybookService.validate_references 与 create/update 的引用门禁:
- 命中空间池 -> 通过
- 未命中但全局可解析 -> warning(不阻断,兼容存量/seed)
- 全局确认不存在(skill/mcp) -> error(阻断保存,防悬空引用)
"""
from unittest.mock import MagicMock

import pytest

from gyra_serve.playbook.api.schemas import PlaybookRequest
from gyra_serve.playbook.service.service import PlaybookService


def _make_app(pool_records=None, skill_lookup=None):
    """构造 system_app:workspace/skill service 按组件名分派。"""
    app = MagicMock()
    ws_svc = MagicMock()
    ws_svc.list_resources.return_value = pool_records or []
    skill_svc = MagicMock()
    if skill_lookup:
        skill_svc.get_by_skill_code.side_effect = lambda code: skill_lookup.get(code)

    def _get_component(name, cls=None, default=None):
        if name == "serve_workspace_service":
            return ws_svc
        if name == "serve_skill_service":
            return skill_svc
        return default

    app.get_component.side_effect = _get_component
    return app


def _service(app) -> PlaybookService:
    svc = PlaybookService(MagicMock(), MagicMock())
    svc._dao = MagicMock()
    svc._version_dao = MagicMock()
    svc._system_app = app
    return svc


def _decl(skills=None, resources=None) -> dict:
    return {
        "skills": skills or [],
        "context": {"assets_required": [], "resources": resources or []},
        "deliverables": [{"type": "report", "delivery": []}],
        "distill": {"forced": False},
    }


def test_pool_hit_passes():
    rec = MagicMock(type="skill", name="绑定技能", physical_ref="my_skill", is_active=True)
    svc = _service(_make_app(pool_records=[rec]))
    result = svc.validate_references(1, _decl(skills=["my_skill"]))
    assert result == {"errors": [], "warnings": []}


def test_unbound_but_existing_skill_warns():
    svc = _service(_make_app(pool_records=[], skill_lookup={"db_query_skill": True}))
    result = svc.validate_references(1, _decl(skills=["db_query_skill"]))
    assert result["errors"] == []
    assert any("db_query_skill" in w for w in result["warnings"])


def test_dangling_skill_blocks():
    svc = _service(_make_app(pool_records=[], skill_lookup={"ghost_skill": None}))
    result = svc.validate_references(1, _decl(skills=["ghost_skill"]))
    assert any("ghost_skill" in e for e in result["errors"])


def test_dangling_mcp_blocks():
    from unittest.mock import patch

    app = _make_app(pool_records=[])
    svc = _service(app)
    with patch(
        "gyra_serve.agent.resource.tool.mcp_collect.get_mcp_info", return_value=None
    ):
        result = svc.validate_references(
            1, _decl(resources=[{"type": "mcp", "ref": "ghost_mcp"}])
        )
    assert any("ghost_mcp" in e for e in result["errors"])


def test_resource_unbound_warns_not_blocks():
    """datasource 等类型无法低成本核验全局,未绑定时仅 warning。"""
    svc = _service(_make_app(pool_records=[]))
    result = svc.validate_references(
        1, _decl(resources=[{"type": "datasource", "ref": "prod_core_db"}])
    )
    assert result["errors"] == []
    assert any("prod_core_db" in w for w in result["warnings"])


def test_create_blocks_dangling_reference():
    svc = _service(_make_app(pool_records=[], skill_lookup={"ghost_skill": None}))
    with pytest.raises(ValueError, match="ghost_skill"):
        svc.create(PlaybookRequest(
            workspace_id=1, name="t", task_type="routine",
            declaration=_decl(skills=["ghost_skill"]),
        ))
    svc._dao.create.assert_not_called()


def test_create_allows_unbound_but_existing_skill():
    svc = _service(_make_app(pool_records=[], skill_lookup={"db_query_skill": True}))
    svc._dao.create.return_value = MagicMock(id=1)
    svc._version_dao.create_version.return_value = MagicMock()
    resp = svc.create(PlaybookRequest(
        workspace_id=1, name="t", task_type="routine",
        declaration=_decl(skills=["db_query_skill"]),
    ))
    assert resp.id == 1
