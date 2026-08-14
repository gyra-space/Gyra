"""RFC-005 Step D / RFC-006 Stage 5: memory capability 测试。

记忆:declare 空(配置载体)+ consume 检索回注(memory_context→USER_PART/SESSION)。
"""

import pytest

from gyra.core.interface.resource.bundle import Lifetime
from gyra.agent.capabilities.memory import MemoryCapability


# =========================================================================== #
# RFC-006 Stage 5:MemoryCapability 自管理对象模型(最小占位)
# =========================================================================== #
def test_memory_capability_declare_empty():
    cap = MemoryCapability()
    assert cap.declare() == []
    assert cap.capability_id == "memory"
    assert cap.executor_id == "memory"


async def test_memory_capability_consume():
    cap = MemoryCapability()
    contribs = await cap.consume("ctx")
    assert len(contribs) == 1
    assert "memory-context" in contribs[0].content
    assert contribs[0].lifetime == Lifetime.SESSION


async def test_memory_capability_consume_empty():
    cap = MemoryCapability()
    assert await cap.consume("") == []
    assert await cap.consume(None) == []


async def test_memory_capability_prepare_release():
    from gyra.core.interface.resource.executor import ExecutorStatus, ReleaseReason

    cap = MemoryCapability()
    await cap.prepare()
    assert cap._status == ExecutorStatus.READY
    await cap.release(ReleaseReason.SESSION_END)
    assert cap._status == ExecutorStatus.RELEASED


async def test_memory_capability_execute_not_implemented():
    """execute 未接 store(memory_* 工具暂走 MemoryToolPack builtin)。"""
    from gyra.core.interface.resource.executor import ExecutorCall

    cap = MemoryCapability()
    with pytest.raises(NotImplementedError):
        await cap.execute(
            ExecutorCall(executor_id="memory", capability_id="memory", tool_name="memory_search", args={})
        )


def test_memory_from_config_builds_memory_parameters():
    """Phase D:from_config 把 value dict 规范化为 MemoryParameters。"""
    from gyra.agent.capabilities.memory.capability import MemoryCapability
    from gyra.agent.resource.memory import MemoryParameters

    cap = MemoryCapability.from_config({"top_k": 5, "discard_strategy": "lru"})
    assert isinstance(cap.memory_params, MemoryParameters)
    assert cap.memory_params.top_k == 5
    assert cap.memory_params.discard_strategy == "lru"


def test_memory_from_config_empty_or_bad_value():
    from gyra.agent.capabilities.memory.capability import MemoryCapability

    assert MemoryCapability.from_config(None).memory_params is None
    assert MemoryCapability.from_config({}).memory_params is None
