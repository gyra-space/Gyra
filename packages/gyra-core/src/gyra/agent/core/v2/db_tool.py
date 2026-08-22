"""DbTool——V2 引擎统一 ``db({ action, ... })`` 工具（对齐 DSH tool-db）。

将 V1 的 4 个 DB 工具 ``get_table_spec`` / ``execute_sql`` / ``list_tables`` /
``search_tables`` 收敛为单一模型入口：

  - ``db({ action: "list_tables", db_name, ... })``
  - ``db({ action: "describe_tables", db_name, table_names, ... })``
  - ``db({ action: "search", db_name, question, ... })``
  - ``db({ action: "execute_sql", db_name, sql, ... })``

设计动机（对齐 DSH tool-db + DSH tool-skill 风格）：
  1. **不在 system prompt 拼 schema**：DB schema 是运行时数据，DSH 一致把
     "可用 DB 列表" 的**摘要**作为 user-role reminder 注入，让模型按需用
     ``db({action: "list_tables"})`` / ``describe_tables`` 取详情；
  2. **单入口替代多 tool**：4 个 V1 工具合并为 1 个 V2 工具，模型只需掌握
     1 个工具签名，减少 tool 列表 token 开销 + 调用入口碎片化；
  3. **V1 完全兼容**：原 4 个 V1 工具继续保留（``@tool`` 自动注册 + builtin
     Route A），V1 链路零变化；DbTool 仅作为 V2 引擎的额外注册项。

设计依据：[DSH skills.md / credentials.md / subsystems/tools.md]（DSH 把资源
工具化 + on-demand invoke 的统一模式）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from gyra.agent.tools.base import ToolBase, ToolCategory, ToolRiskLevel
from gyra.agent.tools.context import ToolContext
from gyra.agent.tools.metadata import ToolMetadata
from gyra.agent.tools.result import ToolResult

logger = logging.getLogger(__name__)


DB_TOOL_NAME = "db"
DB_TOOL_DESCRIPTION = (
    "Unified database access tool.\n\n"
    "Use the `action` field to choose what to do:\n"
    '  - "list_tables" (args: db_name, group?, page?, page_size?)\n'
    '  - "describe_tables" (args: db_name, table_names?, question?)\n'
    '  - "search" (args: db_name, question) - Schema Linking recommend mode\n'
    '  - "execute_sql" (args: db_name, sql, page?, page_size?, output_to_file?)\n\n'
    "Notes:\n"
    "  - Use the database names from the available-databases reminder in the system prompt.\n"
    "  - Use describe_tables / list_tables first to discover schema before writing SQL.\n"
    "  - DDL is disabled by default; data-modification DML is also disabled unless explicitly enabled.\n"
    "  - Set output_to_file=true on execute_sql to spill large results to a sandbox file."
)


_DB_ACTIONS = ("list_tables", "describe_tables", "search", "execute_sql")


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace("\"", "&quot;")
    )


class DbTool(ToolBase):
    """V2 引擎统一 ``db({ action, ... })`` 工具（对齐 DSH tool-db）。"""

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=DB_TOOL_NAME,
            display_name="Database",
            description=DB_TOOL_DESCRIPTION,
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.MEDIUM,
            requires_permission=True,  # SQL 执行需要审批
            timeout=120,
            tags=["db", "sql", "database", "v2", "dsh-style"],
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": list(_DB_ACTIONS),
                    "description": "DB action to perform.",
                },
                "db_name": {
                    "type": "string",
                    "description": "Database name (from available-databases reminder).",
                },
                "datasource_id": {
                    "type": "integer",
                    "description": "Optional datasource_id (preferred over db_name when known).",
                },
                "table_names": {
                    "type": "string",
                    "description": "Comma-separated table names (for describe_tables).",
                },
                "question": {
                    "type": "string",
                    "description": "Natural-language question (for describe_tables / search).",
                },
                "sql": {
                    "type": "string",
                    "description": "SQL statement (for execute_sql).",
                },
                "page": {
                    "type": "integer",
                    "description": "1-based page number (for execute_sql / list_tables).",
                    "default": 1,
                },
                "page_size": {
                    "type": "integer",
                    "description": "Page size (for execute_sql / list_tables).",
                    "default": 50,
                },
                "group": {
                    "type": "string",
                    "description": "Group filter (for list_tables).",
                },
                "output_to_file": {
                    "type": "boolean",
                    "description": "Spill large results to a sandbox file (execute_sql).",
                    "default": False,
                },
            },
            "required": ["action"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None,
    ) -> ToolResult:
        action = (args.get("action") or "").strip()
        if not action:
            return ToolResult.fail(
                error="action is required (one of: list_tables, describe_tables, search, execute_sql)",
                tool_name=self.name,
            )
        if action not in _DB_ACTIONS:
            return ToolResult.fail(
                error=f"Unknown action {action!r}; must be one of {list(_DB_ACTIONS)}",
                tool_name=self.name,
            )

        # 懒导入 V1 工具实现（serve 层；core 不直接依赖）
        try:
            from gyra_serve.agent.capabilities.db.tools._db_tools_impl import (
                get_table_spec,
                execute_sql,
                list_tables,
                search_tables,
            )
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(
                error=(
                    f"DB tools unavailable (serve-layer import failed: {e}). "
                    "Make sure gyra-serve is installed and DB capability is wired."
                ),
                tool_name=self.name,
            )

        # V1 工具函数期望 kwargs 里带 agent / context
        v1_kwargs: Dict[str, Any] = {
            "context": context,
        }
        agent = getattr(context, "agent", None) if context is not None else None
        if agent is not None:
            v1_kwargs["agent"] = agent

        try:
            if action == "list_tables":
                db_name = args.get("db_name")
                if not db_name:
                    return ToolResult.fail(
                        error="db_name is required for action=list_tables",
                        tool_name=self.name,
                    )
                output = await list_tables(
                    db_name=db_name,
                    group=args.get("group"),
                    page=int(args.get("page", 1) or 1),
                    page_size=int(args.get("page_size", 100) or 100),
                    **v1_kwargs,
                )
            elif action == "describe_tables":
                # 等价 V1 ``get_table_spec`` 的两模式：table_names / question
                output = await get_table_spec(
                    table_names=args.get("table_names"),
                    question=args.get("question"),
                    datasource_id=args.get("datasource_id"),
                    db_name=args.get("db_name"),
                    **v1_kwargs,
                )
            elif action == "search":
                # Schema Linking 推荐表（``search_tables`` 的语义）
                question = args.get("question") or args.get("db_name")
                if not args.get("db_name") or not question:
                    return ToolResult.fail(
                        error="db_name and question are required for action=search",
                        tool_name=self.name,
                    )
                output = await search_tables(
                    db_name=args["db_name"],
                    question=question,
                    **v1_kwargs,
                )
            elif action == "execute_sql":
                db_name = args.get("db_name")
                sql = args.get("sql")
                if not db_name or not sql:
                    return ToolResult.fail(
                        error="db_name and sql are required for action=execute_sql",
                        tool_name=self.name,
                    )
                output = await execute_sql(
                    db_name=db_name,
                    sql=sql,
                    page=int(args.get("page", 1) or 1),
                    page_size=int(args.get("page_size", 50) or 50),
                    output_to_file=bool(args.get("output_to_file", False)),
                    **v1_kwargs,
                )
            else:  # pragma: no cover - guarded above
                return ToolResult.fail(
                    error=f"Unsupported action: {action!r}",
                    tool_name=self.name,
                )
        except Exception as e:  # noqa: BLE001
            logger.exception("[DbTool] V1 dispatch failed")
            return ToolResult.fail(
                error=f"db action {action!r} failed: {e}",
                tool_name=self.name,
            )

        return ToolResult.ok(
            output=str(output) if output is not None else "",
            tool_name=self.name,
            metadata={"action": action, "db_name": args.get("db_name") or ""},
        )
