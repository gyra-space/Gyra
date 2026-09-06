"""Unified masking entry point for SQL execution sites.

Every place that runs SQL and hands the result to the LLM or the user
should route the result through :func:`mask_run_result` instead of calling
the masker directly. This guarantees consistent, datasource-scoped,
restart-safe masking across all data exits (agent ``execute_sql``, table
preview, chart rendering, sample-data collection, ...).
"""

import logging
import re
from typing import List, Optional, Set, Tuple

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

_SYSTEM_SCHEMA_NAMES: Set[str] = {
    "information_schema",
    "pg_catalog",
    "pg_toast",
    "performance_schema",
    "mysql",
    "sys",
    "syscat",
    "sysibm",
    "sysstat",
    "system",
}

_SYSTEM_TABLE_NAMES: Set[str] = {
    "all_tables",
    "all_views",
    "all_tab_columns",
    "all_tab_comments",
    "all_col_comments",
    "all_objects",
    "all_constraints",
    "all_cons_columns",
    "all_indexes",
    "all_ind_columns",
    "all_sequences",
    "all_synonyms",
    "all_triggers",
    "all_mviews",
    "all_tab_privs",
    "dual",
    "user_tables",
    "user_views",
    "user_tab_columns",
    "user_objects",
    "user_indexes",
    "user_constraints",
    "user_sequences",
    "user_synonyms",
    "dba_tables",
    "dba_views",
    "dba_objects",
    "dba_tab_columns",
    "dba_users",
    "dba_sequences",
    "dba_indexes",
    "dba_constraints",
    "pg_tables",
    "pg_views",
    "pg_matviews",
    "pg_class",
    "pg_attribute",
    "pg_namespace",
    "pg_proc",
    "pg_type",
    "pg_index",
    "pg_indexes",
    "pg_database",
    "pg_roles",
    "pg_user",
    "pg_groups",
    "pg_settings",
    "pg_stat_activity",
    "pg_stat_user_tables",
    "pg_locks",
    "pg_extension",
    "pg_description",
    "pg_constraint",
    "pg_inherits",
    "pg_am",
    "pg_enum",
    "sqlite_master",
    "sqlite_schema",
    "sqlite_temp_master",
    "sqlite_temp_schema",
    "sqlite_sequence",
}

_INTERNAL_STATEMENT_RE = re.compile(
    r"^\s*(?:SHOW|DESC|DESCRIBE|EXPLAIN)\b", re.IGNORECASE
)


def is_internal_catalog_sql(sql: str) -> bool:
    """Return True when ``sql`` only reads system/internal catalog objects.

    Used to skip result masking for metadata queries (e.g.
    ``SELECT table_name FROM all_tables``) that carry no business data
    yet whose column names easily collide with configured masking rules
    via the column-name fallback. SHOW/DESC/EXPLAIN statements are
    treated as internal too. Any parse failure or mixed business/system
    access conservatively returns False so masking still applies
    (fail-safe).
    """
    if not sql or not sql.strip():
        return False
    if _INTERNAL_STATEMENT_RE.match(sql):
        return True
    try:
        statements = [s for s in sqlglot.parse(sql) if s is not None]
    except Exception:  # noqa: BLE001
        return False
    if not statements:
        return False
    refs: Set[Tuple[str, str]] = set()
    for stmt in statements:
        cte_names = {cte.alias_or_name for cte in stmt.find_all(exp.CTE)}
        for table in stmt.find_all(exp.Table):
            name = (table.name or "").strip('"`[]').lower()
            if not name or name in cte_names:
                continue
            db = (table.db or "").strip('"`[]').lower()
            refs.add((db, name))
    if not refs:
        return False
    return all(
        db in _SYSTEM_SCHEMA_NAMES or name in _SYSTEM_TABLE_NAMES for db, name in refs
    )


def is_internal_catalog_table(table_name: str) -> bool:
    """Return True when ``table_name`` refers to a system/internal catalog object.

    Counterpart of :func:`is_internal_catalog_sql` for call sites that only
    know a single table name (e.g. table preview). Accepts schema
    qualification (``pg_catalog.pg_class``) and quoted identifiers.
    """
    if not table_name:
        return False
    name = table_name.strip().strip('"`[]').lower()
    if not name:
        return False
    if "." in name:
        schema, _, tbl = name.rpartition(".")
        return schema in _SYSTEM_SCHEMA_NAMES or tbl in _SYSTEM_TABLE_NAMES
    return name in _SYSTEM_TABLE_NAMES


def resolve_result_table(sql: Optional[str]) -> Optional[str]:
    """Return the primary (first) non-system table referenced by ``sql``.

    Gives the masker precise table context so it can use exact ``table.column``
    matching instead of a loose column-name fallback (which would mask a column
    that is only sensitive in another table of the same datasource). Returns
    None when no business table can be determined (e.g. pure system catalog
    query or parse failure), leaving the fallback path unchanged.
    """
    if not sql or not sql.strip():
        return None
    try:
        statements = [s for s in sqlglot.parse(sql) if s is not None]
    except Exception:  # noqa: BLE001
        return None
    if not statements:
        return None
    cte_names = {cte.alias_or_name for cte in statements[0].find_all(exp.CTE)}
    for table in statements[0].find_all(exp.Table):
        name = (table.name or "").strip('"`[]')
        if not name or name in cte_names:
            continue
        db = (table.db or "").strip('"`[]')
        if db in _SYSTEM_SCHEMA_NAMES or name in _SYSTEM_TABLE_NAMES:
            continue
        return f"{db}.{name}" if db else name
    return None


def mask_run_result(
    datasource_id: Optional[int],
    columns,
    rows: List,
    *,
    table_name: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Tuple[list, List, List[str]]:
    """Apply privacy masking to a ``connector.run()`` style result set.

    Args:
        datasource_id: Datasource the rows came from. Used to scope which
            masking rules apply (lazily loaded — restart-safe). May be None,
            in which case only globally-registered rules apply.
        columns: Column names (list/tuple).
        rows: Data rows (list of lists/tuples).
        table_name: Table name, when known, for precise table.column lookup.
        session_id: Conversation/session id for tokenization mode.

    Returns:
        (columns, masked_rows, masked_column_names). On any failure the
        original columns/rows are returned unchanged with an empty masked
        list, so masking can never break a query path.
    """
    if not rows or not columns:
        return columns, rows, []
    try:
        from gyra_serve.sql_guard.masking.masker import get_data_masker

        masker = get_data_masker()
        return masker.mask_results_ex(
            columns,
            rows,
            datasource_id=datasource_id,
            table_name=table_name,
            session_id=session_id,
        )
    except ImportError:
        return columns, rows, []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Data masking failed, returning unmasked result: {e}")
        return columns, rows, []
