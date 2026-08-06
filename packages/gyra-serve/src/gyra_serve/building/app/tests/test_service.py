import pytest

from gyra.component import SystemApp
from gyra.storage.metadata import db
from gyra_serve.building.app.api.schemas import ServeRequest
from gyra_serve.core.tests.conftest import (  # noqa: F401
    asystem_app,
    client,
    system_app,
)

from ..service.service import Service


@pytest.fixture(autouse=True)
def setup_and_teardown():
    db.init_db("sqlite:///:memory:")
    db.create_all()
    yield


@pytest.fixture
def service(system_app: SystemApp):
    instance = Service(system_app)
    instance.init_app(system_app)
    return instance


@pytest.fixture
def default_entity_dict():
    # TODO: build your default entity dict
    return {}


@pytest.mark.parametrize(
    "system_app",
    [{"app_config": {"DEBUG": True, "gyra.serve.test_key": "hello"}}],
    indirect=True,
)
def test_config_exists(service: Service):
    system_app = service._system_app
    assert system_app.config.get("DEBUG") is True
    assert system_app.config.get("gyra.serve.test_key") == "hello"
    assert service.config is not None


def test_service_create(service: Service, default_entity_dict):
    # TODO: implement your test case
    # eg. entity: ServerResponse = service.create(ServeRequest(**default_entity_dict))
    # ...
    pass


def test_service_update(service: Service, default_entity_dict):
    # TODO: implement your test case
    pass


def test_service_get(service: Service, default_entity_dict):
    # TODO: implement your test case
    pass


def test_service_delete(service: Service, default_entity_dict):
    # TODO: implement your test case
    pass


def test_service_get_list(service: Service):
    # TODO: implement your test case
    pass


def test_service_get_list_by_page(service: Service):
    # TODO: implement your test case
    pass


@pytest.mark.asyncio
async def test_get_and_save_multimedia_agent_config(service: Service):
    """测试 get/save_multimedia_agent_config 读写 ext_config.multimedia_agent。"""
    # 1. 创建一个测试 app
    req = ServeRequest(
        app_code="test-multimedia-agent-app",
        app_name="测试多媒体 Agent 应用",
        app_describe="多媒体 Agent 配置测试",
        team_mode="single_agent",
    )
    entity = service.create(req)
    assert entity is not None
    assert entity.app_code == "test-multimedia-agent-app"

    # 2. 首次读取（未配置应返回默认配置，enabled=False）
    result = service.get_multimedia_agent_config("test-multimedia-agent-app")
    assert isinstance(result, dict)
    assert result.get("enabled") is False
    assert result.get("name") == "multimedia_agent"  # 默认值
    assert result.get("capability_image") is True
    assert result.get("capability_video") is True

    # 3. 写入自定义配置
    test_config = {
        "enabled": True,
        "name": "my-image-generator",
        "description": "我的图片生成 Agent",
        "capability_image": True,
        "capability_video": False,
        "default_image_model": "dall-e-3",
        "default_image_size": "1024x1792",
        "style_prompt": "复古胶片风格",
        "scene_prompt": "居中构图",
        "negative_prompt": "模糊, 低质量",
        "async_default": False,
        "timeout": 120,
        "fixed_params": {"quality": "hd", "n": 1},
    }
    saved = await service.save_multimedia_agent_config(
        "test-multimedia-agent-app", test_config
    )
    assert saved is not None
    assert saved.get("enabled") is True
    assert saved.get("name") == "my-image-generator"
    assert saved.get("capability_video") is False
    assert saved.get("default_image_model") == "dall-e-3"
    assert saved.get("fixed_params") == {"quality": "hd", "n": 1}

    # 4. 再次读取应匹配保存结果
    result2 = service.get_multimedia_agent_config("test-multimedia-agent-app")
    assert result2 == saved
    assert result2.get("enabled") is True
    assert result2.get("name") == "my-image-generator"


# Add more test cases according to your own logic