"""DB capability —— 数据库能力自管目录(RFC-005 / RFC-006 Stage 6,serve 层)。

DB 资源连 serve 服务(spec_service/connector),整体在 serve 层自管:
- capability.py: DBCapability(自管理 prepare/fetch/declare/release)[RFC-006]
- executor.py: DBExecutor(fetch 分级 spec,连 serve spec_service,异步)[旧,Stage 9 删]
- tools/: execute_sql/get_table_spec/list_tables/search_tables(capability_id="db")

config→DBCapability 经 CapabilityFactoryRegistry(register_capability_to)构造;
工具暂走 Route A builtin,运行时从 DBCapability 实例取 connector(折中,见
capability.py docstring)。
"""

def register(registry) -> None:
    pass


def build_capability(value, system_app=None):
    """RFC-006 Stage 6:从 AgentResource.value dict 构造 DBCapability(不建连接;prepare 时建)。"""
    from .capability import DBCapability
    return DBCapability.from_config(value, system_app)


# RFC-006 Phase A:供 CapabilityFactoryRegistry 构造期 build_pack 用。
CAPABILITY_TYPE_KEY = "datasource"


def register_capability_to(registry) -> None:
    """注册 build_capability 到 CapabilityFactoryRegistry(构造期产 CapabilityPack)。"""
    registry.register(CAPABILITY_TYPE_KEY, build_capability)
