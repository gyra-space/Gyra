"""build_multimedia_delegate 共享解析与 v1 spawn 接线测试。

覆盖:
- resolve_multimedia_config 按 app_code/app_name 解析(与 V2 factory 同逻辑)
- build_multimedia_delegate 注入 main_conv_id(Path A 产物聚合的前提)
- SpawnAgentTaskTool 在 v1 路径(context 即 agent 本身,无 get_resource)
  能构建 Path A delegate;非多媒体 app 回退 None(Path B)
- MultimediaAgent.correctness_check 消费结构化失败标记
"""

from types import SimpleNamespace

import pytest

from gyra.agent.multimedia import MultimediaAgent, MultimediaAgentConfig
from gyra.agent.multimedia.delegate import (
    build_multimedia_delegate,
    resolve_multimedia_config,
)


class FakeMultimediaAppCapability:
    def __init__(self, app_code, app_name, app_desc, multimedia_cfg):
        self.app_code = app_code
        self.app_name = app_name
        self.app_desc = app_desc
        self._cfg = multimedia_cfg

    def get_multimedia_config(self):
        return self._cfg


class FakeAppCapability:
    app_code = "app-plain"
    app_name = "普通应用"
    app_desc = ""


class FakeCapabilityPack:
    def __init__(self, caps):
        self._caps = caps

    def get_all(self, kind):
        return list(self._caps) if kind == "app" else []


def _pack():
    return FakeCapabilityPack(
        [
            FakeMultimediaAppCapability(
                app_code="app-cartoon",
                app_name="卡通风格",
                app_desc="生成卡通图片",
                multimedia_cfg={
                    "name": "卡通风格",
                    "default_image_model": "img-cartoon",
                    "enabled": True,
                },
            ),
        ]
    )


def test_resolve_by_app_code_and_name():
    cfg, code, name, desc = resolve_multimedia_config(
        "app-cartoon", capability_pack=_pack()
    )
    assert cfg["default_image_model"] == "img-cartoon"
    assert code == "app-cartoon"

    cfg2, code2, _, _ = resolve_multimedia_config("卡通风格", capability_pack=_pack())
    assert cfg2 is not None and code2 == "app-cartoon"

    assert resolve_multimedia_config("unknown", capability_pack=_pack())[0] is None


def test_build_delegate_injects_main_conv_id(monkeypatch):
    """Path A 在主会话直跑:spawn 的 conv_id 即主会话 id,必须注入 executor,
    否则轮询任务 context 缺 main_conv_id,主会话产物聚合查不到。"""
    captured = {}
    orig = MultimediaAgent.to_async_delegate

    def _spy(self, afs=None, conv_id=""):
        captured["inst"] = self
        return orig(self, afs=afs, conv_id=conv_id)

    monkeypatch.setattr(MultimediaAgent, "to_async_delegate", _spy)
    del_fn = build_multimedia_delegate(
        "app-cartoon", capability_pack=_pack(), conv_id="main-1"
    )
    assert del_fn is not None
    assert captured["inst"].executor.main_conv_id == "main-1"


def test_build_delegate_non_multimedia_returns_none():
    """普通 app(无多媒体配置)→ None,调用方回退 Path B。"""
    pack = FakeCapabilityPack([FakeAppCapability()])
    assert build_multimedia_delegate("app-plain", capability_pack=pack) is None


def test_build_delegate_empty_name_returns_none():
    assert build_multimedia_delegate("") is None


# ---------------------------------------------------------------------------
# v1 路径:SpawnAgentTaskTool context 即 agent 本身
# ---------------------------------------------------------------------------


class _FakeManager:
    def __init__(self):
        self.spawned = None

    def find_in_flight(self, **kwargs):
        return None

    def find_completed_equivalent(self, **kwargs):
        return None

    async def spawn(self, spec):
        self.spawned = spec
        return spec.task_id


class _FakeV1Agent:
    """v1 tool_action 路径的 context:agent 本身(无 get_resource)。"""

    def __init__(self, pack):
        self.agent_context = SimpleNamespace(conv_id="main-conv-1")
        self.capability_pack = pack
        self.ext_config = None


async def test_spawn_tool_v1_builds_path_a_delegate():
    import inspect

    from gyra.agent.tools.builtin.async_task.async_task_tools import (
        SpawnAgentTaskTool,
    )

    manager = _FakeManager()
    tool = SpawnAgentTaskTool(async_task_manager=manager)
    result = await tool.execute(
        {"agent_name": "app-cartoon", "task": "一只猫", "wait_for_result": False},
        context=_FakeV1Agent(_pack()),
    )
    assert result.success
    spec = manager.spawned
    assert spec is not None
    # Path A:delegate 是零参 async callable(_run_task 直接 await)
    assert spec.delegate is not None
    assert inspect.iscoroutinefunction(spec.delegate)
    assert spec.conv_id == "main-conv-1"


async def test_spawn_tool_v1_non_multimedia_falls_back_path_b():
    from gyra.agent.tools.builtin.async_task.async_task_tools import (
        SpawnAgentTaskTool,
    )

    manager = _FakeManager()
    tool = SpawnAgentTaskTool(async_task_manager=manager)
    result = await tool.execute(
        {"agent_name": "app-plain", "task": "做个分析", "wait_for_result": False},
        context=_FakeV1Agent(FakeCapabilityPack([FakeAppCapability()])),
    )
    assert result.success
    # 非多媒体 app:无 delegate,回退 subagent_manager(Path B)
    assert manager.spawned.delegate is None


# ---------------------------------------------------------------------------
# 结构化失败标记:correctness_check 消费 _gen_failure
# ---------------------------------------------------------------------------


async def test_correctness_check_consumes_gen_failure():
    agent = MultimediaAgent(config=MultimediaAgentConfig(name="mm"))
    agent._gen_failure = "provider 403"
    ok, reason = await agent.correctness_check(SimpleNamespace())
    assert ok is False
    assert reason == "provider 403"
    # 消费后清空,不影响后续成功轮次
    assert agent._gen_failure is None
    ok2, reason2 = await agent.correctness_check(SimpleNamespace())
    assert ok2 is True
    assert reason2 is None
