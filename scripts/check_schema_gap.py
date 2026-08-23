#!/usr/bin/env python3
"""对比生产 MySQL 库与权威 schema (assets/schema/mysql/gyra.sql) 的列级差异。

背景：schema_migrator 的存量库 baseline 机制会把历史增量脚本"记账跳过"，
导致生产库缺失某些列（如 gpts_work_log.message_id）。本脚本只读不写，
输出缺失列清单 + 自动生成的修复 SQL，供人工确认后执行。

用法：
    python3 scripts/check_schema_gap.py --host <host> --port 3306 \
        --user <user> --password <pwd> --database <db>
    # 也支持环境变量 MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB

输出：
    - 缺失列报告（表.列 列表）
    - 修复 SQL 写入 scripts/out/schema_gap_fix.sql
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "assets" / "schema" / "mysql" / "gyra.sql"
OUT_DIR = ROOT / "scripts" / "out"

# 解析 CREATE TABLE 块：表名 -> {列名: 列定义}
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE",
    re.S | re.I,
)
_COLUMN_RE = re.compile(r"^\s*`(\w+)`\s+(.+?),?\s*$", re.M)


def parse_schema_file(path: Path) -> Dict[str, Dict[str, str]]:
    """从 gyra.sql 提取 表名 -> {列名: 完整列定义}."""
    text = path.read_text(encoding="utf-8")
    tables: Dict[str, Dict[str, str]] = {}
    for m in _CREATE_TABLE_RE.finditer(text):
        table = m.group(1)
        cols: Dict[str, str] = {}
        body = m.group(2)
        # 跳过 PRIMARY KEY / KEY / CONSTRAINT / UNIQUE 等行
        for cm in _COLUMN_RE.finditer(body):
            name, rest = cm.group(1), cm.group(2)
            if rest.upper().startswith(("PRIMARY", "KEY", "UNIQUE", "CONSTRAINT", "FOREIGN")):
                continue
            cols[name] = cm.group(0).strip()
        tables[table] = cols
    return tables


def fetch_db_columns(cursor, database: str) -> Dict[str, Dict[str, str]]:
    """从 information_schema 读取现有表列."""
    cursor.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """,
        (database,),
    )
    result: Dict[str, Dict[str, str]] = {}
    for tname, cname, ctype, nullable, default in cursor.fetchall():
        result.setdefault(tname, {})[cname] = f"{ctype} nullable={nullable} default={default}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="检查生产库与权威 schema 的列差异")
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DB", "gyra"))
    args = parser.parse_args()

    try:
        import pymysql
    except ImportError:
        print("缺少依赖 pymysql，先执行: pip install pymysql", file=sys.stderr)
        return 1

    if not SCHEMA_FILE.is_file():
        print(f"找不到权威 schema 文件: {SCHEMA_FILE}", file=sys.stderr)
        return 1

    target = parse_schema_file(SCHEMA_FILE)
    print(f"权威 schema 解析完成: {len(target)} 张表")

    try:
        conn = pymysql.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.database,
            charset="utf8mb4",
        )
    except Exception as e:
        print(f"连接数据库失败: {e}", file=sys.stderr)
        return 1

    try:
        with conn.cursor() as cursor:
            actual = fetch_db_columns(cursor, args.database)
    finally:
        conn.close()

    print(f"生产库实际表数: {len(actual)}")

    missing_tables: List[str] = []
    missing_cols: List[Tuple[str, str, str]] = []

    for table, cols in target.items():
        if table not in actual:
            missing_tables.append(table)
            continue
        for col, definition in cols.items():
            if col not in actual[table]:
                missing_cols.append((table, col, definition))

    print("\n========== 缺失表（整表不存在） ==========")
    if missing_tables:
        for t in missing_tables:
            print(f"  - {t}")
    else:
        print("  （无）")

    print("\n========== 缺失列（表存在但缺列） ==========")
    if missing_cols:
        for table, col, _ in missing_cols:
            print(f"  - {table}.{col}")
    else:
        print("  （无）—— 生产库列结构与权威 schema 一致")

    # 生成修复 SQL
    if missing_cols or missing_tables:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUT_DIR / "schema_gap_fix.sql"
        lines = ["SET NAMES utf8mb4;", "SET FOREIGN_KEY_CHECKS = 0;", ""]
        for table in missing_tables:
            lines.append(f"-- 缺失整表（若确需新建请手动核对，本脚本不自动建表）")
            lines.append(f"-- CREATE TABLE `{table}` ...;")
            lines.append("")
        for table, col, definition in missing_cols:
            lines.append(f"ALTER TABLE `{table}` ADD COLUMN {definition};")
            lines.append("")
        lines.append("SET FOREIGN_KEY_CHECKS = 1;")
        out_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n修复 SQL 已写入: {out_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
