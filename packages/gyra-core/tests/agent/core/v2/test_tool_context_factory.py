"""ToolContextFactory 测试(Phase D:capability_pack 驱动)。"""
from gyra.agent.core.v2.tool_context_factory import ToolContextFactory
from gyra.agent.core.v2.tool_call_types import V2ToolCall


class FakeSandboxManager:
    @property
    def client(self):
        return "fake_sandbox_client"


class FakeCapabilityPack:
    """按 capability_id 前缀过滤的 fake pack。"""

    def __init__(self, caps=()):
        self._caps = list(caps)

    def get_all(self, prefix):
        return [c for c in self._caps if c.capability_id.startswith(prefix)]

    def get(self, prefix):
        caps = self.get_all(prefix)
        return caps[0] if caps else None


class FakeDBCapability:
    capability_id = "db:1"


class FakeKnowledgeCapability:
    capability_id = "knowledge"


class FakeAppCapability:
    capability_id = "app"


class FakeMultimediaAppCapability:
    """模拟带 app_code 的多媒体 AppCapability：按 app_code 返回各自配置。"""

    capability_id = "app"

    def __init__(self, app_code, app_name, app_desc="", multimedia_cfg=None):
        self.app_code = app_code
        self.app_name = app_name
        self.app_desc = app_desc
        self._multimedia_cfg = multimedia_cfg

    def get_multimedia_config(self):
        return self._multimedia_cfg


def _make_factory(capability_pack=None, sandbox_manager=None):
    return ToolContextFactory(
        agent_id="agent-1",
        conv_id="conv-1",
        user_id="user-1",
        scene="data_analyst",
        scenario_id="wm-sales",
        language="zh",
        capability_pack=capability_pack,
        sandbox_manager=sandbox_manager,
        skill_dir="/skills",
        available_skills={"sql_review": "/skills/sql_review"},
    )


def test_basic_context_fields():
    factory = _make_factory()
    tc = V2ToolCall(name="read_file", args={})
    ctx = factory.build(tc, tool=None)
    assert ctx.agent_id == "agent-1"
    assert ctx.conversation_id == "conv-1"
    assert ctx.user_id == "user-1"
    assert ctx.scene == "data_analyst"
    assert ctx.scenario_id == "wm-sales"
    assert ctx.language == "zh"
    assert ctx.skill_dir == "/skills"
    assert ctx.available_skills["sql_review"] == "/skills/sql_review"


def test_sandbox_client_injected():
    factory = _make_factory(sandbox_manager=FakeSandboxManager())
    tc = V2ToolCall(name="bash", args={})
    ctx = factory.build(tc, tool=None)
    assert ctx.get_resource("sandbox_client") == "fake_sandbox_client"


def test_db_resource_injected_for_db_tool():
    db = FakeDBCapability()
    factory = _make_factory(capability_pack=FakeCapabilityPack([db]))
    tc = V2ToolCall(name="execute_sql", args={"sql": "SELECT 1"})
    ctx = factory.build(tc, tool=None)
    assert ctx.get_resource("db_resource") is db


def test_knowledge_retriever_injected():
    retriever = FakeKnowledgeCapability()
    factory = _make_factory(capability_pack=FakeCapabilityPack([retriever]))
    tc = V2ToolCall(name="KnowledgeSearch", args={"query": "test"})
    ctx = factory.build(tc, tool=None)
    assert ctx.get_resource("knowledge_retriever") is retriever


def test_app_resource_injected_for_agent_start():
    app = FakeAppCapability()
    factory = _make_factory(capability_pack=FakeCapabilityPack([app]))
    tc = V2ToolCall(name="AgentStart", args={})
    ctx = factory.build(tc, tool=None)
    assert ctx.get_resource("app_resource") is app


def test_no_resource_injected_for_unrelated_tool():
    factory = _make_factory(
        capability_pack=FakeCapabilityPack(
            [FakeDBCapability(), FakeKnowledgeCapability()]
        )
    )
    tc = V2ToolCall(name="read_file", args={})
    ctx = factory.build(tc, tool=None)
    assert ctx.get_resource("db_resource") is None
    assert ctx.get_resource("knowledge_retriever") is None


# ---------------------------------------------------------------------------
# 多媒体子 Agent 按 app_code 寻址（多实例各自独立）
# ---------------------------------------------------------------------------


def _multimedia_factory():
    return ToolContextFactory(
        agent_id="agent-1",
        conv_id="conv-1",
        capability_pack=FakeCapabilityPack(
            [
                FakeMultimediaAppCapability(
                    app_code="app-cartoon",
                    app_name="卡通风格",
                    app_desc="生成卡通图片",
                    multimedia_cfg={
                        "name": "卡通风格",
                        "default_image_model": "img-cartoon",
                        "default_video_model": "vid-cartoon",
                        "enabled": True,
                    },
                ),
                FakeMultimediaAppCapability(
                    app_code="app-real",
                    app_name="真人风格",
                    app_desc="生成写实图片",
                    multimedia_cfg={
                        "name": "真人风格",
                        "default_image_model": "img-real",
                        "default_video_model": "vid-real",
                        "enabled": True,
                    },
                ),
            ]
        ),
    )


def test_resolve_multimedia_by_app_code():
    """按 app_code 解析到对应多媒体 app 的配置（多实例互不覆盖）。"""
    factory = _multimedia_factory()
    cfg_a, code_a, name_a, desc_a = factory._resolve_multimedia("app-cartoon")
    assert cfg_a["default_image_model"] == "img-cartoon"
    assert code_a == "app-cartoon"
    assert name_a == "卡通风格"
    assert desc_a == "生成卡通图片"

    cfg_b, code_b, name_b, _ = factory._resolve_multimedia("app-real")
    assert cfg_b["default_image_model"] == "img-real"
    assert code_b == "app-real"
    assert name_b == "真人风格"

    # 未命中 app_code → 返回 None
    assert factory._resolve_multimedia("unknown-app")[0] is None


def test_resolve_multimedia_by_app_name():
    """也支持按 app_name 匹配（与 CoreV1 子 agent 委派一致）。"""
    factory = _multimedia_factory()
    cfg, code, name, _ = factory._resolve_multimedia("卡通风格")
    assert cfg is not None
    assert code == "app-cartoon"


def test_build_delegate_by_app_code_constructs_independent_instances():
    """按 app_code 动态构造绑定各自配置的多媒体 agent 委派协程。"""
    from gyra.agent.multimedia import MultimediaAgent

    factory = _multimedia_factory()
    delegate_a = factory._build_subagent_delegate_factory(
        subagent_name="app-cartoon", task="一只猫", conv_id="c1"
    )
    delegate_b = factory._build_subagent_delegate_factory(
        subagent_name="app-real", task="一只猫", conv_id="c1"
    )
    # 两个 app_code 都能构造出多媒体委派（互不湮灭）
    assert delegate_a is not None
    assert delegate_b is not None
    assert delegate_a is not delegate_b


def test_build_delegate_empty_name_returns_none():
    factory = _multimedia_factory()
    assert factory._build_subagent_delegate_factory(subagent_name="") is None


def test_build_delegate_unknown_returns_none_for_non_multimedia():
    """非多媒体 app（无 get_multimedia_config）→ 无委派，回退普通子 agent。"""
    factory = _make_factory(capability_pack=FakeCapabilityPack([FakeAppCapability()]))
    assert (
        factory._build_subagent_delegate_factory(subagent_name="some-app", task="t")
        is None
    )


def test_build_delegate_resolver_injection():
    """注入 multimedia_resolver 时优先按 app_code 解析。"""
    resolver_calls = []

    def resolver(app_code):
        resolver_calls.append(app_code)
        if app_code == "app-x":
            return {"name": "X", "default_image_model": "img-x", "enabled": True}
        return None

    factory = ToolContextFactory(
        agent_id="a1",
        conv_id="c1",
        capability_pack=FakeCapabilityPack([FakeAppCapability()]),
        multimedia_resolver=resolver,
    )
    delegate = factory._build_subagent_delegate_factory(
        subagent_name="app-x", task="t", conv_id="c1"
    )
    assert delegate is not None
    assert resolver_calls == ["app-x"]
