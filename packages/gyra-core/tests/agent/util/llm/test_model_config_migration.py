"""上下文空间(context_window)与输出上限(max_new_tokens)口径分离的迁移测试。

覆盖：
- LLMProviderModelConfig.model_post_init 遗留迁移（误填进 max_new_tokens 的上下文空间迁回）
- _migrate_legacy_token_fields（raw dict 路径，parse_provider_configs/空间级复用）
- 幂等性：已显式设置 context_window 时不再迁移
"""
from __future__ import annotations

from gyra_core.config.schema import LLMProviderModelConfig
from gyra.agent.util.llm.model_config_cache import _migrate_legacy_token_fields


class TestSchemaMigration:
    def test_legacy_large_max_new_tokens_migrated_to_context_window(self):
        """256K 被误填进 max_new_tokens -> 迁回 context_window，输出上限重置为默认。"""
        m = LLMProviderModelConfig(name="kimi-k2.5", max_new_tokens=262144)
        assert m.context_window == 262144
        assert m.max_new_tokens == 4096

    def test_small_max_new_tokens_not_migrated(self):
        """正常的输出上限（如 8192）保持不变，context_window 留空。"""
        m = LLMProviderModelConfig(name="gpt-4o", max_new_tokens=8192)
        assert m.max_new_tokens == 8192
        assert m.context_window is None

    def test_default_max_new_tokens_not_migrated(self):
        m = LLMProviderModelConfig(name="m")
        assert m.max_new_tokens == 4096
        assert m.context_window is None

    def test_explicit_context_window_preserved(self):
        """显式配置了 context_window 时，即使 max_new_tokens 较大也不迁移。"""
        m = LLMProviderModelConfig(name="m", max_new_tokens=8192, context_window=200000)
        assert m.context_window == 200000
        assert m.max_new_tokens == 8192


class TestDictHelperMigration:
    def test_migrate_large_legacy(self):
        cfg = {"model": "kimi-k2.5", "max_new_tokens": 262144}
        _migrate_legacy_token_fields(cfg)
        assert cfg["context_window"] == 262144
        assert cfg["max_new_tokens"] == 4096

    def test_migrate_legacy_max_tokens_key(self):
        """旧配置可能用 max_tokens 键。"""
        cfg = {"model": "m", "max_tokens": 200000}
        _migrate_legacy_token_fields(cfg)
        assert cfg["context_window"] == 200000
        assert cfg["max_tokens"] == 4096

    def test_no_migrate_small(self):
        cfg = {"model": "m", "max_new_tokens": 4096}
        _migrate_legacy_token_fields(cfg)
        assert cfg.get("context_window") is None
        assert cfg["max_new_tokens"] == 4096

    def test_idempotent(self):
        cfg = {"model": "m", "max_new_tokens": 262144}
        _migrate_legacy_token_fields(cfg)
        once = dict(cfg)
        _migrate_legacy_token_fields(cfg)
        assert cfg == once

    def test_skips_when_context_window_set(self):
        cfg = {"model": "m", "max_new_tokens": 262144, "context_window": 128000}
        _migrate_legacy_token_fields(cfg)
        assert cfg["context_window"] == 128000
        assert cfg["max_new_tokens"] == 262144
