import os
import tempfile

import pytest
from unittest.mock import MagicMock
from gyra_serve.skill.config import ServeConfig
from gyra_serve.skill.service.service import Service
from gyra_serve.skill.api.schemas import SkillRequest

@pytest.fixture
def mock_dao():
    return MagicMock()

@pytest.fixture
def service(mock_dao):
    system_app = MagicMock()
    # A real config is required: Service.create/update build the default path
    # with os.path.join, and a MagicMock there raises TypeError instead.
    config = ServeConfig(project_skill_dir=tempfile.mkdtemp())
    return Service(system_app, config, dao=mock_dao)

def test_create(service, mock_dao):
    # No pre-existing row -> must take the create path. Note that a MagicMock
    # would be truthy here and silently send create() down the update branch.
    mock_dao.get_one.return_value = None

    req = SkillRequest(name="test", description="desc", type="type")
    service.create(req)
    mock_dao.create.assert_called_once()

    # Check that skill_code was generated
    call_args = mock_dao.create.call_args[0][0]
    assert call_args.skill_code is not None

    # Check that the default path was derived from the project skill dir
    assert call_args.path == os.path.join(
        service.config.get_project_skill_dir(), call_args.skill_code
    )

def test_create_existing_skill_updates(service, mock_dao):
    """An existing skill must be updated in place, never duplicated."""
    mock_dao.get_one.return_value = SkillRequest(
        skill_code="123", name="old-name", description="desc", type="type"
    )

    req = SkillRequest(skill_code="123", name="new-name", description="desc", type="type")
    service.create(req)

    mock_dao.create.assert_not_called()
    mock_dao.update.assert_called_once()

def test_update(service, mock_dao):
    mock_dao.get_one.return_value = None

    req = SkillRequest(skill_code="123", name="test_updated", description="desc", type="type")
    service.update(req)

    mock_dao.update.assert_called_once()
    assert mock_dao.update.call_args[0][0] == {"skill_code": "123"}

    # dao.update is called as update(query_request, update_request=request), so
    # the request lands in kwargs, not as a second positional argument.
    update_data = mock_dao.update.call_args[1]["update_request"]
    assert update_data.name == "test_updated"
    assert update_data.path == os.path.join(
        service.config.get_project_skill_dir(), "123"
    )

def test_delete(service, mock_dao):
    req = SkillRequest(skill_code="123", name="test", description="desc", type="type")
    service.delete(req)
    mock_dao.delete.assert_called_once_with(req)

def test_get(service, mock_dao):
    req = SkillRequest(skill_code="123", name="test", description="desc", type="type")
    service.get(req)
    mock_dao.get_one.assert_called_once_with(req)
