"""Tests for workspace_resource materializer."""
import json
from unittest.mock import MagicMock, patch
from gyra_serve.workspace.materializer import (
    materialize_resources,
    MaterializedResources,
)


def test_materialize_empty_resources_returns_empty():
    """空资源列表返回空物化结果，不抛异常。"""
    system_app = MagicMock()
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = []
        result = materialize_resources(system_app, workspace_id=1)
    assert isinstance(result, MaterializedResources)
    assert result.dynamic_resources == []
    assert result.extra_agents == []


def test_materialize_unknown_type_skipped_not_raised():
    """未知 type（如 slo/oncall_rotation）跳过，不抛异常，记 warning。"""
    system_app = MagicMock()
    unknown_resource = MagicMock(
        type="slo",
        name="p99_latency",
        physical_ref=None,
        config={"metric": "p99", "target": 200},
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [unknown_resource]
        result = materialize_resources(system_app, workspace_id=1)
    assert result.dynamic_resources == []
    assert result.extra_agents == []


def test_materialize_mcp_resource_produces_agent_resource():
    """type=mcp 的资源物化成 AgentResource（type=mcp(gyra)）。"""
    system_app = MagicMock()
    mcp_resource = MagicMock(
        type="mcp",
        name="k8s_mcp",
        physical_ref="k8s_mcp_code",
        config={},
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService, patch(
        "gyra_serve.agent.resource.tool.mcp_collect.get_mcp_info"
    ) as mock_get_mcp:
        MockWsService.return_value.list_resources.return_value = [mcp_resource]
        mock_get_mcp.return_value = {
            "mcp_code": "k8s_mcp_code",
            "name": "k8s_mcp",
            "type": "sse",
            "sse_url": "http://k8s-mcp.local/sse",
            "sse_headers": {"Authorization": "Bearer token"},
        }
        result = materialize_resources(system_app, workspace_id=1)
    assert len(result.dynamic_resources) == 1
    res = result.dynamic_resources[0]
    assert res.type == "mcp(gyra)"
    assert res.name == "k8s_mcp"
    assert res.value["mcp_code"] == "k8s_mcp_code"
    assert res.value["name"] == "k8s_mcp"
    assert res.value["mcp_servers"] == "http://k8s-mcp.local/sse"
    assert res.value["headers"] == {"Authorization": "Bearer token"}
    assert res.value["source"] == "sse"
    assert res.value["timeout"] == 30


def test_materialize_mcp_resource_config_json_fallback():
    """config 不存在时回退读取 config_json，保持兼容原始实体。"""
    system_app = MagicMock()
    mcp_resource = MagicMock(
        type="mcp",
        name="k8s_mcp",
        physical_ref="k8s_mcp_code",
        config=None,
        config_json='{}',
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService, patch(
        "gyra_serve.agent.resource.tool.mcp_collect.get_mcp_info"
    ) as mock_get_mcp:
        MockWsService.return_value.list_resources.return_value = [mcp_resource]
        mock_get_mcp.return_value = {
            "mcp_code": "k8s_mcp_code",
            "name": "k8s_mcp",
            "type": "sse",
            "sse_url": "http://k8s-mcp.local/sse",
            "sse_headers": {},
        }
        result = materialize_resources(system_app, workspace_id=1)
    assert len(result.dynamic_resources) == 1
    res = result.dynamic_resources[0]
    assert res.type == "mcp(gyra)"
    assert res.value["mcp_servers"] == "http://k8s-mcp.local/sse"


def test_materialize_inactive_resource_skipped():
    """is_active=False 的资源跳过。"""
    system_app = MagicMock()
    inactive = MagicMock(
        type="mcp",
        name="old_mcp",
        physical_ref="old_code",
        config={},
        is_active=False,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [inactive]
        result = materialize_resources(system_app, workspace_id=1)
    assert result.dynamic_resources == []
    assert result.extra_agents == []


def test_materialize_llm_model_sets_space_config_and_injects_agentinfo():
    """type=llm_model 资源:设置空间级模型配置(ContextVar)。

    Phase D:不再产出 AgentResource(llm_model 类型下线),只保留 ModelConfigCache
    副作用。
    """
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    ModelConfigCache.set_space_model_config(None)  # 清空遗留覆盖
    system_app = MagicMock()
    llm_resource = MagicMock(
        type="llm_model",
        name="space_deepseek",
        physical_ref="deepseek-chat",
        config={
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key_ref": "${secrets.space_deepseek_key}",
        },
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [llm_resource]
        result = materialize_resources(system_app, workspace_id=1)

    # Phase D:不再物化 AgentResource
    assert result.dynamic_resources == []

    # 空间级配置生效:has_model / get_config 命中空间模型
    assert ModelConfigCache.has_model("deepseek-chat") is True
    cfg = ModelConfigCache.get_config("deepseek-chat")
    assert cfg is not None
    assert cfg["provider"] == "deepseek"
    assert cfg["model"] == "deepseek-chat"

    ModelConfigCache.set_space_model_config(None)  # 清理,避免影响其他用例


def test_materialize_llm_model_prefers_is_default():
    """多个 llm_model 时,空间级模型覆盖取 config.is_default 标记的那个。"""
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    ModelConfigCache.set_space_model_config(None)
    system_app = MagicMock()
    first = MagicMock(
        type="llm_model", name="model_a", physical_ref="model-a",
        config={"provider": "openai", "model": "model-a", "is_default": False},
        is_active=True,
    )
    second = MagicMock(
        type="llm_model", name="model_b", physical_ref="model-b",
        config={"provider": "openai", "model": "model-b", "is_default": True},
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        # 返回顺序 model_a 在前,但默认标记在 model_b,物化应选中 model_b
        MockWsService.return_value.list_resources.return_value = [first, second]
        result = materialize_resources(system_app, workspace_id=1)
    assert result.dynamic_resources == []
    cfg = ModelConfigCache.get_config("model-b")
    assert cfg is not None
    assert cfg["model"] == "model-b"
    assert cfg["provider"] == "openai"

    ModelConfigCache.set_space_model_config(None)  # 清理


def test_materialize_llm_model_falls_back_to_first_when_no_default():
    """无 is_default 标记时,取列表首个启用的模型作为空间模型覆盖。"""
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    ModelConfigCache.set_space_model_config(None)
    system_app = MagicMock()
    first = MagicMock(
        type="llm_model", name="model_a", physical_ref="model-a",
        config={"provider": "openai", "model": "model-a"},
        is_active=True,
    )
    second = MagicMock(
        type="llm_model", name="model_b", physical_ref="model-b",
        config={"provider": "openai", "model": "model-b"},
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [first, second]
        result = materialize_resources(system_app, workspace_id=1)
    assert result.dynamic_resources == []
    cfg = ModelConfigCache.get_config("model-a")
    assert cfg is not None
    assert cfg["model"] == "model-a"

    ModelConfigCache.set_space_model_config(None)  # 清理


def test_materialize_llm_model_empty_model_returns_none():
    """llm_model 无 model/physical_ref 时不注入、不设置空间配置。"""
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache

    ModelConfigCache.set_space_model_config(None)
    system_app = MagicMock()
    bad = MagicMock(
        type="llm_model",
        name="empty",
        physical_ref=None,
        config={},
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [bad]
        result = materialize_resources(system_app, workspace_id=1)
    assert result.dynamic_resources == []
    assert ModelConfigCache.get_space_model_config() is None

    ModelConfigCache.set_space_model_config(None)


def test_materialize_knowledge_space_emits_knowledge_pack_v2():
    """Phase D:knowledge_space 物化为 type=knowledge_pack + v2 JSON value。"""
    system_app = MagicMock()
    ks = MagicMock(
        type="knowledge_space",
        name="wiki",
        physical_ref="kid-1",
        config={"name": "内部wiki"},
        is_active=True,
    )
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [ks]
        result = materialize_resources(system_app, workspace_id=1)

    assert len(result.dynamic_resources) == 1
    ar = result.dynamic_resources[0]
    assert ar.type == "knowledge_pack"
    value = ar.value if isinstance(ar.value, dict) else json.loads(ar.value)
    assert value["knowledges"] == [{"knowledge_id": "kid-1"}]


# --------------------------------------------------------------------------- #
# 剧本声明物化:引用对齐空间资源池(空间=注册/治理池,剧本=选配/编排子集)
# --------------------------------------------------------------------------- #

def test_materialize_playbook_declaration_pool_hit_uses_pool_config():
    """命中空间池的引用按绑定记录物化(type/physical_ref/config 以绑定为准)。"""
    from gyra_serve.workspace.materializer import materialize_playbook_declaration

    system_app = MagicMock()
    pool_record = MagicMock(
        type="data_source",
        name="生产核心库",
        physical_ref="prod_core_db",
        config={"schema_filter": ["orders"]},
        is_active=True,
    )
    declaration = {
        "skills": [],
        "context": {"resources": [{"type": "datasource", "ref": "prod_core_db"}]},
    }
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = [pool_record]
        result = materialize_playbook_declaration(
            system_app, declaration, workspace_id=1
        )

    assert len(result) == 1
    assert result[0].type == "datasource"
    assert result[0].value["db_name"] == "prod_core_db"
    assert result[0].value["schema_filter"] == ["orders"]


def test_materialize_playbook_declaration_unbound_falls_back_global():
    """未绑定到空间池的引用走全局兜底(存量/seed 兼容)。"""
    from gyra_serve.workspace.materializer import materialize_playbook_declaration

    system_app = MagicMock()
    declaration = {
        "skills": ["ghost_skill"],
        "context": {"resources": []},
    }
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = []
        result = materialize_playbook_declaration(
            system_app, declaration, workspace_id=1
        )

    assert len(result) == 1
    assert result[0].type == "skill(gyra)"
    assert result[0].name == "ghost_skill"


def test_materialize_playbook_declaration_without_workspace_unchanged():
    """不传 workspace_id 保持原行为:直接按声明类型全局物化。"""
    from gyra_serve.workspace.materializer import materialize_playbook_declaration

    system_app = MagicMock()
    declaration = {
        "skills": ["a_skill"],
        "context": {"resources": [{"type": "mcp", "ref": "mcp_code"}]},
    }
    with patch(
        "gyra_serve.workspace.materializer.WorkspaceService"
    ) as MockWsService:
        MockWsService.return_value.list_resources.return_value = []
        with patch(
            "gyra_serve.agent.resource.tool.mcp_collect.get_mcp_info",
            return_value={"name": "m", "type": "sse", "sse_url": "http://x/sse"},
        ):
            result = materialize_playbook_declaration(system_app, declaration)

    assert len(result) == 2
    assert {r.type for r in result} == {"skill(gyra)", "mcp(gyra)"}
