"""DbSemanticsProposer 批量提案 LLM 链路单元测试。

覆盖本轮修复点：
1. _get_llm_config 解析优先级：空间级模型配置 > 全局首个 LLM 模型。
2. _propose_batch 在「LLM 有返回但解析出 0 条提案」时显式抛错，
   避免任务静默 completed 却又一个提案都没有。
"""

import pytest

from gyra.agent.util.llm.model_config_cache import ModelConfigCache
from gyra_serve.ecp.service.propose import DbSemanticsProposer


class _FakeService:
    """proposer 只用到 service 作为占位，真实调用在 generate 里才发生。"""


def _make_proposer():
    return DbSemanticsProposer(_FakeService())


# ------------------------------------------------------------------ LLM 配置
@pytest.fixture
def _clear_llm_cache():
    ModelConfigCache.clear()
    ModelConfigCache.set_space_model_config(None)
    yield
    ModelConfigCache.clear()
    ModelConfigCache.set_space_model_config(None)


def test_get_llm_config_prefers_space_model(_clear_llm_cache):
    """有空间级模型配置时优先使用，而非全局首个模型。"""
    ModelConfigCache.register_configs(
        {
            "openai/global-llm": {
                "provider": "openai", "model": "global-llm",
                "base_url": "https://global.example/v1", "api_key": "g-key",
            }
        }
    )
    ModelConfigCache.set_space_model_config(
        {
            "provider": "openai", "model": "space-llm",
            "base_url": "https://space.example", "api_key": "s-key",
        }
    )
    p = _make_proposer()
    cfg = p._get_llm_config()
    assert cfg is not None
    assert cfg["model"] == "space-llm"
    assert cfg["api_key"] == "s-key"
    # 空间 base_url 缺 /v1 时自动补齐
    assert cfg["base_url"] == "https://space.example/v1"


def test_get_llm_config_falls_back_to_global(_clear_llm_cache):
    """无空间级配置时回退全局首个 LLM 模型。"""
    ModelConfigCache.register_configs(
        {
            "openai/global-llm": {
                "provider": "openai", "model": "global-llm",
                "base_url": "https://global.example/v1", "api_key": "g-key",
            }
        }
    )
    p = _make_proposer()
    cfg = p._get_llm_config()
    assert cfg is not None
    assert cfg["model"] == "global-llm"
    assert cfg["base_url"] == "https://global.example/v1"


def test_get_llm_config_none_when_no_model(_clear_llm_cache):
    """无任何可用模型时返回 None（上游据此报 LLM 未配置）。"""
    p = _make_proposer()
    assert p._get_llm_config() is None


# ------------------------------------------------------------------ 0 提案
@pytest.mark.asyncio
async def test_propose_batch_raises_on_zero_proposals():
    """LLM 返回文本但解析不出提案时显式抛错，不静默 completed。"""
    p = _make_proposer()

    async def _fake_llm(prompt):
        return "这不是约定的 JSON 输出"

    p._call_llm = _fake_llm  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="未解析出任何合法提案"):
        await p._propose_batch(
            batch=[{"table_name": "t1", "columns": [], "table_comment": "x"}],
            datasource_id=1,
            distinct_values={},
            existing_catalog=None,
            domain_hint=None,
        )