"""workspace 记忆空间(get_or_create_workspace_space)单测。

真 LocalVaultFS( ServeConfig.local_root 指向 tmp_path):slug 清洗、
lazy 创建播种 AGENTS.md、幂等且不覆盖用户内容。
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from gyra.agent.agents_md_context import is_agents_md_placeholder
from gyra_serve.knowledge.config import ServeConfig
from gyra_serve.knowledge.service.service import Service


def _make_service(tmp_path) -> Service:
    system_app = MagicMock()
    system_app.config.get = lambda key: None
    return Service(
        system_app=system_app,
        serve_config=ServeConfig(local_root=str(tmp_path / "spaces")),
    )


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _close_vaults(ks: Service):
    """关闭 LocalVaultFS 后台线程,否则 pytest 进程无法退出。"""

    async def _close_all():
        for vault in list(getattr(ks, "_vaults", {}).values()):
            try:
                await vault.close()
            except Exception:  # noqa: BLE001
                pass

    _run(_close_all())


class TestWorkspaceSpaceSlug:
    def test_cleaning(self):
        assert Service.workspace_space_slug("ws-abc") == "memory-ws-ws-abc"
        assert Service.workspace_space_slug("ws abc/1") == "memory-ws-ws_abc_1"
        assert Service.workspace_space_slug("") == "memory-ws-unknown"


class TestGetOrCreateWorkspaceSpace:
    def test_lazy_create_seeds_agents_md(self, tmp_path):
        ks = _make_service(tmp_path)
        try:
            vault = _run(ks.get_or_create_workspace_space("ws alpha"))
            assert ks.workspace_space_slug("ws alpha") == "memory-ws-ws_alpha"
            agents_md = _run(vault.read_agents_md())
            assert agents_md, "agent_memory 空间应播种 AGENTS.md"
            assert not is_agents_md_placeholder(agents_md) or "AGENTS.md" in agents_md
        finally:
            _close_vaults(ks)

    def test_idempotent_and_preserves_user_content(self, tmp_path):
        ks = _make_service(tmp_path)
        try:
            v1 = _run(ks.get_or_create_workspace_space("ws-1"))
            _run(v1.write_agents_md("# 自定义空间记忆\n\n用户手写内容\n"))
            v2 = _run(ks.get_or_create_workspace_space("ws-1"))
            assert v2 is v1
            assert "用户手写内容" in _run(v2.read_agents_md())
        finally:
            _close_vaults(ks)

    def test_different_workspaces_get_different_spaces(self, tmp_path):
        ks = _make_service(tmp_path)
        try:
            va = _run(ks.get_or_create_workspace_space("ws-a"))
            vb = _run(ks.get_or_create_workspace_space("ws-b"))
            assert va is not vb
            assert va.root != vb.root
        finally:
            _close_vaults(ks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
