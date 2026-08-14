"""Knowledge capability —— 知识库能力自管目录(RFC-005 Step C / RFC-006 Stage 7)。

知识库是 Consumer:declare 库列表 + consume 检索回注。
config→KnowledgeCapability 经 CapabilityFactoryRegistry(register_capability_to)构造。
注:facade 时序 declare 先于 prepare,Knowledge declare 依赖 spaces 元数据(对象
非 str,无法 DataRequirement 占位),故 KnowledgeCapability 不自管 prepare 的重 I/O;
execute 保持 v1 action。详见 capability.py。
"""

from .capability import KnowledgeCapability  # noqa: F401

__all__ = ["KnowledgeCapability"]


def register(registry) -> None:
    pass


def build_capability(value, system_app=None):
    """RFC-006 Stage 7:从 config dict 构造 KnowledgeCapability(无 I/O;spaces 走 config)。"""
    return KnowledgeCapability.from_config(value, system_app)


# RFC-006 Phase A:供 CapabilityFactoryRegistry 构造期 build_pack 用。
CAPABILITY_TYPE_KEY = "knowledge_pack"


def register_capability_to(registry) -> None:
    registry.register(CAPABILITY_TYPE_KEY, build_capability)
