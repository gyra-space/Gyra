#!/usr/bin/env python3
"""合并 assets/schema/mysql/upgrades/ 下所有增量脚本为一份"真实增量"SQL。

背景：当前 DDL 生成器在版本号不变（0.3.0 -> 0.3.0）时仍按全量 schema 生成
diff，导致 upgrade 脚本互相"累积覆盖"（后一个包含前一个的全部内容），
大部分文件是冗余快照（1400+ 条 DDL 重复）。

本脚本按"真实增量"语义合并：
- CREATE TABLE IF NOT EXISTS : 按表名去重，保留最早出现
- ALTER TABLE ADD COLUMN      : 按 (表, 列) 去重，保留定义（同列重复则保留后出现者）
- ALTER TABLE ADD INDEX       : 按 (表, 索引) 去重，保留最早出现
- ALTER TABLE MODIFY COLUMN   : 按 (表, 列) 取最后一次定义（类型演进以最新为准）

用法：
    python3 scripts/merge_upgrade_ddl.py [--out scripts/out/merged_upgrade_ddl.sql]
    # 输出: 合并后的真实增量 SQL + 精简报告（每个脚本的真实增量条数）

注意：合并结果基于"从空库升级到最新"的完整增量；生产库是存量库时，
实际只需执行 check_schema_gap.py 检测出的缺失部分。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
UPGRADES_DIR = ROOT / "assets" / "schema" / "mysql" / "upgrades"
DEFAULT_OUT = ROOT / "scripts" / "out" / "merged_upgrade_ddl.sql"


def _load_ordered_scripts(upgrades_dir: Path) -> List[Tuple[str, Path]]:
    """按 manifest version 排序返回 (name, path) 列表；无 manifest 则按文件名排序."""
    manifest = upgrades_dir / "manifest.json"
    ordered: List[Tuple[str, Path]] = []
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for item in data.get("scripts", []):
                name = item.get("name", "")
                path = upgrades_dir / name
                if path.is_file():
                    ordered.append((name, path))
        except Exception as e:
            print(f"manifest 解析失败({e})，回退文件名排序", file=sys.stderr)
    if not ordered:
        ordered = [(p.name, p) for p in sorted(upgrades_dir.glob("upgrade_*.sql"))]
    return ordered


def _identifier(dialect: str) -> str:
    """返回标识符包裹符号: mysql=反引号, postgresql=双引号."""
    return "`" if dialect == "mysql" else '"'


def parse_statements(text: str, dialect: str = "mysql"):
    """解析脚本中的三类语句.

    Args:
        text: 脚本内容
        dialect: mysql（反引号）或 postgresql（双引号）

    Returns:
        (tables: Dict[表名, 建表语句],
         add_cols: Dict[(表,列), 定义],
         add_idx: Dict[(表,索引), 语句],
         modify_cols: Dict[(表,列), 语句])
    """
    q = _identifier(dialect)
    tables: Dict[str, str] = {}
    add_cols: Dict[Tuple[str, str], str] = {}
    add_idx: Dict[Tuple[str, str], str] = {}
    modify_cols: Dict[Tuple[str, str], str] = {}

    lines = text.splitlines()
    buf = ""
    for line in lines:
        raw = line.strip()
        if raw.startswith("--") or not raw:
            continue
        buf = raw if not buf else buf + " " + raw
        if not buf.endswith(";"):
            continue
        stmt = buf.rstrip(";").strip()
        buf = ""

        m = re.match(rf"CREATE TABLE IF NOT EXISTS {q}([^{q}]+){q}", stmt, re.I)
        if m:
            tables.setdefault(m.group(1), stmt)
            continue
        m = re.match(rf"ALTER TABLE {q}(\w+){q} ADD COLUMN {q}(\w+){q}", stmt, re.I)
        if m:
            add_cols[(m.group(1), m.group(2))] = stmt  # 保留后出现者（定义更全）
            continue
        # PostgreSQL 索引语法: CREATE INDEX "idx" ON "table" (...)
        m = re.match(rf"CREATE (?:UNIQUE )?INDEX {q}(\w+){q} ON {q}(\w+){q}", stmt, re.I)
        if m:
            add_idx.setdefault((m.group(2), m.group(1)), stmt)
            continue
        # PostgreSQL 修改列: ALTER TABLE "t" ALTER COLUMN "c" TYPE ...
        m = re.match(
            rf"ALTER TABLE {q}(\w+){q} ALTER COLUMN {q}(\w+){q}", stmt, re.I
        )
        if m:
            modify_cols[(m.group(1), m.group(2))] = stmt  # 类型演进取最新
            continue
        m = re.match(
            rf"ALTER TABLE {q}(\w+){q} ADD (?:UNIQUE )?INDEX {q}?(\w+){q}?", stmt, re.I
        )
        if m:
            add_idx.setdefault((m.group(1), m.group(2)), stmt)
            continue
        m = re.match(
            rf"ALTER TABLE {q}(\w+){q} MODIFY COLUMN {q}(\w+){q}", stmt, re.I
        )
        if m:
            modify_cols[(m.group(1), m.group(2))] = stmt  # 类型演进取最新
            continue
        # 其他语句（SET NAMES / FOREIGN_KEY_CHECKS / DROP 等）暂不处理
    return tables, add_cols, add_idx, modify_cols


def main() -> int:
    parser = argparse.ArgumentParser(description="合并增量脚本为真实增量 SQL")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--dialect", default="mysql", choices=["mysql", "postgresql"],
                        help="数据库方言，影响标识符解析（mysql 反引号 / postgresql 双引号）")
    parser.add_argument("--upgrades-dir", default=str(UPGRADES_DIR),
                        help="upgrades 目录路径（默认 assets/schema/mysql/upgrades）")
    args = parser.parse_args()

    upgrades_dir = Path(args.upgrades_dir)
    scripts = _load_ordered_scripts(upgrades_dir)
    if not scripts:
        print(f"目录 {upgrades_dir} 下没有 upgrade 脚本", file=sys.stderr)
        return 1
    print(f"共 {len(scripts)} 个脚本，开始合并（dialect={args.dialect}）...")

    merged_tables: Dict[str, str] = {}
    merged_cols: Dict[Tuple[str, str], str] = {}
    merged_idx: Dict[Tuple[str, str], str] = {}
    merged_modify: Dict[Tuple[str, str], str] = {}

    report: List[str] = []
    prev_cols, prev_idx, prev_tbl = set(), set(), set()
    total_new_cols = total_new_idx = total_new_tbl = 0

    for name, path in scripts:
        text = path.read_text(encoding="utf-8")
        tables, add_cols, add_idx, modify_cols = parse_statements(text, args.dialect)

        new_tbl = set(tables) - prev_tbl
        new_cols = set(add_cols) - prev_cols
        new_idx = set(add_idx) - prev_idx

        merged_tables.update(tables)
        merged_cols.update(add_cols)
        merged_idx.update(add_idx)
        merged_modify.update(modify_cols)

        prev_tbl |= set(tables)
        prev_cols |= set(add_cols)
        prev_idx |= set(add_idx)

        total_new_cols += len(new_cols)
        total_new_idx += len(new_idx)
        total_new_tbl += len(new_tbl)
        report.append(
            f"  {name}: 新增表={len(new_tbl)} 列={len(new_cols)} 索引={len(new_idx)} MODIFY={len(modify_cols)}"
        )

    # ---- 输出合并文件 ----
    lines = [
        "-- Gyra 真实增量合并文件（由 merge_upgrade_ddl.py 生成）",
        "-- 全量权威 schema 见 assets/schema/mysql/gyra.sql",
        "-- 幂等：重复执行时已存在对象报 duplicate 可安全跳过（迁移器 tolerate_duplicate）",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]

    # 建表
    if merged_tables:
        lines.append("-- ============ 新建表 ============")
        for stmt in merged_tables.values():
            lines.append(stmt + ";")
        lines.append("")

    # 加列：按表名分组输出
    if merged_cols:
        lines.append("-- ============ 新增列 ============")
        by_table: Dict[str, List[str]] = OrderedDict()
        for (table, _col), stmt in merged_cols.items():
            by_table.setdefault(table, []).append(stmt)
        for table, stmts in by_table.items():
            lines.append(f"-- 表: {table}")
            lines.extend(s + ";" for s in stmts)
            lines.append("")

    # 加索引
    if merged_idx:
        lines.append("-- ============ 新增索引 ============")
        by_table = OrderedDict()
        for (table, _idx), stmt in merged_idx.items():
            by_table.setdefault(table, []).append(stmt)
        for table, stmts in by_table.items():
            lines.append(f"-- 表: {table}")
            lines.extend(s + ";" for s in stmts)
            lines.append("")

    # 修改列（类型演进）
    if merged_modify:
        lines.append("-- ============ 修改列定义（取最新） ============")
        by_table = OrderedDict()
        for (table, _col), stmt in merged_modify.items():
            by_table.setdefault(table, []).append(stmt)
        for table, stmts in by_table.items():
            lines.append(f"-- 表: {table}")
            lines.extend(s + ";" for s in stmts)
            lines.append("")

    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    lines.append("")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n========== 合并报告 ==========")
    print("\n".join(report))
    print("\n========== 汇总 ==========")
    print(f"  合并后: 新建表={len(merged_tables)} 新增列={len(merged_cols)} 新增索引={len(merged_idx)} MODIFY={len(merged_modify)}")
    print(f"  真实增量（各脚本首次出现）: 表={total_new_tbl} 列={total_new_cols} 索引={total_new_idx}")
    print(f"\n输出文件: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
