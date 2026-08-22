"""DbCatalogConsumer——把可用 DB 列表以 user-role reminder 注入 LLM。

对齐 DSH tool-db + tool-skill 风格：

  - **不**把表 schema / 列定义拼到 system prompt（schema 是运行时数据，
    拼 system prompt 会让 KV-cache 频繁失效 + 占用大块 token）；
  - 仅在 user-role ``<system-reminder>`` 里贴一份**轻量 DB 列表摘要**
    （db_name + type + dialect），与 DSH ``<available_skills>`` 形态对齐；
  - DB 列表变化（agent 增删 DB capability / conn 状态变更）才发替换；
  - 模型通过 ``db({action: "describe_tables" / "list_tables"})`` 按需取
    schema，避免盲写 SQL。

设计依据：[DSH subsystems/skills.md:228-235（digest 变化才注入）+ 
DSH subsystems/credentials.md（资源只发引用 / 详情按需 invoke）]。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


DEFAULT_DESCRIPTION_MAX = 200


# --------------------------------------------------------------------------- #
# 渲染辅助
# --------------------------------------------------------------------------- #

def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace("\"", "&quot;")
    )


def render_available_databases_xml(
    items: List[Dict[str, Any]],
    *,
    description_max: int = DEFAULT_DESCRIPTION_MAX,
) -> str:
    """渲染 ``<available_databases>`` XML 段。

    严格只含 db_name + type + dialect + datasource_id（短标识）；
    摘要 view 不带 schema 详情（按需 ``db({action: "describe_tables"})`` 取）。

    Args:
        items: ``[{"db_name": str, "db_type": str, "dialect": str,
                    "datasource_id": int|str, "description": str}, ...]``
        description_max: 单条 description 截断长度（默认 200）。
    """
    rows: List[str] = []
    for it in items:
        name = (it.get("db_name") or "").strip()
        if not name:
            continue
        desc = (it.get("description") or "").strip()
        if len(desc) > description_max:
            desc = desc[: description_max - 1] + "…"
        db_type = (it.get("db_type") or "").strip()
        dialect = (it.get("dialect") or "").strip()
        ds_id = it.get("datasource_id")
        ds_id_str = (
            str(ds_id) if ds_id is not None and str(ds_id).strip() else ""
        )
        rows.append(
            f"  <database>\n"
            f"    <db_name>{_xml_escape(name)}</db_name>\n"
            f"    <db_type>{_xml_escape(db_type)}</db_type>\n"
            f"    <dialect>{_xml_escape(dialect or db_type)}</dialect>\n"
            f"    <datasource_id>{_xml_escape(ds_id_str)}</datasource_id>\n"
            f"    <description>{_xml_escape(desc)}</description>\n"
            f"  </database>"
        )
    if not rows:
        return ""
    return "<available_databases>\n" + "\n".join(rows) + "\n</available_databases>"


def build_initial_reminder(
    items: List[Dict[str, Any]],
    *,
    description_max: int = DEFAULT_DESCRIPTION_MAX,
) -> Optional[Dict[str, str]]:
    """构造"首次 DB 列表注入"的 user-role reminder 消息（DSH 风格）。"""
    xml = render_available_databases_xml(
        items, description_max=description_max,
    )
    if not xml:
        return None
    return {
        "role": "user",
        "content": (
            "<system-reminder>\n"
            f"{xml}\n\n"
            "Database access is provided by the `db({ action, db_name, ... })` tool. "
            "Use `action: \"list_tables\"` or `\"describe_tables\"` to discover "
            "schema on demand, and `\"execute_sql\"` to run queries. DDL is "
            "disabled by default; data-modification DML is also disabled unless "
            "explicitly enabled.\n"
            "</system-reminder>"
        ),
    }


def build_replacement_reminder(
    items: List[Dict[str, Any]],
    *,
    description_max: int = DEFAULT_DESCRIPTION_MAX,
) -> Dict[str, str]:
    """构造"DB 列表变化时"的完整替换消息。空列表也返回（清空视图）。"""
    xml = render_available_databases_xml(
        items, description_max=description_max,
    )
    return {
        "role": "user",
        "content": (
            "<system-reminder>\n"
            f"{xml}\n\n"
            "Database access is provided by the `db({ action, db_name, ... })` tool. "
            "Use `action: \"list_tables\"` or `\"describe_tables\"` to discover "
            "schema on demand, and `\"execute_sql\"` to run queries. DDL is "
            "disabled by default; data-modification DML is also disabled unless "
            "explicitly enabled.\n"
            "</system-reminder>"
        ),
    }


# --------------------------------------------------------------------------- #
# Consumer（拉模式 + digest 跟踪）
# --------------------------------------------------------------------------- #

@dataclass
class DbCatalogConsumer:
    """DB 列表消费方——跟踪上次 digest，按需产出 user-role reminder。

    与 :class:`SkillCatalogConsumer` 形态一致：consumer 内部 digest 与 provider
    的 digest 计算保持一致；任何对 provider 的 invalidate 都会触发 generation
    增长；consumer 选择用 pull 模式（每次 ``initial`` / ``refresh`` 自检），
    与 DSH 文档行为一致。

    Args:
        provider: 提供 ``list_dbs()`` 与 ``invalidate()`` 的可观察对象。
            V2Agent 用 agent 持有的 ``DBCapability`` 集合（capability_pack
            的 get_all("db") 视图）作为 provider，digest 由
            ``(db_name, db_type, dialect, datasource_id)`` 拼成。
    """

    provider: Any
    description_max: int = DEFAULT_DESCRIPTION_MAX
    _last_published_digest: Optional[str] = None
    _last_published_generation: int = -1

    async def _list(self) -> List[Dict[str, Any]]:
        """从 provider 拉 DB 列表。"""
        if self.provider is None:
            return []
        # provider 可为 list / 可调用 / async callable
        if callable(self.provider):
            value = self.provider()
            if hasattr(value, "__await__"):
                value = await value
            return list(value or [])
        return list(self.provider or [])

    async def _digest(self, items: List[Dict[str, Any]]) -> str:
        payload = "|".join(
            f"{it.get('db_name','')}:{it.get('db_type','')}:"
            f"{it.get('dialect','')}:{it.get('datasource_id','')}"
            for it in items
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    async def _generation(self) -> int:
        """provider 可选暴露 ``generation`` 属性（与 SkillRegistry 对齐）。"""
        return int(getattr(self.provider, "generation", 0) or 0)

    async def initial(self) -> Optional[Dict[str, str]]:
        """首次发布——若 DB 列表非空返回 user-role reminder；否则 None。"""
        items = await self._list()
        self._last_published_digest = await self._digest(items)
        self._last_published_generation = await self._generation()
        return build_initial_reminder(
            items, description_max=self.description_max,
        )

    async def refresh(self) -> Optional[Dict[str, str]]:
        """DB 列表 digest 变化才追加完整替换。"""
        cur_gen = await self._generation()
        items = await self._list()
        cur_digest = await self._digest(items)
        if self._last_published_digest is None:
            return await self.initial()
        if cur_gen == self._last_published_generation and cur_digest == self._last_published_digest:
            return None
        self._last_published_digest = cur_digest
        self._last_published_generation = cur_gen
        return build_replacement_reminder(
            items, description_max=self.description_max,
        )

    def reset(self) -> None:
        """清空状态（新 session / 显式重置）。"""
        self._last_published_digest = None
        self._last_published_generation = -1
