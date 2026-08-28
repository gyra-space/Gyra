"""V1 场景空间对话的 AGENTS.md 注入（对话开始默认进 system prompt）。

复用 gyra-core 的公共实现 ``gyra.agent.agents_md_context``，三路来源
按优先级合并：显式配置路径 > 记忆空间 vault AGENTS.md > project_dir
自动探测。与 V2（react_master_agent._build_agents_md_section /
read_pipeline.load_static_block）语义对齐。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from gyra.agent.agents_md_context import (
    detect_project_agents_md,
    is_agents_md_placeholder,
    parse_agents_md_config,
    read_agents_md_file,
    render_agents_md_block,
)

logger = logging.getLogger(__name__)


def _coerce_ext_config(ext_config: Any) -> Dict[str, Any]:
    """ext_config 落库为 JSON Text，读取侧可能是 dict 或 JSON 字符串。"""
    if isinstance(ext_config, str):
        try:
            ext_config = json.loads(ext_config)
        except (json.JSONDecodeError, TypeError):
            return {}
    return ext_config if isinstance(ext_config, dict) else {}


def _resolve_memory_space_slug(gpt_app: Any) -> Optional[str]:
    """从 app.resource_memory 解析绑定的记忆空间 slug。

    enable_memory 的落库形态：resource_memory[0].value = JSON 字符串，
    含 ``memories[0].memory_id``（= ``memory-{app_code}``）与 ``space_slug``。
    """
    resource_memory = getattr(gpt_app, "resource_memory", None)
    if not resource_memory:
        return None
    try:
        first = resource_memory[0]
        value = (
            getattr(first, "value", None)
            if not isinstance(first, dict)
            else first.get("value")
        )
        if not value:
            return None
        payload = json.loads(value) if isinstance(value, str) else (value or {})
    except (json.JSONDecodeError, IndexError, TypeError) as e:
        logger.debug(f"[agents-md] parse resource_memory failed: {e}")
        return None
    if not isinstance(payload, dict):
        return None
    slug = payload.get("space_slug")
    if not slug:
        memories = payload.get("memories") or []
        if memories and isinstance(memories[0], dict):
            slug = memories[0].get("memory_id")
    return str(slug).strip() or None


async def _load_vault_agents_md(system_app: Any, slug: str) -> Optional[str]:
    """读记忆空间 vault 根级 AGENTS.md（tier3 管线维护）。"""
    try:
        from gyra_serve.knowledge.service.service import (
            Service as KnowledgeService,
        )

        ks = KnowledgeService.get_instance(system_app)
        if ks is None:
            return None
        vault = await ks.get_vault(slug)
        if vault is None or not hasattr(vault, "read_agents_md"):
            return None
        return await vault.read_agents_md()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[agents-md] load vault AGENTS.md (slug={slug}) failed: {e}")
        return None


async def collect_agents_md_sections(
    system_app: Any, gpt_app: Any, ext_info: Dict[str, Any]
) -> List[Tuple[str, str]]:
    """按优先级收集三路 AGENTS.md 内容。"""
    sections: List[Tuple[str, str]] = []
    ext_config = _coerce_ext_config(getattr(gpt_app, "ext_config", None))

    # 1. 显式配置路径（相对路径基于场景空间 workspace 根解析）
    enabled, path = parse_agents_md_config(ext_config)
    if enabled and path:
        base_dir = None
        ws_id = ext_info.get("workspace_id")
        if ws_id:
            try:
                from gyra_serve.workspace.dataset_service import (
                    workspace_sandbox_root,
                )

                base_dir = workspace_sandbox_root(int(ws_id))
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[agents-md] resolve workspace root failed: {e}")
        content = read_agents_md_file(path, base_dir)
        if content and not is_agents_md_placeholder(content):
            sections.append(("explicit-config", content))

    # 2. 记忆空间 vault AGENTS.md
    slug = _resolve_memory_space_slug(gpt_app)
    if slug:
        raw = await _load_vault_agents_md(system_app, slug)
        if raw and (raw := raw.strip()) and not is_agents_md_placeholder(raw):
            sections.append(("memory-space", raw))

    # 3. project_dir 自动探测（AGENTS.md；CLAUDE.md 系列归项目生态链路）
    eco_cfg = ext_config.get("project_ecosystem") or {}
    content = detect_project_agents_md(eco_cfg.get("project_dir"))
    if content:
        sections.append(("project-dir", content))

    return sections


async def build_agents_md_block(
    system_app: Any, gpt_app: Any, ext_info: Dict[str, Any]
) -> Optional[str]:
    """构建 AGENTS.md 注入块；无有效内容返回 None。失败降级不阻断对话。"""
    try:
        sections = await collect_agents_md_sections(system_app, gpt_app, ext_info)
        return render_agents_md_block(sections)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[agents-md] build injection block failed: {e}")
        return None
