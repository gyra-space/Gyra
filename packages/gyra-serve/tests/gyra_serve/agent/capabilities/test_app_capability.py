"""RFC-006 Stage 4: app capability 迁移测试。"""

from types import SimpleNamespace

import pytest

from gyra.core.interface.resource.bundle import CacheScope, Slot
from gyra_serve.agent.capabilities.app import (
    AppCapability,
    build_capability,
)
from gyra.agent.capabilities.facade import ResourceFacade


# =========================================================================== #
# RFC-006 Stage 4:AppCapability 自管理对象模型(走 facade.assemble 全链)
# =========================================================================== #
def test_app_capability_from_config():
    """factory 从 config dict 产 AppCapability(无 I/O,无旧 Resource 实例)。"""
    cap = build_capability(
        {"app_name": "DB 诊断", "app_code": "db-agent", "app_desc": "数据库诊断助手"},
        system_app=None,
    )
    assert isinstance(cap, AppCapability)
    assert cap.capability_id == "app"
    assert cap.executor_id == "app:db-agent"  # 多 app 唯一


def test_app_capability_declare_renders_description():
    """AppCapability.declare 产 app 描述 SYSTEM。"""
    cap = build_capability(
        {"app_name": "DB 诊断", "app_code": "db-agent", "app_desc": "数据库诊断助手"},
    )
    contribs = cap.declare()
    assert len(contribs) == 1
    c = contribs[0]
    assert c.slot == Slot.SYSTEM
    assert c.capability_id == "app"
    assert c.cache_scope == CacheScope.USER
    assert "DB 诊断" in c.content
    assert "db-agent" in c.content
    assert "数据库诊断助手" in c.content


def test_app_capability_declare_empty_when_no_name():
    assert AppCapability(app_name="", app_code="", description="").declare() == []


async def test_assemble_declares_app_via_capability_pack():
    """Agent 持有 CapabilityPack(对象)→ facade.assemble 经适配器产 app 描述进 system。

    验证对象模型自洽:factory→对象→pack→facade declare 适配器→system,无需 config
    再流到 facade(config 在更上游构造期已被消费成对象)。
    """
    from gyra.agent.capabilities.facade import _iter_sub_resources
    from gyra.core.interface.resource.capability import CapabilityPack

    facade = ResourceFacade()
    cap = AppCapability(app_name="Canvas", app_code="canvas", description="画布助手")
    pack = CapabilityPack([cap])
    # _iter_sub_resources 能把 CapabilityPack 当 pack 遍历
    assert _iter_sub_resources(pack) == [cap]

    snap = await facade.assemble(
        agent_id="a1", conv_id="c1", resource_root=pack,
        identity="id", control_block="ctl",
    )
    texts = [b.text for b in snap.frozen.system]
    assert any("Canvas" in t and "画布助手" in t for t in texts)


async def test_app_capability_prepare_release_and_execute():
    from gyra.core.interface.resource.executor import (
        ExecutorCall,
        ExecutorStatus,
        ReleaseReason,
    )

    cap = AppCapability(app_name="Z", app_code="z", description="")
    assert cap._status == ExecutorStatus.UNINITIALIZED
    await cap.prepare()
    assert cap._status == ExecutorStatus.READY
    await cap.release(ReleaseReason.SESSION_END)
    assert cap._status == ExecutorStatus.RELEASED
    # execute 不接管 agent_start(保持 AgentAction)
    with pytest.raises(NotImplementedError):
        await cap.execute(
            ExecutorCall(executor_id="app:z", capability_id="app", tool_name="agent_start", args={})
        )


# =========================================================================== #
# Phase D: AppCapability 执行面(start_app / async_execute / get_multimedia_config)
# =========================================================================== #
def _fake_app_manager(reply_content="子 agent 回复"):
    fake_agent = SimpleNamespace(
        sandbox_manager=None,
        generate_reply=lambda received_message, sender: None,
    )

    async def _generate_reply(received_message, sender):
        fake_agent.last_message = received_message
        fake_agent.last_sender = sender
        return SimpleNamespace(content=reply_content)

    fake_agent.generate_reply = _generate_reply
    mgr = SimpleNamespace()
    mgr.get_app = lambda code: _async(
        SimpleNamespace(app_code=code, app_name="子应用", language="zh")
    )
    mgr.create_agent_by_app_code = lambda gpts_app, conv_uid=None, context=None: _async(
        fake_agent
    )
    return mgr, fake_agent


def _async(value):
    import asyncio

    fut = asyncio.Future()
    fut.set_result(value)
    return fut


async def test_start_app_delegates_and_returns_reply(monkeypatch):
    import gyra_serve.agent.agents.app_agent_manage as aam

    mgr, fake_agent = _fake_app_manager()
    monkeypatch.setattr(aam, "get_app_manager", lambda: mgr)

    cap = AppCapability.from_config(
        {"app_code": "sub-app", "app_name": "子应用", "app_desc": "d"}
    )
    reply = await cap.start_app("帮我查一下", sender=None)
    assert reply.content == "子 agent 回复"
    assert fake_agent.last_message.content == "帮我查一下"
    assert fake_agent.last_message.context["conv_uid"]


async def test_start_app_tolerates_none_sender(monkeypatch):
    """sender=None(cron 注入路径)不透传上下文/沙箱,不报错。"""
    import gyra_serve.agent.agents.app_agent_manage as aam

    mgr, _ = _fake_app_manager()
    monkeypatch.setattr(aam, "get_app_manager", lambda: mgr)

    cap = AppCapability.from_config({"app_code": "sub-app", "app_name": "子应用"})
    reply = await cap.start_app("hi", sender=None, parent_depth=0)
    assert reply.content == "子 agent 回复"


async def test_async_execute_shim(monkeypatch):
    import gyra_serve.agent.agents.app_agent_manage as aam

    mgr, fake_agent = _fake_app_manager()
    monkeypatch.setattr(aam, "get_app_manager", lambda: mgr)

    cap = AppCapability.from_config({"app_code": "sub-app", "app_name": "子应用"})
    reply = await cap.async_execute(user_input="hi", parent_agent=None)
    assert reply.content == "子 agent 回复"
    assert fake_agent.last_sender is None


def test_get_multimedia_config_disabled(monkeypatch):
    from gyra_serve.building.app.service import service as app_service_mod

    monkeypatch.setattr(
        app_service_mod.Service,
        "get_instance",
        staticmethod(lambda app: SimpleNamespace(
            get_multimedia_agent_config=lambda code: {"enabled": False}
        )),
    )
    cap = AppCapability.from_config({"app_code": "sub-app", "app_name": "子应用"})
    assert cap.get_multimedia_config() is None


def test_get_multimedia_config_enabled_and_cached(monkeypatch):
    from gyra_serve.building.app.service import service as app_service_mod

    calls = []

    def _get_cfg(code):
        calls.append(code)
        return {"enabled": True, "name": "mm"}

    monkeypatch.setattr(
        app_service_mod.Service,
        "get_instance",
        staticmethod(lambda app: SimpleNamespace(get_multimedia_agent_config=_get_cfg)),
    )
    cap = AppCapability.from_config({"app_code": "sub-app", "app_name": "子应用"})
    assert cap.get_multimedia_config() == {"enabled": True, "name": "mm"}
    assert cap.get_multimedia_config() == {"enabled": True, "name": "mm"}
    assert calls == ["sub-app"]  # 第二次走缓存
