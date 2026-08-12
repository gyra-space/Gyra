"""Memory tool pack for agent integration.

Exposes memory operations as agent-callable tools so that agents can
proactively search, save, and query knowledge graph entries during
conversations.

Works with any registered MemoryStoreBase provider.
"""

import json
import logging
import re
from functools import partial
from typing import Any, Dict, List, Optional

from gyra.agent.resource.tool.pack import ToolPack, json_parse_execute_args_func
from gyra.storage.memory.base import MemoryStoreBase

logger = logging.getLogger(__name__)

# AGENTS.md 高价值分类 → section 标题映射（与 gyra-core longterm_manager 一致）
_AGENTS_MD_CATEGORY_SECTION = {
    "identity": "Identity",
    "preference": "Preferences",
    "decision": "Decisions",
    "lesson": "Lessons",
    "event": "Events",
    "data": "References",
    "convention": "Conventions",
    "user": "Identity",
}

# 用户显式写入 AGENTS.md 的标记（永不淘汰）
_AGENTS_MD_USER_TAG = "[来源: user]"

_AGENTS_MD_HEADER_RE = re.compile(r"^(# .*\n)(?:\n*)", re.MULTILINE)
_AGENTS_MD_SECTION_RE = re.compile(r"(^##\s+[^\n]+\n)", re.MULTILINE)


def _sanitize_tool_suffix(name: str) -> str:
    """Convert a space/memory id into a safe tool-name suffix."""
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_") or "space"


def _insert_agents_md_user_item(existing: str, content: str, category: str) -> str:
    """Insert a user-tagged high-value item into AGENTS.md.

    - Preserves the header (lines before the first `## `) and all existing
      content.
    - Routes the item into the section matching its category (creates the
      section if missing).
    - Tags the line with `[来源: user]` so the consolidation pass never
      evicts it.
    - Dedupes: if the same normalized line already exists, no-op.
    """
    existing = existing or ""
    item = f"- {content.strip()} {_AGENTS_MD_USER_TAG}".strip()

    header_lines: List[str] = []
    sections: Dict[str, List[str]] = {}
    current_title: Optional[str] = None
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_title = stripped[3:].strip()
            sections.setdefault(current_title, [])
        elif current_title is None:
            header_lines.append(line)  # header：第一个 ## 之前
        else:
            sections[current_title].append(line)

    target_section = _AGENTS_MD_CATEGORY_SECTION.get(category, "Conventions")
    sections.setdefault(target_section, [])

    # 去重：规范化（去掉标记与空白差异）
    normalized = re.sub(r"\s+", " ", item.replace(_AGENTS_MD_USER_TAG, "")).strip()
    for line in sections[target_section]:
        if re.sub(r"\s+", " ", line.replace(_AGENTS_MD_USER_TAG, "")).strip() == normalized:
            return existing  # 已存在，不重复写入
    sections[target_section].append(item)

    ordered = ["Identity", "Preferences", "Decisions", "Lessons", "Events",
               "References", "Conventions", "Recent Updates"]
    out_lines = [ln for ln in header_lines if ln.strip()] or ["# Agent 整体记忆（AGENTS.md）"]
    for name in ordered:
        body_lines = [l for l in sections.get(name, []) if l.strip()]
        if not body_lines:
            continue
        out_lines.append("")
        out_lines.append(f"## {name}")
        out_lines.append("")
        out_lines.extend(body_lines)
    return "\n".join(out_lines).strip() + "\n"


class MemoryToolPack(ToolPack):
    """Tool pack that exposes memory store operations to agents.

    Registers four base tools:
    - ``memory_search``: Semantic search over long-term memories.
    - ``memory_save``: Save important information to long-term memory.
    - ``kg_query``: Query knowledge graph for entity relationships.
    - ``kg_add``: Add a fact to the knowledge graph.

    When multiple memory stores are provided, each store also gets a
    namespaced copy of the four tools (e.g. ``memory_search_<space>``),
    while the base tools operate on the first/default store for backward
    compatibility.
    """

    def __init__(
        self,
        memory_store: Optional[MemoryStoreBase] = None,
        memory_stores: Optional[Dict[str, MemoryStoreBase]] = None,
        wing: str = "default",
        **kwargs,
    ):
        super().__init__([], name="Memory Tool Pack", **kwargs)
        if memory_store is not None and memory_stores is not None:
            raise ValueError(
                "Provide either memory_store or memory_stores, not both."
            )
        if memory_stores:
            self._memory_stores = dict(memory_stores)
            # Default/fallback store for the unprefixed tools.
            self._memory_store = next(iter(self._memory_stores.values()))
        elif memory_store:
            self._memory_stores = {}
            self._memory_store = memory_store
        else:
            raise ValueError("Either memory_store or memory_stores must be provided.")
        self._wing = wing

    @classmethod
    def type_alias(cls) -> str:
        return "tool(memory)"

    async def preload_resource(self):
        """Register the memory tools."""
        # Unprefixed base tools (backward compatible single-store behaviour).
        self._register_memory_commands(self._memory_store)

        # Namespaced tools for every additional bound memory space.
        for space_id, store in self._memory_stores.items():
            suffix = _sanitize_tool_suffix(space_id)
            self._register_memory_commands(
                store,
                command_prefix=f"memory_{suffix}_",
                kg_prefix=f"kg_{suffix}_",
                space_hint=f" (space: {space_id})",
            )

    def _register_memory_commands(
        self,
        store: MemoryStoreBase,
        command_prefix: str = "",
        kg_prefix: str = "",
        space_hint: str = "",
    ):
        """Register the four memory commands targeting a specific store."""
        self.add_command(
            command_label=(
                "Search long-term memories by semantic similarity. "
                "Use this to recall past conversations, decisions, and facts."
                f"{space_hint}"
            ),
            command_name=f"{command_prefix}memory_search",
            args={
                "query": {
                    "type": "string",
                    "description": "The search query text.",
                    "required": True,
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5).",
                    "default": 5,
                },
                "room": {
                    "type": "string",
                    "description": "Optional topic filter.",
                },
            },
            function=partial(self._do_search, store=store),
            parse_execute_args_func=json_parse_execute_args_func,
        )

        self.add_command(
            command_label=(
                "Save important information to long-term memory. "
                "Use this when the conversation contains facts, decisions, "
                "or knowledge worth remembering across sessions."
                f"{space_hint}"
            ),
            command_name=f"{command_prefix}memory_save",
            args={
                "content": {
                    "type": "string",
                    "description": "The text content to memorize.",
                    "required": True,
                },
                "room": {
                    "type": "string",
                    "description": "Topic category (e.g. 'backend', 'meetings').",
                    "default": "general",
                },
            },
            function=partial(self._do_save, store=store),
            parse_execute_args_func=json_parse_execute_args_func,
        )

        self.add_command(
            command_label=(
                "Explicitly record a high-value item into the agent's overall "
                "memory document (AGENTS.md). Use this ONLY when the user "
                "explicitly asks to remember something (e.g. '记住', '以后注意', "
                "'不要忘记'), or when a hard-won lesson / key decision / "
                "critical event / important data emerged in the conversation. "
                "Items are categorized as: lesson (易错点/踩坑), decision "
                "(关键逻辑/架构决策), event (重要事件), data (关键数据/配置/引用)."
                f"{space_hint}"
            ),
            command_name=f"{command_prefix}memory_remember",
            args={
                "content": {
                    "type": "string",
                    "description": "The high-value fact to remember (concise statement).",
                    "required": True,
                },
                "category": {
                    "type": "string",
                    "description": "lesson | decision | event | data",
                    "required": False,
                },
            },
            function=partial(self._do_remember, store=store),
            parse_execute_args_func=json_parse_execute_args_func,
        )

        self.add_command(
            command_label=(
                "Query the knowledge graph for entity relationships. "
                "Use this to find facts about people, projects, or concepts."
                f"{space_hint}"
            ),
            command_name=f"{kg_prefix}kg_query",
            args={
                "entity": {
                    "type": "string",
                    "description": "The entity name to query.",
                    "required": True,
                },
            },
            function=partial(self._do_kg_query, store=store),
            parse_execute_args_func=json_parse_execute_args_func,
        )

        self.add_command(
            command_label=(
                "Add a fact (triple) to the knowledge graph. "
                "Use this to record entity relationships discovered in "
                "conversations, e.g. 'Alice manages ProjectX'."
                f"{space_hint}"
            ),
            command_name=f"{kg_prefix}kg_add",
            args={
                "subject": {
                    "type": "string",
                    "description": "The subject entity.",
                    "required": True,
                },
                "predicate": {
                    "type": "string",
                    "description": "The relationship type.",
                    "required": True,
                },
                "object": {
                    "type": "string",
                    "description": "The object entity.",
                    "required": True,
                },
            },
            function=partial(self._do_kg_add, store=store),
            parse_execute_args_func=json_parse_execute_args_func,
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _do_search(
        self,
        query: str,
        top_k: int = 5,
        room: Optional[str] = None,
        store: Optional[MemoryStoreBase] = None,
        **kwargs,
    ) -> str:
        store = store or self._memory_store
        entries = store.search_memory(
            query=query,
            top_k=top_k,
            wing=self._wing,
            room=room,
        )
        if not entries:
            return "No relevant memories found."

        results = []
        for e in entries:
            results.append(
                {
                    "id": e.id,
                    "content": e.content,
                    "wing": e.wing,
                    "room": e.room,
                    "score": round(e.score, 3) if e.score else None,
                }
            )
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _do_save(
        self,
        content: str,
        room: str = "general",
        store: Optional[MemoryStoreBase] = None,
        **kwargs,
    ) -> str:
        store = store or self._memory_store
        entry = store.write_memory(
            content=content,
            wing=self._wing,
            room=room,
        )
        return json.dumps(
            {
                "status": "saved",
                "id": entry.id,
                "wing": entry.wing,
                "room": entry.room,
            },
            ensure_ascii=False,
        )

    async def _do_remember(
        self,
        content: str,
        category: str = "decision",
        store: Optional[MemoryStoreBase] = None,
        **kwargs,
    ) -> str:
        """Explicitly record a high-value item into AGENTS.md (source=user).

        Only works with a knowledge-vault store that exposes the vault
        AGENTS.md API. Falls back to a normal memory_save otherwise.
        """
        store = store or self._memory_store
        content = (content or "").strip()
        if not content:
            return json.dumps({"status": "error", "reason": "empty content"})

        category = (category or "decision").strip().lower()
        vault = getattr(store, "vault", None)
        if vault is None or not hasattr(vault, "read_agents_md"):
            entry = store.write_memory(
                content=content,
                wing=self._wing,
                room=category,
            )
            return json.dumps(
                {
                    "status": "saved",
                    "fallback": True,
                    "id": entry.id,
                    "wing": entry.wing,
                    "room": category,
                },
                ensure_ascii=False,
            )

        try:
            existing = await vault.read_agents_md()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[memory_remember] read AGENTS.md failed: {e}")
            existing = ""
        merged = _insert_agents_md_user_item(existing, content, category)
        try:
            await vault.write_agents_md(merged)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[memory_remember] write AGENTS.md failed: {e}")
            return json.dumps({"status": "error", "reason": str(e)})
        return json.dumps(
            {
                "status": "remembered",
                "source": "user",
                "category": category,
                "section": _AGENTS_MD_CATEGORY_SECTION.get(category, "Conventions"),
            },
            ensure_ascii=False,
        )

    def _do_kg_query(
        self,
        entity: str,
        store: Optional[MemoryStoreBase] = None,
        **kwargs,
    ) -> str:
        store = store or self._memory_store
        try:
            triples = store.kg_query(entity=entity)
        except RuntimeError as e:
            return f"Knowledge graph not available: {e}"

        if not triples:
            return f"No knowledge graph entries found for '{entity}'."

        results = []
        for t in triples:
            results.append(
                {
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object_,
                    "valid_from": t.valid_from,
                    "valid_to": t.valid_to,
                }
            )
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _do_kg_add(
        self,
        subject: str,
        predicate: str,
        object: str,
        store: Optional[MemoryStoreBase] = None,
        **kwargs,
    ) -> str:
        store = store or self._memory_store
        try:
            triple_id = store.kg_add(
                subject=subject,
                predicate=predicate,
                object_=object,
            )
        except RuntimeError as e:
            return f"Knowledge graph not available: {e}"

        return json.dumps(
            {
                "status": "added",
                "triple_id": triple_id,
                "subject": subject,
                "predicate": predicate,
                "object": object,
            },
            ensure_ascii=False,
        )
