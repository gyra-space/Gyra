"""gyra-core 测试根 conftest。

进程级共享缓存（facade 静态快照 / LLM provider / V2 StateStore / SkillRegistry）
在生产代码里跨 agent 实例复用；测试中不同用例常以相同 key（agent_id、模型名、
空资源配置）构造对象，共享缓存会导致跨用例污染。这里在每个测试前清空。
"""
import pytest


@pytest.fixture(autouse=True)
def _clear_process_level_caches():
    from gyra.agent.capabilities import facade as _facade_mod
    from gyra.agent.util.llm import llm_client as _llm_mod
    from gyra.agent.util.llm.model_config_cache import ModelConfigCache
    from gyra.agent.expand.v2_agent import v2_agent as _v2_mod

    _facade_mod._SHARED_SNAPSHOT_CACHE.clear()
    _facade_mod._SHARED_REQUIRES_CACHE.clear()
    _llm_mod._PROVIDER_CACHE.clear()
    _llm_mod._PROVIDER_CACHE_ORDER.clear()
    _v2_mod._V2_STATE_STORES.clear()
    _v2_mod._V2_SKILL_REGISTRIES.clear()
    # 模型配置注册表同为进程级：上一用例注册的模型会影响下一用例的
    # fallback/解析路径（如 "fake-model" 被回退到残留模型）
    ModelConfigCache.clear()
    yield
