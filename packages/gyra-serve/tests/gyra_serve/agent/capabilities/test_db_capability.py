"""RFC-006 Stage 6: db capability 自管理测试(prepare/fetch/declare/release + 取连接)。

DBExecutor(连 serve spec_service)已迁 serve 层,相关测试在 serve 测试目录。
facade 回填用 mock executor(不依赖真实 DBExecutor)。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from gyra.core.interface.resource.data_requirement import (
    DataRequirement,
    InjectionMode,
    injection_mode_for_table_count,
)


def test_large_db_not_injects_table_list():
    """大库分级纯函数:>=500 → LARGE(不注入表列表,发工具指引)。"""
    mode = injection_mode_for_table_count(800)
    assert mode == InjectionMode.LARGE
    assert mode != InjectionMode.SMALL


# =========================================================================== #
# RFC-006 Stage 6:DBCapability 自管理(prepare/fetch/declare/release + 取连接)
# =========================================================================== #
def test_db_capability_from_config():
    from gyra_serve.agent.capabilities.db.capability import DBCapability

    cap = DBCapability.from_config({"db_name": "paydb", "db_id": 42})
    assert isinstance(cap, DBCapability)
    assert cap.db_name == "paydb"
    assert cap.capability_id == "db:42"
    assert cap.executor_id == "db:42"


def test_db_capability_declare_basic_and_placeholder():
    from gyra.core.interface.resource.data_requirement import DataRequirement
    from gyra_serve.agent.capabilities.db.capability import DBCapability

    cap = DBCapability(db_name="paydb", db_id=42, db_type="mysql", dialect="mysql")
    contribs = cap.declare()
    assert len(contribs) == 2
    basic, placeholder = contribs
    assert "paydb" in basic.content and "mysql" in basic.content
    assert isinstance(placeholder.content, DataRequirement)
    assert placeholder.content.kind == "db_prompt"
    assert placeholder.content.executor_id == "db:42"


async def test_db_capability_fetch_uses_connector_when_no_spec_service(monkeypatch):
    """无 spec_service 时 fetch 回退 connector.get_table_names(异步)。"""
    from gyra_serve.agent.capabilities.db.capability import DBCapability

    cap = DBCapability(db_name="paydb", db_id=42)
    cap._connector = MagicMock()
    cap._connector.get_table_names.return_value = ["orders", "users"]
    # _get_spec_service 返 None(serve 不可用)
    monkeypatch.setattr(DBCapability, "_get_spec_service", lambda self: None)
    req = DataRequirement(
        executor_id="db:42", capability_id="db:42", kind="db_prompt",
        params={"datasource_id": 42, "db_name": "paydb"},
    )
    text = await cap.fetch(req)
    assert "orders" in text and "users" in text


async def test_db_capability_prepare_builds_connector(monkeypatch):
    """prepare 经 local_db_manager.get_connector 建连接(异步),状态 READY。"""
    from gyra_serve.agent.capabilities.db.capability import DBCapability

    fake_conn = MagicMock()
    fake_conn.db_type = "sqlite"
    fake_conn.dialect = "sqlite"
    fake_mgr = MagicMock()
    fake_mgr.get_connector.return_value = fake_conn
    fake_cfg = MagicMock()
    fake_cfg.local_db_manager = fake_mgr
    monkeypatch.setattr("gyra._private.config.Config", lambda: fake_cfg)

    cap = DBCapability(db_name="paydb", db_id=42)
    await cap.prepare()
    assert cap._status.value == "ready"
    assert cap.get_connector() is fake_conn
    assert cap._db_type == "sqlite"


def test_db_capability_get_connector_for_route_a_tools():
    """折中:Route A DB 工具从 DBCapability.get_connector() 取连接(取代扫 resource_map)。"""
    from gyra_serve.agent.capabilities.db.capability import DBCapability

    cap = DBCapability(db_name="paydb", db_id=42)
    conn = MagicMock()
    cap._connector = conn
    assert cap.get_connector() is conn


# =========================================================================== #
# RFC-006 Phase B3: _resolve_db_from_agent 优先从 CapabilityPack 取连接
# =========================================================================== #
async def test_resolve_db_from_agent_prefers_capability_pack():
    """agent 有 capability_pack 含 DBCapability(db_name 匹配)→ 从其取 connector。"""
    from gyra.core.interface.resource.capability import CapabilityPack
    from gyra.core.interface.resource.executor import ExecutorStatus
    from gyra_serve.agent.capabilities.db.capability import DBCapability

    cap = DBCapability(db_name="paydb", db_id=42)
    cap._status = ExecutorStatus.READY
    fake_conn = MagicMock()
    cap._connector = fake_conn
    pack = CapabilityPack([cap])
    agent = SimpleNamespace(capability_pack=pack)

    from gyra_serve.agent.capabilities.db.tools._db_tools_impl import _resolve_db_from_agent
    conn, ds_id = _resolve_db_from_agent("paydb", {"agent": agent})
    assert conn is fake_conn
    assert ds_id == 42


async def test_resolve_db_from_agent_no_match_returns_none():
    """capability_pack 无 db_name 匹配 → (None, None)(v1 resource_map 兜底已删)。"""
    from gyra.core.interface.resource.capability import CapabilityPack

    pack = CapabilityPack([])
    agent = SimpleNamespace(capability_pack=pack)
    from gyra_serve.agent.capabilities.db.tools._db_tools_impl import _resolve_db_from_agent
    conn, ds_id = _resolve_db_from_agent("paydb", {"agent": agent})
    assert conn is None
    assert ds_id is None
