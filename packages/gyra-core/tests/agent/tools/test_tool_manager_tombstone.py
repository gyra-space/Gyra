"""ToolManager tombstone（显式解绑）机制测试。

覆盖场景：
1. parse_resource_tool_bindings 解析绑定/解绑混合清单
2. 旧数据兼容：持久化清单不含默认工具且无 tombstone → 默认工具恢复默认绑定
3. tombstone：显式解绑的默认工具保持未绑定，其余默认工具仍绑定
4. get_agent_config 对返回纯 List[str] 的旧回调保持向后兼容
"""
import json
from types import SimpleNamespace

import pytest

from gyra.agent.tools.tool_manager import (
    PersistedToolBindings,
    ToolBindingType,
    ToolManager,
    parse_resource_tool_bindings,
)
from gyra.agent.tools.registry import tool_registry


def _make_resource_entry(tool_id: str, unbound: bool = False) -> dict:
    value = {"tool_id": tool_id, "key": tool_id, "name": tool_id}
    if unbound:
        value["unbound"] = True
    return {"type": "tool(system)", "name": tool_id, "value": json.dumps(value)}


def _stub_registry_tools(monkeypatch, tool_ids):
    """用假的 tool 对象替换 registry 列表，仅需要 metadata.name。"""
    stubs = [SimpleNamespace(metadata=SimpleNamespace(name=tid)) for tid in tool_ids]
    monkeypatch.setattr(tool_registry, "list_all", lambda: stubs)


ALL_TOOL_IDS = [
    "ask_user",  # BUILTIN_CORE_TOOLS
    "Bash",
    "Read",
    "Write",
    "Edit",
    "deliver_file",
    "skill",  # BASIC_TOOLS
    "Grep",  # BUILTIN_OPTIONAL_TOOLS
]


# ========== parse_resource_tool_bindings ==========


def test_parse_empty_returns_none():
    assert parse_resource_tool_bindings(None) is None
    assert parse_resource_tool_bindings("") is None
    assert parse_resource_tool_bindings([]) is None
    assert parse_resource_tool_bindings("not-json") is None


def test_parse_bound_and_tombstone():
    raw = [
        _make_resource_entry("Grep"),
        _make_resource_entry("Read", unbound=True),
        {"type": "datasource", "name": "db", "value": "{}"},  # 无 tool_id，跳过
    ]
    result = parse_resource_tool_bindings(raw)
    assert result is not None
    assert result.bound_ids == ["Grep"]
    assert result.unbound_ids == ["Read"]


def test_parse_json_string_input():
    raw = json.dumps([_make_resource_entry("Bash")])
    result = parse_resource_tool_bindings(raw)
    assert result is not None
    assert result.bound_ids == ["Bash"]
    assert result.unbound_ids == []


def test_parse_only_tombstone_still_valid():
    """只有 tombstone 条目也算有效持久化数据（不能回落默认配置）。"""
    result = parse_resource_tool_bindings([_make_resource_entry("Read", unbound=True)])
    assert result is not None
    assert result.bound_ids == []
    assert result.unbound_ids == ["Read"]


# ========== _create_config_from_persisted ==========


def test_legacy_list_missing_defaults_restores_default_binding(monkeypatch):
    """旧数据场景：清单只有部分工具、无 tombstone → 默认工具按默认规则绑定。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()

    config = manager._create_config_from_persisted(
        "app1", "agent1", persisted_tool_ids=["Grep"]
    )

    # 默认工具恢复绑定
    for tid in ["ask_user", "Bash", "Read", "Write", "Edit"]:
        binding = config.bindings[tid]
        assert binding.is_bound is True, f"{tid} should be bound by default rule"
        assert binding.is_default is True
    # 显式在清单里的可选工具绑定
    assert config.bindings["Grep"].is_bound is True
    assert config.bindings["Grep"].is_default is False


def test_tombstone_keeps_default_tool_unbound(monkeypatch):
    """tombstone 场景：显式解绑的默认工具保持未绑定，其余默认工具仍绑定。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()

    config = manager._create_config_from_persisted(
        "app1",
        "agent1",
        persisted_tool_ids=["Grep"],
        unbound_tool_ids=["Read", "Write"],
    )

    assert config.bindings["Read"].is_bound is False
    assert config.bindings["Read"].unbound_at is not None
    assert config.bindings["Write"].is_bound is False
    # 其余默认工具不受影响
    assert config.bindings["Bash"].is_bound is True
    assert config.bindings["Edit"].is_bound is True
    assert config.bindings["ask_user"].is_bound is True
    # 清单里的可选工具仍绑定
    assert config.bindings["Grep"].is_bound is True


def test_bound_wins_over_tombstone(monkeypatch):
    """同一工具同时出现在绑定清单和 tombstone 时，绑定优先（异常数据兜底）。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()

    config = manager._create_config_from_persisted(
        "app1", "agent1", persisted_tool_ids=["Read"], unbound_tool_ids=["Read"]
    )
    assert config.bindings["Read"].is_bound is True


def test_runtime_enabled_matches_binding(monkeypatch):
    """is_tool_enabled / get_enabled_tools 与绑定状态一致。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()

    config = manager._create_config_from_persisted(
        "app1", "agent1", persisted_tool_ids=[], unbound_tool_ids=["Read"]
    )

    assert config.is_tool_enabled("Read") is False
    assert config.is_tool_enabled("Bash") is True
    assert config.is_tool_enabled("Grep") is False
    enabled = config.get_enabled_tools()
    assert "Read" not in enabled
    assert "Bash" in enabled


# ========== get_agent_config 回调兼容 ==========


def test_load_callback_legacy_list_still_works(monkeypatch):
    """回调返回纯 List[str]（旧实现）时行为不变：缺失的默认工具回落默认绑定。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()
    manager.set_load_callback(lambda app_id, agent_name: ["Grep"])

    config = manager.get_agent_config("app1", "agent1")
    assert config is not None
    assert config.bindings["Grep"].is_bound is True
    assert config.bindings["Read"].is_bound is True  # 默认工具回落默认规则


def test_load_callback_with_tombstone(monkeypatch):
    """回调返回 PersistedToolBindings 时 tombstone 生效。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()
    manager.set_load_callback(
        lambda app_id, agent_name: PersistedToolBindings(
            bound_ids=["Grep"], unbound_ids=["Read"]
        )
    )

    config = manager.get_agent_config("app1", "agent1")
    assert config is not None
    assert config.bindings["Read"].is_bound is False
    assert config.bindings["Bash"].is_bound is True
    assert config.bindings["Grep"].is_bound is True


def test_load_callback_none_falls_back_to_default(monkeypatch):
    """回调返回 None（无持久化数据）时使用默认配置，默认工具全部绑定。"""
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()
    manager.set_load_callback(lambda app_id, agent_name: None)
    # 默认配置需要 registry.get 能返回工具
    monkeypatch.setattr(
        tool_registry,
        "get",
        lambda tid: SimpleNamespace(metadata=SimpleNamespace(name=tid)),
    )

    config = manager.get_agent_config("app1", "agent1")
    assert config is not None
    for tid in ["ask_user", "Bash", "Read", "Write", "Edit", "deliver_file", "skill"]:
        assert config.bindings[tid].is_bound is True


# ========== 缓存键按 app_id 作用域（修复运行时 agent_name 分裂） ==========


def test_cache_key_is_app_scoped_not_agent_scoped(monkeypatch):
    """缓存键必须按 app_id 作用域。

    工具绑定按 App 存储、load 回调忽略 agent_name，因此同一 app 下无论
    agent_name 是编辑页的 "default" 还是运行时的显示名（如"场景空间助手"/
    角色名"BAIZE"），都应命中同一份配置。若按 "app_id:agent_name" 缓存，
    运行时键会被旧默认配置污染、编辑页保存后清不掉，导致运行时永远拿到的
    是默认 7 工具而非持久化的多媒体/Web 工具。
    """
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()
    load_call_count = {"n": 0}
    manager.set_load_callback(
        lambda app_id, agent_name: (load_call_count.__setitem__("n", load_call_count["n"] + 1) or ["Grep"])
    )

    # 不同 agent_name 第一次调用都会 miss → 触发 load
    c1 = manager.get_agent_config("app1", "agent1")
    c2 = manager.get_agent_config("app1", "anther_agent")
    # 同一 app 命中同一缓存（app-scoped），第二次不再触发 load
    c3 = manager.get_agent_config("app1", "yet_another")

    assert c1 is c2 is c3, "同一 app 的配置必须是同一实例（app 作用域缓存）"
    assert load_call_count["n"] == 1, "仅首次调用应触发 load 回调"
    assert c1.bindings["Grep"].is_bound is True


def test_clear_cache_app_id_invalidates_runtime_agent_key(monkeypatch):
    """编辑页保存后 clear_cache(app_id) 必须让运行时（不同 agent_name）重新加载。

    历史 bug：运行时键为 "app_id:显示名"，编辑页 clear_cache(app_id,"default")
    只清 "app_id:default"，运行时键一直被旧默认配置污染。修复后缓存键按
    app_id 作用域，clear_cache(app_id) 即可失效整个 App 的配置。
    """
    _stub_registry_tools(monkeypatch, ALL_TOOL_IDS)
    manager = ToolManager()
    calls = {"n": 0}
    manager.set_load_callback(
        lambda app_id, agent_name: (calls.__setitem__("n", calls["n"] + 1) or ["Grep"])
    )

    runtime_config = manager.get_agent_config("app1", "场景空间助手")
    manager.clear_cache("app1", "default")  # 编辑页保存时以其 agent_name 调用的清缓存
    runtime_config_after = manager.get_agent_config("app1", "场景空间助手")

    # 编辑页的 clear_cache 必须让运行时键重新加载
    assert calls["n"] == 2, "clear_cache(app_id) 后运行时键应重新触发 load"
    assert runtime_config_after is not runtime_config
